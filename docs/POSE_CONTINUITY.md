# 長任務的稀疏姿態診斷

Unity0.33.0／Android code40／NGO29新增獨立`--vr-pose-continuity <全新絕對目錄>`模式。只限Windows Development、非Editor；一般啟動與Android不安裝。舊NativePoseTrace仍32768列／240秒，NativeReplicationProbe仍240秒，沒有延長原工具或改舊資料／讀取器。新模式與舊pose／loop trace互斥；`--vr-pose-continuity-loop`必須同時有新收集器。

目的為捕捉[25程序15分鐘](DESKTOP_MULTIPLAYER_LONG.md)在第12分鐘附近的失效。API/UI0.30、envelope7／world schema1／NGO29、rules0.8.0與0.5秒姿態／1.5秒來源政策不變；診斷不授權傷害、延長參戰或移動Tracked資料。需要本輪同源Windows／Quest建置，實際結果及限制見[PROGRESS](PROGRESS.md)，不能以儀表本身稱根因已解。

## 啟用與上限

```powershell
python scripts/check-desktop-multiplayer-long.py --api-dll '<本次API.dll>' --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns" --players-per-room 5 --pose-continuity
```

工具在自己的26個原生程序啟用新模式，只有server加PlayerLoop邊界觀察，25個client只記收發／Update與自身執行緒計數。每程序有獨立短目錄及manifest，原25玩家配置仍只有Client短票券，不把GameServer key傳給玩家。

每程序最多1200秒、256個(point／connection／source)聚合stream、4096個稀疏gap、4096個body轉換及4096個主執行緒空窗；PlayerLoop沿用512節點／4096個>100ms邊界空窗。超界保留最早證據並標truncated／complete=false，不環狀覆寫。時間截止需主執行緒回到Update才執行，不能當作能中斷卡死的外部watchdog。

ManagementApply等正常輪詢本來就可能相隔200ms以上，gap是稀疏時間記錄，不自動代表異常；必須按point、connection及階段解讀，不能把總gap筆數當姿態或封包失敗數。

PoseSend／PoseReceive／PoseAccepted／拒絕／throttle及既有WorldCapture／WorldJournal／WorldPublish／CombatJournal／ManagementApply量測共用原呼叫點。正常事件只累加有界統計，間隔或量測工作超200ms才保留端點；body只記connected轉換與最後接受姿態的本程序年齡。沒有逐pose清單、位置／旋轉、玩家姓名、票券、管理key、UDP payload、GPU／PCM或OS畫面。每個正常事件仍有診斷成本；不能把此模式視為零擾動。

所有程序只在記憶體收集。每0.25秒最多查看自己的finish.request；900秒任務End、全部玩家結果ack且雙seal完成後，父工具才明確finish，先停止收集／移除本身PlayerLoop markers，再序列化並原子產生report.json。報告輸出在收集窗口之外，仍可能佔用主執行緒；工具安排在任務封存後，不把它當作任務內的自然停頓。明確finish、未截斷且counter有效才complete；退出、owner銷毀、到時或counter失敗都不能算完整。

## 自己的主執行緒計數

在Install與本收集器Update，以呼叫執行緒的[GetCurrentThread pseudo handle](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getcurrentthread)讀取[GetThreadTimes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getthreadtimes)與[QueryThreadCycleTime](https://learn.microsoft.com/en-us/windows/win32/api/realtimeapiset/nf-realtimeapiset-querythreadcycletime)。不列舉或開啟其他執行緒，不讀記憶體／stack，不暫停程序、不調優先級或OS設定；pseudo handle不需要關閉。

每筆sample有Windows thread ID、creation FILETIME、kernel／user的100ns累積值、cycles，以及查詢前後的單調秒數／UTC括號。只保存Update-to-Update相隔>200ms的兩端sample，另保留總sample數及clock step最大值；thread ID／creation或counter不一致拒絕。不是完整CPU profiler，也不能用沒有稀疏空窗推成frame delta或CPU為零。

分析出的mainThreadCpuSeconds只屬**整個sample括號**，包含一整幀及其間的等待／工作；不是某個engine node內的CPU時間。QueryThreadCycleTime的cycles保持原整數差，不換算秒。CPU時間的量化或零增量不證明執行緒全程停止。PlayerLoop觀察點仍只是wall time，inside／between及跨幀要分開，不由名稱歸因根因；其他worker工作不計入此主執行緒數值。

## 校準與分析

```powershell
# 兩個headless真client，一位由自有loopback gate刻意中斷上行1.2秒。
python scripts/check-pose-continuity.py --api-dll '<本次API.dll>' --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns"
# 長場所有原生程序及writer確定退出後：
python scripts/analyze-pose-continuity.py '<本次desktop-long目錄>'
```

校準只轉送原UDP bytes並在明確窗口丟棄單一自有client的上行，不解析／保存payload、不注入姿態／射擊，也不改外部網路。檢查該玩家body過期及同admission恢復、peer仍有效、server收到>0.8秒空窗且sender無>0.2秒呼叫空窗。`calibrationPassed=true`不代表自然25端根因或容量成功；受控掉包與自然場次要分開。

分析只讀已關閉fixture的JSON與cleanup／診斷metadata，不開SQLite或讀控制台憑證；可分析executionFinished=true但acceptancePassed=false的自然場，不能把部分／仍活著的fixture當完成。解析器明確驗role、版本／容量、clock／counter單調、stream／gap對照與PlayerLoop宣告。JsonUtility會將未啟用的loop class寫成初始化預設物件，僅精確空形狀可作缺少模式，非空未宣告資料仍拒絕。

以保存世界的Running擷取UTC窗口篩選body轉換及收發／主迴圈／loop空窗；clock step達50ms則不做跨程序join，結果留null且CLI非零。RPC的PoseSend只是呼叫前觀察，不是transport送出完成；沒有packet序號，不能逐封包配對。時間重疊、較少CPU或單次乾淨長場都不證明底層根因。分析輸出另存，拒絕覆寫既有分析；原始報告、失敗、封存與snapshot保持不變。
