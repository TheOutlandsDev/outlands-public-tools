"""In-memory shim for the pinned public project parser; no stores or live adapters."""
from toolkit import Rejected as WorkbenchError, decode, encode, digest

MAX_INPUT = 4 * 1024 * 1024
