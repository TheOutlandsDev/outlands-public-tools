# Standalone boot/vendor-boot source-download qualification

## Scope and accepted records

The source ZIP requires eight fresh Windows/Ubuntu lanes on exact CPython 3.12.16, 3.13.18, 3.14.10 and 3.15.2. Each lane selects 83 methods: 53 original methods and 30 copied-runtime methods, totaling 664 selections across the matrix. These are required selections, not assumed pass counts. The [release validation asset](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/android-boot-inspector-v0.1.0) supplies actual accepted outcomes, exact skips and source revisions.

Python is supplied separately. The recipe verifies SHA-256 and lengths of locked standalone distributions from build release 20261110, extracts into new owned prefixes and measures actual executable version/hash before binding the evidence to the selected source. It does not install globally or change persistent PATH. Native-binary reproducibility is not claimed. No third-party Python package, Android SDK, native image utility, parser or runtime binary is bundled or required by the inspector.

## Original test and implementation preservation

The 53 original methods comprise 35 boot/reader/CLI cases and 18 repeated first-party safeguards. There are 105 assertion calls: 103 in test methods and two in eight supporting helpers. All four production/generator files, both original test files, 28 runtime definitions and four generator definitions retain raw bytes and parsed definition/method/helper bodies against the reviewed base. No production mirror, parser replacement or version rebinding is introduced.

A test-only adapter rejects undocumented skips and narrows broad operating-system skip paths. Applicable hosted links/hardlinks are mandatory. Exact opposite-platform cases and actual local Windows error 1314 link-creation limitations are recorded by test ID/reason, separately from passes. Arbitrary operating-system errors, empty discovery, wholly skipped groups and failures/errors do not qualify. Native cases cover Windows stream syntax and POSIX special files.

## Copied runtime and metadata checks

Additional tests copy the inspector, bounded reader, shared support and fictional generator to an external owned location and invoke the actual Python CLI. They check boot/vendor v3/v4, exact declared section offsets/sizes/padded ends, signature placement only, vendor-v4 table extent/fragments, malformed/unsupported/truncated declarations, bounds, private output, fixed statuses/stdout/stderr, escaped HTML, independent metadata/report hashes, input immutability and new-only output. Applicable native links/junctions/FIFO/socket/sparse fixtures retain finite native conditions.

Every report must retain `whole_image_hashed: false`, `payloads_inspected: false` and `strings_and_hardware_identifiers_included: false`. Header/table SHA-256 entries describe exactly the inspected metadata ranges, including intentionally repeated prefixes; they are not whole-image hashes. A signature-content mutation with identical headers must produce an identical metadata report, demonstrating that declared placement is not signature verification. No signature or AVB authenticity claim, decompression, extraction, repair, mount, image execution or real device/firmware is part of acceptance.

Tables contribute numeric fragment extents/types only. File boundaries and padding declarations do not prove kernel/ramdisk/DTB/signature/bootconfig content validity or successful bootloader selection. Zero-size declarations are allowed without deciding an image's boot role. Trailing bytes remain uninspected, without inferring a tail format. Real reports and inputs remain private; field omission is not anonymization.

## Fresh source archive and release gates

Each lane independently rebuilds deterministic ZIP and build-manifest bytes from exact reviewed Git source, verifies the source manifest and every archive member, and extracts into a new external owned directory. Relative paths, exact member inventory, fixed timestamps, regular modes and UTF-8 source bytes are checked. The source ZIP contains 30 reviewed source files plus their manifest, 31 members, with no images, interpreters, vendor implementations, generated reports or raw logs.

A fresh application environment has no pip and zero installed distributions. Actual imports/tests must resolve from extracted source, and interpreter/runtime bytes must remain unchanged before/after. Validation helpers reject optimized Python where assertions serve as gates. All selected original/copied methods must succeed subject only to the exact documented skips. Canonical owned fixture directories avoid inherited path aliases in retained source-suite jobs; the original source/test command invocations remain available.

Review a finite source/privacy allowlist and exact finding dispositions. Publish only the ZIP, usage guide, public validation JSON, build manifest and checksums. Download all five assets anonymously, compare byte counts/hashes and exact tagged source, then run the downloaded source in another fresh environment. A consumer run without a reference rebuild records that omission instead of claiming identical-build evidence.

## Executed fictional guide and practical boundary

The [walkthrough](../USAGE.md) runs 15 cases: six exit 0 outcomes, three expected review exit 1 outcomes and six controlled incomplete/refusal exit 2 outcomes. It independently verifies eight report manifests/sixteen report-file hashes, 25 metadata-region hashes, ten unchanged fixtures and 34 exact input/report files. Signature content changes leave the same metadata report. All payload, whole-image-hash and identifier-inclusion flags remain false. Tiny-fixture preservation hashes read the authored examples; those checks do not change the inspector's metadata-only scope.

The unchanged [format](FORMAT.md), [historical validation](VALIDATION.md) and [provenance](PROVENANCE.md) define this narrow subset and prior evidence. Structural findings do not establish payload integrity, AVB/signature authenticity, bootability, device compatibility, a usable firmware set or deployment rights. Trusted stable paths and report parents remain required; sampled path/handle identities and cooperative budgets are not an OS sandbox, atomic snapshot or hard native I/O deadline. Output errors can leave partial newly created reports.
