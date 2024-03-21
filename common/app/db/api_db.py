from datetime import datetime
from typing import List
from common.app.core.config import config as cfg

from psycopg import Cursor
from psycopg.types.uuid import UUID
from common.app.db.db_pool import get_pool_cur
from psycopg.rows import dict_row


@get_pool_cur
async def clear_db(cur: Cursor):
    # Удаление всех записей из таблиц, начиная с таблицы, не имеющей внешних ключей
    await cur.execute("DELETE FROM pixels;")
    await cur.execute("DELETE FROM admins;")
    await cur.execute("DELETE FROM users;")

    await cur.execute("COMMIT;")


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
    # Проверяем, существует ли уже пользователь с таким никнеймом
    await cur.execute("""
        SELECT id FROM users WHERE nickname = %s;
    """, (new_nickname,))
    if await cur.fetchone():
        # Если найден пользователь с таким никнеймом, возвращаем ошибку
        return False

    # Если никнейм уникален, обновляем его для пользователя
    await cur.execute("""
        UPDATE users SET nickname = %s WHERE id = %s;
    """, (new_nickname, user_id))
    return True


@get_pool_cur
async def get_user_by_id(cur: Cursor, user_id: UUID):
    cur.row_factory = dict_row
    await cur.execute("""
        SELECT id, nickname, is_banned FROM users WHERE id = %s;
    """, (user_id,))
    return await cur.fetchone()


@get_pool_cur
async def get_admin_by_username(cur: Cursor, username: str):
    cur.row_factory = dict_row
    await cur.execute("""
        SELECT id FROM admins WHERE username = %s;
    """, (username,))
    return await cur.fetchone()


@get_pool_cur
async def update_pixel(cur: Cursor, x: int, y: int, color: str, user_id: str, action_time: datetime,
                       permission: bool = False) -> str:
    # Сначала проверяем, когда пользователь последний раз обновлял пиксель
    cur.row_factory = dict_row
    await cur.execute("""
        SELECT last_pixel_update FROM users WHERE id = %s;
    """, (user_id,))
    user = await cur.fetchone()

    # Проверяем, было ли предыдущее обновление и прошло ли с тех пор COOLDOWN
    if not permission:
        if user and user['last_pixel_update'] and (
                action_time - user['last_pixel_update']).total_seconds() < cfg.COOLDOWN:
            return "cooldown"

    # Если last_pixel_update NULL или прошло более 5 минут, обновляем пиксель
    await cur.execute("""
        INSERT INTO pixels (x, y, color, user_id, action_time) VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (x, y) DO UPDATE
        SET color = CASE WHEN pixels.action_time < EXCLUDED.action_time THEN EXCLUDED.color ELSE pixels.color END,
            user_id = CASE WHEN pixels.action_time < EXCLUDED.action_time THEN EXCLUDED.user_id ELSE pixels.user_id END,
            action_time = CASE WHEN pixels.action_time < EXCLUDED.action_time THEN EXCLUDED.action_time ELSE pixels.action_time END;
    """, (x, y, color, user_id, action_time))

    # Обновляем время последнего обновления для пользователя
    if not permission:
        await cur.execute("""
            UPDATE users SET last_pixel_update = %s WHERE id = %s;
        """, (action_time, user_id,))
    return "ok"


# TODO: на данный момент возразаются просто все записи о состоянии поля.
# Структуры как таковой нет, нужно согласовать с фронтом
@get_pool_cur
async def get_pixels(cur: Cursor) -> List[dict]:
    cur.row_factory = dict_row
    await cur.execute("""
        SELECT p.x, p.y, p.color, u.nickname
        FROM pixels p
        JOIN users u ON p.user_id = u.id;
    """)
    return await cur.fetchall()


@get_pool_cur
async def create_admin(cur: Cursor, username: str, password_hash: str):
    # создаем админа если его еще нет, а если есть то ничего не делаем
    await cur.execute("""
        INSERT INTO admins (username, password_hash) VALUES (%s, %s)
        ON CONFLICT (username) DO NOTHING;
    """, (username, password_hash))


@get_pool_cur
async def toggle_ban_user(cur: Cursor, user_id: UUID):
    await cur.execute("""
        UPDATE users SET is_banned = NOT is_banned WHERE id = %s;
    """, (user_id,))



@get_pool_cur
async def get_users_info(cur: Cursor, user_ids: List[str]) -> List[dict]:
    cur.row_factory = dict_row
    await cur.execute("""
        SELECT id, nickname FROM users WHERE id = ANY(%s);
    """, (user_ids,))
    return await cur.fetchall()


@get_pool_cur
async def get_pixel_info(cur: Cursor, x: int, y: int) -> dict:
    cur.row_factory = dict_row
    await cur.execute("""
        SELECT p.x, p.y, p.color, p.user_id, u.nickname
        FROM pixels p
        LEFT JOIN users u ON p.user_id = u.id
        WHERE p.x = %s AND p.y = %s;
    """, (x, y))
    return await cur.fetchone()


@get_pool_cur
async def get_users_info(cur: Cursor, user_ids: List[str]) -> List[dict]:
    cur.row_factory = dict_row
    await cur.execute("""
        SELECT id, nickname FROM users WHERE id = ANY(%s);
    """, (user_ids,))
    return await cur.fetchall()


@get_pool_cur
async def clear_db_admin(cur: Cursor):
    # Удаление всех записей из таблиц, начиная с таблицы, не имеющей внешних ключей
    await cur.execute("DELETE FROM pixels;")
    # await cur.execute("DELETE FROM admins;")
    await cur.execute("DELETE FROM users;")

    await cur.execute("COMMIT;")
