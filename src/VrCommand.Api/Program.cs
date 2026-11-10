using System.Text.Json.Serialization;
using VrCommand.Core;
using VrCommand.Persistence;
using VrCommand.Api;

var builder = WebApplication.CreateBuilder(new WebApplicationOptions
{
    Args = args,
    WebRootPath = Path.Combine(AppContext.BaseDirectory, "wwwroot")
});
var operatorKeyFile = builder.Configuration["OperatorKeyFile"];
if (!string.IsNullOrWhiteSpace(operatorKeyFile))
    builder.Configuration.AddJsonFile(Path.GetFullPath(operatorKeyFile), optional: false, reloadOnChange: false)
        .AddEnvironmentVariables().AddCommandLine(args);
var authentication = new OperatorAuthentication(builder.Configuration);
builder.Services.ConfigureHttpJsonOptions(options =>
    options.SerializerOptions.Converters.Add(new JsonStringEnumConverter(allowIntegerValues: false)));
var dataDirectory = Path.GetFullPath(builder.Configuration["DataDirectory"]
    ?? Path.Combine(builder.Environment.ContentRootPath, "data", "missions"));
builder.Services.AddSingleton(_ => new SqliteMissionLibrary(dataDirectory));
var ticketSigner = new PlayerJoinTicketSigner(PlayerTicketKey.Load(Path.GetDirectoryName(dataDirectory)!,
    builder.Configuration["PlayerTicketSigningKey"]));
var sessionDirectory = Path.GetFullPath(builder.Configuration["SessionDataDirectory"]
    ?? Path.Combine(Path.GetDirectoryName(dataDirectory)!, "sessions"));
if (string.Equals(Path.TrimEndingDirectorySeparator(dataDirectory), Path.TrimEndingDirectorySeparator(sessionDirectory),
    OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal))
    throw new InvalidOperationException("Mission and session data directories must be separate.");
builder.Services.AddSingleton(_ => new SqliteSessionEventStore(sessionDirectory));
builder.Services.AddSingleton(services => new SessionManager(services.GetRequiredService<SqliteSessionEventStore>()));
builder.Services.AddSingleton(services => new WorldRecordings(sessionDirectory, services.GetRequiredService<SessionManager>()));
builder.Services.AddHostedService<MissionClockService>();
var app = builder.Build();
ControlPipeLifetime.Attach(app, builder.Configuration["ControlPipeToken"]);
// Fail startup on inconsistent persisted histories, before reporting a healthy service.
app.Services.GetRequiredService<SessionManager>();
app.Services.GetRequiredService<SqliteMissionLibrary>();
app.Services.GetRequiredService<WorldRecordings>();
app.UseWebSockets(new WebSocketOptions { KeepAliveInterval = TimeSpan.FromSeconds(30) });

app.Use(async (context, next) =>
{
    context.Response.Headers.XContentTypeOptions = "nosniff";
    context.Response.Headers["Referrer-Policy"] = "no-referrer";
    if (context.Request.Path.StartsWithSegments("/console"))
    {
        context.Response.Headers.ContentSecurityPolicy = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'";
        context.Response.Headers.CacheControl = "no-store";
    }
    await next(context);
});
app.UseDefaultFiles();
app.UseStaticFiles();

app.Use(async (context, next) =>
{
    if (context.Request.Path.StartsWithSegments("/api"))
    {
        var identity = authentication.Authenticate(context.Request.Headers.Authorization.ToString());
        if (identity is null)
        {
            context.Response.StatusCode = 401;
            context.Response.Headers.WWWAuthenticate = "Bearer";
            await context.Response.WriteAsJsonAsync(new { error = "Operator authentication required." });
            return;
        }
        context.Items[typeof(OperatorIdentity)] = identity;
    }
    await next(context);
});

