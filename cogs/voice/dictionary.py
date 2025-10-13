import discord
from discord.ext import commands
from discord import app_commands
from lib.postgres import PostgresDB  # PostgresDBをインポート
import re
from discord.ui import View, Button
import asyncio
import time

class DictionaryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = PostgresDB()  # データベースインスタンスを初期化
        self.voice_cog = None  # VoiceReadCogの参照
        self.global_dict_cache = []
        self.server_dict_cache = {}  # guild_id: list of dict rows
        self.user_dict_cache = {}  # user_id: list of dict rows
        self.cache_lock = asyncio.Lock()
        self.cache_task = None
        self.cache_last_update = 0

    async def cog_load(self):
        await self.db.initialize()  # データベース接続を初期化
        self.voice_cog = self.bot.get_cog("VoiceReadCog")  # VoiceReadCogを取得
        self.cache_task = self.bot.loop.create_task(self.cache_updater())

    async def cog_unload(self):
        await self.db.close()  # データベース接続を閉じる
        if self.cache_task:
            self.cache_task.cancel()
            try:
                await self.cache_task
            except asyncio.CancelledError:
                pass

    async def cache_updater(self):
        while True:
            try:
                async with self.cache_lock:
                    self.global_dict_cache = await self.db.get_all_global_dictionary()
                    # サーバー辞書キャッシュは必要なものだけ都度取得するのでここでは空に
                    self.server_dict_cache.clear()
                    self.cache_last_update = time.time()
            except Exception as e:
                print(f"辞書キャッシュ更新エラー: {e}")
            await asyncio.sleep(10)

    async def get_server_dict(self, guild_id):
        async with self.cache_lock:
            if guild_id in self.server_dict_cache:
                return self.server_dict_cache[guild_id]
        # キャッシュになければ取得してキャッシュ
        rows = await self.db.get_all_dictionary(guild_id)
        async with self.cache_lock:
            self.server_dict_cache[guild_id] = rows
        return rows

    async def get_user_dict(self, user_id):
        async with self.cache_lock:
            if user_id in self.user_dict_cache:
                return self.user_dict_cache[user_id]
        # キャッシュになければ取得してキャッシュ
        rows = await self.db.get_all_user_dictionary(user_id)
        async with self.cache_lock:
            self.user_dict_cache[user_id] = rows
        return rows

    async def is_banned(self, user_id: int) -> bool:
        """ユーザーがBANされているか確認"""
        if self.voice_cog:
            return await self.voice_cog.is_banned(user_id)
        return False

    # 辞書コマンドグループ
    dictionary_group = app_commands.Group(name="dictionary", description="読み上げ辞書の管理")

    @dictionary_group.command(name="add", description="読み上げ辞書を設定 (サーバーまたはユーザー)")
    @app_commands.describe(user_dict="ユーザー辞書を使用するかどうか")
    async def dictionary_add(self, interaction: discord.Interaction, key: str, value: str, user_dict: bool = False):
        if await self.is_banned(interaction.user.id):
            await interaction.response.send_message("あなたはbotからBANされています。", ephemeral=True)
            return
        try:
            if user_dict:
                await self.db.upsert_user_dictionary(interaction.user.id, key, value)
                # キャッシュを即時反映
                async with self.cache_lock:
                    self.user_dict_cache.pop(interaction.user.id, None)
                embed = discord.Embed(
                    title="ユーザー辞書更新",
                    description=f"ユーザー辞書に追加しました: **{key}** -> **{value}**",
                    color=discord.Color.green()
                )
            else:
                author_id = interaction.user.id  # 登録者のユーザーIDを取得
                guild_id = interaction.guild.id
                await self.db.upsert_dictionary(guild_id, key, value, author_id)
                # キャッシュを即時反映
                async with self.cache_lock:
                    self.server_dict_cache.pop(guild_id, None)
                embed = discord.Embed(
                    title="辞書更新",
                    description=f"辞書に追加しました: **{key}** -> **{value}**",
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

    @dictionary_group.command(name="remove", description="読み上げ辞書を削除 (サーバーまたはユーザー)")
    @app_commands.describe(user_dict="ユーザー辞書を使用するかどうか")
    async def dictionary_remove(self, interaction: discord.Interaction, key: str, user_dict: bool = False):
        if await self.is_banned(interaction.user.id):
            await interaction.response.send_message("あなたはbotからBANされています。", ephemeral=True)
            return
        try:
            if user_dict:
                result = await self.db.remove_user_dictionary(interaction.user.id, key)
                # キャッシュを即時反映
                async with self.cache_lock:
                    self.user_dict_cache.pop(interaction.user.id, None)
                title = "ユーザー辞書削除"
            else:
                guild_id = interaction.guild.id
                result = await self.db.remove_dictionary(guild_id, key)
                # キャッシュを即時反映
                async with self.cache_lock:
                    self.server_dict_cache.pop(guild_id, None)
                title = "辞書削除"
            if result == "DELETE 1":
                embed = discord.Embed(
                    title=title,
                    description=f"辞書から削除しました: **{key}**",
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

    @dictionary_group.command(name="search", description="読み上げ辞書を検索 (サーバーまたはユーザー)")
    @app_commands.describe(user_dict="ユーザー辞書を使用するかどうか")
    async def dictionary_search(self, interaction: discord.Interaction, key: str, user_dict: bool = False):
        if await self.is_banned(interaction.user.id):
            await interaction.response.send_message("あなたはbotからBANされています。", ephemeral=True)
            return
        try:
            if user_dict:
                row = await self.db.get_user_dictionary_entry(interaction.user.id, key)
                title = "ユーザー辞書検索結果"
            else:
                guild_id = interaction.guild.id
                row = await self.db.get_dictionary_entry(guild_id, key)
                title = "辞書検索結果"
            if row:
                description = f"**{key}** -> **{row['value']}**"
                embed = discord.Embed(
                    title=title,
                    description=description,
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

    @dictionary_group.command(name="list", description="読み上げ辞書一覧を表示 (サーバーまたはユーザー)")
    @app_commands.describe(user_dict="ユーザー辞書を使用するかどうか")
    async def dictionary_list(self, interaction: discord.Interaction, user_dict: bool = False):
        if await self.is_banned(interaction.user.id):
            await interaction.response.send_message("あなたはbotからBANされています。", ephemeral=True)
            return
        try:
            if user_dict:
                rows = await self.get_user_dict(interaction.user.id)
                title = "📖 ユーザー辞書一覧"
                empty_description = "あなたのユーザー辞書にはまだ辞書が登録されていません。\n`/dictionary add user_dict:True` コマンドで新しい単語を追加できます！"
            else:
                guild_id = interaction.guild.id
                rows = await self.get_server_dict(guild_id)
                title = "📖 サーバー辞書一覧"
                empty_description = "このサーバーにはまだ辞書が登録されていません。\n`/dictionary add` コマンドで新しい単語を追加できます！"
            if not rows:
                embed = discord.Embed(
                    title=title,
                    description=empty_description,
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # ページネーション設定
            PAGE_SIZE = 20
            pages = [rows[i:i+PAGE_SIZE] for i in range(0, len(rows), PAGE_SIZE)]

            def make_embed(page_idx):
                embed = discord.Embed(
                    title=title,
                    description=f"ページ {page_idx+1}/{len(pages)}\n",
                    color=discord.Color.green()
                )
                for i, row in enumerate(pages[page_idx], start=1 + page_idx * PAGE_SIZE):
                    embed.add_field(
                        name=f"{i}. `{row['key']}` → `{row['value']}`",
                        value="",
                        inline=False
                    )
                return embed

            class PaginationView(View):
                def __init__(self):
                    super().__init__(timeout=120)
                    self.page = 0
                    self.prev_button = Button(label="◀ 前へ", style=discord.ButtonStyle.secondary)
                    self.next_button = Button(label="次へ ▶", style=discord.ButtonStyle.secondary)
                    self.prev_button.callback = self.prev
                    self.next_button.callback = self.next
                    self.add_item(self.prev_button)
                    self.add_item(self.next_button)

                async def update(self, interaction):
                    embed = make_embed(self.page)
                    await interaction.response.edit_message(embed=embed, view=self)

                async def prev(self, interaction: discord.Interaction):
                    if self.page > 0:
                        self.page -= 1
                        await self.update(interaction)
                    else:
                        await interaction.response.defer()

                async def next(self, interaction: discord.Interaction):
                    if self.page < len(pages) - 1:
                        self.page += 1
                        await self.update(interaction)
                    else:
                        await interaction.response.defer()

            view = PaginationView() if len(pages) > 1 else None
            if view:
                await interaction.response.send_message(embed=make_embed(0), view=view, ephemeral=True)
            else:
                await interaction.response.send_message(embed=make_embed(0), ephemeral=True)
        except Exception as e:
            print(e)  # ここでエラー内容を出力
            embed = discord.Embed(
                title="エラー",
                description="エラーが発生しました。詳細は管理者にお問い合わせください。",
                color=discord.Color.red()
            )
            # どちらでも送信できるように両方例外処理
            try:
                if interaction.response.is_done():
                    await interaction.edit_original_response(embed=embed, view=None)
                else:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception as inner_e:
                print(inner_e)

    async def apply_dictionary(self, text: str, guild_id: int = None) -> str:
        """辞書を適用してテキストを変換（サーバーごと対応 & グローバル辞書対応）"""
        if not self.cache_task or self.cache_task.done():
            self.cache_task = self.bot.loop.create_task(self.cache_updater())
        msg = discord.utils.get(self.bot.cached_messages, content=text)
        if msg:
            for user_id in {m.id for m in msg.mentions}:
                user = await self.bot.fetch_user(user_id)
                if user:
                    text = text.replace(f"<@{user_id}>", f"あっと{user.display_name}")
                    text = text.replace(f"<@!{user_id}>", f"あっと{user.display_name}")
        for role in msg.role_mentions if msg else []:
            text = text.replace(f"<@&{role.id}>", f"ろーる:{role.name}")
        text = re.sub(r'<a?:([a-zA-Z0-9_]+):\d+>', lambda m: f"えもじ:{m.group(1)}", text)
        text = re.sub(r'<a?:([a-zA-Z0-9_]+):\d+>', lambda m: f"すたんぷ:{m.group(1)}", text)
        text = re.sub(r'https?://\S+', 'リンク省略', text)
        # guild_idが指定されていなければ、メッセージから取得
        if guild_id is None and msg and msg.guild:
            guild_id = msg.guild.id
        # グローバル辞書をキャッシュから適用
        async with self.cache_lock:
            global_rows = list(self.global_dict_cache)
        for row in global_rows:
            text = text.replace(row['key'], row['value'])
        # サーバーごとの辞書をキャッシュから適用
        if guild_id is not None:
            rows = await self.get_server_dict(guild_id)
            for row in rows:
                text = text.replace(row['key'], row['value'])
        # ユーザー辞書適用
        user_id = msg.author.id if msg else None
        if user_id is not None:
            user_rows = await self.get_user_dict(user_id)
            for row in user_rows:
                text = text.replace(row['key'], row['value'])
        if len(text) > 70:
            text = text[:150] + "省略"
        return text

async def setup(bot):
    await bot.add_cog(DictionaryCog(bot))