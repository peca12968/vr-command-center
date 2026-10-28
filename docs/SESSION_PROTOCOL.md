# 場次與事件契約 v0.4

本契約目前僅實作管理資料狀態。狀態為 `Running` 不代表已連接遊戲伺服器，`Pause` 尚不會停止頭盔畫面或硬體。

## 生命週期

```mermaid
stateDiagram-v2
    [*] --> Preparing: 建立並保留房間
    Preparing --> Running: Begin，至少一名玩家
    Running --> Paused: Pause
    Paused --> Running: Resume
    Preparing --> Ended: End
    Running --> Ended: End
    Paused --> Ended: End
```

建立時複製任務模板，`CreatedAtUtc` 記錄建立時間；`StartedAtUtc` 在首次 `Begin` 設定，恢復時不覆寫。`EndedAtUtc` 在結束時設定。所有事件時間由後端產生，以序號決定順序，不依賴裝置時鐘。

玩家只可在 `Preparing` 加入，在任一未結束狀態離開。沒有自動開局、倒數結束、斷線偵測、設備準備確認或重連席位。控制台權限見 `AUTHORIZATION.md`。結束時保留當時名冊供歷史查閱，活動名額全部釋放；曾離開的玩家可從事件查閱。

`SetEnvironment` 與 `SetEnemies` 可用於任一未結束狀態。它們更新場次的執行設定，不修改任務模板，也不影響其他獨立場次。已結束的場次拒絕新操作；成功命令的原樣重送仍可查詢接受結果。

## 命令

`POST /api/sessions/{id}/commands`：

```json
{
  "commandId": "251227ab-bc64-4aca-9838-55db6f49dd99",
  "action": "Pause",
  "expectedSequence": 27
}
```

`expectedSequence` 可省略；有指定時必須符合伺服器目前序號，否則回傳 409，讓控制者重新載入再決定。命令重送的去重檢查優先於版本檢查，因此已接受的同一命令即使版本已前進仍能取得結果。

去重範圍是每場次。相同 ID 必須由同一認證身分發出且有完全相同的解析後內容，包含 `expectedSequence`；改變內容或身分回傳 409。回應 `duplicate`、`appliedAtSequence` 表示是否重送及原始接受位置，`session` 一律為最新快照，而非原命令當時的舊狀態。新接受事件與去重資訊一起寫入磁碟，重啟後仍有效。

環境設定範例：

```json
{
  "commandId": "9904f941-aa41-4ca3-808e-8a7efb8677dc",
  "action": "SetEnvironment",
  "environment": { "mode": "VR", "weather": "Rain", "timeOfDay": "Night", "lightning": false }
}
```

敵軍設定範例：

```json
{
  "commandId": "111298ae-c5ce-4746-9e0b-17062e869fae",
  "action": "SetEnemies",
  "enemies": { "count": 8, "behavior": "Advance", "autoAttack": true }
}
```

與動作無關的設定欄位會回傳 400。`commandId` 不可為空 GUID，`action` 不可省略。控制台身分由認證中介層指定，請求 body 的 `actor` 不會改變權限或紀錄來源。

## 事件讀取與持久化

`GET /api/sessions/{id}/events?after=0&limit=100` 回傳事件陣列。每場次從序號 1 開始，僅接受的變更會遞增；讀取端以最後收到的序號作為下一次 `after`，空陣列表示已讀到目前尾端。預設 100、最多 500 筆；沒有訂閱推播與長輪詢。

共同欄位為 `schemaVersion`（新事件為 3）、`eventId`、`sessionId`、`sequence`、`recordedAtUtc`、`kind`、`payload` 及 `actor`。schema 1／2 歷史仍可讀取，schema 1 的 `actor` 保持 null，細節見權限文件。

| kind | payload | 用途 |
|---|---|---|
| `Created` | mode、roomIds、完整 mission | 建立事件與任務快照 |
| `PlayerJoined` | id、name、roomId、headset | 玩家加入名冊 |
| `PlayerLeft` | playerId | 玩家離開 |
| `ControlApplied` | 完整 ControlCommand | 生命週期或執行設定變更 |
| `CombatRecorded` | 完整 CombatReport | 可去重且帶來源標記的戰鬥統計事件，僅 schema 3 |

預設儲存於 `SessionDataDirectory/events.db`，每次事件以交易追加後才更新記憶體及統計。單一目錄仍以 `.writer.lock` 限制寫入程序；舊 JSON 歷史會驗證後一次匯入並保留原檔，詳見 `STORAGE.md`。

服務啟動時從事件重建活動與歷史場次，驗證 schema、身分、連續序號、事件／命令 ID、狀態轉移與活動房間／玩家衝突。資料損壞或未知版本時啟動失敗，不靜默丟棄歷史。執行中的場次會恢復管理狀態；此行為尚不涵蓋遊戲世界、裝置重連或硬體恢復。

事件逐筆追加並增量更新統計，但啟動時仍載入所有場次；尚無保留／刪除介面、世界快照或姿態串流。戰鬥事件已有傷害及射擊關聯，仍不包含 3D 位置與動畫，不能視為需求第 9 項的 3D 任務回放。實際遊戲的傳輸與批次寫入將在 Quest 3 垂直切片中整合。
