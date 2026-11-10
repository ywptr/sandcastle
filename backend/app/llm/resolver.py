"""Operation-scoped composition of capability-specific adapters. Never caches secrets."""
from fastapi import HTTPException
from app.llm.secrets import SecretUnavailable, decrypt_credentials
from app.llm.routing import LLMActorContext, resolve_provider_for_role


def resolve_adapter(db, user_id: str, role: str, *, capability: str | None = None):
    selection = resolve_provider_for_role(db, LLMActorContext(user_id), role)
    if selection is None:
        raise HTTPException(503, "No usable AI provider for this task. Configure AI Providers in Settings.")
    row, model = selection.configuration, selection.model
    try:
        key = decrypt_credentials(selection.scope_id, row.provider, row.encrypted_credentials)
        if capability == "creative_direction":
            from app.creative_direction.recommender import OpenAIRecommender, AnthropicRecommender, GoogleRecommender
            Adapter = {"openai": OpenAIRecommender, "anthropic": AnthropicRecommender, "google": GoogleRecommender}[row.provider]
        elif role == "narrative_media_translator":
            if row.provider == "openai":
                from app.media.production.adapters.openai import OpenAINarrativeMediaTranslator as Adapter
            elif row.provider == "anthropic":
                from app.media.production.adapters.anthropic import AnthropicNarrativeMediaTranslator as Adapter
            else:
                from app.media.production.adapters.google import GoogleNarrativeMediaTranslator as Adapter
        elif row.provider == "openai":
            if role == "creative_writer":
                from app.stories.adapters.openai_generator import OpenAIStoryGenerator as Adapter
            else:
                from app.story_import.openai_analyzer import OpenAIStoryImportAnalyzer as Adapter
        elif row.provider == "anthropic":
            from app.llm.providers.anthropic import AnthropicStoryGenerator, AnthropicStoryImportAnalyzer
            Adapter = AnthropicStoryGenerator if role == "creative_writer" else AnthropicStoryImportAnalyzer
        else:
            from app.llm.providers.google import GoogleStoryGenerator, GoogleStoryImportAnalyzer
            Adapter = GoogleStoryGenerator if role == "creative_writer" else GoogleStoryImportAnalyzer
        return Adapter(api_key=key, model=model)
    except (ImportError, SecretUnavailable):
        raise HTTPException(503, "AI provider is unavailable. Check provider settings or contact the operator.") from None
