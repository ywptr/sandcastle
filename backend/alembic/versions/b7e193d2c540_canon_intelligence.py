"""Create reviewable Canon proposals and minimally scope existing Canon facts."""
from alembic import op
import sqlalchemy as sa

revision = "b7e193d2c540"
down_revision = "a42d7e90c681"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("canon_entries", sa.Column("subject_id", sa.String(36), nullable=True))
    op.add_column("canon_entries", sa.Column("fact_type", sa.String(50), nullable=True))
    # The old e5a5b285762e revision was empty. Do not rewrite its history.
    op.create_table(
        "canon_candidates",
        sa.Column("canon_candidate_id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("story_id", sa.String(36), sa.ForeignKey("stories.story_id"), nullable=False),
        sa.Column("scene_id", sa.String(36), sa.ForeignKey("scenes.scene_id"), nullable=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("subject_id", sa.String(36), nullable=True),
        sa.Column("subject_name", sa.String(255), nullable=True),
        sa.Column("fact_type", sa.String(50), nullable=False),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("source_kind", sa.String(30), nullable=False),
        sa.Column("source_snapshot", sa.Text(), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("dedup_key", sa.String(64), nullable=False),
        sa.Column("extraction_data", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("classification", sa.String(30), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("comparison_snapshot", sa.JSON(), nullable=False),
        sa.Column("superseded_entry_ids", sa.JSON(), nullable=False),
        sa.Column("approved_canon_entry_id", sa.String(36), sa.ForeignKey("canon_entries.canon_entry_id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.UniqueConstraint("user_id", "story_id", "dedup_key", name="uq_canon_candidate_source_fact"),
        sa.CheckConstraint("status IN ('pending','approved','rejected')", name="ck_canon_candidate_status"),
        sa.CheckConstraint("classification IN ('new','consistent','conflict','uncertain')", name="ck_canon_candidate_classification"),
        sa.CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_canon_candidate_confidence"),
    )
    for column in ("user_id", "story_id", "scene_id", "status", "classification", "approved_canon_entry_id"):
        op.create_index(f"ix_canon_candidates_{column}", "canon_candidates", [column])


def downgrade() -> None:
    op.drop_table("canon_candidates")
    with op.batch_alter_table("canon_entries") as batch:
        batch.drop_column("fact_type")
        batch.drop_column("subject_id")
