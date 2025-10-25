import discord
from discord.ext import commands, tasks
from prometheus_client import Gauge, start_http_server
from collections import defaultdict

class PrometheusCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vc_count_metric = Gauge('bot_voice_channel_count', '現在botが接続しているVC数')
        self.server_count_metric = Gauge('bot_server_count', 'botが参加しているサーバー数')
        self.latency_metric = Gauge('bot_latency_ms', 'botのレイテンシ（ms）') 
        self.tts_count_per_minute = Gauge('bot_tts_count_per_minute', '1分間に読み上げた回数')
        self.error_count_per_minute = Gauge('bot_error_count_per_minute', '1分間に起きたエラー数')
        self.command_counters = defaultdict(int)
        self.command_gauges = {}
        self.update_metrics.start()
        start_http_server(47724)

    def cog_unload(self):
        self.update_metrics.cancel()

    @commands.Cog.listener()
    async def on_application_command(self, ctx):
        cmd_name = ctx.command.name if hasattr(ctx, "command") else "unknown"
        self.command_counters[cmd_name] += 1

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
        # 各コマンドの1分間使用回数をPrometheus Gaugeにセット
        for cmd_name, count in self.command_counters.items():
            if cmd_name not in self.command_gauges:
                self.command_gauges[cmd_name] = Gauge(
                    f'bot_command_{cmd_name}_count_per_minute',
                    f'1分間に使用されたコマンド {cmd_name} の回数'
                )
            self.command_gauges[cmd_name].set(count)
        self.command_counters.clear()
        # カウンターをリセット
        self.bot.tts_counter = 0
        self.bot.error_counter = 0

    @update_metrics.before_loop
    async def before_update_metrics(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(PrometheusCog(bot))