# 場館安裝包

請先完整解壓 ZIP。根目錄的 `venue-release.json` 是這一組 Windows 程式與 Quest APK 的版本核對報告。分發到不同電腦時，複製對應的整個資料夾，保留其中的啟動器、清單及說明。

重新開場時，可在主控台展開「已保存的五房任務配置」，輸入部分配置名稱搜尋，選取後按「載入已保存配置」。核對房號與任務版本後，再按建立準備場次。

報告的 `launcherFirewall` 列出三個 Windows 啟動器及其共用防火牆檢查的 SHA-256。啟動前若 Windows 可能顯示入站通知，或無法讀取通知設定，啟動器會略過該次啟動。工作站可以先完成下方的離線檔案核對。

| 電腦或裝置 | 交付內容 |
| --- | --- |
| 主控台 | `VRCommand-ControlServer`，由 `Start-Control.exe` 開啟，依資料夾中的 README 建立或選取管理實例。 |
| 遊戲伺服器 | `VRCommand-GameServer`，使用包內啟動器載入場次的伺服器設定。 |
| Windows 玩家 | `VRCommand-Player`，使用包內啟動器載入該席玩家的連線檔。需要核對主控派發的席位時，一併複製根目錄的 `scripts` 資料夾。 |
| Quest 3 | `Quest` 內的 APK 與原始建置回條，以及 `scripts` 內的 USB 診斷和部署工具。 |
| 硬體排演工作站（選配） | `VRCommand-HardwareSimulator` 內的模擬器、範例及操作說明。發行報告的 `hardwareSimulator` 欄記載隨包版本。 |

中央環境設備的轉接電腦可提供 `VR_COMMAND_MASTER_KEY`，執行 `.\scripts\watch-room-environment.ps1 -ManagementApi https://venue.example:5081 -AllRooms`，將網址換成場館管理位址。每行 JSON 都含房號 1 至 5。各房在 `Running` 期間提供天氣、日夜與雷電設定；服務中斷會輸出五房 `Unavailable`。房控電腦使用下方的單房模式。

驗收環境設備時，可在主控台「五房硬體模擬排演報告」按「下載目前五房環境設定」。檔案列出同一次取樣的五房場次、階段與生效中的天氣、日夜和雷電設定，可與設備端紀錄對時核對。

單房或五房監看命令加上 `-RequireCurrentRead` 後，每筆回覆都必須帶回本次讀取的識別碼。遇到舊回覆或管理服務未支援此功能時，輸出 `Unavailable` 及 `sample-id-mismatch`；下一次收到有效回覆即可恢復。

單房轉接工作站可設定該房的環境變數 `VR_COMMAND_ROOM_KEY`，執行 `.\scripts\watch-room-environment.ps1 -ManagementApi https://venue.example:5081 -RoomId 3`。將網址與房號替換為現場值。每筆 JSON 包含取樣時間與房間狀態；只有 `Running` 會帶生效中的環境。若讀取中斷，工具會輸出 `Unavailable`，連線恢復後重新讀取該房的目前值。可加上 `-Samples 1` 單次查詢。

將資料夾複製到各台電腦後，可在啟動前用 PowerShell 逐檔核對。原始 ZIP 可放在 USB 隨身碟。以下範例檢查 Windows 玩家電腦，請使用交付方提供的 ZIP SHA-256，並替換兩個路徑。

```powershell
.\scripts\check-field-install.ps1 -Archive 'E:\VRCommand-Venue.zip' `
  -ArchiveSha256 '<交付方提供的 64 位十六進位 SHA-256>' `
  -Role Player -InstallDirectory 'C:\Venue\VRCommand-Player'
```

`-Role` 可選 `Control`、`Server`、`Player` 或 `Quest`，並將 `-InstallDirectory` 指向該角色的資料夾。選 `All` 時指向完整解壓目錄。請把原 ZIP、連線檔及產生的執行資料放在待核對目錄外。成功時會輸出 `verified: true` 與檔案數。缺檔、多檔或內容不同時會指出檔名。此檢查可離線執行，無需 Unity、Android SDK 或管理員權限。Quest 角色核對的是待部署 APK 與建置回條。

含硬體模擬器的交付包另可選 `-Role Hardware`，指向 `VRCommand-HardwareSimulator`。裝有 .NET 10 Runtime 的工作站可在解壓根目錄執行下列排演，輸出位置請使用包外的新檔案。報告內的確認與取消數來自模擬設備。廠商實體設備須依供應商協定另行聯測。

