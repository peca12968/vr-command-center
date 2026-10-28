# VR Command Center

五房間、總計 25 人的 VR/MR 軍事戰鬥遊戲系統，目標支援 VIVE XR 與 Meta Quest 3。

依 2026-10-29 的使用者指示，**優先開發 Meta Quest 3**，暫以 Android 獨立執行為工作假設；VIVE 延後接入，共用架構與原始雙平台目標保留。

目前為 **v0.5 後端與 Quest 3 接入來源碼原型**。後端已有五房權限、場次、SQLite 事件、戰鬥統計與短效玩家票券；Unity 工程已有共同場景生成、頭手姿態與管理狀態同步程式。Unity 編輯器已安裝，但實際 Prepare 因尚無有效授權而退出，尚無成功編譯或 APK；沒有實機相容證據。實際射擊／AI、管理畫面、硬體控制與 3D 觀戰回放仍待開發。

## 開發位置

- GitHub：<https://github.com/peca12968/vr-command-center>（私人）
- 本機：`F:\Projects\vr-command-center`
- 長期目標與階段驗收：[ROADMAP.md](docs/ROADMAP.md)
- 原始需求追蹤：[REQUIREMENTS.md](docs/REQUIREMENTS.md)
- 架構與雙平台策略：[ARCHITECTURE.md](docs/ARCHITECTURE.md)
- 本次進度與接續工作：[PROGRESS.md](docs/PROGRESS.md)
- 硬體對接資料清單：[HARDWARE.md](docs/HARDWARE.md)
- API：[API.md](docs/API.md)
- 場次與事件契約：[SESSION_PROTOCOL.md](docs/SESSION_PROTOCOL.md)
- 控制台身分與權限：[AUTHORIZATION.md](docs/AUTHORIZATION.md)
- 戰鬥事件與統計：[COMBAT_PROTOCOL.md](docs/COMBAT_PROTOCOL.md)
- SQLite 儲存與升級：[STORAGE.md](docs/STORAGE.md)
- Quest 3 工程、建置與待驗操作：[QUEST3.md](docs/QUEST3.md)

## 啟動

需要 .NET SDK `10.0.400`（版本由 `global.json` 固定）及首次 NuGet 還原的網路連線。Windows 本機啟動助手需要 PowerShell 7。下列命令在專案根目錄執行：

```powershell
dotnet restore VrCommand.slnx --locked-mode
dotnet build VrCommand.slnx --configuration Release --no-restore
dotnet run --project tests/VrCommand.Checks --configuration Release --no-build
.\scripts\start-local.ps1
```

啟動助手首次在 `data/operator-keys.local.json` 產生七份不同的隨機憑證，分別供主控、五房控制台與遊戲事件來源使用；檔案已排除於 Git，畫面不輸出憑證。重新啟動沿用原檔。`GET http://127.0.0.1:5080/health` 無需登入；所有 `/api` 端點需帶 Bearer 憑證。頭盔設定使用另行配發的短效玩家票券，不含上述憑證；尚無人員帳號登入或實際頭盔驗證。其他部署方式見權限文件。

任務預設存於 API 專案的 `data/missions/`，可用 `DataDirectory` 指定絕對路徑。場次事件預設位於旁邊的 `sessions/events.db`，亦可用 `SessionDataDirectory` 指定另一目錄；兩者不可相同，均已排除於 Git。舊 JSON 場次會驗證後一次匯入，原檔保留。場次、名冊、執行設定、去重及統計會在重啟後恢復；結束後保留歷史並釋放房間。事件目錄限單一 API 程序寫入。任務時間目前不會自動結束場次。

## 操作範例

另開 PowerShell，在專案根目錄執行：

```powershell
$baseUrl = 'http://127.0.0.1:5080'
$keys = (Get-Content -LiteralPath data/operator-keys.local.json -Raw | ConvertFrom-Json).OperatorKeys
$headers = @{ Authorization = 'Bearer ' + $keys.Master }
$body = Get-Content -LiteralPath examples/mission.json -Raw -Encoding utf8
$mission = Invoke-RestMethod "$baseUrl/api/missions" -Headers $headers -Method Post -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body))
$sessionRequest = @{ missionId = $mission.id; mode = 'Linked'; roomIds = @(1,2,3,4,5) } | ConvertTo-Json
$session = Invoke-RestMethod "$baseUrl/api/sessions" -Headers $headers -Method Post -ContentType application/json -Body $sessionRequest
Invoke-RestMethod "$baseUrl/api/rooms" -Headers $headers
```

`Independent` 每次指定一個房間；可同時建立五場。`Linked` 必須指定全部五個房間，且全部空閒。每房最多五人是初始設計假設，可於後續需求確認後調整；總上限維持 25 人。

建立場次後狀態為 `Preparing`，至少加入一名玩家後才能發送 `Begin`。以下接續上例：

```powershell
$player = @{ playerId = [guid]::NewGuid().ToString(); name = 'Alpha'; roomId = 1; headset = 'Quest3' } | ConvertTo-Json
$session = Invoke-RestMethod "$baseUrl/api/sessions/$($session.id)/players" -Headers $headers -Method Post -ContentType application/json -Body $player
$command = @{ commandId = [guid]::NewGuid().ToString(); action = 'Begin'; expectedSequence = $session.sequence } | ConvertTo-Json
$receipt = Invoke-RestMethod "$baseUrl/api/sessions/$($session.id)/commands" -Headers $headers -Method Post -ContentType application/json -Body $command
$receipt.session
```

命令回應遺失時重送相同 `commandId` 與相同內容；伺服器回覆原始接受序號及最新狀態，不會再次套用命令。修改命令內容須使用新的 ID。這個契約適用於 `/commands`；建立場次與加入／離開的舊操作尚未支援呼叫端指定去重 ID。

## HTTP 整合驗證

需要 Python 3.12 以上，使用標準函式庫，不需安裝套件：

```powershell
python scripts/smoke_api.py
```

腳本使用隨機測試憑證及暫存資料，驗證權限、名額、場次狀態、去重、SQLite 交易儲存、戰鬥因果、玩家票券及設定產生，並兩次實際重啟 API 驗證復原。核心檢查另包含 JSON 升級、回滾、資料損壞及五房 25 個玩家的模擬統計。目前 128 項核心檢查、229 項 HTTP 斷言通過；這不等同 Unity 編譯或 25 台頭盔連線效能驗收。

本機 API 啟動後，也可在空閒房間執行一場明確標記的模擬紀錄：

```powershell
python scripts/demo_combat.py --room 1
```

預期輸出：使用彈藥 3、命中率 66.67%、擊殺 1、中彈 1、耗損 20、血量 80。腳本只結束自己建立的場次，並保留歷史供查閱；它不連接頭盔或硬體。

## 目錄

```text
src/VrCommand.Core/      任務與場次管理規則
src/VrCommand.Persistence/ SQLite 交易式事件儲存
src/VrCommand.Api/       ASP.NET Core 管理 API
clients/unity/          Quest 3 Unity 來源碼工程
tests/VrCommand.Checks/  無外部測試套件的核心規則驗證
scripts/                HTTP 整合驗證
examples/               可直接送入 API 的任務範例
docs/                   規格、開發路線、驗收與外部依賴
```

Unity 工程固定 Editor 6000.3.27f1，使用獨立 JSON 契約，不引用 .NET 10 後端組件。建置工具、授權依賴與未驗證步驟見 [QUEST3.md](docs/QUEST3.md)。
