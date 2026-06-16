"""Tests for multi-asset instrument parsing."""

from global_trading.core.domain import AssetClass
from global_trading.instruments import (
    analysis_ticker,
    apply_env_defaults,
    parse_instrument_token,
    to_instrument_id,
)


def test_equity_token():
    spec = parse_instrument_token("AAPL")
    assert spec.symbol == "AAPL"
    assert spec.asset_class == AssetClass.EQUITY


def test_future_token_with_expiry():
    spec = apply_env_defaults(parse_instrument_token("ES:future:202506"))
    assert spec.symbol == "ES"
    assert spec.asset_class == AssetClass.FUTURES
    assert spec.expiry == "202506"
    assert analysis_ticker(spec) == "ES=F"


def test_option_token():
    spec = parse_instrument_token("AAPL:option:20250620:200:C")
    assert spec.asset_class == AssetClass.OPTION
    assert spec.strike == 200.0
    assert spec.right == "C"
    assert analysis_ticker(spec) == "AAPL"


def test_fx_token():
    spec = parse_instrument_token("EURUSD:fx")
    assert spec.asset_class == AssetClass.FX
    assert analysis_ticker(spec) == "EURUSD=X"


def test_to_instrument_id_carries_extra():
    spec = apply_env_defaults(parse_instrument_token("ES:future:202506"))
    iid = to_instrument_id(spec)
    assert iid.asset_class == AssetClass.FUTURES
    assert iid.extra.get("expiry") == "202506"
