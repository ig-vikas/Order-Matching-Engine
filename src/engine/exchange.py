"""
exchange.py — Multi-symbol Exchange orchestrator with concurrency safety.

This is the top-level coordinator that:
    1. Manages one MatchingEngine per symbol
    2. Serializes order book mutations per symbol using asyncio.Lock
    3. Routes incoming orders to the correct engine
    4. Broadcasts trade/book events to WebSocket subscribers

Concurrency model:
    - Each symbol has its own asyncio.Lock
    - Two orders for AAPL serialize on the AAPL lock
    - An AAPL order and a GOOGL order run in parallel (different locks)
    - This is the "single sequencer per symbol" pattern used by real exchanges

Why asyncio.Lock and not threading.Lock?
    - FastAPI runs on a single-threaded asyncio event loop
    - asyncio.Lock cooperates with the event loop (no OS thread blocking)
    - Two coroutines can't truly execute simultaneously in Python's GIL anyway
    - The lock prevents INTERLEAVING of coroutines at await points

The race condition we're preventing:
    Without locking, two concurrent POST /orders for AAPL could:
    1. Both read the same best ask
    2. Both decide to match against it
    3. Double-fill the resting order (10 shares sold to two different buyers)

    The lock ensures step 1-3 happen atomically for each order.
"""

import sys
import os
import asyncio
from datetime import datetime, timezone
from typing import Any

# Add the pre-req engine to Python path
_ENGINE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "pre-req", "matching_engine")
_ENGINE_PATH = os.path.abspath(_ENGINE_PATH)
if _ENGINE_PATH not in sys.path:
    sys.path.insert(0, _ENGINE_PATH)

from order import Side
from matching_engine import MatchingEngine
from src.engine.order_types import OrderTypeHandler
from src.models.schemas import (
    OrderTypeEnum, OrderStatusEnum, SideEnum,
    OrderResponse, TradeResponse, OrderBookResponse,
    PriceLevelResponse,
)


