"""Tests for network analysis: centrality, communities, systemic importance."""

import networkx as nx
import numpy as np
import pytest

from app.services.analysis import (
    compute_centrality,
    compute_systemic_importance,
    detect_communities,
)


def _make_test_graph() -> nx.Graph:
    """Create a hub-and-spoke graph for testing centrality metrics.

    Topology: HUB connects to A, B, C, D (degree 4).
    There is also an edge A-B so A has degree 2.
    This ensures HUB has the highest degree and betweenness centrality.

    Returns
    -------
    nx.Graph
        Undirected weighted graph with 5 nodes.
    """
    G = nx.Graph()
    G.add_edges_from(
        [
            ("HUB", "A", {"weight": 0.9}),
            ("HUB", "B", {"weight": 0.8}),
            ("HUB", "C", {"weight": 0.7}),
            ("HUB", "D", {"weight": 0.6}),
            ("A", "B", {"weight": 0.5}),
        ]
    )
    return G


# --- Centrality tests ---


def test_centrality_returns_dict():
    """compute_centrality should return a dict with centrality metrics per node."""
    G = _make_test_graph()
    result = compute_centrality(G)

    assert isinstance(result, dict)
    assert "HUB" in result
    hub = result["HUB"]
    assert "degree" in hub
    assert "betweenness" in hub
    assert "eigenvector" in hub
    assert "pagerank" in hub


def test_hub_has_highest_centrality():
    """HUB node should have the highest degree centrality."""
    G = _make_test_graph()
    result = compute_centrality(G)

    assert result["HUB"]["degree"] > result["A"]["degree"]


# --- Community tests ---


def test_communities_returns_list():
    """detect_communities should return a dict with num_communities and assignment."""
    G = _make_test_graph()
    result = detect_communities(G)

    assert isinstance(result, dict)
    assert "num_communities" in result
    assert "assignment" in result
    assert isinstance(result["assignment"], dict)
    assert result["num_communities"] >= 1


# --- Systemic importance tests ---


def test_systemic_importance_returns_dict():
    """compute_systemic_importance should return score and percentile per node."""
    G = _make_test_graph()
    result = compute_systemic_importance(G)

    assert isinstance(result, dict)
    assert "HUB" in result
    hub = result["HUB"]
    assert "score" in hub
    assert "percentile" in hub
    assert 0.0 <= hub["percentile"] <= 100.0
