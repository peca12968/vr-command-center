# 場館安裝包

請先完整解壓 ZIP。根目錄的 `venue-release.json` 是這一組 Windows 程式與 Quest APK 的版本核對報告。分發到不同電腦時，複製對應的整個資料夾，保留其中的啟動器、清單及說明。

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

在解壓目錄用 PowerShell 7 執行以下命令，可唯讀查看 Windows 是否已列舉頭盔及其 USB 偵錯介面。

```powershell
.\scripts\check-quest-usb.ps1
```

首次安裝時，請準備已開啟開發者模式、允許本機 USB 偵錯的 Quest 3，以及 Android SDK 的 `adb.exe`。請把下列序號與 ADB 路徑替換成現場值。部署工具會查核防火牆條件、APK 雜湊及裝置型號，啟動後查核 OpenXR 顯示與輸入狀態。若防火牆查核略過啟動，可繼續使用上方的唯讀診斷。

```powershell
$env:VR_COMMAND_UNATTENDED = '1'
$apk = (Get-ChildItem -LiteralPath .\Quest -Filter '*.apk' -File).FullName
.\scripts\deploy-quest.ps1 -SmokeTest -RequireOpenXR -Serial '<頭盔序號>' `
  -AdbPath 'C:\Android\platform-tools\adb.exe' -ApkPath $apk -ReleaseReport .\venue-release.json
```

各席實際入場時使用主控台為該玩家產生的連線檔。MR 場次還需要現場校正資料。五房連線與實機操作須在場館網路驗收。
