"""Reusable Canon snapshots with explicit Story pins; existing data stays in place."""
from alembic import op
import sqlalchemy as sa

revision = "c81f24a709de"
down_revision = "b7e193d2c540"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("canon_objects",
        sa.Column("canon_object_id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("object_type", sa.String(30), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("object_type IN ('character','place')", name="ck_canon_object_type"))
    op.create_index("ix_canon_objects_user_id", "canon_objects", ["user_id"])
    op.create_table("canon_object_versions",
        sa.Column("canon_version_id", sa.String(36), primary_key=True),
        sa.Column("canon_object_id", sa.String(36), sa.ForeignKey("canon_objects.canon_object_id"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("parent_version_id", sa.String(36), sa.ForeignKey("canon_object_versions.canon_version_id")),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_by_story_id", sa.String(36), sa.ForeignKey("stories.story_id")),
        sa.Column("fork_reason", sa.String(1000)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("canon_object_id", "version_number", name="uq_canon_object_version"))
    op.create_index("ix_canon_object_versions_canon_object_id", "canon_object_versions", ["canon_object_id"])
    op.create_table("story_canon_references",
        sa.Column("reference_id", sa.String(36), primary_key=True),
        sa.Column("story_id", sa.String(36), sa.ForeignKey("stories.story_id"), nullable=False),
        sa.Column("canon_object_id", sa.String(36), sa.ForeignKey("canon_objects.canon_object_id"), nullable=False),
        sa.Column("canon_version_id", sa.String(36), sa.ForeignKey("canon_object_versions.canon_version_id"), nullable=False),
        sa.Column("target_type", sa.String(30), nullable=False),
        sa.Column("target_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("story_id", "target_type", "target_id", name="uq_story_canon_target"))
    op.create_index("ix_story_canon_references_story_id", "story_canon_references", ["story_id"])


def downgrade():
    # Never silently discard library history or effective Story facts.
    if not op.get_context().as_sql:
        count = op.get_bind().scalar(sa.text("SELECT count(*) FROM canon_objects"))
        if count:
            raise RuntimeError("Export and explicitly remove Canon library objects before downgrade")
    op.drop_table("story_canon_references")
    op.drop_table("canon_object_versions")
    op.drop_table("canon_objects")
