import json
from datetime import datetime, timezone
from typing import List, Tuple, Optional, Dict

import starlette
from fastapi import WebSocket, FastAPI
from fastapi.websockets import WebSocketDisconnect
from jose import jwt, JWTError
from pydantic import ValidationError
from starlette.websockets import WebSocketState

from backend.app.prometheus.metrics import active_connections_gauge, ws_messages_sent, ws_messages_received
from common.app.db.api_db import get_pixels, update_pixel, get_user_by_id, create_user, update_user_nickname, \
    get_users_info, get_pixel_info, clear_db_admin, get_admin_by_username, toggle_ban_user
from common.app.core.config import config as cfg

from backend.app.schemas.schemas import (
    LoginRequest, AdminLoginRequest, ErrorResponse, UserInfoResponse,
    FieldStateResponse, OnlineCountResponse,
    PixelInfoRequest, BanUserRequest, ResetGameRequest, PixelInfoResponse, SuccessResponse,
    AuthResponse, PixelUpdateRequest, PixelUpdateNotification, FieldStateData, SelectionUpdateRequest,
    SelectionUpdateBroadcast, SelectionUpdateBroadcastData, Position, Pixel, Selection,
    ChangeCooldownResponse, ChangeCooldownRequest
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
        self.nicknames: Dict[WebSocket, str] = {}  # Словарь для хранения никнеймов
        self.selections: Dict[str, Position] = {}  # Словарь для хранения текущих выделений пользователей

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

    async def update_selection(self, nickname: str, position: Optional[Position]):
        if position:
            self.selections[nickname] = position
        else:
            self.selections.pop(nickname, None)
        await self.broadcast_selection_update(nickname, position)

    async def broadcast_selection_update(self, nickname: str, position: Optional[Position]):
        # Формирование и отправка броадкаста с обновлённым состоянием выделения
        broadcast_message = SelectionUpdateBroadcast(
            data=SelectionUpdateBroadcastData(
                nickname=nickname,
                position=position
            )
        )
        await self.broadcast(broadcast_message.json())
        await self.broadcast_to_admins(broadcast_message.json())

    async def connect(self, websocket: WebSocket, nickname: str, user_id: str):
        self.active_connections.append((websocket, user_id))
        active_connections_gauge.set(len(self.active_connections))
        self.nicknames[websocket] = nickname  # Сохраняем никнейм
        await self.broadcast_online_count()
        await self.broadcast_users_info()

    async def disconnect(self, websocket: WebSocket, code=1000, reason="Normal Closure"):
        nickname = self.nicknames.pop(websocket, None)
        self.active_connections = [(conn, uid) for conn, uid in self.active_connections if conn != websocket]
        active_connections_gauge.set(len(self.active_connections))
        if nickname:
            await self.broadcast_selection_update(nickname, None)

        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close(code=code, reason=reason)
                websocket.client_state = WebSocketState.DISCONNECTED
        except RuntimeError as e:
            print(f"RuntimeError: {e}", flush=True)
        await self.broadcast_online_count()
        await self.broadcast_users_info()

    async def broadcast_online_count(self):
        online_count = len(self.active_connections)
        await self.broadcast(OnlineCountResponse(data={"online": online_count}).json())

    async def broadcast_users_info(self):
        user_ids = [uid for _, uid in self.active_connections]
        if user_ids:
            users_info = await get_users_info(user_ids)
            await self.broadcast_to_admins(UserInfoResponse(data=users_info).json())

    async def broadcast_change_cooldown(self, data: int):
        await self.broadcast(ChangeCooldownResponse(data=data).json())
        await self.broadcast_to_admins(ChangeCooldownResponse(data=data).json())

    async def broadcast_pixel(self, x: int, y: int, color: str, nickname: str):
        message = PixelUpdateNotification(data={"x": x, "y": y, "color": color, "nickname": nickname}).json()
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
                await websocket.send_json(ErrorResponse(message="Nickname is required").dict())
                return None, (1002, "Protocol Error")

            user_id = request.user_id
            if user_id:
                user = await get_user_by_id(user_id)
                if not user:
                    await websocket.send_json(ErrorResponse(message="User not found").dict())
                    return None, (1002, "Protocol Error")
                elif user['nickname'] != request.nickname:
                    success = await update_user_nickname(user_id, request.nickname)
                    if not success:
                        await websocket.send_json(ErrorResponse(message="Nickname already exist").dict())
                        return None, (1002, "Protocol Error")
            else:
                user = await create_user(request.nickname)
                if not user:
                    await websocket.send_json(ErrorResponse(message="Nickname already exist").dict())
                    return None, (1002, "Protocol Error")
                user_id = user['id']
                await websocket.send_json(AuthResponse(data=user_id).dict())

            if user.get('is_banned'):
                await websocket.send_json(ErrorResponse(message="User is banned").dict())
                return None, (1002, "Protocol Error")

            return (request.nickname, user_id), (200, "user")
        else:
            await websocket.send_json(ErrorResponse(message="Unsupported login type").dict())
            return None, (1003, "Unsupported Data")

    except WebSocketDisconnect:
        return None, (1001, "Going Away")
    except ValidationError as e:
        await websocket.send_json(ErrorResponse(message=str(e)).dict())
        return None, (1011, "Internal Server Error")


async def authenticate_admin(token: str) -> Optional[Tuple[str, str]]:
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
    admin = False
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
            await manager.connect(websocket, user[0], user[1])
            await send_text_metric(websocket, SuccessResponse(data="Success login as user").json())
        while True:
            message = await receive_text_metric(websocket)
            await process_message(websocket, message, user, admin)

    except WebSocketDisconnect or starlette.websockets.WebSocketDisconnect:
        if admin is not False:
            manager.admin_connections = [adm for adm in manager.admin_connections if adm != websocket]
        else:
            await manager.disconnect(websocket, code=1001, reason="Going Away")
    except RuntimeError as e:
        print(f"RuntimeError: {e}", flush=True)
        if admin is not False:
            manager.admin_connections = [adm for adm in manager.admin_connections if adm != websocket]
        else:
            await manager.disconnect(websocket, code=1006, reason="Abnormal Closure")


async def process_message(websocket: WebSocket, message: str, user: Tuple[str, str], admin: bool = False):
    message_data = json.loads(message)
    message_type = message_data.get('type')

    try:
        match message_type:
            case 'disconnect':
                await manager.disconnect(websocket, code=1000, reason="Normal Closure")
            case 'update_pixel':
                request = PixelUpdateRequest(**message_data)
                await handle_update_pixel(websocket, request, user, permission=False)
            case 'update_selection':
                request = SelectionUpdateRequest(**message_data)
                await handle_selection_update(request, user)
            case 'get_field_state':
                await handle_send_field_state(websocket)
            case 'get_online_count':
                await handle_online_count(websocket)
            case 'get_cooldown':
                await send_text_metric(websocket, ChangeCooldownResponse(data=cfg.COOLDOWN).json())
            case _ if admin:
                await process_admin_message(websocket, message_type, message_data, user)
    except ValidationError as e:
        await send_text_metric(websocket, ErrorResponse(message=str(e)).json())


async def process_admin_message(websocket: WebSocket, message_type: str, message_data: dict, user: Tuple[str, str]):
    match message_type:
        case 'update_pixel_admin':
            request = PixelUpdateRequest(**message_data)
            await handle_update_pixel(websocket, request, user, permission=True)
        case 'pixel_info_admin':
            request = PixelInfoRequest(**message_data)
            await handle_pixel_info(websocket, request)
        case 'toggle_ban_user_admin':
            request = BanUserRequest(**message_data)
            await handle_ban_user(websocket, request)
        case 'update_cooldown_admin':
            request = ChangeCooldownRequest(**message_data)
            await handle_change_cooldown(request.data)
            await send_text_metric(websocket, SuccessResponse(data="Cooldown changed").json())
        case 'reset_game_admin':
            request = ResetGameRequest(**message_data)
            await handle_reset_game(websocket, request)
            await manager.disconnect_everyone()


async def handle_online_count(websocket: WebSocket):
    online_count = len(manager.active_connections)
    await send_text_metric(websocket, OnlineCountResponse(data={"online": online_count}).json())


async def handle_change_cooldown(data: int):
    cfg.COOLDOWN = data
    await manager.broadcast_change_cooldown(data)


async def handle_selection_update(request: SelectionUpdateRequest, user: Tuple[str, str]):
    await manager.update_selection(user[0], request.data.position)


async def handle_send_field_state(websocket: WebSocket):
    field_size = cfg.FIELD_SIZE
    cooldown = cfg.COOLDOWN

    raw_pixels = await get_pixels()
    raw_selections = manager.selections

    pixels = [Pixel(position=Position(**pixel), color=pixel["color"], nickname=pixel["nickname"]) for pixel in
              raw_pixels]
    selections = [Selection(nickname=nickname, position=position) for nickname, position in raw_selections.items()]

    field_state_data = FieldStateData(pixels=pixels, selections=selections)
    message = FieldStateResponse(size=field_size, cooldown=cooldown, data=field_state_data).json()
    await websocket.send_text(message)


async def handle_update_pixel(websocket: WebSocket, request: PixelUpdateRequest, user: Tuple[str, str],
                              permission: bool = False):
    if not (0 <= request.data.x < cfg.FIELD_SIZE[0] and 0 <= request.data.y < cfg.FIELD_SIZE[1]):
        await websocket.send_text(ErrorResponse(message="Invalid pixel coordinates").json())
    message = await update_pixel(x=request.data.x, y=request.data.y, color=request.data.color, user_id=user[1],
                                 action_time=datetime.utcnow(), permission=permission)
    if message == "cooldown":
        await websocket.send_text(
            ErrorResponse(message="You can only color a pixel at a set time.").json())
    else:
        await manager.broadcast_pixel(request.data.x, request.data.y, request.data.color, user[0])


async def handle_pixel_info(websocket: WebSocket, request: PixelInfoRequest):
    data = await get_pixel_info(request.data['x'], request.data['y'])
    if data is None:
        await websocket.send_text(
            ErrorResponse(message="There is no one who past pixel there").json())
        return
    message = PixelInfoResponse(data=data).json()
    await send_text_metric(websocket, message)


async def handle_ban_user(websocket: WebSocket, request: BanUserRequest):
    await toggle_ban_user(request.data['user_id'])
    for connection, user_id in manager.active_connections:
        if user_id == request.data['user_id']:
            await manager.disconnect(connection, code=1002, reason="Protocol Error")
    await send_text_metric(websocket, SuccessResponse(data="User ban toggled").json())


async def handle_reset_game(websocket: WebSocket, request: ResetGameRequest):
    await clear_db_admin()
    cfg.FIELD_SIZE = request.data
    await send_text_metric(websocket, SuccessResponse(data="Game reset").json())
