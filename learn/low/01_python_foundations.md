# Python Foundations — For Absolute Beginners

> **What is this?** This file teaches you every Python concept used in the matching engine project.
> If you're new to Python, start here. Everything is explained like you're seeing it for the first time.

---

## What is Python?

Python is a programming language. You write instructions in a `.py` file, and the computer follows them.

```python
# This is a comment. Python ignores it. It's for humans.
print("Hello, world!")  # This prints text to the screen.
```

---

## 1. Variables — Boxes That Hold Values

Think of a variable like a **labeled box**. You put a value inside and give it a name.

```python
price = 150.50       # A box called "price" holding the number 150.50
quantity = 100       # A box called "quantity" holding the number 100
symbol = "AAPL"      # A box called "symbol" holding the text "AAPL"
is_active = True     # A box called "is_active" holding True or False
```

### Types of Values

| Type | What It Holds | Example |
|------|--------------|---------|
| `int` | Whole numbers | `100`, `-5`, `0` |
| `float` | Decimal numbers | `150.50`, `3.14`, `-0.01` |
| `str` | Text (strings) | `"AAPL"`, `"BUY"`, `"hello"` |
| `bool` | True or False | `True`, `False` |
| `list` | A collection of things | `[1, 2, 3]`, `["AAPL", "GOOGL"]` |
| `dict` | Key-value pairs | `{"name": "Apple", "price": 150}` |
| `None` | Nothing / empty | `None` |

---

## 2. Functions — Reusable Blocks of Code

A function is a **recipe**. You define it once, then use it whenever you need it.

```python
# DEFINING a function (writing the recipe)
def calculate_total(price, quantity):
    """Multiply price by quantity and return the result."""
    total = price * quantity
    return total

# CALLING the function (using the recipe)
result = calculate_total(150.0, 100)
print(result)  # 15000.0

# You can call it with different inputs every time:
result2 = calculate_total(200.0, 50)
print(result2)  # 10000.0
```

### Key Points:
- `def` means "I'm defining a function"
- The name comes after `def` (like `calculate_total`)
- **Parameters** are the inputs (in parentheses)
- `return` sends a value back to whoever called the function
- The `"""text"""` is called a **docstring** — it explains what the function does

---

## 3. Classes — Blueprints for Objects

A class is a **blueprint** for creating objects. An object is a thing that has data AND behavior.

### Real-World Analogy
```
Blueprint (Class):     "Order" — has a price, quantity, and side
                       Can calculate its total value

Object (Instance):     Order #1: price=150, quantity=100, side=BUY
                       Order #2: price=200, quantity=50, side=SELL
```

### In Python
```python
class Order:
    """Blueprint for a stock market order."""
    
    def __init__(self, price, quantity, side):
        """
        __init__ runs automatically when you create a new Order.
        'self' refers to THIS specific order being created.
        """
        self.price = price          # Store price in this order
        self.quantity = quantity    # Store quantity in this order
        self.side = side           # Store side ("BUY" or "SELL")
    
    def total_value(self):
        """Calculate the total value of this order."""
        return self.price * self.quantity

# Creating objects from the blueprint:
order1 = Order(price=150.0, quantity=100, side="BUY")
order2 = Order(price=200.0, quantity=50, side="SELL")

# Using the objects:
print(order1.price)          # 150.0
print(order1.total_value())  # 15000.0
print(order2.side)           # "SELL"
```

### What is `self`?

`self` = "this specific object". Every method gets `self` as its first parameter.

```python
class Dog:
    def __init__(self, name):
        self.name = name       # THIS dog's name
    
    def bark(self):
        print(f"{self.name} says: Woof!")  # THIS dog's name

rex = Dog("Rex")
buddy = Dog("Buddy")
rex.bark()    # "Rex says: Woof!"
buddy.bark()  # "Buddy says: Woof!"
# self = rex when rex.bark() is called
# self = buddy when buddy.bark() is called
```

---

## 4. Dataclasses — Classes Without the Boilerplate

Writing `__init__` manually is tedious. Dataclasses do it for you.

```python
from dataclasses import dataclass

# ❌ The long way:
class OrderLong:
    def __init__(self, order_id, side, price, quantity):
        self.order_id = order_id
        self.side = side
        self.price = price
        self.quantity = quantity

# ✅ The dataclass way (does the EXACT same thing):
@dataclass
class Order:
    order_id: int
    side: str
    price: float
    quantity: int
```

