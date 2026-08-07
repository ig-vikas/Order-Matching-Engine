# Red-Black Tree — Deep Dive

> **What is it?** A self-balancing binary search tree that guarantees O(log n) operations.
> It's what makes our order book fast — even with millions of price levels.

---

## Why Do We Need This?

Remember from the basics: a regular BST can become a linked list if you insert sorted data, making everything O(n). A Red-Black Tree prevents this by **rebalancing after every insert and delete**.

```
Regular BST with sorted inserts:        Red-Black Tree with the SAME inserts:

1                                            4
 \                                          / \
  2                                        2   6
   \                                      / \   \
    3              vs.                   1   3   7
     \
      4
       \
        5
        
Height = n (BAD!)                        Height ≈ log n (GOOD!)
Search = O(n)                            Search = O(log n)
```

---

## The 5 Properties — The Rules That Keep It Balanced

Every Red-Black Tree MUST satisfy these 5 rules AT ALL TIMES:

```
Rule 1: Every node is either RED or BLACK
        (just a single bit of extra data per node)

Rule 2: The ROOT is always BLACK
        (this is the starting point)

Rule 3: Every NULL leaf (empty child) is considered BLACK
        (the "invisible" nodes at the bottom)

Rule 4: A RED node cannot have a RED child
        (no two reds in a row — "red rule")

Rule 5: Every path from root to any NULL leaf has the
        SAME number of BLACK nodes
        (this is called "black-height" — the key to balance)
```

### Why Rule 5 Guarantees Balance

If every path has the same number of black nodes, and you can't have two reds in a row (Rule 4), then:

```
Longest possible path:   B → R → B → R → B → R → B  (alternating, length 7)
Shortest possible path:  B → B → B → B              (all black, length 4)

Longest ≤ 2 × Shortest
Therefore: height ≤ 2 × log₂(n+1)
Therefore: everything is O(log n)
```

---

## Node Structure

```python
# From pre-req/matching_engine/rb_tree.py

class RBNode:
    """
    A single node in the Red-Black Tree.
    
    Fields:
        key:    The price (what we sort by)
        value:  The PriceLevel (the DLL of orders at this price)
        color:  RED or BLACK
        left:   Left child (prices less than this)
        right:  Right child (prices greater than this)
        parent: The node above this one
    """
    RED = True
    BLACK = False
    
    def __init__(self, key, value):
        self.key = key        # e.g., 150.0 (the price)
        self.value = value    # e.g., PriceLevel(150.0)
        self.color = RBNode.RED   # New nodes always start RED
        self.left = None
        self.right = None
        self.parent = None
```

**Why do new nodes start RED?**

Adding a RED node never violates Rule 5 (black-height stays the same). It might violate Rule 4 (two reds in a row), but that's easier to fix than violating Rule 5.

---

## Rotations — The Rebalancing Tool

Rotations are like picking up a subtree and rearranging it. They change the tree's shape WITHOUT changing the sorted order.

### Left Rotation

```
    x                 y
   / \               / \
  a   y     →       x   c
     / \           / \
    b   c         a   b

Before in-order: a, x, b, y, c
After in-order:  a, x, b, y, c  (SAME!)
```

```python
def _left_rotate(self, x):
    """
    Rotate x down to the left, y up.
    
    x becomes the left child of its right child (y).
    y's left child becomes x's right child.
    """
    y = x.right              # y is x's right child
    x.right = y.left         # y's left child becomes x's right child
    if y.left is not None:
        y.left.parent = x   # Update parent pointer
    y.parent = x.parent      # y takes x's position in the tree
    
    if x.parent is None:
        self.root = y        # y becomes the new root
    elif x == x.parent.left:
        x.parent.left = y   # y replaces x as left child
    else:
        x.parent.right = y  # y replaces x as right child
    
    y.left = x               # x becomes y's left child
    x.parent = y             # x's parent is now y
```

### Right Rotation (Mirror of Left)

```
      y              x
     / \            / \
    x   c   →      a   y
   / \                 / \
  a   b               b   c
```

---

## Insert — Step by Step

### Step 1: Regular BST Insert
Walk down the tree. Go left if new key < current, right if new key > current. Insert when you find an empty spot. Color it RED.

### Step 2: Fix-Up (Restore the 5 Properties)

After inserting a RED node, Rule 4 might be violated (RED parent with RED child). There are 3 cases to fix:

### Case 1: Uncle is RED

```
      G(B)              G(R)       ← Recolor grandparent to RED
     / \               / \
   P(R) U(R)   →    P(B) U(B)     ← Recolor parent and uncle to BLACK
   /                 /
 N(R)              N(R)            ← New node stays RED

Then: move up to G and check again (G might now violate Rule 4 with ITS parent)
```

**Why this works**: We pushed the "problem" up the tree. Eventually we reach the root and just color it BLACK (Rule 2).

### Case 2: Uncle is BLACK, Node is Inner Child

```
    G(B)              G(B)
   / \               / \
 P(R) U(B)   →    N(R) U(B)     ← Rotate P to convert to Case 3
   \               /
  N(R)           P(R)
```

