# Basic Data Structures — For Absolute Beginners

> **What is a data structure?** It's a way to organize data so you can access it efficiently.
> Just like a library organizes books so you can find them quickly,
> data structures organize information so your computer can work with it fast.

---

## Why Do Data Structures Matter?

Imagine you have 1 million orders. How you store them determines how fast you can:
- Find a specific order (search)
- Add a new order (insert)
- Remove a cancelled order (delete)
- Find the best price (min/max)

Bad choice = slow program. Good choice = fast program.

---

## 1. Array / List — The Simplest Structure

### What is it?
A numbered collection of items, stored side by side in memory.

```
Index:  0     1     2     3     4
       [100] [200] [150] [300] [50]
```

### In Python (lists)
```python
prices = [100, 200, 150, 300, 50]

# Access by position (index starts at 0!)
prices[0]    # 100 (first)
prices[2]    # 150 (third)
prices[-1]   # 50  (last)

# Add to the end
prices.append(250)  # [100, 200, 150, 300, 50, 250]

# Remove from a position
prices.pop(0)  # Removes 100, everything shifts left
# Now: [200, 150, 300, 50, 250]
# ↑ This shift is SLOW for big lists! O(n)

# Search for a value
if 300 in prices:  # O(n) — has to check each one
    print("Found!")
```

### Speed (Big-O)

| Operation | Speed | Why |
|-----------|-------|-----|
| Access by index `prices[3]` | O(1) | Direct jump to position |
| Append to end | O(1) | Just add at the end |
| Insert at beginning | **O(n)** | Everything shifts right |
| Remove from beginning | **O(n)** | Everything shifts left |
| Search for a value | **O(n)** | Check each one |
| Find min/max | **O(n)** | Check each one |

### When to Use
- ✅ You need to access items by position
- ✅ You mostly add/remove from the end
- ❌ You frequently insert/remove from the middle or beginning

---

## 2. Linked List — A Chain of Nodes

### What is it?
Instead of items side by side, each item (node) has a pointer to the next one.

```
Array:       [A] [B] [C] [D]     (side by side in memory)

Linked List: [A]→[B]→[C]→[D]→None   (scattered, connected by arrows)
              ↑
             head
```

### Why Use a Linked List?

**Inserting/removing from the beginning is O(1)!**

```
Remove first element:

Array:       [A] [B] [C] [D]  →  [B] [C] [D]  (shift everything! O(n))

Linked List: [A]→[B]→[C]→[D]  →  [B]→[C]→[D]  (just move head! O(1))
```

### Simple Implementation

```python
class Node:
    """One link in the chain."""
    def __init__(self, data):
        self.data = data    # The actual value
        self.next = None    # Pointer to the next node

class LinkedList:
    def __init__(self):
        self.head = None    # Points to the first node
    
    def add_front(self, data):
        """Add to the beginning — O(1)."""
        new_node = Node(data)
        new_node.next = self.head   # New node points to old head
        self.head = new_node        # New node becomes the head
    
    def remove_front(self):
        """Remove from the beginning — O(1)."""
        if self.head is None:
            return None
        data = self.head.data
        self.head = self.head.next  # Head moves to the next node
        return data
```

### The Problem — Can't Go Backwards

```
Want to remove C (and we have a pointer to C):

[A]→[B]→[C]→[D]

To remove C, we need to set B.next = D
But C doesn't know about B! We can only go FORWARD.
We'd have to walk from head to find B. That's O(n).
```

**Solution: Doubly Linked List!**

---

## 3. Doubly Linked List (DLL) — Links in Both Directions

### What is it?

Each node has TWO pointers: one to the NEXT node and one to the PREVIOUS node.

```
None ← [A] ↔ [B] ↔ [C] ↔ [D] → None
        ↑                    ↑
       head                 tail
```

### Why This Matters for Our Order Book

At each price level ($150.00), orders wait in a queue:

```
Price $150.00 queue:
None ← [Order1: 100 shares] ↔ [Order2: 50 shares] ↔ [Order3: 75 shares] → None
        ↑ matched first (FIFO)                        ↑ matched last
       head                                           tail
```

We need THREE fast operations:
1. **Add to back** (new order joins the queue) → O(1)
2. **Remove from front** (fill the oldest order) → O(1)
3. **Remove from anywhere** (cancel an order) → O(1)

DLL gives us all three!

### Our Actual Implementation

