import pytest
import asyncio
import json
import websockets as client_websockets
from faker import Faker
from common.app.db.api_db import clear_db
from common.app.db.db_pool import init_pool
from common.app.core.config import config as cfg_c

uri = "ws://localhost:8000/ws/"
fake = Faker()


# to run this test, run the following command inside the pixel_battle_backend container:
# cd /root_app/backend/app/tests
# pytest websocket_users_sumulation_test.py


async def send_and_receive(websocket, message, expected_responses_count=100, timeout=2):
    print(f"Sending to server: {message}")  # Отправка сообщения серверу
    await websocket.send(message)

    responses = []
    start_time = asyncio.get_event_loop().time()

    while len(responses) < expected_responses_count and asyncio.get_event_loop().time() - start_time < timeout:
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=timeout)
            print(f"Received from server: {response}")  # Получение ответа от сервера
            responses.append(json.loads(response))
        except asyncio.TimeoutError:
            print("Timeout while waiting for response from server")  # Превышено время ожидания ответа от сервера
            break

    return responses


async def create_user_and_login(nickname):
    print(f"Attempting to create and login user with nickname: {nickname}")  # Попытка создания пользователя и входа
    async with client_websockets.connect(uri) as websocket:
        responses = await send_and_receive(websocket, json.dumps(
            {"type": "login", "data": {"nickname": nickname}}))
        user_id = responses[0]['data']
        print(f"User created and logged in with user_id: {user_id}")  # Пользователь создан и вошел
        await websocket.close()
        return user_id


async def perform_user_actions(user_id, nickname, x, y, color):
    print(f"User {nickname} (ID: {user_id}) performing actions")  # Пользователь выполняет действия
    async with client_websockets.connect(uri) as websocket:
        await send_and_receive(websocket,
                               json.dumps({"type": "login", "data": {"user_id": user_id, "nickname": nickname}}))
        await send_and_receive(websocket,
                               json.dumps({"type": "update_pixel", "data": {"x": x, "y": y, "color": color}}))
        await send_and_receive(websocket, json.dumps({"type": "get_field_state"}))
        print(f"User {nickname} completed actions")  # Действия пользователя завершены


@pytest.mark.asyncio
async def test_multiple_users_actions_simultaneously():
    await init_pool(cfg=cfg_c)
    await clear_db()

    async def user_workflow():
        # Генерация случайных данных для пользователя
        nickname = fake.user_name()
        color = f"#{fake.hex_color()[1:]}"  # Генерируем цвет
        x, y = fake.random_int(min=0, max=100), fake.random_int(min=0, max=100)

        # Регистрация пользователя и получение user_id
        user_id = await create_user_and_login(nickname)

        # Повторный вход с тем же user_id и выполнение действий
        await perform_user_actions(user_id, nickname, x, y, color)

    # Создание и запуск задач для 100 пользователей
    tasks = [user_workflow() for _ in range(10)]
    await asyncio.gather(*tasks)