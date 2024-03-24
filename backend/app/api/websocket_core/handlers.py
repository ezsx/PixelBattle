from datetime import datetime
from typing import Tuple

from fastapi import WebSocket

from backend.app.schemas.admin.admin_requests import AdminPixelInfoRequest, AdminBanUserRequest, AdminResetGameRequest
from backend.app.schemas.admin.admin_respones import AdminPixelInfoResponse
from backend.app.schemas.data_models import PixelData, PositionData, SelectionData, FieldStateData
from backend.app.schemas.user.user_requests import SelectionUpdateRequest, PixelUpdateRequest, DisconnectRequest
from backend.app.schemas.user.user_respones import OnlineCountResponse, ChangeCooldownResponse, FieldStateResponse, \
    ErrorResponse, SuccessResponse
from common.app.core.config import config as cfg
from common.app.db.api_db import get_pixels, update_pixel, get_pixel_info, clear_db_admin, toggle_ban_user
from backend.app.api.websocket_core.metrics_handler import send_text_metric
from backend.app.api.websocket_core.connection_manager import manager


async def handle_disconnect(websocket: WebSocket, request: DisconnectRequest):
    await manager.disconnect(websocket, code=request.data.code, reason=request.data.reason)


async def handle_send_cooldown(websocket: WebSocket):
    await send_text_metric(websocket, ChangeCooldownResponse(data=cfg.COOLDOWN).json())


async def handle_online_count(websocket: WebSocket):
    online_count = len(manager.active_connections)
    await send_text_metric(websocket, OnlineCountResponse(data={"online": online_count}).json())


async def handle_change_cooldown(data: int):
    cfg.COOLDOWN = data
    await manager.broadcast(ChangeCooldownResponse(data=data).json())


async def handle_selection_update(websocket: WebSocket, request: SelectionUpdateRequest, user: Tuple[str, str]):
    if not (0 <= request.data.position.x < cfg.FIELD_SIZE[0] and 0 <= request.data.position.y < cfg.FIELD_SIZE[1]):
        await websocket.send_text(ErrorResponse(message="Invalid selection coordinates").json())
        return
    await manager.update_selection(user[0], request.data.position)


async def handle_send_field_state(websocket: WebSocket):
    field_size = cfg.FIELD_SIZE
    cooldown = cfg.COOLDOWN

    raw_pixels = await get_pixels()
    raw_selections = manager.selections

    pixels = [PixelData(position=PositionData(**pixel), color=pixel["color"], nickname=pixel["nickname"]) for pixel in
              raw_pixels]
    selections = [SelectionData(nickname=nickname, position=position) for nickname, position in raw_selections.items()]

    field_state_data = FieldStateData(pixels=pixels, selections=selections)
    message = FieldStateResponse(size=field_size, cooldown=cooldown, data=field_state_data).json()
    await send_text_metric(websocket, message)


async def handle_update_pixel(websocket: WebSocket, request, user: Tuple[str, str],
                              permission: bool = False):
    if not (0 <= request.data.x < cfg.FIELD_SIZE[0] and 0 <= request.data.y < cfg.FIELD_SIZE[1]):
        await websocket.send_text(ErrorResponse(message="Invalid pixel coordinates").json())
        return
    message = await update_pixel(x=request.data.x, y=request.data.y, color=request.data.color, user_id=user[1],
                                 action_time=datetime.utcnow(), permission=permission)
    if message == "cooldown":
        await websocket.send_text(
            ErrorResponse(message="You can only color a pixel at a set time.").json())
    else:
        await manager.broadcast_pixel_update(request.data.x, request.data.y, request.data.color, user[0])


async def handle_pixel_info(websocket: WebSocket, request: AdminPixelInfoRequest):
    data = await get_pixel_info(request.data['x'], request.data['y'])
    if data is None:
        await websocket.send_text(
            ErrorResponse(message="There is no one who past pixel there").json())
        return
    message = AdminPixelInfoResponse(data=data).json()
    await send_text_metric(websocket, message)


async def handle_ban_user(websocket: WebSocket, request: AdminBanUserRequest):
    await toggle_ban_user(request.data['user_id'])
    for connection, user_id in manager.active_connections:
        if user_id == request.data['user_id']:
            await manager.disconnect(connection, code=1002, reason="Protocol Error")
    await send_text_metric(websocket, SuccessResponse(data="User ban toggled").json())


async def handle_reset_game(websocket: WebSocket, request: AdminResetGameRequest):
    await clear_db_admin()
    manager.selections = {}
    manager.nicknames = {}
    cfg.FIELD_SIZE = request.data
    await send_text_metric(websocket, SuccessResponse(data="Game reset").json())
