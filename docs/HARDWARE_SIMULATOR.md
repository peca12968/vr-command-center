# 硬體回饋離線模擬器

即時模擬與單房停止的操作方式見[硬體模擬閘道](HARDWARE.md#停止單房模擬閘道)。

模擬器 0.2.13 可在五房排演期間以逐房停止標記關閉指定房間。該房保留原確認，取消待確認批次，並在發布 `stopped` 前釋放本機鎖。`hardware-simulator-0.2.13-net10.zip` 為 239,542 bytes，SHA-256 `c1805466c73ab8bbbdfc6c9de5e4c971e1d287b064ea97e32225f562ad45d99c`，清單含 8 個檔案，已解壓核對。 [逐房操作](HARDWARE.md#停止五房排演中的指定房間)

模擬器 0.2.12 核對戰鬥串流、來源與執行階段序號。管理服務暫時無法使用時，閘道會在恢復後重新握手並使用當前游標。`hardware-simulator-0.2.12-net10.zip` 為 237,182 bytes，SHA-256 `b6749640058a96922da751e60d562cab3b768db84d2dce933caf04f9ee0b852e`，清單含 8 個檔案，已解壓核對。 [五房操作](HARDWARE.md#一次啟動與停止五房排演)

模擬器 0.2.11 在管理服務拒絕或回覆無效時，保留受影響房間的終止報告與模擬確認。已解壓驗證的 `hardware-simulator-0.2.11-verified-net10.zip` 為 224,896 bytes，SHA-256 `a71e547ed32d87aa8323fc7bc3e5a0ec78ee4cd6be1d351e87b95d0699d2eeeb`，清單含 8 個檔案。 [五房操作](HARDWARE.md#一次啟動與停止五房排演)

模擬器 0.2.10 可由一個程序核對、啟動與停止五房排演，並輸出逐房及全館結果。`hardware-simulator-0.2.10-net10.zip` 為 217,733 bytes，SHA-256 `79c18d5ff76d22851f34531df8add6459d668612eac2a10b4e58ffb88d80efc9`，清單含 8 個檔案。 [五房操作](HARDWARE.md#一次啟動與停止五房排演)

模擬器 0.2.9 可在電腦上彙整五房狀態。`hardware-simulator-0.2.9-final-net10.zip` 為 212,827 bytes，SHA-256 `bbe7f61f5144ed95abfd6511ab8c4fec2e845f4a17c400daf7dbd74c4990326a`，清單含 8 個檔案。 [五房狀態操作](HARDWARE.md#查看五房排演狀態)

模擬器 0.2.8 可搭配管理包 0.31.94，一次建立合併或獨立五房的即時設定。`hardware-simulator-0.2.8-net10.zip` 為 206,958 bytes，SHA-256 `63f7f8d607710bca12cdc538fa31001caf62232f0911872c2f0560273c5b5a54`，清單含 8 個檔案。 [五房綁定操作](HARDWARE.md#一次建立五房設備綁定)

模擬器 0.2.6 會在暫停時關閉閒置及待確認的連線，繼續後以新連線附掛。每房可指定專屬的模擬接收程序，並在握手和後續批次核對房號。 [暫停與繼續](HARDWARE.md#暫停與繼續模擬連線) · [五房資源互斥](HARDWARE.md#五房資源互斥)

模擬器 0.2.4 在同一台電腦、同一帳戶內避免同場同房重複啟動。原程序退出後，新閘道可從當前游標重新接上。 [互斥與重啟](HARDWARE.md#同房閘道的互斥與重新啟動)

模擬器 0.2.3 可用本房名冊建立及驗證座位綁定。離線模式沿用原事件重建與確認契約。 [座位綁定](HARDWARE.md#依現行名冊建立座位綁定)

模擬器 0.2.1 會在等待設備回覆期間檢查管理狀態，失效時關閉原模擬連線。`artifacts/hardware-packages/hardware-simulator-0.2.1-net10.zip` 為 160,744 bytes，SHA-256 `2f35bae86ef5a2e711419891417ce73f81dbbee3e835eb3572434f3c272bc7be`，含 8 個清單檔案。 [即時操作](HARDWARE.md#即時模擬閘道)

模擬器 0.2.0 同時提供本頁的離線重建和[即時房間排演](HARDWARE.md#即時模擬閘道)。打包 0.2.0 需另外以 `--live-evidence` 指定即時驗證目錄，離線與即時證據需來自同一編譯輸出。以下保留 0.1.0 的離線契約與歷史證據。

0.2.0 的 `artifacts/hardware-packages/hardware-simulator-0.2.0-net10.zip` 為 159,240 bytes，SHA-256 `be909c1422f9e857c6c19db810f44ae1353fcb2a34a317a973173169ec6a22b4`。清單含 8 個檔案，包括本機 `mock-device.py`。 [驗證紀錄](PROGRESS.md#2026-11-09-即時硬體模擬閘道)

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
python scripts/check-live-hardware-gateway.py --api-dll <同次Api.dll> --simulator-dll <同次HardwareSimulator.dll>
python scripts/package-hardware-simulator.py --evidence <離線run目錄> --live-evidence <即時run目錄> --stage-root <暫存根目錄> --output <新的ZIP>
python scripts/package-hardware-simulator.py --verify <解壓的VRCommand-HardwareSimulator目錄>
```

[功能574df36](https://github.com/peca12968/vr-command-center/commit/574df36d3cd4246dec0ad67885e8a544fa4f47c1)的[CI41349387031](https://github.com/peca12968/vr-command-center/actions/runs/41349387031)／job124976066366完整 **success**：Linux772核心／459 HTTP／47 world、6 pipe、38實際API／.NET離線模擬CLI、全部Python／素材及89 Node／296 Chromium通過。2 Windows限定skip不是WinForms、Unity／Editor、native遊戲、實體硬體或頭盔驗收。console49 artifact13100741395／ZIP **12,022,752 bytes／SHA256 e24b2ce787ccae8aabb70c3bc32268a064ce9a89cc9c51313c37da983dd51d47**，control13 artifact13100701380／ZIP **3,919／SHA256 a2569dfd539a5c1fef56e3b703f7e83e1bc1dc9aa1eca2046fcff0311239077a**，hardware26 artifact13099889416／ZIP **22,380／SHA256 e8ce6368326ccb6080a5a9e4f7280e7a44bbeacad894929a079d8ad24f508172**，已下載核對GitHub digest／逐檔hash；hardware檢查與原API cleanup讀回成功，artifact不含DB、journal或角色金鑰。完整decoded log SHA256 **53685b090bb76aeb81af85d2c7270473cb3867b64fd50692c046af9eefc0f5fa**保存。`hardware-ci-validation.json`明列1415＋49＝**1464 browser證據**，control13／hardware26各自另列，nativeUI7保持；不是新本機全browser或Unity執行。本機C75／F與原C27／四舊報告、9管理／5server ZIP及原Unity0.39／e0d／224雙平台、玩家ZIP APK保持。後續只有文件提交skip ci，測試來源精確574df36，完整11active。

本機原件與雜湊見[PROGRESS](PROGRESS.md)。完整11項仍active，廠商資料、真正輸入／輸出、設備認證、現場時間／斷線復原及實機停止方式依[HARDWARE](HARDWARE.md)另確認；不把此離線工具當作第3項整合完成。舊31／world371／Windows startup／F吞吐、PickerHost GUI阻擋、跨機／25位操作／MR及頭盔亦各自待驗。
