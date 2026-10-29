# 世界來源、頭手與補送

目前 Unity NGO protocol／Android code 17、bundle 0.17.0，API 仍 0.16；真正 Editor 已通過 29 項 EditMode 及 Windows／Quest 同源建置。PC 重連及 Simulated 恢復姿態的 admission 隔離見 [RECONNECT](RECONNECT.md)；不能把桌面快取當 Tracked 或持久世界恢復。下方 v0.13／14 為歷次改動。新 header 預設 environmentVersion 1，舊 journal 保持 0／原始 JSON／checksum，codec 正規化比較支援缺少選用欄位的原樣恢復。`--environment-demo true` 只搭配新 `--demo-room` 產生 Storm／Night／雷電 Simulation；完整聲光規則、UTC 與升級見 [ENVIRONMENT.md](ENVIRONMENT.md)。

v0.14 新增每次入場識別、票券 v2／protocol 2、If-Match-Admission 與跨輪詢重入撤銷，Unity／API 需同版升級並重發舊券，見 [ADMISSION.md](ADMISSION.md)。生成器 NGO protocol 14／bundle 0.14；當時的 15 項 EditMode／建置尚待執行；最新真正 Editor／PC 結果以上方與 NATIVE_VALIDATION 為準，頭盔仍待驗。

WorldOutbox／WorldPublisher 是 Unity 與 .NET 工具共用的唯一來源，位於 embedded Simulation Runtime，實際編譯為 C# 9／.NET Standard 2.1，不引用後端或 UnityEngine。JSON 由 IWorldCodec 提供：工具使用 System.Text.Json，Unity 使用 JsonUtility。真實 WebSocket、API、SQLite、SSE 及 Chromium 已以此 .NET 發送器驗證；Unity 已由真正 Windows server 與兩個 desktop client 通過獨立／跨房 Simulation 世界發布、暫停及精確封存，觀戰排隊也已修正；已建置 APK，沒有 Quest／VIVE、實際 Tracked 姿態或 25 台效能證據。最新範圍見 [NATIVE_VALIDATION.md](NATIVE_VALIDATION.md)。

伺服器、主控台與新來源一起升至 v0.13：header 增加 captureStartedAtUtc，嚴格的 v0.12 API 不接受此欄位。舊 schema 1 世界 header 缺少時間仍可讀／去重，回應補空值及 capturedAtUtc:null；未改 SQLite schema 1、session envelope 5 或 rules 0.8.0。不要只更新發布器卻繼續使用舊 API。

## 持久來源與確認

來源檔有 VRWORLD1 signature；每筆以 length／payload／SHA-256 保存，payload 最多 1 MiB 減 128 bytes。種類為 header、世界幀、逐幀 acknowledgment、completion intent、seal receipt。CreateNew 不覆寫既有檔案，FileShare.None 保持單一程序；每次 append 都 Flush(true)。SHA-256 用於損壞偵測，不是來源簽章。

重開逐筆驗證檔案，不載入整場幀或建立逐幀記憶體索引；只保留最後幀、待確認幀及檔案讀取位置。讀取／寫入由 outbox lock 協調，避免非同步網路確認與主執行緒錄製操作同一 FileStream。損壞／截斷不自動忽略、覆寫或修尾端；磁碟失敗先於記憶體 cursor、ack 或 complete 推進。

WorldPublisher 每次只送一份待確認幀，等待該幀 throughCombatSequence 已由 TelemetryOutbox 持久確認。World API 的 combat witness 是另一層伺服器核對。收到 ack 後，先保存本機 receipt 才推進 cursor；丟失回應可用同一幀再確認。連線中斷時須建立新 publisher／socket，重新附上原 header。缺少完成意圖、未送完幀或 combat 尚未 sealed，不能製造世界 seal。

世界來源是錄製／補送，**不是崩潰後恢復遊戲運算**。不能用全新 Preparing 世界假冒 Running 的延續；既有來源檔須在原程序停止後補送，之後為新場次建立新檔案。已保存的 ack 假設伺服器保留該 durable state；這個工具沒有強制重建遺失／被回復到舊備份的世界資料庫模式。

## 工具操作

房間 5 必須空閒，檔案必須不存在。只建立自己的 Simulation 任務，不變更現有場次。

```powershell
dotnet tools/VrCommand.WorldRelay/bin/Release/net10.0/VrCommand.WorldRelay.dll --world-journal F:/Projects/vr-command-center/artifacts/world-source/demo.worldlog --demo-room 5 --seconds 3
```

這會使用共用 publisher／journal，另存 demo.worldlog.combat。原程序停止後補送：

```powershell
dotnet tools/VrCommand.WorldRelay/bin/Release/net10.0/VrCommand.WorldRelay.dll --world-journal F:/Projects/vr-command-center/artifacts/world-source/demo.worldlog
```

Unity 在 telemetryDirectory 保存 `<sessionId>.worldlog` 與 `<sessionId>.journal`，可明確指定兩份原始來源：

