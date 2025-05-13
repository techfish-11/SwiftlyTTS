import discord
from discord.ext import commands, tasks
from prometheus_client import Gauge, start_http_server

class PrometheusCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vc_count_metric = Gauge('bot_voice_channel_count', '現在botが接続しているVC数')
        self.server_count_metric = Gauge('bot_server_count', 'botが参加しているサーバー数')
        self.update_metrics.start()
        start_http_server(47724)

    def cog_unload(self):
        self.update_metrics.cancel()

    @tasks.loop(seconds=10)
    async def update_metrics(self):
        vc_count = len(self.bot.voice_clients)
        server_count = len(self.bot.guilds)
        self.vc_count_metric.set(vc_count)
        self.server_count_metric.set(server_count)

    @update_metrics.before_loop
    async def before_update_metrics(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(PrometheusCog(bot))
