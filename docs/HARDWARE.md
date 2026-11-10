# 硬體介接準備

## 即時戰鬥回饋介面

Windows 管理包 0.31.27 提供 `GET /api/sessions/{sessionId}/rooms/{roomId}/hardware-feedback`。主控可選場次內任一房，房控憑證限本房。這個介面提供 `ShotFired` 與 `PlayerDamaged` 兩種已接受的遊戲事件，供房間轉接器開發與驗證。傳回事件、回報、玩家及當次入場識別，以及從零起算的席位、損傷量和接受時間。`combatOrigin` 保留原戰鬥來源。

初次連線及重連省略 `after`，服務回傳目前的 `throughSequence` 與空訊號清單。後續以 `?after=<throughSequence>` 續讀，每次使用回覆的 `throughSequence` 作下一次游標。以場次、房間、`streamId` 及 `runningSinceSequence` 確認來源，以 `eventId` 去重。

以下從管理服務所在電腦讀取房間 1。`$sessionId` 填入場次 UUID，`$headers` 使用該實例的主控或房間 1 Bearer 憑證。

```powershell
$feed = "http://127.0.0.1:5081/api/sessions/$sessionId/rooms/1/hardware-feedback"
$page = Invoke-RestMethod -Uri $feed -Headers $headers
# 場次有新動作後，使用本次回覆的序號讀取下一頁。
$page = Invoke-RestMethod -Uri "${feed}?after=$($page.throughSequence)" -Headers $headers
$page.signals
```

| 回覆 | 轉接器可採取的動作 |
| --- | --- |
| `resetReason: attached` | 從回覆序號建立新的讀取起點 |
| `resetReason: inactive` | 清空待處理訊號，使用回覆序號重新等待 |
| `resetReason: backlog` | 相差超過 256 筆時捨棄積壓，從回覆序號恢復 |
| `resetReason: null` | 逐筆核對本房設備綁定及 `admissionId`，再處理本頁訊號 |

只提供目前 Running 階段觀察到的事件，當次入場仍須存在於目前名冊。暫停及結束時回覆空訊號，繼續後會排除之前 Running 階段才觀察到的遲送回報。接受時間距服務檢查達 2 秒的事件會捨棄。`acceptedAtUtc` 是管理服務事件的時間，實際動作時間和設備端期限需由廠商轉接器定義。轉接器發現失聯、錯誤或來源切換時須清空自己的佇列，依設備文件確認安全停止。損傷量保留遊戲值，設備動作及強度映射留待廠商規格。

## 現況

硬體由外部公司負責，目前尚待技術資料或 SDK。模擬器 0.2.10 支援以下即時排演，以及[離線回饋模擬](HARDWARE_SIMULATOR.md)的事件重建、佇列、重送和到期測試。設備輸入、強度映射、實體停止及廠商協議列入後續實機驗收。

### 依現行名冊建立座位綁定

搭配管理包 0.31.61，房控可將設備與座位的對照轉為即時排演設定。每份清單只填一間房，座位從 0 起算。設備 ID 和座位在同一份清單中各只能出現一次，可選擇實際要排演的部分座位。

```json
{
  "version": 1,
  "managementUrl": "http://127.0.0.1:5081",
  "sessionId": "11111111-1111-4111-8111-111111111111",
  "roomId": 1,
  "mockPort": 19101,
  "seconds": 60,
  "devices": [{"seat": 0, "deviceId": "22222222-2222-4222-8222-222222222222"}]
}
```

設定本房的 `VR_COMMAND_ROOM_KEY` 後執行，使用新的輸出路徑。

```powershell
dotnet .\VrCommand.HardwareSimulator.dll --bind-room ..\room-1-seats.json --output ..\room-1.json
```

輸出的版本 2 即時設定包含每個座位目前的玩家與入場識別，並可直接交給下方的 `--live`。工具以 `?includeBindings=true` 取得同一房、同一回覆中的名冊與回饋游標。這個選項回傳版本 2 及本房的 `bindings`，舊設定沿用版本 1 回覆。

閘道在握手前、取用回饋時及確認批次時均核對當次綁定。若任一已配置座位的入場失效，閘道會關閉該房模擬連線，待確認批次記為 `cancelled`，報告記為 `binding-mismatch` 並回傳退出碼 1。核對座位後可重新產生設定並啟動。其他房間各自使用其設定及連線。

### 一次建立五房設備綁定

使用管理包 0.31.94 與模擬器 0.2.8。主控可為五個獨立場次或一個合併場次一次建立設定。輸入須列出房間 1 至 5、各房當前場次 UUID、不同的模擬 TCP 埠，以及每房 1 至 5 個已編列席位。各設備 ID 在五房間須唯一。

