"""
tests.py — Comprehensive test suite for the Order Matching Engine.

Tests cover:
    - Red-Black Tree operations and invariants
    - Doubly Linked List operations
    - Price Level FIFO ordering
    - Order Book add/cancel/modify
    - Matching engine: full fills, partial fills, price crossing
    - Market depth
    - Stress test with 10,000+ random orders
"""

import unittest
import random
import time

from rb_tree import RBTree, RED, BLACK
from linked_list import DoublyLinkedList
from order import Order, Trade, Side
from price_level import PriceLevel
from order_book import OrderBook
from matching_engine import MatchingEngine


# ══════════════════════════════════════════════════════════════
#  RED-BLACK TREE TESTS
# ══════════════════════════════════════════════════════════════

class TestRBTree(unittest.TestCase):
    """Test the Red-Black Tree implementation."""

    def test_insert_single(self):
        """Insert one node — it should be the root and BLACK."""
        tree = RBTree()
        tree.insert(10)
        self.assertEqual(tree.root.key, 10)
        self.assertEqual(tree.root.color, BLACK)
        tree.validate()

    def test_insert_multiple(self):
        """Insert several keys and verify tree is valid after each."""
        tree = RBTree()
        keys = [10, 20, 30, 15, 25, 5, 1]
        for k in keys:
            tree.insert(k)
            tree.validate()
        self.assertEqual(len(tree), len(keys))

    def test_insert_sorted_order(self):
        """Inserting sorted keys is the worst case for BST but RBTree handles it."""
        tree = RBTree()
        for i in range(1, 51):
            tree.insert(i)
            tree.validate()
        self.assertEqual(len(tree), 50)

    def test_insert_reverse_sorted(self):
        """Reverse sorted insertion."""
        tree = RBTree()
        for i in range(50, 0, -1):
            tree.insert(i)
            tree.validate()
        self.assertEqual(len(tree), 50)

    def test_search_found(self):
        """Search for keys that exist."""
        tree = RBTree()
        for k in [5, 10, 15, 20, 25]:
            tree.insert(k, f"val_{k}")
        node = tree.search(15)
        self.assertIsNotNone(node)
        self.assertEqual(node.key, 15)
        self.assertEqual(node.value, "val_15")

    def test_search_not_found(self):
        """Search for a key that doesn't exist."""
        tree = RBTree()
        for k in [5, 10, 15]:
            tree.insert(k)
        self.assertIsNone(tree.search(99))

    def test_minimum_maximum(self):
        """Min and max should return the smallest and largest keys."""
        tree = RBTree()
        keys = [30, 10, 50, 20, 40]
        for k in keys:
            tree.insert(k)
        self.assertEqual(tree.minimum().key, 10)
        self.assertEqual(tree.maximum().key, 50)

    def test_successor_predecessor(self):
        """Test in-order successor and predecessor."""
        tree = RBTree()
        for k in [10, 20, 30, 40, 50]:
            tree.insert(k)

        node20 = tree.search(20)
        self.assertEqual(tree.successor(node20).key, 30)
        self.assertEqual(tree.predecessor(node20).key, 10)

        # Successor of max is None
        node50 = tree.search(50)
        self.assertIsNone(tree.successor(node50))

        # Predecessor of min is None
        node10 = tree.search(10)
        self.assertIsNone(tree.predecessor(node10))

    def test_delete_leaf(self):
        """Delete a leaf node."""
        tree = RBTree()
        for k in [10, 5, 15]:
            tree.insert(k)
        tree.delete(5)
        tree.validate()
        self.assertIsNone(tree.search(5))
        self.assertEqual(len(tree), 2)

    def test_delete_node_with_one_child(self):
        """Delete a node that has one child."""
        tree = RBTree()
        for k in [10, 5, 15, 12]:
            tree.insert(k)
        tree.delete(15)
        tree.validate()
        self.assertIsNone(tree.search(15))

    def test_delete_node_with_two_children(self):
        """Delete a node that has two children (needs successor swap)."""
        tree = RBTree()
        for k in [10, 5, 15, 3, 7, 12, 20]:
            tree.insert(k)
        tree.delete(10)
        tree.validate()
        self.assertIsNone(tree.search(10))
        # All other keys should still be there
        for k in [5, 15, 3, 7, 12, 20]:
            self.assertIsNotNone(tree.search(k))

    def test_delete_root(self):
        """Delete the root node."""
        tree = RBTree()
        for k in [10, 5, 15]:
            tree.insert(k)
        tree.delete(10)
        tree.validate()
        self.assertIsNone(tree.search(10))
        self.assertEqual(len(tree), 2)

    def test_delete_all(self):
        """Delete all nodes one by one."""
        tree = RBTree()
        keys = [10, 5, 15, 3, 7, 12, 20, 1, 4, 6, 8]
        for k in keys:
            tree.insert(k)

        random.shuffle(keys)
        for k in keys:
            tree.delete(k)
            tree.validate()

        self.assertTrue(tree.is_empty())
        self.assertEqual(len(tree), 0)

    def test_delete_nonexistent(self):
        """Deleting a key that doesn't exist should return None."""
        tree = RBTree()
        tree.insert(10)
        result = tree.delete(99)
        self.assertIsNone(result)
        self.assertEqual(len(tree), 1)

    def test_inorder(self):
        """In-order traversal should return keys in sorted order."""
        tree = RBTree()
        keys = [30, 10, 50, 20, 40, 5, 35]
        for k in keys:
            tree.insert(k)
        result = [node.key for node in tree.inorder()]
        self.assertEqual(result, sorted(keys))

    def test_duplicate_key_updates_value(self):
        """Inserting a duplicate key should update the value, not add a new node."""
        tree = RBTree()
        tree.insert(10, "original")
        tree.insert(10, "updated")
        self.assertEqual(len(tree), 1)
        self.assertEqual(tree.search(10).value, "updated")

    def test_random_insert_delete(self):
        """Random inserts and deletes — validate tree after each operation."""
        tree = RBTree()
        keys = list(range(100))
        random.shuffle(keys)

        for k in keys:
            tree.insert(k)
            tree.validate()

        random.shuffle(keys)
        for k in keys:
            tree.delete(k)
            tree.validate()

        self.assertTrue(tree.is_empty())


