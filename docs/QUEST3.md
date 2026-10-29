# Quest 3 接入原型與工具鏈 v0.14

管理 API／控制台現為 v0.16，任務不可變版本保持，見 MISSION_VERSIONS。Unity 新增 tick 驅動雨景／聲音與原子 WeatherState，NGO protocol／Android code 16、bundle 0.16.0；Mission 本體仍 schema 1。後續 10 runtime／5 test 檔案已通過真正 managed SDK 型別編譯，整個 Unity 工程、NGO／ILPP、Shader／音訊匯入與 18 項 EditMode 仍待驗。最新實際 Prepare 仍因找不到有效 Editor 授權退出 198，沒有 APK／頭盔結果。效果見 [ENVIRONMENT.md](ENVIRONMENT.md)，編譯範圍見 [UNITY_SDK_CHECK.md](UNITY_SDK_CHECK.md)；下方舊版本段落保留歷次說明。

v0.14 新增每次入場識別、票券 v2／protocol 2、If-Match-Admission 與跨輪詢重入撤銷，Unity／API 需同版升級並重發舊券，見 [ADMISSION.md](ADMISSION.md)。生成器 NGO protocol 14／bundle 0.14；15 項 EditMode 仍待執行，沒有 Unity／APK／頭盔結果。

v0.13 新增共用世界來源／發布器、接受後頭手錄製、追蹤中斷與 NGO protocol 13；接入／補送見 [WORLD_SOURCE.md](WORLD_SOURCE.md)。本輪仍無 Unity 編譯／APK／頭盔證據，Prepare 實際退出 198。12 項 EditMode 只新增來源，尚未執行；C# 9 語法檢查為 23 份。

使用者指定先用 Meta Quest 3；暫按 Android 獨立執行規劃。工程在 `clients/unity/`，後端仍獨立使用 .NET 10，不把後端 DLL 放進 Unity。

## 已有程式與驗證邊界

已有場地生成器、玩家頭部／雙手及武器物件、OpenXR 瞄準／射擊／換彈、NGO 連線審核、固定出生席位，以及管理狀態／環境、任務擺設、敵軍與健康／彈藥的接入來源碼。姿態透過 NGO 傳送，不走 REST。姿態目標 20 Hz、戰鬥狀態 10 Hz 是設定值，沒有實機量測；支援範圍與未接通的報告見 `GAMEPLAY.md`。

**目前僅完成來源碼原型，沒有成功的 Unity 編譯、生成場景、EditMode 結果、桌面執行檔或 APK。** 2026-10-29 本機 Editor 已完整安裝，本輪 Prepare 仍因授權退出 198。23 份 C# 通過 C# 9 語法檢查，沒有綁定 Unity SDK；其中 embedded Runtime 另通過 .NET Standard 2.1 型別建置。399 項核心、322 項原 HTTP 及 32 項世界串流 檢查包含管理、票券、幾何核心與新任務接入層。

沒有實機互見、Unity 射擊／AI 運行證據、MR 透視／錨點、遊戲內物件編輯或頭盔任務錄製。雨線／雷聲已有 Unity 接入來源及瀏覽器 Simulation 驗證，沒有頭盔聲光結果。瀏覽器自由觀戰／鏡頭書籤已驗證；Unity 桌面觀察鏡頭固定，不能作為需求 10 的完整證據。Unity 已接入持久事件／補送來源碼，仍無實際統計整合運行證據；頻率與效能仍須量測，詳見 TELEMETRY。

embedded package `com.vrcommand.simulation` 現為 0.11.0。Runtime asmdef 已引用它，ProjectBuilder／CombatAuthority 來源碼會建立世界及同步渲染，但尚未成功執行生成器；不能將 .NET 核心通過結果當作 Unity 工程成功編譯。規則與接入分別見 `SIMULATION.md`／`GAMEPLAY.md`。

## 固定工具鏈

| 項目 | 版本／位置 |
|---|---|
| Unity Editor | 6000.3.27f1，revision `672d562a42a7` |
| 本機 Editor | `F:\Tools\UnityEditors\6000.3.27f1\Editor\Unity.exe` |
| Unity CLI | 1.0.0-beta.14，已安裝 |
| OpenXR / XR Management | 1.19.0 / 4.6.1 |
| NGO / Transport | 2.7.0 / 由 NGO 相依解析（2.6.0） |
| Input System / URP | 1.17.0 / 17.3.0（對齊固定 Editor 隨附版本） |
| Test Framework / UGUI | 1.6.0 / 2.0.0 |
| Quest 建置設定 | IL2CPP、ARM64、Vulkan、min API 32、target API 35，Development APK |

