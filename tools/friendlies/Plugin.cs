// Original MIT integration code. External runtimes/game libraries are not included.
using System;
using System.Collections.Concurrent;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading;
using BepInEx;
using BepInEx.Bootstrap;
using BepInEx.Configuration;
using Comfort.Common;
using DrakiaXYZ.BigBrain.Brains;
using EFT;
using HarmonyLib;
using Outlands.Friendlies.Core;
using UnityEngine;

namespace Outlands.Friendlies
{
    [BepInPlugin("com.theoutlandsdev.friendlies", "Outlands Friendlies (source preview)", "0.4.0")]
    [BepInProcess("EscapeFromTarkov.exe")]
    [BepInDependency("xyz.drakia.bigbrain", BepInDependency.DependencyFlags.HardDependency)]
    [BepInDependency("me.sol.sain", BepInDependency.DependencyFlags.SoftDependency)]
    public sealed class Plugin : BaseUnityPlugin
    {
        internal static Plugin? Instance;
        internal readonly ConcurrentQueue<Action> MainQueue = new ConcurrentQueue<Action>();
        internal int UnityThread;
        internal readonly RaidSession Session = new RaidSession();
        private Harmony? harmony;
        private GameWorld? world;
        private SoloAdapter? adapter;
        private Coroutine? waiting;
        private bool panel;
        private string integrationBlock = "";
        private Rect rect = new Rect(30, 30, 620, 440);
        private ConfigEntry<bool> settingEnabled = null!, auto = null!;
        private ConfigEntry<int> size = null!, timeout = null!;
        private ConfigEntry<float> distance = null!;
        private ConfigEntry<Side> manual = null!;
        private ConfigEntry<KeyboardShortcut> key = null!;
        private ConfigEntry<SquadRole>[] roles = null!;