app.Use(async (context, next) =>
{
    try { await next(context); }
    catch (Exception ex) when (ex is ArgumentException or KeyNotFoundException or InvalidOperationException or AccessDeniedException)
    {
        context.Response.StatusCode = ex switch
        {
            ArgumentException => 400,
            AccessDeniedException => 403,
            KeyNotFoundException => 404,
            _ => 409
        };
        if (ex is MissionLayoutRejectedException { RoomId: int roomId } roomLayout)
            await context.Response.WriteAsJsonAsync(new { error = ex.Message, roomId, layout = roomLayout.Report });
        else if (ex is MissionLayoutRejectedException layout)
            await context.Response.WriteAsJsonAsync(new { error = ex.Message, layout = layout.Report });
        else if (ex is EnemyCapacityExceededException capacity)
            await context.Response.WriteAsJsonAsync(new { error = ex.Message, code = "enemy-capacity-exceeded", maxCount = capacity.MaxCount });
        else if (ex is MixedRealityNotReadyException mr)
            await context.Response.WriteAsJsonAsync(new { error = ex.Message,
                code = mr.Action == ControlAction.Resume ? "mr-resume-readiness-required" : "mr-readiness-required" });
        else if (ex is MixedRealityTrackingPauseException)
            await context.Response.WriteAsJsonAsync(new { error = ex.Message, code = "mr-tracking-pause-no-witness" });
        else if (ex is VrParticipationPauseException)
            await context.Response.WriteAsJsonAsync(new { error = ex.Message, code = "vr-participation-pause-no-witness" });
        else if (ex is VrParticipationResumeException)
            await context.Response.WriteAsJsonAsync(new { error = ex.Message, code = "vr-participation-resume-not-ready" });
        else if (ex is MixedRealityAlignmentRequiredException)
            await context.Response.WriteAsJsonAsync(new { error = ex.Message, code = "mr-alignment-required" });
        else if (ex is IndependentRoomsOccupiedException occupied)
            await context.Response.WriteAsJsonAsync(new { error = ex.Message, code = "independent-rooms-occupied", roomIds = occupied.RoomIds });
        else if (ex is MrVenueBundleConflict venue)
            await context.Response.WriteAsJsonAsync(new { error = ex.Message, code = venue.Code, roomId = venue.RoomId });
        else if (ex is VrVenueTicketConflict vrVenue)
            await context.Response.WriteAsJsonAsync(new { error = ex.Message, code = vrVenue.Code, roomId = vrVenue.RoomId });
        else if (ex is VenuePhaseChangedException)
            await context.Response.WriteAsJsonAsync(new { error = ex.Message, code = "venue-phase-changed" });
        else if (ex is VenuePauseNotObservedException waiting)
            await context.Response.WriteAsJsonAsync(new { error = ex.Message, code = "venue-pause-not-observed", roomIds = waiting.RoomIds });
        else if (ex is VenueResumeNotReadyException notReady)
            await context.Response.WriteAsJsonAsync(new { error = ex.Message, code = "venue-resume-not-ready", roomIds = notReady.RoomIds });
        else if (ex is VenueBeginNotReadyException beginNotReady)
            await context.Response.WriteAsJsonAsync(new { error = ex.Message, code = "venue-begin-not-ready", roomIds = beginNotReady.RoomIds });
        else if (ex is VenueReportsNotReadyException reportsNotReady)
            await context.Response.WriteAsJsonAsync(new { error = ex.Message, code = "venue-reports-not-ready", roomIds = reportsNotReady.RoomIds });
        else if (ex is VenueFieldEvidenceNotReadyException fieldNotReady)
            await context.Response.WriteAsJsonAsync(new { error = ex.Message, code = "venue-field-evidence-not-ready", roomIds = fieldNotReady.RoomIds });
        else await context.Response.WriteAsJsonAsync(new { error = ex.Message });
    }
});

