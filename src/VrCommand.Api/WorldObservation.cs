using VrCommand.Core;
using VrCommand.Simulation;

namespace VrCommand.Api;

public sealed partial class WorldRecordings
{
    internal static void RequireObserverRoom(WorldRecordingInfo info, int room, OperatorIdentity actor)
    {
        if (actor.Role == OperatorRole.RoomController && actor.RoomId != room)
            throw new AccessDeniedException("Select your own room for the room observation stream.");
        if (!info.Header.roomIds.Contains(room)) throw new ArgumentException("Select a room within this recording.");
    }

    internal static WorldRecordingInfo ObservationInfo(WorldRecordingInfo info, int? observerRoom)
    {
        if (observerRoom is not int room) return info;
        // Info deserializes a fresh header for each response. The stored header is never changed.
        info.Header.props = info.Header.props.Where(prop => prop.roomId == room).ToArray();
        return info with { ObserverRoomId = room };
    }

    internal WorldFrameView ObservationFrame(Guid id, WorldFrameView view, int room,
        IReadOnlyDictionary<string, int> propRooms, OperatorIdentity actor)
    {
        // Frame owns this deserialized packet; project the response after reading the unfiltered source.
        var packet = view.Packet;
        var previousEnemies = packet.sequence > 1 && packet.events.Any(entry => entry.enemyId.Length > 0 || entry.targetId.Length > 0)
            ? Frame(id, packet.sequence - 1, actor)?.Packet.frame.enemies ?? [] : [];
        packet.events = RoomCombatEvents(packet, view.Statistics, previousEnemies, propRooms, room);
        var frame = packet.frame;
        frame.players = frame.players.Where(player => player.roomId == room).ToArray();
        frame.enemies = frame.enemies.Where(enemy => enemy.roomId == room).ToArray();
        if (frame.roomEnemyPolicies is { } policies)
            frame.roomEnemyPolicies = policies.Where(policy => policy.roomId == room).ToArray();
        return view with { ObserverRoomId = room, Statistics = view.Statistics.Where(player => player.RoomId == room).ToArray() };
    }
}
