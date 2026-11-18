# Use the offline SQL report binder

Compare the source ZIP against `SHA256SUMS.txt` with `Get-FileHash -Algorithm
SHA256` on Windows or `sha256sum` on Ubuntu. Extract the archive and run the
example from its root with Python 3.12 or 3.15. The binder requires no package
installation or database connection.

```python
from datetime import date
from queries.report_detail.bind import build_detail_query

sql, parameters = build_detail_query(
    start_date=date(2026, 1, 10),
    end_date=date(2026, 1, 11),
    selected_products=["DEMO-61", "DEMO-11"],
    product_options={"DEMO-11", "DEMO-61", "DEMO-88"},
)
print(sql)
print(parameters)
```

The fictional template has two date placeholders and `PR.Name IN (?, ?)`.
The returned tuple contains the original start and end values, then `DEMO-61`
and `DEMO-11` in that order. Product values stay in the tuple. The dates are
compared by calendar day and passed through with their original types and times.
Two datetimes on the same day are accepted even if their times are reversed.

The binder rejects reversed calendar dates, empty selections, duplicate or
unknown values, and templates with a missing or repeated product marker. It
allows up to 2,098 products plus two dates for a total of 2,100 parameters.
Supply your allowed options as a separate collection of strings. The bundled
SQL illustrates binding against fictional tables. The qualification exercises
SQL text and parameters locally.

Run all seven retained cases with `python -B -m unittest discover -s tests -v`.
`VALIDATION.json` records Windows and Ubuntu results for Python 3.12.16 and
3.15.2, eight checks against the extracted API and exact ZIP rebuilds.
