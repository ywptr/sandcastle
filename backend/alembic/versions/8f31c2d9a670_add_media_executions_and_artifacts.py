"""Persist approved panel execution snapshots and external artifact references."""
from alembic import op
import sqlalchemy as sa

revision = "8f31c2d9a670"
down_revision = "6b2c8f10a4d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "media_executions",
        sa.Column("execution_id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("story_id", sa.String(36), sa.ForeignKey("stories.story_id"), nullable=False),
        sa.Column("scene_id", sa.String(36), sa.ForeignKey("scenes.scene_id"), nullable=False),
        sa.Column("storyboard_plan_id", sa.String(255), nullable=False),
        sa.Column("media_request_id", sa.String(255), nullable=False),
        sa.Column("panel_number", sa.Integer(), nullable=False),
        sa.Column("backend_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("external_execution_id", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("plan_digest", sa.String(64), nullable=False),
        sa.Column("request_snapshot", sa.JSON(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "storyboard_plan_id", "panel_number", name="uq_media_execution_plan_panel"),
        sa.CheckConstraint("panel_number BETWEEN 1 AND 4", name="ck_media_execution_panel"),
        sa.CheckConstraint("status IN ('pending','submitted','running','completed','failed')", name="ck_media_execution_status"),
    )
    op.create_table(
        "artifacts",
        sa.Column("artifact_id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("story_id", sa.String(36), sa.ForeignKey("stories.story_id"), nullable=False),
        sa.Column("scene_id", sa.String(36), sa.ForeignKey("scenes.scene_id"), nullable=False),
        sa.Column("execution_id", sa.String(36), sa.ForeignKey("media_executions.execution_id"), nullable=False),
        sa.Column("media_type", sa.String(30), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("external_reference", sa.String(255), nullable=False),
        sa.Column("external_artifact_id", sa.String(255), nullable=True),
        sa.Column("retrieval_reference", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(255), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("execution_id", "external_reference", name="uq_artifact_execution_reference"),
    )
    for table, columns in (
        ("media_executions", ("user_id", "story_id", "scene_id")),
        ("artifacts", ("user_id", "story_id", "scene_id", "execution_id")),
    ):
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade() -> None:
    op.drop_table("artifacts")
    op.drop_table("media_executions")
