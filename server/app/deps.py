from uuid import uuid4

from fastapi import Header, HTTPException, Request


def workspace(request: Request, authorization: str | None = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    try:
        db = request.app.state.db
        user = db.auth.get_user(authorization[7:]).user
        row = db.table("workspaces").select("id").eq("user_id", user.id).maybe_single().execute().data
        if row:
            return row["id"]
        workspace_id = f"ws_{uuid4().hex[:8]}"
        db.table("workspaces").insert({"id": workspace_id, "user_id": user.id}).execute()
        return workspace_id
    except Exception:
        raise HTTPException(401, "Invalid bearer token")
