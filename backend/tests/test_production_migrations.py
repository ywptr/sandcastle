import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from alembic import command
from sqlalchemy import create_engine, inspect, text
from test_migrations import config
from app.db.database import Base


class ProductionMigrationTests(unittest.TestCase):
    def test_upgrade_role_preservation_check_and_downgrade(self):
        with tempfile.TemporaryDirectory() as directory:
            url='sqlite:///'+str(Path(directory)/'production.db');engine=create_engine(url)
            Base.metadata.create_all(engine,tables=[t for t in Base.metadata.sorted_tables if t.name not in ('approved_media_adaptations','creative_direction_snapshots')])
            with engine.begin() as connection:
                connection.execute(text("INSERT INTO llm_role_bindings (scope_type,scope_id,role,provider,updated_at) VALUES ('user','synthetic','creative_writer','openai',CURRENT_TIMESTAMP)"))
            with patch.dict(os.environ,DATABASE_URL=url):
                command.stamp(config(),'8d40f6a2c910');command.upgrade(config(),'head');command.check(config())
                self.assertIn('approved_media_adaptations',inspect(engine).get_table_names())
                with engine.begin() as connection:
                    self.assertEqual(connection.scalar(text('SELECT count(*) FROM llm_role_bindings')),1)
                    connection.execute(text("INSERT INTO llm_role_bindings (scope_type,scope_id,role,provider,updated_at) VALUES ('user','synthetic','narrative_media_translator','openai',CURRENT_TIMESTAMP)"))
                with self.assertRaisesRegex(RuntimeError,'Remove narrative media translator'):
                    command.downgrade(config(),'8d40f6a2c910')
                with engine.begin() as connection:
                    connection.execute(text("DELETE FROM llm_role_bindings WHERE role='narrative_media_translator'"))
                command.downgrade(config(),'8d40f6a2c910')
                self.assertNotIn('approved_media_adaptations',inspect(engine).get_table_names())
                command.upgrade(config(),'head');command.check(config())
            engine.dispose()
