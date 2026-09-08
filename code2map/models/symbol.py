from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Symbol:
    name: str
    kind: str  # class, method, function
    start_line: int
    end_line: int
    original_file: str
    language: str
    parent: str | None = None
    qualname: str | None = None
    role: str | None = None
    signature: str | None = None
    calls: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    side_effects: list[str] = field(default_factory=list)
    part_file: str | None = None
    id: str | None = None

    def display_name(self) -> str:
        if self.kind == "method" and self.parent:
            return f"{self.parent}#{self.name}"
        return self.name

    def line_range(self) -> str:
        return f"L{self.start_line}–L{self.end_line}"
