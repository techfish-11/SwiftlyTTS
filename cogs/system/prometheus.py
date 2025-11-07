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
        # シャードごとのメトリクス
        self.shard_latency_metric = Gauge('bot_shard_latency_ms', 'シャードごとのレイテンシ（ms）', ['shard_id'])
        self.shard_server_count_metric = Gauge('bot_shard_server_count', 'シャードごとのサーバー数', ['shard_id'])
        self.shard_vc_count_metric = Gauge('bot_shard_vc_count', 'シャードごとのVC接続数', ['shard_id'])
        self.shard_tts_count_per_minute = Gauge('bot_shard_tts_count_per_minute', 'シャードごとの1分間TTS回数', ['shard_id'])
        self.shard_error_count_per_minute = Gauge('bot_shard_error_count_per_minute', 'シャードごとの1分間エラー回数', ['shard_id'])
        # シャードごとのカウンターをボットに追加
        self.bot.shard_tts_counters = defaultdict(int)
        self.bot.shard_error_counters = defaultdict(int)
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
        # シャードごとのメトリクス
        for shard_id, shard in self.bot.shards.items():
            self.shard_latency_metric.labels(shard_id=shard_id).set(shard.latency * 1000 if shard.latency else 0)
            shard_servers = [g for g in self.bot.guilds if g.shard_id == shard_id]
            self.shard_server_count_metric.labels(shard_id=shard_id).set(len(shard_servers))
            shard_vcs = [vc for vc in self.bot.voice_clients if vc.guild and vc.guild.shard_id == shard_id]
            self.shard_vc_count_metric.labels(shard_id=shard_id).set(len(shard_vcs))
            self.shard_tts_count_per_minute.labels(shard_id=shard_id).set(self.bot.shard_tts_counters.get(shard_id, 0))
            self.shard_error_count_per_minute.labels(shard_id=shard_id).set(self.bot.shard_error_counters.get(shard_id, 0))
        # カウンターをリセット
        self.bot.tts_counter = 0
        self.bot.error_counter = 0
        self.bot.shard_tts_counters.clear()
        self.bot.shard_error_counters.clear()

    @update_metrics.before_loop
    async def before_update_metrics(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(PrometheusCog(bot))