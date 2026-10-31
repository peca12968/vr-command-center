# 電腦端接收狀態診斷

實際W／Space／R／Space到25端的檢查及新增全程條件見[DESKTOP_ACTIVE](DESKTOP_ACTIVE.md)。該工具分批要求快照、使用自己的artifact family；原靜態capacity範圍與歷史結果保留，不把單次檢查點一致推成全程持續可參戰。

`check-desktop-capacity.py --replication-probe`在自己的Windows Development server／client加掛唯讀`NativeReplicationProbe`。它觀察各程序真正收到的NGO變數；沒有測試RPC、姿態／武器注入、網路設定變更、GPU讀回或PCM錄音。普通啟動、Editor與Android不安裝。頭手仍為Simulation，不是頭盔追蹤或25台驗收。

```powershell
python scripts/check-desktop-capacity.py --replication-probe --api-dll artifacts/build-report-v1/bin/VrCommand.Api/release/VrCommand.Api.dll --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns"
```

預設仍先Linked、再五個獨立房，每模式25個client與60秒穩定期。明確的探針目錄必須全新、絕對路徑；helper放在本次SSD runtime的短目錄`replication/p001`等，名稱對照保存在本輪`replication-probes.json`，避免長admission名稱加上原子暫存檔超出Windows路徑限制，不修改系統設定。只由父程序新增`capture.request`整數及`finish.request`檔案，沒有控制遊戲內容的能力；不讀其他程序記憶體或原SQLite。不要公開本輪設定／票券，所有runtime與artifacts保持不提交。

探針每次看見本地Presentation tick／phase改變，記錄本地單調秒數、UTC、tick、玩家數／連線數／健康總和、Actors最小／最大tick及coherent。保留最早4096列、最多240秒，不環狀覆寫；穩定期不逐幀寫檔。64次有界明確capture可輸出完整本地玩家／敵軍Actors、avatar的playerId／connection／owner／PoseAccepted／來源／世界頭位置、天氣與phase。每個結果名稱唯一，寫完同目錄temp才move，不覆蓋歷史；格式使用明確可序列化DTO，不能直接把沒有Serializable的NGO struct當JSON證據。

五個檢查點為Running起點／60秒後、目標房Pause、Resume、AI傷害後全部Pause。每次先保存自己的API世界參考tick，再請各程序取本地快照；設定8秒重試視窗，仍受既有單次HTTP及capture等待逾時約束，不當作精確的整體wall-clock上限。每次失敗快照／原因保留、不覆寫，最多64輪。核對全玩家／敵軍唯一ID、房間、健康／彈藥、位置、敵軍fireSequence、avatar connection對應與正確本地owner、Simulated／accepted，及各Actor tick與當時Presentation一致、不得落後參考tick。浮點非有限值拒絕，位置容差0.02公尺。

起點與終點之間，每一張已記錄的本地tick列都須Ready／Running、全員connected與健康100、Actors時鐘一致，包含端點的本地新tick觀察間隔須小於原1.5秒界線。這是本地接收狀態／主迴圈觀察間隔，**不是packet RTT、單向網路延遲或逐封包送達率**。快照可比API參考tick新，靜止穩定期與AI後凍結才用於精確數值比較，不聲稱跨程序同一瞬間快照或每張世界幀都在每client顯示。

`Application.logMessageReceivedThreaded`只擷取`send queue full`的本地UTC／單調秒數與最後一次Update觀察到的phase／tick，最多4096列。worker callback不呼叫Unity物件API、不寫檔，結束先取消訂閱再一次保存report。快取phase／tick不是引擎內發送時點的原子狀態，也不是封包內容／計數器；錯誤行數不能當丟包數。

client在AI後暫停核對完成便明確finish，避免End後正常撤銷入場而來不及報告；**不驗每client收到Ended狀態**。server持續到End及精確seal完成才finish，以涵蓋結束階段日誌。報告完整、未截斷及上述全部檢查成立後才繼續回放／CSV／cleanup。原生程序仍由父程序持有並收尾，失敗保留結果；強制停止可能沒有完整探針report，不能補寫成完整。

`replication-checks.json`記錄每次capture的參考tick、本地tick、秒數及判定；原始完整快照和report在runtime內，全部writer退出後才一次複製回F snapshot。`localReplicaCheckpointsPassed`只代表本工具上述範圍，`networkCapacityAccepted`仍false。既有沒有probe的資料不能補造本地端證據；先前105行queue錯誤仍保留為未解問題，不因後續單次無錯誤稱修復。

0.28.3／code35新增`VenueTransportProfile`：在StartServer／StartHost／StartClient前，server／host的UnityTransport.MaxPacketQueueSize設為1024，client維持官方預設128。該設定同時控制driver各自的send／receive packet池，為全連線共用的每update容量，不是每peer；不改MTU、可靠視窗、timeout、模擬規則、權限、資料或OS設定。官方嵌入Transport修正與SHA仍保持。這是有界的伺服器突發保留空間，並非25台或任意敵軍／物件數的效能保證。

探針快照另讀本地packetQueueCapacity，並以真正Actors.WriteField寫到暫存記憶體取得actorListSerializedBytes；不清除dirty、不改集合、不發送這份診斷資料。檢查器核對server1024／client128。真正EditMode的30／125個GUID角色欄位分別4232／17627 bytes，已需要多封包；這只含Actor field，不含NGO／UTP封裝、其他變數、重傳或入場爆量，不能直接當網路實際頻寬或完整封包數。1024為候選保留配置，實際改善與限制須看本輪前後對照，不以設定值本身證明成功。

這還不涵蓋持續25玩家真實移動／射擊、顯示FPS／音效／使用手感、跨機／Wi-Fi、長任務、MR／頭盔或廠商硬體。診斷本身與capture檔案I/O可能改變時序，需搭配同版未啟用對照。每輪實際結果、失敗及二進位證據見[PROGRESS](PROGRESS.md)。
