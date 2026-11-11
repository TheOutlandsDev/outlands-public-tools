using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Reflection;
using System.Reflection.Metadata;
using System.Reflection.Metadata.Ecma335;
using System.Reflection.PortableExecutable;
using System.Runtime.InteropServices;
using System.ComponentModel;
using Microsoft.Win32.SafeHandles;
using Outlands.ApiDiff;

static class Tests
{
    static int passed, failed, skipped;
    static readonly List<object> skipReasons = [];
    static readonly List<(string Path, bool Directory)> links = [];
    static readonly bool requireNativeLinks = !OperatingSystem.IsWindows()
        || Environment.GetEnvironmentVariable("OUTLANDS_API_REQUIRE_NATIVE_LINKS") == "1"
        || Environment.GetEnvironmentVariable("OUTLANDS_REQUIRE_SYMLINK_TEST") == "1";
    static void Assert(bool condition) { if (!condition) throw new InvalidOperationException("Fixture assertion failed."); }
    static void Test(string name, Action action)
    {
        try { action(); passed++; Console.WriteLine("PASS: " + name); }
        catch (FixtureSkip reason) { skipped++; skipReasons.Add(new { name, reason = reason.Message }); Console.WriteLine("SKIP: " + name + ": " + reason.Message); }
        catch (Exception error) { failed++; Console.WriteLine("FAIL: " + name + ": " + error.GetType().Name); }
    }
    static void Check(Func<bool> condition, string name) => Test(name, () => Assert(condition()));
    static void MustRefuse(Action action)
    {
        try { action(); }
        catch (Exception ex) when (ex is AuditException or IOException or BadImageFormatException or UnauthorizedAccessException) { return; }
        throw new InvalidOperationException("Expected a metadata or local-file refusal.");
    }
    static void Refuses(Action action, string name) => Test(name, () => MustRefuse(action));
    static void NativeLink(string link, string target, bool directory)
    {
        try
        {
            if (directory) Directory.CreateSymbolicLink(link, target); else File.CreateSymbolicLink(link, target);
            links.Add((link, directory));
        }
        catch (Exception error) when (OperatingSystem.IsWindows() && !requireNativeLinks
            && (error is IOException or UnauthorizedAccessException) && (error.HResult & 0xffff) == 1314)
        { throw new FixtureSkip("WINDOWS_NATIVE_LINK_PRIVILEGE_UNAVAILABLE_1314"); }
    }
    static string TestParent()
    {
        string selected = Environment.GetEnvironmentVariable("OUTLANDS_TEST_TEMP_ROOT") ?? Path.GetTempPath();
        if (!Path.IsPathFullyQualified(selected)) throw new InvalidOperationException("Test parent must be absolute.");
        string parent = Path.TrimEndingDirectorySeparator(Path.GetFullPath(selected));
        if (!Directory.Exists(parent)) throw new InvalidOperationException("Test parent must exist.");
        for (string? current = parent; current is not null; current = Path.GetDirectoryName(current))
            if ((File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0) throw new InvalidOperationException("Test parent must be nonlinked.");
        return parent;
    }
    static void Junction(string link, string target)
    {
        Directory.CreateDirectory(link);
        byte[] substitute = Encoding.Unicode.GetBytes("\\??\\" + target), printable = Encoding.Unicode.GetBytes(target);
        using var data = new MemoryStream();
        using (var writer = new BinaryWriter(data, Encoding.Unicode, leaveOpen: true))
        {
            writer.Write(0xa0000003u); writer.Write((ushort)(8 + substitute.Length + printable.Length + 4)); writer.Write((ushort)0);
            writer.Write((ushort)0); writer.Write((ushort)substitute.Length); writer.Write((ushort)(substitute.Length + 2)); writer.Write((ushort)printable.Length);
            writer.Write(substitute); writer.Write((ushort)0); writer.Write(printable); writer.Write((ushort)0);
        }
        using SafeFileHandle handle = Native.CreateFile(link, 0x40000000, 0, IntPtr.Zero, 3, 0x02200000, IntPtr.Zero);
        if (handle.IsInvalid) throw new Win32Exception(Marshal.GetLastWin32Error());
        byte[] bytes = data.ToArray();
        if (!Native.DeviceIoControl(handle, 0x000900a4, bytes, (uint)bytes.Length, IntPtr.Zero, 0, out _, IntPtr.Zero))
            throw new Win32Exception(Marshal.GetLastWin32Error());
        links.Add((link, true));
    }
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
        string parent = TestParent();
        var root = Path.Combine(parent, "outlands-api-tests-" + Guid.NewGuid().ToString("N")); Directory.CreateDirectory(root);
        var originalTrap = Environment.GetEnvironmentVariable("OUTLANDS_API_EXECUTION_TRAP");
        try
        {
            string trap = Path.Combine(root, "executed.txt"); Environment.SetEnvironmentVariable("OUTLANDS_API_EXECUTION_TRAP", trap);
            var beforeBytes = File.ReadAllBytes(beforePath); var afterBytes = File.ReadAllBytes(afterPath);
            var before = Inspector.Inspect(beforePath); var after = Inspector.Inspect(afterPath); var report = Comparison.Compare(before, after);
            Check(() => before.Assembly == "Example.Plugin" && after.Assembly == before.Assembly, "authored builds have the same assembly identity");
            Check(() => !File.Exists(trap), "metadata comparison did not run module initializers");
            Check(() => before.Sha256 == Convert.ToHexString(SHA256.HashData(beforeBytes)).ToLowerInvariant(), "snapshot hash covers exact before bytes");
            Check(() => before.Declarations.Keys.SequenceEqual(before.Declarations.Keys.Order(StringComparer.Ordinal)), "declarations use deterministic ordinal order");
            Check(() => Comparison.Compare(before, before).Changes.Count == 0, "identical snapshot has no changes");
            Check(() => report.Changes.Count == 6, "exact golden change count");
            Check(() => report.Changes.Count(c => c.Kind == "added") == 1 && report.Changes.Count(c => c.Kind == "removed") == 2 && report.Changes.Count(c => c.Kind == "changed") == 3, "golden change kinds");
            Check(() => report.Changes.Any(c => c.Kind == "changed" && c.Id.Contains("Convert") && c.Before!.Contains("Int32") && c.After!.Contains("Int64")), "return change keeps method identity");
            Check(() => report.Changes.Any(c => c.Kind == "changed" && c.Id.Contains("Level")), "public field type change");
            Check(() => report.Changes.Any(c => c.Kind == "changed" && c.Id.Contains("property")), "public setter visibility change");
            Check(() => report.Changes.Any(c => c.Kind == "removed" && c.Id.Contains("set_Name")), "removed public accessor declaration");
            Check(() => report.Changes.Any(c => c.Kind == "added" && c.Id.Contains("Added")) && report.Changes.Any(c => c.Kind == "removed" && c.Id.Contains("Removed")), "added and removed methods");
            Check(() => before.Declarations.Keys.Count(k => k.Contains("Convert")) == 2, "overloads have separate identities");
            Check(() => before.Declarations.Keys.Any(k => JsonDocument.Parse(k).RootElement[1].GetString() == "Example.Plugin+Nested"), "nested public type visible");
            Check(() => !before.Declarations.Keys.Any(k => k.Contains("Hidden") || k.Contains("PrivateNested") || k.Contains("ProtectedOnly") || k.Contains("PrivateOnly")), "internal, private and protected APIs excluded");
            Check(() => before.Declarations.Keys.Any(k => k.Contains("event") && k.Contains("Completed")), "public event included");
            Check(() => before.Declarations.Keys.Any(k => k.Contains("Generic")) && before.Declarations.Values.Any(v => v.Contains("!!0")), "generic methods decoded");
            Check(() => before.Declarations.Values.Any(v => v.Contains("!0")), "generic type parameters decoded");
            Check(() => Values(before).Contains("System.Int32&"), "by-reference signatures decoded");
            Check(() => before.Declarations.Values.Any(v => v.Contains("System.Int32*")), "pointer signatures decoded");
            Check(() => before.Declarations.Values.Any(v => v.Contains("rank=2")), "multidimensional arrays decoded");
            Check(() => before.Declarations.Values.Any(v => v.Contains("[]")), "generic instantiation with array decoded");
            Check(() => before.Declarations.Values.Any(v => v.Contains("fnptr")), "function pointers decoded");
            Check(() => before.Declarations.Values.Any(v => v.Contains("modreq")), "required custom modifiers retained");
            Check(() => !report.Changes.Any(c => c.Id.Contains("Constant")), "documented constant-value exclusion");
            var changedIdentity = after with { Assembly = "Other.Plugin" }; Refuses(() => Comparison.Compare(before, changedIdentity), "different assembly simple names refused");
            var text = JsonSerializer.Serialize(report, Outlands.ApiDiff.Program.Json);
            using (var parsed = JsonDocument.Parse(text)) Check(() => parsed.RootElement.GetProperty("schemaVersion").GetInt32() == 1, "JSON report version");
            Check(() => !text.Contains(Path.GetDirectoryName(Path.GetFullPath(beforePath))!, StringComparison.Ordinal) && !text.Contains("ExecutionTrap"), "report omits input paths and internal execution trap");
            Check(() => Cli(["--help"], out var help, out var helpErr) == 0 && help.Contains("trusted") && helpErr.Length == 0, "help does not require file inputs");
            Check(() => Cli(["compare", "--before", beforePath, "--after", afterPath], out var cliReport, out _) == 1 && cliReport.Contains("changes"), "CLI changed exit code and report");
            Check(() => Cli(["compare", "--before", beforePath, "--after", beforePath], out _, out _) == 0, "CLI equal exit code");
            string output = Path.Combine(root, "report.json");
            Check(() => Cli(["compare", "--before", beforePath, "--after", afterPath, "--output", output], out var noStdout, out _) == 1 && File.Exists(output) && noStdout.Length == 0, "exclusive file report creation");
            var outputHash = SHA256.HashData(File.ReadAllBytes(output));
            Check(() => Cli(["compare", "--before", beforePath, "--after", afterPath, "--output", output], out _, out _) == 2 && outputHash.SequenceEqual(SHA256.HashData(File.ReadAllBytes(output))), "existing output never overwritten");
            Check(() => Cli(["compare", "--before", beforePath, "--after", afterPath, "--output", beforePath], out _, out _) == 2, "output cannot overwrite source");
            Check(() => Cli(["compare", "--before", beforePath, "--before", afterPath], out _, out _) == 2, "duplicate options rejected");
            Check(() => Cli(["compare", "--after", afterPath, "--unknown", "x"], out _, out _) == 2, "unknown options rejected");
            Check(() => Cli(["compare", "--before"], out _, out _) == 2, "incomplete options rejected");
            Check(() => Cli(["compare", "--after", afterPath], out _, out _) == 2, "missing required option rejected");
            var invalid = Path.Combine(root, "not-an-assembly.dll"); File.WriteAllText(invalid, "synthetic invalid binary");
            Check(() => Cli(["compare", "--before", invalid, "--after", afterPath], out _, out var failure) == 2 && !failure.Contains(root), "malformed input error omits private path");
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
            // Native fixtures never change device policy or request additional OS privileges.
            var link = Path.Combine(root, "link.dll");
            Test("symlink input refused", () => { NativeLink(link, Path.GetFullPath(beforePath), false); MustRefuse(() => Inspector.Inspect(link)); Assert(beforeBytes.SequenceEqual(File.ReadAllBytes(beforePath))); });
            Test("symlink input parent refused", () => { string real = Path.Combine(root, "input-real"), linked = Path.Combine(root, "input-linked"); Directory.CreateDirectory(real); string input = Path.Combine(real, "fixture.dll"); File.WriteAllBytes(input, beforeBytes); NativeLink(linked, real, true); MustRefuse(() => Inspector.Inspect(Path.Combine(linked, "fixture.dll"))); Assert(beforeBytes.SequenceEqual(File.ReadAllBytes(input))); });
            Test("symlink output parent refused", () => { string real = Path.Combine(root, "output-real"), linked = Path.Combine(root, "output-linked"); Directory.CreateDirectory(real); NativeLink(linked, real, true); Assert(Cli(["compare", "--before", beforePath, "--after", afterPath, "--output", Path.Combine(linked, "report.json")], out _, out _) == 2 && !File.Exists(Path.Combine(real, "report.json"))); });
            Test("existing symlink output preserves target", () => { string target = Path.Combine(root, "retained.json"), linked = Path.Combine(root, "retained-link.json"); byte[] retained = Encoding.UTF8.GetBytes("Fictional retained output.\n"); File.WriteAllBytes(target, retained); NativeLink(linked, target, false); Assert(Cli(["compare", "--before", beforePath, "--after", afterPath, "--output", linked], out _, out _) == 2 && retained.SequenceEqual(File.ReadAllBytes(target))); });
            Test("dangling symlink output creates no target", () => { string target = Path.Combine(root, "absent-target.json"), linked = Path.Combine(root, "dangling-link.json"); NativeLink(linked, target, false); Assert(Cli(["compare", "--before", beforePath, "--after", afterPath, "--output", linked], out _, out _) == 2 && !File.Exists(target)); });
            Test("Windows junction input and output parents refused", () => { if (!OperatingSystem.IsWindows()) throw new FixtureSkip("POSIX_HAS_NO_WINDOWS_JUNCTION"); string real = Path.Combine(root, "junction-real"), linked = Path.Combine(root, "junction-linked"); Directory.CreateDirectory(real); string input = Path.Combine(real, "fixture.dll"); File.WriteAllBytes(input, beforeBytes); Junction(linked, real); Assert((File.GetAttributes(linked) & FileAttributes.ReparsePoint) != 0); MustRefuse(() => Inspector.Inspect(Path.Combine(linked, "fixture.dll"))); Assert(Cli(["compare", "--before", beforePath, "--after", afterPath, "--output", Path.Combine(linked, "report.json")], out _, out _) == 2 && !File.Exists(Path.Combine(real, "report.json")) && beforeBytes.SequenceEqual(File.ReadAllBytes(input))); });
            Check(() => beforeBytes.SequenceEqual(File.ReadAllBytes(beforePath)) && afterBytes.SequenceEqual(File.ReadAllBytes(afterPath)), "original fixture bytes unchanged");
        }
        catch (Exception error) { failed++; Console.WriteLine("FAIL: harness setup or execution: " + error.GetType().Name); }
        finally
        {
            Environment.SetEnvironmentVariable("OUTLANDS_API_EXECUTION_TRAP", originalTrap);
            // The harness owns this fresh random child of the resolved temporary directory.
            var target = Path.GetFullPath(root);
            if (!string.Equals(Path.GetDirectoryName(target), parent, OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal)
                || !Path.GetFileName(target).StartsWith("outlands-api-tests-", StringComparison.Ordinal)
                || (File.GetAttributes(target) & FileAttributes.ReparsePoint) != 0) throw new Exception("Refusing unexpected test cleanup path.");
            foreach (var created in links) { if (created.Directory) Directory.Delete(created.Path); else File.Delete(created.Path); }
            Directory.Delete(target, recursive: true);
        }
        Console.WriteLine(JsonSerializer.Serialize(new { discovered = passed + failed + skipped, passed, failed, skipped, skipReasons, nativeLinksRequired = requireNativeLinks, modelOrHistoricalDataUsed = false }));
        return failed == 0 ? 0 : 1;
    }
}

sealed class FixtureSkip(string reason) : Exception(reason);
static class Native
{
    [DllImport("kernel32.dll", EntryPoint = "CreateFileW", CharSet = CharSet.Unicode, SetLastError = true)]
    internal static extern SafeFileHandle CreateFile(string path, uint access, uint share, IntPtr security, uint creation, uint flags, IntPtr template);
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    internal static extern bool DeviceIoControl(SafeFileHandle handle, uint code, byte[] input, uint inputSize, IntPtr output, uint outputSize, out uint returned, IntPtr overlapped);
}
