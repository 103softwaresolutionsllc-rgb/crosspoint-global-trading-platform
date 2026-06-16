"""
Peer-to-peer agent debate matrix — adversarial cross-review before consensus.

Agents review each other's top picks and append counter-arguments to risk_factors,
reducing systemic bias from isolated fundamental models.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Sequence

from fincept_terminal.agents.base import AgentResult, Recommendation

# Directed debate pairs: reviewer → subject agent name
DEBATE_PAIRS: list[tuple[str, str]] = [
    ("Peter Lynch", "Benjamin Graham"),
    ("Warren Buffett", "Ian Dunlap"),
    ("Benjamin Graham", "Peter Lynch"),
    ("Ian Dunlap", "Warren Buffett"),
]

_REC_SCORES: dict[Recommendation, float] = {
    Recommendation.STRONG_BUY: 2.0,
    Recommendation.BUY: 1.0,
    Recommendation.HOLD: 0.0,
    Recommendation.SELL: -1.0,
    Recommendation.STRONG_SELL: -2.0,
}


@dataclass
class DebateRound:
    reviewer: str
    subject: str
    ticker: str
    counter_argument: str


@dataclass
class DebateResult:
    ticker: str
    results: list[AgentResult]
    rounds: list[DebateRound] = field(default_factory=list)


def _agent_by_name(results: Sequence[AgentResult], name: str) -> AgentResult | None:
    for r in results:
        if r.agent_name == name:
            return r
    return None


def _build_counter_argument(reviewer: AgentResult, subject: AgentResult) -> str | None:
    """Rule-based adversarial review — no extra LLM call required."""
    subj_score = _REC_SCORES.get(subject.recommendation, 0.0) * subject.confidence
    rev_score = _REC_SCORES.get(reviewer.recommendation, 0.0) * reviewer.confidence

    if subj_score <= 0 or rev_score >= subj_score:
        return None

    margin = subject.key_metrics.get("margin_of_safety")
    peg = subject.key_metrics.get("peg_ratio")
    moat = subject.key_metrics.get("moat_score")
    parts: list[str] = []

    if reviewer.agent_name == "Peter Lynch" and margin is not None and margin > 0.2:
        parts.append(
            f"Lynch challenges Graham's deep-value framing: {margin:.0%} margin of safety "
            f"may signal a value trap without earnings growth."
        )
    elif reviewer.agent_name == "Benjamin Graham" and peg is not None and peg > 1.5:
        parts.append(
            f"Graham flags Lynch's GARP thesis: PEG {peg:.1f} exceeds defensive thresholds."
        )
    elif reviewer.agent_name == "Warren Buffett" and moat is not None and moat < 0.5:
        parts.append(
            f"Buffett questions Dunlap turnaround quality: moat score {moat:.2f} below durable-compounder bar."
        )
    elif reviewer.agent_name == "Ian Dunlap":
        if subject.confidence > 0.75 and margin is not None and margin < 0.1:
            parts.append(
                "Dunlap warns Buffett-style quality bias may ignore near-term operational catalysts."
            )
    else:
        parts.append(
            f"{reviewer.agent_name} dissent: {reviewer.recommendation.value} "
            f"(conf {reviewer.confidence:.2f}) vs {subject.agent_name} "
            f"{subject.recommendation.value} (conf {subject.confidence:.2f})."
        )

    return " ".join(parts) if parts else None


def run_debate_matrix(results: Sequence[AgentResult], ticker: str) -> DebateResult:
    """
    Cross-review agent results in-place: append peer counter-arguments to risk_factors
    and lightly dampen confidence when a strong dissent exists.
    """
    updated = list(results)
    rounds: list[DebateRound] = []

    for reviewer_name, subject_name in DEBATE_PAIRS:
        reviewer = _agent_by_name(updated, reviewer_name)
        subject = _agent_by_name(updated, subject_name)
        if not reviewer or not subject:
            continue

        counter = _build_counter_argument(reviewer, subject)
        if not counter:
            continue

        rounds.append(DebateRound(reviewer_name, subject_name, ticker, counter))
        new_risks = list(subject.risk_factors) + [f"[Debate · {reviewer_name}] {counter}"]
        dampened = max(0.0, subject.confidence - 0.05)
        idx = next(i for i, r in enumerate(updated) if r.agent_name == subject_name)
        add = dict(subject.additional_data or {})
        add["debate_notes"] = add.get("debate_notes", []) + [counter]
        updated[idx] = replace(subject, risk_factors=new_risks, confidence=dampened, additional_data=add)

    return DebateResult(ticker=ticker, results=updated, rounds=rounds)