# ══════════════════════════════════════════════════════════════
#  DOUBLY LINKED LIST TESTS
# ══════════════════════════════════════════════════════════════

class TestDoublyLinkedList(unittest.TestCase):
    """Test the hand-rolled doubly linked list."""

    def test_append_and_iterate(self):
        dll = DoublyLinkedList()
        dll.append(1)
        dll.append(2)
        dll.append(3)
        self.assertEqual(list(dll), [1, 2, 3])

    def test_pop_front(self):
        dll = DoublyLinkedList()
        dll.append("a")
        dll.append("b")
        dll.append("c")
        self.assertEqual(dll.pop_front(), "a")
        self.assertEqual(dll.pop_front(), "b")
        self.assertEqual(dll.pop_front(), "c")
        self.assertTrue(dll.is_empty())

    def test_pop_front_empty(self):
        dll = DoublyLinkedList()
        with self.assertRaises(IndexError):
            dll.pop_front()

    def test_remove_middle(self):
        dll = DoublyLinkedList()
        n1 = dll.append(1)
        n2 = dll.append(2)
        n3 = dll.append(3)
        dll.remove(n2)
        self.assertEqual(list(dll), [1, 3])

    def test_remove_head(self):
        dll = DoublyLinkedList()
        n1 = dll.append(1)
        n2 = dll.append(2)
        dll.remove(n1)
        self.assertEqual(list(dll), [2])
        self.assertEqual(dll.head.data, 2)

    def test_remove_tail(self):
        dll = DoublyLinkedList()
        n1 = dll.append(1)
        n2 = dll.append(2)
        dll.remove(n2)
        self.assertEqual(list(dll), [1])
        self.assertEqual(dll.tail.data, 1)

    def test_remove_only_element(self):
        dll = DoublyLinkedList()
        n1 = dll.append(42)
        dll.remove(n1)
        self.assertTrue(dll.is_empty())
        self.assertIsNone(dll.head)
        self.assertIsNone(dll.tail)

    def test_size_tracking(self):
        dll = DoublyLinkedList()
        self.assertEqual(len(dll), 0)
        n1 = dll.append(1)
        n2 = dll.append(2)
        self.assertEqual(len(dll), 2)
        dll.remove(n1)
        self.assertEqual(len(dll), 1)
        dll.pop_front()
        self.assertEqual(len(dll), 0)

    def test_peek_front(self):
        dll = DoublyLinkedList()
        dll.append(10)
        dll.append(20)
        self.assertEqual(dll.peek_front(), 10)
        self.assertEqual(len(dll), 2)  # peek doesn't remove


