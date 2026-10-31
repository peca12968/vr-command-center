# 五個獨立世界的15分鐘PC任務

`scripts/check-desktop-independent-long.py`在自己的新API與runtime啟動五個真正Windows server，每房預設五個真正client。五份任務有不同天氣／日夜、場景物件、session／world stream及UDP port，各自執行900秒活動時間並於tick18000自動結束。玩家全為靜止、無圖形Simulation；這不是25位持續操作、25台裝置、跨機／Wi-Fi或Quest／VIVE容量驗收。

先依[DESKTOP](DESKTOP.md)完成目前同源API及Windows播放器，再執行：

```powershell
$runtimeRoot = Join-Path $env:LOCALAPPDATA 'VrCommand/SimulationRuns'
python scripts/check-desktop-independent-long.py --api-dll '<目前同版API.dll>' --runtime-root $runtimeRoot --players-per-room 5
```

每房一至五人可由`--players-per-room`指定；不能把較少人數的結果稱為25程序通過。本輪的實際人數、結果與限制見[PROGRESS](PROGRESS.md)。工具先核對Windows build receipt與目前來源，再按房間分批入場，新增每個原生程序前檢查至少2 GiB可用記憶體。五個server使用不同loopback UDP port，每個程序兩個job workers；沒有變更OS、安全性、網路政策或正式5080服務。

每房先取得真正AI損耗，停用自動攻擊後保存個別健康及接受政策序號。持續核對所有原玩家與room／rig／健康，任務狀態不得因管理失聯suspended；天氣、日夜、閃電旗標與敵軍房間也必須保持各房條件。沒有注入玩家姿態、射擊或統計，沒有啟用稀疏診斷或延長舊240秒探針。

房間1約tick2400時由自己的Room1控制台Pause，實際等待至少3秒並核對凍結tick；另外四房必須維持Running且tick增加。然後以同一房Resume。暫停仍逐幀核對名冊／健康／有效姿態，不計入Running人次。完整回放中每一Paused幀必須落於實際接受的Pause／Resume序號之間且tick相同；其他房間出現Pause仍算失敗，不能以「本輪有暫停測試」免除所有房間的失效。

五個live SSE在獨立觀察執行緒連續讀取，每個frame及heartbeat以來源擷取UTC檢查原1.5秒界線；主執行緒監看真正自有process handle與worker future，錯誤停止觀察後進入原cleanup，不因暫時無輸出重啟來源。原票券到期後再次確認playerId／admission／room／seat保持；沒有用過期票券重新入場。

五房各自核對唯一自動End、精確combat／world雙seal、全部原玩家的結果ack、七統計、world stream／sequence、ledger through與combat final sequence，另各輸出CSV。之後同時開五個4倍回放，從第1幀到各自封存尾端逐幀檢查序號／tick／capture gap／所有玩家、暫停與環境，不以少數檢查點、最後恢復或CSV一致代表全程正常。

證據位於全新`artifacts/desktop-long/<時間-識別>/`，以`independent-checks.json`／`fixtureKind=IndependentFiveRoomLong`與Linked工具區分，不能套用只支援Linked的跨場比較器。`executionFinished`表示已走完整驗證；`acceptancePassed`獨立保存全部live／replay、來源年齡及send queue full條件，只有通過且cleanup／snapshot成功才有`complete=true`與exit0。反例仍保留封存與原計數，不能因任務完成改寫成成功。

全部writer停止後才一次複製runtime到該次F槽`runtime-snapshot/`，保留C原件；保存SQLite不需另外開連線。來源與遊戲binary仍F，顯式SSD runtime的結果不代表F USB通過；既有資料、journal、票券與憑證不提交Git。沒有替代原31筆姿態失效的根因定位，完整需求與實機驗收仍見[REQUIREMENTS](REQUIREMENTS.md)。
