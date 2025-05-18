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
    async def admin_command(self, interaction: discord.Interaction, option: str, value: str):
        if not await self.is_admin(interaction):
            await interaction.response.send_message("このコマンドを実行する権限がありません。", ephemeral=True)
            return

        try:
            value_int = int(value)
        except ValueError:
            pass

        if option == "ban":
            await self.db.execute(
                "INSERT INTO banlist (user_id) VALUES ($1) ON CONFLICT DO NOTHING", value_int
            )
            for cog in self.bot.cogs.values():
                if hasattr(cog, "banlist"):
                    cog.banlist.add(value_int)
            await interaction.response.send_message(f"ユーザーID {value_int} をBANしました。", ephemeral=True)

        elif option == "unban":
            await self.db.execute("DELETE FROM banlist WHERE user_id = $1", value_int)
            for cog in self.bot.cogs.values():
                if hasattr(cog, "banlist"):
                    cog.banlist.discard(value_int)
            await interaction.response.send_message(f"ユーザーID {value_int} のBANを解除しました。", ephemeral=True)

        elif option == "voice":
            # ページ番号をパース
            try:
                page = int(value)
            except ValueError:
                await interaction.response.send_message("ページ番号は整数で指定してください。", ephemeral=True)
                return

            # 接続中の VC をリストアップ
            items = [
                f"{vc.channel.name} - {vc.guild.name} ({vc.guild.id})"
                for vc in self.bot.voice_clients
            ]
            if not items:
                await interaction.response.send_message("現在接続中のVCはありません。", ephemeral=True)
                return

            # ページネーション
            page_size = 10
            max_page = (len(items) + page_size - 1) // page_size
            if page < 1 or page > max_page:
                await interaction.response.send_message(f"ページ番号は 1～{max_page} の範囲で指定してください。", ephemeral=True)
                return

            start = (page - 1) * page_size
            end = start + page_size
            page_items = items[start:end]

            embed = discord.Embed(
                title=f"接続中 VC 一覧 (ページ {page}/{max_page})",
                color=discord.Color.blue()
            )
            embed.description = "\n".join(
                f"{i+1}. {item}"
                for i, item in enumerate(page_items, start)
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        else:
            await interaction.response.send_message(
                "無効なオプションです。'ban', 'unban', または 'voice' を指定してください。", ephemeral=True
            )

async def setup(bot: commands.Bot):
    db = PostgresDB()
    await db.initialize()
    await bot.add_cog(AdminCog(bot, db))
