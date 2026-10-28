# 開發指引

開發根目錄為 `F:\Projects\vr-command-center`；以此庫的實際 Git 狀態與執行結果為準。

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

Quest 接入與建置見 `docs/QUEST3.md`。`scripts/check-unity-source.ps1` 只檢查 C# 9 語法，不能代替 Unity 編譯與 EditMode 測試。Editor 已安裝至 F 槽。使用者已明確同意 SDK／NDK 條款，不再要求相同確認；CLI 子模組失敗後已整理官方目錄，`check-android-toolchain.ps1` 的 API 32 ARM64 編譯通過。CLI 失敗登錄仍在，不盲目重裝。使用者雖回覆已登入，實際 CLI 仍無 session／license、Prepare 退出 198，一次瀏覽器回呼等待亦已逾時。後續已補裝並啟動 Hub 3.22.5（Appx 3.22.5.65535），套件雜湊及 Unity 簽章通過；Windows 安全性對 adb.exe 提示遮住畫面，待使用者自行處理及確認 Hub 授權，不自動操作安全提示或登入。不再把 Hub 說成未安裝；CLI 未登入不是否定 Hub／浮動授權的充分證據，後續以實際 Editor 建置為準。

3D 模擬回放在 `replay-*.js`，資料與操作見 `docs/REPLAY.md`。維護 schema 2／rules 0.8.0、明確 Simulation 來源、射線與快照／統計的一致性。`tests/browser` 的 test 會執行資料驗證與軟體 WebGL 檢查，不能視為真實 GPU、Unity 或頭盔測試。Three.js 上游原始檔、MIT 及 provenance 一併保留，不混入 CDN 執行相依。

頭盔只配置短效玩家票券；GameServer 憑證僅存桌面伺服器設定。所有 `data/`、`artifacts/`、Unity 快取與本機憑證均不得提交。生成場景、APK 或桌面程式須有實際成功結果，不能以來源碼存在宣稱完成。

v0.9 的建立／加入／離開以選用 Idempotency-Key 去重，事件 schema 4 的 requestId 與業務事件一起持久化；重試只確認歷史接受，不重施新狀態。保留 schema 1–3 讀取與不帶 key 的相容性。前端與後端需一起升級，不能把 v0.9 的可重試前端放到忽略 key 的舊後端；寫入新 schema 後不可直接降版。契約見 SESSION_PROTOCOL。

v0.11 新事件 schema 5，讀取 schema 1–4；戰鬥串流綁定唯一來源／origin，接受有 Running 觀察位置的已保存尾端，封存後只允許既有報告去重確認。End 釋放房間但 pendingTelemetry 保持 true 到精確 seal；不能把未封存報表當作最終結果。批次可能已提交前綴，須原樣重試。journal 壞尾端不自動截斷；補送不是世界恢復。HTTP 隔離檢查另設 VR_COMMAND_TELEMETRY_RELAY_DLL。備份資料後再升級，不能降版讀取 schema 5。

v0.12 世界發布為 WebSocket、觀察為帶 Bearer 的 fetch SSE，來源規範在 WORLD_RECORDING.md。新增 worlds.db 與每幀統計／combat witness 核對；管理 events.db schema 不變。必要另跑 python scripts/smoke_world.py，隔離指定 VR_COMMAND_WORLD_RELAY_DLL；瀏覽器檢查包含 world-browser.cjs。共享 WorldRecording DTO 仍須 C# 9／netstandard2.1；Unity 尚未發布世界或採樣頭手，不能把合成 Simulated rig 宣稱為 Tracked。

v0.13 共用 WorldOutbox／WorldPublisher 與 Unity 頭手來源／追蹤／管理邊界已接源碼，尚未編譯運行。binary journal 有 checksum、exclusive lease、durable ack 與 completion/seal；Native --world-journal 使用同一發布器，--recording 留舊 NDJSON，恢復 Unity 可另指定 --combat-journal。header UTC 擷取時間需 v0.13 API，舊資料預設空值；DB schema 不變不表示可直接降回舊 reader。新鮮度不可用收到時間代替擷取時間。NGO source byte 改 wire format，生成器 protocol 13；EditMode 至少 12 項，來源／證據／限制見 WORLD_SOURCE.md。

v0.14 入場規範見 ADMISSION.md：envelope 6 讀 1–5，以原加入 EventId 派生／保存 admissionId；v2 票券簽 admission／seat，v1 全拒。新 HTTP 移除及配票必須 If-Match-Admission，已接受的歷史 leave 重試仍保留原 fence 只確認；不要以當前入場覆蓋舊 pending 操作。GameServer 驗票 protocolVersion 2，ArenaSession.Connect 必帶 admissionId；Unity 以 throughSequence 快照及 expiry 驗後綁定，管理 fetch 合併串行。15 項 EditMode 仍待執行；協同更新 API／UI／所有 GameServer／頭盔來源並重發票券，不以舊來源忽略 epoch 作相容解法。

v0.14.1 僅管理／觀戰新增相同 worlds.db 的 camera_bookmarks 表，envelope 6／world schema 1／NGO protocol 14 不變。鏡頭以完整 OperatorIdentity 及場次隔離，僅 Master／RoomController，24 個有效位置；PUT 同 ID／內容確認原結果、DELETE 留 tombstone，舊保存重試不得重建已移除位置。新路由每次重查錄製及房間範圍。camera-ui.js 待確認操作保留原內容，logout／換身分 epoch 阻擋晚回應；鏡頭設定存伺服器，憑證仍限頁面記憶體。規範見 WORLD_RECORDING。預覽資料實際在 src/VrCommand.Api/data，root data 是控制台 key／來源設定；隔離 DLL 啟動須顯式 DataDirectory／SessionDataDirectory，備份兩處及 WAL，不以空白新資料庫替代原歷史。

v0.15 任務庫由 Persistence.SqliteMissionLibrary 的 missions.db／schema 1 管理，原 GUID.json 一次交易匯入後只保留備份；目前 Core.MissionStore 不能讀寫已版本化目錄，不混跑舊 API。任務本體 schema 1／場次 envelope 6／world schema 1／NGO protocol 14 不變。series 的版本不可變且線性，revision route 的 baseId 必須當前 head；任務 request key 綁完整作者／kind／base／definition，已接受重試回原版本不重施。所有 HTTP 讀寫明確傳 Actor；ReadMission 為共用範本政策，AuthorMission 限 Master。UI 待確認寫入保留原請求，保存成功但後續讀回失敗也保留；已知 head 於單次登入只前進，背景更新不換掉已選的開場版本或草稿。history 只傳分頁 metadata，控制台輪詢 /mission-library，不載入全部歷史定義。見 MISSION_VERSIONS。PowerShell 直接 @(Invoke-RestMethod ...) 會多包一層陣列；安全檢查先賦值再檢查 Count，檢查／備份非零退出時不得啟動下一個相依步驟。
