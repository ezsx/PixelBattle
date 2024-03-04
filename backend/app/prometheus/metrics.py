from prometheus_client import Gauge, Counter

# Создание метрики для отслеживания активных подключений
active_connections_gauge = Gauge('active_websocket_connections', 'Number of active websocket connections')

# Создаем счетчики для отправленных и полученных сообщений
ws_messages_sent = Counter('ws_messages_sent', 'Number of WebSocket messages sent')
ws_messages_received = Counter('ws_messages_received', 'Number of WebSocket messages received')