Both create objects the same way:
```python
order = Order(order_id=1, side="BUY", price=150.0, quantity=100)
print(order.price)  # 150.0
```

### What `@dataclass` Gives You For Free

```python
@dataclass
class Order:
    order_id: int
    price: float
    quantity: int

order = Order(1, 150.0, 100)

# Auto-generated __init__:
# Order(order_id=1, price=150.0, quantity=100) ← works automatically

# Auto-generated __repr__ (print-friendly string):
print(order)  # Order(order_id=1, price=150.0, quantity=100)

# Auto-generated __eq__ (comparison):
order2 = Order(1, 150.0, 100)
print(order == order2)  # True (compares all fields)
```

### ⚠️ The Mutable Default Trap

```python
from dataclasses import dataclass, field

# ❌ BUG: All orders share the SAME list!
@dataclass
class BadPortfolio:
    items: list = []

# ✅ CORRECT: Each portfolio gets its OWN list
@dataclass
class GoodPortfolio:
    items: list = field(default_factory=list)
```

### Where We Use Dataclasses

In `pre-req/matching_engine/order.py`:
```python
@dataclass
class Order:
    order_id: int
    side: 'Side'       # BUY or SELL
    price: float       # Limit price
    quantity: int      # Shares remaining

@dataclass
class Trade:
    price: float       # Execution price
    quantity: int      # Shares traded
    buy_order_id: int  # Who bought
    sell_order_id: int # Who sold
```

---

## 5. Enums — Safe Constants

### The Problem

```python
# Using plain strings is dangerous:
side = "BYUE"  # Typo! Python won't tell you this is wrong.

if side == "BUY":
    print("Buying!")
elif side == "SELL":
    print("Selling!")
# Nothing happens. The typo is silently ignored. This is a bug.
```

### The Solution — Enums

```python
from enum import Enum

class Side(Enum):
    BUY = "BUY"
    SELL = "SELL"

side = Side.BYUE  # ❌ AttributeError! Python catches the typo immediately!
side = Side.BUY   # ✅ This works
```

### Enums in Our Project

```python
# From src/models/schemas.py:

class SideEnum(str, Enum):
    """str + Enum = works with JSON automatically"""
    BUY = "BUY"
    SELL = "SELL"

class OrderTypeEnum(str, Enum):
    LIMIT = "LIMIT"    # "I want to buy at exactly $150"
    MARKET = "MARKET"  # "I want to buy right now at whatever price"
    IOC = "IOC"        # "Fill what you can, cancel the rest"
    FOK = "FOK"        # "Fill ALL of it, or don't fill any"

class OrderStatusEnum(str, Enum):
    NEW = "NEW"             # Order is sitting in the book, waiting
    PARTIAL = "PARTIAL"     # Some of it filled, rest is waiting
    FILLED = "FILLED"       # 100% filled, done
    CANCELLED = "CANCELLED" # User cancelled it
    REJECTED = "REJECTED"   # System rejected it (e.g., FOK with no liquidity)
```

---

## 6. Lists — Collections of Things

```python
# Creating a list
prices = [100.0, 101.5, 99.0, 102.0]
symbols = ["AAPL", "GOOGL", "MSFT"]

# Accessing by index (starts at 0!)
print(prices[0])   # 100.0 (first item)
print(prices[2])   # 99.0 (third item)
print(prices[-1])  # 102.0 (last item)

# Adding items
prices.append(103.0)  # Add to the end
prices.insert(0, 98.0)  # Insert at position 0

# Removing items
prices.remove(99.0)  # Remove first occurrence of 99.0
prices.pop()         # Remove and return the last item
prices.pop(0)        # Remove and return the first item

# Length
print(len(prices))  # How many items

# Looping
for price in prices:
    print(price)

# List comprehension (create a new list from an existing one)
doubled = [p * 2 for p in prices]
expensive = [p for p in prices if p > 100]
```

---

## 7. Dictionaries — Key-Value Pairs

Think of a dictionary like a phone book: look up a name (key), get a number (value).

```python
# Creating a dictionary
stock = {
    "symbol": "AAPL",
    "price": 150.0,
    "volume": 1000000,
}

# Accessing values
print(stock["symbol"])    # "AAPL"
print(stock["price"])     # 150.0
print(stock.get("name"))  # None (doesn't crash if key missing)

# Adding/updating
stock["name"] = "Apple Inc."  # Add new key
stock["price"] = 155.0        # Update existing key

# Removing
del stock["volume"]  # Remove a key

# Checking if key exists
if "price" in stock:
    print("Price exists!")

# Looping
for key, value in stock.items():
    print(f"{key}: {value}")
```

