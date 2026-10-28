# 開發進度

## 2026-10-29：v0.14 每次入場識別、票券 v2 與撤銷接入

上一輪 v0.13 已推送、部署並完成具體驗證。本輪以乾淨的 27242b2 接續原目標，CLI 仍 loggedIn false／license list 空；新的 Prepare 實際退出 198，命令已結束，沒有等待中的 Unity 工作。SDK 條款無須重問，沒有重裝或代填登入。長期目標保持開發中。

新增 Player.admissionId，以原始 PlayerJoined.EventId 為本次入場識別；新 schema 6 payload 明確保存，舊 1–5 從原 EventId 穩定推導，不改寫歷史。相同玩家／房間／席位重新加入仍取得新識別；相同加入 requestId 只確認歷史。PlayerLeft 保存實際 admission 與原始 expectedAdmissionId；同 requestId 改 fence 回 409。DB schema 仍 1，但新 envelope 不能降回舊 reader。

票券改 v2，HMAC 簽 session／player／admission／room／seat／expiry／nonce，仍五分鐘且頭盔只拿四欄連線檔。舊 v1 即使原簽章／期限有效也拒絕。配票及新的 HTTP 玩家移除必須 If-Match-Admission，缺／壞 header 400、入場變更 409；已接受的舊移除只確認，不影響後來入場者，未接受的舊 fence 不可移除新成員。舊版已接受且無 fence 的 requestId 仍可確認。

GameServer 驗票需 protocolVersion:2，驗簽後原子比對當前 admission／room／seat／state，回 throughSequence 及 expiry。ArenaSession.Connect 必帶 admission，Preparing 輪詢即使跳過離場／同 ID 重入也能撤銷舊 binding，舊姿態／武器不影響新身體。Running 不得換 epoch／重生。Preparing 重新入場變更名稱的世界統計 metadata 亦對齊最終 ledger，避免封存名稱不一致。

Unity 來源碼加入驗後取得至少 throughSequence 的快照、expiry／epoch 比對、即時清除內部過時 binding、遠端斷線／Host 關閉，以及合併串行管理 fetch，避免多個 approval 回應造成快照倒退。approval buffer 20 秒；既有連線撤銷仍依管理觀察，正常目標 0.5 秒，管理過期 1.5 秒暫停，未承諾實機零延遲。生成器 bundle／Android／NGO protocol 14。新增三項待執行 EditMode，總數 15；JSON 舊管理範例補 admission，不以忽略 epoch 作相容解法。

鎖定還原／Release 0 警告／0 錯誤，**399 核心、322 HTTP、32 世界串流、12 回放資料、78 Chromium，共 843 項通過**。23 份 C# 9 語法通過；同源 Runtime 仍真正建置 .NET Standard 2.1，沒有 Unity SDK 編譯。驗證含 SQLite 後撤銷保持、同 ID／同席位重入、簽章正確的舊 v1 拒絕、過時／空 fence、原始重試內容、舊 schema 派生與無 fence 歷史確認、跨輪詢撤銷、世界 metadata／封存一致；瀏覽器讓移除先接受但丟回應，再由其他操作員重入，原 fence 重試保持新玩家。15 項 EditMode 未執行，沒有 APK 或頭盔證據。

本機 5080 先確認自有程序且活動場次 0，停止後完整備份至 artifacts/backups/pre-v014-*，再升級 API／控制台；新 exec 59527 服務 0.14.0。原七場在 player 新增可推導 admissionId 後逐欄一致，三份 world metadata 完全不變。另以自己的空房 5 新建純 API 驗證場次 deb56282-e99c-49a7-abf4-dcd6c1134272：同 ID／席位取得不同 admission、舊票券拒絕、舊 leave retry 無害、新券有效，驗後 End 釋放房間；目前活動 0。沒有把此 API 驗證稱為遊戲或實機，摘要在忽略的 artifacts/v014-live-admission.json。

規範與升級見 ADMISSION.md。下一步仍先取得工具可讀授權，實際 Prepare／15 Tests／Desktop／Quest，驗雙 Quest 的重連／撤銷／追蹤與排空，再推進 5／25 台、硬體、MR、VIVE、任務版本與書籤等未完成項目。完整 11 項及雙平台範圍保留；CI 依本輪推送另記，不改帳務或盲目重跑受限工作。

5e77123 已推送；雲端 run 40778846449／check 123135061355 steps 為空，annotation 指出付款／支出限制，工作未啟動。只有本機 843 項通過，沒有本輪雲端成功證據；未修改帳務或盲目重跑。

## 2026-10-29：v0.13 共用世界來源、Unity 頭手接入與擷取時間

上一輪 v0.12 已推送並部署，屬於實際進展。本輪依目前乾淨的 418decb 接續，CLI auth 仍 loggedIn false／license list 空。完成來源接入後實際 Prepare 再次退出 198，log 為 No valid Unity Editor license；該 exec 32393 已結束，沒有仍在等待的安裝或建置，也沒有 Unity／APK／頭盔通過證據。長期目標持續開發。

新增共用 WorldOutbox／WorldPublisher／WorldWebSocket，真正建置 C# 9／.NET Standard 2.1，Unity 與 Native 工具只替換 JSON codec。來源 binary journal 以 VRWORLD1／length／SHA-256、獨占 lease 及 Flush(true) 保存 header／幀／ack／completion／seal，逐筆重開且只保留最後／待送幀。失敗 ack 不推進 cursor；丟回應／封存重試維持同一內容，壞尾端不自動截斷。發布等待 combat durable ack，世界封存另等 combat sealed；來源補送仍不是世界運算恢復。

Unity 來源新增接受後的世界頭／左右手及旋轉、None／Simulated／Tracked 宣告、追蹤中斷停送、10 Hz 世界錄製、管理前後邊界、suspended Pause、Ended completion 與非同步排空／取消生命週期。頭與雙控制器需同時 isTracked，trackingState 含 Position／Rotation。右手 aim、左手 device pose，尚無手指骨架。Tracked 是客戶端宣告經位置／格式驗證後保留，不能當作裝置認證。AvatarPose 新 source byte 由生成器 NGO ProtocolVersion 13 區隔；bundle 0.13／Android code 13。

