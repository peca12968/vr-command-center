# 最終任務報表 CSV

API／控制台 **0.27.0** 新增 `GET /api/sessions/{id}/report.csv`。在「場館操作」選取場次，勾選「包含已結束紀錄」，於任務統計下按「下載最終報表 CSV」。進行中、暫停中及等待戰鬥補送封存的場次不提供最終下載；後端也獨立檢查。

檔案為 UTF-8 BOM、逗號分隔、CRLF 換行，所有欄位加雙引號，內部雙引號重複。固定名稱 `vr-command-report-v1-{sessionId}.csv`，可供試算表或標準 CSV reader 讀取。HTTP 使用 `text/csv; charset=utf-8`、attachment、`Cache-Control: no-store`。

## 場次與戰績同步

控制台 0.31.73 以 `GET /api/sessions/{id}/overview` 一次讀取場次、玩家戰績和最近最多 20 筆事件。場次的序號、統計的 `throughSequence` 及最後一筆事件序號對齊。戰鬥串流等待補送或確認封存的狀態也取自這次讀取。讀取權限與原場次相同，回應使用 `Cache-Control: no-store`。

## 五房分房匯出

控制台 0.31.8 在五房連線場次的任務統計中提供報表範圍。主控預設下載全場，也可選定其中一房。房控畫面固定為自己的房間。下載期間會鎖定範圍，切換場次或登出會取消該次下載。

分房端點為 `GET /api/sessions/{id}/rooms/{roomId}/report.csv`。主控可選場次內的任一房，房控只能在此端點指定自己的房間，跨房回應 403。主控指定場次外的房間時回應 400。兩個端點使用相同的最終戰鬥封存條件。全場端點沿用原場次讀取權限及 CSV 欄位。

