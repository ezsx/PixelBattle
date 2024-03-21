import asyncio
import json
import websockets
import httpx
import pytest

from common.app.db.api_db import clear_db
from common.app.db.db_pool import init_pool
from common.app.core.config import config as cfg_c


# pytest /root_app/backend/app/tests/websocket_login_actions_admin_test.py
# or
# cd /root_app/backend/app/tests
# pytest websocket_login_actions_admin_test.py

async def send_and_receive(websocket, message, expected_responses_count=10, timeout=1):
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
        except websockets.exceptions.ConnectionClosed:
            print("Соединение было принудительно закрыто сервером")
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
                                     json={"username": "admin", "password": "password"})
        token_data = response.json()

        print(token_data)
        access_token = token_data["access_token"]
        print("Токен администратора получен:", access_token)

    # Подключение к WebSocket как администратор и бан пользователя
    async with websockets.connect(uri) as websocket:
        # Аутентификация с использованием токена
        await send_and_receive(websocket, json.dumps({
            "type": "login_admin",
            "data": access_token
        }), )

        await send_and_receive(websocket, json.dumps({
            "type": "get_field_state"
        }), )

        # Пример выполнения действий от имени администратора
        # Например, отправка сообщения об очистке пикселя

        # Получение информации о пикселе
        await send_and_receive(websocket, json.dumps({
            "type": "pixel_info_admin",
            "data": {"x": 10, "y": 20}
        }), )

        await send_and_receive(websocket, json.dumps({
            "type": "update_cooldown_admin",
            "data": 10
        }), )

        # отправка сообщения об очистке пикселя
        await send_and_receive(websocket, json.dumps({
            "type": "update_pixel_admin",
            "data": {"x": 10, "y": 20, "color": "#FFFFFF"}
        }), )

        # Бан пользователя
        await send_and_receive(websocket, json.dumps({
            "type": "toggle_ban_user_admin",
            "data": {"user_id": user_id}
        }), )

        # разбан пользователя
        await send_and_receive(websocket, json.dumps({
            "type": "toggle_ban_user_admin",
            "data": {"user_id": user_id}
        }), )

        await send_and_receive(websocket, json.dumps({
            "type": "get_field_state"
        }), )

        # Сброс игры
        await send_and_receive(websocket, json.dumps({
            "type": "reset_game_admin",
            "data": (64, 64)
        }), )
        # обрабатываем отключение админа
        await websocket.close()


@pytest.mark.asyncio
async def test_run():
    # TODO: исправить инициализацию пула базы
    await init_pool(cfg=cfg_c)
    await clear_db()
    await create_user_get_admin_token_and_ban_user()
