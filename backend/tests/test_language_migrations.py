"""Additive C2 migration on a temporary SQLite DB; never target a deployment."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from sqlalchemy import create_engine, inspect, text
from alembic import command
from test_migrations import config, strip_language_provenance
from app.db.database import Base


class LanguageMigrationTests(unittest.TestCase):
 def test_existing_codes_untouched_upgrade_downgrade_and_metadata_match(self):
  with tempfile.TemporaryDirectory() as directory:
   url='sqlite:///'+str(Path(directory)/'language.db');engine=create_engine(url);Base.metadata.create_all(engine);strip_language_provenance(engine)
   with engine.begin() as connection:
    connection.execute(text("INSERT INTO stories(story_id,user_id,title,status,language,secondary_genres,created_at,updated_at) VALUES('legacy','synthetic','Kept','active','id','[]',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
   with patch.dict(os.environ,DATABASE_URL=url):
    command.stamp(config(),'a062c8d4e132');command.upgrade(config(),'head');command.check(config())
    with engine.connect() as connection:self.assertEqual(tuple(connection.execute(text("SELECT language,language_provenance FROM stories WHERE story_id='legacy'")).one()),('id',None))
    command.downgrade(config(),'a062c8d4e132');self.assertNotIn('language_provenance',[row['name'] for row in inspect(engine).get_columns('stories')])
    command.upgrade(config(),'head');command.check(config())
   engine.dispose()
