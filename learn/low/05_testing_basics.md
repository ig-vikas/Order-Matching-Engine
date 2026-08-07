# Testing Basics — For Absolute Beginners

> **What is testing?** Testing is writing code that checks if your other code works correctly.
> You write a test that says "if I do X, I expect Y to happen." Then you run it.
> If Y happens → ✅ PASS. If something else happens → ❌ FAIL.

---

## 1. Why Test?

Imagine you fix a bug in the cancel function. But your fix accidentally breaks the matching function. Without tests, you wouldn't know until a user reports it. With tests, you'd know immediately.

```
Without tests:
    You: "I fixed the cancel bug!"
    User: "But now my orders aren't matching..."
    You: "Oh no..."

With tests:
    You: "I fixed the cancel bug!"
    Tests: "✅ Cancel works, ❌ Matching is broken!"
    You: "Good thing I caught that before shipping."
```

---

## 2. unittest — Python's Built-In Test Framework

### Basic Structure

```python
import unittest

class TestCalculator(unittest.TestCase):
    """A test class. Each method starting with 'test_' is a test."""
    
    def test_addition(self):
        """Test that 2 + 2 = 4."""
        result = 2 + 2
        self.assertEqual(result, 4)  # Is result equal to 4?
    
    def test_subtraction(self):
        """Test that 10 - 3 = 7."""
        result = 10 - 3
        self.assertEqual(result, 7)

# Run the tests:
if __name__ == "__main__":
    unittest.main()
```

Running it:
```
$ python -m pytest test_calculator.py -v
test_addition PASSED
test_subtraction PASSED
```

### Key Rules

1. Test file names start with `test_` (e.g., `test_order_types.py`)
2. Test class inherits from `unittest.TestCase`
3. Test methods start with `test_` (e.g., `test_limit_order`)
4. Use `self.assert*` methods to check results

---

## 3. Assertion Methods — Checking Results

| Method | What It Checks | Example |
|--------|---------------|---------|
| `assertEqual(a, b)` | a == b | `assertEqual(2+2, 4)` |
| `assertNotEqual(a, b)` | a != b | `assertNotEqual(2+2, 5)` |
| `assertTrue(x)` | x is True | `assertTrue(order.is_active)` |
| `assertFalse(x)` | x is False | `assertFalse(order.is_cancelled)` |
| `assertIsNone(x)` | x is None | `assertIsNone(engine.get_best_bid())` |
| `assertIsNotNone(x)` | x is not None | `assertIsNotNone(result)` |
| `assertGreater(a, b)` | a > b | `assertGreater(len(trades), 0)` |
| `assertLess(a, b)` | a < b | `assertLess(best_bid, best_ask)` |
| `assertIn(a, b)` | a is in b | `assertIn("AAPL", symbols)` |
| `assertRaises(Error)` | code raises error | see below |

### Checking for Errors
```python
def test_unknown_symbol_raises_error(self):
    """Submitting to an unknown symbol should raise ValueError."""
    with self.assertRaises(ValueError):
        exchange.submit_order("NOPE", "BUY", "LIMIT", 100.0, 10)
    # If ValueError is NOT raised, this test FAILS
```

---

## 4. setUp and tearDown — Preparing for Tests

```python
class TestMatchingEngine(unittest.TestCase):
    
    def setUp(self):
        """
        Runs BEFORE each test.
        Creates a fresh engine so tests don't affect each other.
        """
        self.engine = MatchingEngine()
        self.handler = OrderTypeHandler()
    
    def tearDown(self):
        """
        Runs AFTER each test.
        Clean up if needed.
        """
        pass  # Nothing to clean up for us
    
    def test_limit_no_match(self):
        # self.engine is a FRESH engine (created in setUp)
        order, trades = self.handler.submit_limit(self.engine, Side.BUY, 99.0, 10)
        self.assertEqual(len(trades), 0)
    
    def test_limit_match(self):
        # self.engine is ANOTHER fresh engine (setUp runs again)
        self.handler.submit_limit(self.engine, Side.SELL, 100.0, 10)
        order, trades = self.handler.submit_limit(self.engine, Side.BUY, 100.0, 10)
        self.assertEqual(len(trades), 1)
```

**Why setUp?** Each test gets a clean starting state. Test A can't accidentally break Test B.

---

## 5. Our Actual Test Files — What Each One Tests

### test_order_types.py (25 tests)

```python
class TestMarketOrder(unittest.TestCase):
    def setUp(self):
        self.engine = MatchingEngine()
        self.handler = OrderTypeHandler()

    def test_market_buy_fills_at_best_ask(self):
        """MARKET BUY should fill at the best ask price."""
        # Add a sell order first (the resting order)
        self.handler.submit_limit(self.engine, Side.SELL, 100.0, 10)
        
        # Now submit a market buy
        order, trades = self.handler.submit_market(self.engine, Side.BUY, 10)
        
        # Check that it filled at the sell price
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].price, 100.0)  # Filled at $100
        self.assertEqual(trades[0].quantity, 10)   # All 10 shares

    def test_market_no_liquidity(self):
        """MARKET BUY with no asks should produce no trades."""
        order, trades = self.handler.submit_market(self.engine, Side.BUY, 10)
        self.assertEqual(len(trades), 0)           # Nothing to fill against
        self.assertIsNone(self.engine.get_best_bid())  # Should NOT rest in book

    def test_market_partial_fill_does_not_rest(self):
        """If MARKET only partially fills, the remainder is cancelled (never rests)."""
        self.handler.submit_limit(self.engine, Side.SELL, 100.0, 5)   # Only 5 available
        order, trades = self.handler.submit_market(self.engine, Side.BUY, 10)  # Want 10
        
        self.assertEqual(trades[0].quantity, 5)    # Only got 5
        self.assertIsNone(self.engine.get_best_bid())  # Remaining 5 NOT in book
        self.assertFalse(self.engine.order_exists(order.order_id))
```

