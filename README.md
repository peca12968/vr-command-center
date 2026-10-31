# VR Command Center

五房間、總計 25 人的 VR/MR 軍事戰鬥遊戲系統，目標支援 VIVE XR 與 Meta Quest 3。

依 2026-10-29 的使用者指示，**優先開發 Meta Quest 3**，暫以 Android 獨立執行為工作假設；VIVE 延後接入，共用架構與原始雙平台目標保留。

目前為 **API v0.29／Unity 遊戲端 v0.31.0 原型**。真正 Editor 已完成 Prepare、141 項 EditMode、同源 Windows 播放器及 ARM64／IL2CPP Quest APK。PC 已驗證 AI 傷害、射擊／擊殺／命中率、換彈／暫停、票券撤銷與重連；強制離線後保留已接受的位置、健康與彈藥，回放／報表一致。可用 [電腦練習場](docs/DESKTOP.md) 操作，重連與 Windows UDP 修正見 [RECONNECT](docs/RECONNECT.md)／[TRANSPORT_PATCH](docs/TRANSPORT_PATCH.md)。NGO protocol 29，所有遊戲 server／client 須一起更新。**使用者目前沒有頭盔，先繼續電腦端；沒有 Quest／VIVE 實機或 25 人完整驗收**。桌面頭手維持 Simulation，完整 11 項保持開發中。

新增[玩家參戰快照](docs/PLAYER_READINESS.md)：名冊直接顯示本次入場的有效姿態數與來源中斷／過期，不把頭盔分類當在線。真正雙PC退出、同ID換入場、新端恢復及控制台流程通過；這是Simulation快照觀察，實體安全與25台另驗。

新增[玩家任務簡報](docs/PLAYER_BRIEFING.md)：B開啟／翻頁、Escape關閉，完整10000字與繁中隨附字型；閱讀時抑制自己的武器輸入，頭手與全場計時繼續。真正雙PC按鍵、晚連線、原任務與封存戰績核對通過；Quest同源APK成功，實體控制器仍待驗。

新增[15分鐘PC驗證](docs/DESKTOP_LONG.md)與[封存失聯回歸](docs/SEAL_RECOVERY.md)：原入場與受傷狀態、完整回放及最終戰績一致；封存或統計暫時失聯時保留正確等待狀態。此為單玩家同機Simulation，完整25人／實機驗收仍待。

新增[計時失聯恢復驗證](docs/CLOCK_RECOVERY.md)：真正PC在管理與發布分別失聯後，停表／到期等待／補送及封存一致，60與180秒各8項；仍為同機Simulation，有界試跑不代表長期或實機驗收。

新增[任務活動倒數](docs/MISSION_CLOCK.md)：準備中明確選用到時結束，暫停停表；兩房PC已驗自動tick1200及手動超時、結果與封存回放一致。新envelope7讀1–7，不得降回舊reader；API／UI與遊戲端須一起更新。

新增[各玩家端接收狀態診斷](docs/DESKTOP_REPLICATION.md)：Linked及五獨立房各25個同機無圖形client、各60秒，22項檢查、280個同步快照及六場精確封存通過。舊128格driver重現112筆send queue full；server改1024、client仍128後，本輪原生日誌與56份完整報告皆0筆，同版未啟用探針的25人對照亦0筆。114真正EditMode及同源雙平台成功；這是有界的同機靜止Simulation負載，**完整網路／25台／實機驗收仍待**，原主迴圈停頓亦未證明修復。完整結果見PROGRESS。

新增[實際操作的25端對照](docs/DESKTOP_ACTIVE.md)：一位可見PC玩家以W／Space／R／Space前進0.05m、兩發命中／一擊殺／100%，24端接收；分批診斷9項、130快照及19916筆Running觀察列通過，966幀回放／CSV一致。首輪只看檢查點漏掉65筆暫時失效列，現已補全程條件並保留反例；不稱25人同時操作、根因已修復或實機驗收。

[電腦練習場入口](docs/DESKTOP.md)已接上目前API0.27及共用原生生命週期，拒絕過期receipt，支援明確SSD runtime、同房最多五個PC client、正常關窗／控制台End／到時封存，結束自動核對CSV。27項無圖形及9項真正視窗流程通過；這是同機Simulation，非25台或跨機驗收。

新增 [最終任務報表 CSV](docs/REPORTS.md)：結束並完成戰鬥精確封存後，可下載含離場玩家、原任務版本、Simulation／GameServer來源及封存序號的逐玩家數據。後端獨立檢查權限與完整性；下載不跨登入或場次。這是最終戰鬥 ledger，世界錄影完整性另有驗收，不代表頭盔／25台通過。

新增[玩家任務結束戰績](docs/DESKTOP_DEBRIEF.md)：combat及world都精確seal後，兩位PC玩家各自收到自己的最終數據，ack斷線後畫面保留；移除者與Ended票券收不到結果，Host等peer結束才shutdown。一般啟動器真正Space／封存／保留／Reconnect清除及新場取代舊結果已觀察；125 EditMode、36 Python、30練習場、49 UI native及8項原生票券重連回歸通過，零事件JSON反例已修正。來源仍Simulation，完整證據及限制見PROGRESS。

新增[End期間的網路故障回歸](docs/DESKTOP_END_NETWORK.md)：兩位真正PC client的已批准入場延遲、pending後全部下行loss，以及只丟較大datagram三場各6項、各37幀完整回放通過；正常peer仍取得自己的結果，故障者沒有誤確認final，Ended新票券拒絕。既有Unity0.29.0／NGO27正確處理選定情境，本輪不改遊戲協定或重建APK；45 Python通過，同機Simulation，不是跨機／25台驗收。

