# 共用戰鬥模擬核心 v0.8

`clients/unity/Packages/com.vrcommand.simulation/Runtime/` 是唯一來源；`src/VrCommand.Simulation` 直接編譯這些檔案，目標 .NET Standard 2.1／C# 9，無 Unity、管理 API 或資料庫相依。Unity 工程將它作為 embedded package，尚未實際匯入／編譯，也尚未從現有場景建立世界。管理 API 與瀏覽器介面維持 v0.6 契約。

目前已證明 .NET 遊戲規則與幾何模擬，以及讀取紀錄的瀏覽器 3D 回放，不能當作 Quest／VIVE、Unity Physics、IL2CPP、網路延遲或 25 台裝置驗收。Android 工具已安裝整理並通過 ARM64 原生編譯；Unity 編輯器仍未取得有效授權，見 `QUEST3.md`。

## 規則與資料

| 項目 | 已實作規則 |
|---|---|
| 時間／狀態 | 每步 0.05 秒；Preparing → Running ↔ Paused → Ended。只有 Running 推進 tick、AI、射擊與換彈。暫停可更新追蹤姿態，但不能新增射擊 |
| 場地 | 1 房或全部 5 房，每房最多 5 人；房間原點 X = (roomId − 3) × 14m。每房範圍 ±6m，角色中心保留 0.3m 邊界距離 |
| 玩家姿態 | 檢查有限值、頭高 0.45–2.4m、槍口與頭距離 ≤1.2m、方向長度及場地範圍，平面移動不能穿越掩體；沒有移動速度／延遲補償驗證 |
| 碰撞 | 沙包及油桶使用可旋轉的實心盒；角色使用簡化身體盒。射線取最近交點，掩體／隊友擋住後方敵軍，沒有穿透、散彈、彈道下墜或爆炸 |
| 武器 | 玩家有效射程 40m、每 4 tick 可射一次、每次傷害 50、彈匣 30／備彈 90。換彈需 30 個執行中 tick，從備彈補足彈匣 |
| 傷害 | 玩家／敵軍初始血量 100；AI 每次 20 傷害、攻擊間隔 20 tick。死亡後不射擊、不再受傷／重複計殺，沒有復活、補血、護甲或友軍傷害 |
| AI | Hold 原地守備；Patrol 沿指定兩端往返；Advance 追向同房最近存活玩家。0.5m 四鄰格點 BFS 尋路，掩體按角色半徑擴張，移動上限 0.1m/tick；不可達時停留 |
| AI 控制 | 受信任伺服器可變更 Hold／Patrol／Advance、自動攻擊及能見度／日夜；可新增／移除敵軍，最多 100 個當前實例，移除後不能重用同一實例 ID |
| AI 視線 | 同房玩家進入範圍才選取；晴天 15m、暴風雨 10m、霧 6m，夜間上限 8m。攻擊須有未受掩體或其他身體阻擋的射線。Advance 尋路知道所選玩家位置，尚無隱匿／記憶與戰術協作 |
| 重試 | 射擊 ID 保存原始結果，重送不再次扣彈／傷害；同 ID 不能由另一玩家接管。換彈命令也去重，原先接受的重試可在暫停／結束後確認 |

Tick 是邏輯步進；示範程序加速執行，尚未提供實際 20 Hz 遊戲伺服器排程器。世界由單一呼叫執行緒持有，網路端之後須排序與驗證輸入，不能直接並行修改世界。

場景目前平坦、沒有樓梯／跳躍／角色間擠壓、動態掩體或複雜網格碰撞。呼叫者需選擇不與角色重疊的出生點；新增角色目前檢查掩體與邊界，未驗角色相互重疊。角色移動只限所屬房間，全連線的空間轉換、跨房移動與實體定位仍待場館設計。

配置器可保存超出此範圍的資料；轉接到此原型時須明確驗證／回報，不能默默丟掉不支援的物件。本核心不是硬體協議或登入授權層：只能由通過身分／場次驗證的遊戲伺服器呼叫，不可直接暴露給頭盔指定命中或血量。

## 世界快照與事件

`Snapshot()` 回傳目前 tick、phase、throughSequence、玩家頭部／槍口／方向／彈藥／血量，以及敵軍位置與血量。陣列與內部狀態分離。`Events(after, limit)` 使用嚴格大於 after 的序號，單頁最多 500；事件 ID 生成後不變，含 tick、種類、玩家、射擊、敵軍與傷害。

世界事件包含 ShotFired、ShotHit、EnemyEliminated、EnemyShot、PlayerDamaged、ReloadStarted／Completed。模擬工具把其中四種統計事件轉為既有 `CombatReport`，以世界 eventId 作 reportId，**一律標記 Simulation**。AI 射擊與換彈不冒充玩家彈藥或擊殺；每次成功玩家射擊只有一份 ShotFired。

