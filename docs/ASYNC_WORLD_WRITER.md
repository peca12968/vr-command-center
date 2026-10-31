# 有界背景世界錄製

0.36.1 的玩家結果等待 context 改綁已排入的 Ended 幀，final 另核對真正 durable seal；不能把背景寫入中的 LastSequence 前綴當任務終點。原長場反例與修正見 [DEBRIEF_BOUNDARY](DEBRIEF_BOUNDARY.md)。

0.36承接[JOURNAL_STAGES](JOURNAL_STAGES.md)的量測：0.35世界幀的同步Flush及背景ack持鎖，會阻塞遊戲主執行緒的寫入／狀態讀取。新路徑把**常態世界幀**的檔案寫入移至獨立背景writer；啟動時header建立與combat journal仍可能同步IO，不稱所有IO已離開主執行緒，也不保證F USB吞吐量或修復舊31筆。

主執行緒仍在原0.1秒節奏擷取真實Arena／頭手／事件與原UTC時鐘，再序列化／detach純DTO，提交immutable JSON。writer按FIFO逐幀重建DTO並執行原WorldOutbox.Append，每筆仍Flush(true)；Ended幀成功後才寫completion intent。Unity對純DTO的背景JSON支援見官方[ToJson](https://docs.unity.com/en-us/engine/6000.3/script-reference/unityengine/jsonutility/tojson)／[FromJson](https://docs.unity.com/en-us/engine/6000.3/script-reference/unityengine/jsonutility/fromjson)；不在背景讀Transform／Input／Arena或操作UI，callback在主迴圈通知。

`CapturedSequence`及`CapturedThroughWorldSequence`只代表已提交的記憶體快照，用於下一幀序號與事件cursor，**不是durable／ack／可回放完成邊界**。WorldOutbox的immutable State只在原journal Flush成功後以Volatile公布；狀態讀取不再等待檔案mutex，任何單個State內的Last／Through／Ack／Complete／Sealed來自同一提交點。Pending及寫入仍受原同一gate保護，沒有關閉lease、checksum、逐筆flush或讀取完整性檢查。

writer最多32個未完成幀（含in-flight），UTF-8 JSON合計最多8MiB，單幀仍受原journal record上限限制。caller之後改動原DTO不影響排隊內容。序號錯誤或無效packet不消耗提交序號；滿載會fail closed、停止接受新幀並暫停combat，已接受幀仍依序drain；IO失敗保留durable前綴，不製造frame／ack／completion。`VR_WORLD_WRITER_FAULT`僅一次記錄captured／durable／pending計數，不含payload／憑證。

發布另用背景task讀**durable** Pending，仍等待真正combat ack、API receipt、world durable ack及精確雙seal；不以queue成功當網路成功。writer與WS發布分開，網路暫時中斷不阻塞writer保存。停止時先停止接收、等待已接受write與進行中的publisher完成／取消後才釋放source lease；不在主迴圈同步Wait或先關file。正常End仍須原完整seal流程；非正常process終止可能失去未落盤queue，尚未發布的buffer不能稱已保存，補送不是引擎世界恢復。

`QueuedWorldRecorder`只接受全新空source，不把journal recover當成Arena／玩家恢復；既有同步WorldOutbox／恢復工具保留。live NGO可能領先durable世界錄製，管理端仍使用原擷取UTC與1.5秒門檻判斷新鮮度，不能用收到時間、queue序號或恢復後正常掩蓋過期窗口。

已停止writer的VRWORLD1可用`python scripts/analyze-world-journal.py '<閉源.worldlog>' --output '<全新.json>'`做持久回條積壓核對，不開SQLite或建立outbox。新增peakUnacknowledgedFrames與最早firstPeakBoundary（幀／ack／tag／byte offset），逐筆checksum及連續性檢查後才產出；後來歸零／seal不清除曾經的高峰。這是**已保存幀但尚無本地durable receipt的差額**，不是32幀記憶體queue深度，也不證明API拒收或網路延遲；acks沒有獨立擷取UTC，不補造高峰持續時間。沒有該場Begin回應時可省略accepted-sequence，applicationBoundaryKnown=false／firstApplied=null，不猜接受序號；提供response-utc仍須精確Begin邊界。舊報告缺peak欄位是unknown，不能補成0或改寫歷史。

舊診斷點`WorldJournal`代表同步Append；新`WorldEnqueue`代表主線提交而非磁碟持久寫入，兩者不可直接當相同成本比較。分析器明列captureMode，混合模式拒絕；WorldCapture內含各自模式，不相加。真正Flush仍由細分trace以managed thread ID分類，Main／Background及重疊區間不可任意加總。

`check-unity-admission.py --server-trace --journal-trace`只在自己的測試程序、每輪最多讀server.log尾端64KiB以fail fast擷取writer故障計數；只有不完整／失敗證據，不稱成功。一般模式不加這個log檢查。trace仍沿用90秒／32768列／64 in-flight與0.25秒finish檢查，所有原生證據和範圍見PROGRESS。

不改world schema／header／rules／素材／NGO wire，API／UI版本保持；共用.NET DLL及所有遊戲端仍須取同次來源建置。這是PC／Quest優先路徑的進展，完整11項及頭盔／MR／跨機／25台／廠商硬體驗收各自保留。
