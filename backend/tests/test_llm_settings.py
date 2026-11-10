"""BYOK isolation and routing; only fake keys/transports, no provider network calls."""
import os
import unittest
from unittest.mock import AsyncMock, patch
from cryptography.fernet import Fernet
from fastapi import HTTPException
from sqlalchemy import select
import test_world_api
from app.db.models.llm import LLMProviderConfig, LLMRoleBinding
from app.llm import service
from app.llm.resolver import resolve_adapter
from app.llm.schemas import ProviderUpdate, RoleUpdate
from app.llm.secrets import decrypt_credentials, SecretUnavailable

ROOT = "/api/settings/llm"
KEY = "test-only-provider-key-never-live"


class ProviderSettingsTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, SANDCASTLE_PROVIDER_SECRET_ENCRYPTION_KEY=Fernet.generate_key().decode())
        self.env.start()
        self.world = test_world_api.WorldAPITests()
        self.world.setUp()
        self.client, self.sessions = self.world.client, self.world.sessions

    def tearDown(self):
        self.world.tearDown()
        self.env.stop()

    def configure(self, provider="openai", **extra):
        values = {"enabled": True, "credentials": {"api_key": KEY}, "config": {"default_model": "test-model"}, **extra}
        r = self.client.put(ROOT + "/providers/" + provider, json=values)
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(KEY, r.text)
        return r.json()

    def test_encryption_roundtrip_omission_rotation_disable_removal(self):
        view = self.configure()
        self.assertTrue(view["has_credentials"])
        with self.sessions() as db:
            row = service.get_provider_config(db, "alice", "openai")
            first = row.encrypted_credentials
            self.assertNotIn(KEY, first)
            self.assertEqual(decrypt_credentials("alice", "openai", first), KEY)
        self.client.put(ROOT + "/providers/openai", json={"enabled": False})
        with self.sessions() as db:
            self.assertEqual(service.get_provider_config(db, "alice", "openai").encrypted_credentials, first)
        self.client.put(ROOT + "/providers/openai", json={"enabled": True})
        self.configure(credentials={"api_key": "rotated-test-key"})
        with self.sessions() as db:
            second = service.get_provider_config(db, "alice", "openai").encrypted_credentials
            self.assertNotEqual(first, second)
            self.assertEqual(decrypt_credentials("alice", "openai", second), "rotated-test-key")
        r = self.client.delete(ROOT + "/providers/openai/credentials")
        self.assertFalse(r.json()["has_credentials"])
        self.assertFalse(r.json()["enabled"])

    def test_readiness_rejects_tenant_scope_and_reports_effective_routing(self):
        self.configure()
        for path, payload in [("/providers/openai", {"scope_type": "tenant", "scope_id": "fake", "enabled": True}),
                              ("/roles/creative_writer", {"provider": "openai", "scope_type": "tenant"})]:
            self.assertEqual(self.client.put(ROOT + path, json=payload).status_code, 422)
        self.assertEqual(self.client.put(ROOT + "/roles/unknown", json={"provider": "openai"}).status_code, 422)
        self.assertEqual(self.client.put(ROOT + "/roles/creative_writer", json={"provider": "openai"}).status_code, 200)
        self.client.put(ROOT + "/providers/openai", json={"enabled": False})
        roles = self.client.get(ROOT + "/roles").json()
        self.assertFalse(next(r for r in roles if r["role"] == "creative_writer")["available"])
        self.assertEqual(self.client.put(ROOT + "/roles/story_importer", json={"provider": "openai"}).status_code, 422)
        self.assertEqual(self.client.put(ROOT + "/roles/story_importer", json={"provider": "google"}).status_code, 422)
        self.world.sign_in("bob")
        roles = self.client.get(ROOT + "/roles").json()
        self.assertTrue(all(r["provider"] is None and not r["available"] for r in roles))
        response = self.client.get(ROOT + "/providers").text
        self.assertNotIn(KEY, response)
        self.assertNotIn("encrypted_credentials", response)

    def test_scope_swap_wrong_key_and_tamper_fail_closed(self):
        self.configure()
        with self.sessions() as db:
            token = service.get_provider_config(db, "alice", "openai").encrypted_credentials
        for scope, provider, value in [("bob", "openai", token), ("alice", "google", token), ("alice", "openai", token[:-3]+"bad")]:
            with self.assertRaises(SecretUnavailable) as caught:
                decrypt_credentials(scope, provider, value)
            self.assertNotIn(KEY, str(caught.exception))
        with patch.dict(os.environ, SANDCASTLE_PROVIDER_SECRET_ENCRYPTION_KEY=Fernet.generate_key().decode()):
            with self.assertRaises(SecretUnavailable):
                decrypt_credentials("alice", "openai", token)

    def test_user_isolation_and_no_scope_override(self):
        self.configure()
        self.world.sign_in("bob")
        self.assertFalse(self.client.get(ROOT + "/providers/openai").json()["has_credentials"])
        self.assertFalse(any(v["has_credentials"] for v in self.client.get(ROOT + "/providers").json()))
        self.assertEqual(self.client.put(ROOT + "/roles/creative_writer", json={"provider": "openai"}).status_code, 422)
        self.assertEqual(self.client.put(ROOT + "/providers/openai", json={"scope_id": "alice", "enabled": False}).status_code, 422)
        self.client.delete(ROOT + "/providers/openai/credentials")
        with self.sessions() as db:
            with self.assertRaises(HTTPException) as e:
                resolve_adapter(db, "bob", "creative_writer")
            self.assertEqual(e.exception.status_code, 503)
            self.assertEqual(decrypt_credentials("alice", "openai", service.get_provider_config(db, "alice", "openai").encrypted_credentials), KEY)
        self.configure(credentials={"api_key": "bob-test-key"})
        with self.sessions() as db:
            a, b = resolve_adapter(db, "alice", "creative_writer"), resolve_adapter(db, "bob", "creative_writer")
            self.assertIsNot(a, b)
            self.assertNotEqual(a._api_key, b._api_key)

    def test_safe_validation_and_no_arbitrary_urls_or_secret_config(self):
        for body in [{"credentials": {"api_key": {"secret": KEY}}}, {"credentials": {"api_key": ""}},
                     {"credentials": {"api_key": KEY}, "config": {"base_url": "http://localhost/"}},
                     {"config": {"api_key": KEY}}, {"config": {"default_model": "https://evil.test/"}},
                     {"credentials": None}, {"enabled": None}, {}]:
            r = self.client.put(ROOT + "/providers/openai", json=body)
            self.assertEqual(r.status_code, 422)
            self.assertNotIn(KEY, r.text)
            self.assertNotIn('"input"', r.text)
        self.assertEqual(self.client.put(ROOT + "/providers/unknown", json={"enabled": True}).status_code, 422)
        self.assertEqual(self.client.put(ROOT + "/roles/unknown", json={"provider": None}).status_code, 422)

    def test_authentication_and_safe_read_responses(self):
        self.configure()
        for endpoint in ["/providers", "/providers/openai", "/roles"]:
            r = self.client.get(ROOT+endpoint)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.headers["cache-control"], "no-store")
            self.assertNotIn(KEY, r.text)
            self.assertNotIn("encrypted_credentials", r.text)
            self.assertNotIn("api_key", r.text)
        self.client.cookies.clear()
        self.assertEqual(self.client.get(ROOT+"/providers").status_code, 401)
        self.assertEqual(self.client.put(ROOT+"/providers/openai", json={"enabled": True}).status_code, 401)

    def test_missing_encryption_key_or_storage_failure_is_safe(self):
        with patch.dict(os.environ, SANDCASTLE_PROVIDER_SECRET_ENCRYPTION_KEY="invalid"):
            r = self.client.put(ROOT+"/providers/openai", json={"credentials": {"api_key": KEY}})
        self.assertEqual(r.status_code, 503)
        self.assertNotIn(KEY, r.text)
        with self.sessions() as db:
            self.assertIsNone(service.get_provider_config(db, "alice", "openai"))
            with patch.object(db, "commit", side_effect=RuntimeError(KEY)), patch.object(db, "rollback", wraps=db.rollback) as rollback:
                with self.assertRaises(service.SettingsStorageError) as caught:
                    service.set_provider_config(db, "alice", "openai", ProviderUpdate(enabled=True, credentials={"api_key": KEY}))
                self.assertNotIn(KEY, str(caught.exception))
                rollback.assert_called_once()
            self.assertIsNone(service.get_provider_config(db, "alice", "openai"))

    def test_deterministic_routing_and_roles_no_fallback_from_invalid_binding(self):
        self.configure("google")
        self.configure("anthropic")
        self.configure("openai")
        with self.sessions() as db:
            for role in ["creative_writer", "story_importer"]:
                self.assertTrue(type(resolve_adapter(db, "alice", role)).__name__.startswith("OpenAI"))
        for provider, prefix in [("anthropic", "Anthropic"), ("google", "Google"), ("openai", "OpenAI")]:
            for role in ["creative_writer", "story_importer"]:
                r = self.client.put(ROOT+"/roles/"+role, json={"provider": provider, "model": "override-model"})
                self.assertEqual(r.status_code, 200)
                with self.sessions() as db:
                    adapter = resolve_adapter(db, "alice", role)
                    self.assertTrue(type(adapter).__name__.startswith(prefix))
                    self.assertEqual(adapter.model, "override-model")
        self.client.put(ROOT+"/providers/openai", json={"enabled": False})
        with self.sessions() as db:
            with self.assertRaises(HTTPException):
                resolve_adapter(db, "alice", "creative_writer")
        self.client.put(ROOT+"/roles/creative_writer", json={"provider": None})
        with self.sessions() as db:
            self.assertEqual(type(resolve_adapter(db, "alice", "creative_writer")).__name__, "AnthropicStoryGenerator")
        self.client.delete(ROOT+"/providers/anthropic/credentials")
        with self.sessions() as db:
            self.assertEqual(type(resolve_adapter(db, "alice", "creative_writer")).__name__, "GoogleStoryGenerator")
        self.client.put(ROOT+"/providers/google", json={"enabled": False})
        with self.sessions() as db:
            with self.assertRaises(HTTPException) as error:
                resolve_adapter(db, "alice", "creative_writer")
            self.assertEqual(error.exception.status_code, 503)

    def test_scene_api_uses_authenticated_routing_and_sanitizes_provider_failure(self):
        self.configure("anthropic")
        with patch("app.llm.providers.anthropic.AnthropicStoryGenerator.generate_scene", new=AsyncMock(return_value="New prose")) as generated:
            r = self.client.post(self.world.root+"/scenes/generate", json={"request": "Continue"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(generated.await_args.args[0].title, "The Last Flower")
        with patch("app.llm.providers.anthropic.AnthropicStoryGenerator.generate_scene", new=AsyncMock(side_effect=RuntimeError(KEY))):
            r = self.client.post(self.world.root+"/scenes/generate", json={"request": "Continue"})
        self.assertEqual(r.status_code, 502)
        self.assertNotIn(KEY, r.text)
        self.assertNotIn(KEY, self.client.get(self.world.root+"/actions").text)

    def test_import_api_routes_without_persisting_analysis(self):
        from test_story_import import analysis, SOURCE
        self.configure("google")
        with self.sessions() as db:
            counts = {t.name: db.execute(select(t)).all() for t in [LLMProviderConfig.__table__, LLMRoleBinding.__table__]}
        with patch("app.llm.providers.google.GoogleStoryImportAnalyzer.analyze", new=AsyncMock(return_value=analysis())) as analyzer:
            r = self.client.post("/api/stories/import/analyze", json={"content": SOURCE, "source_type": "notes"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(analyzer.await_args.args[0].content, SOURCE)
        self.assertEqual(r.json()["characters"][0]["evidence"], ["Mara is Elias's sister."])
        with self.sessions() as db:
            self.assertEqual(counts, {t.name: db.execute(select(t)).all() for t in [LLMProviderConfig.__table__, LLMRoleBinding.__table__]})

    def test_optional_openai_sdk_unavailable_is_503_without_fallback(self):
        import builtins
        self.configure("openai")
        self.configure("anthropic")
        real_import = builtins.__import__
        def blocked(name, *args, **kwargs):
            if name == "app.stories.adapters.openai_generator":
                raise ImportError("SDK unavailable")
            return real_import(name, *args, **kwargs)
        with self.sessions() as db, patch("builtins.__import__", side_effect=blocked):
            with self.assertRaises(HTTPException) as caught:
                resolve_adapter(db, "alice", "creative_writer")
            self.assertEqual(caught.exception.status_code, 503)