### How Our Project Uses Dictionaries

```python
# Exchange: one engine per symbol
engines = {
    "AAPL": MatchingEngine(),   # AAPL has its own order book
    "GOOGL": MatchingEngine(),  # GOOGL has its own order book
    "MSFT": MatchingEngine(),   # MSFT has its own order book
}

# Cancel an order in O(1):
order_map = {
    1: (dll_node_1, "BUY", 150.0),   # Order 1 → its location
    2: (dll_node_2, "SELL", 151.0),  # Order 2 → its location
    3: (dll_node_3, "BUY", 149.5),   # Order 3 → its location
}
# Want to cancel order 2? Just do: order_map[2] → instant!
```

---

## 8. Type Hints — Labels for Your Variables

Type hints tell you (and your IDE) what type a variable should be. Python doesn't enforce them — they're like comments that tools can understand.

```python
# Without type hints (works but unclear):
def calculate_vwap(prices, volumes):
    total = sum(p * v for p, v in zip(prices, volumes))
    return total / sum(volumes)

# With type hints (much clearer):
def calculate_vwap(prices: list[float], volumes: list[int]) -> float:
    total = sum(p * v for p, v in zip(prices, volumes))
    return total / sum(volumes)
# Now you know: takes list of floats + list of ints, returns a float
```

### Common Type Hints

```python
name: str = "AAPL"              # A string
price: float = 150.0            # A decimal number
count: int = 100                # A whole number
active: bool = True             # True or False
items: list[str] = ["A", "B"]  # A list of strings
prices: dict[str, float] = {"AAPL": 150.0}  # Dict with string keys, float values

# "This could be a float OR None"
best_bid: float | None = None   # Python 3.10+
```

### Where We Use Them

```python
# src/engine/exchange.py
async def submit_order(
    self,
    symbol: str,           # "AAPL"
    side: str,             # "BUY" or "SELL"
    order_type: str,       # "LIMIT", "MARKET", "IOC", "FOK"
    price: float | None,   # 150.0 or None (for MARKET orders)
    quantity: int,         # 100
) -> OrderResponse:        # Returns an OrderResponse object
```

---

## 9. If/Elif/Else — Making Decisions

```python
price = 150.0

if price > 200:
    print("Expensive!")
elif price > 100:
    print("Moderate")
elif price > 50:
    print("Cheap")
else:
    print("Very cheap")

# Output: "Moderate"
```

### How Our Matching Engine Uses Decisions

```python
# From src/engine/exchange.py — choosing which order type to use:
if order_type == "LIMIT":
    order, trades = handler.submit_limit(engine, side, price, quantity)
elif order_type == "MARKET":
    order, trades = handler.submit_market(engine, side, quantity)
elif order_type == "IOC":
    order, trades = handler.submit_ioc(engine, side, price, quantity)
elif order_type == "FOK":
    order, trades = handler.submit_fok(engine, side, price, quantity)
else:
    raise ValueError(f"Unknown order type: {order_type}")
```

---

## 10. Loops — Repeating Things

### For Loop
```python
# Loop through a list
symbols = ["AAPL", "GOOGL", "MSFT"]
for symbol in symbols:
    print(f"Processing {symbol}")

# Loop with index
for i, symbol in enumerate(symbols):
    print(f"{i}: {symbol}")
# 0: AAPL
# 1: GOOGL
# 2: MSFT

# Loop through a dictionary
engines = {"AAPL": engine1, "GOOGL": engine2}
for symbol, engine in engines.items():
    print(f"{symbol} has {len(engine.get_trade_log())} trades")
```

### While Loop
```python
# Keep going until a condition is met
node = linked_list.head
while node is not None:
    print(node.data)
    node = node.next  # Move to next node
```

### How Our Matching Loop Works (Simplified)
```python
# From pre-req/matching_engine/matching_engine.py:
while True:
    best = book.best_ask()  # Get cheapest sell order
    if best is None:
        break  # No more sell orders — stop
    if incoming_order.price < best.key:
        break  # Incoming buy price is too low — stop
    
    # Match against this sell order
    resting_order = best.value.peek_front()
    fill_qty = min(incoming_order.quantity, resting_order.quantity)
    # ... execute the trade ...
```

---

## 11. Error Handling — Try/Except

