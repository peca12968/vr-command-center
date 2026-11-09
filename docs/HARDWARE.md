# 硬體介接準備

## 即時戰鬥回饋介面

Windows 管理包 0.31.27 提供 `GET /api/sessions/{sessionId}/rooms/{roomId}/hardware-feedback`。主控可選場次內任一房，房控憑證限本房。這個介面提供 `ShotFired` 與 `PlayerDamaged` 兩種已接受的遊戲事件，供房間轉接器開發與驗證。傳回事件、回報、玩家及當次入場識別，以及從零起算的席位、損傷量和接受時間。`combatOrigin` 保留原戰鬥來源。

初次連線及重連省略 `after`，服務回傳目前的 `throughSequence` 與空訊號清單。後續以 `?after=<throughSequence>` 續讀，每次使用回覆的 `throughSequence` 作下一次游標。以場次、房間、`streamId` 及 `runningSinceSequence` 確認來源，以 `eventId` 去重。

以下從管理服務所在電腦讀取房間 1。`$sessionId` 填入場次 UUID，`$headers` 使用該實例的主控或房間 1 Bearer 憑證。

```powershell
$feed = "http://127.0.0.1:5081/api/sessions/$sessionId/rooms/1/hardware-feedback"
$page = Invoke-RestMethod -Uri $feed -Headers $headers
# 場次有新動作後，使用本次回覆的序號讀取下一頁。
$page = Invoke-RestMethod -Uri "${feed}?after=$($page.throughSequence)" -Headers $headers
$page.signals
```

| 回覆 | 轉接器可採取的動作 |
| --- | --- |
| `resetReason: attached` | 從回覆序號建立新的讀取起點 |
| `resetReason: inactive` | 清空待處理訊號，使用回覆序號重新等待 |
| `resetReason: backlog` | 相差超過 256 筆時捨棄積壓，從回覆序號恢復 |
| `resetReason: null` | 逐筆核對本房設備綁定及 `admissionId`，再處理本頁訊號 |

只提供目前 Running 階段觀察到的事件，當次入場仍須存在於目前名冊。暫停及結束時回覆空訊號，繼續後會排除之前 Running 階段才觀察到的遲送回報。接受時間距服務檢查達 2 秒的事件會捨棄。`acceptedAtUtc` 是管理服務事件的時間，實際動作時間和設備端期限需由廠商轉接器定義。轉接器發現失聯、錯誤或來源切換時須清空自己的佇列，依設備文件確認安全停止。損傷量保留遊戲值，設備動作及強度映射留待廠商規格。

## 現況

硬體由外部公司負責，目前尚未收到技術資料或 SDK；不對未知設備發送命令。已有[硬體回饋離線模擬器](HARDWARE_SIMULATOR.md)0.1.0，以正式事件重建規則驗證room／player／admission綁定、模擬佇列、重送、到期與ACK；不連實體設備，不定義廠商wire，也不提供硬體輸入、強度或實體停止保證。取得文件後再設計廠商轉接器，不能以離線模擬宣稱實機整合完成。

## 廠商需提供

1. 設備清單、型號、韌體、每房數量，以及設備／房間／玩家如何對應。
2. 傳輸方式：USB、Serial、TCP、UDP、BLE、HTTP、MQTT 或廠商 SDK；作業系統與架構支援。
3. 封包格式、單位、座標系、時間戳、校驗碼、命令編號及版本相容規則。
4. 輸入事件：觸發、換彈、感測、中彈、定位、按鈕等；事件頻率、序號及重送行為。
5. 輸出命令：回饋、燈光、震動等；範圍限制、確認回覆、逾時、取消與停止方式。
6. 配對、授權、裝置身分與憑證管理；斷線重連、重複封包及錯誤碼範例。
7. 測試工具、模擬器、實機測試設備、SDK 授權與可供開發人員使用的文件。

## 預定閘道責任

每房使用獨立設備閘道，將廠商格式轉換成版本化事件。事件至少包含 `eventId`、`deviceId`、`roomId`、`playerId`、`kind`、`sequence`、`occurredAtUtc` 及 `payload`；實際欄位以協議確認後固定。閘道處理心跳、事件去重、連線狀態、逾時及命令確認，遊戲伺服器負責決定事件對遊戲狀態的影響。

斷線或場次結束時，輸出回到設備文件定義的停止狀態；不能假設軟體停止可取代實體設備控制。模擬器須包含重送、亂序、斷線、過期命令與設備換綁場景。實機驗收應記錄封包、時間與對應遊戲事件，避免僅以 UI 顯示成功判定整合完成。