app.MapGet("/", () => new { service = "VR Command Center", stage = "VR mission placement preflight and Quest connection integration prototype", version = "0.31.0", layoutProfile = "vr-room-v1", worldAssetSets = new[] { VrCommand.Simulation.WorldAssetSets.Legacy, VrCommand.Simulation.WorldAssetSets.FieldProps, VrCommand.Simulation.WorldAssetSets.ServiceRifle, VrCommand.Simulation.WorldAssetSets.Combatants, VrCommand.Simulation.WorldAssetSets.WeaponActions, VrCommand.Simulation.WorldAssetSets.ArmedCombatants, VrCommand.Simulation.WorldAssetSets.CombatEffects, VrCommand.Simulation.WorldAssetSets.PlayerFire, VrCommand.Simulation.WorldAssetSets.PlayerBody }, enemyPresentationVersion = 1, weaponPresentationVersion = 1, enemyFireVersion = 1, playerFireVersion = 1, combatAudioVersion = 1, playerPresentationVersion=1 });
app.MapWorldRoutes();
app.MapGet("/health", () => Results.Ok(new { status = "ok" }));
app.MapGet("/api/me", (HttpContext context) => Actor(context));
app.MapGet("/api/rooms", (SessionManager manager, HttpContext context) => manager.Rooms(Actor(context)));
app.MapGet("/api/missions", (SqliteMissionLibrary store, HttpContext context) => store.List(Actor(context)));
app.MapGet("/api/mission-library", (SqliteMissionLibrary store, HttpContext context) => store.Heads(Actor(context)));
app.MapGet("/api/missions/{id:guid}", (Guid id, SqliteMissionLibrary store, HttpContext context) => store.Get(id, Actor(context)));
app.MapGet("/api/missions/{id:guid}/template", (Guid id, SqliteMissionLibrary store, HttpContext context) =>
{
    var actor = Actor(context);
    AccessPolicy.AuthorMission(actor);
    var template = MissionTemplate.Export(store.Get(id, actor));
    context.Response.Headers.CacheControl = "no-store";
    return Results.File(System.Text.Json.JsonSerializer.SerializeToUtf8Bytes(template, JsonFormat.Options),
        "application/json", $"vr-mission-template-{id:D}.json");
});
app.MapPost("/api/mission-templates/check-file", async (HttpContext context) =>
{
    AccessPolicy.AuthorMission(Actor(context));
    context.Response.Headers.CacheControl = "no-store";
    return await MissionTemplate.Check(context.Request, context.RequestAborted);
});
app.MapGet("/api/missions/{id:guid}/layout", (Guid id, SessionMode? mode, SqliteMissionLibrary store, HttpContext context) =>
    MissionLayout.Inspect(store.Get(id, Actor(context)).Definition, mode ?? SessionMode.Independent));
app.MapPost("/api/mission-layout", (MissionLayoutRequest request, HttpContext context) =>
{
    AccessPolicy.AuthorMission(Actor(context));
    return MissionLayout.Inspect(request);
});
app.MapPost("/api/room-alignment", (RoomAlignmentRequest request, HttpContext context) =>
{
    AccessPolicy.AuthorMission(Actor(context));
    context.Response.Headers.CacheControl = "no-store";
    return RoomAlignment.Solve(request);
});
app.MapPost("/api/room-alignment/check-file", async (HttpContext context) =>
{
    AccessPolicy.AuthorMission(Actor(context));
    context.Response.Headers.CacheControl = "no-store";
    if (context.Request.ContentLength is 0 or > RoomAlignment.MaxFileBytes)
        throw new ArgumentException("Use a room alignment export up to 16 KiB.");
    var bytes = new byte[RoomAlignment.MaxFileBytes + 1];
    var count = await context.Request.Body.ReadAtLeastAsync(bytes, bytes.Length, throwOnEndOfStream: false, context.RequestAborted);
    return RoomAlignment.CheckFile(bytes.AsSpan(0, count));
});
app.MapGet("/api/missions/{id:guid}/version", (Guid id, SqliteMissionLibrary store, HttpContext context) => store.Version(id, Actor(context)));
app.MapGet("/api/missions/{id:guid}/history", (Guid id, int? before, int? limit, SqliteMissionLibrary store, HttpContext context) => store.History(id, before, limit ?? 20, Actor(context)));
app.MapPost("/api/missions", (MissionDraft draft, SqliteMissionLibrary store, HttpContext context) =>
{
    AccessPolicy.AuthorMission(Actor(context));
    var mission = store.Create(draft, Actor(context), RequestId(context));
    return Results.Created($"/api/missions/{mission.Id}", mission);
});
app.MapPost("/api/missions/{id:guid}/revisions", (Guid id, MissionDraft draft, SqliteMissionLibrary store, HttpContext context) =>
{
    AccessPolicy.AuthorMission(Actor(context));
    var mission = store.Revise(id, draft, Actor(context), RequestId(context) ?? throw new ArgumentException("Idempotency-Key is required for mission revisions."));
    return Results.Created($"/api/missions/{mission.Id}", mission);
});
app.MapPost("/api/sessions", (CreateSession request, SqliteMissionLibrary store, SessionManager manager, HttpContext context) =>
{
    var session = manager.Create(request.Mode, request.RoomIds, store.Get(request.MissionId, Actor(context)), Actor(context), RequestId(context));
    return Results.Created($"/api/sessions/{session.Id}", session);
});
app.MapPost("/api/sessions/independent-set", (CreateIndependentSet request, SqliteMissionLibrary store, SessionManager manager, HttpContext context) =>
{
    var actor = Actor(context);
    AccessPolicy.AuthorMission(actor);
    var key = RequestId(context) ?? throw new ArgumentException("Idempotency-Key is required for five independent sessions.");
    IndependentSessionSet receipt;
    if (request.MissionId is Guid missionId && missionId != Guid.Empty && request.Rooms is null)
        receipt = manager.CreateIndependentSet(store.Get(missionId, actor), actor, key);
    else if (request.MissionId is null && request.Rooms is { Length: SessionManager.RoomCount } rooms
        && rooms.All(room => room is not null && room.MissionId != Guid.Empty)
        && rooms.Select(room => room.RoomId).Order().SequenceEqual(Enumerable.Range(1, SessionManager.RoomCount)))
    {
        var missions = rooms.Select(room => room.MissionId).Distinct().ToDictionary(id => id, id => store.Get(id, actor));
        receipt = manager.CreateIndependentSet(rooms.OrderBy(room => room.RoomId).Select(room => missions[room.MissionId]).ToArray(), actor, key);
    }
    else throw new ArgumentException("Use a saved mission ID for all five rooms or assign one saved mission to each room.");
    context.Response.Headers.CacheControl = "no-store";
    return Results.Json(receipt, statusCode: receipt.Duplicate ? StatusCodes.Status200OK : StatusCodes.Status201Created);
});
app.MapGet("/api/sessions/{id:guid}", (Guid id, SessionManager manager, HttpContext context) => manager.Get(id, Actor(context)));
app.MapGet("/api/sessions/{id:guid}/overview", (Guid id, SessionManager manager, HttpContext context) =>
{
    context.Response.Headers.CacheControl = "no-store";
    return manager.GetOverview(id, Actor(context));
});
app.MapGet("/api/sessions", (bool? includeEnded, SessionManager manager, HttpContext context) => manager.List(includeEnded ?? false, Actor(context)));
app.MapGet("/api/sessions/{id:guid}/events", (Guid id, long? after, int? limit, SessionManager manager, HttpContext context) =>
    manager.Events(id, after ?? 0, limit ?? 100, Actor(context)));
