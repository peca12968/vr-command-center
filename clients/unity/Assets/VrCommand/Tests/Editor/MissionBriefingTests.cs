using System;
using System.Linq;
using NUnit.Framework;
using Unity.Collections;
using Unity.Netcode;
using UnityEngine;
using UnityEngine.UI;
using VrCommand.Simulation;

namespace VrCommand.Unity.Tests
{
    public sealed class MissionBriefingTests
    {
        [Test] public void EntireMaximumSavedChineseBriefingRoundTripsWithoutTruncation()
        {
            var text = new string('任', 10000); var header = MissionBriefingText.Pack("防線任務", text, out var parts);
            Assert.LessOrEqual(parts.Length, 80); Assert.IsTrue(MissionBriefingText.TryRead(header, parts, out var name, out var restored));
            Assert.AreEqual("防線任務", name); Assert.AreEqual(text, restored);
            Assert.Throws<ArgumentException>(() => MissionBriefingText.Pack("Test", text + "x", out _));
        }
        [Test] public void ChunkAndPageBoundariesNeverSplitSupplementaryCharacters()
        {
            var text = new string('A', 127) + "\U0001F680" + new string('務', 260);
            var header = MissionBriefingText.Pack("Test", text, out var parts);
            Assert.IsTrue(MissionBriefingText.TryRead(header, parts, out _, out var actual)); Assert.AreEqual(text, actual);
            foreach (var part in parts) Assert.IsFalse(char.IsHighSurrogate(part.ToString().Last()));
            foreach (var page in MissionBriefingText.Pages(text)) Assert.IsFalse(char.IsHighSurrogate(page.Last()));
        }
        [Test] public void PartialCorruptOrFutureMetadataCannotBecomeAReadableBriefing()
        {
            var header = MissionBriefingText.Pack("Mission", new string('中', 600), out var parts);
            Assert.IsFalse(MissionBriefingText.TryRead(header, parts.Take(parts.Length - 1).ToArray(), out _, out _));
            parts[0] = "changed"; Assert.IsFalse(MissionBriefingText.TryRead(header, parts, out _, out _));
            header.version = 2; Assert.IsFalse(MissionBriefingText.TryRead(header, parts, out _, out _));
            Assert.AreNotEqual(MissionBriefingText.Digest("a\0b", "c"), MissionBriefingText.Digest("a", "b\0c"));
        }
        [Test] public void BriefingHeaderSurvivesRealNgoSerialization()
        {
            var expected = MissionBriefingText.Pack("測試", "Content", out _);
            using (var writer = new FastBufferWriter(2048, Allocator.Temp))
            {
                writer.WriteValueSafe(expected);
                using (var reader = new FastBufferReader(writer.ToArray(), Allocator.Temp))
                { reader.ReadValueSafe(out BriefingHeader actual); Assert.IsTrue(expected.Equals(actual)); }
            }
        }
        [Test] public void PagesRetainLiteralMarkupAndBoundLinesForLongContent()
        {
            var text = "<b>任務原文</b>\n" + new string('防', 10000);
            var pages = MissionBriefingText.Pages(text); Assert.Greater(pages.Length, 40);
            Assert.AreEqual(text.Replace("\n", ""), string.Concat(pages).Replace("\n", ""));
            foreach (var page in pages) { Assert.LessOrEqual(page.Split('\n').Length, 11); foreach (var line in page.Split('\n')) Assert.LessOrEqual(line.Length, 20); }
        }
        [Test] public void DuplicateSnapshotPreservesPageButChangedMissionResetsIt()
        {
            var header = MissionBriefingText.Pack("Alpha", new string('A', 500), out var parts);
            using (var panel = new MissionBriefingPanel())
            {
                panel.Set(header, parts); panel.Next(); panel.Next(); Assert.IsTrue(panel.Open); Assert.AreEqual(1, panel.Page);
                panel.Set(header, parts); Assert.AreEqual(1, panel.Page);
                panel.Set(MissionBriefingText.Pack("Bravo", "New", out var next), next); Assert.IsFalse(panel.Open);
                panel.Next(); Assert.AreEqual(0, panel.Page);
            }
        }
        [Test] public void ClosingWhileFireIsHeldRequiresARealReleaseBeforeFiring()
        {
            var gate = new BriefingInputGate(); Assert.IsTrue(gate.Allows(false, false));
            gate.Changed(); Assert.IsFalse(gate.Allows(true, true, true)); Assert.IsFalse(gate.Allows(false, true)); Assert.AreEqual(1, gate.SuppressedPresses);
            Assert.IsTrue(gate.Allows(false, false)); Assert.IsTrue(gate.Allows(false, true));
        }
        [Test] public void TrackedPanelDoesNotMoveTrackedHeadAndRendersUserTextLiterally()
        {
            var head = new GameObject("Tracked test head"); head.transform.position = new Vector3(2, 1.7f, 3); head.transform.rotation = Quaternion.Euler(0, 65, 0);
            try
            {
                using (var panel = new MissionBriefingPanel())
                {
                    panel.Set(MissionBriefingText.Pack("<b>測試</b>", "Original", out var parts), parts); panel.CreateTracked(head.transform); panel.Next();
                    Assert.AreEqual(new Vector3(2, 1.7f, 3), head.transform.position); Assert.Less(Quaternion.Angle(Quaternion.Euler(0, 65, 0), head.transform.rotation), .001);
                    foreach (var label in head.GetComponentsInChildren<Text>(true)) Assert.IsFalse(label.supportRichText);
                }
            }
            finally { UnityEngine.Object.DestroyImmediate(head); }
        }
        [Test] public void BundledFontContainsCommonTraditionalChineseAndItsLicense()
        {
            var font = MissionBriefingPanel.Font; Assert.IsNotNull(font);
            font.RequestCharactersInTexture("任務防線救援", 24, FontStyle.Normal);
            foreach (var value in "任務防線救援") Assert.IsTrue(font.HasCharacter(value));
            Assert.IsTrue(Resources.Load<TextAsset>("VrCommand/Fonts/OFL").text.Contains("SIL OPEN FONT LICENSE"));
        }
        [Test] public void RealUnityJsonReadsSavedMissionNameAndBriefingFields()
        {
            var definition = JsonUtility.FromJson<ManagedDefinition>("{\"name\":\"防線\",\"briefing\":\"第一頁\\n第二頁\",\"durationSeconds\":60,\"props\":[]}");
            var header = MissionBriefingText.Pack(definition.name, definition.briefing, out var parts);
            Assert.IsTrue(MissionBriefingText.TryRead(header, parts, out var name, out var text)); Assert.AreEqual("防線", name); Assert.AreEqual("第一頁\n第二頁", text);
        }
    }
}
