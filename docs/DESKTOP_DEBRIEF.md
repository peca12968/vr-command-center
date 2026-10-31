# 玩家任務結束戰績

背景 writer 的等待結果必須綁定已排入的 Ended 幀，不能用尚未完成寫入的 durable 前綴當任務終點；最終送出另核對精確 durable seal。0.36 長場反例與 0.36.1 修正見 [DEBRIEF_BOUNDARY](DEBRIEF_BOUNDARY.md)，不放寬原客戶端尾界檢查。

Unity 0.29.0／Android code36／NGO27；API／UI 0.27、驗票2、rules0.8.0及歷史錄製格式不變。所有遊戲程序須一起更新，Prepare 原位保存場景／prefab識別。

結束時的已批准入場延遲、pending後下行丟包與應用期限，另見[DESKTOP_END_NETWORK](DESKTOP_END_NETWORK.md)的真正PC故障檢查；既有版本在選定情境正確，沒有為此更改wire或重新建置。

End 後，原本仍在名冊且 admission／房間／座位相同的現有連線先解除遊戲綁定。畫面顯示等待封存，伺服器等 combat journal 及 world journal 都收到精確 seal，再以自己的 GameServer 身分讀取 statistics，僅向各自連線可靠傳送該玩家戰績。玩家端沒有新增 API／主控台憑證，不能查其他人的結果。

最終畫面包含彈藥數、命中數、擊殺、中彈、損耗、健康及兩位小數命中率，並標示 Simulation／GameServer。session、player、admission、stream及兩個最終序號固定；ledger序號不得倒退。玩家確認接收後伺服器斷線，畫面保留至重新連線或關閉程式。結果不是新的本機永久檔案；重新開啟後由控制者查伺服器既有報表／回放。

已移除／換席者仍立即斷線，不延後撤銷；Ended 不接受新的票券入場。等待結果上限30秒，若正在等最長5秒HTTP要求，斷線可再延至該要求返回；沒有最終結果只顯示未確認，不把本地HUD當封存戰績。連線失敗重試會清除舊結果，避免新場次顯示前次戰績。

PC顯示獨立於玩家avatar的結果面板；Android等候世界空間標籤也接入相同文字，但目前沒有頭盔操作／排版驗收。

一般`start-desktop-demo.py`及`start-desktop-control.py`也會先等結果ack／斷線，再保留可見結果視窗，`--results-seconds`預設30、可設0–300。關閉結果視窗或建立該run的`dismiss-results.request`可提早結束顯示。操作員工具以非阻塞期限保留舊場畫面；新同房可見玩家入場時優先開新遊戲，不讓舊結果占用唯一視窗。其他房間仍可操作；手動退出helper會結束剩餘保留畫面。報表封存和玩家收到結果分開記錄在`*-player-results.json`，空集合、關窗、未確認或逾時不當作送達成功。

## 原生驗證工具

先建置同源播放器，使用獨立API DLL及全新SSD runtime：

```powershell
$env:VR_COMMAND_API_DLL = 'F:\Projects\vr-command-center\artifacts\build-report-v1\bin\VrCommand.Api\release\VrCommand.Api.dll'
python scripts/check-desktop-debrief.py --runtime-root "$env:LOCALAPPDATA\VrCommand\SimulationRuns"
python scripts/check-desktop-debrief.py --runtime-root "$env:LOCALAPPDATA\VrCommand\SimulationRuns" --host
python scripts/check-desktop-debrief.py --runtime-root "$env:LOCALAPPDATA\VrCommand\SimulationRuns" --cancel-preparing
python scripts/check-desktop-debrief.py --runtime-root "$env:LOCALAPPDATA\VrCommand\SimulationRuns" --interactive --inspect-seconds 120
```

工具建立自己API／憑證／三位PC玩家，移除第三位後開場。一般模式以真正AI傷害產生戰績；interactive模式只開第一位GPU視窗，等待真正Space射擊後Pause／End，不使用輸入RPC或姿態注入。兩位接收結果須逐值等於sealed statistics及回放，ack後斷線；移除者和Ended舊票券不得收到結果。另比對combat及world的最終序號，拒絕後戰績不變。

`--host`改以第一位玩家兼任Host，驗其自身ack不會提前切斷peer；Host在兩位結束後shutdown，此模式不另外宣稱Ended票券拒絕（由dedicated模式驗證）。人工觀察可另存`visual-observation.json`，與4項程式檢查分開。真正結果與限制見PROGRESS最新一節。

`--cancel-preparing`在Begin前End，驗零事件串流。Unity把API JSON `origin:null`讀為空字串，僅已sealed、final combat sequence=0且全部玩家零事件／健康100時接受，來源仍取已綁定的stream，不補造combat origin。非零串流／其他玩家有事件的缺失來源仍拒絕。

`inspect-result`階段可查看保留畫面；建立本次資料夾的`inspected.done`結束等待。標記只結束人工檢視等待，不當作視覺驗收證據。完整結果在`artifacts/desktop-debrief/<run>/debrief-result.json`，只在cleanup及snapshot成功後`complete=true`。所有writer停止後才複製SSD資料回F，保留原件，不開啟舊資料庫、不覆蓋既有快照。正式5080預覽不受影響。

此工具檢查的是同機Windows UDP／NGO與Simulation來源；不是頭盔／跨機／25人容量、原生音訊、GPU效能或MR驗收。原生結果畫面須另以實際視窗觀察確認。
