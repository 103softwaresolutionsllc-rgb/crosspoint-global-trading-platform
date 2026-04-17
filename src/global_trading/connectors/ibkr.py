from __future__ import annotations

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
from global_trading.connectors.fake import FakeConnector
from global_trading.observability.metrics import Metrics

if TYPE_CHECKING:
    pass

try:
    from ib_insync import IB, Forex, MarketOrder, Stock  # type: ignore[import-not-found]
except ImportError:
    IB = None  # type: ignore[misc, assignment]
    Stock = Forex = MarketOrder = None  # type: ignore[misc, assignment]


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
        self._use_stub = use_stub or IB is None
        self._metrics = metrics
        self._stub = FakeConnector(account_id=account_id, metrics=metrics)
        self._ib: Any = None

    def _ensure_ib(self) -> Any:
        if self._use_stub:
            return None
        if IB is None:
            raise RuntimeError("ib_insync not installed; pip install 'global-trading-platform[ibkr]'")
        if self._ib is None:
            self._ib = IB()
            self._ib.connect(self._host, self._port, clientId=self._client_id)
        return self._ib

    def place_order(self, order: Order) -> Order:
        if self._use_stub:
            o = replace(order, instrument=self._normalize_instrument(order.instrument))
            return self._stub.place_order(o)

        ib = self._ensure_ib()
        assert ib is not None
        inst = order.instrument
        sym = inst.symbol
        if inst.asset_class == AssetClass.FX:
            if Forex is None:
                raise RuntimeError("ib_insync Forex unavailable")
            contract = Forex(sym.replace("/", ""))
        else:
            if Stock is None:
                raise RuntimeError("ib_insync Stock unavailable")
            contract = Stock(sym, "SMART", "USD")
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
            sym = getattr(p.contract, "symbol", "") or str(p.contract)
            iid = InstrumentId(
                symbol=sym,
                venue=Venue.INTERACTIVE_BROKERS,
                asset_class=AssetClass.EQUITY,
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
            if v.tag == "TotalCashValue" and v.currency:
                out[v.currency] = Money(amount=float(v.value), currency=v.currency)
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
