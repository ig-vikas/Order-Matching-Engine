# Order Matching Engine

A production-grade stock exchange order matching engine built from scratch in Python.

## Architecture

```
Client / Test Script
      │  POST /api/v1/orders
      ▼
FastAPI Layer  ────────────► Exchange Orchestrator (per-symbol asyncio.Lock)
      │                         │
      │                    MatchingEngine (per symbol)
      │                         │  bids: RB-Tree (max by price) + DLL (FIFO)
      │                         │  asks: RB-Tree (min by price) + DLL (FIFO)
      │                         │
      │                    OrderTypeHandler
      │                         │  LIMIT ─ direct passthrough
      │                         │  MARKET ─ extreme-price trick
      │                         │  IOC ─ fill + cancel remainder
      │                         │  FOK ─ check liquidity, then fill or reject
      │                         ▼
      │                    Trade Generation
      │                         │
      ├──────── WebSocket ◄─────┤  (real-time feed)
      │                         │
      └──── SQLAlchemy ─────────┘
              │
              ▼
         SQLite / MySQL
              │
              ▼
         Analytics (VWAP, Spread, OHLC, Volume)
```

## Features

### Core Engine (from scratch — no external libraries)
- **Red-Black Tree** for O(log n) price-level lookup
- **Doubly Linked List** for O(1) FIFO order management at each price level
- **Hash Map** for O(1) order cancellation by ID
- **Price-Time Priority** matching algorithm

### Order Types
| Type | Behavior |
|------|----------|
| **LIMIT** | Place at price, rest in book if unmatched |
| **MARKET** | Execute immediately at best available, never rests |
| **IOC** | Immediate-or-Cancel: fill what you can, cancel rest |
| **FOK** | Fill-or-Kill: fill entirely or reject entirely |

### Multi-Symbol Exchange
- One `MatchingEngine` per symbol (isolated order books)
- `asyncio.Lock` per symbol (concurrent orders for different symbols run in parallel)
- Global trade ID counter for cross-symbol uniqueness

### Persistence
- SQLAlchemy 2.0 async ORM
- `aiosqlite` for development (zero setup)
- `aiomysql` for production (Docker MySQL)
- Orders, Trades, Symbols tables with proper indexing

### SQL Analytics
| Query | What It Does |
|-------|-------------|
| **VWAP** | Volume-Weighted Average Price per hour |
| **Top Symbols** | Rank by traded volume |
| **Spread History** | Price changes between consecutive trades |
| **Rolling Volume** | Trade count per 60-second window |
| **OHLC** | Open/High/Low/Close candlestick data |
| **Cumulative Volume** | Running total with window functions |
| **Latest N per Symbol** | ROW_NUMBER top-N-per-group |

### REST API
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/orders` | Submit order |
| DELETE | `/api/v1/orders/{id}` | Cancel order |
| PATCH | `/api/v1/orders/{id}` | Modify order |
| GET | `/api/v1/orderbook/{symbol}` | Book depth |
| GET | `/api/v1/trades/{symbol}` | Trade history |
| GET | `/api/v1/analytics/{symbol}/vwap` | VWAP |
| GET | `/api/v1/analytics/{symbol}/spread` | Spread |
| GET | `/api/v1/analytics/{symbol}/volume` | Rolling volume |
| GET | `/api/v1/analytics/{symbol}/ohlc` | Candlestick |
| GET | `/api/v1/analytics/top-symbols` | Most active |
| GET | `/api/v1/symbols` | List symbols |
| GET | `/api/v1/health` | Health check |

### WebSocket
- `ws://localhost:8000/ws/feed/{symbol}` — real-time trade + book updates

## Quick Start

For detailed step-by-step setup instructions, Docker setup, and troubleshooting, see **[`SETUP.md`](SETUP.md)**.

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000

# Open Web Trading Terminal
# http://127.0.0.1:8000/app

# Open Swagger docs
# http://127.0.0.1:8000/docs
```

## Run Tests

```bash
# All new tests (92 tests)
pytest tests/ -v

