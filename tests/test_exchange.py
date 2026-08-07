"""
test_exchange.py — Tests for the multi-symbol Exchange orchestrator.

Tests cover:
    - Multi-symbol isolation (AAPL trades don't affect GOOGL)
    - Order lifecycle (NEW → PARTIAL → FILLED → CANCELLED)
    - Concurrent order submission (100 simultaneous orders)
    - Cancel and modify through the exchange layer
    - Symbol management
    - Order ID uniqueness across symbols
"""

import sys
import os
import asyncio
import unittest

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_ENGINE_PATH = os.path.join(_PROJECT_ROOT, "pre-req", "matching_engine")
_SRC_PATH = os.path.join(_PROJECT_ROOT, "src")

for p in [_ENGINE_PATH, _SRC_PATH, _PROJECT_ROOT]:
    if p not in sys.path:
        sys.path.insert(0, p)

from src.engine.exchange import Exchange


def run_async(coro):
    """Helper to run async tests in sync unittest."""
    return asyncio.get_event_loop().run_until_complete(coro)


class TestExchangeBasic(unittest.TestCase):
    """Basic exchange operations."""

    def setUp(self):
        self.exchange = Exchange(symbols=["AAPL", "GOOGL", "MSFT"])

    def test_symbols_initialized(self):
        """All symbols should be available."""
        symbols = self.exchange.get_symbols()
        self.assertIn("AAPL", symbols)
        self.assertIn("GOOGL", symbols)
        self.assertIn("MSFT", symbols)

    def test_symbol_exists(self):
        self.assertTrue(self.exchange.symbol_exists("AAPL"))
        self.assertFalse(self.exchange.symbol_exists("NOPE"))

    def test_add_symbol(self):
        self.exchange.add_symbol("NVDA")
        self.assertTrue(self.exchange.symbol_exists("NVDA"))

    def test_unknown_symbol_raises(self):
        with self.assertRaises(ValueError):
            run_async(self.exchange.submit_order("NOPE", "BUY", "LIMIT", 100.0, 10))


class TestExchangeOrderSubmission(unittest.TestCase):
    """Test order submission through the exchange."""

    def setUp(self):
        self.exchange = Exchange(symbols=["AAPL", "GOOGL"])

    def test_limit_order_new(self):
        """A non-crossing LIMIT order should have status NEW."""
        resp = run_async(self.exchange.submit_order("AAPL", "BUY", "LIMIT", 150.0, 100))
        self.assertEqual(resp.status, "NEW")
        self.assertEqual(resp.symbol, "AAPL")
        self.assertEqual(resp.side, "BUY")
        self.assertEqual(resp.remaining_quantity, 100)
        self.assertEqual(len(resp.trades), 0)

    def test_limit_order_filled(self):
        """Crossing LIMIT orders should produce trades and status FILLED."""
        run_async(self.exchange.submit_order("AAPL", "SELL", "LIMIT", 150.0, 100))
        resp = run_async(self.exchange.submit_order("AAPL", "BUY", "LIMIT", 150.0, 100))

        self.assertEqual(resp.status, "FILLED")
        self.assertEqual(resp.remaining_quantity, 0)
        self.assertEqual(len(resp.trades), 1)
        self.assertEqual(resp.trades[0].quantity, 100)
        self.assertEqual(resp.trades[0].price, 150.0)

    def test_market_order(self):
        """MARKET order should fill at best available."""
        run_async(self.exchange.submit_order("AAPL", "SELL", "LIMIT", 150.0, 50))
        resp = run_async(self.exchange.submit_order("AAPL", "BUY", "MARKET", None, 50))

        self.assertEqual(resp.status, "FILLED")
        self.assertEqual(len(resp.trades), 1)
        self.assertEqual(resp.trades[0].price, 150.0)

    def test_market_no_liquidity(self):
        """MARKET with no liquidity should be cancelled."""
        resp = run_async(self.exchange.submit_order("AAPL", "BUY", "MARKET", None, 50))
        self.assertEqual(resp.status, "CANCELLED")

    def test_ioc_partial(self):
        """IOC with partial liquidity fills what it can."""
        run_async(self.exchange.submit_order("AAPL", "SELL", "LIMIT", 150.0, 30))
        resp = run_async(self.exchange.submit_order("AAPL", "BUY", "IOC", 150.0, 50))

        self.assertEqual(len(resp.trades), 1)
        self.assertEqual(resp.trades[0].quantity, 30)
        # Remainder cancelled, not in book
        book = run_async(self.exchange.get_order_book("AAPL"))
        self.assertEqual(len(book.bids), 0)

    def test_fok_rejected(self):
        """FOK with insufficient liquidity should be rejected."""
        run_async(self.exchange.submit_order("AAPL", "SELL", "LIMIT", 150.0, 30))
        resp = run_async(self.exchange.submit_order("AAPL", "BUY", "FOK", 150.0, 50))

        self.assertEqual(resp.status, "REJECTED")
        self.assertEqual(resp.order_id, -1)
        self.assertEqual(len(resp.trades), 0)

    def test_fok_filled(self):
        """FOK with enough liquidity should fill."""
        run_async(self.exchange.submit_order("AAPL", "SELL", "LIMIT", 150.0, 50))
        resp = run_async(self.exchange.submit_order("AAPL", "BUY", "FOK", 150.0, 50))

        self.assertEqual(resp.status, "FILLED")
        self.assertEqual(len(resp.trades), 1)


