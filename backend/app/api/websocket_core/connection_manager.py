from typing import List, Tuple, Optional, Dict

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from backend.app.prometheus.metrics import active_connections_gauge
from backend.app.schemas.admin.admin_respones import AdminUserInfoResponse
from backend.app.schemas.data_models import PositionData, UserInfoData, \
    SelectionUpdateBroadcastData
from backend.app.schemas.user.user_respones import SelectionUpdateResponse, OnlineCountResponse, PixelUpdateResponse


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[Tuple[WebSocket, str]] = []
        self.admin_connections: List[WebSocket] = []
        self.nicknames: Dict[WebSocket, str] = {}
        self.selections: Dict[str, PositionData] = {}

    async def broadcast(self, message: str, recipients: List[WebSocket] = None):
        if recipients is None:
            recipients = [conn for conn, _ in self.active_connections] + self.admin_connections
        for connection in recipients:
            if connection.client_state == WebSocketState.CONNECTED:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    print(f"Error sending message: {e}")

    async def update_selection(self, nickname: str, position: Optional[PositionData]):
        if position:
            self.selections[nickname] = position
        else:
            self.selections.pop(nickname, None)
        await self.broadcast_selection_update(nickname, position)

    async def broadcast_selection_update(self, nickname: str, position: Optional[PositionData]):
        broadcast_message = SelectionUpdateResponse(
            data=SelectionUpdateBroadcastData(
                nickname=nickname,
                position=position
            )
        ).json()
        await self.broadcast(broadcast_message)

    async def connect(self, websocket: WebSocket, nickname: str, user_id: str):
        self.active_connections.append((websocket, user_id))
        self.nicknames[websocket] = nickname
        active_connections_gauge.set(len(self.active_connections))
        await self.notify_updates()

    async def disconnect(self, websocket: WebSocket, code=1000, reason="Normal Closure"):
        self.active_connections = [(conn, uid) for conn, uid in self.active_connections if conn != websocket]
        nickname = self.nicknames.pop(websocket, None)
        if nickname:
            await self.broadcast_selection_update(nickname, None)
            await self.selections.pop(nickname, None)
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close(code=code, reason=reason)
        except RuntimeError as e:
            print(f"RuntimeError: {e}", flush=True)
        active_connections_gauge.set(len(self.active_connections))
        await self.notify_updates()

    async def notify_updates(self):
        await self.broadcast_online_count()
        await self.broadcast_users_info()

    async def broadcast_online_count(self):
        online_count = len(self.active_connections)
        message = OnlineCountResponse(data={"online": online_count}).json()
        await self.broadcast(message)

    async def broadcast_users_info(self):
        users_info = [UserInfoData(nickname=self.nicknames[websocket], id=user_id) for websocket, user_id in
                      self.active_connections if websocket in self.nicknames]
        message = AdminUserInfoResponse(data=users_info).json()
        await self.broadcast(message, recipients=self.admin_connections)

    async def broadcast_pixel_update(self, x: int, y: int, color: str, nickname: str):
        message = PixelUpdateResponse(data={"x": x, "y": y, "color": color, "nickname": nickname}).json()
        await self.broadcast(message)

    async def disconnect_everyone(self):
        for connection, _ in self.active_connections:
            await connection.close(code=1001, reason="Server shutdown")
        for admin in self.admin_connections:
            await admin.close(code=1001, reason="Server shutdown")
        self.active_connections.clear()
        self.admin_connections.clear()
        self.nicknames.clear()
        self.selections.clear()


manager = ConnectionManager()
