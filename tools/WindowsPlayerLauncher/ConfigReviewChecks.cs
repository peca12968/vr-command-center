// Actual review class, local fixture bytes only; no ticket/admission or GUI proof.
using System;
using System.IO;
using System.Text;

internal static class PlayerReviewChecks
{
    private static int checks;
    private static void Check(bool value) { if (!value) throw new InvalidOperationException("Config review check failed."); checks++; }
    private static void Reject(Action action) { bool rejected = false; try { action(); } catch { rejected = true; } Check(rejected); }
    private static void Write(string file, string address, string ticket)
    { File.WriteAllText(file, "{\"role\":\"Client\",\"address\":\"" + address + "\",\"port\":7777,\"joinTicket\":\"" + ticket + "\"}", new UTF8Encoding(false)); }
    private static void Empty(PlayerLauncher.ConfigReview review) { Check(!review.Loaded && review.FilePath == null && review.ContentHash == null && review.Endpoint == null); }
    private static int Main(string[] args)
    {
        var root = Path.GetFullPath(args[0]); Directory.CreateDirectory(root);
        var file = Path.Combine(root, "player 玩家 &.json");
        var review = new PlayerLauncher.ConfigReview(); Empty(review); Reject(review.RequireCurrent);
        Write(file, "127.0.0.1", "fixture-not-a-ticket"); review.Load(file);
        Check(review.Loaded && review.FilePath == file && review.Endpoint == "127.0.0.1:7777" && review.ContentHash.Length == 64);
        review.RequireCurrent(); Check(review.Loaded);
        var originalHash = review.ContentHash;
        Write(file, "192.168.1.22", "fixture-not-a-ticket"); Reject(review.RequireCurrent); Empty(review);
        review.Load(file); Check(review.Endpoint == "192.168.1.22:7777" && review.ContentHash != originalHash);
        Write(file, "192.168.1.22", "replacement-ticket"); Reject(review.RequireCurrent); Empty(review);
        review.Load(file); review.Clear(); Empty(review); Reject(review.RequireCurrent);
        review.Load(file); File.Move(file, file + ".moved"); Reject(review.RequireCurrent); Empty(review);
        File.Move(file + ".moved", file); review.Load(file);
        File.WriteAllText(file, "{\"role\":\"Server\",\"secret\":\"fixture-secret\"}"); Reject(delegate { review.Load(file); }); Empty(review);
        Write(file, "127.0.0.1", "fixture-not-a-ticket"); review.Load(file);
        Reject(delegate { review.Load("relative.json"); }); Empty(review);
        Reject(delegate { review.Load("C:relative.json"); }); Empty(review);
        Reject(delegate { review.Load("\\drive-relative.json"); }); Empty(review);
        review.Load(file);
        using (var writer = new FileStream(file, FileMode.Open, FileAccess.ReadWrite, FileShare.Read))
            Reject(review.RequireCurrent);
        Empty(review); review.Load(file); review.RequireCurrent(); Check(review.Loaded);
        Console.WriteLine("{\"complete\":true,\"checks\":" + checks + ",\"scope\":\"Actual compiled ConfigReview with local fixture files, no GUI/network/admission proof\"}");
        return 0;
    }
}
