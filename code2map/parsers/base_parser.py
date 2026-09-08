from __future__ import annotations

from abc import ABC, abstractmethod

from code2map.models.symbol import Symbol


class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> tuple[list[Symbol], list[str]]:
        raise NotImplementedError
