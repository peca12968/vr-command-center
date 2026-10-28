# 戰鬥統計契約

本契約沿用 v0.4 引入的 schema 3 事件接收、因果檢查、去重、統計與復原。v0.7 共用核心已可獨立判定幾何射擊、敵軍血量及 AI 傷害，並透過 Simulation 示範接入，見 `SIMULATION.md`；尚未由 Unity 場景或頭盔輸入驅動。API 仍信任持有 GameServer 憑證的來源報告，不會從畫面推算命中。`origin: GameServer` 是來源宣告，不是實機驗收證明。

## 接收與讀取

`POST /api/sessions/{id}/combat` 只允許 GameServer 身分（受信任的程序內部也可呼叫核心），主控與房間控制台回傳 403。新報告只在 `Running` 接受。範例：

```json
{
  "reportId": "bd89d00b-981f-45fe-bcc0-a66bd578ea36",
  "kind": "ShotFired",
  "origin": "Simulation",
  "playerId": "8cc8f8cc-7716-4981-a10a-e8a0e6ac2bd6",
  "shotId": "cd417719-2cae-4b08-a723-e891560b0102"
}
```

| kind | 必要資料 | 判定與更新 |
|---|---|---|
| ShotFired | playerId、唯一 shotId | 當前且存活玩家；彈藥使用 +1 |
| ShotHit | playerId、shotId、enemyId | 同玩家已射出的尚未計分射擊、尚未被消滅的敵軍；命中射擊 +1 |
| EnemyEliminated | playerId、shotId、enemyId | 必須對應同玩家、同敵軍的已確認命中；每個敵軍實例僅記一次擊殺 |
| PlayerDamaged | playerId、damage（1–1000） | 當前且存活玩家；中彈 +1、血量扣除，最低為零 |

除 PlayerDamaged 外 `damage` 必須為 0；ShotFired 不帶 enemyId，PlayerDamaged 不帶 shotId／enemyId。GUID 不可為空。報告中無關的欄位會被拒絕，避免混合不同事件語意。

`origin` 必須明確為 `Simulation` 或 `GameServer`。首份成功報告決定整場來源，之後不能混用。模擬器永遠使用 Simulation。命令與報告的去重 ID 具有各自的命名空間；報告 ID 在每場次內唯一，相同來源身分及相同內容的重送不重複計數，改變內容回傳 409。失敗報告不進入歷史，可在修正前置順序後原樣重試。

回應包含 `reportId`、`appliedAtSequence`、`duplicate` 與最新 `statistics`。先前成功報告可在暫停／結束後原樣重送；新報告在暫停／結束時回傳 409。事件採伺服器接受順序，命中先於射擊抵達會被拒絕，來源須按因果順序發送或重試。

`GET /api/sessions/{id}/statistics` 遵循場次讀取權限，包含曾加入後離開的玩家。回應帶有 `sessionId`、`throughSequence`（管理與戰鬥共用序號）、`origin`（尚無報告時為 null）及 `players`。

## 統計定義

- ammoUsed：成功記錄的唯一射擊數，每次計一發；統計 API 不回傳剩餘彈藥。v0.7 共用核心另管理彈匣／換彈／備彈，但尚未接入 Unity HUD。
- shotsHit：至少命中一次的射擊數；本版單一射擊最多計一次命中，不支援散彈／穿透多目標計分。
- accuracyPercent：shotsHit / ammoUsed × 100，保留兩位小數；未開火為 0。
- kills：唯一敵軍實例的已確認消滅次數；沒有助攻。敵軍復活應使用新的實例 ID。
- hitsReceived：對存活玩家成功套用的傷害事件數。
- damageTaken：實際扣除血量總和，過量傷害不灌入數值；health 初始 100，最低 0。

目前沒有護甲、補血、復活與陣營傷害規則。「自身耗損」暫以實際血量減損表示。玩家離開後不能新增射擊或傷害，但已記錄射擊的命中／擊殺仍可結算，直到場次結束。玩家資料可在準備階段重新加入，正式遊戲中的斷線保留席位待整合。

管理後端檢查射擊歸屬、命中前置、重複敵軍擊殺、來源與場次狀態；場景敵軍、碰撞與死亡須由遊戲伺服器確認。共用核心已有這些簡化判定，但尚未完成真實輸入與世界同步整合；不得將原始硬體感測直接視為有效擊殺。

## 模擬範例

先用 `scripts/start-local.ps1` 啟動 API，再於另一個終端執行：

```powershell
python scripts/demo_combat.py --room 1
```

腳本要求指定房間空閒；建立自己的模擬任務及 Quest3 玩家名冊，送入三次射擊、兩次命中、一次擊殺與一次 20 點傷害，最後結束自己建立的場次並輸出統計。預期彈藥 3、命中率 66.67%、擊殺 1、中彈 1、耗損 20、血量 80。它保留任務與歷史供查閱，不變更既有場次；沒有實際操作頭盔或硬體。

這個 REST 接入適用於驗證契約與模擬。實際遊戲的傳輸、批次入庫、伺服器 tick、姿態／世界快照與 25 台裝置效能仍需在 Quest 3 原型中量測與整合。

另有 `tools/VrCommand.SimulationDemo`，使用共用核心實際算出油桶阻擋、AI 傷害及敵軍死亡後再提交報告，不以預寫的命中結果代替判定；操作見 `SIMULATION.md`。該程序仍強制 Simulation，不能作為 Unity／頭盔遊戲已完成的證據。
