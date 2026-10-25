# OUTLANDS | Friendlies — experimental source preview

**Source only. Gameplay is UNVERIFIED. Disabled by default. Solo SPT target;
Fika spawning is blocked. This is not an install-ready or gameplay-qualified mod.**

Friendlies is a rewritten companion-squad prototype based on the owner's local
unfinished SPT plugin. It requests one to four bots, matches or selects their
faction, establishes guarded ally/group membership, and supplies an idle follow
formation layer. An F10 panel shows requested slots and accepted activation
receipts. Original source, tests, documentation and fictional examples are
[MIT licensed](LICENSE), as part of
[OUTLANDS Public Tools](https://github.com/TheOutlandsDev/outlands-public-tools).

The client **compiles against** locally supplied references from **SPT 4.0.13 /
EFT 0.16.9.40087**, BepInEx **5.4.23.2**, HarmonyX **2.9.0**, and BigBrain
**1.4.0**. That build has zero warnings/errors. The pure core has 62 generated
fixture tests. Compilation and those fixtures do **not** verify bot spawning,
friendliness, following, combat, extraction or save behavior in a real raid.

The owner selected experimental source publication because no clean solo test
installation was available. No mod was installed, game/server launched, existing
client modified, player profile read/copied or gameplay test claimed in this pass.
The local Fika-managed installation served as a read-only compile-reference source.

## What changed from the old draft

- Removed the invalid paste-placeholder source line and fixed project references.
- Replaced first-method-name reflection guessing with typed profile creation,
  bot activation and callback APIs verified against the local SDK's signatures.
- Applied faction and role settings to a frozen per-raid plan. Role names now
  have an explicit, limited meaning: **follow spacing**, not special gear or combat AI.
- Added generation tokens, duplicate-start rejection, bounded per-slot waits and
  late-callback rejection. A requested bot does not count as an activated bot.
- Added ownership checks before ally-list changes. A default group containing
  unrelated members is refused rather than made friendly wholesale. Only actors
  associated with the requested generated profile can be claimed for cleanup.
- Added an idle BigBrain follow layer for owned squad members; enemy/under-fire
  conditions yield control to other AI. Existing AI layers are not removed.
- Made the preview opt-in, pinned SPT/EFT metadata gates, and blocked integration
  before raid hooks/layers are installed when Fika or an unknown version is detected.

These mechanisms are implemented source, not proof of their in-game effects.
Read the [known limits and pending test plan](docs/GAMEPLAY-TEST-PLAN.md).

## Inspect and test without a game

Download/clone the collection and open a terminal in `tools/friendlies`.
Install the .NET **8 SDK** for the core tests, or use an installed .NET 9 SDK with
the .NET 8 runtime available. No third-party NuGet/test packages are required.
Python 3.12+ is needed only for the source gate.

```text
python -B source_check.py
dotnet build tests/Friendlies.Tests.csproj -c Release --artifacts-path ../../../.audit/friendlies-tests
dotnet ../../../.audit/friendlies-tests/bin/Friendlies.Tests/release/Friendlies.Tests.dll
dotnet ../../../.audit/friendlies-tests/bin/Friendlies.Tests/release/Friendlies.Tests.dll --demo
```

The final command prints a clearly marked fictional plan. It opens no game,
server, profile or SDK binary. The harness tests the actual core policy/lifecycle
implementation and checks that no game or mod-runtime assembly is loaded. CI
runs the core on Windows and Ubuntu with .NET 8. It does not compile the game
adapter or start Unity. See [validation](docs/VALIDATION.md).

## Build the client against your own local SDK

The recorded client build used the .NET **9.0.310 SDK** on Windows. The projects
target **netstandard2.1**. Your legally acquired matching installation must supply
the reference DLLs. BigBrain 1.4.0 must be installed separately in that installation.
No game, dependency or SDK library is downloaded or bundled by these projects.

From this tool's directory, using PowerShell:

```powershell
dotnet build Friendlies.Client.csproj -c Release --artifacts-path ../../../.audit/friendlies-client '-p:SptRoot=D:\Games\SPT-Solo'
```

Replace the fictional folder with the intended matching installation. Keep the
whole quoted `-p:SptRoot=...` argument together if it contains spaces. All external
references use `Private=false`; the build does not copy game/BepInEx/Harmony/
BigBrain DLLs into its outputs. Required files are:

- `BepInEx/core/BepInEx.dll` and `0Harmony.dll`.
- `BepInEx/plugins/DrakiaXYZ-BigBrain.dll`.
- `EscapeFromTarkov_Data/Managed/Assembly-CSharp.dll`, `DissonanceVoip.dll`,
  `Comfort.dll`, `Comfort.Unity.dll`, `UnityEngine.dll`, `UnityEngine.CoreModule.dll`,
  `UnityEngine.IMGUIModule.dll`, `UnityEngine.InputLegacyModule.dll`, and
  `UnityEngine.AIModule.dll`.

The Dissonance reference is needed to compile inherited game interface signatures;
Friendlies implements no voice feature. Reference presence is not a distribution
license. See [dependency records](docs/DEPENDENCIES.json) and
[third-party notices](THIRD-PARTY-NOTICES.txt).

Outputs include your two newly built assemblies:

```text
.audit/friendlies-client/bin/Friendlies.Client/release/Outlands.Friendlies.dll
.audit/friendlies-client/bin/Friendlies.Client/release/Outlands.Friendlies.Core.dll
```

Those paths are relative to the collection root. PDB/deps files may also be
generated locally. They are not included in this public source package. The
build performs no installation, server start or game launch.

## Optional future solo testing

**No clean solo installation was available for this release. Leave the preview
disabled until the [gameplay test plan](docs/GAMEPLAY-TEST-PLAN.md) can be followed.**

Use a separate matching solo SPT test installation with a disposable profile,
preserved and hash-verified profile/config backups, and a reviewed mod list.
Start with SPT plus the required loader/BigBrain; SAIN, other AI/spawn mods and
custom brains need later separate qualification. Do not alter a Fika-managed
client or bypass its updater's file-integrity policy.

When a suitable test environment is available, close the game/server before
placing only the two original build DLLs in a new
`BepInEx/plugins/Outlands.Friendlies/` folder. Do not redistribute or copy the
referenced proprietary/third-party SDK libraries along with them. Start the
test installation normally, confirm the plugin stays disabled, close it, then
review its generated `BepInEx/config/com.theoutlandsdev.friendlies.cfg`.

The public plugin/Harmony identity is `com.theoutlandsdev.friendlies`, with the
new generated config name above. If you used an earlier preview, preserve its
config and manually migrate only intended compatible settings into the new
config; no automatic migration is provided. Remove the earlier preview DLL
before a later test to avoid loading both identities.

The [example configuration](examples/solo-preview.cfg) remains disabled. Preserve
an existing configuration before changing it. Enable `EnableExperimentalSquad`
only in the disposable solo test. Do not hot-replace DLLs or enable it mid-raid.
F10 opens the status panel after loading; it is a diagnostic panel, not an editor.

## Configuration

| Section / key | Default | Meaning |
| --- | --- | --- |
| General / EnableExperimentalSquad | false | Explicit spawning opt-in before a test raid. |
| General / SquadSize | 2 | Requested slots, 1–4. |
| General / AutoFaction | true | Match USEC, BEAR or scav player side. Each side needs real testing. |
| General / ManualFaction | Usec | Usec/Bear/Savage when automatic matching is off. |
| General / SpawnDistance | 8 | Behind-player navigation sample distance, 5–20 metres. |
| General / ActivationTimeoutSeconds | 90 | Cooperative per-slot timeout, 10–120 seconds. |
| Squad / Slot1–Slot4 | Bodyguard, Enforcer, Sniper, Bodyguard | Formation presets. Only the selected number of slots are requested. |
| Hotkeys / ToggleUI | F10 | Diagnostic panel toggle. |

Bodyguard, Enforcer and Sniper use nominal idle follow distances of 4, 7 and
12 metres with lateral slot offsets. They **do not** select sniper weapons,
special loadouts, elite difficulty, boss behavior or distinct combat tactics.
All profiles use normal difficulty and faction-appropriate PMC/scav spawn types.
Equipment generation is left to the game/SPT backend. No server preset is shipped.

The adapter waits up to 30 seconds for the raid/player/bot context. It samples
NavMesh positions, requires a complete path and a bot zone, and uses the nearest
available AI core point. Failure is reported; there is no teleport fallback or
global bot-cap increase. It requests slots serially. Cooperative cancellation
cannot force every native/backend operation to stop immediately.

An accepted activation receipt requires an expected profile, exclusive owned
group, an ally/non-enemy check and a follow directive. `Ready` in the core means
all requested activation receipts were accepted; it is **not** gameplay acceptance.
The follow layer's registration, navigation, combat handoff and AI interoperability
are among the checks still requiring a real raid.

**Cancel pending slots** rejects subsequent receipts and requests cancellation.
Already activated companions remain in the raid; it is not a dismiss/delete-all
button. End-of-raid cleanup belongs to the game. Failed/stale activations can be
despawned only when tied to this adapter's generated profile. Other world bots,
game files, player inventory and saves are not directly edited by this source.

## Limits, recovery and suggestions

There is no verified Fika/SAIN/other-AI-mod compatibility, co-op synchronization,
companion persistence, voice command system, teammate loot transfer, quest credit,
extraction synchronization, healing/resurrection, dedicated loadout generation,
or full accessibility/usability acceptance. New game/library versions need new
SDK and gameplay checks. The build is not a safety or license clearance for inputs.

For a failed disposable test, close the game/server and move the two Friendlies
DLLs aside together. Retain the generated configuration/logs privately for review.
Use the verified profile backup if the test profile needs recovery; do not overwrite
a real profile. Follow the [test plan](docs/GAMEPLAY-TEST-PLAN.md) and record failures
without treating fixture passes or one successful spawn as full acceptance.

[Suggest an improvement](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=friendlies_suggestion.yml)
or [report a bug](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=friendlies_bug.yml).
Reports about source, core tests and future solo test results are welcome. Use
fictional examples and redact logs. Do not attach game/dependency DLLs, profiles,
account/session data, private server addresses or credentials. See
[contributing](CONTRIBUTING.md), [provenance](docs/PROVENANCE.md) and
[security/privacy](SECURITY.md).