# ══════════════════════════════════════════════════════════════
#  PRICE LEVEL TESTS
# ══════════════════════════════════════════════════════════════

class TestPriceLevel(unittest.TestCase):
    """Test that PriceLevel maintains FIFO ordering."""

    def _make_order(self, oid, qty):
        return Order(oid, Side.BUY, 100.0, qty, time.time())

    def test_fifo_ordering(self):
        """Orders should come out in the order they were added."""
        pl = PriceLevel(100.0)
        pl.add_order(self._make_order(1, 10))
        pl.add_order(self._make_order(2, 20))
        pl.add_order(self._make_order(3, 30))

        self.assertEqual(pl.peek().order_id, 1)
        self.assertEqual(pl.pop_front().order_id, 1)
        self.assertEqual(pl.pop_front().order_id, 2)
        self.assertEqual(pl.pop_front().order_id, 3)
        self.assertTrue(pl.is_empty())

    def test_volume(self):
        """Volume should be the sum of all order quantities."""
        pl = PriceLevel(100.0)
        pl.add_order(self._make_order(1, 10))
        pl.add_order(self._make_order(2, 20))
        pl.add_order(self._make_order(3, 30))
        self.assertEqual(pl.volume(), 60)

    def test_remove_middle_order(self):
        """Removing a middle order should preserve FIFO for the rest."""
        pl = PriceLevel(100.0)
        n1 = pl.add_order(self._make_order(1, 10))
        n2 = pl.add_order(self._make_order(2, 20))
        n3 = pl.add_order(self._make_order(3, 30))

        pl.remove_order(n2)
        self.assertEqual(pl.volume(), 40)
        self.assertEqual(pl.peek().order_id, 1)


# ══════════════════════════════════════════════════════════════
#  ORDER BOOK TESTS
# ══════════════════════════════════════════════════════════════

class TestOrderBook(unittest.TestCase):
    """Test the order book (without matching)."""

    def test_best_bid_ask(self):
        """Best bid = highest buy, best ask = lowest sell."""
        book = OrderBook()
        book.add_order(Order(1, Side.BUY, 99.0, 10, time.time()))
        book.add_order(Order(2, Side.BUY, 100.0, 10, time.time()))
        book.add_order(Order(3, Side.SELL, 101.0, 10, time.time()))
        book.add_order(Order(4, Side.SELL, 102.0, 10, time.time()))

        self.assertEqual(book.best_bid().key, 100.0)
        self.assertEqual(book.best_ask().key, 101.0)

    def test_cancel_order(self):
        """Cancel should remove the order and clean up empty price levels."""
        book = OrderBook()
        book.add_order(Order(1, Side.BUY, 100.0, 10, time.time()))
        book.add_order(Order(2, Side.BUY, 100.0, 20, time.time()))

        # Cancel order 1 — price level should still exist (order 2 remains)
        book.cancel_order(1)
        self.assertFalse(book.order_exists(1))
        self.assertTrue(book.order_exists(2))
        self.assertIsNotNone(book.best_bid())

        # Cancel order 2 — price level should be removed
        book.cancel_order(2)
        self.assertIsNone(book.best_bid())

    def test_cancel_nonexistent(self):
        """Cancelling an order that doesn't exist should return None."""
        book = OrderBook()
        result = book.cancel_order(999)
        self.assertIsNone(result)

    def test_market_depth(self):
        """Market depth should return price levels in the right order."""
        book = OrderBook()
        book.add_order(Order(1, Side.BUY, 99.0, 10, time.time()))
        book.add_order(Order(2, Side.BUY, 100.0, 20, time.time()))
        book.add_order(Order(3, Side.BUY, 98.0, 30, time.time()))

        bids, asks = book.market_depth(levels=3)
        # Bids should be highest first
        self.assertEqual([b[0] for b in bids], [100.0, 99.0, 98.0])


