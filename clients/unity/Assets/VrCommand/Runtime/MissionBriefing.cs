using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using Unity.Collections;
using Unity.Netcode;
using UnityEngine;
using UnityEngine.UI;

namespace VrCommand.Unity
{
    public struct BriefingHeader : INetworkSerializable, IEquatable<BriefingHeader>
    {
        public int version, chunks, length;
        public FixedString512Bytes title;
        public FixedString128Bytes digest;
        public void NetworkSerialize<T>(BufferSerializer<T> serializer) where T : IReaderWriter
        { serializer.SerializeValue(ref version); serializer.SerializeValue(ref chunks); serializer.SerializeValue(ref length); serializer.SerializeValue(ref title); serializer.SerializeValue(ref digest); }
        public bool Equals(BriefingHeader other) => version == other.version && chunks == other.chunks && length == other.length && title.Equals(other.title) && digest.Equals(other.digest);
    }

    public static class MissionBriefingText
    {
        public const int MaximumLength = 10000, ChunkCharacters = 128, MaximumChunks = 80;
        public static bool Valid(string name, string text) => !string.IsNullOrWhiteSpace(name) && name.Length <= 100 && text != null && text.Length <= MaximumLength;
        private static string Unicode(string value) => Encoding.UTF8.GetString(Encoding.UTF8.GetBytes(value));
        public static string Digest(string name, string text)
        {
            using (var memory = new MemoryStream())
            using (var writer = new BinaryWriter(memory, Encoding.UTF8))
            using (var hash = SHA256.Create())
            { writer.Write(1); writer.Write(name); writer.Write(text); writer.Flush(); return BitConverter.ToString(hash.ComputeHash(memory.ToArray())).Replace("-", "").ToLowerInvariant(); }
        }
        public static BriefingHeader Pack(string name, string text, out FixedString512Bytes[] parts)
        {
            if (!Valid(name, text)) throw new ArgumentException("Invalid saved mission briefing.");
            name = Unicode(name); text = Unicode(text); var result = new List<FixedString512Bytes>();
            for (var offset = 0; offset < text.Length;)
            {
                var count = Math.Min(ChunkCharacters, text.Length - offset);
                if (offset + count < text.Length && char.IsHighSurrogate(text[offset + count - 1]) && char.IsLowSurrogate(text[offset + count])) count--;
                result.Add(new FixedString512Bytes(text.Substring(offset, count))); offset += count;
            }
            parts = result.ToArray();
            return new BriefingHeader { version = 1, chunks = parts.Length, length = text.Length, title = name, digest = Digest(name, text) };
        }
        public static bool TryRead(BriefingHeader header, IReadOnlyList<FixedString512Bytes> parts, out string name, out string text)
        {
            name = text = "";
            if (header.version != 1 || header.chunks < 0 || header.chunks > MaximumChunks || header.length < 0 || header.length > MaximumLength
                || parts == null || parts.Count != header.chunks) return false;
            var builder = new StringBuilder(header.length);
            for (var i = 0; i < parts.Count; i++) { builder.Append(parts[i].ToString()); if (builder.Length > MaximumLength) return false; }
            var title = header.title.ToString(); var body = builder.ToString();
            if (body.Length != header.length || !Valid(title, body) || header.digest.ToString() != Digest(title, body)) return false;
            name = title; text = body; return true;
        }
        // Conservative explicit lines; preserve surrogate pairs and all text. This
        // keeps ordinary TC / Latin text within the bounded desktop and XR panel.
        public static string[] Pages(string text)
        {
            text = (text ?? "").Replace("\r\n", "\n").Replace('\r', '\n').Replace('\t', ' ').Replace('\0', '\uFFFD');
            var pages = new List<string>(); var page = new StringBuilder(); var column = 0; var line = 0;
            for (var index = 0; index < text.Length; index++)
            {
                var value = text[index];
                if (value == '\n') { page.Append(value); line++; column = 0; }
                else
                {
                    if (column == 20) { page.Append('\n'); line++; column = 0; }
                    if (line == 10) { pages.Add(page.ToString()); page.Clear(); line = 0; }
                    page.Append(value);
                    if (char.IsHighSurrogate(value) && index + 1 < text.Length && char.IsLowSurrogate(text[index + 1])) page.Append(text[++index]);
                    column++;
                }
                if (line == 10) { pages.Add(page.ToString()); page.Clear(); line = 0; }
            }
            if (page.Length != 0 || pages.Count == 0) pages.Add(page.ToString());
            return pages.ToArray();
        }
    }

    public sealed class BriefingInputGate
    {
        private bool releaseRequired;
        public int SuppressedPresses { get; private set; }
        public void Changed() { releaseRequired = true; }
        public bool Allows(bool open, bool held, bool pressed = false)
        {
            if (open) releaseRequired = true; if (!open && !held) releaseRequired = false;
            var allowed = !open && !releaseRequired;
            if (!allowed && pressed && SuppressedPresses < int.MaxValue) SuppressedPresses++;
            return allowed;
        }
    }

