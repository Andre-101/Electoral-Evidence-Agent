from __future__ import annotations

from decimal import Decimal
from statistics import median


def to_decimal(value) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def median_decimal(values) -> Decimal | None:
    cleaned = [to_decimal(v) for v in values if v is not None]
    cleaned = [v for v in cleaned if v is not None]
    if not cleaned:
        return None
    return Decimal(str(median(cleaned)))


def mad_decimal(values, center: Decimal | None = None) -> Decimal | None:
    cleaned = [to_decimal(v) for v in values if v is not None]
    cleaned = [v for v in cleaned if v is not None]
    if not cleaned:
        return None
    center = center if center is not None else median_decimal(cleaned)
    deviations = [abs(v - center) for v in cleaned]
    return Decimal(str(median(deviations)))


def robust_z(value, center: Decimal | None, mad: Decimal | None) -> Decimal | None:
    val = to_decimal(value)
    if val is None or center is None or mad is None or mad == 0:
        return None
    return Decimal("0.6745") * (val - center) / mad
