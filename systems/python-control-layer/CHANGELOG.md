# Changes

## 0.1.0 original-source release

- Preserve all four application modules and both original test files byte-for-byte.
- Add 14 separate configuration, logging, route and lifecycle checks plus actual
  loopback HTTP/startup/shutdown checks.
- Retain Python 3.12 and qualify 3.12.16 on Windows/Ubuntu with complete SDK pins.
- Update separate dependency pins, add hash-locked runtime/validation sets and
  record an exact-version known-advisory and license-metadata review.
- Pin the Linux base image; separate runtime/test stages; use a non-root user,
  loopback host publishing and a read-only filesystem in the supplied Compose file.
- Publish source-only packaging, setup and measured validation records. No database
  or query functionality is added, and the test-stack deprecation stays visible.
