"""Persist Story language and creative genre metadata."""
from alembic import op
import sqlalchemy as sa

revision = "7c2e91a4b830"
down_revision = "f15d7b92a640"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("stories", sa.Column("language", sa.String(16), nullable=True))
    op.add_column("stories", sa.Column("primary_genre", sa.String(30), nullable=True))
    op.add_column("stories", sa.Column("secondary_genres", sa.JSON(), nullable=False, server_default="[]"))


def downgrade():
    op.drop_column("stories", "secondary_genres")
    op.drop_column("stories", "primary_genre")
    op.drop_column("stories", "language")
