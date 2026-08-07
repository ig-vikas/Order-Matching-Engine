"""
rb_tree.py — Red-Black Tree from scratch.

A Red-Black Tree is a self-balancing binary search tree.
Each node has a color (RED or BLACK) and the tree maintains
these 5 rules to stay balanced:

    Rule 1: Every node is either RED or BLACK.
    Rule 2: The root is always BLACK.
    Rule 3: Every None leaf is considered BLACK.
    Rule 4: A RED node cannot have a RED child (no two reds in a row).
    Rule 5: Every path from a node to its None leaves has the same
            number of BLACK nodes (the "black-height").

Why these rules matter:
    - Rule 4 + Rule 5 together guarantee that the longest path (alternating
      red-black) is at most 2x the shortest path (all black).
    - This means the tree height is at most 2*log(n+1).
    - So insert, delete, and search are all O(log n) — guaranteed.

Why not a regular BST?
    - A plain BST can degenerate into a linked list if you insert sorted data.
    - That makes operations O(n). Red-Black Trees prevent this.

In our matching engine, each node stores a price level.
The BUY tree and SELL tree each have their own RBTree.
"""

# We use boolean constants instead of strings to avoid typos.
# RED = True, BLACK = False — simple and fast to compare.
RED = True
BLACK = False


class RBNode:
    """
    A single node in the Red-Black Tree.

    Each node represents one price level in the order book.

    Fields:
        key       - the price (used for BST ordering)
        value     - the PriceLevel object at this price
        color     - RED or BLACK
        left      - left child
        right     - right child
        parent    - parent node
    """

    def __init__(self, key, value=None):
        self.key = key
        self.value = value
        # New nodes always start RED.
        # Why? If we insert a BLACK node, we immediately violate Rule 5
        # (one path now has more black nodes). A RED node doesn't change
        # black-height, so the only possible violation is Rule 4 (two reds
        # in a row) — which is easier to fix with rotations.
        self.color = RED
        self.left = None
        self.right = None
        self.parent = None

    def __repr__(self):
        c = "R" if self.color == RED else "B"
        return f"RBNode({self.key}, {c})"


