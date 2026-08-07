# FastAPI and Pydantic — API Layer Architecture

> **What is FastAPI?** A modern high-performance web framework for building APIs with Python.
> **What is Pydantic?** A data validation and parsing library that enforces type hints at runtime.

---

## 1. Request Validation with Pydantic Models

Pydantic automatically parses JSON payloads, converts types, and enforces validation rules before passing data to route handlers.

```python
# src/models/schemas.py snippet

from pydantic import BaseModel, Field, model_validator
from enum import Enum

class SideEnum(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderTypeEnum(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"

class OrderRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10, description="Ticker symbol")
    side: SideEnum
    order_type: OrderTypeEnum
    price: float | None = Field(default=None, gt=0)
    quantity: int = Field(..., gt=0, description="Order quantity")

    @model_validator(mode="after")
    def validate_price_rules(self):
        if self.order_type == OrderTypeEnum.LIMIT and self.price is None:
            raise ValueError("LIMIT orders require a price")
        if self.order_type == OrderTypeEnum.MARKET and self.price is not None:
            raise ValueError("MARKET orders cannot specify a price")
        return self
```

---

## 2. FastAPI Route Handlers

FastAPI maps HTTP endpoints directly to Python functions.

```python
# src/api/routes.py snippet

from fastapi import APIRouter, HTTPException, status
from src.models.schemas import OrderRequest, OrderResponse

router = APIRouter()

@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def submit_order(request: OrderRequest):
    try:
        response = await exchange.submit_order(
            symbol=request.symbol,
            side=request.side.value,
            order_type=request.order_type.value,
            price=request.price,
            quantity=request.quantity
        )
        return response
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
```

---

## 3. Lifespan Events (Startup & Shutdown)

FastAPI manages resource lifecycles (such as database engines or exchange startup) using lifespan context managers.

```python
# src/main.py snippet

from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.engine.exchange import Exchange

exchange_instance = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global exchange_instance
    # Startup phase: Initialize multi-symbol exchange
    exchange_instance = Exchange(symbols=["AAPL", "GOOGL", "MSFT"])
    yield
    # Shutdown phase: Clean up connections
    exchange_instance = None

app = FastAPI(title="Order Matching Engine API", lifespan=lifespan)
```
