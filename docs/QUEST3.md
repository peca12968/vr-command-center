# Quest 3 接入與工具鏈

目前 Quest 開發 APK 為 `0.50.12`／77，61,046,094 bytes，SHA-256 `f2ff7f1ce8cd9a89864a8a6f245d168d64457869cb1e812d9582399eef098873`。2026-11-17 重新核對同一份 APK 的 7 個 ARM64 ELF、SDK 32／35、v2 簽章及內附 AndroidManifest 的 VR 啟動與 MR 透視宣告。已用新版報告通過獨立與合併場的 VR／MR 離線部署前檢查。 [APK](../artifacts/quest/VrCommand.apk) · [發行報告](../artifacts/quest-native-elf-20261117/venue-release.json)

2026-11-16 Quest 開發 APK `0.50.11`／76 為 61,044,650 bytes，SHA-256 `06cec1ccf61c867038a05ff89acdd476ce24766dc146b3a325f6327455cf493c`。通過 ARM64、SDK 32／35、OpenXR 程式庫、APK v2 簽章及同版 Windows 來源核對。開啟遊戲內量測後，每條新連線可獨立採樣。 [發行報告](../artifacts/venue-release-quest-reconnect-0511.json) · [前版原件](../artifacts/history/unity-0510-before-reconnect-fd0b4f27/quest/VrCommand.apk)

2026-11-16 Quest 開發 APK `0.50.9`／74 為 61,038,434 bytes，SHA-256 `53d965a70d8ffbdad95f01a955386909ec995a4156d762f9110294c66d905c8f`。通過 ARM64、SDK 32／35、OpenXR 程式庫、APK v2 簽章及同版 Windows 來源核對。新增首次啟動的 OpenXR 顯示與輸入檢查。 [APK 封存](../artifacts/history/unity-0509-before-quest-link-7650a819/quest/VrCommand.apk) · [發行報告](../artifacts/venue-release-quest-openxr-0509.json)

2026-11-16 Quest 開發 APK `0.50.8`／73 為 61,039,210 bytes，SHA-256 `04a84cdb6739891c8ff8fd5da7874e6239e15140f27fa0960553d89d3ee3d9e9`。通過 ARM64、SDK 32／35、OpenXR 程式庫、APK v2 簽章及同版 Windows 來源核對。 [APK 封存](../artifacts/history/unity-0508-before-quest-openxr-c4ccb59a/quest/VrCommand.apk) · [發行報告](../artifacts/venue-release-tracked-vr-0508.json)

2026-11-11 Quest 開發 APK 0.50.7／72 為 61,037,854 bytes，SHA-256 `74457e3422ae4d312ba4d073fca1e3e982aedc55bccf9312656a21c638cf0473`。發行核對通過 ARM64、最低 SDK 32、目標 SDK 35、OpenXR 預載及 APK v2 開發簽章。安裝與操作待頭盔。 [APK](../artifacts/quest-packages/vr-command-quest-0.50.7-arm64-debug.apk) · [發行核對](../artifacts/venue-release-0.50.7-local-profiler.json)

2026-11-11 Quest 開發 APK 0.50.6／71 為 61,037,858 bytes，SHA-256 `d8047b1358b4f6ef355b15791b44a747977a56b0e2d62a7bf8cdf977d6a6a79a`。已核對 ARM64、最低 SDK 32、目標 SDK 35、APK v2 開發簽章與 OpenXR 預載。 [APK](../artifacts/quest-packages/vr-command-quest-0.50.6-arm64-debug.apk) · [發行核對](../artifacts/venue-release-0.50.6-xr-startup.json)

2026-11-11 Quest 開發 APK 0.50.5／70 為 61,037,854 bytes，SHA-256 `43b95a998e113896a0286338f3d47c928822bd60cadc7a460d6918a70d4a9254`。已核對 ARM64、最低 SDK 32、目標 SDK 35、APK v2 開發簽章，與 Windows 玩家及伺服器使用相同遊戲來源和場景網路識別。實機安裝與操作待頭盔。 [APK](../artifacts/quest-packages/vr-command-quest-0.50.5-arm64-debug.apk) · [發行核對](../artifacts/venue-release-0.50.5-weapon-gate.json)

2026-11-10 Quest 3 開發 APK 0.50.2／67 為 61,028,450 bytes，SHA-256 `916c314102a8af03a5480f0548f3f8d2ddbc3b79c63493c17a2a4ec7fdf7ce35`。已核對 ARM64、最低 SDK 32、目標 SDK 35、APK v2 開發簽章，以及與 Windows 0.50.2 的來源及網路識別。頭盔安裝與運行待實機。 [APK](../artifacts/quest-packages/vr-command-quest-0.50.2-arm64-debug.apk) · [發行核對](../artifacts/venue-release-0.50.2-debrief.json)

