"""
test_order_types.py — Tests for MARKET, IOC, FOK order types.

These tests verify that the new order type wrappers correctly implement:
    - MARKET: fills at best available, never rests in book
    - IOC:    fills what it can, cancels remainder
    - FOK:    all-or-nothing, rejects if insufficient liquidity

Every test uses the real MatchingEngine — no mocks.
"""

import sys
import os
import unittest

# Add paths so we can import both the engine and our new code
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_ENGINE_PATH = os.path.join(_PROJECT_ROOT, "pre-req", "matching_engine")
_SRC_PATH = os.path.join(_PROJECT_ROOT, "src")

for p in [_ENGINE_PATH, _SRC_PATH, _PROJECT_ROOT]:
    if p not in sys.path:
        sys.path.insert(0, p)

from order import Side
from matching_engine import MatchingEngine
from engine.order_types import OrderTypeHandler


class TestLimitPassthrough(unittest.TestCase):
    """Verify LIMIT orders still work identically through the handler."""

    def setUp(self):
        self.engine = MatchingEngine()
        self.handler = OrderTypeHandler()

    def test_limit_no_match(self):
        """LIMIT order that doesn't cross should rest in the book."""
        order, trades = self.handler.submit_limit(self.engine, Side.BUY, 99.0, 10)
        self.assertEqual(len(trades), 0)
        self.assertEqual(self.engine.get_best_bid(), 99.0)
        self.assertTrue(self.engine.order_exists(order.order_id))

    def test_limit_match(self):
        """LIMIT order that crosses should produce trades."""
        self.handler.submit_limit(self.engine, Side.SELL, 100.0, 10)
        order, trades = self.handler.submit_limit(self.engine, Side.BUY, 100.0, 10)
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].price, 100.0)
        self.assertEqual(trades[0].quantity, 10)

    def test_limit_partial_fill_rests(self):
        """LIMIT partial fill: remainder stays in book."""
        self.handler.submit_limit(self.engine, Side.SELL, 100.0, 5)
        order, trades = self.handler.submit_limit(self.engine, Side.BUY, 100.0, 10)
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].quantity, 5)
        # 5 shares remain as a bid
        self.assertEqual(self.engine.get_best_bid(), 100.0)
        self.assertTrue(self.engine.order_exists(order.order_id))


class TestMarketOrder(unittest.TestCase):
    """Test MARKET order behavior."""

    def setUp(self):
        self.engine = MatchingEngine()
        self.handler = OrderTypeHandler()

    def test_market_buy_fills_at_best_ask(self):
        """MARKET BUY should fill at the best ask price."""
        self.handler.submit_limit(self.engine, Side.SELL, 100.0, 10)
        order, trades = self.handler.submit_market(self.engine, Side.BUY, 10)

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].price, 100.0)  # Fills at resting price
        self.assertEqual(trades[0].quantity, 10)

    def test_market_sell_fills_at_best_bid(self):
        """MARKET SELL should fill at the best bid price."""
        self.handler.submit_limit(self.engine, Side.BUY, 100.0, 10)
        order, trades = self.handler.submit_market(self.engine, Side.SELL, 10)

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].price, 100.0)
        self.assertEqual(trades[0].quantity, 10)

    def test_market_buy_sweeps_multiple_levels(self):
        """MARKET BUY should sweep through all ask levels."""
        self.handler.submit_limit(self.engine, Side.SELL, 100.0, 5)
        self.handler.submit_limit(self.engine, Side.SELL, 101.0, 5)
        self.handler.submit_limit(self.engine, Side.SELL, 102.0, 5)

        order, trades = self.handler.submit_market(self.engine, Side.BUY, 12)

        self.assertEqual(len(trades), 3)
        self.assertEqual(trades[0].price, 100.0)
        self.assertEqual(trades[0].quantity, 5)
        self.assertEqual(trades[1].price, 101.0)
        self.assertEqual(trades[1].quantity, 5)
        self.assertEqual(trades[2].price, 102.0)
        self.assertEqual(trades[2].quantity, 2)

    def test_market_no_liquidity(self):
        """MARKET BUY with no asks should produce no trades and not rest."""
        order, trades = self.handler.submit_market(self.engine, Side.BUY, 10)

        self.assertEqual(len(trades), 0)
        # The order should NOT be resting in the book
        self.assertIsNone(self.engine.get_best_bid())

    def test_market_partial_fill_does_not_rest(self):
        """MARKET partial fill: remainder is cancelled, not resting."""
        self.handler.submit_limit(self.engine, Side.SELL, 100.0, 5)
        order, trades = self.handler.submit_market(self.engine, Side.BUY, 10)

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].quantity, 5)
        # Remaining 5 shares should NOT be in the book
        self.assertIsNone(self.engine.get_best_bid())
        self.assertFalse(self.engine.order_exists(order.order_id))

    def test_market_sell_sweeps_bids_highest_first(self):
        """MARKET SELL should match highest bids first."""
        self.handler.submit_limit(self.engine, Side.BUY, 98.0, 5)
        self.handler.submit_limit(self.engine, Side.BUY, 100.0, 5)
        self.handler.submit_limit(self.engine, Side.BUY, 99.0, 5)

        order, trades = self.handler.submit_market(self.engine, Side.SELL, 7)

        # Should hit $100 first (5 shares), then $99 (2 shares)
        self.assertEqual(trades[0].price, 100.0)
        self.assertEqual(trades[0].quantity, 5)
        self.assertEqual(trades[1].price, 99.0)
        self.assertEqual(trades[1].quantity, 2)


