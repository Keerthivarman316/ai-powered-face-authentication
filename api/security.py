from fastapi import Depends, HTTPException, status
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


# ============================================================
# API KEY VALIDATION
# ============================================================

def validate_api_key(
    api_key: str | None = Depends(API_KEY_HEADER),
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

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key.",
        )

    # --------------------------------------------------------
    # Constant-time comparison
    # --------------------------------------------------------

    if not secrets.compare_digest(
        api_key,
        expected_api_key,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )

    return True