Native WorldRelay 新 --world-journal 走相同 Runtime 發布器與校驗來源；--combat-journal 可對應 Unity 原始 journal，恢復前核對 session／stream／origin。原 --recording NDJSON 保留。新增實際來源重開、獨占、掉 ack、掉 seal、磁碟 receipt／completion 失敗、世界對統計依賴、並行發送拒絕與 damaged-tail 測試。Unity 新增五個待執行 EditMode 測試，總數 12；腳本不能再以舊七個結果宣稱通過。

另修正補送新鮮度：header 保存不可重設的 UTC 擷取基準，elapsed 保留來源單調時間，API capturedAtUtc 對照擷取時間，updatedAtUtc 仍為接收時間。觀戰以正在顯示幀的擷取時間判斷，持續收到舊幀仍標過期，無時間標未知、超前時鐘標未同步。v0.12 舊 header 補空值可讀／去重；SQLite schema 1／session envelope 5 未變，但舊嚴格 reader 不接受新欄位，不能把 v0.13 來源配舊 API 或直接降版。

鎖定還原及 Release 建置 0 警告／0 錯誤，**363 核心、302 原 HTTP、32 真實世界串流、12 回放資料、76 Chromium 通過，共 785 項**。22 份 C# 9 語法通過；12 項 Unity EditMode 僅有來源，沒有結果。真實 WebSocket／SQLite／SSE／瀏覽器皆使用共用 Native 發布器驗證，仍不等同 Unity SDK／ILPP／IL2CPP、頭盔或 25 台效能。已檢視 world-old-capture.png，確認有新資料抵達但擷取時間老舊仍顯示過期。

現有 5080 自有預覽先確認活動場次 0，停止後備份完整 API data 至 artifacts/backups/pre-v013-*，再升級前後端，新 exec session 17719 版本 0.13.0。原六份歷史完全一致、兩份 world metadata 僅新增預設 captureStartedAtUtc 空值／capturedAtUtc null。實際重送舊 v0.12 NDJSON 64 幀後 metadata 不變，驗證舊 header 缺欄位的相容性。另新增自己的房 5 clocked Simulation：e382ddcc-733b-440a-ab6a-395f5aa37a35，64 幀 complete、UTC 擷取時間保存、彈藥 2／擊殺 1／血量 80；另一程序恢復 ack 64 後不變，舊六場均保持一致，活動場次仍 0。前面另一次未升級預覽的 shared-source 示範也保留，所有示範均無頭盔。

本輪 ADB 實際讀取 ready 0／unauthorized 0，只表示當下沒有可用 ADB 裝置，未宣稱有頭盔實測。來源／驗證摘要在忽略的 artifacts/world-source-demo 與 artifacts/v013-live-demo.json。接入與補送見 WORLD_SOURCE.md。下一步仍需工具可讀的 Unity 授權及真正 Prepare／12 Tests／Desktop／Quest，驗兩位 Quest 的頭手／追蹤中斷、HTTP／WS 分別斷線、Pause／End、完整排空，再做效能、MR、硬體與 VIVE。未把來源接線當成 Unity 運行完成，完整 11 項需求保持原範圍。CI 依本輪推送另記；未改帳務或重跑已知受限工作。

7c4ddb9 已推送；CI run 40773104321／check 123115220952 的 steps 空白，annotation 指出付款／支出限制，工作沒有啟動。本機 785 項結果有效，但不宣稱雲端成功；未修改帳務或盲目重跑相同工作。

## 2026-10-29：v0.12 持久世界、即時觀戰與伺服器回放

上一輪 v0.11 已推送並部署，屬於實際進展。本輪接續同一 F 槽儲存庫，Unity CLI 仍未讀到登入／授權；沒有啟動新登入或盲目重裝，沒有新的 Unity 編譯／APK／頭盔結果。長期目標保持開發中。

新增 engine-independent WorldRecording field DTO：schema 1、rules 0.8.0、primitives-v1／uncalibrated-vr，保存頭／槍口／方向、頭旋轉／左右手位置旋轉與來源、健康／彈藥／換彈／參戰、敵軍、完整世界事件及環境／AI 政策。此 schema 與既有本機 schema 2 模擬檔不同。未知版本、非有限資料、壞旋轉、幀／世界事件／戰鬥邊界不連續、越界／缺少名冊／政策衝突均拒絕。

新增 GameServer owner 專用 WebSocket world/publish，與既有 combat-stream 同 ID／origin／身分。先 header 再 frame／seal；UTF-8 文字最多 1 MiB。每份四種統計事件逐筆對照 durable combat witness，核對 ID／順序／來源／玩家／shot／enemy／damage／觀察時序，血量及剩餘彈藥也對上此事件前綴。未知來源不會變成真人／物理證據。沒有以世界渲染重新推算權威射擊。

世界另存 SessionDataDirectory/worlds.db（SQLite schema 1、WAL／FULL），管理 events.db／envelope 5 不變。每幀、統計、唯一事件 ID 及 cursor 同交易，拒絕／寫入失敗沒有部分幀。以 sequence／elapsed 索引讀取，不在啟動時載入整場幀。最後 Ended、精確 finalSequence、combat sealed、相同戰鬥邊界及最終統計都對上，才 complete=true；API End 不製造世界末幀。

主控台新增「觀戰與任務回放」，用有 Bearer 標頭的 fetch SSE 讀取 latest／replay，不加入玩家席位。支援房間與角色、自由／俯視／跟隨、暫停、時間索引跳轉、0.25–4 倍速及逐幀統計；頭手來源明示 None／Simulated／Tracked。來源超過 1.5 秒沒有新快照即標過期，心跳不能掩蓋停送；登出／切頁／換場取消串流。刪除離場角色的渲染資源，並修正即時時間軸長度及手機標題排列。

新增 VrCommand.WorldRelay：只建立自己的 Simulation 任務，以真正共用核心產生射擊／擊殺／AI 傷害／暫停／天氣／Ended。原始 NDJSON Flush(true) 後才逐幀送出並核對 ack，旁邊保留既有 combat journal；另一程序可逐行重送，同序內容只確認。來源損壞不自動截斷，缺少完成記錄不補造 seal；目前網路錯誤保留檔案後退出，尚無自動世界重連／恢復運算。

