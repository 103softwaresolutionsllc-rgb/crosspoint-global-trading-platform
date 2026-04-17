from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class Venue(str, Enum):
    BROKER_GENERIC = "broker"
    INTERACTIVE_BROKERS = "interactive_brokers"
    CRYPTO_CEX = "crypto_cex"


class AssetClass(str, Enum):
    EQUITY = "equity"
    FX = "fx"
    CRYPTO = "crypto"
    FUTURES = "futures"
    OPTION = "option"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class InstrumentId:
    symbol: str
    venue: Venue
    asset_class: AssetClass
    quote_currency: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Instrument:
    id: InstrumentId
    description: str = ""


@dataclass
class Money:
    amount: float
    currency: str

    def __add__(self, other: Money) -> Money:
        if self.currency != other.currency:
            raise ValueError("Currency mismatch for Money add")
        return Money(amount=self.amount + other.amount, currency=self.currency)


@dataclass
class AccountRef:
    account_id: str
    venue: Venue


@dataclass
class TradeIntent:
    """Strategy output: what we want to do before risk and sizing."""

    instrument: InstrumentId
    side: OrderSide
    quantity: float
    order_type: OrderType = OrderType.MARKET
    limit_price: float | None = None
    rationale: str = ""
    strategy_name: str = "default"
    intent_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")


@dataclass
class Order:
    venue: Venue
    account_id: str
    instrument: InstrumentId
    side: OrderSide
    order_type: OrderType
    quantity: float
    client_order_id: str = field(default_factory=lambda: str(uuid4()))
    limit_price: float | None = None
    status: OrderStatus = OrderStatus.PENDING
    broker_order_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Fill:
    client_order_id: str
    venue: Venue
    instrument: InstrumentId
    side: OrderSide
    quantity: float
    price: float
    fill_id: str = field(default_factory=lambda: str(uuid4()))
    fee: Money | None = None
    filled_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Position:
    account_id: str
    venue: Venue
    instrument: InstrumentId
    quantity: float
    avg_price: float | None = None
    as_of: datetime = field(default_factory=lambda: datetime.now(UTC))