2026-11-10 Quest 3 開發 APK 更新至 0.50.1／66。`vr-command-quest-0.50.1-arm64-debug.apk` 為 61,026,698 bytes，SHA-256 `0d0c4ea6983247eecd033aaf4cd52f52a7698ecb9b2f2ba468d1d73acf71f221`。ARM64、最低 SDK 32、目標 SDK 35、APK v2 開發簽章及同版 Windows 的遊戲來源與網路識別均通過離線核對。 [驗證紀錄](PROGRESS.md#2026-11-10-遊戲主機的-https-與-wss-管理連線)

2026-11-10 Quest 3 開發 APK 為 0.50.0／65，檔案 `vr-command-quest-0.50.0-arm64-debug.apk` 為 60,997,166 bytes，SHA-256 `0cb23ff041b1787e24a694b0ae9b8184764f150740710876c8cceef70d9f1bba`。與同版 Windows 玩家和伺服器使用相同的遊戲來源及場景網路識別。已核對 ARM64、最低 SDK 32、目標 SDK 35 及 APK v2 開發簽章。頭盔安裝及現場 MR 驗收待實機。 [建置紀錄](PROGRESS.md#2026-11-10-合併場分房敵軍策略)

## Windows USB 與 ADB 診斷

接上頭盔後，可在 PowerShell 7 執行唯讀檢查。工具讀取 Windows 目前列舉的 Meta USB 裝置及 ADB 介面描述，並向 `127.0.0.1:5037` 上現有的 ADB 服務查詢清單。它只輸出計數和狀態，省略裝置序號、位址和原始回覆。執行過程無需提權、啟動 ADB 或調整防火牆。 [Windows 裝置相容識別](https://learn.microsoft.com/windows-hardware/drivers/install/devpkey-device-compatibleids) · [ADB 主機查詢協定](https://android.googlesource.com/platform/packages/modules/adb/+/HEAD/docs/dev/services.md)

```powershell
pwsh -NoProfile -NonInteractive -File .\scripts\check-quest-usb.ps1
```

| 狀態 | 觀察結果 |
| --- | --- |
| `windows-usb-inventory-unavailable` | 無法讀取 Windows USB 裝置清單。 |
| `meta-usb-not-enumerated` | Windows 的目前清單沒有列出 Meta USB 裝置。 |
| `meta-usb-without-adb-interface` | Windows 已列舉 Meta USB，已讀到的介面描述中沒有 ADB。`portableMediaInterfaces` 顯示其中有幾個介面可用於檔案傳輸。 |
| `meta-usb-interface-descriptors-incomplete` | 部分裝置的介面描述讀不到，ADB 介面狀態仍未確認。 |
| `adb-usb-driver-problem` | Windows 已列出 ADB 介面，該介面有 PnP 問題碼。 |
| `adb-server-inventory-unavailable` | Windows 已列出 ADB 介面，本機服務未回傳可解讀的裝置清單。 |
| `adb-usb-transport-unmatched` | Windows 已列出 ADB 介面，本機 ADB 清單沒有可和 Meta USB 裝置比對的序號。 |
| `adb-usb-unauthorized`／`adb-usb-offline` | ADB 清單中和 Meta USB 序號相符的裝置仍待授權，或處於離線。 |
| `adb-usb-other` | 相同序號出現不支援的 ADB 狀態或重複項目。 |
| `adb-usb-device`／`adb-usb-mixed-states` | 已比對的裝置處於 `device`，或有多種狀態。以 `adb.matchingMetaUsb` 查看每種狀態的數量，再由部署工具核對實際型號。 |

退出碼 0 表示已輸出快照。`adb.unmatchedEntries` 包含其他 Android 裝置、無序號項目，以及無法和 USB 序號比對的無線連線。若狀態為 `unauthorized`，依 Meta 指引在頭盔內確認本機的 USB 偵錯授權。 [Meta 實機設定](https://developers.meta.com/vr/documentation/android-apps/enable-developer-mode/) · [Android Debug Bridge](https://developer.android.com/tools/adb)

## 首次安裝與啟動檢查

準備一台尚未安裝 VR Command 的 Quest 3。在手機 Meta Horizon App 開啟頭盔的開發者模式，接上資料線，再於頭盔內允許 USB 偵錯。從 `adb devices -l` 取得狀態為 `device` 的裝置序號。Windows 若只顯示 Reality Labs 的 USB 介面，請確認開發者模式、重啟頭盔並重新連接。 [Meta 實機設定](https://developers.meta.com/vr/documentation/android-apps/enable-developer-mode/) · [Android Debug Bridge](https://developer.android.com/tools/adb)

以目前 `artifacts/quest/VrCommand.apk` 對應的原發行報告執行以下檢查。`-ApkPath` 可指定另存的原 APK；兩者的 SHA-256 必須一致。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -SmokeTest -Serial '<ADB 序號>' `
  -ReleaseReport .\artifacts\quest-apk-manifest-20261117\venue-release-final.json
```

工具核對指定 Quest 3，在目前 Android 使用者下安裝 APK，並讀回裝置上的 APK 雜湊。沒有既有玩家設定時，工具等待 Android 確認啟動，接著讀取該程序的 Unity 與 AndroidRuntime 日誌，並在三秒後重查原程序。成功輸出 JSON 的 `status` 為 `process-observed`。`unityLogLines` 是查到的 Unity 日誌列數，允許為零。預設遇到既有安裝會停止。

首次安裝、續測、單席部署與票券更新會在每次執行開始時從 `adb devices -l` 取得該裝置的 ADB 連線識別。從型號檢查到最後一步均使用這條連線。原連線消失後，本次指令會停止，可在原頭盔重新連線後用新的一輪核對。若同時有多台已授權裝置，單席部署須用 `-Serial` 指定目標。缺少或重複的連線識別會在寫入前回報 `transport-unavailable` 或 `transport-ambiguous`。 [ADB 命令參考](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/docs/user/adb.1.md)

部署工具對原生 ADB 指令設有期限。安裝最多 180 秒，檔案傳輸與 `am start` 各 30 秒，其他指令通常 10 秒。逾時時結束本次 ADB 用戶端並回報，已啟用的 ADB 服務繼續供其他操作使用。若安裝或檔案切換逾時，請先核對頭盔上的現行版本及設定再重試。批次預檢可在各席列出 `adb-timeout`，部署中的逾時會保留失敗步驟。

如果 APK 安裝完成後遇到暫時的啟動或日誌錯誤，可在原命令加上 `-ResumeSmokeTest`。工具先核對已安裝 APK 的雜湊與原發行報告一致，並確認沒有玩家連線設定，才停止該遊戲程序並重新啟動。應用程式資料會保留。成功回條的 `installedThisRun` 在這次續測為 `false`，本輪完成首次安裝時為 `true`。 [Android 啟動指令](https://developer.android.com/tools/adb#am)

這項檢查無需玩家票券。後續備妥測試場次，依[單房實機追蹤驗收](#單房實機追蹤驗收)部署新配發的玩家設定，再驗證入場、OpenXR 追蹤、MR 對位及操作。

### 核對首次啟動的 OpenXR 子系統

Quest APK 0.50.9／74 起，首次啟動命令可加 `-RequireOpenXR`。腳本隨 Android Launcher Intent 傳入當次識別碼，從原程序的 Unity 日誌讀取相同識別碼的回報。同一次啟動必須載入 OpenXR，且顯示與輸入子系統都在執行，才會回傳 `status: "openxr-ready"`。舊日誌、其他程序的日誌，或互相衝突的回報都無法通過。 [Android Activity 啟動](https://developer.android.com/tools/adb#am) · [Unity XR 顯示子系統](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/XR.XRDisplaySubsystem.html)

檢查使用沒有玩家連線設定的 Quest。取得遊戲 PID 後，部署工具用同一個 20 秒期限輪詢日誌並重查 PID。期間若遊戲退出、重啟或 ADB 逾時會中止。已安裝相同版本可同時加 `-ResumeSmokeTest`，用新的識別碼重新檢查。頭手追蹤、入場、MR 對位及操作仍在單房實機驗收中確認。

### 單房實機追蹤驗收

1. 啟動 Windows 管理服務。用主控台建立一場單房 VR 任務，將 Quest 3 玩家登記在該房。
2. 從伺服器啟動器選擇同一場次，填入頭盔能連到的場館 IPv4 及 UDP 埠。勾選「VR 房間只接受追蹤姿態」及「記錄本次玩家連線來源（場館驗收）」。CLI 使用 `--tracked-vr on --peer-diagnostics on`。 [伺服器操作](WINDOWS_SERVER_PACKAGE.md#vr-場次使用實機追蹤)
3. 等伺服器就緒，在主控台下載同一席的最新連線檔，再用 `deploy-quest.ps1 -ClientConfig`、`-ManagementApi` 及原發行報告部署。頭盔入場後，核對本房名冊的席位、`Tracked` 狀態及玩家頭手是否正確。
4. 開始任務前用原玩家連線檔執行下方席位核對，每席保存一份成功回條，再啟動[原始日誌擷取](#收集-quest-場館驗收日誌)。在管理包 0.31.200 以上的控制台按「確認追蹤並開始」，管理服務會重新核對當時的追蹤。 [單場 VR 追蹤開場](PLAYER_READINESS.md#單場-vr-追蹤開場)
5. 結束後保持遊戲開啟至戰績確認完成，保存伺服器的戰鬥與世界封存及同一席的日誌。 [單場封存核對](EXTERNAL_CLIENTS.md#核對封存戰績與-udp-來源)

在已設好 `VR_COMMAND_MASTER_KEY` 的管理主機終端機執行。管理服務在其他主機時，使用它的 HTTPS 網址。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -ClientConfig .\quest-player.json `
  -VerifyPlayerTracking -ManagementApi http://127.0.0.1:5080 |
  Set-Content -Encoding utf8 -LiteralPath .\quest-player-readiness.json
```

工具從原連線檔找出場次、房號、席次和入場身分，向管理服務核對本次已連線且有有效追蹤的玩家，並讀回同一張 GameServer 準備中畫格。保存畫格也須在原房含有唯一的原玩家，且該玩家已連線、仍存活並有 `Tracked` 姿態。完成讀回時，取樣時的畫格年齡加上本次查詢時間仍須在 1.5 秒內。成功回條含 `scope: player`、`complete: true`、原世界及管理序號。`evidenceVersion: 1` 回條以入場雜湊供戰後核對，省略票券與金鑰。已換過入場身分、追蹤尚未就緒或場次已開始時，輸出 `complete: false` 及原因，退出碼為 1。這項查詢只讀管理服務，無需 ADB。頭盔畫面和操作仍需在現場驗收。

頭盔剛啟動時，可在同一命令加 `-WaitForTrackedSeconds 30`，讓工具在指定的 1 至 120 秒內自動重查。每次均使用原連線檔的場次與入場識別。票券到期、原入場變更、場次已離開準備階段或無權讀取時會停止。回條的 `wait` 欄位會記錄取樣次數及結束原因。開場仍由操作員在主控台確認。

戰後將原始回條傳給 `verify-field-results.py --quest-readiness-report .\quest-player-readiness.json`，並一同提供原 `.worldlog` 和 `--quest-player` 日誌。若使用舊版工具取得的回條缺少 `evidenceVersion`，須在 Begin 前用新版工具重新取得。 [回條核對方式](EXTERNAL_CLIENTS.md#核對單場-quest-開場追蹤回條)

#### 部署前核對單席連線檔

管理包 0.31.199 支援單席 VR、MR 的線上部署核對。`-CheckOnly` 會以完整原始 JSON 核對 Quest 3 席位、票券簽章、公告端點及遊戲來源。MR 同時加上 `-AlignmentFile`，傳入原鎖定的校正 JSON。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -ClientConfig .\quest-player.json `
  -ManagementApi http://127.0.0.1:5080 -CheckOnly
```

核對通過時可移除 `-CheckOnly`，加入 `-Serial` 和 `-ReleaseReport` 進行部署。工具會在安裝 APK 前和切換頭盔的連線設定前重新核對。同一席在安裝期間若被換掉，工具會保留原啟用中的連線設定，停止本次設定啟用及啟動流程。APK 可能已完成安裝。沒有 `-ManagementApi` 時可沿用本機部署流程。

#### 使用頭盔上已安裝的 APK 加入場次

完成首次啟動檢查或事先安裝後，可加 `-UseInstalledApk` 直接部署單席連線設定。使用原發行報告與最新連線檔即可省去複製 APK 到部署電腦的步驟。工具透過已授權的 ADB 核對指定 Quest 3 目前 Android 使用者的已安裝 APK SHA-256，再寫入設定及啟動。查不到 APK 或雜湊不同時，會保留原裝置上的設定並停止。

```powershell
pwsh -NoProfile -NonInteractive -File .\scripts\deploy-quest.ps1 -ClientConfig .\quest-player.json `
  -Serial '<ADB 序號>' -ReleaseReport .\venue-release.json -UseInstalledApk -RequireOpenXR `
  -ManagementApi http://127.0.0.1:5080
```

從五房 ZIP 部署單席時，也可搭配 `-VenueBundle`、`-RoomId` 和 `-Seat`。MR 仍使用該席原場次鎖定的校正檔。請保存 `-RequireOpenXR` 成功輸出的原樣 JSON。它記錄本次程序、啟動識別、席位和發行報告摘要，戰後可與同一程序的日誌及原入場一起核對。入場與追蹤依上方單房實機流程確認。 [驗收啟動回條](EXTERNAL_CLIENTS.md#核對單場-quest-openxr-啟動回條)

## 開場前從頭盔執行 UDP 預檢

使用獨立的 `vr-command-quest-udp-probe-0.1.0.apk`（套件 `com.vrcommand.udpprobe`）做場館診斷。它透過已授權的 ADB 裝置執行，從頭盔指定的 IPv4 傳送與 Windows 監聽端相同的 UDP 挑戰。報告可以納入逐來源封存驗收。 [Windows 監聽與封存操作](EXTERNAL_CLIENTS.md#核對每個玩家來源的-udp-預檢) · [Android Debug Bridge](https://developer.android.com/tools/adb)

在 Windows 伺服器開場前，先用 `check-lan-udp.ps1 -NewKey` 產生本次探測金鑰，再使用正式遊戲埠啟動監聽，指定頭盔實際的 Wi-Fi IPv4 及樣本數。保存監聽端的原始報告。監聽出現 `listening` 後，在連接頭盔的電腦執行以下指令。例子以頭盔 `192.168.1.20`、伺服器 `192.168.1.10` 和遊戲埠 `7777` 為例。

```powershell
$adb = 'F:\Tools\UnityEditors\6000.3.27f1\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\adb.exe'
$serial = '<原 ADB 裝置序號>'
$key = '<本次探測金鑰檔>'
& $adb -s $serial install .\artifacts\quest-udp-probe\vr-command-quest-udp-probe-0.1.0.apk
python .\scripts\probe-quest-udp.py --adb $adb --serial $serial --key-file $key `
  --local-address 192.168.1.20 --peer-address 192.168.1.10 --port 7777 --count 5 `
  --report .\quest-probe-room-01.json
```

每次用新報告檔，樣本數須與監聽端一致。同一頭盔一次執行一組。工具用 `adb devices -l` 確認唯一授權連線，固定在該連線傳入診斷套件的私有暫存金鑰、執行探測與清理。原連線消失時，本次探測失敗。若中斷時金鑰已傳入但尚未讀取，暫存檔可能留在原頭盔，下一次探測會使用新金鑰。完成報告含實際來源和交換摘要，請與原監聽報告一併保存在私人位置。逾時樣本以空值保存，整次未完成會以退出碼 1 結束。兩端退出後用原綁定位址與埠開場，再保留遊戲原始 logcat 與封存。 [ADB 連線選擇](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/docs/user/adb.1.md) · [逐來源驗收](EXTERNAL_CLIENTS.md#核對每個玩家來源的-udp-預檢)

建置可使用 `scripts/build-quest-udp-probe.py --sdk <SDK> --jdk <JDK> --keystore <診斷用開發金鑰庫> --output <新APK>`。需要 Android 35 平台、Build Tools 36.0.0 及 JDK 17。診斷金鑰庫使用別名 `androiddebugkey` 和標準開發密碼 `android`，獨立保存以供同一診斷套件更新。APK 的最低 Android API 為 32，目標 API 為 35。 [APK 簽章工具](https://developer.android.com/tools/apksigner)

### 批次預檢五房 Quest 席位

先在各台要測的 Quest 安裝診斷 APK 並授權 ADB。批次工具在可操作這些 ADB 裝置的遊戲伺服器電腦上執行。它讀取原版本 1 的 `device-map.json`，再用開場前的網路清單取得各房正式綁定位址與埠。網路清單的 `sources` 必須和裝置清單的房號、席位完全相符，每台填自己的實際 IPv4。可只安排部分 Quest 席位。

從 Windows 啟動器準備場館時，可用原啟動計畫、成功預覽及全館席位 IPv4 產生 Quest 專用清單。 [從原啟動預覽產生網路清單](EXTERNAL_CLIENTS.md#從原啟動預覽產生網路清單)

```json
{
  "version": 1,
  "mode": "Linked",
  "endpoints": [
    {"roomIds": [1, 2, 3, 4, 5], "address": "192.168.1.10", "port": 7777}
  ],
  "sources": [
    {"roomId": 1, "seat": 1, "address": "192.168.1.20"},
    {"roomId": 2, "seat": 1, "address": "192.168.1.21"}
  ]
}
```

獨立五房使用 `"mode": "Independent"`，在 `endpoints` 為房間 1 到 5 各填一筆，例如 `{"roomIds":[1],"address":"192.168.1.10","port":7777}`。各筆須使用不同的綁定位址與埠組合。

```powershell
python .\scripts\probe-quest-venue.py --adb $adb --device-map .\device-map.json `
  --network-plan .\quest-network.json --output-directory .\quest-udp-batch --count 5
```

工具為每席選定當次 ADB 連線、啟動 Windows 監聽並配對該台 Quest 的回覆。五房獨立模式可同時探測最多五個端點。每個端點等上一席的監聽與清理完成，再按席位順序接續。合併模式的五房共用一個端點，按房間與席位順序測試。即時進度會依完成順序輸出，原始證據與 `preflight-report.json` 存在每次新建的輸出資料夾，報告按房間與席位排序。

某席 ADB 連線中斷時仍會繼續其他席位。按 Ctrl+C 或達到 20 分鐘安排上限時，工具會停止安排新探測並保存報告。五房獨立模式會先等待已開始的探測依各自的時限完成及清理。頭盔重連後可用原報告補測未通過席位。未完成的批次會列出失敗階段並以非零結束。每組端點的席位全部通過後，該組才有 `udpSourcePreflights` 清單。原始報告仍須符合 30 分鐘啟動前有效窗。

全部探測完成後，按原網路清單啟動遊戲伺服器。封存驗收清單可用 `udpPreflightBatch` 引用一份報告，或用 `udpPreflightBatches` 引用多份。混合 Windows 與 Quest 時，可在開場前用場館工具核對各席位的雙端報告，也可在封存驗收清單逐場補上 Windows 來源的 `udpSourcePreflights`。 [場館 UDP 核對](EXTERNAL_CLIENTS.md#開場前核對五房-udp-報告) · [封存核對](EXTERNAL_CLIENTS.md#核對每個玩家來源的-udp-預檢)

#### 預檢前核對 Windows 原啟動批次

使用 Windows 啟動計畫時，可在上面的預檢命令加上 `--launch-plan .\venue-plan.json --launcher-preview .\venue-preview.json`。兩個參數要一起提供。工具在呼叫 ADB 或建立輸出目錄前，先核對兩份檔案的場次、任務版本、序號及端點，再核對 Quest 網路清單裡的全部端點。只測部分 Quest 席位時，仍會檢查其他房間的端點。

報告會保存兩份原檔的路徑及 SHA-256，請與原 UDP 雙端報告一併保留。封存驗收會重讀這兩份原檔，核對原場次及實際遊戲綁定。若用全館 UDP 工具合併多份報告，請同時提供這兩份原檔。 [全館 UDP 核對](EXTERNAL_CLIENTS.md#開場前核對五房-udp-報告)

### 重試 Quest UDP 預檢席位

某席失敗或操作員在探測中按 Ctrl+C 時，工具會保存已確認的結果與未完成席位。恢復裝置連線後，沿用原裝置對照表、網路清單、`--count` 及 `--timeout-ms`，並指定新的輸出資料夾。等待上限記在報告的 `sampleTimeoutMs`。若要改用其他上限，或舊報告沒有這個欄位，請開始新的預檢批次。舊報告仍可供離線驗收。

若首次已核對 Windows 原啟動批次，重試也要提供相同原檔。場次更新或兩份原檔的 SHA-256 改變時，須用新計畫開始新的預檢批次。

新版 Quest 回條會將探測到的端點場次、任務版本與修訂記在 `networkPlanSessions`。重試及合併全館資料會核對這些欄位。同一台頭盔或相同 IP、埠及席位換到新場次時，請開始新的預檢批次。獨立模式的部分席位回條可與全館清單合併，逐一核對其探測的房組。使用含場次修訂的網路清單時，舊回條若缺少這些欄位，需要原 Windows 啟動計畫與預覽才能沿用。

```powershell
python .\scripts\probe-quest-venue.py --adb $adb --device-map .\device-map.json `
  --network-plan .\quest-network.json --count 5 --timeout-ms 900 `
  --retry-report .\quest-udp-batch\preflight-report.json --output-directory .\quest-udp-retry
```

工具會逐席核對原監聽及探測報告的 SHA-256、來源、埠、有效時間及每筆往返時間。通過的席位標為 `reused`，其餘席位重新探測。`reusedSeats` 為仍有效且沿用的席位數。批次結束時已超過 30 分鐘的席位標為 `expired`。若還有缺件，可用最新一輪報告再次重試。

完成後用新一輪的 `preflight-report.json` 做場館核對。它仍會引用先前有效的原始雙端報告，請保留各輪資料夾與原相對位置。若更換裝置、來源 IPv4 或所用端點，請用更新的清單開始新批次。

### 從全館報告選出 Quest 補測席位

混用 Windows 與 Quest 時，可用未完成的全館 UDP 報告補測。這個流程使用全館原始網路清單、原裝置對照表，以及原報告引用的啟動計畫與預覽。工具會重新核對有效期限和雙端檔案，只探測仍待補測且在對照表內的 Quest 席位。其他待補席位的數量會列在 `pendingOtherSeats`。若映射的 Quest 席位均仍有效，工具會回報 `no-quest-retest` 並在存取 ADB 前結束。

```powershell
python .\scripts\probe-quest-venue.py --adb $adb --device-map .\device-map.json `
  --network-plan .\venue-network.json --venue-retry-report .\venue-readiness.json `
  --launch-plan .\venue-plan.json --launcher-preview .\venue-preview.json `
  --output-directory .\quest-venue-retest
```

新資料夾的 `preflight-report.json` 包含本輪補測的席位。用全館工具的 `--retry-report .\venue-readiness.json` 加上 `--batch .\quest-venue-retest\preflight-report.json`，以相同網路清單及原啟動檔重驗、合併。若仍有 Windows 缺件，可加上該批新增的雙端報告。 [全館補測](EXTERNAL_CLIENTS.md#補測未完成的全館-udp-預檢)

## 追蹤恢復後的武器輸入

0.50.12／77 以右手指向姿態的位置與旋轉追蹤判定能否發布頭手姿態及處理武器輸入。握持姿態仍有效但指向追蹤失效時，玩家要等指向追蹤恢復，再放開並按下扳機或換彈鍵。此版已建置 ARM64 APK 並核對簽章，頭盔待驗。 [Quest APK](../artifacts/quest/VrCommand.apk) · [共同發行核對](../artifacts/vive-release-05012-fb9bcabe/venue-release.json)

遊戲自 0.48.1 起，在應用程式及 OpenXR 工作階段均有輸入焦點時才處理頭盔操作。系統選單或應用程式暫停期間會停止發布本機追蹤姿態。返回遊戲後，右手扳機、換彈鍵及 B 重連鍵各自需要先放開，再按下。 [Unity OpenXR 焦點介面](https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/api/UnityEngine.XR.OpenXR.OpenXRUtility.html#UnityEngine_XR_OpenXR_OpenXRUtility_IsSessionFocused)

MR 量測中失去焦點會清除尚未完成的 A／B／C 取樣。返回後從 A 開始，在每個標記先放開再按左扳機。單純失去焦點會保留已完成的校正，應用程式暫停或追蹤原點改變則需重新校正。主控仍可按原流程查看席位追蹤狀態，並決定何時暫停或繼續。

遊戲 0.47.1 在頭盔追蹤中斷、場地校正失效、姿態遭拒或暫停時撤下武器輸入。恢復參戰後，請在追蹤有效時先放開右手扳機與換彈鍵，再重新按下。狀態板會提示 `RELEASE TRIGGER AND RELOAD TO ARM`。連續按住扳機的射擊節奏從下一次主動按下起算。

遊戲 0.49.1 會讀取同一次輸入更新中已放開的右手扳機短按。短按須在可射擊且已重新武裝時發生，仍由遊戲伺服器判定射速、彈藥與命中。追蹤、焦點或開場條件尚未恢復時的短按不會延後補射。

MR 玩家需要重新對位時，可由操作員暫停場次，完成量測並在主控台確認存活席位的追蹤後繼續。 [暫停後繼續](PLAYER_READINESS.md#暫停後繼續)

2026-11-06 建置 0.41.2、版本 53 的 ARM64 APK，minSDK 32、targetSDK 35，通過 v2 開發簽章驗證。與 Windows 建置來源及場景、玩家網路識別一致，242 項 Unity EditMode 測試通過。新來源診斷只在 Windows 專用伺服器明確開啟時運作。頭盔安裝及操作仍待實機。 [建置與校驗資料](PROGRESS.md)

2026-11-01 最新Unity0.36.1／code44、179真正Editor與e0594513...同源Windows／ARM64 APK建置成功，NGO29／API UI0.30及原ID保持。[結果尾界](DEBRIEF_BOUNDARY.md)修正背景End寫入尚未完成時的context競態，final另須精確durable seal；PC證據與原失敗場見PROGRESS，頭盔操作仍待設備。

2026-11-01 Unity0.36／code43、NGO29／API UI0.30，177真正Editor與7194dc98...同源Windows／ARM64 IL2CPP APK成功，原ID保持。新增[背景世界writer](ASYNC_WORLD_WRITER.md)用純DTO、bounded queue及durable State，不在背景讀Unity場景／輸入；Quest client沒有server journal。PC及F反例範圍見PROGRESS，APK成功不是頭盔／MR／25台驗收。

2026-11-01 最終Unity0.35／code42、NGO29／API UI0.30，169真正Editor與d30cc34c...同源Windows／ARM64 IL2CPP APK成功，原網路ID保持。新增[journal細分診斷](JOURNAL_STAGES.md)僅明確Windows專用server，Android不安裝；最終PC一般8項363幀／SSD負載8項355幀成功，F反例／候選與限制見PROGRESS。仍無頭盔／實體控制器／MR／25台驗收。

2026-10-31 最新Unity0.34／code41／NGO29、API/UI0.30，163真正Editor（含3項PlayMode Dynamic官方Touch虛擬綁定）與同源Windows／ARM64 IL2CPP APK成功。新增[右手B鍵重連](QUEST_RECONNECT.md)，原票券／驗票與網路ID保持；PC8項372幀及保留的失敗／APK大小差異見PROGRESS。沒有頭盔按鍵、USB更新、MR或實體跨機驗收。

2026-10-31 最新Unity0.33／code40／NGO29、API/UI0.30，152真正Editor及同源Windows／ARM64 IL2CPP APK成功。新增Windows opt-in[長診斷](POSE_CONTINUITY.md)，Android與一般啟動不安裝；原網路ID、world／命中規則與頭盔Client短票券邊界保持。首次Quest Bee目錄存取失敗與成功重試分開保留，不當授權失效；實際結果見PROGRESS，仍無頭盔驗收。

2026-10-31 最新Unity0.32.0／code39／NGO29、API/UI0.30，144真正EditMode及同源Windows／ARM64 IL2CPP APK成功。新增server listenAddress及[外部玩家流程](EXTERNAL_CLIENTS.md)，頭盔仍只收四欄Client短票券設定；不把新版server設定或管理key配置到頭盔。原網路識別保留、wire不變，但需使用讀取listenAddress的同源新版server。真實Quest／VIVE／MR仍未驗。

2026-10-31 最新Unity0.31.0／code38／NGO29，API/UI0.28；新增[玩家任務簡報](PLAYER_BRIEFING.md)，左手X／Y／握柄分頁與授權頁接入OpenXR，隨附固定來源繁中字型。141真正EditMode及PC原生輸入／晚連線通過，Windows／Android最終receipt見PROGRESS；Android建置不代表控制器／頭盔／MR已測。所有遊戲程序一起升29，保存原Scene／prefab ID與既有API reader規則。

2026-10-31目前為Unity0.30.0／code37／NGO28、API UI0.28；131項真正EditMode及同源Windows／ARM64 IL2CPP Quest APK成功。新增[任務活動倒數](MISSION_CLOCK.md)，新寫入envelope7讀1–7，API／UI及所有遊戲程序協同更新；原ID保留。無頭盔運行證據，下文保留歷史。

2026-10-31目前為Unity0.29.0／code36／NGO27、API UI0.27；125項真正EditMode與同源Windows／ARM64 IL2CPP APK成功，場景／prefab ID保留。新增[玩家End戰績](DESKTOP_DEBRIEF.md)，同機PC驗證與限制見PROGRESS，沒有頭盔實測。下文版本數字保留各輪歷史。

2026-10-31 最新遊戲端0.28.3／code35，API／UI0.27、NGO26保持；114真正EditMode及同源Windows／ARM64 IL2CPP Quest APK成功，aapt確認min32／target35。新增Windows明確選用的[本地複本診斷](DESKTOP_REPLICATION.md)，Editor／Android與普通啟動不安裝；server／host packet queue1024、client仍128，沒有改資料欄位、追蹤或舊回放。原生25程序前後對照及限制以PROGRESS為準，APK成功不代表頭盔啟動／效能。

2026-10-31 新姿態診斷patch為Unity0.28.1／code33，API／UI0.27及NGO26／全部遊戲契約保持。`--vr-pose-loop-trace`只在明確Windows Development與原pose trace一起啟用，Android不安裝觀察點；不改原0.5／1.5秒政策。新增7項PlayerLoop EditMode、總門檻109，最終真正Tests／Windows／Quest結果以PROGRESS及當次receipt為準；不因Editor通過推定Windows條件分支或實機成功。操作見[POSE_TIMING](POSE_TIMING.md)。

2026-10-31 最新玩家人物為API／UI0.26、Unity0.28／code32／NGO26，102真正EditMode；新player-body-v1及header playerPresentationVersion1需來源／API／UI／全部遊戲端一起更新，舊缺失0不補步態。頭部／比例及桌面腕點為裝飾性呈現，Tracked不合成握持雙臂或改追蹤資料；原scope／rules保持，見 [PLAYER_BODY](PLAYER_BODY.md)。新Quest實際結果以最新PROGRESS／receipt為準，不把PC GPU、managed SDK或舊APK算成本輪實機成果。

2026-10-31 最新戰鬥音效為API／UI0.25、Unity0.27／code31／NGO25，93真正EditMode。新header combatAudioVersion1、actor原子presentationRunning及固定combat-audio-v1需來源／API／UI／全部遊戲端一起更新；舊header0不補聲。來源fingerprint新增WAV／meta及Resources資產引用，雙平台結果以最新PROGRESS／receipt為準。音效在Android正常接入，NativeCombatAudioProbe只限明確Windows Development，不把PC DSP或APK建置當頭盔聽感，見 [COMBAT_AUDIO](COMBAT_AUDIO.md)。

2026-10-31 姿態時序patch為Unity0.26.1／code30、87真正EditMode，API／UI0.24及NGO24／player-fire-v1與網路資料保持；雙平台以最新PROGRESS／receipt為準。--vr-pose-trace僅明確Windows Development安裝，Android不啟用，不把本機診斷當頭盔證據。操作與邊界見 [POSE_TIMING](POSE_TIMING.md)。

2026-10-31 最新換彈／合成手套為API／UI0.21、Unity0.23／code26／NGO22；weaponPresentationVersion1及weapon-actions-v1需來源／API／UI／全體遊戲端一起更新，舊資料保持0／舊外觀，不可降舊reader。保存時鐘、Tracked界線及實際證據見 [WEAPON_ACTIONS](WEAPON_ACTIONS.md)／PROGRESS。

2026-10-30 最新人形敵軍接入為API／UI0.20、Unity0.22／Android code25／NGO21，header enemyPresentationVersion1及combatants-v1需協同更新；舊來源／外觀保留，不能降舊reader。保存姿態、原命中盒與限制見 [ENEMY_PRESENTATION](ENEMY_PRESENTATION.md)，真正建置／PC結果以 PROGRESS 為準。

管理 API／控制台現為 v0.17，NGO protocol19／Android code22、bundle0.20.0。2026-10-29 使用者確認 Hub 有有效授權後，真正 Unity 6000.3.27f1 已成功 Prepare、46 項 EditMode、Windows 播放器及 ARM64／IL2CPP Quest Development APK。SDK 診斷已被這些較強的實際結果補充；完整 11 項與頭盔實機驗收尚未完成。最終建置雜湊及多人／觀戰驗證以 [PROGRESS.md](PROGRESS.md) 為準；下方舊版本段落保留歷次說明。

v0.14 新增每次入場識別、票券 v2／protocol 2、If-Match-Admission 與跨輪詢重入撤銷，Unity／API 需同版升級並重發舊券，見 [ADMISSION.md](ADMISSION.md)。生成器 NGO protocol 14／bundle 0.14；當時 15 項 EditMode 尚待執行；現已擴為 46 項並通過，頭盔仍待驗。

v0.13 新增共用世界來源／發布器、接受後頭手錄製、追蹤中斷與 NGO protocol 13；接入／補送見 [WORLD_SOURCE.md](WORLD_SOURCE.md)。該版本當時 Prepare 退出 198、12 項 EditMode 尚待執行；最新真正 Editor 結果以上方與 NATIVE_VALIDATION 為準。

使用者指定先用 Meta Quest 3；暫按 Android 獨立執行規劃。工程在 `clients/unity/`，後端仍獨立使用 .NET 10，不把後端 DLL 放進 Unity。

目前遊戲端 v0.20.0／Android code22／NGO19，API 為 0.17.0／驗票 2。保存的 Arena 原位升級，不重建場景；全部遊戲 server／client 同版。PC 重連與嵌入 Transport 修正見 [RECONNECT](RECONNECT.md)／[TRANSPORT_PATCH](TRANSPORT_PATCH.md)，Windows／Quest receipt 來源指紋一致。

## 已有程式與驗證邊界

已有場地生成器、玩家頭部／雙手及武器物件、OpenXR 瞄準／射擊／換彈、NGO 連線審核、固定出生席位，以及管理狀態／環境、任務擺設、敵軍與健康／彈藥的接入來源碼。姿態透過 NGO 傳送，不走 REST。姿態目標 20 Hz、戰鬥狀態 10 Hz 是設定值，沒有實機量測；支援範圍與未接通的報告見 `GAMEPLAY.md`。

**目前已完成真正 Unity 編譯、生成資產、46 項 EditMode、Windows 及 Quest APK。** Windows server 加兩個 client 以無圖形模式通過獨立／Linked Simulation 入場、AI 傷害、暫停及封存；本輪通過489核心、369 HTTP、43世界串流與35項UI／native；新軍事掩體版本及相容範圍見FIELD_PROPS。另有真正 PC GPU 視窗／鍵鼠射擊證據，見 DESKTOP；沒有頭盔實機。

沒有實機互見或頭盔射擊操作；電腦鍵鼠射擊已驗證、MR 透視／錨點、遊戲內物件編輯或頭盔任務錄製；已有真正 PC AI 傷害證據。雨線／雷聲已有 Unity 接入來源及瀏覽器 Simulation 驗證，沒有頭盔聲光結果。瀏覽器自由觀戰／鏡頭書籤已驗證；Unity 桌面觀察鏡頭固定，不能作為需求 10 的完整證據。Unity 持久事件／補送已通過 PC 統計與回放封存整合；頻率與效能仍須量測，詳見 TELEMETRY。

embedded package `com.vrcommand.simulation` 現為 0.11.0。Runtime asmdef 已引用它，ProjectBuilder／CombatAuthority 來源碼會建立世界及同步渲染，並已由真正 Editor 成功生成、編譯與建置；實機操作另行驗收。規則與接入分別見 `SIMULATION.md`／`GAMEPLAY.md`。

## 固定工具鏈

| 項目 | 版本／位置 |
|---|---|
| Unity Editor | 6000.3.27f1，revision `672d562a42a7` |
| 本機 Editor | `F:\Tools\UnityEditors\6000.3.27f1\Editor\Unity.exe` |
| Unity CLI | 1.0.0-beta.14，已安裝 |
| OpenXR / XR Management | 1.19.0 / 4.6.1 |
| NGO / Transport | 2.7.0 / 2.7.4 固定官方來源加單行修正，embedded |
| Input System / URP | 1.17.0 / 17.3.0（對齊固定 Editor 隨附版本） |
| Test Framework / UGUI | 1.6.0 / 2.0.0 |
| Quest 建置設定 | IL2CPP、ARM64、Vulkan、min API 32、target API 35，Development APK |

版本由官方 Unity release feed、套件 metadata 與 URP Blank 17.1.0 模板選定。URP 已對齊 Editor 隨附 17.3.0，真正 Editor 完成匯入與資產升級，原範本授權保留。已產生真正 packages-lock.json；Editor 最低版本政策使 Transport／Collections／Burst／Math 等相依提高，實際為 2.7.4／2.7.1／1.8.31／1.3.3，XR Core Utils／Legacy Input Helpers 為 2.6.0／2.1.13。先前 managed SDK 的最低相依診斷圖不是此 UPM 圖，不能混稱。

新增 [managed SDK 接入檢查](UNITY_SDK_CHECK.md)：14 份 runtime 與 11 份測試來源使用官方 NGO／Input／Transport 等來源及真正 Unity DLL，在 Android／Windows 條件分支均通過型別編譯。該工具不執行 NUnit 或 Editor／ILPP／IL2CPP／APK；本輪真正 Editor 的 46 項測試與建置另有日誌，不混用證據。

使用者已明確同意 SDK／NDK 條款；Android Build Support 與 OpenJDK 已由 CLI 安裝，SDK／NDK 目錄修復及實際原生編譯結果見下節，不再等待條款確認。

歷史診斷：使用者先回覆已登入／啟用，當時工具端驗證仍為 CLI `loggedIn: false`、`unity license list` 空陣列、`unity license status` 為 active=false／signedIn=false，先前實際 Prepare 退出 198。一次瀏覽器登入流程已逾時，不能繼續等待舊回呼。CLI 狀態只是診斷資訊；是否能建置仍以實際 Editor 結果為準，不因 CLI 未登入而否定有效的 Hub／浮動授權。

2026-10-29 已查核本機 Appx、解除安裝登錄與常見目錄，原先只有 Unity CLI，未找到 Hub。已補裝並啟動 **Unity Hub 3.22.5**，Appx 版本 3.22.5.65535，註冊狀態正常。Windows 管理 Hub 套件位於 C 槽；工程、Editor、Android 工具及安裝包仍在 F 槽。套件來自 Windows 套件來源列出的 Unity 官方 CDN，SHA-256 `26b4103d7784d09a1ec312058360710f01c53a5881caa1c722e692055dcb9032` 與來源相符，Authenticode 為 Valid／Unity Technologies SF。安裝包存於忽略的 `artifacts/setup/UnityHubSetup-3.22.5-x64.msix`，無須重裝 Editor／SDK。

當時 Windows 安全性對 adb.exe 提示遮住 Hub；後續使用者已回覆在終端機執行 unity auth login，並確認「Hub 已有有效授權」。真正 Editor 已成功識別 entitlement 並完成上述 Prepare／測試／首輪建置，授權不再是當前阻礙。未操作安全設定、代填帳戶、選擇授權資格或購買方案。沒有要求密碼／token／序號。

依序執行下節 Prepare／Tests／Desktop／Quest。僅出現 Hub 或登入頁不算建置完成；本輪已有真正 Editor 產物。CLI 的 session 可與 Hub 不同，後續以實際 Editor 結果為準，不再要求使用者重複登入或接受相同條款。

官方說明：[Hub 授權管理](https://docs.unity.com/en-us/hub/manage-license)、[CLI 驗證與授權命令](https://github.com/Unity-Technologies/skills/blob/main/skills/unity-cli/references/auth-license-cloud.md)。

## Android 工具實測

安裝命令使用已同意的 `--accept-eula`。CLI 結束時回報 Android、OpenJDK、SDK parent、platform 34 成功，其餘八個子模組失敗；原始登錄並非全部成功。實際解壓檔案已存在，NDK、CMake、Build Tools、command-line tools 留在未整理的 archive 根目錄。

依官方 release metadata 的 extractedPathRename，`scripts/repair-android-layout.ps1` 已先用 `-WhatIf` 核對，再以限定在此 Editor 的絕對路徑移動新解壓元件；不合併／覆寫既有目標或刪除資料。整理後再次 WhatIf 沒有待移動項目。

| 元件 | 已實際驗證 |
|---|---|
| NDK | r27c／27.2.12479018，clang 18.0.3 可執行 |
| OpenJDK | Temurin 17.0.18+8 可執行 |
| CMake | 3.22.1 可執行，搭配內建 Ninja 完成組態及建置 |
| SDK | SDK Manager 辨識 Build Tools 36.0.0、Platform Tools 37.0.1、platform 34／35／36 |
| 工具與條款 | command-line tools 16.0 可執行；使用者已同意的 android-sdk-license 已由官方 SDK Manager 登錄 |
| 原生編譯 | C++17、Android log／STL、API 32、arm64-v8a 的共享庫編譯／連結通過，ELF header 驗證為 64-bit AArch64 |

可重驗 `.\scripts\check-android-toolchain.ps1`，輸出在忽略的 `artifacts/android-toolchain-check/`。這證明主要原生工具可協同工作；CLI 八個子模組的失敗登錄仍保留，後續真正 Unity 已偵測並成功建置 APK。沒有把原生 `.so` 當成 APK 或 Quest 執行結果。

來源：[Unity CLI 使用方式](https://docs.unity.com/en-us/unity-cli/use-unity-cli)、[Meta Unity requirements](https://developers.meta.com/vr/documentation/unity/unity-development-requirements/)、[Unity 套件庫](https://packages.unity.com/)、[Android SDK 條款](https://developer.android.com/studio/terms)。

## 可重現建置

在儲存庫根目錄執行：

```powershell
.\scripts\build-unity.ps1 -Target Prepare
.\scripts\build-unity.ps1 -Target Tests
.\scripts\build-unity.ps1 -Target Desktop
.\scripts\build-unity.ps1 -Target Quest
```

`Prepare` 首次建立 `Assets/VrCommand/Generated/Arena.unity`、玩家 prefab 與 XR 設定，之後重用保存的網路識別；需重建時明確執行 RebuildArena，並一起重建所有平台。Tests 要求新 XML 至少 179 項全數通過，包含新版Touch綁定在真正Editor Play Mode的Dynamic更新檢查。Desktop 輸出 `artifacts/desktop/VrCommand.exe`（須連同整個資料夾使用），Quest 輸出 `artifacts/quest/VrCommand.apk`。腳本檢查 exit 0／1，Desktop／Quest 另核對本次成功 BuildReport 的新 build-receipt.json，日誌在 `artifacts/unity-logs/`。PC 自動 smoke 與限制見 NATIVE_VALIDATION，下方頭盔步驟仍待設備。

無授權時可先執行 `.\scripts\check-unity-source.ps1`，但只能回報語法檢查結果。不得把其輸出視為可執行的 Unity 工程。

## 區域網路原型操作

以下原型流程使用 `Simulation` 來源。管理 API 預設留在伺服器本機 `127.0.0.1:5080`，玩家只連遊戲伺服器的 UDP 7777。場館網路與防火牆須允許該連線。實機驗收請使用[單房實機追蹤驗收](#單房實機追蹤驗收)。

1. 用 `.\scripts\start-local.ps1` 啟動 API，保留其視窗。
2. 建置桌面與 Quest 後，再產生連線資料，避免票券在建置期間到期：

   ```powershell
   python scripts/prepare-vr-session.py --server-address 192.168.1.100 --room 1 --players 2
   ```

   把範例 IP 換成頭盔能連到的桌面 LAN IP。助手只在空閒房間新建自己的 Independent 場次，保留 `Preparing`，輸出場次 ID 與 `data/vr-connections/<場次ID>/` 路徑。`server.json` 含 GameServer 憑證，只留在桌面；`player-1.json`／`player-2.json` 各含自己的五分鐘票券，不含控制台憑證。
3. 啟動桌面伺服器（請替換 GUID 路徑）：

   ```powershell
   .\scripts\start-windows-vr.ps1 -Config 'F:\Projects\vr-command-center\data\vr-connections\<場次ID>\server.json'
   ```

   腳本會在防火牆可能顯示允許視窗時記錄原因並跳過啟動。同一台桌面可用另一份玩家設定啟動 Client。WASD／按住滑鼠右鍵可操作桌面預覽。
4. Quest 3 須開啟開發者模式，USB 連接並在頭盔內授權 ADB。部署每台不同玩家設定：

   ```powershell
   pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -ClientConfig .\data\vr-connections\<場次ID>\player-1.json
   ```

   多台裝置須用 `-Serial` 指定；腳本核對裝置型號、只接受玩家欄位、安裝本專案 APK 並複製設定後啟動。此腳本尚未實機執行。
5. 先在 Preparing 啟動伺服器與玩家，再發 Begin；核對頭手互見、射擊／換彈、掩體與 AI／健康同步，再試 Pause、Resume、SetEnvironment 及 SetEnemies。管理資料超過 1.5 秒未更新時應停止戰鬥；所有路徑尚待實際執行。另核對 journal、批次補送與 End 封存；同一管道已有 .NET／HTTP 證據，Unity 路徑仍須實際執行。
6. 測試後以 End 結束自己建立的場次，保留歷史並釋放房間。票券過期時由有權控制台對同一玩家重新配發；不用刪除其他場次。已結束場次不能再配發或驗證。

### Quest 3 場地對位部署

先從管理台下載通過檢查的房間校正檔，再用同一房的玩家設定部署。一般部署可省略 `-AlignmentFile`。

管理台 0.31.246 在鎖定前會以瀏覽器核對所選原檔的位元組與服務回傳的 SHA-256，換行及 BOM 均納入。若鎖定回條與原檔雜湊不符，可按「重試確認結果」沿用原命令確認。五房開場清單可定位各 MR 房的校正欄。

#### 在管理台核對席位部署檔

1. 主控鎖定校正檔並為玩家配票後，開啟當前場次的「Quest 3 MR 席位部署核對」。房控可選本房的 Quest 3 席位，主控可選全場席位。
2. 選擇要交付的席位，加入該席的連線 JSON 與該房鎖定的原始校正 JSON，再按「核對部署檔」。若使用整房 ZIP，先解出個別席位的 JSON。
3. 核對結果會標明房號與席位。資料相符時顯示票券到期時間。席位拿錯、入場名額更換、票券無效及校正檔不符時，依提示重新配票或換回原檔。

此功能自控制台 0.31.25 提供。檔案交由目前登入的管理服務驗簽及核對名冊，票券與校正檔內容不寫入場次紀錄。連線地址及埠只做格式驗證。頭盔安裝、UDP 可達性和現場定位各有獨立驗收步驟。

#### PowerShell 部署

控制台 0.31.24 的 MR 連線檔包含該房鎖定的 `roomAlignmentSha256`。部署工具會自動使用 MR，並在呼叫 ADB 前核對提供的原始校正檔。以下以新下載的 MR 連線檔示範 PowerShell 7 離線預檢。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -CheckOnly `
  -ClientConfig .\player.json -AlignmentFile .\room-1-alignment.json
```

預檢回報房間、從 1 開始計算的席位、票券到期時間、選用模式及校正檔 SHA-256。`alignmentPinsVerified: true` 表示原檔符合連線檔內的鎖定值。預檢只讀本機檔案，輸出不含票券。遊戲伺服器負責驗簽及核對目前名冊，頭盔會重新計算校正並量測追蹤。票券效期為五分鐘，正式部署時請使用當場新配發的檔案。舊四欄 MR 連線檔仍可明確指定 `-MixedReality`，校正檔由伺服器在入場時核對。

單席可另帶 `-ReleaseReport` 與原 `-ApkPath`，例如以下 VR 預檢。省略 `-ApkPath` 時使用 `artifacts/quest/VrCommand.apk`。用五房 ZIP 選定單席時，也可把 `-ClientConfig` 換成 `-VenueBundle`、`-RoomId` 和 `-Seat`。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -CheckOnly -ClientConfig .\player.json `
  -ReleaseReport .\venue-release.json -ApkPath .\VrCommand.apk
```

`localApkVerified: true` 表示本機 APK 與原發行報告的 SHA-256 相符，此步驟無需頭盔。正式安裝時會核對當次暫存副本，ADB 安裝後再讀回裝置上 `base.apk` 的 SHA-256。若讀回失敗，流程停在 APK 核對，保留原玩家連線設定。安裝指令已送出時，須到裝置核對目前套件狀態。 [產生發行報告](EXTERNAL_CLIENTS.md#發送前離線核對交付套件)

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -ClientConfig .\data\vr-connections\<場次ID>\player-1.json -AlignmentFile .\room-1-alignment.json
```

正式部署會先執行相同檢查，再把當次核對的校正檔內容複製到頭盔。玩家設定記錄該份內容的 SHA-256。頭盔讀入時核對檔案、房間和標記，再以當次 OpenXR 追蹤重新量測。量測、回到出生位與原點失效的流程見 [場地配置](LAYOUT.md#quest-3-場地對位)。ADB 實機安裝、頭盔取樣與 MR 透視列入設備驗收。

### 直接使用 VR 五房連線 ZIP

管理包 0.31.42 可核對從「VR 五房配票」下載的原始 `vr-venue-connections.zip`。搭配 0.31.235 管理包及新版部署工具時，ZIP 可包含五房各 1、2 或 5 席。部署工具依原包核對房間、席位、場次、端點及本機效期。先在 PowerShell 7 離線預檢，或用 `-RoomId`、`-Seat` 查看指定席位。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\vr-venue-connections.zip
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\vr-venue-connections.zip -RoomId 4 -Seat 2 -CheckOnly
```

正式寫入 VR 設定前須提供 `-ManagementApi` 與主控環境變數 `VR_COMMAND_MASTER_KEY`。工具把原檔送給管理服務，逐席驗簽並核對現行名冊及公告端點。指定單席或使用裝置清單時，要寫入的席位須登記為 Quest 3，並對上各自已授權且已安裝指定 APK 版本的裝置。混合 VIVE 與 Quest 的名冊可用小批次部署指定 Quest 席位。 [小批次操作](#部署指定的-quest-席位)

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\vr-venue-connections.zip `
  -RoomId 4 -Seat 2 -Serial YOUR_ADB_SERIAL -ManagementApi http://127.0.0.1:5080
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\vr-venue-connections.zip `
  -DeviceMap .\quest-devices.json -ExpectedVersionCode 64 -ManagementApi http://127.0.0.1:5080 -CheckOnly
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\vr-venue-connections.zip `
  -DeviceMap .\quest-devices.json -ExpectedVersionCode 64 -ManagementApi http://127.0.0.1:5080 -DeployMappedSeats
```

裝置清單格式與 MR 相同。整批 VR 部署把各席的四欄連線設定寫到對應裝置並請求啟動，現場頭盔的入場與追蹤仍須另外觀察。連線檔與主控金鑰請私下保管。 [VR 五房配票](EXTERNAL_CLIENTS.md#vr-五房配票) · [裝置清單格式](#用裝置清單部署-25-席)

### 混合 VR 與 MR 五房部署包

管理包 0.31.47 可從五個獨立場次一次下載混合部署包。管理包 0.31.236 起可選五房各 1、2 或 5 席。各房先按指定席數登記玩家並啟動自己的遊戲伺服器，五房使用不同的場館 IPv4／UDP 端點。所有 MR 席皆登記為 Quest 3，並在啟動伺服器前鎖定各 MR 房的校正檔。

以主控登入「房間與場次」，在「VR／MR 混合五房配票」按「讀取五房名冊」。核對各房的模式、名冊及端點，只為 MR 房選擇已鎖定的原始校正 JSON，然後下載 `vr-mr-venue-deployment.zip`。包內有 `venue.json`（版本 2、`Mixed`、`Independent`）、五個房間的連線 ZIP，以及各 MR 房的原始校正檔。票券自簽發起有效五分鐘，整包由主控保管。

原席位完成入場後，可在全館場次控制啟用五房追蹤開場條件。管理包 0.31.237 的 5／10 人試場可選相應的每房席數。管理服務會在受理時重新核對每房原席位及最新遊戲快照。 [五房追蹤驗收開場](PLAYER_READINESS.md#五房追蹤驗收開場)

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\vr-mr-venue-deployment.zip
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\vr-mr-venue-deployment.zip `
    -DeviceMap .\quest-batch.json -ExpectedVersionCode 64 -AllowPartialMap `
    -ManagementApi http://127.0.0.1:5081 -CheckOnly
```

完成預檢後可改用 `-DeployMappedSeats` 套用，或指定 `-RoomId`、`-Seat` 及 `-Serial` 部署一席。正式部署須提供主控金鑰與管理服務網址，先核對原包每席的簽章、名冊、端點及 MR 校正檔。VR 席使用原始四欄連線設定。MR 席另寫入原校正檔並啟用透視。用 `-AllowPartialMap` 時，Quest 裝置清單只列當次要部署的 Quest 3 席位。 [指定席位操作](#部署指定的-quest-席位)

主控 API 使用 `GET /api/mixed-deployment/venue` 預覽、`POST /api/mixed-deployment/venue-bundle` 配票、`POST /api/mixed-deployment/venue-check` 驗票。5／10 席試場在預覽查詢、配票 JSON 和驗票 JSON 使用相同的 `playersPerRoom`，也記錄在原包的 `venue.json`。省略時使用原 25 席格式。各次請求使用當時同一次讀取的場次與端點。全 VR 或全 MR 場館仍使用各自的部署入口。

<a id="五房-25-席部署預檢"></a>

### 五房 MR 部署預檢

#### 從主控台下載五房部署包

1. 在五房各登記同樣數量的 Quest 3 席位。管理包 0.31.29 支援每房 5 席，0.31.236 起也可每房登記 1 或 2 席。鎖定各房校正檔，並啟動遊戲伺服器，等它公布場館 IPv4 與 UDP 埠。合併模式用一個端點，五房獨立各用不同端點。
2. 以主控登入「房間與場次」，選取合併 MR 場次或任一獨立 MR 場次。在「Quest 3 MR 五房部署包」選每房席數，依房號選取五份鎖定的原始校正 JSON，再按「下載五房部署包 ZIP」。畫面會提示場次、端點、名冊或校正檔有問題的房間。
3. 保留 `quest-mr-venue.zip`，可直接預檢或為指定席位部署。外層 ZIP 包含五個房間連線 ZIP、五份校正原檔及 `venue.json`。由主控保管整包，入場票券自簽發起有效五分鐘。

控制台 0.31.103 會在五房部署區顯示各房公布的 UDP 端點。批次公告的遊戲來源暫停更新時，下載按鈕會停用，已選的校正檔會保留。原來源恢復後可再次點選下載。若等待 ZIP 回應期間原端點失效，控制台會擋下該次下載，並指出需要確認的房間。

管理 API `POST /api/mr-deployment/venue-bundle` 限主控。請求包含 `topology`，以及五筆 `rooms`，各有 `roomId`、`sessionId`、按席位排序的完整 `players`（`playerId`、`admissionId`）及 Base64 的 `alignmentFile`。5／10 席試場在配票和 `POST /api/mr-deployment/venue-check` 的 JSON 使用相同的 `playersPerRoom`。服務按同一次讀取的場次和端點驗證五房，完整通過後以 `Cache-Control: no-store` 回傳 ZIP。場次、校正原檔、端點或當前名冊不符時回傳 `409` 及房號，無法取得部分部署包。裝置安裝和場館 UDP 可達性仍需實測。

#### 直接用 ZIP 預檢或部署單席

直接使用管理台下載的原始 ZIP。省略房號與席位會讀取包內全部席位並輸出預檢結果。指定房號與席位並加上 `-CheckOnly`，會輸出該席的到期時間與校正雜湊。兩種預檢皆只讀檔，不呼叫 ADB。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\quest-mr-venue.zip
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\quest-mr-venue.zip `
    -RoomId 4 -Seat 2 -CheckOnly
```

接好已授權 USB 偵錯的 Quest 3，核對實體標籤與 ADB 裝置序號。房號和席位從 1 開始。正式部署須指定 `-Serial`，只會對該裝置安裝專案 APK、複製對應席位設定與該房原始校正檔，再啟動應用程式。以下用實際序號替換 `YOUR_ADB_SERIAL`。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\quest-mr-venue.zip `
    -RoomId 4 -Seat 2 -Serial YOUR_ADB_SERIAL -ManagementApi http://127.0.0.1:5081
```

任一席位過期、場次或校正檔不符時，整份 ZIP 預檢失敗，應從主控下載當前部署包。線上操作使用 `-ManagementApi` 與 `VR_COMMAND_MASTER_KEY`。管理包 0.31.104 支援單席線上部署在 APK 安裝前及安裝後各核對一次原遊戲來源。安裝後核對失敗時會停在連線檔寫入前。單席線上部署也會在停止遊戲前重新核對已驗證暫存檔所對應的原場次。

#### 用裝置清單部署 25 席

在各台 Quest 3 授權 USB 偵錯。建立 25 席清單後，依實體標籤把每個 `REPLACE-*` 換成對應的 ADB 裝置序號。每組房號與席位須對應一個唯一序號，清單只保存在操作電腦。可以在配票前用 `-PrepareQuestApks` 安裝原發行 APK。腳本透過 `adb devices -l` 讀取授權狀態及 ADB 連線識別，再用 Android 套件管理器查詢已啟用的應用程式版本。 [配票前準備](#配票前準備-quest-apk) · [ADB 命令參考](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/docs/user/adb.1.md)

```powershell
$seats = foreach ($room in 1..5) {
    foreach ($seat in 1..5) {
        @{ roomId = $room; seat = $seat; serial = "REPLACE-$room-$seat" }
    }
}
@{ version = 1; seats = @($seats) } | ConvertTo-Json -Depth 4 |
    Set-Content -LiteralPath .\device-map.json -Encoding utf8
```

用原始部署 ZIP 與清單預檢。每席會回報裝置狀態和已讀到的版本。腳本也從各台裝置讀取 Android 的 `ro.serialno`。即使清單中的 ADB 連線識別碼不同，只要裝置回報同一序號，涉及的席位都會標記為 `duplicate-device`。讀不到可用序號時標記為 `device-identity-unavailable`。缺席、離線、未授權、型號、版本或裝置身分檢查失敗時，指令回傳非零結束碼。回報不包含讀取的裝置序號。 [Android ADB 文件](https://developer.android.com/tools/adb) · [AOSP 的 shell 序號讀取權限](https://android.googlesource.com/platform/system/sepolicy/+/34df8fb682160d5862f463547b31e846aa8ab52d/private/shell.te)

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\quest-mr-venue.zip `
    -DeviceMap .\device-map.json -ExpectedVersionCode 67 -CheckOnly
```

正式套用時，先依下方方式設定 `VR_COMMAND_MASTER_KEY`，再加入 `-DeployMappedSeats` 與管理服務網址。所有裝置與票券核對通過後，工具依房號與席位順序寫入設定並請求啟動，使用各台已安裝的 APK。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\quest-mr-venue.zip `
    -DeviceMap .\device-map.json -ExpectedVersionCode 67 -DeployMappedSeats `
    -ManagementApi http://127.0.0.1:5081
```

正式部署在各席開始寫入前會再讀一次裝置序號。若和預檢結果不同，該席會標記為 `device-identity-changed`。若讀取失敗則標記為 `device-identity-unavailable`。兩種情況都會在該席寫入前停止。這些檢查適用於完整與部分裝置清單，現場仍須依實體標籤核對房號及席位。

同一輪預檢與部署中的檔案驗證、寫入、停啟遊戲及 OpenXR 檢查，會固定使用該席從 `adb devices -l` 取得的連線識別。缺少有效識別或多個裝置共用識別時，預檢分別回報 `transport-unavailable` 或 `transport-ambiguous`。若原連線在寫入途中中斷，該步驟會失敗，暫存檔可能留在原頭盔。下一輪重試會為原裝置重新取得連線識別。ADB 服務的重啟須先讓本輪部署結束，再開始重試。 [ADB 依連線識別選取裝置](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/docs/user/adb.1.md)

正式部署使用管理包 0.31.104 或更新版。每席寫入前，服務會重新核對整份原部署 ZIP 的 25 個入場、端點及各來源最近五秒內的有效遊戲畫格。VR、MR 及混合部署都適用，部分清單仍使用同一份五房 ZIP 驗證。任一來源失效時，目前席位回報 `venue-check-failed`，後續席位標記為 `not-attempted`。已送出啟動的席位保留原結果。純預檢仍可用來核對檔案、端點與名冊。

各模式的 `venue-check` 接受 `requireLiveSource: true`，並在回條明確傳回 `liveSourceVerified`。來源缺少近期有效畫格時，該房席位會回報 `source-stale`。預設請求省略此欄，沿用只讀核對回條。

中途失敗會停止並以非零結束碼回報。`launch-requested` 表示該席的檔案已核對，且 Android 已確認啟動指定的遊戲活動。`file-verification-failed` 表示該席無法確認裝置檔案與預期內容相同，且尚未送出啟動。`deployment-failed` 表示其他部署步驟失敗。這兩種部署錯誤另附 `failedStep`，可辨別遊戲是否已經過停止指令與正式檔案切換。`not-attempted` 表示該席未進入寫入階段。 [核對頭盔追蹤席位](#核對頭盔追蹤席位)

#### 核對頭盔內已安裝的發行 APK

先在操作電腦執行四件套件的離線驗證，將成功輸出的 JSON 存為 `venue-release.json`。用 `-ReleaseReport` 取代 `-ExpectedVersionCode`，即可同時核對版本代碼和裝置上 `base.apk` 的 SHA-256。使用可信任的原始驗證報告，報告可搭配完整或部分裝置清單。 [產生離線發行報告](EXTERNAL_CLIENTS.md#發送前離線核對交付套件) · [Android 套件路徑查詢](https://developer.android.com/tools/adb#pm)

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\vr-venue-connections.zip `
    -DeviceMap .\device-map.json -ReleaseReport .\venue-release.json -CheckOnly
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\vr-venue-connections.zip `
    -DeviceMap .\device-map.json -ReleaseReport .\venue-release.json -DeployMappedSeats `
    -ManagementApi http://127.0.0.1:5081 -SaveDeploymentReport .\quest-deploy-first.json
```

批次預檢會先核對所有指定裝置。`apk-hash-mismatch` 表示版本代碼相符但 APK 位元組不同。`apk-unverified` 表示無法讀出 APK 的雜湊，或 Android 回傳多個套件檔。正式部署逐席開始寫入前會再核對一次。若第二次核對失敗，該席不寫入設定，後續席位標記為 `not-attempted`。`apkVerified: true` 表示該席已完成當階段的 APK 核對，入場及追蹤仍由主控台驗證。

使用 `-ReleaseReport` 時，預檢與部署報告會記錄整份原發行 JSON 的 `venueReleaseReportSha256`。請將原發行 JSON 和 `-DeployMappedSeats` 的輸出一併保留，包括中途中斷但已有成功席位的報告。成功席位附原場次、玩家、入場及連線埠，可在封存驗收與 logcat 和原戰績對照。 [核對封存席位](EXTERNAL_CLIENTS.md#核對封存席位的-quest-發行-apk)

#### 配票前準備 Quest APK

五房新配發的玩家票券有效期為五分鐘。`-PrepareQuestApks` 可在建立場次或配票前準備 1 至 25 台頭盔，只需裝置清單、原發行報告及 APK。混合場館的清單可只列要準備的 Quest 3 席位。

```powershell
pwsh -NoProfile -NonInteractive -File .\scripts\deploy-quest.ps1 `
    -PrepareQuestApks -DeviceMap .\device-map.json `
    -ReleaseReport .\venue-release.json -ApkPath .\VrCommand.apk
```

加上 `-CheckOnly` 可先讀取裝置狀態。`apk-preflight` 報告的 `ready` 代表裝置 APK 已核對，`install-required` 代表可首次安裝。有裝置未授權、重複指派、型號不符，或已有的遊戲與發行報告不符時，整批在安裝前停止。

正式準備會安裝缺少的 APK，並逐台讀回版號與 SHA-256。`apk-preparation` 完整報告表示指定的頭盔都已通過 APK 核對。中途失敗可用同一命令重跑，已核對的 APK 會直接沿用。這個步驟只準備應用程式。完成後，從主控台下載剛配發的五房 ZIP，再用同一裝置清單執行 `-DeployMappedSeats`。 [發行 APK 核對與部署](#核對頭盔內已安裝的發行-apk)

#### 同批安裝尚未安裝遊戲的 Quest 3

部署 5、10 或 25 席時，可在 `-DeployMappedSeats` 加上 `-InstallMissing`。工具先核對原 APK 的 SHA-256、整批裝置與席位，再對未裝遊戲的 Quest 3 執行首次安裝。只有已安裝且符合原版的遊戲會直接進入設定部署。若 Android 列出停用或保留的套件、版本不符，或 APK 雜湊不同，預檢會報出該席並停止整批。APK 安裝使用 Android 的 `-R` 選項，防止覆寫已存在的套件。 [Android 套件查詢](https://developer.android.com/tools/adb#pm) · [Android 套件管理程式](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/services/core/java/com/android/server/pm/PackageManagerShellCommand.java)

```powershell
pwsh -NoProfile -NonInteractive -File .\scripts\deploy-quest.ps1 `
    -VenueBundle .\vr-venue-connections.zip -DeviceMap .\device-map.json `
    -ReleaseReport .\venue-release.json -ApkPath .\VrCommand.apk `
    -DeployMappedSeats -InstallMissing -ManagementApi http://127.0.0.1:5081
```

每席安裝後會讀回版本與 APK 雜湊，重新核對原場次、端點和入場，才寫入設定。`installedApk: true` 表示 Android 已回報安裝成功。`apkVerified: true` 表示已核對裝置上的發行 APK。若 `failedStep` 為 `install-apk`、`verify-installed-apk` 或 `verify-live-venue-after-install`，這一席尚未寫入連線設定。含 `-RequireOpenXR` 的部署仍會在啟動後核對該次 OpenXR 回報。

中途失敗時，保留原部署報告並沿用 `-InstallMissing` 重試。若當時 APK 已安裝完成且讀回相符，重試直接使用該 APK。原報告中已啟動的席位會被略過。 [從原部署報告重試](#從原部署報告重試未完成席位)

#### 啟動前核對裝置檔案

單席與整批部署都會先傳送並核對 MR 原校正檔，再驗證暫存的玩家連線檔。兩項核對通過且票券仍有效時，才停止遊戲。更名之前，同一個裝置端指令會核對暫存連線檔及它所引用的原校正檔 SHA-256。任一檔案不符時，原正式連線檔仍在，批次報告將該席標為 `file-verification-failed`，步驟為 `activate-connection`。切換成功後，工具會再次核對正式連線檔及校正檔，兩項通過才送出啟動指令。批次沿用裝置上已安裝的 APK，單席流程另含 APK 安裝階段。 [ADB 遠端指令](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/docs/user/adb.1.md)

線上部署會在暫存連線檔通過 SHA-256 核對後，再向管理服務核對原五房來源、端點及入場。核對失敗時會嘗試移除該席暫存連線檔。部署工具會保留正式連線檔，並略過該席的停止及啟動指令。整批回報 `venue-check-failed`，已完成席位保留，後續席位維持 `not-attempted`。來源恢復後可依原報告重試。 [重試操作](#從原部署報告重試未完成席位)

單席及批次部署在寫入前解析目前 Android 使用者的遊戲啟動活動，正式連線檔核對通過後才以 `am start -W` 啟動。Android 必須回傳一筆成功狀態及相符的活動名稱。逾時、缺少確認、回覆互相衝突或 Android 回報沿用已在執行的活動時，該席回報啟動失敗。 [ADB 啟動選項](https://developer.android.com/tools/adb#am)

| `failedStep` | 操作員可確認的部署進度 |
| --- | --- |
| `verify-live-venue` | 服務未確認原來源、端點及名冊。該席尚未開始寫入。 |
| `resolve-launcher` | 找不到目前 Android 使用者的遊戲啟動活動。尚未寫入連線檔或停止遊戲。 |
| `prepare-device`、`stage-alignment`、`stage-connection` | 尚未送出停止指令或切換連線檔。工具會嘗試清理傳輸中的暫存檔。 |
| `verify-live-venue-before-stop` | 暫存檔已驗證，但最新線上核對失敗。正式連線檔仍為原檔，尚未送出停止或啟動指令。 |
| `check-expiry-before-staging`、`check-expiry-before-stop` | 票券已過期，尚未送出停止指令或切換連線檔。請下載目前部署包。 |
| `stop-game` | 停止指令失敗，尚未切換連線檔。請確認遊戲程序狀態。 |
| `activate-connection` | 停止指令已成功。若回報檔案驗證失敗，暫存連線檔或校正檔在更名前的核對未通過，原正式連線檔仍在。其他切換錯誤須查驗裝置目前的正式檔。 |
| `verify-active-connection` | 新連線檔已切換，正式連線檔或校正檔的最終驗證失敗，工具停在啟動前。 |
| `clean-local-connection`、`check-expiry-before-launch` | 新連線檔已切換並通過驗證，尚未送出啟動。後者須取得新票券。 |
| `launch-game` | 新連線檔已通過驗證，Android 未確認啟動指定的遊戲活動。 |

整批回報以 `filesVerified: true` 標示已完成檔案核對的席位。搭配 `launch-requested` 可確認 Android 已回報遊戲活動啟動。遊戲是否完成入場及追蹤，請用同一部署 ZIP 再核對。 [追蹤操作](#核對頭盔追蹤席位) · [Android 檔案傳輸](https://developer.android.com/tools/adb) · [Android 校驗工具](https://android.googlesource.com/platform/external/toybox/%2B/40d21c59f76a9388b0ebb5c4c706732c2d034a67/toys/lsb/md5sum.c)

#### 部署時核對每席 OpenXR

單席及五房部署可加 `-RequireOpenXR`，並以 `-ReleaseReport` 指定同一 APK 的原發行報告。支援版號 0.50.9／74 起。下例使用目前的 0.50.12／77。

```powershell
pwsh -NoProfile -NonInteractive -File .\scripts\deploy-quest.ps1 `
    -VenueBundle .\vr-venue-connections.zip -DeviceMap .\device-map.json `
    -ReleaseReport .\artifacts\vive-release-05012-fb9bcabe\venue-release.json `
    -DeployMappedSeats -ManagementApi http://127.0.0.1:5081 -RequireOpenXR `
    > .\quest-deployment.json
```

工具會先核對並發布原席位設定，再啟動該席，並在原程序日誌中核對本次啟動的 OpenXR loader、顯示和輸入子系統。五房報告按房號、席位逐筆保存原 PID 與啟動識別值。若該席的程序重啟或子系統未就緒，報告標示 `failedStep: "observe-openxr"`，後續席位維持 `not-attempted`。此時該席設定可能已切換、遊戲可能已啟動，須先確認該席現況再手動部署。對較早的部署失敗續跑時，沿用原 `-RequireOpenXR` 選項及報告，已確認的席位會保留原啟動資料。入場與頭手追蹤可接續用主控及追蹤回條核對。

使用 `capture-quest-field-log.py --deployment-report` 指定同一份完整報告。啟用 OpenXR 核對的席位會等到原 PID 的啟動記錄與 OpenXR 記錄都出現，再回報可開始擷取。遊戲程序若已重新啟動，須以當次部署與擷取資料重新核對。 [批次擷取](#一次擷取五房-quest-日誌) · [戰後驗收](EXTERNAL_CLIENTS.md#核對封存席位的-quest-發行-apk)

#### 從原部署報告重試未完成席位

正式部署建議加上 `-SaveDeploymentReport .\quest-deploy-first.json`，選擇既有私人資料夾中的新檔名。工具進入部署階段後會先保存整批席位，並在每席確認啟動後更新完整 JSON。每次更新先寫入同資料夾的暫存檔，再以單次更名發布。部署程序中途關閉時，可讀取最後一次成功保存的報告。

若報告寫到 `failedStep: "launch-game"` 或 `"observe-openxr"`，先核對該席實際啟動情況。原報告有 OpenXR 啟動證據時，可使用下方的復核指令。部署工具會在送出 Android 啟動指令前先保存 `launch-game`，所以中斷時可辨別哪一席的啟動結果仍待確認。若程序突然關閉時該席仍為 `not-attempted`，該席可能已有暫存或已切換的設定，部署尚未送出啟動。 [復核啟動結果](#復核中斷時的-openxr-啟動)

排除故障後，提供最近一次 `phase: "deployment"` 且 `complete: false` 的原始報告，搭配原部署 ZIP、原裝置清單與相同 APK 核對條件。部分清單沿用 `-AllowPartialMap`。下例使用原發行報告核對 APK。若首次使用 `-ExpectedVersionCode`，重試沿用相同版本代碼。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\vr-venue-connections.zip `
    -DeviceMap .\device-map.json -ReleaseReport .\venue-release.json -DeployMappedSeats `
    -ManagementApi http://127.0.0.1:5081 -RetryIncomplete .\quest-deploy-first.json `
    -SaveDeploymentReport .\quest-deploy-retry.json
```

工具跳過報告裡已送出啟動的裝置，只查詢及部署其餘席位。它會核對原 ZIP 雜湊、房席分配、Android 裝置身分及原 APK 條件。原部署報告若記有 `venueReleaseReportSha256`，重試須提交位元組完全相同的發行檔，檢查會在聯絡裝置前完成。舊部署的累計重試沿用原 APK 證據範圍。待重試的 ADB 連線若指向另一台頭盔，即使房席清單沒有改動，仍會在寫入前停下。每個待重試席位寫入前仍須通過原五房的線上檢查，所有票券須仍有效。報告只保存加鹽雜湊、發行摘要及必要場次資訊。

進入寫入階段後，新報告會累計先前及本次已送出啟動的結果，並保存前一份報告原檔的 SHA-256。若再中斷，下一輪使用最新的部署報告。驗收可提交最新的累計報告，或提交可連續核對的原報告歷史。若重試只走到 `phase: "preflight"`，繼續保留上一份部署報告。若缺少原報告、前次啟動結果不明或需替換頭盔，先從主控與實機核對目前狀態，再用只列待部署席位的新清單與有效票券，以 `-AllowPartialMap -DeployMappedSeats` 重新部署。 [收尾驗收](EXTERNAL_CLIENTS.md#核對封存席位的-quest-發行-apk)

#### 重新配票後接續原部署

原票券過期時，在主控台從同一批場次下載剛配發的五房 ZIP。`-VenueBundle` 傳入新 ZIP，`-OriginalVenueBundle` 傳入上一份部署報告對應的原 ZIP。沿用原裝置清單及部署選項，並為這次報告使用新檔名。

```powershell
pwsh -NoProfile -NonInteractive -File .\scripts\deploy-quest.ps1 `
    -VenueBundle .\refreshed-venue.zip -OriginalVenueBundle .\original-venue.zip `
    -DeviceMap .\device-map.json -ReleaseReport .\venue-release.json -DeployMappedSeats `
    -ManagementApi http://127.0.0.1:5081 -RetryIncomplete .\quest-deploy-first.json `
    -SaveDeploymentReport .\quest-deploy-retry.json
```

工具先用上一份部署報告核對原 ZIP，再核對新舊 ZIP 的五房拓撲、端點、MR 校正，以及每席的場次、玩家和入場識別。新票券通過原場次的線上核對後，只部署尚未啟動的席位。累計報告保存上一份報告和原 ZIP 的雜湊。若前次部署在 Android 啟動結果未確認時中斷，仍須先核對該席狀態。增量擷取時，搭配新 ZIP、最新部署報告及 `--after-deployment-report` 指向直接前一份報告。 [批次擷取](#部署中斷時先擷取已啟動的席位)

#### 復核中斷時的 OpenXR 啟動

原部署同時使用 `-RequireOpenXR` 與 `-SaveDeploymentReport` 時，工具會在送出 Android 啟動前保存該次 OpenXR 識別碼及已啟用設定檔的 SHA-256。若部署在確認回覆前中斷，重試可加上 `-RecoverOpenXRLaunch` 復核該席。票券已過期時，可同時使用上方的重新配票流程。

```powershell
pwsh -NoProfile -NonInteractive -File .\scripts\deploy-quest.ps1 `
    -VenueBundle .\vr-venue-connections.zip -DeviceMap .\device-map.json `
    -ReleaseReport .\venue-release.json -DeployMappedSeats -RequireOpenXR `
    -ManagementApi http://127.0.0.1:5081 -RetryIncomplete .\quest-deploy-first.json `
    -RecoverOpenXRLaunch -SaveDeploymentReport .\quest-deploy-retry.json
```

工具讀取原頭盔上的 APK、連線檔、MR 校正及原 OpenXR 日誌，並重讀遊戲程序識別。核對通過後，原程序繼續運作，報告記下原 PID 及識別碼，再部署後續席位。若原程序已退出、設定改動、日誌缺失或 OpenXR 未就緒，工具會停在復核階段。缺少原啟動證據時，請在頭盔確認現況，再用新票券及只列待部署席位的清單補做。入場及追蹤仍以原場次的主控台驗收為準。 [追蹤核對](#核對頭盔追蹤席位)

#### 部署指定的 Quest 席位

使用原五房 VR、MR 或混合部署 ZIP。版本 1 的 `device-map.json` 只列這次要部署的席位，房號、席位和 ADB 序號的格式維持相同。整批裝置表須涵蓋 ZIP 內的所有席位。只部署其中幾席時加上 `-AllowPartialMap`，所選席位皆須存在於原 ZIP。VR 的 5／10 席試場可直接用該 ZIP 的完整裝置表進行部署、追蹤核對及擷取規劃。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\vr-venue-connections.zip `
    -DeviceMap .\quest-batch.json -ExpectedVersionCode 64 -AllowPartialMap `
    -ManagementApi http://127.0.0.1:5081 -CheckOnly
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\vr-venue-connections.zip `
    -DeviceMap .\quest-batch.json -ExpectedVersionCode 64 -AllowPartialMap `
    -ManagementApi http://127.0.0.1:5081 -DeployMappedSeats
```

正式套用前仍會核對 ZIP 的全部 25 份連線檔、簽章、現行名冊和公告端點。MR 同時核對原鎖定校正檔。任何票券過期或名額已更換時，請從主控下載新的 ZIP。混合 VR 名冊中，已列入清單的席位都須登記為 Quest 3。工具只查詢清單中的裝置型號與 APK 版本，只寫入及啟動這些裝置。部署報告的 `mappedSeats` 和 `unmappedSeats` 分別表示本次有列入及未列入的席位數。

#### 核對頭盔追蹤席位

部署並戴上頭盔後，在主控電腦用原五房 ZIP、管理包 0.31.105 或更新版，以及既有 `VR_COMMAND_MASTER_KEY` 核對目前追蹤席位。可用 VR、MR 或混合 ZIP。工具先核對 25 份原連線檔，再以一筆 `POST /api/venue/tracked-readiness` 取得同一取樣時間的各場快照。未指定清單時檢查所有 Quest 3 席位。要查看一批指定席位，加入 `-DeviceMap .\quest-batch.json -AllowPartialMap`。此操作用清單選擇房號與席位，不呼叫 ADB。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\vr-venue-connections.zip `
    -ManagementApi http://127.0.0.1:5081 -VerifyTrackedSeats
```

`tracked-ready` 要求同一場次、玩家及當次入場名額、已套用的場次序號、管理服務判定為 `Fresh` 的快照，以及可參戰的 `Tracked` 姿態。工具將請求與接收耗時一併計入 1.5 秒的畫格期限。MR 另確認遊戲伺服器使用有效 MR 來源設定。報告含共用的 `sampledAtUtc` 與各席房號、席位、狀態及世界序號，所有已選席位就緒時才回傳 `complete: true` 與退出碼 0。

混合 Quest 3 與 VIVE 名冊的場館可加上 `-AllHeadsets`，用同一份 ZIP 核對全部 25 席。此模式不能搭配裝置清單或部分席位。報告含 `scope: "venue"`，各席的 `registeredHeadset` 取自管理名冊。報告核對伺服器接收的追蹤狀態，實體裝置型號與控制器操作由現場驗收。

##### 核對本次部署與追蹤席位

若本批使用 `-ReleaseReport` 核對 APK 並完成部署，可加 `-DeploymentReport` 指定保存的完整部署 JSON。請使用部署時的原 ZIP 與 `-DeviceMap`。若當時只部署部分席位，保留 `-AllowPartialMap`。完成重試後可使用最新的完整累計報告。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\vr-venue-connections.zip `
    -ManagementApi http://127.0.0.1:5081 -VerifyTrackedSeats `
    -DeviceMap .\quest-batch.json -AllowPartialMap -DeploymentReport .\quest-deployment.json `
    -WaitForTrackedSeconds 30
```

工具在連線管理服務前，先核對 ZIP 原檔雜湊、裝置對照表，以及每席原場次、玩家、入場名額和端口。每席須已完成 APK 與檔案核對，並送出啟動指令。取樣報告的 `deploymentSha256` 是所讀部署報告原檔的 SHA-256。查詢仍依管理服務當下的追蹤狀態判定，且全程無需 ADB。 [核對發行 APK](#核對頭盔內已安裝的發行-apk)

要做戰後核對，請在按「開始任務」前保存退出碼為 0 的完整 JSON。這份回條另含 `venueSha256`，每席保留原場次、世界序號、已套用的管理序號及畫格擷取時間。選用 `-DeploymentReport` 時，工具會用原 GameServer 的世界序號重讀每個場次的同一張保存畫格。同場多人共用該次讀取。畫格須在準備中、遊戲 tick 為 0，並且套用了取樣時的管理序號。一般即時追蹤查詢可用於任務進行中。 [在封存回放核對開場畫格](EXTERNAL_CLIENTS.md#核對-quest-開場追蹤回條)

##### 同一輪核對分批部署的追蹤

若原部署中斷後改用獨立的部分對照表補部署，可用 `-DeploymentReportsFile` 讀取兩批原報告。使用同一份原部署 ZIP，與一份包含所有要核對席位的裝置對照表。各原報告的已啟動席位須互不重複，合起來須涵蓋指定席位，且使用同一 APK。沿用累計重試而已取得一份完整報告的場館，可繼續使用單一 `-DeploymentReport`。

新部署報告另保存限於本組場次的裝置指紋。分批讀取時，若同一裝置出現在兩個已啟動席位，會先列出衝突的房號及席號，停止合併取樣。裝置序號不寫入報告。以 `--deployment-report` 擷取原日誌時，工具會在開始讀取及發布完整日誌前核對此指紋。 [戰後核對](EXTERNAL_CLIENTS.md#核對封存席位的-quest-發行-apk)

在私人資料夾保存 `deployment-reports.json`，路徑相對於清單所在位置。

```json
{
  "version": 1,
  "reports": ["quest-deploy-first.json", "quest-deploy-remaining.json"]
}
```

```powershell
pwsh -NoProfile -NonInteractive -File .\scripts\deploy-quest.ps1 `
    -VenueBundle .\vr-venue-connections.zip -DeviceMap .\device-map.json `
    -ManagementApi http://127.0.0.1:5081 -VerifyTrackedSeats `
    -DeploymentReportsFile .\deployment-reports.json -WaitForTrackedSeconds 30 `
    > .\quest-tracked-readiness.json
```

每輪取樣會同時核對指定席位。摘要就緒後，帶入單份或多份原部署報告的驗收會逐場重讀原準備畫格，再逐席核對原房內的原玩家、連線、存活與追蹤狀態。若某席的保存畫格與摘要不符，只在該席顯示 `source-seat-unverified`，整份回條維持未完成。合併多份部署時，`evidenceVersion` 為 2，每席保留自己原部署報告的 SHA-256。戰後將追蹤回條與它引用的各份部署原檔一併提交。 [封存操作](EXTERNAL_CLIENTS.md#核對-quest-開場追蹤回條)

##### 等候指定席位同時追蹤就緒

加入 `-WaitForTrackedSeconds` 可在原部署包核對完成後，等待 1 至 120 秒。每次重新取得同一個五房取樣，並逐席核對原入場名額及 1.5 秒的畫格期限。只有同一輪所有指定席位就緒才會結束等待並回傳退出碼 0。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\vr-venue-connections.zip `
    -ManagementApi http://127.0.0.1:5081 -VerifyTrackedSeats -AllHeadsets -WaitForTrackedSeconds 30
```

JSON 仍只輸出一次。`wait.samples` 是嘗試的取樣次數，`wait.outcome` 表示 `ready`、`timed-out` 或停止原因。逾時時保留本次期限內最後一輪席位結果。原場次、入場或權限有變、收到無效回條或票券到期時，會停止並回傳退出碼 1。這個操作只讀取追蹤資料，開始任務仍由主控依原開場條件執行。 [五房追蹤驗收開場](PLAYER_READINESS.md#五房追蹤驗收開場)

| 狀態 | 現場核對 |
| --- | --- |
| `awaiting-tracked-pose`、`not-tracked` | 檢查頭盔有無進入遊戲、恢復焦點並完成 MR 取點 |
| `source-not-fresh`、`source-revision-pending`、`mr-profile-pending` | 查看遊戲伺服器及房卡，等有效快照套用目前的場次狀態 |
| `source-capture-unverified` | 確認原場次已接上 GameServer，且快照含擷取時間，再重新核對 |
| `source-frame-unverified` | 確認管理服務可讀回該次取樣的原世界畫格及管理序號，再重新核對 |
| `source-seat-unverified` | 保存畫格無法確認該席原玩家已在原房連線、存活且有追蹤姿態。核對該席並重新取樣 |
| `source-outside-preparing` | 本次取樣已超過開場證據的準備階段。使用該場開場前保存的原回條 |
| `source-expired-in-transit` | 畫格在管理服務取樣時有效，但收到回應或完成原畫格讀回時已超過期限，可重新核對 |
| `venue-changed` | 核對期間原場次、房間或版本已有變更，請核對現場並重新取樣 |
| `seat-unavailable`、`admission-changed`、`seat-headset-mismatch` | 核對當前名冊與所選席位，重新下載有變更的部署包 |
| `readiness-unavailable`、`readiness-invalid` | 核對管理服務連線、版本與場次 |
| `readiness-access-denied`、`ticket-expired` | 核對主控權限或下載目前有效的原場館部署包 |

票券到期後可從主控下載新的 ZIP 供核對。報告反映全館同一取樣點，實際裝置序號、網路來源及全館持續容量另由現場驗收確認。 [收集 Quest 場館驗收日誌](#收集-quest-場館驗收日誌)

#### 使用逐房下載的檔案建立清單

若已有逐房下載的「房間連線檔 ZIP」，請將各房原 ZIP 與鎖定的原始校正 JSON 放在同一資料夾，再將下列清單存成 `venue.json`。用 Windows 遊戲伺服器啟動器選場時顯示的「場次ID」替換範例，也可從管理 API `GET /api/sessions` 取得場次的 `id`。相對路徑以 `venue.json` 所在資料夾為基準。 [按房間下載連線檔](EXTERNAL_CLIENTS.md#按房間下載連線檔)

```json
{
  "version": 1,
  "topology": "Linked",
  "rooms": [
    {"roomId": 1, "sessionId": "12345678-1234-1234-1234-123456789abc", "ticketsZip": "room-01-connections.zip", "alignmentFile": "room-1-alignment.json"},
    {"roomId": 2, "sessionId": "12345678-1234-1234-1234-123456789abc", "ticketsZip": "room-02-connections.zip", "alignmentFile": "room-2-alignment.json"},
    {"roomId": 3, "sessionId": "12345678-1234-1234-1234-123456789abc", "ticketsZip": "room-03-connections.zip", "alignmentFile": "room-3-alignment.json"},
    {"roomId": 4, "sessionId": "12345678-1234-1234-1234-123456789abc", "ticketsZip": "room-04-connections.zip", "alignmentFile": "room-4-alignment.json"},
    {"roomId": 5, "sessionId": "12345678-1234-1234-1234-123456789abc", "ticketsZip": "room-05-connections.zip", "alignmentFile": "room-5-alignment.json"}
  ]
}
```

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueManifest .\venue.json
```

`Linked` 要求五房共用場次 ID 與 UDP 端點。五個獨立房請改用 `Independent`，填入各房自己的場次 ID，並使用五個不同端點。同一 IP 使用不同 UDP 埠也符合獨立模式。檢查會比對每個 ZIP 內的五個席位、票券場次及房號、25 個不重複的玩家與入場識別，以及各房校正檔。成功時輸出各房端點、校正檔 SHA-256 與最早到期 UTC，無票券內容。失敗時回傳非零結束碼。

此指令只讀取檔案。若連線檔有鎖定值，須全數使用同一種格式，並逐席核對該房原檔。票券效期依本機 UTC 判斷，簽章和當前名冊由遊戲伺服器核對。若使用逐房檔案，預檢後可解出各席位 JSON 照單機指令部署。裝置安裝、實體校正、MR 透視與 UDP 可達性需在現場驗收。

#### 向管理服務核對五房名冊

管理包 0.31.26 起，主控可在同一份 `venue.json` 加用 `-ManagementApi`，一次驗證五房的票券簽章、當前入場名額與各房鎖定的原始校正檔。需要五房各五席、全部採用含校正雜湊的 MR 連線檔。從管理服務所在的電腦執行，下例使用預設本機埠號。

```powershell
$env:VR_COMMAND_MASTER_KEY = Read-Host '輸入主控金鑰' -MaskInput
try {
    pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueManifest .\venue.json `
        -ManagementApi http://127.0.0.1:5081
} finally {
    Remove-Item Env:VR_COMMAND_MASTER_KEY
}
```

管理服務用同一次讀取的名冊核對單一合併場或五個獨立場。成功時保留原預檢輸出並增加 `managementVerified: true`。簽章或票券失效時會標示 `ticket-invalid`，名額重配時會標示 `admission-changed`，兩者均附房號與席位。重新下載受影響房間的 ZIP 後可再執行。異地管理服務須使用 HTTPS。每份報告對應核對當下的名冊，設備安裝、實體定位及場館 UDP 可達性須另驗。

### 啟動 MR 伺服器前鎖定校正檔

遊戲自 0.48.0 起要求主控在場次為 Preparing、尚未啟動遊戲伺服器時，鎖定該場所有房間的校正檔 SHA-256。玩家部署須使用相同檔案。即使 JSON 欄位值相同，重新排版或改寫檔案也會改變雜湊。

在控制台 0.31.23 的場次面板，開啟「MR 校正檔鎖定」，為每房選取原始校正 JSON。管理服務核對檔案房號、原點和 A、B、C 量測，再依原始位元組計算雜湊。全數顯示「已核對，可鎖定」後，按「鎖定本場校正檔」並確認。等畫面顯示「已鎖定」後再啟動伺服器。若命令回應遺失，可用頁面上方的「重試確認結果」。切換場次或離開操作頁會清除尚未鎖定的選檔。

核對原檔的 `POST /api/room-alignment/check-file` 僅供主控使用。每次讀取最多 16 KiB 的原始校正 JSON，回傳房號與雜湊。原始校正 JSON 請保留作頭盔部署，保存的場次事件包含雜湊。

以下示範單房 3 的管理 API。`$api` 填管理服務網址，`$sessionId` 填實際場次 ID，`$headers` 使用該實例主控憑證的 `Authorization` 標頭。

```powershell
$session = Invoke-RestMethod "$api/api/sessions/$sessionId" -Headers $headers
$hash = (Get-FileHash -LiteralPath .\room-3-floor-alignment.json -Algorithm SHA256).Hash.ToLowerInvariant()
$command = @{
  commandId = [guid]::NewGuid().ToString()
  action = 'SetRoomAlignment'
  expectedSequence = $session.sequence
  roomAlignment = @{ room3 = $hash }
}
Invoke-RestMethod "$api/api/sessions/$sessionId/commands" -Method Post -Headers $headers `
  -ContentType 'application/json' -Body ($command | ConvertTo-Json)
```

五房全連線須在同一次命令填齊 `room1` 至 `room5`；獨立模式則對每場只填它自己的房間。收到回條後核對 `session.roomAlignment`，再啟動伺服器。相同命令可重送取得原回條。若鎖定錯檔，結束該場並以正確檔案建立新場。

Windows 啟動器 1.6 會在清單標示尚未鎖定的 MR 場次。主控鎖定後按「載入／更新」，再選擇符合開場設定的場次。 [伺服器清單](SERVER_CATALOG.md#mr-校正鎖定與啟動資格)

頭盔載入時會核對校正檔雜湊，入場時伺服器比對主控鎖定值及原票券席位。遊戲使用 NGO 協定 31，升級需配套更新管理服務、遊戲伺服器及玩家端。場地標記實際位置、OpenXR 追蹤與透視仍需現場核對。 [版本相容性](EXTERNAL_CLIENTS.md#遊戲版本相容性)

### Quest 3 透視呈現

Unity 0.43.0 的 Quest 開發版可用 `-Passthrough` 在已開啟的 VR 場次中使用 Meta 的透視合成層。部署須附同一房間的校正檔。玩家進入 Preparing 或 Paused 後量測 A、B、C，並依提示回到遊戲起點。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -ClientConfig .\data\vr-connections\<場次ID>\player-1.json -AlignmentFile .\room-1-alignment.json -Passthrough
```

透視啟用後，實景位於虛擬敵軍、擺設、雨線和 HUD 後方。遊戲的日夜與閃電影響虛擬物件照明，雷聲沿用原任務設定。遊戲仍保留地板與擺設的碰撞。合成層或校正未就緒時，頭盔暫停送出姿態與武器輸入。 [Unity 透視設定](https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.3/manual/features/camera.html)

透視畫面由 Meta 合成器處理。場次回放保存原虛擬世界資料。頭盔實景、實體遮擋及跨裝置定位另行驗收。

### 主控建立 MR 場次

在控制台將任務的初始模式選為 MR 並保存版本。建立單房或五房全連線場次後，先鎖定各房校正檔，再從 Windows 伺服器啟動器選擇該場。MR 由專用遊戲伺服器建立 GameServer 來源，模式在建立時固定。 [鎖定校正檔](#啟動-mr-伺服器前鎖定校正檔)

加入 Quest 3 玩家，為各席發票券，並準備對應房間的校正檔。同房玩家共用同一份標記配置，各自部署自己的玩家設定。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -ClientConfig .\data\vr-connections\<場次ID>\player-1.json -AlignmentFile .\room-1-alignment.json
```

玩家在準備中完成 A、B、C 三點量測，再回到頭盔提示的起點。主控可在「MR 開場檢查」查看各房就緒人數與等候席位。遊戲伺服器會核對票券房間、所選校正房間與鎖定的校正檔雜湊。全名冊的有效追蹤快照對上目前場次序號後，即可按開始。場中可調整天氣、時段及閃電。 [參戰快照](PLAYER_READINESS.md#mr-開場條件)

場次暫停時，頭盔需要重新對位的玩家可完成量測。請在「MR 繼續檢查」確認存活席位已就緒，再按繼續。 [暫停後繼續](PLAYER_READINESS.md#暫停後繼續)

## 記錄 Quest 遊戲內連線量測

功能支援 Quest 開發 APK 0.50.11／76 起，部署時加 `-RecordLinkMetrics`，並提供對應的 `-ReleaseReport`。以下使用 0.50.12／77 部署單席。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -ClientConfig .\room-01-seat-01.json `
  -Serial '<ADB 序號>' -ReleaseReport .\artifacts\vive-release-05012-fb9bcabe\venue-release.json -RecordLinkMetrics
```

五房部署也可在原 `-VenueBundle`、`-DeviceMap`、`-DeployMappedSeats` 指令加上同一選項。每條新連線第一次進入執行中時開始採樣。若原程序重連，讓最後一條連線採樣 30 次結案，再由主控結束任務，保留原程序的 logcat。票券更新會保留已安裝的量測設定。 [收集日誌](#收集-quest-場館驗收日誌) · [併入場館驗收](EXTERNAL_CLIENTS.md#quest-遊戲內連線量測)

有現場門檻時，封存驗收可逐席核對最低回覆數及 p95 上限。5、10、25 席總表可統一設定，個別批次也可以採用更嚴的門檻。 [設定 Quest 逐席門檻](EXTERNAL_CLIENTS.md#逐席核對-quest-連線量測門檻)

## 收集 Quest 場館驗收日誌

原程序斷線且票券過期時，可先更新同一入場的票券，再由玩家按 B 重連。 [票券更新](QUEST_RECONNECT.md#保留遊戲程序並更新票券)

在 Windows 遊戲伺服器啟動器 1.7 勾選「記錄本次玩家連線來源（場館驗收）」，或用 CLI 的 `--peer-diagnostics on` 保留 UDP 來源和戰績確認。驗收前先關閉上次場次的遊戲，再部署本場票券並重新啟動。頭盔經 USB 偵錯授權後，從 Wi-Fi 設定記下本次使用的 IPv4。每席遊戲啟動後立即用 Python 3.12 開始擷取。工具從原遊戲程序讀到成功連線才顯示 `capture-ready`。若在最終戰績前讀到該席斷線，會顯示 `capture-disconnected`，直到讀到成功重連才再次就緒。開場仍依主控台確認原入場和追蹤狀態。

```powershell
$adb = 'F:\Tools\UnityEditors\6000.3.27f1\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\adb.exe'
$serial = 'REPLACE-WITH-ADB-SERIAL'
python .\scripts\capture-quest-field-log.py --adb $adb --serial $serial `
    --connection-file .\room-01-seat-01.json --output .\room-01-seat-01-logcat.txt
```

連線檔使用該席部署時的原 JSON。每席使用自己的序號和新輸出路徑，可分開開啟擷取程序。單席與五房工具都從 `adb devices -l` 取得當次連線識別，沿用該連線查詢 PID、讀取原 `threadtime` 日誌及確認結束時的 PID。主控結束場次後，保持頭盔遊戲開啟，讓工具收完戰績和斷線記錄。工具核對戰績與原場次、玩家、房號及入場名額，確認 PID 一致後，會寫出完整日誌及 `logcatPid` 和 SHA-256 摘要。 [ADB 連線選擇](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/docs/user/adb.1.md) · [Android Logcat](https://developer.android.com/tools/logcat)

若單席部署時使用了 `-RequireOpenXR`，可在擷取指令加上 `--quest-launch-report .\quest-launch.json --quest-launch-release .\venue-release.json`。工具會在使用 ADB 前核對回條、原連線檔及發行報告，再等待原 PID 的 OpenXR 啟動標記和成功連線，符合後才顯示 `capture-ready`。完成時會回傳 `openXRVerified` 與原回條的 SHA-256。保留原回條與發行報告供戰後驗收。 [核對單場 Quest OpenXR 啟動回條](EXTERNAL_CLIENTS.md#核對單場-quest-openxr-啟動回條)

單席啟動回條 `evidenceVersion: 2` 保存連線檔伺服器位址的 SHA-256。擷取程式在 ADB 前會比對原位址及 UDP 埠。要用原端點完成戰後驗收，請使用主控公告的 IPv4 連線檔。舊回條可沿用原來的入場、埠及啟動檢查。

擷取預設最多 1,800 秒及 16 MiB，可用 `--seconds` 指定 1 至 7,200 秒。若原啟動記錄已被覆蓋、PID 更換、ADB 中斷或逾時，工具以退出碼 1 結束，保留該席已寫入的 `.partial`。ADB 連線重建後，即使序號與 PID 相同，仍須開始新一輪擷取。五房使用新資料夾補讀失敗席位。擷取只讀取 ADB 裝置清單、原遊戲程序與日誌。

正式日誌在核對完成並關閉暫存檔後才一次出現。若這段期間同名正式檔已存在，擷取會保留原檔和本輪的 `.partial`，並回報該席未完成。

把成功輸出的日誌與 IPv4、`logcatPid` 交給單場或五房驗收工具，逐席核對原 UDP 來源、伺服器確認與封存序號。票券和原日誌存放在私人資料夾。 [單場及五房驗收](EXTERNAL_CLIENTS.md#核對封存戰績與-udp-來源)

MR 場次可一併提供原部署 ZIP 中的房間校正 JSON 與關閉後的 `.worldlog`，對照當次鎖定值。 [核對 MR 校正封存](EXTERNAL_CLIENTS.md#核對-mr-校正封存)

### 一次擷取五房 Quest 日誌

使用 Python 3.12 和 PowerShell 7。各席完成部署並啟動遊戲後，提供同一份原五房 VR、MR 或混合部署 ZIP，以及部署時使用的版本 1 裝置清單。輸出資料夾須尚未建立，且其上層須已存在。

```powershell
python .\scripts\capture-quest-field-log.py --adb $adb `
    --venue-bundle .\vr-venue-connections.zip --device-map .\device-map.json `
    --output-directory .\quest-capture --seconds 1800
```

預設要求完整 25 席。若名冊混有 VIVE，使用只列 Quest 席位的部署清單並加上 `--allow-partial-map`。擷取並行執行，`venue-capture-ready` 代表依已讀取的日誌，所有選取席位最近一次連線事件仍是成功連線。若引用要求 OpenXR 的部署報告，也須讀到該次啟動的 OpenXR 記錄。斷線席會從就緒名單移除，重連後可再觸發全館就緒。任何一席讀到最終戰績或擷取失敗後，全館停止發送新的就緒通知，其餘席位繼續擷取。已入場玩家可沿用原部署包的票券資料核對日誌，包含擷取時已過期的原票券。需要重新入場時仍依遊戲伺服器的票券規則。

場次結束後，`capture-report.json` 依房號、席位及場次列出完整日誌、`logcatPid` 和 SHA-256。各席結案後會一次發布完整報告。任一席失敗時，整批回傳退出碼 1，已完成的日誌與可用的 `.partial` 各自保留。

若部署時使用發行報告核對 APK，可加 `--deployment-report .\quest-deployment.json`，指定同一份 ZIP、同一份裝置清單的完整部署結果。工具會逐席比對原入場，並在開始讀取及保存完整日誌前各讀一次裝置識別。如果 ADB 回報的裝置與原部署不同，該席不會發布完整日誌，已擷取的內容保留為 `.partial`。擷取報告只增加原部署報告的 SHA-256，裝置序號留在原私人裝置清單。 [核對發行 APK](#核對頭盔內已安裝的發行-apk)

### 部署中斷時先擷取已啟動的席位

五房部署中途停止時，可使用同一份部署 ZIP、當時的完整裝置對照表，以及最新的原未完成部署報告。用 `--capture-deployed-seats` 選取報告中已成功啟動的席位，原本使用部分對照表時加上 `--allow-partial-map`。

```powershell
python .\scripts\capture-quest-field-log.py --adb $adb `
    --venue-bundle .\vr-venue-connections.zip --device-map .\device-map.json `
    --deployment-report .\quest-deploy-first.json --capture-deployed-seats `
    --output-directory .\quest-capture-first
```

工具核對完整原對照表的指紋，再讀取已確認席位的原程序。使用 `-RequireOpenXR` 時，仍須確認原 PID 及原啟動記錄。擷取就緒訊息及報告會標記 `partialDeployment: true`，並只計算本次選取的席位。未啟動或啟動結果未確認的席位由主控繼續處理。

若使用 `-RetryIncomplete` 補完部署，用新報告作為 `--deployment-report`，把它直接承接的前一份報告傳給 `--after-deployment-report`，並指定新擷取資料夾。工具會核對直接前一份原報告的雜湊，並只擷取這次新增啟動的席位。若新部署報告仍為未完成，該次擷取也加上 `--capture-deployed-seats`。若改用獨立的部分對照表部署剩餘席位，則用該批原對照表與報告擷取。戰後提交各批原報告和日誌。 [部署重試](#從原部署報告重試未完成席位) · [合併驗收](EXTERNAL_CLIENTS.md#直接使用-quest-批次擷取報告)

### 重試未完成的 Quest 擷取席位

若 ADB 中斷後仍能讀到原遊戲程序的啟動、入場、最終戰績及結束斷線記錄，使用相同的部署 ZIP、原裝置對照表與原擷取報告重試。混合場繼續帶 `--allow-partial-map`。新輸出資料夾須尚未建立。

```powershell
python .\scripts\capture-quest-field-log.py --adb $adb `
    --venue-bundle .\vr-venue-connections.zip --device-map .\device-map.json `
    --retry-incomplete .\quest-capture\capture-report.json `
    --output-directory .\quest-capture-retry --seconds 1800
```

重試只擷取原報告中失敗的席位。擷取報告保存原部署 ZIP 的 SHA-256 和加鹽的裝置席位指紋，調整裝置表的列順序仍可重試。重新配票、重打包或更換裝置時，工具會在啟動 ADB 前拒絕沿用原報告。若首次用了 `--deployment-report`，重試須指定同一份部署原檔並沿用原席位選取選項。舊報告仍可供封存驗收。舊報告若未記錄原部署報告的 SHA-256，也沒有新版的 ZIP 與裝置指紋，請另開一次擷取。

保留首次和重試的原報告、各自的日誌及原裝置對照表。五房驗收可同時帶入裝置表與記錄實際 IPv4 的網路計畫。重試仍須取得同一個原入場的完整紀錄。混合場可在同一份驗收清單加入 Windows 席位。 [核對原始擷取報告](EXTERNAL_CLIENTS.md#直接使用-quest-批次擷取報告)

## 連線與仍待實作事項

一個桌面伺服器程序綁定一個管理場次；五房 Independent 使用各自程序／UDP 埠，全連線則使用一份 Linked 場次與共同伺服器。助手目前只產生單房 Independent 設定；Linked 名冊與票券可透過 API 建立。場景用房間原點平移安排五區，尚無實體場館對位或共用錨點。

入場時伺服器用自己的 GameServer 憑證向 API 驗證票券、目前名冊及固定席位，拒絕同一玩家的同時重複連線。票券不是一次性使用；斷線後在未過期及仍在名冊的條件下可再驗證。尚無完整重連、裝置就緒回報、已連線玩家移除時即時踢出、場次結束時主動斷線，以及伺服器崩潰恢復的整合驗證。

一般 NGO 連線尚未加入應用層加密或設備證明，票券應視為短效憑證；目前用途限受控開發 LAN。正式部署還須完成傳輸保護及權限分場強化。先以兩台 Quest 3 取得實際幀率／頻寬／延遲與拒絕案例，再推進 5／10／25 人。
