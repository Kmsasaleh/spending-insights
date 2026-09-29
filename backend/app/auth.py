from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db import get_client

bearer = HTTPBearer(auto_error=False)


def current_user_id(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> str:
    """Return the id of the signed-in user, or reject the request with 401.

    The frontend sends 'Authorization: Bearer <token>'. We ask Supabase Auth
    whether the token is genuine and unexpired, and whose it is.
    """
    if creds is None:
        raise HTTPException(401, "Please sign in")
    try:
        response = get_client().auth.get_user(creds.credentials)
    except Exception:
        raise HTTPException(401, "Your session has expired. Please sign in again.") from None
    if response is None or response.user is None:
        raise HTTPException(401, "Your session has expired. Please sign in again.")
    return response.user.id