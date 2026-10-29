using System;
using System.Collections.Generic;
using UnityEngine;
using VrCommand.Simulation;

namespace VrCommand.Unity
{
    public static class TacticalHudRules
    {
        public static string Status(string phase, int health, bool ready, bool accepted, bool connected, bool tracking, bool xr)
        {
            if (!ready) return "CONTROL LINK UNAVAILABLE";
            if (health <= 0) return "ELIMINATED";
            if (!tracking) return "TRACKING INVALID";
            if (!accepted) return "POSE REJECTED";
            if (!connected) return "POSE STREAM STALE";
            return phase == "Running" ? "ACTIVE" : phase == "Paused" ? "MISSION PAUSED" : phase == "Ended" ? "MISSION ENDED" : "AWAITING START";
        }
        public static float Bearing(Vector3 forward) => Point(forward).Finite ? Mathf.Repeat(Mathf.Atan2(forward.x, forward.z) * Mathf.Rad2Deg, 360) : 0;
        private static Vec3 Point(Vector3 value) => new Vec3(value.x, value.y, value.z);
        private static void Box(CombatActorState actor, out Vector3 center, out Vector3 half)
        {
            var height = actor.enemy ? 1.8f : actor.position.y + .15f;
            center = new Vector3(actor.position.x, height / 2, actor.position.z);
            half = new Vector3(actor.enemy ? .3f : .25f, height / 2, actor.enemy ? .3f : .25f);
        }
        // Conservative torso visibility using the SAME replicated boxes as aim
        // prediction. Labels do not reveal actors through cover or other actors.
        public static bool Visible(Vector3 eye, int room, string ownId, CombatActorState subject,
            IEnumerable<CombatActorState> actors, IEnumerable<CombatPropState> props)
        {
            if (!Point(eye).Finite || !subject.connected || subject.health <= 0 || subject.room != room || subject.id.ToString() == ownId) return false;
            Box(subject, out var center, out var half);
            var delta = center - eye; var distance = delta.magnitude;
            if (!float.IsFinite(distance) || distance < .05f || distance > 20) return false;
            var direction = delta / distance;
            var target = ArenaGeometry.RayBox(Point(eye), Point(direction), Point(center), Point(half), 0, distance);
            if (!target.HasValue) return false;
            foreach (var prop in props)
            {
                var hit = ArenaGeometry.RayBox(Point(eye), Point(direction), Point(prop.center), Point(prop.half), prop.yaw, distance);
                if (hit.HasValue && hit.Value < target.Value - .001f) return false;
            }
            foreach (var actor in actors)
            {
                if (!actor.connected || actor.health <= 0 || actor.id.Equals(subject.id) || actor.id.ToString() == ownId) continue;
                Box(actor, out center, out half);
                var hit = ArenaGeometry.RayBox(Point(eye), Point(direction), Point(center), Point(half), 0, distance);
                if (hit.HasValue && hit.Value < target.Value - .001f) return false;
            }
            return true;
        }
    }

    [Serializable] public sealed class TacticalHudSnapshot
    {
        public string phase, status, source = "Simulation";
        public int room, health, magazine, reserve;
        public float bearing;
        public bool reloading, ready, poseAccepted, connected, tracking;
        public double renderedAtSeconds;
        public float frameDeltaSeconds;
        public string[] labels;
    }

    [Serializable] public sealed class HudTransition
    { public double seconds; public TacticalHudSnapshot hud; }

    // Capture every rendered status transition, including ones shorter than the
    // probe's periodic sample. No per-frame file writes; capacity is explicit.
    public sealed class HudTransitionLog
    {
        private readonly List<HudTransition> entries = new List<HudTransition>();
        private TacticalHudSnapshot previous;
        private readonly int capacity;
        public bool Truncated { get; private set; }
        public HudTransitionLog(int capacity = 512)
        { if (capacity < 1) throw new ArgumentOutOfRangeException(nameof(capacity)); this.capacity = capacity; }
        public void Observe(double seconds, TacticalHudSnapshot hud)
        {
            if (hud == null || double.IsNaN(seconds) || double.IsInfinity(seconds) || seconds < 0) return;
            var changed = previous == null || previous.status != hud.status || previous.phase != hud.phase
                || previous.ready != hud.ready || previous.poseAccepted != hud.poseAccepted
                || previous.connected != hud.connected || previous.tracking != hud.tracking;
            previous = hud;
            if (!changed) return;
            if (entries.Count < capacity) entries.Add(new HudTransition { seconds = seconds, hud = hud });
            else Truncated = true;
        }
        public HudTransition[] Snapshot() => entries.ToArray();
    }

