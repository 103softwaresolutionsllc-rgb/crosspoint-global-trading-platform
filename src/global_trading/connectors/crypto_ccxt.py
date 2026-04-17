from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

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
from global_trading.observability.metrics import Metrics


def _import_ccxt() -> Any:
    try:
        import ccxt  # type: ignore[import-untyped]
    except ImportError as e:
        raise RuntimeError(
            'ccxt is not installed; run: pip install "global-trading-platform[crypto]"'
        ) from e
    return ccxt


class CCXTCryptoConnector:
    """CEX connector via CCXT; wraps venue-specific details behind BrokerConnector."""

    def __init__(
        self,
        *,
        exchange_id: str,
        api_key: str = "",
        api_secret: str = "",
        sandbox: bool = True,
        account_id: str = "CRYPTO-1",
        metrics: Metrics | None = None,
    ) -> None:
        self.venue_name = f"crypto:{exchange_id}"
        self.account_id = account_id
        self._exchange_id = exchange_id
        self._metrics = metrics
        ccxt = _import_ccxt()
        klass = getattr(ccxt, exchange_id)
        self._ex = klass(
            {
                "apiKey": api_key,
                "secret": api_secret,
                "enableRateLimit": True,
            }
        )
        if sandbox and hasattr(self._ex, "set_sandbox_mode"):
            self._ex.set_sandbox_mode(True)

    def place_order(self, order: Order) -> Order:
        symbol = self._map_symbol(order.instrument.symbol)
        side = "buy" if order.side == OrderSide.BUY else "sell"
        amount = order.quantity
        now = datetime.now(UTC)
        if order.order_type == OrderType.MARKET:
            res = self._ex.create_order(symbol, "market", side, amount)
        elif order.order_type == OrderType.LIMIT:
            if order.limit_price is None:
                raise ValueError("limit_price required for limit order")
            res = self._ex.create_order(symbol, "limit", side, amount, order.limit_price)
        else:
            raise NotImplementedError(order.order_type)
        broker_id = str(res.get("id", ""))
        status = OrderStatus.FILLED if res.get("status") == "closed" else OrderStatus.SUBMITTED
        if self._metrics:
            self._metrics.inc("crypto_orders_submitted")
        return replace(
            order,
            status=status,
            broker_order_id=broker_id,
            updated_at=now,
            meta={**order.meta, "raw": res},
        )

    def cancel_order(self, client_order_id: str) -> bool:
        # Would need symbol + exchange-specific id; kept minimal
        _ = client_order_id
        return False

    def get_positions(self) -> list[Position]:
        """CCXT balance as synthetic positions in base units where applicable."""

        bal = self._ex.fetch_balance()
        out: list[Position] = []
        for cur, amounts in bal.get("total", {}).items():
            if not amounts:
                continue
            qty = float(amounts)
            if abs(qty) < 1e-12:
                continue
            iid = InstrumentId(
                symbol=f"{cur}/USDT",
                venue=Venue.CRYPTO_CEX,
                asset_class=AssetClass.CRYPTO,
                quote_currency="USDT",
            )
            out.append(
                Position(
                    account_id=self.account_id,
                    venue=Venue.CRYPTO_CEX,
                    instrument=iid,
                    quantity=qty,
                )
            )
        return out

    def get_balances(self) -> dict[str, Money]:
        bal = self._ex.fetch_balance()
        out: dict[str, Money] = {}
        for cur, amounts in bal.get("total", {}).items():
            amt = float(amounts or 0)
            if abs(amt) > 1e-12:
                out[cur] = Money(amount=amt, currency=cur)
        return out

    def _map_symbol(self, symbol: str) -> str:
        if "/" in symbol:
            return symbol
        if symbol.endswith("USDT"):
            return f"{symbol[:-4]}/USDT"
        return symbol
