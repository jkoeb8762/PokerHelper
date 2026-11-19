"""SQLAlchemy/SQLite persistence and Alembic migration bootstrap."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import json
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class ScenarioRow(Base):
    __tablename__ = "scenarios"

    scenario_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    solution_id: Mapped[str] = mapped_column(String(96), nullable=False)
    solution_version: Mapped[str] = mapped_column(String(160), nullable=False)
    root_node_id: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    trainer_eligible: Mapped[int] = mapped_column(Integer, nullable=False)
    accuracy_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False)
    synced_at: Mapped[str] = mapped_column(String(40), nullable=False)


class TrainingSessionRow(Base):
    __tablename__ = "training_sessions"

    session_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    schema_version: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    scenario_id: Mapped[str] = mapped_column(
        String(160), ForeignKey("scenarios.scenario_id", ondelete="RESTRICT"), nullable=False
    )
    solution_id: Mapped[str] = mapped_column(String(96), nullable=False)
    solution_version: Mapped[str] = mapped_column(String(160), nullable=False)
    selected_node_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    hero_positions_json: Mapped[str] = mapped_column(Text, nullable=False)
    target_decisions: Mapped[int] = mapped_column(Integer, nullable=False)
    feedback_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    scoring_policy_version: Mapped[str] = mapped_column(String(16), nullable=False)
    sampling_policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    accuracy_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    approximate_acknowledged_at: Mapped[str | None] = mapped_column(String(40))
    rng_enabled: Mapped[int] = mapped_column(Integer, nullable=False)
    drill_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_session_id: Mapped[str | None] = mapped_column(
        String(80), ForeignKey("training_sessions.session_id", ondelete="SET NULL")
    )
    drill_items_json: Mapped[str] = mapped_column(Text, nullable=False)
    pending_prompt_json: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[str] = mapped_column(String(40), nullable=False)
    completed_at: Mapped[str | None] = mapped_column(String(40))
    summary_json: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("ix_training_sessions_started", "started_at"),
        Index("ix_training_sessions_scenario", "scenario_id"),
    )


class DecisionRow(Base):
    __tablename__ = "training_decisions"

    decision_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    prompt_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    session_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("training_sessions.session_id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    scenario_id: Mapped[str] = mapped_column(String(160), nullable=False)
    game_config_id: Mapped[str] = mapped_column(String(96), nullable=False)
    solution_id: Mapped[str] = mapped_column(String(96), nullable=False)
    solution_version: Mapped[str] = mapped_column(String(160), nullable=False)
    node_id: Mapped[str] = mapped_column(String(32), nullable=False)
    hero_position: Mapped[str] = mapped_column(String(8), nullable=False)
    action_history_key: Mapped[str] = mapped_column(Text, nullable=False)
    hero_combo: Mapped[str] = mapped_column(String(4), nullable=False)
    grouped_hand: Mapped[str] = mapped_column(String(3), nullable=False)
    offered_options_json: Mapped[str] = mapped_column(Text, nullable=False)
    selected_option_id: Mapped[str] = mapped_column(String(80), nullable=False)
    selected_resolved_action_json: Mapped[str] = mapped_column(Text, nullable=False)
    combo_reach_weight: Mapped[str] = mapped_column(String(80), nullable=False)
    reference_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    highest_ev_option_id: Mapped[str] = mapped_column(String(80), nullable=False)
    ev_loss_bb: Mapped[str] = mapped_column(String(80), nullable=False)
    feedback_severity: Mapped[str] = mapped_column(String(32), nullable=False)
    strategy_status: Mapped[str] = mapped_column(String(32), nullable=False)
    scoring_policy_version: Mapped[str] = mapped_column(String(16), nullable=False)
    accuracy_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    rng_roll: Mapped[int | None] = mapped_column(Integer)
    rng_mapping_json: Mapped[str | None] = mapped_column(Text)
    presented_at: Mapped[str] = mapped_column(String(40), nullable=False)
    answered_at: Mapped[str] = mapped_column(String(40), nullable=False)
    interpretation: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint("session_id", "sequence", name="uq_training_decision_sequence"),
        Index("ix_training_decisions_session", "session_id"),
        Index("ix_training_decisions_review", "feedback_severity", "ev_loss_bb"),
        Index("ix_training_decisions_calibration", "solution_id", "node_id", "grouped_hand"),
    )


class Database:
    """Own the configured database, migrations, and short-lived transactions."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{self.path.as_posix()}"
        self.engine = create_engine(url, connect_args={"check_same_thread": False})
        event.listen(self.engine, "connect", _configure_sqlite)
        self._sessions = sessionmaker(bind=self.engine, expire_on_commit=False)

    def migrate(self) -> None:
        config = Config()
        script_location = Path(__file__).resolve().parent / "alembic"
        config.set_main_option("script_location", str(script_location))
        config.set_main_option("sqlalchemy.url", f"sqlite:///{self.path.as_posix()}")
        command.upgrade(config, "head")

    @contextmanager
    def session(self) -> Iterator[Session]:
        database_session = self._sessions()
        try:
            yield database_session
            database_session.commit()
        except Exception:
            database_session.rollback()
            raise
        finally:
            database_session.close()

    def sync_scenarios(self, scenarios: list[dict[str, Any]], *, synced_at: str) -> None:
        """Mirror immutable catalog references before training writes are accepted."""

        with self.session() as database_session:
            for item in scenarios:
                row = database_session.get(ScenarioRow, item["scenarioId"])
                accuracy_mode = "CERTIFIED" if item["trainerEligible"] else "REFERENCE_MODEL"
                payload = json.dumps(item, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
                if row is None:
                    row = ScenarioRow(scenario_id=item["scenarioId"])
                    database_session.add(row)
                row.solution_id = item["solutionId"]
                row.solution_version = item["solutionVersion"]
                row.root_node_id = item["rootNodeId"]
                row.title = item["title"]
                row.trainer_eligible = int(item["trainerEligible"])
                row.accuracy_mode = accuracy_mode
                row.metadata_json = payload
                row.synced_at = synced_at

    def dispose(self) -> None:
        self.engine.dispose()


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def parse_json(value: str | None, default: Any = None) -> Any:
    return default if value is None else json.loads(value)


def _configure_sqlite(dbapi_connection: Any, _: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()
