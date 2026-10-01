"""Tests for network construction methods."""

import networkx as nx
import numpy as np
import pandas as pd
import pytest

from app.services.network_builder import (
    build_pearson_network,
    build_spearman_network,
    build_partial_correlation_network,
    build_graphical_lasso_network,
    build_granger_causality_network,
    correlation_to_network,
)


def _make_test_returns(n_assets: int = 10, n_obs: int = 200) -> pd.DataFrame:
    """Generate synthetic correlated returns via 3 latent factors.

    The idea: real asset returns are driven by a handful of common
    risk factors (market, sector, etc).  We simulate this by creating
    3 latent factor returns and loading each asset onto them with
    random weights, then adding idiosyncratic noise.  This produces
    a correlation matrix with a few strong eigenvalues and many weak
    ones — similar to what you see in real financial data.

    Returns
    -------
    pd.DataFrame
        (n_obs, n_assets) DataFrame of synthetic daily returns,
        with columns labelled A, B, C, ...
    """
    rng = np.random.default_rng(42)
    # 3 latent factors, each n_obs observations
    factors = rng.standard_normal((n_obs, 3))
    # Random loadings: each asset loads onto the 3 factors differently
    loadings = rng.standard_normal((n_assets, 3))
    # Returns = factor contributions + idiosyncratic noise
    noise = rng.standard_normal((n_obs, n_assets)) * 0.3
    returns = factors @ loadings.T + noise
    tickers = [chr(65 + i) for i in range(n_assets)]  # A, B, C, ...
    return pd.DataFrame(returns, columns=tickers)


# --- Tests for each method producing a network graph ---


def test_pearson_produces_network():
    """Pearson correlation network should be a graph with correct node count."""
    returns = _make_test_returns()
    G = build_pearson_network(returns)
    assert isinstance(G, nx.Graph)
    assert len(G.nodes) == 10
    assert len(G.edges) > 0


def test_spearman_produces_network():
    """Spearman rank-correlation network should be a graph with correct node count."""
    returns = _make_test_returns()
    G = build_spearman_network(returns)
    assert isinstance(G, nx.Graph)
    assert len(G.nodes) == 10
    assert len(G.edges) > 0


def test_partial_correlation_produces_network():
    """Partial correlation network should be a graph with correct node count."""
    returns = _make_test_returns()
    G = build_partial_correlation_network(returns)
    assert isinstance(G, nx.Graph)
    assert len(G.nodes) == 10
    assert len(G.edges) > 0


def test_graphical_lasso_produces_network():
    """Graphical Lasso network should be a graph with correct node count."""
    returns = _make_test_returns()
    G = build_graphical_lasso_network(returns)
    assert isinstance(G, nx.Graph)
    assert len(G.nodes) == 10
    assert len(G.edges) > 0


def test_granger_produces_directed_network():
    """Granger causality network should be a directed graph."""
    returns = _make_test_returns()
    G = build_granger_causality_network(returns, max_lag=2, significance=0.05)
    assert isinstance(G, nx.DiGraph)
    assert len(G.nodes) == 10


def test_correlation_to_network_top_k():
    """With k=2, no node should have more than 2 edges."""
    rng = np.random.default_rng(99)
    n = 10
    # Random symmetric correlation matrix
    A = rng.standard_normal((n, n))
    corr = (A + A.T) / 2
    np.fill_diagonal(corr, 1.0)
    corr = np.clip(corr, -1, 1)

    tickers = [chr(65 + i) for i in range(n)]
    G = correlation_to_network(corr, tickers, mode="top_k", k=2)

    for node in G.nodes:
        assert G.degree(node) <= 2, (
            f"Node {node} has degree {G.degree(node)}, expected at most 2"
        )


# --- Bug-fix regression tests: singular covariance, NaN corr, shared primitive ---

def test_partial_correlation_singular_covariance_no_crash():
    """Collinear assets (singular covariance) must not 500; pinv fallback applies."""
    rng = np.random.default_rng(7)
    x = rng.standard_normal(5)
    # 5 identical columns -> perfectly singular covariance
    ret = pd.DataFrame({c: x for c in "ABCDE"})
    G = build_partial_correlation_network(ret, mode="threshold", threshold=0.0)
    assert G.number_of_nodes() == 5
    # Perfectly collinear -> complete graph on 5 nodes
    assert G.number_of_edges() == 10


def test_partial_correlation_n_ge_t_singular():
    """N >= T makes covariance singular; must build rather than raise LinAlgError."""
    rng = np.random.default_rng(3)
    ret = pd.DataFrame(rng.standard_normal((3, 5)), columns=list("ABCDE"))
    G = build_partial_correlation_network(ret, mode="top_k", k=2)
    assert G.number_of_nodes() == 5


def test_correlation_to_network_drops_nan():
    """Zero-variance column yields NaN corr; it must not become an edge."""
    rng = np.random.default_rng(1)
    ret = pd.DataFrame({
        "A": rng.standard_normal(20),
        "B": np.ones(20),          # zero variance -> NaN pearson corr
        "C": rng.standard_normal(20),
    })
    corr = np.corrcoef(ret.values, rowvar=False)
    assert np.isnan(corr).any()  # the bug precondition
    G = build_pearson_network(ret, mode="threshold", threshold=0.0)
    # B must be isolated (finite corr with it would be NaN -> no edge)
    assert G.degree("B") == 0
    assert "A" in G and "C" in G


def test_compute_correlation_matrix_shares_builders():
    """compute_correlation_matrix is the single source the builders use."""
    returns = _make_test_returns(n_assets=6, n_obs=120)
    from app.services.network_builder import compute_correlation_matrix
    corr = compute_correlation_matrix(returns, "pearson")
    assert corr.shape == (6, 6)
    G = build_pearson_network(returns)
    # Every edge weight should equal |corr| of that pair
    for u, v, d in G.edges(data=True):
        i, j = list(returns.columns).index(u), list(returns.columns).index(v)
        assert d["weight"] == pytest.approx(abs(corr[i, j]), abs=1e-9)


def test_compute_correlation_matrix_supports_all_methods():
    from app.services.network_builder import compute_correlation_matrix
    returns = _make_test_returns(n_assets=5, n_obs=100)
    for method in ("pearson", "spearman", "partial_correlation", "graphical_lasso"):
        corr = compute_correlation_matrix(returns, method)
        assert corr.shape == (5, 5)
        assert np.allclose(np.diag(corr), 1.0)


def test_compute_correlation_matrix_invalid_method():
    from app.services.network_builder import compute_correlation_matrix
    returns = _make_test_returns(n_assets=3)
    with pytest.raises(ValueError):
        compute_correlation_matrix(returns, "bogus")
