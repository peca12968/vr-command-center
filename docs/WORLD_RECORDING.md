# 持久世界錄製與觀察 v0.16

2026-10-31 新player-body-v1保存playerPresentationVersion1與每玩家hasPlayerPresentation／walking，按接受移動及保存tick重建人物。舊缺失0不推測人物步態，body與腕點不改原rig。遠端即時插值與10Hz保存幀分開比對，規範及新reader要求見 [PLAYER_BODY](PLAYER_BODY.md)。

2026-10-31 新來源另有combatAudioVersion1，缺失保持0；只依已接受的玩家／敵軍fire witness重建短聲音，不保存或宣稱原始音軌。新版本、音效gesture、跳轉／過期抑制及NGO25協同更新見 [COMBAT_AUDIO](COMBAT_AUDIO.md)。world schema1與原binary checksum保持，schema相同不代表可降舊reader。

2026-10-31 最新換彈／合成手套為API／UI0.21、Unity0.23／code26／NGO22；weaponPresentationVersion1及weapon-actions-v1需來源／API／UI／全體遊戲端一起更新，舊資料保持0／舊外觀，不可降舊reader。保存時鐘、Tracked界線及實際證據見 [WEAPON_ACTIONS](WEAPON_ACTIONS.md)／PROGRESS。

2026-10-30 最新人形敵軍接入為API／UI0.20、Unity0.22／Android code25／NGO21，header enemyPresentationVersion1及combatants-v1需協同更新；舊來源／外觀保留，不能降舊reader。保存姿態、原命中盒與限制見 [ENEMY_PRESENTATION](ENEMY_PRESENTATION.md)，真正建置／PC結果以 PROGRESS 為準。

v0.16 新增 `environmentVersion:1`，依保存的 tick／環境重現雨、日夜、閃電及選用聲音，非原始音軌。缺少欄位維持 0 legacy，不補造效果；UI 有音效開關，暫停／跳轉／過期的行為與協同升級見 [ENVIRONMENT.md](ENVIRONMENT.md)。新 NDJSON 示範也附擷取 UTC，舊來源不變。world schema 1 不變，但舊嚴格 reader 不接受新 header 欄位，不可直接降版。

管理主控台的「觀戰與任務回放」讀取遊戲伺服器已接受的世界資料。世界發布走 WebSocket，觀察及回放走帶 Bearer 的 fetch SSE；逐幀遊戲輸入仍由 NGO 處理，不使用管理 REST。觀察者不加入玩家名冊。既有「3D 模擬回放」仍用本機 schema 2 檔案；兩種格式及來源不可混為一談。

目前另有 **真正 Windows Unity → 共用來源／WebSocket → SQLite → SSE → 控制台即時觀戰／鏡頭與回放** 證據，見 [DESKTOP_CONTROL.md](DESKTOP_CONTROL.md)／PROGRESS。瀏覽器為 Chromium 軟體 WebGL；原生玩家 GPU 白天／雨夜／Pause 另行檢視。來源明確 Simulation、頭手合成，不是頭盔錄影或 Quest 驗收。原 v0.13 未編譯／授權問題僅為歷史，最新真正建置見 WORLD_SOURCE／NATIVE_VALIDATION。

## 操作

1. 啟動新版 API／主控台。用 Master 或所屬 Room 憑證登入，選「觀戰與任務回放」。
2. 更新錄製列表，選場次；列表標示房間、來源及是否完整。
3. 「即時觀戰」只取最新已保存快照；拖曳旋轉、Shift／右鍵平移、滾輪縮放，或用全景／上帝俯視／跟隨鏡頭。房間與角色可以選取。未參戰／死亡角色降低透明度。
4. 「從頭回放」按保存時間播放，不重新執行 AI。支援 0.25–4 倍速、暫停及時間跳轉，透過 SQLite 時間索引取前一份快照，不下載整場檔案。角色資訊顯示頭手來源 None／Simulated／Tracked。
5. 統計由各快照的已驗證事件前綴計算。以擷取時間計算超過 1.5 秒或串流中斷即顯示過期；SSE 心跳／補送不重設年齡，沒有時間標示未知，來源時間超前標時鐘未同步。Ended 及未封存仍可能同時存在。
6. 調整鏡頭後輸入名稱，按「保存目前位置」；從已保存位置選單按「切換位置」恢復固定世界目標、水平／垂直角度及距離。跟隨鏡頭保存的是當下位置，不會保存持續跟隨行為。相同控制台身分重新登入後，可在同場即時觀戰或回放讀回位置；不同場次或身分不共用。可移除位置，每個身分每場最多 24 個有效位置。

