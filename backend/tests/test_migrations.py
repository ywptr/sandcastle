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
        self.assertIn("8f31c2d9a670", sql)
        self.assertIn("FOREIGN KEY(story_id) REFERENCES stories (story_id)", sql)
        self.assertIn("ix_characters_story_id", sql)
        self.assertIn("uq_scene_story_sequence", sql)
        self.assertIn("6b2c8f10a4d9", sql)

    def test_new_revision_upgrade_check_downgrade_preserves_story(self):
        with tempfile.TemporaryDirectory(prefix="sandcastle-migrations-") as directory:
            url = "sqlite:///" + str(Path(directory) / "migration.db")
            engine = create_engine(url)
            legacy = [table for table in Base.metadata.sorted_tables if table.name not in {"characters", "places", "media_executions", "artifacts"}]
            Base.metadata.create_all(engine, tables=legacy)
            with engine.begin() as connection:
                connection.execute(Story.__table__.insert().values(story_id="existing", user_id="alice", title="Preserved"))
            with patch.dict(os.environ, {"DATABASE_URL": url}):
                command.stamp(config(), "e5a5b285762e")
                command.upgrade(config(), "head")
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
                        if table.name not in {"media_executions", "artifacts"}]
            Base.metadata.create_all(engine, tables=baseline)
            with patch.dict(os.environ, {"DATABASE_URL": url}):
                command.stamp(config(), "6b2c8f10a4d9")
                command.upgrade(config(), "head")
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


if __name__ == "__main__":
    unittest.main()