鎖定還原與 Release 建置 0 警告／0 錯誤，**333 核心、302 原 HTTP、24 真實世界串流、12 回放資料、72 Chromium 檢查通過，共 743 項**。17 份 Unity／共享 C# 語法通過，embedded Runtime 亦真正以 .NET Standard 2.1 建置，但沒有綁定 Unity SDK／ILPP。已檢視 world-live.png、world-stale.png 與 world-replay-mobile.png；含真實發布／SSE、來源強制中止後過期、房間範圍、回放統計、SQLite 重啟、整份來源跨程序重送、衝突重試及交易回滾。本機軟體 WebGL 不能代替頭盔／GPU 效能驗收。

本機預覽先確認自有舊程序及活動場次為 0，停止後備份完整 API data 至 artifacts/backups/pre-v012-*，再升級前後端。新 exec session 82831 服務版本 0.12.0，原四份歷史場次逐欄完全一致。新增自己的房 5 Simulation：b15507b1-d4cf-45a7-a830-7c2b4192ac6d，64 幀封存，彈藥 2／擊殺 1／健康 80；用新程序補送後世界 metadata 及五份歷史場次均不變，活動場次仍 0。來源／驗證摘要在忽略的 artifacts/world-demo*，預覽可直接選取此場回放。

Unity 目前只有共享錄製 DTO，**尚未接上世界發布器或真正頭手採樣**；既有統計 outbox 來源碼也仍未編譯運行。接續先完成工具可讀的 Unity 授權及真實 Prepare／Tests／Desktop／Quest，再接世界發送、頭手、雙玩家及斷線驗收。書籤、保留／壓縮、長任務／25 台吞吐量、正式資產、硬體、MR、VIVE 與實機仍待做。GitHub CI 依本輪推送結果另記，沒有修改帳務或重跑已知受限工作。

87e7a6c 已推送。其雲端 CI run 40766549749／check 123092115458 的 steps 為空，annotation 明確指出近期付款失敗或支出限制，因此工作未啟動。不能宣稱本輪雲端測試通過；本機 743 項結果仍有效。未修改帳務、未盲目重跑相同受限工作。

## 2026-10-29：v0.11 持久戰鬥補送、結束封存與主控台完整性

上一輪 v0.10 已推送來源碼與測試修正，屬於實際進展。本輪以該工作樹接續：CLI 仍未登入、license list 空，完成程式後實際 Unity Prepare 再次退出 198；命令已結束，不是仍在等待的建置。整體長期目標開發中，沒有 Unity 編譯、APK 或頭盔結果。

新增 GameServer 專用 combat-stream／reports／batch／seal 端點，Preparing 綁定唯一 streamId、origin 與來源身分。streamSequence 連續，observedSequence 指向事件產生時最後觀察的 Running 管理快照，以稀疏管理索引驗證當時狀態及名冊。Pause／End 後仍接受原觀察尾端，未來／暫停／已離場觀察不能偽造新射擊；既有報告可原樣去重，來源及內容不可換手。綁定後舊 combat 端點不可繞過。

End 釋放房間但 pendingTelemetry 維持 true；精確 finalSequence 已收到且來源送出 seal 後才標為完整。主控台 End 時自動保留待確認歷史，顯示補送／封存提示；新房間場次不受舊尾端影響。新 envelope schema 5 保留舊 1–4，SQLite user_version 仍 1；不得直接降版。批次最多 128 筆、逐筆持久化，失敗可已提交前綴，原樣重試去重續送，不宣稱跨批次原子性。

共用 Runtime 新增 TelemetryOutbox：獨占 journal、版本與身分、SHA-256 frame 完整性、批次 Flush、累計 acknowledgment、completion 及 seal。穩定 eventId 轉 reportId，只選四種統計事件，AI 射線／reload 不冒充玩家彈藥。檔案損壞／截斷不自動丟棄尾端；磁碟失敗不推進記憶體 cursor／ack。補送恢復不是世界恢復，尚無自動修復、壓縮或保留政策。

Unity 來源碼已在伺服器建立 journal／綁來源後開放戰鬥，武器及 tick 在保存後才發佈快照，網路／5xx 保留重試，永久拒絕／磁碟錯誤暫停戰鬥；在管理 End 前先保存原觀察尾端，再完成／補送／封存。預設明確 Simulation，server.json 指到 F 槽 data/telemetry，頭盔四欄設定不含密鑰。尚未編譯／運行發送器，不宣稱實機報表已一致。

新增 VrCommand.TelemetryRelay，可在原程序停止後以同一 journal 補送；只有 completion 存在才嘗試封存，否則保留未確認完整。其 demo 模式在空閒房建立自己的 Simulation 世界，以真正兩次射擊／命中／擊殺及一次 AI 傷害生成六份報告，先 End 並退出；另一程序才讀檔補送。HTTP fixture 另先接受一筆但不保存回應、重啟 API，再跑補送，驗證同一前綴不重複計數。

鎖定還原及 Release 建置 0 警告／0 錯誤，**295 項核心（新增 41 項）、302 項 HTTP、12 項回放資料、59 項 Chromium 通過**；16 份 C# 9 語法通過，embedded Runtime 真正建置 .NET Standard 2.1，Unity SDK／ILPP 未綁定。已檢視 telemetry-pending.png，畫面及測試區分 Ended／待補送／已封存。測試含競爭來源、失序、觀察資格、來源混用、批次部分提交／重試、兩邊獨立重啟、磁碟失敗、壞尾端及確認邊界。

本機原 5080 服務先驗證為本任務程序且活動場次 0，停止後備份完整 API data 至忽略的 artifacts/backups/pre-v011-*，再升級前後端；新 exec session 24293 正在服務，版本 0.11.0，原三份歷史快照在新增 null combatStream 相容欄位後完全一致。舊服務已停止。另於自有房 5 執行 demo 及恢復，場次 bafd9eb0-9309-4e10-b422-0a27a2e9cd78 六筆確認、sealed true、pending false、彈藥 2／擊殺 1／血量 80；只操作新建示範場次。journal 與摘要在忽略的 artifacts/telemetry-demo。

接續優先真正編譯／實測 Unity 管道與 Quest 雙玩家，並開發完整世界持久化、頭手錄製及即時觀戰；25 台吞吐量、硬體、MR、VIVE 型號與實機仍待驗收。沒有把這次統計補送當作完整遊戲完成。GitHub CI 先前曾部分運行但最新受帳務限制，待本次推送再依實際狀態記錄，沒有改帳務或盲目重跑受限工作。

