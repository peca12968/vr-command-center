# 任務版本與保存 v0.15

任務庫保存不可變的任務快照。新任務建立自己的 series，第 1 版的 ID 同時是 seriesId；修訂建立新的任務 ID，保存 seriesId、連續 number、previousId 與伺服器認定的 Author。任務本體仍為 schema 1，場次只綁定精確的任務 ID 及完整快照，不會隨任務庫的新版本改動。遊戲任務回放仍依原場次與已保存世界，不重新套用任務庫的最新版。

## 控制台操作

1. 在「任務庫與編輯」選取任務，按「載入最新版」。版本紀錄每次讀取 20 筆，按「讀取更舊版本」繼續；選取歷史版本後按「載入選取版本」讀回原名稱、內容、時間、環境、敵軍及物件配置。
2. 修改後按「保存為下一版」延續此任務。只能從目前最新的版本修訂；其他主控先保存新版時，草稿保留，舊版本不能分支或覆寫它。需明確載入最新版後編輯，或將手邊草稿另存為獨立任務。
3. 「儲存為新任務」建立新 series，原任務及版本鏈保持不變。名稱相同不代表相同任務；任務以 ID／seriesId 識別。
4. 「選用草稿原版開場」選取草稿所依據的已保存版本，再到「房間與場次」開局；未保存的修改不會套用。開場選單保留已選取的歷史版本並標註，不會在背景收到新版時偷偷切換。一般任務選單只列各 series 的最新版。

控制台 0.31.52 會在載入任務、建立新草稿、登出或重新整理頁面前提醒尚未儲存的修改。取消會保留原欄位、場地物件與復原紀錄。確認載入後，等選定版本成功讀回才會替換草稿。任務保存尚待確認時，手動登出也會提示重試資料將被清除。憑證失效時會直接登出，請在工作結束前保存需要保留的內容。

控制台 0.31.53 在版本紀錄提供「與目前草稿比較」。選取一個保存版本後，可以對照名稱、簡報、時間、環境、敵軍及場地物件。物件依清單順序列出素材、座標與旋轉，增減物件會反映在對應列。修改草稿或改選版本後，可重新按下比較。從結果按「選用比對的保存版本開場」會將該版帶到場次準備區，保留當前草稿。逐房指定模式下，選用會套到目前預覽的房間。儲存草稿時會保留開場區已選定的版本。

在「房間與場次」的「開場條件預覽」，可核對選定的保存版本、目標房間、時間、初始天氣及敵軍策略，並展開完整簡報。預覽會標明敵軍數適用全場或各獨立場次，場地物件依每房數量顯示。場地檢查通過且所選房間空閒後，可建立準備場次。切換到歷史版本時，預覽與建立請求會共同使用該版本的 ID。

背景更新不覆蓋草稿。已知版本號在同一次登入期間只前進；晚到的較舊任務列表不能倒退剛從歷史端點讀到的版本。載入歷史與任務定義均檢查登入 epoch，登出清理版本列表、草稿及配置。資料庫備份還原會使這些單調假設失效，還原後須重新載入頁面並登入，不把還原當作正常的版本刪除。

保存新任務與修訂都使用固定 Idempotency-Key。網路中斷、逾時或 5xx 時，UI 保留原 kind／parent／名稱／內容／配置／key，凍結新寫入與載入，按工作區上方「重試確認結果」確認原請求。保存已接受、但後續版本資料讀回失敗，也保留此請求，不再產生另一份新任務。關閉／重新載入／登出會失去記憶體中的待確認操作，應先讀回任務庫確認結果。

## 五房各自獨立

1. 使用主控憑證登入，在「房間與場次」選擇已保存的 VR 或 MR 任務版本。
2. 將模式設為「五房各自獨立」，核對五間房及各場的場地、敵軍設定，再按「建立五個準備場次」。如有房間在送出前被占用，服務會回報房號，五場都不會建立。
3. 每個房間會有自己的場次 ID。房控可開啟本房場次進行名冊、連線及開場準備，之後各自開始或結束。若送出後顯示「結果未確認」，用「重試確認結果」取回原五場。

