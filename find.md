# Quick Reference — What File Is What

### 🟢 `learn/low/` — Basic Learning Guides
* **[`learn/low/01_python_foundations.md`](learn/low/01_python_foundations.md)**: Teaches beginner Python (variables, loops, classes, dataclasses, functions).
* **[`learn/low/02_basic_data_structures.md`](learn/low/02_basic_data_structures.md)**: Explains lists, linked lists, hash maps, binary trees, and heaps.
* **[`learn/low/03_sql_fundamentals.md`](learn/low/03_sql_fundamentals.md)**: Explains SQL databases, queries (SELECT, WHERE, GROUP BY), and VWAP math.
* **[`learn/low/04_http_and_rest.md`](learn/low/04_http_and_rest.md)**: Explains how APIs work (HTTP GET/POST, status codes, JSON format).
* **[`learn/low/05_testing_basics.md`](learn/low/05_testing_basics.md)**: Explains unit testing basics (`unittest`, assertions, test structure).

---

### 🟡 `learn/medium/` — Core Project Concepts
* **[`learn/medium/01_red_black_tree.md`](learn/medium/01_red_black_tree.md)**: Explains self-balancing Red-Black Trees and rotation algorithms.
* **[`learn/medium/02_order_book_design.md`](learn/medium/02_order_book_design.md)**: Explains how the RB-Tree, Linked List, and Hash Map work together.
* **[`learn/medium/03_matching_algorithm.md`](learn/medium/03_matching_algorithm.md)**: Step-by-step walkthrough of matching Buy and Sell orders.
* **[`learn/medium/04_order_types.md`](learn/medium/04_order_types.md)**: Explains how LIMIT, MARKET, IOC, and FOK orders work.
* **[`learn/medium/05_async_python.md`](learn/medium/05_async_python.md)**: Explains non-blocking Python (`async`/`await` and event loops).
* **[`learn/medium/06_fastapi_and_pydantic.md`](learn/medium/06_fastapi_and_pydantic.md)**: Explains FastAPI web routes and Pydantic input validation.
* **[`learn/medium/07_sqlalchemy_orm.md`](learn/medium/07_sqlalchemy_orm.md)**: Explains how Python objects save into database tables.
* **[`learn/medium/08_sql_analytics.md`](learn/medium/08_sql_analytics.md)**: Explains advanced analytics SQL queries (VWAP, window rankings).

---

### 🔴 `learn/high/` — Advanced System Design
* **[`learn/high/01_concurrency_and_locking.md`](learn/high/01_concurrency_and_locking.md)**: Explains how per-symbol `asyncio.Lock` prevents double-fill bugs.
* **[`learn/high/02_system_design.md`](learn/high/02_system_design.md)**: Full architecture diagram and data flow of the entire system.
* **[`learn/high/03_property_based_testing.md`](learn/high/03_property_based_testing.md)**: Explains Hypothesis invariant testing with thousands of random orders.
* **[`learn/high/04_scaling_and_low_latency.md`](learn/high/04_scaling_and_low_latency.md)**: Explains how real institutional exchanges reach microsecond speeds.
* **[`learn/high/05_websocket_realtime.md`](learn/high/05_websocket_realtime.md)**: Explains live trade streaming via WebSockets.
* **[`learn/high/06_database_optimization.md`](learn/high/06_database_optimization.md)**: Explains SQL database indexes and query optimization.

---

### ⚡ `src/` — Engine & API Code
* **[`src/engine/order_types.py`](src/engine/order_types.py)**: Code for MARKET, IOC, and FOK order logic.
* **[`src/engine/exchange.py`](src/engine/exchange.py)**: Multi-symbol routing and symbol-locking orchestrator.
* **[`src/models/schemas.py`](src/models/schemas.py)**: Pydantic request/response validation models.
* **[`src/models/database.py`](src/models/database.py)**: SQLAlchemy ORM table schemas for Orders, Trades, and Symbols.
* **[`src/persistence/repository.py`](src/persistence/repository.py)**: Database saving and fetching operations (CRUD).
* **[`src/persistence/analytics.py`](src/persistence/analytics.py)**: 7 SQL analytics queries (VWAP, OHLC, volume rankings).
* **[`src/api/routes.py`](src/api/routes.py)**: REST API endpoints for submitting orders, checking books, and reading trades.
* **[`src/api/websocket.py`](src/api/websocket.py)**: WebSocket connection manager for live market data.
* **[`src/main.py`](src/main.py)**: Main FastAPI application entry point.
* **[`src/config.py`](src/config.py)**: Environment configuration settings.

---

### 🧪 `tests/` — Automated Test Suite
* **[`tests/test_order_types.py`](tests/test_order_types.py)**: 25 tests for LIMIT, MARKET, IOC, and FOK orders.
* **[`tests/test_exchange.py`](tests/test_exchange.py)**: 24 tests for multi-symbol isolation and concurrency.
* **[`tests/test_persistence.py`](tests/test_persistence.py)**: 10 database storage and lookup tests.
* **[`tests/test_analytics.py`](tests/test_analytics.py)**: 7 tests for VWAP and volume rankings.
* **[`tests/test_api.py`](tests/test_api.py)**: 17 API endpoint tests.
* **[`tests/test_invariants.py`](tests/test_invariants.py)**: 9 property-based invariant tests (Hypothesis).
