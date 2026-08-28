"""Integration tests for the full API pipeline.

These tests exercise the real HTTP endpoints end-to-end: the request
payloads go through Pydantic validation, the routers, the services,
and back as JSON.  We mock yfinance so the tests don't hit the
network, but everything else is live.
"""

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _fake_prices(tickers, period="1y", use_cache=True):
    """Return synthetic adjusted-close prices for any ticker set.

    We generate 252 trading days (~1 year) of prices driven by 3
    latent factors, the same approach used in the unit tests.  This
    ensures the network builders receive data with realistic
    cross-correlations rather than pure noise.
    """
    rng = np.random.default_rng(42)
    n_obs = 252
    n_assets = len(tickers)
    factors = rng.standard_normal((n_obs, 3))
    loadings = rng.standard_normal((n_assets, 3))
    noise = rng.standard_normal((n_obs, n_assets)) * 0.3
    returns = factors @ loadings.T + noise
    # Accumulate log returns into prices starting at 100
    prices_array = 100 * np.exp(np.vstack([np.zeros((1, n_assets)), returns]).cumsum(axis=0))
    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=n_obs + 1)
    return pd.DataFrame(prices_array, index=dates, columns=tickers)


# --- Network build integration tests ---


def test_build_network_pearson():
    """POST /api/networks/build with pearson method returns valid graph."""
    with patch("app.routers.networks.fetch_prices", side_effect=_fake_prices):
        resp = client.post("/api/networks/build", json={
            "assets": ["SPY", "QQQ", "TLT", "GLD"],
            "method": "pearson",
            "period": "1y",
            "top_k": 3,
        })
    assert resp.status_code == 200
    body = resp.json()
    assert body["method"] == "pearson"
    assert body["num_nodes"] == 4
    assert body["num_edges"] > 0
    # Verify graph structure
    graph = body["graph"]
    assert "nodes" in graph and "edges" in graph
    assert len(graph["nodes"]) == 4
    node_ids = {n["id"] for n in graph["nodes"]}
    assert node_ids == {"SPY", "QQQ", "TLT", "GLD"}
    # Verify metrics are present
    metrics = body["metrics"]
    assert "centrality" in metrics
    assert "communities" in metrics
    assert "systemic_importance" in metrics


def test_build_network_with_rmt():
    """POST /api/networks/build with use_rmt=true applies RMT filtering."""
    with patch("app.routers.networks.fetch_prices", side_effect=_fake_prices):
        resp = client.post("/api/networks/build", json={
            "assets": ["SPY", "QQQ", "TLT", "GLD"],
            "method": "pearson",
            "period": "1y",
            "top_k": 3,
            "use_rmt": True,
        })
    assert resp.status_code == 200
    body = resp.json()
    assert body["method"] == "pearson"
    assert body["num_nodes"] == 4


def test_build_network_invalid_method():
    """POST /api/networks/build with unknown method returns 400."""
    with patch("app.routers.networks.fetch_prices", side_effect=_fake_prices):
        resp = client.post("/api/networks/build", json={
            "assets": ["SPY", "QQQ"],
            "method": "bogus_method",
        })
    assert resp.status_code == 400
    assert "Unknown method" in resp.json()["detail"]


def test_build_network_too_few_assets():
    """POST /api/networks/build with 1 asset fails Pydantic validation."""
    resp = client.post("/api/networks/build", json={
        "assets": ["SPY"],
        "method": "pearson",
    })
    assert resp.status_code == 422


def test_build_network_spearman():
    """POST /api/networks/build with spearman method works end-to-end."""
    with patch("app.routers.networks.fetch_prices", side_effect=_fake_prices):
        resp = client.post("/api/networks/build", json={
            "assets": ["SPY", "QQQ", "TLT", "GLD"],
            "method": "spearman",
        })
    assert resp.status_code == 200
    body = resp.json()
    assert body["method"] == "spearman"
    assert body["num_edges"] > 0


# --- Stress test integration tests ---


def test_stress_test_run():
    """POST /api/stress-test/run returns per-asset results."""
    with patch("app.routers.stress_test.fetch_prices", side_effect=_fake_prices):
        resp = client.post("/api/stress-test/run", json={
            "assets": ["SPY", "QQQ", "TLT", "GLD"],
            "method": "pearson",
            "period": "1y",
            "shock_asset": "SPY",
            "shock_magnitude": -0.2,
            "n_sims": 500,
        })
    assert resp.status_code == 200
    body = resp.json()
    assert body["shock_asset"] == "SPY"
    assert body["shock_magnitude"] == -0.2
    assert body["n_sims"] == 500
    assert body["method"] == "pearson"
    results = body["results"]
    # Shocked asset should appear in results
    assert "SPY" in results
    assert results["SPY"]["median"] == pytest.approx(-0.2, abs=0.01)
    # All 4 assets should have results
    assert len(results) == 4
    for ticker in ["SPY", "QQQ", "TLT", "GLD"]:
        assert "median" in results[ticker]
        assert "ci_95" in results[ticker]
        assert "prob_negative" in results[ticker]


def test_stress_test_unknown_asset():
    """POST /api/stress-test/run with non-existent shock asset returns 400."""
    with patch("app.routers.stress_test.fetch_prices", side_effect=_fake_prices):
        resp = client.post("/api/stress-test/run", json={
            "assets": ["SPY", "QQQ"],
            "method": "pearson",
            "shock_asset": "AAPL",
            "shock_magnitude": -0.1,
            "n_sims": 100,
        })
    assert resp.status_code == 400
    assert "not found" in resp.json()["detail"].lower()


# --- Health + assets integration ---


def test_health_and_assets():
    """Health and assets endpoints work alongside the main pipeline."""
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    assets = client.get("/api/assets")
    assert assets.status_code == 200
    universe = assets.json()["universe"]
    assert "tech" in universe
    assert "QQQ" in universe["tech"]
