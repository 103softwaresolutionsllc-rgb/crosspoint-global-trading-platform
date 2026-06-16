"""Multi-asset instrument specs — equity, futures, options, FX, crypto."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from global_trading.core.domain import AssetClass, InstrumentId, Venue

_ASSET_CLASS_ALIASES: dict[str, AssetClass] = {
    "equity": AssetClass.EQUITY,
    "stock": AssetClass.EQUITY,
    "stocks": AssetClass.EQUITY,
    "fx": AssetClass.FX,
    "forex": AssetClass.FX,
    "future": AssetClass.FUTURES,
    "futures": AssetClass.FUTURES,
    "fut": AssetClass.FUTURES,
    "option": AssetClass.OPTION,
    "options": AssetClass.OPTION,
    "opt": AssetClass.OPTION,
    "crypto": AssetClass.CRYPTO,
}

# Default IBKR exchanges when not specified on the token or in .env
_DEFAULT_EXCHANGES: dict[AssetClass, str] = {
    AssetClass.EQUITY: "SMART",
    AssetClass.FUTURES: "GLOBEX",
    AssetClass.OPTION: "SMART",
    AssetClass.FX: "IDEALPRO",
}


@dataclass
class InstrumentSpec:
    """Parsed watchlist / CLI token (e.g. ES:future:202506, AAPL:option:20250620:200:C)."""

    symbol: str
    asset_class: AssetClass = AssetClass.EQUITY
    exchange: str = ""
    expiry: str = ""
    strike: float | None = None
    right: str = "C"
    currency: str = "USD"
    raw: str = ""
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def display(self) -> str:
        label = self.asset_class.value
        if self.asset_class == AssetClass.OPTION and self.strike is not None:
            return f"{self.symbol} {label} {self.expiry} {self.strike:g}{self.right}"
        if self.asset_class != AssetClass.EQUITY:
            return f"{self.symbol} ({label})"
        return self.symbol


def parse_asset_class(value: str | None = None) -> AssetClass:
    raw = (value or os.environ.get("GTP_ASSET_CLASS", "equity")).strip().lower()
    return _ASSET_CLASS_ALIASES.get(raw, AssetClass.EQUITY)


def asset_class_name(asset_class: AssetClass) -> str:
    for name, ac in _ASSET_CLASS_ALIASES.items():
        if ac == asset_class and name in ("equity", "future", "option", "fx", "crypto"):
            return name
    return asset_class.value


def contract_spec_from_env() -> dict[str, str]:
    return {
        "exchange": os.environ.get("GTP_CONTRACT_EXCHANGE", "").strip(),
        "expiry": os.environ.get("GTP_CONTRACT_EXPIRY", "").strip(),
        "strike": os.environ.get("GTP_OPTION_STRIKE", "").strip(),
        "right": (os.environ.get("GTP_OPTION_RIGHT", "C").strip().upper() or "C"),
        "currency": (os.environ.get("GTP_BASE_CURRENCY", "USD").strip() or "USD"),
    }


def parse_instrument_token(
    token: str,
    *,
    default_class: AssetClass | None = None,
) -> InstrumentSpec:
    """
    Parse watchlist tokens:
      AAPL                 -> equity
      ES:future            -> futures (expiry from .env)
      ES:future:202506     -> futures with expiry
      AAPL:option:20250620:200:C
      EURUSD:fx
    """
    raw = token.strip()
    if not raw:
        raise ValueError("empty instrument token")
    parts = [p.strip() for p in raw.split(":") if p.strip()]
    symbol = parts[0].upper()
    if len(parts) == 1:
        ac = default_class or parse_asset_class()
        return InstrumentSpec(symbol=symbol, asset_class=ac, raw=raw)

    kind = parts[1].lower()
    ac = _ASSET_CLASS_ALIASES.get(kind)
    if ac is None:
        ac = default_class or parse_asset_class()
        return InstrumentSpec(symbol=symbol, asset_class=ac, raw=raw)

    spec = InstrumentSpec(symbol=symbol, asset_class=ac, raw=raw)
    if ac == AssetClass.FUTURES:
        if len(parts) > 2:
            spec.expiry = parts[2]
    elif ac == AssetClass.OPTION:
        if len(parts) > 2:
            spec.expiry = parts[2]
        if len(parts) > 3:
            spec.strike = float(parts[3])
        if len(parts) > 4:
            spec.right = parts[4].upper()
    return spec


def apply_env_defaults(spec: InstrumentSpec) -> InstrumentSpec:
    """Fill missing contract fields from .env defaults."""
    env = contract_spec_from_env()
    if not spec.exchange:
        spec.exchange = env["exchange"] or _DEFAULT_EXCHANGES.get(spec.asset_class, "SMART")
    if not spec.currency:
        spec.currency = env["currency"]
    if spec.asset_class in (AssetClass.FUTURES, AssetClass.OPTION) and not spec.expiry:
        spec.expiry = env["expiry"]
    if spec.asset_class == AssetClass.OPTION:
        if spec.strike is None and env["strike"]:
            spec.strike = float(env["strike"])
        if not spec.right:
            spec.right = env["right"]
    spec.extra = {
        "exchange": spec.exchange,
        "expiry": spec.expiry,
        "strike": str(spec.strike) if spec.strike is not None else "",
        "right": spec.right,
        "currency": spec.currency,
    }
    return spec


def watchlist_from_env(key: str = "GTP_WATCHLIST") -> list[str]:
    raw = os.environ.get(key, "AAPL")
    return [t.strip() for t in raw.split(",") if t.strip()]


def watchlist_specs_from_env(key: str = "GTP_WATCHLIST") -> list[InstrumentSpec]:
    return [apply_env_defaults(parse_instrument_token(t)) for t in watchlist_from_env(key)]


def analysis_ticker(spec: InstrumentSpec) -> str:
    """Ticker symbol for Yahoo/agent consensus (underlying or continuous contract)."""
    if spec.asset_class == AssetClass.FUTURES:
        return f"{spec.symbol}=F"
    if spec.asset_class == AssetClass.FX:
        sym = spec.symbol.replace("/", "")
        if len(sym) == 6:
            return f"{sym}=X"
        return sym
    if spec.asset_class == AssetClass.CRYPTO:
        if "/" in spec.symbol:
            return spec.symbol.replace("/", "-")
        return f"{spec.symbol}-USD"
    return spec.symbol


def to_instrument_id(spec: InstrumentSpec) -> InstrumentId:
    extra = {k: v for k, v in spec.extra.items() if v}
    return InstrumentId(
        symbol=spec.symbol,
        venue=Venue.INTERACTIVE_BROKERS,
        asset_class=spec.asset_class,
        quote_currency=spec.currency,
        extra=extra,
    )


def apply_spec_to_env(spec: InstrumentSpec) -> None:
    """Set per-run env so IBKR connector and bridge read the active contract."""
    os.environ["GTP_ASSET_CLASS"] = asset_class_name(spec.asset_class)
    if spec.exchange:
        os.environ["GTP_CONTRACT_EXCHANGE"] = spec.exchange
    if spec.expiry:
        os.environ["GTP_CONTRACT_EXPIRY"] = spec.expiry
    if spec.strike is not None:
        os.environ["GTP_OPTION_STRIKE"] = str(spec.strike)
    if spec.right:
        os.environ["GTP_OPTION_RIGHT"] = spec.right
