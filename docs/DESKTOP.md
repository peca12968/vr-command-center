# 電腦練習場

2026-11-01 最新Unity0.37.1／code46／NGO29、API/UI0.30.1，新增[敵軍旋轉掩體繞路修正](AI_NAVIGATION.md)。保留既有軍服手臂、碰撞與戰鬥規則；189真正Editor／同源雙平台及原生巡邏／控制回歸成功。舊版本與GPU證據範圍保持，詳見PROGRESS。

2026-11-01 電腦玩家新增[自己的第一人稱軍服手臂](DESKTOP_FIRST_PERSON.md)，正常啟動即可看見袖子與換彈，不需開診斷。最新Unity0.37.0／code45／NGO29及API/UI0.30.1，184真正Editor、同源Windows／Quest建置；單玩家GPU／回放、遠端人物、Host戰績與五房流程回歸範圍見PROGRESS。以下各版本段落為歷史，不當最新版本號。

玩家端另可交付[Windows可攜玩家包](WINDOWS_PLAYER_PACKAGE.md)，解壓後用繁中啟動器選擇個別短票券連線檔；對應[外部玩家模式](EXTERNAL_CLIENTS.md)，不需要在玩家PC安裝Python或Editor。這不包含管理API／伺服器，實際跨機與GUI安全性提示處理仍另驗。

最新API/UI0.30、Unity0.32.0／code39／NGO29，144真正EditMode及同源雙平台成功；工具API gate同步0.30。新增[外部玩家流程](EXTERNAL_CLIENTS.md)可只開server並用控制台下載檔另行開PC，原練習場仍使用local模式。下文版本數字為歷史。

最新[玩家任務簡報](PLAYER_BRIEFING.md)可在遊戲內按B開啟／下一頁、Escape關閉、L查看字型授權。內容取自控制者保存並選定的任務，支援繁中及完整10000字分頁。閱讀不暫停全場，會抑制自己的射擊／換彈，關閉後須放開再按；仍可能受敵軍攻擊。Unity0.31.0／NGO29的全部遊戲程序須一起更新。

目前玩家End流程見[DESKTOP_DEBRIEF](DESKTOP_DEBRIEF.md)：Unity0.29／NGO27；雙seal後傳送自己的最終戰績、ack斷線保留。`--results-seconds`預設30（0–300），可關窗或以`dismiss-results.request`提早結束；新任務玩家可取代舊結果視窗。最新建置／125 EditMode與原生驗證以PROGRESS為準，下文版本數字為功能首輪歷史。

在 Windows 不接頭盔操作同一份 Unity 遊戲接入。這是桌面合成頭手的 **Simulation**，不代表 Quest／VIVE 或正式軍事美術驗收。

要從控制台自行編輯／保存／選取任務並啟動真正 PC，見 [DESKTOP_CONTROL.md](DESKTOP_CONTROL.md)。本頁保留固定練習任務。

五房同時獨立的啟動、房間重用與之後新開 Linked 的驗證見 [DESKTOP_VENUE.md](DESKTOP_VENUE.md)；本機五房即時 SQLite／journal 已使用明確指定的 SSD runtime，程式碼及建置仍在 F 槽。

先依 QUEST3／NATIVE_VALIDATION 建置 Desktop。API 使用隔離輸出，避免既有服務鎖住 DLL，再於專案根目錄執行：

```powershell
dotnet restore VrCommand.slnx --locked-mode --artifacts-path artifacts/build-practice
dotnet build VrCommand.slnx --configuration Release --no-restore --artifacts-path artifacts/build-practice
python scripts/start-desktop-demo.py --api-dll artifacts/build-practice/bin/VrCommand.Api/release/VrCommand.Api.dll --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns"
# 指定隔離 API 建置，例如：
# --api-dll artifacts/build-unity-first/bin/VrCommand.Api/release/VrCommand.Api.dll
# --enemies 1 --peers 1 --duration 900
```

啟動器共用五房 Venue 的來源 fingerprint、官方嵌入 Transport 檢查與 API **0.27.0** 版本 gate，場次建立前即拒絕過期 receipt／API，不只看檔案存在。目前Unity為同源0.28.1／NGO26，新選用診斷見[POSE_TIMING](POSE_TIMING.md)，一般練習不啟用；入口修復當輪為0.28且當輪未重建遊戲端。舊啟動器實際仍要求0.21，已確認無法啟動目前API並修復，不要改回舊reader來配合。

上例明確將全新 SQLite／journal runtime 放在本機 SSD；此機為 C 槽，來源、API、遊戲 binary、設定與最終檔案仍在 F。writer 全停後複製一份 runtime-snapshot 回本輪 F 目錄，保留原件，不搬動既有歷史。省略 `--runtime-root` 仍全部放 F，但 F USB 全資料的既有量測未達1.5秒門檻；本工具照原擷取UTC門檻失敗並保留資料，不偷偷放寬。`--job-workers` 預設2，不代表減少worker已修復F延遲或歷史偶發姿態原因。

啟動器建立自己的本機 API、任務與房間 5，啟動一個無圖形 Unity server、一個可操作玩家視窗，以及預設一個無圖形同伴。敵軍預設 Hold／不自動開火，環境 Clear／Day，含沙包與油桶；方便驗證玩家輸入。`--peers 0..4` 控制同伴數，總共最多5個不同admission的客戶端，設定與程序名稱不互相覆蓋。`--enemies 0..12` 控制敵軍，`--duration 60..1800` 為練習啟動後的wall-clock秒數上限，包含Pause，不是正式任務的扣暫停倒數。這不是五台／25 台或跨機效能量測。

