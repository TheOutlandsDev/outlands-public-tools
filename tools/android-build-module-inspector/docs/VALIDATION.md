# Validation and limits

The reviewed local Windows/CPython 3.12.7 suite discovers **56 methods**: 38
parser/CLI/generator methods and 18 repeated first-party safeguard methods.
It passes **53** with **3 platform/environment skips**, no failures/errors.
Hardlink/symlink creation was unavailable locally; POSIX FIFO behavior is a
platform-only case. Skips stay separate from passes. Windows/Ubuntu CI runs the
source gate and suite on the collection's configured Python versions; consult
Actions for actual matrix outcomes.

Run from the module folder:

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```

Use an existing writable private `TEMP`/`TMP` directory when running tests in a
restricted environment. Tests create and clean their own disposable fixtures.
They never open a real AOSP checkout, call Android/Make tools, follow includes,
start a build or operate a device.

BP cases cover direct versus nested names, comment/string traps, multiline and
compact blocks, escaped strings, balanced containers, duplicate names/properties,
missing/dynamic/invalid names, top-level assignment remainder holds, namespace/
package/config scope, malformed delimiters, and quoted structural-character
regressions. Token/depth/string/identifier limits are checked explicitly.

Make cases cover supported clear/name/build blocks, discarded assignment fields,
comments, quoted/dynamic/escaped names, unsupported assignment variants,
duplicate/unfinished blocks, unknown includes, continuations, directives,
recipes and unrecognized-rule remainder holds. Request cases exercise exact
matching without suffix inference, observed/held/repeated states, unknown-scope
unmatched holds, malformed requests and default private-field omission.

Actual CLI child processes validate generated example outcomes, both input
formats, fixed statuses/errors, unchanged input bytes, report hashes, optional
details, alias refusal, existing output refusal, malformed bytes and byte limits.
The example generator refuses an existing destination. Shared guard tests cover
stable regular files, absolute routes, links/reparse behavior, Windows streams,
POSIX special files, text/JSON bounds, escaped HTML and exclusive report output.
Repeated guard tests support standalone downloads, not extra product features.

Generated fixtures are intentionally small and fictional. They are not a real
Android compatibility corpus, complete Soong/Make grammar suite, build acceptance
test, module functionality test or proof of global namespace uniqueness. No
upstream executable/parser implementation is bundled or executed. Source hashes
are unsigned consistency checks, not authorship or input-authenticity proof.
