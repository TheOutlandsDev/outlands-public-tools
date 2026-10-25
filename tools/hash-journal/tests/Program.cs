// Original MIT generated fixtures. No game, historical chain data or network is used.
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using Outlands.HashJournal;

string parent = Path.TrimEndingDirectorySeparator(Path.GetFullPath(args.Length == 0 ? Path.GetTempPath() : args[0]));
if (!Directory.Exists(parent)) throw new InvalidOperationException("Explicit test parent must exist.");
string root = Path.Combine(parent, "hash-journal-tests-" + Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(root);
int passed = 0, failed = 0, skipped = 0;
var links = new List<(string Path, bool Directory)>();
string Fresh() => Path.Combine(root, Guid.NewGuid().ToString("N") + ".jsonl");
JournalRecord One(string text = "Fictional build prepared.") => Journal.NewRecord(1, Journal.Zero, text);
JournalRecord[] Two()
{
    JournalRecord one = One();
    return [one, Journal.NewRecord(2, one.Hash, "Fictional checks passed.")];
}
void Assert(bool value) { if (!value) throw new InvalidOperationException("Fixture assertion failed."); }
void Refused(Action action, string? code = null)
{
    try { action(); }
    catch (JournalException error) { if (code is not null) Assert(error.Code == code); return; }
    throw new InvalidOperationException("Expected a journal refusal.");
}
void Test(string name, Action action)
{
    try { action(); passed++; Console.WriteLine("PASS " + name); }
    catch (FixtureSkip) { skipped++; Console.WriteLine("SKIP " + name); }
    catch (Exception error) { failed++; Console.WriteLine("FAIL " + name + ": " + error.GetType().Name); }
}
byte[] Bytes(string text) => Encoding.UTF8.GetBytes(text);
string EncodedOne() => Encoding.UTF8.GetString(Journal.Encode([One()]));
int CliRun(string[] arguments, out string stdout, out string stderr)
{
    using var output = new StringWriter(); using var error = new StringWriter();
    int status = Cli.Run(arguments, output, error); stdout = output.ToString(); stderr = error.ToString(); return status;
}

try
{
    Test("Golden hash independently calculated with Python SHA-256", () => Assert(One().Hash == "66a82dd6cfc9760a7b9d754525fe693e9d63ca60e427e3d1d2bd25a4c61c398e"));
    Test("Public fictional example matches its independently generated head", () => { string fixture = Path.Combine(AppContext.BaseDirectory, "two-record.jsonl"); Verification value = Journal.Verify(Journal.ReadFile(fixture), "ec91f00284e1d0faccd7f3301ae23ae7af1c8eed6121cab890dd1648d9f33d36", 2); Assert(value.Anchor == "HEAD_MATCHED"); });
    Test("Valid one-record chain is explicitly unanchored", () => Assert(Journal.Verify([One()]).Anchor == "UNANCHORED"));
    Test("Two-record chain links and verifies", () => Assert(Journal.Verify(Two()).Count == 2));
    Test("Trusted head is explicitly matched", () => { var records = Two(); Assert(Journal.Verify(records, records[^1].Hash).Anchor == "HEAD_MATCHED"); });
    Test("Expected count alone does not claim anchored authenticity", () => { var report = Journal.Verify(Two(), expectedCount: 2); Assert(report.Anchor == "UNANCHORED" && report.ExpectedCountMatched == true); });
    Test("Text rewrite with old hash is refused", () => Refused(() => Journal.Verify([One() with { Text = "Changed fictional event." }]), "HASH_MISMATCH"));
    Test("Previous-link rewrite is refused", () => { var records = Two(); records[1] = records[1] with { Previous = Journal.Zero }; Refused(() => Journal.Verify(records), "PREVIOUS_MISMATCH"); });
    Test("Reordered records are refused", () => { var records = Two(); Refused(() => Journal.Verify([records[1], records[0]]), "SEQUENCE_MISMATCH"); });
    Test("Sequence gap is refused", () => Refused(() => Journal.Verify([One() with { Sequence = 2 }]), "SEQUENCE_MISMATCH"));
    Test("Tail truncation can still be internally valid without an anchor", () => Assert(Journal.Verify([Two()[0]]).Count == 1));
    Test("Trusted head catches complete-record tail truncation", () => { var records = Two(); Refused(() => Journal.Verify([records[0]], records[1].Hash), "EXPECTED_HEAD_MISMATCH"); });
    Test("Trusted count catches complete-record tail truncation", () => Refused(() => Journal.Verify([One()], expectedCount: 2), "EXPECTED_COUNT_MISMATCH"));
    Test("Full chain rewrite needs a separately trusted head", () => { var rewritten = One("Different fictional event."); Assert(Journal.Verify([rewritten]).Count == 1); Refused(() => Journal.Verify([rewritten], One().Hash), "EXPECTED_HEAD_MISMATCH"); });
    Test("Malformed expected head is refused", () => Refused(() => Journal.Verify([One()], "not-a-hash"), "INVALID_EXPECTED_HEAD"));
    Test("Uppercase hashes are outside canonical format", () => Refused(() => Journal.Verify([One() with { Hash = One().Hash.ToUpperInvariant() }]), "INVALID_HASH"));
    Test("Expected count must be positive", () => Refused(() => Journal.Verify([One()], expectedCount: 0), "INVALID_EXPECTED_COUNT"));
    Test("Expected count ceiling is enforced", () => Refused(() => Journal.Verify([One()], expectedCount: Journal.MaxRecords + 1), "INVALID_EXPECTED_COUNT"));
    Test("Empty chains are refused", () => Refused(() => Journal.Verify([]), "RECORD_LIMIT"));
    Test("Record ceiling is enforced before enumeration", () => Refused(() => Journal.Verify(Enumerable.Repeat(One(), Journal.MaxRecords + 1).ToArray()), "RECORD_LIMIT"));
    Test("Empty text is refused", () => Refused(() => One(""), "EMPTY_TEXT"));
    Test("Whitespace-only text is refused", () => Refused(() => One(" \t\n"), "EMPTY_TEXT"));
    Test("Text byte bound accepts its exact multibyte boundary", () => Assert(One(new string('\u00e9', 4096)).Text.Length == 4096));
    Test("Text byte bound refuses excess multibyte data", () => Refused(() => One(new string('\u00e9', 4097)), "TEXT_BYTE_LIMIT"));
    Test("Unpaired UTF-16 surrogate text is refused", () => Refused(() => One("\ud800"), "INVALID_UNICODE"));
    Test("Unicode is preserved without implicit normalization", () => Assert(One("\u00e9").Hash != One("e\u0301").Hash));
    Test("Newline and quote text round trips", () => { string text = "Fictional\nsecond line \"quoted\"\rreturn"; Assert(Journal.Parse(Journal.Encode([One(text)]))[0].Text == text); });
    Test("Encoding is deterministic and uses LF", () => { byte[] one = Journal.Encode(Two()); Assert(one.SequenceEqual(Journal.Encode(Two())) && one[^1] == 10 && !one.Contains((byte)13)); });
    Test("JSON member order and string escape spelling are not hash inputs", () => { JournalRecord record = One("a"); string raw = $"{{\"hash\":\"{record.Hash}\",\"text\":\"\\u0061\",\"previous\":\"{Journal.Zero}\",\"sequence\":1,\"schema\":1}}\n"; Assert(Journal.Parse(Bytes(raw))[0].Text == "a"); });
    Test("Missing final LF is detected", () => Refused(() => Journal.Parse(Journal.Encode([One()])[..^1]), "FINAL_LF_REQUIRED"));
    Test("CRLF conversion is explicitly refused", () => Refused(() => Journal.Parse(Bytes(EncodedOne().Replace("\n", "\r\n", StringComparison.Ordinal))), "CRLF_UNSUPPORTED"));
    Test("Blank JSONL lines are refused", () => Refused(() => Journal.Parse(Bytes(EncodedOne() + "\n")), "LINE_BYTE_LIMIT"));
    Test("UTF-8 BOM is refused", () => Refused(() => Journal.Parse([0xef, 0xbb, 0xbf, .. Journal.Encode([One()])]), "BOM_UNSUPPORTED"));
    Test("Invalid UTF-8 is refused", () => Refused(() => Journal.Parse([0xff, 0x0a]), "INVALID_UTF8"));
    Test("Oversized input bytes are refused", () => Refused(() => Journal.Parse(new byte[Journal.MaxBytes + 1]), "INPUT_BYTE_LIMIT"));
    Test("Oversized JSONL line is refused", () => Refused(() => Journal.Parse(Bytes(new string(' ', Journal.MaxLineBytes + 1) + "\n")), "LINE_BYTE_LIMIT"));
    Test("Malformed JSON is refused", () => Refused(() => Journal.Parse(Bytes("{broken\n")), "INVALID_JSON"));
    Test("Non-object records are refused", () => Refused(() => Journal.Parse(Bytes("[]\n")), "RECORD_OBJECT_REQUIRED"));
    Test("Duplicate JSON properties are refused", () => Refused(() => Journal.Parse(Bytes(EncodedOne().Replace("\"schema\":1", "\"schema\":1,\"schema\":1", StringComparison.Ordinal))), "DUPLICATE_PROPERTY"));
    Test("Unknown JSON properties are refused", () => Refused(() => Journal.Parse(Bytes(EncodedOne().Replace("\"schema\":1", "\"schema\":1,\"other\":1", StringComparison.Ordinal))), "UNKNOWN_PROPERTY"));
    Test("Missing JSON properties are refused", () => Refused(() => Journal.Parse(Bytes(EncodedOne().Replace("\"schema\":1,", "", StringComparison.Ordinal))), "MISSING_PROPERTY"));
    Test("Unknown schema is refused", () => Refused(() => Journal.Parse(Bytes(EncodedOne().Replace("\"schema\":1", "\"schema\":2", StringComparison.Ordinal))), "UNSUPPORTED_SCHEMA"));
    Test("Boolean schema is refused", () => Refused(() => Journal.Parse(Bytes(EncodedOne().Replace("\"schema\":1", "\"schema\":true", StringComparison.Ordinal))), "UNSUPPORTED_SCHEMA"));
    Test("Floating sequence syntax is refused", () => Refused(() => Journal.Parse(Bytes(EncodedOne().Replace("\"sequence\":1", "\"sequence\":1.0", StringComparison.Ordinal))), "INVALID_SEQUENCE"));
    Test("Nonfinite JSON token is refused", () => Refused(() => Journal.Parse(Bytes(EncodedOne().Replace("\"sequence\":1", "\"sequence\":NaN", StringComparison.Ordinal))), "INVALID_JSON"));
    Test("Escaped unpaired surrogate is refused", () => { string raw = $"{{\"schema\":1,\"sequence\":1,\"previous\":\"{Journal.Zero}\",\"text\":\"\\ud800\",\"hash\":\"{One("\ufffd").Hash}\"}}\n"; Refused(() => Journal.Parse(Bytes(raw))); });
    Test("Strict property type is enforced", () => Refused(() => Journal.Parse(Bytes(EncodedOne().Replace("\"previous\":\"" + Journal.Zero + "\"", "\"previous\":null", StringComparison.Ordinal))), "STRING_PROPERTY_REQUIRED"));
    Test("Fresh create writes a valid one-record file", () => { string file = Fresh(); Journal.Create(file, "Fictional event."); Assert(Journal.ReadFile(file).Count == 1); });
    Test("Append writes a new version and preserves input bytes", () => { string old = Fresh(), updated = Fresh(); Journal.Create(old, "First fictional event."); byte[] before = File.ReadAllBytes(old); Journal.Append(old, updated, "Second fictional event."); Assert(before.SequenceEqual(File.ReadAllBytes(old)) && Journal.ReadFile(updated).Count == 2); });
    Test("Existing output is not overwritten", () => { string file = Fresh(); Journal.Create(file, "First fictional event."); byte[] before = File.ReadAllBytes(file); Refused(() => Journal.Create(file, "Changed event."), "OUTPUT_EXISTS"); Assert(before.SequenceEqual(File.ReadAllBytes(file))); });
    Test("Append cannot use its input as output", () => { string file = Fresh(); Journal.Create(file, "First fictional event."); byte[] before = File.ReadAllBytes(file); Refused(() => Journal.Append(file, file, "Next event."), "OUTPUT_EXISTS"); Assert(before.SequenceEqual(File.ReadAllBytes(file))); });
    Test("Corrupt input creates no append output", () => { string bad = Fresh(), target = Fresh(); File.WriteAllText(bad, "broken\n"); Refused(() => Journal.Append(bad, target, "Next event.")); Assert(!File.Exists(target)); });
    Test("Invalid selected records create no output", () => { string target = Fresh(); Refused(() => Journal.WriteFresh(target, [One() with { Text = "tampered" }])); Assert(!File.Exists(target)); });
    Test("Oversized encoded journal creates no output", () => { var records = new List<JournalRecord>(); string previous = Journal.Zero; for (int n = 1; n <= 150; n++) { var next = Journal.NewRecord(n, previous, new string('x', Journal.MaxTextBytes)); records.Add(next); previous = next.Hash; } string target = Fresh(); Refused(() => Journal.WriteFresh(target, records), "OUTPUT_BYTE_LIMIT"); Assert(!File.Exists(target)); });
    Test("Relative input paths are refused", () => Refused(() => Journal.ReadFile("fixture.jsonl"), "ABSOLUTE_PATH_REQUIRED"));
    Test("Relative output paths are refused", () => Refused(() => Journal.Create("fixture.jsonl", "Fictional event."), "ABSOLUTE_PATH_REQUIRED"));
    Test("Missing output parent is not created", () => { string directory = Path.Combine(root, "missing"); Refused(() => Journal.Create(Path.Combine(directory, "new.jsonl"), "Fictional event."), "PARENT_DIRECTORY_REQUIRED"); Assert(!Directory.Exists(directory)); });
    Test("Directory inputs are refused", () => Refused(() => Journal.ReadFile(root), "REGULAR_FILE_REQUIRED"));
    Test("Empty input is refused before opening", () => { string file = Fresh(); File.WriteAllBytes(file, []); Refused(() => Journal.ReadFile(file), "INPUT_BYTE_LIMIT"); });
    Test("Oversized file is refused before parsing", () => { string file = Fresh(); File.WriteAllBytes(file, new byte[Journal.MaxBytes + 1]); Refused(() => Journal.ReadFile(file), "INPUT_BYTE_LIMIT"); });
    Test("Leaf symlink input is refused", () => { string target = Fresh(), link = Fresh(); Journal.Create(target, "Fictional event."); try { File.CreateSymbolicLink(link, target); links.Add((link, false)); } catch (Exception e) when (e is UnauthorizedAccessException or IOException or PlatformNotSupportedException) { throw new FixtureSkip(); } Refused(() => Journal.ReadFile(link), "LINKED_PATH"); });
    Test("Symlink parent output is refused", () => { string target = Path.Combine(root, "real"), link = Path.Combine(root, "linked"); Directory.CreateDirectory(target); try { Directory.CreateSymbolicLink(link, target); links.Add((link, true)); } catch (Exception e) when (e is UnauthorizedAccessException or IOException or PlatformNotSupportedException) { throw new FixtureSkip(); } Refused(() => Journal.Create(Path.Combine(link, "new.jsonl"), "Fictional event."), "LINKED_PATH"); Assert(!File.Exists(Path.Combine(target, "new.jsonl"))); });
    Test("Unix new outputs request owner-only mode", () => { if (OperatingSystem.IsWindows()) throw new FixtureSkip(); string file = Fresh(); Journal.Create(file, "Fictional event."); Assert((File.GetUnixFileMode(file) & (UnixFileMode.GroupRead | UnixFileMode.GroupWrite | UnixFileMode.OtherRead | UnixFileMode.OtherWrite)) == 0); });
    Test("Unix FIFO input is refused without opening", () => { if (OperatingSystem.IsWindows()) throw new FixtureSkip(); string fifo = Fresh(); if (Native.Mkfifo(fifo, 0x180) != 0) throw new InvalidOperationException("Could not make disposable FIFO."); Refused(() => Journal.ReadFile(fifo), "INPUT_BYTE_LIMIT"); });
    Test("CLI help does not open selected inputs", () => { int code = CliRun([], out string stdout, out string stderr); Assert(code == 0 && stdout.Contains("Fresh output", StringComparison.Ordinal) && stderr.Length == 0); });
    Test("CLI demo is explicitly simulated", () => { int code = CliRun(["demo"], out string stdout, out string stderr); using var data = JsonDocument.Parse(stdout); Assert(code == 0 && data.RootElement.GetProperty("simulated").GetBoolean() && !data.RootElement.GetProperty("writes").GetBoolean() && stderr.Length == 0); });
    Test("CLI create and anchored verify emit metadata only", () => { string file = Fresh(); int code = CliRun(["create", "--output", file, "--text", "PRIVATE_FIXTURE_CONTENT"], out string stdout, out string stderr); Assert(code == 0 && !stdout.Contains("PRIVATE_FIXTURE_CONTENT", StringComparison.Ordinal) && !stdout.Contains(root, StringComparison.Ordinal) && stderr.Length == 0); string head = Journal.Verify(Journal.ReadFile(file)).Head; code = CliRun(["verify", "--input", file, "--expected-head", head, "--expected-count", "1"], out stdout, out stderr); Assert(code == 0 && stdout.Contains("VALID_HEAD_MATCHED", StringComparison.Ordinal) && stderr.Length == 0); });
    Test("CLI errors do not echo paths or text", () => { int code = CliRun(["verify", "--input", Path.Combine(root, "PRIVATE_NAME.jsonl")], out string stdout, out string stderr); Assert(code == 2 && stdout.Length == 0 && !stderr.Contains(root, StringComparison.Ordinal) && !stderr.Contains("PRIVATE_NAME", StringComparison.Ordinal)); });
    Test("CLI duplicate arguments are refused", () => Assert(CliRun(["verify", "--input", Fresh(), "--input", Fresh()], out _, out _) == 2));
    Test("CLI unknown options are refused", () => Assert(CliRun(["verify", "--unknown", "fictional"], out _, out _) == 2));
    Test("CLI missing values are refused", () => Assert(CliRun(["create", "--output"], out _, out _) == 2));
    Test("CLI expected count syntax is strict", () => Assert(CliRun(["verify", "--input", Fresh(), "--expected-count", "+1"], out _, out _) == 2));
    Test("CLI append preserves original and reports unanchored status", () => { string old = Fresh(), updated = Fresh(); Journal.Create(old, "Fictional event."); Assert(CliRun(["append", "--input", old, "--output", updated, "--text", "Another fictional event."], out string stdout, out string stderr) == 0 && stdout.Contains("VALID_UNANCHORED", StringComparison.Ordinal) && stderr.Length == 0 && Journal.ReadFile(old).Count == 1); });
}
finally
{
    foreach (var link in links) { if (link.Directory) Directory.Delete(link.Path); else File.Delete(link.Path); }
    string full = Path.GetFullPath(root);
    if (Path.GetDirectoryName(full) == parent && Path.GetFileName(full).StartsWith("hash-journal-tests-", StringComparison.Ordinal)) Directory.Delete(full, true);
}
Console.WriteLine(JsonSerializer.Serialize(new { discovered = passed + failed + skipped, passed, failed, skipped, modelOrHistoricalDataUsed = false }));
return failed == 0 ? 0 : 1;

sealed class FixtureSkip : Exception;
static class Native
{
    [DllImport("libc", EntryPoint = "mkfifo", SetLastError = true)]
    public static extern int Mkfifo(string path, uint mode);
}