以下以五房合併為例。把 `$sessionId` 換成目前合併場次的 UUID。獨立模式用 `Independent`，各房填自己的場次 UUID。`seat` 從 0 起算。請把 UUID 對應到排演中實際要用的模擬設備。

```powershell
$sessionId = '11111111-1111-4111-8111-111111111111'
$rooms = foreach ($room in 1..5) {
    $devices = foreach ($seat in 0..4) {
        @{ seat = $seat; deviceId = [guid]::NewGuid().ToString('D') }
    }
    @{ roomId = $room; sessionId = $sessionId; mockPort = 19100 + $room; devices = @($devices) }
}
@{ version = 1; managementUrl = 'http://127.0.0.1:5081'; mode = 'Linked'; seconds = 60; rooms = @($rooms) } |
    ConvertTo-Json -Depth 5 | Set-Content -LiteralPath ..\venue-map.json -Encoding utf8NoBOM

$env:VR_COMMAND_MASTER_KEY = Read-Host '輸入主控金鑰' -MaskInput
try {
    dotnet .\VrCommand.HardwareSimulator.dll --bind-venue ..\venue-map.json --output ..\venue-bindings-run01
} finally {
    Remove-Item Env:VR_COMMAND_MASTER_KEY
}
```

輸出資料夾須為新路徑，父目錄須已存在。工具以主控身分讀取 `GET /api/venue/hardware-bindings` 的同一份五房名冊快照。五房都核對成功後才發布 `room-01.json` 至 `room-05.json` 以及記錄原場次和序號的 `venue-bindings.json`。任一房場次不符、席位缺人或資源重複時，不會發布資料夾。這一步不會啟動閘道。

每房排演仍用該房的 `VR_COMMAND_ROOM_KEY` 與對應的 `room-XX.json`。如果設定發布後入場名額被換掉，閘道會依版本 2 設定的入場核對停止或拒絕握手。

### 一次啟動與停止五房排演

使用 0.2.10 的 `--live-venue` 搭配原 `venue-bindings.json` 與同目錄的五房設定。先按各房設定啟動對應埠的本機模擬設備。執行指令的程序使用 `VR_COMMAND_ROOM_1_KEY` 至 `VR_COMMAND_ROOM_5_KEY`，各值為該房的房控憑證。每次指定新的輸出目錄和停止標記，兩者的父目錄都須存在。

```powershell
try {
    foreach ($room in 1..5) {
        Set-Item -Path "Env:VR_COMMAND_ROOM_${room}_KEY" -Value (Read-Host "房間 $room 控制金鑰" -MaskInput)
    }
    dotnet .\VrCommand.HardwareSimulator.dll --live-venue ..\venue\venue-bindings.json --output ..\rehearsal-01 --stop-file ..\rehearsal-01.stop
} finally {
    foreach ($room in 1..5) {
        Remove-Item -Path "Env:VR_COMMAND_ROOM_${room}_KEY" -ErrorAction SilentlyContinue
    }
}
```

在開始連接前，程序會核對五房設定、房控身分、現行入場與本機資源鎖。任何一房啟動檢查失敗時，整批拒絕。可在另一個終端使用 `--venue-status`，將 `--status-directory` 指向本次輸出目錄。要停止全部仍在排演的房間，在另一個終端以 `New-Item -ItemType File -Path ..\rehearsal-01.stop` 建立標記。

五房各有自己的連線、回饋游標與報告。運行中若一房入場失效，該房取消待確認批次並停止，其他房繼續排演。程序在各房結束後發布 `venue-report.json`，可從各房退出碼及報告確認結果。只有五房都符合原閘道的附掛與終止條件時，整批退出碼為 0。已確認的回饋數量和取消的批次請查各房報告。這個指令控制本機模擬閘道，遊戲場次照常由主控操作。

## 即時模擬閘道

解壓模擬器後，用 Python 3.12 開啟模擬設備。每房使用自己的程序和 TCP 埠，模擬連線固定使用本機 `127.0.0.1`。指定 `--room` 時，設備只接受該房握手。後續批次須符合握手房號及連線 ID 才會確認。

```powershell
python .\mock-device.py --room 1 --port 19101
```

可使用上節產生的版本 2 設定，或手動填寫以下版本 1 設定。將設定存到包外的 `room-1.json`。填入當前場次 UUID，從該房名冊取得玩家 `id`、`admissionId` 及從零起算的 `seat`。`deviceId` 由排演操作者指定，每個綁定各用一個 UUID。管理服務使用本機 HTTP 或遠端 HTTPS。

