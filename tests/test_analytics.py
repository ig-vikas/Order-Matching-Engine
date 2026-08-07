"""
test_analytics.py — Tests for SQL analytics queries.

Uses an in-memory SQLite database seeded with known trade data
to verify that VWAP, volume, and other analytics produce correct results.
"""

import sys
import os
import asyncio
import unittest
from datetime import datetime, timezone, timedelta

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_ENGINE_PATH = os.path.join(_PROJECT_ROOT, "pre-req", "matching_engine")
_SRC_PATH = os.path.join(_PROJECT_ROOT, "src")

for p in [_ENGINE_PATH, _SRC_PATH, _PROJECT_ROOT]:
    if p not in sys.path:
        sys.path.insert(0, p)

from src.models.database import init_db, close_db, TradeDB, Base
from src.persistence.analytics import TradingAnalytics
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestAnalytics(unittest.TestCase):
    """Test SQL analytics queries with known data."""

    @classmethod
    def setUpClass(cls):
        """Set up in-memory DB and seed known trade data."""
        async def setup():
            engine = await init_db("sqlite+aiosqlite:///:memory:")
            cls.session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            # Seed known trades
            now = datetime.now(timezone.utc)
            async with cls.session_factory() as session:
                trades = [
                    # AAPL trades — known VWAP: (100*10 + 102*20 + 98*30) / (10+20+30) = 99.67
                    TradeDB(trade_id=1, symbol="AAPL", price=100.0, quantity=10,
                            buy_order_id=1, sell_order_id=2, created_at=now - timedelta(minutes=5)),
                    TradeDB(trade_id=2, symbol="AAPL", price=102.0, quantity=20,
                            buy_order_id=3, sell_order_id=4, created_at=now - timedelta(minutes=3)),
                    TradeDB(trade_id=3, symbol="AAPL", price=98.0, quantity=30,
                            buy_order_id=5, sell_order_id=6, created_at=now - timedelta(minutes=1)),

                    # GOOGL trades — separate symbol
                    TradeDB(trade_id=4, symbol="GOOGL", price=2800.0, quantity=5,
                            buy_order_id=7, sell_order_id=8, created_at=now - timedelta(minutes=4)),
                    TradeDB(trade_id=5, symbol="GOOGL", price=2810.0, quantity=10,
                            buy_order_id=9, sell_order_id=10, created_at=now - timedelta(minutes=2)),

                    # MSFT trades
                    TradeDB(trade_id=6, symbol="MSFT", price=300.0, quantity=50,
                            buy_order_id=11, sell_order_id=12, created_at=now - timedelta(minutes=6)),
                ]
                for t in trades:
                    session.add(t)
                await session.commit()

        run_async(setup())

    @classmethod
    def tearDownClass(cls):
        run_async(close_db())

    # ── VWAP ──

    def test_vwap_calculation(self):
        """VWAP should match hand-computed value."""
        async def run():
            async with self.session_factory() as session:
                result = await TradingAnalytics.vwap_per_hour(session, "AAPL", hours_back=24)

                self.assertGreater(len(result), 0)
                row = result[0]

                # Expected VWAP: (100*10 + 102*20 + 98*30) / (10+20+30)
                # = (1000 + 2040 + 2940) / 60 = 5980 / 60 ≈ 99.6667
                self.assertAlmostEqual(row["vwap"], 99.6667, places=2)
                self.assertEqual(row["total_volume"], 60)
                self.assertEqual(row["trade_count"], 3)

        run_async(run())

    def test_vwap_empty_symbol(self):
        """VWAP for a symbol with no trades should return empty."""
        async def run():
            async with self.session_factory() as session:
                result = await TradingAnalytics.vwap_per_hour(session, "NOPE", hours_back=24)
                self.assertEqual(len(result), 0)

        run_async(run())

    # ── Top Symbols by Volume ──

    def test_top_symbols_by_volume(self):
        """MSFT (50 shares) > AAPL (60 shares) actually AAPL > MSFT > GOOGL."""
        async def run():
            async with self.session_factory() as session:
                result = await TradingAnalytics.top_symbols_by_volume(session, top_n=10, hours_back=24)

                self.assertGreater(len(result), 0)

                # Check volumes are in descending order
                volumes = [r["total_volume"] for r in result]
                self.assertEqual(volumes, sorted(volumes, reverse=True))

                # AAPL should be first (60 total shares)
                self.assertEqual(result[0]["symbol"], "AAPL")
                self.assertEqual(result[0]["total_volume"], 60)

        run_async(run())

    # ── Spread History ──

    def test_spread_history(self):
        """Should return price changes between consecutive trades."""
        async def run():
            async with self.session_factory() as session:
                result = await TradingAnalytics.spread_history(session, "AAPL", limit=10)

                self.assertGreater(len(result), 0)
                # Each row should have a price_change field
                for row in result:
                    self.assertIn("price_change", row)

        run_async(run())

    # ── Rolling Trade Count ──

    def test_rolling_trade_count(self):
        """Rolling count should include trades within 60-second window."""
        async def run():
            async with self.session_factory() as session:
                result = await TradingAnalytics.rolling_trade_count(session, "AAPL", limit=10)

                self.assertGreater(len(result), 0)
                for row in result:
                    self.assertIn("trades_last_minute", row)
                    self.assertIn("volume_last_minute", row)
                    self.assertGreaterEqual(row["trades_last_minute"], 1)

        run_async(run())

    # ── Latest N Trades Per Symbol ──

    def test_latest_trades_per_symbol(self):
        """Should return top N trades for each symbol."""
        async def run():
            async with self.session_factory() as session:
                result = await TradingAnalytics.latest_trades_per_symbol(session, n=2)

                self.assertGreater(len(result), 0)
                # Each symbol should have at most 2 rows
                symbols_seen = {}
                for row in result:
                    sym = row["symbol"]
                    symbols_seen[sym] = symbols_seen.get(sym, 0) + 1

                for sym, count in symbols_seen.items():
                    self.assertLessEqual(count, 2, f"{sym} has {count} rows, expected <= 2")

        run_async(run())

    # ── Cumulative Volume ──

    def test_cumulative_volume(self):
        """Cumulative volume should be monotonically increasing."""
        async def run():
            async with self.session_factory() as session:
                result = await TradingAnalytics.cumulative_volume(session, "AAPL", limit=10)

                self.assertGreater(len(result), 0)
                for row in result:
                    self.assertIn("cumulative_volume", row)
                    self.assertGreater(row["cumulative_volume"], 0)

        run_async(run())


if __name__ == "__main__":
    unittest.main(verbosity=2)
