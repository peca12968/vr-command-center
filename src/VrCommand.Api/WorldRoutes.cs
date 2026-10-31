using System.Diagnostics;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using VrCommand.Core;
using VrCommand.Simulation;

namespace VrCommand.Api;

public static class WorldRoutes
{
    private static OperatorIdentity Actor(HttpContext context) => (OperatorIdentity)context.Items[typeof(OperatorIdentity)]!;
    public static void MapWorldRoutes(this WebApplication app)
    {
        app.MapGet("/api/world-recordings", (WorldRecordings store, HttpContext context) => Results.Json(store.List(Actor(context)), WorldJson.Options));
        app.MapGet("/api/sessions/{id:guid}/world", (Guid id, WorldRecordings store, HttpContext context) => Results.Json(store.Info(id, Actor(context)), WorldJson.Options));
        app.MapGet("/api/sessions/{id:guid}/readiness", (Guid id, WorldRecordings store, HttpContext context) => store.Readiness(id, Actor(context)));
        app.MapGet("/api/sessions/{id:guid}/connection-endpoint", (Guid id, WorldRecordings store, HttpContext context) => store.ConnectionEndpoint(id, Actor(context)));
        app.MapPut("/api/sessions/{id:guid}/connection-endpoint", (Guid id, ConnectionEndpointDraft draft, WorldRecordings store, HttpContext context) => store.PublishEndpoint(id, draft, Actor(context)));
        app.MapGet("/api/sessions/{id:guid}/world/publish", Publish);
        app.MapGet("/api/sessions/{id:guid}/world/watch", Watch);
        app.MapGet("/api/sessions/{id:guid}/world/cameras", (Guid id, WorldRecordings store, HttpContext context) => store.Bookmarks(id, Actor(context)));
        app.MapPut("/api/sessions/{id:guid}/world/cameras/{camera:guid}", (Guid id, Guid camera, CameraBookmarkDraft draft, WorldRecordings store, HttpContext context) => store.SaveBookmark(id, camera, draft, Actor(context)));
        app.MapDelete("/api/sessions/{id:guid}/world/cameras/{camera:guid}", (Guid id, Guid camera, WorldRecordings store, HttpContext context) =>
        { store.DeleteBookmark(id, camera, Actor(context)); return Results.NoContent(); });
    }

    private static async Task Publish(Guid id, WorldRecordings store, SessionManager manager, HttpContext context)
    {
        var actor = Actor(context); AccessPolicy.ReportCombat(actor);
        var view = manager.Get(id, actor);
        if (view.CombatStream is null) throw new InvalidOperationException("Attach a combat stream before publishing a world.");
        if (view.CombatStream.Owner != actor) throw new AccessDeniedException("World publisher must own the combat stream.");
        if (!context.WebSockets.IsWebSocketRequest) { context.Response.StatusCode = 400; return; }
        using var socket = await context.WebSockets.AcceptWebSocketAsync();
        var cancellation = context.RequestAborted; var opened = false;
        try
        {
            while (socket.State == WebSocketState.Open && !cancellation.IsCancellationRequested)
            {
                var bytes = new byte[16384]; using var body = new MemoryStream(); WebSocketReceiveResult result;
                do
                {
                    result = await socket.ReceiveAsync(bytes, cancellation);
                    if (result.MessageType == WebSocketMessageType.Close)
                    { await socket.CloseOutputAsync(WebSocketCloseStatus.NormalClosure, "Closed", cancellation); return; }
                    if (result.MessageType != WebSocketMessageType.Text || body.Length + result.Count > 1024 * 1024) throw new ArgumentException("Use UTF-8 text messages up to 1 MiB.");
                    body.Write(bytes, 0, result.Count);
                } while (!result.EndOfMessage);
                using var message = JsonDocument.Parse(body.ToArray(), new JsonDocumentOptions { MaxDepth = 32 });
                if (!message.RootElement.TryGetProperty("type", out var type) || type.ValueKind != JsonValueKind.String) throw new ArgumentException("Missing publisher message type.");
                WorldRecordingInfo receipt;
                switch (type.GetString())
                {
                    case "header":
                        receipt = store.Open(id, WorldJson.Read<WorldRecordingHeader>(Payload(message)), actor); opened = true; break;
                    case "frame" when opened:
                        receipt = store.Append(id, WorldJson.Read<WorldRecordingPacket>(Payload(message)), actor); break;
                    case "seal" when opened:
                        if (!message.RootElement.TryGetProperty("finalSequence", out var final) || !final.TryGetInt64(out var sequence)) throw new ArgumentException("Missing final sequence.");
                        receipt = store.Seal(id, sequence, actor); break;
                    default: throw new ArgumentException("Send header first, then frame or seal.");
                }
                await socket.SendAsync(Encoding.UTF8.GetBytes(WorldJson.Write(new { type = "ack", info = receipt })), WebSocketMessageType.Text, true, cancellation);
            }
        }
        catch (Exception exception) when (exception is ArgumentException or InvalidOperationException or AccessDeniedException or KeyNotFoundException or JsonException or FormatException)
        {
            if (socket.State == WebSocketState.Open)
            {
                await socket.SendAsync(Encoding.UTF8.GetBytes(WorldJson.Write(new { type = "error", error = exception.Message })), WebSocketMessageType.Text, true, cancellation);
                await socket.CloseOutputAsync(WebSocketCloseStatus.PolicyViolation, "World message rejected", cancellation);
            }
        }
        catch (Exception exception) when (exception is OperationCanceledException or WebSocketException or IOException) { /* No acknowledged frame is lost on disconnect. */ }
    }