class TestExchangeMultiSymbol(unittest.TestCase):
    """Test that symbols are isolated from each other."""

    def setUp(self):
        self.exchange = Exchange(symbols=["AAPL", "GOOGL"])

    def test_symbol_isolation(self):
        """Orders for AAPL should not affect GOOGL's book."""
        run_async(self.exchange.submit_order("AAPL", "BUY", "LIMIT", 150.0, 100))
        run_async(self.exchange.submit_order("GOOGL", "SELL", "LIMIT", 2800.0, 50))

        aapl_book = run_async(self.exchange.get_order_book("AAPL"))
        googl_book = run_async(self.exchange.get_order_book("GOOGL"))

        # AAPL should have bids, no asks
        self.assertEqual(len(aapl_book.bids), 1)
        self.assertEqual(len(aapl_book.asks), 0)

        # GOOGL should have asks, no bids
        self.assertEqual(len(googl_book.bids), 0)
        self.assertEqual(len(googl_book.asks), 1)

    def test_cross_symbol_no_match(self):
        """A BUY for AAPL should NOT match a SELL for GOOGL, even if prices cross."""
        run_async(self.exchange.submit_order("GOOGL", "SELL", "LIMIT", 100.0, 10))
        resp = run_async(self.exchange.submit_order("AAPL", "BUY", "LIMIT", 200.0, 10))

        # No trades — different symbols
        self.assertEqual(len(resp.trades), 0)
        self.assertEqual(resp.status, "NEW")

    def test_total_trade_count(self):
        """Total trade count should span all symbols."""
        run_async(self.exchange.submit_order("AAPL", "SELL", "LIMIT", 150.0, 10))
        run_async(self.exchange.submit_order("AAPL", "BUY", "LIMIT", 150.0, 10))

        run_async(self.exchange.submit_order("GOOGL", "SELL", "LIMIT", 2800.0, 5))
        run_async(self.exchange.submit_order("GOOGL", "BUY", "LIMIT", 2800.0, 5))

        self.assertEqual(self.exchange.get_total_trade_count(), 2)


class TestExchangeCancel(unittest.TestCase):
    """Test cancellation through the exchange."""

    def setUp(self):
        self.exchange = Exchange(symbols=["AAPL"])

    def test_cancel_active_order(self):
        """Cancelling an active order should return CANCELLED status."""
        resp = run_async(self.exchange.submit_order("AAPL", "BUY", "LIMIT", 150.0, 100))
        cancel_resp = run_async(self.exchange.cancel_order("AAPL", resp.order_id))

        self.assertIsNotNone(cancel_resp)
        self.assertEqual(cancel_resp.status, "CANCELLED")

        # Book should be empty
        book = run_async(self.exchange.get_order_book("AAPL"))
        self.assertEqual(len(book.bids), 0)

    def test_cancel_nonexistent(self):
        """Cancelling a non-existent order should return None."""
        result = run_async(self.exchange.cancel_order("AAPL", 9999))
        self.assertIsNone(result)


class TestExchangeModify(unittest.TestCase):
    """Test order modification through the exchange."""

    def setUp(self):
        self.exchange = Exchange(symbols=["AAPL"])

    def test_modify_quantity(self):
        """Modifying quantity should keep the order in the book."""
        resp = run_async(self.exchange.submit_order("AAPL", "BUY", "LIMIT", 150.0, 100))
        mod_resp = run_async(self.exchange.modify_order("AAPL", resp.order_id, new_quantity=50))

        self.assertIsNotNone(mod_resp)
        book = run_async(self.exchange.get_order_book("AAPL"))
        self.assertEqual(book.bids[0].volume, 50)

    def test_modify_price(self):
        """Modifying price cancels and re-inserts (new order ID)."""
        resp = run_async(self.exchange.submit_order("AAPL", "BUY", "LIMIT", 150.0, 100))
        old_id = resp.order_id
        mod_resp = run_async(self.exchange.modify_order("AAPL", old_id, new_price=155.0))

        self.assertIsNotNone(mod_resp)
        # Price change creates a new order
        self.assertNotEqual(mod_resp.order_id, old_id)
        book = run_async(self.exchange.get_order_book("AAPL"))
        self.assertEqual(book.best_bid, 155.0)

    def test_modify_nonexistent(self):
        """Modifying non-existent order should return None."""
        result = run_async(self.exchange.modify_order("AAPL", 9999, new_quantity=50))
        self.assertIsNone(result)


