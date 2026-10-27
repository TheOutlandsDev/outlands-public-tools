"""Canonical data-only state validation; no selected code or schema execution."""
from copy import deepcopy
import math
import re

from .components.ingestion import Point, ReferenceError
from .contracts import (MAX_JOBS, MAX_RUNS, MAX_TICK, StackError, canonical,
                        digest, integer, job, message, token)

FORMAT = "outlands-data-services-v1"
HASH = re.compile(r"[a-f0-9]{64}")
RUN_STATES = {"RUNNING", "COMPLETED", "REJECTED", "REVIEW_REQUIRED"}
QUEUE_CODES = {
    "PENDING": {"QUEUED", "RETRY_SCHEDULED"}, "IN_FLIGHT": {"ATTEMPTING"},
    "ACCEPTED": {"ADAPTER_ACCEPTED"}, "DELIVERY_REPORTED": {"CALLER_REPORTED_DELIVERY"},
    "FAILED": {"RETRY_EXHAUSTED", "DEFINITELY_REJECTED"},
    "REVIEW_REQUIRED": {"DELIVERY_UNCERTAIN", "ADAPTER_RESULT_INVALID", "DELIVERY_INTERRUPTED", "RESTART_UNCERTAIN"}}


def empty():
    return dict(jobs={}, runs={}, queue={}, last_tick=0)


def fingerprint(spec, input_sha):
    return digest(canonical(dict(job=spec, input_sha256=input_sha)))


def notification(key, spec, result):
    return dict(key=key, route=spec["route"], subject="Data services run complete",
                body=canonical(result).decode("ascii"))


def _hash(value):
    if type(value) is not str or HASH.fullmatch(value) is None:
        raise StackError("STATE_HASH_INVALID")


def _code(value):
    if type(value) is not str or re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", value) is None:
        raise StackError("STATE_CODE_INVALID")


def _result(value, spec):
    if type(value) is not dict or set(value) != {"accepted", "duplicates", "forecast", "score"}:
        raise StackError("RESULT_SCHEMA_INVALID")
    integer(value["accepted"], 1, 256)
    integer(value["duplicates"], 0, 255)
    if value["accepted"] + value["duplicates"] > 256:
        raise StackError("RESULT_COUNTS_INVALID")
    points = value["forecast"]
    if type(points) is not list or len(points) != spec["horizon"]:
        raise StackError("RESULT_FORECAST_INVALID")
    previous = None
    for item in points:
        if type(item) is not dict or set(item) != {"series", "period", "value"}:
            raise StackError("RESULT_FORECAST_INVALID")
        try:
            point = Point(**item)
        except ReferenceError:
            raise StackError("RESULT_FORECAST_INVALID") from None
        if previous and (point.series != previous.series or point.period != previous.period + 1):
            raise StackError("RESULT_FORECAST_INVALID")
        previous = point
    score = value["score"]
    if type(score) is not dict or set(score) != {"count", "mae", "rmse"}:
        raise StackError("RESULT_SCORE_INVALID")
    integer(score["count"], 1, 255)
    if score["count"] != value["accepted"] - spec["min_history"]:
        raise StackError("RESULT_SCORE_INVALID")
    for name in ("mae", "rmse"):
        number = score[name]
        if type(number) not in (int, float) or not 0 <= number <= 2000000000 or not math.isfinite(number):
            raise StackError("RESULT_SCORE_INVALID")


def validate(value):
    if type(value) is not dict or set(value) != {"jobs", "runs", "queue", "last_tick"}:
        raise StackError("STATE_SCHEMA_INVALID")
    integer(value["last_tick"], 0, MAX_TICK)
    for name, maximum in (("jobs", MAX_JOBS), ("runs", MAX_RUNS), ("queue", MAX_RUNS)):
        if type(value[name]) is not dict or len(value[name]) > maximum:
            raise StackError("STATE_CAPACITY_INVALID")
    for key, spec in value["jobs"].items():
        if job(spec)["id"] != token(key):
            raise StackError("STATE_JOB_INVALID")
    completed = set()
    for key, run in value["runs"].items():
        token(key)
        if type(run) is not dict or set(run) != {"job", "input_sha256", "fingerprint", "state", "code", "result"}:
            raise StackError("STATE_RUN_INVALID")
        spec = job(run["job"])
        _hash(run["input_sha256"])
        if run["fingerprint"] != fingerprint(spec, run["input_sha256"]):
            raise StackError("STATE_RUN_FINGERPRINT_INVALID")
        if type(run["state"]) is not str or run["state"] not in RUN_STATES:
            raise StackError("STATE_RUN_INVALID")
        _code(run["code"])
        if run["state"] == "COMPLETED":
            _result(run["result"], spec)
            completed.add(key)
        elif run["result"] is not None:
            raise StackError("STATE_RUN_INVALID")
    if set(value["queue"]) != completed:
        raise StackError("STATE_QUEUE_RELATION_INVALID")
    for key, entry in value["queue"].items():
        if type(entry) is not dict or set(entry) != {"message", "max_attempts", "attempts", "state", "next_attempt", "code", "receipt"}:
            raise StackError("STATE_QUEUE_INVALID")
        selected = message(entry["message"])
        run = value["runs"][key]
        if (selected.key != key or entry["message"] != notification(key, run["job"], run["result"])
                or entry["max_attempts"] != run["job"]["max_attempts"]):
            raise StackError("STATE_QUEUE_RELATION_INVALID")
        integer(entry["attempts"], 0, entry["max_attempts"])
        status = entry["state"]
        if (type(status) is not str or status not in QUEUE_CODES
                or type(entry["code"]) is not str or entry["code"] not in QUEUE_CODES[status]):
            raise StackError("STATE_QUEUE_INVALID")
        if status == "PENDING":
            integer(entry["next_attempt"], 0, MAX_TICK)
            if entry["attempts"] >= entry["max_attempts"] or entry["receipt"] is not None:
                raise StackError("STATE_QUEUE_INVALID")
        elif entry["next_attempt"] is not None or entry["attempts"] == 0:
            raise StackError("STATE_QUEUE_INVALID")
        if status in ("ACCEPTED", "DELIVERY_REPORTED"):
            token(entry["receipt"])
        elif entry["receipt"] is not None:
            raise StackError("STATE_QUEUE_INVALID")
    return deepcopy(value)
