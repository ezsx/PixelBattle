from fastapi import WebSocket, FastAPI

from backend.app.prometheus.metrics import ws_messages_sent, ws_messages_received

app_ws = FastAPI()


async def send_text_metric(websocket: WebSocket, data: str):
    """
    Отправка текстового сообщения через WebSocket и инкремент счетчика отправленных сообщений
    Тут можно брать метрику по любому событию, которое происходит в WebSocket,
    сообщения об ошибки в учет не идут
    :param websocket:
    :param data:
    :return:
    """
    ws_messages_sent.inc()  # Инкрементируем счетчик отправленных сообщений
    await websocket.send_text(data)


async def receive_text_metric(websocket: WebSocket) -> str:
    data = await websocket.receive_text()
    ws_messages_received.inc()  # Инкрементируем счетчик полученных сообщений
    return data
