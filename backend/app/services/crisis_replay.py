"""
Historical crisis replay — build networks for specific market regimes.

The idea: instead of just looking at the current network, we can
replay historical crises and see how the network topology changed.
Did correlations spike? Did the network become more dense (systemic)?
Did new hubs emerge?

This is powerful because it validates the model: if the network
looks "different" during crises, it's capturing real systemic risk.

Crises covered:
- 2008 Global Financial Crisis (Lehman Brothers collapse)
- 2020 COVID-19 Crash (March 2020)
- 2022 Rate Hike / Tech Selloff

Physics analogy: this is like observing a phase transition.
In normal markets, the network is sparse (low density).
During crises, correlations spike → network densifies → systemic risk rises.
This is analogous to a ferromagnetic transition in a spin system.
"""

import yfinance as yf
import pandas as pd
import numpy as np
import networkx as nx
from datetime import datetime, timedelta


# Crisis definitions: (name, start_date, end_date, description)
CRISES = {
    "2008_gfc": {
        "name": "2008 Global Financial Crisis",
        "short": "2008 GFC",
        "pre": ("2007-01-01", "2008-08-31"),
        "during": ("2008-09-01", "2009-03-31"),
        "post": ("2009-04-01", "2010-06-30"),
        "description": "Lehman Brothers collapse, global credit freeze, stock market crash",
    },
    "2020_covid": {
        "name": "2020 COVID-19 Crash",
        "short": "2020 COVID",
        "pre": ("2019-09-01", "2020-02-19"),
        "during": ("2020-02-20", "2020-03-23"),
        "post": ("2020-03-24", "2020-12-31"),
        "description": "Fastest bear market in history — 34% drop in 23 trading days",
    },
    "2022_rates": {
        "name": "2022 Rate Hike Selloff",
        "short": "2022 Rates",
        "pre": ("2021-09-01", "2022-01-03"),
        "during": ("2022-01-04", "2022-10-12"),
        "post": ("2022-10-13", "2023-06-30"),
        "description": "Fed raises rates from 0% to 5.5%, tech stocks collapse, bonds sell off",
    },
}

# Default asset universe for crisis analysis
DEFAULT_ASSETS = [
    "SPY",   # S&P 500
    "QQQ",   # Nasdaq 100
    "IWM",   # Small caps
    "TLT",   # Long-term Treasuries
    "GLD",   # Gold
    "UUP",   # US Dollar
    "XLF",   # Financials
    "XLE",   # Energy
    "XLK",   # Technology
    "VIX",   # Volatility index
]


def fetch_crisis_data(
    assets: list[str],
    crisis_id: str,
) -> dict[str, pd.DataFrame]:
    """
    Fetch price data for a crisis period: pre, during, and post.

    Returns dict with keys 'pre', 'during', 'post', each containing
    a DataFrame of adjusted close prices.
    """
    if crisis_id not in CRISES:
        raise ValueError(f"Unknown crisis '{crisis_id}'. Choose from: {list(CRISES.keys())}")

    crisis = CRISES[crisis_id]
    results = {}

    for phase in ["pre", "during", "post"]:
        start, end = crisis[phase]
        # Extend start date to get enough history for returns
        start_dt = datetime.strptime(start, "%Y-%m-%d") - timedelta(days=30)
        data = yf.download(
            assets,
            start=start_dt.strftime("%Y-%m-%d"),
            end=end,
            progress=False,
            auto_adjust=True,
        )
        if isinstance(data.columns, pd.MultiIndex):
            prices = data["Close"]
        else:
            prices = data[["Close"]]
            prices.columns = assets

        # Drop columns with too many NaNs
        prices = prices.dropna(axis=1, thresh=int(len(prices) * 0.8))
        results[phase] = prices

    return results


