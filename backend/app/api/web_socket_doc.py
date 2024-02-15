from fastapi import APIRouter

router = APIRouter()

@router.get("/docs/ws", include_in_schema=False)
def get_websocket_docs():
    return {
        "name": "Pixel Battle WebSocket",
        "description": "WebSocket-эндпоинт для игры Pixel Battle, позволяющий пользователям взаимодействовать с игровым полем в реальном времени.",
        "usage": """
        **WebSocket Endpoint**: `/ws?user_id={user_id}`

        **Типы сообщений**:

        - `update_pixel`: Запрос на обновление цвета пикселя. Пример сообщения:
          ```json
          {
            "type": "update_pixel",
            "data": {
              "x": 10,
              "y": 20,
              "color": "#FF5733"
            }
          }
          ```

        - `get_field_state`: Запрос на получение текущего состояния игрового поля. Просто отправьте сообщение с типом `get_field_state`.

        **Системные сообщения**:

        - `online_count`: Сервер отправляет это сообщение для информирования о текущем количестве активных пользователей.

        - `heartbeat`: Сервер периодически отправляет это сообщение для поддержания соединения активным.

        **Обработка ошибок**:

        - Если пользователь заблокирован, сервер отправит сообщение с типом `banned` и закроет соединение с кодом 4001.
        """,
        "examples": {
            "update_pixel": boilerplate,
            "get_field_state": '{"type": "get_field_state"}'
        }
    }


boilerplate = """
{
  "type": "update_pixel",
  "data": {
    "x": 10,
    "y": 20,
    "color": "#FF5733"
  }
}
"""