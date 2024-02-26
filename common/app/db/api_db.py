from datetime import datetime
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
async def update_pixel(cur: Cursor, x: int, y: int, color: str, user_id: str, action_time: datetime):
    print("update_pixel_database_func: Updating pixel")
    # Сначала проверяем, когда пользователь последний раз обновлял пиксель
    cur.row_factory = dict_row
    user = await cur.execute("""
            SELECT last_pixel_update FROM users WHERE id = %s;
        """, (user_id,))
    user = await cur.fetchone()

    if user and (action_time - user['last_pixel_update']).total_seconds() < 300:  # 5 минут = 300 секунд
        print("Too soon to update the pixel again.")
        return False  # Или другая логика для обработки слишком частых обновлений

    # Обновление пикселя и времени последнего обновления пользователя
    await cur.execute("""
        INSERT INTO pixels (x, y, color, user_id, action_time) VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (x, y) DO UPDATE
        SET color = CASE WHEN pixels.action_time < EXCLUDED.action_time THEN EXCLUDED.color ELSE pixels.color END,
            user_id = CASE WHEN pixels.action_time < EXCLUDED.action_time THEN EXCLUDED.user_id ELSE pixels.user_id END,
            action_time = CASE WHEN pixels.action_time < EXCLUDED.action_time THEN EXCLUDED.action_time ELSE pixels.action_time END;
    """, (x, y, color, user_id, action_time))

    # Обновляем время
    await cur.execute("""
               UPDATE users SET last_pixel_update = NOW() AT TIME ZONE 'utc' WHERE id = %s;
           """, (user_id,))
    print("update_pixel_database_func: pixel updated")
    return True


# TODO: на данный момент возразаются просто все записи о состоянии поля.
# Структуры как таковой нет, нужно согласовать с фронтом
@get_pool_cur
async def get_pixels(cur: Cursor):
    cur.row_factory = dict_row
    await cur.execute("""
        SELECT x, y, color, user_id FROM pixels;
    """)
    return await cur.fetchall()





@get_pool_cur
async def save_admin_token(cur: Cursor, username: str, token: str, expires: datetime):
    await cur.execute("""
        UPDATE admins SET token = %s, token_expires = %s WHERE username = %s;
    """, (token, expires, username))

@get_pool_cur
async def ban_user(cur: Cursor, user_id: UUID):
    await cur.execute("""
        UPDATE users SET is_banned = TRUE WHERE id = %s;
    """, (user_id,))


