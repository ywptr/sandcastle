"""SC#0000 encrypted user provider credentials and semantic role bindings."""
from alembic import op
import sqlalchemy as sa

revision = "8d40f6a2c910"
down_revision = "7c2e91a4b830"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("llm_provider_configs",
        sa.Column("provider_config_id", sa.String(36), primary_key=True),
        sa.Column("scope_type", sa.String(20), nullable=False),
        sa.Column("scope_id", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("encrypted_credentials", sa.Text(), nullable=True),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("scope_type", "scope_id", "provider", name="uq_llm_provider_scope"),
        sa.CheckConstraint("scope_type = 'user'", name="ck_llm_provider_scope"),
        sa.CheckConstraint("provider IN ('openai','anthropic','google')", name="ck_llm_provider_id"))
    op.create_table("llm_role_bindings",
        sa.Column("scope_type", sa.String(20), primary_key=True),
        sa.Column("scope_id", sa.String(255), primary_key=True),
        sa.Column("role", sa.String(40), primary_key=True),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("model", sa.String(160), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("scope_type = 'user'", name="ck_llm_role_scope"),
        sa.CheckConstraint("role IN ('creative_writer','story_importer')", name="ck_llm_role_id"),
        sa.CheckConstraint("provider IN ('openai','anthropic','google')", name="ck_llm_role_provider"))


def downgrade():
    op.drop_table("llm_role_bindings")
    op.drop_table("llm_provider_configs")
