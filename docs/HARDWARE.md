# 硬體介接準備

## 房間環境狀態

控制台 0.31.293 的主控可在「五房硬體模擬排演報告」按「下載目前五房環境設定」，取得帶有取樣時間的 JSON。場館整合程式可使用主控憑證呼叫 `GET /api/venue/hardware-environment`。管理服務在同一次讀取中取得五房狀態，`rooms` 依房號 1 至 5 排列，每列格式與下方單房介面一致。即使只有一房開場，也會保留其餘四列。空房的 `session` 為 `null`，暫停中的房間保留場次及階段，其 `environment` 為 `null`。取樣時間為 `checkedAtUtc`。這份快照描述管理服務當下提供給轉接器的設定；設備實際套用狀態須依廠商回報核對。

管理包 0.31.282 起，每台房間轉接器可固定讀取 `GET /api/rooms/{roomId}/hardware-environment`。主控或該房憑證都可讀取。空房回覆中的 `session` 為 `null`。有場次時，`session` 同時包含場次 ID、階段與該次讀取的環境設定。換場或服務重啟後仍使用同一網址。

在管理電腦上，以下範例使用本房的 `$roomId` 及既有的 Bearer `$headers`。跨機時請使用場館設定的 HTTPS 管理位址。

```powershell
$url = "http://127.0.0.1:5081/api/rooms/$roomId/hardware-environment"
$snapshot = (Invoke-RestMethod -Uri $url -Headers $headers).session
$snapshot | Select-Object sessionId, roomId, state, phaseSinceSequence, environmentSinceSequence, environment
```

請依序取樣。若場次 ID 改變，請捨棄上場序號並採用新快照。跨場序號各自從頭計算。要查指定場次，可使用 0.31.275 起提供的 `GET /api/sessions/{sessionId}/rooms/{roomId}/hardware-environment`，直接取得下表欄位。

| 欄位 | 轉接器判讀方式 |
| --- | --- |
| `version`、`sessionId`、`roomId` | 介面版本為 1。每次讀取都核對場次及房號。 |
| `state`、`phaseSinceSequence` | 階段及進入該階段的場次序號。繼續執行時，即使天氣相同，階段序號也會前進。 |
| `environmentSinceSequence` | 初始任務設定的序號為 1，後續為最近一次套用環境命令的序號。 |
| `throughSequence` | 此次讀值涵蓋的場次序號，包含其他場次活動。 |
| `environment` | Running 時包含 `mode`、`weather`、`timeOfDay`、`lightning`。Preparing、Paused、Ended 時為 `null`。 |

重連時直接讀取最新值即可；兩次取樣之間可能發生多次變更。`lightning` 表示任務允許雷電，單次閃光的時刻需另行同步。確認頭盔所見畫面請使用場景觀測；確認實體設備已套用則需要廠商回報。轉接器失聯時，應依廠商的停止與逾時規格處理。

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

硬體由外部公司負責，目前尚待技術資料或 SDK。模擬器 0.2.22 支援以下即時排演，以及[離線回饋模擬](HARDWARE_SIMULATOR.md)的事件重建、佇列、重送和到期測試。設備輸入、強度映射、實體停止及廠商協議列入後續實機驗收。

### 使用場館 HTTPS

