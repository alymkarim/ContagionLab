"""
Tail dependence — measuring extreme co-movements.

Standard correlation (Pearson, Spearman) measures average co-movement.
But crises are about EXTREME co-movements — when markets crash, do they
crash together? That's what tail dependence measures.

We use copulas to estimate the probability that one asset falls into
its extreme lower tail given that another asset is also in its tail.

Physics analogy: standard correlation is like measuring the average
interaction between particles. Tail dependence is like measuring the
interaction specifically during high-energy collisions — the extreme
events that matter most for systemic risk.

Mathematical background:
    Lower tail dependence coefficient:
        λ_L = lim_{q→0} P(X₂ ≤ F₂⁻¹(q) | X₁ ≤ F₁⁻¹(q))

    If λ_L = 0: no tail dependence (independent in extremes)
    If λ_L = 1: perfect tail dependence (always crash together)

We estimate this empirically using the lower quadrant dependency:
    λ̂_L(q) = (1/n) Σ I(X₁ ≤ q₁) * I(X₂ ≤ q₂)

where q is a quantile threshold (e.g., 5th percentile = 0.05).
"""

import numpy as np
import pandas as pd
import networkx as nx
from scipy import stats


def compute_tail_dependence(
    returns: pd.DataFrame,
    quantile: float = 0.05,
) -> pd.DataFrame:
    """
    Compute pairwise tail dependence coefficients.

    Parameters
    ----------
    returns : pd.DataFrame
        Log returns matrix (T x N)
    quantile : float
        Threshold for "extreme" events (default 5th percentile)

    Returns
    -------
    pd.DataFrame
        NxN matrix of tail dependence coefficients
    """
    tickers = list(returns.columns)
    n = len(tickers)
    tail_corr = np.zeros((n, n))

    for i in range(n):
        for j in range(n):
            if i == j:
                tail_corr[i, j] = 1.0
            else:
                # Lower tail dependence
                # Count joint extremes / marginal extremes
                x = returns.iloc[:, i].values
                y = returns.iloc[:, j].values

                q_x = np.percentile(x, quantile * 100)
                q_y = np.percentile(y, quantile * 100)

                # Joint probability of both being in lower tail
                joint_extreme = np.mean((x <= q_x) & (y <= q_y))
                # Marginal probability
                marginal = quantile

                # Tail dependence coefficient
                if marginal > 0:
                    tail_corr[i, j] = joint_extreme / marginal
                else:
                    tail_corr[i, j] = 0.0

    # Clip to [0, 1] (numerical issues)
    tail_corr = np.clip(tail_corr, 0, 1)

    return pd.DataFrame(tail_corr, index=tickers, columns=tickers)


def build_tail_dependence_network(
    returns: pd.DataFrame,
    quantile: float = 0.05,
    mode: str = "top_k",
    k: int = 10,
    threshold: float = 0.3,
) -> nx.Graph:
    """
    Build network from tail dependence coefficients.

    This is similar to correlation_to_network but uses tail dependence
    instead of Pearson/Spearman correlation.
    """
    tail_corr = compute_tail_dependence(returns, quantile)
    tickers = list(returns.columns)
    n = len(tickers)

    G = nx.Graph()
    G.add_nodes_from(tickers)

    edges = []
    for i in range(n):
        for j in range(i + 1, n):
            w = tail_corr.iloc[i, j]
            if w > 1e-10:
                edges.append((tickers[i], tickers[j], w))

    if mode == "top_k":
        node_edges = {t: [] for t in tickers}
        for src, dst, w in edges:
            node_edges[src].append((w, dst))
            node_edges[dst].append((w, src))

        selected = set()
        for node in tickers:
            node_edges[node].sort(reverse=True)
            for w, neighbor in node_edges[node][:k]:
                edge_key = tuple(sorted([node, neighbor]))
                selected.add((edge_key[0], edge_key[1], w))

        for src, dst, w in selected:
            G.add_edge(src, dst, weight=w)

    elif mode == "threshold":
        for src, dst, w in edges:
            if w > threshold:
                G.add_edge(src, dst, weight=w)

    return G


def compare_tail_vs_pearson(
    returns: pd.DataFrame,
    quantile: float = 0.05,
) -> dict:
    """
    Compare tail dependence with Pearson correlation.

    This reveals assets that have low average correlation but
    high tail dependence — the "hidden" systemic risk.
    """
    from app.services.network_builder import build_pearson_network

    tickers = list(returns.columns)

    # Pearson network
    pearson_G = build_pearson_network(returns, mode="top_k", k=5)
    pearson_edges = set(pearson_G.edges())

    # Tail dependence network
    tail_G = build_tail_dependence_network(returns, quantile, mode="top_k", k=5)
    tail_edges = set(tail_G.edges())

    # Edges that appear in tail but not in Pearson
    hidden_risk = tail_edges - pearson_edges

    # Edges that appear in both
    shared = pearson_edges & tail_edges

    return {
        "pearson_edges": len(pearson_edges),
        "tail_edges": len(tail_edges),
        "shared_edges": len(shared),
        "hidden_risk_edges": len(hidden_risk),
        "hidden_risk_pairs": [
            {"source": u, "target": v} for u, v in hidden_risk
        ],
        "interpretation": (
            f"Found {len(hidden_risk)} edges that appear in tail dependence "
            f"but not in Pearson correlation. These are assets with low "
            f"average correlation but high crash co-movement — the hidden "
            f"systemic risk that standard correlation misses."
        ),
    }
