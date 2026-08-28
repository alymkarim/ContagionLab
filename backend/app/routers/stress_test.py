"""
Stress test router — runs Monte Carlo stress propagation on a network.

The endpoint builds a correlation network from the requested assets,
then propagates a shock from the specified asset through its neighbours
using a linear threshold model with Monte Carlo noise.
"""

import networkx as nx
from fastapi import APIRouter, HTTPException

from backend.app.models.schemas import StressTestRequest
from backend.app.services.data_fetcher import fetch_prices, get_returns
from backend.app.services.network_builder import (
    build_pearson_network,
    build_spearman_network,
    build_partial_correlation_network,
    build_graphical_lasso_network,
    build_granger_causality_network,
)
from backend.app.services.simulation import run_stress_test

router = APIRouter(prefix="/api/stress-test", tags=["stress-test"])

# Reuse the same method map as the networks router for consistency.
METHOD_MAP = {
    "pearson": build_pearson_network,
    "spearman": build_spearman_network,
    "partial_correlation": build_partial_correlation_network,
    "graphical_lasso": build_graphical_lasso_network,
    "granger_causality": build_granger_causality_network,
}


@router.post("/run")
def run_stress_test_endpoint(req: StressTestRequest):
    """Build a network and run a Monte Carlo stress test on it.

    Steps:
      1. Fetch prices and compute log returns for the requested assets.
      2. Build the correlation network using the specified method.
      3. Validate that the shock asset exists in the graph.
      4. Run the Monte Carlo stress test: for each neighbour j of the
         shocked asset, simulate x_j = w * shock + N(0, noise_std)
         over n_sims draws.
      5. Return per-asset summaries: median response, 95% CI, and
         probability of negative outcome.
    """
    method = req.method.lower()
    if method not in METHOD_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown method '{method}'. Choose from: {list(METHOD_MAP.keys())}",
        )

    try:
        prices = fetch_prices(req.assets, period=req.period)
        returns = get_returns(prices)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data fetch failed: {e}")

    # --- Build the network ------------------------------------------------
    builder = METHOD_MAP[method]

    if method == "granger_causality":
        G = builder(returns)
    else:
        G = builder(returns, mode="top_k", k=3)

    # --- Validate shock asset is in the graph -----------------------------
    if req.shock_asset not in G:
        raise HTTPException(
            status_code=400,
            detail=f"Shock asset '{req.shock_asset}' not found in the network. "
            f"Available: {list(G.nodes())}",
        )

    # --- Run the Monte Carlo stress test ----------------------------------
    # The linear threshold model propagates the shock to direct neighbours
    # only: x_j = w_{Sj} * shock_magnitude + epsilon_j.
    results = run_stress_test(
        G,
        shock_asset=req.shock_asset,
        shock_magnitude=req.shock_magnitude,
        n_sims=req.n_sims,
    )

    return {
        "shock_asset": req.shock_asset,
        "shock_magnitude": req.shock_magnitude,
        "n_sims": req.n_sims,
        "method": method,
        "results": results,
    }
