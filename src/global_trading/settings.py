from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _b(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _i(name: str, default: int) -> int:
    v = os.environ.get(name)
    if v is None or v == "":
        return default
    return int(v)


def _f(name: str, default: float) -> float:
    v = os.environ.get(name)
    if v is None or v == "":
        return default
    return float(v)


def _s(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_dotenv(path: str | None = None) -> None:
    """Load repo-root .env into os.environ (first value wins per key)."""
    candidates = []
    if path:
        candidates.append(Path(path))
    else:
        candidates.append(_repo_root() / ".env")
        candidates.append(Path.cwd() / ".env")
    env_file = next((p for p in candidates if p.is_file()), None)
    if env_file is None:
        return
    with open(env_file, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            os.environ.setdefault(key, val)


@dataclass
class Settings:
    jurisdictions: str = "US"
    paper_first: bool = True
    rollout_mode: str = "paper_then_live"
    kill_switch: bool = False
    max_daily_loss_base: float = 10_000.0
    base_currency: str = "USD"
    ibkr_host: str = "127.0.0.1"
    ibkr_port: int = 7497
    ibkr_client_id: int = 1
    ibkr_use_stub: bool = True
    crypto_exchange: str = "binance"
    crypto_api_key: str = ""
    crypto_api_secret: str = ""
    crypto_sandbox: bool = True
    log_format: str = "json"
    audit_db_path: str = "var/audit.sqlite3"
    asset_class: str = "equity"
    contract_exchange: str = ""
    contract_expiry: str = ""
    option_strike: str = ""
    option_right: str = "C"


def load_settings() -> Settings:
    _load_dotenv()
    lf = _s("GTP_LOG_FORMAT", "json").lower()
    if lf not in ("json", "console"):
        lf = "json"
    return Settings(
        jurisdictions=_s("GTP_JURISDICTIONS", "US"),
        paper_first=_b("GTP_PAPER_FIRST", True),
        rollout_mode=_s("GTP_ROLLOUT_MODE", "paper_then_live"),
        kill_switch=_b("GTP_KILL_SWITCH", False),
        max_daily_loss_base=_f("GTP_MAX_DAILY_LOSS_BASE", 10_000.0),
        base_currency=_s("GTP_BASE_CURRENCY", "USD"),
        ibkr_host=_s("GTP_IBKR_HOST", "127.0.0.1"),
        ibkr_port=_i("GTP_IBKR_PORT", 7497),
        ibkr_client_id=_i("GTP_IBKR_CLIENT_ID", 1),
        ibkr_use_stub=_b("GTP_IBKR_USE_STUB", True),
        crypto_exchange=_s("GTP_CRYPTO_EXCHANGE", "binance"),
        crypto_api_key=_s("GTP_CRYPTO_API_KEY", ""),
        crypto_api_secret=_s("GTP_CRYPTO_API_SECRET", ""),
        crypto_sandbox=_b("GTP_CRYPTO_SANDBOX", True),
        log_format=lf,
        audit_db_path=_s("GTP_AUDIT_DB_PATH", "var/audit.sqlite3"),
        asset_class=_s("GTP_ASSET_CLASS", "equity"),
        contract_exchange=_s("GTP_CONTRACT_EXCHANGE", ""),
        contract_expiry=_s("GTP_CONTRACT_EXPIRY", ""),
        option_strike=_s("GTP_OPTION_STRIKE", ""),
        option_right=_s("GTP_OPTION_RIGHT", "C"),
    )
