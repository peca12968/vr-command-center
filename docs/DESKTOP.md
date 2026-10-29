# 電腦練習場

在 Windows 不接頭盔操作同一份 Unity 遊戲接入。這是桌面合成頭手的 **Simulation**，不代表 Quest／VIVE 或正式軍事美術驗收。

要從控制台自行編輯／保存／選取任務並啟動真正 PC，見 [DESKTOP_CONTROL.md](DESKTOP_CONTROL.md)。本頁保留固定練習任務。

五房同時獨立的啟動、房間重用與之後新開 Linked 的驗證見 [DESKTOP_VENUE.md](DESKTOP_VENUE.md)；本機五房即時 SQLite／journal 已使用明確指定的 SSD runtime，程式碼及建置仍在 F 槽。

先依 QUEST3／NATIVE_VALIDATION 建置 API 與 Desktop，再於專案根目錄執行：

```powershell
dotnet restore VrCommand.slnx --locked-mode
dotnet build VrCommand.slnx --configuration Release --no-restore
python scripts/start-desktop-demo.py
# 指定隔離 API 建置，例如：
# --api-dll artifacts/build-unity-first/bin/VrCommand.Api/release/VrCommand.Api.dll
# --enemies 1 --peers 1 --duration 900
```

啟動器會在建立場次前檢查 API 0.16.0，舊 DLL 會立即提示重新建置；不能只憑檔案存在就當作同版。上方 .NET 建置可更新一般 Release 輸出；若 API 正在鎖住該輸出，改用 SIMULATION 的隔離建置並指定 `--api-dll`，不要為了示範停止既有服務。

啟動器建立自己的本機 API、任務與房間 5，啟動一個無圖形 Unity server、一個可操作玩家視窗，以及預設一個無圖形同伴。敵軍預設 Hold／不自動開火，環境 Clear／Day，含沙包與油桶；方便驗證玩家輸入。`--peers 0..4` 控制同伴數，`--enemies 0..12` 控制敵軍，`--duration 60..1800` 控制練習秒數。這不是五台／25 台效能量測或正式部署。

| 操作 | 輸入 |
|---|---|
| 平面移動 | WASD，依目前朝向前進，斜走不加速 |
| 瞄準 | 按住右鍵拖曳，或方向鍵；上下最多 70 度；方向鍵短按 3 度 |
| 射擊 | 左鍵或空白鍵，仍由伺服器判定射速／彈藥／射線 |
| 換彈 | R |
| 結束 | 關閉玩家視窗、終端 Ctrl+C，或等待練習時間結束 |

HUD 顯示階段、房間、血量、彈匣／備彈、換彈及連線／姿態異常。桌面準星由手部槍口及收到的場景幾何預測投影，只是瞄準參考，沒有授予客戶端命中或傷害權限；網路延遲、物件移動可能讓預覽與伺服器判定不同。合成頭手與真正 Tracked 輸入分開；頭盔保留原 OpenXR／world-space HUD。

v0.17 新增斷線後 **Reconnect / reload player ticket**，可在玩家程序仍存在時重讀原檔案的有效短效票券。撤銷／過期須由控制台重新配票；同次 admission 重啟可恢復已接受的合成姿態與原健康／彈藥。詳見 [RECONNECT.md](RECONNECT.md)。練習啟動器會在玩家視窗關閉後結束場次，專門的強制斷線／重連驗證請使用該文件的檢查器。

短按也會讀取按下事件；視窗系統按鍵與 InputSystem 原始裝置輸入合併，讓輔助鍵盤仍能操作，避免同一按鍵重複執行。原始鍵盤／右鍵拖曳的完整組合與手感仍待人工驗收。

移動依房間邊界限制，而不是依各出生席位的根物件限制；長幀不會直接大幅跳位。掩體碰撞仍由共用權威核心拒絕，未通過姿態時須退回有效位置，這不是完整的客戶端碰撞／移動預測。

自己的 API 埠、場次、播放器 receipt／程序 ID 與記錄在 `artifacts/desktop-demo/<時間-識別>/ready.json`；最新路徑在 `artifacts/latest-desktop-demo-path.txt`。啟動後會顯示隔離控制台 URL；若需操作該控制台，僅使用該目錄 `keys.json` 的臨時 Master 值。不要使用正式預覽憑證，也不要把 keys、server／client 設定或票券加入 Git／貼出。頭盔／玩家檔仍只有短效票券，GameServer key 只在伺服器。

結束時向自己的 API 送 End，等待戰鬥／世界精確封存，核對回放末幀與報表統計後保存 `summary.json`，再停止自己啟動的程序；原預覽服務、資料與其他應用保持。若 API／server 意外退出或封存失敗，保留 journal 並回報錯誤，不把未封存報表當成完成。

本輪實際圖形／輸入結果與限制見 [PROGRESS.md](PROGRESS.md)，連線無圖形回歸見 [NATIVE_VALIDATION.md](NATIVE_VALIDATION.md)。沒有頭盔、MR、25 人或正式場館性能證據。
