# 電腦端姿態時序診斷

## 外部唯讀程序CPU取樣

在既有檢查器另加`--process-timing`，會為自己的visible／peer／server取得唯讀Windows CPU計數，不改Unity來源、二進位、遊戲規則或新鮮度門檻：

```powershell
python scripts/check-desktop-pose-input.py --heartbeat --player-loop --process-timing --api-dll artifacts/build-report-v1/bin/VrCommand.Api/release/VrCommand.Api.dll --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns"
python scripts/analyze-pose-input.py artifacts/desktop-venue/<本輪時間-識別>
python -m unittest discover -s tests -p test_pose_process_timing.py
```

父程序借用原Popen handle確認exe／建立FILETIME，不關閉原handle；獨立probe重新以QUERY_LIMITED_INFORMATION＋SYNCHRONIZE開啟並核對同一身分，固定handle避免PID重用。只查[GetProcessTimes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes)與[QueryProcessCycleTime](https://learn.microsoft.com/en-us/windows/win32/api/realtimeapiset/nf-realtimeapiset-queryprocesscycletime)，無thread／memory／stack存取、暫停、優先級或權限設定。每50ms、最多5000輪／15000列／240秒；基線前一次ready，之後樣本只存記憶體，明確finish先關唯讀handle才一次寫report。所有cleanup必須無剩餘自有程序。

manifest與report在runtime的pose-process-targets.json及pose-process-timing/；只有完成fixture才可分析。以每個查詢的前後UTC括號篩選完全在原生空窗內的樣本，不插值，上界向外取整，少於兩個點為未知／null。輸出原Update及三方loop共同區間，另提供名義等長的前後比較窗口；實際取樣跨度仍明示，不能把CPU累積差當固定負載／每核百分比。CPU時間與cycles加總全程序threads，不能由正值指定主線程或根因、也不能由零值證明suspend；cycles不轉換成秒。身份／完整性／關閉handle／clock檢查失敗拒絕，UTC差達50ms不join。

2026-10-31兩場新證據：091639場共同loop0.6374241秒，各13個內部樣本CPU時間差為0，但前後計數均增加；原raw未記cycles，讀為version0／unavailable，不補寫。092109場共同loop0.594546秒，每程序12個樣本，三者CPU時間均增加0.015625–0.03125秒，cycles增加約1875萬–2208萬，11對相鄰查詢每對均增加。這不支持三程序在該區間全程停止，但仍不識別主線程／worker或解決根因；不能推論兩場同類提示底層成因相同。43項Python及兩場真正三發／精確封存，資料／限制見PROGRESS；Unity0.28.1與既有雙平台來源不變。

## 明確選用的主迴圈邊界

Unity0.28.1／Android code33新增`--vr-pose-loop-trace`，必須同時有`--vr-pose-trace`，仍只限Windows Development／非Editor。一般啟動與Android不安裝。檢查器以`--player-loop`向自己的三個程序傳遞旗標，建議另帶`--heartbeat`對照獨立程序；其餘操作與原三發流程相同：

```powershell
python scripts/check-desktop-pose-input.py --heartbeat --player-loop --api-dll artifacts/build-report-v1/bin/VrCommand.Api/release/VrCommand.Api.dll --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns"
```

記錄器從**目前**PlayerLoop樹，在每個既有節點前後插入自己的兄弟觀察點，保留原type／delegate／native function／loop condition與次序，不替換引擎或NGO。最多512節點／32層，超界在安裝前拒絕；不在運行中反覆重建樹。每個觀察點只讀單調時間／UTC／frame與更新有界計數，不做GPU、音訊、網路或檔案輸出。原trace仍32768列／240秒；新增獨立4096個>100ms相鄰觀察空窗，保留最早證據，截斷不能complete。每節點統計保留實際最大相鄰間隔，沒有稀疏列不能當零frame delta。

診斷finish時從**當時目前的樹**只移除屬於自己的marker，再停止收集與序列化`report.playerLoop`；不把舊樹快照寫回而覆蓋後來的NGO／其他變更。Unity的[PlayerLoop API](https://docs.unity.com/en-us/engine/6000.3/script-reference/unityengine/lowlevel/playerloop/setplayerloop)在下一次完整迴圈才套用新次序，因此剩餘當幀marker由stopped旗標成為no-op。結束診斷仍須另做End／精確seal，detached不代表遊戲結束。

分析保留from／to的節點path、名稱、before／after及frame。相同path的before→after標為inside observed system，其他為between observers；跨幀／樹外時間亦保留。這是觀察點間的**wall time**，包含等待、排程及診斷成本，不能由名稱斷言某子系統CPU耗時或根因。核對pair、計數、稀疏列與max一致、完整性、時鐘／UTC覆蓋後才做phase及三程序交集；缺失宣告的報告拒絕。沒有新的遊戲事件／world／NGO欄位，API／UI0.27及NGO26保持；新的來源指紋需同源雙平台建置，不能用舊receipt啟動。

本輪`085931-26eeed5d`真正取得三程序相同的after WaitForLastPresentationAndUpdateTime→before TimeUpdate空窗（0.869584／0.729702／0.725520秒）。這不是該Wait的before→after；三方邊界共同0.7167323秒，原Update共同0.727348秒，獨立timer整場≤16.433ms。不得只由標籤假設引擎的實際執行順序或歸因該節點。未啟用loop的同版實際三發對照乾淨，仍未排除診斷及外部操作擾動，不稱修復。三份294邊界報告都detached並覆蓋完整觀察期，否則CLI非零；109真正EditMode／同源Windows與Quest、33項Python及49項一般UI／native回歸，完整數據見PROGRESS。

CLI要求完成的input-timing-result及cleanup metadata；不能分析失敗／仍開啟的fixture當成功。JsonUtility會把未啟用的null報告class寫成空預設物件，只有fixture明確playerLoop=false且每欄皆為該空預設才能忽略；declared true、未知模式或非空／失敗資料仍拒絕。不修改raw報告來配分析器，舊沒有欄位的資料保持可讀。

## 獨立程序心跳與操作對照

目前檢查器另有明確選用的`--heartbeat`，啟動自己的普通優先級Python程序，每10ms sleep後量單調時間、UTC及process CPU。沒有UI、遊戲或網路介面，不改系統設定。只在記憶體記>100ms空窗與每秒clock anchor，4096列／256 anchors／240秒上限；明確finish才complete，輸出在觀察結束後。helper持有自己的程序handle並在finally收尾；heartbeat-cleanup與native cleanup必須皆無殘留。

```powershell
python scripts/check-desktop-pose-input.py --heartbeat --api-dll artifacts/build-report-v1/bin/VrCommand.Api/release/VrCommand.Api.dll --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns"
python scripts/check-desktop-pose-input.py --heartbeat --observation-only --api-dll artifacts/build-report-v1/bin/VrCommand.Api/release/VrCommand.Api.dll --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns"
python scripts/analyze-pose-input.py artifacts/desktop-venue/<本輪時間-識別>
python -m unittest discover -s tests -p test_pose_heartbeat.py
```

observation-only先安靜基線，在window-review階段只觀察、不按遊戲鍵，觀察後建立該輪`window-review.done`，再安靜同長時間。人工作業確認有120秒界線，這不是遊戲新鮮度門檻；trace仍240秒有界，耗時過長會拒絕不完整結果。外部操作起訖應另存該輪根目錄，不改runtime原始報告。

2026-10-31真正射擊場`082536-8cb741cb`再次取得三Unity共同0.7017494秒Update觀察空窗與HUD約0.088214秒過期；獨立程序完整覆蓋它，整場最大wake間隔13.348ms、UTC／單調步進差1.456ms。這不支持「全部程序／整個OS一起暫停」，仍未證明Unity內哪個階段或外部因素造成。另文字／截圖各5次、無UI安靜場、同一exec handle六次輸出poll場皆無觀察期過期；不能由乾淨對照證明歷史偶發已修復。不同操作組合／時機、診斷與外部工具影響仍待排除，原0.5／1.5秒門檻保持。

分析核對報告完整性、counter範圍／順序、UTC guard與覆蓋區間，明示fullyCovered／uncovered；沒有>100ms列不代表timer delta為零，須看maximumWakeGapSeconds。新報告使用明確UTC起訖，早期沒有欄位的檔案只用首末anchor保守覆蓋，不修改raw檔。時鐘偏差達50ms時心跳join留null、CLI非零；native join仍按自己時鐘獨立判斷。7項心跳（其中一個真正timer程序）、12項輸入與3項舊分析檢查通過；舊無心跳資料保持可讀。完整四場資料、失敗與限制見PROGRESS。

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
