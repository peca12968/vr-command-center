# 任務計時的管理／發布失聯驗證

這是 [MISSION_CLOCK](MISSION_CLOCK.md) 的真正 PC 回歸。遊戲仍 API／UI0.28、Unity0.30.0／code37／NGO28；本輪新增 Python 故障工具與測試，未重建或重跑131項Editor／雙平台。必須先有相符的成功 Windows build receipt，不能以工具來源碼代替原生結果。本輪場次、數值與失敗紀錄見 PROGRESS。

管理快照、combat HTTP 與 world WebSocket 用途不同。工具只把自己新建的 Unity server 指向本機代理；操作員的觀察與命令仍直接到自己新建的 API。頭盔／client 的 NGO UDP 不經代理；不碰正式5080、既有世界、帳號、登入或安全設定。

管理失聯時，只對該 session 的管理 GET 回503，保留 combat及world發布。Unity 既有安全流程暫停世界、Ready=false，保存 suspended=true 的 Paused 幀；API管理狀態仍 Running，這不是操作員送出 Pause。工具用已接受世界幀與真正本地複本，多次核對 tick 相同及政策未重置。恢復 GET 後同一場次接續活動時間。

遊戲伺服器日誌以 `VR_AUTHORITY_SUSPENDED` 標示進入暫停時先觸發的路徑，包括管理更新失敗、管理更新逾時及封存錯誤。另以 `VR_MANAGEMENT_REFRESH_FAILED` 保存更新結果類型、HTTP 狀態及耗時，以 `VR_AUTHORITY_RESUMED` 保存恢復時的管理序號與場次狀態。這些記錄使用程序的單調時間，不含請求網址、憑證或回應內容。原有的 1.5 秒管理更新逾時規則仍適用。

加上 `--delay-management` 可測試管理 GET 尚未回應時的行為。代理暫留原請求，讓遊戲伺服器的 1.5 秒更新逾時計時器觸發暫停。釋放後將同一請求交給原管理服務處理。驗收要求暫停標記為 `ManagementWatchdog`、恢復沿用原管理序號，並核對封存回放、時鐘到期與原戰績回條。

五房獨立模式可再加 `--five-room-isolation`。五房各開五個 Windows 模擬玩家端，僅暫留第 1 房的原管理請求。依已接受畫格的擷取時間，確認其他四房在第 1 房時鐘暫停期間仍持續更新原席位的姿態與推進時鐘。遊戲暫停時原姿態可能因 0.5 秒時限失效，工具另用原生客戶端日誌確認每位玩家從入場到收到結果均沿用同一條 UDP 連線。五場到期後逐房核對原入場戰績回條及封存回放。這個選項固定使用 `--seconds 60`，適用於同機排演。

接近期限時，代理關閉自己既有 world tunnel，拒絕新的 publish upgrade，其他管理與 combat HTTP 正常。Unity計時繼續，恰好期限 tick 停止並 Ready=false；用既有 Windows Development `--vr-replication-probe` 分別觀察真正 server／client，**不讀取或破壞仍有 exclusive lease 的 journal**。後端的已接受序號保持不變且仍 Running，證明未發布的本地到期不能授權 End。

維持本地到期至少6秒後恢復 publication，原 world publisher 重連、原來源精確補送。API收到保存的到期幀後只能出現一次 mission-clock End；原 combat／world雙seal、結果ack與原入場／ledger核對均須通過。完整封存回放須逐幀連續、tick不倒退／不超過期限，保留管理失聯與到期等待兩個階段，末packet及統計與已保存世界相同。這不是世界進程崩潰恢復，也不保證指定某一個ACK曾經丟失。

## 代理範圍

`venue_http_gate.py` 只綁127.0.0.1，拒絕非plain loopback、正式5080、帶使用者資訊／路徑／query的upstream；由fixture從自己的新API建立，不是部署用代理或認證邊界。HTTP仍由API檢查GameServer認證，代理不製造Internal身分。

只允許自己場次的管理與戰績查詢、戰鬥資料與封存、原戰績確認回條、世界發布及入場票券驗證。HTTP 在記憶體轉送原內容及認證，不保存憑證或內容。WebSocket 轉送原始位元組。

最多8個處理連線，HTTP body1MiB、response2MiB，tunnel每塊最多64KiB、沒有無界排隊；每次故障最長20秒、代理最長240秒。自動上限觸發會記為失效證據，不能passed。HTTP處理執行緒為non-daemon，server_close等待其全部完成；listener／watchdog與自己的tunnel亦必須停止，所有writer全停後才一次複製runtime回F，原件不移動。兩類故障獨立，不以關掉整個API冒充分通道驗證。

## 執行

```powershell
$env:VR_COMMAND_API_DLL = "$PWD/artifacts/build-clock-v1/bin/VrCommand.Api/release/VrCommand.Api.dll"
python scripts/check-desktop-clock-faults.py --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns" --seconds 60
python scripts/check-desktop-clock-faults.py --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns" --seconds 60 --delay-management
python scripts/check-desktop-clock-faults.py --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns" --seconds 60 --delay-management --five-room-isolation
python scripts/check-desktop-clock-faults.py --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns" --seconds 180
python -m unittest discover -s tests -p test_venue_http_gate.py
```

每次測試建立自己的伺服器、模擬玩家、憑證與資料。來源標記為 Simulation。單房模式使用一個模擬玩家與原生探針，固定 240 秒、4,096 筆和 64 份快照，支援 60 或 180 秒任務。五房模式透過管理 API 讀回精確畫格，另核對原生伺服器及客戶端日誌。

`checks.json`只在代理停止、工具fingerprint未變、cleanup／snapshot成功後complete=true，內含原生複本快照、故障秒數、API未接受邊界、End證據、雙seal／玩家結果、整段回放與代理上限／錯誤計數。`--vr-replication-probe`僅觀察，不授權遊戲行為；finish.request須在正常斷線及固定期限前完成。任何工具失敗都保留自己的原件與cleanup結果，不改規則或丟掉舊資料重跑。

本頁範圍為 Windows 同機模擬及選定通道故障。跨機、25 位真人持續操作、封存中斷、整個 API 重啟、長任務、Quest／VIVE／MR 與廠商硬體須分別驗收。
