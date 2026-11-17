# Rev 3b patch notes

## What changed
- Shifted portrait sampling windows +3 px to the right.
- Expanded legacy sampling into a wider candidate pool around the original ranges.
- Added per-line QC before measurement math using:
  - band count,
  - contrast,
  - spacing consistency,
  - comb-center proximity.
- Rejected poor lines before family aggregation.
- Added fallback ranking so the script can still return a result if QC is too strict.

## Files
- Vern_Analyze_v2.py  (patched main/original file)
- Vern_Analyze_v3b.py (same patched content, revision-trace copy)
- verify_patch.py
