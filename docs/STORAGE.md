# 任務、事件儲存與升級 v0.15

v0.15 任務庫新增 DataDirectory/missions.db（獨立 schema 1）及 writer lease，原 GUID.json 在單一交易內匯入為各自第 1 版，之後以 SQLite 為權威來源。保存 request／作者／不可變版本與線性前置版本同交易，舊 JSON 保留備份，不再由 API 寫入；不可混用舊 API 或直接降版。完整保存 root data 及實際 API data／WAL，見 [MISSION_VERSIONS.md](MISSION_VERSIONS.md)。場次 envelope 6、events.db／worlds.db schema 1 及 NGO protocol 14 不變。

v0.14 session envelope 升 6，PlayerJoined 保存 admissionId=EventId，PlayerLeft 保存 admission 與原始 fence，讀取 1–5 會從舊加入 EventId 推導穩定識別。DB schema 不變，但寫入後不可降回舊 event reader；舊 v1 票券失效須重發。備份後協同升級 API／控制台／GameServer，見 ADMISSION.md。

v0.13 header 新增選用 UTC 擷取基準與 capturedAtUtc metadata，舊無時間 header 可讀／原樣去重；DB schema 不變，但 v0.12 的嚴格 reader 不接受新欄位，寫入後不可直接降版。完整備份後再一同升級來源、API 與主控台。來源 binary journal 及 ack 規範見 WORLD_SOURCE.md。

v0.12 另在相同 SessionDataDirectory 新增 worlds.db（schema 1），以交易保存逐幀世界／統計並以時間索引播放。管理 events.db 的 schema 與 envelope 5 不變；完整備份需包含兩個資料庫及來源檔，詳見 [WORLD_RECORDING.md](WORLD_RECORDING.md)。

v0.11 新事件 schema 5，戰鬥來源／觀察位置／有序報告及封存各以事件保存，仍讀取 1–4，資料庫結構 user_version 不變。每筆有序報告單獨交易；批次失敗可能已有前綴，原樣重試去重續送。主控台以 pendingTelemetry 區分已 End 但尚未 seal 的統計。

遊戲伺服器另有獨占開啟、checksummed frame 及 Flush 的本地 journal，與 API SQLite 分開保存，格式及補送見 TELEMETRY。兩者先後提交依靠穩定 reportId／順序與 acknowledgment 恢復，不宣稱跨檔案／跨程序原子交易。

API 預設使用 `SessionDataDirectory/events.db`，由獨立的 `VrCommand.Persistence` 專案負責。依賴 Microsoft.Data.Sqlite 10.0.14，版本及相依套件已鎖定於各專案的 `packages.lock.json`；首次還原需要 NuGet 網路連線。任務由同專案的 SqliteMissionLibrary 管理 DataDirectory/missions.db，既有 JSON 僅作一次匯入來源及保留備份。

## 追加與復原

每個事件在一筆 SQLite 交易中驗證連續序號並插入一列。主鍵為場次 ID／序號，事件 ID 另有唯一約束；失敗交易不推進記憶體狀態。SQLite 使用 WAL 與 FULL synchronous；本版仍限制單一 API 程序持有事件目錄的 `.writer.lock`，不支援多個獨立管理程序同時維護同一館的記憶體狀態。

交易將多個資料庫操作作為同一個工作單元提交，依據 [Microsoft.Data.Sqlite 交易文件](https://learn.microsoft.com/en-us/dotnet/standard/data/sqlite/transactions)。連線使用私有預設快取，未將 shared cache 與 WAL 混用，見 [連線字串文件](https://learn.microsoft.com/en-us/dotnet/standard/data/sqlite/connection-strings)。

後端在儲存提交後才套用統計投影與場次狀態。事件清單採追加、控制命令與報告使用索引去重，統計增量更新；不會每次射擊重寫全部歷史或重算全部統計。服務啟動時讀取完整歷史並重建場次及統計，現階段仍將歷史載入記憶體；長期保留、快照、壓縮與批次寫入待正式場館效能測試後補齊。

資料庫 schema 目前為 user_version 1；新事件 envelope 為 schema 5，仍讀取既有 schema 1–4。Created／PlayerJoined／PlayerLeft 的 requestId 隨同一筆事件原子提交，不另寫容易不同步的去重檔；啟動重建跨場次索引。未知版本、重複 requestId、資料列與 envelope 身分不符、序號缺口、非法狀態轉移或未授權來源都會使啟動失敗，不清空資料重新開館。

新 PlayerLeft 保留當時玩家房間，schema 4 恢復時須符合前一名冊。舊事件沒有 requestId 或 roomId 仍按其原版本解讀，不補造去重證據。寫入 schema 5 後舊版不認識此版本，不能直接降版；升級前應先備份完整資料目錄。

## JSON 升級

首次建立 SQLite 儲存時，會讀取原事件目錄內 `{sessionId}.json`，先驗證所有場次及房間衝突，再於同一筆交易匯入並寫入完成標記。任一檔案錯誤會回滾整次匯入；修復來源檔案後可重新啟動重試。原始 JSON 不移動、不覆寫、不刪除，保留為升級備份。

完成標記寫入後，以 SQLite 為唯一權威來源，不會在每次重啟重新讀入舊 JSON。不要降版後繼續向同一目錄的舊 JSON 寫入新場次，再期待新版自動合併；這不是雙向同步工具。備份應在服務停止後保留完整事件目錄，或另建 SQLite 線上備份流程；不能在運行時只複製 `events.db` 而忽略 WAL。

核心內的 `FileSessionEventStore` 保留供舊 JSON 相容測試與匯入使用，其舊格式仍會重寫單一場次檔。HTTP 服務不使用該 adapter 接收新戰鬥事件。
