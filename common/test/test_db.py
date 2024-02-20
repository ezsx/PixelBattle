# import contextlib
# import io
# import pytest
# from common.app.db.api_db import create_user, update_pixel, clear_db, get_pixels
# from common.app.core.config import config as cfg_c
# from datetime import datetime
#
# import logging
#
# from common.app.db.db_pool import init_pool
#
# logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)
#
#
# # run test command, to run inside backend.docker container:
# # python -c "import common.test.test_db"
#
#
# @pytest.fixture
# async def setup_user():
#     # Создание тестового пользователя
#     await init_pool(cfg=cfg_c)
#     return await create_user("test_user")
#
#
# @pytest.mark.asyncio
# async def test_update_pixel(setup_user):
#     user = await setup_user
#     user_id = user['id']
#
#     x, y, color = 1, 1, "#FFFFFF"
#     action_time = datetime.utcnow()
#
#     # Создаем пиксель в бпзе данных
#     await update_pixel(x=x, y=y, color=color, user_id=user_id, action_time=action_time)
#
#     # Получаем записи с базы данных, о том что пиксель создан и с ним все ок.
#     responses = await get_pixels()
#     logger.info(f"result from test_update_pixel(): {responses}")
#
#     # Проверка, что в базе данных есть запись с ожидаемыми значениями
#     expected_response = [{'x': x, 'y': y, 'color': color.upper(), 'user_id': user_id}]
#     assert responses == expected_response, f"Expected {expected_response}, got {responses}"
#
#     await clear_db()
#
#
# """
# В этом примере весь вывод, который генерирует pytest, сначала перенаправляется в объект StringIO,
# а затем содержимое этого объекта выводится в консоль с помощью print.
# """
#
# f = io.StringIO()
# with contextlib.redirect_stdout(f):
#     pytest.main(["-rP"])
# output = f.getvalue()
# print(output)
