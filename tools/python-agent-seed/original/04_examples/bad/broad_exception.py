"""Bad example: hiding useful failures."""


def parse_int(value):
    try:
        return int(value)
    except Exception:
        return 0


# Problem:
# This catches too much and silently replaces errors. Catch ValueError and decide whether a default is appropriate.
