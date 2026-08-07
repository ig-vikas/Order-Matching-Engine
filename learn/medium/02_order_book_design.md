# Order Book Design — Three Layers Working Together

> **What is an order book?** It's the central data structure of any stock exchange.
> It keeps track of all pending buy orders (bids) and sell orders (asks).

---

## What Does an Order Book Look Like?

```
              BUY SIDE (Bids)              SELL SIDE (Asks)
         ──────────────────────    ──────────────────────────
Level    Price    Volume  Orders   Price    Volume  Orders
         $150.00  500     3        $150.50  200     2     ← best ask
         $149.50  300     2  ← best bid
         $149.00  150     1        $151.00  450     4
         $148.00  800     5        $151.50  100     1
         $147.00  200     1        $152.00  600     3

Spread = Best Ask - Best Bid = $150.50 - $149.50 = $1.00
```

- **Bids**: People wanting to BUY (sorted highest to lowest)
- **Asks**: People wanting to SELL (sorted lowest to highest)
- **Spread**: The gap between the best bid and best ask
- **Best Bid**: The highest price someone is willing to pay
- **Best Ask**: The lowest price someone is willing to sell at

---

## The Three Layers — Why One Data Structure Isn't Enough

No single data structure gives us fast performance for ALL operations. So we use THREE together:

```
┌─────────────────────────────────────────────────────┐
│  LAYER 1: Red-Black Tree (one per side)             │
│  Purpose: Keep price levels SORTED                  │
│  Why: O(log n) insert, delete, find min/max         │
│                                                     │
│  $147 → $148 → $149 → $149.50 → $150               │
│  (sorted by price)                                  │
├─────────────────────────────────────────────────────┤
│  LAYER 2: Doubly Linked List (one per price level)  │
│  Purpose: FIFO queue of orders at the same price    │
│  Why: O(1) for add, remove, and match               │
│                                                     │
│  $150.00: [Order1: 100] ↔ [Order2: 200] ↔ [Order3: 200] │
│           ^ matched first                ^ matched last    │
├─────────────────────────────────────────────────────┤
│  LAYER 3: Hash Map (one for the whole book)         │
│  Purpose: Find ANY order instantly by its ID        │
│  Why: O(1) lookup for cancellation                  │
│                                                     │
│  { 1: node_ref, 2: node_ref, 3: node_ref, ... }    │
└─────────────────────────────────────────────────────┘
```

---

## Layer 1: Red-Black Tree — Price Level Index

The RB-Tree stores price levels in sorted order.

**For Bids (BUY side):**
- Tree sorted by price
- `maximum()` gives the BEST BID (highest buy price)

**For Asks (SELL side):**
- Tree sorted by price
- `minimum()` gives the BEST ASK (lowest sell price)

```python
class OrderBook:
    def __init__(self):
        self._bids = RBTree()  # Highest price = best bid
        self._asks = RBTree()  # Lowest price = best ask
    
    def best_bid(self):
        """What's the highest price someone will pay?"""
        node = self._bids.maximum()  # O(log n)
        return node  # Returns the PriceLevel at the highest price
    
    def best_ask(self):
        """What's the lowest price someone will sell at?"""
        node = self._asks.minimum()  # O(log n)
        return node
```

### What's Stored in Each Tree Node?

Each tree node stores:
- **Key**: The price (e.g., $150.00)
- **Value**: A PriceLevel object (which is a DLL of all orders at that price)

```
RB-Tree Node:
    key = 150.00
    value = PriceLevel:
        [Order(id=1, qty=100)] ↔ [Order(id=7, qty=200)] ↔ [Order(id=12, qty=200)]
```

---

## Layer 2: Doubly Linked List — FIFO Order Queue

At each price level, multiple orders can exist. They're served in **FIFO** order (first in, first out).

```
Price $150.00 — who placed their order first gets filled first:

    [Order 1]  ↔  [Order 7]  ↔  [Order 12]
    100 shares    200 shares    200 shares
    ↑ arrived first             ↑ arrived last
    ↑ gets filled first         ↑ gets filled last
```

### Why FIFO?

It's fair. If you placed your order first, you get priority over someone who placed the same-price order later. This is called "price-time priority" — first sort by price, then by time.

### Operations We Need

```python
# New order at $150 → goes to the BACK of the line
dll.append(new_order)  # O(1)

# Matching → fill the OLDEST order first (front of line)
oldest_order = dll.pop_front()  # O(1)

# Cancel → remove from anywhere in the line
dll.remove(specific_node)  # O(1) with direct reference
```

---

## Layer 3: Hash Map — The Cancel Trick

### The Problem

When someone cancels an order, they give us the order ID:
"Cancel order #12345"

Without the hash map:
```
1. Which side is it on? BUY or SELL?         → don't know
2. What price level is it at?                → don't know
3. Where in the DLL at that price level?     → don't know

Solution: Search EVERY price level in BOTH trees, checking
          every order in every DLL. That's O(n).
```

