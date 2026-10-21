from urllib.parse import urlencode

import httpx

from app.auth.config import AuthConfig
from app.auth.identity import (
    AuthenticatedIdentity,
)


class ISAuthenticationError(Exception):
    pass


class ISOIDCClient:
    def __init__(
        self,
        config: AuthConfig,
    ) -> None:
        self.config = config

        self.authorization_endpoint = (
            f"{config.issuer}/oauth2/authorize"
        )

        self.token_endpoint = (
            f"{config.issuer}/oauth2/token"
        )

        self.userinfo_endpoint = (
            f"{config.issuer}/oauth2/userinfo"
        )


    def build_authorization_url(
        self,
        *,
        state: str,
        code_challenge: str,
    ) -> str:
        query = urlencode({
            "client_id":
                self.config.client_id,

            "redirect_uri":
                self.config.callback_url,

            "response_type":
                "code",

            "scope":
                "openid profile email",

            "state":
                state,

            "code_challenge":
                code_challenge,

            "code_challenge_method":
                "S256",
        })

        return (
            f"{self.authorization_endpoint}"
            f"?{query}"
        )


    async def exchange_code(
        self,
        *,
        code: str,
        code_verifier: str,
    ) -> str:
        async with httpx.AsyncClient(
            timeout=10.0
        ) as client:
            response = await client.post(
                self.token_endpoint,
                data={
                    "grant_type":
                        "authorization_code",

                    "code":
                        code,

                    "redirect_uri":
                        self.config.callback_url,

                    "client_id":
                        self.config.client_id,

                    "code_verifier":
                        code_verifier,
                },
                auth=httpx.BasicAuth(
                    self.config.client_id,
                    self.config.client_secret,
                ),
            )

        if response.is_error:
            raise ISAuthenticationError(
                "IS token exchange failed"
            )

        payload = response.json()

        access_token = payload.get(
            "access_token"
        )

        if not access_token:
            raise ISAuthenticationError(
                "IS returned no access token"
            )

        return access_token


    async def get_identity(
        self,
        access_token: str,
    ) -> AuthenticatedIdentity:
        async with httpx.AsyncClient(
            timeout=10.0
        ) as client:
            response = await client.get(
                self.userinfo_endpoint,
                headers={
                    "Authorization":
                        f"Bearer {access_token}"
                },
            )

        if response.is_error:
            raise ISAuthenticationError(
                "IS userinfo request failed"
            )

        payload = response.json()

        subject = payload.get("sub")
        email = payload.get("email")

        if not subject or not email:
            raise ISAuthenticationError(
                "IS identity is incomplete"
            )

        return AuthenticatedIdentity(
            user_id=subject,
            email=email,
            name=payload.get("name"),
        )