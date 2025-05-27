import discord
from discord.ext import commands
import asyncio
import os
import subprocess
from lib.VOICEVOXlib import VOICEVOXLib
from discord import app_commands
from lib.postgres import PostgresDB  # PostgresDBをインポート
import uuid
import re
from dotenv import load_dotenv  # dotenvをインポート

class VoiceReadCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voicelib = VOICEVOXLib()
        self.speaker_id = 1
        self.tts_channels = {}      # {guild.id: channel.id}
        self.message_queues = {}    # {guild.id: asyncio.Queue}
        self.queue_tasks = {}       # {guild.id: Task}
        self.db = PostgresDB()  # データベースインスタンスを初期化
        self.cleanup_task = None  # 定期的なクリーンアップタスク
        load_dotenv()  # .envファイルを読み込む
        self.reconnect_enabled = os.getenv("RECONNECT", "true").lower() != "false"  # reconnect設定を取得

    async def cog_load(self):
        await self.db.initialize()  # データベース接続を初期化
        self.cleanup_task = self.bot.loop.create_task(self.cleanup_temp_files())
        self.banlist = set(await self.db.fetch_column("SELECT user_id FROM banlist"))  # BANリストをキャッシュ

        if not self.reconnect_enabled:
            print("Reconnect is disabled. Skipping VC state restoration.")
            return  # 再接続が無効の場合はスキップ

        # VC接続状態を復元
        vc_states = await self.db.fetch("SELECT guild_id, channel_id, tts_channel_id FROM vc_state")
        for state in vc_states:
            guild = self.bot.get_guild(state['guild_id'])
            vc_channel = guild.get_channel(state['channel_id'])
            tts_channel = guild.get_channel(state['tts_channel_id'])
            if guild and vc_channel and tts_channel:
                # チャンネルに人がいない場合はスキップ
                if not vc_channel.members or all(member.bot for member in vc_channel.members):
                    print(f"Skipping reconnection to empty VC in guild {guild.id}")
                    continue
                try:
                    await vc_channel.connect()
                    await guild.change_voice_state(channel=vc_channel, self_mute=False, self_deaf=True)
                    self.tts_channels[guild.id] = tts_channel.id
                    self.message_queues[guild.id] = asyncio.Queue()
                    self.queue_tasks[guild.id] = self.bot.loop.create_task(self.process_queue(guild.id))
                except Exception as e:
                    print(f"Failed to reconnect to VC in guild {guild.id}: {e}")

    async def cog_unload(self):
        await self.db.close()  # データベース接続を閉じる
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

    async def is_banned(self, user_id: int) -> bool:
        """ユーザーがBANされているか確認"""
        return user_id in self.banlist

    @app_commands.command(name="join", description="ボイスチャンネルに参加")
    async def join(self, interaction: discord.Interaction):
        if await self.is_banned(interaction.user.id):
            await interaction.response.send_message("このコマンドを実行する権限がありません。", ephemeral=True)
            return
        if interaction.user.voice:
            channel = interaction.user.voice.channel
            await channel.connect()
            await channel.guild.change_voice_state(channel=channel, self_mute=False, self_deaf=True)
            # 記録する（テキストチャンネルはコマンド実行時のチャンネル）
            self.tts_channels[interaction.guild.id] = interaction.channel.id
            self.message_queues[interaction.guild.id] = asyncio.Queue()
            self.queue_tasks[interaction.guild.id] = self.bot.loop.create_task(self.process_queue(interaction.guild.id))
            
            # データベースにVC接続状態を保存
            await self.db.execute(
                "INSERT INTO vc_state (guild_id, channel_id, tts_channel_id) VALUES ($1, $2, $3) ON CONFLICT (guild_id) DO UPDATE SET channel_id = $2, tts_channel_id = $3",
                interaction.guild.id, channel.id, interaction.channel.id
            )

            # 「接続しました。」と喋る処理を非同期で実行
            async def play_connection_message():
                tmp_wav = f"tmp_{uuid.uuid4()}_join.wav"  # UUIDを使用
                await self.voicelib.synthesize("接続しました。", self.speaker_id, tmp_wav)
                voice_client = interaction.guild.voice_client
                if voice_client and not voice_client.is_playing():
                    audio_source = discord.FFmpegPCMAudio(tmp_wav)
                    voice_client.play(audio_source)
                    while voice_client.is_playing():
                        await asyncio.sleep(0.5)
                if os.path.exists(tmp_wav):
                    os.remove(tmp_wav)

            self.bot.loop.create_task(play_connection_message())

            embed = discord.Embed(
                title="接続完了",
                description=f"{channel.name}に接続しました。\n\nこのbotは、[Swiftly](https://discord.com/oauth2/authorize?client_id=1310198598213963858)の派生botです。\n\n導入リンク: https://discord.com/oauth2/authorize?client_id=1371465579780767824\n\nサポートサーバー: https://discord.gg/mNDvAYayp5",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Hosted by sakana11.org")
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(
                title="エラー",
                description="先にボイスチャンネルに参加してください。",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="leave", description="ボイスチャンネルから退出")
    async def leave(self, interaction: discord.Interaction):
        if await self.is_banned(interaction.user.id):
            await interaction.response.send_message("このコマンドを実行する権限がありません。", ephemeral=True)
            return
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            # キュー・タスク等をリセット
            if interaction.guild.id in self.queue_tasks:
                self.queue_tasks[interaction.guild.id].cancel()
                del self.queue_tasks[interaction.guild.id]
            self.tts_channels.pop(interaction.guild.id, None)
            self.message_queues.pop(interaction.guild.id, None)
            # データベースからVC接続状態を削除
            await self.db.execute("DELETE FROM vc_state WHERE guild_id = $1", interaction.guild.id)
            embed = discord.Embed(
                title="退出完了",
                description="ボイスチャンネルから退出しました。\nご利用ありがとうございました。\n\n導入リンク: https://discord.com/oauth2/authorize?client_id=1371465579780767824",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(
                title="エラー",
                description="ボイスチャンネルに接続していません。",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="read", description="テキストを合成して読み上げる")
    async def read(self, interaction: discord.Interaction, text: str):
        if await self.is_banned(interaction.user.id):
            await interaction.response.send_message("このコマンドを実行する権限がありません。", ephemeral=True)
            return
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            embed = discord.Embed(
                title="エラー",
                description="ボイスチャンネルに接続していません。",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        await interaction.response.defer()
        # テキストを辞書で変換
        text = await self.apply_dictionary(text)
        try:
            tmp_wav = f"tmp/tmp_{uuid.uuid4()}_read.wav"  # UUIDを使用
            await self.voicelib.synthesize(text, self.speaker_id, tmp_wav)
        except Exception:
            return
        if not voice_client.is_playing():
            audio_source = discord.FFmpegPCMAudio(tmp_wav)
            voice_client.play(audio_source)
            while voice_client.is_playing():
                await asyncio.sleep(0.5)
        if os.path.exists(tmp_wav):
            os.remove(tmp_wav)
        embed = discord.Embed(
            title="再生完了",
            description="テキストの読み上げが完了しました。\n\n導入リンク: https://discord.com/oauth2/authorize?client_id=1371465579780767824",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="voice", description="読み上げる声を設定")
    @app_commands.choices(
        speaker=[
            app_commands.Choice(name="四国めたん", value="四国めたん"),
            app_commands.Choice(name="ずんだもん", value="ずんだもん"),
            app_commands.Choice(name="春日部つむぎ", value="春日部つむぎ"),
        ]
    )
    async def voice(self, interaction: discord.Interaction, speaker: app_commands.Choice[str]):
        if await self.is_banned(interaction.user.id):
            await interaction.response.send_message("あなたはbotからBANされています。", ephemeral=True)
            return

        speaker_map = {
            "四国めたん": 0,
            "ずんだもん": 1,
            "春日部つむぎ": 2,
        }

        speaker_id = speaker_map[speaker.value]
        try:
            await self.db.execute(
                "INSERT INTO user_voice (user_id, speaker_id) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET speaker_id = $2",
                interaction.user.id, speaker_id
            )
            embed = discord.Embed(
                title="声の設定完了",
                description=f"あなたの声を **{speaker.value}** に設定しました。",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)
        except Exception as e:
            embed = discord.Embed(
                title="エラー",
                description="エラーが発生しました。詳細は管理者にお問い合わせください。",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def get_user_speaker_id(self, user_id: int) -> int:
        """ユーザーのスピーカーIDを取得"""
        row = await self.db.fetchrow("SELECT speaker_id FROM user_voice WHERE user_id = $1", user_id)
        return row['speaker_id'] if row else self.speaker_id  # デフォルトはself.speaker_id

    async def process_queue(self, guild_id):
        """サーバーごとの読み上げキューを処理"""
        guild = self.bot.get_guild(guild_id)
        queue = self.message_queues.get(guild_id)
        if not queue:
            return  # キューが存在しない場合は終了
        while True:
            try:
                text, speaker_id = await queue.get()  # キューからテキストとスピーカーIDを取得
                voice_client = guild.voice_client
                # ボイスチャンネル未接続の場合はスキップ
                if not voice_client or not voice_client.is_connected():
                    continue
                # テキストを辞書で変換
                text = await self.apply_dictionary(text)
                tmp_wav = f"tmp_{uuid.uuid4()}_queue.wav"  # UUIDを使用
                await self.voicelib.synthesize(text, speaker_id, tmp_wav)
                if not voice_client.is_playing():
                    audio_source = discord.FFmpegPCMAudio(tmp_wav)
                    voice_client.play(audio_source)
                    while voice_client.is_playing():
                        await asyncio.sleep(0.5)
                if os.path.exists(tmp_wav):
                    os.remove(tmp_wav)
            except asyncio.CancelledError:
                break  # タスクがキャンセルされた場合は終了
            except Exception as e:
                continue  # その他のエラーは無視して次のメッセージへ
            await asyncio.sleep(0.1)  # 少し待機して次のメッセージへ

    @commands.Cog.listener()
    async def on_message(self, message):
        """メッセージを読み上げキューに追加"""
        if await self.is_banned(message.author.id):
            return  # BANされたユーザーのメッセージは無視
        # BotやDMは無視
        if message.author.bot or not message.guild:
            return
        # joinコマンドが実行されたチャンネルか確認
        tts_channel_id = self.tts_channels.get(message.guild.id)
        if tts_channel_id != message.channel.id:
            return  # 違うチャンネルの場合は無視
        # キューが存在しない場合は初期化
        queue = self.message_queues.setdefault(message.guild.id, asyncio.Queue())
        # 添付画像の枚数をカウント
        image_count = sum(1 for a in message.attachments if a.content_type and a.content_type.startswith("image/"))
        # 読み上げテキストを決定
        if image_count > 0:
            if image_count == 1:
                tts_text = "1枚の画像"
            else:
                tts_text = f"{image_count}枚の画像"
        else:
            tts_text = message.content  # メッセージ本文（str型）

        # ユーザーのスピーカーIDを取得
        speaker_id = await self.get_user_speaker_id(message.author.id)
        await queue.put((tts_text, speaker_id))  # テキストとスピーカーIDをキューに追加
        # コマンドの処理も継続
        await self.bot.process_commands(message)

    @app_commands.command(name="dictionary", description="読み上げ辞書を設定")
    async def dictionary(self, interaction: discord.Interaction, key: str, value: str):
        if await self.is_banned(interaction.user.id):
            await interaction.response.send_message("あなたはbotからBANされています。", ephemeral=True)
            return
        try:
            author_id = interaction.user.id  # 登録者のユーザーIDを取得
            await self.db.execute(
                "INSERT INTO dictionary (key, value, author_id) VALUES ($1, $2, $3) ON CONFLICT (key) DO UPDATE SET value = $2, author_id = $3",
                key, value, author_id
            )
            embed = discord.Embed(
                title="辞書更新",
                description=f"辞書に追加しました: **{key}** -> **{value}**\n\n導入リンク: https://discord.com/oauth2/authorize?client_id=1371465579780767824",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)
        except Exception as e:
            embed = discord.Embed(
                title="エラー",
                description="エラーが発生しました。詳細は管理者にお問い合わせください。",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="dictionary-remove", description="読み上げ辞書を削除")
    async def dictionary_remove(self, interaction: discord.Interaction, key: str):
        if await self.is_banned(interaction.user.id):
            await interaction.response.send_message("あなたはbotからBANされています。", ephemeral=True)
            return
        try:
            result = await self.db.execute("DELETE FROM dictionary WHERE key = $1", key)
            if result == "DELETE 1":
                embed = discord.Embed(
                    title="辞書削除",
                    description=f"辞書から削除しました: **{key}**\n\n導入リンク: https://discord.com/oauth2/authorize?client_id=1371465579780767824",
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="エラー",
                    description=f"指定されたキーが見つかりません: **{key}**",
                    color=discord.Color.red()
                )
            await interaction.response.send_message(embed=embed, ephemeral=False)
        except Exception as e:
            embed = discord.Embed(
                title="エラー",
                description="エラーが発生しました。詳細は管理者にお問い合わせください。",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="dictionary-search", description="読み上げ辞書を検索")
    async def dictionary_search(self, interaction: discord.Interaction, key: str):
        if await self.is_banned(interaction.user.id):
            await interaction.response.send_message("あなたはbotからBANされています。", ephemeral=True)
            return
        try:
            row = await self.db.fetchrow("SELECT value, author_id FROM dictionary WHERE key = $1", key)
            if row:
                author_id = row['author_id']
                if interaction.user.id == 1241397634095120438:
                    description = f"**{key}** -> **{row['value']}**\n登録者: <@{author_id}>"
                else:
                    description = f"**{key}** -> **{row['value']}**"
                embed = discord.Embed(
                    title="辞書検索結果",
                    description=f"{description}\n\n導入リンク: https://discord.com/oauth2/authorize?client_id=1371465579780767824",
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="エラー",
                    description=f"指定されたキーが見つかりません: **{key}**",
                    color=discord.Color.red()
                )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                title="エラー",
                description="エラーが発生しました。詳細は管理者にお問い合わせください。",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def apply_dictionary(self, text: str) -> str:
        """辞書を適用してテキストを変換"""
        # キャッシュメッセージから該当するものを取得し、存在すればメンション変換を行う
        msg = discord.utils.get(self.bot.cached_messages, content=text)
        if msg:
            for user_id in {m.id for m in msg.mentions}:
                user = await self.bot.fetch_user(user_id)
                if user:
                    text = text.replace(f"<@{user_id}>", f"あっと{user.display_name}")
                    text = text.replace(f"<@!{user_id}>", f"あっと{user.display_name}")
        # カスタム絵文字 <a:name:id> または <name:id> を「えもじ:名前」に変換
        text = re.sub(r'<a?:([a-zA-Z0-9_]+):\d+>', lambda m: f"えもじ:{m.group(1)}", text)
        # スタンプ <:[a-zA-Z0-9_]+:\d+> も同様に「すたんぷ:名前」に変換
        text = re.sub(r'<a?:([a-zA-Z0-9_]+):\d+>', lambda m: f"すたんぷ:{m.group(1)}", text)
        # Unicode絵文字はそのまま
        # http/httpsリンクを「リンク省略」に変換
        text = re.sub(r'https?://\S+', 'リンク省略', text)
        rows = await self.db.fetch("SELECT key, value FROM dictionary")
        for row in rows:
            text = text.replace(row['key'], row['value'])
        # 70文字以上の場合、省略
        if len(text) > 70:
            text = text[:70] + "省略"
        return text

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """ボイスチャンネルの状態変化を監視"""
        try:
            guild = member.guild
            voice_client = guild.voice_client

            # ボットのみになった場合は切断
            if voice_client and voice_client.channel and len(voice_client.channel.members) == 1:
                await voice_client.disconnect()
                if guild.id in self.queue_tasks:
                    self.queue_tasks[guild.id].cancel()
                    del self.queue_tasks[guild.id]
                self.tts_channels.pop(guild.id, None)
                self.message_queues.pop(guild.id, None)
                # データベースからVC接続状態を削除
                await self.db.execute("DELETE FROM vc_state WHERE guild_id = $1", guild.id)
                return

            # ボイスチャンネル未接続の場合の処理や接続チェック
            if voice_client and before.channel == voice_client.channel and after.channel != voice_client.channel:
                # ボットがVCから追放された場合
                if member == guild.me:
                    await voice_client.disconnect()
                    if guild.id in self.queue_tasks:
                        self.queue_tasks[guild.id].cancel()
                        del self.queue_tasks[guild.id]
                    self.tts_channels.pop(guild.id, None)
                    self.message_queues.pop(guild.id, None)
                    # データベースからVC接続状態を削除
                    await self.db.execute("DELETE FROM vc_state WHERE guild_id = $1", guild.id)
                    return

            # 参加・退出時にTTSを再生
            if before.channel is None and after.channel is not None:
                msg = f"{member.display_name}が参加しました。"
            elif before.channel is not None and after.channel is None:
                msg = f"{member.display_name}が退出しました。"
            else:
                return

            if not voice_client or not voice_client.is_connected():
                return

            # メッセージをキューに追加（システム音声はスピーカーIDを1に固定）
            queue = self.message_queues.setdefault(guild.id, asyncio.Queue())
            await queue.put(f"{msg}")  # システム音声用
            # ここでプロセスタスクが存在しなければ作成する
            if guild.id not in self.queue_tasks or self.queue_tasks[guild.id].done():
                self.queue_tasks[guild.id] = self.bot.loop.create_task(self.process_queue(guild.id))

        except Exception as e:
            print(f"Error in on_voice_state_update: {e}")

    async def cleanup_temp_files(self):
        """定期的に不要なwavファイルを削除"""
        while True:
            try:
                temp_dir = "tmp"
                if os.path.exists(temp_dir):
                    for file in os.listdir(temp_dir):
                        if file.endswith(".wav"):
                            file_path = os.path.join(temp_dir, file)
                            try:
                                os.remove(file_path)
                                print(f"Deleted temp file: {file_path}")
                            except Exception as e:
                                print(f"Failed to delete {file_path}: {e}")
                await asyncio.sleep(3600)  # 1時間ごとに実行
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in cleanup_temp_files: {e}")
                await asyncio.sleep(3600)

async def setup(bot):
    await bot.add_cog(VoiceReadCog(bot))