```powershell
dotnet tools/VrCommand.WorldRelay/bin/Release/net10.0/VrCommand.WorldRelay.dll --world-journal F:/Projects/vr-command-center/data/telemetry/SESSION.worldlog --combat-journal F:/Projects/vr-command-center/data/telemetry/SESSION.journal
```

用實際 UUID 取代 SESSION。兩份檔案的 session、streamId、origin 必須一致，否則在補送前拒絕。恢復可接受原始 Simulation 或 GameServer；所有 demo 仍強制 Simulation。可加 --base-url／--key-file，預設讀忽略的本機密鑰，永不寫入來源檔或輸出密鑰。只在桌面伺服器配置 GameServer 憑證，頭盔仍只有玩家短效票券。

舊 --recording 模式繼續處理 v0.12 NDJSON，不把它當成 binary journal。CLI 遇到網路失敗退出並保留來源供重送；自動重連在 Unity 接入程式碼內，尚待運行驗證。Native demo 的 tick／錄製頻率及等待網路的節奏不等同 Unity 的 10 Hz 來源或實機吞吐量。

## 擷取時間與觀戰新鮮度

新 WorldOutbox.Create 保存 UTC 擷取基準；frame 的 elapsedMilliseconds 是從該來源開始的單調時間，重新連線／補送不改基準。header 時間不可在附加後重設。捕捉時間目前要求 round-trip UTC 格式、年份 2020–2100；空值只用於無時間的舊來源。API capturedAtUtc 是該基準加最後已接受幀的 elapsed，updatedAtUtc 仍是伺服器接收／保存時間。

主控台以**正在顯示的幀之擷取時間**判斷過期，不以「剛收到資料」重設歷史資料年齡。超過 1.5 秒或串流中斷標過期；沒有來源時間標未知，來源時間超前 1 秒以上標時鐘未同步。重連補送中的舊幀即使持續抵達也不是即時畫面。場館的來源／API／操作員電腦需要同步 UTC 時鐘；來源為受信任伺服器，此欄位不是硬體時間戳或防偽證明。回放仍按保存 elapsed 播放，沒有依目前 UTC 重新跑模擬。

## Unity 接入來源碼

- CombatAuthority 初始化 Preparing 世界及 combat journal 後，以同一 stream 建立世界來源，先保存第一幀。以目標 10 Hz 錄製，管理變更前後另存邊界；先保存統計事件，再保存世界，再發佈遊戲狀態。
- accepted pose 同時更新受該連線綁定的頭／左右手與旋轉，轉到世界座標；斷線不移除其他新連線的 rig。未參戰者使用 None，既有身體及健康／彈藥仍由 ArenaSession 決定。
- AvatarPose 增加 source byte：桌面為 Simulated，XR 客戶端只有頭與雙控制器 isTracked 均為真、trackingState 均含 Position／Rotation，才發送 Tracked。追蹤中斷停止姿態及武器輸入，伺服器仍依原有 0.5 秒姿態期限撤下參戰狀態。Tracked 是經驗證欄位／位置後保留的**客戶端宣告**，不是裝置認證或頭盔實測證明。
- 世界錄製檢查左右手距頭範圍；Quaternion、頭／槍口與房間範圍也保留原驗證。右手使用 OpenXR aim，左手為裝置 pose，尚無手指骨架／控制器模型。
- WorldRecordingDelivery 把共用非同步 publisher 接到 coroutine，等待 combat ack、重試連線中斷，永久訊息／磁碟錯誤暫停戰鬥。結束後先排空並確認 combat seal，再送 world seal。銷毀時取消 socket，等待尚在進行的工作結束才釋放來源檔。
- 管理連線過期時保存 suspended Paused 快照；新鮮管理快照恢復後再記錄 Running。記錄結束幀與完成意圖後不再追加新世界幀。

AvatarPose 的 NGO wire format 於 v0.13 改變；目前 v0.16 另有原子 WeatherState，兩端需按 protocol 16 重新建置同版。姿態、world codec、入場及天氣 EditMode 來源共 18 項，腳本要求至少 **18 項通過**；目前沒有 EditMode 結果。Input System 1.17.0 trackingState／isTracked／TrackedPoseDriver 與 NGO 2.7.0 ProtocolVersion 已依本機快取的官方固定版本來源檢視，仍不能代替 Unity 編譯。

## 接續驗收

先完成工具可讀的 Unity 授權，實際 Prepare／18 項 Tests／Desktop／Quest。以兩位 Quest 玩家驗證頭手與控制器遮擋／追蹤中斷、射擊與資料依賴、Pause／End、HTTP／WS 各自斷線與排空、封存／重送及聲光同步，再對照主控台及 APK 日誌。瀏覽器鏡頭書籤已實作；尚無長任務壓測、檔案保留／壓縮、自動世界恢復、實機校正、25 台吞吐量或硬體驗收。
