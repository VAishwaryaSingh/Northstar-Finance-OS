import pandas as pd
import pytest
from transformations import build_rate_table, to_reporting_currency


@pytest.fixture
def rates():
    raw = pd.DataFrame([
        {"currency_from": "GBP", "currency_to": "USD", "rate_date": "2026-06-01", "rate": 1.27},
        {"currency_from": "GBP", "currency_to": "USD", "rate_date": "2026-06-08", "rate": 1.30},
    ])
    return build_rate_table(raw)


def test_same_currency_passes_through_unchanged(rates):
    amount, rate, method = to_reporting_currency(100.0, "GBP", "2026-06-01", rates)
    assert amount == 100.0
    assert rate == 1.0
    assert method == "same_currency"


def test_usd_converts_to_gbp_using_nearest_rate(rates):
    amount, rate, method = to_reporting_currency(127.0, "USD", "2026-06-01", rates)
    assert amount == 100.0  # 127 USD / 1.27 = 100 GBP
    assert rate == 1.27
    assert method == "divide_by_target_to_currency_rate"


def test_picks_the_nearest_rate_date_not_just_the_first(rates):
    # 2026-06-08 is closer to the second rate (1.30) than the first (1.27)
    amount, rate, method = to_reporting_currency(130.0, "USD", "2026-06-08", rates)
    assert rate == 1.30
    assert amount == 100.0


def test_no_rate_available_is_reported_not_silently_zeroed(rates):
    amount, rate, method = to_reporting_currency(50.0, "EUR", "2026-06-01", rates)
    assert amount is None
    assert rate is None
    assert method == "no_rate_available"
