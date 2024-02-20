import asyncio
import json
import websockets as client_websockets
from common.app.db.api_db import clear_db
from common.app.db.db_pool import init_pool
from common.app.core.config import config as cfg_c
from datetime import datetime

uri = "ws://localhost:8000/ws/"  # адрес WebSocket сервера


# run test command, to run inside backend.docker container:
# python -c "import backend.app.tests.test_websocket"

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


async def create_user_and_login():
    async with client_websockets.connect(uri) as websocket:
        # Создание пользователя
        responses = await send_and_receive(websocket, json.dumps({"nickname": "NewUser"}), expected_responses_count=3)
        user_id = responses[0]['data']  # Получаем user_id из ответа сервера

        # Повторное подключение для входа пользователя
        await websocket.close()
        return user_id


async def perform_user_actions(user_id):
    async with client_websockets.connect(uri) as websocket:
        # Вход пользователя
        await send_and_receive(websocket, json.dumps({"user_id": user_id, "nickname": "NewUser"}),
                               expected_responses_count=2)

        # Создание пикселя
        message = {
            "type": "update_pixel",
            "data": {
                "x": 10,
                "y": 20,
                "color": '#FF5733',
                "action_time": datetime.utcnow().isoformat()  # Добавляем временную метку в формате ISO
            }
        }
        await send_and_receive(websocket, json.dumps(message), expected_responses_count=0)

        # Получение состояния пикселей
        await send_and_receive(websocket, json.dumps({"type": "get_field_state"}), expected_responses_count=1)


async def run_tests():
    # TODO: исправить инициализацию пула базы
    await init_pool(cfg=cfg_c)
    await clear_db()

    user_id = await create_user_and_login()
    await perform_user_actions(user_id)


asyncio.run(run_tests())
