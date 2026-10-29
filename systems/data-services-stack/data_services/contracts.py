"""Strict neutral configuration and bounded JSON contracts; no source discovery."""
from copy import deepcopy
import hashlib
import json
import math
import re

from .components.outbox import Message, OutboxError

MAX_JSON = 1048576
MAX_CONFIG = 65536
MAX_JOBS = 16
MAX_RUNS = 128
MAX_TICK = 1000000000000
TOKEN = re.compile(r"[a-z][a-z0-9_-]{0,63}")
JOB_FIELDS = {"id", "input_format", "method", "horizon", "window", "season",
              "min_history", "route", "max_attempts"}


class StackError(ValueError):
    """Fixed codes only; paths, native errors and payloads are never diagnostics."""


def token(value):
    if type(value) is not str or TOKEN.fullmatch(value) is None:
        raise StackError("TOKEN_INVALID")
    return value


def integer(value, low, high, code="PARAMETER_INVALID"):
    if type(value) is not int or not low <= value <= high:
        raise StackError(code)
    return value


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def decode(raw, maximum=MAX_JSON):
    if type(raw) is not bytes or len(raw) > maximum:
        raise StackError("JSON_BYTE_LIMIT")
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise StackError("JSON_DUPLICATE_KEY")
            value[key] = item
        return value
    def constant(value):
        raise StackError("JSON_NONSTANDARD_NUMBER")
    try:
        value=json.loads(raw.decode("utf-8-sig"), object_pairs_hook=pairs, parse_constant=constant)
        def bounded(item,depth=0):
            if depth>64:raise StackError("JSON_DEPTH_LIMIT")
            if type(item) is float and not math.isfinite(item):raise StackError("JSON_NONSTANDARD_NUMBER")
            if type(item) is dict:
                for child in item.values():bounded(child,depth+1)
            elif type(item) is list:
                for child in item:bounded(child,depth+1)
        bounded(value)
        return value
    except StackError:
        raise
    except (ValueError, UnicodeError, RecursionError):
        raise StackError("JSON_INVALID") from None


def job(value):
    if type(value) is not dict or set(value) != JOB_FIELDS:
        raise StackError("JOB_SCHEMA_INVALID")
    token(value["id"])
    token(value["route"])
    if type(value["input_format"]) is not str or value["input_format"] not in ("csv", "jsonl"):
        raise StackError("JOB_FORMAT_INVALID")
    if type(value["method"]) is not str or value["method"] not in ("last", "mean", "seasonal"):
        raise StackError("JOB_METHOD_INVALID")
    integer(value["horizon"], 1, 32)
    for name in ("window", "season", "min_history"):
        integer(value[name], 1, 256)
    integer(value["max_attempts"], 1, 5)
    required = value["window"] if value["method"] == "mean" else value["season"] if value["method"] == "seasonal" else 1
    if value["min_history"] < required:
        raise StackError("JOB_HISTORY_INVALID")
    return deepcopy(value)


def configuration(raw):
    value = decode(raw, MAX_CONFIG)
    if (type(value) is not dict or set(value) != {"version", "jobs"}
            or type(value["version"]) is not int or value["version"] != 1
            or type(value["jobs"]) is not list or not 1 <= len(value["jobs"]) <= MAX_JOBS):
        raise StackError("CONFIGURATION_INVALID")
    output = {}
    for item in value["jobs"]:
        selected = job(item)
        if selected["id"] in output:
            raise StackError("JOB_DUPLICATE")
        output[selected["id"]] = selected
    return output


def message(value):
    if type(value) is not dict or set(value) != {"key", "route", "subject", "body"}:
        raise StackError("MESSAGE_SCHEMA_INVALID")
    try:
        return Message(**value)
    except OutboxError:
        raise StackError("MESSAGE_INVALID") from None


def fictional_configuration():
    return canonical(dict(version=1, jobs=[dict(id="sample", input_format="jsonl",
        method="mean", horizon=3, window=3, season=1, min_history=3,
        route="sample_route", max_attempts=3)]))


def fictional_input():
    return b"\n".join(canonical(dict(series="sample", period=i, value=2*(i+1))) for i in range(6))
