from __future__ import annotations


def format_bytes(value: float, *, per_second: bool = False) -> str:
    suffix = "/s" if per_second else ""
    size = float(value)
    units = ("B", "KB", "MB", "GB", "TB", "PB")
    for unit in units:
        if abs(size) < 1024 or unit == units[-1]:
            precision = 0 if unit == "B" else 1
            return f"{size:.{precision}f} {unit}{suffix}"
        size /= 1024
    return f"{size:.1f} PB{suffix}"


def format_duration(seconds: float) -> str:
    total = max(0, int(seconds))
    days, remainder = divmod(total, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    if days:
        return f"{days}d {hours}h {minutes}m"
    return f"{hours}h {minutes}m"

