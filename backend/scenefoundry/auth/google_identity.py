"""Verify Google ID tokens without trusting browser claims."""

import os
from collections.abc import Callable
from typing import Any

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from scenefoundry.domain.user import VerifiedUser


TokenVerifier = Callable[[str, object, str], dict[str, Any]]

_GOOGLE_ISSUERS = {
    "accounts.google.com",
    "https://accounts.google.com",
}


def _resolve_client_id(explicit: str | None) -> str:
    client_id = (
        explicit
        if explicit is not None
        else os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
    ).strip()

    if not client_id:
        raise RuntimeError(
            "GOOGLE_OAUTH_CLIENT_ID is required."
        )

    return client_id


def verify_google_id_token(
    credential: str,
    *,
    client_id: str | None = None,
    verifier: TokenVerifier | None = None,
) -> VerifiedUser:
    """Validate signature, audience and verified-email claims."""

    if not isinstance(credential, str):
        raise TypeError("Google credential must be text.")

    credential = credential.strip()
    if not credential:
        raise ValueError("Google credential cannot be blank.")
    if len(credential) > 10_000:
        raise ValueError("Google credential is too large.")

    audience = _resolve_client_id(client_id)
    verify = verifier or id_token.verify_oauth2_token

    try:
        claims = verify(
            credential,
            google_requests.Request(),
            audience,
        )
    except ValueError as error:
        raise ValueError(
            "Google credential verification failed."
        ) from error

    if not isinstance(claims, dict):
        raise ValueError(
            "Google returned malformed identity claims."
        )
    if claims.get("aud") != audience:
        raise ValueError(
            "Google credential audience is invalid."
        )
    if claims.get("iss") not in _GOOGLE_ISSUERS:
        raise ValueError(
            "Google credential issuer is invalid."
        )
    if claims.get("email_verified") is not True:
        raise ValueError(
            "Google account email is not verified."
        )

    uid = str(claims.get("sub", "")).strip()
    email = str(claims.get("email", "")).strip()
    name = str(claims.get("name", "")).strip()
    picture = str(claims.get("picture", "")).strip()

    if not name and email:
        name = email.partition("@")[0]

    return VerifiedUser(
        uid=uid,
        email=email,
        email_verified=True,
        name=name,
        picture_url=picture or None,
    )
