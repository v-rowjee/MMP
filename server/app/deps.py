from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request


def current_user_id(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    try:
        user = request.app.state.db.auth.get_user(authorization[7:]).user
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
    row = (
        db.table("workspaces")
        .select("id")
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
        .data
    )
    if row:
        return row["id"]

    created = db.table("workspaces").insert({"user_id": user_id}).execute().data
    if not created:
        raise RuntimeError("Workspace creation failed")
    return created[0]["id"] if isinstance(created, list) else created["id"]
