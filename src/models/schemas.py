"""
schemas.py — Pydantic request/response models.

These define the exact shape of data coming into and out of the API.
FastAPI uses these for automatic validation, serialization, and Swagger docs.

Every field has a type annotation — Pydantic rejects anything that doesn't match.
This is your first line of defense against bad data (negative quantities, missing prices, etc).
"""

from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, model_validator


# ══════════════════════════════════════════════════════════
#  ENUMS — shared by request and response models
# ══════════════════════════════════════════════════════════

class SideEnum(str, Enum):
    """BUY or SELL — the direction of an order."""
    BUY = "BUY"
    SELL = "SELL"


class OrderTypeEnum(str, Enum):
    """
    Supported order types:
        LIMIT  — specify a price, rest in book if unmatched
        MARKET — execute immediately at best available price, no resting
        IOC    — immediate-or-cancel: fill what you can, cancel the rest
        FOK    — fill-or-kill: fill entirely or reject entirely
    """
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    IOC = "IOC"
    FOK = "FOK"


class OrderStatusEnum(str, Enum):
    """Lifecycle states of an order."""
    NEW = "NEW"             # Resting in the book, no fills yet
    PARTIAL = "PARTIAL"     # Partially filled, remainder still resting
    FILLED = "FILLED"       # Completely filled
    CANCELLED = "CANCELLED" # Cancelled by user (or auto-cancelled for MARKET/IOC)
    REJECTED = "REJECTED"   # Rejected (e.g., FOK with insufficient liquidity)


# ══════════════════════════════════════════════════════════
#  REQUEST MODELS — what the client sends to us
# ══════════════════════════════════════════════════════════

class OrderRequest(BaseModel):
    """
    Request body for POST /orders.

    Validation rules:
        - quantity must be > 0
        - LIMIT orders MUST have a price > 0
        - MARKET orders MUST NOT have a price (we use best available)
        - IOC/FOK orders MUST have a price > 0
    """
    symbol: str = Field(..., min_length=1, max_length=10, description="Ticker symbol (e.g., AAPL)")
    side: SideEnum = Field(..., description="BUY or SELL")
    order_type: OrderTypeEnum = Field(default=OrderTypeEnum.LIMIT, description="Order type")
    price: float | None = Field(default=None, description="Limit price (required for LIMIT/IOC/FOK)")
    quantity: int = Field(..., gt=0, description="Number of shares (must be > 0)")

    @model_validator(mode="after")
    def validate_price_for_order_type(self):
        """
        Ensure price rules are followed:
        - LIMIT/IOC/FOK: price is required and must be > 0
        - MARKET: price must be None (we pick the best available)
        """
        if self.order_type == OrderTypeEnum.MARKET:
            if self.price is not None:
                raise ValueError("MARKET orders must not specify a price — they execute at best available")
        else:
            # LIMIT, IOC, FOK all require a price
            if self.price is None:
                raise ValueError(f"{self.order_type.value} orders require a price")
            if self.price <= 0:
                raise ValueError(f"Price must be > 0, got {self.price}")
        return self

    model_config = {"json_schema_extra": {
        "examples": [
            {
                "symbol": "AAPL",
                "side": "BUY",
                "order_type": "LIMIT",
                "price": 150.00,
                "quantity": 100,
            }
        ]
    }}


class ModifyOrderRequest(BaseModel):
    """
    Request body for PATCH /orders/{order_id}.
    At least one of new_price or new_quantity must be provided.
    """
    new_price: float | None = Field(default=None, gt=0, description="New limit price")
    new_quantity: int | None = Field(default=None, gt=0, description="New quantity")

    @model_validator(mode="after")
    def at_least_one_field(self):
        if self.new_price is None and self.new_quantity is None:
            raise ValueError("Must provide at least one of new_price or new_quantity")
        return self


# ══════════════════════════════════════════════════════════
#  RESPONSE MODELS — what we send back to the client
# ══════════════════════════════════════════════════════════

class TradeResponse(BaseModel):
    """A single executed trade."""
    trade_id: int
    symbol: str
    price: float
    quantity: int
    buy_order_id: int
    sell_order_id: int
    timestamp: datetime


class OrderResponse(BaseModel):
    """Response after submitting, modifying, or querying an order."""
    order_id: int
    symbol: str
    side: str
    order_type: str
    price: float | None
    quantity: int
    remaining_quantity: int
    status: str
    timestamp: datetime
    trades: list[TradeResponse] = Field(default_factory=list)


class PriceLevelResponse(BaseModel):
    """A single price level in the order book."""
    price: float
    volume: int
    order_count: int


class OrderBookResponse(BaseModel):
    """Current state of the order book for a symbol."""
    symbol: str
    bids: list[PriceLevelResponse]
    asks: list[PriceLevelResponse]
    best_bid: float | None = None
    best_ask: float | None = None
    spread: float | None = None
    timestamp: datetime


class AnalyticsResponse(BaseModel):
    """Generic analytics response — flexible data field."""
    symbol: str | None = None
    metric: str
    data: list[dict]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    version: str = "1.0.0"
    active_symbols: int = 0
    total_trades: int = 0
