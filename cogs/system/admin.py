import discord
from discord.ext import commands
from discord import app_commands
from lib.postgres import PostgresDB
from lib.VOICEVOXlib import VOICEVOXLib  # 追加: VOICEVOXLib をインポート
import os
from dotenv import load_dotenv
import time
import wave
import io

class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot, db: PostgresDB, voicelib: VOICEVOXLib):  # 変更: voicelib を追加
        self.bot = bot
        self.db = db
        self.voicelib = voicelib  # 追加: voicelib を保存

    def get_admin_id(self) -> int:
        load_dotenv()  # .envを毎回読み込む
        admin_id = os.getenv("ADMIN_ID")
        if admin_id is None:
            raise ValueError("ADMIN_ID is not set in .env")
        return int(admin_id)

    async def is_admin(self, interaction: discord.Interaction) -> bool:
        """管理者かどうかを確認"""
        return interaction.user.id == self.get_admin_id()

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

        elif option == "warn":
            parts = value.split(":", 1)
            if len(parts) != 2:
                await interaction.response.send_message("正しい形式は <userid>:<warn内容> です。", ephemeral=True)
                return
            try:
                user_id = int(parts[0])
            except ValueError:
                await interaction.response.send_message("ユーザーIDは整数で指定してください。", ephemeral=True)
                return
            warn_message = parts[1].strip()
            try:
                user = await self.bot.fetch_user(user_id)
                await user.send(f"警告: {warn_message}")
            except discord.Forbidden:
                await interaction.response.send_message("ユーザーにDMを送信できませんでした。", ephemeral=True)
                return
            except Exception:
                await interaction.response.send_message("警告メッセージの送信中にエラーが発生しました。", ephemeral=True)
                return
            await interaction.response.send_message(f"ユーザーID {user_id} に警告を送信しました。", ephemeral=True)

        elif option == "bench":
            # テキストをVOICEVOXで合成し、時間を計測
            text = value.strip()
            if not text:
                await interaction.response.send_message("テキストを指定してください。", ephemeral=True)
                return

            await interaction.response.defer(ephemeral=True)  # 追加: 考え中を表示

            speaker_id = 1
            speed = 1.0

            start_time = time.perf_counter()
            try:
                used_url, wav_bytes = await self.voicelib.synthesize_bytes(text, speaker_id)
                elapsed = time.perf_counter() - start_time

                # 音声長さを計算
                with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
                    n_frames = wav_file.getnframes()
                    framerate = wav_file.getframerate()
                    duration_sec = n_frames / framerate if framerate else 0.0

                # embed で結果を表示
                embed = discord.Embed(
                    title="VOICEVOX ベンチマーク結果",
                    color=discord.Color.green()
                )
                embed.add_field(name="テキスト", value=text, inline=False)
                embed.add_field(name="処理時間 (秒)", value=f"{elapsed:.2f}", inline=True)
                embed.add_field(name="音声長さ (秒)", value=f"{duration_sec:.2f}", inline=True)
                embed.add_field(name="使用 VOICEVOX サーバー URL", value=used_url, inline=False)
                embed.add_field(name="Speaker ID", value=str(speaker_id), inline=True)
                embed.add_field(name="Speed", value=str(speed), inline=True)
                await interaction.followup.send(embed=embed, ephemeral=True)  # 変更: followup で送信

            except Exception as e:
                await interaction.followup.send(f"ベンチマーク中にエラーが発生しました: {str(e)}", ephemeral=True)  # 変更: followup で送信

        else:
            await interaction.response.send_message(
                "無効なオプションです。'ban', 'unban', 'voice', 'warn' または 'bench' を指定してください。", ephemeral=True
            )

async def setup(bot: commands.Bot):
    db = PostgresDB()
    await db.initialize()
    voicelib = VOICEVOXLib()  # 追加: VOICEVOXLib を初期化
    await bot.add_cog(AdminCog(bot, db, voicelib))  # 変更: voicelib を渡す