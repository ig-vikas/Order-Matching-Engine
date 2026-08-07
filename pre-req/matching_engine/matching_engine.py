"""
matching_engine.py — The Matching Engine.

This is the top-level class that ties everything together.
It receives orders from the outside world and:

    1. Tries to match incoming orders against resting orders (price-time priority)
    2. Generates Trade objects for every fill
    3. Places any unmatched remainder into the order book

Matching Rules (Price-Time Priority):
    - Incoming BUY matches against the lowest SELL prices first
    - Incoming SELL matches against the highest BUY prices first
    - At the same price, oldest order fills first (FIFO)
    - Trade price = resting order's price (the one already in the book)
    - Partial fills are supported (reduce quantity, keep the rest in the book)
"""

import time
from order import Order, Trade, Side
from order_book import OrderBook


class MatchingEngine:
    """
    The main matching engine.

    Usage:
        engine = MatchingEngine()
        trades = engine.add_limit_order(Side.BUY, 100.0, 10)
        engine.cancel_order(order_id)
        engine.modify_order(order_id, new_price=101.0, new_quantity=5)

    Complexity:
        add_limit_order()   O(m * log n)   where m = number of price levels matched
        cancel_order()      O(log n)       hash lookup + DLL remove + possible tree delete
        modify_order()      O(log n)       cancel + re-insert (if price changes)
        get_best_bid()      O(log n)       tree maximum
        get_best_ask()      O(log n)       tree minimum
        order_exists()      O(1)           hash map lookup
    """

    def __init__(self):
        self.book = OrderBook()
        self._next_order_id = 1      # Auto-incrementing order ID
        self._trade_log = []         # History of all trades

    # ══════════════════════════════════════════════════════════
    #  ADD LIMIT ORDER
    # ══════════════════════════════════════════════════════════

    def add_limit_order(self, side, price, quantity):
        """
        Submit a new limit order.

        Steps:
        1. Create the Order object.
        2. Try to match it against the opposite side of the book.
        3. If there's any remaining quantity, add it to the book.
        4. Return (order, list of trades).
        """
        order = Order(
            order_id=self._next_order_id,
            side=side,
            price=price,
            quantity=quantity,
            timestamp=time.time(),
        )
        self._next_order_id += 1

        # Try to match against the opposite side
        trades = self._match(order)

        # If the order still has remaining quantity, add to book
        if order.quantity > 0:
            self.book.add_order(order)

        return order, trades

    # ══════════════════════════════════════════════════════════
    #  MATCHING
    # ══════════════════════════════════════════════════════════

    def _match(self, incoming):
        """
        Match an incoming order against resting orders.

        For a BUY order:
            - Look at the best ask (lowest sell price)
            - If incoming.price >= best_ask.price, we have a match
            - Fill at the resting order's price

        For a SELL order:
            - Look at the best bid (highest buy price)
            - If incoming.price <= best_bid.price, we have a match
            - Fill at the resting order's price

        Keep matching until:
            - Incoming order is fully filled (quantity = 0), or
            - No more crossing prices
        """
        trades = []

        while incoming.quantity > 0:
            # Find the best resting order on the opposite side
            if incoming.side == Side.BUY:
                best_node = self.book.best_ask()
            else:
                best_node = self.book.best_bid()

            # No resting orders on the opposite side
            if best_node is None:
                break

            best_price = best_node.key

            # Check if prices cross
            if incoming.side == Side.BUY and incoming.price < best_price:
                break  # Buy price is too low
            if incoming.side == Side.SELL and incoming.price > best_price:
                break  # Sell price is too high

            # Get the price level and the oldest order there
            price_level = best_node.value
            resting = price_level.peek()

            # Figure out how many shares to trade
            fill_qty = min(incoming.quantity, resting.quantity)

            # Determine buy and sell order IDs for the trade
            if incoming.side == Side.BUY:
                buy_id = incoming.order_id
                sell_id = resting.order_id
            else:
                buy_id = resting.order_id
                sell_id = incoming.order_id

            # Create the trade (price = resting order's price)
            trade = Trade(
                buy_order_id=buy_id,
                sell_order_id=sell_id,
                price=best_price,
                quantity=fill_qty,
                timestamp=time.time(),
            )
            trades.append(trade)
            self._trade_log.append(trade)

            # Update quantities
            incoming.quantity -= fill_qty
            resting.quantity -= fill_qty

            # If the resting order is fully filled, remove it from the book
            if resting.quantity == 0:
                self.book.remove_front_order(resting.side, best_price)

        return trades

    # ══════════════════════════════════════════════════════════
    #  CANCEL ORDER
    # ══════════════════════════════════════════════════════════

    def cancel_order(self, order_id):
        """
        Cancel an existing order.
        Returns the cancelled order, or None if not found.
        """
        return self.book.cancel_order(order_id)

    # ══════════════════════════════════════════════════════════
    #  MODIFY ORDER
    # ══════════════════════════════════════════════════════════

    def modify_order(self, order_id, new_price=None, new_quantity=None):
        """
        Modify an existing order.

        Rules:
        - If price changes: cancel old order, insert new one (loses FIFO priority)
        - If only quantity changes: keep same position in the queue
        - Returns (new_order, trades) if price changed, (existing_order, []) if only qty changed
        """
        old_order = self.book.get_order(order_id)
        if old_order is None:
            return None, []

        price_changed = (new_price is not None and new_price != old_order.price)

        if price_changed:
            # Price changed — cancel and re-insert (new timestamp = new FIFO position)
            side = old_order.side
            qty = new_quantity if new_quantity is not None else old_order.quantity
            price = new_price

            self.book.cancel_order(order_id)
            return self.add_limit_order(side, price, qty)

        elif new_quantity is not None and new_quantity != old_order.quantity:
            # Only quantity changed — keep same FIFO position
            if new_quantity <= 0:
                # Treat as cancellation
                return self.book.cancel_order(order_id), []
            old_order.quantity = new_quantity
            return old_order, []

        else:
            # Nothing changed
            return old_order, []

    # ══════════════════════════════════════════════════════════
    #  QUERIES
    # ══════════════════════════════════════════════════════════

    def get_best_bid(self):
        """Get the highest buy price, or None if no bids."""
        node = self.book.best_bid()
        return node.key if node else None

    def get_best_ask(self):
        """Get the lowest sell price, or None if no asks."""
        node = self.book.best_ask()
        return node.key if node else None

    def market_depth(self, levels=5):
        """Get the top N price levels on each side."""
        return self.book.market_depth(levels)

    def order_exists(self, order_id):
        """Check if an order is still active in the book."""
        return self.book.order_exists(order_id)

    def get_trade_log(self):
        """Get all trades that have been executed."""
        return list(self._trade_log)

    def print_book(self):
        """Print the current state of the order book."""
        self.book.print_book()
