// Original synthetic core fixtures. Does not reference, load or run game libraries.
using Outlands.Friendlies.Core;
using System.Text.Json;

var tests = new List<(string Name, Action Run)>();
void Test(string name, Action run) => tests.Add((name, run));
void Check(bool value) { if (!value) throw new InvalidOperationException("Assertion failed"); }
void Bad(Action run) { try { run(); } catch (ArgumentException) { return; } throw new InvalidOperationException("Expected input refusal"); }
Settings Settings(int size = 2) => new Settings { Enabled = true, SquadSize = size };
RuntimeInfo Runtime() => new RuntimeInfo { SptVersion = "4.0.13", EftVersion = "0.16.9.40087", BigBrainLoaded = true };
(RaidSession Session, int Token) Start(int size = 2) { var s = new RaidSession(); int token = s.Begin("fictional-raid", SquadPlan.Create(Settings(size), Side.Usec), ""); return (s, token); }
SlotPlan Slot(SquadRole role, int index = 0) { var s = Settings(4); s.Roles[index] = role; return SquadPlan.Create(s, Side.Usec).Slots[index]; }

if (args.Contains("--demo"))
{
    var settings = Settings(); var runtime = Runtime(); var plan = SquadPlan.Create(settings, Side.Usec);
    Console.WriteLine(JsonSerializer.Serialize(new { simulated = true, gameplayVerified = false, qualifiedRuntime = false,
        description = "Fictional plan only; no game, server, user profile or binary was opened.",
        slots = plan.Slots.Select(s => new { slot = s.Index + 1, role = s.Role.ToString(), faction = s.Faction.ToString(), behindMetres = Formation.FollowOffset(s).Behind }),
        liveGateExample = runtime.BlockReason(false) }, new JsonSerializerOptions { WriteIndented = true }));
    return 0;
}
Test("Disabled by default", () => Check(!new Settings().Enabled));
Test("Valid four-slot plan", () => Check(SquadPlan.Create(Settings(4), Side.Usec).Slots.Count == 4));
Test("Zero squad refused", () => Bad(() => SquadPlan.Create(Settings(0), Side.Usec)));
Test("Oversized squad refused", () => Bad(() => SquadPlan.Create(Settings(5), Side.Usec)));
Test("Negative squad refused", () => Bad(() => SquadPlan.Create(Settings(-1), Side.Usec)));
Test("Missing role array refused", () => { var s = Settings(); s.Roles = null!; Bad(() => s.Validate()); });
Test("Too few roles refused", () => { var s = Settings(); s.Roles = new[] { SquadRole.Bodyguard }; Bad(() => s.Validate()); });
Test("Unknown role refused", () => { var s = Settings(); s.Roles[2] = (SquadRole)99; Bad(() => s.Validate()); });
Test("Unknown manual faction refused", () => { var s = Settings(); s.ManualFaction = (Side)99; Bad(() => s.Validate()); });
Test("NaN spawn distance refused", () => { var s = Settings(); s.SpawnDistance = float.NaN; Bad(() => s.Validate()); });
Test("Infinite spawn distance refused", () => { var s = Settings(); s.SpawnDistance = float.PositiveInfinity; Bad(() => s.Validate()); });
Test("Too close spawn distance refused", () => { var s = Settings(); s.SpawnDistance = 4; Bad(() => s.Validate()); });
Test("Too far spawn distance refused", () => { var s = Settings(); s.SpawnDistance = 21; Bad(() => s.Validate()); });
Test("Timeout below bound refused", () => { var s = Settings(); s.ActivationTimeoutSeconds = 9; Bad(() => s.Validate()); });
Test("Timeout above bound refused", () => { var s = Settings(); s.ActivationTimeoutSeconds = 121; Bad(() => s.Validate()); });
Test("Auto USEC faction", () => Check(SquadPlan.Create(Settings(), Side.Usec).Slots.All(s => s.Faction == Side.Usec)));
Test("Auto BEAR faction", () => Check(SquadPlan.Create(Settings(), Side.Bear).Slots.All(s => s.Faction == Side.Bear)));
Test("Auto scav faction", () => Check(SquadPlan.Create(Settings(), Side.Savage).Slots.All(s => s.Faction == Side.Savage)));
Test("Explicit manual faction", () => { var s = Settings(); s.AutoFaction = false; s.ManualFaction = Side.Bear; Check(SquadPlan.Create(s, Side.Usec).Slots.All(x => x.Faction == Side.Bear)); });
Test("Unknown player side refused", () => Bad(() => SquadPlan.Create(Settings(), (Side)99)));
Test("Plan keeps original frozen roles", () => { var s = Settings(); var plan = SquadPlan.Create(s, Side.Usec); s.Roles[0] = SquadRole.Sniper; s.SquadSize = 4; Check(plan.Slots.Count == 2 && plan.Slots[0].Role == SquadRole.Bodyguard); });
Test("Bodyguard close formation", () => Check(Formation.FollowOffset(Slot(SquadRole.Bodyguard)).Behind == 4));
Test("Enforcer middle formation", () => Check(Formation.FollowOffset(Slot(SquadRole.Enforcer)).Behind == 7));
Test("Sniper far formation", () => Check(Formation.FollowOffset(Slot(SquadRole.Sniper)).Behind == 12));
Test("Distinct four-slot spawn offsets", () => { var p = SquadPlan.Create(Settings(4), Side.Usec); Check(p.Slots.Select(Formation.SpawnOffset).Select(o => (o.Right, o.Behind)).Distinct().Count() == 4); });
Test("Disabled runtime blocks", () => Check(Runtime().BlockReason(false).Length > 0));
Test("Pinned runtime passes metadata gate only", () => Check(Runtime().BlockReason(true) == ""));
Test("Fika blocks solo operation", () => { var r = Runtime(); r.FikaLoaded = true; Check(r.BlockReason(true).Contains("Fika")); });
Test("Unknown SPT blocks", () => { var r = Runtime(); r.SptVersion = ""; Check(r.BlockReason(true).Length > 0); });
Test("Different EFT blocks", () => { var r = Runtime(); r.EftVersion = "0.0.0"; Check(r.BlockReason(true).Length > 0); });
Test("Missing BigBrain blocks", () => { var r = Runtime(); r.BigBrainLoaded = false; Check(r.BlockReason(true).Length > 0); });
Test("Blocked session makes no slot request", () => { var s = new RaidSession(); int g = s.Begin("fictional", SquadPlan.Create(Settings(), Side.Usec), "Fika detected"); Check(!s.Request(g, 0) && s.Read().State == SquadState.Blocked); });
Test("Duplicate raid start is ignored", () => { var (s, g) = Start(); Check(s.Begin("fictional-raid", SquadPlan.Create(Settings(), Side.Usec), "") == 0 && s.Read().Generation == g); });
Test("Empty raid key refused", () => { var s = new RaidSession(); Bad(() => s.Begin("", SquadPlan.Create(Settings(), Side.Usec), "")); });
Test("Unknown generation cannot request", () => { var (s, g) = Start(); Check(!s.Request(g + 1, 0)); });
Test("Slot bounds enforced", () => { var (s, g) = Start(); Check(!s.Request(g, -1) && !s.Request(g, 2)); });
Test("Duplicate slot request refused", () => { var (s, g) = Start(); Check(s.Request(g, 0) && !s.Request(g, 0)); });
Test("Activation before request is refused", () => { var (s, g) = Start(); Check(!s.Activated(g, 0, "fixture-a", true, true)); });
Test("Friendliness evidence required", () => { var (s, g) = Start(); s.Request(g, 0); Check(!s.Activated(g, 0, "fixture-a", false, true) && s.Read().Activated == 0); });
Test("Follow directive evidence required", () => { var (s, g) = Start(); s.Request(g, 0); Check(!s.Activated(g, 0, "fixture-a", true, false) && s.Read().Activated == 0); });
Test("Missing actor identity refused", () => { var (s, g) = Start(); s.Request(g, 0); Check(!s.Activated(g, 0, "", true, true)); });
Test("Duplicate actor cannot fill two slots", () => { var (s, g) = Start(); s.Request(g, 0); s.Request(g, 1); Check(s.Activated(g, 0, "fixture-a", true, true)); Check(!s.Activated(g, 1, "fixture-a", true, true) && s.Read().Activated == 1); });
Test("Full receipt set reaches Ready", () => { var (s, g) = Start(1); s.Request(g, 0); Check(s.Activated(g, 0, "fixture-a", true, true)); Check(s.Read().State == SquadState.Ready); });
Test("Partial failures remain Partial", () => { var (s, g) = Start(); s.Request(g, 0); s.Activated(g, 0, "fixture-a", true, true); s.Fail(g, 1); Check(s.Read().State == SquadState.Partial && s.Read().Activated == 1); });
Test("All failures remain Failed", () => { var (s, g) = Start(); s.Fail(g, 0); s.Fail(g, 1); Check(s.Read().State == SquadState.Failed); });
Test("Late callback after failure refused", () => { var (s, g) = Start(); s.Request(g, 0); s.Fail(g, 0); Check(!s.Activated(g, 0, "late", true, true)); });
Test("Late callback after ending refused", () => { var (s, g) = Start(); s.Request(g, 0); s.End(); Check(!s.Activated(g, 0, "late", true, true)); });
Test("Old raid callback cannot enter new raid", () => { var (s, g) = Start(); s.Request(g, 0); s.End(); int n = s.Begin("next-fixture-raid", SquadPlan.Create(Settings(), Side.Usec), ""); Check(n != g && !s.Activated(g, 0, "old", true, true) && s.Read().Activated == 0); });
Test("Snapshot cannot mutate session slots", () => { var (s, g) = Start(); s.Read().Slots[0] = SlotState.Activated; Check(s.Read().Activated == 0); });
Test("Simultaneous receipts accept one actor", () => { var (s, g) = Start(1); s.Request(g, 0); int accepted = 0; Parallel.Invoke(() => { if (s.Activated(g, 0, "a", true, true)) Interlocked.Increment(ref accepted); }, () => { if (s.Activated(g, 0, "b", true, true)) Interlocked.Increment(ref accepted); }); Check(accepted == 1 && s.Read().Activated == 1); });
Test("Group with unrelated member refused", () => { var o = new GroupOwnership(); Check(!o.Admit("own-a", new[] { "unrelated" }) && !o.Contains("own-a")); });
Test("New exclusive group accepted", () => { var o = new GroupOwnership(); Check(o.Admit("own-a", new[] { "own-a" }) && o.Contains("own-a")); });
Test("Second owned group member accepted", () => { var o = new GroupOwnership(); o.Admit("own-a", Array.Empty<string>()); Check(o.Admit("own-b", new[] { "own-a", "own-b" })); });
Test("Unrelated group member still refused after ownership", () => { var o = new GroupOwnership(); o.Admit("own-a", Array.Empty<string>()); Check(!o.Admit("own-b", new[] { "own-a", "stranger" }) && !o.Contains("own-b")); });
Test("Blank ownership ID refused", () => Check(!new GroupOwnership().Admit("", Array.Empty<string>())));
Test("Unowned bot receives no follow decision", () => Check(!Formation.ShouldFollow(false, true, true, false, false)));
Test("Dead bot receives no follow decision", () => Check(!Formation.ShouldFollow(true, false, true, false, false)));
Test("Dead leader stops following", () => Check(!Formation.ShouldFollow(true, true, false, false, false)));
Test("Combat enemy yields follow layer", () => Check(!Formation.ShouldFollow(true, true, true, true, false)));
Test("Under fire yields follow layer", () => Check(!Formation.ShouldFollow(true, true, true, false, true)));
Test("Healthy owned idle actor may follow", () => Check(Formation.ShouldFollow(true, true, true, false, false)));
bool GameLoaded() => AppDomain.CurrentDomain.GetAssemblies().Any(a => new[] { "Assembly-CSharp", "BepInEx", "0Harmony", "DrakiaXYZ-BigBrain" }.Contains(a.GetName().Name) || (a.GetName().Name ?? "").StartsWith("UnityEngine", StringComparison.Ordinal));
Test("Core tests load no game or mod-runtime assemblies", () => Check(!GameLoaded()));

int failed = 0;
foreach (var test in tests)
{
    try { test.Run(); Console.WriteLine("PASS " + test.Name); }
    catch (Exception error) { failed++; Console.Error.WriteLine("FAIL " + test.Name + ": " + error.GetType().Name); }
}
Console.WriteLine(JsonSerializer.Serialize(new { discovered = tests.Count, passed = tests.Count - failed, failed, gameAssembliesLoaded = GameLoaded(), gameplayVerified = false }));
return failed == 0 ? 0 : 1;
