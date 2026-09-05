"""The adapter contract. All offsets are Unicode characters, end-exclusive."""

from dataclasses import dataclass, field
from typing import Protocol
import hashlib
import json


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def identity(*parts: object) -> str:
    return digest(json.dumps(parts, ensure_ascii=False, separators=(",", ":")))[:24]


@dataclass
class Node:
    kind: str
    start: int
    end: int
    name: str = ""
    header_end: int | None = None
    symbol: str = ""
    confidence: str = "syntax"
    children: list["Node"] = field(default_factory=list)


@dataclass
class Reference:
    kind: str
    symbol: str
    start: int
    end: int


@dataclass
class Parsed:
    root: Node
    references: list[Reference] = field(default_factory=list)
    diagnostics: list[dict] = field(default_factory=list)


class Adapter(Protocol):
    """Adapters must return a non-overlapping interval tree, including opaque areas."""

    name: str
    version: str
    extensions: tuple[str, ...]

    def parse(self, text: str, path: str) -> Parsed: ...


class BudgetCounter(Protocol):
    """Pin identity to implementation AND vocabulary/version for reproducibility."""

    identity: str

    def count(self, text: str) -> int: ...


class UTF8Bytes:
    """Exact byte budget. This is deliberately NOT a model token estimate."""

    identity = "utf8-bytes-v1"

    def count(self, text: str) -> int:
        return len(text.encode("utf-8"))
