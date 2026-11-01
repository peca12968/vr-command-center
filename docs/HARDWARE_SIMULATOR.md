# 硬體回饋離線模擬器

工具 **0.1.0** 提供設備回饋的離線測試台，先驗證事件、房間、玩家入場與模擬連線的對應，等待廠商文件後再設計真正轉接器。它不連USB、Serial、TCP或BLE、不使用廠商SDK、不發實體命令；不是廠商封包格式，也沒有輸入按鈕、追蹤、震動力道或實體停止的整合證據。

主包 `artifacts/hardware-packages/hardware-simulator-0.1.0-v2-net10.zip`，**122,352 bytes／SHA256 `72e73214c03948ac312cac52c246338ae061e498fb7f8aa9f5d4e0bd62d7412b`**，7 manifest檔案／ZIP8含manifest。只含自己專案的5個DLL／deps／runtimeconfig檔、合成example及說明，需.NET 10 runtime，沒有隨包帶runtime、apphost、金鑰、DB或journal。前包122,332／SHAff7b1c68...及原解壓驗證保留；v2補上權限／缺玩家資料的受控拒絕，不能拿前版當最終版。

```powershell
dotnet VrCommand.HardwareSimulator.dll --input example.json --output <新的包外report.json>
```

輸入最大8MiB、輸出最大64MiB，必須使用不同JSON路徑，既有輸出不覆蓋。輸入／輸出錯誤、格式及生產規則拒絕一律exit1且只列例外型別，不回顯資料；成功exit0。complete僅表示離線腳本處理完成，**simulatedHardwareOnly=true／physicalDeliveryConfirmed=false**。包manifest是檔案完整性清單，不是簽章；任意輸入檔符合重建規則，也不能證明它曾被某台API接受。不要把操作憑證放進輸入。

## 輸入與來源

`HardwareSimulationInput` version1含 `events`、`bindings`、`steps`。這是測試台自己的檔案契約，沒有新增API路由、廠商協議或遊戲wire。事件必須是單場完整schema6／7歷史，最多4096筆；以原 `SessionManager`／入場、角色、CombatLedger及stream seal規則重建，要求Ended且戰鬥精確封存。這不要求或證明世界錄影封存，也不讀資料庫。

每個binding含deviceId、sessionId、streamId、roomId、playerId、admissionId；設備ID是測試台內的UUID，不能當成實體序號。最多128筆綁定，來源必須確曾在本歷史中入場。回饋只投影 `StreamCombatRecorded` 的 `ShotFired`／`PlayerDamaged`，保留原event ID／全域序號、stream sequence、observed sequence、report ID、combat origin及damage，沒有從傷害推算設備輸出強度。

玩家／房間／admission取自原回報的 **ObservedSequence**，不是收到事件時的當前名冊。遲到但被正式接受的End後／離場後回報仍使用原Running觀察；同玩家ID的舊入場或別房綁定不可消費新回饋。`combatOrigin`描述原戰鬥來源，與「硬體端永遠模擬」是不同欄位；本輪來源全部Simulation，不提供頭盔或GameServer實機證據。

## 虛擬設備腳本

每個step含遞增或相同的atMilliseconds及action，最多4096步、0至600000虛擬毫秒。時間只由後續step推進，**不是現場時鐘、來源年齡或RTT**；2秒期限是測試台自己的佇列生命期，不改遊戲0.5／1.5秒政策。

| action | 參數與行為 |
|---|---|
| Connect | deviceId／bindingIndex（零起算）；建立新的模擬connection號，取消舊佇列與in-flight，不清除消費序號 |
| Dispatch | deviceId／原eventId；只把相符的原admission訊號排入該設備，拒絕重送／倒序，其他事件為NotFeedback |
| Receive | 取FIFO下一筆成為唯一in-flight，回傳SimulatedReceived；已有in-flight時不重送 |
| Acknowledge | deviceId／connection／delivery；須精確相符且尚未到期，才回SimulatedAcknowledged；錯誤或遲到ACK不清掉其他項目 |
| Disconnect | 取消該設備待送與in-flight，停止本次模擬綁定 |
| StopAll | 不含deviceId；取消所有模擬設備的待送與in-flight |

每設備32項，包含in-flight；滿載明確QueueFull、拒絕新項，不丟掉原佇列，也不自動重試。Reconnect／換綁不自動重播已排入但取消的效果；單次腳本內保留全域來源序號下界。到期先記Expired或TimedOut，再判斷當步ACK，因此恰好2000ms的ACK不被接受。所有腳本最後一律Finalized並取消殘留項目；取消、停止、過期都不是ACK，更不是實體設備已停止的保證。新一輪離線Run重設狀態，沒有跨程序的實體去重或復原能力。

## 已驗證範圍

新增34項Core檢查、完整 **772核心** 通過；涵蓋原admission／跨房、離場及End後遲到事件、換綁／重連／重送／倒序、in-flight容量、錯設備／錯connection／錯delivery ACK、1999／2000ms期限、停止、缺seal／重複歷史及輸入上限。

真正隔離API與.NET `ArenaSession`／`TelemetryOutbox`先產生戰鬥，再由原relay補送及seal，最終CLI **38項**通過。原12筆歷史、2發2中1殺、損耗20／健康80、3個邏輯回饋（2 ShotFired／1 PlayerDamaged）與所有原識別逐欄相符。這是.NET Simulation，沒有Unity遊戲程序、頭盔或實體設備；不是25人負載或世界回放新證據。工具前後原API事件／統計相同、active0；原API經私有pipe正常exit0後才各一次raw snapshot，保存SQLite不開。

第一版對權限不符但結構可解析的歷史已正確拒絕寫報告，卻發生未處理AccessDeniedException（Windows exit3762504530）。保留同一原輸入、stdout與無輸出反例；v2的同一位元輸入exit1／只列型別／無輸出。另驗KeyNotFoundException也是受控拒絕。此修正是CLI錯誤處理，沒有放寬角色或歷史規則。

v2已真正解壓、執行example，報告與原CLI的結果逐位元相同，包內檔案未改。初24／33／34／36及最終38五場、初包與拒絕反例全保存，不混稱同一輪。Windows459 HTTP／47 world回歸通過，不當舊startup根因修復。本輪無新本機全瀏覽器、Editor、Unity、APK、native遊戲或WinForms操作；原UI0.31.2、API0.31.0與Unity0.39／224／e0d同源雙平台保持。

開發驗證命令：

```powershell
python scripts/check-hardware-simulator.py --api-dll <同次Api.dll> --simulator-dll <同次HardwareSimulator.dll> --relay-dll <同次TelemetryRelay.dll> --runtime-root <新的runtime根目錄>
python scripts/package-hardware-simulator.py --evidence <完成的run目錄> --stage-root <暫存根目錄> --output <新的ZIP>
python scripts/package-hardware-simulator.py --verify <解壓的VRCommand-HardwareSimulator目錄>
```

CI及本機原件與雜湊見[PROGRESS](PROGRESS.md)。完整11項仍active，廠商資料、真正輸入／輸出、設備認證、現場時間／斷線復原及實機停止方式依[HARDWARE](HARDWARE.md)另確認；不把此離線工具當作第3項整合完成。舊31／world371／Windows startup／F吞吐、PickerHost GUI阻擋、跨機／25位操作／MR及頭盔亦各自待驗。