app.MapGet("/api/sessions/{id:guid}/rooms/{roomId:int}/hardware-feedback", (Guid id, int roomId, long? after, bool? includeBindings, SessionManager manager, HttpContext context) =>
{
    context.Response.Headers.CacheControl = "no-store";
    return manager.ReadHardwareFeedback(id, roomId, after, Actor(context), includeBindings == true);
});
app.MapPost("/api/sessions/{id:guid}/commands", (Guid id, ControlCommand command, WorldRecordings worlds, HttpContext context) =>
    worlds.ExecuteCommand(id, command, Actor(context)));
app.MapGet("/api/venue/phase", (SessionManager manager, HttpContext context) =>
{
    context.Response.Headers.CacheControl = "no-store";
    return manager.ReadVenuePhase(Actor(context));
});
app.MapGet("/api/venue/closure", (bool? includeScores, WorldRecordings worlds, HttpContext context) =>
{
    context.Response.Headers.CacheControl = "no-store";
    return worlds.ReadVenueClosure(Actor(context), includeScores == true);
});
app.MapGet("/api/venue/closure/history", (Guid? before, int? limit, SessionManager manager, HttpContext context) =>
{
    context.Response.Headers.CacheControl = "no-store";
    return manager.ReadVenueEndHistory(before, limit ?? 20, Actor(context));
});
app.MapGet("/api/venue/closure/{id:guid}", (Guid id, bool? includeScores, WorldRecordings worlds, HttpContext context) =>
{
    context.Response.Headers.CacheControl = "no-store";
    return worlds.ReadVenueClosure(Actor(context), includeScores == true, id);
});
app.MapGet("/api/venue/closure/{id:guid}/reports.zip", (Guid id, SessionManager manager, HttpContext context) =>
{
    context.Response.Headers.CacheControl = "no-store";
    var report = manager.FinalVenueReports(id, Actor(context));
    return Results.File(FinalReportCsv.EncodeVenueBundle(report), "application/zip", $"vr-command-venue-reports-v1-{id:D}.zip");
});
app.MapGet("/api/venue/closure/{id:guid}/field-evidence.zip", (Guid id, WorldRecordings worlds, HttpContext context) =>
{
    context.Response.Headers.CacheControl = "no-store";
    var evidence = worlds.ReadVenueFieldEvidence(id, Actor(context));
    return Results.File(evidence.Encode(), "application/zip", $"vr-command-venue-field-v1-{id:D}.zip");
});
app.MapPost("/api/venue/phase", (VenuePhaseRequest request, WorldRecordings worlds, HttpContext context) =>
{
    context.Response.Headers.CacheControl = "no-store";
    var actor = Actor(context);
    if (actor.Role != OperatorRole.Master) throw new AccessDeniedException("Venue phase operations require the master operator.");
    var key = RequestId(context) ?? throw new ArgumentException("Idempotency-Key is required for venue phase changes.");
    return worlds.ExecuteVenuePhase(request.Action, request.Targets, key, actor, request.Environment, request.EnemyPolicy,
        request.RequireFullTracking, request.RequireFullParticipation);
});
app.MapGet("/api/sessions/{id:guid}/statistics", (Guid id, SessionManager manager, HttpContext context) =>
    manager.Statistics(id, Actor(context)));
