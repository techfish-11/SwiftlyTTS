
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from lib import postgres
import asyncio


app = FastAPI()

_bot = None  # グローバルでbotインスタンスを保持

def set_bot(bot):
    global _bot
    _bot = bot

# CORS許可（必要に応じて調整）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB初期化
pg = postgres.PostgresDB()
@app.on_event("startup")
async def startup():
    await pg.initialize()

@app.on_event("shutdown")
async def shutdown():
    await pg.close()

@app.get("/user-dictionary/{user_id}")
async def get_user_dictionary(user_id: int):
    print(f"[API] Fetching user dictionary for user_id={user_id}")
    try:
        entries = await pg.get_all_user_dictionary(user_id)
        return {"dictionary": [{"key": r["key"], "value": r["value"]} for r in entries]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/servers")
async def get_server_count():
    """Return the number of guilds the bot is connected to.

    Response shape:
      { "count": 123 }

    If the global bot instance is not set, return a 503 with ok:false.
    """
    try:
        if _bot is None:
            raise HTTPException(status_code=503, detail="bot not ready")

        # AutoShardedBot and Bot both expose guilds; use len(list(_bot.guilds)) to be safe
        try:
            guilds = list(_bot.guilds)
            count = len(guilds)
        except Exception:
            # Fallback: try attribute `guild_count` if available
            count = getattr(_bot, "guild_count", None)
            if count is None:
                raise

        return JSONResponse({"count": int(count)})
    except HTTPException:
        raise
    except Exception as e:
        # Return 500 on unexpected errors
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/user-dictionary/notify")
async def notify_user_dictionary(request: Request):
    print("[Notify] Received user dictionary change notification")
    data = await request.json()
    user_id = data.get("user_id")
    print(f"[Notify] user_dictionary changed for user_id={user_id}")
    # --- キャッシュクリア処理 ---
    if _bot is not None and user_id is not None:
        cog = _bot.get_cog("DictionaryCog")
        if cog is not None:
            # cache_lockを使ってpop
            try:
                async def clear_cache():
                    async with cog.cache_lock:
                        cog.user_dict_cache.pop(int(user_id), None)
                # 別スレッドから呼ばれる可能性があるのでloopで実行
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(clear_cache(), loop)
                else:
                    loop.run_until_complete(clear_cache())
            except Exception as e:
                print(f"[Notify] cache clear error: {e}")
    return {"ok": True}


# ギルド辞書変更通知
@app.post("/guild-dictionary/notify")
async def notify_guild_dictionary(request: Request):
    print("[Notify] Received guild dictionary change notification")
    data = await request.json()
    guild_id = data.get("guild_id")
    print(f"[Notify] guild_dictionary changed for guild_id={guild_id}")
    # --- キャッシュクリア処理 ---
    if _bot is not None and guild_id is not None:
        cog = _bot.get_cog("DictionaryCog")
        if cog is not None:
            try:
                async def clear_cache():
                    async with cog.cache_lock:
                        cog.server_dict_cache.pop(int(guild_id), None)
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(clear_cache(), loop)
                else:
                    loop.run_until_complete(clear_cache())
            except Exception as e:
                print(f"[Notify] guild cache clear error: {e}")
    return {"ok": True}