    // Desktop presentation only; all values come from accepted replicated state.
    public sealed class TacticalHud
    {
        private static readonly Color Panel = new Color(.035f, .055f, .045f, .94f), Green = new Color(.72f, .88f, .53f), Amber = new Color(1, .72f, .28f), Red = new Color(1, .39f, .30f);
        private readonly List<CombatActorState> candidates = new List<CombatActorState>(), visible = new List<CombatActorState>(), drawn = new List<CombatActorState>();
        private readonly List<CombatActorState> frameActors = new List<CombatActorState>();
        private readonly List<CombatPropState> frameProps = new List<CombatPropState>();
        private GUIStyle small, heading, number, center;
        private float nextLabels, damageUntil;
        private int previousHealth = -1;
        public static TacticalHudSnapshot LastDrawn { get; private set; }
        public void Reset() { visible.Clear(); candidates.Clear(); drawn.Clear(); previousHealth = -1; nextLabels = 0; LastDrawn = null; }
        private static void Fill(Rect rect, Color color)
        { var saved = GUI.color; GUI.color = color; GUI.DrawTexture(rect, Texture2D.whiteTexture); GUI.color = saved; }
        private void PanelAt(Rect rect) { Fill(rect, Panel); Fill(new Rect(rect.x, rect.y, 3, rect.height), Green); }
        public void Draw(NetworkAvatar avatar, CombatAuthority combat, CombatActorState player, Camera camera, Transform weapon, string phase)
        {
            small ??= new GUIStyle(GUI.skin.label) { fontSize = 14, normal = { textColor = new Color(.83f, .88f, .82f) } };
            heading ??= new GUIStyle(small) { fontSize = 20, fontStyle = FontStyle.Bold };
            number ??= new GUIStyle(heading) { fontSize = 42 };
            center ??= new GUIStyle(heading) { alignment = TextAnchor.MiddleCenter };
            var status = TacticalHudRules.Status(phase, player.health, combat.Ready.Value, avatar.PoseAccepted.Value, player.connected, avatar.TrackingReady, false);
            var active = status == "ACTIVE";
            if (previousHealth >= 0 && player.health < previousHealth) damageUntil = Time.unscaledTime + .35f;
            previousHealth = player.health;
            var scale = Mathf.Max(.5f, Mathf.Min(Screen.width / 1100f, Screen.height / 760f));
            var matrix = GUI.matrix; GUI.matrix = Matrix4x4.Scale(new Vector3(scale, scale, 1));
            var width = Screen.width / scale; var height = Screen.height / scale;
            PanelAt(new Rect(20, 20, 255, 83));
            GUI.Label(new Rect(34, 25, 230, 22), "VR COMMAND / TACTICAL", small);
            GUI.Label(new Rect(34, 48, 230, 29), "ROOM " + player.room.ToString("00") + " / " + phase.ToUpperInvariant(), heading);
            GUI.Label(new Rect(34, 77, 230, 22), "SIMULATION / SYNTHETIC RIG", small);
            var bearing = TacticalHudRules.Bearing(camera.transform.forward);
            var compass = width - 180;
            PanelAt(new Rect(compass - 160, 20, 320, 68));
            GUI.Label(new Rect(compass - 150, 24, 300, 24), "VENUE HDG " + (Mathf.RoundToInt(bearing) % 360).ToString("000") + "°", center);
            for (var offset = -2; offset <= 2; offset++)
            {
                var angle = Mathf.Repeat(Mathf.Round(bearing / 15) * 15 + offset * 15, 360);
                var x = compass + Mathf.DeltaAngle(bearing, angle) * 4;
                Fill(new Rect(x, 54, 1, 7), Green);
                GUI.Label(new Rect(x - 20, 61, 40, 20), angle.ToString("000"), small);
            }
            PanelAt(new Rect(20, height - 116, 250, 65));
            GUI.Label(new Rect(34, height - 112, 220, 24), "VITALS  " + player.health.ToString("000") + " / 100", heading);
            Fill(new Rect(34, height - 80, 220, 9), new Color(.17f, .22f, .18f));
            Fill(new Rect(34, height - 80, 220 * Mathf.Clamp01(player.health / 100f), 9), player.health <= 30 ? Red : Green);
            PanelAt(new Rect(width - 245, height - 137, 225, 86));
            GUI.Label(new Rect(width - 230, height - 134, 200, 20), player.reloading ? "RELOADING" : player.magazine == 0 ? "EMPTY / R TO RELOAD" : "AMMUNITION", small);
            GUI.Label(new Rect(width - 230, height - 115, 92, 54), player.magazine.ToString("00"), number);
            GUI.Label(new Rect(width - 140, height - 99, 110, 26), "/ " + player.reserve.ToString("000"), heading);
            GUI.Label(new Rect(20, height - 32, width - 40, 25), "WASD MOVE   /   RIGHT DRAG + ARROWS AIM   /   CLICK + SPACE FIRE   /   R RELOAD", small);
            drawn.Clear();
            if (!active)
            {
                PanelAt(new Rect(width / 2 - 235, height * .28f, 470, 53));
                var color = GUI.color; GUI.color = player.health <= 0 || status.Contains("REJECTED") || status.Contains("STALE") ? Red : Amber;
                GUI.Label(new Rect(width / 2 - 225, height * .28f + 10, 450, 32), status, center); GUI.color = color;
            }
            else DrawLabels(avatar, combat, player, camera, scale);
            GUI.matrix = matrix;
            if (damageUntil > Time.unscaledTime)
            {
                var color = new Color(1, .15f, .1f, .65f * Mathf.Clamp01((damageUntil - Time.unscaledTime) / .35f));
                Fill(new Rect(0, 0, Screen.width, 5), color); Fill(new Rect(0, Screen.height - 5, Screen.width, 5), color);
            }
            if (active)
            {
                var aim = camera.WorldToScreenPoint(combat.PreviewAimPoint(weapon.position + weapon.forward * AvatarPose.MuzzleOffset, weapon.forward, avatar.PlayerId.Value.ToString()));
                if (aim.z > 0)
                {
                    var x = aim.x; var y = Screen.height - aim.y;
                    Fill(new Rect(x - 10, y - 1, 6, 2), Green); Fill(new Rect(x + 4, y - 1, 6, 2), Green);
                    Fill(new Rect(x - 1, y - 10, 2, 6), Green); Fill(new Rect(x - 1, y + 4, 2, 6), Green);
                }
            }
            if (Event.current.type == EventType.Repaint && NativeWeatherProbe.Recording)
            {
                var labels = new List<string>(); foreach (var actor in drawn) labels.Add(actor.id.ToString());
                LastDrawn = new TacticalHudSnapshot { phase = phase, status = status, room = player.room, health = player.health,
                    magazine = player.magazine, reserve = player.reserve, reloading = player.reloading, bearing = bearing, labels = labels.ToArray(),
                    ready = combat.Ready.Value, poseAccepted = avatar.PoseAccepted.Value, connected = player.connected, tracking = avatar.TrackingReady,
                    renderedAtSeconds = Time.realtimeSinceStartupAsDouble, frameDeltaSeconds = Time.unscaledDeltaTime };
                NativeWeatherProbe.ObserveHud(LastDrawn);
            }
        }
        private static bool OnScreen(Camera camera, CombatActorState actor, out Vector3 point)
        {
            point = camera.WorldToViewportPoint(actor.position + Vector3.up * (actor.enemy ? 1.95f : .3f));
            return point.z > camera.nearClipPlane && point.x >= 0 && point.x <= 1 && point.y >= 0 && point.y <= 1;
        }
        private void DrawLabels(NetworkAvatar avatar, CombatAuthority combat, CombatActorState player, Camera camera, float scale)
        {
            frameActors.Clear(); frameProps.Clear();
            foreach (var actor in combat.Actors) frameActors.Add(actor);
            foreach (var prop in combat.Props) frameProps.Add(prop);
            if (Time.unscaledTime >= nextLabels)
            {
                nextLabels = Time.unscaledTime + .1f; visible.Clear(); candidates.Clear();
                foreach (var actor in frameActors) if (actor.room == player.room && actor.health > 0 && actor.connected && !actor.id.Equals(player.id)) candidates.Add(actor);
                candidates.Sort((a, b) => (a.position - camera.transform.position).sqrMagnitude.CompareTo((b.position - camera.transform.position).sqrMagnitude));
                for (var i = 0; i < candidates.Count && i < 32 && visible.Count < 8; i++)
                    if (OnScreen(camera, candidates[i], out _) && TacticalHudRules.Visible(camera.transform.position, player.room, avatar.PlayerId.Value.ToString(), candidates[i], frameActors, frameProps)) visible.Add(candidates[i]);
            }
            foreach (var cached in visible)
            {
                var actor = default(CombatActorState); var found = false;
                foreach (var current in frameActors) if (current.id.Equals(cached.id)) { actor = current; found = true; break; }
                // Refresh visibility on every rendered frame, even between the
                // bounded candidate searches. A newly occluded actor loses its tag.
                if (!found || actor.id.Length < 4 || !OnScreen(camera, actor, out var point)
                    || !TacticalHudRules.Visible(camera.transform.position, player.room, avatar.PlayerId.Value.ToString(), actor, frameActors, frameProps)) continue;
                var width = Screen.width / scale; var x = Mathf.Clamp(point.x * width - 72, 12, width - 156);
                var y = (1 - point.y) * Screen.height / scale - 34;
                Fill(new Rect(x, y, 144, 35), Panel);
                var tone = actor.enemy ? Red : Green; Fill(new Rect(x, y, 3, 35), tone);
                GUI.Label(new Rect(x + 9, y + 1, 132, 22), (actor.enemy ? "HOSTILE / " : "ALLY / ") + actor.id.ToString().Substring(0, 4).ToUpperInvariant(), small);
                Fill(new Rect(x + 9, y + 26, 124 * Mathf.Clamp01(actor.health / 100f), 3), tone);
                drawn.Add(actor);
            }
        }
    }
}
