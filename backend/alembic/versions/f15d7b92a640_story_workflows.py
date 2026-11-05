"""Pinned Story workflow configuration; no billing or workflow runs."""
from alembic import op
import sqlalchemy as sa

revision = "f15d7b92a640"
down_revision = "e04c8a12b763"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("story_workflows",
        sa.Column("story_id", sa.String(36), sa.ForeignKey("stories.story_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("workflow_template_id", sa.String(100), nullable=False),
        sa.Column("template_version", sa.Integer(), nullable=False),
        sa.Column("difficulty", sa.String(20), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("difficulty IN ('easy','normal','difficult','impossible')", name="ck_workflow_difficulty"),
        sa.CheckConstraint("template_version >= 1", name="ck_workflow_template_version"))


def downgrade():
    op.drop_table("story_workflows")
