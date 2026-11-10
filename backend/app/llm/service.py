from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.llm import LLMProviderConfig, LLMRoleBinding
from app.llm.schemas import PROVIDERS, ROLES, ProviderUpdate, ProviderView, RoleUpdate, RoleView, validate_scope
from app.llm.secrets import encrypt_credentials

from app.llm.errors import SettingsInvalid, SettingsStorageError


def get_provider_config(db: Session, scope_id: str, provider: str):
    validate_scope(scope_id)
    if provider not in PROVIDERS:
        raise SettingsInvalid("Unsupported LLM provider")
    return db.scalar(select(LLMProviderConfig).where(LLMProviderConfig.scope_type == "user",
        LLMProviderConfig.scope_id == scope_id, LLMProviderConfig.provider == provider))


def provider_view(row, provider):
    return ProviderView(provider=provider, enabled=row.enabled if row else False,
        has_credentials=bool(row and row.encrypted_credentials), config=row.config if row else {})


def list_provider_configs(db: Session, scope_id: str):
    return [provider_view(get_provider_config(db, scope_id, provider), provider) for provider in PROVIDERS]


def _commit(db):
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise SettingsStorageError("Provider settings could not be saved. Please retry.") from None


def set_provider_config(db: Session, scope_id: str, provider: str, update: ProviderUpdate):
    row = get_provider_config(db, scope_id, provider)
    # Encrypt before mutating anything; encryption failures cannot partially change config.
    encrypted = encrypt_credentials(scope_id, provider, update.credentials.api_key.get_secret_value()) if update.credentials else None
    if row is None:
        row = LLMProviderConfig(scope_type="user", scope_id=scope_id, provider=provider, enabled=False, config={})
        db.add(row)
    if "enabled" in update.model_fields_set:
        row.enabled = update.enabled
    if "config" in update.model_fields_set:
        row.config = update.config.model_dump()
    if encrypted is not None:
        row.encrypted_credentials = encrypted
    _commit(db)
    return provider_view(row, provider)


def remove_credentials(db: Session, scope_id: str, provider: str):
    row = get_provider_config(db, scope_id, provider)
    if row:
        row.encrypted_credentials = None
        row.enabled = False
        _commit(db)
    return provider_view(row, provider)


def set_role_binding(db: Session, scope_id: str, role: str, update: RoleUpdate):
    validate_scope(scope_id)
    if role not in ROLES:
        raise SettingsInvalid("Unsupported LLM role")
    row = db.get(LLMRoleBinding, ("user", scope_id, role))
    if update.provider is None:
        if row:
            db.delete(row)
    else:
        provider = get_provider_config(db, scope_id, update.provider)
        if not provider or not provider.enabled or not provider.encrypted_credentials or not (update.model or provider.config.get("default_model")):
            raise SettingsInvalid("Configure and enable this provider with a model before selecting it")
        if row is None:
            row = LLMRoleBinding(scope_type="user", scope_id=scope_id, role=role)
            db.add(row)
        row.provider, row.model = update.provider, update.model
    _commit(db)


def select_provider(db: Session, scope_id: str, role: str):
    validate_scope(scope_id)
    if role not in ROLES:
        raise SettingsInvalid("Unsupported LLM role")
    binding = db.get(LLMRoleBinding, ("user", scope_id, role))
    for provider in [binding.provider] if binding else PROVIDERS:
        row = get_provider_config(db, scope_id, provider)
        model = (binding.model if binding else None) or (row.config.get("default_model") if row else None)
        if row and row.enabled and row.encrypted_credentials and model:
            return row, model
    return None


def list_role_bindings(db: Session, scope_id: str):
    result = []
    for role in ROLES:
        binding = db.get(LLMRoleBinding, ("user", scope_id, role))
        selected = select_provider(db, scope_id, role)
        result.append(RoleView(role=role, provider=binding.provider if binding else None, model=binding.model if binding else None,
            selected_provider=selected[0].provider if selected else None, selected_model=selected[1] if selected else None, available=selected is not None))
    return result
