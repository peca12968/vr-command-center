# 原生開場命令的接受與套用

`scripts/check-desktop-startup.py`記錄管理端接受Begin、來源observedSequence、第一個觀察到的有效Running幀，以及完整封存回放中最早的Running幀。只有來源已觀察到該接受序號、非suspended、Running且tick>0才算套用；程序啟動、HTTP200、舊Running或Preparing／tick0均不算。

```powershell
python scripts/check-desktop-startup.py --api-dll '<同版API.dll>' --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns" --trials 3
```

使用自己的新API／資料、每場真正Windows server與兩個獨立client，來源全為Simulation。三場直接連線後，另執行一場受控校準：自己的loopback gate拒絕來源的管理GET，操作員直接對原API發Begin，確認管理已Running、世界仍Preparing／tick0且明確suspended，再恢復管理來源。gate不讀寫遊戲UDP、不記憑證／HTTP payload，不改玩家姿態或遊戲規則。

套用觀察界線仍15秒，來源擷取UTC保持原1.5秒門檻。secondsAfterResponse是本機收到控制回應至觀察到有效幀的時間，包含輪詢／儲存／發布，**不是網路延遲或來源內部執行時間**；受控場另列secondsAfterRelease。live可能略過幀，所以完整4倍回放必須從1到精確seal尾端連續核對，另保留firstApplied，不能混稱為同一個最早幀。

每場兩份原admission結果均須ack，七統計與各自world stream／sequence／ledger through一致；全部雙seal、回放及自有程序／gate清理成功才保存complete。證據在全新`artifacts/desktop-clock-faults/<時間-識別>/startup-checks.json`，與原clock工具格式分開；toolFingerprint為此腳本SHA，依賴版本另由Git／玩家receipt定位。沒有修改Unity或後端，沒有重建APK。

上述`210737`是開場觀察工具與已知原因校準，**不是舊Preparing逾時或31筆姿態失效的根因證明**。原逾時場未保存Begin回應，不能從observed6推定它就是當時Begin序號；單一舊快照也不足以排除中間曾有其他狀態。該場沒有原撤銷／重加入與同時建置情境，SSD資料不當作F USB效能；後續原入場流程與封裝重疊結果如下。

## 原入場檢查與發布積壓

`scripts/check-unity-admission.py`現在也保存有界`begin-witness.json`：Begin回應序號、最多256個最早live取樣、全部取樣計數、首次有效套用、來源UTC／擷取年齡及回應後觀察時間。缺少capture UTC保留null，不用收到時間補造來源新鮮度；不保存玩家姿態、票券或raw payload。Preparing／tick0、舊序號Running、suspended均不能通過套用判定。這項套用判定和擷取年齡分開，不能把已套用的過期幀當作符合1.5秒新鮮度政策。

原撤銷／同ID重新加入、舊票券／舊移除拒絕、背景程序重連、位置／健康／彈藥及末幀統計檢查保持，Running觀察仍15秒。可明確選用新SSD執行資料：

```powershell
python scripts/check-unity-admission.py --api-dll '<同版API.dll>' --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns"
```

未帶`--runtime-root`仍使用自己全新F artifacts目錄；帶入時只在指定根下建立唯一新目錄，API的missions／sessions及server telemetry均在此。二進位、設定／log與觀察證據仍F。全部自有writer停止後才以既有writer lease fence複製`runtime-snapshot`回F，不搬動／刪除原件或改現有服務；cleanup／snapshot失敗保持失敗。stage與summary明列實際runtimeDirectory。observerFingerprint為check-unity-admission.py、admission_witness.py及共用snapshot所在start-desktop-venue.py的名稱＋內容SHA，**不是Python／OS／原生binary的完整依賴雜湊**；遊戲來源另由原receipt核對。

### 關閉來源的唯讀核對

live只顯示API已接受資料，逾時不能據此斷言來源沒有套用。新增`analyze-world-journal.py`以`rb`讀取**已停止writer**的VRWORLD1檔，逐筆核對長度、SHA256、連續world sequence、不可倒退觀察與ack／completion／seal邊界；不開SQLite、不建立outbox writer、不ack／補送／修復／截尾。只輸出有界狀態轉換、第一個有效套用、最後來源幀／持久ack及未確認數，`--output`必須是新檔。這是binary envelope與序號核對，**不是完整遊戲規則／幾何驗證或封存成功宣告**。

```powershell
python scripts/analyze-world-journal.py '<已關閉的.worldlog>' --accepted-sequence <control-Begin.json的接受序號> --response-utc '<begin-witness.json的responseObservedAtUtc>' --output '<全新分析.json>'
```

只能使用該場已保存的接受序號，不能為舊場猜測；`firstAppliedCaptureSecondsAfterResponse`比較本機UTC擷取與收到回應的時間，含輪詢／排程等，不稱RTT或命令內部耗時。工具保留舊header缺少UTC的unknown，損壞或未知tag直接失敗，不忽略尾端。實際F反例／SSD比較、雜湊與限制見[PROGRESS](PROGRESS.md)；完整11項、原31筆與頭盔／跨機驗收保持未完成。
