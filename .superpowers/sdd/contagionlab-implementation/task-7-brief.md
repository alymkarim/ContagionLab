# Task 7: FastAPI Endpoints

**Files:**
- Create: `backend/app/routers/networks.py`
- Create: `backend/app/routers/stress_test.py`
- Create: `backend/app/models/schemas.py`
- Modify: `backend/app/main.py`

**Depends on:** Tasks 2-6

## Steps

1. Create `backend/app/models/schemas.py` with Pydantic models:
   - `NetworkBuildRequest` — assets, method, period, top_k, use_rmt
   - `StressTestRequest` — assets, method, period, shock_asset, shock_magnitude, n_sims

2. Create `backend/app/routers/networks.py`:
   - `POST /api/networks/build` — accepts NetworkBuildRequest, fetches data, builds network, returns JSON with network graph, metrics, centrality, communities, systemic importance
   - `graph_to_json(G)` helper converting networkx graph to {nodes, edges} dict
   - METHOD_MAP dict mapping method names to builder functions
   - Optional RMT filtering when use_rmt=True

3. Create `backend/app/routers/stress_test.py`:
   - `POST /api/stress-test/run` — accepts StressTestRequest, builds network, runs stress test, returns results

4. Update `backend/app/main.py`:
   - Import and register all routers (assets, networks, stress_test)

5. Test the API:
   - `cd backend && python -m pytest tests/ -v` — all existing tests should still pass

6. Commit: `git add backend/ && git commit -m "FastAPI endpoints — /api/networks/build, /api/stress-test/run, Pydantic schemas"`

## Global Constraints

- Python 3.11+
- Working comments explaining the math
- Human-style commit messages
- Tests use pytest
