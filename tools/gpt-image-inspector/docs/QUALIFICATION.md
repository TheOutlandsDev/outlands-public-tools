# Standalone GPT source-download qualification

## Accepted scope and evidence

The source ZIP is qualified by fresh Windows and Ubuntu environments using exact CPython 3.12.16, 3.13.18, 3.14.10 and 3.15.2. The matrix has eight lanes. Python is a separately supplied qualification/runtime prerequisite, not a bundled release asset. Runtime imports use only the standard library; no native parser or disk utility is required.

The qualification recipe verifies hash/length-pinned standalone CPython archives from build release20261110, extracts the selected version into a new owned prefix, probes its actual version and executable hash, and binds that evidence to the selected source. It does not install globally or change global PATH. Interpreter/compiler binary reproducibility is not claimed. The [release validation asset](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/gpt-image-inspector-v0.1.0) records actual accepted lanes and any exact skips; this contract does not turn expected counts into claimed results.

## Preserved original suite

The original 46 methods comprise 29 GPT cases and 17 first-party safeguard cases, with 77 assertion calls: 75 in test methods and two in seven supporting helpers. Both original test files, production `gpt_inspector.py`, first-party `inspection_support.py` and the fictional generator remain byte-identical to the reviewed base. Preservation records compare raw bytes, method/helper bodies and parsed definitions. No production mirror, parser replacement or version rebinding is needed.

A test-only adapter narrows the original broad operating-system skip paths. Applicable hosted native links/hardlinks must work. Required opposite-platform cases and actual local Windows error1314 symlink limitations are exact test-ID/reason pairs, recorded separately. Arbitrary operating-system errors, empty discovery, wholly skipped groups, unexpected skips and failed/error results do not qualify. Original platform-sensitive cases include Windows alternate-stream syntax, POSIX FIFO inputs and a POSIX logical sparse-file fixture.

## Copied-runtime and CRC checks

Additional tests copy the actual runtime/support/generator into an external owned location and invoke the real Python CLI. They independently verify clean 512/4096 layouts, CRC corruption, primary/backup disagreement even with matching CRCs, overlaps, truncated/unsupported/bounded metadata, private defaults and escaped details, manifests and unchanged inputs. CRC expectations use an independent bitwise IEEE CRC-32 calculation with known-vector checks, rather than asking the production CRC function for its own expected answer.

The runner checks exact statuses, JSON stdout and stderr; applicable native link/junction/FIFO/socket/sparse cases; new-only reports and input/source preservation. Fixtures are generated, small or logically sparse regular files. No physical drive, real firmware, runtime/image execution, mount, repair or network inspection is part of qualification. A fixture reading only the declared metadata budget does not claim validation of all partition contents.

## Fresh archive gates

Each lane independently rebuilds the deterministic source ZIP from the exact reviewed Git source, compares ZIP and build-manifest bytes, verifies every source-manifest row and archive member, and extracts into an owned external directory. Archive paths, regular-file modes, fixed timestamps, exact member inventory and UTF-8 source payloads are checked before use.

The application environment is new, has no pip and zero installed distributions, and resolves runtime/tests from the extracted source. Runtime bytes and the base interpreter's version/hash remain unchanged before/after. The helper scripts refuse optimized Python where assertions are validation gates. All selected original and copied-runtime tests must pass subject only to the exact recorded platform/permission cases.

Review source/privacy findings against a finite allowlist and exact dispositions. Publish only the source ZIP, usage guide, public validation JSON, build manifest and checksums. Download all five assets anonymously, compare byte counts/hashes and the exact tagged Git source, then run the downloaded source in another fresh environment. A downloaded consumer run without a reference rebuild records that omission explicitly rather than claiming identical-build proof.

## Guide and limits

The [fictional walkthrough](../USAGE.md) executes thirteen cases: four exit0 cases, three expected review exit1 cases and six controlled refusal/incomplete exit2 cases. It independently verifies six report manifests/twelve payload hashes, twenty-four header/table CRC observations, thirty metadata-region hashes, seven unchanged fixtures and exactly25 output/input files. Its generated fixture hashes read tiny authored inputs to check preservation; production inspection remains limited to metadata.

The original [format and limits](FORMAT.md), [historical validation](VALIDATION.md) and [provenance](PROVENANCE.md) retain the supported subset and historical boundary. Metadata findings and CRC agreement are not image authenticity, full UEFI conformance, filesystem validity, bootability, device compatibility, repair readiness or permission to deploy. Default omission of names/GUID fields is not anonymization. Trusted stable input paths and output parents remain required; best-effort file checks and budgets are not an OS sandbox, atomic snapshot or hard native I/O deadline.
