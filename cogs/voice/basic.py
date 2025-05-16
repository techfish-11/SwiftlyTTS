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

    async def cog_load(self):
        await self.db.initialize()  # データベース接続を初期化
        self.cleanup_task = self.bot.loop.create_task(self.cleanup_temp_files())
        self.banlist = set(await self.db.fetch_column("SELECT user_id FROM banlist"))  # BANリストをキャッシュ

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

    async def process_queue(self, guild_id):
        """サーバーごとの読み上げキューを処理"""
        guild = self.bot.get_guild(guild_id)
        queue = self.message_queues.get(guild_id)
        if not queue:
            return  # キューが存在しない場合は終了
        while True:
            try:
                text = await queue.get()  # キューからテキストを取得
                voice_client = guild.voice_client
                # ボイスチャンネル未接続の場合はスキップ
                if not voice_client or not voice_client.is_connected():
                    continue
                # テキストを辞書で変換
                text = await self.apply_dictionary(text)
                tmp_wav = f"tmp_{uuid.uuid4()}_queue.wav"  # UUIDを使用
                await self.voicelib.synthesize(text, self.speaker_id, tmp_wav)
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
            tts_text = message.content  # メッセージ本文（str型）をキューに追加
        await queue.put(tts_text)
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
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                title="エラー",
                description=f"エラーが発生しました: {e}",
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
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                title="エラー",
                description=f"エラーが発生しました",
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
                description=f"エラーが発生しました",
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
                return

            # ボイスチャンネル未接続の場合の処理や接続チェック
            # 参加・退出時にTTSを再生
            if before.channel is None and after.channel is not None:
                msg = f"{member.display_name}が参加しました。"
            elif before.channel is not None and after.channel is None:
                msg = f"{member.display_name}が退出しました。"
            else:
                return

            if not voice_client or not voice_client.is_connected():
                return

            # メッセージをキューに追加（str型で追加）
            queue = self.message_queues.setdefault(guild.id, asyncio.Queue())
            await queue.put(str(msg))
            print(f"Added to queue: {msg}")
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
