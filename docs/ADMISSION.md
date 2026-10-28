# 每次入場、票券與連線 v0.14

玩家 ID 是邏輯玩家，每次加入則有獨立 admissionId。離場後即使以相同 ID、房間及席位重新加入，先前票券仍保持撤銷；舊移除操作也不能套用到新入場。API、持久資料、共用 ArenaSession 與 Unity 接入來源碼使用同一識別。

本輪已驗證 .NET 核心、SQLite 重啟、真實 HTTP、原始世界發布／回放與瀏覽器。**Unity 接入尚未編譯／運行**；Prepare 仍退出 198，沒有 APK、Quest／VIVE 或 25 台效能結果。這不是裝置身分認證或完整的伺服器崩潰恢復。

## 身分與持久化

- PlayerJoined 的 EventId 就是 admissionId，與玩家及席位一起在 schema 6 payload 保存。新事件的 admissionId 不可省略或換成其他值。
- 同一個已接受的加入 requestId 只確認原操作，回覆目前快照；不產生新入場或重新加入已離場的人。新的加入操作才產生新的 EventId／admissionId。
- schema 1–5 沒有入場欄位，重建時從原始加入事件 EventId 推導，重開保持一致，不改寫舊事件。場次序號、玩家 ID、席位及舊統計不因升級改變。
- PlayerLeft schema 6 保存實際 admissionId 與選用 expectedAdmissionId。後者是原始請求內容；同一 requestId 改成另一個 fence 回 409。
- SQLite schema 仍 1，新 session event envelope 為 6，讀取 1–5。寫入後不能降回不支援 schema 6 的 API，須先備份完整 data 與來源檔。

## API 契約

全部端點保留原 Bearer 身分及房間檢查；admissionId 是識別碼，不能代替憑證。主控台／房間控制台只能替有權管理的當前玩家配票或移除；GameServer 不能代替控制台操作名冊。

| 動作 | 必要資訊 | 行為 |
|---|---|---|
| POST `/api/sessions/{id}/players` | 原 playerId／name／roomId／headset，選用 Idempotency-Key | 回應玩家包含 admissionId |
| POST `.../players/{playerId}/join-ticket` | `If-Match-Admission: 當前 admissionId` | 只替該次入場簽發 v2 票券；缺欄位 400，已換入場 409 |
| DELETE `.../players/{playerId}` | `If-Match-Admission`，建議固定 Idempotency-Key | 新操作必須與當前入場相符；失敗不追加事件 |
| POST `/api/player-tickets/validate` | GameServer；sessionId、ticket、protocolVersion:2 | 驗簽／期限及原子名冊比對，回傳入場／席位／throughSequence／expiresAtUtc |

If-Match-Admission 必須恰好一個非零 D-format UUID。重試移除時固定原 header、path、requestId；不要重新查當前入場後更換舊重試的 fence。若舊移除已接受，歷史確認即使在該玩家再次入場或場次結束後仍回 204，不移除新成員；改 fence 回 409。若原請求從未接受，舊 fence 在重新入場後回 409。v0.13 或更舊已接受、沒有 fence 的 requestId 可原樣確認；**新的 HTTP 移除不可省略 fence**。

API 範例（已有控制台憑證，勿把整份密鑰放進頭盔）：

```powershell
$session = Invoke-RestMethod "$baseUrl/api/sessions/$sessionId" -Headers $headers
$player = $session.players | Where-Object id -eq $playerId
$admissionHeaders = $headers.Clone()
$admissionHeaders['If-Match-Admission'] = $player.admissionId
$ticket = Invoke-RestMethod -Method Post "$baseUrl/api/sessions/$sessionId/players/$playerId/join-ticket" -Headers $admissionHeaders
```

頭盔連線檔仍只有 role／address／port／joinTicket，不增加操作員或 GameServer 憑證。票券是 opaque invitation，不是加密資料。

## 票券 v2

字串 `v2.base64url(payload).base64url(HMAC-SHA256)`，payload 75 bytes：版本標記 2（1 byte）、session 16、player 16、admission 16、room 1、seat 1、Unix expiry big-endian 8、random nonce 16。GUID 編碼以 .NET TryWriteBytes／Guid(span) 成對讀寫。期限維持五分鐘、比較 HMAC 使用固定時間；簽章 key 的保存位置不變，不因升級自動輪替。

v1 票券不含入場識別，升級後全部拒絕，即使簽章及期限原先有效。須由控制台重發；不靠等待舊券自然過期解決撤銷問題。v2 也不是一次性券：同一入場內可在有效期重新驗證以重連，但 ArenaSession 只允許一個目前連線綁定該玩家。票券期限限制入場驗證，不是遊戲執行五分鐘後強制斷線。

API 驗簽後以同一鎖內的當前名冊比對 session／player／admission／room／seat 及非 Ended，throughSequence 指向該次驗證的管理觀察。離場、重新入場或結束都不能透過舊 claims 復活成員。GameServer protocolVersion 不為 2 時拒絕，避免舊發送器忽略新身分欄位。

## 共用核心與 Unity 接入

ManagementSnapshot.players 需要非零、互不重複的 admissionId。Connect 必須提交經驗票的 admissionId，不以玩家 ID／席位推測。Preparing 的輪詢即使跳過完整「離場→同 ID 同席位重入」也能察覺 epoch 改變，重建尚未開局的世界並撤銷舊 binding；舊姿態／武器不能操作新身體。Running 不允許換入場或補造新身體。一般裝置重連仍綁同次入場，保留既有健康與彈藥。

Unity 原始碼會先驗 protocol 2 票券，再取得至少 throughSequence 的管理快照、比對完整 admission／room／seat 與期限，才綁定 NGO 連線。驗證期間已離開 pending clients 的請求不能保留 ghost binding。名冊更新後即移除過時 admission 的內部綁定並要求斷線；Host 自己被撤銷則關閉 Host。

因多個驗票可能同時完成，管理請求會共用序列化／合併的 coroutine，避免舊 HTTP 回應倒退或讓健康快照變為無效。必要時再取一次快照，connection approval buffer 設 20 秒。入場／撤銷不是每個姿態都走 REST；姿態／武器仍走 NGO。現有連線的撤銷依下一次管理觀察生效，正常輪詢目標 0.5 秒，管理資料超過 1.5 秒則暫停戰鬥；**尚無實機時間上限量測或零延遲撤銷承諾**。

生成器 bundle 0.14／Android code 14／NGO ProtocolVersion 14。新增三個待執行 EditMode 契約測試，總共 15，建置腳本要求至少 15 項通過；沒有 Unity 結果。已依固定 NGO 2.7 原始碼確認 server client IDs 遞增，既有不同連線的延遲斷線不移除新 binding；完整裝置重連仍須實測。

## 升級與驗收

停止活動場次及所有遊戲伺服器，備份 data／來源，更新 API、主控台及 GameServer／頭盔工程，再重發票券；不要混用忽略 admissionId 的舊來源或保留舊 v1 邀請。管理端可先完成 Native／API 檢查，但不能把這些當成 NGO、APK 或 Quest 驗證。

另有錄製統計相容修正：Preparing 重入若改了顯示名稱／房間，錄製會依觀察到的名冊更新統計 metadata，保持與最終 ledger 一致。仍不允許 Running 加入／重設健康的 respawn。

接續實機需驗證兩台 Quest 的同券競爭、斷線重連、移除／同 ID 重入、延遲回應／撤銷、管理中斷、Host 撤銷、15 項 EditMode 及舊版本連線拒絕；再測五房／25 台與完整任務。硬體、MR、VIVE 與原始 11 項需求仍保留。
