from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


supabase_bearer = HTTPBearer(
    scheme_name="SupabaseBearer",
    bearerFormat="JWT",
    description="Enter a Supabase user access token.",
    auto_error=False,
)


def current_user_id(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(supabase_bearer)
    ],
) -> str:
    if not credentials:
        raise HTTPException(401, "Missing bearer token")
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "Invalid bearer token")
    try:
        user = request.app.state.db.auth.get_user(credentials.credentials).user
        if not user:
            raise ValueError("User not found")
        return user.id
    except Exception:
        raise HTTPException(401, "Invalid bearer token")


def workspace(
    request: Request,
    user_id: Annotated[str, Depends(current_user_id)],
) -> str:
    db = request.app.state.db
    response = (
        db.table("workspaces")
        .select("id")
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    row = response.data if response else None
    if row:
        return row["id"]

    created = db.table("workspaces").insert({"user_id": user_id}).execute().data
    if not created:
        raise RuntimeError("Workspace creation failed")
    return created[0]["id"] if isinstance(created, list) else created["id"]
