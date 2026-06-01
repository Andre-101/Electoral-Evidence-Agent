from __future__ import annotations

import re
import unicodedata
from decimal import Decimal
from typing import Any


SPECIAL_BLANK_LABELS = {"VOTO EN BLANCO", "BLANCO", "VOTOS EN BLANCO"}
SPECIAL_NULL_LABELS = {"VOTO NULO", "NULO", "VOTOS NULOS"}
SPECIAL_UNMARKED_LABELS = {"NO MARCADO", "NO MARCADOS", "VOTO NO MARCADO"}


def normalize_key(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().upper()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_label(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def parse_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, Decimal):
        return int(value)
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(".", "").replace(",", "")
    return int(text)


def infer_option_type(candidate_label: str | None, party_label: str | None) -> str:
    candidate_key = normalize_key(candidate_label)
    party_key = normalize_key(party_label)
    combined = candidate_key or party_key
    if combined in SPECIAL_BLANK_LABELS:
        return "BLANK"
    if combined in SPECIAL_NULL_LABELS:
        return "NULL"
    if combined in SPECIAL_UNMARKED_LABELS:
        return "UNMARKED"
    if candidate_key:
        return "CANDIDATE"
    if party_key:
        return "PARTY"
    return "OTHER"
