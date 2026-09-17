from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class PollSourceAdapter(ABC):
    name: str

    @abstractmethod
    def fetch(self) -> list[dict[str, Any]]:
        """Return normalized poll objects. Never mutate stored data directly."""
        raise NotImplementedError
