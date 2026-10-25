# Fictional preset and core-only simulation

solo-preview.cfg is a commented configuration example with spawning disabled.
It contains no profile IDs, addresses, secrets or real game settings export.
The original draft's Sniper/Enforcer/Bodyguard names now explicitly mean far,
middle and close follow spacing. No elite loadout or special combat AI is implied.

Build the core fixture harness using README's commands, then pass `--demo`.
Expected JSON includes `simulated: true`, `gameplayVerified: false`, two slots
with Usec faction, Bodyguard/Enforcer presets and nominal 4/7 metre spacing.
The disabled gate example blocks spawning. No game/backend/SDK file is accessed.

The harness's ordinary run exercises 62 core fixtures and exits nonzero on failure.
Neither the demo nor a successful fixture run qualifies an actual companion raid.
Follow ../docs/GAMEPLAY-TEST-PLAN.md when a clean solo installation is available.
