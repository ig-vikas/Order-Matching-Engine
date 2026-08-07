# SQLAlchemy ORM — Async Database Layer

> **What is SQLAlchemy ORM?** Object-Relational Mapping (ORM) translates Python objects into database rows and SQL queries.
> We use SQLAlchemy 2.0 with `asyncio` support for persistent storage.

---

## 1. ORM Model Definitions

Database tables are declared as Python classes inheriting from `DeclarativeBase`.

```python
# src/models/database.py snippet

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, Integer, DateTime
from datetime import datetime, timezone

class Base(DeclarativeBase):
    pass

class TradeDB(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    symbol: Mapped[str] = mapped_column(String(10), index=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    buy_order_id: Mapped[int] = mapped_column(Integer, nullable=False)
    sell_order_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc)
    )
```

---

## 2. Async Repository Pattern

We decouple raw SQL execution from API handlers using repository classes operating on `AsyncSession`.

```python
# src/persistence/repository.py snippet

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models.database import TradeDB

class TradeRepository:
    @staticmethod
    async def save_trade(
        session: AsyncSession,
        trade_id: int,
        symbol: str,
        price: float,
        quantity: int,
        buy_order_id: int,
        sell_order_id: int
    ) -> TradeDB:
        trade = TradeDB(
            trade_id=trade_id,
            symbol=symbol,
            price=price,
            quantity=quantity,
            buy_order_id=buy_order_id,
            sell_order_id=sell_order_id
        )
        session.add(trade)
        await session.commit()
        return trade

    @staticmethod
    async def get_trades_by_symbol(session: AsyncSession, symbol: str, limit: int = 100):
        stmt = select(TradeDB).where(TradeDB.symbol == symbol).order_by(TradeDB.created_at.desc()).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()
```
