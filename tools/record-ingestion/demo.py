#!/usr/bin/env python3
"""Run only built-in fictional CSV/JSONL ingestion examples."""
import argparse
import json
from ingestion import ReferenceError, ingest_csv, ingest_jsonl


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ReferenceError("ARGUMENTS_INVALID")


def run_demo():
    rows = [dict(series=" SAMPLE ", period=index, value=2 * (index + 1)) for index in range(6)]
    rows.append(dict(series="sample", period=5, value=12))
    text = "\n".join(json.dumps(row) for row in rows)
    clean = ingest_jsonl(text)
    csv_text = "series,period,value\n" + "\n".join(
        "sample," + str(index) + "," + str(2 * (index + 1)) for index in range(6))
    matching = clean.require_clean() == ingest_csv(csv_text).require_clean()
    review = ingest_jsonl(text + '\n{"series":"sample","period":2,"value":99}')
    try:
        review.require_clean()
    except ReferenceError as error:
        gate = str(error)
    else:
        raise ReferenceError("DEMO_REVIEW_GATE_FAILED")
    return dict(mode="FICTIONAL_INGESTION_DEMO", format_results_equal=matching,
                clean=dict(accepted=len(clean.records), duplicates=clean.duplicates,
                           issues=len(clean.issues), ready=clean.ok),
                review=dict(accepted=len(review.records), duplicates=review.duplicates,
                            issues=[dict(record=issue.record, code=issue.code) for issue in review.issues],
                            ready=review.ok), downstream_gate=gate, application_files_written=0)


def main(argv=None):
    parser = Parser(prog="record-ingestion", description=__doc__)
    parser.add_argument("--demo", action="store_true", help="use only built-in synthetic records")
    try:
        args = parser.parse_args(argv)
        if not args.demo:
            parser.print_help()
            return 0
        print(json.dumps(run_demo(), sort_keys=True))
        return 0
    except ReferenceError as error:
        print(json.dumps(dict(status="ERROR", code=str(error))))
        return 2
    except KeyboardInterrupt:
        print(json.dumps(dict(status="ERROR", code="INTERRUPTED")))
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
