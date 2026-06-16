from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from global_trading.core.domain import (
    AssetClass,
    InstrumentId,
    Money,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    Venue,
)
from global_trading.asyncio_compat import ensure_event_loop
from global_trading.connectors.fake import FakeConnector
from global_trading.instruments import contract_spec_from_env
from global_trading.observability.metrics import Metrics

if TYPE_CHECKING:
    from ib_insync import IB, Forex, Future, MarketOrder, Option, Stock  # noqa: F401

IB = None  # type: ignore[misc, assignment]
Stock = Forex = Future = Option = MarketOrder = None  # type: ignore[misc, assignment]
_ib_import_error: str | None = None


def _load_ib_insync() -> tuple[Any, ...]:
    """Lazy import — ib_insync/eventkit require an event loop on Python 3.10+."""
    global IB, Stock, Forex, Future, Option, MarketOrder, _ib_import_error
    if IB is not None:
        return IB, Stock, Forex, Future, Option, MarketOrder
    try:
        ensure_event_loop()
        from ib_insync import IB as _IB
        from ib_insync import Forex as _Forex
        from ib_insync import Future as _Future
        from ib_insync import MarketOrder as _MarketOrder
        from ib_insync import Option as _Option
        from ib_insync import Stock as _Stock

        IB, Stock, Forex, Future, Option, MarketOrder = (
            _IB,
            _Stock,
            _Forex,
            _Future,
            _Option,
            _MarketOrder,
        )
        _ib_import_error = None
        return IB, Stock, Forex, Future, Option, MarketOrder
    except ImportError as exc:
        _ib_import_error = str(exc)
        return None, None, None, None, None, None  # type: ignore[return-value]


def _sec_type_to_asset_class(sec_type: str) -> AssetClass:
    mapping = {
        "STK": AssetClass.EQUITY,
        "FUT": AssetClass.FUTURES,
        "OPT": AssetClass.OPTION,
        "CASH": AssetClass.FX,
    }
    return mapping.get((sec_type or "STK").upper(), AssetClass.EQUITY)


def _build_ib_contract(inst: InstrumentId) -> Any:
    _load_ib_insync()
    sym = inst.symbol
    spec = {**contract_spec_from_env(), **(inst.extra or {})}
    exchange = spec.get("exchange") or "SMART"
    currency = spec.get("currency") or "USD"

    if inst.asset_class == AssetClass.FX:
        if Forex is None:
            raise RuntimeError("ib_insync Forex unavailable")
        return Forex(sym.replace("/", ""))
    if inst.asset_class == AssetClass.FUTURES:
        if Future is None:
            raise RuntimeError("ib_insync Future unavailable")
        expiry = spec.get("expiry") or ""
        if not expiry:
            raise ValueError(
                f"Futures {sym} require expiry — use ES:future:202506 or GTP_CONTRACT_EXPIRY in .env"
            )
        return Future(sym, expiry, exchange)
    if inst.asset_class == AssetClass.OPTION:
        if Option is None:
            raise RuntimeError("ib_insync Option unavailable")
        expiry = spec.get("expiry") or ""
        strike = spec.get("strike") or ""
        right = (spec.get("right") or "C").upper()
        if not expiry or not strike:
            raise ValueError(
                f"Options {sym} require expiry/strike — use AAPL:option:YYYYMMDD:STRIKE:C or .env fields"
            )
        return Option(sym, expiry, float(strike), right, exchange)
    if Stock is None:
        raise RuntimeError("ib_insync Stock unavailable")
    return Stock(sym, exchange, currency)


class InteractiveBrokersConnector:
    """
    Interactive Brokers via ib_insync + TWS/IB Gateway.
    When ``use_stub`` is True or ``ib_insync`` is unavailable, uses in-memory simulation.
    """

    def __init__(
        self,
        *,
        account_id: str = "IBKR-PAPER",
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 1,
        use_stub: bool = True,
        metrics: Metrics | None = None,
    ) -> None:
        self.venue_name = "interactive_brokers"
        self.account_id = account_id
        self._host = host
        self._port = port
        self._client_id = client_id
        _load_ib_insync()
        self._use_stub = use_stub or IB is None
        self._metrics = metrics
        self._stub = FakeConnector(account_id=account_id, metrics=metrics)
        self._ib: Any = None

    def _ensure_ib(self) -> Any:
        if self._use_stub:
            return None
        _load_ib_insync()
        if IB is None:
            hint = _ib_import_error or "ib_insync not installed"
            raise RuntimeError(f"{hint}; pip install ib-insync")
        if self._ib is None:
            ensure_event_loop()
            self._ib = IB()
            self._ib.connect(self._host, self._port, clientId=self._client_id)
        return self._ib

    def place_order(self, order: Order) -> Order:
        if self._use_stub:
            o = replace(order, instrument=self._normalize_instrument(order.instrument))
            return self._stub.place_order(o)

        ib = self._ensure_ib()
        assert ib is not None
        contract = _build_ib_contract(order.instrument)
        ib.qualifyContracts(contract)
        action = "BUY" if order.side == OrderSide.BUY else "SELL"
        if order.order_type == OrderType.MARKET:
            if MarketOrder is None:
                raise RuntimeError("ib_insync MarketOrder unavailable")
            ib_order = MarketOrder(action, order.quantity)
        else:
            raise NotImplementedError("Limit orders require price wiring")
        trade = ib.placeOrder(contract, ib_order)
        broker_id = str(trade.order.orderId) if trade and trade.order else None
        now = datetime.now(UTC)
        out = replace(
            order,
            status=OrderStatus.SUBMITTED,
            broker_order_id=broker_id,
            updated_at=now,
        )
        if self._metrics:
            self._metrics.inc("ibkr_orders_submitted")
        return out

    def cancel_order(self, client_order_id: str) -> bool:
        if self._use_stub:
            return self._stub.cancel_order(client_order_id)
        # Minimal stub: real cancel would map client_order_id -> broker id
        return False

    def get_positions(self) -> list[Position]:
        if self._use_stub:
            return self._stub.get_positions()
        ib = self._ensure_ib()
        assert ib is not None
        result: list[Position] = []
        for p in ib.positions():
            c = p.contract
            sym = getattr(c, "symbol", "") or str(c)
            sec_type = getattr(c, "secType", "STK")
            iid = InstrumentId(
                symbol=sym,
                venue=Venue.INTERACTIVE_BROKERS,
                asset_class=_sec_type_to_asset_class(sec_type),
            )
            result.append(
                Position(
                    account_id=self.account_id,
                    venue=Venue.INTERACTIVE_BROKERS,
                    instrument=iid,
                    quantity=float(p.position),
                    avg_price=float(p.avgCost or 0) / abs(float(p.position)) if p.position else None,
                )
            )
        return result

    def get_balances(self) -> dict[str, Money]:
        if self._use_stub:
            return self._stub.get_balances()
        ib = self._ensure_ib()
        assert ib is not None
        out: dict[str, Money] = {}
        for v in ib.accountValues():
            if v.tag in ("TotalCashValue", "NetLiquidation", "BuyingPower") and v.currency:
                out[f"{v.tag}:{v.currency}"] = Money(amount=float(v.value), currency=v.currency)
        return out

    def disconnect(self) -> None:
        if self._ib is not None:
            self._ib.disconnect()
            self._ib = None

    @staticmethod
    def _normalize_instrument(i: InstrumentId) -> InstrumentId:
        if i.venue == Venue.INTERACTIVE_BROKERS:
            return i
        return replace(i, venue=Venue.INTERACTIVE_BROKERS)
