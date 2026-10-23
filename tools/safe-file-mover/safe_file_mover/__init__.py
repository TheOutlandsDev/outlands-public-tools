"""Safe File Mover public API."""

from .core import (
    ConflictPolicy,
    MoveOperation,
    MovePlan,
    SafeMoveEngine,
    SafeMoveError,
    is_remote_path,
)

__all__ = [
    "ConflictPolicy",
    "MoveOperation",
    "MovePlan",
    "SafeMoveEngine",
    "SafeMoveError",
    "is_remote_path",
]

__version__ = "0.2.0"
