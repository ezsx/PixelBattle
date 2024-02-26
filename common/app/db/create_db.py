from psycopg import Cursor
from common.app.db.db_pool import get_pool_cur

# from app.core.db_pool

"""
The init_db function creates the necessary tables in the database if they don't already exist.
It executes a series of CREATE TABLE statements for the pixels, admins, and users tables.
Finally, it commits the changes to the database. 
"""


@get_pool_cur
async def init_db(cur: Cursor):
    for tbl in ('pixels', 'admins', 'users'):  # Убедитесь, что 'users' удаляется последним
        await cur.execute(f"""DROP TABLE IF EXISTS public.{tbl} CASCADE;""")

    await cur.execute("""
    CREATE EXTENSION IF NOT EXISTS pgcrypto;
    """)

    # Создание таблицы users
    await cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
        nickname VARCHAR(255) UNIQUE NOT NULL,
        is_banned BOOLEAN DEFAULT FALSE,
        last_pixel_update TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')  
    );
    """)

    # Создание таблицы pixels
    await cur.execute("""
    CREATE TABLE IF NOT EXISTS pixels (
        x INT NOT NULL,
        y INT NOT NULL,
        color VARCHAR(7) NOT NULL, -- Цвет в формате HEX, например, #FFFFFF
        user_id VARCHAR(36),
        last_updated TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
        action_time TIMESTAMP WITHOUT TIME ZONE,
        PRIMARY KEY (x, y),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    );
    """)

    # Создание таблицы admins
    await cur.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        id VARCHAR(36) PRIMARY KEY,
        username VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
    );
    """)

    await cur.execute("COMMIT;")
