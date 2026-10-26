# Supported text and report format

Schema version 1 deliberately supports a subset of saved AAPT2 badging text.
It is not a binary Android manifest parser or an implementation of every AAPT2
release's human-readable output. Unknown syntax is retained as fixed coverage
codes with source-side labels and physical line numbers, never as raw text.

## Selected declarations

Lines are stripped of surrounding ASCII spaces/tabs. Blank lines are ignored.
Every interpreted nonblank line is a case-sensitive prefix, a colon, and a
supported value. No comments, backslash escaping, XML entities, shell expansion,
continuation, environment substitution or quote repair is performed.

```text
package: name='example.orchard' versionCode='9007199254740993' versionName='demo = 1'
sdkVersion:'23'
targetSdkVersion:'34'
maxSdkVersion:'35'
uses-library:'example.alpha'
uses-library-not-required:'example.beta'
```

Package attributes are unordered unique `attribute='value'` tokens separated by
ASCII spaces/tabs. A supported package line requires `name`, `versionCode` and
`versionName`. Attribute values may be empty except where constrained; each is
at most 1,024 characters and contains neither a single quote nor backslash.
Package names have at least two dot-separated ASCII segments, each beginning
with a letter/underscore and containing letters/digits/underscores; total at
most 256 characters. This tool's subset is not a universal Android package-name
validator. Version code is 1–20 decimal digits preserved as text; version name
is literal text, including an empty string. No version ordering or Android's
runtime numeric limits are inferred.

`platformBuildVersionCode`, `platformBuildVersionName`, `compileSdkVersion` and
`compileSdkVersionCodename` are recognized package attributes whose values are
discarded and not compared. Any other attribute, including `split`, makes the
package row unsupported and holds package identity and the remaining comparison.
Duplicate attributes or package rows are ambiguous even if identical.

`sdkVersion`, `targetSdkVersion`, `maxSdkVersion` each take exactly one
single-quoted value of 1–10 decimal digits. Leading zeros remain significant
text. Codenames, extra attributes and malformed values hold that field.
Missing SDK rows mean *unspecified in this report*, not inherited defaults.
Duplicate SDK rows hold the field even when the text matches.

Library rows take one single-quoted ASCII name of 1–256 letters/digits,
underscore, dot or hyphen. `uses-library` maps to `required`;
`uses-library-not-required` maps to `optional`. Repeated library names, including
cross-kind repeats, are held. A malformed row with a supported quoted name at
its beginning retains that identity as held; an unidentifiable row contributes
unknown coverage. Implied, static, SDK and other library row families are outside
this grammar and trigger coverage. Input order of supported unique library names
is retained only to compare relative order among common names.

## Discarded rows and uncertainty

These exact row prefixes are recognized and discarded without interpreting their
payload: `application`, `launchable-activity`, `uses-permission`,
`uses-permission-sdk-23`, `uses-feature`, `uses-implied-feature`, `permission`,
`supports-screens`, `supports-any-density`, `densities`, `locales`, `native-code`,
`alt-native-code`, `compatible-screens`, `supports-gl-texture`, `feature-group`,
`uses-configuration`, `uses-package`, `package-verifier`.
`application-label`, `application-icon` and those prefixes followed by a hyphen
and one or more ASCII alphanumeric/underscore/hyphen characters are also counted
and discarded. These rows have no asserted syntax validity or security meaning;
they are explicitly outside the selected comparison. Unsupported single-line
flags, indented human-readable diagnostics and future prefixes cause coverage.

Unknown rows make the side uncertain. If a scalar field or library name exists
only on the other side, its addition/removal is held. Supported uniquely matched
values can still be compared. Common-library order is held when either side has
unknown rows or a held library identity. Comparison requires unique supported
package identities on both sides. Different package names cause
`PACKAGE_IDENTITY_CHANGED`, with all remaining comparisons held. No package
rename, effective configuration, library availability or upgrade is inferred.

## Bounds and local files

Two distinct absolute stable regular files, 1 MiB each, UTF-8 with optional BOM;
LF/CRLF only. Maximum 20,000 physical lines including final empty line and 8,192
characters per line. Bare CR, NUL, unsupported Unicode control categories and
Unicode line/paragraph separators are refused. Parsed/finding/change/hold
collections are bounded to 4,000 entries; reaching a collection limit is an
incomplete run. The two source issue lists are merged within the same 4,000 cap.
No network paths, device paths, stream paths, symlink/reparse routes, special
files, input alias pairs or changing file snapshots are accepted.

## Report schema

- `schema_version`, `tool`, `scope`, `details_included`, `status` identify output.
- `sources` records `before`/`after` byte sizes and SHA-256 of selected text.
- `summaries` counts package rows, supported library identities (including held
  known identities), unidentified and explicitly ignored rows per side.
- `package_identity` is `unresolved`, `same_declared_name` or
  `different_declared_names`; `declared_packages` appears only with details.
- `changes` contains opaque `entity_id`, `field`, `before_present`,
  `after_present`. With details it adds `before`, `after`, and a library's
  `declared_identity` when relevant. Scalar strings remain strings; library
  requirement is `required`/`optional` or null for no selected declaration.
  Common-order changes use arrays of names only with details.
- `held_comparisons` records opaque entities, a fixed `reason`, and scalar field
  when relevant. A held identity is not a confirmed unchanged identity.
- `findings` includes `DECLARED_METADATA_CHANGED` or `PACKAGE_IDENTITY_CHANGED`.
- `coverage_issues` uses fixed `code`, `source` and 1-based `line`; line zero means
  no package row was found. No raw unsupported values are emitted.

Opaque library IDs follow sorted names internally and are local to one report;
they are not global pseudonyms or stable cross-report identifiers. A comparison
can have changes and incomplete coverage together. Status 0 means only that no
selected change or coverage issue was observed. Empty/filtered/truncated capture
authenticity cannot be established by this inspector.

Output JSON and escaped static HTML are at most 8 MiB each and written to a fresh
directory under an existing local parent. `MANIFEST.json` hashes those outputs;
it is unsigned. Defaults omit literal identities/values but retain hashes and
structural observations, which can identify sources. Details does not expose
application labels or raw unknown rows. Review all output before publication.
