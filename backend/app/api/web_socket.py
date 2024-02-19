import asyncio
import json
import websockets.exceptions
from typing import List
from fastapi import WebSocket, FastAPI, Header, HTTPException
from fastapi.websockets import WebSocketDisconnect, WebSocketState
from common.app.db.api_db import get_pixels, update_pixel, get_user_by_id, create_user, update_user_nickname, \
    create_user_with_id
from datetime import datetime

app_ws = FastAPI()


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def broadcast(self, message: str):
        # print("DEBUG broadcast:", len(self.active_connections))
        # Создаем копию списка активных соединений, чтобы избежать изменения списка во время итерации
        connections = self.active_connections.copy()
        for connection in connections:
            if connection.application_state == WebSocketState.CONNECTED:
                try:
                    await connection.send_text(message)
                    print(f"Message sent to {connection.client}: {message}")  # DEBUG
                except Exception as e:
                    print(f"Error sending message: {e}")
                    # Удаляем соединение, если не удалось отправить сообщение
                    self.active_connections.remove(connection)

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"User connected: {websocket.client}")  # DEBUG
        await self.broadcast_online_count()

    async def disconnect(self, websocket: WebSocket, code=403, reason="Forbiden"):
        if websocket in self.active_connections:
            print(f"Disconnecting: {websocket.client}, Code: {code}, Reason: {reason}")  # DEBUG
            if websocket.application_state == WebSocketState.CONNECTED:
                await websocket.close(code=code, reason=reason)
            self.active_connections.remove(websocket)
            # print(f"User disconnected: {websocket.client}")  # DEBUG
            await self.broadcast_online_count()

    async def broadcast_online_count(self):
        online_count = len(self.active_connections)
        await self.broadcast(json.dumps({
            "type": "online_count",
            "data": {"online": online_count}
        }))


manager = ConnectionManager()


@app_ws.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    try:
        # Подключение пользователя к менеджеру соединений
        await manager.connect(websocket)

        # Ожидаем получение сообщения с данными пользователя
        auth_data = await websocket.receive_json()

        # Извлекаем nickname и user_id из полученного сообщения
        nickname = auth_data.get('nickname')
        user_id = auth_data.get('user_id')
        print("Server get from client data to authenticate:", nickname, " ___ ", user_id)
        if not nickname:
            # Обработка случая, когда nickname не предоставлен
            await manager.disconnect(websocket, code=4002, reason="Nickname is required")
            return

        if user_id:
            user = await get_user_by_id(user_id)
            if not user:
                # Обработка случая, когда пользователь с предоставленным user_id не найден
                await manager.disconnect(websocket, code=4003, reason="Invalid user_id, create a new account")
                return
            elif user['nickname'] != nickname:
                # Обновление nickname пользователя, если он отличается
                await update_user_nickname(user_id, nickname)
        else:
            # Создание нового пользователя, если user_id не предоставлен
            user = await create_user(nickname)
            user_id = user['id']
            await websocket.send_json({"type": "user_id", "data": f"{user_id}"})

        if user.get('is_banned'):
            # Обработка случая, когда пользователь забанен
            await websocket.send_json({"type": "banned"})
            await manager.disconnect(websocket, code=4001, reason="Banned")
            return

        # Отправка состояния игрового поля
        await send_field_state(websocket)
        # Отправка heartbeat сообщений
        await asyncio.create_task(websocket_heartbeat(websocket))

        while True:
            message = await websocket.receive_text()
            print(f"Message received from {websocket.client}: {message}")  # DEBUG
            message_data = json.loads(message)
            if message_data['type'] == 'update_pixel':
                await handle_update_pixel(message_data['data'], user_id)
            elif message_data['type'] == 'get_field_state':
                await send_field_state(websocket)
            elif message_data['type'] == 'disconnect':
                print("disconnect")
                await manager.disconnect(websocket, code=1000, reason="Closed")

    except BaseException:
        # ловим принудительное отключение конетка,
        # TODO: небезопасный код, ошибок вызывающих непредвиденное отключение, много
        # нужно разобраться как их всех ловить без BaseException.
        if websocket.application_state == WebSocketState.CONNECTED:
            await manager.disconnect(websocket, code=1000, reason="Closed")


async def websocket_heartbeat(websocket: WebSocket):
    while True:
        try:
            await asyncio.sleep(30)  # Периодическое отправление сообщения каждые 30 секунд
            await websocket.send_text(json.dumps({"type": "heartbeat"}))
        except Exception:
            break


#
# async def handle_user_connection(websocket: WebSocket, user_id: str):
#     user = await get_user_by_id(user_id)  # Функция из api_db.py для получения информации о пользователе
#     if user and user['is_banned']:
#         await websocket.send_text(json.dumps({"type": "banned"}))  # Опционально, сообщить пользователю о бане
#         await manager.disconnect(websocket, code=4001, reason="Banned")  # Код закрытия для забаненных пользователей
#         return
#     # Продолжение обработки подключения пользователя


async def handle_update_pixel(data, user_id):
    x = data['x']
    y = data['y']
    color = data['color']
    action_time_str = data.get('action_time')

    # Преобразование временной метки из строки в объект datetime
    action_time = datetime.fromisoformat(action_time_str) if action_time_str else datetime.utcnow()

    # Предполагается, что user_id уже является объектом UUID, если нет, его нужно преобразовать
    # user_id = UUID(user_id) if isinstance(user_id, str) else user_id

    print(f"Handling update_pixel: x={x}, y={y}, color={color}, user_id={user_id}, action_time={action_time}")

    await update_pixel(x=x, y=y, color=color, user_id=user_id, action_time=action_time)
    print("Pixel updated")


async def send_field_state(websocket):
    print(f"Sending field state to: {websocket.client}")
    field_state = await get_pixels()
    await websocket.send_text(json.dumps({
        "type": "field_state",
        "data": field_state
    }))
    print("Field state sent")
