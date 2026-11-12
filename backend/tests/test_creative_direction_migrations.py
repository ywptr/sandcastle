import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from alembic import command
from sqlalchemy import create_engine,inspect,text
from app.db.database import Base
from test_migrations import config, strip_language_provenance


class CreativeDirectionMigrationTests(unittest.TestCase):
    def test_upgrade_check_downgrade_preserves_existing_story(self):
        with tempfile.TemporaryDirectory() as directory:
            url='sqlite:///'+str(Path(directory)/'creative.db');engine=create_engine(url)
            Base.metadata.create_all(engine,tables=[t for t in Base.metadata.sorted_tables if t.name!='creative_direction_snapshots'])
            strip_language_provenance(engine)
            with engine.begin() as c:c.execute(text("INSERT INTO stories (story_id,user_id,title,status,secondary_genres,created_at,updated_at) VALUES ('legacy','synthetic','Kept','active','[]',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
            with patch.dict(os.environ,DATABASE_URL=url):
                command.stamp(config(),'9e51b7c3d021');command.upgrade(config(),'head');command.check(config())
                self.assertIn('creative_direction_snapshots',inspect(engine).get_table_names())
                command.downgrade(config(),'9e51b7c3d021');self.assertNotIn('creative_direction_snapshots',inspect(engine).get_table_names())
                command.upgrade(config(),'head');command.check(config())
                with engine.connect() as c:self.assertEqual(c.scalar(text("SELECT title FROM stories WHERE story_id='legacy'")),'Kept')
            engine.dispose()
