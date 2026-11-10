import json
from app.llm.providers.anthropic import AnthropicStoryGenerator
from app.llm.providers.http import anthropic_schema
from app.llm.errors import ProviderFailed
from app.media.production.prompts import SYSTEM_INSTRUCTIONS
from app.media.production.schemas import proposal_type


class AnthropicNarrativeMediaTranslator(AnthropicStoryGenerator):
    async def translate(self, context):
        schema = proposal_type(context.target_format)
        text = await self._message({"max_tokens": 16000, "system": SYSTEM_INSTRUCTIONS,
            "messages": [{"role": "user", "content": json.dumps(context.narrative_data(), ensure_ascii=False)}],
            "output_config": {"format": {"type": "json_schema", "schema": anthropic_schema(schema.model_json_schema())}}})
        try:
            return schema.model_validate_json(text)
        except Exception:
            raise ProviderFailed("Narrative translation returned invalid output.") from None
