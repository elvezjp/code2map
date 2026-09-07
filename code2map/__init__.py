"""Source maps and deterministic, context-aware code partitioning."""

from ._version import __version__
from .context import build_index, validate_index, pack_index, validate_pack

__all__ = [
    "cli",
    "__version__",
    "build_index",
    "validate_index",
    "pack_index",
    "validate_pack",
]
