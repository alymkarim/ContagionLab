"""Tests for the composite fragility index."""

import numpy as np
import pandas as pd
import pytest

from app.services.fragility import (
    compute_fragility_index,
    get_fragility_summary,
)


def _fake_returns(n=200, seed=42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=n)
    factor = rng.standard_normal(n)
    data = {
        "SPY": factor + rng.standard_normal(n) * 0.3,
        "QQQ": factor + rng.standard_normal(n) * 0.3,
        "TLT": -factor * 0.5 + rng.standard_normal(n) * 0.3,
        "GLD": rng.standard_normal(n) * 0.2,
    }
    return pd.DataFrame(data, index=dates)


def test_fragility_index_returns_dataframe():
    """compute_fragility_index returns a DataFrame with expected columns."""
    returns = _fake_returns()
    result = compute_fragility_index(returns, window=60)
    assert isinstance(result, pd.DataFrame)
    assert "fragility" in result.columns
    assert "density" in result.columns
    assert "clustering" in result.columns
    assert "volatility" in result.columns


def test_fragility_index_values_in_range():
    """Fragility scores should be between 0 and 1."""
    returns = _fake_returns()
    result = compute_fragility_index(returns, window=60)
    assert (result["fragility"] >= 0).all()
    assert (result["fragility"] <= 1).all()


def test_fragility_index_density_in_range():
    """Density component should be between 0 and 1."""
    returns = _fake_returns()
    result = compute_fragility_index(returns, window=60)
    assert (result["density"] >= 0).all()
    assert (result["density"] <= 1).all()


def test_fragility_index_length():
    """Output length should be len(returns) - window."""
    returns = _fake_returns(n=200)
    result = compute_fragility_index(returns, window=60)
    assert len(result) == 140  # 200 - 60


def test_fragility_summary_returns_expected_keys():
    """get_fragility_summary returns summary with expected fields."""
    returns = _fake_returns()
    fragility_df = compute_fragility_index(returns, window=60)
    summary = get_fragility_summary(fragility_df)
    assert "current_fragility" in summary
    assert "mean_fragility" in summary
    assert "regime" in summary
    assert "trend" in summary
    assert summary["regime"] in ("resilient", "stressed", "normal")
    assert summary["trend"] in ("increasing", "decreasing", "stable", "unknown")


def test_fragility_summary_regime_classification():
    """Regime should be one of the three categories."""
    returns = _fake_returns()
    fragility_df = compute_fragility_index(returns, window=60)
    summary = get_fragility_summary(fragility_df)
    assert summary["regime"] in ("resilient", "stressed", "normal")


def test_fragility_with_different_methods():
    """Fragility works with different network methods."""
    returns = _fake_returns()
    for method in ("pearson", "spearman"):
        result = compute_fragility_index(returns, window=60, method=method)
        assert "fragility" in result.columns
        assert len(result) > 0
