from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import polars as pl

def normalize_key(value: str) -> str:
    return (value.strip().lower().replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u").replace("ñ","n").replace(" ","_"))

@dataclass(frozen=True)
class ColumnProfile:
    source_field_name: str
    inferred_type: str
    null_rate: float
    unique_count: int
    sample_values: list[Any]
    candidate_for: str | None = None

def infer_candidate(column_name: str, aliases: dict[str, list[str]]) -> str | None:
    normalized = normalize_key(column_name)
    for canonical, values in aliases.items():
        if normalized in [normalize_key(v) for v in values]:
            return canonical
    return None

def profile_dataframe(df: pl.DataFrame, aliases: dict[str, list[str]] | None = None) -> list[ColumnProfile]:
    aliases = aliases or {}
    total = df.height
    out = []
    for col in df.columns:
        s = df[col]
        vals = s.drop_nulls().unique().head(5).to_list() if total else []
        out.append(ColumnProfile(col, str(s.dtype), float(s.null_count()/total) if total else 0.0, s.n_unique(), vals, infer_candidate(col, aliases)))
    return out
