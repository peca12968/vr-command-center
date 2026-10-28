# 管理 API v0.1

REST、UTF-8 JSON；預設範例地址 `http://127.0.0.1:5080`。列舉使用字串，不接受數字列舉。這是低頻管理介面，沒有姿態串流、遊戲伺服器或角色驗證。

| 方法 | 路徑 | 行為 |
|---|---|---|
| GET | `/health` | 服務存活狀態 |
| GET | `/api/rooms` | 五房名額、場次與目前人數 |
| GET | `/api/missions` | 列出磁碟保存任務 |
| GET | `/api/missions/{id}` | 取得任務 |
| POST | `/api/missions` | 以 `examples/mission.json` 格式建立任務，回傳 201 |
| POST | `/api/sessions` | 依任務建立場次，回傳 201 |
| GET | `/api/sessions/{id}` | 場次快照及玩家名冊 |
| POST | `/api/sessions/{id}/players` | 加入玩家，回傳場次快照 |
| DELETE | `/api/sessions/{id}/players/{playerId}` | 離開並釋放名額，回傳 204 |
| DELETE | `/api/sessions/{id}` | 結束並釋放房間，回傳 204；目前不保存歷史 |

建立場次：

```json
{ "missionId": "<任務 GUID>", "mode": "Linked", "roomIds": [1, 2, 3, 4, 5] }
```

獨立場次使用 `"mode": "Independent"` 與單一房間，例如 `[2]`。

加入玩家：

```json
{ "playerId": "<非空 GUID>", "name": "Player A", "roomId": 1, "headset": "Quest3" }
```

`headset` 可為 `Quest3`、`ViveXr`。此資料由呼叫者提供，目前不會確認設備實際連線，也不會偵測離線；名額需明確呼叫離開或結束場次釋放。

已處理的輸入錯誤回傳 400、找不到任務／場次／玩家回傳 404、房間占用／玩家重複／人數超限回傳 409。領域錯誤 JSON 為 `{ "error": "原因" }`；JSON 語法與模型繫結錯誤由 ASP.NET Core 處理，回應內容格式可能不同。無法解析的 GUID 路徑因路由限制回傳 404。

任務時間範圍 60–14400 秒；敵軍數量 0–100；物件最多 500。這些是原型輸入範圍，尚非實機效能承諾。環境可設定 `VR`／`MR`、`Clear`／`Rain`／`Fog`／`Storm`、`Day`／`Night` 及 `lightning` 布林值；目前僅保存設定，沒有渲染與實時控制。
