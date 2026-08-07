# SQL Fundamentals — For Absolute Beginners

> **What is SQL?** SQL (Structured Query Language) is the language you use to talk to databases.
> A database is like a big spreadsheet — it stores data in tables with rows and columns.
> SQL lets you ask questions about that data ("What was the average price?", "How many trades happened?").

---

## 1. What is a Database?

Think of a database as a collection of **spreadsheets** (called **tables**).

### Our "trades" Table

| id | trade_id | symbol | price | quantity | buy_order_id | sell_order_id | created_at |
|----|----------|--------|-------|----------|--------------|---------------|------------|
| 1 | 1 | AAPL | 150.00 | 100 | 1 | 2 | 2024-01-15 10:30:00 |
| 2 | 2 | AAPL | 150.50 | 50 | 3 | 4 | 2024-01-15 10:31:00 |
| 3 | 3 | GOOGL | 2800.00 | 10 | 5 | 6 | 2024-01-15 10:32:00 |
| 4 | 4 | AAPL | 149.00 | 200 | 7 | 8 | 2024-01-15 11:00:00 |
| 5 | 5 | MSFT | 300.00 | 75 | 9 | 10 | 2024-01-15 11:15:00 |

- **Columns** = what kind of data (symbol, price, quantity)
- **Rows** = individual records (each trade)
- **Table** = the whole thing

---

## 2. SELECT — Getting Data Out

### Get everything
```sql
SELECT * FROM trades;
-- * means "all columns"
-- Returns ALL rows with ALL columns
```

### Get specific columns
```sql
SELECT symbol, price, quantity FROM trades;
-- Only returns these 3 columns
```

**Result:**

| symbol | price | quantity |
|--------|-------|----------|
| AAPL | 150.00 | 100 |
| AAPL | 150.50 | 50 |
| GOOGL | 2800.00 | 10 |
| AAPL | 149.00 | 200 |
| MSFT | 300.00 | 75 |

---

## 3. WHERE — Filtering Rows

```sql
-- Only AAPL trades:
SELECT * FROM trades WHERE symbol = 'AAPL';

-- Trades over $200:
SELECT * FROM trades WHERE price > 200;

-- AAPL trades with quantity >= 100:
SELECT * FROM trades WHERE symbol = 'AAPL' AND quantity >= 100;

-- AAPL or GOOGL trades:
SELECT * FROM trades WHERE symbol = 'AAPL' OR symbol = 'GOOGL';

-- Same thing using IN:
SELECT * FROM trades WHERE symbol IN ('AAPL', 'GOOGL');
```

---

## 4. ORDER BY — Sorting Results

```sql
-- Sort by price, cheapest first:
SELECT * FROM trades ORDER BY price ASC;
-- ASC = ascending (1, 2, 3... smallest to largest)

-- Sort by price, most expensive first:
SELECT * FROM trades ORDER BY price DESC;
-- DESC = descending (3, 2, 1... largest to smallest)

-- Sort by symbol, then by price within each symbol:
SELECT * FROM trades ORDER BY symbol ASC, price DESC;
```

---

## 5. LIMIT — Only Get N Rows

```sql
-- Get the 3 most recent trades:
SELECT * FROM trades ORDER BY created_at DESC LIMIT 3;

-- Get the single most expensive trade:
SELECT * FROM trades ORDER BY price DESC LIMIT 1;
```

---

## 6. Aggregate Functions — Math on Columns

| Function | What It Does | Example |
|----------|-------------|---------|
| `COUNT(*)` | Count rows | How many trades? |
| `SUM(quantity)` | Add up values | Total shares traded |
| `AVG(price)` | Average | Average trade price |
| `MIN(price)` | Smallest value | Cheapest trade |
| `MAX(price)` | Largest value | Most expensive trade |

```sql
-- How many trades total?
SELECT COUNT(*) FROM trades;
-- Result: 5

-- Total shares traded:
SELECT SUM(quantity) FROM trades;
-- Result: 435

-- Average price:
SELECT AVG(price) FROM trades;
-- Result: 689.90

-- Cheapest and most expensive:
SELECT MIN(price), MAX(price) FROM trades;
-- Result: 149.00, 2800.00

-- All at once:
SELECT
    COUNT(*) AS trade_count,
    SUM(quantity) AS total_volume,
    AVG(price) AS avg_price,
    MIN(price) AS low_price,
    MAX(price) AS high_price
FROM trades;
```

The `AS` keyword gives a name to the result column.

---

## 7. GROUP BY — Aggregate Per Group

"What's the total volume **for each symbol**?"

```sql
SELECT
    symbol,
    COUNT(*) AS trade_count,
    SUM(quantity) AS total_volume,
    AVG(price) AS avg_price
FROM trades
GROUP BY symbol;
```

**Result:**

| symbol | trade_count | total_volume | avg_price |
|--------|-------------|--------------|-----------|
| AAPL | 3 | 350 | 149.83 |
| GOOGL | 1 | 10 | 2800.00 |
| MSFT | 1 | 75 | 300.00 |

### How GROUP BY Works (Step by Step)

```
Step 1: Take all rows
Step 2: Put them into groups by symbol:
    AAPL group:  [150, 100] [150.50, 50] [149, 200]
    GOOGL group: [2800, 10]
    MSFT group:  [300, 75]
Step 3: Apply aggregate function to each group:
    AAPL:  SUM(quantity) = 100+50+200 = 350
    GOOGL: SUM(quantity) = 10
    MSFT:  SUM(quantity) = 75
```

