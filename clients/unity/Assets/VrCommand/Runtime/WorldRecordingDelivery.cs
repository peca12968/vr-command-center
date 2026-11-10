using System;
using System.Collections;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;
using VrCommand.Simulation;

namespace VrCommand.Unity
{
    public sealed class WorldRecordingDelivery : MonoBehaviour
    {
        private WorldOutbox source;
        private QueuedWorldRecorder writer;
        private TelemetryOutbox combat;
        private LaunchConfiguration configuration;
        private Action<string> fault;
        private WorldPublisher publisher;
        private CancellationTokenSource operation;
        private Task<bool> active;
        private bool stopped, writerFaultReported;
        public void Initialize(WorldOutbox source, QueuedWorldRecorder writer, TelemetryOutbox combat, LaunchConfiguration configuration, Action<string> fault)
        {
            this.source = source; this.writer = writer; this.combat = combat; this.configuration = configuration; this.fault = fault;
            StartCoroutine(Deliver());
        }
        private IEnumerator Deliver()
        {
            var codec = new UnityWorldCodec();
            while (!stopped && !source.Sealed)
            {
                Exception failure = null; var delivered = false;
                try
                {
                    if (publisher == null) publisher = new WorldPublisher(source, codec, new WorldWebSocket(configuration.managementApiUrl,
                        Guid.Parse(configuration.sessionId), configuration.gameServerKey, configuration.managementCertificateSha256));
                    operation = new CancellationTokenSource(TimeSpan.FromSeconds(10));
                    var sender = publisher; var acknowledged = combat.AcknowledgedSequence; var sealedCombat = combat.Sealed; var token = operation.Token;
                    active = Task.Run(() => sender.Deliver(acknowledged, sealedCombat, token));
                }
                catch (Exception exception) { failure = exception; }
                if (failure == null)
                {
                    while (!active.IsCompleted && !stopped) yield return null;
                    if (stopped) yield break;
                    try { delivered = active.GetAwaiter().GetResult(); } catch (Exception exception) { failure = exception; }
                }
                operation?.Dispose(); operation = null; active = null;
                if (failure != null)
                {
                    publisher?.Dispose(); publisher = null;
                    if (!(failure is WorldConnectionInterrupted) && !(failure is OperationCanceledException))
                    { fault("WORLD RECORDING REJECTED OR DISK ERROR - RECOVER SOURCE"); yield break; }
                }
                if (delivered) yield return null;
                else yield return new WaitForSecondsRealtime(failure == null ? .05f : .5f);
            }
            publisher?.Dispose(); publisher = null;
        }
        public void StopAndDispose()
        {
            if (stopped) return; stopped = true;
            writer?.Stop();
            operation?.Cancel(); publisher?.Dispose();
            var savedSource = source; var savedOperation = operation; var savedTask = active;
            var savedWriter = writer;
            Task.WhenAll((Task)savedTask ?? Task.CompletedTask, savedWriter?.Completion ?? Task.CompletedTask).ContinueWith(task =>
            { var observed = task.Exception; try { savedSource?.Dispose(); } finally { savedOperation?.Dispose(); savedWriter?.Dispose(); } }, TaskScheduler.Default);
        }
        private void Update()
        {
            if (!stopped && !writerFaultReported && writer != null && writer.Faulted)
            {
                writerFaultReported = true;
                Debug.LogError("VR_WORLD_WRITER_FAULT captured=" + writer.CapturedSequence + " durable=" + source.LastSequence
                    + " pendingFrames=" + writer.PendingFrames + " pendingBytes=" + writer.PendingBytes);
                fault("WORLD WRITER FAILED OR QUEUE FULL - RECOVER SOURCE");
            }
        }
        private void OnDestroy() => StopAndDispose();
    }
}
