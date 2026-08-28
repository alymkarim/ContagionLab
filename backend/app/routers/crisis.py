"""
Crisis replay router — historical crisis analysis endpoints.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/crisis", tags=["crisis"])


class CrisisRequest(BaseModel):
    assets: list[str]
    crisis_id: str  # 2008_gfc, 2020_covid, 2022_rates
    method: str = "pearson"
    top_k: int = 5


@router.get("/list")
def list_crises():
    """List available historical crises."""
    from app.services.crisis_replay import CRISES
    return {
        "crises": [
            {
                "id": cid,
                "name": c["name"],
                "short": c["short"],
                "description": c["description"],
                "periods": {
                    "pre": c["pre"],
                    "during": c["during"],
                    "post": c["post"],
                },
            }
            for cid, c in CRISES.items()
        ]
    }


@router.post("/analyze")
def analyze_crisis(req: CrisisRequest):
    """Run full crisis analysis: pre/during/post networks + comparison."""
    from app.services.crisis_replay import analyze_crisis, CRISES

    if req.crisis_id not in CRISES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown crisis '{req.crisis_id}'. Choose from: {list(CRISES.keys())}",
        )

    try:
        result = analyze_crisis(
            assets=req.assets,
            crisis_id=req.crisis_id,
            method=req.method,
            top_k=req.top_k,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crisis analysis failed: {e}")