app.MapGet("/api/sessions/{id:guid}/field-evidence.zip", (Guid id, WorldRecordings worlds, HttpContext context) =>
{
    context.Response.Headers.CacheControl = "no-store";
    var evidence = worlds.ReadFieldEvidence(id, Actor(context));
    return Results.File(evidence.Encode(), "application/zip", $"vr-command-field-v1-{id:D}.zip");
});
app.MapGet("/api/sessions/{id:guid}/report.csv", (Guid id, SessionManager manager, HttpContext context) =>
    ExportReport(id, null, manager, context));
app.MapGet("/api/sessions/{id:guid}/rooms/{roomId:int}/report.csv", (Guid id, int roomId, SessionManager manager, HttpContext context) =>
    ExportReport(id, roomId, manager, context));
app.MapGet("/api/sessions/{id:guid}/players/{playerId:guid}/report.csv", (Guid id, Guid playerId, SessionManager manager, HttpContext context) =>
{
    context.Response.Headers.CacheControl = "no-store";
    var report = manager.FinalPlayerReport(id, playerId, Actor(context));
    return Results.File(FinalReportCsv.Encode(report), "text/csv; charset=utf-8", FinalReportCsv.FileName(id, playerId));
});
app.MapGet("/api/sessions/{id:guid}/reports.zip", (Guid id, SessionManager manager, HttpContext context) =>
{
    context.Response.Headers.CacheControl = "no-store";
    var actor = Actor(context);
    if (actor.Role != OperatorRole.Master) throw new AccessDeniedException("Only the master may export the linked report bundle.");
    var report = manager.FinalReport(id, actor);
    if (report.Mode != SessionMode.Linked) throw new ArgumentException("The report bundle requires a linked session.");
    return Results.File(FinalReportCsv.EncodeBundle(report), "application/zip", $"vr-command-reports-v1-{id:D}.zip");
});
static IResult ExportReport(Guid id, int? roomId, SessionManager manager, HttpContext context)
{
    context.Response.Headers.CacheControl = "no-store";
    var report = manager.FinalReport(id, Actor(context), roomId);
    return Results.File(FinalReportCsv.Encode(report), "text/csv; charset=utf-8", FinalReportCsv.FileName(id, roomId));
}
app.MapPost("/api/sessions/{id:guid}/combat", (Guid id, CombatReport report, SessionManager manager, HttpContext context) =>
    manager.ReportCombat(id, report, Actor(context)));
app.MapPost("/api/sessions/{id:guid}/combat-stream", (Guid id, OpenCombatStream request, SessionManager manager, HttpContext context) =>
    manager.OpenStream(id, request, Actor(context)));
app.MapPost("/api/sessions/{id:guid}/combat-stream/reports", (Guid id, StreamCombatRecord request, SessionManager manager, HttpContext context) =>
    manager.ReportStream(id, request, Actor(context)));
app.MapPost("/api/sessions/{id:guid}/combat-stream/batch", (Guid id, StreamCombatRecord[] request, SessionManager manager, HttpContext context) =>
    manager.ReportStreamBatch(id, request, Actor(context)));
app.MapPost("/api/sessions/{id:guid}/combat-stream/seal", (Guid id, SealCombatStream request, SessionManager manager, HttpContext context) =>
    manager.SealStream(id, request, Actor(context)));
app.MapPost("/api/sessions/{id:guid}/players", (Guid id, JoinPlayer request, SessionManager manager, HttpContext context) =>
    manager.Join(id, request.PlayerId, request.Name, request.RoomId, request.Headset, Actor(context), RequestId(context)));
