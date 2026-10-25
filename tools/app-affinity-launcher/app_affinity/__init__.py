"""App Affinity Launcher 0.1.0. Original MIT source; no action on import."""
from .core import (AffinityError, launch, make_plan, mask_from_cores, parse_cores,
                   parse_mask, validate_mask)
__version__ = "0.1.0"
__all__ = ["AffinityError", "launch", "make_plan", "mask_from_cores", "parse_cores", "parse_mask", "validate_mask"]