## 2026-10-29：v0.10 Quest 任務與戰鬥接入來源碼

上一輪 v0.9 已推送並更新本機服務，屬於具體進展。本輪再次查核 Unity CLI，仍未登入且無 license；完成接入程式後實際 Prepare 仍退出 198，日誌為 No valid Unity Editor license found。該命令已結束，沒有執行中的安裝／建置等待，也沒有 APK 或 Unity 編譯通過證據。長期目標保持開發中。

embedded package 升至 0.10.0，新增無引擎 ArenaSession 與 field DTO，以真實管理 SessionView JSON 建立世界、名冊、任務掩體、固定席位與全場敵軍。重複刷新保持物件身分；敵軍增減不復活既有死者。VR 場地、資產、地面高度、出生點及範圍會驗證，拒絕不支援的 MR／幾何。遊戲伺服器須從 Preparing 啟動，不以新世界假冒 Running／Ended 的恢復。

以經驗票的連線 ID 綁定玩家，姿態不能指定玩家／傷害。新增核心 Connected 參戰狀態及粗略平面位移檢查；未連線、姿態超過 0.5 秒、斷線或名冊移除者不射擊、不擋彈、不被 AI 選取，保留血量／彈藥。新連線有獨立輸入 ID 域，晚到輸入／舊斷線不影響新連線。Preparing 移除已綁定玩家會安全重建未開局世界；管理 Begin 後全員離開而被輪詢跳過時，也不補造玩家或卡死轉移。

Unity Runtime asmdef 已引用核心，新增 CombatAuthority、伺服器固定步進與管理新鮮度暫停、伺服器 NetworkList、同源掩體及敵軍渲染、右手 OpenXR aim／扳機／A 鍵、桌面左鍵／R、owner 武器 RPC、健康／彈藥／換彈 HUD 與有效參戰顯示。生成器移除未與核心一致的展示掩體，改由任務資料提供，增加武器盒與 CombatAuthority。來源碼要求 Floor tracking origin，尚不可用時暫用 1.65m offset；並非 MR 校正方案。

依本機官方 NGO 2.7.0 原始碼確認 HostServerInitialize 不等待非同步 approval，改為啟動前驗 Host 票券，再同步回答；過期 pending client 不保留綁定。輪詢名冊後斷開被撤銷／結束的遠端連線；Host 玩家被撤銷則關閉 Host。這些都是尚待 Unity 運行的路徑，不能把原始碼檢視當作網路測試。

本機鎖定還原與 Release 建置 0 警告／0 錯誤，**254 項核心（新增 41 項）、282 項 HTTP、12 項回放資料、56 項 Chromium 通過**。15 份 C# 9 語法通過；embedded Runtime 真正型別建置為 .NET Standard 2.1，Unity SDK／ILPP 未綁定。新增三個待執行 EditMode 測試，合計七個；腳本要求至少七個通過，不能用舊四個結果宣稱新接入驗證。新檔案有穩定 meta GUID。

管理 API／瀏覽器仍為 v0.9，本輪未停用或更新原 5080 服務。Unity WorldEvent 目前只在記憶體，未送入 API CombatReport，頭盔 HUD 尚不會自動更新主控台統計。持久 outbox、Pause／End 事件排空、正式世界錄製及即時觀戰列為接續工作，詳見 GAMEPLAY。既有 SimulationDemo 維持明確 Simulation，舊回放規則／格式保留。

下一步仍先讓 Unity 授權可讀並真正 Prepare／Tests／Desktop／Quest，再實測雙玩家、武器／掩體／AI、管理中斷及撤銷；並行可做正式 outbox 與任務結束契約。沒有重新要求已同意的 SDK 條款，沒有代填登入、購買授權或改 GitHub 帳務。

de972be 的雲端 CI（40755707968）已實際啟動，故先前「帳務未讓工作啟動」已不適用本次；Linux 建置、254 項核心、282 項 HTTP 及 12 項回放資料通過。瀏覽器失敗在把隨機 UUID 排序報表的第一列誤認為 Alpha；新增 Temporary 玩家後列序不保證。改以明確玩家列核對，保留六項數值要求，再驗本機及雲端結果。

修正提交 76ab77d 以固定低 UUID 的離場玩家穩定重現此列序，本機 56 項 Chromium 通過。其雲端 run 40756358256／check 123056213471 再次因付款／支出限制未啟動（steps 空，annotation 明確指出帳務原因）。故只可聲明前次 Linux 部分檢查及修正後本機通過，不能宣稱完整雲端成功，也不能認定帳務依賴已永久解除。未修改帳務或盲目重跑相同受限工作。

## 2026-10-29：v0.9 場次與名冊的持久重試

上一輪 v0.8 已推送，屬於有實際程式與驗證結果的進展。本輪再次查核 Unity CLI，仍無登入 session、license list 為空；沒有啟動新登入或重裝 SDK，繼續可獨立開發的連線可靠性工作。整體長期目標保持開發中。

建立場次、加入玩家與移除玩家支援選用 `Idempotency-Key` UUID，與原事件在同一筆 SQLite append 交易中接受。跨三種操作與全館場次共用 key 索引，綁定身分、種類、目標及內容，持久化後重啟重建，失敗 append 不保留 key。每次重試仍檢查房間權限；改內容／身分／操作回傳 409，無效／全零／多值標頭回傳 400。不帶 key 的舊 API 行為保留。

重試回傳原操作已接受的確認與目前快照，不重播舊狀態：已離開玩家不因舊加入重試復活，重新入場者不因舊離開重試被移除；封存場次的建立重試不會占用新場次房間。新事件 envelope 為 schema 4，增加 requestId 與 PlayerLeft.roomId，保留 schema 1–3 讀取；資料庫 user_version 仍 1。不得在寫入新事件後直接降版。

瀏覽器三種操作都保存原 key、路徑、玩家 ID 與 body；遇到連線中斷／5xx 時鎖定後續寫入、切換與輪詢，在工作區頂端保留重試入口，無選中場次也可確認建立結果。成功後重新載入目前狀態。控制命令原去重保留，API 回應 body 讀完後也再次核對登入 epoch；登出後舊回應不能改寫新狀態。待確認操作只在頁面記憶體，關頁不持久保存。

