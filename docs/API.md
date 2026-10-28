# 管理、統計與玩家接入 API v0.9

REST、UTF-8 JSON；預設範例地址 `http://127.0.0.1:5080`。列舉使用字串，不接受數字列舉。提供管理、統計與短效入場票券；姿態不經此 API。Unity 遊戲來源碼尚待編譯／運行。所有 `/api` 呼叫須帶 `Authorization: Bearer <credential>`；配置與角色表見 [AUTHORIZATION.md](AUTHORIZATION.md)。

v0.6 新增瀏覽器介面 `/console/`，操作見 [CONSOLE.md](CONSOLE.md)。靜態介面可匿名載入，資料與操作仍經下列已認證 API；任務每次儲存使用 POST 建立新 ID，未新增覆寫或版本修改端點。

| 方法 | 路徑 | 行為 |
|---|---|---|
| GET | `/health` | 服務存活狀態 |
| GET | `/api/me` | 經認證的控制台身分與房間範圍 |
| GET | `/api/rooms` | 五房名額、場次與目前人數 |
| GET | `/api/missions` | 列出磁碟保存任務 |
| GET | `/api/missions/{id}` | 取得任務 |
| POST | `/api/missions` | 以 `examples/mission.json` 格式建立任務，回傳 201 |
| POST | `/api/sessions` | 依任務建立場次，回傳 201 |
| GET | `/api/sessions` | 活動場次；加 `?includeEnded=true` 包含歷史 |
| GET | `/api/sessions/{id}` | 場次快照及玩家名冊，包含已結束場次 |
| POST | `/api/sessions/{id}/commands` | 套用帶有去重 ID 的控制命令，回傳接受序號與最新狀態 |
| GET | `/api/sessions/{id}/events` | 有序管理／戰鬥事件，參數 `after` 預設 0、`limit` 預設 100，上限 500 |
| POST | `/api/sessions/{id}/combat` | GameServer 身分提交已分類戰鬥報告，回傳去重收據與統計 |
| GET | `/api/sessions/{id}/statistics` | 包含曾離開玩家的統計、資料來源及統計涵蓋序號 |
| POST | `/api/sessions/{id}/players` | 加入玩家，回傳場次快照 |
| POST | `/api/sessions/{id}/players/{playerId}/join-ticket` | 主控／自房控制台配發五分鐘玩家票券，回傳 200 |
| POST | `/api/player-tickets/validate` | 僅 GameServer 驗證票券及現行名冊，回傳玩家與固定席位 |
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

建立場次進入 `Preparing`，此時才可加入玩家。開始後可離開但不能新增／重新加入玩家；重連與保留席位將在遊戲接入階段實作。`Begin` 至少需要一名玩家，尚未要求每房滿額或設備準備完成。

控制命令、狀態圖、去重／版本語意與事件格式見 [SESSION_PROTOCOL.md](SESSION_PROTOCOL.md)。新命令使用 `Begin`、`Pause`、`Resume`、`End`、`SetEnvironment` 或 `SetEnemies`。Unity 狀態／環境接入程式尚待編譯；AI 與硬體尚未接入。

已處理的輸入錯誤回傳 400、認證失敗 401、權限不足 403、找不到任務／場次／玩家 404、房間占用／玩家重複／人數超限 409。領域錯誤 JSON 為 `{ "error": "原因" }`；JSON 語法與模型繫結錯誤由 ASP.NET Core 處理，回應內容格式可能不同。無法解析的 GUID 路徑因路由限制回傳 404。

任務時間範圍 60–14400 秒；敵軍數量 0–100；物件最多 500。這些是原型輸入範圍，尚非實機效能承諾。環境可設定 `VR`／`MR`、`Clear`／`Rain`／`Fog`／`Storm`、`Day`／`Night` 及 `lightning` 布林值；可藉命令更新場次設定並留下事件。Unity 霧／光照／閃光程式尚待驗證，MR、雨粒子與雷聲尚未實作。

## 玩家票券

配發端點無 body，回傳 `{ "ticket": "<opaque>", "expiresAtUtc": "<UTC>" }`。配發不消耗事件序號，重試會產生另一份票券。主控可配發任意本場玩家，房間控制台限自己的玩家；GameServer 無配發權。Preparing、Running、Paused 可配發，Ended 回傳 409。

遊戲伺服器帶 GameServer Bearer 呼叫驗證端點：

```json
{ "sessionId": "<場次 GUID>", "ticket": "<玩家提供的票券>" }
```

成功回傳 `{ "sessionId": "<GUID>", "playerId": "<GUID>", "roomId": 1, "seat": 0 }`。票券格式／簽章／到期／跨場次錯誤、玩家已離開或場次已結束回傳 403；缺少 API 憑證仍為 401。票券不具有 REST 權限，頭盔不應取得 GameServer 憑證或直接呼叫此端點。

票券不是一次性：目前仍在名冊且未到期可再次驗證。同一玩家離開後又以相同 ID／房間加入，舊未到期票券可能再次有效；尚無每次加入的撤銷版本。Unity 伺服器有同一玩家同時重複連線拒絕程式，仍待運行驗證。移除玩家不會自動斷開現有 Unity 連線。詳見 [QUEST3.md](QUEST3.md)。

## 相容性

v0.9 新增上述三個端點的選用去重標頭。新事件使用 schema 4，保留 schema 1–3 讀取；新 PlayerLeft 保存房間，requestId 隨接受事件一起持久化。事件資料庫結構仍為 user_version 1。寫入 schema 4 後不能用舊版程式服務同一資料目錄。

v0.5 新增玩家票券及名冊 `seat`；事件仍為 schema 3。舊事件缺席位時按歷史加入順序分配，明確的錯誤／重複席位拒絕恢復。簽章鑰與事件分開保存，不隨任務或歷史送出。

v0.4 新事件使用 schema 3，支援讀取 schema 1／2；JSON 歷史一次匯入 SQLite，見 `STORAGE.md`。報告需明確標記 Simulation 或 GameServer，詳見 `COMBAT_PROTOCOL.md`。

v0.3 新增強制控制台認證與房間範圍授權；匿名 `/api` 呼叫不再成功。新事件使用 schema 2 及伺服器認證的 `actor`；仍可讀取 schema 1 歷史。

`GET /api/sessions/{id}` 現在可讀取已結束場次；不再因結束而回傳 404。快照新增 `state`、`createdAtUtc`、`endedAtUtc`、`environment`、`enemies` 與 `sequence`；`startedAtUtc` 改為可為 null，僅在 `Begin` 後有值。程式層的 `SessionManager.Start` 改名為 `Create`，避免與真正開始遊戲混淆。
