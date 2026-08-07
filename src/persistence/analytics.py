"""
analytics.py — SQL analytics queries for the matching engine.

These are the "SQL interview prep" queries — each demonstrates a real
analytical technique used in trading systems:

1. VWAP (Volume-Weighted Average Price) — the most important metric
2. Volume by symbol — activity ranking
3. Spread history — computed from trade data
4. Rolling trade count — window functions
5. Latest N trades per symbol — ROW_NUMBER
6. Price OHLC (Open/High/Low/Close) — candlestick data

All queries use SQLAlchemy text() for raw SQL since these are complex
analytical queries that are cleaner in raw SQL than the ORM query builder.

Both SQLite and MySQL dialects are supported where they differ.
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class TradingAnalytics:
    """
    SQL analytics queries against the trades table.

    Every method takes an AsyncSession and returns a list of dicts
    (row results), making them easy to serialize to JSON.
    """

    # ══════════════════════════════════════════════════════════
    #  1. VWAP — Volume-Weighted Average Price
    # ══════════════════════════════════════════════════════════

    @staticmethod
    async def vwap_per_hour(
        session: AsyncSession,
        symbol: str,
        hours_back: int = 24,
    ) -> list[dict]:
        """
        VWAP per hour for a symbol.

        Formula: SUM(price * quantity) / SUM(quantity)

        This is how institutional traders evaluate whether they got a good
        execution price — if you bought below VWAP, you did well.

        Uses strftime for SQLite compatibility.
        """
        since = datetime.now(timezone.utc) - timedelta(hours=hours_back)

        query = text("""
            SELECT
                strftime('%Y-%m-%d %H:00:00', created_at) AS hour_bucket,
                ROUND(SUM(price * quantity) * 1.0 / SUM(quantity), 4) AS vwap,
                SUM(quantity) AS total_volume,
                COUNT(*) AS trade_count,
                MIN(price) AS low_price,
                MAX(price) AS high_price
            FROM trades
            WHERE symbol = :symbol
                AND created_at >= :since
            GROUP BY hour_bucket
            ORDER BY hour_bucket
        """)

        result = await session.execute(query, {"symbol": symbol, "since": since})
        rows = result.mappings().all()
        return [dict(row) for row in rows]

    # ══════════════════════════════════════════════════════════
    #  2. MOST ACTIVE SYMBOLS BY VOLUME
    # ══════════════════════════════════════════════════════════

    @staticmethod
    async def top_symbols_by_volume(
        session: AsyncSession,
        top_n: int = 10,
        hours_back: int = 24,
    ) -> list[dict]:
        """
        Rank symbols by total traded volume.

        This answers: "What are the most actively traded symbols?"
        Real exchanges use this for regulatory reporting and fee calculations.
        """
        since = datetime.now(timezone.utc) - timedelta(hours=hours_back)

        query = text("""
            SELECT
                symbol,
                SUM(quantity) AS total_volume,
                COUNT(*) AS trade_count,
                ROUND(AVG(price), 4) AS avg_price,
                MIN(price) AS low,
                MAX(price) AS high,
                ROUND(SUM(price * quantity), 2) AS notional_value
            FROM trades
            WHERE created_at >= :since
            GROUP BY symbol
            ORDER BY total_volume DESC
            LIMIT :top_n
        """)

        result = await session.execute(query, {"since": since, "top_n": top_n})
        rows = result.mappings().all()
        return [dict(row) for row in rows]

    # ══════════════════════════════════════════════════════════
    #  3. PRICE CHANGE / SPREAD FROM CONSECUTIVE TRADES
    # ══════════════════════════════════════════════════════════

    @staticmethod
    async def spread_history(
        session: AsyncSession,
        symbol: str,
        limit: int = 100,
    ) -> list[dict]:
        """
        Approximate spread from consecutive trade prices.

        Real spread = best_ask - best_bid at each point in time.
        Since we don't snapshot the book, we approximate from trade data:
        the price change between consecutive trades gives a sense of
        the effective spread.

        Uses a subquery to compute LAG equivalent (SQLite compatible).
        """
        query = text("""
            SELECT
                t1.trade_id,
                t1.price,
                t1.quantity,
                t1.created_at,
                t1.price - COALESCE(
                    (SELECT t2.price
                     FROM trades t2
                     WHERE t2.symbol = t1.symbol
                       AND t2.created_at < t1.created_at
                     ORDER BY t2.created_at DESC
                     LIMIT 1),
                    t1.price
                ) AS price_change
            FROM trades t1
            WHERE t1.symbol = :symbol
            ORDER BY t1.created_at DESC
            LIMIT :limit
        """)

        result = await session.execute(query, {"symbol": symbol, "limit": limit})
        rows = result.mappings().all()
        return [dict(row) for row in rows]

    # ══════════════════════════════════════════════════════════
    #  4. ROLLING TRADE COUNT (per minute window)
    # ══════════════════════════════════════════════════════════

    @staticmethod
    async def rolling_trade_count(
        session: AsyncSession,
        symbol: str,
        limit: int = 100,
    ) -> list[dict]:
        """
        For each trade, count how many trades happened in the preceding 60 seconds.

        This is a "rolling window" — a classic interview question.
        Real exchanges use this for circuit breakers (halt trading if volume spikes).

        SQLite doesn't support RANGE BETWEEN INTERVAL, so we use a correlated subquery.
        """
        query = text("""
            SELECT
                t1.trade_id,
                t1.price,
                t1.quantity,
                t1.created_at,
                (SELECT COUNT(*)
                 FROM trades t2
                 WHERE t2.symbol = t1.symbol
                   AND t2.created_at BETWEEN datetime(t1.created_at, '-60 seconds') AND t1.created_at
                ) AS trades_last_minute,
                (SELECT COALESCE(SUM(t2.quantity), 0)
                 FROM trades t2
                 WHERE t2.symbol = t1.symbol
                   AND t2.created_at BETWEEN datetime(t1.created_at, '-60 seconds') AND t1.created_at
                ) AS volume_last_minute
            FROM trades t1
            WHERE t1.symbol = :symbol
            ORDER BY t1.created_at DESC
            LIMIT :limit
        """)

        result = await session.execute(query, {"symbol": symbol, "limit": limit})
        rows = result.mappings().all()
        return [dict(row) for row in rows]

    # ══════════════════════════════════════════════════════════
    #  5. LATEST N TRADES PER SYMBOL (ROW_NUMBER)
    # ══════════════════════════════════════════════════════════

    @staticmethod
    async def latest_trades_per_symbol(
        session: AsyncSession,
        n: int = 5,
    ) -> list[dict]:
        """
        Get the latest N trades for EACH symbol.

        Uses ROW_NUMBER() window function to rank trades per symbol,
        then filters to the top N.

        This is the "top-N per group" pattern — appears in every SQL interview.
        """
        query = text("""
            SELECT * FROM (
                SELECT
                    trade_id,
                    symbol,
                    price,
                    quantity,
                    buy_order_id,
                    sell_order_id,
                    created_at,
                    ROW_NUMBER() OVER (
                        PARTITION BY symbol
                        ORDER BY created_at DESC
                    ) AS rn
                FROM trades
            ) ranked
            WHERE rn <= :n
            ORDER BY symbol, rn
        """)

        result = await session.execute(query, {"n": n})
        rows = result.mappings().all()
        return [dict(row) for row in rows]

    # ══════════════════════════════════════════════════════════
    #  6. OHLC CANDLESTICK DATA
    # ══════════════════════════════════════════════════════════

    @staticmethod
    async def ohlc_per_hour(
        session: AsyncSession,
        symbol: str,
        hours_back: int = 24,
    ) -> list[dict]:
        """
        OHLC (Open/High/Low/Close) candlestick data per hour.

        Open  = first trade price in the hour
        High  = max trade price in the hour
        Low   = min trade price in the hour
        Close = last trade price in the hour

        This is what candlestick charts are built from.
        """
        since = datetime.now(timezone.utc) - timedelta(hours=hours_back)

        query = text("""
            SELECT
                strftime('%Y-%m-%d %H:00:00', created_at) AS hour_bucket,
                -- Open: first trade in the bucket
                (SELECT t2.price FROM trades t2
                 WHERE t2.symbol = :symbol
                   AND strftime('%Y-%m-%d %H:00:00', t2.created_at) = strftime('%Y-%m-%d %H:00:00', trades.created_at)
                 ORDER BY t2.created_at ASC LIMIT 1) AS open_price,
                MAX(price) AS high_price,
                MIN(price) AS low_price,
                -- Close: last trade in the bucket
                (SELECT t3.price FROM trades t3
                 WHERE t3.symbol = :symbol
                   AND strftime('%Y-%m-%d %H:00:00', t3.created_at) = strftime('%Y-%m-%d %H:00:00', trades.created_at)
                 ORDER BY t3.created_at DESC LIMIT 1) AS close_price,
                SUM(quantity) AS volume,
                COUNT(*) AS trade_count
            FROM trades
            WHERE symbol = :symbol
                AND created_at >= :since
            GROUP BY hour_bucket
            ORDER BY hour_bucket
        """)

        result = await session.execute(query, {"symbol": symbol, "since": since})
        rows = result.mappings().all()
        return [dict(row) for row in rows]

    # ══════════════════════════════════════════════════════════
    #  7. CUMULATIVE VOLUME
    # ══════════════════════════════════════════════════════════

    @staticmethod
    async def cumulative_volume(
        session: AsyncSession,
        symbol: str,
        limit: int = 100,
    ) -> list[dict]:
        """
        Running total of volume for a symbol.

        Uses SUM() window function — shows how cumulative volume grows over time.
        Useful for volume profile analysis.
        """
        query = text("""
            SELECT
                trade_id,
                price,
                quantity,
                created_at,
                SUM(quantity) OVER (
                    ORDER BY created_at
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS cumulative_volume
            FROM trades
            WHERE symbol = :symbol
            ORDER BY created_at DESC
            LIMIT :limit
        """)

        result = await session.execute(query, {"symbol": symbol, "limit": limit})
        rows = result.mappings().all()
        return [dict(row) for row in rows]