```json
{
  "version": 1,
  "managementUrl": "http://127.0.0.1:5081",
  "sessionId": "11111111-1111-4111-8111-111111111111",
  "roomId": 1,
  "mockPort": 19101,
  "seconds": 60,
  "bindings": [
    {"deviceId": "22222222-2222-4222-8222-222222222222", "playerId": "33333333-3333-4333-8333-333333333333", "admissionId": "44444444-4444-4444-8444-444444444444", "seat": 0}
  ]
}
```

在另一個 PowerShell 7 終端輸入對應房控金鑰，用 .NET 10 執行。每次使用新的輸出路徑。閘道會在場次結束或設定時間到達後寫出報告。

```powershell
$env:VR_COMMAND_ROOM_KEY = Read-Host '輸入本房控制金鑰' -MaskInput
try {
    dotnet .\VrCommand.HardwareSimulator.dll --live ..\room-1.json --output ..\room-1-report.json
} finally {
    Remove-Item Env:VR_COMMAND_ROOM_KEY
}
```

閘道每次只處理一批，最多 32 個訊號。模擬設備須回覆同一連線 ID 和批次 ID。等待回覆期間及收到回覆後都會向管理服務核對原訊號、Running 階段、現行入場及兩秒期限。如果管理狀態先使批次失效，閘道會取消該批並關閉原連線。錯誤、逾時或斷線的批次會記下個別狀態，重新握手後從目前序號開始。成功狀態為 `simulated-acknowledged`。報告的 `acknowledged` 是成功確認的模擬訊號數，`physicalDeliveryConfirmed` 固定為 `false`。

### 查看排演中的閘道狀態

在已設定本房金鑰的終端加入 `--status`。這個選項可與 `--stop-file` 一起使用。

```powershell
dotnet .\VrCommand.HardwareSimulator.dll --live ..\room-1.json --output ..\room-1-report.json --status
```

終端會在狀態或計數變動時輸出一行 `kind` 為 `gateway-status` 的版本 1 JSON，包含房號、觀察時間、程序內序號與累計計數。

| 狀態 | 操作者看到的進度 |
| --- | --- |
| `checking-management`、`waiting-mission`、`waiting-source` | 正在核對管理服務，或等待任務和戰鬥來源 |
| `paused` | 任務已暫停，閘道未連接模擬設備 |
| `connecting`、`active` | 正在握手，或已握手並接上本房回饋來源 |
| `awaiting-ack` | 批次等候確認，`acknowledged` 只計入已核對的模擬訊號 |
| `mock-unavailable`、`management-unavailable` | 模擬連線或管理讀取發生錯誤，`fault` 可顯示模擬斷線、逾時或無效回覆 |
| `stopped` | 終止原因已確定，報告檔已寫出並關閉 |

沒有看到 `stopped` 時，請核對程序退出碼和報告。指定 `--status` 時，原結束摘要仍會接在狀態列後面。程式讀取時可用 `kind` 區分兩者。狀態不含金鑰、位址或玩家識別，`physicalDeliveryConfirmed` 固定為 `false`。

### 查看五房排演狀態

使用模擬器 0.2.9。每次排演先建立專用的本機狀態目錄，五房啟動時都加上同一個 `--status-directory`。每房仍使用自己的房控金鑰和新的報告路徑。狀態檔在狀態變更或閘道迴圈中每隔約 500 毫秒以原子替換更新。正常結束時，先寫完報告，再發布終止狀態。

```powershell
dotnet .\VrCommand.HardwareSimulator.dll --live ..\venue\room-01.json --output ..\room-01-report.json --status-directory ..\venue-status
dotnet .\VrCommand.HardwareSimulator.dll --venue-status ..\venue\venue-bindings.json --status-directory ..\venue-status
```

第二行只讀本機檔案，無須金鑰。可重複執行以取得最新快照。每房依原場次 UUID 及房號核對，`current` 的 `progress.phase` 顯示閘道正在等待、連線、模擬確認或發生故障。超過三秒未更新的執行中狀態會顯示 `stale`，隱藏該房上次的模擬確認計數。未發布狀態顯示 `waiting`，房號或場次不合顯示 `mismatch`，損壞或未來時間顯示 `invalid`。`stopped` 可查最後計數及停止原因。重啟同房後會換新的 `runId` 並重算計數。這些狀態記錄的是本機模擬，`physicalDeliveryConfirmed` 固定為 `false`。

### 同房閘道的互斥與重新啟動

模擬器 0.2.4 在同一台電腦、同一作業系統帳戶下，對每個場次及房間只允許一個即時閘道。版本 1 與版本 2 設定共用該鎖定。即使使用不同設定檔、模擬設備埠或報告路徑，第二個程序仍會在設備握手前退出，回傳退出碼 1 並顯示 `GatewayLeaseUnavailable`。若看見此訊息，請先確認原程序是否還在執行，以及本機應用程式資料夾 `VrCommand/HardwareGatewayLeases` 是否可寫入。

