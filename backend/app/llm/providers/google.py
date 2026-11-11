import json
from urllib.parse import quote
from app.llm.errors import ProviderFailed, ProviderIncomplete, ProviderOutputInvalid, reject_credential_output
from app.llm.providers.http import post_json, import_schema
from app.stories.prompts import build_prompt
from app.story_import.prompts import SYSTEM_INSTRUCTIONS
from app.story_import.schemas import ImportAnalysis


class GoogleStoryGenerator:
    def __init__(self, *, api_key: str, model: str, transport=None):
        self._api_key, self.model, self._transport = api_key, model, transport

    async def _generate(self, body):
        result = await post_json(f"https://generativelanguage.googleapis.com/v1beta/models/{quote(self.model, safe='')}:generateContent",
            {"x-goog-api-key": self._api_key}, body, transport=self._transport)
        try:
            if result.get("promptFeedback", {}).get("blockReason"):
                raise ValueError()
            candidates = result["candidates"]
            if len(candidates) != 1 or candidates[0]["finishReason"] != "STOP":
                raise ValueError()
            parts = candidates[0]["content"]["parts"]
            if any("text" not in part for part in parts):
                raise ValueError()
            text = "".join(part["text"] for part in parts if not part.get("thought"))
            if not text.strip():
                raise ValueError()
            reject_credential_output(text, self._api_key)
            return text
        except ProviderOutputInvalid:
            raise
        except Exception:
            raise ProviderIncomplete("Google returned incomplete, blocked, or invalid output.") from None

    async def generate_scene(self, context) -> str:
        return (await self._generate({"contents": [{"role": "user", "parts": [{"text": build_prompt(context)}]}],
            "generationConfig": {"maxOutputTokens": 8000, "candidateCount": 1}})).strip()


class GoogleStoryImportAnalyzer(GoogleStoryGenerator):
    async def analyze(self, request) -> ImportAnalysis:
        text = await self._generate({"systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTIONS}]},
            "contents": [{"role": "user", "parts": [{"text": json.dumps(request.model_dump(), ensure_ascii=False)}]}],
            "generationConfig": {"maxOutputTokens": 12000, "candidateCount": 1,
                "responseMimeType": "application/json", "responseJsonSchema": import_schema()}})
        try:
            return ImportAnalysis.model_validate_json(text)
        except Exception:
            raise ProviderFailed("Google returned an invalid import proposal.") from None
