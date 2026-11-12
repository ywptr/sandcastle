"""C2 language provenance; existing language values and approvals remain unchanged."""
from alembic import op
import sqlalchemy as sa
revision = "b174d9e5f243"
down_revision = "a062c8d4e132"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("stories", sa.Column("language_provenance", sa.JSON(), nullable=True))
    op.add_column("story_actions", sa.Column("language_context", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("story_actions", "language_context")
    op.drop_column("stories", "language_provenance")
