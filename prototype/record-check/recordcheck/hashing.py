"""Canonical JSON and SHA-256. One place, so every hash in the system is comparable."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel


def canonical(obj: Any) -> str:
    if isinstance(obj, BaseModel):
        obj = obj.model_dump(mode="json")
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def sha256(obj: Any) -> str:
    data = obj if isinstance(obj, (bytes, bytearray)) else canonical(obj).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def short(h: str | None, n: int = 4) -> str:
    """9f2c…a71e style, for screens."""
    if not h:
        return "—"
    return f"{h[:n]}…{h[-n:]}"
