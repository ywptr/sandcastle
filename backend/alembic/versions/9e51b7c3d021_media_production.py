"""SC#0001 immutable production approvals and narrative translation role."""
from alembic import op
import sqlalchemy as sa
revision = "9e51b7c3d021"
down_revision = "8d40f6a2c910"
branch_labels = None
depends_on = None


def upgrade():
    # Batch also supports SQLite regression fixtures without editing historical revisions.
    with op.batch_alter_table("llm_role_bindings") as batch:
        batch.drop_constraint("ck_llm_role_id", type_="check")
        batch.create_check_constraint("ck_llm_role_id", "role IN ('creative_writer','story_importer','narrative_media_translator')")
    op.create_table("approved_media_adaptations",
        sa.Column("adaptation_id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("story_id", sa.String(36), sa.ForeignKey("stories.story_id"), nullable=False),
        sa.Column("scene_id", sa.String(36), sa.ForeignKey("scenes.scene_id"), nullable=False),
        sa.Column("target_format", sa.String(20), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.String(36), nullable=False),
        sa.Column("source_digest", sa.String(64), nullable=False),
        sa.Column("context_digest", sa.String(64), nullable=False),
        sa.Column("snapshot_digest", sa.String(64), nullable=False),
        sa.Column("plan_json", sa.JSON(), nullable=False),
        sa.Column("manifest_json", sa.JSON(), nullable=False),
        sa.Column("compiler_version", sa.String(40), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("scene_id", "target_format", "revision", name="uq_adaptation_scene_revision"),
        sa.UniqueConstraint("user_id", "plan_id", "snapshot_digest", name="uq_adaptation_approval"),
        sa.CheckConstraint("target_format IN ('webtoon','short_drama','story_reel')", name="ck_adaptation_format"),
        sa.CheckConstraint("revision >= 1", name="ck_adaptation_revision"))
    for field in ("user_id", "story_id", "scene_id"):
        op.create_index(f"ix_approved_media_adaptations_{field}", "approved_media_adaptations", [field])


def downgrade():
    # Do not silently lose new role preferences when downgrading operational databases.
    if op.get_context().as_sql:
        op.execute("DO $$ BEGIN IF EXISTS (SELECT 1 FROM llm_role_bindings WHERE role = 'narrative_media_translator') THEN RAISE EXCEPTION 'Remove narrative media translator role bindings before downgrade'; END IF; END $$")
    else:
        count = op.get_bind().scalar(sa.text("SELECT count(*) FROM llm_role_bindings WHERE role='narrative_media_translator'"))
        if count:
            raise RuntimeError("Remove narrative media translator role bindings explicitly before downgrade")
    op.drop_table("approved_media_adaptations")
    with op.batch_alter_table("llm_role_bindings") as batch:
        batch.drop_constraint("ck_llm_role_id", type_="check")
        batch.create_check_constraint("ck_llm_role_id", "role IN ('creative_writer','story_importer')")
