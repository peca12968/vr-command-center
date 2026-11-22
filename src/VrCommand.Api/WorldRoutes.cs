using System.Diagnostics;
using System.IO.Compression;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using VrCommand.Core;
using VrCommand.Simulation;

namespace VrCommand.Api;

public static class WorldRoutes
{
    internal const string OfflinePlayerPath = "/console/player-replay-offline.html";
    internal const string OfflinePlayerName = "VRCommand-Player-Replay.html";
    private static OperatorIdentity Actor(HttpContext context) => (OperatorIdentity)context.Items[typeof(OperatorIdentity)]!;
    public static void MapWorldRoutes(this WebApplication app)
    {
        app.MapGet("/api/world-recordings", (WorldRecordings store, HttpContext context) =>
            Results.Json(store.List(Actor(context), context.RequestAborted), WorldJson.Options));
        app.MapGet("/api/world-recordings/page", (int? limit, Guid? before, Guid[]? include, WorldRecordings store, HttpContext context) =>
        {
            context.Response.Headers.CacheControl = "no-store";
            return Results.Json(store.Page(Actor(context), limit ?? 30, before, include ?? [], context.RequestAborted), WorldJson.Options);
        });
        app.MapGet("/api/sessions/{id:guid}/world", (Guid id, bool? includeDebriefReceipts, int? observerRoomId, WorldRecordings store, HttpContext context) =>
        {
            var actor = Actor(context);
            context.Response.Headers.CacheControl = "no-store";
            var info = includeDebriefReceipts == true ? store.ReadWorldWithDebriefReceipts(id, actor) : store.Info(id, actor);
            if (observerRoomId is int room)
            {
                WorldRecordings.RequireObserverRoom(info, room, actor);
                if (info.DebriefReceipts is { } receipts)
                    info = info with { DebriefReceipts = receipts with { Players = receipts.Players.Where(player => player.RoomId == room).ToArray() } };
                if (info.Header.roomIds.Length > 1) info = info with { TrackedVrStart = null };
            }
            return Results.Json(WorldRecordings.ObservationInfo(info, observerRoomId), WorldJson.Options);
        });
        app.MapPost("/api/sessions/{id:guid}/debrief-receipts", async (Guid id, WorldRecordings store, HttpContext context) =>
        {
            var actor = Actor(context);
            if (actor.Role != OperatorRole.GameServer)
                throw new AccessDeniedException("Only the original game server can report debrief receipts.");
            var batch = await DeploymentJson.Read<DebriefReceiptBatch>(context.Request, 4096,
                "Provide the sealed boundaries and original admissions.", context.RequestAborted, completeFile: true);
            store.PublishDebriefReceipts(id, batch, actor);
            return Results.NoContent();
        });
        app.MapGet("/api/sessions/{id:guid}/readiness", (Guid id, WorldRecordings store, HttpContext context) => store.Readiness(id, Actor(context)));
        app.MapPost("/api/venue/tracked-readiness", async (WorldRecordings store, HttpContext context) =>
        {
            context.Response.Headers.CacheControl = "no-store";
            var actor = Actor(context);
            if (actor.Role != OperatorRole.Master) throw new AccessDeniedException("Venue tracking requires the master operator.");
            var input = await DeploymentJson.Read<VenueReadinessRequest>(context.Request, 4096,
                "Provide the five original room sessions and venue topology.", context.RequestAborted);
            return store.ReadVenueTracking(input, actor);
        });
        app.MapGet("/api/rooms/readiness", (WorldRecordings store, HttpContext context) =>
        {
            context.Response.Headers.CacheControl = "no-store";
            return store.ReadRoomsReadiness(Actor(context));
        });
        app.MapGet("/api/sessions/{id:guid}/connection-endpoint", (Guid id, WorldRecordings store, HttpContext context) => store.ConnectionEndpoint(id, Actor(context)));
        app.MapPut("/api/sessions/{id:guid}/connection-endpoint", (Guid id, ConnectionEndpointDraft draft, WorldRecordings store, HttpContext context) => store.PublishEndpoint(id, draft, Actor(context)));
        app.MapGet("/api/venue/connection-endpoints", (HttpContext context) =>
        {
            context.Response.Headers.CacheControl = "no-store";
            if (Actor(context).Role != OperatorRole.GameServer) throw new AccessDeniedException("Venue publication requires the game-server identity.");
            return new { version = 1 };
        });
        app.MapPut("/api/venue/connection-endpoints", (VenueEndpointBatch batch, WorldRecordings store, HttpContext context) =>
        {
            context.Response.Headers.CacheControl = "no-store";
            return store.PublishVenueEndpoints(batch, Actor(context));
        });
        app.MapGet("/api/sessions/{id:guid}/world/publish", Publish);
        app.MapGet("/api/sessions/{id:guid}/world/watch", Watch);
        app.MapGet("/api/sessions/{id:guid}/world/policy-frames", (Guid id, long throughFrame, long? afterFrame, bool? includeEnemyRoster, int? roomId, string? change,
            WorldRecordings store, HttpContext context) =>
        {
            var page = store.PolicyFrames(id, afterFrame ?? 0, throughFrame, includeEnemyRoster == true, roomId, change, Actor(context), context.RequestAborted);
            context.Response.Headers.CacheControl = "no-store";
            return Results.Json(page, WorldJson.Options);
        });
        app.MapGet("/api/sessions/{id:guid}/world/policy-neighbor", (Guid id, long fromFrame, long throughFrame, string direction,
            bool? includeFrom, bool? includeEnemyRoster, int? roomId, string? change, WorldRecordings store, HttpContext context) =>
        {
            var result = store.PolicyNeighbor(id, fromFrame, throughFrame, direction, includeFrom == true, includeEnemyRoster == true, roomId,
                change, Actor(context), context.RequestAborted);
            context.Response.Headers.CacheControl = "no-store";
            return Results.Json(result, WorldJson.Options);
        });
        app.MapGet("/api/sessions/{id:guid}/world/event-frames", (Guid id, long throughFrame, long? afterFrame, int? roomId,
            string? kind, Guid? playerId, int? observerRoomId, WorldRecordings store, HttpContext context) =>
        {
            var page = store.EventFrames(id, afterFrame ?? 0, throughFrame, roomId, kind, playerId, Actor(context), context.RequestAborted, observerRoomId);
            context.Response.Headers.CacheControl = "no-store";
            return Results.Json(page, WorldJson.Options);
        });
        app.MapGet("/api/sessions/{id:guid}/world/clip-statistics", (Guid id, long fromFrame, long throughFrame,
            int? roomId, Guid? playerId, WorldRecordings store, HttpContext context) =>
        {
            context.Response.Headers.CacheControl = "no-store";
            return store.ClipStatistics(id, fromFrame, throughFrame, roomId, playerId, Actor(context), context.RequestAborted);
        });
        app.MapGet("/api/sessions/{id:guid}/world/clip-statistics.csv", (Guid id, Guid streamId, long fromFrame, long throughFrame,
            int? roomId, Guid? playerId, WorldRecordings store, HttpContext context) =>
        {
            context.Response.Headers.CacheControl = "no-store";
            var report = store.ClipStatistics(id, fromFrame, throughFrame, roomId, playerId, Actor(context), context.RequestAborted);
            if (report.StreamId != streamId.ToString("D")) throw new InvalidOperationException("The recording source differs from the selected clip.");
            return Results.File(ClipStatisticsCsv.Encode(report), "text/csv; charset=utf-8", ClipStatisticsCsv.FileName(report));
        });
        app.MapGet("/api/sessions/{id:guid}/world/event-neighbor", (Guid id, long throughFrame, long fromFrame, string direction,
            int? roomId, string? kind, Guid? playerId, int? observerRoomId, WorldRecordings store, HttpContext context) =>
        {
            var neighbor = store.EventNeighbor(id, fromFrame, throughFrame, direction, roomId, kind, playerId, Actor(context), context.RequestAborted, observerRoomId);
            context.Response.Headers.CacheControl = "no-store";
            return Results.Json(neighbor, WorldJson.Options);
        });
        app.MapGet("/api/sessions/{id:guid}/world/shot-trace", (Guid id, long fromFrame, long throughFrame, Guid eventId,
            int? roomId, WorldRecordings store, HttpContext context) =>
        {
            context.Response.Headers.CacheControl = "no-store";
            return store.ShotTrace(id, fromFrame, throughFrame, eventId, roomId, Actor(context), context.RequestAborted);
        });
        app.MapGet("/api/sessions/{id:guid}/world/frames/{sequence:long}", (Guid id, long sequence, int? observerRoomId, WorldRecordings store, HttpContext context) =>
        {
            if (sequence < 1) throw new ArgumentException("Frame sequence must be positive.");
            var actor = Actor(context);
            var info = observerRoomId.HasValue ? store.Info(id, actor) : null;
            if (observerRoomId is int requestedRoom) WorldRecordings.RequireObserverRoom(info!, requestedRoom, actor);
            var frame = store.Frame(id, sequence, actor) ?? throw new KeyNotFoundException("No saved world frame with this sequence.");
            if (observerRoomId is int room)
                frame = store.ObservationFrame(id, frame, room, info!.Header.props.ToDictionary(prop => prop.id, prop => prop.roomId), actor);
            context.Response.Headers.CacheControl = "no-store";
            return Results.Json(frame, WorldJson.Options);
        });
        app.MapGet("/api/sessions/{id:guid}/world/venue-begin-running", (Guid id, long throughFrame,
            WorldRecordings store, HttpContext context) =>
        {
            var result = store.ReadWorldBeginReplay(id, throughFrame, Actor(context), context.RequestAborted);
            context.Response.Headers.CacheControl = "no-store";
            return Results.Json(result, WorldJson.Options);
        });
        app.MapGet("/api/sessions/{id:guid}/world/venue-environment/{requestId:guid}", (Guid id, Guid requestId,
            WorldRecordings store, HttpContext context) =>
        {
            context.Response.Headers.CacheControl = "no-store";
            return Results.Json(store.ReadWorldVenueEnvironment(id, requestId, Actor(context), context.RequestAborted), WorldJson.Options);
        });
        app.MapGet("/api/sessions/{id:guid}/world/venue-enemies/{requestId:guid}", (Guid id, Guid requestId, int? roomId,
            WorldRecordings store, HttpContext context) =>
        {
            context.Response.Headers.CacheControl = "no-store";
            return Results.Json(store.ReadWorldVenueEnemies(id, requestId, roomId, Actor(context), context.RequestAborted), WorldJson.Options);
        });
        app.MapGet("/api/sessions/{id:guid}/world/frame-context", (Guid id, long centerFrame, long throughFrame,
            WorldRecordings store, HttpContext context) =>
        {
            var result = store.FrameContext(id, centerFrame, throughFrame, Actor(context), context.RequestAborted);
            context.Response.Headers.CacheControl = "no-store";
            return Results.Json(result, WorldJson.Options);
        });
        app.MapGet("/api/sessions/{id:guid}/world/cameras", (Guid id, WorldRecordings store, HttpContext context) => store.Bookmarks(id, Actor(context)));
        app.MapPut("/api/sessions/{id:guid}/world/cameras/{camera:guid}", (Guid id, Guid camera, CameraBookmarkDraft draft, WorldRecordings store, HttpContext context) => store.SaveBookmark(id, camera, draft, Actor(context)));
        app.MapDelete("/api/sessions/{id:guid}/world/cameras/{camera:guid}", (Guid id, Guid camera, WorldRecordings store, HttpContext context) =>
        { store.DeleteBookmark(id, camera, Actor(context)); return Results.NoContent(); });
        app.MapGet("/api/sessions/{id:guid}/world/clips", (Guid id, WorldRecordings store, HttpContext context) =>
        {
            context.Response.Headers.CacheControl = "no-store";
            return Results.Json(store.ReplayClips(id, Actor(context)), WorldJson.Options);
        });
        app.MapPut("/api/sessions/{id:guid}/world/clips/{clip:guid}", (Guid id, Guid clip, ReplayClipDraft draft, WorldRecordings store, HttpContext context) =>
            Results.Json(store.SaveReplayClip(id, clip, draft, Actor(context)), WorldJson.Options));
        app.MapDelete("/api/sessions/{id:guid}/world/clips/{clip:guid}", (Guid id, Guid clip, WorldRecordings store, HttpContext context) =>
        { store.DeleteReplayClip(id, clip, Actor(context)); return Results.NoContent(); });
        app.MapGet("/api/sessions/{id:guid}/world/clips/{clip:guid}/player-replay.json", (Guid id, Guid clip, int? roomId, WorldRecordings store, HttpContext context) =>
        {
            context.Response.Headers.CacheControl = "no-store";
            var replay = store.ExportPlayerReplay(id, clip, roomId, Actor(context), context.RequestAborted);
            return Results.File(replay, "application/json", ReplayFileStem(clip, roomId) + ".json");
        });
        app.MapGet("/api/sessions/{id:guid}/world/clips/{clip:guid}/player-replay.zip",
            async (Guid id, Guid clip, int? roomId, WorldRecordings store, IWebHostEnvironment environment, HttpContext context) =>
            {
                context.Response.Headers.CacheControl = "no-store";
                var cancellation = context.RequestAborted;
                var parts = store.PlayerReplayParts(id, clip, roomId, Actor(context), cancellation);
                var player = environment.WebRootFileProvider.GetFileInfo(OfflinePlayerPath);
                if (!player.Exists || player.IsDirectory || player.Length is < 1 or > 2 * 1024 * 1024)
                    return Results.NotFound(new { error = "此管理包未提供離線播放器。" });

                var stem = ReplayFileStem(clip, roomId);
                using var output = new MemoryStream();
                using (var archive = new ZipArchive(output, ZipArchiveMode.Create, leaveOpen: true))
                {
                    using (var entry = FieldEvidence.Entry(archive, OfflinePlayerName).Open())
                    using (var input = player.CreateReadStream())
                        await input.CopyToAsync(entry, cancellation);
                    foreach (var part in parts)
                    {
                        using var entry = FieldEvidence.Entry(archive, stem + part.Suffix + ".json").Open();
                        await entry.WriteAsync(part.Data, cancellation);
                    }
                }
                return Results.File(output.ToArray(), "application/zip", stem + ".zip");
            });
        app.MapGet("/api/sessions/{id:guid}/world/clips/{clip:guid}/player-replay.html",
            async (Guid id, Guid clip, int? roomId, long? fromFrame, WorldRecordings store, IWebHostEnvironment environment, HttpContext context) =>
            {
                context.Response.Headers.CacheControl = "no-store";
                var cancellation = context.RequestAborted;
                var parts = store.PlayerReplayParts(id, clip, roomId, Actor(context), cancellation, fromFrame: fromFrame);
                var player = environment.WebRootFileProvider.GetFileInfo(OfflinePlayerPath);
                if (!player.Exists || player.IsDirectory || player.Length is < 1 or > 2 * 1024 * 1024)
                    return Results.NotFound(new { error = "此管理包未提供離線播放器。" });

                using var reader = new StreamReader(player.CreateReadStream(), Encoding.UTF8);
                var template = await reader.ReadToEndAsync(cancellation);
                const string marker = "<!--player-replay-data-->";
                var offset = template.IndexOf(marker, StringComparison.Ordinal);
                if (offset < 0) throw new InvalidOperationException("請更新此管理包內的離線播放器。");
                var output = new MemoryStream();
                output.Write(Encoding.UTF8.GetBytes(template[..offset]));
                long last = 0;
                foreach (var part in parts)
                {
                    // The JSON writer escapes HTML delimiters. Fail closed if its encoding ever changes.
                    if (part.Data.AsSpan().Contains((byte)'<')) throw new InvalidOperationException("回放資料無法嵌入網頁。");
                    output.Write("<script type=\"application/json\" data-player-replay-part>"u8);
                    output.Write(part.Data);
                    output.Write("</script>"u8);
                    last = part.LastFrame;
                }
                output.Write(Encoding.UTF8.GetBytes(template[(offset + marker.Length)..]));
                output.Position = 0;
                var stem = ReplayFileStem(clip, roomId);
                if (fromFrame is long first)
                {
                    stem += FormattableString.Invariant($"-frames-{first:D6}-{last:D6}");
                    context.Response.Headers["X-Replay-Last-Frame"] = last.ToString(System.Globalization.CultureInfo.InvariantCulture);
                }
                return Results.File(output, "text/html; charset=utf-8", stem + ".html");
            });
    }