版本由官方 Unity release feed、套件 metadata 與 URP Blank 17.1.0 模板選定。後續實際檢查本機 Editor 發現隨附 URP／SRP Core 為 17.3.0，manifest 已由 17.0.4 對齊；原範本資產與授權仍保留，真正匯入／升級待 Editor 驗證。Unity 套件鎖定檔尚待第一次成功套件解析產生並提交。

新增 [managed SDK 接入檢查](UNITY_SDK_CHECK.md)：10 份 runtime 與 5 份測試來源使用官方 NGO／Input／Transport 等來源及真正 Unity DLL，在 Android／Windows 條件分支均通過型別編譯。18 個 NUnit 方法沒有執行，Editor 生成器／OpenXR／URP／ILPP／IL2CPP／APK 亦未驗證；不能把它當成整個 Unity 工程成功。

使用者已明確同意 SDK／NDK 條款；Android Build Support 與 OpenJDK 已由 CLI 安裝，SDK／NDK 目錄修復及實際原生編譯結果見下節，不再等待條款確認。

使用者另回覆已登入／啟用，但後續工具端驗證仍為 CLI `loggedIn: false`、`unity license list` 空陣列、`unity license status` 為 active=false／signedIn=false，先前實際 Prepare 退出 198。一次瀏覽器登入流程已逾時，不能繼續等待舊回呼。CLI 狀態只是診斷資訊；是否能建置仍以實際 Editor 結果為準，不因 CLI 未登入而否定有效的 Hub／浮動授權。

2026-10-29 已查核本機 Appx、解除安裝登錄與常見目錄，原先只有 Unity CLI，未找到 Hub。已補裝並啟動 **Unity Hub 3.22.5**，Appx 版本 3.22.5.65535，註冊狀態正常。Windows 管理 Hub 套件位於 C 槽；工程、Editor、Android 工具及安裝包仍在 F 槽。套件來自 Windows 套件來源列出的 Unity 官方 CDN，SHA-256 `26b4103d7784d09a1ec312058360710f01c53a5881caa1c722e692055dcb9032` 與來源相符，Authenticode 為 Valid／Unity Technologies SF。安裝包存於忽略的 `artifacts/setup/UnityHubSetup-3.22.5-x64.msix`，無須重裝 Editor／SDK。

Hub 視窗已實際出現，但 Windows 安全性對 `adb.exe` 的網路存取提示遮住畫面。由使用者自行處理提示後，在 Hub 完成 Sign in，再到 Settings → Licenses 確認有效授權。若需新增，使用者應選擇適用方案及確認條款；不預設具備 Personal 資格、不購買授權、不要求提供密碼／token／序號。此步尚待完成，沒有操作安全設定或自動登入。

Hub 授權正常後，依序執行下節 Prepare／Tests／Desktop／Quest；僅出現 Hub 視窗或網頁登入成功不算建置完成。若選擇 CLI 流程，須等待新的 `unity auth login` 成功，`unity license activate` 的方案依實際適用授權決定。官方 CLI beta.14 支援 Personal 啟用及其條款旗標，但本專案未代替使用者選擇／接受 Personal 方案。

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

可重驗 `.\scripts\check-android-toolchain.ps1`，輸出在忽略的 `artifacts/android-toolchain-check/`。這證明主要原生工具可協同工作；CLI 八個子模組的失敗登錄仍保留，Unity Editor 偵測及 APK 建置還須實際驗證。沒有把原生 `.so` 當成 APK 或 Quest 執行結果。

