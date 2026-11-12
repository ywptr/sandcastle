"""Validate the new revision without connecting to any configured deployment."""
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select

from app.db.database import Base
from app.db.models import Story

BACKEND = Path(__file__).resolve().parents[1]


def config(output=None):
    cfg = Config(str(BACKEND / "alembic.ini"), output_buffer=output)
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    return cfg


def create_historical_baseline(engine, tables):
    # Current metadata includes M7 columns; older baselines must not pre-create them.
    Base.metadata.create_all(engine, tables=[table for table in tables if table.name not in {"canon_candidates", "canon_objects", "canon_object_versions", "story_canon_references", "universes", "universe_story_memberships", "universe_canon_references", "narrative_guidance_profiles", "story_workflows", "llm_provider_configs", "llm_role_bindings", "approved_media_adaptations", "creative_direction_snapshots"}])
    with engine.begin() as connection:
        columns = {column["name"] for column in inspect(connection).get_columns("canon_entries")}
        for name in ("subject_id", "fact_type"):
            if name in columns:
                connection.exec_driver_sql(f"ALTER TABLE canon_entries DROP COLUMN {name}")


def strip_language_provenance(engine):
    assert engine.dialect.name == "sqlite"
    with engine.begin() as connection:
        for table, column in [("stories", "language_provenance"), ("story_actions", "language_context")]:
            if table in inspect(connection).get_table_names() and column in {item["name"] for item in inspect(connection).get_columns(table)}:
                connection.exec_driver_sql(f"ALTER TABLE {table} DROP COLUMN {column}")


def upgrade_fixture_to_head():
    # Historical fixtures use current metadata; remove synthetic M13 columns
    # before exercising the real migration. No production connection is used.
    engine = create_engine(os.environ["DATABASE_URL"])
    assert engine.dialect.name == "sqlite", "Historical fixture helper is SQLite-only"
    with engine.begin() as connection:
        columns = {column["name"] for column in inspect(connection).get_columns("stories")}
        for name in ("language", "primary_genre", "secondary_genres"):
            if name in columns:
                connection.exec_driver_sql(f"ALTER TABLE stories DROP COLUMN {name}")
    engine.dispose()
    strip_language_provenance(engine)
    command.upgrade(config(), "head")


