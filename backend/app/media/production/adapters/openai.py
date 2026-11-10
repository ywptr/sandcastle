import json
from openai import AsyncOpenAI
from app.llm.errors import ProviderFailed, reject_credential_output
from app.media.production.prompts import SYSTEM_INSTRUCTIONS
from app.media.production.schemas import proposal_type


class OpenAINarrativeMediaTranslator:
    def __init__(self, *, api_key, model):
        self._api_key, self.model = api_key, model

    async def translate(self, context):
        try:
            schema = proposal_type(context.target_format)
            async with AsyncOpenAI(api_key=self._api_key, base_url="https://api.openai.com/v1", timeout=60.0, max_retries=0) as client:
                result = await client.responses.parse(model=self.model, text_format=schema, store=False, max_output_tokens=16000,
                    input=[{"role": "system", "content": SYSTEM_INSTRUCTIONS},
                           {"role": "user", "content": json.dumps(context.narrative_data(), ensure_ascii=False)}])
            if result.status != "completed" or result.output_parsed is None:
                raise ValueError()
            reject_credential_output(result.output_parsed.model_dump_json(), self._api_key)
            return schema.model_validate(result.output_parsed.model_dump())
        except Exception:
            raise ProviderFailed("Narrative translation failed or returned invalid output. No automatic retry was made.") from None
