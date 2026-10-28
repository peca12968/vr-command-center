# 持久世界錄製與觀察 v0.12

管理主控台的「觀戰與任務回放」讀取遊戲伺服器已接受的世界資料。世界發布走 WebSocket，觀察及回放走帶 Bearer 的 fetch SSE；逐幀遊戲輸入仍由 NGO 處理，不使用管理 REST。觀察者不加入玩家名冊。既有「3D 模擬回放」仍用本機 schema 2 檔案；兩種格式及來源不可混為一談。

本輪已驗證的是 **.NET 共用核心 → 本機來源檔 → 真實 WebSocket → SQLite → 真實 SSE → Chromium 軟體 WebGL**。示範明確為 Simulation，雙手及旋轉為合成；不是頭盔錄影、實機追蹤或 Quest 驗收。Unity 目前只有共享錄製 DTO，**尚未接上世界發布器／實際頭手採樣**；原有統計 outbox 來源碼另見 TELEMETRY。Unity 編譯仍受授權未被工具讀取影響。

## 操作

1. 啟動新版 API／主控台。用 Master 或所屬 Room 憑證登入，選「觀戰與任務回放」。
2. 更新錄製列表，選場次；列表標示房間、來源及是否完整。
3. 「即時觀戰」只取最新已保存快照；拖曳旋轉、Shift／右鍵平移、滾輪縮放，或用全景／上帝俯視／跟隨鏡頭。房間與角色可以選取。未參戰／死亡角色降低透明度。
4. 「從頭回放」按保存時間播放，不重新執行 AI。支援 0.25–4 倍速、暫停及時間跳轉，透過 SQLite 時間索引取前一份快照，不下載整場檔案。角色資訊顯示頭手來源 None／Simulated／Tracked。
5. 統計由各快照的已驗證事件前綴計算。來源超過 1.5 秒沒有新快照，畫面顯示中斷／過期；SSE 心跳不重設新鮮度。Ended 及未封存仍可能同時存在。

切頁、換場或登出會取消當前串流，舊回應不能恢復場景。所有文字採 textContent，不執行任務／玩家名稱內的標記。憑證只在頁面記憶體及 Authorization 標頭，不放 URL、localStorage、sessionStorage 或 cookie。

## 可重現示範與補送

從專案根目錄執行，房間 5 必須空閒，輸出檔必須不存在。工具只建立及控制自己的 Simulation 任務，其他場次不變。

```powershell
dotnet tools/VrCommand.WorldRelay/bin/Release/net10.0/VrCommand.WorldRelay.dll --recording F:/Projects/vr-command-center/artifacts/world-demo/example.ndjson --demo-room 5 --seconds 3
```

預設服務 `http://127.0.0.1:5080`，使用忽略的 `data/operator-keys.local.json`，不輸出密鑰。可指定 `--base-url` 與 `--key-file`。`--seconds` 為 1–60 秒，逐 20 Hz 邏輯 tick 產生快照；寫入／網路耗時使實際牆鐘時間更長，這不是吞吐量或 25 台裝置效能測試。會記錄 Preparing、實際射擊／AI 傷害、Pause、Storm／Night／Lightning 設定、Ended，先確認戰鬥封存再確認世界封存。

來源檔以單行 JSON 保存 header／frame／seal，寫入後 Flush(true)，再送出並等待逐幀回應。旁邊 `.combat` 是既有 checksummed TelemetryOutbox。來源檔及 journal 都只允許獨占寫入；不儲存憑證。預設任務只有一位合成玩家，沒有頭盔連接。

原程序停止後，可以由另一程序讀同一來源：

```powershell
dotnet tools/VrCommand.WorldRelay/bin/Release/net10.0/VrCommand.WorldRelay.dll --recording F:/Projects/vr-command-center/artifacts/world-demo/example.ndjson
```

先補送持久戰鬥報告，再逐行送出原始世界資料；已接受的同序同內容只確認，不再新增。來源缺少 seal／Ended 或戰鬥未完整，不會自行製造完成。JSON 壞尾端、內容衝突會停止，不截斷／忽略損壞資料。工具目前遇到網路錯誤會退出，保留來源供手動重送；不宣稱自動重連或崩潰後世界繼續運算。來源 NDJSON 沒有簽章／逐行 checksum，磁碟／傳輸可接受性仍依賴受信任來源及伺服器驗證。

## API 與封包

所有端點都經既有 /api Bearer 驗證及 SessionManager 房間範圍檢查。

| 路徑 | 用途 |
|---|---|
| GET `/api/world-recordings` | 只列可讀場次的錄製 metadata |
| GET `/api/sessions/{id}/world` | header、acceptedSequence、durationMilliseconds、complete、updatedAtUtc、missionName |
| WS `/api/sessions/{id}/world/publish` | 僅綁定該 combat-stream 的 GameServer 身分可發布 |
| SSE `/api/sessions/{id}/world/watch` | 最新已保存快照；可跳過中間幀，以免慢速觀察者積壓 |
| SSE `.../watch?mode=replay&fromMs=0&rate=1` | 順序回放；rate 僅 0.25／0.5／1／2／4 |

