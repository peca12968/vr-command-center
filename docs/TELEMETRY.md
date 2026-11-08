# 持久戰鬥事件與封存 v0.11

v0.13 另有同源世界 journal／publisher，會等待此 outbox 的 durable ack 後才送相應世界幀；操作與限制見 [WORLD_SOURCE.md](WORLD_SOURCE.md)。兩份來源及 API durable state 需一起保留，補送不是世界恢復。

已實作有順序的戰鬥來源、桌面持久 outbox、補送工具及主控台完整性提示。實際 .NET／HTTP 跨程序測試通過；2026-10-29 Unity 已真正編譯、產出 Windows／APK，並以 Windows server 加兩個 desktop client 驗證獨立／跨房的 AI 傷害、戰鬥封存及回放統計一致；來源仍明確 Simulation，沒有頭盔驗證，見 [NATIVE_VALIDATION.md](NATIVE_VALIDATION.md)。這是戰鬥統計管道，尚非完整世界／頭手姿態錄影或崩潰後的世界恢復。

## API 契約

全部端點需 GameServer Bearer；Master／房間控制台不能寫入或接管來源。每場只有一個不可換手的來源，來源 ID、Simulation／GameServer 與操作者身分在 Preparing 綁定；已開始的場次不能新增來源。來源不持有／記錄 API 密鑰。

| POST 路徑（前綴 `/api/sessions/{id}`） | 請求與效果 |
|---|---|
| `/combat-stream` | `{ "streamId": "<UUID>", "origin": "Simulation" }`；回傳來源狀態，原樣重試不重複綁定 |
| `/combat-stream/reports` | 單筆 StreamCombatRecord，回傳接受序號與統計 |
| `/combat-stream/batch` | 1–128 筆相同格式的有序陣列；回傳累計接受序號與統計 |
| `/combat-stream/seal` | `{ "streamId": "<UUID>", "finalSequence": 6 }`；僅 Ended 且已接受到精確序號才可封存 |

單筆格式：

```json
{
  "streamId": "fb4e4bbe-1dfc-4516-890d-2602859b43c4",
  "streamSequence": 1,
  "observedSequence": 4,
  "report": {
    "reportId": "8f69a5f4-fd9a-4ed6-97ed-a6d125d1934d",
    "kind": "ShotFired", "origin": "Simulation",
    "playerId": "4c93ca0c-8348-4bd5-b5a2-9f90883e5633",
    "shotId": "ed885558-8ba1-4baf-9607-0cff9e310fd4", "damage": 0
  }
}
```

streamSequence 從 1 連續增加；observedSequence 是產生事件時，遊戲伺服器最後成功讀到的管理快照序號。API 以稀疏管理快照索引驗證該時點屬於同場 Running，並以當時名冊驗證射擊／受傷資格；不重播整段戰鬥歷史。不得使用未來、Paused／Ended 或已離場的觀察位置偽造新射擊。命中／擊殺仍需前置射擊及同一敵軍因果，來源不得混用。

同 reportId 必須保留完全相同的來源、順序、觀察序號及報告內容，原樣重試可在暫停、結束或封存後取得確認。新序號缺口、改內容／來源或已封存後的新報告回傳 409；其他伺服器身分回傳 403。綁定來源後，舊 `/combat` 端點不能繞過有序管道；未綁來源的既有模擬工具仍用原契約。

批次逐筆持久化，不宣稱整批原子性。中途儲存失敗可能已接受前綴；以原陣列重試會去重前綴並接續。用戶端只在成功收據確認整個已送前綴後記錄本地 acknowledgment，不因網路成功傳送就移除資料。

## 暫停、結束與完整性

Pause／End 保留既有管理生命週期。End 釋放房間；已綁定來源則 `statistics.pendingTelemetry: true`，UI 保留結束場次並提示「等待補送、尚未封存」。由舊 Running 快照產生的已保存事件仍可依序補入該場歷史，不會寫到重用房間的新場次。

遊戲伺服器觀察到 End，先保存舊觀察位置的完整事件尾端，再停止世界、寫入本地 completion 邊界、補送剩餘資料，最後提交精確 finalSequence。只有封存成功後 pendingTelemetry 才變 false；封存回應遺失可原樣確認，不新增第二個封存事件。Paused 的串流維持開啟，以便 Resume 繼續相同序號。

