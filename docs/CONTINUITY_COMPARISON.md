# 長任務跨場證據對照

`scripts/compare-desktop-continuity.py`將已關閉的多人長場整理為JSON及Markdown表。它逐場保留失敗，**不判定根因、修復、容量或實機成功**；不因兩場乾淨、來源相同或欄位相同，就假定未量測的主機狀態也相同。

先以實際程序handle確認各工具已terminal、所有writer與原生程序均結束，再執行：

```powershell
python scripts/compare-desktop-continuity.py artifacts/desktop-long/<已結束場次A> artifacts/desktop-long/<已結束場次B> --output artifacts/continuity-comparison/<全新名稱>
```

只接受本庫明確的desktop-long時間目錄、executionFinished及無錯誤／無殘留的cleanup，拒絕受控校準混入自然長場。檔案metadata不是仍活著或已終止的獨立證明，呼叫者仍須先查驗實際handle，不能從一個stage.json或等待逾時重啟程序。

比對獨立sealed檔、原25名冊admission／room、全部結果ack、逐玩家七統計、world stream／sequence、ledger through／combat final sequence及CSV SHA／數值。要求900秒／tick18000、完整回放與人次計數一致，並依live／replay／來源年齡／queue error計數重查接受結果。原失效場即使25份最終結果／CSV完全一致，也仍保持未通過；工具不開保存SQLite、不讀控制台憑證、不重寫原始檔。

表格列source fingerprint、診斷模式、人數、Running幀、應核對人次、失效幀／玩家筆數及本場接受。`comparedFields`明列有比較的條件，不表示其他條件已受控。模式分為：

- `Sparse`：報告明確保存完整診斷宣告及預期程序數，且有manifest。
- `DisabledByTool`：報告明確保存poseContinuity=null且無manifest。
- `NotRecorded`：舊報告缺少模式欄位，不由資料缺少推成未啟用。

不同source版本、模式、人數或規則／素材條件逐項列出。即使同一0.33 source在開／關診斷兩場皆乾淨，這也只是序列進行、靜止Simulation的觀察，並非隨機實驗、根因已解或25位同時操作／跨機／頭盔驗收。

輸出只放全新artifacts目錄，包含比較JSON、Markdown及關鍵證據檔SHA。拒絕覆寫既有結果，所有原件／反例／C runtime／F snapshot保持。complete代表比較流程完成，不代表各場全部成功或整體開發完成；每輪原生結果與限制見[PROGRESS](PROGRESS.md)。