原程序正常停止或意外退出時，由作業系統釋放鎖定。可使用新的報告路徑重啟該房。重啟從當前游標開始，跳過舊批次及離線期間的回饋。鎖定檔會保留供下一次啟動使用。其他房間可同時排演。跨電腦、跨帳戶的協調及實體設備停止列入廠商介接驗收。

### 五房資源互斥

同一台電腦、同一帳戶的閘道均使用 0.2.5 時，啟動還會取得該模擬 TCP 埠及所有已配置設備 ID 的鎖定。不同房間或場次使用相同資源，會在模擬連線前以退出碼 1 拒絕，並釋放本次已取得的鎖定。原閘道繼續運作。

| 診斷 | 排查項目 |
| --- | --- |
| `MockPortLeaseUnavailable` | 核對其他運作中閘道的模擬 TCP 埠 |
| `DeviceLeaseUnavailable` | 核對其他運作中閘道綁定的模擬設備 ID |

### 暫停與繼續模擬連線

0.2.6 可先啟動閘道等候。閘道在任務進入執行中且有戰鬥來源後才開始模擬握手。每條連線只用於同一段執行期間與戰鬥來源。收到暫停狀態後，即使沒有待確認的批次，閘道也會關閉該連線。暫停時保留本機鎖定，繼續後重新握手並從當前游標開始。

握手回覆抵達時，閘道會再核對場次。若期間已暫停並繼續，原連線會關閉，並使用新連線重新附掛。可在模擬設備 `--manual` 模式收到 `hello` 時輸入 `ready-observe-close`，送出握手確認後觀察沒有批次時的關線。上述行為適用於本機模擬連線。廠商設備的實體停止程序仍需依廠商協議驗證。

### 停止單房模擬閘道

啟動時在原指令後加上 `--stop-file 'C:\VRCommand\rehearsal\room-1-run-01.stop'`。每次排演和每房都用不同路徑。標記檔要放在已存在的本機資料夾中，啟動前該檔必須尚未建立，並與設定檔及報告分開。

要停止時，在另一個終端建立空白標記檔。

```powershell
New-Item -ItemType File -Path 'C:\VRCommand\rehearsal\room-1-run-01.stop'
```

閘道約每 150 毫秒檢查標記。看到標記後關閉自己的模擬連線並保留標記檔。尚未完成確認的批次記為 `cancelled`。程序結束後，從報告查看 `termination: operator-stop`。已成功連到該房回饋來源時回傳退出碼 0，握手或附掛未完成時回傳 1。這項操作只控制指定的本機模擬閘道。

故障排演可在模擬設備加入 `--manual`，收到畫面上的訊息後輸入 `ack`、`wrong`、`timeout` 或 `drop`。要觀察單房停止、暫停、結束及程序中斷，可輸入 `observe-close`。設備會保留 ACK 並等待原連線關閉，輸出連線與批次 ID，以及 `eof` 或 `reset`。排演協議以四位元組大端長度加 UTF-8 JSON 傳輸，使用 `hello`／`ready` 和 `feedback`／`ack`。廠商實體設備採用其後續提供的協議。

## 廠商需提供

1. 設備清單、型號、韌體、每房數量，以及設備／房間／玩家如何對應。
2. 傳輸方式：USB、Serial、TCP、UDP、BLE、HTTP、MQTT 或廠商 SDK；作業系統與架構支援。
3. 封包格式、單位、座標系、時間戳、校驗碼、命令編號及版本相容規則。
4. 輸入事件：觸發、換彈、感測、中彈、定位、按鈕等；事件頻率、序號及重送行為。
5. 輸出命令：回饋、燈光、震動等；範圍限制、確認回覆、逾時、取消與停止方式。
6. 配對、授權、裝置身分與憑證管理；斷線重連、重複封包及錯誤碼範例。
7. 測試工具、模擬器、實機測試設備、SDK 授權與可供開發人員使用的文件。

## 預定閘道責任

每房使用獨立設備閘道，將廠商格式轉換成版本化事件。事件至少包含 `eventId`、`deviceId`、`roomId`、`playerId`、`kind`、`sequence`、`occurredAtUtc` 及 `payload`；實際欄位以協議確認後固定。閘道處理心跳、事件去重、連線狀態、逾時及命令確認，遊戲伺服器負責決定事件對遊戲狀態的影響。

斷線或場次結束時，輸出回到設備文件定義的停止狀態；不能假設軟體停止可取代實體設備控制。模擬器須包含重送、亂序、斷線、過期命令與設備換綁場景。實機驗收應記錄封包、時間與對應遊戲事件，避免僅以 UI 顯示成功判定整合完成。
