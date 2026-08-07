"""
main.py — Demo of the Order Matching Engine.

Run this file to see the engine in action with a realistic trading scenario.
"""

import time
from order import Side
from matching_engine import MatchingEngine


def print_trades(trades):
    """Print a list of trades."""
    if not trades:
        print("  No trades.")
        return
    for t in trades:
        print(f"  {t}")


def main():
    engine = MatchingEngine()

    print("=" * 60)
    print("  ORDER MATCHING ENGINE — LIVE DEMO")
    print("=" * 60)

    # ── Step 1: Build up the sell side ──
    print("\n--- Step 1: Adding SELL orders ---")
    engine.add_limit_order(Side.SELL, 102.00, 10)
    engine.add_limit_order(Side.SELL, 101.50, 15)
    engine.add_limit_order(Side.SELL, 101.00, 20)
    engine.add_limit_order(Side.SELL, 100.50, 5)
    engine.add_limit_order(Side.SELL, 100.50, 10)  # Two orders at same price
    print("  Added 5 sell orders at prices 100.50 to 102.00")

    # ── Step 2: Build up the buy side ──
    print("\n--- Step 2: Adding BUY orders ---")
    engine.add_limit_order(Side.BUY, 99.00, 10)
    engine.add_limit_order(Side.BUY, 99.50, 20)
    engine.add_limit_order(Side.BUY, 99.50, 15)  # Two orders at same price
    engine.add_limit_order(Side.BUY, 98.50, 25)
    print("  Added 4 buy orders at prices 98.50 to 99.50")

    # ── Show the book ──
    engine.print_book()
    print(f"  Best Bid: {engine.get_best_bid()}")
    print(f"  Best Ask: {engine.get_best_ask()}")
    print(f"  Spread:   {engine.get_best_ask() - engine.get_best_bid():.2f}")

    # ── Step 3: Aggressive buy sweeps through asks ──
    print("\n--- Step 3: Aggressive BUY order (30 shares at $101.50) ---")
    print("  This should sweep through $100.50 (15 shares) and $101.00 (15 shares)")
    order, trades = engine.add_limit_order(Side.BUY, 101.50, 30)
    print_trades(trades)
    engine.print_book()

    # ── Step 4: Cancel an order ──
    print("--- Step 4: Cancelling buy order at $98.50 ---")
    engine.cancel_order(10)  # The $98.50 buy
    if not engine.order_exists(10):
        print("  Order 10 successfully cancelled.")
    engine.print_book()

    # ── Step 5: Modify an order (quantity only — keeps FIFO) ──
    print("--- Step 5: Modify order — change quantity only ---")
    print("  Changing order 8 (BUY $99.50 qty=20) to qty=50")
    engine.modify_order(8, new_quantity=50)
    engine.print_book()

    # ── Step 6: Modify an order (price change — loses FIFO) ──
    print("--- Step 6: Modify order — change price ---")
    print("  Moving order 9 (BUY $99.50 qty=15) to $100.00")
    new_order, trades = engine.modify_order(9, new_price=100.00)
    print(f"  New order: {new_order}")
    print_trades(trades)
    engine.print_book()

    # ── Step 7: Aggressive sell ──
    print("--- Step 7: Aggressive SELL order (60 shares at $99.00) ---")
    order, trades = engine.add_limit_order(Side.SELL, 99.00, 60)
    print_trades(trades)
    engine.print_book()

    # ── Summary ──
    print("\n" + "=" * 60)
    print("  TRADE LOG")
    print("=" * 60)
    for t in engine.get_trade_log():
        print(f"  {t}")
    print(f"\n  Total trades: {len(engine.get_trade_log())}")
    print("=" * 60)


if __name__ == "__main__":
    main()