```python
# Without error handling — program crashes:
price = int("not a number")  # ❌ ValueError: invalid literal

# With error handling — program continues:
try:
    price = int("not a number")
except ValueError:
    print("That's not a valid number!")
    price = 0  # Use a default value instead

# Multiple error types:
try:
    result = order_map[order_id]
except KeyError:
    print(f"Order {order_id} not found")
except Exception as e:
    print(f"Something went wrong: {e}")
finally:
    print("This runs no matter what")
```

### Where We Use It

```python
# src/api/routes.py — don't crash the API if the database fails:
try:
    await OrderRepository.save_order(session, ...)
except Exception:
    pass  # Don't fail the order if DB write fails
```

---

## 12. Imports — Using Code From Other Files

```python
# Import a whole module
import os
print(os.path.join("folder", "file.txt"))

# Import specific things
from dataclasses import dataclass, field
from enum import Enum

# Import with an alias (nickname)
import asyncio as aio

# Import from our own project files
from src.engine.exchange import Exchange
from src.models.schemas import OrderRequest, OrderResponse
from order import Order, Trade, Side
```

### How Our Project Is Organized

```
pre-req/matching_engine/
    order.py          → Order, Trade, Side
    order_book.py     → OrderBook
    matching_engine.py → MatchingEngine
    rb_tree.py        → RBTree

src/
    engine/
        order_types.py → from order import Side (imports from pre-req)
        exchange.py    → from src.engine.order_types import OrderTypeHandler
    models/
        schemas.py     → from pydantic import BaseModel
    api/
        routes.py      → from src.engine.exchange import Exchange
```

---

## 13. F-Strings — Formatted Text

```python
symbol = "AAPL"
price = 150.50
quantity = 100

# f-string — put variables inside text:
message = f"Buy {quantity} shares of {symbol} at ${price}"
# "Buy 100 shares of AAPL at $150.5"

# Formatting numbers:
print(f"Price: ${price:.2f}")      # "Price: $150.50" (2 decimal places)
print(f"Volume: {quantity:,}")     # "Volume: 100" (comma-separated)
print(f"Ratio: {price/quantity:.4f}")  # "Ratio: 1.5050" (4 decimal places)
```

---

## 14. `None` — The Absence of a Value

`None` means "nothing" or "no value". It's not 0, not empty string, not False — it's NOTHING.

```python
best_bid = None  # There are no buy orders yet

# Check for None:
if best_bid is None:
    print("No bids in the book")

if best_bid is not None:
    print(f"Best bid is {best_bid}")

# Common pattern in our project:
def get_best_bid():
    node = self._bids.maximum()
    if node is None:
        return None    # No bids exist
    return node.key    # Return the highest bid price
```

---

## 15. Generators and `yield`

A generator is a function that produces values **one at a time** instead of all at once.

```python
# Regular function — creates entire list in memory:
def get_all_numbers():
    result = []
    for i in range(1000000):
        result.append(i)
    return result  # 1 million items in memory at once!

# Generator — produces one item at a time:
def get_all_numbers():
    for i in range(1000000):
        yield i  # Produce one, pause, wait for next request

# Usage is the same:
for number in get_all_numbers():
    print(number)
```

### Where We Use `yield`

```python
# In our doubly linked list:
class DoublyLinkedList:
    def __iter__(self):
        """Walk through the list, giving one item at a time."""
        node = self.head
        while node is not None:
            yield node.data   # Give this item
            node = node.next  # Move to next

# Now you can do:
for order in price_level_dll:
    print(order.price, order.quantity)
```

---

## Summary — Where Each Concept Appears in the Project

| Python Concept | Where It's Used | File |
|---------------|----------------|------|
| `@dataclass` | Order, Trade objects | `pre-req/order.py` |
| `Enum` | Side (BUY/SELL) | `pre-req/order.py` |
| `str, Enum` | SideEnum, OrderTypeEnum | `src/models/schemas.py` |
| Type hints | Every function signature | All files |
| `dict` | Order tracking, engine mapping | `exchange.py`, `order_book.py` |
| `list` | Trade logs, results | Everywhere |
| For loops | Matching loop, iteration | `matching_engine.py` |
| While loops | Tree/list traversal | `rb_tree.py`, DLL |
| `if/elif/else` | Order type dispatch | `exchange.py` |
| `try/except` | DB error handling | `routes.py` |
| `None` | "No best bid" | `order_book.py` |
| `yield` | DLL iteration | `order_book.py` |
| f-strings | Logging, `__repr__` | `database.py` |
| Imports | Module organization | Every file |
| Functions | Everything is functions | Every file |
| Classes | Every component | Every file |
