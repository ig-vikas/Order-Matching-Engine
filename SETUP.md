# 🛠️ Setup & Execution Guide — Order Matching Engine

A step-by-step guide to installing, configuring, running, and testing the Order Matching Engine.

---

## 🚀 Quick Start (Choose Mode 1 or Mode 2)

---

### Mode 1: Local / Development (Zero Setup Needed) 🟢

This mode uses **SQLite** (built directly into Python). No Docker or external database installation is needed.

#### Step 1: Install Dependencies
Open your terminal in the project root folder and run:
```bash
pip install -r requirements.txt
```

#### Step 2: Start the Web App & Server
```bash
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

#### Step 3: Open in Browser
- **Web Trading Dashboard**: [`http://127.0.0.1:8000/app`](http://127.0.0.1:8000/app)
- **Interactive API Docs (Swagger)**: [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs)
- **Alternative Docs (ReDoc)**: [`http://127.0.0.1:8000/redoc`](http://127.0.0.1:8000/redoc)

---

### Mode 2: Production Setup (Docker + MySQL) 🔴

This mode runs a dedicated **MySQL 8.0** server inside Docker for production-grade concurrency.

#### Step 1: Install Docker Desktop
Download and install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/). Make sure Docker is running.

#### Step 2: Start MySQL in Docker
Run:
```bash
docker-compose up -d
```
*(This starts a MySQL container in the background listening on port `3306`)*

#### Step 3: Set the Database URL Environment Variable

**Windows PowerShell:**
```powershell
$env:DATABASE_URL="mysql+aiomysql://root:matchingengine@localhost:3306/matching_engine"
```

**Bash / Mac / Linux:**
```bash
export DATABASE_URL="mysql+aiomysql://root:matchingengine@localhost:3306/matching_engine"
```

#### Step 4: Start the Server
```bash
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

---

## 🧪 Running the Test Suite (145 Tests)

To run all unit tests, integration tests, and property-based invariant tests:

```bash
# Run all tests (92 system tests + 53 core engine tests)
pytest tests/ pre-req/matching_engine/tests.py -v

# Run only new system tests
pytest tests/ -v

# Run only core engine data structure tests
pytest pre-req/matching_engine/tests.py -v

# Run property-based invariant tests (Hypothesis)
pytest tests/test_invariants.py -v
```

---

## 🖥️ Using the Web Trading Terminal

Once the server is running, visit [`http://127.0.0.1:8000/app`](http://127.0.0.1:8000/app):

1. **Symbol Selector**: Click on `AAPL`, `GOOGL`, `MSFT`, `AMZN`, or `TSLA` in the top bar to switch instruments.
2. **Order Entry Form**:
   - Choose `BUY` or `SELL`.
   - Select Order Type: `LIMIT`, `MARKET`, `IOC`, or `FOK`.
   - Enter Price & Quantity and click Submit.
3. **Live Order Book Depth**: Displays active Bid (buy) and Ask (sell) price levels in real time.
4. **Live Trade Stream**: Displays filled trades automatically via WebSockets.
5. **Interactive Chart**: Canvas price chart updates automatically as executions occur.

---

## 📡 API Cheat Sheet

### Submit Order
```bash
curl -X POST http://127.0.0.1:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "side": "BUY",
    "order_type": "LIMIT",
    "price": 150.0,
    "quantity": 100
  }'
```

### View Order Book Depth
```bash
curl http://127.0.0.1:8000/api/v1/orderbook/AAPL
```

### Cancel Order
```bash
curl -X DELETE "http://127.0.0.1:8000/api/v1/orders/1?symbol=AAPL"
```

### Health Check
```bash
curl http://127.0.0.1:8000/api/v1/health
```

---

## 🛑 How to Stop Servers & Services

### 1. Stop Uvicorn Web Server
Press `Ctrl + C` in the terminal window where Uvicorn is running.

### 2. Stop Docker MySQL Database
Run:
```bash
docker-compose stop
```
*(To completely remove the container while saving data, run `docker-compose down`)*

### 3. Reset Local SQLite Database (Clean Slate)
To start fresh with an empty SQLite database, delete the file:
```bash
# Windows PowerShell
Remove-Item matching_engine.db

# Linux / Mac
rm matching_engine.db
```

---

## 💡 Pro Tips & Tricks

- **Auto-Reload Code**: Running Uvicorn with `--reload` automatically updates the server whenever you edit files in `src/`.
- **Fast Testing**: Run pytest with `-k` to execute specific tests (e.g. `pytest -k "test_market"`).
- **In-Memory Speed**: SQLite development mode (`sqlite+aiosqlite:///./matching_engine.db`) requires zero installation and is extremely fast for rapid iterations.
- **WebSocket Testing**: Use the Web Trading Terminal at [`http://127.0.0.1:8000/app`](http://127.0.0.1:8000/app) or Chrome DevTools Network tab to observe raw WebSocket frames (`/ws/feed/AAPL`).

---

## ❓ Troubleshooting

- **Port 8000 in use**: Run `uvicorn src.main:app --port 8001` to run on port 8001 instead.
- **Docker Connection Error**: Make sure Docker Desktop is open and running.
- **Python Version**: Recommended Python 3.10, 3.11, or 3.12.
