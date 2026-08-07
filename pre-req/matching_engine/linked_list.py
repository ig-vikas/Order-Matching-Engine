"""
linked_list.py — A simple Doubly Linked List built from scratch.

We don't use collections.deque because we need O(1) removal of any
node given a direct pointer to it. deque.remove() is O(n).

The matching engine stores a pointer to each order's DLL node in a
hash map, so when a cancel comes in we can yank it out instantly.
"""


class DLLNode:
    """A single node in the doubly linked list."""

    def __init__(self, data):
        self.data = data
        self.prev = None
        self.next = None

    def __repr__(self):
        return f"DLLNode({self.data!r})"


class DoublyLinkedList:
    """
    Doubly linked list with O(1) append, pop_front, and remove.

    head -> A <-> B <-> C <- tail

    - append(data)   : add to tail, return the node              O(1)
    - pop_front()    : remove from head, return the data          O(1)
    - remove(node)   : unlink a node given its reference          O(1)
    - is_empty()     : check if list has no elements              O(1)

    Why every operation is O(1):
        - append: just update tail pointer and link one node
        - pop_front: just update head pointer
        - remove: given a DIRECT POINTER to the node, just re-link neighbors
                  (no searching needed — this is why we return the node from append)
    """

    def __init__(self):
        self.head = None
        self.tail = None
        self._size = 0

    # ── Add to the end ──

    def append(self, data):
        """Add data to the tail. Returns the new node (save it for O(1) cancel)."""
        node = DLLNode(data)

        if self.tail is None:
            # List was empty — this node is both head and tail
            self.head = node
            self.tail = node
        else:
            # Link after current tail
            node.prev = self.tail
            self.tail.next = node
            self.tail = node

        self._size += 1
        return node

    # ── Remove from the front ──

    def pop_front(self):
        """Remove and return data from the head (oldest order = FIFO)."""
        if self.head is None:
            raise IndexError("pop_front from empty list")

        data = self.head.data

        if self.head is self.tail:
            # Only one element
            self.head = None
            self.tail = None
        else:
            self.head = self.head.next
            self.head.prev = None

        self._size -= 1
        return data

    # ── Remove any node by reference ──

    def remove(self, node):
        """
        Remove a specific node from the list in O(1).

        This is the magic behind fast cancellation:
        we stored the node pointer when the order was added,
        so we just re-link the neighbors.
        """
        # Fix the previous node's next pointer
        if node.prev is not None:
            node.prev.next = node.next
        else:
            # node was the head
            self.head = node.next

        # Fix the next node's prev pointer
        if node.next is not None:
            node.next.prev = node.prev
        else:
            # node was the tail
            self.tail = node.prev

        data = node.data
        # Clean up the removed node
        node.prev = None
        node.next = None
        node.data = None

        self._size -= 1
        return data

    # ── Helpers ──

    def is_empty(self):
        """Check if the list has no elements."""
        return self.head is None

    def peek_front(self):
        """Look at the head without removing it."""
        if self.head is None:
            raise IndexError("peek_front on empty list")
        return self.head.data

    def __len__(self):
        return self._size

    def __iter__(self):
        """Walk from head to tail, yielding each node's data."""
        current = self.head
        while current is not None:
            yield current.data
            current = current.next

    def __repr__(self):
        items = list(self)
        return "DLL" + str(items)
