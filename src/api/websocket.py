"""
websocket.py — WebSocket live market data feed.

This is how real trading systems deliver market data:
    - Clients connect via WebSocket to get real-time updates
    - No polling needed — server pushes data as events happen
    - Two event types: "trade" and "book_update"

Connection flow:
    1. Client connects to ws://localhost:8000/ws/feed/{symbol}
    2. Server registers the client as a subscriber for that symbol
    3. When a trade happens in that symbol, server pushes a trade event
    4. When the book changes, server pushes a book_update event
    5. Client disconnects → server removes the subscriber

Message format (JSON):
    {
        "type": "trade",
        "symbol": "AAPL",
        "data": [{"trade_id": 1, "price": 150.0, "quantity": 100, ...}]
    }

    {
        "type": "book_update",
        "symbol": "AAPL",
        "data": {"bids": [...], "asks": [...], "spread": 0.5, ...}
    }
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# Set by main.py at startup
exchange = None


@router.websocket("/ws/feed/{symbol}")
async def market_data_feed(websocket: WebSocket, symbol: str):
    """
    WebSocket endpoint for real-time market data.

    Connect to receive live trade and book update events for a symbol.

    Protocol:
        1. Connect → server sends initial book snapshot
        2. Server pushes events as they happen (no request needed)
        3. Client can send "ping" to keep alive
        4. Close connection to unsubscribe
    """
    if exchange is None or not exchange.symbol_exists(symbol.upper()):
        await websocket.close(code=4004, reason=f"Symbol '{symbol}' not found")
        return

    symbol = symbol.upper()
    await websocket.accept()

    # Register as subscriber
    exchange.subscribe(symbol, websocket)

    try:
        # Send initial book snapshot
        book = await exchange.get_order_book(symbol, levels=10)
        await websocket.send_json({
            "type": "book_snapshot",
            "symbol": symbol,
            "data": book.model_dump(mode="json"),
        })

        # Keep connection alive — listen for client messages
        while True:
            message = await websocket.receive_text()

            # Handle ping/pong
            if message == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        # Client disconnected — clean up
        exchange.unsubscribe(symbol, websocket)
    except Exception:
        # Any other error — clean up
        exchange.unsubscribe(symbol, websocket)
        try:
            await websocket.close()
        except Exception:
            pass