單房及五房清單可在 `managementUrl` 旁加入 `managementCertificateSha256`，填管理員提供的葉憑證 SHA-256，以 64 個小寫十六進位字元表示。工具會核對 HTTPS 站台名稱、有效期及憑證指紋，確認後才送出管理請求。使用作業系統已信任的憑證時，可以省略指紋。本機 HTTP 請省略指紋。 [場館 HTTPS 設定](WINDOWS_CONTROL_PACKAGE.md#啟用場館-https)

`--bind-room` 和 `--bind-venue` 會保留指定的指紋，產生的資料可直接交給 `--live` 或 `--live-venue`。五房必須使用同一管理原點及相同指紋。管理員更換憑證後，用新的指紋重建綁定再開始排演。

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

使用 `--live-venue` 搭配原 `venue-bindings.json` 與同目錄的五房設定。先按各房設定啟動對應埠的本機模擬設備。執行指令的程序使用 `VR_COMMAND_ROOM_1_KEY` 至 `VR_COMMAND_ROOM_5_KEY`，各值為該房的房控憑證。每次指定新的輸出目錄和停止標記，兩者的父目錄都須存在。

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

從 0.2.11 起，排演中收到管理服務拒絕時，該房會關閉模擬連線並以 `management-refused` 結束。收到無法解析或不符合回饋格式的管理回應時，原因是 `management-invalid-response`。兩者都會取消待確認批次、保留先前的模擬確認，並在寫完該房報告後發布 `stopped`。該房退出碼為 1，五房模式的其他房可繼續排演。可重試的管理連線錯誤仍顯示 `management-unavailable`。

從 0.2.12 起，附掛前會核對戰鬥串流識別及來源，執行中的回覆也須帶有有效的階段序號。已附掛的同一串流若回報不同戰鬥來源，該房以 `management-invalid-response` 結束。若管理服務暫時回覆 503，該房關閉原連線並取消待確認批次。管理服務恢復後，該房重新握手，從當前游標接收新的回饋。

從 0.2.14 起，同一輪排演的每房會保留最近已核對的管理序號與檢查時間，包括等待模擬確認及重新連線時的讀取。後續回覆的任一值倒退時，該房以 `management-invalid-response` 結束並取消待確認批次，先前已確認的回饋仍會保存。其他房間繼續排演。重開該房時，請使用目前的場次與設備綁定。

從 0.2.19 起，同一房的管理回覆內若有重複的 `eventId` 或 `reportId`，或下一批沿用本輪已嘗試送出的識別，該房會在送出前以 `management-invalid-response` 結束。原模擬確認會保留，其他房照常排演。閘道等待同一批確認時仍可重讀原管理回覆，重連後也會保留本輪已嘗試送出的識別。

0.2.20 也核對戰鬥來源的 `streamSequence`。同一頁及同一串流的後續轉送批次須遞增，房間過濾後的序號間隔可保留。等待確認時仍可重讀原批次。若序號重複或倒退，該房會在錯誤批次送出前結束，保留此前的模擬確認。

同版套件內含 `mock-device.py` 使用的防火牆查核檔。Windows 可從解壓目錄直接執行，模擬設備會在監聽前查核實際的 Python。若有提示風險，終端機會記錄原因並退出。

#### 離線核對五房排演結果

模擬器 0.2.16 會在版本 2 的 `venue-report.json` 保存原綁定清單的 SHA-256，以及各房報告的雜湊與位元組長度。交接時保留原 `venue-bindings.json` 和整個排演輸出目錄。在解壓目錄執行下列指令，可核對搬移後的檔案。查詢只讀取本機檔案，無需憑證。

```powershell
dotnet .\VrCommand.HardwareSimulator.dll --verify-venue-report ..\venue\venue-bindings.json --report-directory ..\rehearsal-01
```

輸出列出各房的退出碼、終止原因及模擬確認、取消與模擬設備失敗的訊號數。`verified` 表示報告互相一致。`rehearsalComplete` 反映原排演結果，即使某房排演失敗，只要原報告一致仍可核對。命令在檔案缺漏、變更、場次不符或版本不符時回傳退出碼 1。這些雜湊供交接核對，實體送達與停止仍需設備端驗收。

模擬器 0.2.17 產生版本 3 總報告。交接時也須保留綁定清單同目錄中的 `room-01.json` 至 `room-05.json`。工具核對排演實際讀入的設定檔雜湊，以及每筆訊號的設備、玩家、入場及席位是否與設定相符。輸出 `configurationsVerified: true` 並逐席列出結果，席號從 0 起算。版本 2 仍可查各房總數，`configurationsVerified` 為 `false`。

模擬器 0.2.23 的版本 4 總報告會保存每批模擬回饋的原始串流及執行階段序號。離線核對會查驗事件與串流序號，並拒絕同一場次中重複的事件或回報，包括合併場跨房重複。通過時摘要顯示 `attemptIdentitiesVerified: true`。舊版報告仍可用原方式核對，其摘要會顯示 `attemptIdentitiesVerified: false`。

模擬器 0.2.18 可將原綁定檔與原報告打包成單一 ZIP。接收方可直接驗證 ZIP，核對結果與讀取原資料夾相同。ZIP 包含場次、玩家、入場與設備識別，請私下交接。

```powershell
dotnet .\VrCommand.HardwareSimulator.dll --pack-venue-report ..\venue\venue-bindings.json --report-directory ..\rehearsal-01 --output ..\rehearsal-01.zip
dotnet .\VrCommand.HardwareSimulator.dll --verify-venue-zip ..\rehearsal-01.zip
```

打包時須指定新 ZIP 路徑。原檔核對失敗時不會發布 ZIP。版本 3 及 4 收錄五房設定，版本 2 收錄可核對的原清單及報告。兩個指令均可離線執行。

版本 4 也可逐筆對照場次的原始事件。管理台 0.31.265 起，原場次結束且戰鬥串流封存後，主控可在「五房硬體模擬排演報告」匯入核對工具輸出的版本 4 排演摘要並按「下載原場次封存事件」。將下載的 ZIP 解壓到單獨目錄。管理服務依摘要列出的原場次匯出，所以可以核對先前已結束的排演。

也可用主控身分讀取 `GET /api/sessions/{id}/events?after=0&limit=500`。每頁以最後一筆的 `sequence` 作為下一頁的 `after`，讀到空頁為止。依序合併為一個 JSON 陣列並以 `<場次 UUID>.json` 儲存，從序號 1 開始，每場上限 32 MiB。合併模式提供一份，獨立模式在同一目錄提供原五場的五份事件檔。事件檔含場次與玩家資料，請保存在交接 ZIP 之外。

```powershell
dotnet .\VrCommand.HardwareSimulator.dll --verify-venue-zip ..\rehearsal-01.zip --events-directory ..\original-events
dotnet .\VrCommand.HardwareSimulator.dll --verify-venue-report ..\venue\venue-bindings.json --report-directory ..\rehearsal-01 --events-directory ..\original-events
```

核對通過時，`sourceEventsVerified` 為 `true`，`sourceSignalsVerified` 為與所提供原事件相符的訊號筆數，涵蓋已確認、已取消和失敗批次。工具會核對原場次的封存、綁定當時的席位與入場，以及各訊號的串流、執行階段和原始事件。可用不帶 `--events-directory` 的原指令單獨核對交接檔。所提供的事件檔及模擬確認仍須由來源方保管，實體送達另由設備驗收。

#### 在主控台查看五房模擬摘要

管理台 0.31.230 的「五房硬體模擬排演報告」可開啟核對工具輸出的 UTF-8 JSON。把 `--verify-venue-report` 或 `--verify-venue-zip` 成功回傳的內容存成檔案後選取。檔案在瀏覽器內讀取，原 ZIP 與雜湊核對由模擬器指令完成。

主控可以查看各房終止原因及模擬確認、取消、失敗數。新版總報告可以切換房間看逐席結果，舊格式會顯示各房總數。畫面比對原場次與目前場次，並區分排演完成與未完成。實體設備送達與停止仍需現場驗收。

從模擬器 0.2.25 起，核對摘要也會帶出每房原報告累計的管理通訊異常和模擬裝置通訊異常次數。裝置在第一次交握時斷線，之後重新連上並完成排演，仍會保留這次異常。控制台 0.31.290 開檔時會先選取未完成的房間。若所有房間均完成，會先選取有通訊異常或模擬失敗的房間。舊摘要與缺少原報告的房間顯示「未提供」。手上若有原交接 ZIP，可用新版工具重新核對，補出各房的次數。

#### 停止五房排演中的指定房間

從 0.2.13 起，可在本次輸出目錄建立 `room-01.stop` 至 `room-05.stop`，單獨停止該房的模擬閘道。例如要停第二房，在另一個終端執行 `New-Item -ItemType File -Path ..\rehearsal-01\room-02.stop`。該房取消尚待確認的批次，保留先前的模擬確認，並以 `operator-room-stop` 結束。當 `--venue-status` 顯示該房 `stopped` 時，報告已寫入，場次／房間、模擬埠和設備 ID 的本機鎖也已釋放。其他房繼續排演。

需要重新排演該房時，使用原房控憑證和仍有效的房間設定，以 `--live` 另開該房，並指定新的報告和停止標記。新閘道使用當前游標。重開的房間由自己的標記控制，五房原輸出中的房間報告保留原樣。

## Windows 無人值守的本機排演

開發主機可用 0.2.23 起的 AF_UNIX 模式排演。下列檢查會啟動隔離的管理服務、五房模擬閘道與模擬設備，使用既有的短路徑作為工作目錄。三者均使用本機 socket，可在防火牆仍啟用入站通知時執行。搭配管理台 0.31.265 以上加入 `--verify-event-export`，會用主控匯出的原場次事件核對該輪實際產生的交接檔。

```powershell
python scripts/check-live-hardware-gateway.py --ipc-work-root C:\VrRehearsal `
  --api-exe '<解壓後的管理包>\Runtime\VrCommand.Api.exe' `
  --simulator-dll '<解壓後的模擬器>\VrCommand.HardwareSimulator.dll' --verify-event-export
```

若要自行啟動同機排演，在閘道及模擬設備的程序環境設定 `VR_COMMAND_HARDWARE_IPC_DIRECTORY` 為同一個短的私有絕對目錄。設定檔的管理 URL 為 `http://127.0.0.1:<數字>`，管理服務只繫結到目錄內的 `management-<數字>.sock`。每房用設定中的 `mockPort` 執行 `mock-device.py --port <數字> --room <房號>`，對應 `mock-<數字>.sock`。這些數字用來選 socket 檔和辨識模擬資源。程序依原設定驗證金鑰、名冊和回饋，報告沿用原格式。場館連線按原流程使用 TCP／HTTPS，請在該工作階段移除本機 IPC 環境變數。

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
| `mock-unavailable` | `fault` 顯示模擬斷線、逾時或無效回覆 |
| `management-unavailable` | `fault` 為 `management-service-unavailable`（HTTP 502、503 或 504）、`management-timeout`（管理讀取逾時）或 `management-transport`（傳輸中斷等連線錯誤） |
| `stopped` | 終止原因已確定，報告檔已寫出並關閉 |

沒有看到 `stopped` 時，請核對程序退出碼和報告。指定 `--status` 時，原結束摘要仍會接在狀態列後面。程式讀取時可用 `kind` 區分兩者。狀態不含金鑰、位址或玩家識別，`physicalDeliveryConfirmed` 固定為 `false`。

### 查看五房排演狀態

從 0.2.21 起，Windows 查詢遇到狀態檔正在替換或短暫的共用限制時，會在 25 毫秒的重試期限內再讀。若其他程式暫時禁止狀態檔替換，排演保留上一份完整狀態並繼續原回饋，下一輪再嘗試更新。停止時先寫原房間報告，再以 500 毫秒為終止狀態的重試期限。持續鎖定而無法發布時會回報錯誤。

使用模擬器 0.2.9。每次排演先建立專用的本機狀態目錄，五房啟動時都加上同一個 `--status-directory`。每房仍使用自己的房控金鑰和新的報告路徑。狀態檔在狀態變更或閘道迴圈中每隔約 500 毫秒以原子替換更新。正常結束時，先寫完報告，再發布終止狀態。

```powershell
dotnet .\VrCommand.HardwareSimulator.dll --live ..\venue\room-01.json --output ..\room-01-report.json --status-directory ..\venue-status
dotnet .\VrCommand.HardwareSimulator.dll --venue-status ..\venue\venue-bindings.json --status-directory ..\venue-status
```

第二行只讀本機檔案，無須金鑰。可重複執行以取得最新快照。每房依原場次 UUID 及房號核對，`current` 的 `progress.phase` 顯示閘道正在等待、連線、模擬確認或發生故障。超過三秒未更新的執行中狀態會顯示 `stale`，隱藏該房上次的模擬確認計數。未發布狀態顯示 `waiting`，房號或場次不合顯示 `mismatch`，損壞或未來時間顯示 `invalid`。`stopped` 可查最後計數及停止原因。重啟同房後會換新的 `runId` 並重算計數。這些狀態記錄的是本機模擬，`physicalDeliveryConfirmed` 固定為 `false`。

從模擬器 0.2.15 起，五房狀態和單房終端共用上述管理讀取故障碼。恢復後，該房以新模擬連線與當前游標重新附掛，正常狀態的 `fault` 會清除。查詢也可讀取舊版 `fault` 為 `null` 的管理故障快照。

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