```powershell
dotnet .\VRCommand-HardwareSimulator\VrCommand.HardwareSimulator.dll `
  --input .\VRCommand-HardwareSimulator\example.json --output ..\hardware-rehearsal.json
```

硬體廠商可用房控憑證固定讀取 `GET /api/rooms/{roomId}/hardware-environment`。空房的 `session` 為 `null`，準備或暫停時的 `session.environment` 為 `null`。執行中提供 VR／MR 模式、天氣、日夜與雷電設定。恢復連線後重新讀取。若 `session.sessionId` 改變，請重新採用新場次的設定與序號。實體輸出與確認方式由廠商介面決定。

### 開場前測試兩台電腦的遊戲連線

在兩台電腦解壓同一份場館包，開啟 PowerShell，切換至解壓目錄。以下用伺服器 `192.168.1.10`、玩家 `192.168.1.20`、遊戲埠 `7777` 示範，請代入實際位址與埠。金鑰及輸出檔放在包外，使用新檔名。

1. 在伺服器產生本次金鑰，以私人方式複製到玩家電腦的使用者目錄。

   ```powershell
   .\scripts\check-lan-udp.ps1 -NewKey -KeyFile "$env:USERPROFILE\vr-lan.key"
   ```

2. 在伺服器執行下列命令。顯示 `listening` 後，在 60 秒內開始下一步。工具會在開啟網路埠前檢查防火牆設定，有提示風險時會自行結束。

   ```powershell
   .\scripts\check-lan-udp.ps1 -Mode Listen -KeyFile "$env:USERPROFILE\vr-lan.key" -LocalAddress 192.168.1.10 -PeerAddress 192.168.1.20 -Port 7777 -Seconds 60 | Tee-Object "$env:USERPROFILE\vr-listener.ndjson"
   ```

3. 在玩家電腦送出探測。

   ```powershell
   .\scripts\check-lan-udp.ps1 -Mode Probe -KeyFile "$env:USERPROFILE\vr-lan.key" -LocalAddress 192.168.1.20 -PeerAddress 192.168.1.10 -Port 7777 | Tee-Object "$env:USERPROFILE\vr-probe.json"
   ```

4. 等兩端程序結束，把兩份報告放到同一個使用者目錄，再執行離線配對。看到 `stage: pair-verified` 及 `complete: true`，表示本次兩端位址、埠及五次往返樣本相符。其他房間及其他玩家來源要各自測量。

   ```powershell
   .\scripts\check-lan-udp.ps1 -ListenerReport "$env:USERPROFILE\vr-listener.ndjson" -ProbeReport "$env:USERPROFILE\vr-probe.json"
   ```

### 五房開場前找出需補測的座位

在裝有 Python 3.12 與 PowerShell 的管理電腦解壓場館包。下例從包外的場次資料夾執行，將 `$tools` 改成解壓位置。五房獨立和合併使用同一組指令，每個場次各自保存檔案。

1. 從控制台下載本場的第 4 版啟動計畫，保存為 `venue-plan.json`，並備妥遊戲伺服器啟動器用這份計畫執行 `--venue-check` 成功產生的 `venue-preview.json`。把 25 席實際使用的 IPv4 填入 `seat-addresses.json`。檔案格式為 `{"version":1,"seats":[{"roomId":1,"seat":1,"address":"192.168.1.20"}]}`，在 `seats` 中填齊五房各五席。以各自獨立的裝置驗收時，每席使用自己的位址。

   ```powershell
   $tools = 'C:\Venue\field\scripts'
   $plan = @('--launch-plan', '.\venue-plan.json', '--launcher-preview', '.\venue-preview.json')
   python -B "$tools\prepare-venue-network-plan.py" @plan --seat-addresses .\seat-addresses.json --require-distinct-remote-roster --output .\network.json
   ```

2. 將第一輪的雙端原始報告集中到 `first` 資料夾，每份使用不同檔名。該資料夾只放測量報告。執行下列兩行，第二行的 `pendingSeats` 會列出房號、席號與狀態。資料有缺漏時，指令回傳 1，第一行仍會寫出可供補測使用的場館報告。

   ```powershell
   $network = @('--network-plan', '.\network.json', '--require-distinct-remote-roster')
   python -B "$tools\check-venue-udp-preflight.py" @plan @network --inbox .\first --output .\first.json
   python -B "$tools\start-verified-venue.py" --verify-only --launch-plan .\venue-plan.json @network --readiness .\first.json
   ```

3. 例如第 5 房第 5 席需補測，下列指令會從原計畫匯出該席的 Windows 測量參數。把產生的端點檔複製到伺服器和該席電腦。沿用上一節的 Listen、Probe 指令，在兩端都以 `-EndpointFile .\r5-s5.json` 取代 `-LocalAddress`、`-PeerAddress` 和 `-Port`，保留金鑰與其餘參數。

   ```powershell
   python -B "$tools\check-venue-udp-preflight.py" @plan @network --retry-report .\first.json --windows-retest-seat 5 5 --output .\r5-s5.json
   ```

4. 將補測的兩份報告放入新的 `retry` 資料夾，保留原始檔案與位置，再合併核對。若顯示 `udp-evidence-verified` 且 `pendingSeats` 為空，代表這份場次計畫的全館 UDP 資料已核對。開場前可再執行最後一行，重查各筆測量是否仍在 30 分鐘有效期內。這些離線查核都可以在遊戲關閉時執行。

   ```powershell
   python -B "$tools\check-venue-udp-preflight.py" @plan @network --retry-report .\first.json --inbox .\retry --output .\complete.json
   python -B "$tools\start-verified-venue.py" --verify-only --launch-plan .\venue-plan.json @network --readiness .\complete.json
   ```

### 補測 Quest 3 的 Wi-Fi 連線

若發行報告有 `questUdpProbe`，這份場館包包含頭盔端網路診斷 APK。沿用上一節包外的工作目錄、`$tools` 和 `$plan`。在 `device-map.json` 填寫接到這台電腦的頭盔，例如 `{"version":1,"seats":[{"roomId":5,"seat":5,"serial":"實際裝置序號"}]}`。

先查有哪些 Quest 席位需要重測。這一步只讀資料，頭盔可保持關機。`pendingQuestSeats` 列出此對照表內的房號與席號，`pendingOtherSeats` 是其他仍缺資料的席位數。

```powershell
$retry = @('--device-map', '.\device-map.json', '--network-plan', '.\network.json', '--venue-retry-report', '.\first.json')
python -B "$tools\probe-quest-venue.py" @plan @retry --list-retest-seats
```

若列出待測頭盔，請在可連到這些已授權頭盔的遊戲伺服器電腦上執行以下指令。先為每台待測 Quest 3 安裝隨包診斷程式。安裝工具會核對頭盔型號及已安裝 APK 的雜湊，再回報結果。防火牆查核若略過啟動，可以繼續使用上方離線清單。

```powershell
$env:VR_COMMAND_UNATTENDED = '1'
$adb = 'C:\Android\platform-tools\adb.exe'
python -B "$tools\install-quest-udp-probe.py" --adb $adb --serial '<裝置序號>'
python -B "$tools\probe-quest-venue.py" @plan @retry --adb $adb --output-directory .\quest-retest
```

診斷會從頭盔實際 Wi-Fi 位址向該房遊戲埠傳送測量封包。若有產生 `preflight-report.json`，用下列命令把這次結果合併回原場館報告。保留原始報告和位置，輸出使用新檔名。

```powershell
python -B "$tools\check-venue-udp-preflight.py" @plan @network --retry-report .\first.json --batch .\quest-retest\preflight-report.json --output .\after-quest.json
```

### 頭盔接入

若由主控分發 Windows 席位，請向主控取得本場匯出成功的回條。可在開啟遊戲前離線執行 `pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -WindowsStageReceipt .\windows-stage.json -Station PC-A -ClientConfig .\seat.json`。將 PC-A 換成這台電腦的標籤，並選擇實際收到的連線檔。成功時會顯示房號、席位、效期及 `connectionFileMatched`。

若使用 VIVE 的 Windows PC VR 連線方式，可在解壓根目錄執行下列檢查。請使用包外的新報告檔名。這一步讀取本機 OpenXR 設定與執行環境檔案；指定型號的頭盔畫面與左右控制器須在場館實測。

```powershell
$report = Join-Path (Split-Path (Get-Location).Path -Parent) 'windows-openxr.json'
& .\VRCommand-Player\Launch-Player.exe --check-openxr --report $report | Out-Null
Get-Content -LiteralPath $report
```

Quest 3 的 MR 部署會在電腦上先核對票券房號與三個地面標記。A、B 在房間及頭盔追蹤座標中都須相距至少 0.5 公尺，房間標記 C 到 A–B 直線也須至少 0.5 公尺。套用 A、B 算出的平移與旋轉後，每個量測點的誤差須在 5 公分內。若預檢指出房號及標記有誤，可先核對該房 A、B、C 的標記順序並重新量測，再匯出校準資料和相應的玩家連線檔。

若使用 Quest 3，在解壓目錄用 PowerShell 7 執行以下命令。第一行顯示交付包內的遊戲版本；第二行以本機預計接入五台為例，列出 Windows 裝置台數及 USB 偵錯狀態。請將 5 改成本次接到這台電腦的預期台數，可填 1 至 25。

```powershell
(Get-Content -Raw .\venue-release.json | ConvertFrom-Json).quest | Select-Object version, versionCode
.\scripts\check-quest-usb.ps1 -ExpectedDevices 5 -Summary
```

若只對應到部分裝置，摘要會列出仍無法對應的台數。若 Windows 或 ADB 清單無法讀取，摘要會指出資料不足。省略 `-Summary` 可輸出 JSON 記錄。裝置型號與實際安裝版本由接下來的部署工具核對。

已有場館座位對應檔時，可用同一份檔案確認是哪一席待授權、離線或尚未出現在 USB 清單。只填接到這台電腦的座位即可。結果依房號與席號排列，省略裝置序號。這項檢查只讀取 Windows 與現有 ADB 服務，全程無需啟動遊戲或按「允許」。

```powershell
.\scripts\deploy-quest.ps1 -CheckSeatUsb -DeviceMap .\device-map.json -SeatUsbSummary
```

在已連線的席位旁查看 ADB 型號提示。若顯示「其他型號」，可依房號、席號核對這副頭盔；「型號未確認」表示清單沒有提供可辨識的單一型號。安裝時會從選定頭盔再讀取實際型號。

某席在 Windows 已出現、但 ADB 尚無法對應時，該列會附上 Windows 能核對到該席的檔案傳輸介面、USB 偵錯介面或驅動程式問題。若 ADB 已列出裝置但缺少有效的連線編號，或有其他項目使用同一編號，摘要會指出房號與席號。只有連線編號可唯一使用的席位才計入已連線台數。

若頭盔能傳檔卻沒出現偵錯提示，可先看摘要列出的檔案傳輸與 USB 偵錯介面數量。Windows 回報偵錯介面異常時，摘要會列出裝置管理員的問題代碼。代碼 22 表示裝置已停用，28 表示驅動程式尚未安裝。有座位表時，可在對應的房號和席號旁查看該裝置的代碼。 [Microsoft 裝置管理員問題代碼](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/device-manager-problem-codes)

尚未接上頭盔時，可先核對解壓後的遊戲 APK。工具從腳本所在的套件讀取根目錄的 `venue-release.json` 及 `Quest` 目錄內的遊戲 APK。成功時會列出版本編號與兩份檔案的 SHA-256。此步驟可以在沒有 ADB 的電腦上完成。

```powershell
.\scripts\deploy-quest.ps1 -SmokeTest -CheckOnly -RequireOpenXR
```

首次安裝時，請準備已開啟開發者模式、允許本機 USB 偵錯的 Quest 3，以及 Android SDK 的 `adb.exe`。填入頭盔序號後，工具會查核防火牆條件、APK 及裝置型號，啟動後查核 OpenXR 顯示與輸入。可使用 `ANDROID_HOME` 中的 platform-tools 或 PATH 上的 ADB，也可以用 `-AdbPath` 指定現場的執行檔。若防火牆查核略過啟動，可繼續使用上方的唯讀診斷。

```powershell
$env:VR_COMMAND_UNATTENDED = '1'
.\scripts\deploy-quest.ps1 -SmokeTest -RequireOpenXR -Serial '<頭盔序號>'
```

各席實際入場時使用主控台為該玩家產生的連線檔。以下指令可在接頭盔前核對單席的 VR 連線檔、席號及包內的 APK。MR 場次還需要現場校正資料。

連線檔的 `address` 應是頭盔可連到的遊戲伺服器 IP，例如場館內的 `192.168.1.100`。若原場次已公布 `127.0.0.1`，請在新場次公布場館端點並重新配票。頭盔會把回送位址指向自己，工具會在安裝前攔下。同一台電腦上的管理服務仍可使用 `-ManagementApi http://127.0.0.1:5080`。單席部署在 Android 確認啟動後才會輸出成功訊息。