app.MapPost("/api/sessions/{id:guid}/players/{playerId:guid}/join-ticket", (Guid id, Guid playerId, SessionManager manager, HttpContext context) =>
{
    var session = manager.Get(id, Actor(context));
    var player = session.Players.SingleOrDefault(p => p.Id == playerId) ?? throw new KeyNotFoundException("Player does not exist.");
    AccessPolicy.Player(Actor(context), session, player.RoomId);
    if (session.State == SessionState.Ended) throw new InvalidOperationException("Session has ended.");
    var expected = AdmissionMatch(context) ?? throw new ArgumentException("If-Match-Admission is required; reload the current player roster.");
    if (expected != player.AdmissionId) throw new InvalidOperationException("Player admission changed; reload the current roster.");
    context.Response.Headers.CacheControl = "no-store";
    return ticketSigner.Issue(session, player);
});
app.MapPost("/api/player-tickets/validate", (ValidatePlayerTicket request, SessionManager manager, HttpContext context) =>
{
    if (Actor(context).Role != OperatorRole.GameServer)
        throw new AccessDeniedException("Player ticket validation requires a game-server identity.");
    if (request.ProtocolVersion != 2) throw new ArgumentException("Game server admission protocol 2 is required; upgrade the game server.");
    var claims = ticketSigner.Validate(request.Ticket, request.SessionId);
    return manager.ResolveAdmission(claims, Actor(context));
});
app.MapPost("/api/sessions/{id:guid}/rooms/{roomId:int}/join-ticket-bundle", (Guid id, int roomId, RoomTicketRequest request, SessionManager manager, HttpContext context) =>
{
    var actor = Actor(context);
    var bundle = RoomTicketBundles.Create(manager.Get(id, actor), roomId, request, actor, ticketSigner);
    context.Response.Headers.CacheControl = "no-store";
    return Results.File(bundle, "application/zip", FormattableString.Invariant($"room-{roomId:00}-connections.zip"));
});
app.MapPost("/api/sessions/{id:guid}/rooms/{roomId:int}/players/{playerId:guid}/deployment-check", async (Guid id, int roomId, Guid playerId, SessionManager manager, HttpContext context) =>
{
    context.Response.Headers.CacheControl = "no-store";
    var actor = Actor(context);
    if (actor.Role != OperatorRole.Master && (actor.Role != OperatorRole.RoomController || actor.RoomId != roomId))
        throw new AccessDeniedException("Deployment checks are limited to the controller's room.");
    var files = await MrDeploymentCheck.ReadFiles(context.Request, context.RequestAborted);
    var session = manager.Get(id, actor);
    var player = session.Players.SingleOrDefault(p => p.Id == playerId && p.RoomId == roomId)
        ?? throw new KeyNotFoundException("Player does not exist in this room.");
    return MrDeploymentCheck.Check(session, player, files, ticketSigner);
});
app.MapPost("/api/mr-deployment/venue-check", async (SessionManager manager, HttpContext context) =>
{
    context.Response.Headers.CacheControl = "no-store";
    var actor = Actor(context);
    if (actor.Role != OperatorRole.Master) throw new AccessDeniedException("Venue deployment checks require the master operator.");
    var files = await MrDeploymentCheck.ReadVenue(context.Request, context.RequestAborted);
    return MrDeploymentCheck.CheckVenue(files, manager.List(false, actor), ticketSigner);
});
app.MapPost("/api/mr-deployment/venue-bundle", async (WorldRecordings worlds, HttpContext context) =>
{
    context.Response.Headers.CacheControl = "no-store";
    var actor = Actor(context);
    if (actor.Role != OperatorRole.Master) throw new AccessDeniedException("Venue exports require the master operator.");
    var request = await MrVenueBundle.Read(context.Request, context.RequestAborted);
    return Results.File(MrVenueBundle.Create(request, worlds, actor, ticketSigner), "application/zip", "quest-mr-venue.zip");
});
app.MapGet("/api/vr-deployment/venue", (WorldRecordings worlds, HttpContext context) =>
{
    context.Response.Headers.CacheControl = "no-store";
    return VrVenueTickets.Read(worlds, Actor(context));
});
app.MapPost("/api/vr-deployment/venue-bundle", async (WorldRecordings worlds, HttpContext context) =>
{
    context.Response.Headers.CacheControl = "no-store";
    var actor = Actor(context);
    if (actor.Role != OperatorRole.Master) throw new AccessDeniedException("Venue exports require the master operator.");
    var request = await VrVenueTickets.ReadRequest(context.Request, context.RequestAborted);
    return Results.File(VrVenueTickets.Create(request, worlds, actor, ticketSigner), "application/zip", "vr-venue-connections.zip");
});
app.MapPost("/api/vr-deployment/venue-check", async (WorldRecordings worlds, HttpContext context) =>
{
    context.Response.Headers.CacheControl = "no-store";
    var actor = Actor(context);
    if (actor.Role != OperatorRole.Master) throw new AccessDeniedException("Venue checks require the master operator.");
    var request = await VrVenueTickets.ReadCheck(context.Request, context.RequestAborted);
    return VrVenueTickets.Check(request, worlds, actor, ticketSigner);
});
app.MapGet("/api/mixed-deployment/venue", (WorldRecordings worlds, HttpContext context) =>
{
    context.Response.Headers.CacheControl = "no-store";
    return MixedVenueDeployment.Read(worlds, Actor(context));
});
app.MapPost("/api/mixed-deployment/venue-bundle", async (WorldRecordings worlds, HttpContext context) =>
{
    context.Response.Headers.CacheControl = "no-store";
    var actor = Actor(context);
    if (actor.Role != OperatorRole.Master) throw new AccessDeniedException("Venue exports require the master operator.");
    var request = await MixedVenueDeployment.ReadBundle(context.Request, context.RequestAborted);
    return Results.File(MixedVenueDeployment.Create(request, worlds, actor, ticketSigner), "application/zip", "vr-mr-venue-deployment.zip");
});
app.MapPost("/api/mixed-deployment/venue-check", async (WorldRecordings worlds, HttpContext context) =>
{
    context.Response.Headers.CacheControl = "no-store";
    var actor = Actor(context);
    if (actor.Role != OperatorRole.Master) throw new AccessDeniedException("Venue checks require the master operator.");
    var request = await MixedVenueDeployment.ReadCheck(context.Request, context.RequestAborted);
    return MixedVenueDeployment.Check(request, worlds, actor, ticketSigner);
});
app.MapDelete("/api/sessions/{id:guid}/players/{playerId:guid}", (Guid id, Guid playerId, SessionManager manager, HttpContext context) =>
{
    manager.Leave(id, playerId, Actor(context), RequestId(context), AdmissionMatch(context), requireAdmissionMatch: true);
    return Results.NoContent();
});
app.MapDelete("/api/sessions/{id:guid}", (Guid id, SessionManager manager, HttpContext context) =>
{
    manager.End(id, Actor(context));
    return Results.NoContent();
});
app.Run();

