using UnityEngine;

namespace VrCommand.Unity
{
    public sealed class PhaseLabel : MonoBehaviour
    {
        private void Update()
        {
            if (VenueBootstrap.Instance != null) GetComponent<UnityEngine.UI.Text>().text = "VR COMMAND  /  " + VenueBootstrap.Instance.State.ToUpperInvariant();
        }
    }
}
