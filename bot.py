import asyncio
import sys
if sys.platform == "win32":
    # Windows 上ではselectorベースの高速なイベントループを明示的に設定
    from asyncio import WindowsSelectorEventLoopPolicy
    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
else:
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except ImportError:
        pass

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import yaml
from lib.postgres import PostgresDB  # PostgresDBクラスをインポート
import threading
import uvicorn
from lib.bot_http_server import app as bot_http_app, set_bot

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
SHARD_COUNT = int(os.getenv('SHARD_COUNT', 3))  # デフォルト値を3に設定

with open("config.yml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.AutoShardedBot(
    command_prefix=config["prefix"],
    shard_count=SHARD_COUNT,  # 環境変数から取得したシャード数を使用
    intents=intents
)
bot.config = config  # 追加: 設定をbotインスタンスに保持
    
# --- FastAPI HTTPサーバーをバックグラウンドで起動 ---

def start_bot_http_server():
    port = int(os.getenv("BOT_HTTP_PORT", 8000))
    uvicorn.run(bot_http_app, host="0.0.0.0", port=port, log_level="info")


# botインスタンスをFastAPI側に渡す
set_bot(bot)
threading.Thread(target=start_bot_http_server, daemon=True).start()

# メトリクス用のカウンターを初期化
bot.tts_counter = 0
bot.error_counter = 0

# --- ここから同期的にコグを全ロード ---
async def load_all_cogs():
    for root, _, files in os.walk('./cogs'):
        for file in files:
            if not file.endswith('.py'):
                continue
            ext = (
                "cogs."
                + os.path.relpath(os.path.join(root, file), "./cogs")
                    .replace(os.sep, ".")
                    .rsplit(".", 1)[0]
            )
            await bot.load_extension(ext)  # 非同期でロード
    print("All cogs loaded synchronously!")

# --- ここまで ---

db = PostgresDB()  # データベースクラスのインスタンスを作成

async def update_rpc_task():
    while True:
        try:
            guild_count = len(bot.guilds)
            debug_mode = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")

            if not debug_mode:
                await db.insert_guild_count(guild_count)
            else:
                pass

            latency = round(bot.latency * 1000)
            vc_count = sum(1 for vc in bot.voice_clients if vc.is_connected() and vc.channel and len(vc.channel.members) > 0)
            await bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name=f"/join | {guild_count} servers | {vc_count} VCs | {latency}ms"
                )
            )
        except Exception as e:
            print(f"Error in update_rpc_task: {e}")
        await asyncio.sleep(10)  # 10秒ごとに更新するように変更

async def restart_rpc_task():
    while True:
        try:
            # 現在のタスクをキャンセルして再作成
            for task in asyncio.all_tasks():
                if task.get_name() == "update_rpc_task":
                    task.cancel()
                    break
            bot.loop.create_task(update_rpc_task(), name="update_rpc_task")
        except Exception as e:
            print(f"Error in restart_rpc_task: {e}")
        await asyncio.sleep(3600)  # 1時間ごとにタスクを再作成

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

    # データベース接続テスト
    print("Testing database connection...")
    try:
        await db.initialize()
        print("Database connection successful!")
    except Exception as e:
        print(f"Database connection failed: {e}")
        await bot.close()
        return

    # コグロードを非同期で実行
    await load_all_cogs()

    # コマンド同期を非同期タスクとして実行
    bot.loop.create_task(bot.tree.sync())
    print("Commands syncing in background!")

    # RPCタスクを遅延起動
    bot.loop.create_task(update_rpc_task(), name="update_rpc_task")
    bot.loop.create_task(restart_rpc_task(), name="restart_rpc_task")

bot.run(TOKEN)
