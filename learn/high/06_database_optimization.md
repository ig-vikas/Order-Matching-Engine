# Database Optimization — Indexing and Query Tuning

> **Optimizing SQL Performance:** Ensures query response times remain under 10ms even as trade and order historical logs grow to millions of rows.

---

## 1. Indexing Strategy

Indexes turn table scans (O(n)) into B-Tree lookups (O(log n)).

```sql
-- High-frequency lookup indexes
CREATE INDEX idx_orders_symbol ON orders(symbol);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_trades_symbol_created ON trades(symbol, created_at DESC);
```

### Composite Indexes
For queries filtering on `symbol` and ordering by `created_at`:
`CREATE INDEX idx_trades_symbol_created ON trades(symbol, created_at DESC);`
This allows the database to locate the exact symbol slice and read pre-sorted timestamp rows without performing a separate filesort step.

---

## 2. EXPLAIN Query Execution Plan

Using `EXPLAIN QUERY PLAN` confirms index usage:

```sql
EXPLAIN QUERY PLAN 
SELECT * FROM trades 
WHERE symbol = 'AAPL' 
ORDER BY created_at DESC 
LIMIT 10;
```

**Good Execution Plan Output:**
`SEARCH TABLE trades USING INDEX idx_trades_symbol_created (symbol=?)`