本機鎖定還原及 Release 建置 0 警告／0 錯誤；**213 項核心、282 項 HTTP、12 項回放資料及 56 項 Chromium 檢查通過**。新增並行建立／加入／離開、內容及身分衝突、跨操作 key、容量已滿仍可確認原加入、晚到重試、封存／新場次隔離、SQLite 重啟、append 失敗恢復及 schema 相容／重複 key 拒絕。瀏覽器實際讓伺服器先完成操作再丟棄回應，驗證原 key／body 重送與單筆事件。HTTP 檢查失敗日誌亦改為容錯解碼及遮蔽測試憑證，避免 Windows 編碼錯誤蓋過原失敗。

原本 5080 服務已確認為本任務建立的程序且活動場次為 0。停止後將完整 API data 備份至忽略的 `artifacts/backups/pre-v09-*`，再建置並以原 `scripts/start-local.ps1` 升級主控台與後端；新 exec session 81620 正在服務，`GET /` 為 0.9.0、`/console/` 為 200，升級前後三份歷史場次快照完全一致。舊程序已停止，不要再當作活程序。前後端需一同升級，沒有將可重試前端留給忽略 key 的舊 API。

本輪只完成管理連線可靠性，不代表裝置重連、票券即時撤銷、Unity／APK／頭盔或正式世界串流驗收。接續優先取得工具可讀的 Unity 授權並接入已驗證共用核心；可獨立進行每次入場票券撤銷版本、遊戲伺服器與世界儲存工作。GitHub CI 帳務限制尚無解除證據。

## 2026-10-29：v0.8 3D 模擬回放與 Android 工具修復

新增「3D 模擬回放」頁，可載入實際幾何模擬紀錄或本機檔案，支援播放／暫停、逐格、時間跳轉、0.25–4 倍速、自由旋轉／平移／縮放、俯視及跟隨／點選角色。以快照還原角色、武器與實際掩體盒，顯示已記錄的射線，統計按快照 throughSequence 重建並與結束報表核對，不重新運行 AI。Three.js 0.186.1 由官方套件取得、SHA-512 核對，原始碼及 MIT／provenance 保留，不使用 CDN。

紀錄升至 schema 2／rules 0.8.0，增加 world props、射擊當下槍口／方向／距離／碰撞目標、快照的 AI／能見度／夜間設定。示範新增 10 秒巡邏，實際輸出 216 份快照、8 筆世界事件、10.4 秒邏輯時間；來源強制 Simulation。範例已保存為公開合成資產，沒有控制台憑證或真人資料。舊 schema 1 檔案保留但回放拒絕猜測缺少的資料。正式持久世界、頭盔六軸／雙手、即時觀戰與長任務串流仍待整合。

本機 Release 建置 0 警告／0 錯誤；**181 項核心、234 項 HTTP、12 項回放資料及 50 項 Chromium 檢查通過**。新增射線／快照設定驗證、資料因果與統計一致性、真實軟體 WebGL、鏡頭及時間控制、390px 版面、錯誤檔拒絕、文字渲染與登出後延遲回應不恢復舊檔。已檢視 `artifacts/console/replay-combat.png`、`replay-mobile.png`；這不是實機 GPU／頭盔效能證據。操作及限制見 `REPLAY.md`。

已將新版靜態資產更新到原本 5080 預覽輸出，`/console/` 與回放模組實際 200；沒有為此停止原 API 或改資料庫。管理 API 契約維持 v0.6，主控台／共用核心為 v0.8。

使用者已明確回覆「同意條款並安裝」，已執行 Android 模組安裝。原程序（exec session 34308／CLI PID 40596）已終止，不要再當作活程序重啟：Android、OpenJDK、SDK parent、platform 34 登錄成功，八個子模組回報失敗；單獨重試 Platform Tools 也回報失敗。檔案實際已解壓，部分留在巢狀目錄。

依官方 6000.3.27f1 module metadata 建立 `repair-android-layout.ps1`，先 WhatIf 核對來源／最終絕對目標，再整理限定 AndroidPlayer 內的 NDK、CMake、Build Tools、command-line tools；沒有覆寫／刪除既有目標。再次 WhatIf 無待移動。ADB 37.0.1、Temurin 17.0.18+8、NDK r27c／27.2.12479018（clang 18.0.3）、CMake 3.22.1、aapt2 均可執行；SDK Manager 辨識 Build Tools 36 及 platform 34／35／36。經使用者同意的 android-sdk-license 已用官方 SDK Manager 登錄。

`check-android-toolchain.ps1` 已實際以 CMake／Ninja／NDK 編譯及連結 C++17、Android log／STL、API 32 arm64-v8a 共享庫，驗證 ELF64 AArch64；輸出 `artifacts/android-toolchain-check/build/libvr_command_probe.so`。這是主要原生工具可用的證據，CLI 失敗登錄仍保留，不能宣稱 Unity APK 或 Quest 執行通過。

使用者另回覆「已登入並啟用」，但工具端 `auth status` 仍 loggedIn false、`license list` 空陣列；實際 Prepare 再次退出 198。已啟動一次 Unity 瀏覽器登入（exec session 1845），Chrome 標題停在 Unity ID Account Login，CLI 最終 AUTH_LOGIN_FAILED／登入逾時；該 session 已終止。後續需由使用者本機重新執行登入並等成功，再核對適用授權；不得把使用者回覆本身當作編輯器授權成功證據。沒有購買授權或代填登入。新詢問已提出，繼續其他可獨立開發工作。

整體目標仍開發中。下一步先取得工具端可讀的 Unity 授權並真正 Prepare／Tests／Desktop／Quest，接入共用核心與任務；同時仍需建立正式世界儲存、即時觀戰、硬體與頭盔實機流程。GitHub 雲端 CI 的既有帳務限制未有解除證據。

## 2026-10-29：v0.7 同源射擊、掩體、武器與 AI 模擬

新增 Unity embedded package `com.vrcommand.simulation`，Runtime 四份 C# 是唯一來源；`src/VrCommand.Simulation` 直接編譯為 .NET Standard 2.1／C# 9，不引用 .NET 10 後端或 UnityEngine。已實作固定 20 Hz 時間、準備／執行／暫停／結束、可旋轉掩體與身體盒射線、最近碰撞、隊友阻擋、射擊去重、射速、有限彈匣／備彈、換彈及傷害／死亡。

