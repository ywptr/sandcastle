import json
from app.llm.providers.google import GoogleStoryGenerator
from app.llm.errors import ProviderFailed
from app.media.production.prompts import SYSTEM_INSTRUCTIONS
from app.media.production.schemas import proposal_type


class GoogleNarrativeMediaTranslator(GoogleStoryGenerator):
    async def translate(self, context):
        schema = proposal_type(context.target_format)
        text = await self._generate({"systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTIONS}]},
            "contents": [{"role": "user", "parts": [{"text": json.dumps(context.narrative_data(), ensure_ascii=False)}]}],
            "generationConfig": {"maxOutputTokens": 16000, "candidateCount": 1, "responseModalities": ["TEXT"],
                "responseMimeType": "application/json", "responseJsonSchema": schema.model_json_schema()}})
        try:
            return schema.model_validate_json(text)
        except Exception:
            raise ProviderFailed("Narrative translation returned invalid output.") from None
