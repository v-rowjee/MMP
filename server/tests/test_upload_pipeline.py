from io import BytesIO
from types import SimpleNamespace

import pandas as pd
import pytest
from fastapi import FastAPI, UploadFile
from fastapi.testclient import TestClient

from app.api.upload import router
from app.services.ingestion.service import IngestionService


class Query:
    def __init__(self, db, table):
        self.db, self.table, self.data, self.id = db, table, None, None

    def insert(self, data):
        self.data = data
        return self

    def delete(self):
        self.data = "delete"
        return self

    def eq(self, _, value):
        self.id = value
        return self

    def execute(self):
        if self.table == self.db.fail:
            raise RuntimeError("database error")
        if self.data == "delete":
            self.db.rows["datasets"] = []
        else:
            self.db.rows.setdefault(self.table, []).extend(self.data if isinstance(self.data, list) else [self.data])
        return SimpleNamespace(data=None)


class Storage:
    def __init__(self):
        self.files = {}

    def upload(self, path, data, _):
        self.files[path] = data

    def remove(self, paths):
        for path in paths:
            self.files.pop(path, None)


class Database:
    def __init__(self, fail=None):
        self.rows, self.fail, self.bucket = {}, fail, Storage()
        self.storage = SimpleNamespace(from_=lambda _: self.bucket)

    def table(self, name):
        return Query(self, name)


def file(data, name="sales.csv"):
    return UploadFile(BytesIO(data), filename=name)


def upload(db, *files):
    if not files:
        files = (file(b"Order ID,Amount\n1,10\n2,20\n"),)
    elif len(files) == 1 and isinstance(files[0], bytes):
        files = (file(files[0]),)
    return IngestionService(db, "upload", 1_000_000).upload_files("ws_12345678", list(files))


def test_upload_creates_profile_metadata_and_parquet():
    db = Database()

    response = upload(db)

    dataset = db.rows["datasets"][0]
    assert response.processing_status == "uploaded"
    assert [item.model_dump() for item in response.files] == [
        {"filename": "sales.csv", "row_count": 2, "column_count": 2}
    ]
    assert dataset["meta"]["profile"] == {"row_count": 2, "column_count": 2, "missing_values": 0}
    assert "analysis_runs" not in db.rows
    parquet = pd.read_parquet(BytesIO(db.bucket.files[dataset["meta"]["parquet_path"]]))
    assert list(parquet.columns) == ["order_id", "amount"]


@pytest.mark.parametrize("data,name", [(b"", "empty.csv"), (b"a\n1\n", "data.txt")])
def test_rejects_invalid_files(data, name):
    with pytest.raises(ValueError):
        IngestionService(Database(), "upload", 1_000_000).upload_files("ws_12345678", [file(data, name)])


def test_rejects_duplicate_normalised_columns():
    with pytest.raises(ValueError, match="Duplicate"):
        upload(Database(), b"Order ID,order-id\n1,2\n")


def test_upload_accepts_multiple_files():
    db = Database()

    response = upload(
        db,
        file(b"Order ID,Amount\n1,10\n", "sales.csv"),
        file(b"Customer,Spend\nAda,20\n", "customers.csv"),
    )

    assert [item.filename for item in response.files] == ["sales.csv", "customers.csv"]
    assert len(db.rows["datasets"]) == 2


def test_rejects_files_with_duplicate_normalised_names():
    with pytest.raises(ValueError, match="unique names"):
        upload(
            Database(),
            file(b"a\n1\n", "sales-data.csv"),
            file(b"a\n2\n", "sales data.csv"),
        )


def test_cleans_text_columns_without_removing_rows():
    db = Database()

    upload(db, b" Customer Name ,Note\n  Alice  ,   \n")

    dataset = db.rows["datasets"][0]
    parquet = pd.read_parquet(BytesIO(db.bucket.files[dataset["meta"]["parquet_path"]]))
    assert list(parquet.columns) == ["customer_name", "note"]
    assert parquet.iloc[0]["customer_name"] == "Alice"
    assert pd.isna(parquet.iloc[0]["note"])
    assert dataset["meta"]["profile"]["missing_values"] == 1


def test_cleans_up_after_database_failure():
    db = Database(fail="dataset_fields")

    with pytest.raises(RuntimeError):
        upload(db)

    assert not db.rows["datasets"]
    assert not db.bucket.files


def test_unauthenticated_upload_is_rejected():
    app = FastAPI()
    app.include_router(router)

    assert TestClient(app).post("/upload", files={"files": ("sales.csv", b"a\n1\n", "text/csv")}).status_code == 401
