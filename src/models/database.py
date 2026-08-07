"""
database.py — SQLAlchemy async ORM models and engine setup.

Tables:
    orders  — every order that enters the system
    trades  — every executed trade
    symbols — registered tradeable symbols

Uses SQLAlchemy 2.0 async API with:
    - aiosqlite for development (zero setup)
    - aiomysql for production (Docker MySQL)

The database is the PERSISTENCE layer, not the source of truth for active orders.
The in-memory order book is the source of truth. The DB stores:
    1. Historical trades for analytics
    2. Audit trail of all orders
    3. Data for SQL analytics queries (VWAP, spread, volume)
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean,
    ForeignKey, Index, Enum as SAEnum, create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)


# ══════════════════════════════════════════════════════════
#  BASE CLASS
# ══════════════════════════════════════════════════════════

class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# ══════════════════════════════════════════════════════════
#  ORDERS TABLE
# ══════════════════════════════════════════════════════════

class OrderDB(Base):
    """
    Persistent record of every order that enters the system.

    Schema:
        order_id       — unique ID (from the matching engine)
        symbol         — ticker symbol (e.g., "AAPL")
        side           — "BUY" or "SELL"
        order_type     — "LIMIT", "MARKET", "IOC", "FOK"
        price          — limit price (NULL for MARKET orders)
        quantity        — original quantity requested
        remaining_qty  — how many shares are still unfilled
        status         — "NEW", "PARTIAL", "FILLED", "CANCELLED", "REJECTED"
        created_at     — when the order was submitted
        updated_at     — last status change
    """
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, unique=True, nullable=False, index=True)
    symbol = Column(String(10), nullable=False)
    side = Column(String(4), nullable=False)  # "BUY" or "SELL"
    order_type = Column(String(10), nullable=False)  # "LIMIT", "MARKET", "IOC", "FOK"
    price = Column(Float, nullable=True)  # NULL for MARKET orders
    quantity = Column(Integer, nullable=False)
    remaining_qty = Column(Integer, nullable=False)
    status = Column(String(10), nullable=False, default="NEW")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_symbol_status", "symbol", "status"),
        Index("idx_created_at", "created_at"),
    )

    def __repr__(self):
        return (f"OrderDB(order_id={self.order_id}, {self.side} {self.symbol} "
                f"@ {self.price}, qty={self.quantity}, status={self.status})")


# ══════════════════════════════════════════════════════════
#  TRADES TABLE
# ══════════════════════════════════════════════════════════

class TradeDB(Base):
    """
    Persistent record of every executed trade.

    This is the core table for analytics:
        - VWAP = SUM(price * quantity) / SUM(quantity)
        - Volume = SUM(quantity)
        - Spread = computed from consecutive trade prices

    Schema:
        trade_id       — globally unique trade ID
        symbol         — ticker symbol
        price          — execution price (= resting order's price)
        quantity       — shares traded
        buy_order_id   — the buyer's order ID
        sell_order_id  — the seller's order ID
        created_at     — when the trade executed
    """
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(Integer, unique=True, nullable=False, index=True)
    symbol = Column(String(10), nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    buy_order_id = Column(Integer, nullable=False)
    sell_order_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_symbol_time", "symbol", "created_at"),
        Index("idx_price", "price"),
    )

    def __repr__(self):
        return (f"TradeDB(trade_id={self.trade_id}, {self.symbol} "
                f"@ {self.price} x {self.quantity})")


# ══════════════════════════════════════════════════════════
#  SYMBOLS TABLE
# ══════════════════════════════════════════════════════════

class SymbolDB(Base):
    """
    Registered tradeable symbols.

    Schema:
        symbol     — ticker (primary key)
        name       — full company name
        is_active  — whether the symbol is currently tradeable
        created_at — when the symbol was registered
    """
    __tablename__ = "symbols"

    symbol = Column(String(10), primary_key=True)
    name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"SymbolDB(symbol={self.symbol}, name={self.name})"


# ══════════════════════════════════════════════════════════
#  DATABASE ENGINE + SESSION FACTORY
# ══════════════════════════════════════════════════════════

# Global references — initialized by init_db()
_async_engine = None
_async_session_factory = None


async def init_db(database_url: str = "sqlite+aiosqlite:///./matching_engine.db"):
    """
    Initialize the async database engine and create all tables.

    Args:
        database_url: SQLAlchemy connection string.
            - Dev:  "sqlite+aiosqlite:///./matching_engine.db"
            - Prod: "mysql+aiomysql://root:matchingengine@localhost:3306/matching_engine"
    """
    global _async_engine, _async_session_factory

    _async_engine = create_async_engine(
        database_url,
        echo=False,  # Set True for SQL debug logging
    )

    _async_session_factory = async_sessionmaker(
        _async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create all tables
    async with _async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return _async_engine


async def get_session() -> AsyncSession:
    """Get a new async database session."""
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _async_session_factory()


async def close_db():
    """Close the database engine cleanly."""
    global _async_engine, _async_session_factory
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
        _async_session_factory = None
