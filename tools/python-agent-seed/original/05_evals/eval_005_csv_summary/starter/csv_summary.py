import csv


def summarize_scores(path):
    rows = list(csv.reader(open(path)))
    scores = [int(row[1]) for row in rows[1:]]
    return {"count": len(scores), "average": sum(scores) / len(scores), "maximum": max(scores)}
