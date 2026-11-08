# Quest 3 接入與工具鏈

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
   pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -ClientConfig .\data\vr-connections\<場次ID>\player-1.json
   ```

   多台裝置須用 `-Serial` 指定；腳本核對裝置型號、只接受玩家欄位、安裝本專案 APK 並複製設定後啟動。此腳本尚未實機執行。
5. 先在 Preparing 啟動伺服器與玩家，再發 Begin；核對頭手互見、射擊／換彈、掩體與 AI／健康同步，再試 Pause、Resume、SetEnvironment 及 SetEnemies。管理資料超過 1.5 秒未更新時應停止戰鬥；所有路徑尚待實際執行。另核對 journal、批次補送與 End 封存；同一管道已有 .NET／HTTP 證據，Unity 路徑仍須實際執行。
6. 測試後以 End 結束自己建立的場次，保留歷史並釋放房間。票券過期時由有權控制台對同一玩家重新配發；不用刪除其他場次。已結束場次不能再配發或驗證。

### Quest 3 場地對位部署

先從管理台下載通過檢查的房間校正檔，再用同一房的玩家設定部署。一般部署可省略 `-AlignmentFile`。

`-CheckOnly` 可在 PowerShell 7 預檢部署檔，適合在接頭盔之前核對。以下以 MR 為例。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -CheckOnly -MixedReality `
  -ClientConfig .\player.json -AlignmentFile .\room-1-alignment.json
```

預檢回報房間、從 1 開始計算的席位、票券到期時間、選用模式及校正檔 SHA-256。以本機 UTC 檢查票券效期，並比對票券房號與校正檔，核對 A、B、C 欄位和座標範圍。預檢只讀本機檔案，輸出不含票券。遊戲伺服器仍負責驗簽及核對目前名冊，頭盔會重新計算校正並量測追蹤。票券效期為五分鐘，正式部署時請使用當場新配發的檔案。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -ClientConfig .\data\vr-connections\<場次ID>\player-1.json -AlignmentFile .\room-1-alignment.json
```

正式部署會先執行相同檢查，再把當次核對的校正檔內容複製到頭盔。玩家設定記錄該份內容的 SHA-256。頭盔讀入時核對檔案、房間和標記，再以當次 OpenXR 追蹤重新量測。量測、回到出生位與原點失效的流程見 [場地配置](LAYOUT.md#quest-3-場地對位)。ADB 實機安裝、頭盔取樣與 MR 透視列入設備驗收。

### Quest 3 透視呈現

Unity 0.43.0 的 Quest 開發版可用 `-Passthrough` 在已開啟的 VR 場次中使用 Meta 的透視合成層。部署須附同一房間的校正檔。玩家進入 Preparing 或 Paused 後量測 A、B、C，並依提示回到遊戲起點。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -ClientConfig .\data\vr-connections\<場次ID>\player-1.json -AlignmentFile .\room-1-alignment.json -Passthrough
```

透視啟用後，實景位於虛擬敵軍、擺設、雨線和 HUD 後方。遊戲的日夜與閃電影響虛擬物件照明，雷聲沿用原任務設定。遊戲仍保留地板與擺設的碰撞。合成層或校正未就緒時，頭盔暫停送出姿態與武器輸入。 [Unity 透視設定](https://docs.unity3d.com/Packages/com.unity.xr.meta-openxr@2.3/manual/features/camera.html)

透視畫面由 Meta 合成器處理。場次回放保存原虛擬世界資料。頭盔實景、實體遮擋及跨裝置定位另行驗收。

### 主控建立 MR 場次

以控制台 0.31.12 將任務的初始模式選為 MR 並保存版本。建立單房或五房全連線場次後，在 Windows 伺服器啟動器 1.4 的清單選擇該 MR 場次。MR 由專用遊戲伺服器建立 GameServer 來源，模式在建立時固定。

加入 Quest 3 玩家，為各席發票券，並準備對應房間的校正檔。同房玩家共用同一份標記配置，各自部署自己的玩家設定。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -ClientConfig .\data\vr-connections\<場次ID>\player-1.json -AlignmentFile .\room-1-alignment.json -MixedReality
```

玩家在準備中完成 A、B、C 三點量測，再回到頭盔提示的起點。主控可在「MR 開場檢查」查看各房就緒人數與等候席位。遊戲伺服器會核對票券房間和所選校正房間。全名冊的有效追蹤快照對上目前場次序號後，即可按開始。場中可調整天氣、時段及閃電。 [參戰快照](PLAYER_READINESS.md#mr-開場條件)

## 連線與仍待實作事項

一個桌面伺服器程序綁定一個管理場次；五房 Independent 使用各自程序／UDP 埠，全連線則使用一份 Linked 場次與共同伺服器。助手目前只產生單房 Independent 設定；Linked 名冊與票券可透過 API 建立。場景用房間原點平移安排五區，尚無實體場館對位或共用錨點。

入場時伺服器用自己的 GameServer 憑證向 API 驗證票券、目前名冊及固定席位，拒絕同一玩家的同時重複連線。票券不是一次性使用；斷線後在未過期及仍在名冊的條件下可再驗證。尚無完整重連、裝置就緒回報、已連線玩家移除時即時踢出、場次結束時主動斷線，以及伺服器崩潰恢復的整合驗證。

一般 NGO 連線尚未加入應用層加密或設備證明，票券應視為短效憑證；目前用途限受控開發 LAN。正式部署還須完成傳輸保護及權限分場強化。先以兩台 Quest 3 取得實際幀率／頻寬／延遲與拒絕案例，再推進 5／10／25 人。