---

## 8. HAVING — Filter AFTER Grouping

WHERE filters BEFORE grouping. HAVING filters AFTER.

```sql
-- Symbols with more than 1 trade:
SELECT symbol, COUNT(*) AS trade_count
FROM trades
GROUP BY symbol
HAVING COUNT(*) > 1;
```

| symbol | trade_count |
|--------|-------------|
| AAPL | 3 |

```
Think of it as:
1. WHERE filters individual rows
2. GROUP BY groups them
3. Aggregate functions compute
4. HAVING filters the groups
```

---

## 9. VWAP — The Key Formula

**VWAP = Volume-Weighted Average Price**

This is THE most important metric in trading. It tells you the "fair" average price, weighted by how many shares traded at each price.

```
Trades:
    $150.00 × 100 shares = $15,000
    $150.50 × 50 shares  = $7,525
    $149.00 × 200 shares = $29,800

VWAP = Total Dollar Volume / Total Shares
     = ($15,000 + $7,525 + $29,800) / (100 + 50 + 200)
     = $52,325 / 350
     = $149.50
```

Plain average would be ($150 + $150.50 + $149) / 3 = $149.83
VWAP is $149.50 — the $149 trade had MORE weight because it was 200 shares.

### In SQL

```sql
SELECT
    ROUND(SUM(price * quantity) * 1.0 / SUM(quantity), 4) AS vwap,
    SUM(quantity) AS total_volume
FROM trades
WHERE symbol = 'AAPL';
```

This is our actual query from `src/persistence/analytics.py`!

---

## 10. Subqueries — A Query Inside a Query

```sql
-- Find trades where the price is above average:
SELECT * FROM trades
WHERE price > (SELECT AVG(price) FROM trades);
-- The inner query runs first: AVG(price) = 689.90
-- Then the outer query finds all trades with price > 689.90
```

---

## 11. Window Functions — The Advanced Stuff

Window functions let you do calculations ACROSS rows without collapsing them.

### ROW_NUMBER — Numbering Rows

```sql
-- Number each trade within its symbol group:
SELECT
    trade_id, symbol, price,
    ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY created_at DESC) AS rn
FROM trades;
```

| trade_id | symbol | price | rn |
|----------|--------|-------|----|
| 4 | AAPL | 149.00 | 1 |
| 2 | AAPL | 150.50 | 2 |
| 1 | AAPL | 150.00 | 3 |
| 3 | GOOGL | 2800.00 | 1 |
| 5 | MSFT | 300.00 | 1 |

`PARTITION BY symbol` = restart numbering for each symbol
`ORDER BY created_at DESC` = newest gets #1

### "Top N Per Group" Pattern

```sql
-- Get the latest 2 trades for EACH symbol:
SELECT * FROM (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY symbol ORDER BY created_at DESC
    ) AS rn
    FROM trades
) ranked
WHERE rn <= 2;
```

This is a **classic interview question**!

### SUM as a Window Function (Running Total)

```sql
-- Running total of volume:
SELECT
    trade_id, quantity,
    SUM(quantity) OVER (ORDER BY created_at) AS running_total
FROM trades WHERE symbol = 'AAPL';
```

| trade_id | quantity | running_total |
|----------|----------|---------------|
| 1 | 100 | 100 |
| 2 | 50 | 150 |
| 4 | 200 | 350 |

---

## 12. Our Actual SQL Tables

From `src/models/database.py`:

### Orders Table
```sql
CREATE TABLE orders (
    id            INTEGER PRIMARY KEY,
    order_id      INTEGER UNIQUE NOT NULL,   -- Engine's order ID
    symbol        VARCHAR(10) NOT NULL,      -- "AAPL"
    side          VARCHAR(4) NOT NULL,       -- "BUY" or "SELL"
    order_type    VARCHAR(10) NOT NULL,      -- "LIMIT", "MARKET", etc.
    price         FLOAT,                     -- NULL for MARKET orders
    quantity      INTEGER NOT NULL,          -- Original quantity
    remaining_qty INTEGER NOT NULL,          -- How much is left
    status        VARCHAR(10) NOT NULL,      -- "NEW", "FILLED", etc.
    created_at    DATETIME,
    updated_at    DATETIME
);
```

### Trades Table
```sql
CREATE TABLE trades (
    id            INTEGER PRIMARY KEY,
    trade_id      INTEGER UNIQUE NOT NULL,
    symbol        VARCHAR(10) NOT NULL,
    price         FLOAT NOT NULL,
    quantity      INTEGER NOT NULL,
    buy_order_id  INTEGER NOT NULL,
    sell_order_id INTEGER NOT NULL,
    created_at    DATETIME
);
```

---

## Summary — SQL Cheat Sheet

| What You Want | SQL |
|---------------|-----|
| Get all data | `SELECT * FROM trades` |
| Filter rows | `WHERE symbol = 'AAPL'` |
| Sort | `ORDER BY price DESC` |
| Limit results | `LIMIT 10` |
| Count rows | `SELECT COUNT(*) FROM trades` |
| Total volume | `SELECT SUM(quantity) FROM trades` |
| Average price | `SELECT AVG(price) FROM trades` |
| Per-group stats | `GROUP BY symbol` |
| Filter groups | `HAVING COUNT(*) > 5` |
| VWAP | `SUM(price*qty) / SUM(qty)` |
| Row numbering | `ROW_NUMBER() OVER (...)` |
| Running total | `SUM(x) OVER (ORDER BY ...)` |
