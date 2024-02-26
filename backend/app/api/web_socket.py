import json
from datetime import datetime, timezone
from typing import List, Tuple, Optional

from fastapi import WebSocket, FastAPI
from fastapi.websockets import WebSocketDisconnect
from jose import jwt, JWTError
from starlette.websockets import WebSocketState

from common.app.db.api_db import get_pixels, update_pixel, get_user_by_id, create_user, update_user_nickname
from common.app.core.config import config as cfg

app_ws = FastAPI()


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.admin_connections: List[WebSocket] = []

    async def broadcast(self, message: str):
        # print("DEBUG broadcast:", len(self.active_connections)) # DEBUG
        # Создаем копию списка активных соединений, чтобы избежать изменения списка во время итерации
        connections = self.active_connections.copy()
        for connection in connections:
            if connection.client_state == WebSocketState.CONNECTED:
                try:
                    await connection.send_text(message)
                    print(f"Message sent to {connection.client}: {message}")  # DEBUG
                except Exception as e:
                    print(f"Error sending message: {e}")
                    # Удаляем соединение, если не удалось отправить сообщение
                    self.active_connections.remove(connection)

    async def connect(self, websocket: WebSocket):
        self.active_connections.append(websocket)
        print(f"User connected: {websocket.client}")  # DEBUG
        await self.broadcast_online_count()

    async def disconnect(self, websocket: WebSocket, code=1000, reason="Normal Closure"):
        if websocket in self.active_connections:
            print(f"Disconnecting: {websocket.client}, Code: {code}, Reason: {reason}")  # DEBUG
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


async def authenticate(websocket: WebSocket) -> Tuple[Optional[str], Tuple[int, str]]:
    try:
        # Ожидаем получение сообщения с данными пользователя
        auth_data = await websocket.receive_json()
        if auth_data.get('type') == "admin":
            token = auth_data.get('data')
            admin = await authenticate_admin_websocket(token)
            return (admin, (200, "admin")) if admin else (admin, (1008, "Policy Violation"))

            # Проверяем тип сообщения
        if auth_data.get('type') != "login":
            return None, (1003, "Unsupported Data")

        # Извлекаем nickname и user_id из полученного сообщения
        # TODO исправить на 'type'
        nickname = auth_data.get('nickname')
        user_id = auth_data.get('user_id')

        if not nickname:
            # Обработка случая, когда nickname не предоставлен
            return None, (1002, "Protocol Error")

        if user_id:
            user = await get_user_by_id(user_id)
            if not user:
                # Пользователь с предоставленным user_id не найден
                return None, (1002, "Protocol Error")
            elif user['nickname'] != nickname:
                # Обновление nickname пользователя, если он отличается
                await update_user_nickname(user_id, nickname)
        else:
            # Создание нового пользователя, если user_id не предоставлен
            user = await create_user(nickname)
            user_id = user['id']
            await websocket.send_json({"type": "user_id", "data": f"{user_id}"})

        if user.get('is_banned'):
            # Пользователь забанен
            return None, (1002, "Protocol Error")  # Использование кода ошибки протокола для запрещенного доступа

        return user_id, (200, "user")

    except WebSocketDisconnect:
        return None, (1001, "Going Away")


async def authenticate_admin_websocket(token: str):
    try:
        payload = jwt.decode(token, cfg.SECRET_KEY, algorithms="HS256")
        username: str = payload.get("sub")
        expiration: int = payload.get("exp")
        issue_time: int = payload.get("iat")

        # Проверка срока действия токена
        current_time = datetime.now(timezone.utc).timestamp()
        if current_time > expiration:
            return None  # Токен просрочен

        # Тут можно добавить дополнительные проверки, если нужно

        return username

    except JWTError as e:
        print(f"JWTError: {e}")
        return None


@app_ws.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    user_id, response = await authenticate(websocket)

    if not (user_id and response[0] == 200):
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=response[0], reason=response[1])
        return
    if response[1]=="admin":
        pass
        #TODO подключаем как admin
    # если все ок, подключаем пользователя
    await manager.connect(websocket)

    await send_field_state(websocket)

    try:
        while True:
            message = await websocket.receive_text()
            message_data = json.loads(message)
            if message_data['type'] == 'update_pixel':
                success = await handle_update_pixel(message_data['data'], user_id)
                if not success:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "You can only color a pixel at a set time."
                    }))
            elif message_data['type'] == 'get_field_state':
                await send_field_state(websocket)
            elif message_data['type'] == 'disconnect':
                await manager.disconnect(websocket, code=1000, reason="Normal Closure")

    except WebSocketDisconnect:
        await manager.disconnect(websocket, code=1001, reason="Going Away")


async def handle_update_pixel(data, user_id):
    x = data['x']
    y = data['y']
    color = data['color']

    # Установка временной метки на сервере
    action_time = datetime.utcnow()

    # # Преобразование временной метки из строки в объект datetime
    # action_time = datetime.fromisoformat(action_time_str) if action_time_str else datetime.utcnow()

    # Предполагается, что user_id уже является объектом UUID, если нет, его нужно преобразовать
    # user_id = UUID(user_id) if isinstance(user_id, str) else user_id

    print(f"Handling update_pixel: x={x}, y={y}, color={color}, user_id={user_id}, action_time={action_time}")
    success = await update_pixel(x=x, y=y, color=color, user_id=user_id, action_time=action_time)
    print("Pixel updated")
    return success


async def send_field_state(websocket):
    print(f"Sending field state to: {websocket.client}")
    field_state = await get_pixels()
    await websocket.send_text(json.dumps({
        "type": "field_state",
        "data": field_state
    }))
    print("Field state sent")
