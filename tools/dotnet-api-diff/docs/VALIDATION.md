# Validation

The dependency-free console test project builds two original fictional `Example.Plugin` libraries. Both have the same assembly simple name. The test fixture source is shipped; generated binaries stay outside the source tree. Tests inspect metadata only and check that the module initializer's execution marker is absent afterward.

Run the four build/test commands in the [README](../README.md). `tests/ApiDiff.Tests.csproj` references the tool and both fixture projects, so no separate fixture build is required. The harness can also take two explicit fixture paths if an alternative artifacts layout is used:

```text
dotnet ApiDiff.Tests.dll path/to/Before/Example.Plugin.dll path/to/After/Example.Plugin.dll
```

The default layout is the SDK `--artifacts-path` layout; fixtures must be Release builds. The harness creates a fresh random directory beneath the OS temporary directory, verifies that its resolved cleanup target stays under that temporary directory, and removes only that owned directory. It never modifies the fixture DLLs.

Coverage includes:

- Exact six-change golden result and deterministic declaration order.
- Added/removed methods, return-type and field-type changes, and setter visibility.
- Overloads, nested visibility chains, interfaces, events, constraints, generics, arrays, pointers, references, function pointers, and required custom modifiers.
- Explicit constant-value exclusion and private/protected/internal exclusions.
- Malformed and oversized files, generated trailing/deep/oversized signatures, generated duplicate metadata identities, and delimiter-bearing type-name refusal.
- CLI success/difference/error codes, invalid options, report JSON, fresh-only writes, source overwrite prevention, source byte preservation, and path-free error messages.
- Empty/missing/directory/UNC/control-containing paths; symlink rejection where OS privilege permits creation.

Initial Windows validation with **.NET SDK 8.0.418** passed **52 assertions** with one symlink-creation privilege skip and zero build warnings/errors. Linux CI must exercise that rejection; the test fails if the required Linux symlink branch is unavailable (53 assertions when it runs). `OUTLANDS_REQUIRE_SYMLINK_TEST=1` can require it on another platform. Windows and Ubuntu CI run the same generated fixtures with .NET 8.

Tests establish the declared comparison behavior for the authored inputs. They do not establish safety for hostile DLLs, every legal metadata encoding, API compatibility across runtimes, game interoperability, or permission to distribute someone else's assembly. No real game DLLs were used as public fixtures.
