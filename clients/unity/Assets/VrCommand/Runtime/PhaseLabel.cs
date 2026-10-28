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
            var combat = CombatAuthority.Instance;
            if (avatar != null && combat != null && combat.Player(avatar.PlayerId.Value.ToString(), out var player))
            {
                message += "\nHEALTH " + player.health + "   AMMO " + player.magazine + " / " + player.reserve + (player.reloading ? "   RELOADING" : "");
                message += !combat.Ready.Value ? "\nCONTROL LINK UNAVAILABLE - COMBAT PAUSED"
                    : !avatar.PoseAccepted.Value || !player.connected ? "\nTRACKING INVALID - RETURN TO YOUR AREA"
                    : player.health == 0 ? "\nELIMINATED" : "\nTRIGGER / LEFT CLICK: FIRE    A / R: RELOAD";
            }
            GetComponent<UnityEngine.UI.Text>().text = message;
        }
    }
}