static OperatorIdentity Actor(HttpContext context) => (OperatorIdentity)context.Items[typeof(OperatorIdentity)]!;

static Guid? RequestId(HttpContext context)
{
    if (!context.Request.Headers.TryGetValue("Idempotency-Key", out var values)) return null;
    if (values.Count != 1 || !Guid.TryParseExact(values[0], "D", out var id) || id == Guid.Empty)
        throw new ArgumentException("Idempotency-Key must be one non-empty UUID in D format.");
    context.Response.Headers["Idempotency-Key"] = id.ToString("D");
    return id;
}

static Guid? AdmissionMatch(HttpContext context)
{
    if (!context.Request.Headers.TryGetValue("If-Match-Admission", out var values)) return null;
    if (values.Count != 1 || !Guid.TryParseExact(values[0], "D", out var admission) || admission == Guid.Empty)
        throw new ArgumentException("If-Match-Admission must contain one non-empty UUID.");
    return admission;
}

record CreateSession(Guid MissionId, SessionMode Mode, int[] RoomIds);
record IndependentRoomMission(int RoomId, Guid MissionId);
record CreateIndependentSet(Guid? MissionId, IndependentRoomMission[]? Rooms);
record VenuePhaseRequest(ControlAction Action, VenuePhaseFence?[]? Targets, VenueClimate? Environment, VenueEnemyPolicy? EnemyPolicy,
    bool RequireFullTracking = false, bool RequireFullParticipation = false);
record JoinPlayer(Guid PlayerId, string Name, int RoomId, HeadsetKind Headset);
record ValidatePlayerTicket(Guid SessionId, string Ticket, int ProtocolVersion = 0);
