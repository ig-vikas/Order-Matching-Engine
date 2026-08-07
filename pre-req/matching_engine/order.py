"""
order.py — Order, Trade, and Side definitions.

These are the basic building blocks of the matching engine.
Every order that enters the system becomes an Order object.
Every executed match produces a Trade object.

All operations here are O(1) — just creating objects and reading fields.
"""

from enum import Enum


class Side(Enum):
    """BUY or SELL — the direction of an order."""
    BUY = "BUY"
    SELL = "SELL"

    def __str__(self):
        return self.value


class Order:
    """
    Represents a single limit order.

    Fields:
        order_id  - unique ID for this order
        side      - BUY or SELL
        price     - limit price (max willing to pay for BUY, min willing to accept for SELL)
        quantity  - number of shares (gets decremented on partial fills)
        timestamp - when the order was placed (used for FIFO tiebreaking)
    """

    def __init__(self, order_id, side, price, quantity, timestamp):
        self.order_id = order_id    # Unique ID assigned by the engine
        self.side = side            # BUY or SELL
        self.price = price          # Limit price
        self.quantity = quantity    # Shares remaining (MUTABLE — decremented on partial fills)
        self.timestamp = timestamp  # Used for FIFO tiebreaking (earliest wins)

    def __repr__(self):
        return (f"Order(id={self.order_id}, {self.side}, "
                f"price={self.price}, qty={self.quantity})")


class Trade:
    """
    Represents an executed trade between a buy and sell order.

    The price is always the resting order's price (the order that was
    already sitting in the book, not the incoming aggressor).
    """

    def __init__(self, buy_order_id, sell_order_id, price, quantity, timestamp):
        self.buy_order_id = buy_order_id    # The buyer in this trade
        self.sell_order_id = sell_order_id  # The seller in this trade
        self.price = price                  # Execution price (= resting order's price)
        self.quantity = quantity            # Shares traded
        self.timestamp = timestamp          # When the trade happened

    def __repr__(self):
        return (f"Trade(buy={self.buy_order_id}, sell={self.sell_order_id}, "
                f"price={self.price}, qty={self.quantity})")