| 操作 | 輸入 |
|---|---|
| 平面移動 | WASD，依目前朝向前進，斜走不加速 |
| 瞄準 | 按住右鍵拖曳，或方向鍵；上下最多 70 度；方向鍵短按 3 度 |
| 射擊 | 左鍵或空白鍵，仍由伺服器判定射速／彈藥／射線 |
| 換彈 | R |
| 結束 | 關閉玩家視窗、終端 Ctrl+C，或等待練習時間結束 |

也可從該次隔離控制台送 End，或在該次目錄建立空白 `end.request`。正常關窗會移除已停止的玩家handle，先送End並退場自有客戶端，再只等自己的server／API精確seal；不因已關閉的玩家被live-child fence誤判而中斷收尾。非預期背景程序失敗仍為非零結果，不能稱為完成。

HUD 顯示階段、房間、血量、彈匣／備彈、換彈及連線／姿態異常。桌面準星由手部槍口及收到的場景幾何預測投影，只是瞄準參考，沒有授予客戶端命中或傷害權限；網路延遲、物件移動可能讓預覽與伺服器判定不同。合成頭手與真正 Tracked 輸入分開；頭盔保留原 OpenXR／world-space HUD。

v0.17 新增斷線後 **Reconnect / reload player ticket**，可在玩家程序仍存在時重讀原檔案的有效短效票券。撤銷／過期須由控制台重新配票；同次 admission 重啟可恢復已接受的合成姿態與原健康／彈藥。詳見 [RECONNECT.md](RECONNECT.md)。練習啟動器會在玩家視窗關閉後結束場次，專門的強制斷線／重連驗證請使用該文件的檢查器。

短按也會讀取按下事件；視窗系統按鍵與 InputSystem 原始裝置輸入合併，讓輔助鍵盤仍能操作，避免同一按鍵重複執行。原始鍵盤／右鍵拖曳的完整組合與手感仍待人工驗收。

v0.18 桌面移動依同房間伺服器幾何預先裁切，不再持續將相機推進掩體而失去參戰資格。沙包、旋轉油桶、退回與側移已用真正鍵盤驗證；共用規則、重現操作及限制見 [DESKTOP_COLLISION.md](DESKTOP_COLLISION.md)。長幀位移／房間界線與伺服器姿態審核保留，Tracked XR 不被此功能搬動。

自己的 API 埠、場次、播放器 receipt／程序 ID 與記錄在 `artifacts/desktop-demo/<時間-識別>/ready.json`；最新路徑在 `artifacts/latest-desktop-demo-path.txt`。啟動後會顯示隔離控制台 URL；若需操作該控制台，僅使用該目錄 `keys.json` 的臨時 Master 值。不要使用正式預覽憑證，也不要把 keys、server／client 設定或票券加入 Git／貼出。頭盔／玩家檔仍只有短效票券，GameServer key 只在伺服器。

結束時向自己的 API 送 End，等待戰鬥／世界精確封存，核對回放末幀與ledger統計，另經授權API取得[最終CSV](REPORTS.md)並以標準csv／Decimal逐玩家核對後保存 `final-report.csv`。`summary.json`保留原頂層world／statistics／replayStatisticsMatch，新增stopReason、runtimeDirectory、jobWorkersPerProcess及finalReport SHA／玩家數；`cleanup.json`另記錄收尾錯誤／剩餘程序。只有成功封存才有完成摘要，cleanup／snapshot失敗仍非零退出；原5080預覽服務與歷史保持。若API／server意外退出或封存失敗，保留journal，不把未封存報表當完成。

## Windows 原生驗證

```powershell
python scripts/check-desktop-practice.py --api-dll artifacts/build-practice/bin/VrCommand.Api/release/VrCommand.Api.dll --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns"
# 需要實際操作練習場視窗：W、一次Space、R完成後，等close階段再關窗。
python scripts/check-desktop-practice.py --interactive --api-dll artifacts/build-practice/bin/VrCommand.Api/release/VrCommand.Api.dll --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns"
```

預設檢查啟動真正無圖形server／client，分別測同房五client＋控制台End、單client＋end.request及雙client＋60秒到時；各含Pause／Resume、精確seal、CSV／ledger、無殘留程序及SSD snapshot核對。`--interactive`開雙client中的一個真正視窗，只觀察接受的移動／耗彈／換彈，沒有RPC、姿態或武器注入。啟動器的`--headless`只供這類無人值守診斷，沒有GPU／人工操作證據。Linux CI僅編譯Python語法，不能稱這些Windows流程已跑。

本輪27項無圖形／9項真正視窗流程與3項preflight反例通過；實際結果、POSE STREAM STALE樣本與仍待項目見PROGRESS。來源皆Simulation，沒有頭盔或跨機驗收。

本輪實際圖形／輸入結果與限制見 [PROGRESS.md](PROGRESS.md)，連線無圖形回歸見 [NATIVE_VALIDATION.md](NATIVE_VALIDATION.md)。沒有頭盔、MR、25 人或正式場館性能證據。