# Original engine tests (53 tests)
pytest pre-req/matching_engine/tests.py -v

# Property-based tests only (with hypothesis)
pytest tests/test_invariants.py -v

# Everything (145 tests)
pytest tests/ pre-req/matching_engine/tests.py -v
```

## Test Coverage

| Test File | Tests | What It Covers |
|-----------|-------|----------------|
| `test_order_types.py` | 25 | LIMIT, MARKET, IOC, FOK |
| `test_exchange.py` | 24 | Multi-symbol, concurrency, cancel, modify |
| `test_persistence.py` | 10 | Order/Trade/Symbol CRUD |
| `test_analytics.py` | 7 | VWAP, volume, spread, OHLC |
| `test_api.py` | 17 | All REST endpoints |
| `test_invariants.py` | 9 | Property-based (conservation, sorted, no crossed book) |
| `pre-req/tests.py` | 53 | Core engine, RB-Tree, DLL, stress |
| **Total** | **145** | |

## Project Structure

```
Order Matching Engine/
├── pre-req/matching_engine/     # Core engine (untouched)
│   ├── rb_tree.py               # Red-Black Tree (732 lines)
│   ├── order_book.py            # Order book with RB-Tree + DLL
│   ├── matching_engine.py       # Price-time priority matching
│   ├── order.py                 # Order, Trade, Side dataclasses
│   └── tests.py                 # 53 original tests
│
├── src/                         # Production system
│   ├── engine/
│   │   ├── order_types.py       # MARKET, IOC, FOK handlers
│   │   └── exchange.py          # Multi-symbol orchestrator + locking
│   ├── models/
│   │   ├── schemas.py           # Pydantic request/response DTOs
│   │   └── database.py          # SQLAlchemy ORM models
│   ├── persistence/
│   │   ├── repository.py        # Async CRUD operations
│   │   └── analytics.py         # 7 SQL analytics queries
│   ├── api/
│   │   ├── routes.py            # 13 REST endpoints
│   │   └── websocket.py         # Live market data feed
│   ├── config.py                # Pydantic-settings config
│   └── main.py                  # FastAPI entry point
│
├── tests/                       # New test suite
│   ├── test_order_types.py      # 25 tests
│   ├── test_exchange.py         # 24 tests
│   ├── test_persistence.py      # 10 tests
│   ├── test_analytics.py        # 7 tests
│   ├── test_api.py              # 17 tests
│   └── test_invariants.py       # 9 property-based tests
│
├── learn/                       # 19 flat markdown learning guides
│   ├── low/                     # 5 foundation guides
│   ├── medium/                  # 8 core concept guides
│   └── high/                    # 6 advanced system design guides
│
├── find.md                      # Complete "What File Is What" breakdown
├── requirements.txt
├── docker-compose.yml
└── README.md
```

## Key Design Decisions

### Why RB-Tree + DLL instead of heapq?
- `heapq` gives O(1) best price but O(n) cancel
- RB-Tree gives O(log n) for everything + O(1) cancel via hash map
- Real exchanges need fast cancels (most orders are cancelled)

### Why asyncio.Lock per symbol?
- Prevents double-fills when two orders arrive simultaneously
- Per-symbol locking means AAPL and GOOGL orders process in parallel
- Single lock per symbol is the "sequencer" pattern used by real exchanges

### Why extreme-price trick for MARKET orders?
- Reuses the entire existing LIMIT matching loop
- BUY at $999999999 crosses every ask
- Cancel remainder after — MARKET orders never rest

### Why FOK checks liquidity before submitting?
- If we submitted first and it partially filled, we'd need to undo trades
- Read-only check first means the book is never modified on rejection
- Guaranteed full fill after passing the check

## Production Deployment

```bash
# Start MySQL
docker-compose up -d

# Set database URL
export DATABASE_URL=mysql+aiomysql://root:matchingengine@localhost:3306/matching_engine

# Run server
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 1
```

> **Note**: Use `--workers 1` because the in-memory order book is not shared across processes.
> For horizontal scaling, you'd need a shared state layer (Redis, shared memory, etc).
