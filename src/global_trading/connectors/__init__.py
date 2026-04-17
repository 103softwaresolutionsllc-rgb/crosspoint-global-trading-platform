from global_trading.connectors.base import BrokerConnector
from global_trading.connectors.fake import FakeConnector
from global_trading.connectors.ibkr import InteractiveBrokersConnector

__all__ = [
    "BrokerConnector",
    "FakeConnector",
    "InteractiveBrokersConnector",
]


def __getattr__(name: str):  # PEP 562: optional ccxt extra
    if name == "CCXTCryptoConnector":
        from global_trading.connectors.crypto_ccxt import CCXTCryptoConnector

        return CCXTCryptoConnector
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
