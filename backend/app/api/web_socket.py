import json
from typing import Tuple

import starlette
from fastapi import WebSocket, FastAPI
from fastapi.websockets import WebSocketDisconnect
from pydantic import ValidationError
from starlette.websockets import WebSocketState

from backend.app.api.websocket_core.authenticate import authenticate
from backend.app.api.websocket_core.connection_manager import manager
from backend.app.api.websocket_core.handlers import (
    handle_update_pixel, handle_selection_update, handle_send_field_state, handle_online_count,
    handle_change_cooldown, handle_pixel_info, handle_ban_user, handle_reset_game, handle_disconnect,
    handle_send_cooldown,
)
from backend.app.api.websocket_core.metrics_handler import send_text_metric, receive_text_metric
from backend.app.schemas.admin.admin_requests import AdminPixelUpdateRequest, AdminPixelInfoRequest, \
    AdminBanUserRequest, AdminChangeCooldownRequest, AdminResetGameRequest
from backend.app.schemas.user.user_requests import PixelUpdateRequest, SelectionUpdateRequest, DisconnectRequest
from backend.app.schemas.user.user_respones import SuccessResponse, ErrorResponse

app_ws = FastAPI()


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

    except (WebSocketDisconnect, starlette.websockets.WebSocketDisconnect, RuntimeError) as e:
        message_reason = "Normal Closure" if not isinstance(e, RuntimeError) else "Abnormal Closure"
        message_code = 1000 if not isinstance(e, RuntimeError) else 1006
        print(f"Websocket disconnected: {e}" if not isinstance(e, RuntimeError) else f"RuntimeError: {e}", flush=True)
        if admin is not False:
            manager.admin_connections = [adm for adm in manager.admin_connections if adm != websocket]
        else:
            await manager.disconnect(websocket, code=message_code, reason=message_reason)


async def process_message(websocket: WebSocket, message: str, user: Tuple[str, str], admin: bool = False):
    message_data = json.loads(message)
    message_type = message_data.get('type')

    async def access_denied(ws: WebSocket):
        await ws.send_text(ErrorResponse(message="Access denied").json())

    # Словарь обработчиков сообщений
    message_handlers = {
        "disconnect": lambda ws, md, u: handle_disconnect(ws, DisconnectRequest(**md)),
        "update_pixel": lambda ws, md, u: handle_update_pixel(ws, PixelUpdateRequest(**md), u, permission=False),
        "update_selection": lambda ws, md, u: handle_selection_update(ws, SelectionUpdateRequest(**md), u),
        "get_field_state": lambda ws, md, u: handle_send_field_state(ws),
        "get_online_count": lambda ws, md, u: handle_online_count(ws),
        "get_cooldown": lambda ws, md, u: handle_send_cooldown(ws),
        # Административные обработчики
        "update_pixel_admin": lambda ws, md, u: handle_update_pixel(ws, AdminPixelUpdateRequest(**md), u,
                                                                    permission=True) if admin else access_denied(ws),
        "pixel_info_admin": lambda ws, md, u: handle_pixel_info(ws, AdminPixelInfoRequest(
            **md)) if admin else access_denied(ws),
        "toggle_ban_user_admin": lambda ws, md, u: handle_ban_user(ws, AdminBanUserRequest(
            **md)) if admin else access_denied(ws),
        "update_cooldown_admin": lambda ws, md, u: handle_change_cooldown(
            AdminChangeCooldownRequest(**md).data) if admin else access_denied(ws),
        "reset_game_admin": lambda ws, md, u: handle_reset_game(ws, AdminResetGameRequest(
            **md)) if admin else access_denied(ws),
    }

    try:
        if message_type in message_handlers and (message_handlers[message_type] is not None):
            handler = message_handlers[message_type]
            if callable(handler):  # Проверяем, является ли обработчик вызываемым объектом
                await handler(websocket, message_data, user)
        else:
            await websocket.send_text("Unknown message type or action not allowed.")
    except ValidationError as e:
        await websocket.send_text(ErrorResponse(message=str(e)).json())
