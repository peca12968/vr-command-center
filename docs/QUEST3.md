# Quest 3 接入與工具鏈

## 追蹤恢復後的武器輸入

遊戲 0.48.1 在應用程式及 OpenXR 工作階段均有輸入焦點時才處理頭盔操作。系統選單或應用程式暫停期間會停止發布本機追蹤姿態。返回遊戲後，右手扳機、換彈鍵及 B 重連鍵各自需要先放開，再按下。 [Unity OpenXR 焦點介面](https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/api/UnityEngine.XR.OpenXR.OpenXRUtility.html#UnityEngine_XR_OpenXR_OpenXRUtility_IsSessionFocused)

MR 量測中失去焦點會清除尚未完成的 A／B／C 取樣。返回後從 A 開始，在每個標記先放開再按左扳機。單純失去焦點會保留已完成的校正，應用程式暫停或追蹤原點改變則需重新校正。主控仍可按原流程查看席位追蹤狀態，並決定何時暫停或繼續。

遊戲 0.47.1 在頭盔追蹤中斷、場地校正失效、姿態遭拒或暫停時撤下武器輸入。恢復參戰後，請在追蹤有效時先放開右手扳機與換彈鍵，再重新按下。狀態板會提示 `RELEASE TRIGGER AND RELOAD TO ARM`。連續按住扳機的射擊節奏從下一次主動按下起算。

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

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -ClientConfig .\data\vr-connections\<場次ID>\player-1.json -AlignmentFile .\room-1-alignment.json
```

正式部署會先執行相同檢查，再把當次核對的校正檔內容複製到頭盔。玩家設定記錄該份內容的 SHA-256。頭盔讀入時核對檔案、房間和標記，再以當次 OpenXR 追蹤重新量測。量測、回到出生位與原點失效的流程見 [場地配置](LAYOUT.md#quest-3-場地對位)。ADB 實機安裝、頭盔取樣與 MR 透視列入設備驗收。

### 直接使用 VR 五房連線 ZIP

管理包 0.31.42 可核對從「VR 五房配票」下載的原始 `vr-venue-connections.zip`。部署工具讀取 ZIP 裡的 25 份原連線檔，核對房間、席位、場次、端點及本機效期。先在 PowerShell 7 離線預檢，或用 `-RoomId`、`-Seat` 查看指定席位。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\vr-venue-connections.zip
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\vr-venue-connections.zip -RoomId 4 -Seat 2 -CheckOnly
```

正式寫入 VR 設定前須提供 `-ManagementApi` 與主控環境變數 `VR_COMMAND_MASTER_KEY`。工具把原檔送給管理服務，逐席驗簽並核對現行名冊及公告端點。指定單席或使用裝置清單時，要寫入的席位須登記為 Quest 3，並對上各自已授權且已安裝指定 APK 版本的裝置。混合 VIVE 與 Quest 的名冊可用小批次部署指定 Quest 席位。 [小批次操作](#部署指定的-quest-席位)

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\vr-venue-connections.zip `
  -RoomId 4 -Seat 2 -Serial YOUR_ADB_SERIAL -ManagementApi http://127.0.0.1:5080
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\vr-venue-connections.zip `
  -DeviceMap .\quest-devices.json -ExpectedVersionCode 62 -ManagementApi http://127.0.0.1:5080 -CheckOnly
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\vr-venue-connections.zip `
  -DeviceMap .\quest-devices.json -ExpectedVersionCode 62 -ManagementApi http://127.0.0.1:5080 -DeployMappedSeats
```

裝置清單格式與 MR 相同。整批 VR 部署把各席的四欄連線設定寫到對應裝置並請求啟動，現場頭盔的入場與追蹤仍須另外觀察。連線檔與主控金鑰請私下保管。 [VR 五房配票](EXTERNAL_CLIENTS.md#vr-五房配票) · [裝置清單格式](#用裝置清單部署-25-席)

### 混合 VR 與 MR 五房部署包

管理包 0.31.47 可從五個獨立場次一次下載混合部署包。各房先登記五席並啟動自己的遊戲伺服器，五房使用不同的場館 IPv4／UDP 端點。MR 房的五席皆登記為 Quest 3，並在啟動伺服器前鎖定該房校正檔。

以主控登入「房間與場次」，在「VR／MR 混合五房配票」按「讀取五房名冊」。核對各房的模式、名冊及端點，只為 MR 房選擇已鎖定的原始校正 JSON，然後下載 `vr-mr-venue-deployment.zip`。包內有 `venue.json`（版本 2、`Mixed`、`Independent`）、五個房間的連線 ZIP，以及各 MR 房的原始校正檔。票券自簽發起有效五分鐘，整包由主控保管。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\vr-mr-venue-deployment.zip
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\vr-mr-venue-deployment.zip `
    -DeviceMap .\quest-batch.json -ExpectedVersionCode 62 -AllowPartialMap `
    -ManagementApi http://127.0.0.1:5081 -CheckOnly
```

完成預檢後可改用 `-DeployMappedSeats` 套用，或指定 `-RoomId`、`-Seat` 及 `-Serial` 部署一席。正式部署須提供主控金鑰與管理服務網址，先核對 25 席的簽章、名冊、端點及 MR 校正檔。VR 席使用原始四欄連線設定。MR 席另寫入原校正檔並啟用透視。Quest 裝置清單只列當次要部署的 Quest 3 席位。 [指定席位操作](#部署指定的-quest-席位)

主控 API 使用 `GET /api/mixed-deployment/venue` 預覽、`POST /api/mixed-deployment/venue-bundle` 配票、`POST /api/mixed-deployment/venue-check` 驗票。各次請求使用當時同一次讀取的場次與端點。全 VR 或全 MR 場館仍使用各自的部署入口。

### 五房 25 席部署預檢

#### 從主控台下載五房部署包

1. 使用管理包 0.31.29 或更新版。在五房各登記五個 Quest 3 席位、鎖定各房校正檔，並啟動遊戲伺服器，等它公布場館 IPv4 與 UDP 埠。合併模式用一個端點，五房獨立各用不同端點。
2. 以主控登入「房間與場次」，選取合併 MR 場次或任一獨立 MR 場次。在「Quest 3 MR 五房部署包」依房號選取五份鎖定的原始校正 JSON，按「下載五房部署包 ZIP」。畫面會提示場次、端點、名冊或校正檔有問題的房間。
3. 保留 `quest-mr-venue.zip`，可直接預檢或為指定席位部署。外層 ZIP 包含五個房間連線 ZIP、五份校正原檔及 `venue.json`。由主控保管整包，入場票券自簽發起有效五分鐘。

管理 API `POST /api/mr-deployment/venue-bundle` 限主控。請求包含 `topology`，以及五筆 `rooms`，各有 `roomId`、`sessionId`、五個 `players`（`playerId`、`admissionId`）及 Base64 的 `alignmentFile`。服務按同一次讀取的場次和端點驗證五房，完整通過後以 `Cache-Control: no-store` 回傳 ZIP。場次、校正原檔、端點或當前名冊不符時回傳 `409` 及房號，無法取得部分部署包。裝置安裝和場館 UDP 可達性仍需實測。

#### 直接用 ZIP 預檢或部署單席

直接使用管理台下載的原始 ZIP。省略房號與席位會讀取全部 25 席並輸出預檢結果。指定房號與席位並加上 `-CheckOnly`，會輸出該席的到期時間與校正雜湊。兩種預檢皆只讀檔，不呼叫 ADB。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\quest-mr-venue.zip
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\quest-mr-venue.zip `
    -RoomId 4 -Seat 2 -CheckOnly
```

接好已授權 USB 偵錯的 Quest 3，核對實體標籤與 ADB 裝置序號。房號和席位從 1 開始。正式部署須指定 `-Serial`，只會對該裝置安裝專案 APK、複製對應席位設定與該房原始校正檔，再啟動應用程式。以下用實際序號替換 `YOUR_ADB_SERIAL`。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\quest-mr-venue.zip `
    -RoomId 4 -Seat 2 -Serial YOUR_ADB_SERIAL
```

任一席位過期、場次或校正檔不符時，整份 ZIP 預檢失敗，應從主控下載當前部署包。也可沿用下方 `-ManagementApi` 與 `VR_COMMAND_MASTER_KEY`，把範例的 `-VenueManifest .\venue.json` 換成 `-VenueBundle .\quest-mr-venue.zip`。ZIP 線上模式另會比對每個場次目前公布的 UDP 端點，裝置操作前須全數核對成功。

#### 用裝置清單部署 25 席

先在各台 Quest 3 安裝同一版場館 APK 並授權 USB 偵錯。已驗證的開發 APK `0.48.1` 版本代碼為 `62`。建立 25 席清單後，依實體標籤把每個 `REPLACE-*` 換成對應的 ADB 裝置序號。每組房號與席位須對應一個唯一序號，清單只保存在操作電腦。腳本透過 `adb devices` 及 Android 套件管理器讀取授權狀態與已啟用的應用程式版本。 [Android ADB 文件](https://developer.android.com/tools/adb) · [套件管理器版本輸出](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/services/core/java/com/android/server/pm/PackageManagerShellCommand.java#1130)

```powershell
$seats = foreach ($room in 1..5) {
    foreach ($seat in 1..5) {
        @{ roomId = $room; seat = $seat; serial = "REPLACE-$room-$seat" }
    }
}
@{ version = 1; seats = @($seats) } | ConvertTo-Json -Depth 4 |
    Set-Content -LiteralPath .\device-map.json -Encoding utf8
```

用原始部署 ZIP 與清單預檢。每席會回報裝置狀態和已讀到的版本。缺席、離線、未授權、型號或版本不符時，指令回傳非零結束碼。只有 `-DeployMappedSeats` 會寫入裝置。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\quest-mr-venue.zip `
    -DeviceMap .\device-map.json -ExpectedVersionCode 62 -CheckOnly
```

正式套用時，先依下方方式設定 `VR_COMMAND_MASTER_KEY`，再加入 `-DeployMappedSeats` 與管理服務網址。所有裝置與票券核對通過後，工具依房號與席位順序寫入設定並請求啟動，使用各台已安裝的 APK。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\quest-mr-venue.zip `
    -DeviceMap .\device-map.json -ExpectedVersionCode 62 -DeployMappedSeats `
    -ManagementApi http://127.0.0.1:5081
```

中途失敗會停止並以非零結束碼回報。`launch-requested` 表示裝置已收到啟動指令，`deployment-failed` 的席位可能已套用部分檔案，`not-attempted` 表示該席未寫入。已處理席位保留當下結果。可按回報定位故障，必要時重新配發票券，再用單席流程處理尚未成功的裝置。啟動後可回到場次面板，或執行[核對頭盔追蹤席位](#核對頭盔追蹤席位)。

#### 部署指定的 Quest 席位

使用原五房 VR、MR 或混合部署 ZIP。版本 1 的 `device-map.json` 只列這次要部署的 1 至 25 席，房號、席位和 ADB 序號的格式維持相同。加上 `-AllowPartialMap` 即可接受少於 25 席的清單。未指定此選項時，清單仍須有完整 25 席。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\vr-venue-connections.zip `
    -DeviceMap .\quest-batch.json -ExpectedVersionCode 62 -AllowPartialMap `
    -ManagementApi http://127.0.0.1:5081 -CheckOnly
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\vr-venue-connections.zip `
    -DeviceMap .\quest-batch.json -ExpectedVersionCode 62 -AllowPartialMap `
    -ManagementApi http://127.0.0.1:5081 -DeployMappedSeats
```

正式套用前仍會核對 ZIP 的全部 25 份連線檔、簽章、現行名冊和公告端點。MR 同時核對原鎖定校正檔。任何票券過期或名額已更換時，請從主控下載新的 ZIP。混合 VR 名冊中，已列入清單的席位都須登記為 Quest 3。工具只查詢清單中的裝置型號與 APK 版本，只寫入及啟動這些裝置。部署報告的 `mappedSeats` 和 `unmappedSeats` 分別表示本次有列入及未列入的席位數。

#### 核對頭盔追蹤席位

部署並戴上頭盔後，在主控電腦用原五房 ZIP 與既有 `VR_COMMAND_MASTER_KEY` 核對目前追蹤席位。可用 VR、MR 或混合 ZIP。工具先由管理服務核對 25 份原連線檔，再按原場次各讀一次就緒快照。未指定清單時檢查所有 Quest 3 席位。要查看一批指定席位，加入 `-DeviceMap .\quest-batch.json -AllowPartialMap`。此操作用清單選擇房號與席位，不呼叫 ADB。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -VenueBundle .\vr-venue-connections.zip `
    -ManagementApi http://127.0.0.1:5081 -VerifyTrackedSeats
```

`tracked-ready` 要求同一場次、玩家及當次入場名額、已套用的場次序號、管理服務判定為 `Fresh` 的快照，以及可參戰的 `Tracked` 姿態。MR 另確認遊戲伺服器使用有效 MR 來源設定。報告含各席房號、席位、狀態與其世界序號，所有已選席位就緒時才回傳 `complete: true` 與退出碼 0。

| 狀態 | 現場核對 |
| --- | --- |
| `awaiting-tracked-pose`、`not-tracked` | 檢查頭盔有無進入遊戲、恢復焦點並完成 MR 取點 |
| `source-not-fresh`、`source-revision-pending`、`mr-profile-pending` | 查看遊戲伺服器及房卡，等有效快照套用目前的場次狀態 |
| `seat-unavailable`、`admission-changed`、`seat-headset-mismatch` | 核對當前名冊與所選席位，重新下載有變更的部署包 |
| `readiness-unavailable`、`readiness-invalid` | 核對管理服務連線、版本與場次 |

票券到期後可從主控下載新的 ZIP 供核對。報告反映各場讀取時的狀態，實際裝置序號、網路來源及全館持續容量另由現場驗收確認。 [收集 Quest 場館驗收日誌](#收集-quest-場館驗收日誌)

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

## 收集 Quest 場館驗收日誌

在 Windows 遊戲伺服器啟動器 1.7 勾選「記錄本次玩家連線來源（場館驗收）」，或用 CLI 的 `--peer-diagnostics on` 保留 UDP 來源和戰績確認。驗收前先關閉上次場次的遊戲，再部署本場票券並重新啟動。頭盔經 USB 偵錯授權後，從 Wi-Fi 設定記下本次使用的 IPv4。每席遊戲啟動後立即用 Python 3.12 開始擷取。看到 `capture-ready` 後，依主控台原開場條件確認玩家入場和追蹤狀態。

```powershell
$adb = 'F:\Tools\UnityEditors\6000.3.27f1\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\adb.exe'
$serial = 'REPLACE-WITH-ADB-SERIAL'
python .\scripts\capture-quest-field-log.py --adb $adb --serial $serial `
    --connection-file .\room-01-seat-01.json --output .\room-01-seat-01-logcat.txt
```

連線檔使用該席部署時的原 JSON。每席使用自己的序號和新輸出路徑，可分開開啟擷取程序。工具鎖定遊戲 PID，持續保存原 `threadtime` 行，保留同一程序的重連。主控結束場次後，保持頭盔遊戲開啟，讓工具收完戰績和斷線記錄。工具核對戰績與原場次、玩家、房號及入場名額，確認 PID 一致後，會寫出完整日誌及 `logcatPid` 和 SHA-256 摘要。 [Android Logcat](https://developer.android.com/tools/logcat) · [PID 篩選](https://android.googlesource.com/platform/system/logging/+/f3568188d89e74f1202d4266c587ecb4cf027df4/logcat/logcat.cpp)

擷取預設最多 1,800 秒及 16 MiB，可用 `--seconds` 指定 1 至 7,200 秒。若原啟動記錄已被覆蓋、PID 更換、ADB 中斷或逾時，工具以退出碼 1 結束，保留已寫入的 `.partial` 供診斷。擷取只使用 ADB 讀取遊戲程序與日誌。

把成功輸出的日誌與 IPv4、`logcatPid` 交給單場或五房驗收工具，逐席核對原 UDP 來源、伺服器確認與封存序號。票券和原日誌存放在私人資料夾。 [單場及五房驗收](EXTERNAL_CLIENTS.md#核對封存戰績與-udp-來源)

MR 場次可一併提供原部署 ZIP 中的房間校正 JSON 與關閉後的 `.worldlog`，對照當次鎖定值。 [核對 MR 校正封存](EXTERNAL_CLIENTS.md#核對-mr-校正封存)

### 一次擷取五房 Quest 日誌

使用 Python 3.12 和 PowerShell 7。各席完成部署並啟動遊戲後，提供同一份原五房 VR、MR 或混合部署 ZIP，以及部署時使用的版本 1 裝置清單。輸出資料夾須尚未建立，且其上層須已存在。

```powershell
python .\scripts\capture-quest-field-log.py --adb $adb `
    --venue-bundle .\vr-venue-connections.zip --device-map .\device-map.json `
    --output-directory .\quest-capture --seconds 1800
```

預設要求完整 25 席。若名冊混有 VIVE，使用只列 Quest 席位的部署清單並加上 `--allow-partial-map`。擷取並行執行。看到 `venue-capture-ready` 代表清單各席都已讀到對應程序的啟動記錄，再依管理台確認入場及追蹤後開場。已入場玩家可沿用原部署包的票券資料核對日誌，包含擷取時已過期的原票券。需要重新入場時仍依遊戲伺服器的票券規則。

場次結束後，`capture-report.json` 依房號、席位及場次列出完整日誌、`logcatPid` 和 SHA-256。任一席失敗時，整批回傳退出碼 1，已完成的日誌與可用的 `.partial` 各自保留。依報告取用完整日誌，再加入各頭盔實際使用的 IPv4，交給場館驗收工具比對伺服器端紀錄。 [五房驗收清單](EXTERNAL_CLIENTS.md#一次核對五房-25-席)

## 連線與仍待實作事項

一個桌面伺服器程序綁定一個管理場次；五房 Independent 使用各自程序／UDP 埠，全連線則使用一份 Linked 場次與共同伺服器。助手目前只產生單房 Independent 設定；Linked 名冊與票券可透過 API 建立。場景用房間原點平移安排五區，尚無實體場館對位或共用錨點。

入場時伺服器用自己的 GameServer 憑證向 API 驗證票券、目前名冊及固定席位，拒絕同一玩家的同時重複連線。票券不是一次性使用；斷線後在未過期及仍在名冊的條件下可再驗證。尚無完整重連、裝置就緒回報、已連線玩家移除時即時踢出、場次結束時主動斷線，以及伺服器崩潰恢復的整合驗證。

一般 NGO 連線尚未加入應用層加密或設備證明，票券應視為短效憑證；目前用途限受控開發 LAN。正式部署還須完成傳輸保護及權限分場強化。先以兩台 Quest 3 取得實際幀率／頻寬／延遲與拒絕案例，再推進 5／10／25 人。