這是受信任遊戲來源對完整尾端的確認，並不獨立證明每筆資料真的來自頭盔。觀察輪詢有延遲，EndAt 記錄的是管理停止請求；在伺服器取得新狀態前，以最後 Running 觀察產生的尾端仍屬補送範圍。未綁來源的舊場次沒有此封存保證。

## 本地 journal 與 Unity 接入

`TelemetryOutbox.cs` 與 Unity／.NET 共用，無 Unity 或後端相依。二進位格式含版本、session／stream／origin、報告批次、累計 acknowledgment、completion 與 seal。每幀有長度及 SHA-256 完整性校驗，每次批次寫入後 Flush 到磁碟才推進記憶體；檔案只允許一個開啟者。SHA-256 用於損壞偵測，不是來源簽章。

恢復會重建待送前綴；壞 checksum、截斷 frame、未知版本或跨場次重用會明確失敗，不自動截短、清空或丟掉資料。損壞檔需另行檢查，目前沒有自動修復／壓縮／保留政策；恢復會載入完整 journal。備份須先停止持有檔案的程序。

Unity 在伺服器建立檔案及綁定來源後才開放戰鬥。每次核心武器／tick 的四種統計事件會先保存，再發佈戰鬥快照；EnemyShot 視覺事件及 reload 不冒充玩家消耗。以最多 128 筆陣列補送，使用同一 reportId、來源與觀察序號。磁碟失敗或永久拒絕會停止戰鬥；網路／5xx 保留待送資料再試。這些 Unity 路徑尚未運行，頻率、同步磁碟成本及 25 人吞吐量仍待量測。

`prepare-vr-session.py` 的 server.json 現在明確設 telemetryOrigin 為 Simulation，telemetryDirectory 為專案的 data/telemetry；玩家設定仍只有 role／address／port／joinTicket。真正遊戲驗收前再明確選用 GameServer，不能把改標記當作實機證據。Android 禁止 Server／Host；journal 不配置到玩家頭盔。

## 中斷後補送

確認原遊戲伺服器已退出並保留原件。若同時持有世界 journal，使用 [WorldRelay](WORLD_SOURCE.md#工具操作) 依序補送兩份紀錄。只有戰鬥 journal 時，從儲存庫根目錄建置工具，再對副本執行。請替換場次 UUID，並指定原管理實例與 GameServer 密鑰設定。

```powershell
dotnet build tools/VrCommand.TelemetryRelay -c Release
dotnet tools/VrCommand.TelemetryRelay/bin/Release/net10.0/VrCommand.TelemetryRelay.dll --journal F:/Projects/vr-command-center/artifacts/recovery/SESSION.journal --base-url $managementUrl --key-file $operatorKeyFile
```

戰鬥 journal 本身沒有任務時鐘版本。工具先查原場次，僅採用串流 ID 及來源吻合的版本，再由 API 驗證原擁有者。尚未附接且本機無確認的舊 journal 可依版本 0 附接。有 completion 才會嘗試精確封存。其他情況只補送已保存資料，保持未封存。

可用 --demo-room 5 配合**新** --journal 路徑建立獨立合成示範：核心實際射擊兩次、命中兩次、擊殺一次，AI 命中一次；保存六份報告後 End 並退出，尚不送報告。再以同一 journal 執行恢復命令，會得到彈藥 2、擊殺 1、中彈 1、耗損 20、血量 80、命中率 100%。示範只操作自己新建的空閒房，明確標記 Simulation。

## 證據與限制

295 項核心檢查含 41 項管道／journal 檢查；302 項 HTTP 檢查實際啟動示範、保留一筆回應遺失前綴、重啟 API，再以另一個程序讀 journal、去重補送及封存。59 項 Chromium 檢查含結束後保留待確認場次、晚到數值與封存提示；另有 12 項回放資料檢查。

沒有 Unity／IL2CPP／頭盔運行結果，也沒有 25 台吞吐量、完整世界持久化或真正頭盔回放。Unity 伺服器不會以新世界恢復已 Running 的場次；補送工具恢復的是報告投遞，並非接續戰鬥。程序在 completion 前退出會留下尚未確認完整的歷史，須保留此狀態，不宣稱零損失或已完成全部任務需求。
