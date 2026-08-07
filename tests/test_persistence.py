"""
test_persistence.py — Tests for the database persistence layer.

Uses an in-memory SQLite database for fast, isolated tests.
No Docker or MySQL needed.
"""

import sys
import os
import asyncio
import unittest
from datetime import datetime, timezone

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_ENGINE_PATH = os.path.join(_PROJECT_ROOT, "pre-req", "matching_engine")
_SRC_PATH = os.path.join(_PROJECT_ROOT, "src")

for p in [_ENGINE_PATH, _SRC_PATH, _PROJECT_ROOT]:
    if p not in sys.path:
        sys.path.insert(0, p)

from src.models.database import init_db, close_db, Base
from src.persistence.repository import OrderRepository, TradeRepository, SymbolRepository
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestPersistence(unittest.TestCase):
    """Test database CRUD operations with in-memory SQLite."""

    @classmethod
    def setUpClass(cls):
        """Create a fresh in-memory database."""
        async def setup():
            engine = await init_db("sqlite+aiosqlite:///:memory:")
            cls.session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        run_async(setup())

    @classmethod
    def tearDownClass(cls):
        run_async(close_db())

    def _get_session(self):
        return self.session_factory()

    # ── Order Tests ──

    def test_save_and_get_order(self):
        async def run():
            async with self._get_session() as session:
                await OrderRepository.save_order(
                    session, order_id=1, symbol="AAPL", side="BUY",
                    order_type="LIMIT", price=150.0, quantity=100,
                    remaining_qty=100, status="NEW",
                )

                order = await OrderRepository.get_order(session, 1)
                self.assertIsNotNone(order)
                self.assertEqual(order.order_id, 1)
                self.assertEqual(order.symbol, "AAPL")
                self.assertEqual(order.side, "BUY")
                self.assertEqual(order.price, 150.0)
                self.assertEqual(order.quantity, 100)
                self.assertEqual(order.status, "NEW")

        run_async(run())

    def test_update_order_status(self):
        async def run():
            async with self._get_session() as session:
                await OrderRepository.save_order(
                    session, order_id=2, symbol="AAPL", side="SELL",
                    order_type="LIMIT", price=155.0, quantity=50,
                    remaining_qty=50, status="NEW",
                )

                await OrderRepository.update_order_status(session, 2, "FILLED", 0)

                order = await OrderRepository.get_order(session, 2)
                self.assertEqual(order.status, "FILLED")
                self.assertEqual(order.remaining_qty, 0)

        run_async(run())

    def test_get_orders_by_symbol(self):
        async def run():
            async with self._get_session() as session:
                await OrderRepository.save_order(
                    session, order_id=3, symbol="GOOGL", side="BUY",
                    order_type="LIMIT", price=2800.0, quantity=10,
                    remaining_qty=10, status="NEW",
                )

                orders = await OrderRepository.get_orders_by_symbol(session, "GOOGL")
                self.assertGreater(len(orders), 0)
                self.assertTrue(all(o.symbol == "GOOGL" for o in orders))

        run_async(run())

    def test_get_nonexistent_order(self):
        async def run():
            async with self._get_session() as session:
                order = await OrderRepository.get_order(session, 9999)
                self.assertIsNone(order)

        run_async(run())

    # ── Trade Tests ──

    def test_save_and_get_trade(self):
        async def run():
            async with self._get_session() as session:
                await TradeRepository.save_trade(
                    session, trade_id=1, symbol="AAPL",
                    price=150.0, quantity=50,
                    buy_order_id=1, sell_order_id=2,
                )

                trades = await TradeRepository.get_trades_by_symbol(session, "AAPL")
                self.assertGreater(len(trades), 0)
                self.assertEqual(trades[0].trade_id, 1)
                self.assertEqual(trades[0].price, 150.0)

        run_async(run())

    def test_save_trades_batch(self):
        async def run():
            async with self._get_session() as session:
                trades = [
                    {"trade_id": 10, "symbol": "MSFT", "price": 300.0,
                     "quantity": 20, "buy_order_id": 5, "sell_order_id": 6},
                    {"trade_id": 11, "symbol": "MSFT", "price": 301.0,
                     "quantity": 15, "buy_order_id": 5, "sell_order_id": 7},
                    {"trade_id": 12, "symbol": "MSFT", "price": 302.0,
                     "quantity": 10, "buy_order_id": 5, "sell_order_id": 8},
                ]
                await TradeRepository.save_trades_batch(session, trades)

                result = await TradeRepository.get_trades_by_symbol(session, "MSFT")
                self.assertEqual(len(result), 3)

        run_async(run())

    def test_trade_count(self):
        async def run():
            async with self._get_session() as session:
                count = await TradeRepository.get_trade_count(session, "MSFT")
                self.assertEqual(count, 3)

                total = await TradeRepository.get_trade_count(session)
                self.assertGreaterEqual(total, 3)

        run_async(run())

    # ── Symbol Tests ──

    def test_save_and_get_symbols(self):
        async def run():
            async with self._get_session() as session:
                await SymbolRepository.save_symbol(session, "NFLX", "Netflix Inc.")

                symbols = await SymbolRepository.get_all_symbols(session)
                symbol_names = [s.symbol for s in symbols]
                self.assertIn("NFLX", symbol_names)

        run_async(run())

    def test_save_symbols_batch(self):
        async def run():
            async with self._get_session() as session:
                await SymbolRepository.save_symbols_batch(session, [
                    {"symbol": "AMD", "name": "AMD Inc."},
                    {"symbol": "INTC", "name": "Intel Corporation"},
                ])

                symbols = await SymbolRepository.get_all_symbols(session)
                symbol_names = [s.symbol for s in symbols]
                self.assertIn("AMD", symbol_names)
                self.assertIn("INTC", symbol_names)

        run_async(run())

    def test_duplicate_symbol_skipped(self):
        async def run():
            async with self._get_session() as session:
                # Save same symbol twice via batch — should not error
                await SymbolRepository.save_symbols_batch(session, [
                    {"symbol": "TSLA", "name": "Tesla"},
                ])
                await SymbolRepository.save_symbols_batch(session, [
                    {"symbol": "TSLA", "name": "Tesla Again"},
                ])

        run_async(run())


if __name__ == "__main__":
    unittest.main(verbosity=2)
