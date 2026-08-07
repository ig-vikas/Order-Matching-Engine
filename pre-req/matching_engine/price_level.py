"""
price_level.py — A single price level in the order book.

A price level holds all orders at the same price in FIFO order.
Internally it's just a wrapper around our DoublyLinkedList.

Example: at price 100.50 there might be 3 orders:
    [Order A (qty 10)] -> [Order B (qty 5)] -> [Order C (qty 20)]

Order A came first, so it gets filled first (FIFO / time priority).
"""

from linked_list import DoublyLinkedList


class PriceLevel:
    """
    All orders at a single price, stored in FIFO order.

    Methods:
        add_order(order)     - append to back of the queue       O(1)
        remove_order(node)   - remove by DLL node reference      O(1)
        peek()               - look at the oldest order           O(1)
        is_empty()           - check if no orders remain          O(1)
        volume()             - total quantity at this price       O(k) where k = orders at price
    """

    def __init__(self, price):
        self.price = price
        self.orders = DoublyLinkedList()

    def add_order(self, order):
        """
        Add an order to the back of the FIFO queue.
        Returns the DLL node (save this for O(1) cancellation).
        """
        return self.orders.append(order)

    def remove_order(self, dll_node):
        """Remove a specific order given its linked list node."""
        return self.orders.remove(dll_node)

    def peek(self):
        """Look at the oldest order without removing it."""
        return self.orders.peek_front()

    def pop_front(self):
        """Remove and return the oldest order (used during matching)."""
        return self.orders.pop_front()

    def is_empty(self):
        """Check if there are no orders at this price level."""
        return self.orders.is_empty()

    def volume(self):
        """Total number of shares across all orders at this price."""
        total = 0
        for order in self.orders:
            total += order.quantity
        return total

    def order_count(self):
        """Number of orders at this price level."""
        return len(self.orders)

    def __repr__(self):
        return f"PriceLevel(price={self.price}, orders={self.order_count()}, vol={self.volume()})"
