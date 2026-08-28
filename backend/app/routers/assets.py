"""
Assets router — serves the default ticker universe grouped by sector.

The universe is a curated set of liquid ETFs and index funds spanning
equities, fixed income, and commodities.  Grouping by sector allows
the frontend to render a structured asset picker.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/assets", tags=["assets"])

# Default asset universe: ticker → human-readable name, organised by sector.
DEFAULT_UNIVERSE: dict[str, dict[str, str]] = {
    "tech": {
        "QQQ": "Invesco QQQ (Nasdaq 100)",
        "XLK": "Technology Select Sector SPDR",
        "VGT": "Vanguard Information Technology ETF",
        "SOXX": "iShares Semiconductor ETF",
        "ARKK": "ARK Innovation ETF",
    },
    "finance": {
        "XLF": "Financial Select Sector SPDR",
        "VFH": "Vanguard Financials ETF",
        "KBE": "SPDR S&P Bank ETF",
        "KRE": "SPDR S&P Regional Banking ETF",
    },
    "energy": {
        "XLE": "Energy Select Sector SPDR",
        "VDE": "Vanguard Energy ETF",
        "OIH": "VanEck Oil Services ETF",
        "USO": "United States Oil Fund",
    },
    "commodities": {
        "GLD": "SPDR Gold Shares",
        "SLV": "iShares Silver Trust",
        "DBC": "Invesco DB Commodity Index",
        "PDBC": "Invesco Optimum Yield Diversified Commodity",
        "IAU": "iShares Gold Trust",
    },
    "bonds": {
        "TLT": "iShares 20+ Year Treasury Bond ETF",
        "IEF": "iShares 7-10 Year Treasury Bond ETF",
        "SHY": "iShares 1-3 Year Treasury Bond ETF",
        "AGG": "iShares Core U.S. Aggregate Bond ETF",
        "LQD": "iShares iBoxx $ Investment Grade Corporate Bond",
        "HYG": "iShares iBoxx $ High Yield Corporate Bond",
    },
    "index": {
        "SPY": "SPDR S&P 500 ETF Trust",
        "IVV": "iShares Core S&P 500 ETF",
        "VTI": "Vanguard Total Stock Market ETF",
        "DIA": "SPDR Dow Jones Industrial Average ETF",
        "IWM": "iShares Russell 2000 ETF",
        "EFA": "iShares MSCI EAFE ETF",
        "VWO": "Vanguard FTSE Emerging Markets ETF",
    },
}


@router.get("")
def get_assets():
    """Return the default ticker universe grouped by sector."""
    return {"universe": DEFAULT_UNIVERSE}
