import asyncio
import ssl
import websockets as client_websockets
from websockets.sync.client import connect
import json
from common.app.db.api_db import clear_db
from common.app.db.db_pool import init_pool
from common.app.core.config import config as cfg_c

uri = "ws://localhost:8000/ws/"  # адрес  WebSocket сервера


async def test_create_new_user():
    async with client_websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({"nickname": "NewUser"}))

        try:
            # Keep the connection open and handle incoming messages
            while True:
                response = await websocket.recv()
                print("Received from server:", response)

                # You can break the loop or continue based on certain conditions
                # if some_condition:
                #     break

        except client_websockets.exceptions.ConnectionClosedOK:
            print("Connection closed by the server")
        except client_websockets.exceptions.ConnectionClosedError as e:
            print(f"Connection closed with error: {e}")


async def test_new_user_without_user_id():
    async with client_websockets.connect(uri) as websocket:
        # Отправляем данные нового пользователя с nickname, но без user_id
        await websocket.send(json.dumps({"nickname": "NewUser"}))

        # Ожидаем ответа от сервера
        response = await websocket.recv()
        response_data = json.loads(response)
        # await websocket.close()

        print(f"Ответ сервера: {response}")
        # Проверяем, получен ли user_id в ответе
        assert "user_id" in response_data, "user_id не получен в ответе от сервера"



async def run_tests():
    # await test_create_new_user()
    await init_pool(cfg=cfg_c)
    await clear_db()
    await test_new_user_without_user_id()


asyncio.run(run_tests())