class MigrationTests(unittest.TestCase):
    def test_postgres_full_history_sql(self):
        output = io.StringIO()
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql+psycopg://audit:audit@localhost/audit"}):
            command.upgrade(config(output), "head", sql=True)
        sql = output.getvalue()
        self.assertIn("CREATE TABLE characters", sql)
        self.assertIn("CREATE TABLE places", sql)
        self.assertIn("CREATE TABLE media_executions", sql)
        self.assertIn("CREATE TABLE artifacts", sql)
        self.assertIn("CREATE TABLE reference_bindings", sql)
        self.assertIn("CREATE TABLE artifact_relations", sql)
        self.assertIn("CREATE TABLE canon_candidates", sql)
        self.assertIn("CREATE TABLE canon_objects", sql)
        self.assertIn("CREATE TABLE canon_object_versions", sql)
        self.assertIn("CREATE TABLE story_canon_references", sql)
        self.assertIn("CREATE TABLE universes", sql)
        self.assertIn("CREATE TABLE narrative_guidance_profiles", sql)
        self.assertIn("CREATE TABLE story_workflows", sql)
        self.assertIn("CREATE TABLE universe_canon_references", sql)
        self.assertIn("b7e193d2c540", sql)
        self.assertIn("a42d7e90c681", sql)
        self.assertIn("8f31c2d9a670", sql)
        self.assertIn("FOREIGN KEY(story_id) REFERENCES stories (story_id)", sql)
        self.assertIn("ix_characters_story_id", sql)
        self.assertIn("uq_scene_story_sequence", sql)
        self.assertIn("6b2c8f10a4d9", sql)

    def test_new_revision_upgrade_check_downgrade_preserves_story(self):
        with tempfile.TemporaryDirectory(prefix="sandcastle-migrations-") as directory:
            url = "sqlite:///" + str(Path(directory) / "migration.db")
            engine = create_engine(url)
            legacy = [table for table in Base.metadata.sorted_tables if table.name not in {"characters", "places", "media_executions", "artifacts", "reference_bindings", "artifact_relations"}]
            create_historical_baseline(engine, legacy)
            with engine.begin() as connection:
                connection.execute(Story.__table__.insert().values(story_id="existing", user_id="alice", title="Preserved"))
            with patch.dict(os.environ, {"DATABASE_URL": url}):
                command.stamp(config(), "e5a5b285762e")
                upgrade_fixture_to_head()
                self.assertIn("characters", inspect(engine).get_table_names())
                self.assertIn("places", inspect(engine).get_table_names())
                self.assertEqual(inspect(engine).get_foreign_keys("characters")[0]["referred_table"], "stories")
                command.check(config())
                command.downgrade(config(), "e5a5b285762e")
                self.assertNotIn("characters", inspect(engine).get_table_names())
                self.assertNotIn("places", inspect(engine).get_table_names())
            with engine.connect() as connection:
                self.assertEqual(connection.scalar(select(Story.title).where(Story.story_id == "existing")), "Preserved")
            engine.dispose()


    def test_execution_migration_round_trip_and_model_match(self):
        with tempfile.TemporaryDirectory(prefix="sandcastle-execution-migration-") as directory:
            url = "sqlite:///" + str(Path(directory) / "migration.db")
            engine = create_engine(url)
            baseline = [table for table in Base.metadata.sorted_tables
                        if table.name not in {"media_executions", "artifacts", "reference_bindings", "artifact_relations"}]
            create_historical_baseline(engine, baseline)
            with patch.dict(os.environ, {"DATABASE_URL": url}):
                command.stamp(config(), "6b2c8f10a4d9")
                upgrade_fixture_to_head()
                tables = inspect(engine).get_table_names()
                self.assertIn("media_executions", tables)
                self.assertIn("artifacts", tables)
                fks = inspect(engine).get_foreign_keys("artifacts")
                self.assertIn("media_executions", [fk["referred_table"] for fk in fks])
                command.check(config())
                command.downgrade(config(), "6b2c8f10a4d9")
                self.assertNotIn("media_executions", inspect(engine).get_table_names())
                self.assertNotIn("artifacts", inspect(engine).get_table_names())
                self.assertIn("characters", inspect(engine).get_table_names())
            engine.dispose()


    def test_reference_migration_preserves_generated_artifacts_and_guards_registered_data(self):
        from sqlalchemy.orm import Session
        from app.db.models import Artifact, MediaExecution, Scene
        from app.artifacts.schemas import ArtifactRegistration, ReferenceBindingCreate
        from app.artifacts.service import create_binding, delete_binding, register_artifact

        with tempfile.TemporaryDirectory(prefix="sandcastle-reference-migration-") as directory:
            url = "sqlite:///" + str(Path(directory) / "migration.db")
            engine = create_engine(url)
            baseline = [table for table in Base.metadata.sorted_tables if table.name not in
                        {"media_executions", "artifacts", "reference_bindings", "artifact_relations"}]
            create_historical_baseline(engine, baseline)
            with patch.dict(os.environ, {"DATABASE_URL": url}):
                command.stamp(config(), "6b2c8f10a4d9")
                command.upgrade(config(), "8f31c2d9a670")
                with engine.begin() as connection:
                    connection.execute(Story.__table__.insert().values(story_id="story", user_id="alice", title="Preserved"))
                    connection.execute(Scene.__table__.insert().values(scene_id="scene", story_id="story", sequence_number=1, content="Saved prose"))
                    connection.execute(MediaExecution.__table__.insert().values(
                        execution_id="execution", user_id="alice", story_id="story", scene_id="scene",
                        storyboard_plan_id="plan", media_request_id="request", panel_number=1,
                        backend_name="fake", status="completed", plan_digest="a" * 64,
                        request_snapshot={"prompt": "Approved historical prompt"},
                    ))
                    connection.execute(Artifact.__table__.insert().values(
                        artifact_id="generated", user_id="alice", story_id="story", scene_id="scene",
                        execution_id="execution", external_reference="external-image",
                        retrieval_reference="https://media.example.test/image", source="generated", media_type="image",
                    ))
                upgrade_fixture_to_head()
                command.check(config())
                with Session(engine) as db:
                    artifact = db.get(Artifact, "generated")
                    self.assertEqual(artifact.source, "generated")
                    self.assertEqual(artifact.execution_id, "execution")
                    self.assertIsNone(artifact.display_name)
                    self.assertEqual(db.get(MediaExecution, "execution").request_snapshot["prompt"], "Approved historical prompt")
                    registered = register_artifact(db, "alice", ArtifactRegistration(
                        source="external", retrieval_reference="https://media.example.test/reference"))
                    registered_id = registered.artifact_id
                    binding = create_binding(db, "story", "alice", ReferenceBindingCreate(
                        artifact_id=registered_id, target_type="story", role="visual_style"))
                    binding_id = binding.reference_id
                with self.assertRaisesRegex(RuntimeError, "registered artifacts"):
                    command.downgrade(config(), "8f31c2d9a670")
                self.assertIn("reference_bindings", inspect(engine).get_table_names())
                with Session(engine) as db:
                    self.assertIsNotNone(db.get(Artifact, registered_id))
                    # The failed multi-revision downgrade has already removed
                    # M13 columns on SQLite; clean this fixture without current
                    # Story services querying that historical schema.
                    from app.db.models import ReferenceBinding
                    db.delete(db.get(ReferenceBinding, binding_id))
                    db.delete(db.get(Artifact, registered_id))
                    db.commit()
                command.downgrade(config(), "8f31c2d9a670")
                self.assertNotIn("reference_bindings", inspect(engine).get_table_names())
                self.assertNotIn("display_name", [column["name"] for column in inspect(engine).get_columns("artifacts")])
                with engine.connect() as connection:
                    self.assertEqual(connection.scalar(select(Artifact.artifact_id).where(Artifact.artifact_id == "generated")), "generated")
                upgrade_fixture_to_head()
                command.check(config())
            engine.dispose()

    def test_canon_intelligence_migration_preserves_legacy_canon_and_review_history(self):
        from sqlalchemy.orm import Session
        from app.db.models import CanonCandidate, CanonEntry
        from app.canon.candidate_schemas import CandidateApproval, ManualCandidate
        from app.canon.candidate_service import approve_candidate, propose_candidate

        with tempfile.TemporaryDirectory(prefix="sandcastle-canon-migration-") as directory:
            url = "sqlite:///" + str(Path(directory) / "migration.db")
            engine = create_engine(url)
            create_historical_baseline(engine, Base.metadata.sorted_tables)
            with engine.begin() as connection:
                connection.execute(Story.__table__.insert().values(story_id="story", user_id="alice", title="Preserved"))
                connection.execute(CanonEntry.__table__.insert().values(
                    canon_entry_id="legacy", story_id="story", type="world", key="gravity", value="Normal gravity", status="approved"))
            with patch.dict(os.environ, {"DATABASE_URL": url}):
                command.stamp(config(), "a42d7e90c681")
                upgrade_fixture_to_head()
                command.check(config())
                with Session(engine) as db:
                    self.assertIsNone(db.get(CanonEntry, "legacy").subject_id)
                    proposal = propose_candidate(db, story_id="story", user_id="alice", proposal=ManualCandidate(
                        type="world", fact_type="rule", key="gravity", value="Low gravity", evidence="Author changes gravity"))
                    self.assertEqual(proposal.classification, "uncertain")
                    approved = approve_candidate(db, story_id="story", candidate_id=proposal.canon_candidate_id,
                        user_id="alice", approval=CandidateApproval(accept_uncertain=True, replace_conflicts=True))
                    proposal_id = approved.canon_candidate_id
                    replacement_id = approved.approved_canon_entry_id
                with Session(engine) as db:
                    candidate = db.get(CanonCandidate, proposal_id)
                    self.assertEqual(candidate.status, "approved")
                    self.assertEqual(candidate.comparison_snapshot[0]["value"], "Normal gravity")
                    self.assertEqual(db.get(CanonEntry, "legacy").value, "Normal gravity")
                    self.assertEqual(db.get(CanonEntry, "legacy").status, "superseded")
                    self.assertEqual(db.get(CanonEntry, replacement_id).value, "Low gravity")
                command.downgrade(config(), "a42d7e90c681")
                self.assertNotIn("canon_candidates", inspect(engine).get_table_names())
                self.assertNotIn("subject_id", [column["name"] for column in inspect(engine).get_columns("canon_entries")])
                with engine.connect() as connection:
                    self.assertEqual(connection.scalar(select(CanonEntry.value).where(CanonEntry.canon_entry_id == "legacy")), "Normal gravity")
                upgrade_fixture_to_head()
                command.check(config())
            engine.dispose()

    def test_library_migration_preserves_legacy_subjects_candidates_and_visuals(self):
        from sqlalchemy.orm import Session
        from app.db.models import Character, Place, CanonCandidate, ReferenceBinding
        from app.canon.candidate_schemas import ManualCandidate
        from app.canon.candidate_service import propose_candidate
        from app.canon.library_service import promote
        from app.artifacts.service import register_artifact, create_binding
        from app.artifacts.schemas import ArtifactRegistration, ReferenceBindingCreate
        with tempfile.TemporaryDirectory(prefix="sandcastle-library-migration-") as directory:
            url = "sqlite:///" + str(Path(directory) / "migration.db")
            engine = create_engine(url)
            create_historical_baseline(engine, Base.metadata.sorted_tables)
            with patch.dict(os.environ, {"DATABASE_URL": url}):
                command.stamp(config(), "a42d7e90c681")
                command.upgrade(config(), "b7e193d2c540")
                with Session(engine) as db:
                    db.add(Story(story_id="s", user_id="alice", title="Legacy"))
                    db.flush()
                    db.add(Character(character_id="c", story_id="s", name="Mara"))
                    db.add(Place(place_id="p", story_id="s", name="Harbor"))
                    db.commit()
                    candidate = CanonCandidate(user_id="alice", story_id="s", type="character", subject_id="c",
                        fact_type="age", key="age", value="35", evidence="Author", source_kind="manual",
                        source_snapshot="Author", source_hash="a" * 64, dedup_key="b" * 64,
                        extraction_data={"type": "character", "subject_id": "c", "key": "age", "value": "35", "evidence": "Author"},
                        reasoning="Legacy pending fact")
                    db.add(candidate)
                    db.commit()
                    candidate_id = candidate.canon_candidate_id
                    artifact = register_artifact(db, "alice", ArtifactRegistration(source="external", retrieval_reference="https://example.test/image"))
                    binding = create_binding(db, "s", "alice", ReferenceBindingCreate(
                        artifact_id=artifact.artifact_id, target_type="character", target_id="c", role="character_identity"))
                    binding_id = binding.reference_id
                upgrade_fixture_to_head()
                command.check(config())
                with Session(engine) as db:
                    self.assertEqual(db.get(Character, "c").name, "Mara")
                    self.assertEqual(db.get(Place, "p").name, "Harbor")
                    self.assertEqual(db.get(CanonCandidate, candidate_id).subject_id, "c")
                    self.assertEqual(db.get(ReferenceBinding, binding_id).target_id, "c")
                command.downgrade(config(), "b7e193d2c540")
                upgrade_fixture_to_head()
                command.check(config())
                with Session(engine) as db:
                    ref = promote(db, "s", "alice", "character", "c")
                    self.assertEqual(ref.target_id, "c")
                    self.assertEqual(db.get(CanonCandidate, candidate_id).status, "pending")
                with self.assertRaisesRegex(RuntimeError, "Export"):
                    command.downgrade(config(), "b7e193d2c540")
            engine.dispose()

    def test_universe_migration_preserves_prior_milestones_and_round_trips(self):
        from sqlalchemy.orm import Session
        from app.db.models import (Character, Place, Scene, CanonEntry, CanonCandidate, CanonObject,
            CanonObjectVersion, StoryCanonReference, Artifact, ReferenceBinding)
        with tempfile.TemporaryDirectory(prefix="sandcastle-universe-migration-") as directory:
            url = "sqlite:///" + str(Path(directory) / "migration.db")
            engine = create_engine(url)
            new_tables = {"universes", "universe_story_memberships", "universe_canon_references", "narrative_guidance_profiles", "story_workflows", "llm_provider_configs", "llm_role_bindings", "approved_media_adaptations", "creative_direction_snapshots"}
            Base.metadata.create_all(engine, tables=[table for table in Base.metadata.sorted_tables if table.name not in new_tables])
            with Session(engine) as db:
                db.add(Story(story_id="s", user_id="alice", title="Legacy"))
                db.flush()
                db.add(Character(character_id="c", story_id="s", name="Mara"))
                db.add(Place(place_id="p", story_id="s", name="Harbor"))
                db.add(Scene(scene_id="scene", story_id="s", sequence_number=1, content="Preserved prose"))
                db.add(CanonEntry(canon_entry_id="fact", story_id="s", type="character", subject_id="c", key="age", value="35"))
                db.add(CanonCandidate(canon_candidate_id="candidate", user_id="alice", story_id="s", type="character", subject_id="c",
                    fact_type="age", key="age", value="35", evidence="Author", source_kind="manual", source_snapshot="Author",
                    source_hash="a" * 64, dedup_key="b" * 64, extraction_data={}, reasoning="Preserved reasoning"))
                db.add(CanonObject(canon_object_id="object", user_id="alice", object_type="character", name="Mara"))
                db.flush()
                db.add(CanonObjectVersion(canon_version_id="v1", canon_object_id="object", version_number=1,
                    data={"structure": {"name": "Mara"}, "facts": [], "visuals": []}))
                db.add(Artifact(artifact_id="art", user_id="alice", source="external", retrieval_reference="https://example.test/image"))
                db.flush()
                db.add(StoryCanonReference(reference_id="ref", story_id="s", canon_object_id="object", canon_version_id="v1", target_type="character", target_id="c"))
                db.add(ReferenceBinding(reference_id="visual", user_id="alice", story_id="s", artifact_id="art", target_type="character", target_id="c", role="character_identity"))
                db.commit()
            with patch.dict(os.environ, {"DATABASE_URL": url}):
                command.stamp(config(), "c81f24a709de")
                upgrade_fixture_to_head()
                command.check(config())
                with Session(engine) as db:
                    self.assertEqual(db.get(Character, "c").name, "Mara")
                    self.assertEqual(db.get(Place, "p").name, "Harbor")
                    self.assertEqual(db.get(Scene, "scene").content, "Preserved prose")
                    self.assertEqual(db.get(CanonEntry, "fact").value, "35")
                    self.assertEqual(db.get(CanonCandidate, "candidate").reasoning, "Preserved reasoning")
                    self.assertEqual(db.get(StoryCanonReference, "ref").canon_version_id, "v1")
                    self.assertEqual(db.get(ReferenceBinding, "visual").artifact_id, "art")
                    self.assertIsNotNone(db.get(Artifact, "art"))
                command.downgrade(config(), "c81f24a709de")
                self.assertNotIn("universes", inspect(engine).get_table_names())
                upgrade_fixture_to_head()
                command.check(config())
                from app.universes.service import create_universe
                with Session(engine) as db:
                    create_universe(db, "alice", name="Durable")
                with self.assertRaisesRegex(RuntimeError, "Export"):
                    command.downgrade(config(), "c81f24a709de")
            engine.dispose()
        output = io.StringIO()
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql+psycopg://audit:audit@localhost/audit"}):
            command.downgrade(config(output), "d93b71c602fa:c81f24a709de", sql=True)
        self.assertIn("DROP TABLE universe_canon_references", output.getvalue())

    def test_guidance_migration_preserves_legacy_story_and_profile_defaults(self):
        from sqlalchemy.orm import Session
        from app.db.models import Scene, Universe, UniverseStoryMembership, CanonObject, CanonObjectVersion
        from app.guidance.service import get_profile, save_profile
        from app.guidance.schemas import GuidanceProfileInput
        with tempfile.TemporaryDirectory(prefix="sandcastle-guidance-migration-") as directory:
            url = "sqlite:///" + str(Path(directory) / "migration.db")
            engine = create_engine(url)
            Base.metadata.create_all(engine, tables=[table for table in Base.metadata.sorted_tables if table.name not in {"narrative_guidance_profiles", "story_workflows", "llm_provider_configs", "llm_role_bindings", "approved_media_adaptations", "creative_direction_snapshots"}])
            with Session(engine) as db:
                db.add(Story(story_id="legacy", user_id="alice", title="Preserved", premise="A garden", objective="Protect it"))
                db.add(Universe(universe_id="world", user_id="alice", name="World"))
                db.add(CanonObject(canon_object_id="object", user_id="alice", object_type="character", name="Mara"))
                db.flush()
                db.add(Scene(scene_id="scene", story_id="legacy", sequence_number=1, content="Original prose"))
                db.add(UniverseStoryMembership(story_id="legacy", universe_id="world"))
                db.add(CanonObjectVersion(canon_version_id="version", canon_object_id="object", version_number=1,
                    data={"structure": {"name": "Mara"}, "facts": [], "visuals": []}))
                db.commit()
            with patch.dict(os.environ, {"DATABASE_URL": url}):
                command.stamp(config(), "d93b71c602fa")
                upgrade_fixture_to_head()
                command.check(config())
                with Session(engine) as db:
                    profile = get_profile(db, "legacy", "alice")
                    self.assertEqual((profile.audience, profile.maturity_rating), ("adult", "general"))
                    self.assertEqual(profile.rating_count, 0)
                    self.assertEqual(db.get(Story, "legacy").objective, "Protect it")
                    save_profile(db, "legacy", "alice", GuidanceProfileInput(audience="teen", maturity_rating="moderate"))
                    self.assertEqual(get_profile(db, "legacy", "alice").audience, "teen")
                command.downgrade(config(), "d93b71c602fa")
                self.assertNotIn("narrative_guidance_profiles", inspect(engine).get_table_names())
                with Session(engine) as db:
                    self.assertEqual(db.scalar(select(Story.title).where(Story.story_id == "legacy")), "Preserved")
                    self.assertEqual(db.get(Scene, "scene").content, "Original prose")
                    self.assertEqual(db.get(UniverseStoryMembership, "legacy").universe_id, "world")
                    self.assertIsNotNone(db.get(CanonObjectVersion, "version"))
                upgrade_fixture_to_head()
                command.check(config())
            engine.dispose()

    def test_workflow_migration_round_trip_defaults_and_preservation(self):
        from sqlalchemy.orm import Session
        from app.db.models import Universe, UniverseStoryMembership, Scene, CanonEntry, CanonObject, CanonObjectVersion, StoryWorkflow
        from app.workflows.service import read_workflow, save_workflow
        from app.workflows.schemas import StoryWorkflowInput
        with tempfile.TemporaryDirectory(prefix="sandcastle-workflow-migration-") as directory:
            url = "sqlite:///" + str(Path(directory) / "migration.db")
            engine = create_engine(url)
            Base.metadata.create_all(engine, tables=[table for table in Base.metadata.sorted_tables if table.name not in {"story_workflows", "llm_provider_configs", "llm_role_bindings", "approved_media_adaptations", "creative_direction_snapshots"}])
            with Session(engine) as db:
                db.add(Story(story_id="legacy", user_id="alice", title="Preserved"))
                db.add(Universe(universe_id="world", user_id="alice", name="World"))
                db.add(CanonObject(canon_object_id="object", user_id="alice", object_type="place", name="Harbor"))
                db.flush()
                db.add(UniverseStoryMembership(story_id="legacy", universe_id="world"))
                db.add(Scene(scene_id="scene", story_id="legacy", sequence_number=1, content="Original prose"))
                db.add(CanonEntry(canon_entry_id="fact", story_id="legacy", type="world", key="rule", value="Preserved fact"))
                db.add(CanonObjectVersion(canon_version_id="version", canon_object_id="object", version_number=1,
                    data={"structure": {"name": "Harbor"}, "facts": [], "visuals": []}))
                db.commit()
            with patch.dict(os.environ, {"DATABASE_URL": url}):
                command.stamp(config(), "e04c8a12b763")
                upgrade_fixture_to_head()
                command.check(config())
                with Session(engine) as db:
                    self.assertEqual(read_workflow(db, "legacy", "alice")["difficulty"], "easy")
                    self.assertIsNone(db.get(StoryWorkflow, "legacy"))
                    save_workflow(db, "legacy", "alice", StoryWorkflowInput(difficulty="normal", workflow_template_id="webtoon"))
                    self.assertEqual(read_workflow(db, "legacy", "alice")["template_version"], 1)
                command.downgrade(config(), "e04c8a12b763")
                self.assertNotIn("story_workflows", inspect(engine).get_table_names())
                with Session(engine) as db:
                    self.assertEqual(db.scalar(select(Story.title).where(Story.story_id == "legacy")), "Preserved")
                    self.assertEqual(db.get(Scene, "scene").content, "Original prose")
                    self.assertEqual(db.get(CanonEntry, "fact").value, "Preserved fact")
                    self.assertEqual(db.get(UniverseStoryMembership, "legacy").universe_id, "world")
                    self.assertIsNotNone(db.get(CanonObjectVersion, "version"))
                upgrade_fixture_to_head()
                command.check(config())
            engine.dispose()
        output = io.StringIO()
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql+psycopg://audit:audit@localhost/audit"}):
            command.downgrade(config(output), "f15d7b92a640:e04c8a12b763", sql=True)
        self.assertIn("DROP TABLE story_workflows", output.getvalue())


if __name__ == "__main__":
    unittest.main()
