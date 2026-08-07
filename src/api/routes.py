"""
routes.py — FastAPI REST endpoints for the Order Matching Engine.

Endpoints:
    POST   /orders              — Submit a new order
    GET    /orders/{order_id}   — Get order status (from DB)
    DELETE /orders/{order_id}   — Cancel an order
    PATCH  /orders/{order_id}   — Modify an order

    GET    /orderbook/{symbol}  — Current book depth
    GET    /trades/{symbol}     — Trade history

    GET    /analytics/{symbol}/vwap     — VWAP per hour
    GET    /analytics/{symbol}/spread   — Spread history
    GET    /analytics/{symbol}/volume   — Volume data
    GET    /analytics/{symbol}/ohlc     — OHLC candlestick data
    GET    /analytics/top-symbols       — Most active symbols

    GET    /symbols             — List all symbols
    GET    /health              — Health check

All endpoints use Pydantic models for automatic validation and Swagger docs.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query

from src.models.schemas import (
    OrderRequest, ModifyOrderRequest,
    OrderResponse, TradeResponse, OrderBookResponse,
    PriceLevelResponse, AnalyticsResponse, HealthResponse,
)

# Router — will be included in the main app
router = APIRouter()

# These get set by main.py at startup
exchange = None
db_session_factory = None


def _get_exchange():
    """Get the exchange instance (set at startup)."""
    if exchange is None:
        raise HTTPException(status_code=503, detail="Exchange not initialized")
    return exchange


# ══════════════════════════════════════════════════════════
#  ORDER ENDPOINTS
# ══════════════════════════════════════════════════════════

@router.post("/orders", response_model=OrderResponse, status_code=201,
             tags=["Orders"], summary="Submit a new order")
async def submit_order(request: OrderRequest):
    """
    Submit a new order to the exchange.

    Supported order types:
    - **LIMIT**: Place at a specific price, rests in book if unmatched
    - **MARKET**: Execute immediately at best available price
    - **IOC**: Immediate-or-cancel — fill what you can, cancel the rest
    - **FOK**: Fill-or-kill — fill entirely or reject entirely

    Returns the order with any trades that were generated.
    """
    ex = _get_exchange()

    if not ex.symbol_exists(request.symbol.upper()):
        raise HTTPException(status_code=404, detail=f"Symbol '{request.symbol}' not found")

    try:
        response = await ex.submit_order(
            symbol=request.symbol.upper(),
            side=request.side.value,
            order_type=request.order_type.value,
            price=request.price,
            quantity=request.quantity,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Persist to database (fire-and-forget pattern)
    if db_session_factory is not None:
        try:
            from src.persistence.repository import OrderRepository, TradeRepository
            session = db_session_factory()
            async with session:
                await OrderRepository.save_order(
                    session,
                    order_id=response.order_id,
                    symbol=response.symbol,
                    side=response.side,
                    order_type=response.order_type,
                    price=response.price,
                    quantity=response.quantity,
                    remaining_qty=response.remaining_quantity,
                    status=response.status,
                )
                if response.trades:
                    await TradeRepository.save_trades_batch(
                        session,
                        [
                            {
                                "trade_id": t.trade_id,
                                "symbol": t.symbol,
                                "price": t.price,
                                "quantity": t.quantity,
                                "buy_order_id": t.buy_order_id,
                                "sell_order_id": t.sell_order_id,
                                "created_at": t.timestamp,
                            }
                            for t in response.trades
                        ],
                    )
        except Exception:
            pass  # Don't fail the order if DB write fails

    return response


@router.delete("/orders/{order_id}", response_model=OrderResponse,
               tags=["Orders"], summary="Cancel an order")
async def cancel_order(order_id: int, symbol: str = Query(..., description="Symbol of the order")):
    """
    Cancel an active order.

    The order must still be resting in the book (status NEW or PARTIAL).
    Fully filled or already-cancelled orders cannot be cancelled.
    """
    ex = _get_exchange()

    if not ex.symbol_exists(symbol.upper()):
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found")

    response = await ex.cancel_order(symbol.upper(), order_id)

    if response is None:
        raise HTTPException(
            status_code=404,
            detail=f"Order {order_id} not found or already filled/cancelled"
        )

    # Update DB
    if db_session_factory is not None:
        try:
            from src.persistence.repository import OrderRepository
            session = db_session_factory()
            async with session:
                await OrderRepository.update_order_status(
                    session, order_id, "CANCELLED", response.remaining_quantity
                )
        except Exception:
            pass

    return response


@router.patch("/orders/{order_id}", response_model=OrderResponse,
              tags=["Orders"], summary="Modify an order")
async def modify_order(
    order_id: int,
    request: ModifyOrderRequest,
    symbol: str = Query(..., description="Symbol of the order"),
):
    """
    Modify an active order's price or quantity.

    - **Price change**: Cancels the old order and creates a new one (loses FIFO priority)
    - **Quantity change only**: Keeps the same position in the queue
    """
    ex = _get_exchange()

    if not ex.symbol_exists(symbol.upper()):
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found")

    response = await ex.modify_order(
        symbol.upper(), order_id,
        new_price=request.new_price,
        new_quantity=request.new_quantity,
    )

    if response is None:
        raise HTTPException(
            status_code=404,
            detail=f"Order {order_id} not found or already filled/cancelled"
        )

    return response


# ══════════════════════════════════════════════════════════
#  ORDER BOOK ENDPOINTS
# ══════════════════════════════════════════════════════════

@router.get("/orderbook/{symbol}", response_model=OrderBookResponse,
            tags=["Order Book"], summary="Get current order book")
async def get_order_book(
    symbol: str,
    levels: int = Query(default=10, ge=1, le=50, description="Number of price levels per side"),
):
    """
    Get the current order book depth for a symbol.

    Returns bids (highest first) and asks (lowest first) with volume at each price level.
    """
    ex = _get_exchange()

    if not ex.symbol_exists(symbol.upper()):
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found")

    return await ex.get_order_book(symbol.upper(), levels)


# ══════════════════════════════════════════════════════════
#  TRADE ENDPOINTS
# ══════════════════════════════════════════════════════════

@router.get("/trades/{symbol}", response_model=list[TradeResponse],
            tags=["Trades"], summary="Get trade history")
async def get_trades(
    symbol: str,
    limit: int = Query(default=50, ge=1, le=500, description="Number of trades to return"),
):
    """
    Get recent trades for a symbol.

    Returns trades in reverse chronological order (newest first).
    Data comes from the database for persistence.
    """
    ex = _get_exchange()

    if not ex.symbol_exists(symbol.upper()):
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found")

    # Try DB first for persisted trades
    if db_session_factory is not None:
        try:
            from src.persistence.repository import TradeRepository
            session = db_session_factory()
            async with session:
                db_trades = await TradeRepository.get_trades_by_symbol(
                    session, symbol.upper(), limit
                )
                return [
                    TradeResponse(
                        trade_id=t.trade_id,
                        symbol=t.symbol,
                        price=t.price,
                        quantity=t.quantity,
                        buy_order_id=t.buy_order_id,
                        sell_order_id=t.sell_order_id,
                        timestamp=t.created_at,
                    )
                    for t in db_trades
                ]
        except Exception:
            pass

    # Fallback: in-memory trade log
    raw_trades = ex.get_trade_log(symbol.upper())
    return [
        TradeResponse(
            trade_id=i + 1,
            symbol=symbol.upper(),
            price=t.price,
            quantity=t.quantity,
            buy_order_id=t.buy_order_id,
            sell_order_id=t.sell_order_id,
            timestamp=datetime.now(timezone.utc),
        )
        for i, t in enumerate(raw_trades[-limit:])
    ]


# ══════════════════════════════════════════════════════════
#  ANALYTICS ENDPOINTS
# ══════════════════════════════════════════════════════════

@router.get("/analytics/{symbol}/vwap", response_model=AnalyticsResponse,
            tags=["Analytics"], summary="VWAP per hour")
async def get_vwap(
    symbol: str,
    hours: int = Query(default=24, ge=1, le=168, description="Hours to look back"),
):
    """
    Volume-Weighted Average Price per hour.

    VWAP = SUM(price × quantity) / SUM(quantity)

    This is how institutional traders evaluate execution quality.
    """
    if db_session_factory is None:
        raise HTTPException(status_code=503, detail="Database not available for analytics")

    from src.persistence.analytics import TradingAnalytics
    session = db_session_factory()
    async with session:
        data = await TradingAnalytics.vwap_per_hour(session, symbol.upper(), hours)

    return AnalyticsResponse(symbol=symbol.upper(), metric="vwap", data=data)


@router.get("/analytics/{symbol}/spread", response_model=AnalyticsResponse,
            tags=["Analytics"], summary="Spread history")
async def get_spread(
    symbol: str,
    limit: int = Query(default=100, ge=1, le=500),
):
    """Price change between consecutive trades (approximates spread)."""
    if db_session_factory is None:
        raise HTTPException(status_code=503, detail="Database not available for analytics")

    from src.persistence.analytics import TradingAnalytics
    session = db_session_factory()
    async with session:
        data = await TradingAnalytics.spread_history(session, symbol.upper(), limit)

    return AnalyticsResponse(symbol=symbol.upper(), metric="spread", data=data)


@router.get("/analytics/{symbol}/volume", response_model=AnalyticsResponse,
            tags=["Analytics"], summary="Rolling volume")
async def get_volume(
    symbol: str,
    limit: int = Query(default=100, ge=1, le=500),
):
    """Rolling trade count and volume per minute window."""
    if db_session_factory is None:
        raise HTTPException(status_code=503, detail="Database not available for analytics")

    from src.persistence.analytics import TradingAnalytics
    session = db_session_factory()
    async with session:
        data = await TradingAnalytics.rolling_trade_count(session, symbol.upper(), limit)

    return AnalyticsResponse(symbol=symbol.upper(), metric="rolling_volume", data=data)


@router.get("/analytics/{symbol}/ohlc", response_model=AnalyticsResponse,
            tags=["Analytics"], summary="OHLC candlestick data")
async def get_ohlc(
    symbol: str,
    hours: int = Query(default=24, ge=1, le=168),
):
    """Open/High/Low/Close candlestick data per hour."""
    if db_session_factory is None:
        raise HTTPException(status_code=503, detail="Database not available for analytics")

    from src.persistence.analytics import TradingAnalytics
    session = db_session_factory()
    async with session:
        data = await TradingAnalytics.ohlc_per_hour(session, symbol.upper(), hours)

    return AnalyticsResponse(symbol=symbol.upper(), metric="ohlc", data=data)


@router.get("/analytics/top-symbols", response_model=AnalyticsResponse,
            tags=["Analytics"], summary="Most active symbols by volume")
async def get_top_symbols(
    top_n: int = Query(default=10, ge=1, le=50),
    hours: int = Query(default=24, ge=1, le=168),
):
    """Rank symbols by total traded volume."""
    if db_session_factory is None:
        raise HTTPException(status_code=503, detail="Database not available for analytics")

    from src.persistence.analytics import TradingAnalytics
    session = db_session_factory()
    async with session:
        data = await TradingAnalytics.top_symbols_by_volume(session, top_n, hours)

    return AnalyticsResponse(symbol=None, metric="top_symbols", data=data)


# ══════════════════════════════════════════════════════════
#  SYMBOL + HEALTH ENDPOINTS
# ══════════════════════════════════════════════════════════

@router.get("/symbols", tags=["Symbols"], summary="List all tradeable symbols")
async def get_symbols():
    """Get all registered symbols."""
    ex = _get_exchange()
    return {"symbols": ex.get_symbols()}


@router.get("/health", response_model=HealthResponse,
            tags=["System"], summary="Health check")
async def health_check():
    """System health check — confirms the engine is running."""
    ex = _get_exchange()
    return HealthResponse(
        status="ok",
        version="1.0.0",
        active_symbols=len(ex.get_symbols()),
        total_trades=ex.get_total_trade_count(),
    )
