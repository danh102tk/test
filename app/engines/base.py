from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TextEngineResult:
    engine: str
    pages: list[dict[str, Any]] = field(default_factory=list)
    # each page: {"page": int, "text": str, ...}

    @property
    def texts(self) -> list[str]:
        return [p.get("text", "") for p in self.pages]
