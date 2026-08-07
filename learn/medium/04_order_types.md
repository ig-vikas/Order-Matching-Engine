# Order Types — LIMIT, MARKET, IOC, FOK

> **What are order types?** Different ways to submit an order, each with different rules
> about how it should be executed. Every real exchange supports these.

---

## 1. LIMIT Order — "I want this exact price or better"

### What It Does
- Tries to match at the specified price (or better)
- If not fully filled, the remainder **stays in the book** waiting for a match

### Example
```
You: "BUY 100 AAPL at $150.00"

Case 1: Best ask is $148.00 (cheaper than your limit!)
    → Trade happens at $148.00 (you get a better deal!)
    → Order is FILLED

Case 2: Best ask is $152.00 (too expensive)
    → No trade
    → Your order sits in the book at $150.00
    → Status: NEW (waiting for someone to sell at $150 or less)

Case 3: Best ask is $150.00 for only 60 shares
    → Trade: 60 shares at $150.00
    → Remaining 40 shares stay in the book
    → Status: PARTIAL
```

### Code (from src/engine/order_types.py)
```python
def submit_limit(self, engine, side, price, quantity):
    """
    LIMIT is the simplest — just call the engine's add_limit_order directly.
    The engine handles matching and resting automatically.
    """
    order, trades = engine.add_limit_order(side, price, quantity)
    return order, trades
```

---

## 2. MARKET Order — "I want to buy/sell RIGHT NOW at whatever price"

### What It Does
- Executes immediately at the best available price
- **Never rests in the book** — if it can't fill completely, the remainder is cancelled
- Does NOT have a price limit

### Example
```
Book:
    Asks: $149.50 (100 shares), $150.00 (200 shares)

You: "MARKET BUY 150 shares"

Trade 1: 100 shares at $149.50 (sweeps the cheapest ask)
Trade 2: 50 shares at $150.00 (fills the rest from next level)
Status: FILLED

You: "MARKET BUY 500 shares" (but only 300 total shares available)

Trades: 100 @ $149.50, 200 @ $150.00 (gets 300 shares)
Remaining 200: CANCELLED (not resting — market orders never wait)
Status: CANCELLED
```

### The Extreme-Price Trick

How do you make a MARKET order using an engine that only supports LIMIT orders?

```python
def submit_market(self, engine, side, quantity):
    """
    Trick: Submit a LIMIT order at an EXTREME price.
    
    BUY at $999,999,999 → crosses every possible ask
    SELL at $0.01        → crosses every possible bid
    
    The order sweeps the entire book, filling everything available.
    Then we cancel whatever remains (MARKET orders never rest).
    """
    if side == Side.BUY:
        extreme_price = 999_999_999.0  # Higher than any possible ask
    else:
        extreme_price = 0.01           # Lower than any possible bid
    
    order, trades = engine.add_limit_order(side, extreme_price, quantity)
    
    # Cancel remainder — MARKET orders never rest in the book
    if order.quantity > 0:
        engine.cancel_order(order.order_id)
    
    return order, trades
```

**Why this is clever**: We don't need to write ANY new matching logic. The existing LIMIT matching loop handles everything. A BUY at $999,999,999 will match against every ask because $999,999,999 ≥ any ask price.

---

## 3. IOC Order — "Immediate or Cancel"

### What It Does
- Tries to match immediately, just like a LIMIT order
- But the remainder is **cancelled** instead of resting in the book
- It's like a LIMIT that never waits

### Example
```
Book:
    Asks: $150.00 (60 shares)

You: "IOC BUY 100 shares at $150.00"

Trade: 60 shares at $150.00 (fills what's available)
Remaining 40 shares: CANCELLED (not waiting!)
Status: CANCELLED

vs. if this were a LIMIT order:
    40 shares would sit in the book at $150.00 waiting
```

### When to Use IOC
- You want to get what you can RIGHT NOW
- You don't want your order sitting in the book for hours/days
- You want to take liquidity but not provide it

### Code
```python
def submit_ioc(self, engine, side, price, quantity):
    """
    IOC = LIMIT order + cancel remainder.
    
    1. Submit as a normal LIMIT order
    2. Whatever doesn't fill immediately → cancel it
    """
    order, trades = engine.add_limit_order(side, price, quantity)
    
    # Cancel any remaining quantity
    if order.quantity > 0 and engine.order_exists(order.order_id):
        engine.cancel_order(order.order_id)
    
    return order, trades
```