    private static string Payload(JsonDocument message) => message.RootElement.TryGetProperty("payload", out var payload)
        && payload.ValueKind == JsonValueKind.Object ? payload.GetRawText() : throw new ArgumentException("Missing publisher payload.");

    private static async Task Watch(Guid id, WorldRecordings store, HttpContext context)
    {
        var actor = Actor(context); var info = store.Info(id, actor);
        var mode = context.Request.Query["mode"].ToString();
        if (mode is not ("" or "live" or "replay")) throw new ArgumentException("Use live or replay observation mode.");
        var replay = mode == "replay";
        var from = context.Request.Query["fromMs"].ToString();
        if (from.Length > 0 && (!long.TryParse(from, out _) || long.Parse(from) < 0)) throw new ArgumentException("Invalid replay seek time.");
        var speed = context.Request.Query["rate"].ToString();
        if (speed.Length > 0 && speed is not ("0.25" or "0.5" or "1" or "2" or "4")) throw new ArgumentException("Invalid replay speed.");
        var rate = speed.Length == 0 ? 1 : double.Parse(speed, System.Globalization.CultureInfo.InvariantCulture);
        long sequence = replay ? store.Seek(id, from.Length == 0 ? 0 : long.Parse(from), actor) : Math.Max(1, info.AcceptedSequence);
        long sent = 0; var clock = Stopwatch.StartNew(); long? startMilliseconds = null;
        var heartbeat = Stopwatch.StartNew(); var cancellation = context.RequestAborted;
        context.Response.ContentType = "text/event-stream"; context.Response.Headers.CacheControl = "no-store";
        context.Response.Headers["X-Accel-Buffering"] = "no";
        async Task Send(string type, object value)
        {
            await context.Response.WriteAsync("event: " + type + "\ndata: " + WorldJson.Write(value) + "\n\n", cancellation);
            await context.Response.Body.FlushAsync(cancellation);
        }
        try
        {
            await Send("header", info);
            while (!cancellation.IsCancellationRequested)
            {
                var delay = 50;
                info = store.Info(id, actor);
                if (!replay) sequence = Math.Max(1, info.AcceptedSequence);
                var frame = sequence <= info.AcceptedSequence && sequence != sent ? store.Frame(id, sequence, actor) : null;
                if (frame is not null)
                {
                    startMilliseconds ??= frame.Packet.elapsedMilliseconds;
                    var due = (frame.Packet.elapsedMilliseconds - startMilliseconds.Value) / rate;
                    if (!replay || due <= clock.ElapsedMilliseconds)
                    {
                        await Send("frame", frame); sent = sequence; if (replay) { sequence++; continue; }
                    }
                    else delay = (int)Math.Clamp(Math.Ceiling(due - clock.ElapsedMilliseconds), 1, 50);
                }
                if (heartbeat.ElapsedMilliseconds >= 1000)
                { await Send("status", info); heartbeat.Restart(); }
                if (replay && info.Complete && sequence > info.AcceptedSequence) { await Send("complete", info); return; }
                await Task.Delay(delay, cancellation);
            }
        }
        catch (Exception exception) when (exception is OperationCanceledException or IOException) { }
    }
}