來源：[Unity CLI 使用方式](https://docs.unity.com/en-us/unity-cli/use-unity-cli)、[Meta Unity requirements](https://developers.meta.com/vr/documentation/unity/unity-development-requirements/)、[Unity 套件庫](https://packages.unity.com/)、[Android SDK 條款](https://developer.android.com/studio/terms)。

## 待授權就緒後執行的建置

在儲存庫根目錄執行：

```powershell
.\scripts\build-unity.ps1 -Target Prepare
.\scripts\build-unity.ps1 -Target Tests
.\scripts\build-unity.ps1 -Target Desktop
.\scripts\build-unity.ps1 -Target Quest
```

`Prepare` 建立 `Assets/VrCommand/Generated/Arena.unity`、玩家 prefab 與 XR 設定；同一路徑會重建，不應直接在生成場景加入手工內容。Tests 執行 EditMode 並要求 XML 中測試通過。Desktop 輸出 `artifacts/desktop/VrCommand.exe`，Quest 輸出 `artifacts/quest/VrCommand.apk`。腳本檢查退出碼及本次輸出時間，日誌與結果位於 `artifacts/unity-logs/`。成功編譯後仍須執行下列雙玩家檢查。

無授權時可先執行 `.\scripts\check-unity-source.ps1`，但只能回報語法檢查結果。不得把其輸出視為可執行的 Unity 工程。

## 區域網路原型操作

以下步驟尚未完成 Unity 執行與頭盔驗證。管理 API 預設留在伺服器本機 `127.0.0.1:5080`；頭盔只連遊戲伺服器的 UDP 7777。同一場館網路與防火牆須允許該連線；此原型沒有遠端中繼或網際網路部署。

1. 用 `.\scripts\start-local.ps1` 啟動 API，保留其視窗。
2. 建置桌面與 Quest 後，再產生連線資料，避免票券在建置期間到期：

   ```powershell
   python scripts/prepare-vr-session.py --server-address 192.168.1.100 --room 1 --players 2
   ```

   把範例 IP 換成頭盔能連到的桌面 LAN IP。助手只在空閒房間新建自己的 Independent 場次，保留 `Preparing`，輸出場次 ID 與 `data/vr-connections/<場次ID>/` 路徑。`server.json` 含 GameServer 憑證，只留在桌面；`player-1.json`／`player-2.json` 各含自己的五分鐘票券，不含控制台憑證。
3. 啟動桌面伺服器（請替換 GUID 路徑）：

   ```powershell
   & .\artifacts\desktop\VrCommand.exe --vr-config F:\Projects\vr-command-center\data\vr-connections\<場次ID>\server.json
   ```

   同一台桌面可用另一份玩家設定啟動 Client，WASD／按住滑鼠右鍵僅供桌面預覽；這不是 VR 移動功能驗收。
4. Quest 3 須開啟開發者模式，USB 連接並在頭盔內授權 ADB。部署每台不同玩家設定：

   ```powershell
   .\scripts\deploy-quest.ps1 -ClientConfig .\data\vr-connections\<場次ID>\player-1.json
   ```

   多台裝置須用 `-Serial` 指定；腳本核對裝置型號、只接受玩家欄位、安裝本專案 APK 並複製設定後啟動。此腳本尚未實機執行。
5. 先在 Preparing 啟動伺服器與玩家，再發 Begin；核對頭手互見、射擊／換彈、掩體與 AI／健康同步，再試 Pause、Resume、SetEnvironment 及 SetEnemies。管理資料超過 1.5 秒未更新時應停止戰鬥；所有路徑尚待實際執行。另核對 journal、批次補送與 End 封存；同一管道已有 .NET／HTTP 證據，Unity 路徑仍須實際執行。
6. 測試後以 End 結束自己建立的場次，保留歷史並釋放房間。票券過期時由有權控制台對同一玩家重新配發；不用刪除其他場次。已結束場次不能再配發或驗證。

## 連線與仍待實作事項

一個桌面伺服器程序綁定一個管理場次；五房 Independent 使用各自程序／UDP 埠，全連線則使用一份 Linked 場次與共同伺服器。助手目前只產生單房 Independent 設定；Linked 名冊與票券可透過 API 建立。場景用房間原點平移安排五區，尚無實體場館對位或共用錨點。

入場時伺服器用自己的 GameServer 憑證向 API 驗證票券、目前名冊及固定席位，拒絕同一玩家的同時重複連線。票券不是一次性使用；斷線後在未過期及仍在名冊的條件下可再驗證。尚無完整重連、裝置就緒回報、已連線玩家移除時即時踢出、場次結束時主動斷線，以及伺服器崩潰恢復的整合驗證。

一般 NGO 連線尚未加入應用層加密或設備證明，票券應視為短效憑證；目前用途限受控開發 LAN。正式部署還須完成傳輸保護及權限分場強化。先以兩台 Quest 3 取得實際幀率／頻寬／延遲與拒絕案例，再推進 5／10／25 人。
