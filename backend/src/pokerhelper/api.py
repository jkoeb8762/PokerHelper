"""Local-only FastAPI entry point for Study and Trainer modes."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from pokerhelper import __version__
from pokerhelper.api_models import CreateTrainingSessionRequest, RedrillRequest, SubmitDecisionRequest
from pokerhelper.application.catalog import StudyCatalog
from pokerhelper.application.solution_rules import SolutionRuleValidator
from pokerhelper.application.training import TrainingService
from pokerhelper.domain.errors import DomainError
from pokerhelper.infrastructure import Database, SqlAlchemyTrainingRepository
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
    randomizer: Any | None = None,
    clock: Any | None = None,
    id_factory: Any | None = None,
) -> FastAPI:
    data_root = Path(data_dir).resolve() if data_dir is not None else _default_data_dir()
    store = SolutionStore(data_root / "solutions")
    rule_validator = SolutionRuleValidator()
    catalog = StudyCatalog(store, seed_root, rule_validator)
    database = Database(data_root / "pokerhelper.db")
    training = TrainingService(
        catalog,
        SqlAlchemyTrainingRepository(database),
        rule_validator=rule_validator,
        randomizer=randomizer,
        clock=clock,
        id_factory=id_factory,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        database.migrate()
        if auto_seed:
            catalog.bootstrap()
        database.sync_scenarios(catalog.scenarios(), synced_at=_utc_now())
        try:
            yield
        finally:
            database.dispose()

    app = FastAPI(
        title="PokerHelper local API",
        version=__version__,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.state.catalog = catalog
    app.state.database = database
    app.state.training = training
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Accept", "Content-Type"],
    )

    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        if exc.code in {
            "SOLUTION_NOT_FOUND", "SOLUTION_NODE_NOT_FOUND", "SCENARIO_NOT_FOUND",
            "TRAINER_SESSION_NOT_FOUND", "TRAINER_DECISION_NOT_FOUND",
        }:
            response_status = 404
        elif exc.code in {"TRAINER_SESSION_NOT_ACTIVE", "TRAINER_PROMPT_STALE", "TRAINER_FEEDBACK_DELAYED"}:
            response_status = 409
        else:
            response_status = 422
        return JSONResponse(status_code=response_status, content=validation_error_payload(exc))

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

    @app.post("/api/v1/training/sessions", status_code=status.HTTP_201_CREATED)
    def create_training_session(request: CreateTrainingSessionRequest) -> dict[str, Any]:
        return training.create_session(request.model_dump())

    @app.get("/api/v1/training/sessions")
    def training_sessions() -> dict[str, Any]:
        return training.list_sessions()

    @app.get("/api/v1/training/statistics")
    def training_statistics() -> dict[str, Any]:
        return training.statistics()

    @app.get("/api/v1/training/sessions/{session_id}")
    def training_session(session_id: str) -> dict[str, Any]:
        return training.session_detail(session_id)

    @app.get("/api/v1/training/sessions/{session_id}/prompt")
    def training_prompt(session_id: str) -> dict[str, Any]:
        return training.next_prompt(session_id)

    @app.post("/api/v1/training/sessions/{session_id}/prompt/rng")
    def training_rng(session_id: str) -> dict[str, Any]:
        return training.show_rng(session_id)

    @app.post("/api/v1/training/sessions/{session_id}/decisions")
    def submit_training_decision(session_id: str, request: SubmitDecisionRequest) -> dict[str, Any]:
        return training.submit_decision(session_id, request.promptId, request.selectedOptionId)

    @app.post("/api/v1/training/sessions/{session_id}/complete")
    def complete_training_session(session_id: str) -> dict[str, Any]:
        return training.complete_session(session_id)

    @app.post("/api/v1/training/sessions/{session_id}/repeat", status_code=status.HTTP_201_CREATED)
    def repeat_training_session(session_id: str) -> dict[str, Any]:
        return training.repeat_session(session_id)

    @app.post("/api/v1/training/sessions/{session_id}/redrill", status_code=status.HTTP_201_CREATED)
    def redrill_training_session(session_id: str, request: RedrillRequest) -> dict[str, Any]:
        return training.redrill(session_id, request.mode)

    @app.get("/api/v1/training/sessions/{session_id}/decisions/{decision_id}")
    def training_decision(session_id: str, decision_id: str) -> dict[str, Any]:
        return training.decision_replay(session_id, decision_id)

    @app.delete("/api/v1/training/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_training_session(session_id: str) -> Response:
        training.delete_session(session_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    dist = Path(frontend_dist).resolve() if frontend_dist is not None else Path(__file__).resolve().parents[3] / "frontend" / "dist"
    if dist.exists():
        assets = dist / "assets"
        if assets.exists():
            app.mount("/assets", StaticFiles(directory=assets), name="frontend-assets")

        @app.get("/", include_in_schema=False)
        @app.get("/train", include_in_schema=False)
        @app.get("/sessions", include_in_schema=False)
        @app.get("/study/{client_path:path}", include_in_schema=False)
        @app.get("/train/{client_path:path}", include_in_schema=False)
        @app.get("/sessions/{client_path:path}", include_in_schema=False)
        def frontend(client_path: str = "") -> FileResponse:
            # React Router owns every non-API route. Always returning index.html
            # makes copied/bookmarked Study URLs survive a hard refresh.
            return FileResponse(dist / "index.html")
    return app


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


app = create_app()
