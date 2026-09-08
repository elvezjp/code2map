"""Source maps and deterministic, context-aware code partitioning."""

from ._version import __version__
from .context import build_index, pack_index, validate_index, validate_pack

__all__ = [
    "__version__",
    "build_index",
    "cli",
    "pack_index",
    "validate_index",
    "validate_pack",
]
