# 15分鐘 PC 任務驗證

五房Linked的多人版本另見[DESKTOP_MULTIPLAYER_LONG](DESKTOP_MULTIPLAYER_LONG.md)：已完成25個原生client／900秒與完整回放，發現2幀31筆失效body而判未通過；不修改或覆蓋本頁原單玩家成功紀錄，也不將它外推為多人成功。

此工具使用自己的新API、一個真正Windows server／一個headless client、固定900秒活動時間，驗證任務倒數、原入場、受傷狀態、世界保存與最終結果。頭手為Simulation，未操作鍵鼠／頭盔；不是25人、跨機、GPU效能或4小時穩定性驗收。結果與限制見 PROGRESS，不以工具來源碼存在宣稱通過。

不附掛既有240秒NativeReplicationProbe，也不經有240秒限制的故障代理。不能以放寬診斷上限或重開進程湊15分鐘。必須先有相符來源的Windows成功build receipt，正常API／來源／所有程序版本一致。

玩家先由真正AI造成非零損耗，控制者再停下自動攻擊。確認仍存活後，保存已接受的健康與政策序號；後續不得恢復成100或更換admission。原短效票券過期後，必須仍在同一連線／原入場中收到Running快照；這只驗既有連線延續，不把過期票券當作有效新入場證據。

工具從live SSE檢查收到的每份Running快照：自己的玩家存在、connected、rig=Simulated、政策生效後健康不變。額外檢查每份收到的快照／status來源UTC年齡，維持原[-1,1.5)秒範圍；記錄跳過的live序號，最後完整replay會逐幀補足。這些是實際收到資料時的取樣，不等於每個時間點的網路延遲或本機0.5秒姿態統計。

無意暫停、失效body、過期來源或保存幀間隔達1.5秒都不能被濾掉。工具會保留計數與最多200個反例，持續完成15分鐘與封存，以便調查；`executionFinished=true`不代表`acceptancePassed`或`complete=true`。只在全部接續條件、唯一tick18000自動End、原入場final JSON／雙seal／ledger及cleanup均成功後才complete。不得拿少數正常檢查點或最終報表一致冒充全程通過。

完整封存SSE以4倍速從1走至末幀，核對全部Running幀、tick單調且不超過18000、保存擷取時間間隔、精確末packet與所有統計。15分鐘回放約需另3分45秒，正常等待不是程序停止；只有已確認仍存活的工具handle才持續等待，不因log暫時無新行重啟。

```powershell
$env:VR_COMMAND_API_DLL = "$PWD/artifacts/build-clock-v1/bin/VrCommand.Api/release/VrCommand.Api.dll"
python scripts/check-desktop-long.py --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns"
```

資料在明確C SSD，source／binary仍F。全停writer才一次複製runtime回F、原件保留；不在保存SQLite上開連線。`live-observations.json`約30秒保存一次進度，最終`checks.json`內有完整計數、部分反例、票券過期後的原入場觀察與原生結果。憑證、資料庫、journal、binary及artifacts均不提交。
