# 開發指引

2026-10-29 使用者已確認 Hub 有效授權，真正 Editor 已成功 Prepare、執行 34 項 EditMode，並產出同源 Windows 播放器與 ARM64／IL2CPP Quest APK；舊 CLI／198 是歷史狀態，不再當作目前阻礙。已有真正 PC 視窗的方向鍵／Space／滑鼠射擊、擊殺／命中率、換彈／暫停與封存證據；練習場操作見 docs/DESKTOP.md。沒有頭盔連線／實測證據。最新二進位與觀戰延遲修正驗證以 PROGRESS／實際 build log 為準，不能拿 SDK 檢查代替。

當前遊戲端 v0.18.0／Android code 18／NGO protocol 18，API 仍 0.16.0、驗票 protocol 2。Prepare 可在保存 Arena 上從 16／17 升至 18，不能改 file ID；全部遊戲程序一起更新。PC 撤銷／重連與已接受 Simulated 姿態的 admission 快取見 docs/RECONNECT.md。真正視窗已驗證強制離線後 0.65 公尺外位置與健康／彈藥保持，仍非頭盔／server 崩潰恢復。

Transport 2.7.4 固定官方來源嵌入 Packages/com.unity.transport，只修失敗 receive completion 釋放 buffer；保留通知／逐檔雜湊，以 python scripts/check-transport-patch.py 驗證，不改 Library 快取或安全設定。UPM lock 為 embedded，receipt 指紋包含嵌入 C#／asmdef／UPSTREAM.json。來源及原生反例見 docs/TRANSPORT_PATCH.md；29 Tests 含真正 Windows 小佇列 UDP 回歸。scripts/check-unity-admission.py 使用自有隔離資料／憑證，--interactive 才驗證原程序按鈕／鍵鼠，不可注入姿態取代。

桌面碰撞見 docs/DESKTOP_COLLISION.md：ArenaWalkSurface 與權威／AI 共用 0.3m 足跡及 0.05m 線段取樣，只有 untracked 桌面預測裁切／拒絕後回到接受姿態，不能搬動 Tracked XR。CombatPropState 新增 room 是 NGO 18 wire 變更；API 0.16／驗票 2 保持。build-unity Tests 門檻 34。真正鍵盤四階段、五房／Linked、重連及同源雙平台證據以 PROGRESS 為準。

Prepare 必須重用已保存 Arena／PlayerAvatar 的本地 file ID；先前每次重建新 scene 會改變 NGO 識別、破壞跨目標連線。需重建時用 RebuildArena 並一起重建全部玩家；不能 Desktop／Quest 分別重建不同場景。生成物、OpenXR 設定與 packages-lock.json 應隨成功匯入結果保存。ProjectGeneration 測試涵蓋重複 Prepare 識別、非零 hash、場景／音訊引用與 Android XR 設定；build-unity Tests 門檻為 34，腳本明確回傳 exit 0／1。

生成器另外有 scripts/check-unity-editor-sdk.py --offline --verify-missing-reference：重新檢查 Windows player 基線，再以真正 Editor／XR SDK 綁定 ProjectBuilder，直接讀自己的 asmdef 參考、禁止隱含傳遞 ProjectReference。MetaQuestFeature 位於 Unity.XR.OpenXR.Features.MetaQuestSupport，Editor asmdef 必須直接參考它；反例只修改生成的診斷 csproj，應重現 CS0234。此圖明確不含 URP 專用驗證分支（見報告），不是完整 Editor／UPM／資產生成／ILPP／APK 證據。範圍見 docs/UNITY_SDK_CHECK.md。

Unity 接入另有 scripts/check-unity-sdk.py（Windows／Python 3.12+），以官方固定來源與真正 Editor DLL 編譯 11 runtime／9 test 檔案的 Android／Windows 分支；UnityTest 引用真正匯入的 Library/ScriptAssemblies/UnityEngine.TestRunner.dll，不使用 stub。快取與報告在 artifacts/unity-sdk-check，--offline 會拒絕來源 hash 改動。這不是 Unity CompilationPipeline、Editor／UPM／ILPP／EditMode／APK；不要部署診斷 DLL。manifest URP 已對齊 Editor 隨附 17.3.0，Collections 診斷 pin 2.4.3；此較窄圖仍用 registry Transport 2.6.0，不驗證正式嵌入修正。範圍與剩餘驗收見 docs/UNITY_SDK_CHECK.md；舊語法／單一天氣型別檢查仍只是較窄證據。

