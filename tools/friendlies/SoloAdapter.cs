// Original MIT typed adapter for a locally supplied SPT/EFT SDK. No game code bundled.
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using EFT;
using Outlands.Friendlies.Core;
using UnityEngine;
using UnityEngine.AI;

namespace Outlands.Friendlies
{
    public sealed class Member
    {
        public BotOwner Bot = null!;
        public Player Leader = null!;
        public SlotPlan Slot = null!;
        public GameWorld World = null!;
    }
    internal sealed class SoloAdapter
    {
        internal static readonly Dictionary<BotOwner, Member> Members = new Dictionary<BotOwner, Member>();
        private readonly Plugin plugin;
        private readonly GameWorld world;
        private readonly BotSpawner spawner;
        private readonly int generation;
        private readonly CancellationTokenSource lifetime = new CancellationTokenSource();
        private readonly GroupOwnership ownership = new GroupOwnership();
        private readonly HashSet<BotOwner> madeHere = new HashSet<BotOwner>();
        private BotsGroup? group;
        private bool ended;
        internal SoloAdapter(Plugin plugin, GameWorld world, BotSpawner spawner, int generation)
        { this.plugin = plugin; this.world = world; this.spawner = spawner; this.generation = generation; }
        internal async Task Run(SquadPlan plan)
        {
            try { await RunSlots(plan); }
            catch (Exception error)
            {
                foreach (var slot in plan.Slots) plugin.Session.Fail(generation, slot.Index);
                plugin.Log("Friendlies run ended with error: " + error.GetType().Name);
            }
        }
        private async Task RunSlots(SquadPlan plan)
        {
            foreach (var slot in plan.Slots)
            {
                if (!plugin.Session.Request(generation, slot.Index)) break;
                using (var cancel = CancellationTokenSource.CreateLinkedTokenSource(lifetime.Token, spawner.GetCancelToken()))
                {
                    try
                    {
                        var operation = Spawn(slot, cancel.Token);
                        if (await Task.WhenAny(operation, Task.Delay(TimeSpan.FromSeconds(slot.TimeoutSeconds), cancel.Token)) != operation)
                        {
                            cancel.Cancel(); plugin.Session.Fail(generation, slot.Index);
                            _ = operation.ContinueWith(t => { _ = t.Exception; }, CancellationToken.None, TaskContinuationOptions.OnlyOnFaulted | TaskContinuationOptions.ExecuteSynchronously, TaskScheduler.Default);
                            plugin.Log("Friendlies slot timed out/cancelled; late activations will be rejected.");
                        }
                        else await operation;
                    }
                    catch (OperationCanceledException) { plugin.Session.Fail(generation, slot.Index); }
                    catch (Exception error) { plugin.Session.Fail(generation, slot.Index); plugin.Log("Friendlies slot failed: " + error.GetType().Name); }
                }
            }
        }
        private bool Current(SlotPlan slot) => !ended && world != null && world.MainPlayer != null && world.MainPlayer.HealthController != null && world.MainPlayer.HealthController.IsAlive && plugin.Session.IsPending(generation, slot.Index);
        private void MainThread()
        { if (Thread.CurrentThread.ManagedThreadId != plugin.UnityThread) throw new InvalidOperationException("Unity thread required"); }
        private async Task Spawn(SlotPlan slot, CancellationToken token)
        {
            MainThread(); token.ThrowIfCancellationRequested();
            if (!Current(slot)) throw new OperationCanceledException();
            var player = world.MainPlayer;
            var offset = Formation.SpawnOffset(slot);
            var wanted = player.Transform.position - player.Transform.forward * offset.Behind + player.Transform.right * offset.Right;
            if (!NavMesh.SamplePosition(wanted, out var hit, 2f, NavMesh.AllAreas)) throw new InvalidOperationException("No sampled navigation point");
            var path = new NavMeshPath();
            if (!NavMesh.CalculatePath(player.Transform.position, hit.position, NavMesh.AllAreas, path) || path.status != NavMeshPathStatus.PathComplete) throw new InvalidOperationException("No complete navigation path");
            var zone = spawner.GetClosestZone(hit.position, out _);
            if (zone == null) throw new InvalidOperationException("No bot zone");
            var corePoint = UnityEngine.Object.FindObjectsOfType<AICorePoint>().Where(p => p != null).OrderBy(p => (p.Position - hit.position).sqrMagnitude).FirstOrDefault();
            if (corePoint == null) throw new InvalidOperationException("No AI core navigation point");
            int corePointId = corePoint.Id;
            var side = slot.Faction == Side.Bear ? EPlayerSide.Bear : slot.Faction == Side.Savage ? EPlayerSide.Savage : EPlayerSide.Usec;
            var role = side == EPlayerSide.Bear ? WildSpawnType.pmcBEAR : side == EPlayerSide.Savage ? WildSpawnType.assault : WildSpawnType.pmcUSEC;
            var data = await BotCreationDataClass.Create(new BotProfileDataClass(side, role, BotDifficulty.normal, 0f), spawner.BotCreator, 1, new TokenProvider(token));
            MainThread(); token.ThrowIfCancellationRequested();
            if (!Current(slot)) { data.StopSpawn(); throw new OperationCanceledException(); }
            data.AddPosition(hit.position, corePointId);
            var expectedProfiles = new HashSet<string>(data.Profiles.Select(p => p.Id), StringComparer.Ordinal);
            if (expectedProfiles.Count != 1) throw new InvalidOperationException("Expected one generated profile");
            var received = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
            try
            {
                await spawner.BotCreator.ActivateBot(data, zone, true, (bot, botZone) => OwnGroup(bot, botZone, slot, expectedProfiles),
                    bot => plugin.MainQueue.Enqueue(() => Finish(bot, slot, token, received)), token);
                // Callback setup runs on Update, never on an arbitrary backend continuation.
                if (await Task.WhenAny(received.Task, Task.Delay(TimeSpan.FromSeconds(slot.TimeoutSeconds), token)) != received.Task)
                    throw new OperationCanceledException();
                if (!await received.Task) throw new InvalidOperationException("Activation receipt rejected");
            }
            catch { data.StopSpawn(); throw; }
        }
        private BotsGroup OwnGroup(BotOwner bot, BotZone zone, SlotPlan slot, HashSet<string> expectedProfiles)
        {
            MainThread();
            if (!expectedProfiles.Contains(bot.ProfileId)) throw new InvalidOperationException("Callback is not the requested profile");
            madeHere.Add(bot);
            if (!Current(slot)) { DespawnOwned(bot); throw new OperationCanceledException(); }
            // Use the game's typed creation path, but reject a group with unrelated members
            // BEFORE changing its ally/enemy lists. Never convert existing world bots.
            var candidate = group ?? spawner.GetGroupAndSetEnemies(bot, zone);
            var existing = Enumerable.Range(0, candidate.MembersCount).Select(i => candidate.Member(i).ProfileId).ToArray();
            if (!ownership.Admit(bot.ProfileId, existing)) { DespawnOwned(bot); throw new InvalidOperationException("Group has unowned members"); }
            candidate.Lock();
            if (!Enumerable.Range(0, candidate.MembersCount).Any(i => candidate.Member(i) == bot)) candidate.AddMember(bot, false);
            candidate.RemoveEnemy(world.MainPlayer); candidate.AddAlly(world.MainPlayer);
            foreach (var other in madeHere)
                if (other != null && other != bot && other.GetPlayer != null) { candidate.RemoveEnemy(other.GetPlayer); candidate.AddAlly(other.GetPlayer); }
            group = candidate; return candidate;
        }
        private void Finish(BotOwner bot, SlotPlan slot, CancellationToken token, TaskCompletionSource<bool> receipt)
        {
            MainThread();
            try
            {
                if (!madeHere.Contains(bot)) { receipt.TrySetResult(false); return; }
                if (token.IsCancellationRequested || !Current(slot)) { DespawnOwned(bot); receipt.TrySetResult(false); return; }
                var player = world.MainPlayer;
                if (bot == null || bot.IsDead || bot.BotsGroup != group || group == null) throw new InvalidOperationException("Unexpected activation owner/group");
                group.RemoveEnemy(player); group.AddAlly(player); bot.Memory.DeleteInfoAboutEnemy(player);
                bot.PlayerFollowData.SetToFollow(player);
                var friendly = group.IsAlly(player) && !group.IsEnemy(player);
                var directive = bot.PlayerFollowData.HaveToFollow;
                if (!plugin.Session.Activated(generation, slot.Index, bot.ProfileId, friendly, directive)) throw new InvalidOperationException("Unverified or stale receipt");
                Members[bot] = new Member { Bot = bot, Leader = player, Slot = slot, World = world };
                receipt.TrySetResult(true);
            }
            catch { plugin.Session.Fail(generation, slot.Index); DespawnOwned(bot); receipt.TrySetResult(false); }
        }
        private void DespawnOwned(BotOwner bot)
        {
            MainThread();
            if (bot == null || !madeHere.Remove(bot)) return;
            Members.Remove(bot);
            if (world != null) spawner.BotGame.BotDespawn(bot);
        }
        internal void CancelPending() { lifetime.Cancel(); plugin.Session.End(); }
        internal void EndRaid()
        {
            ended = true; lifetime.Cancel(); plugin.Session.End();
            foreach (var bot in madeHere) Members.Remove(bot);
            // Game raid cleanup owns existing actors; do not delete unrelated bots or saves.
        }
        private sealed class TokenProvider : GInterface22
        { private readonly CancellationToken token; internal TokenProvider(CancellationToken token) { this.token = token; } public CancellationToken GetCancelToken() => token; }
    }
}
