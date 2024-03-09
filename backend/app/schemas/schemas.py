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
    username: str




class PixelUpdateData(BaseModel):
    x: int
    y: int
    color: str



class PixelUpdateRequest(BaseMessage):
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
    data: str

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123",
            }
        }



class AdminLoginRequest(BaseMessage):
    data: str  # Здесь предполагается, что data - это токен

    class Config:
        json_schema_extra = {
            "example": {
                "type": "login_admin",
                "data": "token"
            }
        }


class OnlineCountResponse(BaseMessage):
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


class ErrorResponse(BaseMessage):
    type: str = "error"
    message: str


class SuccessResponse(BaseMessage):
    type: str = "success"
    data: str


class PixelInfoRequest(BaseMessage):
    data: dict[str, int]  # Словарь с ключами 'x' и 'y'

    class Config:
        json_schema_extra = {
            "example": {
                "type": "pixel_info_admin",
                "data": {"x": 10, "y": 20}
            }
        }


class PixelInfoResponse(BaseMessage):
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
    data: dict[str, str]  # Словарь с ключом 'user_id'

    class Config:
        json_schema_extra = {
            "example": {
                "type": "ban_user",
                "data": {"user_id": "123"}
            }
        }


class ResetGameRequest(BaseMessage):
    data: tuple[int, int]

    class Config:
        json_schema_extra = {
            "example": {
                "type": "reset_game",
                "data": (10, 10)
            }
        }