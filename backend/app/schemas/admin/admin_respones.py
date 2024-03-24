from typing import List

from pydantic import Field

from backend.app.schemas.data_models import (
    BaseMessage, PixelInfoData, UserInfoData
)


class AdminUserInfoResponse(BaseMessage):
    type: str = Field(default="users_info_update")
    data: List[UserInfoData]

    class Config:
        json_schema_extra = {
            "example": {
                "type": "users_info_update",
                "data": [
                    {"nickname": "user123", "id": "123"},
                    {"nickname": "user124", "id": "124"}
                ]
            }
        }


class AdminPixelInfoResponse(BaseMessage):
    type: str = Field(default="pixel_info_update")
    data: PixelInfoData

    class Config:
        json_schema_extra = {
            "example": {
                "type": "pixel_info_update",
                "data": {
                    "x": 10,
                    "y": 20,
                    "color": "#FF5733",
                    "user_id": "123",
                    "nickname": "user123"
                }
            }
        }
