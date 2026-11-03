"""Reusable artifact metadata, contextual reference bindings, and lineage."""
from alembic import context, op
import sqlalchemy as sa

revision = "a42d7e90c681"
down_revision = "8f31c2d9a670"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("artifacts") as batch:
        for column in ("story_id", "scene_id", "execution_id"):
            batch.alter_column(column, existing_type=sa.String(36), nullable=True)
        batch.alter_column("external_reference", existing_type=sa.String(255), nullable=True)
        batch.add_column(sa.Column("display_name", sa.String(255), nullable=True))
        batch.create_check_constraint("ck_artifact_source", "source IN ('generated','uploaded','external')")
    op.create_table(
        "reference_bindings",
        sa.Column("reference_id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("story_id", sa.String(36), sa.ForeignKey("stories.story_id"), nullable=False),
        sa.Column("artifact_id", sa.String(36), sa.ForeignKey("artifacts.artifact_id"), nullable=False),
        sa.Column("target_type", sa.String(30), nullable=False),
        sa.Column("target_id", sa.String(36), nullable=False),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("story_id", "artifact_id", "target_type", "target_id", "role", name="uq_reference_binding_target"),
        sa.CheckConstraint("target_type IN ('story','character','place')", name="ck_reference_binding_target"),
        sa.CheckConstraint("role IN ('character_identity','outfit','place','visual_style','general')", name="ck_reference_binding_role"),
    )
    op.create_table(
        "artifact_relations",
        sa.Column("relation_id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("parent_artifact_id", sa.String(36), sa.ForeignKey("artifacts.artifact_id"), nullable=False),
        sa.Column("child_artifact_id", sa.String(36), sa.ForeignKey("artifacts.artifact_id"), nullable=False),
        sa.Column("relation_type", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("parent_artifact_id", "child_artifact_id", "relation_type", name="uq_artifact_relation_edge"),
        sa.CheckConstraint("parent_artifact_id <> child_artifact_id", name="ck_artifact_relation_not_self"),
        sa.CheckConstraint("relation_type IN ('derived_from','reference_input')", name="ck_artifact_relation_type"),
    )
    for table, columns in (
        ("reference_bindings", ("user_id", "story_id", "artifact_id")),
        ("artifact_relations", ("user_id", "parent_artifact_id", "child_artifact_id")),
    ):
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade() -> None:
    if not context.is_offline_mode():
        incompatible = op.get_bind().scalar(sa.text(
            "SELECT COUNT(*) FROM artifacts WHERE source <> 'generated' OR story_id IS NULL "
            "OR scene_id IS NULL OR execution_id IS NULL OR external_reference IS NULL"
        ))
        if incompatible:
            raise RuntimeError("Export or migrate registered artifacts before downgrading to the execution-only artifact schema")
    op.drop_table("artifact_relations")
    op.drop_table("reference_bindings")
    with op.batch_alter_table("artifacts") as batch:
        batch.drop_constraint("ck_artifact_source", type_="check")
        batch.drop_column("display_name")
        for column in ("story_id", "scene_id", "execution_id"):
            batch.alter_column(column, existing_type=sa.String(36), nullable=False)
        batch.alter_column("external_reference", existing_type=sa.String(255), nullable=False)
