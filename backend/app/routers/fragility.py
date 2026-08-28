"""
Fragility index router — systemic health monitoring endpoints.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/fragility", tags=["fragility"])


class FragilityRequest(BaseModel):
    assets: list[str]
    period: str = "2y"
    window: int = 60
    method: str = "pearson"
    top_k: int = 5


@router.post("/compute")
def compute_fragility(req: FragilityRequest):
    """Compute rolling fragility index over time."""
    from app.services.data_fetcher import fetch_prices, get_returns
    from app.services.fragility import compute_fragility_index, get_fragility_summary

    try:
        prices = fetch_prices(req.assets, period=req.period)
        returns = get_returns(prices)

        frag_df = compute_fragility_index(
            returns,
            window=req.window,
            method=req.method,
            top_k=req.top_k,
        )

        summary = get_fragility_summary(frag_df)

        # Convert to list of dicts for JSON
        history = []
        for date, row in frag_df.iterrows():
            history.append({
                "date": str(date.date()),
                "fragility": row["fragility"],
                "density": row["density"],
                "clustering": row["clustering"],
                "volatility": row["volatility"],
            })

        return {
            "summary": summary,
            "history": history,
            "method": req.method,
            "window": req.window,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fragility computation failed: {e}")
