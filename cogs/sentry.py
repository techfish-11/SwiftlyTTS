import discord
from discord.ext import commands
import sentry_sdk
import os
import sys
import asyncio

class SentryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        dsn = os.getenv("SENTRY_DSN")
        if dsn:
            sentry_sdk.init(
                dsn=dsn,
                traces_sample_rate=1.0,
                environment=os.getenv("SENTRY_ENV", "production"),
            )
            # sys.excepthookでグローバル例外をキャッチ
            sys.excepthook = self.handle_exception
            # asyncioの例外もキャッチ
            loop = asyncio.get_event_loop()
            loop.set_exception_handler(self.asyncio_exception_handler)
            # Python 3.8+ unraisablehook
            if hasattr(sys, "unraisablehook"):
                sys.unraisablehook = self.unraisable_exception_handler

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        # KeyboardInterruptは無視
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        sentry_sdk.capture_exception(exc_value)
        self.bot.error_counter += 1  # エラーカウンターをインクリメント

    def asyncio_exception_handler(self, loop, context):
        exception = context.get("exception")
        if exception:
            sentry_sdk.capture_exception(exception)
        else:
            sentry_sdk.capture_message(str(context))
        self.bot.error_counter += 1  # エラーカウンターをインクリメント

    def unraisable_exception_handler(self, unraisable):
        exc = unraisable.exc_value if hasattr(unraisable, "exc_value") else None
        if exc:
            sentry_sdk.capture_exception(exc)
        else:
            sentry_sdk.capture_message(str(unraisable))
        self.bot.error_counter += 1  # エラーカウンターをインクリメント

    @commands.Cog.listener()
    async def on_ready(self):
        # 起動時にINFOを送信
        sentry_sdk.capture_message("Bot started", level="info")

    @commands.Cog.listener()
    async def on_error(self, event_method, *args, **kwargs):
        # discord.pyのグローバルエラー
        sentry_sdk.capture_exception()
        self.bot.error_counter += 1  # エラーカウンターをインクリメント
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # コマンドエラー
        sentry_sdk.capture_exception(error)
        self.bot.error_counter += 1  # エラーカウンターをインクリメント

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction, error):
        # アプリケーションコマンドのエラー
        sentry_sdk.capture_exception(error)
        self.bot.error_counter += 1  # エラーカウンターをインクリメント

async def setup(bot):
    await bot.add_cog(SentryCog(bot))
