# Validation record — source preview 0.4.0

## Local checks

- The pure core fixture harness discovered and passed **62 cases** on Windows,
  with the .NET 8 target. It asserts that game/mod-runtime assemblies are absent
  from its process. The console demo is explicitly simulated.
- The complete client and core projects built against local SPT 4.0.13 / EFT
  0.16.9.40087 SDK references using .NET SDK 9.0.310: zero warnings/errors, with
  warnings treated as errors. BepInEx 5.4.23.2, HarmonyX 2.9.0 and BigBrain 1.4.0
  are the inspected local versions. No external reference DLL was copied into
  the build-output folder; only original Friendlies assemblies/PDB/deps files
  were produced privately.
- Source inventory, UTF-8/hash/path checks, project XML, local document links
  and source/privacy patterns are reviewed separately. Source gates do not
  establish gameplay correctness or detect every possible secret.

Core cases cover configuration bounds/enums, faction selection, frozen plans,
formation offsets, disabled/Fika/version/dependency gates, duplicate starts,
generation/slot bounds, required friendliness/directive evidence, duplicate actor
IDs, partial/failure states, stale/cancelled callbacks, snapshot isolation,
simultaneous receipt accounting, group ownership and combat/under-fire yielding.

These tests exercise the core implementation used by the adapter, but **do not
instantiate Unity, call the game's bot factory, run Harmony patches or execute
BigBrain navigation**. No SDK stub is presented as runtime proof. The private
client build checks reference/type/signature compatibility only.

## Public CI

The Friendlies workflow builds/runs the core fixtures and simulated demo on
Windows and Ubuntu with .NET 8, then runs the Python source gate. It deliberately
has no game SDK and does not compile the client adapter. Read the current
[Actions results](https://github.com/TheOutlandsDev/outlands-public-tools/actions)
for each run; fixture passes are not a supported-gameplay claim.

## Explicitly pending

All real gameplay is pending: clean solo startup, actual activation counts,
formation/following, spawn placement, group/ally behavior, combat handoff,
navigation failures, cancellation/late creation, leader death, extraction,
second raid and profile integrity. SAIN/other AI mods need separate testing.
Fika spawning is blocked; no co-op readiness is claimed. The owner selected
experimental source-only publication because no clean solo installation was
available. The existing managed client was not used as a playtest environment.

Follow GAMEPLAY-TEST-PLAN.md before promoting the preview to a playable release.
No binary installer or release DLL is distributed by this source publication.
