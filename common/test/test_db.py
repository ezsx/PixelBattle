import pytest
from unittest.mock import AsyncMock, MagicMock
from common.app.db.api_db import get_pixels, update_pixel, get_user_by_id, create_user, update_user_nickname, \
    create_user_with_id
import sys
import contextlib
import io



"""
Мокирование асинхронного курсора: Создается мок-объект для асинхронного курсора базы данных с замокированным методом
execute. Это позволяет имитировать выполнение SQL-запросов без реального взаимодействия с базой данных.

Мокирование декоратора get_pool_cur: Мокируется декоратор get_pool_cur, который обычно предоставляет курсор
к базе данных. Вместо реального курсора декоратор возвращает замокированный курсор.

Вызов тестируемой функции: Функция update_pixel вызывается с тестовыми параметрами.

Проверка вызова метода execute: С помощью assert_awaited_once_with проверяется, что метод execute мок-курсора
был вызван ровно один раз с ожидаемыми параметрами SQL-запроса и его аргументами.

Запустите тесты с помощью команды pytest в терминале из корневой директории вашего проекта:

pytest test_db.py

pytest автоматически найдет и выполнит тесты в указанном файле.
"""


# run test command, to run inside backend.docker container:
# python -c "import common.test.test_db"
@pytest.mark.asyncio
async def test_update_pixel(mocker):
    # Мокаем курсор и его метод execute
    mock_cursor = AsyncMock()
    mock_cursor.execute = AsyncMock()

    # Мокаем декоратор get_pool_cur, чтобы он возвращал мок-курсор
    mocker.patch('common.app.db.db_pool.get_pool_cur', return_value=mock_cursor)

    # Параметры для тестирования функции
    x, y, color, user_id, action_time = 1, 1, "#FFFFFF", "your-uuid", "2022-01-01T00:00:00"

    # Вызов тестируемой функции
    await update_pixel(x=x, y=y, color=color, user_id=user_id, action_time=action_time)

    # Проверка, что функция execute вызывалась с правильными аргументами
    mock_cursor.execute.assert_awaited_once_with("""
        INSERT INTO pixels (x, y, color, user_id, action_time) VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (x, y) DO UPDATE
        SET color = CASE WHEN pixels.action_time < EXCLUDED.action_time THEN EXCLUDED.color ELSE pixels.color END,
            user_id = CASE WHEN pixels.action_time < EXCLUDED.action_time THEN EXCLUDED.user_id ELSE pixels.user_id END,
            action_time = CASE WHEN pixels.action_time < EXCLUDED.action_time THEN EXCLUDED.action_time ELSE pixels.action_time END;
    """, (x, y, color, user_id, action_time))

    # Для функций, возвращающих результаты, можно проверить возвращаемое значение
    # assert result == ожидаемый_результат


"""
В этом примере весь вывод, который генерирует pytest, сначала перенаправляется в объект StringIO,
а затем содержимое этого объекта выводится в консоль с помощью print.
"""

f = io.StringIO()
with contextlib.redirect_stdout(f):
    pytest.main()
output = f.getvalue()
print(output)
