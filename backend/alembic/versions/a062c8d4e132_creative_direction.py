"""SC#0004 append-only approved Creative Direction snapshots."""
from alembic import op
import sqlalchemy as sa
revision = "a062c8d4e132"
down_revision = "9e51b7c3d021"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("creative_direction_snapshots",
        sa.Column("direction_id",sa.String(36),primary_key=True),
        sa.Column("story_id",sa.String(36),sa.ForeignKey("stories.story_id"),nullable=False),
        sa.Column("user_id",sa.String(255),nullable=False),
        sa.Column("revision",sa.Integer(),nullable=False),
        sa.Column("direction_json",sa.JSON(),nullable=False),
        sa.Column("style_snapshot",sa.JSON(),nullable=False),
        sa.Column("approved_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("story_id","revision",name="uq_direction_story_revision"))
    op.create_index("ix_creative_direction_snapshots_story_id","creative_direction_snapshots",["story_id"])
    op.create_index("ix_creative_direction_snapshots_user_id","creative_direction_snapshots",["user_id"])


def downgrade():
    op.drop_table("creative_direction_snapshots")
