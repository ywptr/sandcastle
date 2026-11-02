"""Create structured characters and places.

Revision ID: 6b2c8f10a4d9
Revises: e5a5b285762e
"""
from alembic import op
import sqlalchemy as sa

revision = "6b2c8f10a4d9"
down_revision = "e5a5b285762e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table, id_column, fields in (
        ("characters", "character_id", ("description", "appearance", "outfit", "personality")),
        ("places", "place_id", ("description", "appearance", "atmosphere")),
    ):
        op.create_table(
            table,
            sa.Column(id_column, sa.String(36), primary_key=True),
            sa.Column("story_id", sa.String(36), sa.ForeignKey("stories.story_id"), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            *(sa.Column(field, sa.Text(), nullable=False) for field in fields),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(f"ix_{table}_story_id", table, ["story_id"])


def downgrade() -> None:
    for table in ("places", "characters"):
        op.drop_index(f"ix_{table}_story_id", table_name=table)
        op.drop_table(table)