def compute_log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Compute log returns: r_t = ln(P_t / P_{t-1})."""
    return np.log(prices / prices.shift(1)).dropna()


def build_phase_network(
    returns: pd.DataFrame,
    method: str = "pearson",
    top_k: int = 5,
) -> nx.Graph:
    """Build a network from returns for a single phase."""
    from app.services.network_builder import (
        build_pearson_network,
        build_spearman_network,
        build_partial_correlation_network,
        build_graphical_lasso_network,
    )

    builders = {
        "pearson": build_pearson_network,
        "spearman": build_spearman_network,
        "partial_correlation": build_partial_correlation_network,
        "graphical_lasso": build_graphical_lasso_network,
    }

    builder = builders.get(method, build_pearson_network)
    return builder(returns, mode="top_k", k=top_k)


def graph_to_json(G: nx.Graph) -> dict:
    """Convert networkx graph to JSON-serializable dict."""
    nodes = [{"id": n} for n in G.nodes()]
    edges = []
    for u, v, data in G.edges(data=True):
        edges.append({
            "source": u,
            "target": v,
            "weight": data.get("weight", 1.0),
        })
    return {"nodes": nodes, "edges": edges}


def compute_network_stats(G: nx.Graph) -> dict:
    """Compute summary statistics for a network phase."""
    density = nx.density(G)

    # Average clustering coefficient
    clustering = nx.average_clustering(G, weight="weight")

    # Average shortest path length (for connected components only)
    if nx.is_connected(G):
        avg_path = nx.average_shortest_path_length(G)
    else:
        # Use largest connected component
        largest_cc = max(nx.connected_components(G), key=len)
        subgraph = G.subgraph(largest_cc)
        avg_path = nx.average_shortest_path_length(subgraph)

    # Number of edges
    num_edges = G.number_of_edges()
    num_nodes = G.number_of_nodes()

    # Max degree
    max_degree = max(dict(G.degree()).values()) if G.nodes() else 0

    return {
        "density": round(density, 4),
        "clustering": round(clustering, 4),
        "avg_path_length": round(avg_path, 4),
        "num_edges": num_edges,
        "num_nodes": num_nodes,
        "max_degree": max_degree,
    }


def analyze_crisis(
    assets: list[str],
    crisis_id: str,
    method: str = "pearson",
    top_k: int = 5,
) -> dict:
    """
    Full crisis analysis: fetch data, build networks for each phase,
    compute statistics, and compare.
    """
    crisis = CRISES[crisis_id]

    # Fetch data
    price_data = fetch_crisis_data(assets, crisis_id)

    # Build networks for each phase
    phases = {}
    for phase_name, prices in price_data.items():
        returns = compute_log_returns(prices)
        if len(returns) < 10:
            continue

        G = build_phase_network(returns, method, top_k)
        stats = compute_network_stats(G)
        graph = graph_to_json(G)

        phases[phase_name] = {
            "graph": graph,
            "stats": stats,
            "num_observations": len(returns),
            "date_range": {
                "start": str(returns.index[0].date()),
                "end": str(returns.index[-1].date()),
            },
        }

    # Compute phase comparisons
    comparison = {}
    if "pre" in phases and "during" in phases:
        pre_stats = phases["pre"]["stats"]
        during_stats = phases["during"]["stats"]

        comparison = {
            "density_change": round(
                during_stats["density"] - pre_stats["density"], 4
            ),
            "density_change_pct": round(
                (during_stats["density"] - pre_stats["density"])
                / max(pre_stats["density"], 0.001)
                * 100,
                1,
            ),
            "clustering_change": round(
                during_stats["clustering"] - pre_stats["clustering"], 4
            ),
            "edges_change": during_stats["num_edges"] - pre_stats["num_edges"],
            "interpretation": _interpret_crisis(pre_stats, during_stats),
        }

    return {
        "crisis": {
            "id": crisis_id,
            "name": crisis["name"],
            "short": crisis["short"],
            "description": crisis["description"],
        },
        "method": method,
        "phases": phases,
        "comparison": comparison,
    }


def _interpret_crisis(pre: dict, during: dict) -> str:
    """Generate a human-readable interpretation of the crisis comparison."""
    density_up = during["density"] > pre["density"]
    clustering_up = during["clustering"] > pre["clustering"]

    if density_up and clustering_up:
        return (
            "Network densified and clustering increased — assets moved together "
            "more strongly, indicating systemic contagion. This is the classic "
            "crisis signature: correlations spike, diversification benefits vanish."
        )
    elif density_up:
        return (
            "Network densified during the crisis — more assets became correlated. "
            "This suggests contagion effects, though cluster structure remained stable."
        )
    elif clustering_up:
        return (
            "Clustering increased while overall density stayed stable — local "
            "groups of assets became more tightly coupled, but the broader "
            "network structure didn't change dramatically."
        )
    else:
        return (
            "Network topology remained relatively stable — the crisis did not "
            "produce the typical correlation spike. This could indicate a "
            "sector-specific event rather than systemic contagion."
        )
