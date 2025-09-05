import discord
from discord.ext import commands
from discord import app_commands
from lib.postgres import PostgresDB  # PostgresDBをインポート
import re
from discord.ui import View, Button

class DictionaryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = PostgresDB()  # データベースインスタンスを初期化
        self.voice_cog = None  # VoiceReadCogの参照

    async def cog_load(self):
        await self.db.initialize()  # データベース接続を初期化
        self.voice_cog = self.bot.get_cog("VoiceReadCog")  # VoiceReadCogを取得

    async def cog_unload(self):
        await self.db.close()  # データベース接続を閉じる

    async def is_banned(self, user_id: int) -> bool:
        """ユーザーがBANされているか確認"""
        if self.voice_cog:
            return await self.voice_cog.is_banned(user_id)
        return False

    @app_commands.command(name="dictionary", description="読み上げ辞書を設定")
    async def dictionary(self, interaction: discord.Interaction, key: str, value: str):
        if await self.is_banned(interaction.user.id):
            await interaction.response.send_message("あなたはbotからBANされています。", ephemeral=True)
            return
        try:
            author_id = interaction.user.id  # 登録者のユーザーIDを取得
            guild_id = interaction.guild.id
            await self.db.upsert_dictionary(guild_id, key, value, author_id)
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

    @app_commands.command(name="dictionary-remove", description="読み上げ辞書を削除")
    async def dictionary_remove(self, interaction: discord.Interaction, key: str):
        if await self.is_banned(interaction.user.id):
            await interaction.response.send_message("あなたはbotからBANされています。", ephemeral=True)
            return
        try:
            guild_id = interaction.guild.id
            result = await self.db.remove_dictionary(guild_id, key)
            if result == "DELETE 1":
                embed = discord.Embed(
                    title="辞書削除",
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

    @app_commands.command(name="dictionary-search", description="読み上げ辞書を検索")
    async def dictionary_search(self, interaction: discord.Interaction, key: str):
        if await self.is_banned(interaction.user.id):
            await interaction.response.send_message("あなたはbotからBANされています。", ephemeral=True)
            return
        try:
            guild_id = interaction.guild.id
            row = await self.db.get_dictionary_entry(guild_id, key)
            if row:
                author_id = row['author_id']
                if interaction.user.id == 1241397634095120438:
                    description = f"**{key}** -> **{row['value']}**\n登録者: <@{author_id}>"
                else:
                    description = f"**{key}** -> **{row['value']}**"
                embed = discord.Embed(
                    title="辞書検索結果",
                    description=f"{description}",
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

    @app_commands.command(name="dictionary-list", description="サーバーの読み上げ辞書一覧を表示")
    async def dictionary_list(self, interaction: discord.Interaction):
        if await self.is_banned(interaction.user.id):
            await interaction.response.send_message("あなたはbotからBANされています。", ephemeral=True)
            return
        try:
            guild_id = interaction.guild.id
            rows = await self.db.get_all_dictionary(guild_id)
            if not rows:
                embed = discord.Embed(
                    title="辞書一覧",
                    description="このサーバーには辞書が登録されていません。",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # ページネーション設定
            PAGE_SIZE = 20
            pages = [rows[i:i+PAGE_SIZE] for i in range(0, len(rows), PAGE_SIZE)]

            def make_embed(page_idx):
                embed = discord.Embed(
                    title=f"辞書一覧 (ページ {page_idx+1}/{len(pages)})",
                    color=discord.Color.green()
                )
                for row in pages[page_idx]:
                    embed.add_field(
                        name=row['key'],
                        value=row['value'],
                        inline=False
                    )
                return embed

            class PaginationView(View):
                def __init__(self):
                    super().__init__(timeout=120)
                    self.page = 0

                async def update(self, interaction):
                    embed = make_embed(self.page)
                    await interaction.response.edit_message(embed=embed, view=self)

                @Button(label="前へ", style=discord.ButtonStyle.secondary)
                async def prev(self, interaction: discord.Interaction, button: Button):
                    if self.page > 0:
                        self.page -= 1
                        await self.update(interaction)
                    else:
                        await interaction.response.defer()

                @Button(label="次へ", style=discord.ButtonStyle.secondary)
                async def next(self, interaction: discord.Interaction, button: Button):
                    if self.page < len(pages) - 1:
                        self.page += 1
                        await self.update(interaction)
                    else:
                        await interaction.response.defer()

            view = PaginationView() if len(pages) > 1 else None
            await interaction.response.send_message(embed=make_embed(0), view=view, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                title="エラー",
                description="エラーが発生しました。詳細は管理者にお問い合わせください。",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def apply_dictionary(self, text: str, guild_id: int = None) -> str:
        """辞書を適用してテキストを変換（サーバーごと対応）"""
        msg = discord.utils.get(self.bot.cached_messages, content=text)
        if msg:
            for user_id in {m.id for m in msg.mentions}:
                user = await self.bot.fetch_user(user_id)
                if user:
                    text = text.replace(f"<@{user_id}>", f"あっと{user.display_name}")
                    text = text.replace(f"<@!{user_id}>", f"あっと{user.display_name}")
        for role in msg.role_mentions:
            text = text.replace(f"<@&{role.id}>", f"ろーる:{role.name}")
        text = re.sub(r'<a?:([a-zA-Z0-9_]+):\d+>', lambda m: f"えもじ:{m.group(1)}", text)
        text = re.sub(r'<a?:([a-zA-Z0-9_]+):\d+>', lambda m: f"すたんぷ:{m.group(1)}", text)
        text = re.sub(r'https?://\S+', 'リンク省略', text)
        # guild_idが指定されていなければ、メッセージから取得
        if guild_id is None and msg and msg.guild:
            guild_id = msg.guild.id
        # サーバーごとの辞書のみ適用
        if guild_id is not None:
            rows = await self.db.get_all_dictionary(guild_id)
            for row in rows:
                text = text.replace(row['key'], row['value'])
        if len(text) > 70:
            text = text[:70] + "省略"
        return text

async def setup(bot):
    await bot.add_cog(DictionaryCog(bot))