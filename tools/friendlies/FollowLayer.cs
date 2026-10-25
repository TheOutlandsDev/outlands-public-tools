// Original MIT custom layer using the separately installed BigBrain public API.
using DrakiaXYZ.BigBrain.Brains;
using EFT;
using Outlands.Friendlies.Core;
using UnityEngine;
using UnityEngine.AI;

namespace Outlands.Friendlies
{
    public sealed class FollowLayer : CustomLayer
    {
        public FollowLayer(BotOwner botOwner, int priority) : base(botOwner, priority) { }
        public override string GetName() => "Outlands Friendlies follow";
        public override bool IsActive()
        {
            if (BotOwner is null || BotOwner == null || !SoloAdapter.Members.TryGetValue(BotOwner, out var member)) return false;
            return Formation.ShouldFollow(true, !BotOwner.IsDead,
                member.World != null && member.Leader != null && member.Leader.HealthController != null && member.Leader.HealthController.IsAlive,
                BotOwner.Memory == null || BotOwner.Memory.HaveEnemy, BotOwner.Memory == null || BotOwner.Memory.IsUnderFire);
        }
        public override Action GetNextAction() => new Action(typeof(FollowLogic), "Owned squad member without combat enemy");
        public override bool IsCurrentActionEnding() => !IsActive();
    }
    public sealed class FollowLogic : CustomLogic
    {
        private float nextUpdate;
        public FollowLogic(BotOwner botOwner) : base(botOwner) { }
        public override void Update(CustomLayer.ActionData data)
        {
            if (Time.time < nextUpdate) return; nextUpdate = Time.time + 0.6f;
            if (!SoloAdapter.Members.TryGetValue(BotOwner, out var member) || member.World == null || member.Leader == null || BotOwner.IsDead || !member.Leader.HealthController.IsAlive) return;
            if (BotOwner.Memory == null || BotOwner.Memory.HaveEnemy || BotOwner.Memory.IsUnderFire) return;
            var offset = Formation.FollowOffset(member.Slot);
            var target = member.Leader.Transform.position - member.Leader.Transform.forward * offset.Behind + member.Leader.Transform.right * offset.Right;
            if ((BotOwner.Position - target).sqrMagnitude < 4f) { BotOwner.Mover.Stop(); return; }
            if (!NavMesh.SamplePosition(target, out var hit, 2f, NavMesh.AllAreas)) return;
            var path = new NavMeshPath();
            if (!NavMesh.CalculatePath(BotOwner.Position, hit.position, NavMesh.AllAreas, path) || path.status != NavMeshPathStatus.PathComplete) return;
            BotOwner.GoToPoint(hit.position, slowAtTheEnd: true, reachDist: 1f, mustHaveWay: true);
        }
        public override void Stop() { /* Leave combat/navigation ownership to the next active layer. */ }
    }
}
