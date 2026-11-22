# 場館安裝包

請先完整解壓 ZIP。根目錄的 `venue-release.json` 是這一組 Windows 程式與 Quest APK 的版本核對報告。分發到不同電腦時，複製對應的整個資料夾，保留其中的啟動器、清單及說明。

報告的 `launcherFirewall` 列出三個 Windows 啟動器及其共用防火牆檢查的 SHA-256。啟動前若 Windows 可能顯示入站通知，或無法讀取通知設定，啟動器會略過該次啟動。工作站可以先完成下方的離線檔案核對。

| 電腦或裝置 | 交付內容 |
| --- | --- |
| 主控台 | `VRCommand-ControlServer`，由 `Start-Control.exe` 開啟，依資料夾中的 README 建立或選取管理實例。 |
| 遊戲伺服器 | `VRCommand-GameServer`，使用包內啟動器載入場次的伺服器設定。 |
| Windows 玩家 | `VRCommand-Player`，使用包內啟動器載入該席玩家的連線檔。 |
| Quest 3 | `Quest` 內的 APK 與原始建置回條，以及 `scripts` 內的 USB 診斷和部署工具。 |
| 硬體排演工作站（選配） | `VRCommand-HardwareSimulator` 內的模擬器、範例及操作說明。發行報告的 `hardwareSimulator` 欄記載隨包版本。 |

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

若使用 VIVE 的 Windows PC VR 連線方式，可在解壓根目錄執行下列檢查。請使用包外的新報告檔名。這一步讀取本機 OpenXR 設定與執行環境檔案；指定型號的頭盔畫面與左右控制器須在場館實測。

```powershell
$report = Join-Path (Split-Path (Get-Location).Path -Parent) 'windows-openxr.json'
& .\VRCommand-Player\Launch-Player.exe --check-openxr --report $report | Out-Null
Get-Content -LiteralPath $report
```

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

某席在 Windows 已出現、但 ADB 尚無法對應時，該列會附上 Windows 能核對到該席的檔案傳輸介面、USB 偵錯介面或驅動程式問題。請依房號與席號查看；表中「已連線」表示該席已取得 USB 偵錯連線。

首次安裝時，請準備已開啟開發者模式、允許本機 USB 偵錯的 Quest 3，以及 Android SDK 的 `adb.exe`。請把下列序號與 ADB 路徑替換成現場值。部署工具會查核防火牆條件、APK 雜湊及裝置型號，啟動後查核 OpenXR 顯示與輸入狀態。若防火牆查核略過啟動，可繼續使用上方的唯讀診斷。

```powershell
$env:VR_COMMAND_UNATTENDED = '1'
$apk = (Get-ChildItem -LiteralPath .\Quest -Filter '*.apk' -File).FullName
.\scripts\deploy-quest.ps1 -SmokeTest -RequireOpenXR -Serial '<頭盔序號>' `
  -AdbPath 'C:\Android\platform-tools\adb.exe' -ApkPath $apk -ReleaseReport .\venue-release.json
```

各席實際入場時使用主控台為該玩家產生的連線檔。MR 場次還需要現場校正資料。五房連線與實機操作須在場館網路驗收。
