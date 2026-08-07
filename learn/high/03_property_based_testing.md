# Property-Based Testing — Hypothesis Invariants

> **What is Property-Based Testing?** Instead of testing specific hardcoded inputs (e.g. `buy(100)`), property-based testing generates hundreds of random operations to verify that fundamental system invariants **never break**.

---

## 1. Key Invariants Tested

1. **Conservation of Quantity**: Total bought quantity must equal total sold quantity across all trades.
2. **Sorted Order Invariant**: Bids are strictly sorted in descending price order; Asks are sorted ascending.
3. **No Crossed Book**: Best bid price must ALWAYS be strictly less than best ask price (`best_bid < best_ask`).
4. **RB-Tree Structural Integrity**: Red-Black Tree rules (color balancing, height equality) hold after every mutation.

---

## 2. Example Hypothesis Test Code

```python
# tests/test_invariants.py snippet

from hypothesis import given, strategies as st
import unittest
from pre-req.matching_engine.matching_engine import MatchingEngine
from pre-req.matching_engine.order import Side

class TestInvariants(unittest.TestCase):
    
    @given(st.lists(st.tuples(
        st.sampled_from([Side.BUY, Side.SELL]),
        st.floats(min_value=1.0, max_value=1000.0),
        st.integers(min_value=1, max_value=500)
    ), min_size=10, max_size=100))
    def test_no_crossed_book_invariant(self, order_sequence):
        engine = MatchingEngine()
        
        for side, price, qty in order_sequence:
            engine.add_limit_order(side, price, qty)
            
            best_bid = engine.get_best_bid()
            best_ask = engine.get_best_ask()
            
            # The book must NEVER remain crossed after matching completes
            if best_bid is not None and best_ask is not None:
                self.assertLess(best_bid, best_ask)
```
