# 管理、統計與玩家接入 API

管理包 0.31.36 支援主控使用 `POST /api/venue/phase` 批次更新執行中場次的敵軍策略。預覽與送出需對上各場原階段及敵軍序號，房卡從 `GET /api/rooms/readiness` 讀取遊戲端確認。 [全館敵軍策略契約](LAYOUT.md#全館敵軍策略)

管理包 0.31.35 支援主控使用 `POST /api/venue/phase` 批次更新執行中場次的環境。預覽及送出需對上原場次的階段與環境序號，各房的遊戲端確認由 `GET /api/rooms/readiness` 提供。 [全館環境契約](ENVIRONMENT.md#全館即時環境)

API／UI0.27新增唯讀 `GET /api/sessions/{id}/report.csv`，Ended且戰鬥精確seal完成才產生reportVersion1最終CSV；未完成回409，僅操作員依現有房間讀取範圍可匯出，GameServer回403。Bearer認證、UTF-8 BOM及no-store；欄位／重試／範圍見 [REPORTS](REPORTS.md)。不新增持久schema或Unity wire，遊戲端維持0.28／NGO26，原降版限制仍適用。

最新API／UI0.26新增player-body-v1及playerPresentationVersion1、每玩家hasPlayerPresentation／walking；舊缺失保持0，來源／API／UI／全部NGO26遊戲端一起更新。新profile需原enemy／weapon／雙方fire版本1，漏標記與無版本姿態由伺服器拒絕；envelope6／world schema1／驗票2保持，不代表可降reader。規範見 [PLAYER_BODY](PLAYER_BODY.md)。

最新API／UI0.25加入獨立的combatAudioVersion1，必須同時有已接受的player／enemyFireVersion1；舊缺失保持0。已接受的stream重開不能移除音效政策。world schema1、envelope6與驗票2不變，新來源／API／UI／全部NGO25遊戲端一起更新，不可降reader，見 [COMBAT_AUDIO](COMBAT_AUDIO.md)。下方為保留的歷次契約說明。

v0.19 新增 [service-rifle-v1](SERVICE_RIFLE.md) 素材版本，保留field-props-v1／primitives-v1的讀取、預設及既有外觀。新Unity來源明確指定；未知版本與已接受header換版本仍拒絕。API／UI及遊戲端須協同更新；world schema1不表示可降版，管理及票券契約不變。

v0.18 新增 [VR 配置檢查](LAYOUT.md)：Master 草稿預覽、精確保存版本報告及新 VR 場次的後端檢查。無效的新建立回 400 `{ error, layout }`，草稿仍可保存；舊場次／已接受 request key 保留原結果。MR 明確不適用。API／UI 須一起更新；事件與世界 schema 不變。v0.17 的 field-props-v1／舊 primitives-v1 持續支援。

v0.16 世界 header 新增選用 `environmentVersion`（0 legacy／1 時間重現），未知版本或改動既有版本拒絕；舊回應補 0，原始持久 header 不改寫。新來源、API 與 UI 協同更新，見 [ENVIRONMENT.md](ENVIRONMENT.md)。管理命令路由不變。

REST、UTF-8 JSON；預設範例地址 `http://127.0.0.1:5080`。列舉使用字串，不接受數字列舉。提供管理、統計與短效入場票券；姿態不經此 API。Unity v0.17／NGO 17 已真正建置，PC 連線、撤銷／重連及五房證據見 PROGRESS；頭盔仍待驗。所有 `/api` 呼叫須帶 `Authorization: Bearer <credential>`；配置與角色表見 [AUTHORIZATION.md](AUTHORIZATION.md)。

瀏覽器介面 `/console/` 的操作見 [CONSOLE.md](CONSOLE.md)。靜態介面可匿名載入，資料與操作仍經下列已認證 API。v0.15 新增不可變任務修訂、metadata 歷史與 latest library；舊版本及既有場次不被改動，規範與資料遷移見 [MISSION_VERSIONS.md](MISSION_VERSIONS.md)。

| 方法 | 路徑 | 行為 |
|---|---|---|
| GET | `/health` | 服務存活狀態 |
| GET | `/api/me` | 經認證的控制台身分與房間範圍 |
| GET | `/api/rooms` | 五房名額、場次與目前人數 |
| GET | `/api/missions` | 相容列出全部不可變 Mission 快照，包含歷史版本 |
| GET | `/api/mission-library` | 每條任務系列的最新版及 lineage metadata，主控台輪詢使用 |
| GET | `/api/missions/{id}/version` | 精確版本及 series／number／previous／author |
| GET | `/api/missions/{id}/history` | 版號 metadata 分頁，before 不含、limit 預設 20／最多 100 |
| GET | `/api/missions/{id}` | 取得任務 |
| GET | `/api/missions/{id}/layout?mode=Independent` | 以明確身分讀保存版本的配置報告；預設單房，支援 Linked |
| POST | `/api/mission-layout` | 僅 Master，預覽 experienceMode／mode／enemyCount／props，不保存 |
| POST | `/api/missions` | 以 `examples/mission.json` 格式建立任務，回傳 201 |
| POST | `/api/missions/{id}/revisions` | 從精確 head 保存下一版，必須 Idempotency-Key；過時 base 為 409 |
| POST | `/api/sessions` | 依任務建立場次，回傳 201 |
| GET | `/api/sessions` | 活動場次；加 `?includeEnded=true` 包含歷史 |
| GET | `/api/sessions/{id}` | 場次快照及玩家名冊，包含已結束場次 |
| POST | `/api/sessions/{id}/commands` | 套用帶有去重 ID 的控制命令，回傳接受序號與最新狀態 |
| GET | `/api/sessions/{id}/events` | 有序管理／戰鬥事件，參數 `after` 預設 0、`limit` 預設 100，上限 500 |
| POST | `/api/sessions/{id}/combat` | GameServer 身分提交已分類戰鬥報告，回傳去重收據與統計 |
| GET | `/api/sessions/{id}/statistics` | 包含曾離開玩家的統計、資料來源及統計涵蓋序號 |
| POST | `/api/sessions/{id}/players` | 加入玩家，回傳場次快照 |
| POST | `/api/sessions/{id}/players/{playerId}/join-ticket` | 主控／自房控制台以 If-Match-Admission 配發五分鐘 v2 券，回傳 200 |
| POST | `/api/player-tickets/validate` | 僅 GameServer 以 protocolVersion:2 驗票及現行入場，回傳 admission／席位／throughSequence／expiry |
| DELETE | `/api/sessions/{id}/players/{playerId}` | 離開並釋放名額，回傳 204 |
| DELETE | `/api/sessions/{id}` | 結束、保存歷史並釋放房間，回傳 204；重複結束回傳 409 |

建立場次：

```json
{ "missionId": "<任務 GUID>", "mode": "Linked", "roomIds": [1, 2, 3, 4, 5] }
```

獨立場次使用 `"mode": "Independent"` 與單一房間，例如 `[2]`。

建立場次、加入玩家及移除玩家三個端點可帶 `Idempotency-Key: <非空 UUID>`。相同身分、端點／目標及內容的重試只接受一次，重啟後仍有效；同一 key 改內容、操作或身分回傳 409，房間權限仍須通過。UUID 必須為單一 `D` 格式（含連字號），空值、全零及多值回傳 400。成功回應標頭回傳同一 key；建立仍回傳 201 及同一 Location，加入回傳目前快照，移除仍回傳 204。未帶 key 的舊客戶端維持原行為，不能盲目重送寫入。

這些 key 是全館三種操作共用的識別空間，不能跨場次／操作重用；與每場次的 `commandId`／`reportId` 分開。重試確認的是歷史接受結果，不會重新建立場次、讓已離開玩家復活，或用舊移除操作踢掉後來重新加入的玩家。詳細最新快照與封存語意見 `SESSION_PROTOCOL.md`。

加入玩家：

```json
{ "playerId": "<非空 GUID>", "name": "Player A", "roomId": 1, "headset": "Quest3" }
```

`headset` 可為 `Quest3`、`ViveXr`。此資料由呼叫者提供，目前不會確認設備實際連線，也不會偵測離線；名額需明確呼叫離開或結束場次釋放。伺服器配發每房 `seat` 0–4，回傳名冊中的席位不因其他玩家離開而改變；呼叫者不能選擇席位。

建立場次進入 `Preparing`，此時才可加入玩家。開始後可離開但不能新增／重新加入名冊；仍在名冊的同次 admission 可重新配票及傳輸重連，見 RECONNECT。`Begin` 至少需要一名玩家，尚未要求每房滿額或設備準備完成。

控制命令、狀態圖、去重／版本語意與事件格式見 [SESSION_PROTOCOL.md](SESSION_PROTOCOL.md)。命令使用 `Begin`、`Pause`、`Resume`、`End`、`SetEnvironment` 或 `SetEnemies`。Unity PC 狀態／環境與 AI 已有原生執行證據；廠商硬體待文件與設備。

已處理的輸入錯誤回傳 400、認證失敗 401、權限不足 403、找不到任務／場次／玩家 404、房間占用／玩家重複／人數超限 409。領域錯誤 JSON 為 `{ "error": "原因" }`；JSON 語法與模型繫結錯誤由 ASP.NET Core 處理，回應內容格式可能不同。無法解析的 GUID 路徑因路由限制回傳 404。

任務時間範圍 60–14400 秒；敵軍數量 0–100；物件最多 500。這些是原型輸入範圍，尚非實機效能承諾。環境可設定 `VR`／`MR`、`Clear`／`Rain`／`Fog`／`Storm`、`Day`／`Night` 及 `lightning` 布林值；可藉命令更新場次設定並留下事件。v0.16 瀏覽器雨線／雷聲／光霧已有 Simulation 驗證，真正 Unity 已完成編譯／匯入／Windows／Quest 建置，PC 已執行不同房間環境；圖形聲光完整操作、MR 與頭盔仍待驗，見 ENVIRONMENT／PROGRESS。

## 玩家票券

配發端點無 body，必須帶 `If-Match-Admission: <目前 admissionId>`，回傳 `{ "ticket": "<opaque>", "expiresAtUtc": "<UTC>" }`。配發不消耗事件序號，重試會產生另一份票券。主控可配發任意本場玩家，房間控制台限自己的玩家；GameServer 無配發權。Preparing、Running、Paused 可配發，Ended 回傳 409。

遊戲伺服器帶 GameServer Bearer 呼叫驗證端點：

```json
{ "sessionId": "<場次 GUID>", "ticket": "<玩家提供的票券>", "protocolVersion": 2 }
```

成功回傳 sessionId、playerId、roomId、seat、admissionId、throughSequence 及 expiresAtUtc。票券格式／簽章／到期／跨場次錯誤、玩家已離開或場次已結束回傳 403；缺少 API 憑證仍為 401，缺少驗票 protocol 2 為 400。票券不具有 REST 權限，頭盔不應取得 GameServer 憑證或直接呼叫此端點。

票券不是一次性：目前仍在同一 admission 且未到期可再次驗證。相同 ID／房間重新加入會產生新 admission，舊未到期票券保持撤銷；移除後 Unity 重新取得管理快照會斷開舊連線，亦拒絕同一玩家同時重複連線。PC 原生撤銷／重連已驗證，詳見 [ADMISSION](ADMISSION.md)／[RECONNECT](RECONNECT.md)；不是頭盔或裝置認證證據。

## 相容性

v0.11 新增 GameServer 專用 combat-stream、reports、batch 及 seal 端點，格式見 `TELEMETRY.md`。SessionView 新增可為 null 的 combatStream，statistics 新增 pendingTelemetry；Ended 的已綁來源場次可依原 Running 觀察補送，精確封存後才表示完整尾端已確認。新事件 schema 5，讀取舊 1–4，SQLite user_version 仍 1；寫入後不可直接降版。

v0.9 新增上述三個端點的選用去重標頭。新事件使用 schema 4，保留 schema 1–3 讀取；新 PlayerLeft 保存房間，requestId 隨接受事件一起持久化。事件資料庫結構仍為 user_version 1。寫入 schema 4 後不能用舊版程式服務同一資料目錄。

v0.5 新增玩家票券及名冊 `seat`；事件仍為 schema 3。舊事件缺席位時按歷史加入順序分配，明確的錯誤／重複席位拒絕恢復。簽章鑰與事件分開保存，不隨任務或歷史送出。

v0.4 新事件使用 schema 3，支援讀取 schema 1／2；JSON 歷史一次匯入 SQLite，見 `STORAGE.md`。報告需明確標記 Simulation 或 GameServer，詳見 `COMBAT_PROTOCOL.md`。

v0.3 新增強制控制台認證與房間範圍授權；匿名 `/api` 呼叫不再成功。新事件使用 schema 2 及伺服器認證的 `actor`；仍可讀取 schema 1 歷史。

`GET /api/sessions/{id}` 現在可讀取已結束場次；不再因結束而回傳 404。快照新增 `state`、`createdAtUtc`、`endedAtUtc`、`environment`、`enemies` 與 `sequence`；`startedAtUtc` 改為可為 null，僅在 `Begin` 後有值。程式層的 `SessionManager.Start` 改名為 `Create`，避免與真正開始遊戲混淆。


## v0.12 世界串流

GET /api/world-recordings、GET /api/sessions/{id}/world 為房間範圍內 metadata；WebSocket .../world/publish 僅 combat-stream owner 可發布；fetch SSE .../world/watch 為只讀 live／replay，不占玩家席位。所有端點仍帶 Bearer，逐幀輸入不走 REST。封包、限制、精確封存及真實驗證範圍見 [WORLD_RECORDING.md](WORLD_RECORDING.md)。


## v0.14.1 觀戰鏡頭位置

v0.14.1 新增 GET `/api/sessions/{id}/world/cameras` 及 PUT／DELETE `.../cameras/{cameraId}`，由 Master／RoomController 管理自己的場次鏡頭位置；每次檢查房間範圍，設定依完整身分隔離。PUT 原樣重試確認不可變位置，DELETE 留移除記錄，晚到的保存不重建位置。最多 24 個有效位置，不變更遊戲／世界／統計；格式與驗證見 [WORLD_RECORDING.md](WORLD_RECORDING.md)。

## v0.13 世界擷取時間

header 的 captureStartedAtUtc 為選用 round-trip UTC 基準，世界 metadata 另有 capturedAtUtc（基準加已接受 elapsed）；updatedAtUtc 仍為接收時間。舊無時間 header 讀取／確認時補空值，不能重設既有 header 來偽裝新擷取時間。新來源需使用 v0.13 API。共享發布器、binary journal 及頭手來源在 WORLD_SOURCE.md。


## v0.14 入場 fence

Player 快照新增 admissionId，每次加入不同。配票及新的玩家 DELETE 必須 If-Match-Admission（單一非零 UUID）；已換入場回 409，缺／壞 header 回 400。DELETE 的 Idempotency-Key 重試保留原 fence，已接受的舊請求只確認、不移除新入場；換 fence 視為改內容。v1 票券全部拒絕，GameServer 驗票 body 需 protocolVersion:2。事件新版本 6、讀舊 1–5，詳見 [ADMISSION.md](ADMISSION.md)。
