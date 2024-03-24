from datetime import datetime, timezone
from typing import Tuple, Optional

from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect
from jose import jwt, JWTError
from pydantic import ValidationError

from backend.app.schemas.admin.admin_requests import AdminLoginRequest
from backend.app.schemas.user.user_requests import LoginRequest
from backend.app.schemas.user.user_respones import ErrorResponse, AuthResponse
from common.app.core.config import config as cfg
from common.app.db.api_db import get_user_by_id, create_user, update_user_nickname, \
    get_admin_by_username


async def authenticate(websocket: WebSocket) -> Tuple[Optional[Tuple[str, str]], Tuple[int, str]]:
    try:
        auth_data = await websocket.receive_json()
        if auth_data['type'] == "login_admin":
            request = AdminLoginRequest(**auth_data)
            admin = await authenticate_admin_token(request.data)
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


async def authenticate_admin_token(token: str) -> Optional[Tuple[str, str]]:
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
