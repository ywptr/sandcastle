"""Structured-output adapter. Imported material is data, never system instructions."""
import json

from openai import AsyncOpenAI

from app.story_import.schemas import ImportAnalysis, ImportAnalysisRequest

from app.story_import.prompts import SYSTEM_INSTRUCTIONS
from app.llm.errors import ProviderFailed, reject_credential_output



class OpenAIStoryImportAnalyzer:
    def __init__(self, *, api_key: str, model: str):
        self._api_key, self.model = api_key, model

    async def analyze(self, request: ImportAnalysisRequest) -> ImportAnalysis:
        try:
            # Per-call lifetime avoids shared async-client state across test/server event loops.
            async with AsyncOpenAI(api_key=self._api_key, base_url="https://api.openai.com/v1", timeout=60.0, max_retries=0) as client:
                response = await client.responses.parse(
                    model=self.model,
                    input=[{"role": "system", "content": SYSTEM_INSTRUCTIONS},
                           {"role": "user", "content": json.dumps(request.model_dump(), ensure_ascii=False)}],
                    text_format=ImportAnalysis,
                    max_output_tokens=12000,
                    store=False,
                )
            if response.status != "completed" or response.output_parsed is None:
                raise ValueError("Import analysis incomplete or refused")
            reject_credential_output(response.output_parsed.model_dump_json(), self._api_key)
            return response.output_parsed
        except Exception:
            raise ProviderFailed("Import provider failed or returned invalid output. No automatic retry was made.") from None
