"""Currency normalisation (Phase 9, PLAN.md §21).

Converts every amount into one reporting currency (GBP) using the rate
closest to the transaction date in fx_rates -- the "defined, auditable
rate source" R08 asks for, in place of today's ad hoc month-end Excel spot
rate (discovery-notes.md).
"""

from __future__ import annotations

from datetime import date

import pandas as pd

REPORTING_CURRENCY = "GBP"


def build_rate_table(fx_rates_df: pd.DataFrame) -> pd.DataFrame:
    df = fx_rates_df.copy()
    df["rate_date"] = pd.to_datetime(df["rate_date"])
    return df.sort_values("rate_date").reset_index(drop=True)


def _nearest_rate(rates_df: pd.DataFrame, currency_from: str, currency_to: str, as_of) -> float | None:
    subset = rates_df[(rates_df["currency_from"] == currency_from) & (rates_df["currency_to"] == currency_to)]
    if subset.empty:
        return None
    as_of_ts = pd.Timestamp(as_of)
    diffs = (subset["rate_date"] - as_of_ts).abs()
    return float(subset.loc[diffs.idxmin(), "rate"])


def to_reporting_currency(
    amount: float,
    currency: str,
    as_of: date,
    rates_df: pd.DataFrame,
    target: str = REPORTING_CURRENCY,
) -> tuple[float | None, float | None, str]:
    """Convert amount (in `currency`, dated `as_of`) into `target`.

    Returns (converted_amount, rate_used, method). method is
    'same_currency', 'divide_by_target_to_currency_rate',
    'multiply_by_currency_to_target_rate', or 'no_rate_available' (in which
    case converted_amount and rate_used are both None -- an exception, not
    a silent zero).
    """
    if currency == target:
        return amount, 1.0, "same_currency"

    # fx_rates stores GBP->USD (rate = USD per 1 GBP), so converting a
    # foreign amount back to the GBP reporting currency divides by that rate.
    rate = _nearest_rate(rates_df, target, currency, as_of)
    if rate is not None:
        return round(amount / rate, 2), rate, "divide_by_target_to_currency_rate"

    rate = _nearest_rate(rates_df, currency, target, as_of)
    if rate is not None:
        return round(amount * rate, 2), rate, "multiply_by_currency_to_target_rate"

    return None, None, "no_rate_available"
