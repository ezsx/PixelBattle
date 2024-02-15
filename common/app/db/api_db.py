from datetime import datetime
from psycopg import Cursor
from psycopg.types.uuid import UUID
from common.app.db.db_pool import get_pool_cur
from psycopg.rows import dict_row


@get_pool_cur
async def create_user(cur: Cursor, nickname: str) -> dict:
    cur.row_factory = dict_row
    await cur.execute("""
        INSERT INTO users (nickname) VALUES (%s)
        ON CONFLICT (nickname) DO NOTHING
        RETURNING id;
    """, (nickname,))
    return await cur.fetchone()


@get_pool_cur
async def create_user_with_id(cur: Cursor, nickname: str, user_id: UUID):
    cur.row_factory = dict_row
    await cur.execute("""
        INSERT INTO users (id, nickname) VALUES (%s, %s)
        ON CONFLICT (nickname) DO NOTHING
        RETURNING id;
    """, (user_id, nickname))
    return await cur.fetchone()


@get_pool_cur
async def update_user_nickname(cur: Cursor, user_id: UUID, new_nickname: str):
    await cur.execute("""
        UPDATE users SET nickname = %s WHERE id = %s;
    """, (new_nickname, user_id))


@get_pool_cur
async def get_user_by_id(cur: Cursor, user_id: UUID):
    cur.row_factory = dict_row
    await cur.execute("""
        SELECT id, nickname, is_banned FROM users WHERE id = %s;
    """, (user_id,))
    return await cur.fetchone()


@get_pool_cur
async def update_pixel(cur: Cursor, x: int, y: int, color: str, user_id: UUID, action_time: datetime):
    await cur.execute("""
        INSERT INTO pixels (x, y, color, user_id, action_time) VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (x, y) DO UPDATE
        SET color = CASE WHEN pixels.action_time < EXCLUDED.action_time THEN EXCLUDED.color ELSE pixels.color END,
            user_id = CASE WHEN pixels.action_time < EXCLUDED.action_time THEN EXCLUDED.user_id ELSE pixels.user_id END,
            action_time = CASE WHEN pixels.action_time < EXCLUDED.action_time THEN EXCLUDED.action_time ELSE pixels.action_time END;
    """, (x, y, color, user_id, action_time))


@get_pool_cur
async def get_pixels(cur: Cursor):
    cur.row_factory = dict_row
    await cur.execute("""
        SELECT x, y, color, user_id FROM pixels;
    """)
    return await cur.fetchall()


@get_pool_cur
async def ban_user(cur: Cursor, user_id: UUID):
    await cur.execute("""
        UPDATE users SET is_banned = TRUE WHERE id = %s;
    """, (user_id,))
