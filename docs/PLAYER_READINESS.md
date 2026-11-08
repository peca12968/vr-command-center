# 玩家參戰快照

## MR 開場條件

控制台 0.31.12 建立的 MR 場次需要 GameServer 錄製來源。按開始時，管理服務核對最後接受的準備中快照及當前管理序號，並逐位比對名冊、入場識別、房間、席位與有效追蹤姿態。快照沿用 1.5 秒的來源新鮮度門檻。換人、管理變更或姿態中斷後，需等新快照確認再開始。

目前 MR 名冊支援 Quest 3。遊戲伺服器要求對應入場房間的 MR 連線設定，並拒絕桌面合成姿態。測試用追蹤快照驗證開場條件。Quest 3 實際位置、光學透視和場館對位另行驗收。 [Quest 3 部署](QUEST3.md#主控建立-mr-場次)

## 五房總覽

控制台 0.31.6 在使用中的房卡顯示名冊人數、有效姿態及合成／追蹤各自的人數。主控可同時查看五房。房控只收到自己房間的摘要，即使場次使用五房連線模式。

`GET /api/rooms/readiness` 回傳 `version: 1` 和可讀房間的摘要。每房包含場次識別、序號、名冊人數、兩種姿態數與來源新鮮度。五房共用一個場次時，服務以同一份已接受的快照分房計數。彙整沿用參戰快照的 admission、席位、健康、連線與姿態判定。摘要沒有個別玩家資料。

總覽頁可見且有使用中的房間時，每秒最多查詢一次。畫面核對房間、場次、序號與名冊人數。超過原本的 1.5 秒新鮮度門檻時撤下有效人數。讀取失敗、換頁或登出也會清除有效狀態。開始與結束仍由操作員決定。

Windows 三包整合可加上 `--check-room-readiness` 核對兩種模式的實際房間計數，再加 `--observe-closure-ui` 檢查新版控制台的房卡與封存。 [三包測試方式](WINDOWS_SERVER_PACKAGE.md#三個可攜包整合驗證)

本機三包測試在五房獨立與五房連線各驗證 25 個模擬玩家，兩種模式的 API 摘要均為每房 5 筆有效合成姿態。瀏覽器也實際顯示五個獨立房間的總覽。追蹤人數的瀏覽器呈現以測試回應驗證，頭盔實機仍待。 [開發進度](PROGRESS.md)

API／控制台0.29新增名冊旁的「即時參戰快照」與有效人數。操作員可以直接區分已登記的頭盔分類、已接受世界中的有效姿態，以及等待來源／姿態中斷；不必只看名冊人數推斷玩家是否在場。

這是**已接受快照的參戰觀察**。Simulation 明確顯示合成姿態，Tracked 表示該份來源提交追蹤資料。VR 開始、暫停與結束仍沿用原控制政策。MR 開場另使用本頁的名冊和快照檢查。

## 操作與狀態

登入主控或房間控制台，選取場次。在「玩家名冊」每位玩家旁查看姿態狀態；摘要顯示來源與有效人數。只在房間與場次頁且頁面可見時，約每秒讀一次診斷，每250ms更新本地老化顯示；不傳送頭手座標或逐幀輸入。

| 顯示 | 意義 |
|---|---|
| 等待遊戲來源／第一份快照 | 名冊或header已存在，但未有可用世界幀 |
| 姿態有效 · 合成／追蹤姿態 | 同一次入場、存活、connected且來源時間有效的最後已接受身體 |
| 等待本次入場同步 | 同一playerId已重新入場，但舊frame觀察的admission／房間／席位不符 |
| 姿態未就緒／中斷 | 該入場的身體未connected或沒有可用頭手來源 |
| 已淘汰 | 保存健康已為0，不視為有效參戰 |
| 快照已過期／擷取時間未知／來源時鐘未同步 | 不以收到時間或心跳補造新鮮度 |
| 等待階段同步／管理連線中斷 | 來源階段尚未追上管理，或來源明確suspended |
| 場次已結束 | End立即優先；舊的有效身體不再顯示為參戰 |

來源年齡使用原header.captureStartedAtUtc＋最後packet.elapsedMilliseconds，相對API抽樣時間計算；保留既有超前1000ms／過期1500ms邊界。瀏覽器再從**請求開始**計算performance單調經過時間，包含下載等待，沉默超過門檻即移除綠色；不是拿HTTP回應抵達時間重設來源時鐘。這是保守觀察，不是RTT、網路延遲或FPS。

暫停中的玩家仍可有有效姿態，畫面同時顯示場次已暫停；有效姿態不表示正在射擊。失聯、切頁、換場或登出會取消／隔離舊請求；場次epoch、登入epoch與current admission／room／seat均須相符，舊回應不能恢復綠色。UI管理序號已較新時，舊readiness報告只顯示等待更新。

## API與保存邊界

`GET /api/sessions/{id}/readiness`僅Master／可讀此場次的RoomController；逐次傳遞已認證Actor並檢查房間範圍，GameServer及Internal也不當控制台使用。Linked讀取沿用既有場次讀取政策，不改玩家操作的房間權限。

回傳version1、sessionId／sessionSequence、sampledAtUtc、sourceState／origin、worldSequence／observedSequence、capturedAtUtc／sourceAgeMilliseconds及當前名冊的playerId／admissionId／roomId／seat／state／rigKind／canParticipate。沒有座標、票券或主控／GameServer key。每份報告只代表其sessionSequence與抽樣時點；管理與來源可能在下一瞬間改變，不能拿它授權玩家戰鬥。

WorldRecordings在自己的gate下讀最後已接受幀，並以SessionManager.Observed還原該幀真正看到的名冊，與本次管理快照比對admission／room／seat。重新加入同一playerId，即使舊frame仍新鮮且connected，也不得沿用舊身體。僅讀現有資料，不追加事件、修改投影、改舊header、補造舊擷取時間或新增DB schema。envelope7、world schema1、rules0.8.0及原素材pin保持；既有新格式reader限制不變。

Unity仍0.31.0／code38／NGO29及原雙平台receipt，本輪不改遊戲wire／追蹤／入場政策，不重新建置或宣稱新的141項Editor結果。部署API／UI0.29需一起更新；工具的版本gate同步，避免新版控制台對舊API讀不存在的狀態。

## 驗證

18項新增.NET規則檢查含真正SQLite／歷史投影、權限、無frame、source時間邊界、舊admission與階段／suspended／End、legacy未知時間及只讀性。HTTP另驗證未登入／外房／GameServer拒絕及不含姿態／憑證。4項Node規則與6項瀏覽器UI反例涵蓋old admission、silence、下載耗時、換場／登出及合成／追蹤標籤；UI fixture回應不當作原生證據。

真正原生整合入口：

```powershell
python scripts/check-desktop-readiness.py --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns" --api-dll <本次隔離API.dll>
# 等該工具輸出native-ready，再在另一個終端執行：
pnpm --dir tests/browser exec node check-readiness-native.cjs <該次desktop-readiness目錄>/ready.json
```

只接受自己的desktop-readiness目錄、Simulation／0頭盔及非5080 loopback URL。工具開兩個真正headless Unity client，先確認名冊不等於參戰、雙端有效，再結束自己peer程序、以同一playerId換新admission、啟動新程序。瀏覽器讀**實際API**、不mock readiness，核對2→1→新入場未就緒→2、Begin／Pause／End、兩份自己的結果與雙精確seal。沒有姿態、射擊RPC或統計注入，沒有GPU／PCM／實體鍵盤觀察；Chromium為SwiftShader。

失敗也End／seal並停止全部writer，保留C SSD原件後一次snapshot回F；保存SQLite不開連線，原件／snapshot逐檔SHA核對。工具fingerprint與API build路徑另記錄；只能在UI真正完成對應觀察後寫該run的done，不重用舊run。實際成功／失敗、版本、雜湊與限制見[PROGRESS](PROGRESS.md)。完整25台、跨機、Quest／VIVE／MR與硬體驗收仍待。
