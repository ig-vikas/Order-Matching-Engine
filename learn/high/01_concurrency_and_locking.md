# Concurrency and Locking — Per-Symbol Isolation

> **Why is locking required?** An order book must maintain strict FIFO price-time priority. If two requests for the same symbol run simultaneously without locks, double-fills or invalid tree states can occur.

---

## 1. The Race Condition Problem

Imagine two simultaneous BUY market orders for symbol `AAPL` when only 10 shares of `SELL` liquidity exist:

```
Thread A Reads Book: 10 shares available at $100
Thread B Reads Book: 10 shares available at $100
Thread A Matches: Fills 10 shares, removes SELL order
Thread B Matches: Fills 10 shares against non-existent order! (DOUBLE-FILL BUG)
```

---

## 2. Per-Symbol `asyncio.Lock` Strategy

Instead of a single global lock (which would bottleneck execution across all symbols like `AAPL`, `GOOGL`, `MSFT`), we assign a separate lock to each symbol:

```python
# src/engine/exchange.py snippet

import asyncio

class Exchange:
    def __init__(self, symbols: list[str]):
        self._engines = {s: MatchingEngine() for s in symbols}
        # Individual Lock per symbol
        self._locks = {s: asyncio.Lock() for s in symbols}

    async def submit_order(self, symbol: str, side: str, order_type: str, price: float | None, quantity: int):
        if symbol not in self._engines:
            raise ValueError(f"Unknown symbol: {symbol}")

        # Acquire lock ONLY for this specific symbol
        async with self._locks[symbol]:
            engine = self._engines[symbol]
            # Match engine logic executes sequentially per symbol
            order, trades = self._handler.submit(engine, side, order_type, price, quantity)
            return order, trades
```

### Performance Characteristics
- **`AAPL` and `GOOGL` orders**: Executed **in parallel** concurrently.
- **Two `AAPL` orders**: Executed **sequentially** in strict arrival order.