分房檔名為 `vr-command-report-v1-{sessionId}-room-NN.csv`。原 `roomIds` 記錄整場房間組成，新增末欄 `reportRoomId` 標示本檔的房號。只有該房的玩家戰績會列入，包括已離場玩家。若該房無玩家戰績，輸出一列帶有房號的場次資料。場次 ID、事件序號及戰鬥封存序號沿用同一份全場資料。 [Windows 三包整合驗證](WINDOWS_SERVER_PACKAGE.md#三個可攜包整合驗證)

### 一次下載五房戰績

控制台 0.31.18 的「下載五房戰績 ZIP」供全館主控使用。五房連線場次結束且可下載最終戰鬥 CSV 後，一次下載全場與五份分房 CSV。ZIP 涵蓋全部房間，個別 CSV 的範圍選單可繼續用於下載單一檔案。

端點為 `GET /api/sessions/{id}/reports.zip`，檔名為 `vr-command-reports-v1-{sessionId}.zip`，使用 `application/zip` 與 `Cache-Control: no-store`。服務先擷取一份最終報表，再產出全場及分房檔案。六份 CSV 的內容與逐一下載相同，包含空房與已離場玩家的既有表示。已結束且沒有戰鬥串流的歷史場次沿用原報表條件。此下載使用戰鬥封存條件，場館驗收 ZIP 則另行核對世界封存、端點與名冊。

三包驗證可加上 `--check-room-reports --check-room-combat`。先在五個獨立房間、再在五房連線，以五名原生模擬玩家及五名敵軍配置每房。所有玩家連線及原 Begin 生效後，使用正常管理命令開啟攻擊。等每位原玩家受傷後關閉攻擊，確認遊戲來源已套用，再執行 End。

驗證會比對每筆原生敵軍射線、同房受傷事件、逐格統計和最終戰鬥封存序號。最後再核對個人戰績、伺服器確認及匯出 CSV。此模式檢查敵軍造成的耗損與中彈，玩家保持原生桌面合成姿態且未操作武器。

玩家開火可另用 [五房射擊驗證](DESKTOP_EXERCISE.md#五房射擊與戰績驗證)，逐筆核對彈藥、命中、擊殺與命中率，並比對連線場次的六份 CSV。

## 從戰績開啟個人回放

控制台 0.31.89 在「任務統計」提供「下載個人戰績 CSV」。原場次結束並完成戰鬥封存後，選擇「戰後檢討玩家」再下載。檔案保留全場 CSV 中該玩家的原始一列及封存序號，可用於玩家未收到遊戲內結果時的人工核對。世界回放封存後才可開啟個人回放。

端點為 `GET /api/sessions/{id}/players/{playerId}/report.csv`。主控可查原場次的任何玩家，房控只可匯出原戰績列屬於本房的玩家。已離場但仍在原統計中的玩家也可選取。找不到玩家或玩家屬於別房時，此端點回應 404。檔名包含原場次與玩家 UUID，下載回應使用 `Cache-Control: no-store`。操作者變更所選玩家、切換頁面或登出時，會取消仍在等待的個人下載。

主控也可在「全館收尾」的原批次選擇「查看席位」，直接下載該席的個人 CSV。端點為 `GET /api/venue/closure/{id}/rooms/{roomId}/seats/{seat}/report.csv`，按原結束名冊的房號與席號查找，須完成戰鬥與世界封存。 [全館席位回條](SESSION_CLOSURE.md#從全館收尾查看席位)

管理包 0.31.137 的全館席位明細提供「個人回放」。可從歷史批次直接開啟該席原房間的錄製及事件篩選。 [全館席位操作](SESSION_CLOSURE.md#從全館收尾查看席位)

控制台 0.31.44 在「任務統計」提供「戰後檢討玩家」。選擇已結束的原場次，等戰鬥統計與世界回放都確認封存，再選玩家並按「開啟個人事件回放」。名單取自最終統計，因此可選已離場的玩家。同名玩家可用房號和 ID 短碼區分。

控制台 0.31.56 起，五房合併場次的「統計與檢討範圍」同時控制戰績表、檢討名單和最終 CSV。主控可選全場或單房，房間控制台在此區顯示本房。戰績表顯示各玩家房號，封存前可先分房查看目前統計。重新整理會保留同場選擇，切換場次或登出會重設。五房 ZIP 仍包含全部房間。

控制台核對原場次、錄製來源與兩個封存序號，停在原錄製最後一格，再自動搜尋該玩家的第一頁事件。從分房統計開啟時，回放從該房俯視並在該房搜尋。全場統計則搜尋玩家在整個錄製中的事件。點選結果後，事件及統計隨保存格更新。按「顯示所有玩家」可清除個人篩選。 [回放操作](WORLD_RECORDING.md#依房間與種類搜尋戰鬥事件)

控制台 0.31.51 可在個人回放按「上一筆事件」或「下一筆事件」直接跳轉，沿用原玩家及目前篩選。 [事件跳轉](WORLD_RECORDING.md#依房間與種類搜尋戰鬥事件)

控制台 0.31.88 在原戰績有中彈紀錄時提供「跳到最近中彈」。選定玩家後按下按鈕，控制台先確認同一場次的戰鬥及世界封存，再從原錄製尾端往回找該玩家的 `PlayerDamaged` 畫格。分房檢討沿用原房間範圍。成功後暫停在該格，事件表保留玩家和受傷篩選，可用上一筆或下一筆繼續檢討。找不到符合的保存事件時，保留原封存尾端並顯示搜尋結果。

停在中彈或其他符合篩選的戰鬥事件時，可用「標記事件前後各 5 秒」設定要重看的原保存片段。 [片段操作](WORLD_RECORDING.md#重看指定片段)

### 下載指定片段的戰績

管理台 0.31.126 可在暫停回放後標記起訖、讀取片段戰績，再按「下載片段戰績 CSV」。檔案沿用目前核對的房間與個人範圍、原錄製識別及兩端畫格。每次最多 300 格，包含起訖兩格。房控只能下載本房；主控可下載全場或所選房間。變更範圍後需重新讀取。

「命中」包含該片段內保存的所有命中，「計入命中率」則只包含本段發射且本段確認命中的射擊。CSV 對應 `shotsHit` 與 `matchedShots`。沒有發射時 `accuracyPercent` 留空。沒有玩家戰鬥事件時，仍可下載一列 `rowType=Clip` 的範圍資料。匯出使用 UTF-8 BOM、CRLF 與原報表的試算表文字防護。

`GET /api/sessions/{id}/world/clip-statistics.csv` 必須帶 `streamId`、`fromFrame`、`throughFrame`，可選 `roomId` 和 `playerId`。下載以原錄製的已保存範圍計算，回應含 `Cache-Control: no-store`。整場結算可使用原最終戰績報表。

## 下載全館結束批次

Windows 管理包 0.31.37 起，主控可在「最近一次全館收尾」按「下載本批戰績 ZIP」。批次內所有場次的戰鬥報表可匯出後，按鈕才會開放。等待時會顯示房號。未連接戰鬥串流的已結束場次可按既有規則匯出，空場保留場次列。

獨立場次每房一份 CSV。五房合併場次包含全場與五份分房 CSV。每份 CSV 與原端點逐一下載的內容相同。ZIP 另含 `manifest.json`，記錄批次 ID、原場次 ID、房號、結束命令序號、最終統計序號與 CSV 檔名。世界回放有獨立封存流程。

`GET /api/venue/closure/{batchId}/reports.zip` 限主控，回傳 `vr-command-venue-reports-v1-{batchId}.zip` 與 `Cache-Control: no-store`。若任一場的戰鬥報表尚未完成，回傳 `409`、`venue-reports-not-ready` 與待封存房號。即使房間重用或已有新批次，原批次網址仍指向原場次和報表。

### 在全館收尾比較分房戰績

Windows 管理包 0.31.81 在「全館收尾」顯示所選批次的分房戰績與本批合計。所有原場次的最終戰鬥報表可讀後才顯示。分房表含玩家數、耗彈、命中、擊殺、中彈、耗損與命中率。未參與該批的房間不列入，原批次中的空房會保留零值列。命中率以該列總命中除以總耗彈，合併場的每份玩家戰績只計入原房一次。

主控可在批次清單選擇舊批次，比較當時的最終戰績。管理 API 在 `GET /api/venue/closure` 或 `GET /api/venue/closure/{batchId}` 加上 `includeScores=true` 時，隨原批次提供已就緒的 `scores`。它沿用戰鬥報表的權限與封存條件。世界回放封存狀態在原區塊獨立顯示。

## 最終性與權限

SessionManager 在同一把鎖內檢查身分／房間、Ended 與戰鬥封存，再擷取場次及 ledger。已綁 combat stream 必須接受精確 seal，只有 End 不足以匯出；尾端補送完成但尚未 seal 仍回 409。未綁 stream 的歷史場次 End 後不能接受新戰鬥，故可匯出。報表不新增事件、不更動歷史，也不寫入伺服器的匯出檔案。

Master 可讀全部；RoomController 依既有場次讀取政策，只能匯出包含其房間的場次。Linked 的房控可讀該場全部玩家，與現有 statistics／觀戰權限一致。GameServer 憑證回 403；未驗證回 401；不存在回 404。HTTP 必須明確傳入認證的 OperatorIdentity，不能退回預設 Internal。

這是**最終戰鬥 ledger 報表**，不是世界錄影封存證書。它不宣稱 worlds.db 已 complete、每個世界繪製幀已驗證、頭盔在線或 25 台效能通過。世界回放有自己的精確 seal 與 witness 檢查，仍依 WORLD_RECORDING／TELEMETRY 流程驗收。GameServer 是宣告的來源類型，不代表頭盔或實體硬體已驗收。

## reportVersion 1 欄位

每位 ledger 玩家一列，排序沿用 roomId、playerId，包含已離場玩家；不依目前名冊篩選。每列重複同一份場次 metadata，沒有可被誤加總的總計列。若從未加入玩家，輸出一列 `rowType=Session`，玩家欄位全空。已有玩家但無戰鬥則為 Player 列及零統計，不冒造射擊事件。

| 欄位 | 意義 |
|---|---|
| reportVersion／rowType | 固定 1；Player 或空場的 Session |
| sessionId／missionId／missionName | 原場次及當時選用的不可變任務 ID／名稱，不讀任務庫目前 head |
| sessionMode／roomIds | Independent／Linked；房號以 `\|` 分隔 |
| createdAtUtc／startedAtUtc／endedAtUtc | ISO 8601 UTC；未 Begin 的 startedAtUtc 留空 |
| plannedDurationSeconds | 任務定義秒數，不冒充扣除 Pause 後的實際遊玩時間 |
| throughSequence | 同一次最終管理／戰鬥事件快照的序號 |
| origin | ledger 的 Simulation／GameServer；零事件但有綁 stream 時保留該 stream 宣告；沒有事件也沒有 stream 時為 None |
| streamId／finalStreamSequence | 已封存 combat stream ID／接受的最終序號；未綁則空，合法空 stream 為 0 |
| playerId／playerName／playerRoomId | 與既有統計 ledger 相同的玩家 ID／姓名／房號 |
| ammoUsed／shotsHit／kills | 接受的玩家發射、命中射擊及擊殺數，不含敵軍開火或換彈 |
| damageTaken／hitsReceived／health | 已確認健康損失、傷害事件數及剩餘健康，沿用既有 overkill 截斷規則 |
| accuracyPercent | shotsHit／ammoUsed ×100，未射擊為 0，沿用兩位小數；66.67 表示 66.67%，不是 0.6667 |

數字採 invariant culture。為避免試算表執行文字公式，任務／玩家名稱若在前導空白後以 `= + - @` 開始，或包含控制字元，CSV 加前導單引號；其後保留原文字，逗號／引號／內嵌換行仍按 CSV 引用。這是匯出呈現，原資料、JSON statistics 及回放姓名不改。程式讀者如需原姓名，應使用已有的授權 statistics JSON，不自行把受保護欄位當公式執行。

同一場已完成報表重複下載及 SQLite 重啟後位元組一致，沒有每次變動的匯出時間。throughSequence 與 stream 最終序號可供追溯，但不是簽章或防竄改證書。

## 瀏覽器下載生命週期

下載以 Bearer fetch 進行，憑證只在頁面記憶體，不寫網址、CSV 或瀏覽器儲存區。只將正確 CSV MIME 的成功回應轉為 Blob。檔名使用場次 UUID，分房檔再加入房號。產生的 ObjectURL 於點擊後釋放。

下載中抑制重複點擊，仍可切換場次或登出；selection generation 與登入 epoch 阻擋晚回應，切離後再選回同場也不能觸發舊下載。重設會中止 fetch，讀 header／blob 後再次核對身分與場次。一般更新不清掉下載結果／錯誤；只有可用狀態改變才換回提示。409／錯誤 MIME 不下載並可重試；當前 401 登出，過期登入的 401 不影響新登入。

切換場次在等待既有背景更新前，就清掉上一場統計、隱藏舊場面板並停用下載；selection epoch 讓等待期間的快速多次切換只接受最後一次。MIME 以完整 media type 比對，不接受 text/csv-fake 之類相似前綴。

本功能只新增 API／UI 唯讀匯出，不改 Unity 0.28／code32／NGO26、資源 pin、rules0.8.0、envelope6、world schema1 或現存 header／checksum。Unity source fingerprint 與已成功的 Windows／Quest binary 保持；不把上一輪 102 EditMode／APK 當成本輪重新執行。驗證結果與原生錄製整合見 [PROGRESS.md](PROGRESS.md)。
