from typing import Optional, Dict, List

from pydantic import BaseModel, Field


class PixelUpdateNotification(BaseModel):
    type: str = Field(default="pixel_update")
    data: dict

    class Config:
        json_schema_extra = {
            "example": {
                "type": "pixel_update",
                "data": {
                    "x": 1,
                    "y": 2,
                    "color": "#FFFFFF",
                    "nickname": "user123"
                }
            }
        }


class BaseMessage(BaseModel):
    type: str


class ErrorResponse(BaseMessage):
    type: str = Field(default="error")
    message: str


class SuccessResponse(BaseMessage):
    type: str = Field(default="success")
    data: str


class TokenRefreshRequest(BaseModel):
    access_token: str


class AdminLoginHTTP(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    nickname: str
    id: str


class LoginData(BaseModel):
    nickname: str
    user_id: Optional[str] = None


class PixelInfoData(BaseModel):
    x: int
    y: int
    color: str
    user_id: Optional[str]
    nickname: Optional[str]


class FieldStateData(BaseModel):
    x: int
    y: int
    color: str
    nickname: str


class PixelUpdateData(BaseModel):
    x: int
    y: int
    color: str


class PixelUpdateRequest(BaseMessage):
    type: str = Field(default="update_pixel")
    data: PixelUpdateData

    class Config:
        json_schema_extra = {
            "example": {
                "type": "update_pixel",
                "data": {
                    "x": 10,
                    "y": 20,
                    "color": "#FF5733"
                }
            }
        }


class LoginRequest(BaseMessage):
    type: str = Field(default="login")
    data: LoginData

    class Config:
        json_schema_extra = {
            "example": {
                "type": "login",
                "data": {
                    "nickname": "user123",
                    "user_id": "123"
                }
            }
        }


class AuthResponse(BaseMessage):
    type: str = Field(default="user_id")
    data: str

    class Config:
        json_schema_extra = {
            "example": {
                "type": "user_id",
                "data": "123"
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


class OnlineCountResponse(BaseMessage):
    type: str = Field(default="online_count")
    data: Dict[str, int]

    class Config:
        json_schema_extra = {
            "example": {
                "type": "online_count",
                "data": {
                    "users": 10,
                    "admins": 2
                }
            }
        }


class UserInfoResponse(BaseMessage):
    type: str = Field(default="user_info")
    data: List[UserInfo]

    class Config:
        json_schema_extra = {
            "example": {
                "type": "user_info",
                "data": [
                    {"nickname": "user123", "id": "123"},
                    {"nickname": "user124", "id": "124"}
                ]
            }
        }


class FieldStateResponse(BaseMessage):
    type: str = Field(default="field_state")
    size: tuple[int, int]
    data: List[FieldStateData]

    class Config:
        json_schema_extra = {
            "example": {
                "type": "field_state",
                "size": (10, 10),  # Размер поля (x, y)
                "data": [
                    {
                        "x": 10,
                        "y": 20,
                        "color": "#FFFFFF",
                        "nickname": "user123"
                    },
                    {
                        "x": 15,
                        "y": 25,
                        "color": "#FF0000",
                        "nickname": "user124"
                    }
                ]
            }
        }


class PixelInfoRequest(BaseMessage):
    type: str = Field(default="pixel_info_admin")
    data: dict[str, int]  # Словарь с ключами 'x' и 'y'

    class Config:
        json_schema_extra = {
            "example": {
                "type": "pixel_info_admin",
                "data": {"x": 10, "y": 20}
            }
        }


class PixelInfoResponse(BaseMessage):
    type: str = Field(default="pixel_info")
    data: PixelInfoData

    class Config:
        json_schema_extra = {
            "example": {
                "type": "pixel_info",
                "data": {
                    "x": 10,
                    "y": 20,
                    "color": "#FF5733",
                    "user_id": "123",
                    "nickname": "user123"
                }
            }
        }


class BanUserRequest(BaseMessage):
    type: str = Field(default="ban_user")
    data: dict[str, str]  # Словарь с ключом 'user_id'

    class Config:
        json_schema_extra = {
            "example": {
                "type": "ban_user",
                "data": {"user_id": "123"}
            }
        }


class ResetGameRequest(BaseMessage):
    type: str = Field(default="reset_game")
    data: tuple[int, int]

    class Config:
        json_schema_extra = {
            "example": {
                "type": "reset_game",
                "data": (10, 10)
            }
        }