class TestIOCOrder(unittest.TestCase):
    """Test Immediate-Or-Cancel order behavior."""

    def setUp(self):
        self.engine = MatchingEngine()
        self.handler = OrderTypeHandler()

    def test_ioc_full_fill(self):
        """IOC with enough liquidity should fill completely."""
        self.handler.submit_limit(self.engine, Side.SELL, 100.0, 10)
        order, trades = self.handler.submit_ioc(self.engine, Side.BUY, 100.0, 10)

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].quantity, 10)

    def test_ioc_partial_fill_cancels_remainder(self):
        """IOC partial fill: remainder is cancelled, not resting."""
        self.handler.submit_limit(self.engine, Side.SELL, 100.0, 5)
        order, trades = self.handler.submit_ioc(self.engine, Side.BUY, 100.0, 10)

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].quantity, 5)
        # Remaining 5 shares should NOT be in the book
        self.assertIsNone(self.engine.get_best_bid())
        self.assertFalse(self.engine.order_exists(order.order_id))

    def test_ioc_no_liquidity(self):
        """IOC with no matching orders produces nothing and doesn't rest."""
        order, trades = self.handler.submit_ioc(self.engine, Side.BUY, 100.0, 10)

        self.assertEqual(len(trades), 0)
        self.assertIsNone(self.engine.get_best_bid())

    def test_ioc_price_limit_respected(self):
        """IOC should not fill above the limit price."""
        self.handler.submit_limit(self.engine, Side.SELL, 100.0, 5)
        self.handler.submit_limit(self.engine, Side.SELL, 105.0, 5)

        # IOC BUY at $102 — should only fill the $100 ask
        order, trades = self.handler.submit_ioc(self.engine, Side.BUY, 102.0, 10)

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].price, 100.0)
        self.assertEqual(trades[0].quantity, 5)
        # Remainder cancelled, $105 ask untouched
        self.assertFalse(self.engine.order_exists(order.order_id))
        self.assertEqual(self.engine.get_best_ask(), 105.0)

    def test_ioc_never_rests_in_book(self):
        """No matter what, an IOC order should never be resting in the book after execution."""
        # Empty book — IOC should not rest
        order, trades = self.handler.submit_ioc(self.engine, Side.SELL, 50.0, 100)
        self.assertIsNone(self.engine.get_best_ask())


