namespace VrCommand.Persistence;

public sealed class StoreWriterLeaseException(string store, IOException cause)
    : IOException($"Cannot acquire the {store} writer lease.", cause) { }

internal static class StoreWriterLease
{
    internal static FileStream Open(string path, string store)
    {
        try { return new FileStream(path, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None); }
        catch (IOException error) { throw new StoreWriterLeaseException(store, error); }
    }
}
