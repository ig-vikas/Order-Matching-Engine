# HTTP & REST APIs — For Absolute Beginners

> **What is an API?** It's a way for two programs to talk to each other.
> Our matching engine is a program. The API is how OTHER programs send orders to it and get results back.

---

## 1. What is HTTP?

HTTP = **H**yper**T**ext **T**ransfer **P**rotocol

It's the language that web browsers and servers use to communicate. When you visit `google.com`, your browser sends an HTTP request, and Google's server sends an HTTP response.

```
Your Program                     Our Server
(client)                        (matching engine)
   |                                 |
   |--- HTTP Request --------------->|  "Submit this order"
   |                                 |
   |<-- HTTP Response ---------------|  "Here's the result"
```

---

## 2. HTTP Methods — Types of Requests

| Method | Meaning | Real-World Analogy | Our API Example |
|--------|---------|-------------------|-----------------|
| **GET** | Read/retrieve data | "Show me the menu" | Get order book |
| **POST** | Create something new | "I'd like to place an order" | Submit order |
| **PUT** | Replace something entirely | "Replace my entire order" | (not used) |
| **PATCH** | Update part of something | "Change just the price" | Modify order |
| **DELETE** | Remove something | "Cancel my order" | Cancel order |

### Our Endpoints

```
POST   /api/v1/orders              → Submit a new order (CREATE)
GET    /api/v1/orderbook/AAPL      → View the order book (READ)
DELETE /api/v1/orders/123?symbol=AAPL  → Cancel order #123 (DELETE)
PATCH  /api/v1/orders/123?symbol=AAPL  → Modify order #123 (UPDATE)
GET    /api/v1/trades/AAPL         → View trade history (READ)
GET    /api/v1/health              → Check if server is alive (READ)
```

---

## 3. HTTP Status Codes — The Server's Response

The server sends a number (status code) to tell you what happened.

| Code | Meaning | When We Use It |
|------|---------|---------------|
| **200** | OK — success | Order book returned, trade history returned |
| **201** | Created — something new was made | New order submitted successfully |
| **307** | Redirect — go somewhere else | Root `/` redirects to `/docs` |
| **400** | Bad Request — your input is wrong | Invalid order type |
| **404** | Not Found — doesn't exist | Unknown symbol, order not found |
| **422** | Validation Error — data format wrong | Negative quantity, missing price |
| **500** | Server Error — our fault | Unexpected crash |
| **503** | Service Unavailable — not ready | Exchange not initialized |

### Categories
```
1xx = "Hold on..."        (informational)
2xx = "Here you go!"      (success) ✅
3xx = "Go over there"     (redirect)
4xx = "You messed up"     (client error) ❌
5xx = "I messed up"       (server error) 💥
```

---

## 4. Request and Response — What They Look Like

### Sending an Order (POST Request)

```http
POST /api/v1/orders HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
    "symbol": "AAPL",
    "side": "BUY",
    "order_type": "LIMIT",
    "price": 150.00,
    "quantity": 100
}
```