```powershell
.\scripts\deploy-quest.ps1 -ClientConfig .\room-01-seat-01.json -CheckOnly
```

若要在任務開始前盤點現場頭盔，接上已授權的裝置後執行下列命令。工具會讀取座位表，比對每席已安裝的遊戲與本包的版本。需要安裝時可依檢查結果進行準備。單席安裝、五房安裝準備及批次部署的 `-InstallMissing` 都會使用同一份包內遊戲檔。單獨查看整場座位規劃時，只需要場館的連線 ZIP。

```powershell
$env:VR_COMMAND_UNATTENDED = '1'
.\scripts\deploy-quest.ps1 -PrepareQuestApks -DeviceMap .\device-map.json -CheckOnly
```

### 收集與核對五房 Quest 玩家紀錄

各席遊戲啟動後，在能連到頭盔的電腦上執行下列命令。使用 Python 3.12、PowerShell 7、當次部署的連線 ZIP 與裝置表，以及已存在的私人資料夾。請填入實際 ADB 路徑。工具會建立新的擷取目錄，等待各席的最終結果與斷線紀錄。若 Windows 防火牆查核拒絕啟動 ADB，可先核對已經收回的檔案。

```powershell
$env:VR_COMMAND_UNATTENDED = '1'
$tools = '.\scripts'
$plan = @('--venue-bundle', '..\private\connections.zip', '--device-map', '..\private\device-map.json')
python -B "$tools\capture-quest-field-log.py" @plan --adb 'C:\Android\platform-tools\adb.exe' --output-directory ..\private\capture
```

