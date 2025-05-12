import discord
from discord.ext import commands
import asyncio
import os
from lib.VOICEVOXlib import VOICEVOXLib
from discord import app_commands
from lib.postgres import PostgresDB  # PostgresDBをインポート

class VoiceReadCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voicelib = VOICEVOXLib()
        self.speaker_id = 1
        self.tts_channels = {}      # {guild.id: channel.id}
        self.message_queues = {}    # {guild.id: asyncio.Queue}
        self.queue_tasks = {}       # {guild.id: Task}
        self.db = PostgresDB()  # データベースインスタンスを初期化

    async def cog_load(self):
        await self.db.initialize()  # データベース接続を初期化

    async def cog_unload(self):
        await self.db.close()  # データベース接続を閉じる

    @app_commands.command(name="join", description="ボイスチャンネルに参加")
    async def join(self, interaction: discord.Interaction):
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
                tmp_wav = f"tmp_{interaction.id}_join.wav"
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
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            embed = discord.Embed(
                title="エラー",
                description="ボイスチャンネルに接続していません。",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        tmp_wav = f"tmp_{interaction.id}.wav"
        await interaction.response.defer()
        # テキストを辞書で変換
        text = await self.apply_dictionary(text)
        await self.voicelib.synthesize(text, self.speaker_id, tmp_wav)
        audio_source = discord.FFmpegPCMAudio(tmp_wav)
        if not voice_client.is_playing():
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
        while True:
            queue = self.message_queues.get(guild_id)
            if not queue:
                break  # キューが存在しない場合は終了
            message = await queue.get()
            voice_client = guild.voice_client
            # ボイスチャンネル未接続の場合はスキップ
            if not voice_client or not voice_client.is_connected():
                continue
            tmp_wav = f"tmp_{guild_id}_{message.id}.wav"
            try:
                # メッセージ内容を辞書で変換
                text = await self.apply_dictionary(message.content)
                # メッセージ内容を合成
                await self.voicelib.synthesize(text, self.speaker_id, tmp_wav)
            except Exception:
                continue
            audio_source = discord.FFmpegPCMAudio(tmp_wav)
            if not voice_client.is_playing():
                voice_client.play(audio_source)
                while voice_client.is_playing():
                    await asyncio.sleep(0.5)
            if os.path.exists(tmp_wav):
                os.remove(tmp_wav)
            await asyncio.sleep(0.1)  # 少し待機して次のメッセージへ

    @commands.Cog.listener()
    async def on_message(self, message):
        """メッセージを読み上げキューに追加"""
        # BotやDMは無視
        if message.author.bot or not message.guild:
            return
        # 登録済みテキストチャンネルで送信されたときのみ
        if self.tts_channels.get(message.guild.id) == message.channel.id:
            queue = self.message_queues.setdefault(message.guild.id, asyncio.Queue())
            await queue.put(message)

    @app_commands.command(name="dictionary", description="読み上げ辞書を設定")
    async def dictionary(self, interaction: discord.Interaction, key: str, value: str):
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
        # メンションを「あっと<名前>」に置き換え
        for user_id in set(discord.utils.find_mentions(text)):
            user = await self.bot.fetch_user(user_id)
            if user:
                text = text.replace(f"<@{user_id}>", f"あっと{user.display_name}")
                text = text.replace(f"<@!{user_id}>", f"あっと{user.display_name}")  # ニックネーム形式も対応

        rows = await self.db.fetch("SELECT key, value FROM dictionary")
        for row in rows:
            text = text.replace(row['key'], row['value'])
        # 70文字以上の場合、省略
        if len(text) > 70:
            text = text[:70] + "省略"
        return text

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # Botがボイスチャンネルに接続している場合のみ処理
        for guild_id, voice_client in [(g.id, g.voice_client) for g in self.bot.guilds if g.voice_client]:
            if voice_client and voice_client.channel and len(voice_client.channel.members) == 1:
                # ボイスチャンネルにBotしかいない場合
                await voice_client.disconnect()
                # キュー・タスク等をリセット
                if guild_id in self.queue_tasks:
                    self.queue_tasks[guild_id].cancel()
                    del self.queue_tasks[guild_id]
                self.tts_channels.pop(guild_id, None)
                self.message_queues.pop(guild_id, None)

        # ライブ配信開始を検知
        if before.self_stream is False and after.self_stream is True:
            guild_id = member.guild.id
            if guild_id in self.tts_channels:
                text = f"{member.display_name}がライブ配信を開始しました"
                queue = self.message_queues.setdefault(guild_id, asyncio.Queue())
                await queue.put(discord.Object(id=0, content=text))  # 仮のメッセージオブジェクトをキューに追加

        # メンバーがボイスチャンネルに参加した場合
        if not before.channel and after.channel:
            guild_id = member.guild.id
            if guild_id in self.tts_channels:
                text = f"{member.display_name}が参加しました"
                queue = self.message_queues.setdefault(guild_id, asyncio.Queue())
                await queue.put(discord.Object(id=0, content=text))  # 仮のメッセージオブジェクトをキューに追加

        # メンバーがボイスチャンネルから退出した場合
        if before.channel and not after.channel:
            guild_id = member.guild.id
            if guild_id in self.tts_channels:
                text = f"{member.display_name}が退出しました"
                queue = self.message_queues.setdefault(guild_id, asyncio.Queue())
                await queue.put(discord.Object(id=0, content=text))  # 仮のメッセージオブジェクトをキューに追加

async def setup(bot):
    await bot.add_cog(VoiceReadCog(bot))
