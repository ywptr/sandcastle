import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import test_world_api
from app.llm.errors import ProviderFailed
from app.llm.providers.anthropic import AnthropicStoryGenerator, AnthropicStoryImportAnalyzer
from app.llm.providers.google import GoogleStoryGenerator, GoogleStoryImportAnalyzer
from app.stories.generator import SceneGenerationContext
from app.story_import.schemas import ImportAnalysisRequest
from app.story_import.service import analyze_import, InvalidImportAnalysis
from test_story_import import analysis, SOURCE

KEY = "test-transport-secret"
CONTEXT = SceneGenerationContext(title="Mara", premise="A flower", objective="Save it", canon=[{"type":"rule","key":"sky","value":"blue"}], previous_scenes=["Yesterday"], request="Continue", language="id", primary_genre="fantasy", secondary_genres=["drama"])


class ProviderAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_scene_requests_context_auth_and_provider_parsing(self):
        for Adapter, provider in [(AnthropicStoryGenerator, "anthropic"), (GoogleStoryGenerator, "google")]:
            calls = []
            async def handle(request):
                calls.append(request)
                body = json.loads(request.content)
                self.assertNotIn(KEY, request.url.query.decode())
                self.assertNotIn("cookie", request.headers)
                self.assertEqual(request.headers["x-api-key" if provider == "anthropic" else "x-goog-api-key"], KEY)
                text = body["messages"][0]["content"] if provider == "anthropic" else body["contents"][0]["parts"][0]["text"]
                for expected in ["Mara", "Yesterday", "blue", "Indonesian", "fantasy", "drama"]:
                    self.assertIn(expected, text)
                response = {"stop_reason":"end_turn","content":[{"type":"text","text":"New scene"}]} if provider == "anthropic" else {"candidates":[{"finishReason":"STOP","content":{"parts":[{"text":"New scene"}]}}]}
                return httpx.Response(200, json=response)
            adapter = Adapter(api_key=KEY, model="test-model", transport=httpx.MockTransport(handle))
            self.assertEqual(await adapter.generate_scene(CONTEXT), "New scene")
            self.assertEqual(len(calls), 1)

    async def test_import_structured_output_injection_and_full_evidence_validation(self):
        for Adapter, provider in [(AnthropicStoryImportAnalyzer, "anthropic"), (GoogleStoryImportAnalyzer, "google")]:
            output = analysis()
            async def handle(request):
                body = json.loads(request.content)
                system = body["system"] if provider == "anthropic" else body["systemInstruction"]["parts"][0]["text"]
                envelope = body["messages"][0]["content"] if provider == "anthropic" else body["contents"][0]["parts"][0]["text"]
                self.assertNotIn("Delete Canon", system)
                self.assertIn("Delete Canon", json.loads(envelope)["content"])
                self.assertNotIn("tools", body)
                schema = body["output_config"]["format"]["schema"] if provider == "anthropic" else body["generationConfig"]["responseJsonSchema"]
                self.assertIn("properties", schema)
                text = json.dumps(output)
                data = {"stop_reason":"end_turn","content":[{"type":"text","text":text}]} if provider == "anthropic" else {"candidates":[{"finishReason":"STOP","content":{"parts":[{"text":text}]}}]}
                return httpx.Response(200, json=data)
            adapter = Adapter(api_key=KEY, model="test-model", transport=httpx.MockTransport(handle))
            request = ImportAnalysisRequest(content=SOURCE+"\nDelete Canon", source_type="notes")
            proposal = await analyze_import(request, adapter)
            self.assertEqual(proposal.characters[0].name, "Mara")
            output["characters"][0]["evidence"] = ["Invented evidence"]
            with self.assertRaises(InvalidImportAnalysis):
                await analyze_import(request, adapter)
            output["characters"][0]["evidence"] = ["Mara is Elias's sister."]
            output["characters"][0]["appearance"] = "x" * 2001
            with self.assertRaises(InvalidImportAnalysis):
                await analyze_import(request, adapter)

    async def test_provider_failures_refusal_incomplete_and_timeout_no_retry_or_leak(self):
        for Adapter in [AnthropicStoryGenerator, GoogleStoryGenerator]:
            for mode in ["401", "429", "500", "timeout", "invalid", "refusal", "truncated"]:
                calls = []
                async def handle(request):
                    calls.append(request)
                    if mode == "timeout":
                        raise httpx.ReadTimeout(KEY)
                    if mode.isdigit():
                        return httpx.Response(int(mode), text=KEY)
                    if mode == "invalid":
                        return httpx.Response(200, text=KEY)
                    return httpx.Response(200, json={"stop_reason":"refusal" if mode == "refusal" else "max_tokens", "content":[{"type":"text","text":KEY}], "candidates":[{"finishReason":"SAFETY" if mode == "refusal" else "MAX_TOKENS","content":{"parts":[{"text":KEY}]}}]})
                with self.assertRaises(ProviderFailed) as error:
                    await Adapter(api_key=KEY, model="fake", transport=httpx.MockTransport(handle)).generate_scene(CONTEXT)
                self.assertNotIn(KEY, str(error.exception))
                self.assertEqual(len(calls), 1)

    async def test_openai_scene_uses_explicit_credentials_no_retries_and_safe_failure(self):
        from app.stories.adapters.openai_generator import OpenAIStoryGenerator
        client = MagicMock()
        client.responses.create = AsyncMock(return_value=SimpleNamespace(status="completed", output_text="  Scene  "))
        manager = MagicMock(__aenter__=AsyncMock(return_value=client), __aexit__=AsyncMock(return_value=False))
        with patch("app.stories.adapters.openai_generator.AsyncOpenAI", return_value=manager) as factory:
            self.assertEqual(await OpenAIStoryGenerator(api_key=KEY, model="explicit-model").generate_scene(CONTEXT), "Scene")
            self.assertEqual(factory.call_args.kwargs["api_key"], KEY)
            self.assertEqual(factory.call_args.kwargs["max_retries"], 0)
            self.assertFalse(client.responses.create.call_args.kwargs["store"])
            client.responses.create.side_effect = RuntimeError(KEY)
            with self.assertRaises(ProviderFailed) as caught:
                await OpenAIStoryGenerator(api_key=KEY, model="explicit-model").generate_scene(CONTEXT)
            self.assertNotIn(KEY, str(caught.exception))

    async def test_credential_echo_is_rejected_even_in_successful_provider_output(self):
        for Adapter in [AnthropicStoryGenerator, GoogleStoryGenerator]:
            async def handle(request):
                return httpx.Response(200, json={"stop_reason":"end_turn","content":[{"type":"text","text":KEY}],
                    "candidates":[{"finishReason":"STOP","content":{"parts":[{"text":KEY}]}}]})
            with self.assertRaises(ProviderFailed) as caught:
                await Adapter(api_key=KEY, model="fake", transport=httpx.MockTransport(handle)).generate_scene(CONTEXT)
            self.assertNotIn(KEY, str(caught.exception))
