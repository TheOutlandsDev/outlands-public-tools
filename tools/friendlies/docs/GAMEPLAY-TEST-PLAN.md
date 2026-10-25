# Pending gameplay qualification plan

**Status: NOT RUN. No clean solo SPT 4.0.13 installation was available.**

Use a separate SPT 4.0.13 / EFT 0.16.9.40087 solo test installation with BepInEx
and BigBrain 1.4.0. Use a disposable profile and reviewed mod list. Close game
and server, preserve profile/config backups and verify their hashes before any
installation or test. Keep the backup outside the test install. Never use an
unbacked real profile or modify an updater-managed/Fika client for this plan.

1. Build the source against that SDK. Copy only the two original Friendlies DLLs
   into their new plugin folder. Confirm no game/dependency DLL came with them.
2. Start with default disabled config. Verify no squad request occurs, inspect
   F10 status, then close. Confirm the installed versions match the recorded target.
3. Enable only in the test profile/install before the next launch. First test one
   Bodyguard slot in a normal solo raid. Record placement, actual bot/profile side,
   ally relation, hostile behavior, idle following and the activation receipt.
4. Verify corners, doorways, floors and blocked paths. The bot must not teleport,
   spawn inside the player or shoot the player. An invalid sample/path should
   produce a failed slot rather than an unrelated actor being repurposed.
5. Test four slots and each formation preset. Verify actual counts remain within
   the requested plan. Presets change spacing only; verify no special equipment
   or combat behavior is incorrectly claimed.
6. Test auto USEC, BEAR and scav matching separately with disposable characters;
   then a deliberate manual-side case. These modes are not qualified together
   merely because one faction succeeded.
7. Verify combat/under-fire yields the follow layer and combat resumes normally.
   Verify the leader is not retained as an enemy. Check ordinary world groups
   are not converted into the squad. Stop if unrelated groups are affected.
8. Cancel pending slots during a delayed activation. Reject/despawn only that
   requested stale actor; keep already activated companions. Test a backend
   failure and partial result. Do not simulate this by altering a real server.
9. Test leader death, normal raid end and a second raid. Check stale callbacks,
   duplicate GameWorld start notifications and old members do not create another
   squad or attach to the new context. Check actual logs and actor counts.
10. Extract normally; close game/server. Compare profile/config evidence with the
    preserved baseline and expected normal test progress. Verify backup recovery
    separately to a new disposable location, without overwriting a real profile.
11. Only after the clean baseline passes, qualify SAIN and each other AI/spawn mod
    individually. Record exact versions and behavior differences. Fika support
    needs a future network design and real host/peer tests; do not enable it here.

Stop on friendly-fire/group pollution, profile errors, hangs or unexpected actor
changes. Close the game/server and move only the two Friendlies DLLs aside.
Retain redacted evidence privately; restore the disposable profile from its
verified backup if required. Do not upload raw profiles, private addresses,
session/account data, proprietary DLLs or unredacted logs to public issues.

Record exact versions, source commit, test count/side/map, expected/actual result,
errors and clean shutdown/extraction evidence. One visible spawn or fixture pass
does not qualify following, combat, persistence, co-op or other game versions.
