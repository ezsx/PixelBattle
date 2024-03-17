import json
from datetime import datetime, timezone
from typing import List, Tuple, Optional

import starlette
from fastapi import WebSocket, FastAPI
from fastapi.websockets import WebSocketDisconnect
from jose import jwt, JWTError
from pydantic import ValidationError
from starlette.websockets import WebSocketState

from backend.app.prometheus.metrics import active_connections_gauge, ws_messages_sent, ws_messages_received
from common.app.db.api_db import get_pixels, update_pixel, get_user_by_id, create_user, update_user_nickname, \
    get_users_info, get_pixel_info, ban_user, clear_db_admin, get_admin_by_username
from common.app.core.config import config as cfg

from backend.app.schemas.schemas import (
    LoginRequest, AdminLoginRequest, ErrorResponse, UserInfoResponse,
    FieldStateResponse, OnlineCountResponse,
    PixelInfoRequest, BanUserRequest, ResetGameRequest, PixelInfoResponse, SuccessResponse,
    AuthResponse, PixelUpdateRequest, PixelUpdateNotification, FieldStateData
)

app_ws = FastAPI()


async def send_text_metric(websocket: WebSocket, data: str):
    """
    Отправка текстового сообщения через WebSocket и инкремент счетчика отправленных сообщений
    Тут можно брать метрику по любому событию, которое происходит в WebSocket,
    сообщения об ошибки в учет не идут
    :param websocket:
    :param data:
    :return:
    """
    ws_messages_sent.inc()  # Инкрементируем счетчик отправленных сообщений
    await websocket.send_text(data)


async def receive_text_metric(websocket: WebSocket) -> str:
    data = await websocket.receive_text()
    ws_messages_received.inc()  # Инкрементируем счетчик полученных сообщений
    return data


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[Tuple[WebSocket, str]] = []
        self.admin_connections: List[WebSocket] = []

    async def broadcast(self, message: str):
        connections = self.active_connections.copy()
        for connection, _ in connections:
            if connection.client_state == WebSocketState.CONNECTED:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    self.active_connections = [(conn, uid) for conn, uid in self.active_connections if
                                               conn != connection]  # filter out disconnected connections

    async def broadcast_to_admins(self, message: str):
        connections = self.admin_connections.copy()
        for admin in connections:
            if admin.client_state == WebSocketState.CONNECTED:
                try:
                    await admin.send_text(message)
                except Exception:
                    self.admin_connections = [adm for adm in self.admin_connections if adm != admin]

    async def connect(self, websocket: WebSocket, user_id: str):
        self.active_connections.append((websocket, user_id))
        active_connections_gauge.set(len(self.active_connections))
        await self.broadcast_online_count()
        await self.broadcast_users_info()

    async def disconnect(self, websocket: WebSocket, code=1000, reason="Normal Closure"):
        self.active_connections = [(conn, uid) for conn, uid in self.active_connections if conn != websocket]
        active_connections_gauge.set(len(self.active_connections))
        print(f"Disconnecting: Code: {code}, Reason: {reason}")
        await self.broadcast_online_count()
        await self.broadcast_users_info()

    async def broadcast_online_count(self):
        online_count = len(self.active_connections)
        await self.broadcast(OnlineCountResponse(type="online_count", data={"online": online_count}).json())

    async def broadcast_users_info(self):
        user_ids = [uid for _, uid in self.active_connections]
        if user_ids:
            users_info = await get_users_info(user_ids)
            await self.broadcast_to_admins(UserInfoResponse(type="users_online", data=users_info).json())

    async def broadcast_pixel(self, x: int, y: int, color: str, nickname: str):
        message = PixelUpdateNotification(type="pixel_update",
                                          data={"x": x, "y": y, "color": color, "nickname": nickname}).json()
        await self.broadcast(message)
        await self.broadcast_to_admins(message)

    async def disconnect_everyone(self):
        for connection, _ in self.active_connections:
            await connection.close(code=1001, reason="Going Away")
        for admin in self.admin_connections:
            await admin.close(code=1001, reason="Going Away")
        self.active_connections = []
        self.admin_connections = []


manager = ConnectionManager()


async def authenticate(websocket: WebSocket) -> Tuple[Optional[Tuple[str, str]], Tuple[int, str]]:
    try:
        auth_data = await websocket.receive_json()
        if auth_data['type'] == "login_admin":
            request = AdminLoginRequest(**auth_data)
            admin = await authenticate_admin(request.data)
            return (admin, (200, "admin")) if admin else (None, (1008, "Policy Violation"))

        elif auth_data['type'] == "login":
            request = LoginRequest(**auth_data)
            request = request.data
            if not request.nickname:
                await websocket.send_json(ErrorResponse(type="error", message="Nickname is required").dict())
                return None, (1002, "Protocol Error")

            user_id = request.user_id
            if user_id:
                user = await get_user_by_id(user_id)
                if not user:
                    await websocket.send_json(ErrorResponse(type="error", message="User not found").dict())
                    return None, (1002, "Protocol Error")
                elif user['nickname'] != request.nickname:
                    success = await update_user_nickname(user_id, request.nickname)
                    if not success:
                        await websocket.send_json(ErrorResponse(type="error", message="Nickname already exists").dict())
                        return None, (1002, "Protocol Error")
            else:
                user = await create_user(request.nickname)
                if not user:
                    await websocket.send_json(ErrorResponse(type="error", message="Nickname already exist").dict())
                    return None, (1002, "Protocol Error")
                user_id = user['id']
                await websocket.send_json(AuthResponse(type="user_id", data=user_id).dict())

            if user.get('is_banned'):
                await websocket.send_json(ErrorResponse(type="error", message="User is banned").dict())
                return None, (1002, "Protocol Error")

            return (request.nickname, user_id), (200, "user")
        else:
            await websocket.send_json(ErrorResponse(type="error", message="Unsupported login type").dict())
            return None, (1003, "Unsupported Data")

    except WebSocketDisconnect:
        return None, (1001, "Going Away")
    except ValidationError as e:
        await websocket.send_json(ErrorResponse(type="error", message=str(e)).dict())
        return None, (1011, "Internal Server Error")


