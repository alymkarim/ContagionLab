"""
Composite fragility index — a single number for systemic health.

Inspired by the VIX (volatility index) but network-aware.
The fragility index combines:

1. Network density — how connected are assets?
   Higher density = more systemic risk (contagion channels)

2. Average clustering — are there tight cliques?
   Higher clustering = more concentrated risk

3. Average shortest path — how fast can shocks propagate?
   Shorter paths = faster contagion

4. Spectral gap — second eigenvalue of the Laplacian
   Smaller gap = more "rigid" network = harder to absorb shocks

5. Volatility — average return volatility
   Higher vol = more uncertainty

Each component is normalized to [0, 1] across historical windows,
then combined with weights. The result is a time-varying fragility
score that can be tracked over time.

Physics analogy: this is like an order parameter for a spin system.
A single number that captures the collective behavior of many
interacting components. Low fragility = disordered (resilient).
High fragility = ordered (fragile, correlated, one shock away from collapse).
"""

import numpy as np
import pandas as pd
import networkx as nx
from typing import Optional


def compute_fragility_index(
    returns: pd.DataFrame,
    window: int = 60,
    method: str = "pearson",
    top_k: int = 5,
) -> pd.DataFrame:
    """
    Compute rolling fragility index over time.

    Parameters
    ----------
    returns : pd.DataFrame
        Log returns matrix (T x N)
    window : int
        Rolling window size in trading days (default 60 ≈ 3 months)
    method : str
        Network construction method
    top_k : int
        Edges per node in network

    Returns
    -------
    pd.DataFrame
        DataFrame with columns: fragility, density, clustering, avg_path, volatility
    """
    from app.services.network_builder import (
        build_pearson_network,
        build_spearman_network,
        build_partial_correlation_network,
    )

    builders = {
        "pearson": build_pearson_network,
        "spearman": build_spearman_network,
        "partial_correlation": build_partial_correlation_network,
    }
    builder = builders.get(method, build_pearson_network)

    n_assets = len(returns.columns)
    results = []

    for end_idx in range(window, len(returns)):
        start_idx = end_idx - window
        window_returns = returns.iloc[start_idx:end_idx]

        # Build network for this window
        G = builder(window_returns, mode="top_k", k=top_k)

        # Compute network metrics
        density = nx.density(G)
        clustering = nx.average_clustering(G, weight="weight") if G.edges() else 0

        # Average path length
        if nx.is_connected(G) and G.number_of_nodes() > 1:
            avg_path = nx.average_shortest_path_length(G)
        elif G.number_of_nodes() > 1:
            largest_cc = max(nx.connected_components(G), key=len)
            subgraph = G.subgraph(largest_cc)
            avg_path = nx.average_shortest_path_length(subgraph)
        else:
            avg_path = 0

        # Spectral gap (second smallest eigenvalue of Laplacian)
        spectral_gap = _compute_spectral_gap(G)

        # Volatility (annualized)
        volatility = window_returns.std().mean() * np.sqrt(252)

        # Normalize each component
        density_norm = min(density / 0.5, 1.0)  # 0.5 is very dense
        clustering_norm = min(clustering / 0.8, 1.0)
        path_norm = max(1 - avg_path / 10, 0)  # shorter path = higher fragility
        spectral_norm = max(1 - spectral_gap / 2, 0)  # smaller gap = higher fragility
        vol_norm = min(volatility / 0.5, 1.0)  # 50% annualized vol is extreme

        # Composite score (weighted average)
        fragility = (
            0.25 * density_norm
            + 0.20 * clustering_norm
            + 0.20 * path_norm
            + 0.15 * spectral_norm
            + 0.20 * vol_norm
        )

        date = returns.index[end_idx - 1]
        results.append({
            "date": date,
            "fragility": round(fragility, 4),
            "density": round(density, 4),
            "clustering": round(clustering, 4),
            "avg_path_length": round(avg_path, 4),
            "spectral_gap": round(spectral_gap, 4),
            "volatility": round(volatility, 4),
        })

    return pd.DataFrame(results).set_index("date")


def _compute_spectral_gap(G: nx.Graph) -> float:
    """
    Compute the spectral gap of the graph Laplacian.

    The spectral gap is the second smallest eigenvalue of the Laplacian
    matrix. It measures how well-connected the graph is:
    - Large gap → well-connected, resilient
    - Small gap → barely connected, fragile

    This is the algebraic connectivity (Fiedler value).
    """
    if G.number_of_nodes() < 2:
        return 0.0

    # Use largest connected component if graph is disconnected
    if not nx.is_connected(G):
        largest_cc = max(nx.connected_components(G), key=len)
        G = G.subgraph(largest_cc).copy()

    try:
        # Compute Laplacian eigenvalues
        L = nx.laplacian_matrix(G).toarray()
        eigenvalues = np.linalg.eigvalsh(L)
        # Sort ascending
        eigenvalues = np.sort(eigenvalues)
        # Spectral gap = second smallest eigenvalue
        return float(eigenvalues[1])
    except Exception:
        return 0.0


def get_fragility_summary(
    fragility_df: pd.DataFrame,
) -> dict:
    """
    Summarize the fragility index time series.
    """
    if fragility_df.empty:
        return {}

    latest = fragility_df.iloc[-1]
    mean = fragility_df["fragility"].mean()
    std = fragility_df["fragility"].std()
    max_val = fragility_df["fragility"].max()
    min_val = fragility_df["fragility"].min()

    # Current regime
    current = latest["fragility"]
    if current > mean + std:
        regime = "stressed"
        regime_desc = "Fragility is elevated above normal — the system is under stress."
    elif current < mean - std:
        regime = "resilient"
        regime_desc = "Fragility is below normal — the system appears resilient."
    else:
        regime = "normal"
        regime_desc = "Fragility is within normal range."

    # Trend (last 20 days)
    if len(fragility_df) > 20:
        recent = fragility_df["fragility"].tail(20)
        trend_slope = np.polyfit(range(20), recent.values, 1)[0]
        if trend_slope > 0.001:
            trend = "increasing"
        elif trend_slope < -0.001:
            trend = "decreasing"
        else:
            trend = "stable"
    else:
        trend = "unknown"

    return {
        "current_fragility": round(current, 4),
        "mean_fragility": round(mean, 4),
        "std_fragility": round(std, 4),
        "max_fragility": round(max_val, 4),
        "min_fragility": round(min_val, 4),
        "regime": regime,
        "regime_description": regime_desc,
        "trend": trend,
        "num_observations": len(fragility_df),
    }
