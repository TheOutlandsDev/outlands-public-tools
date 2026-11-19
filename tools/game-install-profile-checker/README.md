# Offline TOML Game Install Profile Checker

List saved TOML game profiles and check their declared installation directory,
executable, required files, save paths, and port numbers. Checks use a local
root you select and report whether each profile applies to the current platform.

- [Source ZIP, SHA-256 checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/game-install-profile-checker-v0.1.0)
- [Usage guide and fictional installation](SETUP.md)

The source edition keeps Portable OpsKit's original profile test byte for byte
and retains the original CLI case for the engine display. The CLI uses the
Python standard library. Qualification covers Windows and Ubuntu with Python
3.12.16 and 3.15.2.
