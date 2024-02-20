from psycopg_pool import AsyncConnectionPool
from psycopg import Cursor
from common.app.core.config import config as cfg_c

"""
The pool object creates a pool of connects.
This ensures that every user who comes to us will be served asynchronously
"""
pool: AsyncConnectionPool = None


async def init_pool(cfg=cfg_c):
    global pool
    if pool is None:
        pool = AsyncConnectionPool(cfg.DB_URL, open=False, max_size=cfg.DB_POOL_SIZE_MAX, timeout=cfg.DB_POOL_TIMEOUT)
        await pool.open()


async def close_pool():
    global pool
    if not (pool is None):
        await pool.close()
        pool = None


def get_pool():
    return pool


def get_pool_cur(func):
    async def _inner_(*args, **kwargs):
        async with get_pool().connection() as conn:
            await conn.set_autocommit(True)
            cursor: Cursor = conn.cursor()
            return await func(cursor, *args, **kwargs)

    return _inner_
