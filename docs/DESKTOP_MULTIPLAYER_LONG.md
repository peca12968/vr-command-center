# 五房25個 PC 程序的15分鐘任務

新增[稀疏長診斷](POSE_CONTINUITY.md)選項`--pose-continuity`；新場8449完整回放／209775人次及26完整報告乾淨，不覆蓋下列原31筆失效。Unity0.33／code40，API/UI0.30與NGO29保持；模式成本與原始／受控場次分開，不以新模式乾淨一次稱根因已修復。

`scripts/check-desktop-multiplayer-long.py`把原[單玩家長任務](DESKTOP_LONG.md)的連續性驗證擴至五房Linked世界，預設每房5個、共25個真正Windows client及1個server。使用新API與自有資料，固定900秒活動倒數，不重啟程序累計時間。所有client為靜止、無圖形Simulation，沒有鍵鼠／姿態／武器注入；**不是25位同時操作、25台裝置、跨機／Wi-Fi或頭盔容量驗收**。

## 執行

```powershell
python scripts/check-desktop-multiplayer-long.py --api-dll '<本次同版API.dll>' --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns" --players-per-room 5
```

API／UI0.30、Unity0.32／NGO29，沿用已成功的原Windows build receipt及來源fingerprint。工具不修改Unity、API或遊戲規則，不附掛原240秒replication probe，也不延長該probe的限制。`--players-per-room 1..5`可使用5／10／15／20／25個client，每次報告保留真實人數，不將較少程序的結果推成25個成功。每個玩家獨立PID、admission與原短票券；按5個一批確認正常入場，逐次確認可用記憶體至少2GiB。

資料位於本輪C SSD runtime，來源及Unity binary仍F。工具只管理自己的新API／場次／程序，不接5080歷史，不變更網路、OS或安全性提示；使用者若要驗證實體網路或GUI，須另行進行。

## 連續性邊界

開始前確認25份正常來源姿態及五席分配。Begin並選用活動倒數後，真AI在每房造成非零損耗；控制者再關閉自動攻擊，保存政策序號及每位仍存活玩家的健康。之後在所有已觀察Running幀中檢查完整名冊、同房、connected、Simulated、未被淘汰，並在該政策生效後保持個別健康。每次原生程序意外退出皆失敗；這個固定健康階段不是持續移動／交火測試。

每份live frame／status年齡仍使用來源擷取UTC，範圍[-1,1.5)秒，不拿收到時間重設來源年齡。live SSE可能跳過舊幀，跳過序號與觀察間隔均記錄，不能當逐封包送達率。所有票券都到期後，至少再觀察一次全部原入場仍有效；原playerId／admissionId／room／seat不變，每個client日誌只可有一次本地connected。這驗證既有連線延續，沒有以過期票券重新入場。

自動End須唯一且tick18000。所有玩家各自收到原admission的結果並ack，七統計欄、combat final sequence、world sequence／stream及原ledger逐一核對；CSV亦逐玩家核對。未取得全部ack或雙seal時不能算完成。結果保留原Simulation標示，不因名冊Quest3分類變成實機。

## 回放及證據

精確封存後從第一幀以4倍速走完整SSE replay，序號必須連續、tick／擷取elapsed不倒退、不超18000，最後完整packet與封存末幀一致。檢查每份Running幀的全部玩家，不只第一人或正常檢查點；保存幀擷取間隔達1500ms、意外Paused、失效body、錯房或健康重設皆計入失敗。正常Ended退場不當作Running失效。

`multiplayer-live.json`約30秒寫一次，`multiplayer-resources.json`為原生可用記憶體觀察，`multiplayer-native-clients.json`保存自有PID／入場對照。最終`multiplayer-checks.json`分開executionFinished／acceptancePassed／complete；記錄全量失敗計數、每玩家失敗幀及最多200個反例。達到反例上限不丟棄後續計數，也不過濾意外Pause。`expectedParticipantObservations`是應核對人次，不能以它當成全部body已成功的證據，須同看badFrames／reasonCounts與passed。

原生日誌出現send queue full也不能通過本工具的連續性接受。只有完整live／replay、原入場／逐玩家結果、CSV／雙seal、所有原生程序收尾及來源指紋核對都成功，complete才為true；`networkCapacityAccepted`始終false。工具退出失敗時保留原世界、原生日誌與反例，不將封存成功或最終CSV一致改寫成全程通過。

900秒活動任務後另需約3分45秒回放與封存時間；有已確認存活的工具handle才繼續等待，不因暫時沒有新log重開同一測試。全部writer停後由Venue一次snapshot回F、保留C原件，保存SQLite不開連線；憑證、票券、DB、journal、binary與artifacts均不提交。每輪實際成功或未達門檻的結果見[PROGRESS](PROGRESS.md)，不以工具存在宣稱通過。