class RBTree:
    """
    A complete Red-Black Tree implementation.

    Supports: insert, delete, search, min, max,
              predecessor, successor, and in-order traversal.

    All operations are O(log n).
    """

    def __init__(self):
        self.root = None
        self._size = 0

    def __len__(self):
        return self._size

    def is_empty(self):
        return self.root is None

    # ══════════════════════════════════════════════════════════
    #  ROTATIONS — O(1) each
    # ══════════════════════════════════════════════════════════
    #
    # Rotations are the core tool for rebalancing. They're O(1)
    # because they only update a fixed number of pointers (no loops).
    #
    # KEY INSIGHT: Rotations rearrange nodes but preserve BST ordering.
    # In the diagrams below, a < x < b < y < c always holds.
    #
    # Left Rotate around x (x goes down, its right child y goes up):
    #
    #       x                y
    #      / \              / \
    #     a   y    =>      x   c
    #        / \          / \
    #       b   c        a   b
    #
    #   Notice: a < x < b < y < c is preserved.
    #   x's right subtree changes from y to b (y's left child).
    #
    # Right Rotate around x (x goes down, its left child y goes up):
    #
    #       x              y
    #      / \            / \
    #     y   c    =>    a   x
    #    / \                / \
    #   a   b              b   c
    #
    #   Mirror of left rotate. a < y < b < x < c is preserved.
    #

    def _left_rotate(self, x):
        """
        Rotate node x to the left — O(1).

        x goes down-left, x's right child (y) goes up.
        Only 5 pointer updates, no loops.
        """
        y = x.right             # Step 1: y is x's right child (will become new parent)

        x.right = y.left        # Step 2: x adopts y's left subtree (b) as its right child
        if y.left is not None:
            y.left.parent = x   #          update b's parent pointer

        y.parent = x.parent     # Step 3: y takes x's position in the tree
        if x.parent is None:
            self.root = y       #          x was root → y is now root
        elif x is x.parent.left:
            x.parent.left = y   #          x was a left child → y replaces it
        else:
            x.parent.right = y  #          x was a right child → y replaces it

        y.left = x              # Step 4: x becomes y's left child
        x.parent = y            #          x's parent is now y

    def _right_rotate(self, x):
        """
        Rotate node x to the right — O(1).

        Mirror of left_rotate. x goes down-right, x's left child (y) goes up.
        """
        y = x.left              # y is x's left child (will become new parent)

        x.left = y.right        # x adopts y's right subtree (b) as its left child
        if y.right is not None:
            y.right.parent = x

        y.parent = x.parent     # y takes x's position in the tree
        if x.parent is None:
            self.root = y
        elif x is x.parent.right:
            x.parent.right = y
        else:
            x.parent.left = y

        y.right = x             # x becomes y's right child
        x.parent = y

    # ══════════════════════════════════════════════════════════
    #  SEARCH
    # ══════════════════════════════════════════════════════════

    def search(self, key):
        """
        Find the node with the given key. Returns None if not found.

        Standard BST search — start at root, go left if key is smaller,
        right if larger. O(log n) because the tree is balanced (height ≤ 2·log(n+1)).
        """
        node = self.root
        while node is not None:
            if key == node.key:
                return node          # Found it
            elif key < node.key:
                node = node.left     # Key is smaller → go left
            else:
                node = node.right    # Key is larger → go right
        return None                  # Not in the tree

    # ══════════════════════════════════════════════════════════
    #  MIN / MAX
    # ══════════════════════════════════════════════════════════

    def minimum(self, node=None):
        """
        Find the node with the smallest key.
        Just go left as far as possible — O(log n).
        """
        if node is None:
            node = self.root
        if node is None:
            return None
        while node.left is not None:
            node = node.left
        return node

    def maximum(self, node=None):
        """
        Find the node with the largest key.
        Just go right as far as possible — O(log n).
        """
        if node is None:
            node = self.root
        if node is None:
            return None
        while node.right is not None:
            node = node.right
        return node

    # ══════════════════════════════════════════════════════════
    #  SUCCESSOR / PREDECESSOR
    # ══════════════════════════════════════════════════════════

    def successor(self, node):
        """
        Find the node with the next larger key.

        Two cases:
        1. If node has a right child, successor is the minimum of the right subtree.
        2. Otherwise, walk up until we find an ancestor where node is in the left subtree.
        """
        if node.right is not None:
            return self.minimum(node.right)

        parent = node.parent
        while parent is not None and node is parent.right:
            node = parent
            parent = parent.parent
        return parent

    def predecessor(self, node):
        """
        Find the node with the next smaller key.

        Mirror of successor:
        1. If node has a left child, predecessor is the maximum of the left subtree.
        2. Otherwise, walk up until we find an ancestor where node is in the right subtree.
        """
        if node.left is not None:
            return self.maximum(node.left)

        parent = node.parent
        while parent is not None and node is parent.left:
            node = parent
            parent = parent.parent
        return parent

    # ══════════════════════════════════════════════════════════
    #  INSERTION
    # ══════════════════════════════════════════════════════════

    def insert(self, key, value=None):
        """
        Insert a new node with the given key and value — O(log n).
        Returns the newly inserted node.

        Complexity breakdown:
            - BST walk to find insert position: O(log n)
            - Fixup: at most O(log n) recolorings + at most 2 rotations
            - Total: O(log n)

        Steps:
        1. Do a normal BST insert (walk down, find the right spot, link the node).
        2. Color the new node RED (done in __init__).
        3. Fix any Rule 4 violations with _insert_fixup.
        """
        new_node = RBNode(key, value)
        self._size += 1

        # ── Step 1: Standard BST insert ──
        # Walk down the tree to find where the new node belongs.
        parent = None
        current = self.root

        while current is not None:
            parent = current
            if key < current.key:
                current = current.left
            elif key > current.key:
                current = current.right
            else:
                # Key already exists — just update the value, don't add a node.
                # This happens when we add a second order at an existing price.
                current.value = value
                self._size -= 1  # didn't actually add a new node
                return current

        # Link the new node to its parent
        new_node.parent = parent

        if parent is None:
            self.root = new_node        # Tree was empty — new node is root
        elif key < parent.key:
            parent.left = new_node      # Smaller — goes left
        else:
            parent.right = new_node     # Larger — goes right

        # ── Step 2: New node is RED (already set in RBNode.__init__) ──

        # ── Step 3: Fix any "two reds in a row" violations ──
        self._insert_fixup(new_node)

        return new_node

    def _insert_fixup(self, z):
        """
        Fix Red-Black Tree violations after inserting node z.

        The only rule we can violate after inserting a RED node is Rule 4:
        "no two reds in a row". This happens when z's parent is also RED.

        Strategy: look at z's UNCLE (parent's sibling) to decide what to do.

        Case 1: Uncle is RED → easy fix, just recolor
            - Parent and uncle become BLACK, grandparent becomes RED.
            - Move z up to grandparent and check again.
            - This might propagate the violation upward, but that's ok —
              we'll fix it in the next loop iteration.

        Case 2: Uncle is BLACK, z is an "inner" child (triangle shape)
            - The nodes form a zig-zag: grandparent-parent-z is a triangle.
            - Rotate parent to straighten the triangle into a line (Case 3).

        Case 3: Uncle is BLACK, z is an "outer" child (straight line)
            - The nodes form a straight line: grandparent-parent-z.
            - Rotate grandparent the other way and swap colors.
            - This FINISHES the fixup — no more violations.

        The loop runs at most O(log n) times (case 1 moves z up 2 levels).
        Cases 2 and 3 do at most 2 rotations total and then stop.
        """
        # Keep fixing as long as we have two reds in a row
        while z.parent is not None and z.parent.color == RED:
            if z.parent is z.parent.parent.left:
                # Parent is the LEFT child of grandparent
                uncle = z.parent.parent.right

                if uncle is not None and uncle.color == RED:
                    # ── Case 1: Uncle is RED ──
                    # Both parent and uncle are RED. We can "absorb" the
                    # extra redness by making them BLACK and pushing the
                    # RED up to grandparent. This preserves black-height.
                    z.parent.color = BLACK
                    uncle.color = BLACK
                    z.parent.parent.color = RED
                    z = z.parent.parent  # Now check grandparent

                else:
                    # Uncle is BLACK (or None, which counts as BLACK)

                    if z is z.parent.right:
                        # ── Case 2: z is a right child (triangle shape) ──
                        #     G                G
                        #    / \              / \
                        #   P   U    =>     z   U    (then fall through to Case 3)
                        #    \              /
                        #     z            P
                        z = z.parent
                        self._left_rotate(z)

                    # ── Case 3: z is a left child (straight line) ──
                    #       G              P
                    #      / \            / \
                    #     P   U    =>   z    G
                    #    /                    \
                    #   z                      U
                    z.parent.color = BLACK
                    z.parent.parent.color = RED
                    self._right_rotate(z.parent.parent)
                    # After Case 3, the loop condition fails → we're done.

            else:
                # ── MIRROR: Parent is the RIGHT child of grandparent ──
                # Exact same logic, but left/right swapped.
                uncle = z.parent.parent.left

                if uncle is not None and uncle.color == RED:
                    # Case 1 (mirror) — recolor and move up
                    z.parent.color = BLACK
                    uncle.color = BLACK
                    z.parent.parent.color = RED
                    z = z.parent.parent

                else:
                    if z is z.parent.left:
                        # Case 2 (mirror) — straighten the triangle
                        z = z.parent
                        self._right_rotate(z)

                    # Case 3 (mirror) — rotate grandparent and recolor
                    z.parent.color = BLACK
                    z.parent.parent.color = RED
                    self._left_rotate(z.parent.parent)

        # Rule 2: root must always be BLACK.
        # The loop might have made the root RED (via Case 1), so fix it.
        self.root.color = BLACK

    # ══════════════════════════════════════════════════════════
    #  DELETION
    # ══════════════════════════════════════════════════════════

    def delete(self, key):
        """
        Delete the node with the given key — O(log n).
        Returns the deleted node, or None if key not found.

        Complexity breakdown:
            - Search for the node: O(log n)
            - Find successor (if needed): O(log n)
            - Fixup: at most O(log n) recolorings + at most 3 rotations
            - Total: O(log n)

        Steps:
        1. Find the node z with the given key.
        2. If z has two children, replace it with its in-order successor.
        3. Splice out the node.
        4. If the spliced-out node was BLACK, fix violations with _delete_fixup.
           (Removing a RED node never breaks any rule.)
        """
        z = self.search(key)
        if z is None:
            return None
        self._delete_node(z)
        return z

    def delete_node(self, z):
        """Delete a specific node (when you already have a reference to it)."""
        if z is None:
            return
        self._delete_node(z)

    def _transplant(self, u, v):
        """
        Replace subtree rooted at u with subtree rooted at v.
        This is a helper for deletion — it just updates parent pointers.
        """
        if u.parent is None:
            self.root = v
        elif u is u.parent.left:
            u.parent.left = v
        else:
            u.parent.right = v

        if v is not None:
            v.parent = u.parent

    def _delete_node(self, z):
        """
        The actual deletion logic (CLRS-style).

        Key variables:
        - z: the node we WANT to delete
        - y: the node being PHYSICALLY removed or moved
              (same as z in cases 1-2, the successor in case 3)
        - x: the node that takes y's old position (might be None)
        - y_original_color: if this was BLACK, we broke Rule 5 and need fixup.
                            If RED, no rules are broken — we're done.

        Three cases based on how many children z has:
        1. z has no left child  → replace z with its right child
        2. z has no right child → replace z with its left child
        3. z has both children  → find in-order successor y, copy y's data
                                  into z's position, then delete y instead
        """
        y = z
        y_original_color = y.color
        x_parent = None  # Track x's parent because x might be None

        if z.left is None:
            # Case 1: No left child — just replace z with its right child
            x = z.right
            x_parent = z.parent
            self._transplant(z, z.right)

        elif z.right is None:
            # Case 2: No right child — replace z with its left child
            x = z.left
            x_parent = z.parent
            self._transplant(z, z.left)

        else:
            # Case 3: Two children — the tricky case
            # Find z's in-order successor (smallest node in right subtree).
            # This node has at most one child (right), so it's easy to remove.
            y = self.minimum(z.right)
            y_original_color = y.color
            x = y.right

            if y.parent is z:
                # Successor is z's direct right child — simple case
                x_parent = y
            else:
                # Successor is deeper in the right subtree
                # First, detach y from its current position
                x_parent = y.parent
                self._transplant(y, y.right)
                y.right = z.right
                y.right.parent = y

            # Now put y in z's position
            self._transplant(z, y)
            y.left = z.left
            y.left.parent = y
            y.color = z.color  # Keep z's color so we don't break rules here

        self._size -= 1

        # Only need fixup if the physically removed node was BLACK.
        # Removing a BLACK node means one path has fewer black nodes → Rule 5 broken.
        # Removing a RED node never breaks any rule.
        if y_original_color == BLACK:
            self._delete_fixup(x, x_parent)

    def _delete_fixup(self, x, x_parent):
        """
        Fix Red-Black Tree after deleting a BLACK node.

        The problem:
            Removing a BLACK node means one path now has fewer BLACK nodes
            than the others → Rule 5 is broken.

        The idea:
            We think of x as "doubly black" — it counts as 2 black nodes
            to compensate for the missing one. Then we use rotations and
            recoloring to get rid of this extra blackness.

        Four cases (when x is a left child) + their mirrors:

        Case 1: Sibling w is RED
            → Rotate parent toward x. Now sibling becomes BLACK.
            → This doesn't fix the problem directly, but it converts
              the situation into Case 2, 3, or 4.

        Case 2: Sibling w is BLACK, BOTH of w's children are BLACK
            → We can't steal a black from the sibling's side.
            → So we make w RED (removing one black from both sides)
              and push the extra black UP to the parent.
            → If parent is RED, we just make it BLACK and we're done.
            → If parent is BLACK, parent becomes the new "doubly black" → loop again.

        Case 3: Sibling w is BLACK, far child is BLACK, near child is RED
            → Rotate w away from x to make the far child RED.
            → This converts to Case 4.

        Case 4: Sibling w is BLACK, far child is RED
            → Rotate parent toward x and recolor.
            → The extra black is absorbed. DONE!

        The loop runs at most O(log n) times (Case 2 moves x up one level).
        Cases 3→4 do at most 2 rotations total and terminate.
        """
        while x is not self.root and (x is None or x.color == BLACK):
            if x is (x_parent.left if x_parent else None):
                # x is the left child (or None on left side)
                w = x_parent.right  # w = sibling of x

                if w is not None and w.color == RED:
                    # ── Case 1: Sibling is RED ──
                    # Make sibling BLACK, parent RED, rotate left.
                    # After this, x has a new BLACK sibling → fall into 2/3/4.
                    w.color = BLACK
                    x_parent.color = RED
                    self._left_rotate(x_parent)
                    w = x_parent.right  # Update sibling after rotation

                left_black = (w is None or w.left is None or w.left.color == BLACK)
                right_black = (w is None or w.right is None or w.right.color == BLACK)

                if left_black and right_black:
                    # ── Case 2: Both of sibling's children are BLACK ──
                    # Remove one black from both sides by making sibling RED.
                    # Push the extra black up to parent.
                    if w is not None:
                        w.color = RED
                    x = x_parent           # Parent is now "doubly black"
                    x_parent = x.parent    # Move up

                else:
                    if right_black:
                        # ── Case 3: Far child (right) is BLACK, near child (left) is RED ──
                        # Rotate sibling right to move the RED child to the far side.
                        # Then fall through to Case 4.
                        if w is not None and w.left is not None:
                            w.left.color = BLACK
                        if w is not None:
                            w.color = RED
                            self._right_rotate(w)
                        w = x_parent.right

                    # ── Case 4: Far child (right) is RED ──
                    # Rotate parent left, recolor. Extra black is absorbed. Done!
                    if w is not None:
                        w.color = x_parent.color
                    x_parent.color = BLACK
                    if w is not None and w.right is not None:
                        w.right.color = BLACK
                    self._left_rotate(x_parent)
                    x = self.root  # Terminate the loop — we're done

            else:
                # ── MIRROR: x is the right child ──
                # Exact same logic with left/right swapped.
                w = x_parent.left  # sibling

                if w is not None and w.color == RED:
                    # Case 1 (mirror)
                    w.color = BLACK
                    x_parent.color = RED
                    self._right_rotate(x_parent)
                    w = x_parent.left

                left_black = (w is None or w.left is None or w.left.color == BLACK)
                right_black = (w is None or w.right is None or w.right.color == BLACK)

                if left_black and right_black:
                    # Case 2 (mirror)
                    if w is not None:
                        w.color = RED
                    x = x_parent
                    x_parent = x.parent

                else:
                    if left_black:
                        # Case 3 (mirror)
                        if w is not None and w.right is not None:
                            w.right.color = BLACK
                        if w is not None:
                            w.color = RED
                            self._left_rotate(w)
                        w = x_parent.left

                    # Case 4 (mirror)
                    if w is not None:
                        w.color = x_parent.color
                    x_parent.color = BLACK
                    if w is not None and w.left is not None:
                        w.left.color = BLACK
                    self._right_rotate(x_parent)
                    x = self.root  # Done

        # If x is RED, just make it BLACK — absorbs the extra black.
        if x is not None:
            x.color = BLACK

    # ══════════════════════════════════════════════════════════
    #  TRAVERSAL
    # ══════════════════════════════════════════════════════════

    def inorder(self):
        """
        Return all nodes in sorted order (left, root, right).
        Useful for printing the order book.
        """
        result = []
        self._inorder_walk(self.root, result)
        return result

    def _inorder_walk(self, node, result):
        if node is not None:
            self._inorder_walk(node.left, result)
            result.append(node)
            self._inorder_walk(node.right, result)

    # ══════════════════════════════════════════════════════════
    #  VALIDATION (for testing)
    # ══════════════════════════════════════════════════════════

    def validate(self):
        """
        Verify all 5 Red-Black Tree properties.
        Returns True if valid, raises AssertionError if not.
        Used in tests to check the tree after every operation.
        """
        if self.root is None:
            return True

        # Rule 2: Root is BLACK
        assert self.root.color == BLACK, "Root must be BLACK"

        # Rule 4: No two reds in a row
        # Rule 5: All paths have equal black-height
        self._validate_node(self.root)

        # Check parent pointers
        self._validate_parents(self.root, None)

        return True

    def _validate_node(self, node):
        """
        Recursively validate Rules 4 and 5.
        Returns the black-height of the subtree.
        """
        if node is None:
            return 1  # None leaves count as BLACK

        # Rule 4: RED node can't have RED children
        if node.color == RED:
            if node.left is not None:
                assert node.left.color == BLACK, \
                    f"RED node {node.key} has RED left child {node.left.key}"
            if node.right is not None:
                assert node.right.color == BLACK, \
                    f"RED node {node.key} has RED right child {node.right.key}"

        # Rule 5: Equal black-height on both sides
        left_bh = self._validate_node(node.left)
        right_bh = self._validate_node(node.right)
        assert left_bh == right_bh, \
            f"Black-height mismatch at {node.key}: left={left_bh}, right={right_bh}"

        # Add 1 to black-height if this node is BLACK
        return left_bh + (1 if node.color == BLACK else 0)

    def _validate_parents(self, node, expected_parent):
        """Check that every node's parent pointer is correct."""
        if node is None:
            return
        assert node.parent is expected_parent, \
            f"Node {node.key} parent is {node.parent}, expected {expected_parent}"
        self._validate_parents(node.left, node)
        self._validate_parents(node.right, node)