        private void Awake()
        {
            Instance = this; UnityThread = Thread.CurrentThread.ManagedThreadId;
            settingEnabled = Config.Bind("General", "EnableExperimentalSquad", false, "Source preview, gameplay unverified. Enable before a disposable SOLO test raid; Fika is blocked.");
            size = Config.Bind("General", "SquadSize", 2, new ConfigDescription("One to four requested companions.", new AcceptableValueRange<int>(1, 4)));
            auto = Config.Bind("General", "AutoFaction", true, "Use the current player's side.");
            manual = Config.Bind("General", "ManualFaction", Side.Usec, "Used only when AutoFaction is false.");
            distance = Config.Bind("General", "SpawnDistance", 8f, new ConfigDescription("Behind-player navigation sample distance, metres.", new AcceptableValueRange<float>(5, 20)));
            timeout = Config.Bind("General", "ActivationTimeoutSeconds", 90, new ConfigDescription("Cooperative per-slot wait; late callbacks are rejected.", new AcceptableValueRange<int>(10, 120)));
            key = Config.Bind("Hotkeys", "ToggleUI", new KeyboardShortcut(KeyCode.F10));
            roles = new[] {
                Config.Bind("Squad", "Slot1", SquadRole.Bodyguard, "Formation preset only; does not grant special gear or combat AI."),
                Config.Bind("Squad", "Slot2", SquadRole.Enforcer, "Formation preset only."),
                Config.Bind("Squad", "Slot3", SquadRole.Sniper, "Formation preset only; no sniper equipment is generated."),
                Config.Bind("Squad", "Slot4", SquadRole.Bodyguard, "Formation preset only.") };
            integrationBlock = Runtime().BlockReason(true);
            if (integrationBlock.Length != 0)
            {
                Logger.LogWarning("Friendlies integration blocked: " + integrationBlock);
                return; // No Harmony raid hook or BigBrain layer is installed in Fika/unknown versions.
            }
            var brains = new HashSet<string>(new[] { "PMC", "Pmc", "Assault", "Marksman", "ExUsec", "BossKnight", "Gifter" }, StringComparer.Ordinal);
            foreach (string name in Enum.GetNames(typeof(WildSpawnType))) brains.Add(name);
            // Read the API's declared brain labels; never remove another mod's layers.
            foreach (var layer in BrainManager.CustomLayersReadOnly.Values)
                foreach (string name in layer.CustomLayerBrains) brains.Add(name);
            BrainManager.AddCustomLayer(typeof(FollowLayer), brains.ToList(), 50, new List<WildSpawnType> { WildSpawnType.pmcUSEC, WildSpawnType.pmcBEAR, WildSpawnType.assault });
            harmony = new Harmony("com.theoutlandsdev.friendlies");
            harmony.Patch(AccessTools.Method(typeof(GameWorld), nameof(GameWorld.OnGameStarted)), postfix: new HarmonyMethod(typeof(RaidHook), nameof(RaidHook.AfterStarted)));
            Logger.LogWarning("Friendlies source preview 0.4.0: gameplay not verified; disabled by default; solo only.");
        }
        internal RuntimeInfo Runtime()
        {
            string spt = "", eft = "";
            try
            {
                var version = FileVersionInfo.GetVersionInfo(Path.Combine(BepInEx.Paths.PluginPath, "spt", "spt-core.dll"));
                spt = version.FileMajorPart + "." + version.FileMinorPart + "." + version.FileBuildPart;
                eft = FileVersionInfo.GetVersionInfo(Path.Combine(BepInEx.Paths.GameRootPath, "EscapeFromTarkov.exe")).FileVersion ?? "";
            }
            catch { /* Unknown version is a blocked gate, never an assumed match. */ }
            return new RuntimeInfo { SptVersion = spt, EftVersion = eft,
                FikaLoaded = Chainloader.PluginInfos.Keys.Any(k => k.IndexOf("fika", StringComparison.OrdinalIgnoreCase) >= 0),
                BigBrainLoaded = Chainloader.PluginInfos.ContainsKey("xyz.drakia.bigbrain") };
        }
        private Settings ReadSettings() => new Settings { Enabled = settingEnabled.Value, SquadSize = size.Value, AutoFaction = auto.Value, ManualFaction = manual.Value,
            SpawnDistance = distance.Value, ActivationTimeoutSeconds = timeout.Value, Roles = roles.Select(r => r.Value).ToArray() };
        internal void Begin(GameWorld context)
        {
            if (world == context) return;
            adapter?.EndRaid(); world = context;
            if (waiting != null) StopCoroutine(waiting);
            waiting = StartCoroutine(WaitForContext(context));
        }
        private IEnumerator WaitForContext(GameWorld context)
        {
            float started = Time.realtimeSinceStartup;
            while (context != null && world == context && Time.realtimeSinceStartup - started < 30f)
            {
                if (context.MainPlayer != null && !context.MainPlayer.IsAI && Singleton<IBotGame>.Instantiated)
                {
                    var status = Singleton<IBotGame>.Instance.Status;
                    if (status == GameStatus.Started || status == GameStatus.Running || status == GameStatus.Runned)
                    { StartReady(context); waiting = null; yield break; }
                }
                yield return null;
            }
            if (world == context) { Session.End(); Logger.LogWarning("Friendlies raid context not ready within 30 seconds."); }
            waiting = null;
        }
        private void StartReady(GameWorld context)
        {
            try
            {
                var player = context.MainPlayer;
                if (player == null || player.IsAI || !Singleton<IBotGame>.Instantiated) return;
                var settings = ReadSettings();
                var playerSide = player.Side == EPlayerSide.Usec ? Side.Usec : player.Side == EPlayerSide.Bear ? Side.Bear : player.Side == EPlayerSide.Savage ? Side.Savage : throw new InvalidOperationException("Unknown player side");
                var plan = SquadPlan.Create(settings, playerSide);
                var runtime = Runtime(); var blocked = runtime.BlockReason(settings.Enabled);
                var generation = Session.Begin(context.GetInstanceID().ToString(System.Globalization.CultureInfo.InvariantCulture), plan, blocked);
                if (generation == 0 || blocked.Length != 0) { if (blocked.Length != 0) Logger.LogWarning(blocked); return; }
                var game = Singleton<IBotGame>.Instance;
                adapter = new SoloAdapter(this, context, game.BotsController.BotSpawner, generation);
                _ = adapter.Run(plan);
            }
            catch (Exception error) { Logger.LogError("Friendlies raid setup failed: " + error.GetType().Name); Session.End(); }
        }
        private void Update()
        {
            while (MainQueue.TryDequeue(out var action))
            { try { action(); } catch (Exception error) { Logger.LogError("Friendlies callback failed: " + error.GetType().Name); } }
            if (key.Value.IsDown()) panel = !panel;
            if (adapter != null && (world == null || world.MainPlayer == null)) { adapter.EndRaid(); adapter = null; world = null; }
        }
        internal void Log(string message) => Logger.LogInfo(message);
        private void OnGUI()
        {
            if (panel) rect = GUILayout.Window(1830471, rect, Draw, "Friendlies - solo source preview");
        }
        private void Draw(int id)
        {
            var snapshot = Session.Read();
            GUILayout.Label("GAMEPLAY UNVERIFIED | SPT 4.0.13 / EFT 0.16.9.40087 | Solo only");
            GUILayout.Label("Enable before a disposable raid using BepInEx configuration.");
            GUILayout.Label("Enabled: " + settingEnabled.Value + " | Auto faction: " + auto.Value + " | Requested: " + size.Value);
            if (integrationBlock.Length != 0) GUILayout.Label(integrationBlock);
            GUILayout.Label("Role names control follow spacing, not equipment or special combat AI.");
            for (int i = 0; i < roles.Length; i++) GUILayout.Label("Slot " + (i + 1) + ": " + roles[i].Value);
            GUILayout.Space(10); GUILayout.Label("State: " + snapshot.State + " | Accepted activations: " + snapshot.Activated);
            GUILayout.Label(snapshot.Message);
            GUILayout.Label("Accepted activation means ally/directive setup passed; actual following and combat need a raid test.");
            if (GUILayout.Button("Cancel pending slots")) adapter?.CancelPending();
            if (GUILayout.Button("Close")) panel = false;
            GUI.DragWindow();
        }
        private void OnDestroy()
        {
            if (waiting != null) StopCoroutine(waiting);
            adapter?.EndRaid(); harmony?.UnpatchSelf(); Instance = null;
        }
        private static class RaidHook
        { internal static void AfterStarted(GameWorld __instance) => Instance?.Begin(__instance); }
    }
}
