import unittest
from types import SimpleNamespace

from app.deps import workspace


class Query:
    def __init__(self, db): self.db, self.row = db, None
    def select(self, *_): return self
    def eq(self, *_): return self
    def maybe_single(self): return self
    def insert(self, row): self.row = row; return self
    def execute(self):
        if self.row: self.db.created = self.row
        return SimpleNamespace(data=self.db.row)


class WorkspaceTest(unittest.TestCase):
    def test_creates_workspace(self):
        db = SimpleNamespace(row=None, created=None)
        db.auth = SimpleNamespace(get_user=lambda _: SimpleNamespace(user=SimpleNamespace(id="user")))
        db.table = lambda _: Query(db)
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db=db)))
        workspace_id = workspace(request, "Bearer token")
        self.assertEqual(db.created["id"], workspace_id)
        self.assertEqual(db.created["user_id"], "user")
