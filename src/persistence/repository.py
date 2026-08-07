"""
repository.py — Async CRUD operations for orders, trades, and symbols.

This is the data access layer. It translates between:
    - In-memory domain objects (from the matching engine)
    - Database records (SQLAlchemy ORM models)

All operations are async because database I/O is the classic case where
you don't want to block the event loop while waiting for a query to return.

Design note:
    The in-memory order book is the source of truth for ACTIVE orders.
    The database stores HISTORICAL data for analytics and audit.
    On server restart, you'd need to rebuild the order book from the DB
    (stretch goal, not implemented here).
"""

from datetime import datetime, timezone
from sqlalchemy import select, update, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import OrderDB, TradeDB, SymbolDB, get_session


# ══════════════════════════════════════════════════════════
#  ORDER REPOSITORY
# ══════════════════════════════════════════════════════════

class OrderRepository:
    """CRUD operations for the orders table."""

    @staticmethod
    async def save_order(
        session: AsyncSession,
        order_id: int,
        symbol: str,
        side: str,
        order_type: str,
        price: float | None,
        quantity: int,
        remaining_qty: int,
        status: str,
    ) -> OrderDB:
        """
        Persist a new order to the database.

        Called after the matching engine processes the order.
        The order might already be partially or fully filled by this point.
        """
        order = OrderDB(
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            price=price,
            quantity=quantity,
            remaining_qty=remaining_qty,
            status=status,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(order)
        await session.commit()
        return order

    @staticmethod
    async def update_order_status(
        session: AsyncSession,
        order_id: int,
        status: str,
        remaining_qty: int | None = None,
    ) -> None:
        """
        Update an order's status (and optionally remaining quantity).

        Used when:
            - An order gets partially filled (NEW → PARTIAL)
            - An order gets fully filled (PARTIAL → FILLED)
            - An order gets cancelled (any → CANCELLED)
        """
        values = {
            "status": status,
            "updated_at": datetime.now(timezone.utc),
        }
        if remaining_qty is not None:
            values["remaining_qty"] = remaining_qty

        stmt = (
            update(OrderDB)
            .where(OrderDB.order_id == order_id)
            .values(**values)
        )
        await session.execute(stmt)
        await session.commit()

    @staticmethod
    async def get_order(session: AsyncSession, order_id: int) -> OrderDB | None:
        """Retrieve an order by its order_id."""
        stmt = select(OrderDB).where(OrderDB.order_id == order_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_orders_by_symbol(
        session: AsyncSession,
        symbol: str,
        status: str | None = None,
        limit: int = 100,
    ) -> list[OrderDB]:
        """
        Get orders for a symbol, optionally filtered by status.

        Returns most recent orders first.
        """
        stmt = select(OrderDB).where(OrderDB.symbol == symbol)
        if status is not None:
            stmt = stmt.where(OrderDB.status == status)
        stmt = stmt.order_by(desc(OrderDB.created_at)).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())


# ══════════════════════════════════════════════════════════
#  TRADE REPOSITORY
# ══════════════════════════════════════════════════════════

class TradeRepository:
    """CRUD operations for the trades table."""

    @staticmethod
    async def save_trade(
        session: AsyncSession,
        trade_id: int,
        symbol: str,
        price: float,
        quantity: int,
        buy_order_id: int,
        sell_order_id: int,
    ) -> TradeDB:
        """Persist a single trade to the database."""
        trade = TradeDB(
            trade_id=trade_id,
            symbol=symbol,
            price=price,
            quantity=quantity,
            buy_order_id=buy_order_id,
            sell_order_id=sell_order_id,
            created_at=datetime.now(timezone.utc),
        )
        session.add(trade)
        await session.commit()
        return trade

    @staticmethod
    async def save_trades_batch(
        session: AsyncSession,
        trades: list[dict],
    ) -> None:
        """
        Persist multiple trades in a single transaction.

        More efficient than saving one-by-one when a single order
        generates multiple trades (sweeping through price levels).

        Args:
            trades: list of dicts with keys:
                trade_id, symbol, price, quantity, buy_order_id, sell_order_id
        """
        for trade_data in trades:
            trade = TradeDB(
                trade_id=trade_data["trade_id"],
                symbol=trade_data["symbol"],
                price=trade_data["price"],
                quantity=trade_data["quantity"],
                buy_order_id=trade_data["buy_order_id"],
                sell_order_id=trade_data["sell_order_id"],
                created_at=trade_data.get("created_at", datetime.now(timezone.utc)),
            )
            session.add(trade)
        await session.commit()

    @staticmethod
    async def get_trades_by_symbol(
        session: AsyncSession,
        symbol: str,
        limit: int = 100,
    ) -> list[TradeDB]:
        """Get recent trades for a symbol, newest first."""
        stmt = (
            select(TradeDB)
            .where(TradeDB.symbol == symbol)
            .order_by(desc(TradeDB.created_at))
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_trade_count(session: AsyncSession, symbol: str | None = None) -> int:
        """Count total trades, optionally filtered by symbol."""
        stmt = select(func.count(TradeDB.id))
        if symbol is not None:
            stmt = stmt.where(TradeDB.symbol == symbol)
        result = await session.execute(stmt)
        return result.scalar() or 0


# ══════════════════════════════════════════════════════════
#  SYMBOL REPOSITORY
# ══════════════════════════════════════════════════════════

class SymbolRepository:
    """CRUD operations for the symbols table."""

    @staticmethod
    async def save_symbol(
        session: AsyncSession,
        symbol: str,
        name: str | None = None,
    ) -> SymbolDB:
        """Register a new symbol."""
        sym = SymbolDB(
            symbol=symbol,
            name=name,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        session.add(sym)
        await session.commit()
        return sym

    @staticmethod
    async def save_symbols_batch(
        session: AsyncSession,
        symbols: list[dict],
    ) -> None:
        """Register multiple symbols."""
        for sym_data in symbols:
            # Check if already exists
            existing = await session.execute(
                select(SymbolDB).where(SymbolDB.symbol == sym_data["symbol"])
            )
            if existing.scalar_one_or_none() is None:
                sym = SymbolDB(
                    symbol=sym_data["symbol"],
                    name=sym_data.get("name"),
                    is_active=True,
                )
                session.add(sym)
        await session.commit()

    @staticmethod
    async def get_all_symbols(session: AsyncSession, active_only: bool = True) -> list[SymbolDB]:
        """Get all registered symbols."""
        stmt = select(SymbolDB)
        if active_only:
            stmt = stmt.where(SymbolDB.is_active == True)
        stmt = stmt.order_by(SymbolDB.symbol)
        result = await session.execute(stmt)
        return list(result.scalars().all())
