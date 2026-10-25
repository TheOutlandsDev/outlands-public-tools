# Fictional plugin update

The two source fixtures under [tests/Before](../tests/Before/Api.cs) and [tests/After](../tests/After/Api.cs) model an ordinary plugin update. Build them with the README commands, then compare the generated `Example.Plugin.dll` files. There is no download or game installation prerequisite.

Expected changes:

| Change | Interpretation |
| --- | --- |
| `Plugin.Added()` added | New public method. |
| `Plugin.Removed()` removed | Previous public method no longer declared. |
| `Plugin.set_Name(string)` removed | Setter is now private. |
| `Plugin.Name` changed | Public setter presence changed from true to false. |
| `Plugin.Level` changed | Field type changed from `Int32` to `Int64`. |
| `Plugin.Convert(Int32)` changed | Return type changed from `Int32` to `Int64`; method identity stays the same. |

The string overload of `Convert` is unchanged. `Constant` changes from 1 to 2, but constant values are outside this tool's scope and no change is emitted for it. This example demonstrates why an empty result cannot serve as a compatibility guarantee.

An identity in the JSON report is an encoded tuple, for example:

```json
["method", "Example.Plugin", "Convert", 0, ["System.Int32"]]
```

The CLI emits this tuple inside a JSON string. Parse JSON twice to read that tuple, first the report and then the `id`. Method return values are in `before` and `after`, so this return-type change is classified as `changed`, not a removed/added pair.

Keep generated files in the external artifacts directory. Build hashes can differ with compiler version and environment; compare the declaration fields rather than copying a hardcoded hash from an example. Real metadata reports may identify internal project names even though the report omits filesystem input paths.
