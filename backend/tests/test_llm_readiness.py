"""User-only source selection and production inspection safety; no network."""
import io
import os
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch
from app.llm.cli import parser
from app.llm.errors import SettingsInvalid
from app.llm.routing import LLMActorContext, resolve_provider_for_role
from app.ops.database_target import main, safe_target


class ReadinessTests(unittest.TestCase):
    def test_cli_identity_alias_and_no_ambiguous_scope(self):
        for flag in ("--is-subject", "--user-id"):
            args = parser().parse_args([flag, "is-subject-example", "--provider", "openai", "--show"])
            self.assertEqual(args.user_id, "is-subject-example")
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parser().parse_args(["--user-id", "a", "--is-subject", "b", "--provider", "openai"])

    def test_source_is_user_only_and_actor_required(self):
        actor = LLMActorContext("alice")
        with patch("app.llm.routing.select_provider", return_value=None) as select:
            self.assertIsNone(resolve_provider_for_role(None, actor, "creative_writer"))
            select.assert_called_once_with(None, "alice", "creative_writer")
        with self.assertRaises(SettingsInvalid):
            resolve_provider_for_role(None, {"user_id": "alice", "tenant_id": "fake"}, "creative_writer")
        with self.assertRaises(TypeError):
            LLMActorContext(user_id="alice", tenant_id="fake")

    def test_safe_target_never_prints_password_or_query(self):
        raw = "postgresql+psycopg://operator:example-secret@expected.neon.tech/prod_db?token=query-secret"
        self.assertEqual(set(safe_target(raw)), {"driver", "hostname", "database", "user"})
        output = io.StringIO()
        with patch.dict(os.environ, {"DATABASE_URL": raw}), redirect_stdout(output):
            self.assertEqual(main(["--expect-host", "expected.neon.tech", "--expect-database", "prod_db"]), 0)
        self.assertIn("human", output.getvalue())
        for secret in ("example-secret", "query-secret", "postgresql+psycopg://"):
            self.assertNotIn(secret, output.getvalue())

    def test_target_missing_invalid_and_mismatch_fail_closed(self):
        for raw in ("", "secret-invalid-url", "sqlite:///local.db", "postgresql+psycopg://u:p@other/db"):
            output = io.StringIO()
            with patch.dict(os.environ, {"DATABASE_URL": raw}), redirect_stdout(output), redirect_stderr(output):
                self.assertEqual(main(["--expect-host", "expected.neon.tech", "--expect-database", "prod_db"]), 1)
            self.assertIn("STOP", output.getvalue())
            self.assertNotIn("secret-invalid-url", output.getvalue())
