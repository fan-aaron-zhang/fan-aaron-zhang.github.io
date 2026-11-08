"""Schema for a future one-click ChatGPT research handoff; no UI or auto-trading.

Separates source facts from unvalidated scores, prospective trading plans,
model limitations and portfolio facts. No API keys or transaction history.
"""
from __future__ import annotations
from typing import Any

SNAPSHOT_SCHEMA_VERSION = "RS0.1"


def make_research_snapshot(ticker: str, *, price_facts: dict | None = None,
                           financial_research: dict | None = None,
                           portfolio_facts: dict | None = None,
                           model_assessment: dict | None = None,
                           trading_plan: dict | None = None,
                           timestamps: dict | None = None) -> dict[str, Any]:
    """Build traceable structured data; no recommendation is fabricated.

    The exported trading plan must be supplied by a separately validated
    decision engine; it is NOT inferred from a quality score.
    """
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "ticker": ticker.strip().upper(),
        "timestamps": timestamps or {},
        "facts": {"market": price_facts or {}, "financial": financial_research or {},
                  "portfolio": portfolio_facts or {}},
        "model_assessment": model_assessment or {},
        "trading_plan": trading_plan or {},
        "review_instruction": (
            "Independently verify current news, financial filings, price timestamps and risk. "
            "Challenge the model conclusions; distinguish observed facts, estimates "
            "and conditional trade proposals. Do not infer any unreported transaction."
        ),
    }
