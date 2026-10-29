# VR Command Center

五房間、總計 25 人的 VR/MR 軍事戰鬥遊戲系統，目標支援 VIVE XR 與 Meta Quest 3。

依 2026-10-29 的使用者指示，**優先開發 Meta Quest 3**，暫以 Android 獨立執行為工作假設；VIVE 延後接入，共用架構與原始雙平台目標保留。

目前為 **API v0.19／Unity 遊戲端 v0.21 原型**。真正 Editor 已完成 Prepare、56 項 EditMode、同源 Windows 播放器及 ARM64／IL2CPP Quest APK。PC 已驗證 AI 傷害、射擊／擊殺／命中率、換彈／暫停、票券撤銷與重連；強制離線後保留已接受的位置、健康與彈藥，回放／報表一致。可用 [電腦練習場](docs/DESKTOP.md) 操作，重連與 Windows UDP 修正見 [RECONNECT](docs/RECONNECT.md)／[TRANSPORT_PATCH](docs/TRANSPORT_PATCH.md)。NGO protocol 20，所有遊戲 server／client 須一起更新。**使用者目前沒有頭盔，先繼續電腦端；沒有 Quest／VIVE 實機或 25 人驗收**。桌面頭手維持 Simulation，完整 11 項保持開發中。

較窄的 [managed SDK 檢查](docs/UNITY_SDK_CHECK.md) 仍可補充 API／直接參考診斷，其本身不執行 Unity 或產出播放器；目前較強的真正 Editor、56 項測試及 binary 結果以 PROGRESS 為準。

新增 [玩家步槍](docs/SERVICE_RIFLE.md)：原創固定網格、真正槍口對齊與桌面持槍位置，玩家／觀戰／回放共用；正常PC視窗已實際完成瞄準、兩發命中／一擊殺／100%命中率及封存統計，舊錄製保留原外觀。人物及武器動畫仍待。

新增 [VR 場地配置檢查](docs/LAYOUT.md)：旋轉後越界、掩體重疊、出生點阻擋及初始敵軍容量可在編輯時預覽，後端會拒絕無效的新開場；草稿、歷史版本與已接受重試保留。

新 [軍事掩體素材](docs/FIELD_PROPS.md) 已接真正PC玩家、即時觀戰與封存回放，舊錄製保留原方盒；遊戲命中／碰撞仍採包圍盒。

可用 [控制台自訂電腦任務](docs/DESKTOP_CONTROL.md) 從編輯／保存／重載配置直接啟動真正 PC server／玩家，控制天氣、AI、觀戰與回放；已看見原生白天／雨夜／暫停畫面。最新39項 UI／native整合、27 Node＋162 Chromium通過；原生GPU聲光／自身DSP已驗證，實體聽感與頭盔仍待。

已完成 [電腦掩體碰撞](docs/DESKTOP_COLLISION.md)：真正鍵盤推沙包、退回、側移及旋轉油桶阻擋保持有效姿態；新增共用通行規則與原生操作檢查器。NGO 20 須所有遊戲程序同版。

觀戰新增 [精確位置與角度控制](docs/OBSERVER_CAMERA.md)：可輸入看向座標、水平／俯視角及距離，搭配拖曳、縮放與保存書籤。真正 PC 錄製的自訂視角保存／封存回放已驗證；觀戰瀏覽器仍為軟體 WebGL。

已新增 [原生天氣聲光量測](docs/NATIVE_WEATHER.md)：可擷取真正Windows玩家的閃電畫面與自身音訊混音，確認雨雷輸出及暫停靜音；不代表實體聽感或頭盔驗收。

新增 [軍事戰鬥HUD](docs/TACTICAL_HUD.md)：血量條、彈匣／備彈、場地方位與受掩體遮擋限制的敵我標記。真正鍵盤射擊／換彈／轉向、受傷暫停與淘汰已驗證，3D場景及角色美術仍在後續階段。

## 開發位置

