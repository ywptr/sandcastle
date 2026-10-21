import httpx

from app.auth.port import (
    AuthenticatedIdentity,
    IdentityProviderUnavailable,
    IdentityRejected,
)


class IGIdentityProvider:
    def __init__(
        self,
        base_url: str,
    ) -> None:
        self.base_url = base_url.rstrip("/")


    async def resolve_identity(
        self,
        session_token: str,
    ) -> AuthenticatedIdentity:
        response = await self._fetch_identity(
            session_token
        )

        if response.status_code == 401:
            raise IdentityRejected()

        if response.is_error:
            raise IdentityProviderUnavailable()

        payload = response.json()

        return AuthenticatedIdentity(
            user_id=payload["user_id"],
            email=payload["email"],
            name=payload.get("name"),
        )


    async def _fetch_identity(
        self,
        session_token: str,
    ) -> httpx.Response:
        try:
            async with httpx.AsyncClient(
                timeout=5.0
            ) as client:
                return await client.get(
                    f"{self.base_url}/v2/auth/me",
                    cookies={
                        "ig_session":
                            session_token,
                    },
                )

        except httpx.HTTPError as exc:
            raise IdentityProviderUnavailable() \
                from exc