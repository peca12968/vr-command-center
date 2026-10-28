# VR Command Center

五房間、總計 25 人的 VR/MR 軍事戰鬥遊戲系統，目標支援 VIVE XR 與 Meta Quest 3。

目前為 **v0.1 管理後端原型**。已提供房間與玩家名額管理、任務設定儲存及 REST API；尚未交付頭盔遊戲端、戰鬥模擬、管理畫面、硬體控制、3D 觀戰或回放。`ViveXr`、`Quest3` 目前只是玩家裝置分類，不能作為實機相容證據。

## 開發位置

- GitHub：<https://github.com/peca12968/vr-command-center>（私人）
- 本機：`F:\Projects\vr-command-center`
- 長期目標與階段驗收：[ROADMAP.md](docs/ROADMAP.md)
- 原始需求追蹤：[REQUIREMENTS.md](docs/REQUIREMENTS.md)
- 架構與雙平台策略：[ARCHITECTURE.md](docs/ARCHITECTURE.md)
- 本次進度與接續工作：[PROGRESS.md](docs/PROGRESS.md)
- 硬體對接資料清單：[HARDWARE.md](docs/HARDWARE.md)
- API：[API.md](docs/API.md)

## 啟動

需要 .NET SDK `10.0.400`（版本由 `global.json` 固定）。下列命令在專案根目錄執行：

```powershell
dotnet build VrCommand.slnx --configuration Release
dotnet run --project tests/VrCommand.Checks --configuration Release --no-build
dotnet run --project src/VrCommand.Api --configuration Release --no-build -- --urls http://127.0.0.1:5080
```

`GET http://127.0.0.1:5080/health` 回傳服務狀態。這是本機開發 API，尚無登入與角色授權；目前僅綁定 loopback 使用。正式部署及房間控制台接入前須完成角色、裝置身分、傳輸保護與稽核。

任務預設存於 API 專案的 `data/missions/`，已排除於 Git。可透過 `DataDirectory` 環境變數指定絕對路徑。場次與玩家名冊目前僅存記憶體，服務重啟會清空；任務會保留。任務時間是設定欄位，目前不會自動結束場次。

## 操作範例

另開 PowerShell，在專案根目錄執行：

```powershell
$baseUrl = 'http://127.0.0.1:5080'
$body = Get-Content -LiteralPath examples/mission.json -Raw -Encoding utf8
$mission = Invoke-RestMethod "$baseUrl/api/missions" -Method Post -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body))
$sessionRequest = @{ missionId = $mission.id; mode = 'Linked'; roomIds = @(1,2,3,4,5) } | ConvertTo-Json
$session = Invoke-RestMethod "$baseUrl/api/sessions" -Method Post -ContentType application/json -Body $sessionRequest
Invoke-RestMethod "$baseUrl/api/rooms"
```

`Independent` 每次指定一個房間；可同時建立五場。`Linked` 必須指定全部五個房間，且全部空閒。每房最多五人是初始設計假設，可於後續需求確認後調整；總上限維持 25 人。

## HTTP 整合驗證

需要 Python 3.12 以上，使用標準函式庫，不需安裝套件：

```powershell
python scripts/smoke_api.py
```

腳本啟動獨立的本機 API、使用測試資料目錄，驗證任務儲存、HTTP 錯誤碼、五房間連線名額及場次結束後釋放，最後關閉服務並清理測試資料。這不等同 25 台頭盔的連線效能驗收。

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
