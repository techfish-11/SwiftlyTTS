import discord
from discord.errors import ConnectionClosed
from discord.ext import commands
import asyncio
import os
import subprocess
from lib.VOICEVOXlib import VOICEVOXLib
from discord import app_commands
from lib.postgres import PostgresDB  # PostgresDBをインポート
from lib.rust_lib_client import RustQueueClient
import uuid
from dotenv import load_dotenv  # dotenvをインポート
import traceback
import logging

# 話者名とIDの紐付けリスト
SPEAKER_LIST = [
    {"name": "四国めたん", "id": 2},
    {"name": "ずんだもん", "id": 3},
    {"name": "春日部つむぎ", "id": 8},
    {"name": "雨晴はう", "id": 10},
    {"name": "波音リツ", "id": 9},
    {"name": "玄野武宏", "id": 11},
    {"name": "白上虎太郎", "id": 12},
    {"name": "青山龍星", "id": 13},
    {"name": "冥鳴ひまり", "id": 14},
    {"name": "九州そら", "id": 16},
    {"name": "もち子さん", "id": 20},
    {"name": "剣崎雌雄", "id": 21},
    {"name": "WhiteCUL", "id": 23},
    {"name": "後鬼", "id": 27},
    {"name": "No.7", "id": 29},
    {"name": "ちび式じい", "id": 42},
    {"name": "櫻歌ミコ", "id": 43},
    {"name": "小夜/SAYO", "id": 46},
    {"name": "ナースロボ＿タイプＴ", "id": 47},
    {"name": "†聖騎士 紅桜†", "id": 51},
    {"name": "雀松朱司", "id": 52},
    {"name": "麒ヶ島宗麟", "id": 53},
    {"name": "春歌ナナ", "id": 54},
    {"name": "猫使アル", "id": 55},
    {"name": "猫使ビィ", "id": 58},
    {"name": "中国うさぎ", "id": 61},
    {"name": "栗田まろん", "id": 67},
    {"name": "あいえるたん", "id": 68},
    {"name": "満別花丸", "id": 69},
    {"name": "琴詠ニア", "id": 74},
    {"name": "Voidoll", "id": 89},
    {"name": "ぞん子", "id": 90},
    {"name": "中部つるぎ", "id": 94}
]

