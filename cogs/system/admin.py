import discord
from discord.ext import commands
from discord import app_commands
from lib.postgres import PostgresDB

ADMIN_ID = 1241397634095120438

class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot, db: PostgresDB):
        self.bot = bot
        self.db = db

    async def is_admin(self, interaction: discord.Interaction) -> bool:
        """管理者かどうかを確認"""
        return interaction.user.id == ADMIN_ID

    @app_commands.command(name="admin", description="管理者コマンド")
    @app_commands.describe(option="実行する操作", value="操作対象")
    async def admin_command(self, interaction: discord.Interaction, option: str, value: int):
        if not await self.is_admin(interaction):
            await interaction.response.send_message("このコマンドを実行する権限がありません。", ephemeral=True)
            return

        if option == "ban":
            await self.db.execute(
                "INSERT INTO banlist (user_id) VALUES ($1) ON CONFLICT DO NOTHING", value
            )
            # BANリストキャッシュを更新
            for cog in self.bot.cogs.values():
                if hasattr(cog, "banlist"):
                    cog.banlist.add(value)
            await interaction.response.send_message(f"ユーザーID {value} をBANしました。")
        elif option == "unban":
            await self.db.execute("DELETE FROM banlist WHERE user_id = $1", value)
            # BANリストキャッシュを更新
            for cog in self.bot.cogs.values():
                if hasattr(cog, "banlist"):
                    cog.banlist.discard(value)
            await interaction.response.send_message(f"ユーザーID {value} のBANを解除しました。")
        else:
            await interaction.response.send_message("無効なオプションです。'ban' または 'unban' を指定してください。", ephemeral=True)

async def setup(bot: commands.Bot):
    db = PostgresDB()
    await db.initialize()
    await bot.add_cog(AdminCog(bot, db))
