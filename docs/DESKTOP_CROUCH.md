# 電腦端蹲姿與掩體

Unity **0.39.0／Android code49／NGO29**，API/UI0.30.2。電腦玩家按住左／右 Ctrl 蹲下，放開站起；也可用 C 切換蹲姿。兩個 Ctrl 分別釋放，C 的按鍵重複不連續切換；Ctrl 按住期間優先保持蹲姿。HUD 的 STANCE 取自伺服器接受的人物位置與參戰狀態，不把尚未確認的本機輸入顯示成已接受姿態。

只有無頭盔的本機 owner 使用此輸入：原眼高1.65m改為1.0m，左右手及槍口沿用原相對位置和旋轉；WASD保留目前高度、原速度及房間／掩體移動限制。伺服器仍用既有Pose、射線和掩體規則判定參戰與傷害，未新增蹲姿wire欄位、任務／世界header、素材profile或修改0.5／1.5秒政策。Tracked頭手不被搬動，其他玩家仍由各自的Pose決定。

失焦、應用暫停／恢復或停用時，立即清除本機按住／切換／待處理輸入並恢復站立；不依賴背景仍有Update。回到視窗後須重新按C或Ctrl才蹲下，下一次原Pose發送才會更新伺服器。若視窗最小化導致姿態超時，參戰狀態仍按原政策失效，不由此功能放行。

既有player-body-v1輪廓會隨頭高縮放；目前沒有新增屈膝、趴下或完整骨架動畫。這是PC合成姿態，不能當成頭盔實際蹲姿、MR定位或跨機25人驗收。

## 驗證方法

16項新增Editor案例涵蓋雙Ctrl、C重複／兩輸入來源去重、失焦及生命週期、移動／房界和極端俯仰的原槍口限制。3項使用官方InputSystem虛擬Keyboard，在真正Editor PlayMode的Dynamic更新消費Ctrl按住／放開與C事件；不以測試手動InputSystem.Update冒充玩家更新。測試暫時把Editor鍵盤事件導向GameView，finally恢復原Editor routing／background設定並移除自己建立的裝置；正式InputSettings不改。

第一次真正224項測試為218成功／6失敗：EditMode的SendMessage遭引擎拒絕，另3項鍵盤值未送到GameView。改用直接呼叫callback邏輯後第二次為221／3；實際診斷Keyboard仍為0。依已安裝InputSystem的Editor routing行為修正測試設定後，第三次**224成功／0失敗／0 skip**。兩次失敗的XML／log／選定來源先另存並保留，不改判成功。

```powershell
python scripts/check-desktop-crouch.py --api-dll <既有0.30.2隔離API.dll> --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns"
```

工具啟動自己的Windows server、一名可操作玩家及一名headless同伴。房3原席位與原Hold NPC出生點、一個油桶均由正常任務及入場流程產生，不注入Pose、射擊或命中。實際C／W與最小化／恢復視窗後，必須先觀看HUD再寫各stage的review；review僅表示已觀察，來源幀還須符合原位置、健康、彈藥和有效Simulated條件才繼續。

蹲下的主玩家在油桶後維持100健康至少44活動tick，同期間須保存至少兩次敵軍向站立同伴開火，避免把敵軍未射擊當成掩體成功。站起後須恰好一次20傷害，工具經正常管理命令關閉AutoAttack；後續蹲姿移動不改同伴位置／高度／彈藥。焦點測試先用明確Pause命令，只有該接受序號至Resume前的Paused幀可記為有意的暫停失效，所有Running幀仍須有效，恢復後有效站立才Resume。

正常End後核對兩份原admission結果、CSV、戰鬥／世界精確seal、兩個原連線唯一server ACK和完整SSE回放；事件／世界序號不能缺失，保存checkpoint須相同，原Hold NPC／名冊／同伴和兩種合法高度逐幀核對。所有writer停止、cleanup成功後才一次snapshot及complete。五helper雜湊只涵蓋列出的檔案，不是完整runtime／OS graph；不開啟保存SQLite。

真正Windows本輪6項、792完整回放／739來源幀及11保存參考、兩份原戰績與CSV／雙seal／兩個唯一ACK成功；同源五房6項7場及新包19項核對成功。原生使用實際C／W與視窗最小化恢復，Ctrl持續按住／放開只在上述Editor官方Keyboard驗證。本場明確Paused內的參戰失效幀為0，沒有由排除條件補造成功。

[精確914051c的CI](https://github.com/peca12968/vr-command-center/actions/runs/41325529518)完整738規則／459 HTTP／47 world、Python／素材、78 Node／256 Chromium通過，2 Windows skip非Editor／原生。首c78 CI的camera-save逾時與新fixture診斷分開保存，成功新場不當原失敗根因證明；遊戲來源e0d60e4e...與224雙平台保持，fixture後未重建。實際各場、包雜湊與限制見[開發進度](PROGRESS.md)。原31筆參戰失效、world371、Windows startup與F吞吐問題保持待查。
