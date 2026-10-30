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
var app = builder.Build();
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
        if (ex is MissionLayoutRejectedException layout)
            await context.Response.WriteAsJsonAsync(new { error = ex.Message, layout = layout.Report });
        else await context.Response.WriteAsJsonAsync(new { error = ex.Message });
    }
});

app.MapGet("/", () => new { service = "VR Command Center", stage = "VR mission placement preflight and Quest connection integration prototype", version = "0.26.0", layoutProfile = "vr-room-v1", worldAssetSets = new[] { VrCommand.Simulation.WorldAssetSets.Legacy, VrCommand.Simulation.WorldAssetSets.FieldProps, VrCommand.Simulation.WorldAssetSets.ServiceRifle, VrCommand.Simulation.WorldAssetSets.Combatants, VrCommand.Simulation.WorldAssetSets.WeaponActions, VrCommand.Simulation.WorldAssetSets.ArmedCombatants, VrCommand.Simulation.WorldAssetSets.CombatEffects, VrCommand.Simulation.WorldAssetSets.PlayerFire, VrCommand.Simulation.WorldAssetSets.PlayerBody }, enemyPresentationVersion = 1, weaponPresentationVersion = 1, enemyFireVersion = 1, playerFireVersion = 1, combatAudioVersion = 1, playerPresentationVersion=1 });
app.MapWorldRoutes();
app.MapGet("/health", () => Results.Ok(new { status = "ok" }));
app.MapGet("/api/me", (HttpContext context) => Actor(context));
app.MapGet("/api/rooms", (SessionManager manager, HttpContext context) => manager.Rooms(Actor(context)));
app.MapGet("/api/missions", (SqliteMissionLibrary store, HttpContext context) => store.List(Actor(context)));
app.MapGet("/api/mission-library", (SqliteMissionLibrary store, HttpContext context) => store.Heads(Actor(context)));
app.MapGet("/api/missions/{id:guid}", (Guid id, SqliteMissionLibrary store, HttpContext context) => store.Get(id, Actor(context)));
app.MapGet("/api/missions/{id:guid}/layout", (Guid id, SessionMode? mode, SqliteMissionLibrary store, HttpContext context) =>
    MissionLayout.Inspect(store.Get(id, Actor(context)).Definition, mode ?? SessionMode.Independent));
app.MapPost("/api/mission-layout", (MissionLayoutRequest request, HttpContext context) =>
{
    AccessPolicy.AuthorMission(Actor(context));
    return MissionLayout.Inspect(request);
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
app.MapGet("/api/sessions/{id:guid}", (Guid id, SessionManager manager, HttpContext context) => manager.Get(id, Actor(context)));
app.MapGet("/api/sessions", (bool? includeEnded, SessionManager manager, HttpContext context) => manager.List(includeEnded ?? false, Actor(context)));
app.MapGet("/api/sessions/{id:guid}/events", (Guid id, long? after, int? limit, SessionManager manager, HttpContext context) =>
    manager.Events(id, after ?? 0, limit ?? 100, Actor(context)));
app.MapPost("/api/sessions/{id:guid}/commands", (Guid id, ControlCommand command, SessionManager manager, HttpContext context) =>
    manager.Execute(id, command, Actor(context)));
app.MapGet("/api/sessions/{id:guid}/statistics", (Guid id, SessionManager manager, HttpContext context) =>
    manager.Statistics(id, Actor(context)));
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
    return ticketSigner.Issue(id, player);
});
app.MapPost("/api/player-tickets/validate", (ValidatePlayerTicket request, SessionManager manager, HttpContext context) =>
{
    if (Actor(context).Role != OperatorRole.GameServer)
        throw new AccessDeniedException("Player ticket validation requires a game-server identity.");
    if (request.ProtocolVersion != 2) throw new ArgumentException("Game server admission protocol 2 is required; upgrade the game server.");
    var claims = ticketSigner.Validate(request.Ticket, request.SessionId);
    return manager.ResolveAdmission(claims, Actor(context));
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
record JoinPlayer(Guid PlayerId, string Name, int RoomId, HeadsetKind Headset);
record ValidatePlayerTicket(Guid SessionId, string Ticket, int ProtocolVersion = 0);