收件後，把整個擷取目錄交給主控。主控可以在沒有 ADB 或頭盔的電腦上，逐席核對日誌長度、SHA-256、遊戲程序、連線埠和最終玩家入場識別。若原擷取有指定部署報告或部分座位，核對時使用相同的 `--deployment-report` 和相關選項。對補擷取批次也請附上原來的 `--retry-incomplete` 報告。

```powershell
python -B "$tools\capture-quest-field-log.py" @plan --check-capture ..\private\capture\capture-report.json
```

`verifiedSeats` 是本次核對成功的席數。缺檔、檔案不符或擷取尚未完成時，工具回傳退出碼 1，逐席列出結果。舊報告若沒有連線 ZIP 及裝置表的指紋，`captureBindingVerified` 會顯示 `false`。伺服器端戰績與實機體驗另外驗收。

### 混合頭盔場次的收件與驗收

Windows 玩家及 Quest 玩家共用一場時，可從包內建立驗收清單。以下以五房每房五席為例。先將本次全館結束的管理 ZIP、伺服器原終止報告、原場館發行報告、Windows 座位表及玩家回傳的 ZIP，以及 Quest 原擷取、部署、裝置表和網路計畫放在工作資料夾。在套件根目錄執行 `$tools = (Resolve-Path .\scripts).Path`，再切換至工作資料夾。把範例 IP 改成實際伺服器位址，每個位址各列一次。

