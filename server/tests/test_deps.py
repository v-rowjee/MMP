from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.deps import current_user_id, workspace


class Query:
    def __init__(self, db):
        self.db = db
        self.row = None

    def select(self, *_):
        return self

    def eq(self, *_):
        return self

    def maybe_single(self):
        return self

    def insert(self, row):
        self.row = row
        return self

    def execute(self):
        if self.row:
            self.db.created = self.row
            return SimpleNamespace(data={"id": "workspace_id"})
        return SimpleNamespace(data=self.db.row)


def request(row=None):
    db = SimpleNamespace(row=row, created=None)
    db.auth = SimpleNamespace(
        get_user=lambda token: SimpleNamespace(user=SimpleNamespace(id=f"user_{token}"))
    )
    db.table = lambda _: Query(db)
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db=db)))


def test_current_user_id_is_resolved_from_the_bearer_token():
    assert current_user_id(request(), "Bearer token") == "user_token"


def test_workspace_creates_a_single_workspace_for_the_authenticated_user():
    request_ = request()

    workspace_id = workspace(request_, "user_token")

    assert workspace_id == "workspace_id"
    assert request_.app.state.db.created == {"user_id": "user_token"}


def test_workspace_returns_the_authenticated_users_existing_workspace():
    assert workspace(request({"id": "workspace_id"}), "user_token") == "workspace_id"


def test_current_user_id_rejects_a_missing_bearer_token():
    with pytest.raises(HTTPException, match="Missing bearer token"):
        current_user_id(request(), None)
