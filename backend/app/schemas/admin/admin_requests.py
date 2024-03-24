from pydantic import BaseModel, Field

from backend.app.schemas.data_models import (
    BaseMessage, PixelUpdateData
)


class AdminTokenRefreshRequest(BaseModel):
    access_token: str

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "token"
            }
        }


class AdminLoginHTTPRequest(BaseModel):
    username: str
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "username": "admin",
                "password": "password"
            }
        }


class AdminChangeCooldownRequest(BaseModel):
    type: str = Field(default="update_cooldown_admin")
    data: int

    class Config:
        json_schema_extra = {
            "example": {
                "type": "update_cooldown",
                "data": 10
            }
        }


class AdminPixelUpdateRequest(BaseMessage):
    type: str = Field(default="update_pixel_admin")
    data: PixelUpdateData

    class Config:
        json_schema_extra = {
            "example": {
                "type": "update_pixel_admin",
                "data": {
                    "x": 10,
                    "y": 20,
                    "color": "#FF5733"
                }
            }
        }


class AdminLoginRequest(BaseMessage):
    type: str = Field(default="login_admin")
    data: str  # Здесь предполагается, что data - это токен

    class Config:
        json_schema_extra = {
            "example": {
                "type": "login_admin",
                "data": "token"
            }
        }


class AdminPixelInfoRequest(BaseMessage):
    type: str = Field(default="pixel_info_admin")
    data: dict[str, int]  # Словарь с ключами 'x' и 'y'

    class Config:
        json_schema_extra = {
            "example": {
                "type": "pixel_info_admin",
                "data": {"x": 10, "y": 20}
            }
        }


class AdminBanUserRequest(BaseMessage):
    type: str = Field(default="toggle_ban_user_admin")
    data: dict[str, str]  # Словарь с ключом 'user_id'

    class Config:
        json_schema_extra = {
            "example": {
                "type": "toggle_ban_user_admin",
                "data": {"user_id": "123"}
            }
        }


class AdminResetGameRequest(BaseMessage):
    type: str = Field(default="reset_game_admin")
    data: tuple[int, int]

    class Config:
        json_schema_extra = {
            "example": {
                "type": "reset_game",
                "data": (10, 10)
            }
        }
