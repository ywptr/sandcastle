"""Optional durable Universe scope using existing Canon identities and versions."""
from alembic import op
import sqlalchemy as sa

revision = "d93b71c602fa"
down_revision = "c81f24a709de"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("universes",
        sa.Column("universe_id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_universes_user_id", "universes", ["user_id"])
    op.create_table("universe_story_memberships",
        sa.Column("story_id", sa.String(36), sa.ForeignKey("stories.story_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("universe_id", sa.String(36), sa.ForeignKey("universes.universe_id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_universe_story_memberships_universe_id", "universe_story_memberships", ["universe_id"])
    op.create_table("universe_canon_references",
        sa.Column("reference_id", sa.String(36), primary_key=True),
        sa.Column("universe_id", sa.String(36), sa.ForeignKey("universes.universe_id"), nullable=False),
        sa.Column("canon_object_id", sa.String(36), sa.ForeignKey("canon_objects.canon_object_id"), nullable=False),
        sa.Column("canon_version_id", sa.String(36), sa.ForeignKey("canon_object_versions.canon_version_id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("universe_id", "canon_object_id", name="uq_universe_canon_object"))
    op.create_index("ix_universe_canon_references_universe_id", "universe_canon_references", ["universe_id"])


def downgrade():
    if not op.get_context().as_sql and op.get_bind().scalar(sa.text("SELECT count(*) FROM universes")):
        raise RuntimeError("Export and explicitly remove Universes before downgrade")
    op.drop_table("universe_canon_references")
    op.drop_table("universe_story_memberships")
    op.drop_table("universes")
