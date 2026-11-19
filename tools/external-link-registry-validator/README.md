# Offline External Link Registry Validator

Check a saved list of external HTTP(S) links for alphabetical label order,
exact duplicate labels, valid URL syntax, and embedded credentials or session
query keys. The validator reads the saved registry offline and reports a count.

- [Source ZIP, SHA-256 checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/external-link-registry-validator-v0.1.0)
- [Usage guide and 25 fictional links](SETUP.md)

The source edition retains the two original registry tests with fictional
data and uses the Python standard library. Qualification covers Windows and
Ubuntu with Python 3.12.16 and 3.15.2.