class Exchange:
    """
    Multi-symbol exchange with per-symbol locking.

    Usage:
        exchange = Exchange(symbols=["AAPL", "GOOGL", "MSFT"])

        # Thread-safe order submission
        response = await exchange.submit_order("AAPL", "BUY", "LIMIT", 150.0, 100)

        # Cancel
        response = await exchange.cancel_order("AAPL", order_id)

        # Query (no lock needed — read-only snapshot)
        book = await exchange.get_order_book("AAPL", levels=5)
    """

    def __init__(self, symbols: list[str] | None = None):
        """
        Initialize the exchange with a list of tradeable symbols.

        Each symbol gets:
            - Its own MatchingEngine (separate order book)
            - Its own asyncio.Lock (separate concurrency domain)
        """
        if symbols is None:
            symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]

        self._engines: dict[str, MatchingEngine] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._order_type_handler = OrderTypeHandler()

        # Mapping: order_id → symbol (so we can find which engine owns an order)
        self._order_symbol_map: dict[int, str] = {}

        # Mapping: order_id → metadata (type, original qty, symbol)
        self._order_metadata: dict[int, dict[str, Any]] = {}

        # Global trade counter (across all symbols)
        self._next_trade_id = 1

        # WebSocket subscribers per symbol
        self._subscribers: dict[str, set] = {}

        for symbol in symbols:
            self._engines[symbol] = MatchingEngine()
            self._locks[symbol] = asyncio.Lock()
            self._subscribers[symbol] = set()

    # ══════════════════════════════════════════════════════════
    #  SYMBOL MANAGEMENT
    # ══════════════════════════════════════════════════════════

    def get_symbols(self) -> list[str]:
        """Return list of all tradeable symbols."""
        return list(self._engines.keys())

    def symbol_exists(self, symbol: str) -> bool:
        """Check if a symbol is registered."""
        return symbol in self._engines

    def add_symbol(self, symbol: str) -> None:
        """Register a new tradeable symbol."""
        if symbol not in self._engines:
            self._engines[symbol] = MatchingEngine()
            self._locks[symbol] = asyncio.Lock()
            self._subscribers[symbol] = set()

    # ══════════════════════════════════════════════════════════
    #  ORDER SUBMISSION — the critical path
    # ══════════════════════════════════════════════════════════

    async def submit_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        price: float | None,
        quantity: int,
    ) -> OrderResponse:
        """
        Submit an order to the exchange.

        This is the CRITICAL PATH — everything inside the lock must be fast.

        Steps:
            1. Acquire the per-symbol lock (serializes with other orders for this symbol)
            2. Convert side/type strings to enums
            3. Dispatch to the correct order type handler
            4. Build response with trade details
            5. Release the lock

        Raises:
            ValueError: if symbol doesn't exist
        """
        if symbol not in self._engines:
            raise ValueError(f"Unknown symbol: {symbol}")

        engine = self._engines[symbol]
        side_enum = Side.BUY if side == "BUY" else Side.SELL

        async with self._locks[symbol]:
            # ── CRITICAL SECTION: all matching is serialized here ──

            if order_type == "LIMIT":
                order, trades = self._order_type_handler.submit_limit(
                    engine, side_enum, price, quantity
                )
            elif order_type == "MARKET":
                order, trades = self._order_type_handler.submit_market(
                    engine, side_enum, quantity
                )
            elif order_type == "IOC":
                order, trades = self._order_type_handler.submit_ioc(
                    engine, side_enum, price, quantity
                )
            elif order_type == "FOK":
                order, trades = self._order_type_handler.submit_fok(
                    engine, side_enum, price, quantity
                )
            else:
                raise ValueError(f"Unknown order type: {order_type}")

            # ── END CRITICAL SECTION ──

        # Handle FOK rejection
        if order is None:
            return OrderResponse(
                order_id=-1,
                symbol=symbol,
                side=side,
                order_type=order_type,
                price=price,
                quantity=quantity,
                remaining_quantity=quantity,
                status=OrderStatusEnum.REJECTED.value,
                timestamp=datetime.now(timezone.utc),
                trades=[],
            )

        # Track which symbol owns this order
        self._order_symbol_map[order.order_id] = symbol
        self._order_metadata[order.order_id] = {
            "order_type": order_type,
            "original_quantity": quantity,
            "symbol": symbol,
        }

        # Determine order status
        filled_qty = sum(t.quantity for t in trades)
        remaining = order.quantity
        if remaining == 0 and filled_qty > 0:
            status = OrderStatusEnum.FILLED.value
        elif filled_qty > 0 and remaining > 0:
            status = OrderStatusEnum.PARTIAL.value
        elif not engine.order_exists(order.order_id):
            # Was cancelled (MARKET/IOC remainder)
            status = OrderStatusEnum.CANCELLED.value
        else:
            status = OrderStatusEnum.NEW.value

        # Build trade responses
        trade_responses = []
        for t in trades:
            trade_resp = TradeResponse(
                trade_id=self._next_trade_id,
                symbol=symbol,
                price=t.price,
                quantity=t.quantity,
                buy_order_id=t.buy_order_id,
                sell_order_id=t.sell_order_id,
                timestamp=datetime.now(timezone.utc),
            )
            trade_responses.append(trade_resp)
            self._next_trade_id += 1

        # Broadcast to WebSocket subscribers (non-blocking)
        if trade_responses:
            await self._broadcast_trades(symbol, trade_responses)
            await self._broadcast_book_update(symbol)

        return OrderResponse(
            order_id=order.order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            price=order.price,
            quantity=quantity,
            remaining_quantity=remaining,
            status=status,
            timestamp=datetime.now(timezone.utc),
            trades=trade_responses,
        )

    # ══════════════════════════════════════════════════════════
    #  CANCEL ORDER
    # ══════════════════════════════════════════════════════════

    async def cancel_order(self, symbol: str, order_id: int) -> OrderResponse | None:
        """
        Cancel an active order.

        Returns the cancelled order response, or None if not found.
        """
        if symbol not in self._engines:
            raise ValueError(f"Unknown symbol: {symbol}")

        engine = self._engines[symbol]

        async with self._locks[symbol]:
            if not engine.order_exists(order_id):
                return None

            cancelled = engine.cancel_order(order_id)

        if cancelled is None:
            return None

        meta = self._order_metadata.get(order_id, {})

        response = OrderResponse(
            order_id=order_id,
            symbol=symbol,
            side=str(cancelled.side),
            order_type=meta.get("order_type", "LIMIT"),
            price=cancelled.price,
            quantity=meta.get("original_quantity", cancelled.quantity),
            remaining_quantity=cancelled.quantity,
            status=OrderStatusEnum.CANCELLED.value,
            timestamp=datetime.now(timezone.utc),
            trades=[],
        )

        # Broadcast book update after cancel
        await self._broadcast_book_update(symbol)

        return response

    # ══════════════════════════════════════════════════════════
    #  MODIFY ORDER
    # ══════════════════════════════════════════════════════════

    async def modify_order(
        self,
        symbol: str,
        order_id: int,
        new_price: float | None = None,
        new_quantity: int | None = None,
    ) -> OrderResponse | None:
        """
        Modify an active order's price or quantity.

        Price change = cancel + re-insert (loses FIFO priority).
        Quantity-only change = keeps FIFO position.
        """
        if symbol not in self._engines:
            raise ValueError(f"Unknown symbol: {symbol}")

        engine = self._engines[symbol]

        async with self._locks[symbol]:
            result, trades = engine.modify_order(order_id, new_price=new_price, new_quantity=new_quantity)

        if result is None:
            return None

        meta = self._order_metadata.get(order_id, {})

        # If price changed, the old order_id is gone, new one is active
        if result.order_id != order_id:
            self._order_symbol_map[result.order_id] = symbol
            self._order_metadata[result.order_id] = meta.copy()
            if order_id in self._order_symbol_map:
                del self._order_symbol_map[order_id]

        filled_qty = sum(t.quantity for t in trades)
        remaining = result.quantity

        if remaining == 0 and filled_qty > 0:
            status = OrderStatusEnum.FILLED.value
        elif filled_qty > 0:
            status = OrderStatusEnum.PARTIAL.value
        elif engine.order_exists(result.order_id):
            status = OrderStatusEnum.NEW.value
        else:
            status = OrderStatusEnum.CANCELLED.value

        trade_responses = []
        for t in trades:
            trade_responses.append(TradeResponse(
                trade_id=self._next_trade_id,
                symbol=symbol,
                price=t.price,
                quantity=t.quantity,
                buy_order_id=t.buy_order_id,
                sell_order_id=t.sell_order_id,
                timestamp=datetime.now(timezone.utc),
            ))
            self._next_trade_id += 1

        if trade_responses:
            await self._broadcast_trades(symbol, trade_responses)

        await self._broadcast_book_update(symbol)

        return OrderResponse(
            order_id=result.order_id,
            symbol=symbol,
            side=str(result.side),
            order_type=meta.get("order_type", "LIMIT"),
            price=result.price,
            quantity=meta.get("original_quantity", result.quantity),
            remaining_quantity=remaining,
            status=status,
            timestamp=datetime.now(timezone.utc),
            trades=trade_responses,
        )

    # ══════════════════════════════════════════════════════════
    #  QUERIES — read-only, no lock needed for snapshots
    # ══════════════════════════════════════════════════════════

    async def get_order_book(self, symbol: str, levels: int = 10) -> OrderBookResponse:
        """
        Get the current order book depth for a symbol.

        No lock needed — we're reading a snapshot. In a real exchange you'd
        want a read lock, but in Python's GIL single-threaded asyncio world,
        a non-awaiting read is atomic enough for display purposes.
        """
        if symbol not in self._engines:
            raise ValueError(f"Unknown symbol: {symbol}")

        engine = self._engines[symbol]
        bids, asks = engine.market_depth(levels)

        best_bid = engine.get_best_bid()
        best_ask = engine.get_best_ask()
        spread = None
        if best_bid is not None and best_ask is not None:
            spread = round(best_ask - best_bid, 4)

        return OrderBookResponse(
            symbol=symbol,
            bids=[PriceLevelResponse(price=p, volume=v, order_count=c) for p, v, c in bids],
            asks=[PriceLevelResponse(price=p, volume=v, order_count=c) for p, v, c in asks],
            best_bid=best_bid,
            best_ask=best_ask,
            spread=spread,
            timestamp=datetime.now(timezone.utc),
        )

    def get_trade_log(self, symbol: str) -> list:
        """Get all trades for a symbol from the in-memory log."""
        if symbol not in self._engines:
            raise ValueError(f"Unknown symbol: {symbol}")
        return self._engines[symbol].get_trade_log()

    def get_total_trade_count(self) -> int:
        """Total trades across all symbols."""
        return sum(len(e.get_trade_log()) for e in self._engines.values())

    def order_exists(self, symbol: str, order_id: int) -> bool:
        """Check if an order is still active."""
        if symbol not in self._engines:
            return False
        return self._engines[symbol].order_exists(order_id)

    # ══════════════════════════════════════════════════════════
    #  WEBSOCKET BROADCASTING
    # ══════════════════════════════════════════════════════════

    def subscribe(self, symbol: str, websocket) -> None:
        """Add a WebSocket subscriber for a symbol's feed."""
        if symbol in self._subscribers:
            self._subscribers[symbol].add(websocket)

    def unsubscribe(self, symbol: str, websocket) -> None:
        """Remove a WebSocket subscriber."""
        if symbol in self._subscribers:
            self._subscribers[symbol].discard(websocket)

    async def _broadcast_trades(self, symbol: str, trades: list[TradeResponse]) -> None:
        """Broadcast trade events to all subscribers for a symbol."""
        if not self._subscribers.get(symbol):
            return

        message = {
            "type": "trade",
            "symbol": symbol,
            "data": [t.model_dump(mode="json") for t in trades],
        }

        dead_sockets = set()
        for ws in self._subscribers[symbol]:
            try:
                await ws.send_json(message)
            except Exception:
                dead_sockets.add(ws)

        # Clean up disconnected sockets
        self._subscribers[symbol] -= dead_sockets

    async def _broadcast_book_update(self, symbol: str) -> None:
        """Broadcast order book snapshot to all subscribers."""
        if not self._subscribers.get(symbol):
            return

        book = await self.get_order_book(symbol, levels=5)
        message = {
            "type": "book_update",
            "symbol": symbol,
            "data": book.model_dump(mode="json"),
        }

        dead_sockets = set()
        for ws in self._subscribers[symbol]:
            try:
                await ws.send_json(message)
            except Exception:
                dead_sockets.add(ws)

        self._subscribers[symbol] -= dead_sockets
