from global_trading.backtest.engine import BacktestConfig, BacktestEngine


def test_buy_hold_backtest() -> None:
    engine = BacktestEngine(
        BacktestConfig(ticker="SPY", start="2023-01-01", end="2023-12-31", initial_capital=10_000)
    )
    result = engine.run(strategy="buy_hold")
    assert result.num_trades >= 1
    assert result.final_equity > 0
    assert -1.0 <= result.total_return <= 2.0
