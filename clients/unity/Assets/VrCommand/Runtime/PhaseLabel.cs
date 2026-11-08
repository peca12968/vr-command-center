using UnityEngine;

namespace VrCommand.Unity
{
    public sealed class PhaseLabel : MonoBehaviour
    {
        public NetworkAvatar avatar;
        private void Update()
        {
            if (VenueBootstrap.Instance == null) return;
            var message = "VR COMMAND  /  " + VenueBootstrap.Instance.State.ToUpperInvariant();
            var clock = VenueBootstrap.Instance.sceneAuthority;
            if (clock != null && clock.IsSpawned && clock.Clock.Value.Valid)
                message += "\n" + clock.Clock.Value.Label(clock.Presentation.Value.tick);
            var combat = CombatAuthority.Instance;
            if (avatar != null && combat != null && combat.Player(avatar.PlayerId.Value.ToString(), out var player))
            {
                var status = TacticalHudRules.Status(VenueBootstrap.Instance.State, player.health, combat.Ready.Value,
                    avatar.PoseAccepted.Value, player.connected, avatar.TrackingReady, true);
                var armed = status == "ACTIVE" && !avatar.TrackedWeaponReleasePending;
                message += " / ROOM " + player.room.ToString("00") + "\nVITALS " + player.health + "  /  AMMO " + player.magazine.ToString("00") + " / " + player.reserve.ToString("000");
                message += "\n" + (armed ? "XR INPUT / TRIGGER FIRE / A RELOAD"
                    : status == "ACTIVE" ? "RELEASE TRIGGER AND RELOAD TO ARM" : status);
                GetComponent<UnityEngine.UI.Text>().color = armed ? new Color(.72f, .88f, .53f) : new Color(1, .6f, .3f);
            }
            if (avatar != null && !string.IsNullOrEmpty(avatar.AlignmentHint))
            {
                message = avatar.AlignmentHint;
                GetComponent<UnityEngine.UI.Text>().color = new Color(1, .6f, .3f);
            }
            GetComponent<UnityEngine.UI.Text>().text = message;
        }
    }
}
