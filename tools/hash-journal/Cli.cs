// Original MIT command interface. It opens only explicitly selected files.
using System.Globalization;
using System.Text.Json;

namespace Outlands.HashJournal;

public static class Cli
{
    private static void Emit(TextWriter writer, object value) => writer.WriteLine(JsonSerializer.Serialize(value));

    public static int Run(string[] args, TextWriter output, TextWriter error)
    {
        try
        {
            if (args.Length == 0 || args is ["--help"] or ["help"])
            {
                output.WriteLine("Outlands Hash Journal 0.1.0\ncreate --output ABSOLUTE_NEW_FILE --text TEXT\nappend --input ABSOLUTE_FILE --output ABSOLUTE_NEW_FILE --text TEXT\nverify --input ABSOLUTE_FILE [--expected-head LOWERCASE_SHA256] [--expected-count N]\ndemo\nNo input/output defaults. Fresh output files only. Keep real journals private.");
                return 0;
            }
            if (args is ["demo"])
            {
                JournalRecord first = Journal.NewRecord(1, Journal.Zero, "Fictional build prepared.");
                JournalRecord second = Journal.NewRecord(2, first.Hash, "Fictional checks passed.");
                Emit(output, new { simulated = true, writes = false, purpose = "Generated display only; use create/append for JSONL files. No file opened.", count = 2, head = second.Hash, anchor = "UNANCHORED", records = new[] {
                    new { schema = 1, sequence = first.Sequence, previous = first.Previous, text = first.Text, hash = first.Hash },
                    new { schema = 1, sequence = second.Sequence, previous = second.Previous, text = second.Text, hash = second.Hash } } });
                return 0;
            }
            string command = args[0];
            string[] allowed = command switch
            {
                "create" => ["--output", "--text"],
                "append" => ["--input", "--output", "--text"],
                "verify" => ["--input", "--expected-head", "--expected-count"],
                _ => throw new JournalException("UNKNOWN_COMMAND")
            };
            var values = new Dictionary<string, string>(StringComparer.Ordinal);
            for (int index = 1; index < args.Length; index += 2)
            {
                if (index + 1 == args.Length || !allowed.Contains(args[index]) || !values.TryAdd(args[index], args[index + 1]))
                    throw new JournalException("INVALID_ARGUMENTS");
            }
            string Required(string name) => values.TryGetValue(name, out string? value) ? value : throw new JournalException("MISSING_ARGUMENT");
            Verification report;
            if (command == "create") report = Journal.Create(Required("--output"), Required("--text"));
            else if (command == "append") report = Journal.Append(Required("--input"), Required("--output"), Required("--text"));
            else
            {
                string? expected = values.GetValueOrDefault("--expected-head");
                int? count = null;
                if (values.TryGetValue("--expected-count", out string? text))
                {
                    if (!int.TryParse(text, NumberStyles.None, CultureInfo.InvariantCulture, out int number)) throw new JournalException("INVALID_EXPECTED_COUNT");
                    count = number;
                }
                report = Journal.Verify(Journal.ReadFile(Required("--input")), expected, count);
            }
            Emit(output, new { status = report.Anchor == "HEAD_MATCHED" ? "VALID_HEAD_MATCHED" : "VALID_UNANCHORED", command, count = report.Count, head = report.Head, anchor = report.Anchor, expectedCountMatched = report.ExpectedCountMatched, outputWritten = command != "verify" });
            return 0;
        }
        catch (JournalException failure) { Emit(error, new { status = "ERROR", code = failure.Code }); return 2; }
        catch (Exception) { Emit(error, new { status = "ERROR", code = "UNEXPECTED_OR_IO_ERROR" }); return 2; }
    }
}