    private static string ReplayFileStem(Guid clip, int? roomId) => roomId is int room
        ? FormattableString.Invariant($"vr-command-replay-{clip:D}-room-{room:00}") : $"vr-command-replay-{clip:D}";

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

    private static async Task Watch(Guid id, int? observerRoomId, WorldRecordings store, HttpContext context)
    {
        var actor = Actor(context); var info = store.Info(id, actor);
        if (observerRoomId is int requestedRoom) WorldRecordings.RequireObserverRoom(info, requestedRoom, actor);
        var propRooms = observerRoomId.HasValue ? info.Header.props.ToDictionary(prop => prop.id, prop => prop.roomId) : null;
        var mode = context.Request.Query["mode"].ToString();
        if (mode is not ("" or "live" or "replay")) throw new ArgumentException("Use live or replay observation mode.");
        var replay = mode == "replay";
        var from = context.Request.Query["fromMs"].ToString();
        long milliseconds = 0;
        if (from.Length > 0 && (!long.TryParse(from, out milliseconds) || milliseconds < 0)) throw new ArgumentException("Invalid replay seek time.");
        var fromFrame = context.Request.Query["fromFrame"].ToString();
        long exact = 0;
        if (fromFrame.Length > 0)
        {
            if (!replay || from.Length > 0 || !long.TryParse(fromFrame, out exact) || exact < 1)
                throw new ArgumentException("Use a positive frame sequence by itself in replay mode.");
        }
        var speed = context.Request.Query["rate"].ToString();
        if (speed.Length > 0 && speed is not ("0.25" or "0.5" or "1" or "2" or "4")) throw new ArgumentException("Invalid replay speed.");
        var rate = speed.Length == 0 ? 1 : double.Parse(speed, System.Globalization.CultureInfo.InvariantCulture);
        var through = context.Request.Query["throughFrame"].ToString();
        var saved = through.Length > 0;
        if (saved)
        {
            var limit = info.AcceptedSequence;
            if (!replay || (through != "latest" && (!long.TryParse(through, out limit) || limit < 1)))
                throw new ArgumentException("Use latest or a positive saved frame sequence in replay mode.");
            if (limit == 0) throw new InvalidOperationException("This recording has no saved frames yet.");
            if (limit > info.AcceptedSequence) throw new KeyNotFoundException("No saved world frame with this sequence.");
            if (limit < info.AcceptedSequence)
            {
                var end = store.Frame(id, limit, actor) ?? throw new KeyNotFoundException("No saved world frame with this sequence.");
                var duration = end.Packet.elapsedMilliseconds;
                info = info with { AcceptedSequence = limit, DurationMilliseconds = duration, Complete = false,
                    CapturedAtUtc = info.CapturedAtUtc?.AddMilliseconds(duration - info.DurationMilliseconds) };
            }
        }
        if (exact > info.AcceptedSequence) throw new KeyNotFoundException("No saved world frame with this sequence in the requested replay.");
        long sequence = Math.Max(1, info.AcceptedSequence);
        if (replay)
        {
            if (exact > 0) sequence = exact;
            else sequence = saved && from.Length == 0 ? 1 : store.Seek(id, milliseconds, actor);
        }
        if (saved) sequence = Math.Min(sequence, info.AcceptedSequence);
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
            await Send("header", WorldRecordings.ObservationInfo(info, observerRoomId));
            while (!cancellation.IsCancellationRequested)
            {
                var delay = 50;
                if (!saved) info = store.Info(id, actor);
                if (!replay) sequence = Math.Max(1, info.AcceptedSequence);
                var frame = sequence <= info.AcceptedSequence && sequence != sent ? store.Frame(id, sequence, actor) : null;
                if (frame is not null)
                {
                    startMilliseconds ??= frame.Packet.elapsedMilliseconds;
                    var due = (frame.Packet.elapsedMilliseconds - startMilliseconds.Value) / rate;
                    if (!replay || due <= clock.ElapsedMilliseconds)
                    {
                        var visible = observerRoomId is int room ? store.ObservationFrame(id, frame, room, propRooms!, actor) : frame;
                        await Send("frame", visible); sent = sequence; if (replay) { sequence++; continue; }
                    }
                    else delay = (int)Math.Clamp(Math.Ceiling(due - clock.ElapsedMilliseconds), 1, 50);
                }
                if (heartbeat.ElapsedMilliseconds >= 1000)
                { await Send("status", WorldRecordings.ObservationInfo(info, observerRoomId)); heartbeat.Restart(); }
                if (replay ? (saved || info.Complete) && sequence > info.AcceptedSequence
                    : info.Complete && sent == info.AcceptedSequence)
                { await Send(saved ? "saved-end" : "complete", WorldRecordings.ObservationInfo(info, observerRoomId)); return; }
                await Task.Delay(delay, cancellation);
            }
        }
        catch (Exception exception) when (exception is OperationCanceledException or IOException) { }
    }
}
