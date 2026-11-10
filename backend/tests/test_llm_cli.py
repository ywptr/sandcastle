import io
import os
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch
from cryptography.fernet import Fernet
import test_world_api
from app.llm import service
from app.llm.cli import parser, configure, checked_target, UnsafeTarget
from app.llm.secrets import decrypt_credentials


class ProviderCLITests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, SANDCASTLE_PROVIDER_SECRET_ENCRYPTION_KEY=Fernet.generate_key().decode())
        self.env.start()
        self.world = test_world_api.WorldAPITests()
        self.world.setUp()
        self.secret = "cli-only-test-secret"

    def tearDown(self):
        self.world.tearDown()
        self.env.stop()

    def run_cli(self, *options, secret=None, answers=None):
        args = parser().parse_args(["--user-id", "synthetic-cli", "--provider", "openai", *options])
        answers = iter(answers or ["test-model", "y"])
        output = io.StringIO()
        with self.world.sessions() as db, redirect_stdout(output):
            configure(db, args, read_secret=lambda _: self.secret if secret is None else secret,
                      read_input=lambda _: next(answers))
        self.assertNotIn(self.secret, output.getvalue())
        return output.getvalue()

    def test_cli_shares_service_encrypts_and_show_does_not_decrypt(self):
        with patch("app.llm.service.set_provider_config", wraps=service.set_provider_config) as shared:
            self.run_cli()
        shared.assert_called_once()
        with self.world.sessions() as db:
            row = service.get_provider_config(db, "synthetic-cli", "openai")
            self.assertNotIn(self.secret, row.encrypted_credentials)
            self.assertEqual(decrypt_credentials("synthetic-cli", "openai", row.encrypted_credentials), self.secret)
            self.assertIsNone(service.get_provider_config(db, "alice", "openai"))
        with patch.dict(os.environ, SANDCASTLE_PROVIDER_SECRET_ENCRYPTION_KEY="missing"):
            shown = self.run_cli("--show")
        self.assertIn('"has_credentials": true', shown)
        self.assertNotIn("encrypted_credentials", shown)

    def test_rotation_omitted_key_disable_and_reenable(self):
        self.run_cli()
        with self.world.sessions() as db:
            first = service.get_provider_config(db, "synthetic-cli", "openai").encrypted_credentials
        self.run_cli("--disable")
        with self.world.sessions() as db:
            row = service.get_provider_config(db, "synthetic-cli", "openai")
            self.assertFalse(row.enabled)
            self.assertEqual(first, row.encrypted_credentials)
        self.run_cli("--enable")
        self.run_cli(secret="")
        with self.world.sessions() as db:
            self.assertEqual(first, service.get_provider_config(db, "synthetic-cli", "openai").encrypted_credentials)
        self.run_cli(secret="rotated-cli-test-key")
        with self.world.sessions() as db:
            second = service.get_provider_config(db, "synthetic-cli", "openai").encrypted_credentials
            self.assertNotEqual(first, second)
            self.assertEqual(decrypt_credentials("synthetic-cli", "openai", second), "rotated-cli-test-key")

    def test_remove_requires_explicit_interactive_confirmation(self):
        self.run_cli()
        self.assertIn("cancelled", self.run_cli("--remove-credentials", answers=["no"]))
        with self.world.sessions() as db:
            self.assertTrue(service.get_provider_config(db, "synthetic-cli", "openai").encrypted_credentials)
        self.run_cli("--remove-credentials", answers=["REMOVE"])
        with self.world.sessions() as db:
            row = service.get_provider_config(db, "synthetic-cli", "openai")
            self.assertIsNone(row.encrypted_credentials)
            self.assertFalse(row.enabled)

    def test_bad_arguments_and_scope_rejected(self):
        for values in [["--provider", "unknown", "--user-id", "alice"], ["--provider", "openai"],
                       ["--provider", "openai", "--user-id", "alice", "--api-key", "not-accepted"]]:
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                parser().parse_args(values)
        args = parser().parse_args(["--provider", "google", "--user-id", " "])
        with self.world.sessions() as db, self.assertRaises(service.SettingsInvalid):
            configure(db, args, read_secret=lambda _: self.fail("Must not prompt"))

    def test_failed_write_rolls_back_and_never_prints_exception_or_key(self):
        args = parser().parse_args(["--user-id", "synthetic-cli", "--provider", "google"])
        output = io.StringIO()
        with self.world.sessions() as db, patch.object(db, "commit", side_effect=RuntimeError(self.secret)), patch.object(db, "rollback", wraps=db.rollback) as rollback:
            with redirect_stdout(output), self.assertRaises(RuntimeError) as caught:
                configure(db, args, read_secret=lambda _: self.secret, read_input=lambda _: "test-model")
            self.assertNotIn(self.secret, str(caught.exception))
            self.assertNotIn(self.secret, output.getvalue())
            self.assertTrue(rollback.called)
        with self.world.sessions() as db:
            self.assertIsNone(service.get_provider_config(db, "synthetic-cli", "google"))

    def test_database_safety_checks(self):
        good = "postgresql+psycopg://sandcastle_dev:fake@127.0.0.1:5432/sandcastle_dev"
        self.assertEqual(checked_target(good).database, "sandcastle_dev")
        for url in [None, "sqlite://", "postgresql+psycopg://user:secret@remote.test:5432/production", good.replace("sandcastle_dev", "other_app")]:
            with self.assertRaises(UnsafeTarget) as caught:
                checked_target(url)
            self.assertNotIn("secret@", str(caught.exception))
        remote = "postgresql+psycopg://user:fake@remote.test:5432/prod"
        with self.assertRaises(UnsafeTarget):
            checked_target(remote, allow_remote=True, confirmation="prod")
        self.assertEqual(checked_target(remote, allow_remote=True, confirmation="remote.test:5432/prod").database, "prod")

    def test_getpass_echo_fallback_aborts_before_writing(self):
        import getpass
        import warnings
        args = parser().parse_args(["--user-id", "synthetic-cli", "--provider", "openai"])
        def insecure(_):
            warnings.warn("Echo unavailable", getpass.GetPassWarning)
            self.fail("Must abort before reading an echoed key")
        with self.world.sessions() as db:
            with self.assertRaises(RuntimeError):
                configure(db, args, read_secret=insecure)
            self.assertIsNone(service.get_provider_config(db, "synthetic-cli", "openai"))
