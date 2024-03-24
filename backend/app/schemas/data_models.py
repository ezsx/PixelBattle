from pydantic import BaseModel


class BaseMessage(BaseModel):
    type: str


from typing import Optional, List
from pydantic import BaseModel


class LoginData(BaseModel):
    nickname: str
    user_id: Optional[str] = None


class PositionData(BaseModel):
    x: int
    y: int


class PixelInfoData(BaseModel):
    x: int
    y: int
    color: str
    user_id: Optional[str]
    nickname: Optional[str]


class PixelData(BaseModel):
    position: PositionData
    color: str
    nickname: str


class SelectionData(BaseModel):
    nickname: str
    position: PositionData


class CoolDownData(BaseModel):
    cooldown: int


class FieldStateData(BaseModel):
    pixels: List[PixelData]
    selections: List[SelectionData]


class PixelUpdateData(BaseModel):
    x: int
    y: int
    color: str


class SelectionUpdateData(BaseModel):
    position: Optional[PositionData] = None


class SelectionUpdateBroadcastData(BaseModel):
    nickname: str
    position: Optional[PositionData] = None


class UserInfoData(BaseModel):
    nickname: str
    id: str
