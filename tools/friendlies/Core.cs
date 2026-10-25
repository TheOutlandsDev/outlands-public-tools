// Original MIT policy and lifecycle code. No Unity, EFT or dependency implementation.
using System;
using System.Collections.Generic;
using System.Linq;

namespace Outlands.Friendlies.Core
{
    public enum SquadRole { Bodyguard, Enforcer, Sniper }
    public enum Side { Usec, Bear, Savage }
    public enum SquadState { Idle, Blocked, Spawning, Ready, Partial, Failed, Ended }
    public enum SlotState { Pending, Requested, Activated, Failed }
    public sealed class Settings
    {
        public bool Enabled { get; set; }
        public int SquadSize { get; set; } = 2;
        public bool AutoFaction { get; set; } = true;
        public Side ManualFaction { get; set; } = Side.Usec;
        public float SpawnDistance { get; set; } = 8;
        public int ActivationTimeoutSeconds { get; set; } = 90;
        public SquadRole[] Roles { get; set; } = new[] { SquadRole.Bodyguard, SquadRole.Enforcer, SquadRole.Sniper, SquadRole.Bodyguard };
        public void Validate()
        {
            if (SquadSize < 1 || SquadSize > 4) throw new ArgumentException("Squad size must be 1 through 4.");
            if (!Enum.IsDefined(typeof(Side), ManualFaction)) throw new ArgumentException("Unknown manual faction.");
            if (float.IsNaN(SpawnDistance) || float.IsInfinity(SpawnDistance) || SpawnDistance < 5 || SpawnDistance > 20) throw new ArgumentException("Spawn distance must be 5 through 20 metres.");
            if (ActivationTimeoutSeconds < 10 || ActivationTimeoutSeconds > 120) throw new ArgumentException("Activation timeout must be 10 through 120 seconds.");
            if (Roles == null || Roles.Length != 4 || Roles.Any(r => !Enum.IsDefined(typeof(SquadRole), r))) throw new ArgumentException("Exactly four valid role presets are required.");
        }
    }
    public sealed class RuntimeInfo
    {
        public string SptVersion { get; set; } = "";
        public string EftVersion { get; set; } = "";
        public bool FikaLoaded { get; set; }
        public bool BigBrainLoaded { get; set; }
        public string BlockReason(bool enabled)
        {
            if (!enabled) return "Disabled: enable explicitly before starting a test raid.";
            if (FikaLoaded) return "Fika detected: this source preview is solo only.";
            if (SptVersion != "4.0.13" || EftVersion != "0.16.9.40087") return "Unqualified SPT/EFT version; spawning blocked.";
            if (!BigBrainLoaded) return "BigBrain is required for the follow layer.";
            return "";
        }
    }
    public sealed class SlotPlan
    {
        public int Index { get; }
        public SquadRole Role { get; }
        public Side Faction { get; }
        public float SpawnDistance { get; }
        public int TimeoutSeconds { get; }
        internal SlotPlan(int index, SquadRole role, Side side, float distance, int timeout)
        { Index = index; Role = role; Faction = side; SpawnDistance = distance; TimeoutSeconds = timeout; }
    }
    public sealed class SquadPlan
    {
        public IReadOnlyList<SlotPlan> Slots { get; }
        private SquadPlan(SlotPlan[] slots) { Slots = Array.AsReadOnly(slots); }
        public static SquadPlan Create(Settings settings, Side playerSide)
        {
            settings.Validate();
            if (!Enum.IsDefined(typeof(Side), playerSide)) throw new ArgumentException("Unknown player faction.");
            var side = settings.AutoFaction ? playerSide : settings.ManualFaction;
            return new SquadPlan(Enumerable.Range(0, settings.SquadSize).Select(i => new SlotPlan(i, settings.Roles[i], side, settings.SpawnDistance, settings.ActivationTimeoutSeconds)).ToArray());
        }
    }
    public readonly struct Offset
    {
        public float Right { get; }
        public float Behind { get; }
        public Offset(float right, float behind) { Right = right; Behind = behind; }
    }
    public static class Formation
    {
        public static Offset FollowOffset(SlotPlan slot)
        {
            var distance = slot.Role == SquadRole.Bodyguard ? 4f : slot.Role == SquadRole.Enforcer ? 7f : 12f;
            return new Offset((slot.Index % 2 == 0 ? -1 : 1) * (1.5f + slot.Index / 2), distance);
        }
        public static Offset SpawnOffset(SlotPlan slot) => new Offset((slot.Index % 2 == 0 ? -1 : 1) * (2f + slot.Index), slot.SpawnDistance);
        public static bool ShouldFollow(bool owned, bool botAlive, bool leaderAlive, bool hasEnemy, bool underFire)
            => owned && botAlive && leaderAlive && !hasEnemy && !underFire;
    }
    public sealed class Snapshot
    {
        public int Generation { get; internal set; }
        public SquadState State { get; internal set; }
        public string Message { get; internal set; } = "";
        public SlotState[] Slots { get; internal set; } = Array.Empty<SlotState>();
        public int Activated => Slots.Count(x => x == SlotState.Activated);
    }
    public sealed class RaidSession
    {
        private readonly object sync = new object();
        private int generation;
        private string lastRaid = "";
        private SquadState state;
        private string message = "Idle";
        private SlotState[] slots = Array.Empty<SlotState>();
        private readonly HashSet<string> actors = new HashSet<string>(StringComparer.Ordinal);
        public int Begin(string raidKey, SquadPlan plan, string blockReason)
        {
            if (string.IsNullOrWhiteSpace(raidKey) || raidKey.Length > 128) throw new ArgumentException("Invalid raid key.");
            if (plan == null) throw new ArgumentNullException(nameof(plan));
            lock (sync)
            {
                if (lastRaid == raidKey) return 0;
                generation++; lastRaid = raidKey; actors.Clear();
                slots = Enumerable.Repeat(SlotState.Pending, plan.Slots.Count).ToArray();
                state = blockReason.Length == 0 ? SquadState.Spawning : SquadState.Blocked;
                message = blockReason.Length == 0 ? "Starting requested slots; gameplay remains unverified." : blockReason;
                return generation;
            }
        }
        public bool Request(int expected, int slot)
        {
            lock (sync)
            {
                if (!Current(expected, slot) || slots[slot] != SlotState.Pending) return false;
                slots[slot] = SlotState.Requested; return true;
            }
        }
        private bool Current(int expected, int slot) => expected == generation && state == SquadState.Spawning && slot >= 0 && slot < slots.Length;
        public bool IsPending(int expected, int slot)
        { lock (sync) return Current(expected, slot) && slots[slot] == SlotState.Requested; }
        public bool Activated(int expected, int slot, string actorId, bool friendlyVerified, bool followDirectiveSet)
        {
            lock (sync)
            {
                if (!Current(expected, slot) || slots[slot] != SlotState.Requested || !friendlyVerified || !followDirectiveSet || string.IsNullOrWhiteSpace(actorId) || actorId.Length > 128 || !actors.Add(actorId)) return false;
                slots[slot] = SlotState.Activated; Complete(); return true;
            }
        }
        public bool Fail(int expected, int slot)
        {
            lock (sync)
            {
                if (!Current(expected, slot) || slots[slot] == SlotState.Activated || slots[slot] == SlotState.Failed) return false;
                slots[slot] = SlotState.Failed; Complete(); return true;
            }
        }
        private void Complete()
        {
            if (slots.Any(s => s == SlotState.Pending || s == SlotState.Requested)) return;
            var count = slots.Count(s => s == SlotState.Activated);
            state = count == slots.Length ? SquadState.Ready : count == 0 ? SquadState.Failed : SquadState.Partial;
            message = count + "/" + slots.Length + " activation receipts accepted. Following/combat/gameplay still need a raid test.";
        }
        public void End()
        { lock (sync) { generation++; state = SquadState.Ended; actors.Clear(); message = "Raid context ended; stale callbacks are rejected."; } }
        public Snapshot Read()
        { lock (sync) return new Snapshot { Generation = generation, State = state, Message = message, Slots = (SlotState[])slots.Clone() }; }
    }
    public sealed class GroupOwnership
    {
        private readonly HashSet<string> owned = new HashSet<string>(StringComparer.Ordinal);
        public bool Admit(string incomingId, IEnumerable<string> existingMembers)
        {
            if (string.IsNullOrWhiteSpace(incomingId) || incomingId.Length > 128 || existingMembers == null) return false;
            if (existingMembers.Any(id => id != incomingId && !owned.Contains(id))) return false;
            owned.Add(incomingId); return true;
        }
        public bool Contains(string id) => owned.Contains(id);
    }
}