較窄的 [managed SDK 檢查](docs/UNITY_SDK_CHECK.md) 仍可補充 API／直接參考診斷，其本身不執行 Unity 或產出播放器；目前較強的真正 Editor、109 項測試及 binary 結果以 PROGRESS 為準。

新增 [玩家軍事人物](docs/PLAYER_BODY.md)：原創404面頭盔／背心／腿靴與桌面持槍雙臂，伺服器接受移動產生保存步態，PC遊戲、觀戰與回放共用；Tracked不合成握持雙臂，舊錄製保留原外觀。真正雙PC的W／Space／R、六張observer GPU、暫停及封存已核對；629核心、403 HTTP、43世界、58 Node／201 Chromium及47項UI／native通過。完整追蹤人物與動畫仍待。

新增 [玩家與敵軍射擊音效](docs/COMBAT_AUDIO.md)：原創固定PCM、保存事件槍口的空間聲音，Unity普通遊戲及瀏覽器觀戰／回放共用接受序號與時鐘；加入／跳轉／過期不補播，舊錄製保持無射擊聲。真正Space、AI、AudioListener非零與Pause／Resume靜音已量測；聲源不是原始音軌，人工聽感／頭盔仍待。音效當輪與最新回歸結果見PROGRESS。

目前版本的[雙玩家時序取證](docs/POSE_TIMING.md)新增外部唯讀CPU時間／週期取樣：一次三程序共同0.595秒主迴圈邊界空窗內，三者CPU計數在每對相鄰查詢都有週期增加，不支持整段全程停止；仍未識別主執行緒工作或底層根因。另一場零時間計數不能直接推成暫停。維持原門檻、沒有宣稱修復，Unity來源／既有雙平台不變，43項Python與兩場真正三發證據見PROGRESS。

新增 [兩端姿態時序診斷](docs/POSE_TIMING.md)：以有界記憶體記錄RPC呼叫／收件、主線程空窗及日誌／GPU擷取區段；歷史自然60秒、受控丟包與真正Space核對，能區分控制段收件空窗與玩家停頓。一般執行不啟用，原0.5秒規則不改；最新自然重現與獨立心跳證據見PROGRESS，根因仍待。

新增 [玩家射擊閃光與後座](docs/PLAYER_FIRE.md)：實際Space白天／夜間閃光及22mm槍身位移已由原生GPU核對，保存射線與封存事件精確一致；只動子槍身／彈匣，pointer與Tracked資料不改，原七profile保留。兩發扣彈／轉向／回放一致，音效另見COMBAT_AUDIO，玩家人物新增見PLAYER_BODY，完整動畫仍待。

新增 [敵軍射擊閃光與後座](docs/ENEMY_FIRE.md)：保存已接受的射擊原點／方向與tick，真正PC白天／夜間GPU脈衝及封存射線已核對；只移動槍身子Renderer，舊六profile保留。玩家效果另見PLAYER_FIRE，音效另見COMBAT_AUDIO。

新增 [敵軍雙手持槍](docs/ARMED_ENEMIES.md)：原創手槍與裝飾性兩節雙臂，槍口維持原權威原點，玩家、觀戰與回放共用；真正PC GPU與保存肘腕矩陣已核對，舊五個profile保留。閃光／後座與完整人物仍待。

新增 [換彈動作與桌面合成手套](docs/WEAPON_ACTIONS.md)：分離彈匣與手套依已保存的換彈時鐘重建，實際Space／R、換彈中Pause／Resume及30／89已驗；合成手套不改Tracked資料，舊錄製保留原外觀。

新增 [人形敵軍與保存姿態](docs/ENEMY_PRESENTATION.md)：原創頭盔／背心／四肢、權威朝向及依保存tick重建的步態，Windows玩家、即時觀戰與回放共用；暫停與跳轉還原同一姿勢，命中仍採原包圍盒。此舊profile保留原外觀；新持槍模型見ARMED_ENEMIES，完整動畫與玩家人物仍待。

新增 [玩家步槍](docs/SERVICE_RIFLE.md)：原創固定網格、真正槍口對齊與桌面持槍位置，玩家／觀戰／回放共用；正常PC視窗已實際完成瞄準、兩發命中／一擊殺／100%命中率及封存統計，舊錄製保留原外觀。人物及武器動畫仍待。

新增 [VR 場地配置檢查](docs/LAYOUT.md)：旋轉後越界、掩體重疊、出生點阻擋及初始敵軍容量可在編輯時預覽，後端會拒絕無效的新開場；草稿、歷史版本與已接受重試保留。

新 [軍事掩體素材](docs/FIELD_PROPS.md) 已接真正PC玩家、即時觀戰與封存回放，舊錄製保留原方盒；遊戲命中／碰撞仍採包圍盒。

可用 [控制台自訂電腦任務](docs/DESKTOP_CONTROL.md) 從編輯／保存／重載配置直接啟動真正 PC server／玩家，控制天氣、AI、觀戰與回放；已看見原生白天／雨夜／暫停畫面。最新47項 UI／native整合、58 Node＋201 Chromium通過；原生GPU聲光／自身DSP已驗證，實體聽感與頭盔仍待。

已完成 [電腦掩體碰撞](docs/DESKTOP_COLLISION.md)：真正鍵盤推沙包、退回、側移及旋轉油桶阻擋保持有效姿態；新增共用通行規則與原生操作檢查器。NGO版本以目前來源為準，所有遊戲程序須同版。

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
