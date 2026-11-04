"""Interpret Ontech's parallel unit arrays without inventing missing values."""

import math
from datetime import UTC, datetime
from typing import Any


def value(status: dict[str, Any], field: str, index: int) -> Any:
    items = status.get("units", {}).get(field, [])
    return items[index] if isinstance(items, list) and index < len(items) else None


def number(raw: Any) -> float | None:
    try:
        result = float(raw)
        return result if math.isfinite(result) else None
    except TypeError, ValueError:
        return None


def boolean(raw: Any) -> bool | None:
    if raw in (1, "1"):
        return True
    if raw in (0, "0"):
        return False
    return None


def fresh(status: dict[str, Any], now: datetime | None = None) -> bool:
    dates = []
    for field in ("statusUTC", "temperaturesUTC"):
        try:
            date = datetime.fromisoformat(status[field])
            if date.tzinfo is None:
                date = date.replace(tzinfo=UTC)
            dates.append(date)
        except KeyError, TypeError, ValueError, AttributeError:
            pass
    if not dates:
        return False
    age = ((now or datetime.now(UTC)) - max(dates)).total_seconds()
    return -300 <= age < 1800


def unit_indices(status: dict[str, Any]) -> list[int]:
    units = status.get("units", {}).get("connected", [])
    if not isinstance(units, list):
        return []
    return [i for i, model in enumerate(units[:8]) if number(model)]


def has_relay(status: dict[str, Any], index: int) -> bool:
    model = number(value(status, "connected", index))
    settings = status.get("settings", [])
    garage = (
        index == 0
        and isinstance(settings, list)
        and len(settings) > 10
        and str(settings[10]) == "1"
    )
    return model in (9010, 9015, 9025, 9035, 9040, 9060, 9065) and not garage


def relay_command(iccid: str, index: int, on: bool) -> dict[str, Any]:
    if not isinstance(index, int) or not 0 <= index < 8:
        raise ValueError("Invalid relay index")
    return {"command": "sms", "iccid": iccid, "data": f"{int(on)}*{index + 1}#"}
