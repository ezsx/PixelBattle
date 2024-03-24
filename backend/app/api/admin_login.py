from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from jose import jwt
from passlib.context import CryptContext

from backend.app.schemas.admin.admin_requests import AdminLoginHTTPRequest
from common.app.core.config import config as cfg
from common.app.db.api_db import create_admin

router = APIRouter()



def authenticate_admin(username: str, password: str):
    # Здесь должна быть логика для проверки никнейма и пароля администратора
    # Например, проверка хэша пароля из базы данных
    # Пока используем захардкоженные значения для тестирования
    if username == "admin" and password == "password":
        password_hash = CryptContext(schemes=["bcrypt"]).hash(password)
        create_admin(username, password_hash)
        return {"username": username}
    return None


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, cfg.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


@router.post("/login")
async def login_for_access_token(form_data: AdminLoginHTTPRequest):
    user = authenticate_admin(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    access_token_expires = timedelta(minutes=cfg.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user["username"]}, expires_delta=access_token_expires)

    return {"access_token": access_token, "token_type": "bearer"}

