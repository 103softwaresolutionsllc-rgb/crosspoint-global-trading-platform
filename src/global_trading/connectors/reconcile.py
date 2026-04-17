from __future__ import annotations

from dataclasses import dataclass

from global_trading.core.domain import Position, Venue


def _key(p: Position) -> str:
    i = p.instrument
    return f"{p.account_id}|{p.venue.value}|{i.symbol}|{i.asset_class.value}"


@dataclass
class PositionMismatch:
    key: str
    local_qty: float | None = None
    remote_qty: float | None = None
    message: str = ""


@dataclass
class ReconciliationReport:
    venue: Venue
    account_id: str
    ok: bool
    mismatches: list[PositionMismatch]


def reconcile_positions(
    *,
    account_id: str,
    venue: Venue,
    local: list[Position],
    remote: list[Position],
) -> ReconciliationReport:
    """Compare locally tracked positions to broker/exchange truth."""

    lm = {_key(p): p for p in local if p.account_id == account_id and p.venue == venue}
    rm = {_key(p): p for p in remote if p.account_id == account_id and p.venue == venue}
    mismatches: list[PositionMismatch] = []
    all_keys = set(lm) | set(rm)
    for k in sorted(all_keys):
        lp = lm.get(k)
        rp = rm.get(k)
        lq = lp.quantity if lp else None
        rq = rp.quantity if rp else None
        if lq is None or rq is None or abs(lq - rq) > 1e-6:
            mismatches.append(
                PositionMismatch(
                    key=k,
                    local_qty=lq,
                    remote_qty=rq,
                    message="quantity_mismatch_or_missing",
                )
            )
    return ReconciliationReport(
        venue=venue,
        account_id=account_id,
        ok=len(mismatches) == 0,
        mismatches=mismatches,
    )
