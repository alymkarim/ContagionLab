"""Tests for Monte Carlo stress testing simulation."""

import numpy as np
import networkx as nx
import pytest

from app.services.simulation import run_stress_test


def _make_test_network() -> nx.Graph:
    """Build a 3-node test network with known edge weights.

    Topology:
        NVDA ---0.8--- AMD
        NVDA ---0.5--- QQQ
        AMD  ---0.4--- QQQ

    Weights encode correlation strength: higher weight means a
    stronger transmission channel.  NVDA is the most connected hub.
    """
    G = nx.Graph()
    G.add_edge("NVDA", "AMD", weight=0.8)
    G.add_edge("NVDA", "QQQ", weight=0.5)
    G.add_edge("AMD", "QQQ", weight=0.4)
    return G


def test_stress_test_returns_results():
    """run_stress_test must return a dict keyed by every node in the graph."""
    G = _make_test_network()
    results = run_stress_test(G, shock_asset="NVDA", shock_magnitude=-1.0,
                              n_sims=1000, noise_std=0.01)

    for ticker in ("NVDA", "AMD", "QQQ"):
        assert ticker in results, f"Missing ticker {ticker} in results"
        assert "median" in results[ticker], f"Missing 'median' for {ticker}"
        assert "ci_95" in results[ticker], f"Missing 'ci_95' for {ticker}"
        assert "prob_negative" in results[ticker], f"Missing 'prob_negative' for {ticker}"
        assert len(results[ticker]["ci_95"]) == 2, f"ci_95 must have two elements for {ticker}"


def test_stress_test_shock_propagates_proportionally():
    """AMD (weight 0.8 to NVDA) must absorb more shock than QQQ (weight 0.5).

    When NVDA is shocked negatively, AMD's median response should be
    more negative than QQQ's because the stronger edge transmits
    more of the perturbation.  This is the linear-threshold assumption:
    the response of neighbor j is proportional to the edge weight w_ij.
    """
    G = _make_test_network()
    results = run_stress_test(G, shock_asset="NVDA", shock_magnitude=-1.0,
                              n_sims=5000, noise_std=0.01)

    amd_median = results["AMD"]["median"]
    qqq_median = results["QQQ"]["median"]

    assert amd_median < qqq_median, (
        f"Expected AMD median ({amd_median:.4f}) < QQQ median ({qqq_median:.4f}); "
        "stronger edge should transmit more of the negative shock"
    )


def test_stress_test_confidence_intervals():
    """The median must fall inside the 95 % confidence interval.

    By definition, the median is the 50th percentile.  A 95% CI spans
    the 2.5th to 97.5th percentiles, so the median must lie within it
    for every asset — barring extreme noise.  We use a moderate
    noise_std so the property holds robustly.
    """
    G = _make_test_network()
    results = run_stress_test(G, shock_asset="NVDA", shock_magnitude=-1.0,
                              n_sims=5000, noise_std=0.05)

    for ticker in ("NVDA", "AMD", "QQQ"):
        med = results[ticker]["median"]
        lo, hi = results[ticker]["ci_95"]
        assert lo <= med <= hi, (
            f"{ticker}: median {med:.4f} outside CI [{lo:.4f}, {hi:.4f}]"
        )
