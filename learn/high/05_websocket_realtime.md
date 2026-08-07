# WebSocket Real-Time Feeds — Subscriptions & Streaming

> **Why WebSockets?** Unlike HTTP polling (which spams requests), WebSockets establish a full-duplex persistent connection for real-time market data streaming.

---

## 1. Connection Lifecycle and Pub/Sub Pattern

```python
# src/api/websocket.py snippet

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, set[WebSocket]] = {}

    async def connect(self, symbol: str, websocket: WebSocket):
        await websocket.accept()
        if symbol not in self.active_connections:
            self.active_connections[symbol] = set()
        self.active_connections[symbol].add(websocket)

    def disconnect(self, symbol: str, websocket: WebSocket):
        if symbol in self.active_connections:
            self.active_connections[symbol].remove(websocket)

    async def broadcast(self, symbol: str, message: dict):
        if symbol in self.active_connections:
            for connection in list(self.active_connections[symbol]):
                try:
                    await connection.send_json(message)
                except Exception:
                    self.disconnect(symbol, connection)

manager = ConnectionManager()

@router.websocket("/ws/feed/{symbol}")
async def websocket_endpoint(websocket: WebSocket, symbol: str):
    await manager.connect(symbol, websocket)
    try:
        while True:
            # Keep connection open for client messages or heartbeats
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(symbol, websocket)
```
