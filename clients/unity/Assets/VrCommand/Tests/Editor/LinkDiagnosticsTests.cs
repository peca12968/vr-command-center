using NUnit.Framework;

namespace VrCommand.Unity.Tests
{
    public sealed class LinkDiagnosticsTests
    {
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
