"""Separate reference repair for the small original CSV exercise."""
import csv
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class ScoreSummary:
    count: int
    average: float
    maximum: int

def summarize_scores(path: str | Path) -> ScoreSummary:
    with Path(path).open(encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not {'name', 'score'} <= set(reader.fieldnames):
            raise ValueError('Required CSV columns are missing')
        scores = []
        for row in reader:
            if all(value is None or not str(value).strip() for value in row.values()):
                continue
            try:
                scores.append(int(row['score']))
            except (TypeError, ValueError) as error:
                raise ValueError('Score must be integer text') from error
    if not scores:
        raise ValueError('CSV contains no score rows')
    return ScoreSummary(len(scores), sum(scores) / len(scores), max(scores))
