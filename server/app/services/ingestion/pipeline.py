from uuid import uuid4


def upload_files(db, workspace_id, files):
    uploaded = []
    for file in files:
        if not file.filename or not file.filename.lower().endswith(".csv"):
            raise ValueError("CSV files only")
        dataset_id = str(uuid4())
        name = file.filename.rsplit(".", 1)[0].lower().replace(" ", "_").replace("-", "_")
        path = f"{workspace_id}/{dataset_id}.csv"
        db.storage.from_("upload").upload(path, file.file, {"upsert": "false", "content-type": "text/csv"})
        db.table("datasets").insert({
            "id": dataset_id, "workspace_id": workspace_id, "name": name,
            "source_filename": file.filename, "status": "uploaded", "meta": {"storage_path": path},
        }).execute()
        uploaded.append({"id": dataset_id, "name": name, "path": path})
    return uploaded
