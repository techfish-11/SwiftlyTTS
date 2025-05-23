import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
import yaml
from lib.postgres import PostgresDB  # PostgresDBクラスをインポート

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

with open("config.yml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.AutoShardedBot(
    command_prefix=config["prefix"],
    shard_count=3,
    intents=intents
)

db = PostgresDB()  # データベースクラスのインスタンスを作成

async def update_rpc_task():
    while True:
        try:
            guild_count = len(bot.guilds)
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

    bot.loop.create_task(update_rpc_task(), name="update_rpc_task")
    bot.loop.create_task(restart_rpc_task(), name="restart_rpc_task")

    tasks = []
    for root, _, files in os.walk('./cogs'):
        py_files = [file for file in files if file.endswith('.py')]
        tasks.extend(
            bot.load_extension(f'cogs.{os.path.relpath(os.path.join(root, file), "./cogs").replace(os.sep, ".").rsplit(".", 1)[0]}')
            for file in py_files
        )

    await asyncio.gather(*tasks)

    await bot.tree.sync()

    print("All cogs loaded and commands synced!")

bot.run(TOKEN)