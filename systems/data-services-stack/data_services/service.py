"""Persisted workflows and queue transitions around reviewed pure components."""
from copy import deepcopy
from dataclasses import asdict

from .components.evaluator import forecast, rolling_score
from .components.ingestion import ReferenceError, ingest_csv, ingest_jsonl
from .components.outbox import Acceptance, Outbox
from .contracts import (MAX_RUNS, MAX_TICK, StackError, configuration, digest,
                        integer, message, token)
from .journal import Journal
from .state import fingerprint, notification


def _calculate(spec, raw):
    text = raw.decode("utf-8")
    batch = (ingest_csv if spec["input_format"] == "csv" else ingest_jsonl)(text)
    batch.require_clean()
    options = dict(method=spec["method"], window=spec["window"], season=spec["season"])
    predicted = forecast(batch, horizon=spec["horizon"], **options)
    score = rolling_score(batch, min_history=spec["min_history"], **options)
    return dict(accepted=len(batch.records), duplicates=batch.duplicates,
                forecast=[asdict(point) for point in predicted], score=asdict(score))


class Stack(Journal):
    def _ready(self):
        if getattr(self, "_dispatching", False):
            raise StackError("OPERATION_IN_PROGRESS")
        if self.closed or self.poisoned:
            raise StackError("SESSION_UNAVAILABLE")
        if super().status()["recovery_required"]:
            raise StackError("RECOVERY_REQUIRED")

    def configure(self, raw):
        self._ready()
        jobs = configuration(raw)
        if jobs == self._state["jobs"]:
            return dict(configured=len(jobs), changed=False)
        changed = deepcopy(self._state)
        changed["jobs"] = jobs
        self.commit(changed)
        return dict(configured=len(jobs), changed=True)

    def _summary(self, key):
        run = self._state["runs"][key]
        return dict(key=key, job=run["job"]["id"], state=run["state"], code=run["code"])

    def run(self, job_id, key, raw):
        self._ready()
        token(job_id)
        token(key)
        if type(raw) is not bytes or len(raw) > 65536:
            raise StackError("INPUT_BYTE_LIMIT")
        if job_id not in self._state["jobs"]:
            raise StackError("JOB_NOT_FOUND")
        spec = self._state["jobs"][job_id]
        input_sha = digest(raw)
        signature = fingerprint(spec, input_sha)
        if key in self._state["runs"]:
            if self._state["runs"][key]["fingerprint"] != signature:
                raise StackError("RUN_IDEMPOTENCY_CONFLICT")
            return self._summary(key)
        if len(self._state["runs"]) >= MAX_RUNS:
            raise StackError("RUN_CAPACITY")
        changed = deepcopy(self._state)
        changed["runs"][key] = dict(job=deepcopy(spec), input_sha256=input_sha,
                                   fingerprint=signature, state="RUNNING", code="RUN_STARTED", result=None)
        self.commit(changed)
        try:
            result = _calculate(spec, raw)
        except (ReferenceError, UnicodeError) as error:
            changed = deepcopy(self._state)
            run = changed["runs"][key]
            run["state"] = "REJECTED"
            run["code"] = str(error) if type(error) is ReferenceError else "INPUT_ENCODING_INVALID"
            self.commit(changed)
            return self._summary(key)
        except BaseException as error:
            changed = deepcopy(self._state)
            changed["runs"][key].update(state="REVIEW_REQUIRED", code="RUN_INTERRUPTED")
            self.commit(changed)
            if not isinstance(error, Exception):
                raise
            raise StackError("RUN_FAILED_REVIEW") from None
        changed = deepcopy(self._state)
        changed["runs"][key].update(state="COMPLETED", code="RUN_COMPLETED", result=result)
        changed["queue"][key] = dict(message=notification(key, spec, result),
            max_attempts=spec["max_attempts"], attempts=0, state="PENDING", next_attempt=0,
            code="QUEUED", receipt=None)
        # Result and queued notification become visible in one committed snapshot.
        self.commit(changed)
        return self._summary(key)

    def result(self, key):
        if self.closed or self.poisoned:
            raise StackError("SESSION_UNAVAILABLE")
        token(key)
        if key not in self._state["runs"]:
            raise StackError("RUN_NOT_FOUND")
        return deepcopy(self._state["runs"][key])

    def queue(self):
        if self.closed or self.poisoned:
            raise StackError("SESSION_UNAVAILABLE")
        return [dict(key=key, **{name:entry[name] for name in
            ("state", "code", "attempts", "next_attempt")})
            for key, entry in sorted(self._state["queue"].items())]

    def dispatch(self, transport, *, now, limit=10):
        self._ready()
        integer(now, self._state["last_tick"], MAX_TICK, "CLOCK_INVALID")
        integer(limit, 1, 64)
        if now != self._state["last_tick"]:
            changed = deepcopy(self._state)
            changed["last_tick"] = now
            self.commit(changed)
        selected = [key for key, entry in sorted(self._state["queue"].items())
                    if entry["state"] == "PENDING" and entry["next_attempt"] <= now][:limit]
        completed = []
        for key in selected:
            changed = deepcopy(self._state)
            entry = changed["queue"][key]
            entry.update(state="IN_FLIGHT", code="ATTEMPTING", next_attempt=None,
                         attempts=entry["attempts"] + 1)
            self.commit(changed)
            # This durable claim must succeed before caller code can have effects.
            receipt = []
            class Bridge:
                def send(bridge, selected_message):
                    result = transport.send(selected_message)
                    if type(result) is Acceptance:
                        receipt.append(result.receipt)
                    return result
            volatile = Outbox(max_attempts=1)
            volatile.enqueue(message(entry["message"]))
            interrupted = None
            self._dispatching = True
            try:
                outcome = volatile.dispatch(Bridge(), now=now, limit=1)[0]
            except BaseException as error:
                interrupted = error
                outcome = volatile.snapshot(key)
            finally:
                self._dispatching = False
            changed = deepcopy(self._state)
            entry = changed["queue"][key]
            if outcome.state == "ACCEPTED":
                entry.update(state="ACCEPTED", code="ADAPTER_ACCEPTED", receipt=receipt[0])
            elif outcome.code == "RETRY_EXHAUSTED":
                due = now + 2 ** (entry["attempts"] - 1)
                if entry["attempts"] >= entry["max_attempts"] or due > MAX_TICK:
                    entry.update(state="FAILED", code="RETRY_EXHAUSTED")
                else:
                    entry.update(state="PENDING", code="RETRY_SCHEDULED", next_attempt=due)
            else:
                entry.update(state=outcome.state, code=outcome.code)
            self.commit(changed)
            completed.append(next(row for row in self.queue() if row["key"] == key))
            if interrupted is not None:
                raise interrupted
        return completed

    def report_delivery(self, key, receipt):
        self._ready()
        token(key)
        token(receipt)
        if key not in self._state["queue"]:
            raise StackError("MESSAGE_NOT_FOUND")
        entry = self._state["queue"][key]
        if entry["state"] not in ("ACCEPTED", "DELIVERY_REPORTED") or entry["receipt"] != receipt:
            raise StackError("DELIVERY_REPORT_REFUSED")
        if entry["state"] == "DELIVERY_REPORTED":
            return dict(changed=False)
        changed = deepcopy(self._state)
        changed["queue"][key].update(state="DELIVERY_REPORTED", code="CALLER_REPORTED_DELIVERY")
        self.commit(changed)
        return dict(changed=True)

    def recover(self, *, confirm_stopped=False):
        if getattr(self, "_dispatching", False):
            raise StackError("OPERATION_IN_PROGRESS")
        if confirm_stopped is not True:
            raise StackError("STOPPED_ASSERTION_REQUIRED")
        changed = deepcopy(self._state)
        count = 0
        for run in changed["runs"].values():
            if run["state"] == "RUNNING":
                run.update(state="REVIEW_REQUIRED", code="RESTART_UNCERTAIN")
                count += 1
        for entry in changed["queue"].values():
            if entry["state"] == "IN_FLIGHT":
                entry.update(state="REVIEW_REQUIRED", code="RESTART_UNCERTAIN")
                count += 1
        if count:
            self.commit(changed)
        return dict(review_items=count, **self.status())

    def status(self):
        return dict(**super().status(), jobs=sorted(self._state["jobs"]),
                    runs=[self._summary(key) for key in sorted(self._state["runs"])], queue=self.queue())

    def close(self):
        if getattr(self, "_dispatching", False):
            raise StackError("OPERATION_IN_PROGRESS")
        super().close()