async def authenticate_admin(token: str):
    try:
        payload = jwt.decode(token, cfg.SECRET_KEY, algorithms="HS256")
        nickname: str = payload.get("sub")
        expiration: int = payload.get("exp")

        current_time = datetime.now(timezone.utc).timestamp()
        if current_time > expiration:
            return None
        return nickname, await get_admin_by_username(nickname)

    except JWTError as e:
        print(f"JWTError: {e}")
        return None


@app_ws.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    user, response = await authenticate(websocket)
    try:
        if not (user and response[0] == 200):
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close(code=response[0], reason=response[1])
            return
        admin = True if response[1] == "admin" else False

        if admin:
            manager.admin_connections.append(websocket)
            await send_text_metric(websocket, SuccessResponse(data="Success login as admin").json())
        else:
            await manager.connect(websocket, user[1])
            await send_text_metric(websocket, SuccessResponse(data="Success login as user").json())
        await handle_send_field_state(websocket)
        while True:
            message = await receive_text_metric(websocket)
            await process_message(websocket, message, user, admin)

    except WebSocketDisconnect or starlette.websockets.WebSocketDisconnect:
        await manager.disconnect(websocket, code=1001, reason="Going Away")
    except RuntimeError as e:
        print(f"RuntimeError: {e}", flush=True)
        await manager.disconnect(websocket, code=1006, reason="Abnormal Closure")


async def process_message(websocket: WebSocket, message: str, user: Tuple[str, str], admin: bool = False):
    message_data = json.loads(message)
    message_type = message_data.get('type')

    try:
        match message_type:
            case 'disconnect':
                await manager.disconnect(websocket, code=1000, reason="Normal Closure")
            case 'update_pixel' | 'update_pixel_admin':
                permission_required = message_type == 'update_pixel_admin'
                if permission_required and not admin:
                    await websocket.send_text(
                        ErrorResponse(type="error", message="You have not permission").json())
                    return
                request = PixelUpdateRequest(**message_data)
                success = await handle_update_pixel(websocket, request, user, permission=admin)
                if success:
                    await manager.broadcast_pixel(request.data.x, request.data.y, request.data.color, user[0])
            case 'get_field_state':
                await handle_send_field_state(websocket)
            case _ if admin:
                await handle_admin_actions(websocket, message_type, message_data, user)
    except ValidationError as e:
        await send_text_metric(websocket, ErrorResponse(message=str(e)).json())


async def handle_admin_actions(websocket: WebSocket, message_type: str, message_data: dict, user: Tuple[str, str]):
    match message_type:
        case 'pixel_info_admin':
            request = PixelInfoRequest(**message_data)
            await handle_pixel_info(websocket, request)
        case 'ban_user_admin':
            request = BanUserRequest(**message_data)
            await handle_ban_user(websocket, request)
        case 'reset_game_admin':
            request = ResetGameRequest(**message_data)
            await handle_reset_game(websocket, request)
            await manager.disconnect_everyone()


async def handle_send_field_state(websocket: WebSocket):
    pixels = await get_pixels()
    print(pixels, flush=True)
    field_state_data = [FieldStateData(**pixel) for pixel in pixels]
    message = FieldStateResponse(type="field_state", size=cfg.FIELD_SIZE, data=field_state_data).json()
    await send_text_metric(websocket, message)


async def handle_update_pixel(websocket: WebSocket, request: PixelUpdateRequest, user: Tuple[str, str],
                              permission: bool = False) -> bool:
    if not (0 <= request.data.x < cfg.FIELD_SIZE[0] and 0 <= request.data.y < cfg.FIELD_SIZE[1]):
        await websocket.send_text(ErrorResponse(type="error", message="Invalid pixel coordinates").json())
        return False
    success = await update_pixel(x=request.data.x, y=request.data.y, color=request.data.color, user_id=user[1],
                                 action_time=datetime.utcnow(), permission=permission)
    if not success:
        await websocket.send_text(
            ErrorResponse(type="error", message="You can only color a pixel at a set time.").json())
        return False
    else:
        # await websocket.send_text(SuccessResponse(data="Pixel updated").json())
        return True


async def handle_pixel_info(websocket: WebSocket, request: PixelInfoRequest):
    data = await get_pixel_info(request.data['x'], request.data['y'])
    if data is None:
        await websocket.send_text(
            ErrorResponse(type="error", message="There is no one who past pixel there").json())
        return
    message = PixelInfoResponse(type="pixel_info", data=data).json()
    await send_text_metric(websocket, message)


async def handle_ban_user(websocket: WebSocket, request: BanUserRequest):
    await ban_user(request.data['user_id'])
    await send_text_metric(websocket, SuccessResponse(data="User banned").json())


async def handle_reset_game(websocket: WebSocket, request: ResetGameRequest):
    await clear_db_admin()
    cfg.FIELD_SIZE = request.data
    await send_text_metric(websocket, SuccessResponse(data="Game reset").json())
