"""Private transport helper, not a domain text-generation interface."""
import httpx
from app.llm.errors import ProviderFailed


async def post_json(url: str, headers: dict, body: dict, *, transport=None):
    try:
        # Fixed official endpoints, no redirects/env proxy, no cookies/retries/client cache.
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=False, trust_env=False, transport=transport) as client:
            response = await client.post(url, headers=headers, json=body)
        if response.status_code != 200:
            raise ValueError()
        return response.json()
    except Exception:
        raise ProviderFailed("Provider request failed. Check settings and provider access; no automatic retry was made.") from None


def import_schema():
    from app.story_import.schemas import ImportAnalysis
    return ImportAnalysis.model_json_schema()


def anthropic_schema(value):
    """Transport-only schema subset. Original Pydantic/evidence validation is mandatory."""
    removed = {"default", "minimum", "maximum", "minLength", "maxLength", "minItems", "maxItems"}
    if isinstance(value, list):
        return [anthropic_schema(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {key: anthropic_schema(item) for key, item in value.items() if key not in removed}
    constraints = {key: item for key, item in value.items() if key in removed - {"default"}}
    if constraints:
        result["description"] = result.get("description", "") + f" Constraints validated by Sandcastle: {constraints}"
    return result
