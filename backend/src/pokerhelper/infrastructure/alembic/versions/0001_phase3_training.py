"""Create scenario catalog and immutable Phase 3 training records."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_phase3_training"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scenarios",
        sa.Column("scenario_id", sa.String(160), primary_key=True),
        sa.Column("solution_id", sa.String(96), nullable=False),
        sa.Column("solution_version", sa.String(160), nullable=False),
        sa.Column("root_node_id", sa.String(32), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("trainer_eligible", sa.Integer(), nullable=False),
        sa.Column("accuracy_mode", sa.String(32), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("synced_at", sa.String(40), nullable=False),
    )
    op.create_table(
        "training_sessions",
        sa.Column("session_id", sa.String(80), primary_key=True),
        sa.Column("schema_version", sa.String(16), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("scenario_id", sa.String(160), sa.ForeignKey("scenarios.scenario_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("solution_id", sa.String(96), nullable=False),
        sa.Column("solution_version", sa.String(160), nullable=False),
        sa.Column("selected_node_ids_json", sa.Text(), nullable=False),
        sa.Column("hero_positions_json", sa.Text(), nullable=False),
        sa.Column("target_decisions", sa.Integer(), nullable=False),
        sa.Column("feedback_mode", sa.String(20), nullable=False),
        sa.Column("scoring_policy_version", sa.String(16), nullable=False),
        sa.Column("sampling_policy_version", sa.String(64), nullable=False),
        sa.Column("accuracy_mode", sa.String(32), nullable=False),
        sa.Column("approximate_acknowledged_at", sa.String(40)),
        sa.Column("rng_enabled", sa.Integer(), nullable=False),
        sa.Column("drill_type", sa.String(32), nullable=False),
        sa.Column("source_session_id", sa.String(80), sa.ForeignKey("training_sessions.session_id", ondelete="SET NULL")),
        sa.Column("drill_items_json", sa.Text(), nullable=False),
        sa.Column("pending_prompt_json", sa.Text()),
        sa.Column("started_at", sa.String(40), nullable=False),
        sa.Column("completed_at", sa.String(40)),
        sa.Column("summary_json", sa.Text(), nullable=False),
    )
    op.create_index("ix_training_sessions_started", "training_sessions", ["started_at"])
    op.create_index("ix_training_sessions_scenario", "training_sessions", ["scenario_id"])
    op.create_table(
        "training_decisions",
        sa.Column("decision_id", sa.String(80), primary_key=True),
        sa.Column("prompt_id", sa.String(80), nullable=False, unique=True),
        sa.Column("session_id", sa.String(80), sa.ForeignKey("training_sessions.session_id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("scenario_id", sa.String(160), nullable=False),
        sa.Column("game_config_id", sa.String(96), nullable=False),
        sa.Column("solution_id", sa.String(96), nullable=False),
        sa.Column("solution_version", sa.String(160), nullable=False),
        sa.Column("node_id", sa.String(32), nullable=False),
        sa.Column("hero_position", sa.String(8), nullable=False),
        sa.Column("action_history_key", sa.Text(), nullable=False),
        sa.Column("hero_combo", sa.String(4), nullable=False),
        sa.Column("grouped_hand", sa.String(3), nullable=False),
        sa.Column("offered_options_json", sa.Text(), nullable=False),
        sa.Column("selected_option_id", sa.String(80), nullable=False),
        sa.Column("selected_resolved_action_json", sa.Text(), nullable=False),
        sa.Column("combo_reach_weight", sa.String(80), nullable=False),
        sa.Column("reference_snapshot_json", sa.Text(), nullable=False),
        sa.Column("highest_ev_option_id", sa.String(80), nullable=False),
        sa.Column("ev_loss_bb", sa.String(80), nullable=False),
        sa.Column("feedback_severity", sa.String(32), nullable=False),
        sa.Column("strategy_status", sa.String(32), nullable=False),
        sa.Column("scoring_policy_version", sa.String(16), nullable=False),
        sa.Column("accuracy_mode", sa.String(32), nullable=False),
        sa.Column("rng_roll", sa.Integer()),
        sa.Column("rng_mapping_json", sa.Text()),
        sa.Column("presented_at", sa.String(40), nullable=False),
        sa.Column("answered_at", sa.String(40), nullable=False),
        sa.Column("interpretation", sa.Text(), nullable=False),
        sa.UniqueConstraint("session_id", "sequence", name="uq_training_decision_sequence"),
    )
    op.create_index("ix_training_decisions_session", "training_decisions", ["session_id"])
    op.create_index("ix_training_decisions_review", "training_decisions", ["feedback_severity", "ev_loss_bb"])
    op.create_index("ix_training_decisions_calibration", "training_decisions", ["solution_id", "node_id", "grouped_hand"])

    if op.get_bind().dialect.name == "sqlite":
        op.execute(
            "CREATE TRIGGER training_decisions_immutable "
            "BEFORE UPDATE ON training_decisions BEGIN "
            "SELECT RAISE(ABORT, 'training decisions are immutable'); END"
        )
        op.execute(
            "CREATE TRIGGER completed_sessions_immutable "
            "BEFORE UPDATE ON training_sessions WHEN OLD.status <> 'ACTIVE' AND ("
            "NEW.session_id IS NOT OLD.session_id OR "
            "NEW.schema_version IS NOT OLD.schema_version OR "
            "NEW.status IS NOT OLD.status OR "
            "NEW.scenario_id IS NOT OLD.scenario_id OR "
            "NEW.solution_id IS NOT OLD.solution_id OR "
            "NEW.solution_version IS NOT OLD.solution_version OR "
            "NEW.selected_node_ids_json IS NOT OLD.selected_node_ids_json OR "
            "NEW.hero_positions_json IS NOT OLD.hero_positions_json OR "
            "NEW.target_decisions IS NOT OLD.target_decisions OR "
            "NEW.feedback_mode IS NOT OLD.feedback_mode OR "
            "NEW.scoring_policy_version IS NOT OLD.scoring_policy_version OR "
            "NEW.sampling_policy_version IS NOT OLD.sampling_policy_version OR "
            "NEW.accuracy_mode IS NOT OLD.accuracy_mode OR "
            "NEW.approximate_acknowledged_at IS NOT OLD.approximate_acknowledged_at OR "
            "NEW.rng_enabled IS NOT OLD.rng_enabled OR "
            "NEW.drill_type IS NOT OLD.drill_type OR "
            "NEW.drill_items_json IS NOT OLD.drill_items_json OR "
            "NEW.pending_prompt_json IS NOT OLD.pending_prompt_json OR "
            "NEW.started_at IS NOT OLD.started_at OR "
            "NEW.completed_at IS NOT OLD.completed_at OR "
            "NEW.summary_json IS NOT OLD.summary_json OR "
            "NEW.source_session_id IS NOT NULL"
            ") BEGIN "
            "SELECT RAISE(ABORT, 'completed training sessions are immutable'); END"
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS completed_sessions_immutable")
        op.execute("DROP TRIGGER IF EXISTS training_decisions_immutable")
    op.drop_index("ix_training_decisions_calibration", table_name="training_decisions")
    op.drop_index("ix_training_decisions_review", table_name="training_decisions")
    op.drop_index("ix_training_decisions_session", table_name="training_decisions")
    op.drop_table("training_decisions")
    op.drop_index("ix_training_sessions_scenario", table_name="training_sessions")
    op.drop_index("ix_training_sessions_started", table_name="training_sessions")
    op.drop_table("training_sessions")
    op.drop_table("scenarios")
