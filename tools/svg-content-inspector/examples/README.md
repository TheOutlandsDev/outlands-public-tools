# Fictional SVG inspection examples

Run from the module directory with a security-updated Python 3.12/3.13 and
Expat >=2.7.2. Choose an existing private parent and new absolute destinations:

```text
python -B examples/make_demo.py --destination ABS_NEW_DEMO
python -B svg_inspector.py --svg ABS_NEW_DEMO/clean.svg --output ABS_NEW_CLEAN_REPORT
python -B svg_inspector.py --svg ABS_NEW_DEMO/review.svg --output ABS_NEW_REVIEW_REPORT
```

The first inspection returns 0 (`NO_SCOPE_FINDINGS`) for the documented subset:
literal dimensions, a declared internal gradient ID and a unique fragment match.
That result is not a safe-rendering or visual-quality verdict.

The second returns 1 (`REVIEW_REQUIRED`) for deliberate inert markers: an empty
script declaration with a non-executable fictional type, empty foreign object,
duplicate IDs, a missing fragment, an empty event attribute, an inline style and
a harmless fictional data-text placeholder. No example requests a network URL
or local external file. Do not render `review.svg` or arbitrary inspection inputs;
open the generated **report.html** instead. The report displays escaped text
and never embeds SVG or follows references.

Use `--include-details` only for a separately reviewed private report if you need
raw reference/ID strings. The default reports omit those strings. Never replace
these generated examples with a real portfolio, customer artwork or captured
SVG data in a public issue. Source hashes and opaque structural labels can still
identify inputs; the tool is not an anonymizer.
