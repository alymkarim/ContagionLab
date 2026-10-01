"""
Vercel ASGI entrypoint for ContagionLab.

Vercel looks for a top-level `app` in this file and routes every request
under /api to it. The FastAPI application itself is untouched: this module
only fixes up the import path so the backend package resolves the same way
it does when you run `uvicorn app.main:app` from inside backend/.

The backend modules import each other as a top level `app` package
(`from app.routers.assets import ...`), so backend/ has to be on sys.path
rather than the repo root.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _REPO_ROOT / "backend"

if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.main import app  # noqa: E402  (path setup must run before this import)
