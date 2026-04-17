from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID


def to_jsonable(obj: Any) -> Any:
    """Convert dataclasses, enums, UUIDs, and datetimes to JSON-friendly structures."""

    if obj is None:
        return None
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if is_dataclass(obj):
        d: dict[str, Any] = {}
        for f in fields(obj):
            v = getattr(obj, f.name)
            d[f.name] = to_jsonable(v)
        return d
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(x) for x in obj]
    return obj


