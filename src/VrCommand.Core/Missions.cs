using System.Text.Json;
using System.Text.Json.Serialization;

namespace VrCommand.Core;

public enum Weather { Clear, Rain, Fog, Storm }
public enum TimeOfDay { Day, Night }
public enum ExperienceMode { VR, MR }
public enum EnemyBehavior { Hold, Patrol, Advance }
public record Position(float X, float Y, float Z);
public record EnvironmentSettings(ExperienceMode Mode, Weather Weather, TimeOfDay TimeOfDay, bool Lightning);
public record PropPlacement(string AssetId, Position Position, float YawDegrees);
public record EnemySettings(int Count, EnemyBehavior Behavior, bool AutoAttack);
public record MissionDraft(string Name, string Briefing, int DurationSeconds,
    EnvironmentSettings Environment, EnemySettings Enemies, PropPlacement[] Props);
public record Mission(Guid Id, int SchemaVersion, DateTimeOffset CreatedAtUtc, MissionDraft Definition);

public static class JsonFormat
{
    public static JsonSerializerOptions Options { get; } = new(JsonSerializerDefaults.Web)
    {
        WriteIndented = true,
        Converters = { new JsonStringEnumConverter(allowIntegerValues: false) }
    };
}

public sealed class MissionStore(string directory)
{
    public Mission Create(MissionDraft draft)
    {
        Validate(draft);
        var mission = new Mission(Guid.NewGuid(), 1, DateTimeOffset.UtcNow, draft);
        Directory.CreateDirectory(directory);
        var destination = Path.Combine(directory, $"{mission.Id:D}.json");
        var temporary = destination + ".tmp";
        try
        {
            File.WriteAllText(temporary, JsonSerializer.Serialize(mission, JsonFormat.Options));
            File.Move(temporary, destination);
        }
        finally
        {
            if (File.Exists(temporary)) File.Delete(temporary);
        }
        return mission;
    }

    public Mission Get(Guid id)
    {
        var path = Path.Combine(directory, $"{id:D}.json");
        if (!File.Exists(path)) throw new KeyNotFoundException("Mission does not exist.");
        var mission = JsonSerializer.Deserialize<Mission>(File.ReadAllText(path), JsonFormat.Options)
            ?? throw new InvalidDataException("Invalid mission file.");
        if (mission.Id != id || mission.SchemaVersion != 1)
            throw new InvalidDataException("Unsupported or inconsistent mission file.");
        Validate(mission.Definition);
        return mission;
    }

    public Mission[] List() => !Directory.Exists(directory) ? [] :
        Directory.EnumerateFiles(directory, "*.json")
            .Select(Path.GetFileNameWithoutExtension)
            .Where(name => Guid.TryParse(name, out _))
            .Select(name => Get(Guid.Parse(name!)))
            .OrderByDescending(mission => mission.CreatedAtUtc).ToArray();

    public static void Validate(MissionDraft draft)
    {
        ArgumentNullException.ThrowIfNull(draft);
        if (string.IsNullOrWhiteSpace(draft.Name) || draft.Name.Length > 100)
            throw new ArgumentException("Mission name must contain 1–100 characters.");
        if (draft.Briefing is null || draft.Briefing.Length > 10000)
            throw new ArgumentException("Briefing must be a string of at most 10000 characters.");
        if (draft.DurationSeconds is < 60 or > 14400)
            throw new ArgumentException("Mission duration must be 60–14400 seconds.");
        if (draft.Environment is null || !Enum.IsDefined(draft.Environment.Mode)
            || !Enum.IsDefined(draft.Environment.Weather) || !Enum.IsDefined(draft.Environment.TimeOfDay))
            throw new ArgumentException("Environment settings are invalid.");
        if (draft.Enemies is null || draft.Enemies.Count is < 0 or > 100
            || !Enum.IsDefined(draft.Enemies.Behavior))
            throw new ArgumentException("Enemy settings are invalid.");
        if (draft.Props is null || draft.Props.Length > 500)
            throw new ArgumentException("At most 500 props may be configured.");
        foreach (var prop in draft.Props)
        {
            if (prop is null || string.IsNullOrWhiteSpace(prop.AssetId) || prop.AssetId.Length > 100
                || prop.Position is null || !float.IsFinite(prop.Position.X)
                || !float.IsFinite(prop.Position.Y) || !float.IsFinite(prop.Position.Z)
                || !float.IsFinite(prop.YawDegrees))
                throw new ArgumentException("Prop placement is invalid.");
        }
    }
}