```python
class DLLNode:
    def __init__(self, data):
        self.data = data    # The order object
        self.prev = None    # ← Points backwards
        self.next = None    # → Points forwards

class DoublyLinkedList:
    def __init__(self):
        self.head = None    # First node
        self.tail = None    # Last node
        self.size = 0       # How many nodes
    
    def append(self, data):
        """
        Add to the TAIL (back of the queue) — O(1).
        New orders go to the back of the line.
        
        Before: [A] ↔ [B] ↔ [C]
        After:  [A] ↔ [B] ↔ [C] ↔ [NEW]
        """
        node = DLLNode(data)
        if self.tail is None:
            self.head = node
            self.tail = node
        else:
            node.prev = self.tail     # New points back to old tail
            self.tail.next = node     # Old tail points forward to new
            self.tail = node          # New node becomes the tail
        self.size += 1
        return node  # ← IMPORTANT: returns the node so we can save a reference
    
    def pop_front(self):
        """
        Remove from the HEAD (front of the queue) — O(1).
        This is how matching works: fill the oldest order first.
        
        Before: [A] ↔ [B] ↔ [C]
        After:  [B] ↔ [C]
        Returns: A
        """
        if self.head is None:
            return None
        data = self.head.data
        self.head = self.head.next
        if self.head is not None:
            self.head.prev = None
        else:
            self.tail = None    # List is now empty
        self.size -= 1
        return data
    
    def remove(self, node):
        """
        Remove ANY node from anywhere — O(1).
        This is how cancellation works.
        We have a direct reference to the node (from the hash map).
        
        Before: [A] ↔ [B] ↔ [C] ↔ [D]
        Remove [C]:
        After:  [A] ↔ [B] ↔ [D]
        
        Just update the pointers:
        B.next = D  (skip over C going forward)
        D.prev = B  (skip over C going backward)
        """
        if node.prev is not None:
            node.prev.next = node.next    # Previous skips over this node
        else:
            self.head = node.next         # This was the head, new head is next
        
        if node.next is not None:
            node.next.prev = node.prev    # Next skips over this node
        else:
            self.tail = node.prev         # This was the tail, new tail is prev
        
        self.size -= 1
        return node.data
```

### Visual Walkthrough — Removing a Middle Node

```
Step 0 (Before):
    A.next = B
    B.prev = A,  B.next = C
    C.prev = B,  C.next = D
    D.prev = C

We want to remove C.

Step 1: B.next = D  (C.prev.next = C.next)
    A → B → D
    But D still points back to C...

Step 2: D.prev = B  (C.next.prev = C.prev)
    A ↔ B ↔ D
    C is now disconnected! Python's garbage collector will clean it up.
```

---

## 4. Hash Map (Dictionary) — Instant Lookup

### What is it?

A way to store key-value pairs with **instant** (O(1)) lookup.

Think of it like a phone book:
- Key = person's name ("Alice")
- Value = phone number ("555-0123")
- Lookup = "What's Alice's number?" → Instant!

### How It Works Inside (Simplified)

```
Step 1: Convert the key to a number using a hash function
        hash("AAPL") = 7463829103

Step 2: Use modulo to get a bucket index
        7463829103 % 8 = 7

Step 3: Store the value in bucket 7

Buckets: [ ][ ][ ][ ][ ][ ][ ][AAPL → 150.0]
          0  1  2  3  4  5  6       7

Lookup "AAPL":
  hash("AAPL") % 8 = 7 → bucket[7] → 150.0  (instant!)
```

### In Python

```python
# Python dictionaries ARE hash maps
prices = {}
prices["AAPL"] = 150.0     # Insert: O(1)
prices["GOOGL"] = 2800.0   # Insert: O(1)

print(prices["AAPL"])      # Lookup: O(1) → 150.0
del prices["GOOGL"]        # Delete: O(1)

"AAPL" in prices           # Check exists: O(1) → True
```

### The Cancel Trick — Our Most Important Use

```python
# Problem: "Cancel order #12345"
# How do we find where order #12345 is sitting in the order book?

# Solution: A hash map that maps order_id → its exact location
order_map = {}

# When an order is added:
dll_node = price_level_dll.append(order)    # Returns the DLL node
order_map[order.order_id] = dll_node        # Store its location

# When an order is cancelled:
node = order_map[12345]       # O(1) — instant lookup!
price_level_dll.remove(node)  # O(1) — instant removal!
del order_map[12345]          # O(1) — clean up

# Without the hash map: O(n) — search through every price level
# With the hash map:    O(1) — instant!
```

---

## 5. Binary Tree — The Foundation for RB-Trees

### What is it?

A tree where each node has at most 2 children: left and right.

```
        10
       /  \
      5    15
     / \   / \
    3   7 12  20
```

### Terminology

```
        10          ← ROOT (the top node)
       /  \
      5    15       ← 5 is the LEFT CHILD of 10
     / \   / \         15 is the RIGHT CHILD of 10
    3   7 12  20    ← 3 is a LEAF (no children)
```

- **Root**: The topmost node (10)
- **Parent**: A node above another (10 is parent of 5 and 15)
- **Child**: A node below another (5 and 15 are children of 10)
- **Leaf**: A node with no children (3, 7, 12, 20)
- **Height**: How many levels deep the tree goes (this tree has height 3)