# ══════════════════════════════════════════════════════════════
#  MATCHING ENGINE TESTS
# ══════════════════════════════════════════════════════════════

class TestMatchingEngine(unittest.TestCase):
    """Test the full matching engine."""

    def test_no_match(self):
        """Orders that don't cross should just sit in the book."""
        engine = MatchingEngine()
        engine.add_limit_order(Side.BUY, 99.0, 10)
        engine.add_limit_order(Side.SELL, 101.0, 10)

        self.assertEqual(engine.get_best_bid(), 99.0)
        self.assertEqual(engine.get_best_ask(), 101.0)
        self.assertEqual(len(engine.get_trade_log()), 0)

    def test_exact_match(self):
        """Two orders at the same price should match completely."""
        engine = MatchingEngine()
        engine.add_limit_order(Side.SELL, 100.0, 10)
        _, trades = engine.add_limit_order(Side.BUY, 100.0, 10)

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].price, 100.0)
        self.assertEqual(trades[0].quantity, 10)
        # Both orders fully filled — book should be empty
        self.assertIsNone(engine.get_best_bid())
        self.assertIsNone(engine.get_best_ask())

    def test_partial_fill_incoming(self):
        """Incoming order is larger than the resting order."""
        engine = MatchingEngine()
        engine.add_limit_order(Side.SELL, 100.0, 5)
        order, trades = engine.add_limit_order(Side.BUY, 100.0, 10)

        # Should trade 5 shares, 5 remain as a bid
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].quantity, 5)
        self.assertEqual(engine.get_best_bid(), 100.0)
        self.assertIsNone(engine.get_best_ask())

    def test_partial_fill_resting(self):
        """Incoming order is smaller than the resting order."""
        engine = MatchingEngine()
        engine.add_limit_order(Side.SELL, 100.0, 10)
        _, trades = engine.add_limit_order(Side.BUY, 100.0, 3)

        # Should trade 3 shares, 7 remain as an ask
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].quantity, 3)
        self.assertIsNone(engine.get_best_bid())
        self.assertEqual(engine.get_best_ask(), 100.0)

    def test_multiple_price_level_matching(self):
        """Incoming order sweeps through multiple price levels."""
        engine = MatchingEngine()
        engine.add_limit_order(Side.SELL, 100.0, 5)
        engine.add_limit_order(Side.SELL, 101.0, 5)
        engine.add_limit_order(Side.SELL, 102.0, 5)

        # Buy 12 shares at up to $102 — should sweep 100, 101, and partial 102
        _, trades = engine.add_limit_order(Side.BUY, 102.0, 12)

        self.assertEqual(len(trades), 3)
        self.assertEqual(trades[0].price, 100.0)
        self.assertEqual(trades[0].quantity, 5)
        self.assertEqual(trades[1].price, 101.0)
        self.assertEqual(trades[1].quantity, 5)
        self.assertEqual(trades[2].price, 102.0)
        self.assertEqual(trades[2].quantity, 2)

        # 3 shares remain at $102
        self.assertEqual(engine.get_best_ask(), 102.0)

    def test_fifo_within_price_level(self):
        """At the same price, the oldest order should fill first."""
        engine = MatchingEngine()
        order1, _ = engine.add_limit_order(Side.SELL, 100.0, 5)
        order2, _ = engine.add_limit_order(Side.SELL, 100.0, 5)

        _, trades = engine.add_limit_order(Side.BUY, 100.0, 5)

        # Should match against order1 (first in), not order2
        self.assertEqual(trades[0].sell_order_id, order1.order_id)

    def test_trade_price_is_resting(self):
        """Trade price should be the resting order's price, not the aggressor's."""
        engine = MatchingEngine()
        engine.add_limit_order(Side.SELL, 100.0, 10)
        # Buy at 105 — willing to pay more, but should trade at 100
        _, trades = engine.add_limit_order(Side.BUY, 105.0, 10)

        self.assertEqual(trades[0].price, 100.0)

    def test_sell_matches_highest_bid(self):
        """Incoming sell should match the highest bid first."""
        engine = MatchingEngine()
        engine.add_limit_order(Side.BUY, 98.0, 5)
        engine.add_limit_order(Side.BUY, 100.0, 5)
        engine.add_limit_order(Side.BUY, 99.0, 5)

        _, trades = engine.add_limit_order(Side.SELL, 98.0, 7)

        # Should match $100 first (5 shares), then $99 (2 shares)
        self.assertEqual(trades[0].price, 100.0)
        self.assertEqual(trades[0].quantity, 5)
        self.assertEqual(trades[1].price, 99.0)
        self.assertEqual(trades[1].quantity, 2)

    def test_cancel_order(self):
        """Cancelled orders should not match."""
        engine = MatchingEngine()
        order, _ = engine.add_limit_order(Side.SELL, 100.0, 10)
        engine.cancel_order(order.order_id)

        # This buy should NOT match — the sell was cancelled
        _, trades = engine.add_limit_order(Side.BUY, 100.0, 10)
        self.assertEqual(len(trades), 0)
        self.assertEqual(engine.get_best_bid(), 100.0)

    def test_modify_price(self):
        """Modifying price should cancel and re-insert with new timestamp."""
        engine = MatchingEngine()
        order1, _ = engine.add_limit_order(Side.SELL, 100.0, 10)
        order2, _ = engine.add_limit_order(Side.SELL, 100.0, 10)

        # Modify order1's price to a different price — it gets cancelled and re-inserted
        engine.modify_order(order1.order_id, new_price=100.50)

        # order2 should now be the only order at $100
        _, trades = engine.add_limit_order(Side.BUY, 100.0, 10)
        self.assertEqual(trades[0].sell_order_id, order2.order_id)
        self.assertEqual(trades[0].price, 100.0)

    def test_modify_quantity_keeps_fifo(self):
        """Modifying only quantity should keep FIFO position."""
        engine = MatchingEngine()
        order1, _ = engine.add_limit_order(Side.SELL, 100.0, 10)
        order2, _ = engine.add_limit_order(Side.SELL, 100.0, 10)

        # Modify order1's quantity — it should KEEP its FIFO position
        engine.modify_order(order1.order_id, new_quantity=5)

        _, trades = engine.add_limit_order(Side.BUY, 100.0, 5)
        self.assertEqual(trades[0].sell_order_id, order1.order_id)
        self.assertEqual(trades[0].quantity, 5)

    def test_modify_nonexistent(self):
        """Modifying an order that doesn't exist should return None."""
        engine = MatchingEngine()
        result, trades = engine.modify_order(999, new_price=100.0)
        self.assertIsNone(result)
        self.assertEqual(trades, [])

    def test_modify_price_triggers_match(self):
        """Modifying price to a crossing price should trigger a match."""
        engine = MatchingEngine()
        engine.add_limit_order(Side.BUY, 100.0, 10)
        sell_order, _ = engine.add_limit_order(Side.SELL, 105.0, 10)

        # Modify sell price down to 100 — should match against the buy
        _, trades = engine.modify_order(sell_order.order_id, new_price=100.0)
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].quantity, 10)

    def test_market_depth(self):
        """Market depth should show correct levels."""
        engine = MatchingEngine()
        engine.add_limit_order(Side.BUY, 99.0, 10)
        engine.add_limit_order(Side.BUY, 100.0, 20)
        engine.add_limit_order(Side.BUY, 100.0, 15)
        engine.add_limit_order(Side.SELL, 101.0, 5)
        engine.add_limit_order(Side.SELL, 102.0, 10)

        bids, asks = engine.market_depth(levels=5)

        # Bids: highest first
        self.assertEqual(bids[0], (100.0, 35, 2))  # 20 + 15, 2 orders
        self.assertEqual(bids[1], (99.0, 10, 1))

        # Asks: lowest first
        self.assertEqual(asks[0], (101.0, 5, 1))
        self.assertEqual(asks[1], (102.0, 10, 1))

    def test_order_exists(self):
        """order_exists should return True for active orders, False for filled/cancelled."""
        engine = MatchingEngine()
        order, _ = engine.add_limit_order(Side.BUY, 100.0, 10)
        self.assertTrue(engine.order_exists(order.order_id))

        engine.cancel_order(order.order_id)
        self.assertFalse(engine.order_exists(order.order_id))

    def test_empty_book(self):
        """Queries on an empty book should return None."""
        engine = MatchingEngine()
        self.assertIsNone(engine.get_best_bid())
        self.assertIsNone(engine.get_best_ask())
        bids, asks = engine.market_depth()
        self.assertEqual(bids, [])
        self.assertEqual(asks, [])

    def test_self_crossing_prevention(self):
        """Buy at 105 with sell at 100 should immediately match."""
        engine = MatchingEngine()
        engine.add_limit_order(Side.SELL, 100.0, 10)
        _, trades = engine.add_limit_order(Side.BUY, 105.0, 10)

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].price, 100.0)  # resting price
        self.assertIsNone(engine.get_best_bid())
        self.assertIsNone(engine.get_best_ask())

    def test_multiple_fills_same_level(self):
        """Multiple resting orders at the same price filled by one incoming order."""
        engine = MatchingEngine()
        engine.add_limit_order(Side.SELL, 100.0, 3)
        engine.add_limit_order(Side.SELL, 100.0, 4)
        engine.add_limit_order(Side.SELL, 100.0, 5)

        _, trades = engine.add_limit_order(Side.BUY, 100.0, 10)

        self.assertEqual(len(trades), 3)
        self.assertEqual(trades[0].quantity, 3)
        self.assertEqual(trades[1].quantity, 4)
        self.assertEqual(trades[2].quantity, 3)  # partial fill of the 5-lot

        # 2 shares remain at $100 ask
        self.assertEqual(engine.get_best_ask(), 100.0)


