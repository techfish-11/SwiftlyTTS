
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
