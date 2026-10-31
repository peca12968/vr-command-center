# 電腦端姿態時序診斷

## 目前版本的直接連線與重複按鍵

2026-10-31新增`check-desktop-pose-input.py`及`analyze-pose-input.py`，使用現有API／UI0.27、Unity0.28／NGO26的同源binary。這輪不重建Unity，也不改0.5秒姿態／1.5秒世界新鮮度。原時序資料只來自較早0.26.1版；下方舊受控丟包測試保留，不能替代本版人物／射擊音效及雙client的實際紀錄。

```powershell
python scripts/check-desktop-pose-input.py --api-dll artifacts/build-report-v1/bin/VrCommand.Api/release/VrCommand.Api.dll --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns"
python scripts/analyze-pose-input.py artifacts/desktop-venue/<本輪時間-識別>
python -m unittest discover -s tests -p test_pose_input_analysis.py
```

工具只建立自己的房間3／server、可見玩家及一個無圖形同伴；沒有UDP代理、故意丟包或payload改寫。三個程序各明確啟用現有`--vr-pose-trace`，可見玩家另啟用`--vr-hud-trace`，記錄每個渲染幀的狀態轉換、沒有原生GPU讀回／PCM／麥克風。先自然基線15秒，再依`stage.json`的input-shot實際按Space一次，檢視彈藥29／28／27後分別建立shot-1.done至shot-3.done。可在第二發前實按W一步；完成檔只確認操作，不注入姿態或射擊。每一shot階段包含操作員觀察／等待，不是武器處理耗時。

三發接受後，先明確finish三份有界記憶體trace，才獨立End／戰鬥及世界精確seal，等HUD最終狀態檔、關閉全部writer再複製runtime-snapshot回F。分析器只讀已關閉的JSON，不開SQLite、憑證或改原trace；分析輸出存本輪F目錄。

新分析按兩個client各自唯一PoseSend的connection ID篩server PoseReceive／Accepted／BodyConnection，避免背景玩家持續流量掩蓋另一人的空窗。保留跨階段邊界的間隔；connection改變拒絕分析，不能把重連前後當同一流。各程序UTC與Stopwatch步進差達50ms時，phases與三方交集均留null、CLI非零退出，不用錯時鐘做歸因。HUD相對時鐘以它自己的startedAtUtc近似對齊，沒有每packet／每發的對應序號。末尾過期但沒有下一狀態明示rightCensored，沒有把未知時長當零。

本版實際`20261031-075207-5621fa8a`已重現提示：三個程序的Update觀察空窗有共同**0.6425932秒**交集，UTC約23:53:08.870723–23:53:09.513316。可見玩家RPC呼叫空窗0.812241秒、同ID server入口0.811725秒；背景玩家也有0.744546／0.745023秒空窗，server同時發布兩人姿態過期。HUD保留約0.133828秒的POSE STREAM STALE後回ACTIVE，poseAccepted仍true；不是把過期誤稱姿態拒絕。

這個交集發生於兩發之間，已觀察到第一發彈藥29之後約4.6秒，而非扣彈當刻。**這只證明三個程序出現重疊觀察空窗，不證明整個OS暫停、音效／GPU／磁碟／排程器或transport的根因。**本輪有外部computer-use視窗觀察與輸入，尚未排除診斷及工具自身影響，不能直接推論一般人工操作／頭盔同樣成因。已標記的server記錄／發布區段在觀察期間最長2.7402ms，尚未涵蓋到停頓處；MainThreadGap是兩次Update之間的wall time，不能當CPU耗時。下一步需對未量測的PlayerLoop區段與獨立時間心跳取證，不調寬正式姿態門檻。

本輪4項真正原生流程、10項新合成分析反例及原3項分析回歸通過，完整資料、來源年齡、封存與限制見PROGRESS。沒有宣稱已修復，也不是頭盔／跨機／25台效能證據。

## 歷史的受控丟包／GPU區段

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
