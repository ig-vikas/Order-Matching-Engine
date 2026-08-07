# SQL Analytics — Market Insights and Queries

> **What is SQL Analytics?** Extracting key performance metrics, historical aggregation, and window function insights directly from persisted trades.

---

## 1. Volume-Weighted Average Price (VWAP)

Calculates fair market price weighted by traded quantities over a specific window.

$$\text{VWAP} = \frac{\sum (\text{Price} \times \text{Quantity})}{\sum \text{Quantity}}$$

```python
# src/persistence/analytics.py snippet

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

class TradingAnalytics:
    @staticmethod
    async def vwap_per_hour(session: AsyncSession, symbol: str, hours_back: int = 24):
        query = text("""
            SELECT 
                strftime('%Y-%m-%d %H:00:00', created_at) AS hour_bucket,
                ROUND(SUM(price * quantity) / SUM(quantity), 4) AS vwap,
                SUM(quantity) AS total_volume,
                COUNT(*) AS trade_count
            FROM trades
            WHERE symbol = :symbol
              AND created_at >= datetime('now', :time_offset)
            GROUP BY hour_bucket
            ORDER BY hour_bucket DESC
        """)
        res = await session.execute(query, {"symbol": symbol, "time_offset": f"-{hours_back} hours"})
        return [dict(row._mapping) for row in res]
```

---

## 2. Window Functions — Latest N Trades Per Symbol

Uses `ROW_NUMBER() OVER (PARTITION BY ...)` to group and filter without multiple database queries.

```python
@staticmethod
async def latest_trades_per_symbol(session: AsyncSession, n: int = 5):
    query = text("""
        WITH RankedTrades AS (
            SELECT 
                trade_id, symbol, price, quantity, created_at,
                ROW_NUMBER() OVER (
                    PARTITION BY symbol ORDER BY created_at DESC
                ) AS rn
            FROM trades
        )
        SELECT trade_id, symbol, price, quantity, created_at
        FROM RankedTrades
        WHERE rn <= :n
        ORDER BY symbol, rn
    """)
    res = await session.execute(query, {"n": n})
    return [dict(row._mapping) for row in res]
```
