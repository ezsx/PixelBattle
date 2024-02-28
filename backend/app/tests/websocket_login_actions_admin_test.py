import asyncio
import json
import websockets
import httpx
import pytest

from common.app.db.api_db import clear_db
from common.app.db.db_pool import init_pool
from common.app.core.config import config as cfg_c

# pytest /root_app/backend/app/tests/websocket_login_actions_admin_test.py
async def send_and_receive(websocket, message, expected_responses_count, timeout=3):
    print(f"Отправлено на сервер: {message}")
    await websocket.send(message)

    responses = []
    start_time = asyncio.get_event_loop().time()

    while len(responses) < expected_responses_count and asyncio.get_event_loop().time() - start_time < timeout:
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=timeout)
            responses.append(json.loads(response))
            print(f"Received from server: {response}")
        except asyncio.TimeoutError:
            print("Превышено время ожидания ответа от сервера")
            break

    return responses


async def create_user_get_admin_token_and_ban_user():
    uri = "ws://localhost:8000/ws/"
    fastapi_server_url = "http://localhost:8000"

    # Создание пользователя через WebSocket
    async with websockets.connect(uri) as websocket:
        responses = await send_and_receive(websocket, json.dumps({"type": "login", "data": {"nickname": "NewUser"}}), 3)
        user_id = responses[0]['data']
        print("Пользователь создан с user_id:", user_id)
        # Создание пикселя
        message = {
            "type": "update_pixel",
            "data": {
                "x": 10,
                "y": 20,
                "color": '#FF5733'
            }
        }
        await send_and_receive(websocket, json.dumps(message), 0)

    # Получение токена администратора
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{fastapi_server_url}/admin/login",
                                     data={"username": "admin", "password": "password"})
        token_data = response.json()
        print(token_data)
        access_token = token_data["access_token"]
        print("Токен администратора получен:", access_token)

    # Подключение к WebSocket как администратор и бан пользователя
    async with websockets.connect(uri) as websocket:
        response = await send_and_receive(websocket, json.dumps({"type": "login_admin", "data": access_token}), 3)
        print("Ответы", response)
        await websocket.send(json.dumps({"type": "admin", "action": "ban_user", "user_id": user_id}))
        print(f"Пользователь {user_id} забанен")

        # Аутентификация с использованием токена
        await send_and_receive(websocket, json.dumps({
            "type": "admin",
            "data": access_token
        }), 0)

        # Пример выполнения действий от имени администратора
        # Например, отправка сообщения об очистке пикселя

        # Получение информации о пикселе
        await send_and_receive(websocket, json.dumps({
            "type": "pixel_info_admin",
            "data": {"x": 10, "y": 20}
        }), 1)

        # отправка сообщения об очистке пикселя
        await send_and_receive(websocket, json.dumps({
            "type": "update_pixel_admin",
            "data": {"x": 10, "y": 20, "color": "#FFFFFF"}
        }), 0)

        # Бан пользователя
        await send_and_receive(websocket, json.dumps({
            "type": "ban_user_admin",
            "data": {"user_id": "some-user-id"}
        }), 1)

        # Сброс игры
        await send_and_receive(websocket, json.dumps({
            "type": "reset_game_admin"
        }), 0)

        await send_and_receive(websocket, json.dumps({
            "type": "disconnect"
        }), 0)


@pytest.mark.asyncio
async def test_run():
    # TODO: исправить инициализацию пула базы
    await init_pool(cfg=cfg_c)
    await clear_db()
    await create_user_get_admin_token_and_ban_user()
