"""
Macro data router — VIX, Treasury yields, dollar index endpoints.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/macro", tags=["macro"])


class MacroDataRequest(BaseModel):
    assets: list[str]
    period: str = "1y"
    include: Optional[list[str]] = None  # None = all macro indicators


@router.get("/tickers")
def list_macro_tickers():
    """List available macro indicators."""
    from app.services.macro_data import get_macro_tickers
    return {"tickers": get_macro_tickers()}


@router.post("/fetch")
def fetch_macro_data(req: MacroDataRequest):
    """Fetch macro data and merge with equity prices."""
    from app.services.macro_data import (
        fetch_macro_data,
        merge_with_equity,
        get_macro_summary,
    )
    from app.services.data_fetcher import fetch_prices

    try:
        # Fetch equity prices
        equity_prices = fetch_prices(req.assets, period=req.period)

        # Fetch macro data
        macro_prices = fetch_macro_data(period=req.period, include=req.include)

        # Merge
        merged = merge_with_equity(equity_prices, macro_prices)

        # Summary
        summary = get_macro_summary(macro_prices)

        return {
            "assets": req.assets,
            "macro_indicators": list(macro_prices.columns),
            "merged_observations": len(merged),
            "summary": summary,
            "columns": list(merged.columns),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Macro data fetch failed: {e}")


class MacroNetworkRequest(BaseModel):
    assets: list[str]
    macro_indicators: list[str] = ["VIX", "DGS10", "DXY"]
    period: str = "1y"
    method: str = "pearson"
    top_k: int = 5


@router.post("/network")
def build_macro_network(req: MacroNetworkRequest):
    """Build a network that includes macro indicators alongside equity assets."""
    from app.services.macro_data import fetch_macro_data, merge_with_equity
    from app.services.data_fetcher import fetch_prices, get_returns
    from app.services.network_builder import (
        build_pearson_network,
        build_spearman_network,
        build_partial_correlation_network,
        build_graphical_lasso_network,
    )
    from app.services.analysis import (
        compute_centrality,
        detect_communities,
        compute_systemic_importance,
    )

    builders = {
        "pearson": build_pearson_network,
        "spearman": build_spearman_network,
        "partial_correlation": build_partial_correlation_network,
        "graphical_lasso": build_graphical_lasso_network,
    }

    builder = builders.get(req.method, build_pearson_network)

    try:
        # Fetch equity prices
        equity_prices = fetch_prices(req.assets, period=req.period)

        # Fetch macro data
        macro_prices = fetch_macro_data(period=req.period, include=req.macro_indicators)

        # Merge
        merged = merge_with_equity(equity_prices, macro_prices)

        # Compute returns
        returns = get_returns(merged)

        # Build network
        G = builder(returns, mode="top_k", k=req.top_k)

        # Compute metrics
        import networkx as nx
        from app.routers.networks import graph_to_json

        graph_json = graph_to_json(G)
        centrality = compute_centrality(G) if isinstance(G, nx.Graph) else {}
        communities = detect_communities(G) if isinstance(G, nx.Graph) else {}
        systemic = compute_systemic_importance(G) if isinstance(G, nx.Graph) else {}

        return {
            "graph": graph_json,
            "metrics": {
                "centrality": centrality,
                "communities": communities,
                "systemic_importance": systemic,
            },
            "method": req.method,
            "num_nodes": G.number_of_nodes(),
            "num_edges": G.number_of_edges(),
            "macro_included": req.macro_indicators,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Macro network build failed: {e}")
