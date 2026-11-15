using NUnit.Framework;

namespace VrCommand.Unity.Tests
{
    public sealed class LinkDiagnosticsTests
    {
        [Test]
        public void QuestCanMeasureAgainAfterAnAlreadyCompleteConnection()
        {
            var client = new LinkProbeConnection(repeatOnReconnect: true);
            Assert.That(client.TryBegin(1), Is.True);
            Assert.That(client.TryFinish(terminal: false), Is.True);
            Assert.That(client.TryFinish(terminal: false), Is.False);
            Assert.That(client.TryBegin(2), Is.False);
            client.Disconnect();

            Assert.That(client.TryBegin(2), Is.True);
            Assert.That(client.Id, Is.EqualTo(2UL));
            Assert.That(client.Reported, Is.False);
            Assert.That(client.TryFinish(terminal: false), Is.True);
        }

        [Test]
        public void DelayedEchoCannotSatisfyTheFirstProbeAfterReconnect()
        {
            var client = new LinkProbeConnection(repeatOnReconnect: true);
            Assert.That(client.TryBegin(3), Is.True);
            var oldRequest = client.BeginRequest();
            Assert.That(client.IsPendingReply(oldRequest), Is.True);
            Assert.That(client.TryFinish(terminal: false), Is.True);
            Assert.That(client.IsPendingReply(oldRequest), Is.False);
            client.Disconnect();
            Assert.That(client.TryBegin(4), Is.True);

            var nextRequest = client.BeginRequest();
            Assert.That(client.IsPendingReply(oldRequest), Is.False);
            Assert.That(client.IsPendingReply(nextRequest), Is.True);
            client.ClearRequest();
            Assert.That(client.IsPendingReply(nextRequest), Is.False);
        }

        [Test]
        public void QuestEndClosesRecorderEvenAfterItsWindowWasReported()
        {
            var client = new LinkProbeConnection(repeatOnReconnect: true);
            Assert.That(client.TryBegin(1), Is.True);
            Assert.That(client.TryFinish(terminal: false), Is.True);
            Assert.That(client.TryFinish(terminal: true), Is.False);
            client.Disconnect();

            Assert.That(client.Closed, Is.True);
            Assert.That(client.TryBegin(2), Is.False);
        }

        [Test]
        public void WindowsWritesAtMostOneReportEvenIfItFinishesBeforeConnecting()
        {
            var client = new LinkProbeConnection(repeatOnReconnect: false);
            Assert.That(client.TryFinish(terminal: false), Is.True);
            Assert.That(client.TryBegin(1), Is.False);
            Assert.That(client.TryFinish(terminal: true), Is.False);
        }

        [Test]
        public void EchoBudgetIsIndependentPerConnectionAndBoundedToTheVenue()
        {
            var gate = new LinkEchoRateGate();
            for (ulong connection = 1; connection <= 25; connection++)
            {
                Assert.That(gate.TryReply(connection, 0), Is.True);
                Assert.That(gate.TryReply(connection, .79), Is.False);
            }
            Assert.That(gate.TryReply(26, 1), Is.False);
            Assert.That(gate.TryReply(1, 1), Is.True);
            Assert.That(gate.TryReply(2, 1), Is.True);
            gate.Forget(1);
            Assert.That(gate.TryReply(26, 1), Is.True);
        }
    }
}
