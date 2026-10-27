"""Fictional-only forecast walkthrough; no operator file or service adapter."""
import argparse
from dataclasses import asdict
import json

from evaluator import forecast, rolling_score
from ingestion import ReferenceError, ingest_jsonl


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ReferenceError("ARGUMENTS_INVALID")


def run_demo():
    text = "\n".join(json.dumps(dict(series="sample", period=index, value=value))
                     for index, value in enumerate((2, 4, 2, 4, 2, 4)))
    batch = ingest_jsonl(text)
    methods = {}
    for method in ("last", "mean", "seasonal"):
        predicted = forecast(batch, method=method, horizon=4, window=2, season=2)
        score = rolling_score(batch, method=method, min_history=2, window=2, season=2)
        methods[method] = dict(predictions=[point.value for point in predicted],
                               score=asdict(score))
    conflicting = ingest_jsonl(text + '\n{"series":"sample","period":0,"value":99}')
    try:
        forecast(conflicting)
    except ReferenceError as error:
        gate = str(error)
    else:
        raise AssertionError("FICTIONAL_GATE_NOT_ENFORCED")
    return dict(mode="FICTIONAL_FORECAST_DEMO", methods=methods,
                conflict_gate=gate, application_files_written=0)


def main(argv=None):
    parser = Parser(prog="forecast-baseline-evaluator",
                    description="Run a built-in fictional baseline forecast example.")
    parser.add_argument("--demo", action="store_true", help="use invented in-memory records")
    try:
        args = parser.parse_args(argv)
        if not args.demo:
            parser.print_help()
            return 0
        print(json.dumps(run_demo(), sort_keys=True, allow_nan=False))
        return 0
    except ReferenceError as error:
        print(json.dumps(dict(status="ERROR", code=str(error)), sort_keys=True))
        return 2
    except KeyboardInterrupt:
        print(json.dumps(dict(status="ERROR", code="INTERRUPTED"), sort_keys=True))
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
