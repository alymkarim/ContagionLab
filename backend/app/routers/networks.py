"""
Networks router — builds correlation networks and returns graph + metrics.

The endpoint fetches price data, computes log returns, builds a
network using the requested method, optionally applies RMT filtering,
then returns the graph structure along with centrality, community,
and systemic-importance metrics.
"""

import networkx as nx
from fastapi import APIRouter, HTTPException

from app.models.schemas import NetworkBuildRequest
from app.services.analysis import (
    compute_centrality,
    compute_systemic_importance,
    detect_communities,
)
from app.services.data_fetcher import fetch_prices, get_returns
from app.services.network_builder import (
    build_granger_causality_network,
    build_graphical_lasso_network,
    build_partial_correlation_network,
    build_pearson_network,
    build_spearman_network,
)
from app.services.rmt_filter import filter_correlation_matrix

router = APIRouter(prefix="/api/networks", tags=["networks"])

# Map user-friendly method names to the corresponding builder functions.
# Each builder takes (returns, mode, k, threshold) except granger_causality
# which takes (returns, max_lag, significance).
METHOD_MAP = {
    "pearson": build_pearson_network,
    "spearman": build_spearman_network,
    "partial_correlation": build_partial_correlation_network,
    "graphical_lasso": build_graphical_lasso_network,
    "granger_causality": build_granger_causality_network,
}


def graph_to_json(G: nx.Graph | nx.DiGraph) -> dict:
    """Convert a networkx graph to a JSON-serialisable dict.

    Nodes carry their label as 'id' plus any attributes (e.g. community).
    Edges carry 'source', 'target', and 'weight'.
    """
    nodes = [{"id": n, **(G.nodes[n] if G.nodes[n] else {})} for n in G.nodes()]
    edges = []
    for u, v, data in G.edges(data=True):
        edge = {"source": u, "target": v, "weight": data.get("weight", 1.0)}
        # Granger causality edges carry a p_value instead of weight
        if "p_value" in data:
            edge["weight"] = round(1.0 - data["p_value"], 4)  # invert so stronger = higher
            edge["p_value"] = data["p_value"]
        edges.append(edge)
    return {"nodes": nodes, "edges": edges}


@router.post("/build")
def build_network(req: NetworkBuildRequest):
    """Build a correlation network from the requested assets and method.

    Steps:
      1. Fetch adjusted close prices for the given tickers and period.
      2. Compute log returns: r_t = ln(P_t / P_{t-1}).
      3. Build the network using the selected method.
      4. Optionally apply RMT filtering to remove noise eigenvalues.
      5. Compute centrality, communities, and systemic importance.
      6. Return the graph structure and all metrics as JSON.
    """
    method = req.method.lower()
    if method not in METHOD_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown method '{method}'. Choose from: {list(METHOD_MAP.keys())}",
        )

    if req.shock_asset if hasattr(req, "shock_asset") else False:
        # Not applicable here, but guard just in case
        pass

    try:
        prices = fetch_prices(req.assets, period=req.period)
        returns = get_returns(prices)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data fetch failed: {e}")

    # --- Build the network ------------------------------------------------
    builder = METHOD_MAP[method]

    if method == "granger_causality":
        # Granger causality has a different signature (max_lag, significance)
        # and returns a directed graph.
        G = builder(returns)
    else:
        # All correlation-based builders share (returns, mode, k, threshold).
        # We use top_k mode by default since the user specifies top_k.
        G = builder(returns, mode="top_k", k=req.top_k)

    # --- Optional RMT filtering -------------------------------------------
    # When use_rmt=True, we re-build from a filtered correlation matrix.
    # This only applies to correlation-based methods (not Granger).
    if req.use_rmt and method != "granger_causality":
        import numpy as np

        # Recompute the correlation matrix based on the method
        if method == "pearson":
            corr = np.corrcoef(returns.values, rowvar=False)
        elif method == "spearman":
            from scipy.stats import spearmanr

            corr, _ = spearmanr(returns.values)
        elif method == "partial_correlation":
            cov = np.cov(returns.values, rowvar=False)
            precision = np.linalg.inv(cov)
            diag = np.sqrt(np.diag(precision))
            diag = np.maximum(diag, 1e-12)
            corr = -precision / np.outer(diag, diag)
            np.fill_diagonal(corr, 1.0)
            corr = np.clip(corr, -1.0, 1.0)
        elif method == "graphical_lasso":
            from sklearn.covariance import GraphicalLassoCV

            model = GraphicalLassoCV(cv=5).fit(returns.values)
            precision = model.precision_
            diag = np.sqrt(np.diag(precision))
            diag = np.maximum(diag, 1e-12)
            corr = -precision / np.outer(diag, diag)
            np.fill_diagonal(corr, 1.0)
            corr = np.clip(corr, -1.0, 1.0)

        # Apply RMT: clip noise eigenvalues below the Marchenko-Pastur bound.
        # T = number of return observations, used to compute the bound.
        t = returns.shape[0]
        filtered_corr = filter_correlation_matrix(corr, t)

        from app.services.network_builder import correlation_to_network

        G = correlation_to_network(
            filtered_corr,
            list(returns.columns),
            mode="top_k",
            k=req.top_k,
        )

    # --- Compute metrics --------------------------------------------------
    graph_json = graph_to_json(G)

    # Centrality: degree, betweenness, eigenvector, PageRank
    centrality = compute_centrality(G) if isinstance(G, nx.Graph) else {}

    # Communities via Louvain modularity optimisation
    communities = detect_communities(G) if isinstance(G, nx.Graph) else {}

    # Systemic importance: composite score blending centrality + community
    systemic = compute_systemic_importance(G) if isinstance(G, nx.Graph) else {}

    return {
        "graph": graph_json,
        "metrics": {
            "centrality": centrality,
            "communities": communities,
            "systemic_importance": systemic,
        },
        "method": method,
        "num_nodes": G.number_of_nodes(),
        "num_edges": G.number_of_edges(),
    }
