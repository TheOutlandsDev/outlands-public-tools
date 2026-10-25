using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Reflection;
using System.Reflection.Metadata;
using System.Reflection.Metadata.Ecma335;
using System.Reflection.PortableExecutable;
using Outlands.ApiDiff;

static class Tests
{
    static int count;
    static void Check(bool condition, string name) { if (!condition) throw new Exception("FAIL: " + name); count++; Console.WriteLine("PASS: " + name); }
    static void Refuses(Action action, string name) { try { action(); } catch (Exception ex) when (ex is AuditException or IOException or BadImageFormatException or UnauthorizedAccessException) { Check(true, name); return; } throw new Exception("FAIL: " + name); }
    static string Values(Snapshot snapshot) => string.Join("\n", snapshot.Declarations.Values.SelectMany(value => JsonDocument.Parse(value).RootElement.EnumerateArray().Where(e => e.ValueKind == JsonValueKind.String).Select(e => e.GetString())));
    static void MakeAssembly(string path, byte[] signature, bool duplicate = false, string typeName = "Synthetic")
    {
        var metadata = new MetadataBuilder();
        metadata.AddModule(0, metadata.GetOrAddString("Synthetic.dll"), metadata.GetOrAddGuid(Guid.NewGuid()), default, default);
        metadata.AddAssembly(metadata.GetOrAddString("Synthetic"), new Version(1, 0), default, default, 0, AssemblyHashAlgorithm.None);
        metadata.AddTypeDefinition(TypeAttributes.NotPublic, default, metadata.GetOrAddString("<Module>"), default, MetadataTokens.FieldDefinitionHandle(1), MetadataTokens.MethodDefinitionHandle(1));
        metadata.AddTypeDefinition(TypeAttributes.Public, metadata.GetOrAddString("Example"), metadata.GetOrAddString(typeName), default, MetadataTokens.FieldDefinitionHandle(1), MetadataTokens.MethodDefinitionHandle(1));
        for (int i = 0; i < (duplicate ? 2 : 1); i++) metadata.AddMethodDefinition(MethodAttributes.Public | MethodAttributes.Static, MethodImplAttributes.IL, metadata.GetOrAddString("Method"), metadata.GetOrAddBlob(signature), 0, MetadataTokens.ParameterHandle(1));
        var builder = new ManagedPEBuilder(new PEHeaderBuilder(imageCharacteristics: Characteristics.ExecutableImage | Characteristics.Dll), new MetadataRootBuilder(metadata), new BlobBuilder(), flags: CorFlags.ILOnly);
        var content = new BlobBuilder(); builder.Serialize(content); File.WriteAllBytes(path, content.ToArray());
    }
    static int Cli(string[] args, out string stdout, out string stderr)
    {
        var originalOut = Console.Out; var originalError = Console.Error;
        using var output = new StringWriter(); using var error = new StringWriter();
        try { Console.SetOut(output); Console.SetError(error); return Outlands.ApiDiff.Program.Main(args); }
        finally { stdout = output.ToString(); stderr = error.ToString(); Console.SetOut(originalOut); Console.SetError(originalError); }
    }
    public static int Main(string[] args)
    {
        if (args.Length is not (0 or 2)) throw new Exception("Supply both fixture DLL paths or no arguments with standard artifacts layout.");
        var artifacts = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "../../.."));
        var beforePath = args.Length == 2 ? args[0] : Path.Combine(artifacts, "bin/Before/release/Example.Plugin.dll");
        var afterPath = args.Length == 2 ? args[1] : Path.Combine(artifacts, "bin/After/release/Example.Plugin.dll");
        var root = Path.Combine(Path.GetTempPath(), "outlands-api-tests-" + Guid.NewGuid().ToString("N")); Directory.CreateDirectory(root);
        var originalTrap = Environment.GetEnvironmentVariable("OUTLANDS_API_EXECUTION_TRAP");
        try
        {
            string trap = Path.Combine(root, "executed.txt"); Environment.SetEnvironmentVariable("OUTLANDS_API_EXECUTION_TRAP", trap);
            var beforeBytes = File.ReadAllBytes(beforePath); var afterBytes = File.ReadAllBytes(afterPath);
            var before = Inspector.Inspect(beforePath); var after = Inspector.Inspect(afterPath); var report = Comparison.Compare(before, after);
            Check(before.Assembly == "Example.Plugin" && after.Assembly == before.Assembly, "authored builds have the same assembly identity");
            Check(!File.Exists(trap), "metadata comparison did not run module initializers");
            Check(before.Sha256 == Convert.ToHexString(SHA256.HashData(beforeBytes)).ToLowerInvariant(), "snapshot hash covers exact before bytes");
            Check(before.Declarations.Keys.SequenceEqual(before.Declarations.Keys.Order(StringComparer.Ordinal)), "declarations use deterministic ordinal order");
            Check(Comparison.Compare(before, before).Changes.Count == 0, "identical snapshot has no changes");
            Check(report.Changes.Count == 6, "exact golden change count");
            Check(report.Changes.Count(c => c.Kind == "added") == 1 && report.Changes.Count(c => c.Kind == "removed") == 2 && report.Changes.Count(c => c.Kind == "changed") == 3, "golden change kinds");
            Check(report.Changes.Any(c => c.Kind == "changed" && c.Id.Contains("Convert") && c.Before!.Contains("Int32") && c.After!.Contains("Int64")), "return change keeps method identity");
            Check(report.Changes.Any(c => c.Kind == "changed" && c.Id.Contains("Level")), "public field type change");
            Check(report.Changes.Any(c => c.Kind == "changed" && c.Id.Contains("property")), "public setter visibility change");
            Check(report.Changes.Any(c => c.Kind == "removed" && c.Id.Contains("set_Name")), "removed public accessor declaration");
            Check(report.Changes.Any(c => c.Kind == "added" && c.Id.Contains("Added")) && report.Changes.Any(c => c.Kind == "removed" && c.Id.Contains("Removed")), "added and removed methods");
            Check(before.Declarations.Keys.Count(k => k.Contains("Convert")) == 2, "overloads have separate identities");
            Check(before.Declarations.Keys.Any(k => JsonDocument.Parse(k).RootElement[1].GetString() == "Example.Plugin+Nested"), "nested public type visible");
            Check(!before.Declarations.Keys.Any(k => k.Contains("Hidden") || k.Contains("PrivateNested") || k.Contains("ProtectedOnly") || k.Contains("PrivateOnly")), "internal, private and protected APIs excluded");
            Check(before.Declarations.Keys.Any(k => k.Contains("event") && k.Contains("Completed")), "public event included");
            Check(before.Declarations.Keys.Any(k => k.Contains("Generic")) && before.Declarations.Values.Any(v => v.Contains("!!0")), "generic methods decoded");
            Check(before.Declarations.Values.Any(v => v.Contains("!0")), "generic type parameters decoded");
            Check(Values(before).Contains("System.Int32&"), "by-reference signatures decoded");
            Check(before.Declarations.Values.Any(v => v.Contains("System.Int32*")), "pointer signatures decoded");
            Check(before.Declarations.Values.Any(v => v.Contains("rank=2")), "multidimensional arrays decoded");
            Check(before.Declarations.Values.Any(v => v.Contains("[]")), "generic instantiation with array decoded");
            Check(before.Declarations.Values.Any(v => v.Contains("fnptr")), "function pointers decoded");
            Check(before.Declarations.Values.Any(v => v.Contains("modreq")), "required custom modifiers retained");
            Check(!report.Changes.Any(c => c.Id.Contains("Constant")), "documented constant-value exclusion");
            var changedIdentity = after with { Assembly = "Other.Plugin" }; Refuses(() => Comparison.Compare(before, changedIdentity), "different assembly simple names refused");
            var text = JsonSerializer.Serialize(report, Outlands.ApiDiff.Program.Json);
            using (var parsed = JsonDocument.Parse(text)) Check(parsed.RootElement.GetProperty("schemaVersion").GetInt32() == 1, "JSON report version");
            Check(!text.Contains(Path.GetDirectoryName(Path.GetFullPath(beforePath))!, StringComparison.Ordinal) && !text.Contains("ExecutionTrap"), "report omits input paths and internal execution trap");
            Check(Cli(["--help"], out var help, out var helpErr) == 0 && help.Contains("trusted") && helpErr.Length == 0, "help does not require file inputs");
            Check(Cli(["compare", "--before", beforePath, "--after", afterPath], out var cliReport, out _) == 1 && cliReport.Contains("changes"), "CLI changed exit code and report");
            Check(Cli(["compare", "--before", beforePath, "--after", beforePath], out _, out _) == 0, "CLI equal exit code");
            string output = Path.Combine(root, "report.json");
            Check(Cli(["compare", "--before", beforePath, "--after", afterPath, "--output", output], out var noStdout, out _) == 1 && File.Exists(output) && noStdout.Length == 0, "exclusive file report creation");
            var outputHash = SHA256.HashData(File.ReadAllBytes(output));
            Check(Cli(["compare", "--before", beforePath, "--after", afterPath, "--output", output], out _, out _) == 2 && outputHash.SequenceEqual(SHA256.HashData(File.ReadAllBytes(output))), "existing output never overwritten");
            Check(Cli(["compare", "--before", beforePath, "--after", afterPath, "--output", beforePath], out _, out _) == 2, "output cannot overwrite source");
            Check(Cli(["compare", "--before", beforePath, "--before", afterPath], out _, out _) == 2, "duplicate options rejected");
            Check(Cli(["compare", "--after", afterPath, "--unknown", "x"], out _, out _) == 2, "unknown options rejected");
            Check(Cli(["compare", "--before"], out _, out _) == 2, "incomplete options rejected");
            Check(Cli(["compare", "--after", afterPath], out _, out _) == 2, "missing required option rejected");
            var invalid = Path.Combine(root, "not-an-assembly.dll"); File.WriteAllText(invalid, "synthetic invalid binary");
            Check(Cli(["compare", "--before", invalid, "--after", afterPath], out _, out var failure) == 2 && !failure.Contains(root), "malformed input error omits private path");
            var empty = Path.Combine(root, "empty.dll"); File.WriteAllBytes(empty, []); Refuses(() => Inspector.Inspect(empty), "empty input refused");
            var huge = Path.Combine(root, "too-large.dll"); using (var stream = File.Create(huge)) stream.SetLength(Inspector.MaxFileBytes + 1);
            Refuses(() => Inspector.Inspect(huge), "oversized file rejected before read");
            var malformedSignature = Path.Combine(root, "bad-signature.dll"); MakeAssembly(malformedSignature, [0, 0, 1, 1]);
            Refuses(() => Inspector.Inspect(malformedSignature), "trailing signature data refused");
            var deepSignature = Path.Combine(root, "deep-signature.dll"); MakeAssembly(deepSignature, [0, 0, ..Enumerable.Repeat((byte)0x1d, Inspector.MaxDepth + 2), 8]);
            Refuses(() => Inspector.Inspect(deepSignature), "signature depth bound enforced");
            var tooManyParameters = Path.Combine(root, "too-many-parameters.dll"); MakeAssembly(tooManyParameters, [0, 0x84, 0x01, 1]);
            Refuses(() => Inspector.Inspect(tooManyParameters), "signature element bound enforced");
            var duplicateMethods = Path.Combine(root, "duplicate-methods.dll"); MakeAssembly(duplicateMethods, [0, 0, 1], true);
            Refuses(() => Inspector.Inspect(duplicateMethods), "duplicate API identities refused rather than collapsed");
            var delimiterType = Path.Combine(root, "delimiter-type.dll"); MakeAssembly(delimiterType, [0, 0, 1], typeName: "Synthetic.Alias");
            Refuses(() => Inspector.Inspect(delimiterType), "type-name delimiters refused rather than aliasing namespace identity");
            Refuses(() => Inspector.Inspect(root), "directory input refused");
            Refuses(() => Inspector.Inspect(Path.Combine(root, "missing.dll")), "missing input refused");
            Refuses(() => LocalFiles.Validate("\\\\example.invalid\\data.dll", true), "UNC input refused");
            Refuses(() => LocalFiles.Validate("bad\nname.dll", true), "control character path refused");
            Refuses(() => LocalFiles.Validate(Path.Combine(root, "absent", "report.json"), false), "output parent must already exist");
            // Symlink creation on Windows needs Developer Mode or administrator. Exercise it when creation is permitted.
            var link = Path.Combine(root, "link.dll");
            try { File.CreateSymbolicLink(link, Path.GetFullPath(beforePath)); Refuses(() => Inspector.Inspect(link), "symlink input refused"); }
            catch (Exception ex) when (ex is UnauthorizedAccessException or IOException or PlatformNotSupportedException)
            {
                if (OperatingSystem.IsLinux() || Environment.GetEnvironmentVariable("OUTLANDS_REQUIRE_SYMLINK_TEST") == "1") throw new Exception("Required symlink test could not run.", ex);
                Console.WriteLine("SKIP: symlink creation unavailable (OS privilege); Linux CI exercises refusal.");
            }
            Check(beforeBytes.SequenceEqual(File.ReadAllBytes(beforePath)) && afterBytes.SequenceEqual(File.ReadAllBytes(afterPath)), "original fixture bytes unchanged");
            Console.WriteLine($"PASS: {count} assertions"); return 0;
        }
        finally
        {
            Environment.SetEnvironmentVariable("OUTLANDS_API_EXECUTION_TRAP", originalTrap);
            // The harness owns this fresh random child of the resolved temporary directory.
            var temp = Path.TrimEndingDirectorySeparator(Path.GetFullPath(Path.GetTempPath())) + Path.DirectorySeparatorChar;
            var target = Path.GetFullPath(root);
            if (!target.StartsWith(temp, OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal) || !Path.GetFileName(target).StartsWith("outlands-api-tests-", StringComparison.Ordinal)) throw new Exception("Refusing unexpected test cleanup path.");
            Directory.Delete(target, recursive: true);
        }
    }
}
