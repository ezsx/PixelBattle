from pydantic import BaseModel, Field

from backend.app.schemas.data_models import (
    BaseMessage, PixelUpdateData,
    SelectionUpdateData,
    LoginData
)


class SelectionUpdateRequest(BaseModel):
    type: str = Field(default="update_selection")
    data: SelectionUpdateData

    class Config:
        json_schema_extra = {
            "example": {
                "type": "update_selection",
                "data": {
                    "nickname": "user123",
                    "position": {
                        "x": 10,
                        "y": 20
                    }
                }
            }
        }


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


class GetFieldStateRequest(BaseMessage):
    type: str = Field(default="get_field_state")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "get_field_state",
            }
        }


class GetOnlineCountRequest(BaseMessage):
    type: str = Field(default="get_online_count")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "get_online_count",
            }
        }


class GetCooldownRequest(BaseMessage):
    type: str = Field(default="get_cooldown")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "get_cooldown",
            }
        }


class DisconnectRequest(BaseMessage):
    type: str = Field(default="disconnect")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "disconnect",
            }
        }