class TestExchangeOrderBook(unittest.TestCase):
    """Test order book queries."""

    def setUp(self):
        self.exchange = Exchange(symbols=["AAPL"])

    def test_order_book_structure(self):
        """Order book should have correct bid/ask structure."""
        run_async(self.exchange.submit_order("AAPL", "BUY", "LIMIT", 149.0, 50))
        run_async(self.exchange.submit_order("AAPL", "BUY", "LIMIT", 150.0, 100))
        run_async(self.exchange.submit_order("AAPL", "SELL", "LIMIT", 151.0, 75))
        run_async(self.exchange.submit_order("AAPL", "SELL", "LIMIT", 152.0, 25))

        book = run_async(self.exchange.get_order_book("AAPL"))

        self.assertEqual(book.symbol, "AAPL")
        self.assertEqual(len(book.bids), 2)
        self.assertEqual(len(book.asks), 2)
        self.assertEqual(book.best_bid, 150.0)
        self.assertEqual(book.best_ask, 151.0)
        self.assertEqual(book.spread, 1.0)

        # Bids highest first
        self.assertEqual(book.bids[0].price, 150.0)
        self.assertEqual(book.bids[1].price, 149.0)

        # Asks lowest first
        self.assertEqual(book.asks[0].price, 151.0)
        self.assertEqual(book.asks[1].price, 152.0)

    def test_empty_book(self):
        """Empty book should have no bids/asks and None spread."""
        book = run_async(self.exchange.get_order_book("AAPL"))
        self.assertEqual(len(book.bids), 0)
        self.assertEqual(len(book.asks), 0)
        self.assertIsNone(book.spread)


class TestExchangeConcurrency(unittest.TestCase):
    """Test concurrent order submission."""

    def test_concurrent_orders_same_symbol(self):
        """100 concurrent orders for the same symbol should all complete without error."""
        exchange = Exchange(symbols=["AAPL"])

        async def run_concurrent():
            # Add 50 sell orders first (so buys can match)
            for i in range(50):
                await exchange.submit_order("AAPL", "SELL", "LIMIT", 100.0 + i * 0.01, 10)

            # Submit 100 buy orders concurrently
            tasks = []
            for i in range(100):
                task = asyncio.create_task(
                    exchange.submit_order("AAPL", "BUY", "LIMIT", 100.0 + i * 0.01, 5)
                )
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # No exceptions should have occurred
            for r in results:
                self.assertNotIsInstance(r, Exception)

            return results

        results = asyncio.get_event_loop().run_until_complete(run_concurrent())
        self.assertEqual(len(results), 100)

    def test_concurrent_different_symbols(self):
        """Concurrent orders for different symbols should run independently."""
        exchange = Exchange(symbols=["AAPL", "GOOGL", "MSFT"])

        async def run_concurrent():
            tasks = []
            for symbol in ["AAPL", "GOOGL", "MSFT"]:
                for _ in range(20):
                    tasks.append(asyncio.create_task(
                        exchange.submit_order(symbol, "BUY", "LIMIT", 100.0, 10)
                    ))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                self.assertNotIsInstance(r, Exception)

            return results

        results = asyncio.get_event_loop().run_until_complete(run_concurrent())
        self.assertEqual(len(results), 60)

    def test_trade_ids_unique(self):
        """Trade IDs should be globally unique across symbols."""
        exchange = Exchange(symbols=["AAPL", "GOOGL"])

        async def run():
            # Create trades in AAPL
            await exchange.submit_order("AAPL", "SELL", "LIMIT", 100.0, 10)
            r1 = await exchange.submit_order("AAPL", "BUY", "LIMIT", 100.0, 10)

            # Create trades in GOOGL
            await exchange.submit_order("GOOGL", "SELL", "LIMIT", 100.0, 10)
            r2 = await exchange.submit_order("GOOGL", "BUY", "LIMIT", 100.0, 10)

            # Trade IDs should be different
            self.assertNotEqual(r1.trades[0].trade_id, r2.trades[0].trade_id)

        asyncio.get_event_loop().run_until_complete(run())


if __name__ == "__main__":
    unittest.main(verbosity=2)
