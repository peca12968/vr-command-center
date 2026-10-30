# Quest 3 接入原型與工具鏈 v0.20

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

`Prepare` 首次建立 `Assets/VrCommand/Generated/Arena.unity`、玩家 prefab 與 XR 設定，之後重用保存的網路識別；需重建時明確執行 RebuildArena，並一起重建所有平台。Tests 要求新 XML 至少 46 項全數通過。Desktop 輸出 `artifacts/desktop/VrCommand.exe`（須連同整個資料夾使用），Quest 輸出 `artifacts/quest/VrCommand.apk`。腳本檢查 exit 0／1，Desktop／Quest 另核對本次成功 BuildReport 的新 build-receipt.json，日誌在 `artifacts/unity-logs/`。PC 自動 smoke 與限制見 NATIVE_VALIDATION，下方頭盔步驟仍待設備。

無授權時可先執行 `.\scripts\check-unity-source.ps1`，但只能回報語法檢查結果。不得把其輸出視為可執行的 Unity 工程。

## 區域網路原型操作

以下頭盔與區域網路操作仍待驗證；目前僅有同機 Windows server／雙 client 的實際執行證據。管理 API 預設留在伺服器本機 `127.0.0.1:5080`；頭盔只連遊戲伺服器的 UDP 7777。同一場館網路與防火牆須允許該連線；此原型沒有遠端中繼或網際網路部署。

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