世界事件目前留在程序記憶體；API 的 SQLite 只接收轉換後的管理／戰鬥事件。v0.8 工具另存 `schemaVersion: 2`／`rulesVersion: 0.8.0`，新增 world props、快照中的 AI／能見度／夜間設定及射擊事件的槍口、方向、距離、碰撞類別／目標。相同 tick 仍可能有多次變化，需使用 throughSequence 與陣列順序；瀏覽器回放原型見 `REPLAY.md`。舊 schema 1 除錯檔保留但不猜測缺少的射線。正式持久儲存、資產版本、斷點恢復與實機回放仍待完成。

## 幾何模擬示範

管理 API 已啟動時，在儲存庫根目錄執行（先完成下面建置）：

```powershell
dotnet artifacts/build-v08/bin/VrCommand.SimulationDemo/release/VrCommand.SimulationDemo.dll --room 5
```

工具從本機 `data/operator-keys.local.json` 讀取 Master／GameServer 憑證，不輸出憑證；可指定 `--key-file`、`--base-url`、`--room`、`--output`。只在空閒房新建自己的場次，不改既有名冊，成功或失敗後嘗試結束自己的場次。

情境為：低槍口被油桶擋住，AI 命中玩家一次，操作設定關閉自動攻擊，玩家側移並命中兩次擊殺，再加入另一個敵軍巡邏繞障 10 秒。傷害與命中由共用核心計算並依序送入 API。預期 **彈藥 3、命中 2、命中率 66.67%、擊殺 1、中彈 1、耗損 20、血量 80**，216 份快照及 8 筆世界事件。工具是腳本驅動的無頭盔模擬，未從控制台持續輪詢指令。

統計及結束紀錄可在主控台勾選「包含已結束紀錄」後查閱；世界除錯 JSON 預設寫入 `artifacts/simulation-demo/<場次ID>.json`。不會傳送訊息或呼叫實際硬體。

## 隔離建置與驗證

Windows 執行中的 API 會鎖住 DLL。以下使用另一個輸出目錄，不需要停止現有主控台；CI 在乾淨工作目錄仍可沿用 README 的一般建置。

```powershell
dotnet restore VrCommand.slnx --locked-mode --artifacts-path artifacts/build-v08
dotnet build VrCommand.slnx --configuration Release --no-restore --artifacts-path artifacts/build-v08
dotnet artifacts/build-v08/bin/VrCommand.Checks/release/VrCommand.Checks.dll
$env:VR_COMMAND_API_DLL = "$PWD/artifacts/build-v08/bin/VrCommand.Api/release/VrCommand.Api.dll"
$env:VR_COMMAND_SIMULATION_DEMO_DLL = "$PWD/artifacts/build-v08/bin/VrCommand.SimulationDemo/release/VrCommand.SimulationDemo.dll"
python scripts/smoke_api.py
```

瀏覽器檢查也接受 `VR_COMMAND_API_DLL`，命令仍見 `CONSOLE.md`。`check-unity-source.ps1` 現在同時檢查遊戲端及 embedded package，僅提供 C# 9 語法結果；共用核心另由上述 .NET Standard 建置進行真正的 API 型別綁定。

本機證據：Release 建置 0 警告／0 錯誤，**181 項核心、234 項 HTTP、12 項回放資料及 50 項 Chromium 檢查通過**；12 份 Unity／套件 C# 語法通過。核心另新增射線紀錄及快照設定驗證，回放驗證範圍見 `REPLAY.md`。沒有測量頭盔 FPS 或 25 台連線效能。

## 待接入

Unity 端須加入此組件參考、從任務與名冊建立世界、對接已認證的玩家輸入、固定步進排程、敵軍／擺設渲染及 NGO 快照，再將已確認的戰鬥事件可靠送入 API。現有 Unity 場景尚未呼叫此核心；控制台按鈕目前也不會自動驅動這個示範程序。之後補齊硬體轉接、權威姿態驗證、持久 outbox、完整世界回放及觀戰。

技術來源：[Unity 6000.3 C# compiler](https://docs.unity.com/en-us/engine/6000.3/manual/programming-environment/overview-of-dot-net-in-unity/csharp-compiler)、[.NET API profiles](https://docs.unity.com/en-us/engine/6000.3/manual/programming-environment/overview-of-dot-net-in-unity/dotnet-profile-support)、[embedded packages](https://docs.unity.com/en-us/engine/6000.3/manual/packages-list/dependencies-lp/upm-embed)。這些是選型依據，實際 Unity 編譯與實機相容仍需另外驗證。
