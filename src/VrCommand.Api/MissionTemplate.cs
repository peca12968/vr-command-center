using VrCommand.Core;

namespace VrCommand.Api;

internal sealed record MissionTemplate(string Format, int Version, MissionDraft Definition)
{
    internal const int MaxFileBytes = 512 * 1024;
    internal const string FileFormat = "vr-command-mission-template";

    internal static MissionTemplate Export(Mission mission) => new(FileFormat, 1, mission.Definition);

    internal static async Task<MissionTemplate> Check(HttpRequest request, CancellationToken cancellation)
    {
        var template = await DeploymentJson.Read<MissionTemplate>(request, MaxFileBytes,
            "Use a complete mission template JSON file up to 512 KiB.", cancellation, completeFile: true);
        if (template.Format != FileFormat || template.Version != 1)
            throw new ArgumentException("Unsupported mission template format or version.");
        MissionStore.Validate(template.Definition);
        return template;
    }
}