AI 核心已有 Hold／Patrol／Advance、自動攻擊開關、0.5m 四鄰 BFS 繞障與不可達處理、每步移動上限、視線及攻擊冷卻、霧／暴風雨／夜間範圍。這是簡化平面遊戲規則，沒有群體避讓、進階戰術、垂直地形、硬體或真實戰術模型。每個世界保留穩定事件 ID／序號，以及含武器姿態與 throughSequence 的隔離快照，尚非完整回放或持久世界。

新增 `tools/VrCommand.SimulationDemo`，只建立空閒房的自有場次，以真實射線計算低槍口被油桶擋住、AI 命中、操作設定關閉自動攻擊、側移後兩次命中擊殺；將核心事件依序送進 API 並固定標記 Simulation。預期為彈藥 3、命中 2、擊殺 1、耗損 20、中彈 1、命中率 66.67%、血量 80。API 的幾何場景／槍械輸入仍由外部受信任遊戲伺服器負責，此工具不是頭盔遊戲或持續運作的遊戲伺服器。

新增 51 項有意義的模擬檢查；本機 **179 項核心、234 項 HTTP 斷言、36 項 Chromium 檢查通過**。HTTP 測試用隔離服務實際執行新工具、驗證世界檔與 SQLite 統計及釋放房間。12 份 Unity／套件 C# 語法通過；其中共用 Runtime 另外通過真正的 .NET Standard API 型別綁定，仍不能取代 Unity 編譯／IL2CPP。

一般建置曾因現有主控台程序鎖住 API 的依賴 DLL 而失敗；改用 `artifacts/build-v07` 隔離輸出後，鎖定還原與完整 Release 建置 0 警告、0 錯誤。測試腳本新增 `VR_COMMAND_API_DLL`／`VR_COMMAND_SIMULATION_DEMO_DLL` 路徑選項，保持既有 5080 服務執行，不重啟或停止使用中的主控台。

在本機服務另實際執行房 5 幾何模擬並完成場次，保留 Simulation 歷史供主控台查閱；只操作示範自己建立的場次。除錯檔於忽略的 `artifacts/simulation-demo/latest.json`。完整規則、隔離建置、示範及限制見 `SIMULATION.md`。

下一步仍是 Unity 工程授權／Android 模組完成後匯入編譯，再將此核心接入任務、玩家輸入、擺設／敵軍渲染、NGO 世界快照與可靠統計傳送。現有 Unity 場景未呼叫此核心，管理介面也尚不會自動驅動它；沒有 APK、實機射擊／AI、實機混用或 25 人效能證據。整體長期目標維持開發中。

## 2026-10-29：v0.6 瀏覽器主控台、任務與平面配置

在 Unity 授權／Android 模組等待期間推進可獨立驗證的管理操作。新增 `/console/`，與 API 同程序提供繁體中文軍事風格主控／房間介面。可查看五房名額、從任務建立獨立／五房 Linked 場次、操作開始／暫停／繼續／結束、設定環境與敵軍、管理自房玩家及下載短效玩家連線檔。統計含六項需求指標、剩餘血量、明確來源與歷史查閱；操作紀錄不是 3D 回放。

任務編輯器支援名稱、內容、時間、環境／敵軍及沙包／油桶上視圖配置，可拖曳、方向鍵移動、輸入座標與旋轉、移除，再儲存為新的不可變任務；重新載入保留配置。尚無碰撞檢查、場館校正、任務版本鏈、覆寫或 Unity 載入這份配置。

控制台憑證僅保留在頁面記憶體，登出或重新載入需重新登入；所有資料仍由既有 API 授權，房間控制台不能修改 Linked 整場設定或其他房玩家。下載檔只含玩家票券與遊戲連線資料。使用獨立 JS／CSS 檔案、CSP、文字渲染，不載入第三方 CDN。靜態 web root 固定在輸出目錄，實際 DLL 從儲存庫根目錄啟動亦可服務，不依賴 Development 的來源映射。

管理命令失去回應時保留原 commandId／body／expectedSequence，鎖定後續寫入並提供重試；暫停與 End 的實際已接受／回應遺失情境均驗證只追加一次。待確認時停止刷新，避免已結束場次從活動列表消失而藏住重試入口。表單保存載入序號，舊設定不能覆寫他人命令，背景更新不會悄悄改掉正在輸入的草稿。建立／加入／離開去重與跨頁面重試恢復仍未完成。

本機 Release 建置 0 警告、0 錯誤；**128 項核心、229 項 HTTP 與 36 項真實 Chromium 檢查通過**。瀏覽器使用獨立 API、SQLite 與隨機憑證；驗證拖曳／重載、單房與 Linked 開局、環境／敵軍命令、權限、票券、過期表單、失去回應後重試、模擬統計、未信任文字、登出與手機寬度。已檢視截圖，位於忽略的 `artifacts/console/`。測試原先將 fieldset 當作 Playwright disabled 目標，已改驗實際輸入與按鈕；拖曳測試先捲動到可見圖面後操作。

瀏覽器相依固定 Playwright 1.62.1／pnpm 11.25.0，鎖定檔已產生。F 槽 exFAT 導致 pnpm 預設符號連結安裝失敗；確認 pnpm 11 改從 `pnpm-workspace.yaml` 讀取 `nodeLinker`，新增 hoisted 設定後，已鎖定安裝到隔離的 `artifacts/browser-hoisted` 並以該處套件執行 36 項檢查通過。未更改系統執行原則。CI 已加入鎖定安裝及瀏覽器檢查，雲端執行仍須解除既有 GitHub 帳戶付款／支出限制。操作說明見 `CONSOLE.md`。

當次已用 `start-local.ps1` 啟動本機 API，`/health` 及 `/console/` 實際回傳 200，確認 Production 也能載入介面；不是已部署的 Windows 常駐服務，後續先檢查實際程序，避免重複啟動。

完整長期目標仍未完成。Unity 仍無成功編譯／APK／頭盔證據；實際戰鬥、AI、硬體、MR、自由觀戰、世界快照與 3D 回放尚待開發。

## 2026-10-29：v0.5 Quest 3 工程來源碼與玩家票券

