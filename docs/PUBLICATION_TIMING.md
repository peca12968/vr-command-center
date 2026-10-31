# 原生開場窗口的寫入區段計時

承接[Begin接受／套用及來源journal](STARTUP_WITNESS.md)。現有Windows Development播放器已提供`--vr-pose-trace`，在主執行緒量測`WorldJournal`／`WorldCapture`等區段。新入場檢查只在明確`--server-trace`時把它附掛到自己的server；一般執行／client／Android不新增探針，沒有修改Unity或共享遊戲程式。

```powershell
python scripts/check-unity-admission.py --api-dll '<同版API.dll>' --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns" --server-trace
python scripts/analyze-publication-timing.py '<該次artifacts/unity-admission目錄>' --output '<全新分析.json>'
```

省略runtime-root仍使用新F資料；省略server-trace不附掛。trace目錄固定為該次runtime/server-trace，沿用既有240秒／32768列上限。檢查結束或失敗後、停止server之前才建立自己的finish.request，最多等5秒取得完整／非truncated原生report；失敗仍清理所有自有actor、保留cleanup錯誤且工具exit1。探針先停止觀察才序列化／寫report，這段最終輸出IO不算進原trace。SSD snapshot仍在全部writer停止後才一次複製，保留原件。

分析器只讀已停止writer的自有場次：stage所指runtime、固定server-trace、control-Begin及有界witness、cleanup的終態與單一worldlog。接受序號必須一致，journal header的sessionId也必須對應該命令；不讀server設定或金鑰、不開SQLite、不重送／修復。輸出只有metadata、證據SHA及兩個分析腳本的fingerprint，output必須新檔；不是完整OS／native依賴證明或數位簽章。

相關窗口從收到Begin回應的UTC到最後保存live樣本的UTC；各樣本的單調經過與UTC經過、原生row的Stopwatch經過與UTC經過均核對。trace必須覆蓋全窗口，最大時鐘差不超過0.05秒才提供UTC區段交集。這是診斷相關性的容差，**不改遊戲0.5／1.5秒政策**。覆蓋不足或時鐘差超界時保留總取樣／原生最大耗時，但相關窗口欄位為null，不能用0冒充沒有成本。未完成或truncated的trace／witness直接拒絕。

區段先裁切到窗口，再對**同一point**的UTC區間取聯集，避免重疊／量化重複計時；不同point各自保留，不能相加。WorldCapture包住WorldJournal，MainThreadGap是Update觀察間隔而非CPU時間。超過0.1秒的異常明細每point只留最早64列，但全體計數／聯集仍計算，明細截斷與原生buffer截斷是不同旗標。

`WorldJournal`是在`Recording.Append`外的既有主執行緒Stopwatch區段，**包含鎖等待、JSON／驗證、append及Flush(true)，不是單獨fsync或CPU量測**。它沒有world sequence標記，不能將第N個span直接冒充worldN。背景ack的journal鎖／append／flush、WebSocket交換、API驗證／SQLite／durable receipt均尚未分別計時；WorldPublish點是NGO場景複製，不能誤稱WS發布成本。

兩次新原生封裝重疊的數字、真正終態、原件保持及差異見[PROGRESS](PROGRESS.md)。F反例已量到長寫入區段，但探針本身也是新增觀察條件，沒有證明單一硬碟因果、所有逾時修復或與舊31筆姿態失效相同根因。來源／binary仍F、SSD資料明確C；頭盔、跨機及25台驗收另行保留。
