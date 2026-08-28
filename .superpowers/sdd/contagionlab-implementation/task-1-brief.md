# Task 1: Project Scaffolding

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `.gitignore`
- Create: `README.md`

**Depends on:** nothing

## Steps

1. Initialize git repo: `git init`
2. Create `.gitignore` with: `__pycache__/`, `*.pyc`, `.env`, `venv/`, `.venv/`, `*.parquet`, `node_modules/`, `dist/`, `.pytest_cache/`, `.mypy_cache/`
3. Create directory structure: `backend/app/routers`, `backend/app/services`, `backend/app/models`, `backend/tests`, `frontend`
4. Create `__init__.py` files in all Python packages
5. Create `backend/requirements.txt` with: fastapi>=0.104.0, uvicorn>=0.24.0, numpy>=1.24.0, scipy>=1.11.0, pandas>=2.1.0, scikit-learn>=1.3.0, statsmodels>=0.14.0, networkx>=3.2, yfinance>=0.2.30, pyarrow>=14.0, pytest>=7.4.0, httpx>=0.25.0
6. Create `backend/app/main.py` with FastAPI app, CORS middleware, and `/health` endpoint returning `{"status": "ok"}`
7. Create `backend/tests/conftest.py` with just `import pytest`
8. Write test `backend/tests/test_health.py` that calls `/health` and asserts status 200 and `{"status": "ok"}`
9. Run test: `cd backend && python -m pytest tests/test_health.py -v` — expect PASS
10. Create skeleton `README.md`
11. Commit: `git add . && git commit -m "initial project structure — backend skeleton, health endpoint"`

## Global Constraints

- Python 3.11+, no lower versions
- All code must have working comments explaining the math
- Commit messages must be human-style, no conventional-commit format
- Tests use pytest, no other test framework
