from datetime import timedelta

from fastapi import APIRouter
from fastapi import HTTPException

from backend.app.api.admin_login import create_access_token
from backend.app.api.websocket_core.authenticate import authenticate_admin_token
from backend.app.schemas.admin.admin_requests import AdminTokenRefreshRequest
from common.app.core.config import config as cfg

router = APIRouter()


# Функция для обновления access токена
async def refresh_access_token(refresh_token: str) -> str:
    username = await authenticate_admin_token(refresh_token)
    username = username[0]
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token or expired")

    new_access_token = create_access_token(data={"sub": username},
                                           expires_delta=timedelta(minutes=cfg.ACCESS_TOKEN_EXPIRE_MINUTES))
    return new_access_token


# Использование в эндпоинте
@router.post("/refresh")
async def refresh_access_token_endpoint(request: AdminTokenRefreshRequest):
    new_access_token = refresh_access_token(request.refresh_token)
    return {"access_token": new_access_token, "token_type": "bearer"}
