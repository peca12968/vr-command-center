namespace VrCommand.Core;

public enum OperatorRole { Internal, Master, RoomController, GameServer }
public record OperatorIdentity(string Id, OperatorRole Role, int? RoomId = null)
{
    // Trusted in-process callers and pre-v0.3 histories only; never issued by HTTP authentication.
    public static OperatorIdentity Internal { get; } = new("internal", OperatorRole.Internal);
}

public sealed class AccessDeniedException(string message) : Exception(message);

public static class AccessPolicy
{
    public static void Validate(OperatorIdentity actor)
    {
        if (string.IsNullOrWhiteSpace(actor.Id) || actor.Id.Length > 80 || !Enum.IsDefined(actor.Role)
            || (actor.Role == OperatorRole.RoomController
                ? actor.RoomId is null or < 1 or > SessionManager.RoomCount : actor.RoomId is not null))
            throw new ArgumentException("Invalid operator identity.");
    }

    public static bool CanRead(OperatorIdentity actor, int[] roomIds)
    {
        Validate(actor);
        return actor.Role != OperatorRole.RoomController || roomIds.Contains(actor.RoomId!.Value);
    }

    public static void Read(OperatorIdentity actor, int[] roomIds)
    {
        if (!CanRead(actor, roomIds)) throw new AccessDeniedException("This session is outside the controller's room.");
    }

    public static void Manage(OperatorIdentity actor, SessionMode mode, int[] roomIds)
    {
        Validate(actor);
        if (actor.Role is OperatorRole.Internal or OperatorRole.Master) return;
        if (actor.Role == OperatorRole.RoomController && mode == SessionMode.Independent
            && roomIds.Length == 1 && roomIds[0] == actor.RoomId) return;
        throw new AccessDeniedException("Only the master may control linked sessions or other rooms.");
    }

    public static void Player(OperatorIdentity actor, SessionView session, int roomId)
    {
        Validate(actor);
        if (actor.Role is OperatorRole.Internal or OperatorRole.Master) return;
        if (actor.Role == OperatorRole.RoomController && actor.RoomId == roomId && session.RoomIds.Contains(roomId)) return;
        throw new AccessDeniedException("Player management is limited to the controller's room.");
    }

    internal static void Control(OperatorIdentity actor, SessionView session, ControlCommand command)
    {
        if (command.Action != ControlAction.SetRoomEnemies) { Manage(actor, session.Mode, session.RoomIds); return; }
        var room = command.RoomEnemyPolicy?.RoomId ?? 0;
        Validate(actor);
        if (actor.Role is not (OperatorRole.Internal or OperatorRole.Master) &&
            (actor.Role != OperatorRole.RoomController || actor.RoomId != room))
            throw new AccessDeniedException("Enemy policy changes are limited to the controller's room.");
        if (session.Mode != SessionMode.Linked || !session.RoomIds.Contains(room))
            throw new InvalidOperationException("A room enemy policy requires a room in a linked session.");
    }

    public static void AuthorMission(OperatorIdentity actor)
    {
        Validate(actor);
        if (actor.Role is not (OperatorRole.Internal or OperatorRole.Master))
            throw new AccessDeniedException("Only the master may author shared mission templates.");
    }

    public static void ReadMission(OperatorIdentity actor)
    {
        // Shared mission templates are readable by every configured role; writes remain master-only.
        Validate(actor);
    }

    public static void ReportCombat(OperatorIdentity actor)
    {
        Validate(actor);
        if (actor.Role is not (OperatorRole.Internal or OperatorRole.GameServer))
            throw new AccessDeniedException("Combat events require a trusted game-server identity.");
    }
}
