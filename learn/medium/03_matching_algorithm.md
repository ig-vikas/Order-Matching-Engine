# Matching Algorithm — Price-Time Priority

> **What is matching?** When a buy order's price is high enough to meet a sell order's price,
> they "match" — a trade happens. The matching algorithm decides WHO matches with WHOM.

---

## The Core Rule: Price-Time Priority

```
1. PRICE priority first:
   - Buyers who offer MORE get filled first
   - Sellers who ask LESS get filled first

2. TIME priority second (FIFO):
   - If two orders have the SAME price, whoever placed their order FIRST gets filled first
```

This is how almost every major stock exchange works (NYSE, NASDAQ, LSE, etc.).

---

## When Does a Match Happen?

A match happens when: **best bid ≥ best ask**

```
Bids:                    Asks:
$150.00  (3 orders)      $149.50  (2 orders)  ← best ask
$149.50  (2 orders)      $150.00  (1 order)
$149.00  (1 order)       $151.00  (4 orders)
   ↑ best bid

Best bid ($150.00) ≥ best ask ($149.50)? YES → MATCH!
```

The trade price is always the **resting order's price** (the order that was already in the book). In this case, $149.50 — because the sell order at $149.50 was there first.

---

## The Matching Loop — Step by Step

Here's what happens when a new BUY order at $152 for 250 shares arrives:

```
Starting Book:
    Asks:
        $149.50: [Sell1: 100 shares]
        $150.00: [Sell2: 80 shares] [Sell3: 50 shares]
        $151.00: [Sell4: 200 shares]
        $153.00: [Sell5: 300 shares]

Incoming: BUY $152 for 250 shares
```

### Iteration 1: Match against best ask ($149.50)

```
Is $152 (buy) ≥ $149.50 (best ask)? YES → match!

Fill quantity = min(250 remaining, 100 available) = 100
Trade: 100 shares at $149.50 (resting order's price)

Sell1 is fully filled → remove from book
$149.50 level is empty → remove from tree

Remaining: 250 - 100 = 150 shares still need filling
```

### Iteration 2: Match against new best ask ($150.00, Sell2)

```
Is $152 ≥ $150.00? YES → match!

Fill quantity = min(150 remaining, 80 available) = 80
Trade: 80 shares at $150.00

Sell2 is fully filled → remove from DLL
$150.00 still has Sell3 → level stays

Remaining: 150 - 80 = 70 shares
```

### Iteration 3: Match against $150.00 level (Sell3 — FIFO, it was next)

```
Is $152 ≥ $150.00? YES → match!

Fill quantity = min(70 remaining, 50 available) = 50
Trade: 50 shares at $150.00

Sell3 is fully filled → remove from DLL
$150.00 level is now empty → remove from tree

Remaining: 70 - 50 = 20 shares
```

### Iteration 4: Match against new best ask ($151.00)

```
Is $152 ≥ $151.00? YES → match!

Fill quantity = min(20 remaining, 200 available) = 20
Trade: 20 shares at $151.00

Sell4 partially filled: 200 - 20 = 180 remaining
Sell4 stays in the book with 180 shares

Remaining: 20 - 20 = 0 shares → DONE!
```

### Final Result

```
Trades produced:
    Trade 1: 100 shares @ $149.50
    Trade 2: 80 shares @ $150.00
    Trade 3: 50 shares @ $150.00
    Trade 4: 20 shares @ $151.00

Book after matching:
    Asks:
        $151.00: [Sell4: 180 shares]  ← partially filled
        $153.00: [Sell5: 300 shares]

VWAP of this order: (100×149.50 + 80×150 + 50×150 + 20×151) / 250
                   = (14950 + 12000 + 7500 + 3020) / 250
                   = 37470 / 250
                   = $149.88
```

---

## The Code — From pre-req/matching_engine/matching_engine.py

```python
class MatchingEngine:
    def add_limit_order(self, side, price, quantity):
        """
        Add a limit order. If it crosses the book, match immediately.
        Whatever remains (if any) rests in the book.
        """
        order = Order(
            order_id=self._next_id,
            side=side,
            price=price,
            quantity=quantity,
        )
        self._next_id += 1
        trades = []
        
        if side == Side.BUY:
            # Try to match against asks (sell orders)
            trades = self._match_buy(order)
        else:
            # Try to match against bids (buy orders)
            trades = self._match_sell(order)
        
        # If order still has remaining quantity, rest it in the book
        if order.quantity > 0:
            self._book.add_order(order)
        
        return order, trades
    
    def _match_buy(self, incoming):
        """
        Match incoming BUY order against resting SELL orders.
        Keep matching until:
          1. Incoming order is fully filled, OR
          2. No more sell orders with price ≤ incoming price
        """
        trades = []
        
        while incoming.quantity > 0:
            # Get the best (cheapest) sell order
            best_ask_node = self._book.best_ask()
            if best_ask_node is None:
                break  # No sell orders left
            
            if incoming.price < best_ask_node.key:
                break  # Incoming price is too low — can't match
            
            # Get the first order at this price level (FIFO)
            level = best_ask_node.value
            resting = level.peek_front()
            
            # Calculate fill quantity
            fill_qty = min(incoming.quantity, resting.quantity)
            
            # Create the trade
            trade = Trade(
                price=resting.price,  # Always at the resting order's price!
                quantity=fill_qty,
                buy_order_id=incoming.order_id,
                sell_order_id=resting.order_id,
            )
            trades.append(trade)
            
            # Update quantities
            incoming.quantity -= fill_qty
            resting.quantity -= fill_qty
            
            # Remove fully filled resting order
            if resting.quantity == 0:
                level.pop_front()
                if level.size == 0:
                    self._book._asks.delete(best_ask_node.key)
                    # Empty level → remove from tree
        
        return trades
```

---

## Why Trade Price = Resting Order's Price

This is a fundamental rule. The order that was ALREADY in the book gets its price.

```
Scenario:
    Sell order at $100 is sitting in the book (resting)
    Buy order at $105 arrives (incoming/aggressive)
    
    Trade happens at $100 (the resting sell price), NOT $105
    
    Why? The seller asked for $100, and the buyer was willing to pay UP TO $105.
    The buyer gets a better deal ($100 instead of $105).
    The seller gets exactly what they asked for ($100).
    
    This is fair because:
    - The seller placed their order first (time priority)
    - The seller's price is respected
    - The buyer gets "price improvement" (paid less than they were willing to)
```

---

## Self-Crossing Prevention

What if someone buys and sells to themselves?

```python
# In our matching engine, self-crossing is prevented:
if incoming.order_id == resting.order_id:
    skip  # Don't match against your own order
```

This prevents wash trading (trading with yourself to fake volume).

---

## Partial Fills

What happens when an order is only partially filled?

```
Incoming BUY: 500 shares at $150
Best Ask: 200 shares at $150

Trade: 200 shares at $150

Incoming order still has 300 shares left.
It rests in the book as a BID at $150 for 300 shares.

Now the book has:
    Bids: $150 (300 shares)  ← the remaining quantity

Next time a SELL at $150 arrives, it matches against these 300 shares.
```

---

## The Complete Flow

```
New Order Arrives
       │
       ▼
Is it a BUY or SELL?
       │
  BUY──┤──SELL
  │         │
  ▼         ▼
Check       Check
Best Ask    Best Bid
  │         │
  ▼         ▼
Can it match? (price check)
  │
  ├── YES → Execute trade, reduce quantities
  │         │
  │         └── More quantity? → Loop back to check next best
  │         │
  │         └── Fully filled? → Done!
  │
  └── NO → Rest the remaining quantity in the book
```
