from typing import Dict

from pydantic import BaseModel, Field

from backend.app.schemas.data_models import (
    BaseMessage, FieldStateData, SelectionUpdateBroadcastData
)


class ErrorResponse(BaseMessage):
    type: str = Field(default="error")
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "type": "error",
                "message": "Error message"
            }
        }


class SuccessResponse(BaseMessage):
    type: str = Field(default="success")
    data: str

    class Config:
        json_schema_extra = {
            "example": {
                "type": "success",
                "data": "Success message"
            }
        }


class SelectionUpdateResponse(BaseModel):
    type: str = Field(default="selection_update")
    data: SelectionUpdateBroadcastData

    class Config:
        json_schema_extra = {
            "example": {
                "type": "selection_update",
                "data": {
                    "nickname": "user123",
                    "position": {
                        "x": 10,
                        "y": 20
                    }
                }
            }
        }


class ChangeCooldownResponse(BaseModel):
    type: str = Field(default="cooldown_update")
    data: int

    class Config:
        json_schema_extra = {
            "example": {
                "type": "cooldown_update",
                "data": 10
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


class OnlineCountResponse(BaseMessage):
    type: str = Field(default="online_count_update")
    data: Dict[str, int]

    class Config:
        json_schema_extra = {
            "example": {
                "type": "online_count_update",
                "data": {
                    "online": 10,
                }
            }
        }


class FieldStateResponse(BaseMessage):
    type: str = Field(default="field_state")
    cooldown: int
    size: tuple[int, int]
    data: FieldStateData

    class Config:
        json_schema_extra = {
            "example": {
                "type": "field_state",
                "size": (10, 10),  # Размер поля (x, y)
                "data": {
                    "pixels": [
                        {
                            "position": {
                                "x": 10,
                                "y": 20,
                            },
                            "color": "<HEX_цвет>",
                            "nickname": "<псевдоним>"
                        }
                        # Другие пиксели
                    ],
                    "selections": [
                        {
                            "nickname": "<псевдоним>",
                            "position": {
                                "x": 10,
                                "y": 20,
                            }
                        },
                        # Другие выделения
                    ]
                }
            }
        }


class PixelUpdateResponse(BaseModel):
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
