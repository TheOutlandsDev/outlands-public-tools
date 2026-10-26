# Fictional build declarations

Run `python -B examples/generate.py --output NEW_ABSOLUTE_DIRECTORY` from the
module folder. The existing output parent must be a private directory you
control, outside the source checkout. A destination must be new; the generator
does not replace existing content.

It writes five invented UTF-8 files:

- `clean.bp`: two literal declarations with nested/ignored values.
- `clean.mk`: one supported clear/name/build block.
- `wanted.txt`: the three known names from those two files.
- `review.bp`: two repeated literal names and one unresolved name expression.
- `wanted-unseen.txt`: the repeated name and one name not observed in that file.

The [README commands](../README.md) produce a clean report with exit 0 and three
observed requests, then a review report with exit 1, one repeated-name group,
one held unresolved declaration and one held unmatched request. It would be
misleading to call that last request absent from a real build.

These text files are not an actual Android project and are never built or
included. All names, paths inside values and declarations are fictional. Reports
and generated inputs stay outside this reviewed source-only package.
