import asyncio
import ssl
import websockets
from websockets.sync.client import connect
import json

uri = "ws://localhost:8000/ws/"  # Замените на актуальный адрес вашего WebSocket сервера


async def test_create_new_user():
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({"nickname": "NewUser"}))

        try:
            # Keep the connection open and handle incoming messages
            while True:
                response = await websocket.recv()
                print("Received from server:", response)

                # You can break the loop or continue based on certain conditions
                # if some_condition:
                #     break

        except websockets.exceptions.ConnectionClosedOK:
            print("Connection closed by the server")
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"Connection closed with error: {e}")


async def test_authenticate_existing_user():
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({"nickname": "ExistingUser", "user_id": "existing-user-id"}))
        response = await websocket.recv()
        print("Ответ сервера для аутентификации существующего пользователя:", response)


async def test_update_nickname():
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({"nickname": "UpdatedUser", "user_id": "existing-user-id"}))
        response = await websocket.recv()
        print("Ответ сервера на обновление nickname:", response)


async def test_invalid_user_id():
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({"nickname": "UserWithInvalidID", "user_id": "invalid-user-id"}))
        response = await websocket.recv()
        print("Ответ сервера для невалидного user_id:", response)


async def run_tests():
    await test_create_new_user()
    # await test_authenticate_existing_user()
    # await test_update_nickname()
    # await test_invalid_user_id()


asyncio.run(run_tests())