Parts:
- **Method**: `POST` (we're creating something)
- **URL**: `/api/v1/orders` (where to send it)
- **Headers**: `Content-Type: application/json` (we're sending JSON)
- **Body**: The actual data (our order details)

### Getting a Response Back

```http
HTTP/1.1 201 Created
Content-Type: application/json

{
    "order_id": 1,
    "symbol": "AAPL",
    "side": "BUY",
    "order_type": "LIMIT",
    "price": 150.0,
    "quantity": 100,
    "remaining_quantity": 100,
    "status": "NEW",
    "timestamp": "2024-01-15T10:30:00Z",
    "trades": []
}
```

---

## 5. JSON — The Data Format

JSON (JavaScript Object Notation) is how data is sent back and forth.

```json
{
    "symbol": "AAPL",
    "side": "BUY",
    "price": 150.0,
    "quantity": 100,
    "trades": [
        {
            "trade_id": 1,
            "price": 150.0,
            "quantity": 100
        }
    ]
}
```

JSON types:
- **String**: `"AAPL"` (text in quotes)
- **Number**: `150.0`, `100` (no quotes)
- **Boolean**: `true`, `false`
- **Null**: `null` (nothing)
- **Array**: `[1, 2, 3]` (list of things)
- **Object**: `{"key": "value"}` (key-value pairs)

---

## 6. REST — How to Design Good APIs

REST = **RE**presentational **S**tate **T**ransfer

It's a set of rules for designing APIs:

### Rule 1: URLs Are Nouns (Things), Methods Are Verbs (Actions)

```
✅ GOOD:
    GET  /orders        → get all orders
    POST /orders        → create a new order
    GET  /orders/123    → get order #123
    DELETE /orders/123  → delete order #123

❌ BAD:
    GET /getOrders
    POST /createOrder
    POST /deleteOrder/123
```

### Rule 2: Use Plural Nouns

```
✅ /orders     (not /order)
✅ /trades     (not /trade)
✅ /symbols    (not /symbol)
```

### Rule 3: Nest Related Resources

```
GET /api/v1/orderbook/AAPL        → AAPL's order book
GET /api/v1/trades/AAPL           → AAPL's trades
GET /api/v1/analytics/AAPL/vwap   → AAPL's VWAP
```

### Rule 4: Use Query Parameters for Filters

```
GET /api/v1/trades/AAPL?limit=50        → only 50 trades
GET /api/v1/orderbook/AAPL?levels=10    → top 10 price levels
GET /api/v1/analytics/AAPL/vwap?hours=24  → last 24 hours
```

---

## 7. Our Complete API Reference

### Submit Order
```
POST /api/v1/orders

Body:
{
    "symbol": "AAPL",
    "side": "BUY",          // "BUY" or "SELL"
    "order_type": "LIMIT",  // "LIMIT", "MARKET", "IOC", "FOK"
    "price": 150.0,         // Required for LIMIT/IOC/FOK, forbidden for MARKET
    "quantity": 100          // Must be > 0
}

Response (201):
{
    "order_id": 1,
    "symbol": "AAPL",
    "side": "BUY",
    "status": "NEW",        // or "FILLED", "PARTIAL", "REJECTED", "CANCELLED"
    "trades": [...]         // Any trades that happened
}
```

### Cancel Order
```
DELETE /api/v1/orders/123?symbol=AAPL

Response (200):
{
    "order_id": 123,
    "status": "CANCELLED",
    ...
}
```

### Get Order Book
```
GET /api/v1/orderbook/AAPL?levels=5

Response (200):
{
    "symbol": "AAPL",
    "bids": [
        {"price": 150.0, "volume": 500, "order_count": 3},
        {"price": 149.5, "volume": 200, "order_count": 1}
    ],
    "asks": [
        {"price": 150.5, "volume": 300, "order_count": 2},
        {"price": 151.0, "volume": 100, "order_count": 1}
    ],
    "best_bid": 150.0,
    "best_ask": 150.5,
    "spread": 0.5
}
```

### Get Trade History
```
GET /api/v1/trades/AAPL?limit=10

Response (200):
[
    {"trade_id": 5, "price": 150.0, "quantity": 100, ...},
    {"trade_id": 4, "price": 149.5, "quantity": 50, ...}
]
```

### Health Check
```
GET /api/v1/health

Response (200):
{
    "status": "ok",
    "version": "1.0.0",
    "active_symbols": 5,
    "total_trades": 142
}
```

---

## 8. Swagger UI — Interactive Documentation

When you run our server, visit `http://localhost:8000/docs` to get a beautiful interactive page where you can:

1. See all endpoints with descriptions
2. Try sending requests directly from the browser
3. See request/response schemas
4. Test different inputs

FastAPI generates this automatically from our code! That's one of the biggest advantages of FastAPI.

---

## 9. Testing APIs with curl

`curl` is a command-line tool to send HTTP requests:

```bash
# Submit an order:
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL", "side": "BUY", "order_type": "LIMIT", "price": 150, "quantity": 100}'

# Get order book:
curl http://localhost:8000/api/v1/orderbook/AAPL

# Cancel an order:
curl -X DELETE "http://localhost:8000/api/v1/orders/1?symbol=AAPL"

# Health check:
curl http://localhost:8000/api/v1/health
```
