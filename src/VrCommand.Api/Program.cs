using System.Text.Json.Serialization;
using VrCommand.Core;

var builder = WebApplication.CreateBuilder(args);
builder.Services.ConfigureHttpJsonOptions(options =>
    options.SerializerOptions.Converters.Add(new JsonStringEnumConverter(allowIntegerValues: false)));
var dataDirectory = Path.GetFullPath(builder.Configuration["DataDirectory"]
    ?? Path.Combine(builder.Environment.ContentRootPath, "data", "missions"));
builder.Services.AddSingleton(new MissionStore(dataDirectory));
var sessionDirectory = Path.GetFullPath(builder.Configuration["SessionDataDirectory"]
    ?? Path.Combine(Path.GetDirectoryName(dataDirectory)!, "sessions"));
if (string.Equals(Path.TrimEndingDirectorySeparator(dataDirectory), Path.TrimEndingDirectorySeparator(sessionDirectory),
    OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal))
    throw new InvalidOperationException("Mission and session data directories must be separate.");
builder.Services.AddSingleton(_ => new FileSessionEventStore(sessionDirectory));
builder.Services.AddSingleton(services => new SessionManager(services.GetRequiredService<FileSessionEventStore>()));
var app = builder.Build();
// Fail startup on inconsistent persisted histories, before reporting a healthy service.
app.Services.GetRequiredService<SessionManager>();

app.Use(async (context, next) =>
{
    try { await next(context); }
    catch (Exception ex) when (ex is ArgumentException or KeyNotFoundException or InvalidOperationException)
    {
        context.Response.StatusCode = ex switch
        {
            ArgumentException => 400,
            KeyNotFoundException => 404,
            _ => 409
        };
        await context.Response.WriteAsJsonAsync(new { error = ex.Message });
    }
});

app.MapGet("/", () => new { service = "VR Command Center", stage = "control-plane prototype", version = "0.2.0" });
app.MapGet("/health", () => Results.Ok(new { status = "ok" }));
app.MapGet("/api/rooms", (SessionManager manager) => manager.Rooms());
app.MapGet("/api/missions", (MissionStore store) => store.List());
app.MapGet("/api/missions/{id:guid}", (Guid id, MissionStore store) => store.Get(id));
app.MapPost("/api/missions", (MissionDraft draft, MissionStore store) =>
{
    var mission = store.Create(draft);
    return Results.Created($"/api/missions/{mission.Id}", mission);
});
app.MapPost("/api/sessions", (CreateSession request, MissionStore store, SessionManager manager) =>
{
    var session = manager.Create(request.Mode, request.RoomIds, store.Get(request.MissionId));
    return Results.Created($"/api/sessions/{session.Id}", session);
});
app.MapGet("/api/sessions/{id:guid}", (Guid id, SessionManager manager) => manager.Get(id));
app.MapGet("/api/sessions", (bool? includeEnded, SessionManager manager) => manager.List(includeEnded ?? false));
app.MapGet("/api/sessions/{id:guid}/events", (Guid id, long? after, int? limit, SessionManager manager) =>
    manager.Events(id, after ?? 0, limit ?? 100));
app.MapPost("/api/sessions/{id:guid}/commands", (Guid id, ControlCommand command, SessionManager manager) =>
    manager.Execute(id, command));
app.MapPost("/api/sessions/{id:guid}/players", (Guid id, JoinPlayer request, SessionManager manager) =>
    manager.Join(id, request.PlayerId, request.Name, request.RoomId, request.Headset));
app.MapDelete("/api/sessions/{id:guid}/players/{playerId:guid}", (Guid id, Guid playerId, SessionManager manager) =>
{
    manager.Leave(id, playerId);
    return Results.NoContent();
});
app.MapDelete("/api/sessions/{id:guid}", (Guid id, SessionManager manager) =>
{
    manager.End(id);
    return Results.NoContent();
});
app.Run();

record CreateSession(Guid MissionId, SessionMode Mode, int[] RoomIds);
record JoinPlayer(Guid PlayerId, string Name, int RoomId, HeadsetKind Headset);
