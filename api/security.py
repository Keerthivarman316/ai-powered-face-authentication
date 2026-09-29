from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import APIKeyHeader
import os
import secrets


# ============================================================
# API KEY CONFIGURATION
# ============================================================

API_KEY_HEADER = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
)

SESSION_COOKIE = "face_auth_session"


# ============================================================
# API KEY VALIDATION
# ============================================================

def validate_api_key(
    api_key: str | None = Depends(API_KEY_HEADER),
    session_key: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE,
    ),
):
    """
    Validate the client's API key.

    The expected server-side API key is stored in:

        FACE_AUTH_API_KEY
    """

    expected_api_key = os.getenv("FACE_AUTH_API_KEY")

    # --------------------------------------------------------
    # Server configuration check
    # --------------------------------------------------------

    if not expected_api_key:
        raise RuntimeError(
            "FACE_AUTH_API_KEY environment variable "
            "is not configured."
        )

    # --------------------------------------------------------
    # Missing API key
    # --------------------------------------------------------

    provided_key = api_key or session_key

    if not provided_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API authentication.",
        )

    # --------------------------------------------------------
    # Constant-time comparison
    # --------------------------------------------------------

    if not secrets.compare_digest(
        provided_key,
        expected_api_key,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )

    return True