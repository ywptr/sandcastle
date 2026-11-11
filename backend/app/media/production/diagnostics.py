"""Fixed diagnostics only: never serialize provider exceptions, inputs, or payloads."""
from app.llm.errors import ProviderFailed

CATEGORIES = frozenset({"provider_request_failed", "provider_incomplete",
    "provider_structured_output_invalid", "schema_validation_failed",
    "domain_validation_failed", "unexpected_translation_failure"})


REASONS = frozenset({"invalid_json", "invalid_proposal_schema", "sdk_parse_failed", "request_failed",
    "response_not_completed", "parsed_output_missing", "credential_output_rejected",
    "duration_mismatch", "nonconsecutive_beats"})


def schema_reason(error):
    for item in error.errors(include_input=False, include_context=False):
        message = item["msg"]
        if message == "Value error, Target duration must equal the sum of estimated beat durations":
            return "duration_mismatch"
        if message == "Value error, Production beats must be consecutively numbered in display order":
            return "nonconsecutive_beats"
    return "invalid_proposal_schema"


class TranslationFailed(ProviderFailed):
    def __init__(self, category, reason):
        self.category = category if category in CATEGORIES else "unexpected_translation_failure"
        # Reasons must be fixed literals supplied by application code.
        self.reason = reason if reason in REASONS else "invalid_proposal_schema"
        super().__init__("Narrative translation could not produce a valid plan.")


def parse_proposal(text, schema):
    import json
    from pydantic import ValidationError

    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        raise TranslationFailed("provider_structured_output_invalid", "invalid_json") from None
    try:
        return schema.model_validate(data)
    except ValidationError as error:
        raise TranslationFailed("schema_validation_failed", schema_reason(error)) from None