鏡頭設定與遊戲控制分開：保存／移除位置不改變世界幀、戰鬥事件或玩家名額。保存／移除回應遺失或 5xx 時凍結原 ID、位置及名稱，按「重試確認結果」原樣確認；等待期間可調整視角，但不能用新視角取代原請求或切換錄製場次。單次寫入等待最多 10 秒；登出／關閉頁面會失去待確認請求，再登入後應先讀取已保存位置確認結果。已接受後又被其他視窗移除的保存請求，重試回 Deleted 而不重建位置。名稱以 textContent 顯示。

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

v0.13 首選 checksummed binary 世界來源，共用 Unity／.NET publisher、擷取時間與補送操作見 [WORLD_SOURCE.md](WORLD_SOURCE.md)。上述 --recording 範例保留為舊 NDJSON 相容模式。

## API 與封包

所有端點都經既有 /api Bearer 驗證及 SessionManager 房間範圍檢查。

| 路徑 | 用途 |
|---|---|
| GET `/api/world-recordings` | 只列可讀場次的錄製 metadata |
| GET `/api/sessions/{id}/world` | header、acceptedSequence、durationMilliseconds、complete、updatedAtUtc、capturedAtUtc、missionName |
| WS `/api/sessions/{id}/world/publish` | 僅綁定該 combat-stream 的 GameServer 身分可發布 |
| SSE `/api/sessions/{id}/world/watch` | 最新已保存快照；可跳過中間幀，以免慢速觀察者積壓 |
| SSE `.../watch?mode=replay&fromMs=0&rate=1` | 順序回放；rate 僅 0.25／0.5／1／2／4 |
| GET `.../world/cameras` | 目前控制台身分在此錄製場次的有效鏡頭位置 |
| PUT `.../world/cameras/{cameraId}` | 以新的非空 GUID 保存不可變位置；相同 ID／內容重試確認原結果 |
| DELETE `.../world/cameras/{cameraId}` | 移除自己的位置；原 ID 重試可確認，不復活已移除資料 |

鏡頭端點僅 Master／RoomController 可用，每次均重新檢查錄製存在及目前房間讀取範圍，GameServer／Internal 不作控制台使用。命名空間使用完整 OperatorIdentity（ID、角色、房間），不是瀏覽器或員工帳號；共用同一控制台身分的視窗共用設定，Master 也不讀取其他控制台的鏡頭收藏。PUT body 為 `{ "name": "東側沙包", "view": { "target": [-14,0.8,0], "theta": 0.6, "phi": 0.9, "radius": 15 } }`；名稱 1–60 字元、不含控制字元／前後空白；target 三個有限分量各 ±120 m、theta ±π、phi 0.06–1.5、radius 2–240 m。不同內容重用 ID 為 409；未知／他人的 ID 移除為 404，已移除的同身分 ID 重試為 204。有效鏡頭超過 24 個時新保存為 409，同 ID 已接受的重試仍可確認。回傳位置包含 id、name、view、createdAtUtc、deleted。

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

v0.14.1 另以可新增的 camera_bookmarks 表保存不可變位置、完整身分命名空間與移除 tombstone，沿用此資料庫與單一寫入程序租約；不改 header／世界幀／統計／updatedAtUtc 或 schema 1。移除不實體刪掉原請求內容，保留原樣重試的判斷資料；未實作清理 tombstone 或跨任務鏡頭範本。API／主控台需一起更新；共享 Runtime、Unity NGO protocol 14 及場次 envelope 6 不變。

備份前先停 API，再備份整份 API data（missions、events.db、worlds.db、簽章 key），另保留來源 NDJSON／combat journal；不要只拷貝開啟中的單一 db 而漏掉 WAL。沒有自動刪檔、壓縮、保留政策、備援及加密儲存。

檢查包含核心拒絕／交易回滾、真實發布／觀察、跨程序來源重送、API 重啟、房間範圍、來源中斷、瀏覽器鏡頭／回放／行動版面。`python scripts/smoke_world.py` 是額外必要檢查；瀏覽器仍用 `tests/browser/check.cjs`，隔離建置另設 `VR_COMMAND_WORLD_RELAY_DLL`。

GameServer 是受信任的權威來源；格式及統計一致不等於每條射線重新跑物理驗證，也不證明姿態來自真人頭盔。鏡頭位置保存已有 Simulation／HTTP／SQLite／瀏覽器驗證；尚待 Unity 真正編譯運行發布器、Quest 頭手採樣與實機重連、正式美術／動畫／聲音、MR 校正、長任務壓測及 25 台設備效能驗收。
