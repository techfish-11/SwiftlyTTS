import os
import asyncpg
from dotenv import load_dotenv
from typing import Optional, List

load_dotenv(override=True)

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_SSL_ENV = os.getenv("DB_SSL", "false").lower()
if DB_SSL_ENV == "true":
    DB_SSL = True
else:
    DB_SSL = False
print(f"Connecting to DB at {DB_HOST}:{DB_PORT} as {DB_USER} to {DB_NAME} (SSL: {DB_SSL})")

class PostgresDB:
    """PostgreSQL database management class using asyncpg"""

    def __init__(self) -> None:
        self._pool: Optional[asyncpg.Pool] = None

    async def initialize(self) -> None:
        """Initialize the connection pool and ensure the dictionary table exists"""
        self._pool = await asyncpg.create_pool(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            ssl=DB_SSL,
            min_size=1,
            max_size=10
        )
        # 辞書テーブルを作成
        async with self._pool.acquire() as connection:
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS dictionarynew (
                    guild_id BIGINT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    author_id BIGINT NOT NULL,
                    PRIMARY KEY (guild_id, key)
                );
                CREATE TABLE IF NOT EXISTS globaldic (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS banlist (
                    user_id BIGINT PRIMARY KEY
                );
                CREATE TABLE IF NOT EXISTS vc_state (
                    guild_id BIGINT PRIMARY KEY,
                    channel_id BIGINT NOT NULL,
                    tts_channel_id BIGINT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS user_voice (
                    user_id BIGINT PRIMARY KEY,
                    speaker_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS server_voice_speed (
                    guild_id BIGINT PRIMARY KEY,
                    speed FLOAT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS server_stats (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
                    guild_count INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS autojoin_config (
                    guild_id BIGINT PRIMARY KEY,
                    vc_channel_id BIGINT NOT NULL,
                    tts_channel_id BIGINT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS user_dictionary (
                    user_id BIGINT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    PRIMARY KEY (user_id, key)
                );
            """)
            # user_voice.speaker_id の型がintegerならtextにマイグレート
            col_info = await connection.fetchrow("""
                SELECT data_type FROM information_schema.columns
                WHERE table_name = 'user_voice' AND column_name = 'speaker_id'
            """)
            if col_info and col_info['data_type'] in ('integer', 'bigint', 'smallint'):
                # 一時カラム追加→データコピー→カラム削除→リネーム
                await connection.execute("""
                    ALTER TABLE user_voice ADD COLUMN speaker_id_text TEXT;
                """)
                await connection.execute("""
                    UPDATE user_voice SET speaker_id_text = speaker_id::text;
                """)
                await connection.execute("""
                    ALTER TABLE user_voice DROP COLUMN speaker_id;
                """)
                await connection.execute("""
                    ALTER TABLE user_voice RENAME COLUMN speaker_id_text TO speaker_id;
                """)

    async def close(self) -> None:
        """Close the connection pool"""
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def fetch(self, query: str, *args) -> List[asyncpg.Record]:
        """Execute a SELECT query and return the results"""
        if not self._pool:
            raise RuntimeError("Database connection pool is not initialized.")
        async with self._pool.acquire() as connection:
            async with connection.transaction():  # トランザクションを追加
                return await connection.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Execute a SELECT query and return a single row"""
        if not self._pool:
            raise RuntimeError("Database connection pool is not initialized.")
        async with self._pool.acquire() as connection:
            async with connection.transaction():  # トランザクションを追加
                return await connection.fetchrow(query, *args)

    async def fetch_column(self, query: str, *args) -> List:
        """Execute a SELECT query and return the first column of each row as a list"""
        if not self._pool:
            raise RuntimeError("Database connection pool is not initialized.")
        async with self._pool.acquire() as connection:
            records = await connection.fetch(query, *args)
            return [record[0] for record in records]

    async def execute(self, query: str, *args) -> str:
        """Execute an INSERT, UPDATE, or DELETE query"""
        if not self._pool:
            raise RuntimeError("Database connection pool is not initialized.")
        async with self._pool.acquire() as connection:
            async with connection.transaction():  # トランザクションを追加
                return await connection.execute(query, *args)

    async def executemany(self, query: str, args_list: List[tuple]) -> None:
        """Execute a query with multiple sets of arguments"""
        if not self._pool:
            raise RuntimeError("Database connection pool is not initialized.")
        async with self._pool.acquire() as connection:
            async with connection.transaction():  # トランザクションを追加
                for batch in range(0, len(args_list), 100):  # バッチ処理を追加
                    await connection.executemany(query, args_list[batch:batch + 100])

    async def get_server_voice_speed(self, guild_id: int) -> Optional[float]:
        """Get the voice speed for a server (guild). Returns None if not set."""
        if not self._pool:
            raise RuntimeError("Database connection pool is not initialized.")
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(
                "SELECT speed FROM server_voice_speed WHERE guild_id = $1", guild_id
            )
            return row["speed"] if row else None

    async def set_server_voice_speed(self, guild_id: int, speed: float) -> None:
        """Set or update the voice speed for a server (guild)."""
        if not self._pool:
            raise RuntimeError("Database connection pool is not initialized.")
        async with self._pool.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO server_voice_speed (guild_id, speed)
                VALUES ($1, $2)
                ON CONFLICT (guild_id) DO UPDATE SET speed = EXCLUDED.speed
                """,
                guild_id, speed
            )

    async def delete_server_voice_speed(self, guild_id: int) -> None:
        """Delete the voice speed setting for a server (guild)."""
        if not self._pool:
            raise RuntimeError("Database connection pool is not initialized.")
        async with self._pool.acquire() as connection:
            await connection.execute(
                "DELETE FROM server_voice_speed WHERE guild_id = $1", guild_id
            )

    async def upsert_dictionary(self, guild_id: int, key: str, value: str, author_id: int) -> None:
        """Insert or update a dictionary entry for a specific guild."""
        if not self._pool:
            raise RuntimeError("Database connection pool is not initialized.")
        async with self._pool.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO dictionarynew (guild_id, key, value, author_id)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (guild_id, key) DO UPDATE SET value = $3, author_id = $4
                """,
                guild_id, key, value, author_id
            )

    async def remove_dictionary(self, guild_id: int, key: str) -> str:
        """Remove a dictionary entry for a specific guild."""
        if not self._pool:
            raise RuntimeError("Database connection pool is not initialized.")
        async with self._pool.acquire() as connection:
            return await connection.execute(
                "DELETE FROM dictionarynew WHERE guild_id = $1 AND key = $2", guild_id, key
            )

    async def get_dictionary_entry(self, guild_id: int, key: str) -> Optional[asyncpg.Record]:
        """Get a dictionary entry for a specific guild."""
        if not self._pool:
            raise RuntimeError("Database connection pool is not initialized.")
        async with self._pool.acquire() as connection:
            return await connection.fetchrow(
                "SELECT value, author_id FROM dictionarynew WHERE guild_id = $1 AND key = $2", guild_id, key
            )

    async def get_all_dictionary(self, guild_id: int) -> List[asyncpg.Record]:
        """Get all dictionary entries for a specific guild."""
        if not self._pool:
            raise RuntimeError("Database connection pool is not initialized.")
        async with self._pool.acquire() as connection:
            return await connection.fetch(
                "SELECT key, value FROM dictionarynew WHERE guild_id = $1", guild_id
            )

    async def get_all_global_dictionary(self) -> List[asyncpg.Record]:
        """Get all global dictionary entries."""
        if not self._pool:
            raise RuntimeError("Database connection pool is not initialized.")
        async with self._pool.acquire() as connection:
            return await connection.fetch(
                "SELECT key, value FROM globaldic"
            )

    async def get_autojoin(self, guild_id: int) -> Optional[asyncpg.Record]:
        """Get the autojoin configuration for a specific guild."""
        if not self._pool:
            raise RuntimeError("Database connection pool is not initialized.")
        async with self._pool.acquire() as connection:
            return await connection.fetchrow(
                "SELECT vc_channel_id, tts_channel_id FROM autojoin_config WHERE guild_id = $1",
                guild_id
            )

    async def fetch_all_autojoin(self) -> List[asyncpg.Record]:
        """Return all autojoin configurations."""
        if not self._pool:
            raise RuntimeError("Database connection pool is not initialized.")
        async with self._pool.acquire() as connection:
            return await connection.fetch("SELECT guild_id, vc_channel_id, tts_channel_id FROM autojoin_config")

    async def set_autojoin(self, guild_id: int, vc_channel_id: int, tts_channel_id: int) -> None:
        """Insert or update autojoin configuration for a guild."""
        if not self._pool:
            raise RuntimeError("Database connection pool is not initialized.")
        async with self._pool.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO autojoin_config (guild_id, vc_channel_id, tts_channel_id)
                VALUES ($1, $2, $3)
                ON CONFLICT (guild_id) DO UPDATE SET vc_channel_id = $2, tts_channel_id = $3
                """,
                guild_id, vc_channel_id, tts_channel_id
            )

    async def delete_autojoin(self, guild_id: int) -> str:
        """Delete autojoin configuration for a guild."""
        if not self._pool:
            raise RuntimeError("Database connection pool is not initialized.")
        async with self._pool.acquire() as connection:
            return await connection.execute("DELETE FROM autojoin_config WHERE guild_id = $1", guild_id)

    async def insert_guild_count(self, guild_count: int) -> None:
        """サーバー数をserver_statsテーブルに記録し、1日経過したレコードを削除する"""
        if not self._pool:
            raise RuntimeError("Database connection pool is not initialized.")
        async with self._pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    "INSERT INTO server_stats (guild_count) VALUES ($1)", guild_count
                )
                await connection.execute(
                    "DELETE FROM server_stats WHERE timestamp < (now() - INTERVAL '1 day')"
                )

    async def upsert_user_dictionary(self, user_id: int, key: str, value: str) -> None:
        """Insert or update a user dictionary entry."""
        if not self._pool:
            raise RuntimeError("Database connection pool is not initialized.")
        async with self._pool.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO user_dictionary (user_id, key, value)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, key) DO UPDATE SET value = $3
                """,
                user_id, key, value
            )

    async def remove_user_dictionary(self, user_id: int, key: str) -> str:
        """Remove a user dictionary entry."""
        if not self._pool:
            raise RuntimeError("Database connection pool is not initialized.")
        async with self._pool.acquire() as connection:
            return await connection.execute(
                "DELETE FROM user_dictionary WHERE user_id = $1 AND key = $2", user_id, key
            )

    async def get_user_dictionary_entry(self, user_id: int, key: str) -> Optional[asyncpg.Record]:
        """Get a user dictionary entry."""
        if not self._pool:
            raise RuntimeError("Database connection pool is not initialized.")
        async with self._pool.acquire() as connection:
            return await connection.fetchrow(
                "SELECT value FROM user_dictionary WHERE user_id = $1 AND key = $2", user_id, key
            )

    async def get_all_user_dictionary(self, user_id: int) -> List[asyncpg.Record]:
        """Get all user dictionary entries for a user."""
        if not self._pool:
            raise RuntimeError("Database connection pool is not initialized.")
        async with self._pool.acquire() as connection:
            return await connection.fetch(
                "SELECT key, value FROM user_dictionary WHERE user_id = $1", user_id
            )
