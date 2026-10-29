# 五房電腦場館

`scripts/start-desktop-venue.py` 在自己的 API／SQLite 上啟動五個獨立房間、五個真正 Windows Unity server 與每房一個真正 client。每房有不同任務、天氣／日夜、敵軍數量及沙包／油桶；預設只顯示房間 1 的可操作視窗，其餘合成玩家在背景運行。來源一律 **Simulation**，不是五台頭盔或 25 人效能測試。

從空任務庫開始、由控制台編輯並建立自己的任務，另見 [DESKTOP_CONTROL.md](DESKTOP_CONTROL.md)；本工具保留預先配置的五房及回歸模式。

先依 DESKTOP 建置目前 API 與 Desktop，再於專案根目錄執行：

```powershell
$venueData = Join-Path $env:LOCALAPPDATA 'VrCommand\SimulationRuns'
python scripts/start-desktop-venue.py --runtime-root $venueData --visible-room 1
# 全部無圖形：--visible-room 0；練習時間：--duration 60..1800
# 自動驗證獨立、房間重用及之後新開的 Linked 場：
python scripts/start-desktop-venue.py --check --runtime-root $venueData
```

本機 F 槽是 USB 硬碟，五房持續持久寫入時觀戰曾落後約 14 秒，未達原有 1.5 秒門檻；降低工作執行緒或移除場景物件都未解決。4 KiB 持久寫入的短測平均 F 槽 17.17 ms、C 槽 NVMe 1.75 ms，並非完整磁碟基準或效能保證。上述命令明確選用 SSD 保存本次全新隔離 SQLite／journal，程式碼與播放器仍在 F 槽，沒有關閉 durable flush、丟棄幀或放寬門檻。

`--runtime-root` 未指定時，資料仍位於 F 槽自己的 artifacts 目錄；工具不會暗中搬動正式資料。指定時會建立帶時間／識別的新目錄，拒絕覆寫既有目錄。全部自有寫入程序停止後，將完整 runtime 複製到 F 槽該次 `runtime-snapshot/`，保留 SSD 原件；不移動或刪除任何既有預覽資料。這是已驗證的 SSD 配置，不能宣稱 F 槽 USB 硬碟已通過五房新鮮度驗收。

每個 Unity 程序預設兩個 job worker，可用 `--job-workers 1..16` 明確指定並記錄；[Unity 官方參數說明](https://docs.unity.com/en-us/engine/6000.3/script-reference/unity/jobs/lowlevel/unsafe/jobsutility/jobworkermaximumcount)。此設定不是目前延遲修正的證據；同樣兩個 worker 的 F 槽試跑仍失敗。

## 主控與房間控制

啟動成功會顯示自己的控制台 URL。`artifacts/desktop-venue/<時間-識別>/keys.json` 有此次臨時 Master／Room1–Room5／GameServer 憑證；畫面與日誌不輸出值。主控使用 Master，各房使用自己的 RoomN；玩家設定只放短效票券。正式 5080 的憑證與資料不參與。

Master 可觀察全館；房間控制台僅能管理自房獨立任務。可透過現有控制台開始／暫停／繼續、調整天氣與 AI、觀戰及回放。初始敵軍為 Hold／不自動攻擊，需控制台開啟自動攻擊才進行戰鬥。可操作視窗的 WASD／方向鍵／Space／滑鼠／R 見 DESKTOP。

關閉可操作視窗、Ctrl+C、時間到，或在該次 artifacts 目錄建立空白 `end.request`，啟動器會 End 所有自有場次，等戰鬥及世界精確封存、核對回放／統計，再停止自有程序。若操作員先結束某房，封存會沿用已結束狀態；錯誤／不完整尾端保留 journal，不把未封存報表當完成。`cleanup.json` 記錄收尾及 runtime 快照錯誤。

五房要一起玩時，先明確結束並封存獨立場次，再由 Master 以一份任務建立新的 Linked 場，重加名冊與發新票券，使用一個權威遊戲 server。這不合併舊戰鬥世界、統計或回放；舊場各自保留。`--check` 會實際驗證這個流程，包含房間 1 結束／重用時其餘四房持續運行、房間仍占用時拒絕 Linked、舊票券與房間控制台越權拒絕。

`ready.json` 記錄自有 URL、room/session/UDP port 與 PID；`summary.json` 保存成功 build receipt、每場來源／封存／統計及最大取樣年齡。只在全部場次核對成功且活動數為 0 才寫成功結果；清理或快照失敗會非零退出。全部證據留在忽略的 artifacts，精確本輪數字與失敗見 PROGRESS。

目前證明的是同一台電腦上的五房、每房一個合成 client；跨機網路、五名滿房／25 台、GPU 聲光與完整控制台人工操作、Quest／VIVE、MR 及硬體仍須另外驗收。
