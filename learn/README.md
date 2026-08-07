# 🎓 Complete Learning Guide — Order Matching Engine

Everything you need to understand this project, organized by difficulty level into dedicated Markdown files.

---

## 🟢 LOW — Foundations (Absolute Beginner Level)

| # | File | Topics Covered |
|---|------|----------------|
| 1 | [`low/01_python_foundations.md`](low/01_python_foundations.md) | Variables, Functions, Classes, Dataclasses, Enums, Lists, Dicts, Type Hints, Loops, Error Handling, Imports, Generators, `yield` |
| 2 | [`low/02_basic_data_structures.md`](low/02_basic_data_structures.md) | Arrays, Singly & Doubly Linked Lists, Hash Maps, BSTs, Heaps, and the Three-Layer Order Book combination |
| 3 | [`low/03_sql_fundamentals.md`](low/03_sql_fundamentals.md) | SELECT, WHERE, ORDER BY, LIMIT, Aggregates, GROUP BY, HAVING, Subqueries, VWAP formula, Window Functions, Database Schemas |
| 4 | [`low/04_http_and_rest.md`](low/04_http_and_rest.md) | HTTP protocol, GET/POST/DELETE/PATCH methods, Status codes, JSON formatting, REST design rules, API reference, Curl commands |
| 5 | [`low/05_testing_basics.md`](low/05_testing_basics.md) | Unittest framework, Assertion methods, `setUp`/`tearDown`, Project test suite breakdown, AAA testing pattern |

---

## 🟡 MEDIUM — Project Components & Core Architecture

| # | File | Topics Covered |
|---|------|----------------|
| 1 | [`medium/01_red_black_tree.md`](medium/01_red_black_tree.md) | Self-balancing tree properties, Left/Right rotations, Insert Fix-Up (3 cases), Delete Fix-Up (4 cases), Validation logic |
| 2 | [`medium/02_order_book_design.md`](medium/02_order_book_design.md) | Three-layer design (RB-Tree + DLL + Hash Map), Step-by-step Add/Cancel workflows, Market Depth calculation, Complexity analysis |
| 3 | [`medium/03_matching_algorithm.md`](medium/03_matching_algorithm.md) | Price-Time Priority rules, Matching loop execution step-by-step, Resting order price principle, Self-crossing prevention, Partial fills |
| 4 | [`medium/04_order_types.md`](medium/04_order_types.md) | LIMIT, MARKET (extreme-price trick), IOC, FOK (read-only liquidity check before fill), Composition Over Modification principle |
| 5 | [`medium/05_async_python.md`](medium/05_async_python.md) | Synchronous vs Asynchronous execution, Coroutines, Event loop, `async`/`await`, `asyncio.gather` concurrency |
| 6 | [`medium/06_fastapi_and_pydantic.md`](medium/06_fastapi_and_pydantic.md) | Pydantic data validation schemas, FastAPI APIRouter handlers, Custom model validators, Lifespan context managers |
| 7 | [`medium/07_sqlalchemy_orm.md`](medium/07_sqlalchemy_orm.md) | Declarative Base models, AsyncSession handling, Repository pattern, Persistent database operations |
| 8 | [`medium/08_sql_analytics.md`](medium/08_sql_analytics.md) | Hourly VWAP calculation, Window functions (`ROW_NUMBER OVER PARTITION`), Rolling volume metrics |

---

## 🔴 HIGH — Advanced Systems & Interview Deep-Dives

| # | File | Topics Covered |
|---|------|----------------|
| 1 | [`high/01_concurrency_and_locking.md`](high/01_concurrency_and_locking.md) | Race conditions in trading, Double-fill vulnerabilities, Per-symbol `asyncio.Lock` isolation strategy |
| 2 | [`high/02_system_design.md`](high/02_system_design.md) | Full system topology, In-memory source of truth vs persistent storage, Asynchronous notification broadcasting |
| 3 | [`high/03_property_based_testing.md`](high/03_property_based_testing.md) | Hypothesis framework, State invariants (Conservation of Quantity, No Crossed Book, Tree balance), Random test generation |
| 4 | [`high/04_scaling_and_low_latency.md`](high/04_scaling_and_low_latency.md) | Memory layout bottlenecks, Fixed-price arrays, Object pooling, Kernel bypass (DPDK), C++ optimization strategies |
| 5 | [`high/05_websocket_realtime.md`](high/05_websocket_realtime.md) | WebSockets vs HTTP polling, ConnectionManager implementation, Pub/Sub broad-casting for real-time market feeds |
| 6 | [`high/06_database_optimization.md`](high/06_database_optimization.md) | B-Tree database indexes, Composite indexes for time-series data, EXPLAIN query plan optimization |