class VoiceReadCog(commands.Cog):
    autojoin = app_commands.Group(name="autojoin", description="自動参加設定")
    def __init__(self, bot):
        self.bot = bot
        self.voicelib = VOICEVOXLib()
        self.speaker_id = 1
        self.tts_channels = {}      # {guild.id: channel.id}
        self.queue_tasks = {}       # {guild.id: Task}
        self.rust_queue = RustQueueClient()
        self.db = PostgresDB()  # データベースインスタンスを初期化
        self.cleanup_task = None  # 定期的なクリーンアップタスク
        # 新規: ギルド単位の接続ロック
        self.connect_locks = {}  # {guild.id: asyncio.Lock()}
        # self.monitor_task = None  # VC状態監視タスク ← 削除
        load_dotenv()  # .envファイルを読み込む
        self.debug_mode = os.getenv("DEBUG", "0") == "1"  # DEBUGモード判定
        self.reconnect_enabled = os.getenv("RECONNECT", "true").lower() != "false"  # reconnect設定を取得
        self.task_restart_interval = 1800  # タスク再作成間隔（秒）
        self.voice_connect_timeout = int(os.getenv("VOICE_CONNECT_TIMEOUT", "60"))  # 接続タイムアウト（秒）
        self.sync_vcstate_task = None  # ← 追加: VC状態同期タスク
        # ギルドごとの autojoin 設定キャッシュ: {guild.id: (vc_channel_id, tts_channel_id)}
        self.autojoin_configs = {}
        self.logger = logging.getLogger(__name__)

        def handle_global_exception(loop, context):
            self.logger.error("=== Unhandled exception in event loop ===")
            msg = context.get("exception", context.get("message"))
            self.logger.error(f"Exception: {msg}")
            traceback.print_exc()
            if "future" in context:
                fut = context["future"]
                if hasattr(fut, "print_stack"):
                    fut.print_stack()
        self.bot.loop.set_exception_handler(handle_global_exception)

    async def cog_load(self):
        await self.db.initialize()  # データベース接続を初期化
        self.cleanup_task = self.bot.loop.create_task(self.cleanup_temp_files())
        self.banlist = set(await self.db.fetch_column("SELECT user_id FROM banlist"))  # BANリストをキャッシュ

        # autojoin 設定をロード（DEBUGモードでもロードする）
        try:
            rows = await self.db.fetch("SELECT guild_id, vc_channel_id, tts_channel_id FROM autojoin_config")
            for r in rows:
                self.autojoin_configs[r['guild_id']] = (r['vc_channel_id'], r['tts_channel_id'])
            self.logger.info(f"Loaded autojoin configs for {len(self.autojoin_configs)} guild(s)")
        except Exception:
            self.logger.exception("Failed to load autojoin configs")

        if self.debug_mode:
            self.logger.info("DEBUGモードのためVC状態復元をスキップします。")
            return

        if not self.reconnect_enabled:
            self.logger.info("Reconnect is disabled. Skipping VC state restoration.")
            return  # 再接続が無効の場合はスキップ

        # VC接続状態を復元
        vc_states = await self.db.fetch("SELECT guild_id, channel_id, tts_channel_id FROM vc_state")
        for state in vc_states:
            guild = self.bot.get_guild(state['guild_id'])
            if guild is None:
                continue
            vc_channel = guild.get_channel(state['channel_id']) if guild else None
            tts_channel = guild.get_channel(state['tts_channel_id']) if guild else None
            if guild and vc_channel and tts_channel:
                # チャンネルに人がいない場合はスキップ
                if not vc_channel.members or all(member.bot for member in vc_channel.members):
                    self.logger.info(f"Skipping reconnection to empty VC in guild {guild.id}")
                    continue
                try:
                    # 変更: 汎用接続ヘルパーを利用
                    voice_client = await self._connect_voice(vc_channel)
                    if voice_client is None:
                        self.logger.warning(f"Failed to reconnect to VC in guild {guild.id}: helper returned None")
                        continue
                    await guild.change_voice_state(channel=vc_channel, self_mute=False, self_deaf=True)
                    self.tts_channels[guild.id] = tts_channel.id
                    self.message_queues[guild.id] = asyncio.Queue()
                    self.queue_tasks[guild.id] = self.bot.loop.create_task(self.process_queue(guild.id))
                except Exception as e:
                    self.logger.error(f"Failed to reconnect to VC in guild {guild.id}: {e}")
                    traceback.print_exc()

        # self.monitor_task = self.bot.loop.create_task(self.monitor_vc_state()) ← 削除
        self.sync_vcstate_task = self.bot.loop.create_task(self.sync_vcstate_periodically())  # ← 追加

    async def cog_unload(self):
        await self.db.close()  # データベース接続を閉じる
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                self.logger.error(f"Error while cancelling cleanup_task: {e}")
                traceback.print_exc()
        # if self.monitor_task:
        #     self.monitor_task.cancel()
        #     try:
        #         await self.monitor_task
        #     except asyncio.CancelledError:
        #         pass
        if self.sync_vcstate_task:
            self.sync_vcstate_task.cancel()
            try:
                await self.sync_vcstate_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                self.logger.error(f"Error while cancelling sync_vcstate_task: {e}")
                traceback.print_exc()

    async def is_banned(self, user_id: int) -> bool:
        """ユーザーがBANされているか確認"""
        return user_id in self.banlist

    @app_commands.command(name="join", description="ボイスチャンネルに参加")
    async def join(self, interaction: discord.Interaction):
        if await self.is_banned(interaction.user.id):
            await interaction.response.send_message("このコマンドを実行する権限がありません。", ephemeral=True)
            return
        if interaction.user.voice:
            # 処理に時間がかかる可能性があるため Thinking を表示
            await interaction.response.defer(thinking=True)
            channel = interaction.user.voice.channel
            
            # 新規: 既に同じギルドで接続されている場合、既存の接続を切断しデータをクリア
            guild_id = interaction.guild.id
            if interaction.guild.voice_client:
                await interaction.guild.voice_client.disconnect()
                # 既存のキュー・タスク等をリセット
                if guild_id in self.queue_tasks:
                    self.queue_tasks[guild_id].cancel()
                    del self.queue_tasks[guild_id]
                self.tts_channels.pop(guild_id, None)
                # DBから既存のVC接続状態を削除
                await self.db.execute("DELETE FROM vc_state WHERE guild_id = $1", guild_id)
            
            try:
                # 変更: ヘルパーを使って接続、リトライとフォールバック対応
                voice_client = await self._connect_voice(channel)
                if voice_client is None:
                    await interaction.followup.send("ボイスチャンネルへの接続に失敗しました。時間を置いて再試行してください。", ephemeral=True)
                    return
            except asyncio.TimeoutError:
                await interaction.followup.send("ボイスチャンネルへの接続がタイムアウトしました。再試行してください。", ephemeral=True)
                return
            except ConnectionClosed:
                await interaction.followup.send("ボイスサーバーとの接続が切断されました。再試行してください。", ephemeral=True)
                return
            except Exception:
                await interaction.followup.send("ボイスチャンネルへの接続中にエラーが発生しました。", ephemeral=True)
                return

            # 接続成功後の処理
            self.tts_channels[guild_id] = interaction.channel.id
            self.queue_tasks[guild_id] = self.bot.loop.create_task(self.process_queue(guild_id))
            
            # データベースにVC接続状態を保存（DEBUGモード時はスキップ）
            if not self.debug_mode:
                await self.db.execute(
                    "INSERT INTO vc_state (guild_id, channel_id, tts_channel_id) VALUES ($1, $2, $3) ON CONFLICT (guild_id) DO UPDATE SET channel_id = $2, tts_channel_id = $3",
                    guild_id, channel.id, interaction.channel.id
                )

            # 「接続しました。」と喋る処理を非同期で実行
            async def play_connection_message():
                tmp_wav = f"tmp_{uuid.uuid4()}_join.wav"  # UUIDを使用（要求するファイル名だが実際の保存先はライブラリが返す）
                user_speaker_id = await self.get_user_speaker_id(interaction.user.id)
                try:
                    saved_path = await self.voicelib.synthesize("接続しました。", user_speaker_id, tmp_wav)
                except Exception:
                    # 合成失敗は黙って戻る
                    return
                voice_client = interaction.guild.voice_client
                if voice_client and not voice_client.is_playing():
                    audio_source = discord.FFmpegPCMAudio(saved_path)
                    voice_client.play(audio_source)
                    while voice_client.is_playing():
                        await asyncio.sleep(0.5)
                # 再生後はライブラリが保存したファイルを削除
                try:
                    if saved_path and os.path.exists(saved_path):
                        os.remove(saved_path)
                except Exception:
                    pass

            self.bot.loop.create_task(play_connection_message())

            # 高負荷時間帯判定・通知文生成
            from datetime import datetime, time as dtime
            import pytz
            jst = pytz.timezone("Asia/Tokyo")
            now = datetime.now(jst).time()
            extra_msg = ""
            high_load_time = getattr(self.bot, "config", {}).get("high_load_time")
            in_high_load = False
            if high_load_time:
                try:
                    start_str, end_str = high_load_time.split("-")
                    start_h, start_m = map(int, start_str.split(":"))
                    end_h, end_m = map(int, end_str.split(":"))
                    start = dtime(start_h, start_m)
                    end = dtime(end_h, end_m)
                    if start <= end:
                        in_high_load = start <= now < end
                    else:
                        in_high_load = now >= start or now < end
                    if in_high_load:
                        extra_msg = f"\n高負荷時間帯（{high_load_time}）につき一時的に声がずんだもんになります"
                except Exception:
                    pass
            embed = discord.Embed(
                title="接続完了",
                description=f"{channel.name}に接続しました。\n\nサポートサーバー: https://discord.gg/mNDvAYayp5{extra_msg}",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Hosted by sakana11.org")
            # defer しているので followup を使って送信
            await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(
                title="エラー",
                description="先にボイスチャンネルに参加してください。",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="leave", description="ボイスチャンネルから退出")
    async def leave(self, interaction: discord.Interaction):
        if await self.is_banned(interaction.user.id):
            await interaction.response.send_message("このコマンドを実行する権限がありません。", ephemeral=True)
            return
        if interaction.guild.voice_client:
            self.logger.info(f"[VC Disconnect] Reason: leave command by user in guild {interaction.guild.id}, channel {interaction.guild.voice_client.channel.id}")
            await interaction.guild.voice_client.disconnect()
            # キュー・タスク等をリセット
            if interaction.guild.id in self.queue_tasks:
                self.queue_tasks[interaction.guild.id].cancel()
                del self.queue_tasks[interaction.guild.id]
            self.tts_channels.pop(interaction.guild.id, None)
            # データベースからVC接続状態を削除
            await self.db.execute("DELETE FROM vc_state WHERE guild_id = $1", interaction.guild.id)
            embed = discord.Embed(
                title="退出完了",
                description="ボイスチャンネルから退出しました。\nご利用ありがとうございました",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(
                title="エラー",
                description="ボイスチャンネルに接続していません。",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @autojoin.command(name="on", description="自動参加を有効にします。設定したいVCに参加している必要があります。")
    async def autojoin_on(self, interaction: discord.Interaction):
        if await self.is_banned(interaction.user.id):
            await interaction.response.send_message("このコマンドを実行する権限がありません。", ephemeral=True)
            return
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("先にボイスチャンネルに参加してください。", ephemeral=True)
            return
        guild = interaction.guild
        vc_channel = interaction.user.voice.channel
        tts_channel_id = interaction.channel.id
        try:
            await self.db.set_autojoin(guild.id, vc_channel.id, tts_channel_id)
            self.autojoin_configs[guild.id] = (vc_channel.id, tts_channel_id)
        except Exception as e:
            self.logger.error(f"Failed to save autojoin config for guild {guild.id}: {e}")
            traceback.print_exc()
            await interaction.response.send_message("自動参加設定の保存中にエラーが発生しました。", ephemeral=True)
            return

        embed = discord.Embed(
            title="Autojoin: ON",
            description=(f"このサーバーは `{vc_channel.name}` にメンバーが参加したときに自動で参加するように設定されました。\n"
                         f"読み上げチャンネル: <#{tts_channel_id}>") ,
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

        # ユーザーが現在参加しているVCに今すぐ参加する
        try:
            voice_client = guild.voice_client
            if not voice_client or not getattr(voice_client, 'is_connected', lambda: False)():
                vc = await self._connect_voice(vc_channel)
                if vc:
                    # 接続後の初期化
                    self.tts_channels[guild.id] = tts_channel_id
                    self.queue_tasks[guild.id] = self.bot.loop.create_task(self.process_queue(guild.id))
                    # DBにVC接続状態を記録
                    await self.db.execute(
                        "INSERT INTO vc_state (guild_id, channel_id, tts_channel_id) VALUES ($1, $2, $3) ON CONFLICT (guild_id) DO UPDATE SET channel_id = $2, tts_channel_id = $3",
                        guild.id, vc_channel.id, tts_channel_id
                    )
                    # 通知
                    tts_channel = guild.get_channel(tts_channel_id)
                    if tts_channel:
                        try:
                            notify_embed = discord.Embed(
                                title="自動接続",
                                description=f"自動参加が有効になったため、Botが {vc_channel.name} に参加しました。",
                                color=discord.Color.green()
                            )
                            await tts_channel.send(embed=notify_embed)
                        except Exception:
                            self.logger.exception("Failed to send autojoin notification embed")
        except Exception as e:
            self.logger.error(f"Error while performing immediate autojoin for guild {guild.id}: {e}")
            traceback.print_exc()

    @autojoin.command(name="off", description="自動参加を無効にします。")
    async def autojoin_off(self, interaction: discord.Interaction):
        if await self.is_banned(interaction.user.id):
            await interaction.response.send_message("このコマンドを実行する権限がありません。", ephemeral=True)
            return
        try:
            await self.db.delete_autojoin(interaction.guild.id)
            self.autojoin_configs.pop(interaction.guild.id, None)
        except Exception as e:
            self.logger.error(f"Failed to remove autojoin config for guild {interaction.guild.id}: {e}")
            traceback.print_exc()
            await interaction.response.send_message("自動参加設定の削除中にエラーが発生しました。", ephemeral=True)
            return
        embed = discord.Embed(
            title="Autojoin: OFF",
            description="このサーバーの自動参加設定を無効にしました。",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="read", description="テキストを合成して読み上げる")
    async def read(self, interaction: discord.Interaction, text: str):
        if await self.is_banned(interaction.user.id):
            await interaction.response.send_message("このコマンドを実行する権限がありません。", ephemeral=True)
            return
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            embed = discord.Embed(
                title="エラー",
                description="ボイスチャンネルに接続していません。",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        await interaction.response.defer()
        # テキストを辞書で変換
        dictionary_cog = self.bot.get_cog("DictionaryCog")
        if dictionary_cog:
            text = await dictionary_cog.apply_dictionary(text, interaction.guild.id)
        try:
            tmp_wav = f"tmp/tmp_{uuid.uuid4()}_read.wav"  # UUIDを使用（要求するファイル名だが実際の保存先はライブラリが返す）
            speed = await self.db.get_server_voice_speed(interaction.guild.id)
            if speed is None:
                speed = 1.0
            try:
                saved_path = await self.voicelib.synthesize(text, self.speaker_id, tmp_wav, speed=speed)
            except Exception:
                traceback.print_exc()
                self.bot.error_counter += 1  # エラーカウンターをインクリメント
                return
        except Exception:
            traceback.print_exc()
            self.bot.error_counter += 1  # エラーカウンターをインクリメント
            return
        if not voice_client.is_playing():
            audio_source = discord.FFmpegPCMAudio(saved_path)
            voice_client.play(audio_source)
            while voice_client.is_playing():
                await asyncio.sleep(0.5)
            # 読み上げ成功時にカウンターをインクリメント
            self.bot.tts_counter += 1
        try:
            if saved_path and os.path.exists(saved_path):
                os.remove(saved_path)
        except Exception:
            pass
        embed = discord.Embed(
            title="再生完了",
            description="テキストの読み上げが完了しました。",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="voice", description="読み上げる声を設定")
    async def voice(self, interaction: discord.Interaction):
        if await self.is_banned(interaction.user.id):
            await interaction.response.send_message("あなたはbotからBANされています。", ephemeral=True)
            return

        cog = self  # クロージャ用

        class SpeakerListView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)  # ← ここをNoneに
                self.page = 0
                self.per_page = 10
                self.max_page = (len(SPEAKER_LIST)-1)//self.per_page

            def get_embed(self):
                start = self.page * self.per_page
                items = SPEAKER_LIST[start:start+self.per_page]
                desc = "\n".join(f"{i+start+1}. {item['name']}" for i, item in enumerate(items))
                return discord.Embed(title="話者一覧", description=desc, color=discord.Color.blue())

            @discord.ui.button(label="前へ", style=discord.ButtonStyle.secondary)
            async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
                if self.page > 0:
                    self.page -= 1
                    await interaction.response.edit_message(embed=self.get_embed(), view=self)
                else:
                    await interaction.response.defer()

            @discord.ui.button(label="次へ", style=discord.ButtonStyle.secondary)
            async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
                if self.page < self.max_page:
                    self.page += 1
                    await interaction.response.edit_message(embed=self.get_embed(), view=self)
                else:
                    await interaction.response.defer()

            @discord.ui.button(label="設定", style=discord.ButtonStyle.primary)
            async def select(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.send_modal(VoiceSelectModal())

        class VoiceSelectModal(discord.ui.Modal, title="話者を設定"):
            speaker_number = discord.ui.TextInput(
                label="番号を入力", placeholder="例: 1", required=True, max_length=3
            )

            async def on_submit(self, inter: discord.Interaction):
                try:
                    num = int(self.speaker_number.value)
                except:
                    await inter.response.send_message("無効な番号です。", ephemeral=True)
                    return
                if not (1 <= num <= len(SPEAKER_LIST)):
                    await inter.response.send_message("範囲外の番号です。", ephemeral=True)
                    return
                speaker_info = SPEAKER_LIST[num - 1]
                speaker_id_int = speaker_info["id"]
                speaker_id_str = str(speaker_id_int)
                # DBに保存
                await cog.db.execute(
                    "INSERT INTO user_voice (user_id, speaker_id) VALUES ($1,$2) "
                    "ON CONFLICT (user_id) DO UPDATE SET speaker_id = $2",
                    inter.user.id, speaker_id_str
                )
                await inter.response.send_message(
                    f"{inter.user.display_name}さんが声を {speaker_info['name']} (ID: {speaker_id_int}) に設定しました。", ephemeral=False
                )

        view = SpeakerListView()
        await interaction.response.send_message(
            embed=view.get_embed(), view=view, ephemeral=True
        )

    @app_commands.command(name="speed", description="サーバー全体の読み上げスピードを設定・確認・リセット")
    async def speed(self, interaction: discord.Interaction, value: str = None):
        if value is None:
            speed = await self.db.get_server_voice_speed(interaction.guild.id)
            if speed is not None:
                desc = f"現在のサーバー全体の読み上げスピードは{speed}です。"
            else:
                desc = "サーバー全体の読み上げスピードは設定されていません（デフォルト値が使用されます）。"

            class SpeedButtonView(discord.ui.View):
                def __init__(self, parent, timeout=60):
                    super().__init__(timeout=timeout)
                    self.parent = parent

                @discord.ui.button(label="1.0", style=discord.ButtonStyle.primary)
                async def speed_1(self, interaction2: discord.Interaction, button: discord.ui.Button):
                    await self.parent.set_speed(interaction2, 1.0)

                @discord.ui.button(label="1.2", style=discord.ButtonStyle.primary)
                async def speed_12(self, interaction2: discord.Interaction, button: discord.ui.Button):
                    await self.parent.set_speed(interaction2, 1.2)

                @discord.ui.button(label="1.5", style=discord.ButtonStyle.primary)
                async def speed_15(self, interaction2: discord.Interaction, button: discord.ui.Button):
                    await self.parent.set_speed(interaction2, 1.5)

                @discord.ui.button(label="1.8", style=discord.ButtonStyle.primary)
                async def speed_18(self, interaction2: discord.Interaction, button: discord.ui.Button):
                    await self.parent.set_speed(interaction2, 1.8)

                @discord.ui.button(label="2.0", style=discord.ButtonStyle.primary)
                async def speed_20(self, interaction2: discord.Interaction, button: discord.ui.Button):
                    await self.parent.set_speed(interaction2, 2.0)

                @discord.ui.button(label="リセット", style=discord.ButtonStyle.danger)
                async def reset(self, interaction2: discord.Interaction, button: discord.ui.Button):
                    await self.parent.reset_speed(interaction2)

            async def set_speed(self, interaction2, value):
                await self.db.set_server_voice_speed(interaction2.guild.id, value)
                await interaction2.response.send_message(f"サーバー全体の読み上げスピードを{value}に設定しました。", ephemeral=False)

            async def reset_speed(self, interaction2):
                await self.db.delete_server_voice_speed(interaction2.guild.id)
                await interaction2.response.send_message("サーバー全体の読み上げスピード設定をリセットしました。", ephemeral=True)

            self.set_speed = set_speed.__get__(self)
            self.reset_speed = reset_speed.__get__(self)

            embed = discord.Embed(
                title="読み上げスピード設定",
                description=desc + "\n\n下のボタンからスピードを選択してください。",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, view=SpeedButtonView(self), ephemeral=True)
            return
        if value.lower() == "reset":
            await self.db.delete_server_voice_speed(interaction.guild.id)
            await interaction.response.send_message("サーバー全体の読み上げスピード設定をリセットしました。", ephemeral=True)
            return
        try:
            speed = float(value)
        except ValueError:
            await interaction.response.send_message("スピードは数値（1.0～2.0）または'reset'で指定してください。", ephemeral=True)
            return
        if not (1 <= speed <= 2.0):
            await interaction.response.send_message("スピードは1.0～2.0の間で指定してください。", ephemeral=True)
            return
        await self.db.set_server_voice_speed(interaction.guild.id, speed)
        await interaction.response.send_message(f"サーバー全体の読み上げスピードを{speed}に設定しました。", ephemeral=False)

    async def get_user_speaker_id(self, user_id: int) -> int:
        """ユーザーのスピーカーIDを取得（高負荷時間帯はconfigで制御）"""
        from datetime import datetime, time as dtime
        import pytz
        jst = pytz.timezone("Asia/Tokyo")
        now = datetime.now(jst).time()
        # 設定取得
        high_load_time = getattr(self.bot, "config", {}).get("high_load_time")
        if high_load_time:
            try:
                start_str, end_str = high_load_time.split("-")
                start_h, start_m = map(int, start_str.split(":"))
                end_h, end_m = map(int, end_str.split(":"))
                start = dtime(start_h, start_m)
                end = dtime(end_h, end_m)
                # 例: 22:00-03:00 の場合
                if start <= end:
                    in_range = start <= now < end
                else:
                    in_range = now >= start or now < end
                if in_range:
                    return 3  # ずんだもんID
            except Exception:
                pass  # 設定不正時は通常通り
        row = await self.db.fetchrow("SELECT speaker_id FROM user_voice WHERE user_id = $1", user_id)
        return int(row['speaker_id']) if row else self.speaker_id  # デフォルトはself.speaker_id

    async def process_queue(self, guild_id):
        """サーバーごとの読み上げキューをRustで処理"""
        guild = self.bot.get_guild(guild_id)
        while True:
            try:
                item = self.rust_queue.get_next(guild_id)
                if item is None:
                    await asyncio.sleep(0.1)
                    continue
                text, speaker_id = item
                voice_client = guild.voice_client
                # ボイスチャンネル未接続の場合はスキップ
                if not voice_client or not voice_client.is_connected():
                    continue
                # テキストを辞書で変換
                dictionary_cog = self.bot.get_cog("DictionaryCog")
                if dictionary_cog:
                    text = await dictionary_cog.apply_dictionary(text, guild_id)
                tmp_wav = f"tmp_{uuid.uuid4()}_queue.wav"  # UUIDを使用（要求するファイル名だが実際の保存先はライブラリが返す）
                speed = await self.db.get_server_voice_speed(guild_id)
                if speed is None:
                    speed = 1.0
                try:
                    saved_path = await self.voicelib.synthesize(text, speaker_id, tmp_wav, speed=speed)
                except Exception as e:
                    self.logger.error(f"TTS synth failed for guild {guild_id}: {e}")
                    traceback.print_exc()
                    self.bot.error_counter += 1  # エラーカウンターをインクリメント
                    continue
                if not voice_client.is_playing():
                    audio_source = discord.FFmpegPCMAudio(saved_path)
                    voice_client.play(audio_source)
                    while voice_client.is_playing():
                        await asyncio.sleep(0.5)
                    # 読み上げ成功時にカウンターをインクリメント
                    self.bot.tts_counter += 1
                try:
                    if saved_path and os.path.exists(saved_path):
                        os.remove(saved_path)
                except Exception:
                    pass
            except asyncio.CancelledError:
                break  # タスクがキャンセルされた場合は終了
            except Exception as e:
                self.logger.error(f"Error in process_queue for guild {guild_id}: {e}")
                traceback.print_exc()
                self.bot.error_counter += 1  # エラーカウンターをインクリメント
                continue  # その他のエラーは無視して次のメッセージへ
            await asyncio.sleep(0.1)  # 少し待機して次のメッセージへ

    @commands.Cog.listener()
    async def on_message(self, message):
        """メッセージを読み上げキューに追加"""
        if await self.is_banned(message.author.id):
            return  # BANされたユーザーのメッセージは無視
        # BotやDMは無視
        if message.author.bot or not message.guild:
            return
        # joinコマンドが実行されたチャンネルか確認
        tts_channel_id = self.tts_channels.get(message.guild.id)
        if tts_channel_id != message.channel.id:
            return  # 違うチャンネルの場合は無視

        if message.content.strip() == "s":
            self.rust_queue.clear(message.guild.id)
            voice_client = message.guild.voice_client
            if voice_client and voice_client.is_playing():
                voice_client.stop()
            try:
                await message.add_reaction("✅")
            except Exception:
                pass
            return

        # 添付画像の枚数をカウント
        image_count = sum(1 for a in message.attachments if a.content_type and a.content_type.startswith("image/"))
        # 読み上げテキストを決定
        tts_text = message.content  # メッセージ本文（str型）
        if image_count > 0:
            # メッセージ本文がある場合は本文を優先し、最後に画像枚数を追加
            if tts_text.strip():
                if image_count == 1:
                    tts_text += "、1枚の画像"
                else:
                    tts_text += f"、{image_count}枚の画像"
            else:
                # メッセージ本文が空の場合は画像枚数のみ
                if image_count == 1:
                    tts_text = "1枚の画像"
                else:
                    tts_text = f"{image_count}枚の画像"

        # ユーザーのスピーカーIDを取得
        speaker_id = await self.get_user_speaker_id(message.author.id)
        self.rust_queue.add(message.guild.id, tts_text, speaker_id)  # Rustキューに追加
        # コマンドの処理も継続
        await self.bot.process_commands(message)









    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """ボイスチャンネルの状態変化を監視"""
        try:
            guild = member.guild
            voice_client = guild.voice_client

            # --- Autojoin: 指定VCにメンバーが参加したらBotも自動参加 ---
            try:
                # メンバーが参加したイベント（before=None, after!=None）の場合をチェック
                if before.channel is None and after.channel is not None and not member.bot:
                    cfg = self.autojoin_configs.get(guild.id)
                    if cfg and after.channel and after.channel.id == cfg[0]:
                        # 既に接続済みでなければ接続を試みる
                        if not voice_client or not getattr(voice_client, 'is_connected', lambda: False)():
                            try:
                                vc = await self._connect_voice(after.channel)
                                if vc:
                                    self.logger.info(f"[Autojoin] Connected to VC for guild={guild.id}, channel={after.channel.id}")
                                    # 初期化
                                    self.tts_channels[guild.id] = cfg[1]
                                    if guild.id not in self.queue_tasks or self.queue_tasks[guild.id].done():
                                        self.queue_tasks[guild.id] = self.bot.loop.create_task(self.process_queue(guild.id))
                                    # DBにVC接続状態を保存
                                    try:
                                        await self.db.execute(
                                            "INSERT INTO vc_state (guild_id, channel_id, tts_channel_id) VALUES ($1, $2, $3) ON CONFLICT (guild_id) DO UPDATE SET channel_id = $2, tts_channel_id = $3",
                                            guild.id, after.channel.id, cfg[1]
                                        )
                                    except Exception:
                                        self.logger.exception("Failed to persist vc_state after autojoin")
                                    # TTSチャンネルに通知
                                    try:
                                        tts_channel = guild.get_channel(cfg[1])
                                        if tts_channel:
                                            embed = discord.Embed(
                                                title="自動接続",
                                                description=f"{member.display_name} が {after.channel.name} に参加したため、Botが自動で参加しました。",
                                                color=discord.Color.green()
                                            )
                                            await tts_channel.send(embed=embed)
                                    except Exception:
                                        self.logger.exception("Failed to send autojoin notification embed")
                            except Exception:
                                self.logger.exception(f"Error while autojoining VC for guild {guild.id}")
            except Exception:
                # 自動接続処理での例外はログ出力して続行
                self.logger.exception("Unhandled error in autojoin check")

            # ボットのみになった場合は切断
            if voice_client and voice_client.channel and len(voice_client.channel.members) == 1:
                self.logger.info(f"[VC Disconnect] Reason: Bot only in VC (guild={guild.id}, channel={voice_client.channel.id})")
                await voice_client.disconnect()
                if guild.id in self.queue_tasks:
                    self.queue_tasks[guild.id].cancel()
                    del self.queue_tasks[guild.id]
                self.tts_channels.pop(guild.id, None)
                # データベースからVC接続状態を削除
                await self.db.execute("DELETE FROM vc_state WHERE guild_id = $1", guild.id)
                return

            # ボイスチャンネル未接続の場合の処理や接続チェック
            if voice_client and before.channel == voice_client.channel and after.channel != voice_client.channel:
                # ボットがVCから追放された場合
                if member == guild.me:
                    self.logger.info(f"[VC Disconnect] Reason: Bot was kicked from VC (guild={guild.id}, channel={voice_client.channel.id})")
                    await voice_client.disconnect()
                    if guild.id in self.queue_tasks:
                        self.queue_tasks[guild.id].cancel()
                        del self.queue_tasks[guild.id]
                    self.tts_channels.pop(guild.id, None)
                    # データベースからVC接続状態を削除
                    await self.db.execute("DELETE FROM vc_state WHERE guild_id = $1", guild.id)
                    return

            # --- ボットが予期せずVCから切断された場合の即時再接続 ---
            # ボット自身がVCから抜けた場合（leaveコマンド以外の理由で）
            if member == guild.me and before.channel is not None and after.channel is None:
                self.logger.info(f"[VC Disconnect] Reason: Bot left VC unexpectedly (guild={guild.id}, channel={before.channel.id})")
                row = await self.db.fetchrow("SELECT channel_id, tts_channel_id FROM vc_state WHERE guild_id = $1", guild.id)
                if row:
                    vc_channel = guild.get_channel(row['channel_id'])
                    tts_channel = guild.get_channel(row['tts_channel_id'])
                    if vc_channel and tts_channel:
                        self.logger.info(f"Bot was disconnected from VC in guild {guild.id}, attempting immediate reconnect...")
                        try:
                            # 再接続
                            voice_client = await self._connect_voice(vc_channel)
                            if voice_client is not None:
                                await guild.change_voice_state(channel=vc_channel, self_mute=False, self_deaf=True)
                                self.tts_channels[guild.id] = tts_channel.id
                                self.queue_tasks[guild.id] = self.bot.loop.create_task(self.process_queue(guild.id))
                        except Exception as e:
                            self.logger.error(f"Failed to reconnect to VC in guild {guild.id}: {e}")
                            traceback.print_exc()
                return

            # 参加・退出時にTTSを再生
            if before.channel is None and after.channel is not None:
                # 参加したVCがbotのいるVCか判定
                if voice_client and after.channel == voice_client.channel:
                    msg = f"{member.display_name}が参加しました。"
                else:
                    return
            elif before.channel is not None and after.channel is None:
                # 退出したVCがbotのいるVCか判定
                if voice_client and before.channel == voice_client.channel:
                    msg = f"{member.display_name}が退出しました。"
                else:
                    return
            else:
                return

            if not voice_client or not voice_client.is_connected():
                return

            # メッセージをRustキューに追加（システム音声はスピーカーIDを1に固定）
            self.rust_queue.add(guild.id, msg, self.speaker_id)
            # ここでプロセスタスクが存在しなければ作成する
            if guild.id not in self.queue_tasks or self.queue_tasks[guild.id].done():
                self.queue_tasks[guild.id] = self.bot.loop.create_task(self.process_queue(guild.id))

        except Exception as e:
            self.logger.error(f"Error in on_voice_state_update: {e}")
            traceback.print_exc()

    async def cleanup_temp_files(self):
        """定期的に不要なwavファイルを削除"""
        while True:
            try:
                temp_dir = "tmp"
                if os.path.exists(temp_dir):
                    for file in os.listdir(temp_dir):
                        if file.endswith(".wav"):
                            file_path = os.path.join(temp_dir, file)
                            try:
                                os.remove(file_path)
                                self.logger.info(f"Deleted temp file: {file_path}")
                            except Exception as e:
                                self.logger.error(f"Failed to delete {file_path}: {e}")
                await asyncio.sleep(3600)  # 1時間ごとに実行
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup_temp_files: {e}")
                traceback.print_exc()
                await asyncio.sleep(3600)

    # 新規: 汎用 VC 接続ヘルパー（リトライ・4006 フォールバック対応）
    async def _connect_voice(self, channel: discord.VoiceChannel, max_attempts: int = 3):
        """
        channel.connect() を安全に行うヘルパー。
        - ギルド単位のロックで同時接続を防ぐ
        - ConnectionClosed の close code 4006 を検出したら強制切断せず中断（以前はdisconnectしていた）
        - その他例外は指数バックオフで数回リトライ
        戻り値: VoiceClient または None
        """
        guild_id = channel.guild.id
        lock = self.connect_locks.setdefault(guild_id, asyncio.Lock())
        attempt = 0
        backoff = 1.0
        async with lock:
            # If there's already a connected VoiceClient in this guild, prefer to reuse it
            existing_vc = channel.guild.voice_client
            if existing_vc and getattr(existing_vc, "is_connected", lambda: False)():
                try:
                    # If already connected to the requested channel, just return it
                    if getattr(existing_vc.channel, "id", None) == getattr(channel, "id", None):
                        self.logger.info(f"Reusing existing VoiceClient for guild={guild_id}, channel={channel.id}")
                        return existing_vc
                    # Otherwise, disconnect the existing client before attempting a new connection
                    self.logger.info(f"Found existing VoiceClient in another channel for guild={guild_id}, disconnecting it before connect()")
                    try:
                        await existing_vc.disconnect()
                    except Exception as e:
                        self.logger.warning(f"Failed to disconnect existing VoiceClient for guild={guild_id}: {e}")
                except Exception:
                    # Defensive: ignore any unexpected attribute issues and continue to attempt connect
                    pass

            while attempt < max_attempts:
                attempt += 1
                try:
                    vc = await channel.connect(
                        timeout=self.voice_connect_timeout,
                        reconnect=False,
                        self_mute=False,
                        self_deaf=True
                    )
                    return vc
                except ConnectionClosed as e:
                    code = getattr(e, "code", None)
                    self.logger.warning(f"ConnectionClosed when connecting to VC (guild={guild_id}) attempt={attempt} code={code}")
                    if code == 4006:
                        self.logger.warning(f"Detected 4006 for guild={guild_id}; aborting further attempts (no forced disconnect).")
                        return None
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                except asyncio.TimeoutError:
                    self.logger.warning(f"Timeout when connecting to VC (guild={guild_id}) attempt={attempt}")
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                except Exception as e:
                    # Special-case the common library message when a client already exists
                    msg = str(e)
                    if "Already connected to a voice channel" in msg:
                        self.logger.warning(f"Connect called but already connected in guild={guild_id}; attempting to reuse existing client.")
                        existing_vc = channel.guild.voice_client
                        if existing_vc and getattr(existing_vc, "is_connected", lambda: False)():
                            return existing_vc
                        # If we couldn't find the existing client, just give up this attempt and retry
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        continue
                    self.logger.error(f"Error connecting to VC (guild={guild_id}) attempt={attempt}: {e}")
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
        return None

    async def sync_vcstate_periodically(self):
        """DBのvc_stateと実際のVC接続状態を定期的に同期する"""
        while True:
            try:
                await self.sync_vcstate_once()
                await asyncio.sleep(600)  # 10分ごとに実行
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in sync_vcstate_periodically: {e}")
                traceback.print_exc()
                await asyncio.sleep(600)

    async def sync_vcstate_once(self):
        """1回だけvc_stateとVC接続状態を同期する"""
        # DBに記録されているギルド一覧を取得
        db_states = await self.db.fetch("SELECT guild_id FROM vc_state")
        db_guild_ids = {row['guild_id'] for row in db_states}
        # 実際にVC接続しているギルド一覧
        connected_guild_ids = {vc.guild.id for vc in self.bot.voice_clients if vc.is_connected()}
        # DBにあるが実際には接続していないギルド
        stale_guild_ids = db_guild_ids - connected_guild_ids
        for gid in stale_guild_ids:
            self.logger.info(f"Removing stale vc_state for guild {gid}")
            await self.db.execute("DELETE FROM vc_state WHERE guild_id = $1", gid)
        # DBにないが接続しているギルドに対してレコードを追加
        new_guild_ids = connected_guild_ids - db_guild_ids
        for gid in new_guild_ids:
            vc = next((vc for vc in self.bot.voice_clients if vc.guild.id == gid), None)
            if vc and vc.is_connected():
                tts_channel_id = self.tts_channels.get(gid)
                if tts_channel_id:
                    self.logger.info(f"Adding missing vc_state for guild {gid}")
                    await self.db.execute(
                        "INSERT INTO vc_state (guild_id, channel_id, tts_channel_id) VALUES ($1, $2, $3) ON CONFLICT (guild_id) DO UPDATE SET channel_id = $2, tts_channel_id = $3",
                        gid, vc.channel.id, tts_channel_id
                    )

async def setup(bot):
    await bot.add_cog(VoiceReadCog(bot))
