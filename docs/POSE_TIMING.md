# 電腦端姿態時序診斷

Unity0.26.1／Android code30新增明確選用的兩端診斷，API／UI0.24、NGO24、player-fire-v1及所有資料／遊戲規則版本保持。它不修飾HUD警告，不改0.5秒姿態新鮮度、防瞬移、碰撞、入場或命中政策，也沒有新增網路欄位。原始碼與兩平台成功結果以 [PROGRESS](PROGRESS.md) 為準。

```powershell
python scripts/check-desktop-pose-trace.py --runtime-root C:/Users/USER/AppData/Local/VrCommand/SimulationRuns
python scripts/analyze-pose-trace.py artifacts/desktop-venue/<該次目錄>
python -m unittest discover -s tests -p test_pose_trace_analysis.py
```

檢查器使用自己的API／憑證／房間3、真正server與可見Simulated玩家。先自然運行60秒（可用--baseline-seconds設10–90秒），再由loopback代理原樣轉送UDP，只對這個玩家的上行丟棄1.2秒，驗證原0.5秒政策及同admission恢復。代理不解析、保存或改寫payload，不改防火牆／網卡或既有5080。接著依fire階段實際按Space一次，確認畫面彈藥29，再建立fire.done；檢視兩張原生GPU圖後建立review.done。完成檔不注入姿態／射擊。最後先明確結束診斷，再獨立End與精確seal，關閉所有writer後才複製runtime回F，保留SSD原件。

每個程序以獨立全新絕對目錄啟用 `--vr-pose-trace`。僅Windows Development，server可為batch／nographics；Android／Editor及一般未帶旗標啟動不安裝。它可以與明確選用的GPU探針共用，以分辨讀回／編碼／寫檔耗時，但姿態診斷本身不讀GPU、PCM或OS畫面，不記錄位置、旋轉、玩家姓名、票券、控制台key或UDP payload。

資料只存在32768列記憶體緩衝，保留最早證據、不環狀覆寫；正常240秒截止（主執行緒阻塞時須待回到Update才能執行截止）。多玩家可能提前達容量，此時truncated=true／complete=false，不能當完整測試。每0.25秒只檢查本機finish.request，收集期間不定期寫trace狀態檔。明確finish.request才標記收集完成；程式退出／owner銷毀或時間到為未完整。觀察截止時間在最終JSON序列化／寫檔之前，那段報告輸出可能造成的停頓不在本trace內。report.complete並不代表遊戲End／seal。

每列有Stopwatch相對秒數、引擎時間、DateTime UTC ticks、frame、connection數字與原始來源byte（0–255）；非法來源仍由原AvatarPose.Valid拒絕，記錄器不代替權威判定。Unity JsonUtility保留64位UTC ticks；分析器用整數解析。RPC入口區分PoseReceive、PoseInvalid、PoseThrottled、PoseAccepted與PoseRejected，owner另記TrackingUnavailable／DesktopInitializing／LocalPoseInvalid。BodyConnection是發布時的connected轉換，包含接收後最後接受姿態的本程序Stopwatch年齡，不能把它當transport disconnect。

WorldCapture、WorldJournal、CombatJournal、ManagementApply及WorldPublish為明確量測區段；原生玩家GPU探針另分PlayerGpuReadback、PlayerPngEncode、PlayerPngWrite。MainThreadGap只保存Update間超過100ms的空窗，最大值0表示沒有記錄到超門檻空窗，不是實際frame delta或FPS為0。

分析器只讀已關閉程序的trace JSON及階段時間，不開SQLite或憑證；自然、受控丟包及GPU階段分開。它保留跨階段邊界的收發間隔，並檢查同主機UTC與各程序單調時間的步進差異；時鐘跳動、控制段玩家／伺服器主線程空窗超過0.5秒等會使calibrated=false，不把混雜控制稱為校準通過。三項Python反例覆蓋邊界間隔、玩家停頓混雜及UTC跳動。

限制：PoseSend位於RPC呼叫前，並非transport傳送完成；沒有逐packet序號，不能把每個send與receive一一配對，亦不能單靠它分辨NGO排程與網路。BodyConnection在10Hz發布觀察，不是每個模擬tick；沒有捕捉到轉換不能證明完全沒有更短的中間狀態。同主機時序／loopback控制不代表跨機時鐘、RTT、Quest追蹤或25台效能。單次乾淨基線不證明歷史偶發原因或問題已修好。

2026-10-31最終實際結果：60.151秒自然基線呼叫／接收最大約56／67ms，沒有發布失聯或>100ms主線程空窗；1.2秒受控丟包時玩家呼叫仍約56ms，server RPC空窗1.222秒、接受姿態年齡0.589秒時發布非參戰，恢復後沿用原admission。GPU階段各區段最大約38.17／13.94／1.09ms，記到一次134.97ms主線程空窗，沒有0.5秒收件空窗或發布失聯；不能把134.97ms全歸因於GPU。歷史停頓原因未重現，仍待持續取證。完整場次、封存、雜湊與建置證據見PROGRESS。
