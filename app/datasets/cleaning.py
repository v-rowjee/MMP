"""Dataset column cleaning."""

import re

import polars as pl


class IngestionCleaner:
    def clean_df(self, df: pl.DataFrame) -> pl.DataFrame:
        cleaned_names = self._normalise_column_names(df.columns)
        df = df.rename(dict(zip(df.columns, cleaned_names, strict=True)))
        string_columns = [
            name for name, dtype in df.schema.items() if dtype == pl.String
        ]
        if not string_columns:
            return df
        return df.with_columns(
            pl.col(name).str.strip_chars().replace("", None).alias(name)
            for name in string_columns
        )

    def normalise_name(self, value: str) -> str:
        name = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "column"
        return ("column_" + name if name[0].isdigit() else name)[:63]

    def _normalise_column_names(self, names: list[str]) -> list[str]:
        cleaned = [self.normalise_name(name) for name in names]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Duplicate column names after normalisation")
        return cleaned
