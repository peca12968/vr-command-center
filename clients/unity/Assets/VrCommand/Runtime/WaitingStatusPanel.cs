using UnityEngine;

namespace VrCommand.Unity
{
    public sealed class WaitingStatusPanel : MonoBehaviour
    {
        public static void Create(Transform parent)
        {
            var panel = new GameObject("Admission Status", typeof(Canvas));
            panel.transform.SetParent(parent, false);
            panel.transform.localPosition = new Vector3(0, -0.2f, 1);
            panel.transform.localScale = Vector3.one * 0.0015f;
            panel.GetComponent<Canvas>().renderMode = RenderMode.WorldSpace;
            panel.GetComponent<RectTransform>().sizeDelta = new Vector2(750, 100);
            var label = new GameObject("Connection Status", typeof(UnityEngine.UI.Text), typeof(WaitingStatusPanel));
            label.transform.SetParent(panel.transform, false);
            var text = label.GetComponent<UnityEngine.UI.Text>();
            text.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            text.fontSize = 28;
            text.alignment = TextAnchor.MiddleCenter;
            text.color = new Color(0.6f, 1, 0.6f);
            label.GetComponent<RectTransform>().sizeDelta = new Vector2(750, 100);
        }
        private void Update()
        {
            if (VenueBootstrap.Instance != null) GetComponent<UnityEngine.UI.Text>().text = VenueBootstrap.Instance.Status;
        }
    }
}
