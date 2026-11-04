# Validation

`python -B source_check.py` validates the explicit source-byte manifest. `python -B -m unittest discover -s tests -p test_json_xml_structures.py -v` from the repository root exercises fictional examples, structural changes, malformed input, false pins and privacy limits. The Batch 98 Actions matrix runs Python 3.12/3.13 on Windows and Ubuntu. No real input, external XML resource, production data or downstream acceptance is claimed.