### Binary SEARCH Tree (BST)

A BST has one extra rule: **left < parent < right**

```
        10
       /  \
      5    15        5 < 10 < 15  ✅
     / \   / \       3 < 5 < 7   ✅
    3   7 12  20     12 < 15 < 20 ✅
```

This rule means you can SEARCH efficiently:

```
Finding 7:
    Start at 10: 7 < 10 → go LEFT
    At 5:        7 > 5  → go RIGHT
    At 7:        FOUND! ✅

Each step eliminates HALF the tree → O(log n)
```

### The Problem — Worst Case

If you insert sorted data, the tree becomes a straight line:

```
Insert: 1, 2, 3, 4, 5

1                  ← This is NOT a tree anymore
 \                    It's a linked list!
  2                   Search is O(n), not O(log n)
   \
    3
     \
      4
       \
        5
```

**Solution: Red-Black Trees** (covered in medium/01_red_black_tree.md)

---

## 6. Heap — Why We Didn't Use It

### What is it?

A tree where the parent is always smaller (min-heap) or larger (max-heap) than its children.

```
Min-Heap (parent ≤ children):
       1
      / \
     3   2
    / \
   7   4

The smallest value is ALWAYS at the root → O(1) to find it!
```

### Why Heaps Seem Perfect

| Operation | Heap | 
|-----------|------|
| Find smallest/largest | O(1) — it's the root! |
| Insert | O(log n) |
| Remove root | O(log n) |

For an order book, "find best bid" = "find maximum" → O(1) with a max-heap!

### Why We Chose Red-Black Tree Instead

| Operation | Heap | RB-Tree |
|-----------|------|---------|
| Find best price | **O(1)** ← heap wins | O(log n) |
| Insert | O(log n) | O(log n) |
| **Cancel by ID** | **O(n)** ← SLOW! | **O(1)** ← FAST! |
| Delete arbitrary | **O(n)** ← SLOW! | O(log n) |
| Sorted traversal | O(n log n) | O(n) |

**The killer**: In real stock exchanges, **90% of orders are cancelled**.
Cancel by ID is O(n) in a heap because you have to FIND the element first.
With our RB-Tree + hash map, cancel is O(1). That's the winning design.

---

## 7. The Three-Layer Design — How We Combine Everything

Our order book uses three data structures together:

```
LAYER 1: Red-Black Tree
   Purpose: Keep price levels sorted
   Speed:   O(log n) for everything
   
   $149.00 ← $150.00 → $151.00 → $152.00
   (sorted by price)

LAYER 2: Doubly Linked List (one per price level)
   Purpose: FIFO queue of orders at the same price
   Speed:   O(1) for add, remove, and match
   
   $150.00: [Order1] ↔ [Order2] ↔ [Order3]
   (first in, first out)

LAYER 3: Hash Map
   Purpose: Find any order instantly by its ID
   Speed:   O(1) lookup
   
   {order_id: 1 → node_in_dll,
    order_id: 2 → node_in_dll,
    order_id: 3 → node_in_dll}
```

### Every Operation Is Fast

| Operation | How It Works | Speed |
|-----------|-------------|-------|
| **New order** | RB-Tree find/create level → DLL append → HashMap add | O(log n) |
| **Cancel order** | HashMap lookup → DLL remove → (RB-Tree delete if empty) | O(1) |
| **Match (fill)** | RB-Tree best price → DLL pop_front | O(log n) |
| **Best bid/ask** | RB-Tree max/min | O(log n) |

---

## Speed Comparison Cheat Sheet

| Structure | Insert | Delete | Search | Min/Max |
|-----------|--------|--------|--------|---------|
| Array | O(1) end | O(n) | O(n) | O(n) |
| Sorted Array | O(n) | O(n) | O(log n) | O(1) |
| Linked List | O(1) | O(1)* | O(n) | O(n) |
| Doubly Linked List | O(1) | O(1)* | O(n) | O(n) |
| Hash Map | O(1) | O(1) | O(1) | O(n) |
| BST | O(log n)† | O(log n)† | O(log n)† | O(log n)† |
| Red-Black Tree | O(log n) | O(log n) | O(log n) | O(log n) |
| Heap | O(log n) | O(n) | O(n) | O(1) |

`*` = Only if you have a direct reference to the node
`†` = Average case; worst case is O(n) for plain BST

### What O(1), O(log n), O(n) Actually Mean

```
If you have 1,000,000 items:

O(1)     = 1 operation        (instant)
O(log n) = 20 operations      (very fast)
O(n)     = 1,000,000 operations (slow!)
O(n²)    = 1,000,000,000,000   (impossibly slow)
```
