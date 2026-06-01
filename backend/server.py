"""
FastAPI server for the career twin finder.

Serves:
  GET  /                   → frontend (index.html)
  GET  /api/health         → health check
  POST /api/twins          → find twins for a given query

Run locally:
    uvicorn backend.server:app --reload --port 8000

Then open http://localhost:8000
"""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path

mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.twins import find_twins, to_dict, MAX_NUM_TWINS, DEFAULT_NUM_TWINS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("server")

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Career Twin Finder", version="0.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Permissive CORS so a deployed frontend on a different origin works.
# Tighten for prod if you ever care.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


class TwinsRequest(BaseModel):
    query: str = Field(..., min_length=1, description="LinkedIn URL or resume text")
    num_twins: int = Field(DEFAULT_NUM_TWINS, ge=1, le=MAX_NUM_TWINS)
    use_cache: bool = True


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/twins")
@limiter.limit("5/hour")
def api_twins(request: Request, req: TwinsRequest):
    try:
        result = find_twins(
            query=req.query,
            num_twins=req.num_twins,
            use_cache=req.use_cache,
        )
        return to_dict(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # API key not set, etc.
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:  # noqa: BLE001
        log.exception("unexpected error")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


# Static frontend. Mounted last so /api/* takes precedence.
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    def index():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/{path:path}")
    def frontend_passthrough(path: str):
        target = FRONTEND_DIR / path
        if target.is_file():
            return FileResponse(target)
        # SPA-style fallback to index
        return FileResponse(FRONTEND_DIR / "index.html")
