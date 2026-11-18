"""Local-only FastAPI entry point for Study mode."""

from __future__ import annotations

from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from pokerhelper import __version__
from pokerhelper.application.catalog import StudyCatalog
from pokerhelper.domain.errors import DomainError
from pokerhelper.solutions import SolutionStore
from pokerhelper.solutions.artifact import validation_error_payload


def _default_data_dir() -> Path:
    configured = os.environ.get("POKERHELPER_DATA_DIR")
    return Path(configured).resolve() if configured else (Path.cwd() / "data").resolve()


def create_app(
    *,
    data_dir: str | Path | None = None,
    seed_root: str | Path | None = None,
    auto_seed: bool = True,
    frontend_dist: str | Path | None = None,
) -> FastAPI:
    store = SolutionStore(Path(data_dir).resolve() / "solutions" if data_dir is not None else _default_data_dir() / "solutions")
    catalog = StudyCatalog(store, seed_root)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if auto_seed:
            catalog.bootstrap()
        yield

    app = FastAPI(
        title="PokerHelper local API",
        version=__version__,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.state.catalog = catalog
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Accept", "Content-Type"],
    )

    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        status = 404 if exc.code in {"SOLUTION_NOT_FOUND", "SOLUTION_NODE_NOT_FOUND", "SCENARIO_NOT_FOUND"} else 422
        return JSONResponse(status_code=status, content=validation_error_payload(exc))

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": "local-offline"}

    @app.get("/api/v1/version")
    def version() -> dict[str, str]:
        return {"version": __version__, "solutionSchemaVersion": "1.0.0"}

    @app.get("/api/v1/scenarios")
    def scenarios() -> dict[str, Any]:
        return {"items": catalog.scenarios()}

    @app.get("/api/v1/scenarios/{scenario_id}")
    def scenario(scenario_id: str) -> dict[str, Any]:
        return catalog.scenario(scenario_id)

    @app.get("/api/v1/solutions/{solution_id}/assumptions")
    def assumptions(solution_id: str) -> dict[str, Any]:
        return catalog.assumptions(solution_id)

    @app.get("/api/v1/solutions/{solution_id}/nodes/{node_id}")
    def node(solution_id: str, node_id: str) -> Response:
        # These payloads contain 1,326 exact combos. Serializing directly avoids
        # FastAPI's recursive general-purpose encoder and keeps local p95 latency
        # comfortably inside the Study contract.
        payload = json.dumps(catalog.node(solution_id, node_id), ensure_ascii=True, separators=(",", ":"))
        return Response(content=payload, media_type="application/json")

    dist = Path(frontend_dist).resolve() if frontend_dist is not None else Path(__file__).resolve().parents[3] / "frontend" / "dist"
    if dist.exists():
        assets = dist / "assets"
        if assets.exists():
            app.mount("/assets", StaticFiles(directory=assets), name="frontend-assets")

        @app.get("/", include_in_schema=False)
        @app.get("/study/{client_path:path}", include_in_schema=False)
        def frontend(client_path: str = "") -> FileResponse:
            # React Router owns every non-API route. Always returning index.html
            # makes copied/bookmarked Study URLs survive a hard refresh.
            return FileResponse(dist / "index.html")
    return app


app = create_app()
