"""Tests for tail dependence network construction."""

import numpy as np
import pandas as pd
import pytest

from app.services.tail_dependence import (
    build_tail_dependence_network,
    compute_tail_dependence,
    compare_tail_vs_pearson,
)


def _fake_returns(n=200, seed=42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=n)
    # Three correlated assets + one independent
    factor = rng.standard_normal(n)
    data = {
        "A": factor + rng.standard_normal(n) * 0.3,
        "B": factor + rng.standard_normal(n) * 0.3,
        "C": factor + rng.standard_normal(n) * 0.3,
        "D": rng.standard_normal(n),  # independent
    }
    return pd.DataFrame(data, index=dates)


def test_tail_dependence_matrix_diagonal():
    """Diagonal of tail dependence matrix should be 1.0."""
    returns = _fake_returns()
    tc = compute_tail_dependence(returns, quantile=0.05)
    for col in tc.columns:
        assert tc.loc[col, col] == pytest.approx(1.0, abs=1e-10)


def test_tail_dependence_matrix_shape():
    """Tail dependence matrix should be NxN."""
    returns = _fake_returns()
    tc = compute_tail_dependence(returns, quantile=0.05)
    assert tc.shape == (4, 4)


def test_tail_dependence_symmetric():
    """Tail dependence matrix should be symmetric."""
    returns = _fake_returns()
    tc = compute_tail_dependence(returns, quantile=0.05)
    for i in range(4):
        for j in range(4):
            assert tc.iloc[i, j] == pytest.approx(tc.iloc[j, i], abs=1e-10)


def test_tail_dependence_values_in_range():
    """All tail dependence coefficients should be between 0 and 1."""
    returns = _fake_returns()
    tc = compute_tail_dependence(returns, quantile=0.10)
    assert (tc >= 0).all().all()
    assert (tc <= 1).all().all()


def test_correlated_assets_have_higher_tail_dep():
    """Correlated assets (A, B, C) should have higher tail dependence than independent (D)."""
    returns = _fake_returns()
    tc = compute_tail_dependence(returns, quantile=0.10)
    # A and B are correlated via factor
    assert tc.loc["A", "B"] > tc.loc["A", "D"]


def test_build_tail_network_produces_edges():
    """Tail dependence network should produce edges for correlated assets."""
    returns = _fake_returns()
    G = build_tail_dependence_network(returns, quantile=0.05, mode="top_k", k=3)
    assert G.number_of_nodes() == 4
    assert G.number_of_edges() > 0


def test_build_tail_network_top_k():
    """Top k mode should limit edges per node."""
    returns = _fake_returns(n=300)
    G = build_tail_dependence_network(returns, quantile=0.05, mode="top_k", k=2)
    for node in G.nodes():
        assert G.degree(node) <= 4  # k=2 means up to 2 in + 2 out per node


def test_build_tail_network_threshold():
    """Threshold mode should only include edges above threshold."""
    returns = _fake_returns()
    G = build_tail_dependence_network(returns, quantile=0.05, mode="threshold", threshold=0.8)
    for _, _, data in G.edges(data=True):
        assert data["weight"] > 0.8


def test_compare_tail_vs_pearson():
    """compare_tail_vs_pearson should return expected keys."""
    returns = _fake_returns()
    result = compare_tail_vs_pearson(returns, quantile=0.05)
    assert "pearson_edges" in result
    assert "tail_edges" in result
    assert "shared_edges" in result
    assert "hidden_risk_edges" in result
    assert "interpretation" in result
    assert result["pearson_edges"] > 0
    assert result["tail_edges"] > 0
