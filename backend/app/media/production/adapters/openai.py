import json
from openai import AsyncOpenAI, APIError
from pydantic import ValidationError
from app.media.production.diagnostics import TranslationFailed, schema_reason
from app.llm.errors import ProviderFailed, reject_credential_output
from app.media.production.prompts import SYSTEM_INSTRUCTIONS
from app.media.production.schemas import proposal_type


class OpenAINarrativeMediaTranslator:
    def __init__(self, *, api_key, model):
        self._api_key, self.model = api_key, model

    async def translate(self, context):
        schema = proposal_type(context.target_format)
        try:
            async with AsyncOpenAI(api_key=self._api_key, base_url="https://api.openai.com/v1", timeout=60.0, max_retries=0) as client:
                result = await client.responses.parse(model=self.model, text_format=schema, store=False, max_output_tokens=16000,
                    input=[{"role": "system", "content": SYSTEM_INSTRUCTIONS},
                           {"role": "user", "content": json.dumps(context.narrative_data(), ensure_ascii=False)}])
        except ValidationError as error:
            category = ("provider_structured_output_invalid" if any(
                item["type"] == "json_invalid" for item in error.errors(include_input=False, include_context=False))
                else "schema_validation_failed")
            raise TranslationFailed(category, "invalid_json" if category == "provider_structured_output_invalid" else schema_reason(error)) from None
        except APIError:
            raise TranslationFailed("provider_request_failed", "request_failed") from None
        if result.status != "completed":
            raise TranslationFailed("provider_incomplete", "response_not_completed")
        if result.output_parsed is None:
            raise TranslationFailed("provider_structured_output_invalid", "parsed_output_missing")
        try:
            reject_credential_output(result.output_parsed.model_dump_json(), self._api_key)
        except ProviderFailed:
            raise TranslationFailed("provider_structured_output_invalid", "credential_output_rejected") from None
        try:
            return schema.model_validate(result.output_parsed.model_dump())
        except ValidationError:
            raise TranslationFailed("schema_validation_failed", "invalid_proposal_schema") from None
