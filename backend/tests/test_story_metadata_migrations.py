"""M13 real revisions; PostgreSQL bootstrap is opt-in and dev-only."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4
from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from test_migrations import config, strip_language_provenance


class MetadataMigrationTests(unittest.TestCase):
    def exercise(self, url):
        with patch.dict(os.environ, DATABASE_URL=str(url)):
            if make_url(url).get_backend_name() == 'sqlite':
                from app.db.database import Base
                fixture_engine = create_engine(url)
                Base.metadata.create_all(fixture_engine, tables=[t for t in Base.metadata.sorted_tables if not t.name.startswith("llm_") and t.name not in ("approved_media_adaptations", "creative_direction_snapshots")])
                strip_language_provenance(fixture_engine)
                with fixture_engine.begin() as connection:
                    for column in ('language', 'primary_genre', 'secondary_genres'):
                        connection.exec_driver_sql(f'ALTER TABLE stories DROP COLUMN {column}')
                fixture_engine.dispose()
                command.stamp(config(), 'f15d7b92a640')
            else:
                command.upgrade(config(), 'f15d7b92a640')
            engine = create_engine(url)
            try:
                with engine.begin() as connection:
                    connection.execute(text("INSERT INTO stories (story_id,user_id,title,status,created_at,updated_at) VALUES ('legacy','synthetic','Legacy','active',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
                command.upgrade(config(), 'head')
                command.check(config())
                with engine.connect() as connection:
                    row = connection.execute(text("SELECT language,primary_genre,secondary_genres,title FROM stories WHERE story_id='legacy'")).one()
                    self.assertEqual(tuple(row[:2]), (None,None))
                    self.assertIn(row[2], ([], '[]'))
                    self.assertEqual(row[3], 'Legacy')
                command.downgrade(config(), 'f15d7b92a640')
                command.upgrade(config(), 'head')
                command.check(config())
            finally:
                engine.dispose()

    def test_sqlite_m13_and_legacy_defaults(self):
        with tempfile.TemporaryDirectory(prefix='sandcastle-m13-') as directory:
            self.exercise('sqlite:///' + str(Path(directory) / 'migration.db'))

    @unittest.skipUnless(os.getenv('SANDCASTLE_TEST_POSTGRES_BOOTSTRAP') == '1', 'Opt-in verified local PostgreSQL bootstrap')
    def test_postgres_fresh_schema_full_chain(self):
        from dotenv import dotenv_values
        # The opt-in reads only the private local configuration, not test-suite SQLite overrides.
        url = make_url(dotenv_values('.env')['DATABASE_URL'])
        self.assertEqual((url.drivername,url.host,url.port,url.database,url.username),
                         ('postgresql+psycopg','127.0.0.1',5432,'sandcastle_dev','sandcastle_dev'))
        engine = create_engine(url)
        schema = 'm13_bootstrap_' + uuid4().hex
        try:
            with engine.begin() as connection:
                self.assertEqual(tuple(connection.execute(text('select current_database(),current_user')).one()), ('sandcastle_dev','sandcastle_dev'))
                connection.exec_driver_sql(f'CREATE SCHEMA {schema}')
            with patch.dict(os.environ, PGOPTIONS=f'-csearch_path={schema}'):
                self.exercise(url.render_as_string(hide_password=False))
        finally:
            with engine.begin() as connection:
                connection.exec_driver_sql(f'DROP SCHEMA IF EXISTS {schema} CASCADE')
            engine.dispose()
