import discord
from discord.errors import ConnectionClosed
from discord.ext import commands
import asyncio
import os
import subprocess
from lib.VOICEVOXlib import VOICEVOXLib
from discord import app_commands
from lib.postgres import PostgresDB  # PostgresDBをインポート
import uuid
from dotenv import load_dotenv  # dotenvをインポート
import traceback

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
    def __init__(self, bot):
        self.bot = bot
        self.voicelib = VOICEVOXLib()
        self.speaker_id = 1
        self.tts_channels = {}      # {guild.id: channel.id}
        self.message_queues = {}    # {guild.id: asyncio.Queue}
        self.queue_tasks = {}       # {guild.id: Task}
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

        def handle_global_exception(loop, context):
            print("=== Unhandled exception in event loop ===")
            msg = context.get("exception", context.get("message"))
            print(f"Exception: {msg}")
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

        if self.debug_mode:
            print("DEBUGモードのためVC状態復元をスキップします。")
            return

        if not self.reconnect_enabled:
            print("Reconnect is disabled. Skipping VC state restoration.")
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
                    print(f"Skipping reconnection to empty VC in guild {guild.id}")
                    continue
                try:
                    # 変更: 汎用接続ヘルパーを利用
                    voice_client = await self._connect_voice(vc_channel)
                    if voice_client is None:
                        print(f"Failed to reconnect to VC in guild {guild.id}: helper returned None")
                        continue
                    await guild.change_voice_state(channel=vc_channel, self_mute=False, self_deaf=True)
                    self.tts_channels[guild.id] = tts_channel.id
                    self.message_queues[guild.id] = asyncio.Queue()
                    self.queue_tasks[guild.id] = self.bot.loop.create_task(self.process_queue(guild.id))
                except Exception as e:
                    print(f"Failed to reconnect to VC in guild {guild.id}: {e}")
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
                print(f"Error while cancelling cleanup_task: {e}")
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
                print(f"Error while cancelling sync_vcstate_task: {e}")
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
                self.message_queues.pop(guild_id, None)
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
            self.message_queues[guild_id] = asyncio.Queue()
            self.queue_tasks[guild_id] = self.bot.loop.create_task(self.process_queue(guild_id))
            
            # データベースにVC接続状態を保存（DEBUGモード時はスキップ）
            if not self.debug_mode:
                await self.db.execute(
                    "INSERT INTO vc_state (guild_id, channel_id, tts_channel_id) VALUES ($1, $2, $3) ON CONFLICT (guild_id) DO UPDATE SET channel_id = $2, tts_channel_id = $3",
                    guild_id, channel.id, interaction.channel.id
                )

            # 「接続しました。」と喋る処理を非同期で実行
            async def play_connection_message():
                tmp_wav = f"tmp_{uuid.uuid4()}_join.wav"  # UUIDを使用
                user_speaker_id = await self.get_user_speaker_id(interaction.user.id)
                await self.voicelib.synthesize("接続しました。", user_speaker_id, tmp_wav)
                voice_client = interaction.guild.voice_client
                if voice_client and not voice_client.is_playing():
                    audio_source = discord.FFmpegPCMAudio(tmp_wav)
                    voice_client.play(audio_source)
                    while voice_client.is_playing():
                        await asyncio.sleep(0.5)
                if os.path.exists(tmp_wav):
                    os.remove(tmp_wav)

            self.bot.loop.create_task(play_connection_message())

            embed = discord.Embed(
                title="接続完了",
                description=f"{channel.name}に接続しました。\n\nサポートサーバー: https://discord.gg/mNDvAYayp5",
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
            await interaction.guild.voice_client.disconnect()
            # キュー・タスク等をリセット
            if interaction.guild.id in self.queue_tasks:
                self.queue_tasks[interaction.guild.id].cancel()
                del self.queue_tasks[interaction.guild.id]
            self.tts_channels.pop(interaction.guild.id, None)
            self.message_queues.pop(interaction.guild.id, None)
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
            tmp_wav = f"tmp/tmp_{uuid.uuid4()}_read.wav"  # UUIDを使用
            speed = await self.db.get_server_voice_speed(interaction.guild.id)
            if speed is None:
                speed = 1.0
            await self.voicelib.synthesize(text, self.speaker_id, tmp_wav, speed=speed)
        except Exception:
            traceback.print_exc()
            return
        if not voice_client.is_playing():
            audio_source = discord.FFmpegPCMAudio(tmp_wav)
            voice_client.play(audio_source)
            while voice_client.is_playing():
                await asyncio.sleep(0.5)
        if os.path.exists(tmp_wav):
            os.remove(tmp_wav)
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
        """ユーザーのスピーカーIDを取得"""
        row = await self.db.fetchrow("SELECT speaker_id FROM user_voice WHERE user_id = $1", user_id)
        return int(row['speaker_id']) if row else self.speaker_id  # デフォルトはself.speaker_id

    async def process_queue(self, guild_id):
        """サーバーごとの読み上げキューを処理"""
        guild = self.bot.get_guild(guild_id)
        queue = self.message_queues.get(guild_id)
        if not queue:
            return  # キューが存在しない場合は終了
        while True:
            try:
                text, speaker_id = await queue.get()  # キューからテキストとスピーカーIDを取得
                voice_client = guild.voice_client
                # ボイスチャンネル未接続の場合はスキップ
                if not voice_client or not voice_client.is_connected():
                    continue
                # テキストを辞書で変換
                dictionary_cog = self.bot.get_cog("DictionaryCog")
                if dictionary_cog:
                    text = await dictionary_cog.apply_dictionary(text, guild_id)
                tmp_wav = f"tmp_{uuid.uuid4()}_queue.wav"  # UUIDを使用
                speed = await self.db.get_server_voice_speed(guild_id)
                if speed is None:
                    speed = 1.0
                await self.voicelib.synthesize(text, speaker_id, tmp_wav, speed=speed)
                if not voice_client.is_playing():
                    audio_source = discord.FFmpegPCMAudio(tmp_wav)
                    voice_client.play(audio_source)
                    while voice_client.is_playing():
                        await asyncio.sleep(0.5)
                if os.path.exists(tmp_wav):
                    os.remove(tmp_wav)
            except asyncio.CancelledError:
                break  # タスクがキャンセルされた場合は終了
            except Exception as e:
                print(f"Error in process_queue for guild {guild_id}: {e}")
                traceback.print_exc()
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
            queue = self.message_queues.get(message.guild.id)
            if queue:
                while not queue.empty():
                    try:
                        queue.get_nowait()
                    except Exception:
                        break
            voice_client = message.guild.voice_client
            if voice_client and voice_client.is_playing():
                voice_client.stop()
            try:
                await message.add_reaction("✅")
            except Exception:
                pass
            return

        # キューが存在しない場合は初期化
        queue = self.message_queues.setdefault(message.guild.id, asyncio.Queue())
        # 添付画像の枚数をカウント
        image_count = sum(1 for a in message.attachments if a.content_type and a.content_type.startswith("image/"))
        # 読み上げテキストを決定
        if image_count > 0:
            if image_count == 1:
                tts_text = "1枚の画像"
            else:
                tts_text = f"{image_count}枚の画像"
        else:
            tts_text = message.content  # メッセージ本文（str型）

        # ユーザーのスピーカーIDを取得
        speaker_id = await self.get_user_speaker_id(message.author.id)
        await queue.put((tts_text, speaker_id))  # テキストとスピーカーIDをキューに追加
        # コマンドの処理も継続
        await self.bot.process_commands(message)









    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """ボイスチャンネルの状態変化を監視"""
        try:
            guild = member.guild
            voice_client = guild.voice_client

            # --- 自動切断を無効化: エラー発生時にもVCから切断しない ---
            # if voice_client and voice_client.channel and len(voice_client.channel.members) == 1:
            #     await voice_client.disconnect()
            #     if guild.id in self.queue_tasks:
            #         self.queue_tasks[guild.id].cancel()
            #         del self.queue_tasks[guild.id]
            #     self.tts_channels.pop(guild.id, None)
            #     self.message_queues.pop(guild.id, None)
            #     await self.db.execute("DELETE FROM vc_state WHERE guild_id = $1", guild.id)
            #     return

            # --- ボットがVCから追放された場合の自動切断も無効化 ---
            # if voice_client and before.channel == voice_client.channel and after.channel != voice_client.channel:
            #     if member == guild.me:
            #         await voice_client.disconnect()
            #         if guild.id in self.queue_tasks:
            #             self.queue_tasks[guild.id].cancel()
            #             del self.queue_tasks[guild.id]
            #         self.tts_channels.pop(guild.id, None)
            #         self.message_queues.pop(guild.id, None)
            #         await self.db.execute("DELETE FROM vc_state WHERE guild_id = $1", guild.id)
            #         return

            # --- ボットが予期せずVCから切断された場合の即時再接続 ---
            # ボット自身がVCから抜けた場合（leaveコマンド以外の理由で）
            
            if member == guild.me and before.channel is not None and after.channel is None:
                row = await self.db.fetchrow("SELECT channel_id, tts_channel_id FROM vc_state WHERE guild_id = $1", guild.id)
                if row:
                    vc_channel = guild.get_channel(row['channel_id'])
                    tts_channel = guild.get_channel(row['tts_channel_id'])
                    if vc_channel and tts_channel:
                        print(f"Bot was disconnected from VC in guild {guild.id}, attempting immediate reconnect...")
                        try:
                            # 再接続
                            voice_client = await self._connect_voice(vc_channel)
                            if voice_client is not None:
                                await guild.change_voice_state(channel=vc_channel, self_mute=False, self_deaf=True)
                                self.tts_channels[guild.id] = tts_channel.id
                                self.message_queues[guild.id] = asyncio.Queue()
                                self.queue_tasks[guild.id] = self.bot.loop.create_task(self.process_queue(guild.id))
                        except Exception as e:
                            print(f"Failed to reconnect to VC in guild {guild.id}: {e}")
                            traceback.print_exc()
                return

            # 参加・退出時にTTSを再生
            if before.channel is None and after.channel is not None:
                msg = f"{member.display_name}が参加しました。"
            elif before.channel is not None and after.channel is None:
                msg = f"{member.display_name}が退出しました。"
            else:
                return

            if not voice_client or not voice_client.is_connected():
                return

            # メッセージをキューに追加（システム音声はスピーカーIDを1に固定）
            queue = self.message_queues.setdefault(guild.id, asyncio.Queue())
            await queue.put((msg, self.speaker_id))  # システム音声用: (text, speaker_id)
            # ここでプロセスタスクが存在しなければ作成する
            if guild.id not in self.queue_tasks or self.queue_tasks[guild.id].done():
                self.queue_tasks[guild.id] = self.bot.loop.create_task(self.process_queue(guild.id))

        except Exception as e:
            print(f"Error in on_voice_state_update: {e}")
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
                                print(f"Deleted temp file: {file_path}")
                            except Exception as e:
                                print(f"Failed to delete {file_path}: {e}")
                await asyncio.sleep(3600)  # 1時間ごとに実行
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in cleanup_temp_files: {e}")
                traceback.print_exc()
                await asyncio.sleep(3600)

    # 新規: 汎用 VC 接続ヘルパー（リトライ・4006 フォールバック対応）
    async def _connect_voice(self, channel: discord.VoiceChannel, max_attempts: int = 3):
        """
        channel.connect() を安全に行うヘルパー。
        - ギルド単位のロックで同時接続を防ぐ
        - ConnectionClosed の close code 4006 を検出したら即座に失敗を返す（無限リトライ回避）
        - その他例外は指数バックオフで数回リトライ
        戻り値: VoiceClient または None
        """
        guild_id = channel.guild.id
        lock = self.connect_locks.setdefault(guild_id, asyncio.Lock())
        attempt = 0
        reconnect_param = self.reconnect_enabled
        backoff = 1.0
        async with lock:
            while attempt < max_attempts:
                attempt += 1
                try:
                    vc = await channel.connect(
                        timeout=self.voice_connect_timeout,
                        reconnect=False,  # Changed: Disable internal retries to avoid overlapping with custom retry logic
                        self_mute=False,
                        self_deaf=True
                    )
                    return vc
                except ConnectionClosed as e:
                    code = getattr(e, "code", None)
                    print(f"ConnectionClosed when connecting to VC (guild={guild_id}) attempt={attempt} code={code}")
                    if code == 4006:
                        print(f"Detected 4006 for guild={guild_id}; aborting connect attempts without disconnect.")
                        return None
                    # それ以外は少し待って再試行
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                except asyncio.TimeoutError:
                    print(f"Timeout when connecting to VC (guild={guild_id}) attempt={attempt}")
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                except Exception as e:
                    print(f"Error connecting to VC (guild={guild_id}) attempt={attempt}: {e}")
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
                print(f"Error in sync_vcstate_periodically: {e}")
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
            print(f"Removing stale vc_state for guild {gid}")
            await self.db.execute("DELETE FROM vc_state WHERE guild_id = $1", gid)

async def setup(bot):
    await bot.add_cog(VoiceReadCog(bot))
