# Pydantic schemas for API request/response validation

from pydantic import BaseModel, Field


class NetworkBuildRequest(BaseModel):
    """Request payload for building a correlation network.

    The network is constructed from pairwise correlations between
    asset returns.  The 'method' parameter selects which correlation
    estimator to use (Pearson, Spearman, etc.), and 'top_k' controls
    the maximum degree of each node in the resulting graph.
    """

    assets: list[str] = Field(
        ...,
        min_length=2,
        description="Ticker symbols to include in the network (at least 2).",
    )
    method: str = Field(
        default="pearson",
        description="Network construction method: pearson, spearman, "
        "partial_correlation, graphical_lasso, or granger_causality.",
    )
    period: str = Field(
        default="1y",
        description="yfinance period string for historical data (e.g. '1y', '6mo', '5d').",
    )
    top_k: int = Field(
        default=3,
        ge=1,
        description="Maximum degree per node in the network (used in top_k mode).",
    )
    use_rmt: bool = Field(
        default=False,
        description="Apply Random Matrix Theory filtering to the correlation matrix "
        "before building the network.  Removes noise eigenvalues below the "
        "Marchenko-Pastur bound.",
    )


class StressTestRequest(BaseModel):
    """Request payload for running a Monte Carlo stress test.

    The stress test propagates a shock from one asset through the
    correlation network to its neighbours using a linear threshold
    model.  The shock magnitude acts as the initial perturbation,
    and edge weights serve as transmission coefficients.
    """

    assets: list[str] = Field(
        ...,
        min_length=2,
        description="Ticker symbols to include in the network.",
    )
    method: str = Field(
        default="pearson",
        description="Network construction method for the underlying graph.",
    )
    period: str = Field(
        default="1y",
        description="yfinance period string for historical data.",
    )
    shock_asset: str = Field(
        ...,
        description="Ticker symbol of the asset receiving the initial shock.",
    )
    shock_magnitude: float = Field(
        default=-0.2,
        description="Size of the shock (negative = crash scenario, e.g. -0.2 for a 20% drop).",
    )
    n_sims: int = Field(
        default=1000,
        ge=1,
        description="Number of Monte Carlo simulations to run.",
    )
