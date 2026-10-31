# 原生開場命令的接受與套用

`scripts/check-desktop-startup.py`記錄管理端接受Begin、來源observedSequence、第一個觀察到的有效Running幀，以及完整封存回放中最早的Running幀。只有來源已觀察到該接受序號、非suspended、Running且tick>0才算套用；程序啟動、HTTP200、舊Running或Preparing／tick0均不算。

```powershell
python scripts/check-desktop-startup.py --api-dll '<同版API.dll>' --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns" --trials 3
```

使用自己的新API／資料、每場真正Windows server與兩個獨立client，來源全為Simulation。三場直接連線後，另執行一場受控校準：自己的loopback gate拒絕來源的管理GET，操作員直接對原API發Begin，確認管理已Running、世界仍Preparing／tick0且明確suspended，再恢復管理來源。gate不讀寫遊戲UDP、不記憑證／HTTP payload，不改玩家姿態或遊戲規則。

套用觀察界線仍15秒，來源擷取UTC保持原1.5秒門檻。secondsAfterResponse是本機收到控制回應至觀察到有效幀的時間，包含輪詢／儲存／發布，**不是網路延遲或來源內部執行時間**；受控場另列secondsAfterRelease。live可能略過幀，所以完整4倍回放必須從1到精確seal尾端連續核對，另保留firstApplied，不能混稱為同一個最早幀。

每場兩份原admission結果均須ack，七統計與各自world stream／sequence／ledger through一致；全部雙seal、回放及自有程序／gate清理成功才保存complete。證據在全新`artifacts/desktop-clock-faults/<時間-識別>/startup-checks.json`，與原clock工具格式分開；toolFingerprint為此腳本SHA，依賴版本另由Git／玩家receipt定位。沒有修改Unity或後端，沒有重建APK。

這是開場觀察工具與已知原因校準，**不是舊Preparing逾時或31筆姿態失效的根因證明**。原逾時場未保存Begin回應，不能從observed6推定它就是當時Begin序號；單一舊快照也不足以排除中間曾有其他狀態。新場沒有重現原撤銷／重加入與同時建置情境，SSD資料不當作F USB效能；實際結果及下一步見[PROGRESS](PROGRESS.md)。
