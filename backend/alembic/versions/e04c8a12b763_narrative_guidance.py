"""Optional Story narrative profile and private feedback summary."""
from alembic import op
import sqlalchemy as sa

revision = "e04c8a12b763"
down_revision = "d93b71c602fa"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("narrative_guidance_profiles",
        sa.Column("story_id", sa.String(36), sa.ForeignKey("stories.story_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("audience", sa.String(20), nullable=False),
        sa.Column("maturity_rating", sa.String(20), nullable=False),
        sa.Column("tone", sa.String(255)),
        sa.Column("genre", sa.String(255)),
        sa.Column("guidance_notes", sa.Text()),
        sa.Column("average_rating", sa.Float()),
        sa.Column("rating_count", sa.Integer(), nullable=False),
        sa.Column("feedback_tags", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("audience IN ('child','teen','adult')", name="ck_guidance_audience"),
        sa.CheckConstraint("maturity_rating IN ('general','mild','moderate','mature')", name="ck_guidance_maturity"),
        sa.CheckConstraint("(audience != 'child' OR maturity_rating IN ('general','mild')) AND (audience != 'teen' OR maturity_rating != 'mature')", name="ck_guidance_compatibility"),
        sa.CheckConstraint("rating_count >= 0 AND (average_rating IS NULL OR (average_rating >= 1 AND average_rating <= 5))", name="ck_guidance_feedback_range"),
        sa.CheckConstraint("(rating_count = 0 AND average_rating IS NULL) OR (rating_count > 0 AND average_rating IS NOT NULL)", name="ck_guidance_feedback_summary"))


def downgrade():
    op.drop_table("narrative_guidance_profiles")
