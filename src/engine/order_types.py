"""
order_types.py — Extended order type support on top of the existing MatchingEngine.

The existing MatchingEngine only supports LIMIT orders.
This module adds MARKET, IOC, and FOK by wrapping the existing LIMIT logic.

Design approach:
    - We do NOT modify the existing MatchingEngine class.
    - Instead, we compose it: each order type handler calls add_limit_order()
      with the right parameters and post-processes the result.

Key tricks:
    MARKET:  Submit as LIMIT with an extreme price (inf for BUY, 0 for SELL).
             This guarantees it crosses every resting order. Cancel any
             unfilled remainder — market orders never rest in the book.

    IOC:     Submit as LIMIT normally. Cancel any unfilled remainder.
             (Same as MARKET but with a price cap.)

    FOK:     BEFORE submitting, walk the book to check if there's enough
             liquidity. If yes, submit as LIMIT (guaranteed full fill).
             If no, reject entirely — nothing touches the book.
"""

import sys
import os

# Add the pre-req engine to Python path so we can import it
_ENGINE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "pre-req", "matching_engine")
_ENGINE_PATH = os.path.abspath(_ENGINE_PATH)
if _ENGINE_PATH not in sys.path:
    sys.path.insert(0, _ENGINE_PATH)

from order import Order, Trade, Side
from matching_engine import MatchingEngine


class OrderTypeHandler:
    """
    Handles all order types by delegating to the existing MatchingEngine.

    Usage:
        handler = OrderTypeHandler()
        engine = MatchingEngine()

        # LIMIT — direct passthrough
        order, trades = handler.submit_limit(engine, Side.BUY, 100.0, 10)

        # MARKET — extreme price trick
        order, trades = handler.submit_market(engine, Side.BUY, 10)

        # IOC — fill-what-you-can, cancel the rest
        order, trades = handler.submit_ioc(engine, Side.BUY, 100.0, 10)

        # FOK — all or nothing
        order, trades = handler.submit_fok(engine, Side.BUY, 100.0, 10)
    """

    # ══════════════════════════════════════════════════════════
    #  LIMIT ORDER — direct passthrough
    # ══════════════════════════════════════════════════════════

    def submit_limit(self, engine: MatchingEngine, side: Side, price: float, quantity: int):
        """
        Submit a standard limit order.

        Behavior:
            - Match against the opposite side if prices cross
            - Any unmatched remainder rests in the book at the limit price
            - Returns (order, trades)

        This is just a direct call to the existing engine — no extra logic needed.
        """
        return engine.add_limit_order(side, price, quantity)

    # ══════════════════════════════════════════════════════════
    #  MARKET ORDER — extreme price trick
    # ══════════════════════════════════════════════════════════

    def submit_market(self, engine: MatchingEngine, side: Side, quantity: int):
        """
        Submit a market order — execute immediately at best available price.

        Implementation trick:
            - BUY:  Submit as LIMIT at price = 999999999.0 (crosses every ask)
            - SELL: Submit as LIMIT at price = 0.01       (crosses every bid)

            After matching, cancel any unfilled remainder because market orders
            should never rest in the book.

        Why not float('inf')?
            The RB-Tree uses numeric comparison. While Python handles inf fine,
            we use a large finite number for safety and debuggability.

        Returns (order, trades)
        """
        # Use an extreme price to ensure we cross everything
        if side == Side.BUY:
            extreme_price = 999999999.0
        else:
            extreme_price = 0.01  # Lowest sensible price (can't be 0 — division issues)

        order, trades = engine.add_limit_order(side, extreme_price, quantity)

        # Cancel any unfilled remainder — market orders don't rest
        if order.quantity > 0 and engine.order_exists(order.order_id):
            engine.cancel_order(order.order_id)

        return order, trades

    # ══════════════════════════════════════════════════════════
    #  IOC — Immediate-Or-Cancel
    # ══════════════════════════════════════════════════════════

    def submit_ioc(self, engine: MatchingEngine, side: Side, price: float, quantity: int):
        """
        Submit an Immediate-Or-Cancel order.

        Behavior:
            - Try to fill as much as possible at the limit price or better
            - Cancel any unfilled remainder immediately
            - The order NEVER rests in the book

        This is exactly like a LIMIT order, but we cancel the remainder.

        Returns (order, trades)
        """
        order, trades = engine.add_limit_order(side, price, quantity)

        # Cancel any unfilled remainder — IOC orders don't rest
        if order.quantity > 0 and engine.order_exists(order.order_id):
            engine.cancel_order(order.order_id)

        return order, trades

    # ══════════════════════════════════════════════════════════
    #  FOK — Fill-Or-Kill
    # ══════════════════════════════════════════════════════════

    def submit_fok(self, engine: MatchingEngine, side: Side, price: float, quantity: int):
        """
        Submit a Fill-Or-Kill order.

        Behavior:
            - Check if there's enough liquidity at the limit price BEFORE submitting
            - If yes: submit as LIMIT (guaranteed full fill since we checked)
            - If no: reject entirely — NOTHING touches the book

        The liquidity check is read-only — it walks the opposite side of the book
        without modifying anything.

        Returns (order, trades) on success, (None, []) on rejection.
        """
        # Step 1: Check if there's enough liquidity (read-only)
        if not self._check_fok_fillable(engine, side, price, quantity):
            return None, []

        # Step 2: We have enough liquidity — submit as LIMIT
        # Since we verified there's enough volume, this should fully fill
        order, trades = engine.add_limit_order(side, price, quantity)

        # Safety net: if somehow not fully filled (shouldn't happen), cancel remainder
        if order.quantity > 0 and engine.order_exists(order.order_id):
            engine.cancel_order(order.order_id)

        return order, trades

    def _check_fok_fillable(self, engine: MatchingEngine, side: Side, price: float, quantity: int) -> bool:
        """
        Walk the opposite side of the book to check if there's enough liquidity
        at the given price or better.

        For a BUY at price P:
            Walk asks from lowest up. Count volume at ask_price <= P.
            If total available >= quantity, it's fillable.

        For a SELL at price P:
            Walk bids from highest down. Count volume at bid_price >= P.
            If total available >= quantity, it's fillable.

        This is a READ-ONLY operation — it does not modify the book.
        """
        available = 0

        if side == Side.BUY:
            # Walk asks (lowest first) — these are the orders we'd match against
            node = engine.book.best_ask()
            while node is not None and node.key <= price:
                available += node.value.volume()
                if available >= quantity:
                    return True  # Early exit — we have enough
                node = engine.book._asks.successor(node)
        else:
            # Walk bids (highest first) — these are the orders we'd match against
            node = engine.book.best_bid()
            while node is not None and node.key >= price:
                available += node.value.volume()
                if available >= quantity:
                    return True  # Early exit
                node = engine.book._bids.predecessor(node)

        return available >= quantity