class TestFOKOrder(unittest.TestCase):
    """Test Fill-Or-Kill order behavior."""

    def setUp(self):
        self.engine = MatchingEngine()
        self.handler = OrderTypeHandler()

    def test_fok_full_fill(self):
        """FOK with enough liquidity should fill completely."""
        self.handler.submit_limit(self.engine, Side.SELL, 100.0, 10)
        order, trades = self.handler.submit_fok(self.engine, Side.BUY, 100.0, 10)

        self.assertIsNotNone(order)
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].quantity, 10)

    def test_fok_insufficient_liquidity_rejects(self):
        """FOK with not enough liquidity should reject entirely."""
        self.handler.submit_limit(self.engine, Side.SELL, 100.0, 5)
        order, trades = self.handler.submit_fok(self.engine, Side.BUY, 100.0, 10)

        # Rejected — nothing happened
        self.assertIsNone(order)
        self.assertEqual(len(trades), 0)
        # The existing sell order should still be untouched
        self.assertEqual(self.engine.get_best_ask(), 100.0)

    def test_fok_no_liquidity_rejects(self):
        """FOK with empty book should reject."""
        order, trades = self.handler.submit_fok(self.engine, Side.BUY, 100.0, 10)

        self.assertIsNone(order)
        self.assertEqual(len(trades), 0)

    def test_fok_exact_liquidity(self):
        """FOK where available volume == requested quantity should fill."""
        self.handler.submit_limit(self.engine, Side.SELL, 100.0, 3)
        self.handler.submit_limit(self.engine, Side.SELL, 101.0, 7)

        # FOK BUY for 10 at $101 — exactly 10 shares available
        order, trades = self.handler.submit_fok(self.engine, Side.BUY, 101.0, 10)

        self.assertIsNotNone(order)
        self.assertEqual(sum(t.quantity for t in trades), 10)

    def test_fok_price_limit_restricts_liquidity(self):
        """FOK should only count liquidity AT or BETTER than the limit price."""
        self.handler.submit_limit(self.engine, Side.SELL, 100.0, 5)
        self.handler.submit_limit(self.engine, Side.SELL, 105.0, 10)

        # FOK BUY at $102 — only 5 shares available at or below $102
        order, trades = self.handler.submit_fok(self.engine, Side.BUY, 102.0, 10)

        # Should reject — only 5 available within price limit
        self.assertIsNone(order)
        self.assertEqual(len(trades), 0)

    def test_fok_sell_sufficient_bids(self):
        """FOK SELL with enough bids should fill."""
        self.handler.submit_limit(self.engine, Side.BUY, 100.0, 10)
        self.handler.submit_limit(self.engine, Side.BUY, 99.0, 10)

        order, trades = self.handler.submit_fok(self.engine, Side.SELL, 99.0, 15)

        self.assertIsNotNone(order)
        self.assertEqual(sum(t.quantity for t in trades), 15)

    def test_fok_sell_insufficient_bids_rejects(self):
        """FOK SELL with not enough bids should reject."""
        self.handler.submit_limit(self.engine, Side.BUY, 100.0, 5)

        order, trades = self.handler.submit_fok(self.engine, Side.SELL, 100.0, 10)

        self.assertIsNone(order)
        self.assertEqual(len(trades), 0)
        # Existing bid untouched
        self.assertEqual(self.engine.get_best_bid(), 100.0)

    def test_fok_does_not_leave_residue(self):
        """A rejected FOK should leave the book completely unchanged."""
        # Set up a book
        self.handler.submit_limit(self.engine, Side.SELL, 100.0, 5)
        self.handler.submit_limit(self.engine, Side.BUY, 98.0, 5)

        # Capture state before
        best_bid_before = self.engine.get_best_bid()
        best_ask_before = self.engine.get_best_ask()
        trades_before = len(self.engine.get_trade_log())

        # Submit FOK that will be rejected
        self.handler.submit_fok(self.engine, Side.BUY, 100.0, 100)

        # State should be identical
        self.assertEqual(self.engine.get_best_bid(), best_bid_before)
        self.assertEqual(self.engine.get_best_ask(), best_ask_before)
        self.assertEqual(len(self.engine.get_trade_log()), trades_before)


class TestOrderTypeMixedSequence(unittest.TestCase):
    """Test interactions between different order types in sequence."""

    def setUp(self):
        self.engine = MatchingEngine()
        self.handler = OrderTypeHandler()

    def test_limit_then_market(self):
        """LIMIT resting, then MARKET fills against it."""
        self.handler.submit_limit(self.engine, Side.SELL, 100.0, 10)
        _, trades = self.handler.submit_market(self.engine, Side.BUY, 5)

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].quantity, 5)
        # 5 shares remain at $100
        self.assertEqual(self.engine.get_best_ask(), 100.0)

    def test_ioc_then_fok(self):
        """IOC partially fills, then FOK checks remaining liquidity."""
        self.handler.submit_limit(self.engine, Side.SELL, 100.0, 10)

        # IOC takes 7 shares
        self.handler.submit_ioc(self.engine, Side.BUY, 100.0, 7)

        # FOK for 5 — only 3 left, should reject
        order, trades = self.handler.submit_fok(self.engine, Side.BUY, 100.0, 5)
        self.assertIsNone(order)

        # FOK for 3 — exactly enough, should fill
        order, trades = self.handler.submit_fok(self.engine, Side.BUY, 100.0, 3)
        self.assertIsNotNone(order)
        self.assertEqual(trades[0].quantity, 3)

    def test_conservation_of_quantity(self):
        """Total filled across all trades should equal total matched."""
        self.handler.submit_limit(self.engine, Side.SELL, 100.0, 20)

        # MARKET takes 5
        self.handler.submit_market(self.engine, Side.BUY, 5)
        # IOC takes 3
        self.handler.submit_ioc(self.engine, Side.BUY, 100.0, 3)
        # LIMIT takes 7
        self.handler.submit_limit(self.engine, Side.BUY, 100.0, 7)

        total_traded = sum(t.quantity for t in self.engine.get_trade_log())
        self.assertEqual(total_traded, 15)  # 5 + 3 + 7


if __name__ == "__main__":
    unittest.main(verbosity=2)