With the hash map:
```
order_map[12345] = {
    "dll_node": <direct reference to the DLL node>,
    "side": "BUY",
    "price": 150.00
}

1. Look up in hash map                       → O(1)
2. Get the dll_node reference                → O(1)
3. Call dll.remove(dll_node)                 → O(1)
4. If price level is now empty, remove from tree → O(log n)

Total: O(1) amortized!
```

---

## Adding an Order — Step by Step

Let's trace through adding a BUY order at $150.00 for 100 shares:

```python
def add_order(self, order):
    """
    order = Order(id=5, side=BUY, price=150.0, quantity=100)
    """
    
    # Step 1: Pick the correct tree (bids for BUY, asks for SELL)
    tree = self._bids  # because side is BUY
    
    # Step 2: Check if this price level already exists
    node = tree.search(150.0)  # O(log n)
    
    if node is None:
        # Step 3a: Price level doesn't exist → create it
        level = PriceLevel(150.0)
        tree.insert(150.0, level)  # O(log n) — RB-Tree insert
    else:
        # Step 3b: Price level exists → use it
        level = node.value
    
    # Step 4: Add order to the DLL (back of the queue)
    dll_node = level.append(order)  # O(1) — returns the node reference
    
    # Step 5: Register in hash map for O(1) cancel later
    self._order_map[order.order_id] = (dll_node, order.side, order.price)
```

### Visual Before and After

```
BEFORE adding Order(id=5, BUY, $150, 100):

    RB-Tree (bids):        DLLs:
        $150.00            $150: [Order1: 200] ↔ [Order3: 150]
       /       \
    $149.00  $151.00       $149: [Order2: 100]

AFTER:

    RB-Tree (bids):        DLLs:
        $150.00            $150: [Order1: 200] ↔ [Order3: 150] ↔ [Order5: 100]  ← NEW
       /       \                                                      ↑
    $149.00  $151.00       $149: [Order2: 100]                    added to tail

    Hash Map: { ..., 5: (dll_node_5, BUY, 150.0) }  ← NEW entry
```

---

## Cancelling an Order — Step by Step

Cancel Order #3:

```python
def cancel_order(self, order_id):
    """Cancel order_id = 3"""
    
    # Step 1: Look up in hash map
    dll_node, side, price = self._order_map[3]  # O(1)
    # dll_node = reference to [Order3] in the $150 DLL
    # side = BUY
    # price = 150.0
    
    # Step 2: Get the tree and price level
    tree = self._bids  # because side is BUY
    tree_node = tree.search(150.0)  # O(log n)
    level = tree_node.value
    
    # Step 3: Remove from DLL
    level.remove(dll_node)  # O(1) — just update prev/next pointers
    
    # Step 4: If price level is now empty, remove from tree
    if level.size == 0:
        tree.delete(150.0)  # O(log n) — remove empty price level
    
    # Step 5: Remove from hash map
    del self._order_map[3]  # O(1)
```

### Visual Before and After

```
BEFORE cancelling Order 3:
    $150: [Order1: 200] ↔ [Order3: 150] ↔ [Order5: 100]
                              ↑ this one

AFTER:
    $150: [Order1: 200] ↔ [Order5: 100]
    
    Order3 is gone! The pointers were updated:
    Order1.next = Order5
    Order5.prev = Order1
```

---

## Market Depth — Showing Top N Levels

```python
def market_depth(self, side, levels=5):
    """
    Return the top N price levels.
    
    For bids: start at maximum (best bid), walk down
    For asks: start at minimum (best ask), walk up
    """
    tree = self._bids if side == Side.BUY else self._asks
    result = []
    
    if side == Side.BUY:
        node = tree.maximum()  # Start at highest price
        for _ in range(levels):
            if node is None:
                break
            level = node.value
            result.append({
                "price": node.key,
                "volume": level.volume(),
                "order_count": level.size,
            })
            node = tree.predecessor(node)  # Go to next-lower price
    else:
        node = tree.minimum()  # Start at lowest price
        for _ in range(levels):
            if node is None:
                break
            level = node.value
            result.append({
                "price": node.key,
                "volume": level.volume(),
                "order_count": level.size,
            })
            node = tree.successor(node)  # Go to next-higher price
    
    return result
```

---

## Why This Design Is Good — Complexity Table

| Operation | Steps | Total Time |
|-----------|-------|------------|
| Add order | Tree search + DLL append + HashMap insert | O(log n) |
| Cancel order | HashMap lookup + DLL remove + (maybe Tree delete) | O(1) amortized |
| Best bid | Tree maximum | O(log n) |
| Best ask | Tree minimum | O(log n) |
| Match (pop front) | DLL pop_front + (maybe Tree delete) | O(1) amortized |
| Market depth (k) | k × Tree successor | O(k log n) |

Where `n` = number of distinct price levels (NOT number of orders).
If there are 10,000 orders spread across 100 price levels, `n = 100`, so `log n ≈ 7`.