已新增 [五房電腦場館](docs/DESKTOP_VENUE.md)：五個真正 Windows server／每房一個 client 同時獨立、單房結束與重用、全部封存後另開 Linked，回放統計一致。這是在明確 SSD runtime 配置下的本機 Simulation；F 槽 USB 硬碟全資料配置未達原新鮮度門檻，程式碼與建置仍在 F 槽。完整證據見 PROGRESS，仍無 25 台或頭盔驗收。

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
- 瀏覽器主控台與任務配置：[CONSOLE.md](docs/CONSOLE.md)
- 任務修訂、歷史及升級：[MISSION_VERSIONS.md](docs/MISSION_VERSIONS.md)
- 共用射擊／AI 核心與幾何模擬：[SIMULATION.md](docs/SIMULATION.md)
- Quest 戰鬥接入、輸入及驗證邊界：[GAMEPLAY.md](docs/GAMEPLAY.md)
- 持久事件、結束封存與補送工具：[TELEMETRY.md](docs/TELEMETRY.md)
- 3D 模擬回放與自由鏡頭：[REPLAY.md](docs/REPLAY.md)
- 持久世界／即時觀戰與補送：[WORLD_RECORDING.md](docs/WORLD_RECORDING.md)
- 共用來源、Unity 頭手與補送：[WORLD_SOURCE.md](docs/WORLD_SOURCE.md)
- 每次入場、票券 v2 與舊連線撤銷：[ADMISSION.md](docs/ADMISSION.md)

## 啟動

需要 .NET SDK `10.0.400`（版本由 `global.json` 固定）及首次 NuGet 還原的網路連線。Windows 本機啟動助手需要 PowerShell 7。下列命令在專案根目錄執行：

```powershell
dotnet restore VrCommand.slnx --locked-mode
dotnet build VrCommand.slnx --configuration Release --no-restore
dotnet run --project tests/VrCommand.Checks --configuration Release --no-build
.\scripts\start-local.ps1
```

啟動後開啟 **http://127.0.0.1:5080/console/**，以單一 Master 或所屬房間憑證登入。任務儲存後可選取開局；畫面中的人數是名冊，不代表頭盔在線。操作與驗證見 [CONSOLE.md](docs/CONSOLE.md)。

若主控台正在執行，Windows 可能鎖住使用中的 DLL；繼續開發時採用 [隔離輸出建置](docs/SIMULATION.md#隔離建置與驗證)，可保持原服務執行。

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

命令回應遺失時重送相同 `commandId` 與相同內容；伺服器回覆原始接受序號及最新狀態，不會再次套用命令。修改命令內容須使用新的 ID。建立場次與加入／離開另支援 `Idempotency-Key` 標頭，瀏覽器會保留原 key 與內容供重試；不帶 key 的舊客戶端仍無重試保證。細節見 `SESSION_PROTOCOL.md`。

## HTTP 整合驗證

需要 Python 3.12 以上，使用標準函式庫，不需安裝套件：

```powershell
python scripts/smoke_api.py
python scripts/smoke_world.py
```

腳本使用隨機測試憑證及暫存資料，驗證權限、名額、場次狀態、去重、SQLite 儲存、戰鬥因果、票券及幾何模擬接入，並多次實際重啟 API。另有任務／連線／戰鬥接入、回放資料與瀏覽器 WebGL 檢查。後端、瀏覽器與原生各版的執行結果及範圍分別記於 PROGRESS，不將歷史或不同平台測試加總為本輪結果。C# 語法／SDK 型別檢查不能替代真正 Editor、原生執行或 25 台頭盔效能驗收。

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
src/VrCommand.Api/wwwroot/console/ 瀏覽器主控台與平面配置器
src/VrCommand.Simulation/ 同源核心的 .NET Standard 建置入口
clients/unity/          Quest 3 Unity 來源碼工程
clients/unity/Packages/com.vrcommand.simulation/ 共用射擊／AI 核心來源
tools/VrCommand.SimulationDemo/ 幾何模擬與 HTTP 統計接入示範
tests/VrCommand.Checks/  無外部測試套件的核心規則驗證
tests/browser/          Chromium 與實際 API 的操作驗證
scripts/                HTTP 整合驗證
examples/               可直接送入 API 的任務範例
docs/                   規格、開發路線、驗收與外部依賴
```

Unity 工程固定 Editor 6000.3.27f1，使用獨立 JSON 契約，不引用 .NET 10 後端組件。建置工具、授權依賴與未驗證步驟見 [QUEST3.md](docs/QUEST3.md)。
