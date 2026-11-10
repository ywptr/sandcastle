import re
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from app.validation import InputModel
from app.llm.errors import SettingsInvalid

Provider = Literal["openai", "anthropic", "google"]
Role = Literal["creative_writer", "story_importer", "narrative_media_translator"]
PROVIDERS = ("openai", "anthropic", "google")
ROLES = ("creative_writer", "story_importer", "narrative_media_translator")



def validate_scope(scope_id: str):
    if (not isinstance(scope_id, str) or not scope_id.strip() or len(scope_id) > 255
            or scope_id != scope_id.strip() or any(ord(char) < 32 or ord(char) == 127 for char in scope_id)):
        raise SettingsInvalid("An explicit valid IS user subject is required")


def validate_model(value: str | None) -> str | None:
    if value is not None and (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,159}", value)
                              or value.startswith(("sk-", "sk_", "AIza"))):
        raise ValueError("Use a provider model ID, not a URL or credential")
    return value


class ProviderOptions(InputModel):
    default_model: str | None = None

    _model = field_validator("default_model")(validate_model)


class Credentials(InputModel):
    api_key: SecretStr = Field(min_length=1, max_length=4096, repr=False)

    @field_validator("api_key")
    @classmethod
    def usable(cls, value):
        raw = value.get_secret_value()
        if not raw.strip() or any(char.isspace() for char in raw) or not raw.isascii():
            raise ValueError("Invalid provider credential")
        return value


class ProviderUpdate(InputModel):
    enabled: bool | None = None
    credentials: Credentials | None = Field(default=None, repr=False)
    config: ProviderOptions | None = None

    @model_validator(mode="after")
    def supplied_values(self):
        if not self.model_fields_set or any(getattr(self, name) is None for name in self.model_fields_set):
            raise ValueError("Supply settings; use the credential removal endpoint to delete secrets")
        return self


class ProviderView(InputModel):
    provider: Provider
    supported: bool = True
    enabled: bool
    has_credentials: bool
    config: ProviderOptions


class RoleUpdate(InputModel):
    provider: Provider | None = None
    model: str | None = None
    _model = field_validator("model")(validate_model)

    @model_validator(mode="after")
    def automatic_has_no_model(self):
        if self.provider is None and self.model is not None:
            raise ValueError("Automatic routing cannot select a model")
        return self


class RoleView(InputModel):
    role: Role
    provider: Provider | None
    model: str | None
    selected_provider: Provider | None
    selected_model: str | None
    available: bool
