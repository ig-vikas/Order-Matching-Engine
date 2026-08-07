"""
main.py — FastAPI application entry point.

This is the glue that wires everything together:
    1. Creates the FastAPI app
    2. Initializes the Exchange (matching engines + locks)
    3. Connects to the database
    4. Registers all routes and WebSocket endpoints
    5. Seeds default symbols

Run with:
    uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

Then open:
    http://localhost:8000/docs     — Swagger UI (interactive API docs)
    http://localhost:8000/redoc    — ReDoc (alternative API docs)
"""

import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure pre-req engine is importable
_ENGINE_PATH = os.path.join(os.path.dirname(__file__), "..", "pre-req", "matching_engine")
_ENGINE_PATH = os.path.abspath(_ENGINE_PATH)
if _ENGINE_PATH not in sys.path:
    sys.path.insert(0, _ENGINE_PATH)

# Also ensure src is importable
_SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _SRC_PATH not in sys.path:
    sys.path.insert(0, _SRC_PATH)

from src.config import settings
from src.engine.exchange import Exchange
from src.models.database import init_db, close_db
from src.api import routes as api_routes
from src.api import websocket as ws_routes


# ══════════════════════════════════════════════════════════
#  LIFESPAN — startup and shutdown
# ══════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Startup:
        1. Initialize the database (create tables)
        2. Create the Exchange with default symbols
        3. Wire up the exchange to route handlers
        4. Seed symbols into the database

    Shutdown:
        1. Close database connections
    """
    # ── STARTUP ──
    print("=" * 60)
    print("  ORDER MATCHING ENGINE — STARTING UP")
    print("=" * 60)

    # 1. Initialize database
    db_engine = None
    session_factory = None
    try:
        db_engine = await init_db(settings.database_url)
        from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        print(f"  [OK] Database connected: {settings.database_url}")
    except Exception as e:
        print(f"  [FAIL] Database failed: {e}")
        print("  → Running without persistence (in-memory only)")

    # 2. Create exchange
    exchange = Exchange(symbols=settings.symbol_list)
    print(f"  [OK] Exchange initialized with symbols: {settings.symbol_list}")

    # 3. Wire up routes
    api_routes.exchange = exchange
    api_routes.db_session_factory = session_factory
    ws_routes.exchange = exchange
    print("  [OK] API routes wired up")

    # 4. Seed symbols into DB
    if session_factory is not None:
        try:
            from src.persistence.repository import SymbolRepository
            session = session_factory()
            async with session:
                await SymbolRepository.save_symbols_batch(
                    session,
                    [{"symbol": s, "name": f"{s} Corporation"} for s in settings.symbol_list]
                )
            print("  [OK] Symbols seeded in database")
        except Exception as e:
            print(f"  [FAIL] Symbol seeding failed: {e}")

    print("=" * 60)
    print(f"  API docs: http://localhost:8000/docs")
    print(f"  WebSocket: ws://localhost:8000/ws/feed/AAPL")
    print("=" * 60)

    # Store exchange in app state for access from anywhere
    app.state.exchange = exchange
    app.state.db_session_factory = session_factory

    yield  # ── APP IS RUNNING ──

    # ── SHUTDOWN ──
    print("\n  Shutting down...")
    await close_db()
    print("  [OK] Database closed")


# ══════════════════════════════════════════════════════════
#  CREATE THE APP
# ══════════════════════════════════════════════════════════

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="""
## Order Matching Engine API

A production-grade stock exchange order matching engine with:

- **Price-Time Priority** matching algorithm
- **4 order types**: LIMIT, MARKET, IOC, FOK
- **Multi-symbol** support with per-symbol concurrency
- **Real-time WebSocket** market data feed
- **SQL analytics**: VWAP, spread, volume, OHLC

### Architecture
- In-memory Red-Black Tree order book (O(log n) operations)
- Async FastAPI + SQLAlchemy persistence
- Per-symbol asyncio.Lock for thread-safe matching
    """,
    lifespan=lifespan,
)

# CORS — allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(api_routes.router, prefix="/api/v1")
app.include_router(ws_routes.router)


# Root endpoint — Returns JSON status & links
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint providing service information and API documentation links."""
    return {
        "service": settings.api_title,
        "version": settings.api_version,
        "status": "online",
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc"
        },
        "endpoints": {
            "health": "/api/v1/health",
            "symbols": "/api/v1/symbols",
            "orders": "/api/v1/orders",
            "orderbook": "/api/v1/orderbook/{symbol}",
            "trades": "/api/v1/trades/{symbol}",
            "websocket_feed": "/ws/feed/{symbol}"
        }
    }