依「先用 META QUEST 3」建立 `clients/unity/`，固定 Unity 6000.3.27f1、OpenXR 1.19.0、XR Management 4.6.1、NGO 2.7.0、Input System 1.17.0、URP 17.0.4。採官方 URP Blank 17.1.0 的專案／渲染設定並保留授權，不含模板快取或雲端專案連結。來源碼包含簡化五區軍事場景生成、頭手姿態、桌面伺服器／玩家模式、玩家審核、狀態與霧／日夜／閃光同步。這些仍待 Unity 實際編譯與運行。

後端新增 HMAC-SHA256 五分鐘玩家入場票券。主控／自房控制台可配發，僅 GameServer 可驗證；驗證包含場次、名冊、到期與已結束狀態。簽章鑰保存在忽略的本機資料目錄，可重啟沿用；不寫進事件。每房固定 `seat` 0–4，離開時其他玩家不移位；舊事件沒有席位時依原加入順序重建。頭盔設定僅含地址、埠及自己的票券，不含控制台／GameServer 憑證。完整撤銷／重連與已連線玩家踢出仍待整合。

新增 `prepare-vr-session.py` 產生自己的單房 Preparing 場次與連線檔、`build-unity.ps1` 建置／EditMode 入口、`deploy-quest.ps1` 型號與設定欄位檢查及部署入口。詳細操作與限制見 `QUEST3.md`。HTTP 測試實際驗證設定助手與票券，但沒有執行 Unity 玩家或 ADB。

本機鎖定還原與 Release 建置通過，0 警告、0 錯誤；**128 項核心檢查及 229 項 HTTP 斷言通過**。包含票券竄改／到期／跨場次／錯誤角色／離開與結束拒絕、API 重啟後票券可驗、舊名冊恢復席位及玩家檔案不含伺服器憑證。8 份 Unity C# 通過 C# 9 純語法解析；PowerShell 腳本通過語法解析。語法檢查未綁定 Unity SDK，不能代替 Unity 編譯。

工具鏈：Unity CLI 1.0.0-beta.14 已安裝；Editor 已完整安裝至 `F:\Tools\UnityEditors\6000.3.27f1`，原安裝程序已成功結束，Package Manager 已就緒。實際 `build-unity.ps1 -Target Prepare` **退出 198：未登入／未啟用有效 Unity 授權**，日誌在 `artifacts/unity-logs/prepare.log`。已請使用者本機執行 `unity auth login` 並啟用適用授權；沒有自行建立帳戶、判定 Personal 資格或購買授權。

Android 模組尚未安裝。Unity 安裝器要求 `--accept-eula` 才能繼續 SDK／NDK 等模組安裝，已請使用者確認條款；尚未代為接受。**沒有成功的 Unity 編譯、生成場景／prefab、EditMode 結果、桌面程式、APK、雙玩家互見或頭盔實測**。下一個 Unity 步驟須先解決授權，再依 QUEST3.md 實際 Prepare／Tests／Desktop／Quest，修正編譯與執行問題。GitHub CI 的帳戶付款／支出限制仍無解除證據。

## 2026-10-29：v0.4 SQLite、戰鬥統計與 Quest 3 優先

使用者回覆「先用 META QUEST 3」。已同步路線、需求及開發指引：先實作 Quest 3 垂直切片，暫按 Android 獨立執行規劃，VIVE 後續接入；未將原始雙平台與 11 項需求縮減為後端原型。

新增 `VrCommand.Persistence`，使用 Microsoft.Data.Sqlite 10.0.14 與版本鎖定檔。預設事件改為 SQLite 交易逐筆追加，管理與戰鬥共用連續序號，記憶體採追加清單、命令／報告索引及增量統計；不再為每次射擊重寫全部歷史。舊 schema 1／2 JSON 先驗證後一次匯入，交易全有全無，原檔保留。單一寫入程序鎖、資料列／envelope 身分驗證與啟動恢復檢查均保留。

新增 schema 3 的 `CombatRecorded`、GameServer 認證接入、明確的 Simulation／GameServer 來源、射擊與命中關聯、唯一敵軍擊殺，以及傷害／血量投影。統計提供彈藥、命中數／命中率、擊殺、中彈、實際耗損及剩餘血量，保留已離開玩家並可重啟重建。主控與房間控制台不能提交戰鬥報告；模擬與 GameServer 來源不能同場混用。

新增 `scripts/demo_combat.py`：只在空閒房間建立自己的模擬場次，使用 Quest3 玩家分類，產生彈藥 3、命中率 66.67%、擊殺 1、中彈 1、耗損 20、血量 80，結束後保留歷史。HTTP 測試實際執行此腳本，並確認沒有占用既有場次或殘留房間名額。

本機鎖定還原與 Release 建置通過（0 警告、0 錯誤）。**119 項核心檢查、207 項 HTTP 斷言通過**，並將測試資料庫放在 `F:\Projects\vr-command-center\artifacts\temp` 重驗 SQLite、交易、鎖定及程序重啟。檢查涵蓋 schema 2 JSON 升級、錯誤匯入重試、唯一約束回滾、重複報告／射擊／擊殺拒絕、因果順序、傷害截斷、離開與暫停、事件不含憑證、兩次 API 重啟與統計一致。

五房 25 個 Quest3 分類的模擬玩家，合計 175 筆戰鬥報告，連同名冊／生命週期共 203 筆事件；總彈藥 75、命中 50、擊殺 25、耗損 500，各玩家血量 80。這是資料與儲存驗證，沒有 25 台頭盔、實際射擊／碰撞／AI 或 FPS／延遲證據。接收端信任 GameServer 來源的已分類事件，尚未獨立判斷真實場景命中。

契約、限制與升級流程見 `COMBAT_PROTOCOL.md`、`STORAGE.md`；CI 已加入 `--locked-mode`，但帳戶付款／支出限制造成雲端工作無法開始的問題尚無通過證據。完整長期目標仍在開發中。

## 2026-10-29：v0.3 控制台認證、五房權限與事件身分

所有 `/api` 端點現在要求 Bearer 控制台憑證，`/health` 保持公開。主控可管理全館；Room1–Room5 的列表／快照限制在自房及包含自房的共享場次，只能控制自己的獨立任務，以及管理本房玩家名額。全連線的整場命令只允許主控。GameServer 身分可讀取場次，不能管理任務、名額或場次；預留作為後續戰鬥事件來源。

