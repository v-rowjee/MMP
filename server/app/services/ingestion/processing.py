from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import re

import pandas as pd
from fastapi import UploadFile


@dataclass
class ProcessedFile:
    filename: str
    name: str
    original: bytes
    parquet: bytes
    fields: list[dict]
    profile: dict


def process_file(file: UploadFile, max_size: int) -> ProcessedFile:
    filename = file.filename or ""
    if Path(filename).suffix.lower() != ".csv":
        raise ValueError("Only CSV files are supported")
    original = file.file.read()
    if not original or len(original) > max_size:
        raise ValueError("File is empty or too large")
    try:
        frame = pd.read_csv(BytesIO(original))
    except (UnicodeDecodeError, pd.errors.ParserError, ValueError) as error:
        raise ValueError("CSV cannot be read") from error
    if frame.empty or frame.columns.empty:
        raise ValueError("CSV must contain rows and columns")
    original_names = [str(name) for name in frame.columns]
    names = [normalise_name(name) for name in original_names]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate column names after normalisation")
    frame.columns = names
    fields = [
        {
            "name": name,
            "original_name": original_name,
            "position": position,
            "dtype": str(frame[name].dtype),
            "role": "measure" if pd.api.types.is_numeric_dtype(frame[name]) else "dimension",
            "profile": {"null_count": int(frame[name].isna().sum()), "unique_count": int(frame[name].nunique())},
        }
        for position, (name, original_name) in enumerate(zip(names, original_names, strict=True))
    ]
    return ProcessedFile(
        filename=filename,
        name=normalise_name(Path(filename).stem),
        original=original,
        parquet=frame.to_parquet(index=False),
        fields=fields,
        profile={
            "row_count": len(frame),
            "column_count": len(frame.columns),
            "missing_values": int(frame.isna().sum().sum()),
        },
    )


def normalise_name(value: str) -> str:
    name = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "column"
    return ("column_" + name if name[0].isdigit() else name)[:63]