主控也可等所有準備中的場次就緒，再一次開始。 [全館開始](MISSION_CLOCK.md#全館開始)

管理端的 `POST /api/sessions/independent-set` 需要主控身分及有效的 `Idempotency-Key`，請求使用 `{ "missionId": "<保存版本 ID>" }`。成功回傳 `201` 及 `{ sessions, duplicate: false }`，五場在同一筆交易寫入，按房號排序。相同金鑰與原版本重送回傳 `200` 及 `duplicate: true`，包括服務重啟或原場次結束後，回傳的仍是原五個 ID 及其當前狀態。房間被占用時回傳 `409`、`independent-rooms-occupied` 及 `roomIds`。

### 逐房指定任務版本

管理包 0.31.46 可在「五房各自獨立」勾選「逐房指定任務版本」。各房起始使用目前選取的共用版本，可各自換成其他保存版本。選擇「預覽房間」可核對該房的任務時間、環境、敵軍與平面圖。要指定歷史版本，先在編輯器載入該版，按「選用草稿原版開場」，即可套用到目前預覽的房間。已指定的版本在任務庫更新後仍會保留。

五房都選好且場地檢查通過後，主控才可建立。任何一房在送出時被占用或配置不合格，整批不會寫入。VR 和 MR 可分配到不同獨立房間。管理包 0.31.47 可替這種場館一次下載五房部署 ZIP，各房再依自己的模式開場。 [混合配票](QUEST3.md#混合-vr-與-mr-五房部署包)

相同 API 可改送 `{ "rooms": [{ "roomId": 1, "missionId": "<保存版本 ID>" }, …] }`，列出房間 1 至 5 各一次。兩種請求欄位擇一。服務以房號正規化順序，重送時必須保留原房間與版本的配對。批次使用不同版本且配置失敗時，回應會附第一個受影響的房號和場地檢查。同一保存版本指派到多房時，該版本只檢查一次。

建立含不同版本的五房批次後，管理資料需用 0.31.46 或更新的管理包開啟。各房事件保留自己的任務快照，第一房的建立事件另存依房號排列的版本 ID 雜湊，供服務重啟核對原配對。

## API

所有端點須 /api Bearer 認證並傳入已認證身分。任務是全館共用範本，Master、RoomController、GameServer 可讀；建立／修訂只允許 Master，受信任的 in-process Internal 可用於工具／匯入，HTTP 不配發 Internal。版本作者來自服務端身分，請求 body 不提供作者欄位。舊 JSON 匯入版標記為 Internal，這表示舊來源沒有作者資訊，不代表可以識別原始操作人。

| 方法與路徑 | 內容 |
|---|---|
| GET `/api/mission-library` | 各 series 最新的 MissionRevision：mission、seriesId、number、previousId、author；控制台輪詢使用它 |
| GET `/api/missions` | 相容原有契約，列出所有不可變 Mission 快照，包含舊版；不供主控台背景輪詢 |
| GET `/api/missions/{id}` | 精確版本的原 Mission，schema 1 不變 |
| GET `/api/missions/{id}/version` | 精確版本及 lineage／author 包裝，不隨 head 改動 |
| GET `/api/missions/{id}/history?before=5&limit=20` | 任一版所屬 series 的 metadata 歷史；before 為不含該版號的游標，limit 1–100，預設 20 |
| POST `/api/missions` | MissionDraft 建立獨立 series；相容不帶 key 的呼叫，UI 固定提供 key |
| POST `/api/missions/{previousId}/revisions` | MissionDraft 從該精確 head 建立下一版；必須 Idempotency-Key，previousId 即預期 head 的比對條件 |

history 回傳 seriesId、查詢時的 headId／headNumber、versions 及 nextBefore。每筆 versions 只有 id、seriesId、number、previousId、createdAtUtc、name、author，不帶所有場景物件；選取後才讀完整版本，避免一頁下載整條歷史的 500 物件定義。nextBefore 為 null 表示沒有更舊資料。追加新版本不會改動既有頁面的版號邊界。

新建／修訂成功皆為 201，Location 指向該精確 Mission。任務寫入的 request ID 在整個任務庫內唯一，不能換 kind、父版本、完整定義或作者；它與場次操作的 request ID 命名空間分開。已接受請求重試會回原版本，即使其後已有更多修訂。新 request 使用過時 previousId 為 409；非法定義／key／游標為 400、權限為 403、未知任務為 404。沿用舊的不帶 key 的新任務 POST，每次呼叫仍會建立新 series，不能宣稱這種呼叫可安全重試。

場次建立仍使用 POST `/api/sessions` 的 missionId，傳哪一版就完整綁定哪一版；建立、Preparing、Running 及歷史場次都不跟著 head 移動。沒有以新版本修改既有任務、刪除版本、分支、合併草稿或一鍵復原 head 的功能。可將舊版另存新任務；恢復舊內容到原系列需先載入最新版，再明確編輯保存。

## 儲存與升級

`DataDirectory/missions.db` 為獨立 SQLite schema 1，WAL／synchronous FULL；`.library-writer.lock` 僅允許一個程序管理此任務庫。新任務／修訂的完整 schema 1 Mission、series／number／previous、作者及 request ID 在同一列及交易提交，UNIQUE(series,revision)／request 與前置 head 檢查保證線性、不可覆寫及原樣重試。head 由連續不可變版本推得，沒有另寫容易失同步的 head JSON。

第一次啟動在同一交易內讀取原 GUID.json，驗證 schema／ID／完整定義，原樣匯入為獨立第 1 版，然後寫入完成 marker。原 JSON bytes 保留，不再是寫入來源。任何非法 JSON 或不一致鏈使初始化失敗並回滾，不跳過／丟棄損壞任務。後續只讀 catalog，不再匯入後來放進資料夾的 JSON。使用目前 Core 的舊 MissionStore 讀寫已版本化目錄會拒絕，避免只看到殘留的舊 JSON；不要混跑不同版 API 或用舊 writer 寫進此目錄。

升級前先停止自有 API 並備份**整份實際資料目錄**：任務 JSON／missions.db／WAL、場次 events.db、世界 worlds.db、簽章及控制台 key。預覽的任務與場次在 `src/VrCommand.Api/data`，root `data` 另有控制台 key／連線設定。隔離 DLL 啟動須明確指定 DataDirectory／SessionDataDirectory。不可將尚未有 catalog 的空白目錄當作原任務庫啟動，也不能直接降回不懂 SQLite 任務庫的舊 API；回退應停止服務後還原完整同一時間備份，並評估升級後的寫入是否已另行保存。

此版本的改動限管理／任務庫；場次 envelope 6、世界 schema 1、Admission v2／protocol 2、共享 Runtime 與 NGO wire protocol 14 不變。API／主控台需一起更新。Unity 工程、Quest APK、任務畫面還原、MR 校正與兩種頭盔仍須真正編譯及實機驗收，不以任務庫檢查代替。
