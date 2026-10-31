# 世界來源的鎖、寫入與持久 flush 計時

接續[原生journal區段計時](PUBLICATION_TIMING.md)，將原本包住整個Recording.Append的區段細分。這是明確選用的Windows Development專用診斷；一般server／client及Android不安裝探針，world／journal／NGO／rules格式不變。

```powershell
python scripts/check-unity-admission.py --api-dll '<同次隔離建置API.dll>' --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns" --server-trace --journal-trace
python scripts/analyze-journal-stages.py '<該次artifacts/unity-admission目錄>' --output '<全新分析.json>'
```

`--journal-trace`要求同時選用server-trace，只附掛到自己的專用Server。底層`--vr-journal-trace`另要求全新絕對目錄、拒絕Client／Host。GameServer憑證仍只在桌面設定，頭盔沒有此能力。probe目錄固定runtime/journal-trace，和其他diagnostic分開；來源／binary仍F，runtime-root指定SSD才是SSD資料，不能混稱F效能。

共享C#9／netstandard2.1的WorldJournalTrace只保存metadata，以自身小鎖保護最多32768個完成列、64個in-flight stamp。沒有callback、Unity API、檔案IO或payload。重複完成／stamp複本不重記，Stop後不接受新stamp、已開始的仍可drain；容量／in-flight超界保留最早完成列並標truncated，不覆蓋。file及outbox未提供trace時不擷取時間或配置列。

| stage | 原始量測範圍 |
|---|---|
| 0 GateEnter | Monitor.Enter前後，含小量診斷呼叫成本；frame、ack、Pending與所有狀態讀取的同一outbox gate均涵蓋 |
| 1 Write | FileStream定位、長度／payload／SHA寫入與BinaryWriter.Flush；不包含外層WorldCodec JSON／驗證 |
| 2 DurableFlush | 真正FileStream.Flush(true)呼叫前後；含OS／排程／儲存路徑等待，不是只量實體媒體 |

operation 0–4分別Header、Frame、Ack、Complete、Seal；5為Pending，6–10為LastSequence／ThroughWorldSequence／AcknowledgedSequence／CompleteState／SealedState，11為Dispose。File層Frame的sequence=0表示unknown，不能解析或猜造序號；ack／completion／seal使用原9-byte整數metadata，Frame的outbox GateEnter則可帶已知輸入序號。初次建立VRWORLD1 magic signature的flush及讀檔／recovery掃描不屬於這些append量測。

逐筆Flush(true)、既有mutex、exclusive lease、checksum、durable ack／seal、失敗後fault及原始重試順序保持；不批次、不跳幀、不關持久化。trace只傳到建立的outbox及FileWorldJournal，不改共用journal介面；byte-for-byte測試核對相同header／frame／ack的診斷開關結果完全相同。

原生probe最多觀察90秒，finish.request僅每0.25秒檢查，避免每幀查檔干擾IO量測。cleanup先對兩個trace都request finish，再分別等待完整report；collector停止新增後最多drain5秒，未drain／overflow／壽命限制不稱complete。自己的觀察先停止才寫JSON，不在outbox critical section輸出。兩個probe的report IO可能被另一probe看見，但發生在最後live樣本之後，不納入Begin窗口。

分析器只讀已關閉、同場runtime固定位置的report，先用原publication分析器核對Begin／session／journal及大區段。再驗證long整數、frequency、managed主執行緒ID、90秒／32768列與inFlight=0；每列Stopwatch和UTC及原生start／stop anchors對照。全窗口被覆蓋且兩層clock誤差均不超過0.05秒才提供相關值，否則null。這個診斷容差不是遊戲0.5／1.5秒政策。

按managed thread ID分Main／Background，這些不是OS thread ID；每role／operation／stage分組，以UTC終點減去Stopwatch耗時定位區間，再裁切窗口／取聯集。不能直接以可能量化的UTC兩點差充當sub-ms耗時，或把有呼叫的零長度區間當沒有取樣。另算Main GateEnter與Background Ack DurableFlush的聯集交集，不把兩邊時間相加；失敗Write不補造成功Flush。不同執行緒／區段本來可能重疊。該outbox gate的背景ack內確實執行flush，但量測重疊仍不證明所有舊逾時或31筆姿態失效的根因；WS、API／SQLite及combat journal沒有新增分段量測。

實際Editor／雙平台、PC負載、反例與保存原件的結果以[PROGRESS](PROGRESS.md)為準；完整11項及實機／MR／跨機／25台驗收保持獨立。
