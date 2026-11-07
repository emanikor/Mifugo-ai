"""
Outlier detection for newly submitted livestock prices.

Design principle: NEVER silently drop a price. Community agents' data is the
entire value of this system — a wrong flag is recoverable (an official can
review and override it), but a silently discarded real price is not. Every
decision here is stored with a human-readable reason on the row itself
(see PriceEntry.outlier_reason), so it can be audited later.

Method (stubbed, deliberately simple to start):
  - Compare the new price against recent valid prices for the SAME species
    + region (a camel price in Lodwar should only be judged against other
    camel prices in Lodwar, not against goat prices elsewhere).
  - Use a modified z-score (median + MAD) rather than mean/stdev, because
    a single wild outlier already in the data shouldn't drag the mean/stdev
    around and hide the next outlier (mean-based stats are not robust to
    outliers; median-based ones are).
  - Thresholds are deliberately conservative and configurable — this is a
    starting point for tuning against real Turkana market data, not a
    final answer.
"""
from dataclasses import dataclass

import numpy as np
from sqlalchemy.orm import Session

from app.models import PriceEntry

# TODO: tune these thresholds against real historical price data once
# collected. These are placeholder defaults, not empirically derived.
FLAG_THRESHOLD = 3.5      # modified z-score above this -> flagged for review
REJECT_THRESHOLD = 6.0    # modified z-score above this -> auto-rejected
MIN_SAMPLE_SIZE = 5       # below this many recent comparable prices, we
                          # don't have enough signal to judge -- mark valid
                          # but note that it's unverified


@dataclass
class OutlierResult:
    status: str        # 'valid' | 'flagged' | 'rejected'
    reason: str | None
    score: float | None


def _modified_z_scores(values: np.ndarray) -> np.ndarray:
    """Median Absolute Deviation based z-score — robust to existing outliers."""
    median = np.median(values)
    mad = np.median(np.abs(values - median))
    if mad == 0:
        # All values identical (or MAD degenerate) — fall back to a tiny
        # epsilon so we don't divide by zero; any deviation at all is then
        # meaningful.
        mad = 1e-9
    return 0.6745 * (values - median) / mad


def evaluate_new_price(
    db: Session,
    *,
    region_id: int,
    species_id: int,
    price_kes: int,
    lookback_days: int = 90,
) -> OutlierResult:
    """
    Decide whether a newly submitted price looks consistent with recent
    validated prices for the same species + region.

    TODO: this currently only looks at price magnitude. Future iterations
    should also weigh market_date recency (a 90-day-old price is a weaker
    comparison point than one from yesterday) and maybe seasonal patterns
    (livestock prices in Turkana fluctuate with drought/rain cycles).
    """
    recent_valid = (
        db.query(PriceEntry.price_kes)
        .filter(
            PriceEntry.region_id == region_id,
            PriceEntry.species_id == species_id,
            PriceEntry.outlier_status == "valid",
        )
        .order_by(PriceEntry.market_date.desc())
        .limit(200)
        .all()
    )

    values = np.array([row[0] for row in recent_valid], dtype=float)

    if values.size < MIN_SAMPLE_SIZE:
        return OutlierResult(
            status="valid",
            reason=(
                f"Only {values.size} comparable prices on record for this "
                "region/species — not enough history to statistically "
                "validate. Marked valid but treat with caution until more "
                "data accumulates."
            ),
            score=None,
        )

    # Score the *candidate* price against the existing distribution.
    all_values = np.append(values, price_kes)
    scores = _modified_z_scores(all_values)
    candidate_score = float(scores[-1])

    if abs(candidate_score) >= REJECT_THRESHOLD:
        return OutlierResult(
            status="rejected",
            reason=(
                f"Price {price_kes} KES is extremely inconsistent with "
                f"{values.size} recent comparable prices (modified z-score "
                f"{candidate_score:.2f}). Likely a data-entry error or "
                "misreported price — rejected pending manual review."
            ),
            score=candidate_score,
        )

    if abs(candidate_score) >= FLAG_THRESHOLD:
        return OutlierResult(
            status="flagged",
            reason=(
                f"Price {price_kes} KES deviates notably from "
                f"{values.size} recent comparable prices (modified z-score "
                f"{candidate_score:.2f}). Flagged for official review, not "
                "auto-rejected."
            ),
            score=candidate_score,
        )

    return OutlierResult(status="valid", reason=None, score=candidate_score)