v0.16 聲光規範見 docs/ENVIRONMENT.md：EnvironmentPresentation 為共用 tick 規則，header.environmentVersion 缺少保持 legacy 0、新來源 1，不補造舊音效；保留 binary 原始 header／checksum，以 codec 正規化比較。API／UI／來源一起升級，NGO protocol／Android code 16、bundle 0.16.0，18 項 EditMode 待驗。單一 UnityWeatherView 已綁真正 Core／Audio DLL 通過，不代表整個 Unity／NGO／shader／音訊匯入或 APK。新增天氣檢查需設 VR_COMMAND_CHECKS_DLL 指向同次隔離建置，聲音素材以 generate-weather-audio.py --check 驗證。

觀戰精確數值控制在 world-camera-form.js，操作見 docs/OBSERVER_CAMERA.md；欄位為看向目標、度數與距離，套用不自動保存。快照不蓋草稿，登出／換錄製清空，同場回放不清。camera-controls.cjs 由一般／native 檢查器共用；不可將軟體 WebGL 或33項整合當人工GPU／頭盔證據。

開發根目錄為 `F:\Projects\vr-command-center`；以此庫的實際 Git 狀態與執行結果為準。

五房 PC 工具為 scripts/start-desktop-venue.py，操作見 docs/DESKTOP_VENUE.md。--check 啟動五個真正獨立 server／每房一個 client，驗證隔離／權限、單房重用，再於全部 End／精確封存後開新 Linked 世界；不合併歷史。F 為 USB 硬碟，五房資料全放 F 的原生試跑未達 1.5 秒門檻；成功證據為明確 --runtime-root 指向 C NVMe 的全新自有 SQLite／journal，來源及 binary 仍在 F，不得稱為 F USB 或跨機／25 台通過。全部 writer 停止後才複製 runtime-snapshot 回 F，保留原件；不可搬動既有預覽資料。每程序 job workers=2 已記錄，降低 workers 本身未修復 F 延遲。最終七場最大取樣來源年齡 0.275004 秒、回放／報表一致；可操作模式關窗五場共 4037 幀封存。來源與頭手仍 Simulation。

操作員自訂 PC 流程為 scripts/start-desktop-control.py，操作見 docs/DESKTOP_CONTROL.md。僅監看自己新建的隔離 API，全新 Preparing VR、無既有 combat source 才啟動 server；名冊以 playerId＋admissionId 啟停短效票券 client，玩家不持有控制台／GameServer key。dynamicRoster 最終按持久 PlayerJoined 分頁核對所有歷史玩家，不只看目前名冊。operator-status 來自真正世界幀，維持 UTC 1.5 秒門檻。tests/browser/check-operator-native.cjs 需要該次 ready.json，15 項 UI／native／動態名冊／回放通過；不是一般 Linux CI 或頭盔測試。Native 白天／雨夜／Pause 截圖與 Chromium SwiftShader 觀戰分開；不能把 lightning=true 或 Web Audio 當原生閃電／雷聲聽感。

開始接續工作時讀取 `docs/PROGRESS.md`、`docs/ROADMAP.md`、`docs/REQUIREMENTS.md`。使用者的完整目標為 11 項 VR/MR 遊戲需求及 VIVE XR／Quest 3 相容性，不能以管理原型或模擬測試通過替代完整交付。

後端為 .NET 10；Unity 工程位於 `clients/unity/`，固定 Editor 6000.3.27f1，不直接引用後端組件。未知硬體協議使用模擬器，實機整合待廠商文件及設備。

使用者已指定先用 Meta Quest 3；優先推進 Quest 3 的 Android 垂直切片，VIVE 相容性留待後續。模擬戰鬥必須使用 Simulation 標記，不能與 GameServer 資料在同場混用或宣稱頭盔實測完成。

`/api` 端點使用伺服器配發的主控／房間控制台身分。實作新路由時必須傳遞認證身分並檢查操作範圍，不能依賴核心的預設 Internal 身分處理 HTTP 請求。測試用獨立的暫存憑證；不要讀出或提交 `data/operator-keys.local.json`。

後端變更應執行：

