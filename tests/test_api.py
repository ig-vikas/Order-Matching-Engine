"""
test_api.py — FastAPI endpoint tests using httpx.

Tests the full HTTP API layer:
    - Order submission (all types)
    - Order cancellation
    - Order book queries
    - Trade history
    - Error cases (404, 400, validation)
    - Health check

Uses FastAPI's TestClient which runs the app in-process — no server needed.
The exchange is manually wired since we bypass the lifespan context.
"""

import sys
import os
import asyncio
import unittest

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_ENGINE_PATH = os.path.join(_PROJECT_ROOT, "pre-req", "matching_engine")
_SRC_PATH = os.path.join(_PROJECT_ROOT, "src")

for p in [_ENGINE_PATH, _SRC_PATH, _PROJECT_ROOT]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Set database to in-memory SQLite for tests
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.engine.exchange import Exchange
from src.api import routes as api_routes
from src.api import websocket as ws_routes


def _create_test_app():
    """Create a minimal FastAPI app with exchange wired up (no lifespan needed)."""
    test_app = FastAPI()
    test_exchange = Exchange(symbols=["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"])

    # Wire exchange into route handlers
    api_routes.exchange = test_exchange
    api_routes.db_session_factory = None  # No DB for API tests
    ws_routes.exchange = test_exchange

    test_app.include_router(api_routes.router, prefix="/api/v1")
    return test_app, test_exchange


# Create shared app + exchange for all tests
_test_app, _test_exchange = _create_test_app()


class TestHealthEndpoint(unittest.TestCase):
    """Test the health check endpoint."""

    def setUp(self):
        self.client = TestClient(_test_app)

    def test_health_check(self):
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["version"], "1.0.0")
        self.assertGreater(data["active_symbols"], 0)


class TestSymbolsEndpoint(unittest.TestCase):
    """Test the symbols endpoint."""

    def setUp(self):
        self.client = TestClient(_test_app)

    def test_get_symbols(self):
        resp = self.client.get("/api/v1/symbols")
        self.assertEqual(resp.status_code, 200)
        symbols = resp.json()["symbols"]
        self.assertIn("AAPL", symbols)
        self.assertIn("GOOGL", symbols)


class TestOrderSubmission(unittest.TestCase):
    """Test order submission endpoint."""

    def setUp(self):
        # Use a fresh exchange for each test to avoid state leaking
        global _test_app, _test_exchange
        _test_app, _test_exchange = _create_test_app()
        self.client = TestClient(_test_app)

    def test_submit_limit_order(self):
        resp = self.client.post("/api/v1/orders", json={
            "symbol": "AAPL",
            "side": "BUY",
            "order_type": "LIMIT",
            "price": 150.0,
            "quantity": 100,
        })
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["symbol"], "AAPL")
        self.assertEqual(data["side"], "BUY")
        self.assertEqual(data["status"], "NEW")
        self.assertEqual(data["remaining_quantity"], 100)

    def test_submit_market_order(self):
        # Add a sell first
        self.client.post("/api/v1/orders", json={
            "symbol": "AAPL", "side": "SELL", "order_type": "LIMIT",
            "price": 150.0, "quantity": 50,
        })

        resp = self.client.post("/api/v1/orders", json={
            "symbol": "AAPL",
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": 50,
        })
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertIn(data["status"], ["FILLED", "CANCELLED"])

    def test_submit_invalid_order_negative_qty(self):
        resp = self.client.post("/api/v1/orders", json={
            "symbol": "AAPL", "side": "BUY", "order_type": "LIMIT",
            "price": 150.0, "quantity": -1,
        })
        self.assertEqual(resp.status_code, 422)  # Pydantic validation error

    def test_submit_market_with_price_rejected(self):
        resp = self.client.post("/api/v1/orders", json={
            "symbol": "AAPL", "side": "BUY", "order_type": "MARKET",
            "price": 150.0, "quantity": 10,
        })
        self.assertEqual(resp.status_code, 422)

    def test_submit_limit_without_price_rejected(self):
        resp = self.client.post("/api/v1/orders", json={
            "symbol": "AAPL", "side": "BUY", "order_type": "LIMIT",
            "quantity": 10,
        })
        self.assertEqual(resp.status_code, 422)

    def test_submit_unknown_symbol(self):
        resp = self.client.post("/api/v1/orders", json={
            "symbol": "NOPE", "side": "BUY", "order_type": "LIMIT",
            "price": 100.0, "quantity": 10,
        })
        self.assertEqual(resp.status_code, 404)

    def test_submit_fok_rejected(self):
        resp = self.client.post("/api/v1/orders", json={
            "symbol": "AAPL", "side": "BUY", "order_type": "FOK",
            "price": 150.0, "quantity": 1000,
        })
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["status"], "REJECTED")

    def test_matching_produces_trades(self):
        # Sell first
        self.client.post("/api/v1/orders", json={
            "symbol": "MSFT", "side": "SELL", "order_type": "LIMIT",
            "price": 300.0, "quantity": 50,
        })
        # Buy crosses
        resp = self.client.post("/api/v1/orders", json={
            "symbol": "MSFT", "side": "BUY", "order_type": "LIMIT",
            "price": 300.0, "quantity": 50,
        })
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["status"], "FILLED")
        self.assertEqual(len(data["trades"]), 1)
        self.assertEqual(data["trades"][0]["price"], 300.0)
        self.assertEqual(data["trades"][0]["quantity"], 50)


class TestOrderBookEndpoint(unittest.TestCase):
    """Test order book query endpoint."""

    def setUp(self):
        global _test_app, _test_exchange
        _test_app, _test_exchange = _create_test_app()
        self.client = TestClient(_test_app)

    def test_get_empty_book(self):
        resp = self.client.get("/api/v1/orderbook/AMZN")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["symbol"], "AMZN")

    def test_get_book_with_orders(self):
        self.client.post("/api/v1/orders", json={
            "symbol": "TSLA", "side": "BUY", "order_type": "LIMIT",
            "price": 200.0, "quantity": 100,
        })
        self.client.post("/api/v1/orders", json={
            "symbol": "TSLA", "side": "SELL", "order_type": "LIMIT",
            "price": 205.0, "quantity": 50,
        })

        resp = self.client.get("/api/v1/orderbook/TSLA?levels=5")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreater(len(data["bids"]) + len(data["asks"]), 0)

    def test_get_book_unknown_symbol(self):
        resp = self.client.get("/api/v1/orderbook/NOPE")
        self.assertEqual(resp.status_code, 404)


class TestCancelEndpoint(unittest.TestCase):
    """Test order cancellation endpoint."""

    def setUp(self):
        global _test_app, _test_exchange
        _test_app, _test_exchange = _create_test_app()
        self.client = TestClient(_test_app)

    def test_cancel_nonexistent_order(self):
        resp = self.client.delete("/api/v1/orders/99999?symbol=AAPL")
        self.assertEqual(resp.status_code, 404)

    def test_cancel_unknown_symbol(self):
        resp = self.client.delete("/api/v1/orders/1?symbol=NOPE")
        self.assertEqual(resp.status_code, 404)


class TestTradesEndpoint(unittest.TestCase):
    """Test trade history endpoint."""

    def setUp(self):
        global _test_app, _test_exchange
        _test_app, _test_exchange = _create_test_app()
        self.client = TestClient(_test_app)

    def test_get_trades_empty(self):
        resp = self.client.get("/api/v1/trades/AMZN")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), list)

    def test_get_trades_unknown_symbol(self):
        resp = self.client.get("/api/v1/trades/NOPE")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
