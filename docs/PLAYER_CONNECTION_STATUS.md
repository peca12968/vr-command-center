# Windows玩家的入場狀態

啟動器 1.2 在開始遊戲前另顯示連線檔中的房間、席位及依本機時間估算的效期。遊戲開始後，入場狀態仍由下面的原生日誌決定。 [連線檔席位與效期](PLAYER_CONFIG_REVIEW.md#連線檔席位與效期)

新版`Launch-Player.exe`區分「程式啟動」與遊戲回報的入場。一般選檔操作與四欄玩家連線檔保持；無需更改Unity、伺服器、票券、世界格式或規則，也不會代替控制台的[玩家參戰快照](PLAYER_READINESS.md)。目前只有同機背景原生及真正Windows類別檢查，GUI操作與跨機驗收仍見[PROGRESS](PROGRESS.md)。

| 狀態 | 啟動器依據與提示 |
|---|---|
| Waiting | 程式已啟動，等待遊戲回報；不表示伺服器可達或入場成功 |
| Connected | 自己這次遊戲的`VR_CLIENT_CONNECTED`；顯示「遊戲已回報入場」，不等於目前姿態有效或完整設備就緒 |
| Rejected | 遊戲明確回報入場拒絕；向控制人員重取自己的連線檔，不由啟動器猜測票券原因 |
| Disconnected | 遊戲回報斷線；可在遊戲內使用原Reconnect流程讀取更新票券 |
| Unconfirmed | 等待至少30秒仍無入場確認；核對IPv4、UDP埠與版本，不宣稱防火牆、網路或伺服器一定故障 |
| Final | 遊戲回報最終戰績；正常結束斷線不覆蓋它，新一次Connected才重新開始狀態 |

關閉啟動器仍不終止遊戲或End任務。它不配票、不讀管理API、不送網路探測、不重試或修改遊戲狀態，也不把ping／TCP測試當UDP遊戲連線。記錄不可讀時，已連線提示會明示僅是先前回報，請看遊戲視窗。

一般GUI啟動會將原Unity日誌寫到自己新建的`%LOCALAPPDATA%/VrCommand/PlayerRuns/<識別>/player.log`，避免讀其他程序或上一次的全域Player.log。保留原日誌供本人查閱，不自動刪除；裡面可能有自己的入場識別與戰績，請個別保管。沒有新增姿態／GPU／PCM探針，沒有讀取其他程序、記憶體或OS畫面。GUI關閉後不再監看，遊戲仍可持續寫自己的日誌。

監看每次最多讀64 KiB、UTF8 decoder跨讀取保留半字元，完整換行才辨認marker，單列最多4096字元、過長列整列忽略；狀態歷史最多64筆，超界保留最早資料並標不完整。日誌倒退或積壓超過2 MiB停止解讀，不從錯位資料重新推定連線。未知文字、actor ID、票券及最終結果payload不顯示或複製到狀態報告。

CLI原`--launch --headless --wait --log --report`維持。若要驗證相同監看邏輯，可額外指定`--status-report <全新絕對路徑>`，須同時提供waited launch及自己的新`--log`；輸出不能在玩家包內、不能覆寫舊檔，也不能與輸入／其他輸出以Windows大小寫別名重疊。普通GUI不寫此報告。

狀態JSON只有version、processId、exited、state、logAvailable、complete與有界transitions，只有改變才寫入。**complete表示此狀態快照未超界；exited獨立表示自己的遊戲已退出，兩者都不表示任務／戰績／網路驗收成功。**狀態來自自己遊戲的回報，不是獨立驗票器或伺服器簽章證據；正式戰績仍須與原admission、七統計及精確雙seal核對。

開發驗證：

```powershell
python scripts/check-player-connection-status.py
python scripts/check-player-package.py '<解壓目錄>/VRCommand-Player'
node tests/browser/check-external-native.cjs '<本次隔離external ready.json>' '<解壓目錄>/VRCommand-Player' --launcher-status
```

第一個工具真正編譯同一監看類別並以有界檔案／marker反例測試，不把fixture當原生入場。第三個工具只接受自己新建的loopback／Simulation場：兩個真正玩家由控制台下載檔正常入場，另以錯票券驗拒絕、自己不回應的UDP端點驗未確認；不讀UDP payload、不當物理網路故障根因。驗證各玩家最終狀態、身份／票券不洩漏、原戰績與雙seal一致，停止四個自有玩家／啟動器後才保存成功。
