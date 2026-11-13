# Private saved-build-file workspace

Use an existing private local directory outside the extracted source. Explicitly select saved Android.bp, Android.mk and optional wanted-name text files. Input names and selected details can disclose private project structure. Default field omission and report-local IDs are data minimization, not anonymization; inspect reports privately before sharing.

The inspector reads selected text and writes a new report directory. It does not follow includes, evaluate expressions, invoke Make/Soong, compile a project or access a device. Unsupported grammar and incomplete scope remain review holds. Observed or unseen selected names do not establish effective build availability, namespace resolution, variant selection or success of an Android build.

Use stable regular files and an output parent you control. Link and alias checks, immutable-input checks and cooperative bounds do not provide an operating-system sandbox, hostile-filesystem transactions, atomic snapshots or hard I/O deadlines. A failed write can leave a new partial output. Choose a fresh output name after correcting its cause. Source manifests and selected-text hashes detect byte drift; they are unsigned and do not authenticate a complete build configuration.

The release includes original MIT source, fictional examples, tests and packaging methods. Obtain the pinned supported CPython runtime separately. No interpreter, AOSP/vendor source, actual operational configuration, generated report, raw log, credential or third-party implementation is bundled.
