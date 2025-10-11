import discord
from discord.ext import commands, tasks
from prometheus_client import Gauge, start_http_server

class PrometheusCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vc_count_metric = Gauge('bot_voice_channel_count', '現在botが接続しているVC数')
        self.server_count_metric = Gauge('bot_server_count', 'botが参加しているサーバー数')
        self.latency_metric = Gauge('bot_latency_ms', 'botのレイテンシ（ms）') 
        self.tts_count_per_minute = Gauge('bot_tts_count_per_minute', '1分間に読み上げた回数')
        self.error_count_per_minute = Gauge('bot_error_count_per_minute', '1分間に起きたエラー数')
        self.update_metrics.start()
        start_http_server(47724)

    def cog_unload(self):
        self.update_metrics.cancel()

    @tasks.loop(minutes=1)
    async def update_metrics(self):
        vc_count = len(self.bot.voice_clients) if self.bot.voice_clients else 0
        server_count = len(self.bot.guilds)
        latency_ms = self.bot.latency * 1000 if self.bot.latency is not None else 0 
        self.vc_count_metric.set(vc_count)
        self.server_count_metric.set(server_count)
        self.latency_metric.set(latency_ms)
        self.tts_count_per_minute.set(self.bot.tts_counter)
        self.error_count_per_minute.set(self.bot.error_counter)
        # カウンターをリセット
        self.bot.tts_counter = 0
        self.bot.error_counter = 0

    @update_metrics.before_loop
    async def before_update_metrics(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(PrometheusCog(bot))