    public sealed class MissionBriefingPanel : IDisposable
    {
        public bool Open { get; private set; }
        public int Page => page;
        public int PageCount => pages.Length;
        public readonly BriefingInputGate Weapons = new BriefingInputGate();
        private string[] pages = new[] { "" }; private int page; private bool license;
        private string name = "", content = ""; private bool valid;
        private BriefingHeader lastHeader; private IReadOnlyList<FixedString512Bytes> lastParts;
        private GameObject canvas; private Text body, footer; private GUIStyle textStyle, titleStyle;
        private static Font font;
        public static Font Font => font != null ? font : font = Resources.Load<Font>("VrCommand/Fonts/NotoSansCJKtc-Regular");
        public void Set(BriefingHeader header, IReadOnlyList<FixedString512Bytes> parts)
        {
            if (lastParts == parts && lastHeader.Equals(header)) return;
            lastHeader = header; lastParts = parts;
            valid = MissionBriefingText.TryRead(header, parts, out name, out content);
            Open = false; page = 0; license = false; Weapons.Changed(); Refresh();
        }
        public void Next()
        {
            if (!valid) return;
            Weapons.Changed();
            if (!Open) { license = false; pages = MissionBriefingText.Pages(name + "\n\n" + content); page = 0; Open = true; }
            else if (++page >= pages.Length) { page = 0; Open = false; }
            Refresh();
        }
        public void Close() { if (!Open) return; Open = false; Weapons.Changed(); Refresh(); }
        public void License()
        {
            if (!Open) return;
            Weapons.Changed(); license = !license; page = 0;
            var notice = Resources.Load<TextAsset>("VrCommand/Fonts/NOTICE"); var terms = Resources.Load<TextAsset>("VrCommand/Fonts/OFL");
            pages = MissionBriefingText.Pages(license ? (notice?.text ?? "") + "\n" + (terms?.text ?? "") : name + "\n\n" + content); Refresh();
        }
        private string Heading => license ? "FONT LICENSE / NOTO SANS CJK TC" : "MISSION BRIEFING";
        private string Counter => "PAGE " + (page + 1) + " / " + pages.Length;
        public void CreateTracked(Transform head)
        {
            canvas = new GameObject("Mission Briefing", typeof(Canvas), typeof(Image)); canvas.transform.SetParent(head, false);
            canvas.transform.localPosition = new Vector3(0, .03f, .9f); canvas.transform.localScale = Vector3.one * .001f;
            canvas.GetComponent<Canvas>().renderMode = RenderMode.WorldSpace; canvas.GetComponent<RectTransform>().sizeDelta = new Vector2(800, 620);
            canvas.GetComponent<Image>().color = new Color(.035f, .055f, .045f, .97f);
            body = Label("Text", new Vector2(0, 35), new Vector2(720, 480), 25);
            footer = Label("Controls", new Vector2(0, -262), new Vector2(760, 80), 20); Refresh();
        }
        private Text Label(string label, Vector2 position, Vector2 size, int points)
        {
            var node = new GameObject(label, typeof(Text)); node.transform.SetParent(canvas.transform, false); var text = node.GetComponent<Text>();
            text.font = Font; text.fontSize = points; text.supportRichText = false; text.color = new Color(.85f, .94f, .76f);
            text.alignment = TextAnchor.UpperLeft; text.horizontalOverflow = HorizontalWrapMode.Wrap; text.verticalOverflow = VerticalWrapMode.Truncate;
            var rect = node.GetComponent<RectTransform>(); rect.anchoredPosition = position; rect.sizeDelta = size; return text;
        }
        private void Refresh()
        {
            if (canvas == null) return; canvas.SetActive(Open);
            body.text = Heading + "\n\n" + pages[page]; footer.text = Counter + "\nX NEXT / Y CLOSE / LEFT GRIP FONT LICENSE";
        }
        public void Draw()
        {
            if (!valid) return;
            if (!Open) { GUI.Label(new Rect(20, 149, 240, 29), "MISSION BRIEFING [B]"); return; }
            textStyle ??= new GUIStyle(GUI.skin.label) { font = Font, fontSize = 24, richText = false, wordWrap = true };
            titleStyle ??= new GUIStyle(GUI.skin.label) { fontSize = 20, richText = false };
            var width = Mathf.Min(760, Screen.width - 24); var height = Mathf.Min(600, Screen.height - 24); var rect = new Rect((Screen.width - width) / 2, (Screen.height - height) / 2, width, height);
            textStyle.fontSize = Mathf.Clamp(Mathf.FloorToInt(Mathf.Min((height - 142) / 14, (width - 56) / 24)), 10, 24);
            var previousColor = GUI.color; GUI.color = new Color(.035f, .055f, .045f, 1);
            GUI.DrawTexture(rect, Texture2D.whiteTexture); GUI.color = previousColor;
            GUI.Box(rect, ""); GUI.Label(new Rect(rect.x + 24, rect.y + 18, width - 48, 30), Heading + " / " + Counter, titleStyle);
            GUI.Label(new Rect(rect.x + 28, rect.y + 68, width - 56, height - 142), pages[page], textStyle);
            var button = (width - 64) / 3;
            if (GUI.Button(new Rect(rect.x + 24, rect.yMax - 58, button, 36), "NEXT [B]")) Next();
            if (GUI.Button(new Rect(rect.x + 32 + button, rect.yMax - 58, button, 36), "CLOSE [ESC]")) Close();
            if (GUI.Button(new Rect(rect.x + 40 + button * 2, rect.yMax - 58, button, 36), "FONT LICENSE [L]")) License();
        }
        public void Dispose()
        {
            if (canvas != null) { if (Application.isPlaying) UnityEngine.Object.Destroy(canvas); else UnityEngine.Object.DestroyImmediate(canvas); }
            canvas = null; Open = false;
        }
    }
}
