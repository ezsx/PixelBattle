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
    refresh_token: str


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


class LoginRequest(BaseMessage):
    data: LoginData


class AuthResponse(BaseMessage):
    data: str


class AdminLoginRequest(BaseMessage):
    data: str  # Здесь предполагается, что data - это токен


class OnlineCountResponse(BaseMessage):
    data: Dict[str, int]


class UserInfoResponse(BaseMessage):
    data: List[UserInfo]


class FieldStateResponse(BaseMessage):
    data: List[FieldStateData]

    class Config:
        json_schema_extra = {
            "example": {
                "type": "field_state",
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


class PixelInfoResponse(BaseMessage):
    data: PixelInfoData


class BanUserRequest(BaseMessage):
    data: dict[str, str]  # Словарь с ключом 'user_id'


class ResetGameRequest(BaseMessage):
    data: dict[str, int]  # Словарь с ключами 'x' и 'y' разметки поля
