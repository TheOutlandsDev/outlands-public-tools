# Standalone Android sparse source-download qualification

## Accepted scope and evidence

The source ZIP is qualified by fresh Windows and Ubuntu lanes on exact CPython 3.12.16, 3.13.18, 3.14.10 and 3.15.2. Eight lanes select 75 methods each: 45 original methods and 30 copied-runtime methods. These 600 selections describe the required scope; actual passes, exact skips and accepted source commits come from the [release validation asset](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/android-sparse-inspector-v0.1.0), not an assumed outcome.

Python is a separately supplied runtime/qualification prerequisite. The recipe verifies SHA-256 and lengths of pinned standalone distributions from build release 20261110, extracts into a new owned prefix and probes the actual executable version/hash before binding the receipt to the selected source. It does not install globally or change global PATH. Native-binary reproducibility is not claimed. No Android SDK, AOSP executable, native parser or third-party Python package is required or bundled.

## Original suite preservation

All 45 original methods are retained: 27 sparse/reader/CLI and 18 first-party safeguard cases. There are 96 assertion calls, 94 in test methods and two in nine supporting helpers. The 21 runtime definitions and one generator definition, four runtime/generator source files and both original test files remain raw-byte and AST/body preserved against the reviewed base. No production mirror, parser replacement or version rebinding is introduced.

A test-only adapter narrows old broad operating-system skip paths. Applicable hosted links and hardlinks must work. Exact opposite-platform fixtures and actual local Windows error 1314 link-privilege limitations are recorded by test ID/reason, separately from passes. Arbitrary operating-system errors, undocumented/wholly skipped groups, empty discovery and failures/errors do not qualify. Native cases include Windows alternate-stream refusal and POSIX special-file refusal.

## Copied runtime and metadata boundary

Additional tests copy the actual inspector, bounded reader, support and generator to an external owned location and invoke the real Python CLI. They verify clean RAW/FILL/DONT_CARE accounting, unverified CRC/header-checksum declarations, truncation, malformed/extended/unknown metadata, declared bounds and decimal output sizes, fixed JSON stdout/stderr, manifests, unchanged inputs and new-only output. Applicable links/junctions/FIFO/socket/sparse-file cases preserve their exact native conditions.

Qualification keeps `payload_crc_checked` and `whole_image_hashed` false. It does not calculate or validate sparse payload CRCs, read skipped payload/extension ranges as metadata, reconstruct an image or transform DONT_CARE into observed zeroes. Independent hashes verify only expected metadata regions and generated report files. A paired fixture changes RAW/FILL body bytes with identical headers and must retain the same metadata report, demonstrating that metadata inspection cannot establish payload integrity.

All inputs are tiny authored files or bounded logical sparse regular fixtures. No real firmware, physical drive, device route, conversion utility, mount, repair, image execution or deployment is part of acceptance. Tested refusals and metadata budgets are not a claim of complete Android sparse-library behavior or binary safety.

## Fresh archive and release gates

Each lane independently rebuilds the deterministic source ZIP from the reviewed Git source and compares both ZIP and build-manifest bytes. It checks every source-manifest row, exact archive inventory, regular-file modes, fixed timestamps, safe relative member names and UTF-8 source bytes before extraction. The application environment is fresh, has no pip and zero installed distributions, and resolves runtime/tests from extracted source. The interpreter and preserved runtime bytes must remain unchanged before/after. Validation helpers refuse optimized Python where assertion gates are used.

The source ZIP has 30 reviewed source files plus their manifest, 31 members, and no images, runtime archives, firmware, vendor implementations or generated reports. Review exact source/privacy findings against a finite allowlist/disposition set. Publish the ZIP, usage guide, public validation JSON, build manifest and checksums. An anonymous readback must match all five assets and the exact tagged Git source, followed by another fresh downloaded-source run. A consumer run omitting a reference rebuild records that omission instead of claiming identical-build proof.

## Executed fictional guide

The [walkthrough](../USAGE.md) runs 13 cases: three exit 0, four expected review exit 1 and six refusal/incomplete exit 2 outcomes. It independently checks six report manifests/twelve report-payload hashes, 22 metadata-region hashes, eight unchanged tiny fixtures and 26 exact input/report files. Both report scope flags remain false and the changed-payload pair has identical complete metadata reports. No payload CRC is calculated. Tiny-fixture preservation hashes intentionally read authored files; those checks do not change the inspector's metadata-only scope.

The original [format](FORMAT.md), [historical validation](VALIDATION.md) and [provenance](PROVENANCE.md) remain authoritative for this bounded subset. Findings, declarations and CRC coverage do not prove payload integrity, whole-image integrity, reconstruction completeness, Android Verified Boot, bootability, device compatibility or deployment rights. Default report omissions are not anonymization. Trusted stable filesystem paths and output parents remain required; path/handle checks and cooperative limits are not an OS sandbox, atomic snapshot or hard native I/O deadline.
