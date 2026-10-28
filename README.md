# VR Command Center

五房間、總計 25 人的 VR/MR 軍事戰鬥遊戲系統，目標支援 VIVE XR 與 Meta Quest 3。

目前為 **v0.3 管理後端原型**。已提供主控／房間控制台權限、玩家名額、任務儲存、場次生命週期、環境／敵軍設定命令，以及包含控制台身分且可在重啟後重建狀態的事件紀錄。尚未交付頭盔遊戲端、戰鬥模擬、管理畫面、硬體控制、3D 觀戰或回放。`ViveXr`、`Quest3` 目前只是玩家裝置分類，不能作為實機相容證據。

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

## 啟動

需要 .NET SDK `10.0.400`（版本由 `global.json` 固定）。Windows 本機啟動助手需要 PowerShell 7。下列命令在專案根目錄執行：

```powershell
dotnet build VrCommand.slnx --configuration Release
dotnet run --project tests/VrCommand.Checks --configuration Release --no-build
.\scripts\start-local.ps1
```

啟動助手首次在 `data/operator-keys.local.json` 產生七份不同的隨機憑證，分別供主控、五房控制台與預留的遊戲伺服器使用；檔案已排除於 Git，畫面不輸出憑證。重新啟動沿用原檔。`GET http://127.0.0.1:5080/health` 無需登入；所有 `/api` 端點需帶 Bearer 憑證。這是本機控制台憑證機制，尚無人員帳號登入或實際頭盔驗證。其他部署方式見權限文件。

任務預設存於 API 專案的 `data/missions/`，可透過 `DataDirectory` 環境變數指定絕對路徑。場次事件預設位於任務目錄旁的 `sessions/`，亦可用 `SessionDataDirectory` 指定另一目錄；兩者不可相同，均已排除於 Git。場次、名冊、執行設定與命令去重紀錄會在重啟後恢復；結束後保留歷史並釋放房間。事件目錄限單一 API 程序寫入。任務時間目前不會自動結束場次。

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

腳本使用獨立的隨機測試憑證與暫存資料，驗證各角色與五房範圍、錯誤憑證設定拒絕啟動、換鑰、任務儲存、名額、狀態轉移、併發命令去重、版本衝突、單一寫入程序，以及兩次實際重啟後的活動／歷史場次恢復。最後關閉服務並清理測試資料。這不等同 25 台頭盔的連線效能驗收。

## 目錄

```text
src/VrCommand.Core/      任務與場次管理規則
src/VrCommand.Api/       ASP.NET Core 管理 API
tests/VrCommand.Checks/  無外部測試套件的核心規則驗證
scripts/                HTTP 整合驗證
examples/               可直接送入 API 的任務範例
docs/                   規格、開發路線、驗收與外部依賴
```

Unity 遊戲端將另建於 `clients/unity/`；目前尚未建立 Unity 專案，不能將 .NET 10 的後端組件直接當成 Unity 相容組件。
