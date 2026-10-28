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
        private TelemetryOutbox combat;
        private LaunchConfiguration configuration;
        private Action<string> fault;
        private WorldPublisher publisher;
        private CancellationTokenSource operation;
        private Task<bool> active;
        private bool stopped;
        public void Initialize(WorldOutbox source, TelemetryOutbox combat, LaunchConfiguration configuration, Action<string> fault)
        {
            this.source = source; this.combat = combat; this.configuration = configuration; this.fault = fault;
            StartCoroutine(Deliver());
        }
        private IEnumerator Deliver()
        {
            var codec = new UnityWorldCodec();
            while (!stopped && !source.Sealed)
            {
                Exception failure = null;
                try
                {
                    if (publisher == null) publisher = new WorldPublisher(source, codec, new WorldWebSocket(configuration.managementApiUrl, Guid.Parse(configuration.sessionId), configuration.gameServerKey));
                    operation = new CancellationTokenSource(TimeSpan.FromSeconds(10));
                    active = publisher.Deliver(combat.AcknowledgedSequence, combat.Sealed, operation.Token);
                }
                catch (Exception exception) { failure = exception; }
                if (failure == null)
                {
                    while (!active.IsCompleted && !stopped) yield return null;
                    if (stopped) yield break;
                    try { active.GetAwaiter().GetResult(); } catch (Exception exception) { failure = exception; }
                }
                operation?.Dispose(); operation = null; active = null;
                if (failure != null)
                {
                    publisher?.Dispose(); publisher = null;
                    if (!(failure is WorldConnectionInterrupted) && !(failure is OperationCanceledException))
                    { fault("WORLD RECORDING REJECTED OR DISK ERROR - RECOVER SOURCE"); yield break; }
                }
                yield return new WaitForSecondsRealtime(failure == null ? .05f : .5f);
            }
            publisher?.Dispose(); publisher = null;
        }
        public void StopAndDispose()
        {
            if (stopped) return; stopped = true;
            operation?.Cancel(); publisher?.Dispose();
            var savedSource = source; var savedOperation = operation; var savedTask = active;
            if (savedTask == null || savedTask.IsCompleted) { var observed = savedTask?.Exception; savedSource?.Dispose(); savedOperation?.Dispose(); }
            else savedTask.ContinueWith(task => { var observed = task.Exception; savedSource?.Dispose(); savedOperation?.Dispose(); }, TaskScheduler.Default);
        }
        private void OnDestroy() => StopAndDispose();
    }
}
