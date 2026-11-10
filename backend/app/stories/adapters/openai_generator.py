"""OpenAI adapter; all credentials/models are explicit operation-scoped values."""
from openai import AsyncOpenAI
from app.stories.prompts import build_prompt
from app.llm.errors import ProviderFailed, reject_credential_output


class OpenAIStoryGenerator:
    def __init__(self, *, api_key: str, model: str):
        self._api_key, self.model = api_key, model

    async def generate_scene(self, context) -> str:
        try:
            async with AsyncOpenAI(api_key=self._api_key, base_url="https://api.openai.com/v1", timeout=60.0, max_retries=0) as client:
                response = await client.responses.create(model=self.model, input=build_prompt(context), store=False, max_output_tokens=8000)
            if response.status != "completed" or not response.output_text.strip():
                raise ValueError()
            reject_credential_output(response.output_text, self._api_key)
            return response.output_text.strip()
        except Exception:
            raise ProviderFailed("Scene provider failed or returned incomplete output. No automatic retry was made.") from None