```text
dotnet restore VrCommand.slnx --locked-mode
dotnet build VrCommand.slnx --configuration Release --no-restore
dotnet run --project tests/VrCommand.Checks --configuration Release --no-build
python scripts/smoke_api.py
```

`VrCommand.Checks` 是可執行的規則檢查程式，不能只執行 `dotnet test` 就宣稱已完成檢查。依功能實際影響補充有意義的測試，並將驗證結果、限制與下一步更新至 `docs/PROGRESS.md`。

遊戲事件、即時狀態、統計與回放應共享版本化契約；頭盔姿態與逐幀模擬不使用管理 REST API。實機相容、MR 校正、25 台頭盔效能與硬體控制須分別保留驗收證據。

瀏覽器主控台在 `src/VrCommand.Api/wwwroot/console/`，操作與真實瀏覽器檢查見 `docs/CONSOLE.md`。UI 變更執行 `tests/browser/check.cjs`，使用隔離 API 與測試憑證；檢視 `artifacts/console/` 截圖。瀏覽器沒有持久化控制台憑證，保持每次 API 授權與房間範圍；不能用 UI 隱藏按鈕替代後端檢查。平面配置已有任務／Unity 接入來源碼，但尚無 Unity 運行證據。

共用射擊／AI、ArenaSession 及 TelemetryOutbox 唯一來源在 `clients/unity/Packages/com.vrcommand.simulation/Runtime/`；.NET Standard 2.1 建置入口是 `src/VrCommand.Simulation`。保持 C# 9 與無 Unity／.NET 10 相依。SimulationDemo 與 TelemetryRelay 示範一律使用 Simulation。Unity 的遊戲及補送接入已有來源碼，仍未編譯運行；不得將 .NET 管道通過當作頭盔報表整合成功。規則／接入／管道見 SIMULATION、GAMEPLAY、TELEMETRY。

Windows 執行中的本機 API 可能鎖住一般輸出 DLL；採 SIMULATION 文件的 `--artifacts-path` 隔離建置，不為測試任意停止現有服務。HTTP／瀏覽器檢查可用 `VR_COMMAND_API_DLL` 指定隔離 API，HTTP 另以 `VR_COMMAND_SIMULATION_DEMO_DLL` 指定同次建置的示範工具。

Quest 接入與建置見 `docs/QUEST3.md`。`scripts/check-unity-source.ps1` 只檢查 C# 9 語法，不能代替 Unity 編譯與 EditMode。Editor 與 Android 工具已安裝至 F 槽，使用者已明確同意 SDK／NDK 條款，不再要求相同確認或盲目重裝。Hub 3.22.5 已安裝，使用者完成本機授權確認後，真正 Editor 已可編譯／建置；先前 CLI 無 session／198、過期回呼與 Windows 提示均只保留為歷史診斷。不要自動操作登入／安全性提示，不因 CLI 狀態否定已通過的 Editor 建置。

3D 模擬回放在 `replay-*.js`，資料與操作見 `docs/REPLAY.md`。維護 schema 2／rules 0.8.0、明確 Simulation 來源、射線與快照／統計的一致性。`tests/browser` 的 test 會執行資料驗證與軟體 WebGL 檢查，不能視為真實 GPU、Unity 或頭盔測試。Three.js 上游原始檔、MIT 及 provenance 一併保留，不混入 CDN 執行相依。

頭盔只配置短效玩家票券；GameServer 憑證僅存桌面伺服器設定。所有 `data/`、`artifacts/`、Unity 快取與本機憑證均不得提交。生成場景、APK 或桌面程式須有實際成功結果，不能以來源碼存在宣稱完成。

v0.9 的建立／加入／離開以選用 Idempotency-Key 去重，事件 schema 4 的 requestId 與業務事件一起持久化；重試只確認歷史接受，不重施新狀態。保留 schema 1–3 讀取與不帶 key 的相容性。前端與後端需一起升級，不能把 v0.9 的可重試前端放到忽略 key 的舊後端；寫入新 schema 後不可直接降版。契約見 SESSION_PROTOCOL。

