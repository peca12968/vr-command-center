# 任務結束前後的封包故障檢查

`scripts/check-desktop-end-race.py`啟動自己的API／兩個真正Windows Unity client／server，用一個有界loopback UDP gate改變其中一位玩家的下行傳遞；另一位直接連線作對照。世界來源維持Simulation，不注入姿態、武器、命中、RPC或管理事件。入場者由合法名冊及短效票券產生，GameServer key仍只在server。

這是既有Unity0.29.0／code36／NGO27、API UI0.27的回歸證據，不是新的遊戲協定或頭盔建置。最初假設End可能遺失剛批准玩家的結果，但第一個實驗收到正確結果；沒有據此更改遊戲端。

```powershell
$env:VR_COMMAND_API_DLL = 'F:\Projects\vr-command-center\artifacts\build-report-v1\bin\VrCommand.Api\release\VrCommand.Api.dll'
python scripts/check-desktop-end-race.py --runtime-root "$env:LOCALAPPDATA\VrCommand\SimulationRuns"
python scripts/check-desktop-end-race.py --runtime-root "$env:LOCALAPPDATA\VrCommand\SimulationRuns" --mode result-drop
python scripts/check-desktop-end-race.py --runtime-root "$env:LOCALAPPDATA\VrCommand\SimulationRuns" --mode result-large-drop
```

| 模式 | 真正故障條件 | 檢查 |
|---|---|---|
| join-delay | 伺服器記錄新的pending時開始暫存下行；已approved、client尚無CONNECTED log就End，精確seal後再延遲1秒（可設`--post-seal-delay 0..3`）釋放 | 原順序轉送後兩位各自收到自己的sealed結果並ack |
| result-drop | client先真正連線且接受DEBRIEF_PENDING，再丟棄其全部下行datagram | 伺服器結果期限或更早connection release，阻斷期間沒有final；正常peer仍有正確結果 |
| result-large-drop | 接受pending後丟棄大於64 bytes的下行datagram，其餘通過 | 在此取樣維持連線到應用層結果期限，出現DEBRIEF_TIMEOUT且阻斷期間沒有final |

64 bytes只是實驗的封包長度篩選，不辨識傳輸協定、keepalive或RPC內容，也不宣稱所有小包都只是心跳。若某場final提早通過，該實驗直接失敗。阻斷解除後若原已授權玩家收到遲來的結果，仍須逐值等於同一場／同一admission的雙seal；不把這種情況當成新入場。Ended的新連線及舊票券必須被拒絕且收不到任何debrief。

每場都先以真正AI造成對照玩家損耗，再End；兩位結果不能混用。檢查全部統計、來源、session／player／admission、combat stream最終序號、world序號。完整SSE回放必須從1連續走到seal，最後packet及statistics逐值等於保存世界；拒絕新票券後ledger不得改變。

Gate只綁127.0.0.1，目標是本次自己啟動的server port，固定第一個client endpoint，其他sender丟棄；不掃描／中繼外部網路。delay最多1024包／2 MiB，join hold最多8秒；drop不暫存payload、最多40秒，整個worker最多90秒。queue／hold自動上限觸發會使原生實驗無效；成功必須由檢查器明確release並確認thread停止、無錯誤。只保存數量／時間／長度篩選設定，不寫PCAP或payload到磁碟，不調整MTU、Unity timeout或安全設定。

每run保存game build receipt與四份實際執行Python來源的tool fingerprint，執行期間來源變動就拒絕passed。結果位於`artifacts/desktop-end-race/<run>/race-result.json`；只有所有原生條件、gate停止、自己的writer全停及snapshot成功後才complete。server-side deadline與觀察到的connection release分開，不從斷線log推斷未量測的傳輸根因。`holdSeconds`是gate開始作用到開始釋放的區間，不是每包延遲、RTT或FPS。

Runtime需明確指向新SSD目錄，source／binary仍F。全停writer後一次複製回F並保留原件；後續稽核只讀JSON／log／bytes，不開SQLite。失敗及舊檢查器過廣／過早的判定保留，不能改寫舊passed。

此為兩個同機、無圖形、桌面模式client。延遲者在End前可能沒有已接受的rig，不能把無CONNECTED log當成已證明avatar尚未spawn，或稱它已實際參戰。沒有25人／跨機／頭盔、GPU／PCM／網路效能及所有封包重排組合的驗收。最新實測與限制見PROGRESS；一般結果畫面見[DESKTOP_DEBRIEF](DESKTOP_DEBRIEF.md)。
