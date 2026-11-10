import json
from app.llm.errors import ProviderFailed, reject_credential_output
from app.llm.providers.http import post_json, import_schema, anthropic_schema
from app.stories.prompts import build_prompt
from app.story_import.prompts import SYSTEM_INSTRUCTIONS
from app.story_import.schemas import ImportAnalysis


class AnthropicStoryGenerator:
    def __init__(self, *, api_key: str, model: str, transport=None):
        self._api_key, self.model, self._transport = api_key, model, transport

    async def _message(self, body):
        result = await post_json("https://api.anthropic.com/v1/messages",
            {"x-api-key": self._api_key, "anthropic-version": "2023-06-01"},
            {"model": self.model, **body}, transport=self._transport)
        try:
            if result["stop_reason"] != "end_turn":
                raise ValueError()
            blocks = result["content"]
            if any(b.get("type") != "text" for b in blocks):
                raise ValueError()
            text = "".join(b["text"] for b in blocks)
            if not text.strip():
                raise ValueError()
            reject_credential_output(text, self._api_key)
            return text
        except Exception:
            raise ProviderFailed("Anthropic returned incomplete, refused, or invalid output.") from None

    async def generate_scene(self, context) -> str:
        return (await self._message({"max_tokens": 8000, "messages": [{"role": "user", "content": build_prompt(context)}]})).strip()


class AnthropicStoryImportAnalyzer(AnthropicStoryGenerator):
    async def analyze(self, request) -> ImportAnalysis:
        text = await self._message({"max_tokens": 12000, "system": SYSTEM_INSTRUCTIONS,
            "messages": [{"role": "user", "content": json.dumps(request.model_dump(), ensure_ascii=False)}],
            "output_config": {"format": {"type": "json_schema", "schema": anthropic_schema(import_schema())}}})
        try:
            return ImportAnalysis.model_validate_json(text)
        except Exception:
            raise ProviderFailed("Anthropic returned an invalid import proposal.") from None
