# Order Matching Engine

A production-grade stock exchange order matching engine built entirely from scratch in **Python 3** — no external libraries.

Every core data structure (Red-Black Tree, Doubly Linked List) is hand-coded.
This project is designed as a resume-worthy implementation for companies like LSEG, Nasdaq, CME, Jane Street, Citadel, or Optiver.

---

## How It Works

### The Big Picture

```
Incoming Order
      │
      ▼
┌──────────────────┐
│  Matching Engine  │ ── tries to match against opposite side
└──────┬───────────┘
       │ unmatched remainder
       ▼
┌──────────────────┐
│    Order Book     │ ── two Red-Black Trees (bids + asks)
│                   │
│  BIDS (buy side)  │    each tree node = one price level
│  ASKS (sell side) │    each price level = linked list of orders (FIFO)
│                   │
│  + Hash Map       │    order_id → (tree_node, dll_node, price_level)
└──────────────────┘    for O(1) order lookup and cancel
```

### Price-Time Priority (how real exchanges work)

1. **Price priority**: best price gets filled first
   - Incoming BUY → matches lowest SELL prices first
   - Incoming SELL → matches highest BUY prices first

2. **Time priority**: at the same price, oldest order fills first (FIFO)

3. **Trade price**: always the resting order's price (the one already in the book)

---

## File Structure

```
matching_engine/
├── order.py            # Order, Trade, Side — the domain models
├── linked_list.py      # Doubly Linked List (hand-built, no deque)
├── rb_tree.py          # Red-Black Tree (hand-built, no sortedcontainers)
├── price_level.py      # FIFO queue of orders at one price
├── order_book.py       # Two RB-Trees + hash map
├── matching_engine.py  # Price-Time Priority matching logic
├── tests.py            # 53 tests + 10,000 order stress test
└── main.py             # Interactive demo
```

---

## How Each Piece Fits Together

### Order (`order.py`)
The basic unit. Has an `order_id`, `side` (BUY/SELL), `price`, `quantity`, and `timestamp`.
Quantity is mutable — it gets decremented during partial fills.

### Doubly Linked List (`linked_list.py`)
Each price level has a linked list of orders in FIFO order.
Why not `deque`? Because `deque.remove()` is O(n). Our linked list does O(1) removal
given a direct pointer to the node — which is how fast cancellation works.

### Red-Black Tree (`rb_tree.py`)
A self-balancing BST where each node = one price level.
Guarantees O(log n) for insert, delete, search, min, max.
See the "Red-Black Tree Deep Dive" section below.

### Price Level (`price_level.py`)
A thin wrapper around the linked list. Represents all orders at a single price.
Supports `add_order`, `remove_order`, `peek`, `volume`, `is_empty`.

### Order Book (`order_book.py`)
Two trees: `_bids` (buy side) and `_asks` (sell side).
Plus a hash map: `order_id → (tree_node, dll_node, price_level)`.
This three-part reference is what makes cancel O(1) for the lookup + O(log n) worst case for tree cleanup.

### Matching Engine (`matching_engine.py`)
The top-level API. Receives orders, runs matching, returns trades.
Supports: `add_limit_order`, `cancel_order`, `modify_order`, `market_depth`.

---

## Complexity Table

| Operation        | Time       | Why                                              |
|------------------|------------|--------------------------------------------------|
| Insert Order     | O(log n)   | RB-Tree insert for new price level               |
| Cancel Order     | O(log n)   | O(1) hash lookup + O(1) DLL remove + O(log n) tree delete if level empty |
| Modify Order     | O(log n)   | Cancel + re-insert if price changes              |
| Best Bid / Ask   | O(log n)   | RB-Tree max / min                                |
| Price Level Find | O(log n)   | RB-Tree search                                   |
| Order Lookup     | O(1)       | Hash map                                         |

---

## Red-Black Tree Deep Dive

### The 5 Rules

1. Every node is RED or BLACK
2. Root is always BLACK
3. Every `None` leaf counts as BLACK
4. RED node cannot have a RED child (no two reds in a row)
5. Every path from root to `None` leaf has the same number of BLACK nodes