---

## 4. FOK Order — "Fill or Kill"

### What It Does
- Either fills **100% of the order** or **rejects it entirely**
- No partial fills, no resting
- "All or nothing"

### Example
```
Book:
    Asks: $150.00 (200 shares)

You: "FOK BUY 100 shares at $150.00"
    → 200 available ≥ 100 needed → FILL!
    → Trade: 100 shares at $150.00
    → Status: FILLED ✅

You: "FOK BUY 300 shares at $150.00"
    → 200 available < 300 needed → REJECT!
    → No trades happen
    → The book is UNCHANGED
    → Status: REJECTED ❌
```

### The Trick — Check Before Submitting

We can't submit the order and then undo it if it partially fills (trades can't be undone). So we CHECK first:

```python
def submit_fok(self, engine, side, price, quantity):
    """
    FOK requires a READ-ONLY liquidity check BEFORE submitting.
    
    1. Walk through the book and count available quantity
    2. If enough → submit (guaranteed to fill)
    3. If not enough → reject (book untouched)
    """
    # Step 1: Count available liquidity (WITHOUT modifying the book)
    available = 0
    
    if side == Side.BUY:
        node = engine._book.best_ask()
        while node is not None and node.key <= price:
            # This ask is within our price limit
            level = node.value
            for order in level:
                available += order.quantity
            if available >= quantity:
                break  # We have enough, stop counting
            node = engine._book._asks.successor(node)
    else:
        node = engine._book.best_bid()
        while node is not None and node.key >= price:
            level = node.value
            for order in level:
                available += order.quantity
            if available >= quantity:
                break
            node = engine._book._bids.predecessor(node)
    
    # Step 2: Decision
    if available < quantity:
        # NOT enough liquidity → REJECT
        # Create a dummy order with REJECTED status
        order = Order(order_id=engine._next_id, side=side,
                     price=price, quantity=quantity)
        engine._next_id += 1
        order.quantity = quantity  # Nothing filled
        return order, []  # No trades
    
    # Step 3: Enough liquidity → submit (guaranteed to fill completely)
    order, trades = engine.add_limit_order(side, price, quantity)
    return order, trades
```

**Why check first?** Once a trade is created, it's permanent. You can't "undo" a partial fill. So we verify there's enough liquidity BEFORE submitting. If the check passes, the actual submission is guaranteed to fill completely (because we hold the lock — no one else can modify the book between the check and the submission).

---

## Comparison Table

| Feature | LIMIT | MARKET | IOC | FOK |
|---------|-------|--------|-----|-----|
| Has a price? | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes |
| Can rest in book? | ✅ Yes | ❌ Never | ❌ Never | ❌ Never |
| Partial fill? | ✅ Yes (rests remainder) | ✅ Yes (cancels remainder) | ✅ Yes (cancels remainder) | ❌ No (all or nothing) |
| Guarantees fill? | ❌ No | ❌ No (depends on liquidity) | ❌ No | ✅ If accepted, always 100% |

---

## How We Test Each Type — Key Assertions

```python
# MARKET: Never rests in book
order, trades = handler.submit_market(engine, Side.BUY, 10)
assertFalse(engine.order_exists(order.order_id))  # NOT in book

# IOC: Never rests in book
order, trades = handler.submit_ioc(engine, Side.BUY, 100.0, 10)
assertFalse(engine.order_exists(order.order_id))  # NOT in book

# FOK: Rejected if not enough liquidity
order, trades = handler.submit_fok(engine, Side.BUY, 100.0, 1000)
assertEqual(len(trades), 0)  # No trades
# Book is UNCHANGED after rejection

# LIMIT: Rests if unmatched
order, trades = handler.submit_limit(engine, Side.BUY, 100.0, 10)
assertTrue(engine.order_exists(order.order_id))  # IS in book
```

---

## Design Pattern: Composition Over Modification

Notice we NEVER modified the core `MatchingEngine`. All four order types are built ON TOP of it using only its public methods:
- `add_limit_order()` — submit
- `cancel_order()` — cancel
- `order_exists()` — check
- `_book.best_ask()` / `_book.best_bid()` — read book state

This is the **Open/Closed Principle**: "Open for extension, closed for modification."
