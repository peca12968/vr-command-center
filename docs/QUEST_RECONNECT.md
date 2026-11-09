# Quest控制器重連

遊戲 0.48.1 會同時核對應用程式與 OpenXR 工作階段的焦點。系統選單關閉或程式恢復後，回到遊戲並放開右手 B，再按一次才能重連。 [頭盔焦點與輸入](QUEST3.md#追蹤恢復後的武器輸入)

Unity0.34.0／Android code41加入右手B鍵重連入口，NGO29、API/UI0.30與原驗票protocol2保持。它使用與桌面Reconnect按鈕相同的`ReconnectClient`，重新讀取原玩家檔案，再由GameServer驗票；不是自動配票、名冊變更、世界恢復或繞過舊admission fence。

原Android略過桌面OnGUI，所以斷線後沒有該按鈕。現在Client在OpenXR／Android啟動時保留獨立的右手secondaryButton輸入，即使玩家avatar已移除，等待畫面仍可處理。Quest對應右手B，不使用系統Menu按鈕；左手Y不是此綁定。VIVE型號及對應按鍵仍待確認。

操作順序：

1. 斷線後等待NGO停止listening及shutdown；等待畫面只有在可重試時顯示`RELEASE THEN PRESS RIGHT B TO RELOAD PLAYER TICKET`。
2. 若票券仍有效且名冊未撤銷，可以重用；過期時先請有權控制台為同一玩家／本次admission配發新票券，更新頭盔的原`vr-connection.json`。
3. 回到程式並恢復右控制器完整追蹤，放開B，再按一次。只有Client可嘗試，沿用兩秒間隔；一直按住不會自動重連。
4. 連線中、shutdown、冷卻、失焦或控制器追蹤缺失會解除按鍵準備狀態；恢復後必須再次實際放開再按。未重按不會清除原戰績或重新讀檔。

焦點失去、程式暫停及bootstrap停用的Unity回呼也會明確解除準備；不依賴暫停期間仍有Update執行。

首次安裝仍使用[QUEST3](QUEST3.md)的deploy工具。要在**不關閉現有程式**時更新票券，可將控制台下載的四欄Client檔推送到同一app目錄的暫存檔，確認push成功後才改成正式檔；下列步驟尚待Quest實機驗證，不執行install或force-stop：

```powershell
$adb = 'F:/Tools/UnityEditors/6000.3.27f1/Editor/Data/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb.exe'
& $adb -s '<已授權Quest3序號>' push '<自己的新玩家檔.json>' /sdcard/Android/data/com.vrcommand.quest/files/vr-connection.next.json
if ($LASTEXITCODE -ne 0) { throw 'Player file push failed; keep the current file.' }
& $adb -s '<已授權Quest3序號>' shell mv -f /sdcard/Android/data/com.vrcommand.quest/files/vr-connection.next.json /sdcard/Android/data/com.vrcommand.quest/files/vr-connection.json
if ($LASTEXITCODE -ne 0) { throw 'Player file replacement failed; inspect the device.' }
```

只配置role／address／port／joinTicket；不得將主控或GameServer key送到頭盔。不在票券更新工具中讀出或回傳票券內容；實際簽章、效期、room／seat、撤銷及本次admission仍由原伺服器處理。修改檔案不表示已入場，確認有效姿態仍用控制台readiness。

新輸入不改頭手追蹤、原點、模型對位、槍口、Simulated恢復快取、命中或0.5／1.5秒政策。Client按鍵不持有控制台憑證；重新讀檔不能變成Host／Server，錯檔不發動StartClient。入場、結束戰績與桌面重連契約見[RECONNECT](RECONNECT.md)。

驗證範圍以[PROGRESS](PROGRESS.md)為準：純按鍵政策涵蓋角色／listening／shutdown／時間、按住／重按、焦點／追蹤中斷；官方Oculus Touch配置與真正InputAction在Editor Play Mode的Dynamic更新中核對右B、左Y與完整追蹤要求。虛擬測試裝置與state event只存在Editor測試，不在正式程式注入裝置、按鍵或姿態；測試臨時輸入設定會還原。這不是Quest控制器、頭盔視覺／舒適度、票券USB更新或實體網路證據。

仍需實機驗：有／無票券更新的斷線恢復、按住B跨失焦／追蹤中斷／冷卻、重複按鍵、被撤銷／Ended拒絕、原健康彈藥及Tracked姿態、等待面板可讀性；另驗跨機、MR與25台。沒有頭盔時不把APK成功或Editor虛擬事件改稱實機通過。
