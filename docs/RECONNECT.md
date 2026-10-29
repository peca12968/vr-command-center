# 桌面重連與入場識別

Unity 遊戲端 v0.18.1／Android code19／NGO protocol18；管理 API 仍為 0.16.0、驗票 protocol 2，場次 envelope 6／世界 schema 1 不變。更新所有遊戲伺服器與玩家程式，不混用 NGO 16／17／18。Prepare 會在既有 Arena 上將設定 16／17 升為 18，保留 scene／PlayerAvatar 的 GUID、本地 file ID 及 NGO hash；不分平台重建場景。

## 玩家操作

桌面 Client 斷線後，等候 NGO 完成關閉，會出現 **Reconnect / reload player ticket**。點擊後重新讀取原 `--vr-config` 指定的玩家檔，使用其中的位址／UDP 埠與短效票券連線；兩次嘗試至少相隔兩秒。只允許 Client 重新連線，不能透過重讀檔案變成 Host／Server。

同一次 admission 的有效票券可重用；票券過期或操作員移除後，須由控制台重新發票，更新玩家檔再點擊。玩家檔只放玩家票券，不能放 Master／GameServer key。介面不會自行向管理 API 配票，也不會自動繞過被撤銷的入場。

強制結束程序或網路中斷時，最後姿態超過 0.5 秒會失去參戰資格，但這不等於 UDP 連線已釋放。同一玩家仍只允許一條已綁定連線；必須等真正的傳輸斷線回呼後才能重新綁定。UTP 目前的 inactivity timeout 為 30 秒，這是設定值，不能當成任何網路條件下的斷線時間保證。桌面端明確允許背景更新；只有取得焦點的可操作視窗讀取鍵鼠輸入。

## 桌面姿態恢復

既有戰鬥世界保留健康、彈藥與位置。新桌面玩家物件若直接從出生點送姿態，走遠後會被既有防瞬移規則拒絕。因此伺服器僅保存**已接受的 Simulated 姿態**，以 playerId＋admissionId 綁定；斷線不刪除同次 admission 的恢復姿態，名冊移除或 admission 改變即清除。

新玩家物件透過既有 AvatarPose NetworkVariable 取得伺服器的初始姿態，桌面端完成初始化後才發送自己的輸入。位置仍須再次通過權威核心，沒有重設健康／彈藥、放寬瞬移、直接寫入命中或測試 RPC。收到 Tracked 姿態時清除桌面恢復快取；XR 客戶端仍以實際裝置追蹤為準，不能把桌面快取冒充 Tracked。

恢復快取只存在於該遊戲伺服器程序，並非持久世界恢復。伺服器重啟、MR 校正、實際 Quest／VIVE 追蹤、裝置更換及 Host 撤銷仍須分別驗收。

## 驗證

建置目前 API 及 Windows player 後：

```powershell
python scripts/check-unity-admission.py
python scripts/check-unity-admission.py --interactive
```

檢查器會核對播放器 receipt 與目前來源指紋，建立自己的隔離 API／資料／憑證。一個真正 Windows Unity server 及兩個 Client 驗證重複票券拒絕、移除／同 ID 新 admission、舊配位移除與票券拒絕、舊程序退出不移除新綁定、同次 admission 的斷線重連，以及 End 封存與回放統計一致。

互動模式的 `stage.json` 會依序提示：重新配票後點 Reconnect、Running 時射擊一次、Paused 後前進至少 0.64 公尺。檢查器觀察已錄製的權威世界，再強制結束玩家程序、等真正傳輸釋放並重新啟動同次 admission 的玩家，核對位置、健康與彈藥。它不注入姿態或戰鬥事件；沒有輸入時不會假裝這些步驟完成。重新連線前由自己的控制台重發同 admission 的短效票券，避免人工操作時間耗盡票券。

原生日誌只記錄連線狀態／transport client ID，不記錄票券或密鑰。所有私密設定、日誌、stage、前後快照與 summary 留在忽略的 `artifacts/unity-admission/`；最新路徑在 `artifacts/latest-unity-admission-path.txt`。已通過無圖形及真正視窗八項檢查；視窗場走離出生點 0.65 公尺，強制離線後恢復相同位置與 60／29／90 的健康／彈匣／備彈，封存 1648 幀且回放統計一致。實際通過、失敗與範圍以 [PROGRESS.md](PROGRESS.md) 為準。