### test_exchange.py (24 tests)

```python
class TestExchangeMultiSymbol(unittest.TestCase):
    def setUp(self):
        self.exchange = Exchange(symbols=["AAPL", "GOOGL"])

    def test_symbol_isolation(self):
        """Orders for AAPL should NOT affect GOOGL."""
        run_async(self.exchange.submit_order("AAPL", "BUY", "LIMIT", 150.0, 100))
        run_async(self.exchange.submit_order("GOOGL", "SELL", "LIMIT", 2800.0, 50))

        aapl_book = run_async(self.exchange.get_order_book("AAPL"))
        googl_book = run_async(self.exchange.get_order_book("GOOGL"))

        # AAPL has bids, no asks
        self.assertEqual(len(aapl_book.bids), 1)
        self.assertEqual(len(aapl_book.asks), 0)

        # GOOGL has asks, no bids
        self.assertEqual(len(googl_book.bids), 0)
        self.assertEqual(len(googl_book.asks), 1)

class TestExchangeConcurrency(unittest.TestCase):
    def test_concurrent_orders_same_symbol(self):
        """100 simultaneous orders should all complete without crashes."""
        exchange = Exchange(symbols=["AAPL"])

        async def run():
            # Add liquidity
            for i in range(50):
                await exchange.submit_order("AAPL", "SELL", "LIMIT", 100.0 + i*0.01, 10)
            
            # Submit 100 orders AT THE SAME TIME
            tasks = [
                asyncio.create_task(
                    exchange.submit_order("AAPL", "BUY", "LIMIT", 100.0 + i*0.01, 5)
                )
                for i in range(100)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for r in results:
                self.assertNotIsInstance(r, Exception)  # No crashes!

        asyncio.get_event_loop().run_until_complete(run())
```

### test_api.py (17 tests)

```python
class TestOrderSubmission(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(test_app)  # Simulates HTTP requests

    def test_submit_limit_order(self):
        resp = self.client.post("/api/v1/orders", json={
            "symbol": "AAPL",
            "side": "BUY",
            "order_type": "LIMIT",
            "price": 150.0,
            "quantity": 100,
        })
        self.assertEqual(resp.status_code, 201)  # 201 = Created
        data = resp.json()
        self.assertEqual(data["status"], "NEW")
        self.assertEqual(data["remaining_quantity"], 100)

    def test_submit_market_with_price_rejected(self):
        """MARKET orders must NOT have a price."""
        resp = self.client.post("/api/v1/orders", json={
            "symbol": "AAPL",
            "side": "BUY",
            "order_type": "MARKET",
            "price": 150.0,      # ← This is wrong!
            "quantity": 10,
        })
        self.assertEqual(resp.status_code, 422)  # Validation error
```

---

## 6. Test Patterns — How to Think About Testing

### Pattern 1: Arrange → Act → Assert

```python
def test_exact_match(self):
    # ARRANGE — set up the initial state
    self.engine.add_limit_order(Side.SELL, 100.0, 10)
    
    # ACT — do the thing you're testing
    order, trades = self.engine.add_limit_order(Side.BUY, 100.0, 10)
    
    # ASSERT — check the result
    self.assertEqual(len(trades), 1)
    self.assertEqual(trades[0].price, 100.0)
    self.assertEqual(trades[0].quantity, 10)
```

### Pattern 2: Test the Happy Path AND the Edge Cases

```python
# Happy path — things work as expected
def test_cancel_active_order(self):
    resp = submit_order(...)
    cancel_resp = cancel_order(resp.order_id)
    self.assertEqual(cancel_resp.status, "CANCELLED")

# Edge case — what happens when things go wrong
def test_cancel_nonexistent_order(self):
    result = cancel_order(99999)
    self.assertIsNone(result)

# Edge case — empty state
def test_empty_book(self):
    book = get_order_book("AAPL")
    self.assertEqual(len(book.bids), 0)
    self.assertEqual(len(book.asks), 0)
    self.assertIsNone(book.spread)
```

### Pattern 3: Test Invariants (Things That Must ALWAYS Be True)

```python
# No matter what orders we submit, the book should NEVER be "crossed"
# (best_bid should always be LESS than best_ask)
def test_book_never_crossed(self):
    # Submit random orders...
    best_bid = engine.get_best_bid()
    best_ask = engine.get_best_ask()
    if best_bid is not None and best_ask is not None:
        self.assertLess(best_bid, best_ask)  # MUST be true
```

---

## 7. Running Tests

```bash
# Run a specific test file:
pytest tests/test_order_types.py -v

# Run ALL tests:
pytest tests/ -v

# Run a specific test class:
pytest tests/test_exchange.py::TestExchangeBasic -v

# Run a specific test:
pytest tests/test_order_types.py::TestMarketOrder::test_market_no_liquidity -v

# Run with short error messages:
pytest tests/ --tb=short

# Run original engine tests:
pytest pre-req/matching_engine/tests.py -v
```

---

## Our Test Score

```
tests/test_order_types.py  → 25 passed  ✅
tests/test_exchange.py     → 24 passed  ✅
tests/test_persistence.py  → 10 passed  ✅
tests/test_analytics.py    →  7 passed  ✅
tests/test_api.py          → 17 passed  ✅
tests/test_invariants.py   →  9 passed  ✅
pre-req/tests.py           → 53 passed  ✅
─────────────────────────────────────────
TOTAL                      → 145 passed 🎉
```
