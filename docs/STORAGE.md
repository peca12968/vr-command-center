# 事件儲存與升級 v0.4

API 預設使用 `SessionDataDirectory/events.db`，由獨立的 `VrCommand.Persistence` 專案負責。依賴 Microsoft.Data.Sqlite 10.0.14，版本及相依套件已鎖定於各專案的 `packages.lock.json`；首次還原需要 NuGet 網路連線。任務模板仍使用原本的獨立 JSON 檔案。

## 追加與復原

每個事件在一筆 SQLite 交易中驗證連續序號並插入一列。主鍵為場次 ID／序號，事件 ID 另有唯一約束；失敗交易不推進記憶體狀態。SQLite 使用 WAL 與 FULL synchronous；本版仍限制單一 API 程序持有事件目錄的 `.writer.lock`，不支援多個獨立管理程序同時維護同一館的記憶體狀態。

交易將多個資料庫操作作為同一個工作單元提交，依據 [Microsoft.Data.Sqlite 交易文件](https://learn.microsoft.com/en-us/dotnet/standard/data/sqlite/transactions)。連線使用私有預設快取，未將 shared cache 與 WAL 混用，見 [連線字串文件](https://learn.microsoft.com/en-us/dotnet/standard/data/sqlite/connection-strings)。

後端在儲存提交後才套用統計投影與場次狀態。事件清單採追加、控制命令與報告使用索引去重，統計增量更新；不會每次射擊重寫全部歷史或重算全部統計。服務啟動時讀取完整歷史並重建場次及統計，現階段仍將歷史載入記憶體；長期保留、快照、壓縮與批次寫入待正式場館效能測試後補齊。

資料庫 schema 目前為 user_version 1；事件 envelope 新增 schema 3，仍讀取既有 schema 1／2。未知版本、資料列與 envelope 身分不符、序號缺口、非法狀態轉移或未授權來源都會使啟動失敗，不清空資料重新開館。

## JSON 升級

首次建立 SQLite 儲存時，會讀取原事件目錄內 `{sessionId}.json`，先驗證所有場次及房間衝突，再於同一筆交易匯入並寫入完成標記。任一檔案錯誤會回滾整次匯入；修復來源檔案後可重新啟動重試。原始 JSON 不移動、不覆寫、不刪除，保留為升級備份。

完成標記寫入後，以 SQLite 為唯一權威來源，不會在每次重啟重新讀入舊 JSON。不要降版後繼續向同一目錄的舊 JSON 寫入新場次，再期待新版自動合併；這不是雙向同步工具。備份應在服務停止後保留完整事件目錄，或另建 SQLite 線上備份流程；不能在運行時只複製 `events.db` 而忽略 WAL。

核心內的 `FileSessionEventStore` 保留供舊 JSON 相容測試與匯入使用，其舊格式仍會重寫單一場次檔。HTTP 服務不使用該 adapter 接收新戰鬥事件。
