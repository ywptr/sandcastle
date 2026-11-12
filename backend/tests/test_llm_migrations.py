import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from alembic import command
from sqlalchemy import create_engine, inspect, text
from test_migrations import config, strip_language_provenance
from app.db.database import Base


class LLMMigrationTests(unittest.TestCase):
    def test_upgrade_check_downgrade_and_existing_story_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            url = 'sqlite:///' + str(Path(directory) / 'llm.db')
            engine = create_engine(url)
            Base.metadata.create_all(engine, tables=[t for t in Base.metadata.sorted_tables if not t.name.startswith('llm_') and t.name not in ('approved_media_adaptations','creative_direction_snapshots')])
            strip_language_provenance(engine)
            with engine.begin() as connection:
                connection.execute(text("INSERT INTO stories (story_id,user_id,title,status,secondary_genres,created_at,updated_at) VALUES ('legacy','alice','Preserved','active','[]',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
            with patch.dict(os.environ, DATABASE_URL=url):
                command.stamp(config(), '7c2e91a4b830')
                command.upgrade(config(), 'head')
                command.check(config())
                self.assertIn('llm_provider_configs', inspect(engine).get_table_names())
                command.downgrade(config(), '7c2e91a4b830')
                self.assertNotIn('llm_provider_configs', inspect(engine).get_table_names())
                with engine.connect() as connection:
                    self.assertEqual(connection.scalar(text("SELECT title FROM stories WHERE story_id='legacy'")), 'Preserved')
                command.upgrade(config(), 'head')
                command.check(config())
            engine.dispose()
