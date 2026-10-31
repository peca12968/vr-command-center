# 背景錄製下的玩家結果尾界

0.36 的 25 個原生 PC 程序長任務重現結果邊界競態：API／world journal 已封存到 8442，但其中一位玩家收到的 final worldSequence 為 8441，其餘 24 位為 8442。25 端都有 ack 不表示內容正確；原工具真正 exit1，沒有完成報告、CSV 或後續完整 API 回放，不能稱整場通過。場次與原始資料見 [PROGRESS](PROGRESS.md)。

原 checksum journal 中，8441 為 Running／observed36，8442 才是 Ended／observed37，兩者都是 tick18000。不能以相同到期 tick 或最後統計一致替代精確的 Ended 世界尾界；這也不是把 Begin 接受序號從幀內容猜出來的依據。

`ApplyManagement(Ended)` 已在主線排入不可再增加的 Ended 幀，但背景 writer 可以尚未保存該幀。若逐玩家用 `Recording.LastSequence` 建立 pending context，會把當時的 durable 前綴誤當任務終點，而且不同玩家可能綁到不同序號。等真正 seal 後再把這個舊 context 搬入 final，仍會傳出錯誤尾界。

0.36.1 的 pending context 改綁 `RecordingWriter` 已接受的 Ended 幀序號；沒有 terminal capture 或 writer 已失敗時不提供有效邊界。此序號只是**等待中的預期尾界**，不證明資料已持久寫入、已發布或已封存。遊戲 binding 仍在 End 立即解除，原 admission／room／seat、30 秒等待、HTTP 時限與結果 ack／斷線規則保持。

最終結果仍須 combat seal，再以世界同一份 immutable durable State 核對 Complete、Sealed、LastSequence 及 AcknowledgedSequence 都精確等於 context；session、stream、origin 也必須相同，才可選取玩家統計及送出 final。錯誤或不完整的尾界保持 pending／原逾時，不能放寬客戶端的精確序號檢查或直接改寫它已接受的結果。

Editor 測試用自己的 FileWorldJournal gate 阻住 Ended 寫入，重現 durable1／captured2；驗證 context2 在寫入前、只落盤、只 ack 時都不能當 final，真正 seal 後才通過。舊尾界、外場／stream、非 terminal 或 IO failure 均拒絕。這是結果封存競態的修正，不是舊 31 筆 body 失效、F USB 發布吞吐或實機容量的修復證據。

world／NGO wire、API／UI、rules、素材 pin、Tracked 姿態及 0.5／1.5 秒政策保持。雙平台仍須使用同次來源建置；沒有頭盔時先核對 PC 原生程序，Quest／VIVE、MR、跨機與 25 台設備各自待驗。
