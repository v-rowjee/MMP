from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import polars as pl
from fastapi import UploadFile

from app.datasets.cleaning import IngestionCleaner


@dataclass
class ProcessedFile:
    filename: str
    name: str
    original: bytes
    parquet: bytes
    fields: list[dict]
    profile: dict


def process_file(file: UploadFile, max_size: int) -> ProcessedFile:
    cleaner = IngestionCleaner()
    filename = file.filename or ""
    if Path(filename).suffix.lower() != ".csv":
        raise ValueError("Only CSV files are supported")
    original = file.file.read()
    if not original or len(original) > max_size:
        raise ValueError("File is empty or too large")
    try:
        frame = pl.read_csv(BytesIO(original))
    except (pl.exceptions.PolarsError, UnicodeDecodeError, ValueError) as error:
        raise ValueError("CSV cannot be read") from error
    if frame.is_empty() or not frame.columns:
        raise ValueError("CSV must contain rows and columns")
    original_names = [str(name) for name in frame.columns]
    frame = cleaner.clean_df(frame)
    fields = [
        {
            "name": name,
            "original_name": original_name,
            "position": position,
            "dtype": str(frame.schema[name]),
            "role": "measure" if frame.schema[name].is_numeric() else "dimension",
            "profile": {
                "null_count": frame.get_column(name).null_count(),
                "unique_count": frame.get_column(name).n_unique(),
            },
        }
        for position, (name, original_name) in enumerate(
            zip(frame.columns, original_names, strict=True)
        )
    ]
    missing_values = sum(frame.get_column(name).null_count() for name in frame.columns)
    parquet = BytesIO()
    frame.write_parquet(parquet)
    return ProcessedFile(
        filename=filename,
        name=cleaner.normalise_name(Path(filename).stem),
        original=original,
        parquet=parquet.getvalue(),
        fields=fields,
        profile={
            "row_count": frame.height,
            "column_count": frame.width,
            "missing_values": missing_values,
        },
    )
