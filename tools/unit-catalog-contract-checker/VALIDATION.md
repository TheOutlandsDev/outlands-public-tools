# Validation

Run `python -B source_check.py`, then run the input and needs-review examples. Run `python -B -W error -m unittest discover -s tests -v` for copied boundary coverage. The root `tests/test_unit_integrity_tools.py` exercises all four CLI contracts and their connected fictional cohort. Checks establish only supplied declaration behavior. No live instrument, SQL, browser or provider behavior is tested for these tools.
