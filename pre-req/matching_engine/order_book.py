"""
order_book.py — The Order Book.

The order book is the heart of any exchange. It holds two sides:
    - BIDS (buy orders)  — stored in a Red-Black Tree sorted by price
    - ASKS (sell orders)  — stored in a Red-Black Tree sorted by price

Best bid = highest buy price  (maximum of bids tree)
Best ask = lowest sell price  (minimum of asks tree)

For fast cancellation, we keep a hash map (Python dict) that maps:
    order_id -> (tree_node, dll_node, price_level)

So given an order_id, we can:
    1. Find the linked list node in O(1)
    2. Remove it from the linked list in O(1)
    3. If the price level is now empty, remove the tree node in O(log n)

Overall cancel is O(log n) worst case.
"""

from rb_tree import RBTree
from price_level import PriceLevel
from order import Side


class OrderBook:
    """
    Maintains buy and sell sides of the book using two Red-Black Trees.

    The _orders dict is the secret sauce for fast lookups:
        _orders[order_id] = (tree_node, dll_node, price_level)

    Complexity summary:
        add_order()      O(log n)   tree search + possible tree insert
        cancel_order()   O(log n)   O(1) lookup + O(1) DLL remove + O(log n) tree delete
        best_bid()       O(log n)   tree maximum
        best_ask()       O(log n)   tree minimum
        order_exists()   O(1)       hash map lookup
        get_order()      O(1)       hash map lookup
    """

    def __init__(self):
        self._bids = RBTree()    # Buy orders (want highest price first)
        self._asks = RBTree()    # Sell orders (want lowest price first)

        # Hash map for O(1) order lookup
        # Maps order_id -> (tree_node, dll_node, price_level)
        self._orders = {}

    # ── Best prices ──

    def best_bid(self):
        """
        Highest buy price. Buyers want to pay as much as needed,
        so the best bid is the MAX of the bids tree.
        Returns the tree node or None.
        """
        return self._bids.maximum()

    def best_ask(self):
        """
        Lowest sell price. Sellers want to sell for as little as needed,
        so the best ask is the MIN of the asks tree.
        Returns the tree node or None.
        """
        return self._asks.minimum()

    # ── Which tree does this side belong to? ──

    def _get_tree(self, side):
        """Return the correct RBTree for the given side."""
        if side == Side.BUY:
            return self._bids
        return self._asks

    # ── Add an order ──

    def add_order(self, order):
        """
        Add an order to the book.

        Steps:
        1. Pick the right tree (bids or asks).
        2. Find or create the price level for this price.
        3. Add the order to the price level's linked list.
        4. Store everything in the hash map for fast cancel.
        """
        tree = self._get_tree(order.side)

        # Check if a price level already exists at this price
        tree_node = tree.search(order.price)

        if tree_node is None:
            # No orders at this price yet — create a new price level
            price_level = PriceLevel(order.price)
            tree_node = tree.insert(order.price, price_level)
        else:
            price_level = tree_node.value

        # Add the order to the FIFO queue at this price level
        dll_node = price_level.add_order(order)

        # Save in hash map for O(1) lookup later
        self._orders[order.order_id] = (tree_node, dll_node, price_level)

    # ── Cancel an order ──

    def cancel_order(self, order_id):
        """
        Cancel an order by its ID.

        Steps:
        1. Look up the order in the hash map — O(1).
        2. Remove it from the linked list — O(1).
        3. If the price level is now empty, remove it from the tree — O(log n).
        """
        if order_id not in self._orders:
            return None

        tree_node, dll_node, price_level = self._orders.pop(order_id)
        order = dll_node.data

        # Remove from the linked list
        price_level.remove_order(dll_node)

        # If no more orders at this price, remove the price level from the tree
        if price_level.is_empty():
            tree = self._get_tree(order.side)
            tree.delete_node(tree_node)

        return order

    # ── Check if an order exists ──

    def order_exists(self, order_id):
        """Check if an order is still in the book."""
        return order_id in self._orders

    # ── Get an order ──

    def get_order(self, order_id):
        """Get an order by its ID. Returns None if not found."""
        if order_id not in self._orders:
            return None
        _, dll_node, _ = self._orders[order_id]
        return dll_node.data

    # ── Remove the front order from a price level (used during matching) ──

    def remove_front_order(self, side, price):
        """
        Remove the oldest order at the given price.
        Used by the matching engine after a full fill.
        """
        tree = self._get_tree(side)
        tree_node = tree.search(price)

        if tree_node is None:
            return None

        price_level = tree_node.value
        order = price_level.pop_front()

        # Clean up hash map
        if order.order_id in self._orders:
            del self._orders[order.order_id]

        # Clean up empty price level
        if price_level.is_empty():
            tree.delete_node(tree_node)

        return order

    # ── Find the price level node ──

    def find_price(self, side, price):
        """Find the RB tree node for a given price and side."""
        tree = self._get_tree(side)
        return tree.search(price)

    # ── Market depth ──

    def market_depth(self, levels=5):
        """
        Get the top N price levels on each side.

        Returns:
            bids: list of (price, volume, order_count) — highest first
            asks: list of (price, volume, order_count) — lowest first
        """
        # Bids: walk from max to min (highest prices first)
        bid_levels = []
        node = self._bids.maximum()
        while node is not None and len(bid_levels) < levels:
            pl = node.value
            bid_levels.append((pl.price, pl.volume(), pl.order_count()))
            node = self._bids.predecessor(node)

        # Asks: walk from min to max (lowest prices first)
        ask_levels = []
        node = self._asks.minimum()
        while node is not None and len(ask_levels) < levels:
            pl = node.value
            ask_levels.append((pl.price, pl.volume(), pl.order_count()))
            node = self._asks.successor(node)

        return bid_levels, ask_levels

    # ── Pretty print ──

    def print_book(self):
        """Print the order book in a readable format."""
        bids, asks = self.market_depth(levels=20)

        print("\n" + "=" * 50)
        print("            ORDER BOOK")
        print("=" * 50)

        # Print asks in reverse so lowest ask is at the bottom (near the spread)
        print("  ASKS (sell orders):")
        if not asks:
            print("    (empty)")
        for price, vol, count in reversed(asks):
            print(f"    ${price:>10.2f}  |  vol: {vol:<6}  |  orders: {count}")

        print("  " + "-" * 46)
        print("  >>> SPREAD <<<")
        print("  " + "-" * 46)

        print("  BIDS (buy orders):")
        if not bids:
            print("    (empty)")
        for price, vol, count in bids:
            print(f"    ${price:>10.2f}  |  vol: {vol:<6}  |  orders: {count}")

        print("=" * 50 + "\n")

    def __repr__(self):
        bid = self.best_bid()
        ask = self.best_ask()
        bid_price = bid.key if bid else None
        ask_price = ask.key if ask else None
        return f"OrderBook(best_bid={bid_price}, best_ask={ask_price})"
