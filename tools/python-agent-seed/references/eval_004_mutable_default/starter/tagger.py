"""Separate reference repair preserving caller-owned lists."""
def add_tag(tag: str, tags: list[str] | None = None) -> list[str]:
    result = list(tags) if tags is not None else []
    result.append(tag)
    return result
