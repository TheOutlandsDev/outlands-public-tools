"""Format timestamps with the pinned IANA timezone database."""

from datetime import UTC, datetime
from importlib.resources import files
from zoneinfo import ZoneInfo

with files("tzdata.zoneinfo.America").joinpath("New_York").open("rb") as zone_file:
    NEW_YORK = ZoneInfo.from_file(zone_file, key="America/New_York")


def new_york_time(value: datetime) -> dict[str, str]:
    """Normalize one timestamp and expose ISO and New York display values."""

    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    eastern = value.astimezone(NEW_YORK)
    return {
        "iso": eastern.isoformat(timespec="seconds"),
        "display": eastern.strftime("%b %d, %Y · %I:%M:%S %p %Z"),
        "timezone": eastern.tzname() or "ET",
    }