```powershell
python -B "$tools/prepare-venue-field-manifest.py" --venue-bundle management.zip --launcher-report venue-final.json `
    --topology direct-lan --server-ip 192.168.1.10 --players-per-room 5 --minimum-concurrent-ms 2000 `
    --venue-release-report venue-release.json --windows-inbox returned --windows-seat-map windows-seats.json `
    --quest-device-map device-map.json --quest-network-plan quest-network.json `
    --quest-capture-report capture/capture-report.json --quest-deployment-report deployment.json `
    --require-quest-openxr --output venue.json
python -B "$tools/verify-field-results.py" --venue-manifest venue.json --inspect-windows-inbox
python -B "$tools/verify-field-results.py" --venue-manifest venue.json
```

收件檢查會列出 Windows 待補席位，可在補件後重跑。完整驗收會核對原場次、席位、玩家日誌及伺服器確認。範例要求每個 Quest 席位具備當次啟動的 OpenXR 紀錄。VIVE 頭盔的確切型號、實際顯示與左右控制器體驗仍須在現場確認。

兩種連線模式各完成 5、10、25 席後，可將六份批次清單一起檢查。各批準備時分別指定每房 1、2、5 席，並設定本次驗收要求的 `--minimum-concurrent-ms`。以下用 2,000 毫秒示範。將路徑換成本次保留的六份清單和各自引用的原檔。

```powershell
$batches = '5-independent/venue.json','5-linked/venue.json','10-independent/venue.json','10-linked/venue.json','25-independent/venue.json','25-linked/venue.json'
python -B "$tools/prepare-venue-stages.py" --topology direct-lan --minimum-concurrent-ms 2000 --require-quest-openxr --output stages.json @batches
python -B "$tools/verify-field-results.py" --venue-stages stages.json --inspect-venue-stages
python -B "$tools/verify-field-results.py" --venue-stages stages.json
```
