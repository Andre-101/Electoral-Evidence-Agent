from __future__ import annotations
import csv
from dataclasses import dataclass
from pathlib import Path
import polars as pl

SUPPORTED_ENCODINGS = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
SUPPORTED_SEPARATORS = [",", ";", "\t", "|"]

@dataclass(frozen=True)
class FileDetectionResult:
    detected_format: str
    detected_encoding: str
    detected_separator: str
    columns: list[str]

def detect_encoding(path: str | Path) -> str:
    sample = Path(path).read_bytes()[:8192]
    for enc in SUPPORTED_ENCODINGS:
        try:
            sample.decode(enc)
            return enc
        except UnicodeDecodeError:
            pass
    return "latin-1"

def detect_separator(path: str | Path, encoding: str) -> str:
    text = Path(path).read_text(encoding=encoding, errors="replace")[:8192]
    try:
        return csv.Sniffer().sniff(text, delimiters=",;\t|").delimiter
    except csv.Error:
        lines = [ln for ln in text.splitlines()[:5] if ln.strip()]
        scores = {sep: sum(ln.count(sep) for ln in lines) for sep in SUPPORTED_SEPARATORS}
        return max(scores, key=scores.get)

def read_csv(path: str | Path, encoding: str | None = None, separator: str | None = None) -> pl.DataFrame:
    file_path = Path(path)
    enc = encoding or detect_encoding(file_path)
    sep = separator or detect_separator(file_path, enc)
    return pl.read_csv(file_path, separator=sep, encoding=enc, infer_schema_length=500, null_values=["", "NULL", "null", "NA", "N/A"])

def detect_file(path: str | Path) -> FileDetectionResult:
    file_path = Path(path)
    if file_path.suffix.lower() not in [".csv", ".txt"]:
        raise ValueError(f"Unsupported file format: {file_path.suffix}")
    enc = detect_encoding(file_path)
    sep = detect_separator(file_path, enc)
    df = read_csv(file_path, enc, sep)
    return FileDetectionResult("CSV", enc, sep, df.columns)
