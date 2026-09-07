"""Google authentication and verified-user API boundary."""

import os
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Response,
    status,
)
from pydantic import BaseModel, ConfigDict, Field

from scenefoundry.api.projects import Database
from scenefoundry.auth.google_identity import (
    verify_google_id_token,
)
from scenefoundry.domain.user import VerifiedUser
from scenefoundry.storage.users import (
    read_verified_user,
    save_verified_user,
)


router = APIRouter(prefix="/v1/auth", tags=["authentication"])


class GoogleAuthConfiguration(BaseModel):
    """Public browser configuration for Google Identity Services."""

    model_config = ConfigDict(strict=True, extra="forbid")

    enabled: bool
    client_id: str | None


@router.get(
    "/config",
    response_model=GoogleAuthConfiguration,
)
def read_google_auth_configuration() -> GoogleAuthConfiguration:
    """Return only the public OAuth client identifier."""

    client_id = os.environ.get(
        "GOOGLE_OAUTH_CLIENT_ID",
        "",
    ).strip()

    if (
        client_id
        and not client_id.endswith(
            ".apps.googleusercontent.com"
        )
    ):
        client_id = ""

    return GoogleAuthConfiguration(
        enabled=bool(client_id),
        client_id=client_id or None,
    )


class GoogleLoginRequest(BaseModel):
    """A Google ID token received from Google Identity Services."""

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    credential: str = Field(min_length=1, max_length=10_000)


class GoogleLoginResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    created: bool
    user: VerifiedUser


def _authentication_error(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _verify_credential(credential: str) -> VerifiedUser:
    try:
        return verify_google_id_token(credential)
    except ValueError as error:
        raise _authentication_error(
            "Google authentication failed."
        ) from error
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google authentication is not configured.",
        ) from error


def _bearer_credential(
    authorization: Annotated[
        str | None,
        Header(),
    ] = None,
) -> str:
    if authorization is None:
        raise _authentication_error(
            "Authentication is required."
        )

    scheme, separator, credential = authorization.partition(" ")
    if (
        not separator
        or scheme.casefold() != "bearer"
        or not credential.strip()
    ):
        raise _authentication_error(
            "A valid Bearer credential is required."
        )

    return credential.strip()


def require_verified_user(
    credential: Annotated[
        str,
        Depends(_bearer_credential),
    ],
) -> VerifiedUser:
    """Verify the Google credential for one protected request."""

    return _verify_credential(credential)


CurrentUser = Annotated[
    VerifiedUser,
    Depends(require_verified_user),
]


@router.post(
    "/google",
    response_model=GoogleLoginResponse,
    status_code=status.HTTP_201_CREATED,
)
def login_with_google(
    request: GoogleLoginRequest,
    response: Response,
    db: Database,
) -> GoogleLoginResponse:
    """Verify Google identity before creating the user record."""

    user = _verify_credential(request.credential)

    try:
        created = save_verified_user(db, user=user)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    if not created:
        response.status_code = status.HTTP_200_OK

    return GoogleLoginResponse(
        created=created,
        user=user,
    )


@router.get(
    "/me",
    response_model=VerifiedUser,
)
def read_current_user(
    current_user: CurrentUser,
    db: Database,
) -> VerifiedUser:
    """Return the stored profile for the verified token owner."""

    try:
        stored = read_verified_user(
            db,
            uid=current_user.uid,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Verified account registration is required."
            ),
        ) from error

    if (
        stored.uid != current_user.uid
        or stored.email != current_user.email
        or stored.provider != current_user.provider
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Stored account identity is inconsistent.",
        )

    return stored
