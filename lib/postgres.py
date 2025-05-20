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
print(f"Connecting to DB at {DB_HOST}:{DB_PORT} as {DB_USER} to {DB_NAME}")


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
            min_size=1,
            max_size=10
        )
        # 辞書テーブルを作成
        async with self._pool.acquire() as connection:
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS dictionary (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    author_id BIGINT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS banlist (
                    user_id BIGINT PRIMARY KEY
                );
                CREATE TABLE IF NOT EXISTS vc_state (
                    guild_id BIGINT PRIMARY KEY,
                    channel_id BIGINT NOT NULL
                );
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
            return await connection.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Execute a SELECT query and return a single row"""
        if not self._pool:
            raise RuntimeError("Database connection pool is not initialized.")
        async with self._pool.acquire() as connection:
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
            return await connection.execute(query, *args)

    async def executemany(self, query: str, args_list: List[tuple]) -> None:
        """Execute a query with multiple sets of arguments"""
        if not self._pool:
            raise RuntimeError("Database connection pool is not initialized.")
        async with self._pool.acquire() as connection:
            await connection.executemany(query, args_list)


# Example usage
# db = PostgresDB()
# await db.initialize()
# await db.execute("INSERT INTO users (id, name) VALUES ($1, $2)", 1, "John Doe")
# await db.close()