These rules keep the tree height ≤ 2·log(n+1), guaranteeing O(log n) operations.

### Why New Nodes Start RED

If we insert a BLACK node, we'd violate Rule 5 (black-height changes on one path).
A RED node doesn't change black-height, so the only possible violation is Rule 4
(two reds in a row) — which is easier to fix.

### Rotations

Rotations rearrange nodes locally without breaking BST ordering.
They're the core tool for rebalancing.

**Left Rotate around x:**
```
      x                y
     / \              / \
    a   y    =>      x   c
       / \          / \
      b   c        a   b
```

**Right Rotate around x:**
```
      x              y
     / \            / \
    y   c    =>    a   x
   / \                / \
  a   b              b   c
```

### Insert Fixup (3 cases + mirror)

After inserting RED node z, if z's parent is also RED, we look at the **uncle**:

**Case 1 — Uncle is RED:**
Just recolor. Parent and uncle become BLACK, grandparent becomes RED.
Move z up to grandparent and repeat.
```
        G(B)              G(R)  ← new z
       / \               / \
     P(R)  U(R)  =>   P(B)  U(B)
     /                 /
   z(R)              z(R)
```

**Case 2 — Uncle is BLACK, z is inner child (triangle):**
Rotate parent to straighten into Case 3.
```
      G(B)              G(B)
     / \               / \
   P(R)  U(B)  =>   z(R)  U(B)
     \               /
    z(R)           P(R)
```

**Case 3 — Uncle is BLACK, z is outer child (line):**
Rotate grandparent, swap colors. Done!
```
        G(B)            P(B)
       / \             / \
     P(R)  U(B)  =>  z(R)  G(R)
     /                      \
   z(R)                     U(B)
```

### Delete Fixup (4 cases + mirror)

When we remove a BLACK node, one path has fewer black nodes (Rule 5 violated).
We treat the replacement node x as "doubly black" and fix it:

**Case 1 — Sibling is RED:**
Rotate to make sibling BLACK. Converts to cases 2/3/4.

**Case 2 — Sibling is BLACK, both its children are BLACK:**
Make sibling RED (remove one black from both sides). Push the problem up.

**Case 3 — Sibling is BLACK, far child BLACK, near child RED:**
Rotate sibling to make far child RED. Converts to Case 4.

**Case 4 — Sibling is BLACK, far child RED:**
Rotate parent, recolor. Extra black resolved. Done!

---

## Supported Operations

```python
engine = MatchingEngine()

# Add limit orders
order, trades = engine.add_limit_order(Side.BUY, 100.0, 10)
order, trades = engine.add_limit_order(Side.SELL, 99.5, 5)

# Cancel
engine.cancel_order(order_id)

# Modify (price change = new FIFO position, qty change = keeps position)
engine.modify_order(order_id, new_price=101.0)
engine.modify_order(order_id, new_quantity=20)

# Queries
engine.get_best_bid()       # highest buy price
engine.get_best_ask()       # lowest sell price
engine.market_depth(5)      # top 5 levels each side
engine.order_exists(42)     # is order still active?
engine.get_trade_log()      # all executed trades

# Print
engine.print_book()
```

---

## How to Run

```bash
# Run the demo
python main.py

# Run all 53 tests (including 10,000+ order stress test)
python tests.py -v
```

---

## Test Coverage

| Area                    | What's Tested                                              |
|-------------------------|------------------------------------------------------------|
| Red-Black Tree          | Insert, delete, search, min/max, successor/predecessor     |
|                         | Sorted insertion, reverse insertion, random ops            |
|                         | All 5 RB invariants validated after every operation        |
| Doubly Linked List      | Append, pop_front, remove (head/middle/tail/only), size    |
| Price Level             | FIFO ordering, volume, middle order removal                |
| Order Book              | Best bid/ask, cancel, market depth                         |
| Matching Engine         | Exact match, partial fills, multi-level sweeps             |
|                         | FIFO within price level, trade price = resting price       |
|                         | Cancel, modify (price & quantity), price crossing          |
| Stress Test             | 12,000 random operations with tree validation each op      |
|                         | 10,000 crossing orders for heavy matching                  |
