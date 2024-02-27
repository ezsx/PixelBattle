import json
from datetime import datetime, timezone
from typing import List, Tuple, Optional

from fastapi import WebSocket, FastAPI
from fastapi.websockets import WebSocketDisconnect
from jose import jwt, JWTError
from starlette.websockets import WebSocketState

from common.app.db.api_db import get_pixels, update_pixel, get_user_by_id, create_user, update_user_nickname, \
    get_admin_by_id, get_users_info, get_pixel_info, ban_user, clear_db_admin
from common.app.core.config import config as cfg

app_ws = FastAPI()


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[Tuple[WebSocket, str]] = []
        self.admin_connections: List[WebSocket] = []

    async def broadcast(self, message: str):
        # print("DEBUG broadcast:", len(self.active_connections)) # DEBUG
        # Создаем копию списка активных соединений, чтобы избежать изменения списка во время итерации
        connections = self.active_connections.copy()
        for connection, user_id in connections:
            if connection.client_state == WebSocketState.CONNECTED:
                try:
                    await connection.send_text(message)
                    print(f"Message sent to {connection.client}: {message}")  # DEBUG
                except Exception as e:
                    print(f"Error sending message: {e}")
                    # Удаляем соединение, если не удалось отправить сообщение
                    self.active_connections.remove((connection, user_id))

    async def connect(self, websocket: WebSocket, user_id: str):
        self.active_connections.append((websocket, user_id))
        print(f"User connected: {websocket.client, user_id}")  # DEBUG
        await self.broadcast_online_count()
        await self.broadcast_users_info()  # Обновить информацию об активных пользователях

    async def disconnect(self, websocket: WebSocket, code=1000, reason="Normal Closure"):
        # Найти и удалить кортеж с данным WebSocket из списка активных соединений
        for connection, user_id in self.active_connections:
            if connection == websocket:
                print(f"Disconnecting: {user_id}, Code: {code}, Reason: {reason}")  # Используйте user_id
                self.active_connections.remove((connection, user_id))
                break
        await self.broadcast_online_count()
        await self.broadcast_users_info()  # Обновить информацию об активных пользователях

    async def broadcast_online_count(self):
        online_count = len(self.active_connections)
        await self.broadcast(json.dumps({
            "type": "online_count",
            "data": {"online": online_count}
        }))

    async def broadcast_to_admins(self, message: str):
        # Отправка сообщения всем администраторам
        for admin in self.admin_connections:
            if admin.client_state == WebSocketState.CONNECTED:
                try:
                    await admin.send_text(message)
                except Exception as e:
                    print(f"Error sending message to admin: {e}")
                    self.admin_connections.remove(admin)

    async def broadcast_users_info(self):
        # Извлечение списка user_id из активных соединений
        user_ids = [user_id for _, user_id in self.active_connections if user_id]

        if not user_ids:
            return  # Если нет активных пользователей, выходим из функции

        # Получение информации о пользователях из базы данных
        users_info = await get_users_info(user_ids)

        # Отправка информации администраторам
        await self.broadcast_to_admins(json.dumps({
            "type": "users_online",
            "data": users_info
        }))


manager = ConnectionManager()


async def authenticate(websocket: WebSocket) -> Tuple[Optional[str], Tuple[int, str]]:
    try:
        # Ожидаем получение сообщения с данными пользователя
        auth_data = await websocket.receive_json()
        if auth_data.get('type') == "login_admin":
            token = auth_data.get('data')
            admin = await authenticate_admin(token)
            return (admin, (200, "admin")) if admin else (admin, (1008, "Policy Violation"))


        if auth_data.get('type') != "login":
            return None, (1003, "Unsupported Data")
        auth_data = auth_data.get('data')
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


async def authenticate_admin(token: str):
    try:
        payload = jwt.decode(token, cfg.SECRET_KEY, algorithms="HS256")
        username: str = payload.get("sub")
        expiration: int = payload.get("exp")
        # issue_time: int = payload.get("iat")

        # Проверка срока действия токена
        current_time = datetime.now(timezone.utc).timestamp()
        if current_time > expiration:
            return None  # Токен просрочен

        # Тут можно добавить дополнительные проверки, если нужно

        return await get_admin_by_id(username)

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

    admin = True if response[1] == "admin" else False

    # если все ок, подключаем пользователя или админа

    if admin:
        manager.admin_connections.append(websocket)
    else:
        await manager.connect(websocket, user_id)

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

            # Зона администратора
            if admin:
                if message_data['type'] == 'update_pixel_admin':
                    data = message_data['data']
                    data['color'] = '#FFFFFF' if not data['color'] else data['color'] # цвет или белый цвет для очистки пикселя
                    await handle_update_pixel(data, user_id)

                elif message_data['type'] == 'pixel_info_admin':
                    x, y = message_data['data']['x'], message_data['data']['y']
                    pixel_info = await get_pixel_info(x, y)
                    await websocket.send_text(json.dumps({
                        "type": "pixel_info",
                        "data": pixel_info
                    }))

                elif message_data['type'] == 'ban_user_admin':
                    user_id = message_data['data']['user_id']
                    await ban_user(user_id)

                elif message_data['type'] == 'reset_game_admin':
                    await clear_db_admin()


            # обработка добровольного отключения
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
    print(f"Pixel updated: {success}")
    return success


async def send_field_state(websocket):
    print(f"Sending field state to: {websocket.client}")
    field_state = await get_pixels()
    await websocket.send_text(json.dumps({
        "type": "field_state",
        "data": field_state
    }))
    print("Field state sent")