v0.11 新事件 schema 5，讀取 schema 1–4；戰鬥串流綁定唯一來源／origin，接受有 Running 觀察位置的已保存尾端，封存後只允許既有報告去重確認。End 釋放房間但 pendingTelemetry 保持 true 到精確 seal；不能把未封存報表當作最終結果。批次可能已提交前綴，須原樣重試。journal 壞尾端不自動截斷；補送不是世界恢復。HTTP 隔離檢查另設 VR_COMMAND_TELEMETRY_RELAY_DLL。備份資料後再升級，不能降版讀取 schema 5。

v0.12 世界發布為 WebSocket、觀察為帶 Bearer 的 fetch SSE，來源規範在 WORLD_RECORDING.md。新增 worlds.db 與每幀統計／combat witness 核對；管理 events.db schema 不變。必要另跑 python scripts/smoke_world.py，隔離指定 VR_COMMAND_WORLD_RELAY_DLL；瀏覽器檢查包含 world-browser.cjs。共享 WorldRecording DTO 仍須 C# 9／netstandard2.1；Unity 尚未發布世界或採樣頭手，不能把合成 Simulated rig 宣稱為 Tracked。

v0.13 共用 WorldOutbox／WorldPublisher 與 Unity 頭手來源／追蹤／管理邊界已接源碼，尚未編譯運行。binary journal 有 checksum、exclusive lease、durable ack 與 completion/seal；Native --world-journal 使用同一發布器，--recording 留舊 NDJSON，恢復 Unity 可另指定 --combat-journal。header UTC 擷取時間需 v0.13 API，舊資料預設空值；DB schema 不變不表示可直接降回舊 reader。新鮮度不可用收到時間代替擷取時間。NGO source byte 改 wire format，生成器 protocol 13；EditMode 至少 12 項，來源／證據／限制見 WORLD_SOURCE.md。

v0.14 入場規範見 ADMISSION.md：envelope 6 讀 1–5，以原加入 EventId 派生／保存 admissionId；v2 票券簽 admission／seat，v1 全拒。新 HTTP 移除及配票必須 If-Match-Admission，已接受的歷史 leave 重試仍保留原 fence 只確認；不要以當前入場覆蓋舊 pending 操作。GameServer 驗票 protocolVersion 2，ArenaSession.Connect 必帶 admissionId；Unity 以 throughSequence 快照及 expiry 驗後綁定，管理 fetch 合併串行。15 項 EditMode 仍待執行；協同更新 API／UI／所有 GameServer／頭盔來源並重發票券，不以舊來源忽略 epoch 作相容解法。

v0.14.1 僅管理／觀戰新增相同 worlds.db 的 camera_bookmarks 表，envelope 6／world schema 1／NGO protocol 14 不變。鏡頭以完整 OperatorIdentity 及場次隔離，僅 Master／RoomController，24 個有效位置；PUT 同 ID／內容確認原結果、DELETE 留 tombstone，舊保存重試不得重建已移除位置。新路由每次重查錄製及房間範圍。camera-ui.js 待確認操作保留原內容，logout／換身分 epoch 阻擋晚回應；鏡頭設定存伺服器，憑證仍限頁面記憶體。規範見 WORLD_RECORDING。預覽資料實際在 src/VrCommand.Api/data，root data 是控制台 key／來源設定；隔離 DLL 啟動須顯式 DataDirectory／SessionDataDirectory，備份兩處及 WAL，不以空白新資料庫替代原歷史。

v0.15 任務庫由 Persistence.SqliteMissionLibrary 的 missions.db／schema 1 管理，原 GUID.json 一次交易匯入後只保留備份；目前 Core.MissionStore 不能讀寫已版本化目錄，不混跑舊 API。任務本體 schema 1／場次 envelope 6／world schema 1／NGO protocol 14 不變。series 的版本不可變且線性，revision route 的 baseId 必須當前 head；任務 request key 綁完整作者／kind／base／definition，已接受重試回原版本不重施。所有 HTTP 讀寫明確傳 Actor；ReadMission 為共用範本政策，AuthorMission 限 Master。UI 待確認寫入保留原請求，保存成功但後續讀回失敗也保留；已知 head 於單次登入只前進，背景更新不換掉已選的開場版本或草稿。history 只傳分頁 metadata，控制台輪詢 /mission-library，不載入全部歷史定義。見 MISSION_VERSIONS。PowerShell 直接 @(Invoke-RestMethod ...) 會多包一層陣列；安全檢查先賦值再檢查 Count，檢查／備份非零退出時不得啟動下一個相依步驟。