# ══════════════════════════════════════════════════════════════
#  STRESS TEST
# ══════════════════════════════════════════════════════════════

class TestStress(unittest.TestCase):
    """Stress test with 10,000+ random operations."""

    def test_stress_random_orders(self):
        """
        Insert 10,000+ random orders, cancel some, and verify
        the RB tree invariants after every operation.
        """
        engine = MatchingEngine()
        active_orders = []
        num_operations = 12000

        for i in range(num_operations):
            action = random.random()

            if action < 0.6:
                # 60% chance: add a new order
                side = random.choice([Side.BUY, Side.SELL])
                price = round(random.uniform(90.0, 110.0), 2)
                qty = random.randint(1, 100)
                order, trades = engine.add_limit_order(side, price, qty)
                if engine.order_exists(order.order_id):
                    active_orders.append(order.order_id)

            elif action < 0.8 and active_orders:
                # 20% chance: cancel a random active order
                idx = random.randint(0, len(active_orders) - 1)
                oid = active_orders.pop(idx)
                engine.cancel_order(oid)

            elif active_orders:
                # 20% chance: modify a random active order
                idx = random.randint(0, len(active_orders) - 1)
                oid = active_orders[idx]
                if engine.order_exists(oid):
                    if random.random() < 0.5:
                        new_price = round(random.uniform(90.0, 110.0), 2)
                        result, trades = engine.modify_order(oid, new_price=new_price)
                        # If price changed, the old ID is gone, new one is active
                        if result is not None and result.order_id != oid:
                            active_orders[idx] = result.order_id
                    else:
                        new_qty = random.randint(1, 100)
                        engine.modify_order(oid, new_quantity=new_qty)

            # Validate RB tree invariants after every operation
            engine.book._bids.validate()
            engine.book._asks.validate()

        # Final sanity checks
        total_trades = len(engine.get_trade_log())
        print(f"\n  Stress test complete: {num_operations} operations, {total_trades} trades")
        print(f"  Active orders remaining: {sum(1 for oid in active_orders if engine.order_exists(oid))}")

        # Final validation
        engine.book._bids.validate()
        engine.book._asks.validate()

    def test_stress_heavy_matching(self):
        """
        Submit many crossing orders to stress the matching logic.
        All orders are at the same price to maximize matches.
        """
        engine = MatchingEngine()

        # Add 5000 sell orders
        for _ in range(5000):
            engine.add_limit_order(Side.SELL, 100.0, random.randint(1, 10))

        # Add 5000 buy orders that cross
        for _ in range(5000):
            engine.add_limit_order(Side.BUY, 100.0, random.randint(1, 10))

        engine.book._bids.validate()
        engine.book._asks.validate()

        total_trades = len(engine.get_trade_log())
        print(f"\n  Heavy matching stress test: {total_trades} trades executed")


# ══════════════════════════════════════════════════════════════
#  RUN ALL TESTS
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    unittest.main(verbosity=2)
