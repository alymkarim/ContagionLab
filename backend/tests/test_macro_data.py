"""Tests for macro data integration."""

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from app.services.macro_data import (
    MACRO_TICKERS,
    fetch_macro_data,
    get_macro_tickers,
    get_macro_summary,
    merge_with_equity,
)


def test_macro_tickers_defined():
    """All expected macro tickers should be defined."""
    assert "VIX" in MACRO_TICKERS
    assert "DGS10" in MACRO_TICKERS
    assert "DXY" in MACRO_TICKERS
    assert "GOLD" in MACRO_TICKERS
    assert "OIL" in MACRO_TICKERS


def test_macro_tickers_have_required_fields():
    """Each macro ticker should have ticker, name, description, category."""
    for key, info in MACRO_TICKERS.items():
        assert "ticker" in info, f"{key} missing 'ticker'"
        assert "name" in info, f"{key} missing 'name'"
        assert "description" in info, f"{key} missing 'description'"
        assert "category" in info, f"{key} missing 'category'"


def test_get_macro_tickers():
    """get_macro_tickers should return the full dictionary."""
    result = get_macro_tickers()
    assert result == MACRO_TICKERS


@patch("app.services.macro_data.yf.download")
def test_fetch_macro_data(mock_yf):
    """fetch_macro_data should call yfinance and return a DataFrame."""
    rng = np.random.default_rng(42)
    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=100)
    # yfinance returns MultiIndex columns: (Close, ticker)
    mock_yf.return_value = pd.DataFrame(
        {
            ("Close", "^VIX"): 20 + rng.standard_normal(100),
            ("Close", "^TNX"): 4 + rng.standard_normal(100) * 0.1,
        },
        index=dates,
    )

    result = fetch_macro_data(period="1y", include=["VIX", "DGS10"])
    assert isinstance(result, pd.DataFrame)
    assert len(result) > 0


@patch("app.services.macro_data.yf.download")
def test_fetch_macro_data_empty_include(mock_yf):
    """fetch_macro_data with empty include list returns empty DataFrame."""
    result = fetch_macro_data(period="1y", include=[])
    assert result.empty


def test_merge_with_equity():
    """merge_with_equity should join dataframes on date index."""
    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=100)
    equity = pd.DataFrame({"SPY": np.linspace(100, 110, 100)}, index=dates)
    macro = pd.DataFrame({"VIX": np.linspace(20, 15, 100)}, index=dates)

    merged = merge_with_equity(equity, macro)
    assert "SPY" in merged.columns
    assert "VIX" in merged.columns
    assert len(merged) == 100


def test_merge_with_equity_empty_macro():
    """merge_with_equity with empty macro returns equity unchanged."""
    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=100)
    equity = pd.DataFrame({"SPY": np.linspace(100, 110, 100)}, index=dates)
    macro = pd.DataFrame()

    merged = merge_with_equity(equity, macro)
    assert list(merged.columns) == ["SPY"]
    assert len(merged) == 100


def test_get_macro_summary():
    """get_macro_summary should return summary for each column."""
    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=100)
    macro_prices = pd.DataFrame(
        {
            "VIX": 20 + np.random.randn(100) * 2,
            "DGS10": 4 + np.random.randn(100) * 0.1,
        },
        index=dates,
    )
    summary = get_macro_summary(macro_prices)
    assert "VIX" in summary
    assert "DGS10" in summary
    for key in ("VIX", "DGS10"):
        assert "current" in summary[key]
        assert "change_pct" in summary[key]
        assert "volatility" in summary[key]
        assert "name" in summary[key]


def test_get_macro_summary_empty():
    """get_macro_summary with empty DataFrame returns empty dict."""
    result = get_macro_summary(pd.DataFrame())
    assert result == {}
