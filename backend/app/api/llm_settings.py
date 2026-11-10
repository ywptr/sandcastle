"""Account settings never accept scope IDs, URLs, or arbitrary config dictionaries."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_identity, get_db
from app.auth.identity import AuthenticatedIdentity
from app.llm.schemas import Provider, ProviderUpdate, ProviderView, Role, RoleUpdate, RoleView
from app.llm.secrets import SecretUnavailable
from app.llm import service


class SafeSettingsRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def safe(request: Request):
            try:
                response = await handler(request)
                response.headers["Cache-Control"] = "no-store"
                return response
            except RequestValidationError:
                # FastAPI's normal errors include submitted inputs, including malformed secrets.
                raise HTTPException(422, "Invalid AI provider settings. Check supported fields and values.") from None
            except service.SettingsInvalid:
                raise HTTPException(422, "Invalid AI settings. Configure and enable the provider with a model before selecting it.") from None
            except (SecretUnavailable, service.SettingsStorageError):
                raise HTTPException(503, "AI settings could not be saved. Check encryption configuration or retry.") from None
        return safe


router = APIRouter(prefix="/settings/llm", tags=["llm-settings"], route_class=SafeSettingsRoute)


@router.get("/providers", response_model=list[ProviderView])
def list_providers(db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return service.list_provider_configs(db, identity.user_id)


@router.get("/providers/{provider}", response_model=ProviderView)
def read_provider(provider: Provider, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return service.provider_view(service.get_provider_config(db, identity.user_id, provider), provider)


@router.put("/providers/{provider}", response_model=ProviderView)
def update_provider(provider: Provider, update: ProviderUpdate, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return service.set_provider_config(db, identity.user_id, provider, update)


@router.delete("/providers/{provider}/credentials", response_model=ProviderView)
def delete_credentials(provider: Provider, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return service.remove_credentials(db, identity.user_id, provider)


@router.get("/roles", response_model=list[RoleView])
def list_roles(db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    return service.list_role_bindings(db, identity.user_id)


@router.put("/roles/{role}", response_model=list[RoleView])
def update_role(role: Role, update: RoleUpdate, db: Session = Depends(get_db), identity: AuthenticatedIdentity = Depends(get_current_identity)):
    service.set_role_binding(db, identity.user_id, role, update)
    return service.list_role_bindings(db, identity.user_id)