新事件 envelope schema 2 保存伺服器驗證的控制台 ID／角色／房間，不保存憑證值。復原時重新檢查事件身分的權限；去重 ID 不能由另一控制台接管。舊 schema 1 保持可讀與 `actor: null`，不補造身分。核心的 Internal 身分僅供受信任的程序內部呼叫；HTTP 不會配發。

新增 `scripts/start-local.ps1`，首次產生七份不同的隨機本機憑證到 Git 忽略的 `data/operator-keys.local.json`，不在畫面印出鑰匙。也可使用環境變數或 `--OperatorKeyFile`；缺少主控、過短、重複或未知憑證設定會拒絕啟動。換鑰在重啟後生效。控制台認證尚不等同人員個別登入、TLS 部署或頭盔設備註冊。

本機驗證：Release 建置 0 警告、0 錯誤；**70 項核心檢查及 163 項 HTTP 斷言通過**，涵蓋五房列表／操作範圍、跨房讀寫拒絕、全連線權限、body 偽造角色無效、錯誤設定拒絕啟動、憑證檔載入、重啟換鑰與舊鑰失效、事件不含憑證，以及既有場次恢復與併發去重。啟動助手已通過 PowerShell 語法解析；HTTP 測試驗證其使用的憑證檔啟動方式，未對實際開發憑證檔進行操作。

文件已同步至 `AUTHORIZATION.md`、README、API 與事件契約。戰鬥統計尚未實作；下一步先選定可持續接收戰鬥事件的儲存方式，避免將高頻事件塞入目前逐次重寫完整檔案的低頻管理事件儲存，再實作統計與模擬器。M1 與完整長期目標均未完成。

## 2026-10-29：v0.2 場次生命週期與持久化管理事件

已實作 `Preparing → Running ↔ Paused → Ended` 管理狀態，建立場次與真正開始分開。新增環境與敵軍設定命令、命令去重 ID、可選預期序號及活動／歷史場次列表。結束後保留名冊與事件，並釋放房間與玩家名額。

事件包含版本、事件 ID、場次 ID、連續序號、後端 UTC 時間及資料；以相同轉移規則在重啟時重建狀態。採單一寫入程序鎖與暫存檔替換；寫入成功才更新記憶體。第二個 API 程序無法同時取得同一事件目錄。未知 schema、損壞資料與序號缺口會使啟動失敗，不重設歷史。

驗證於 Windows 本機完成：Release 建置 0 警告、0 錯誤；**50 項核心檢查及 116 項 HTTP 斷言通過**。包含 20 次併發核心命令重送、12 次併發 HTTP 重送、兩次實際 API 程序重啟、活動與結束場次恢復、第二個 API 寫入程序被拒絕、版本衝突、磁碟錯誤不推進狀態與損壞檔案拒絕恢復。測試資料與子程序在結束後清理。

契約與操作範例見 `SESSION_PROTOCOL.md`、`API.md` 及 README。v0.1 的 `GET` 已結束場次由 404 改為可讀取歷史；`StartedAtUtc` 改為在 `Begin` 前可為 null。建立／加入／離開操作尚未提供客戶端去重 ID；優先使用 `/commands` 進行可重試的控制。

這些是管理事件，尚無操作者身分、戰鬥事件、傷害、3D 世界快照或頭盔同步；環境／敵軍命令僅更新設定，尚未接到渲染或 AI。M1 仍在進行中。GitHub 雲端 CI 的帳戶付款／支出限制尚未解除，本次結果僅宣稱本機驗證。

## 2026-10-28：建立長期目標及 M0

長期目標已在本對話建立，維持開發中；本地開發根目錄為 `F:\Projects\vr-command-center`。本檔保存接續工作的事實與依賴，整體需求見 `REQUIREMENTS.md`。

GitHub 長期開發追蹤：[Issue #1](https://github.com/peca12968/vr-command-center/issues/1)。階段完成後更新此追蹤與本地文件。

已建立管理核心、REST API、任務 JSON 範例、核心規則檢查與 GitHub Actions 工作流程。後端使用本機已有的 .NET SDK 10.0.400；尚未安裝或建立 Unity 工程。

Release 建置成功：0 警告、0 錯誤。15 項核心檢查全部通過，包含五房獨立、全館 25 人名額、併發加入限制、快照隔離、任務持久化與場次釋放。66 項 HTTP 斷言全部通過，包含實際服務啟動、JSON 往返、錯誤碼與完整名額操作。

上述測試在 Windows 本機執行。私人 GitHub 儲存庫已建立，首次提交 `f4b836a` 已推送至 `main`，遠端私有狀態與分支已確認。實際指令見根目錄 README；CI 設定使用相同建置、核心檢查及 HTTP 整合腳本。

GitHub Actions [首次執行](https://github.com/peca12968/vr-command-center/actions/runs/40720827902) 在任何 step 啟動前失敗。check-run `122930936531` 的 annotation 明確回報：最近帳戶付款失敗，或需要提高 spending limit。第二次提交的執行也於啟動前失敗。**雲端 CI 尚未驗證，不能標示通過**；未變更帳務或啟用付費執行器。本機測試仍可執行，M1 開發不受影響。

## 未完成與外部資料

- Unity 工程尚未編譯或運行；共用核心已有 .NET 驗證，管理／配置 UI 與 3D 模擬回放可操作。Unity／頭盔遊戲、硬體通訊、正式持久錄影與即時觀戰仍待整合。
- 尚未收到廠商 SDK／協議；需依 `HARDWARE.md` 取得資料。
- VIVE XR 確切型號、Android 一體機／PCVR、場館尺寸與網路架構待確認。
- 沒有頭盔或硬體實測證據；25 個玩家記錄通過不代表 25 人實際連線達標。

## 接續位置

下一主線是解決 Unity 授權與 Android 模組條款後實際匯入／編譯，接入共用戰鬥核心、任務擺設、輸入與世界同步，完成 Quest 3 雙玩家切片。管理建立／加入／離開去重、裝置準備與重連、可靠世界儲存、自由觀戰及 3D 回放仍需補齊。等待使用者操作期間可繼續不依賴 Unity 的世界資料與回放工具；雲端 CI 須等 GitHub 帳戶付款／支出限制解除。每次開始先查實際 Git／程序與最新證據，不把無頭盔模擬當成已驗證的遊戲。