Left-rotate P, then fall through to Case 3.

### Case 3: Uncle is BLACK, Node is Outer Child

```
      G(B)            P(B)        ← Recolor P to BLACK
     / \              / \
   P(R) U(B)   →   N(R) G(R)    ← Recolor G to RED, rotate G right
   /                      \
 N(R)                     U(B)
```

This is the **terminal case** — the tree is fixed after this rotation.

### Complete Insert Fix-Up

```python
def _insert_fixup(self, node):
    """Fix the tree after inserting a RED node."""
    while node.parent is not None and node.parent.color == RBNode.RED:
        if node.parent == node.parent.parent.left:
            uncle = node.parent.parent.right
            
            if uncle is not None and uncle.color == RBNode.RED:
                # Case 1: Uncle is RED
                node.parent.color = RBNode.BLACK
                uncle.color = RBNode.BLACK
                node.parent.parent.color = RBNode.RED
                node = node.parent.parent  # Move up
            else:
                if node == node.parent.right:
                    # Case 2: Uncle BLACK, node is inner child
                    node = node.parent
                    self._left_rotate(node)
                # Case 3: Uncle BLACK, node is outer child
                node.parent.color = RBNode.BLACK
                node.parent.parent.color = RBNode.RED
                self._right_rotate(node.parent.parent)
        else:
            # Mirror cases (parent is right child)
            ...  # Same logic but with left/right swapped
    
    self.root.color = RBNode.BLACK  # Rule 2: root is always BLACK
```

---

## Delete — The Hard Part

Deleting is harder because removing a BLACK node reduces the black-height, violating Rule 5.

### 4 Cases for Delete Fix-Up

After deleting a BLACK node, the replacement node is "double-black" — it counts as 2 black nodes on its path. We need to redistribute.

**Case 1: Sibling is RED**
→ Rotate parent, recolor. Converts to Case 2, 3, or 4.

**Case 2: Sibling is BLACK, both nephews are BLACK**
→ Recolor sibling to RED. Move "double-black" up to parent. Repeat.

**Case 3: Sibling BLACK, far nephew BLACK, near nephew RED**
→ Rotate sibling, recolor. Converts to Case 4.

**Case 4: Sibling BLACK, far nephew RED** (TERMINAL CASE)
→ Rotate parent, recolor sibling to parent's color, color parent and far nephew BLACK.
→ **Done!** The tree is fixed.

---

## How Our Order Book Uses the RB-Tree

```python
class OrderBook:
    def __init__(self):
        self._bids = RBTree()  # Sorted by price (highest = best bid)
        self._asks = RBTree()  # Sorted by price (lowest = best ask)
    
    def add_order(self, order):
        tree = self._bids if order.side == Side.BUY else self._asks
        
        # Check if this price level already exists
        node = tree.search(order.price)
        if node is None:
            # NEW price level → create DLL and insert into tree
            level = PriceLevel(order.price)
            tree.insert(order.price, level)  # O(log n)
        else:
            level = node.value
        
        # Add order to the DLL at this price level
        level.append(order)  # O(1)
    
    def best_bid(self):
        return self._bids.maximum()  # Highest price in bid tree → O(log n)
    
    def best_ask(self):
        return self._asks.minimum()  # Lowest price in ask tree → O(log n)
    
    def remove_empty_level(self, side, price):
        tree = self._bids if side == Side.BUY else self._asks
        tree.delete(price)  # Remove price level from tree → O(log n)
```

---

## Complexity Summary

| Operation | Time | Why |
|-----------|------|-----|
| Insert | O(log n) | Walk down + at most 2 rotations + recoloring |
| Delete | O(log n) | Walk down + at most 3 rotations + recoloring |
| Search | O(log n) | Walk down like a BST |
| Min | O(log n) | Keep going left |
| Max | O(log n) | Keep going right |
| Successor | O(log n) | Next-larger key |
| Validate | O(n) | Check all 5 properties on every node |

---

## Validating the Tree — How We PROVE It's Correct

```python
def validate(self):
    """
    Check all 5 Red-Black Tree properties.
    Our test suite calls this after EVERY operation.
    """
    # Property 2: Root is BLACK
    assert self.root is None or self.root.color == RBNode.BLACK
    
    # Property 4: No RED node has a RED child
    def check_no_double_red(node):
        if node is None:
            return
        if node.color == RBNode.RED:
            assert node.left is None or node.left.color == RBNode.BLACK
            assert node.right is None or node.right.color == RBNode.BLACK
        check_no_double_red(node.left)
        check_no_double_red(node.right)
    
    # Property 5: All paths have the same black-height
    def black_height(node):
        if node is None:
            return 1  # NULL nodes are BLACK
        left_bh = black_height(node.left)
        right_bh = black_height(node.right)
        assert left_bh == right_bh, "Black-height mismatch!"
        return left_bh + (1 if node.color == RBNode.BLACK else 0)
    
    check_no_double_red(self.root)
    black_height(self.root)
```

Our property-based tests (test_invariants.py) call `validate()` after EVERY random insert and delete across 200+ test sequences. If ANY sequence violates ANY property, the test fails.
