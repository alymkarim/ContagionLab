"""Tests for historical crisis replay analysis."""

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch

from app.services.crisis_replay import (
    build_phase_network,
    compute_log_returns,
    compute_network_stats,
    graph_to_json,
    CRISES,
)


def _fake_prices(tickers, n=200, seed=42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=n)
    factor = rng.standard_normal(n)
    data = {}
    for i, t in enumerate(tickers):
        load = rng.standard_normal()
        data[t] = 100 * np.exp(np.cumsum(factor * load + rng.standard_normal(n) * 0.3))
    return pd.DataFrame(data, index=dates)


def test_crises_defined():
    """All three crises should be defined."""
    assert "2008_gfc" in CRISES
    assert "2020_covid" in CRISES
    assert "2022_rates" in CRISES


def test_crisis_has_required_fields():
    """Each crisis should have name, pre/during/post periods, and description."""
    for cid, crisis in CRISES.items():
        assert "name" in crisis
        assert "pre" in crisis
        assert "during" in crisis
        assert "post" in crisis
        assert "description" in crisis


def test_compute_log_returns():
    """Log returns should have one fewer row than prices."""
    prices = _fake_prices(["SPY", "QQQ"])
    returns = compute_log_returns(prices)
    assert len(returns) == len(prices) - 1
    assert list(returns.columns) == ["SPY", "QQQ"]


def test_build_phase_network():
    """Building a network from returns should produce a valid graph."""
    prices = _fake_prices(["SPY", "QQQ", "TLT", "GLD"])
    returns = compute_log_returns(prices)
    G = build_phase_network(returns, method="pearson", top_k=3)
    assert G.number_of_nodes() == 4
    assert G.number_of_edges() > 0


def test_compute_network_stats():
    """Network stats should return expected keys."""
    prices = _fake_prices(["SPY", "QQQ", "TLT", "GLD"])
    returns = compute_log_returns(prices)
    G = build_phase_network(returns, method="pearson", top_k=3)
    stats = compute_network_stats(G)
    assert "density" in stats
    assert "clustering" in stats
    assert "avg_path_length" in stats
    assert "num_edges" in stats
    assert "num_nodes" in stats
    assert stats["density"] >= 0


def test_graph_to_json():
    """graph_to_json should produce valid JSON structure."""
    prices = _fake_prices(["SPY", "QQQ", "TLT"])
    returns = compute_log_returns(prices)
    G = build_phase_network(returns, method="pearson", top_k=2)
    result = graph_to_json(G)
    assert "nodes" in result
    assert "edges" in result
    assert len(result["nodes"]) == 3
    for edge in result["edges"]:
        assert "source" in edge
        assert "target" in edge
        assert "weight" in edge


@patch("app.services.crisis_replay.yf.download")
def test_list_crises_endpoint(mock_yf):
    """List crises should return valid structure via API."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/crisis/list")
    assert resp.status_code == 200
    body = resp.json()
    assert "crises" in body
    assert len(body["crises"]) == 3


@patch("app.services.crisis_replay.yf.download")
def test_crisis_analyze_invalid_id(mock_yf):
    """Analyzing an unknown crisis should return 400."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.post("/api/crisis/analyze", json={
        "assets": ["SPY", "QQQ"],
        "crisis_id": "bogus",
    })
    assert resp.status_code == 400