WebSocket 使用一般 Authorization Bearer 握手；不可將頭盔玩家票券當成 GameServer 憑證。每條新 socket 先送 header。UTF-8 文字訊息上限 1 MiB；不接受二進位或未知訊息種類。

```json
{"type":"header","payload":{"schemaVersion":1,"sessionId":"…","streamId":"…","origin":"Simulation","rulesVersion":"0.8.0","assetSet":"primitives-v1","calibration":"uncalibrated-vr","roomIds":[5],"props":[]}}
{"type":"frame","payload":{"sequence":1,"elapsedMilliseconds":0,"observedSequence":3,"throughCombatSequence":0,"suspended":false,"weather":"Clear","lightning":false,"frame":{"tick":0,"throughSequence":0,"phase":"Preparing","behavior":"Hold","visibility":"Clear","autoAttack":true,"night":false,"players":[],"enemies":[]},"events":[]}}
{"type":"seal","finalSequence":44}
```

範例只展示形狀，實際 props／players／enemies 必須符合任務，省略名冊不可發布。成功回應 `{"type":"ack","info":...}`，只在持久交易 commit 後確認。拒絕回 `type:error` 並結束 socket；斷線未收到 ack 應重送原內容。這不是逐幀事務跨 combat.db／worlds.db 的分散式交易；戰鬥前綴可以已接受，世界仍待重送。

header 綁定既有戰鬥 streamId、來源及同一 owner；房間／物件 ID、位置、旋轉與任務規範幾何逐項相同。只支援 rules 0.8.0、primitives-v1、未校正 VR，未知版本／MR 拒絕。第一幀必須 Preparing、tick 0、零事件及零戰鬥邊界。幀序號連續、時間／管理觀察不倒退，Ended 後不可續錄新幀；已接受的歷史幀仍可確認。

每份快照包含玩家頭／槍口／方向、健康／彈匣／備彈／換彈／參戰、頭旋轉／左右手位置旋轉與來源、敵軍位置／健康、環境與 AI 政策，以及自前幀以來完整世界事件。最多 25 玩家、100 敵軍、500 事件／幀；向量／四元數／房間界線及事件格式有界。24 小時／100 萬幀為目前硬限制，不代表已測此容量。

觀察序號須為已接受管理歷史。政策／名冊與該稀疏管理快照核對；管理中斷允許 `suspended=true` 的 Paused 記錄引用 Running，但不能假造新管理命令。四種統計事件必須逐筆對上已持久化的 combat report ID、stream sequence、origin、kind、player、shot、enemy 及 damage，且不引用比此幀更新的觀察。血量及剩餘彈藥與此前綴一致。非統計世界事件的 ID 亦跨幀唯一。

`complete=true` 要求最後一幀為 Ended、finalSequence 精確一致、戰鬥來源已 sealed、throughCombatSequence 對上 acceptedSequence，並核對最終玩家統計。API End 釋放房間不會替來源製造末幀或世界 seal。

SSE 以 `header`、`frame`、`status`、`complete` 事件輸出單行 JSON。frame 有 packet 及此刻 statistics；status 約每秒回 metadata。replay complete 後串流結束；live 可以繼續顯示最後結果。背壓直接等候 socket／HTTP 寫入，不建立每位觀察者的無界快照佇列。

## 儲存與驗證邊界

`SessionDataDirectory/worlds.db` 使用 WAL／synchronous FULL，schema 1。recordings 保存不可變 header 及 cursor，world_frames 以 session／sequence 為鍵並建 elapsed 索引，world_event_ids 保證跨幀事件唯一。每幀、統計、事件 ID、cursor 在同一交易；拒絕／寫入失敗不留下部分幀。重啟不把整場幀載入記憶體，播放讀取當前幀。管理／戰鬥核心仍保留既有事件記憶體投影，未宣稱全系統恆定記憶體。

備份前先停 API，再備份整份 API data（missions、events.db、worlds.db、簽章 key），另保留來源 NDJSON／combat journal；不要只拷貝開啟中的單一 db 而漏掉 WAL。沒有自動刪檔、壓縮、保留政策、備援及加密儲存。

檢查包含核心拒絕／交易回滾、真實發布／觀察、跨程序來源重送、API 重啟、房間範圍、來源中斷、瀏覽器鏡頭／回放／行動版面。`python scripts/smoke_world.py` 是額外必要檢查；瀏覽器仍用 `tests/browser/check.cjs`，隔離建置另設 `VR_COMMAND_WORLD_RELAY_DLL`。

GameServer 是受信任的權威來源；格式及統計一致不等於每條射線重新跑物理驗證，也不證明姿態來自真人頭盔。尚待 Unity 真正發布、Quest 頭手採樣與實機重連、正式美術／動畫／聲音、MR 校正、書籤、長任務壓測及 25 台設備效能驗收。
