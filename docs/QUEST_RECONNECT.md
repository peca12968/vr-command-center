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

## 保留遊戲程序並更新票券

從控制台重新下載同一場次、同一席位的玩家連線檔。透過 USB 偵錯選定 Quest 3，使用原部署工具的 `-RefreshPlayerTicket` 模式。

```powershell
$adb = 'F:/Tools/UnityEditors/6000.3.27f1/Editor/Data/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb.exe'
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 -RefreshPlayerTicket `
    -AdbPath $adb -Serial '<已授權 Quest 3 序號>' -ClientConfig .\new-player-ticket.json
```

工具私下讀取頭盔原設定，核對場次、玩家、入場識別、席位、伺服器位址與埠，並保留原透視和校正設定。MR 要使用同一鎖定校正值。工具只把票券更新到同資料夾的暫存檔，確認原檔及暫存檔的 SHA-256 後再替換。已經是同一票券時會回報 `ticket-file-current`。成功替換會回報 `ticket-file-refreshed`，原遊戲程序可接著處理 B 鍵重連。[Android ADB](https://developer.android.com/tools/adb) · [Android SHA-256 實作](https://android.googlesource.com/platform/external/toybox/+/40d21c59f76a9388b0ebb5c4c706732c2d034a67/toys/lsb/md5sum.c)

在已設定 `VR_COMMAND_MASTER_KEY` 的管理主機上，可加 `-ManagementApi http://127.0.0.1:5080` 使用管理包 0.31.199 的線上核對。遠端管理服務須使用 HTTPS。工具會驗證新票券簽章、當前入場、公告端點和有效的遊戲畫格。MR 會從頭盔讀取原鎖定校正檔送驗，替換前再核對管理狀態和頭盔上的校正雜湊。通過的回條包含 `managementVerified: true`。 [單席驗證方式](QUEST3.md#部署前核對單席連線檔)

若控制台已撤銷原席或重新建立入場，請走新的部署流程。重連時由遊戲伺服器驗證簽章、票券效期及當前入場，回到控制台確認有效參戰快照。USB 更新與頭盔按鍵仍需實機驗收。 [首次部署](QUEST3.md#區域網路原型操作)

新輸入不改頭手追蹤、原點、模型對位、槍口、Simulated恢復快取、命中或0.5／1.5秒政策。Client按鍵不持有控制台憑證；重新讀檔不能變成Host／Server，錯檔不發動StartClient。入場、結束戰績與桌面重連契約見[RECONNECT](RECONNECT.md)。

驗證範圍以[PROGRESS](PROGRESS.md)為準：純按鍵政策涵蓋角色／listening／shutdown／時間、按住／重按、焦點／追蹤中斷；官方Oculus Touch配置與真正InputAction在Editor Play Mode的Dynamic更新中核對右B、左Y與完整追蹤要求。虛擬測試裝置與state event只存在Editor測試，不在正式程式注入裝置、按鍵或姿態；測試臨時輸入設定會還原。這不是Quest控制器、頭盔視覺／舒適度、票券USB更新或實體網路證據。

仍需實機驗：有／無票券更新的斷線恢復、按住B跨失焦／追蹤中斷／冷卻、重複按鍵、被撤銷／Ended拒絕、原健康彈藥及Tracked姿態、等待面板可讀性；另驗跨機、MR與25台。沒有頭盔時不把APK成功或Editor虛擬事件改稱實機通過。

## Windows OpenXR 重連複驗

以支援 Vive 控制器右手 Menu 的測試 DLL 執行 Windows 玩家包整合命令，並加上 `--check-openxr-reconnect`。OpenXR 席先透過同機 UDP 轉送入場，桌面席維持原直連。測試關閉轉送，等原客戶端與伺服器都記錄斷線，再把同一入場的新票券和原伺服器端點寫入測試用連線檔。確認 Menu 按住及放開時都維持離線，重新按下後才由原程序讀檔建立新連線。封存核對原席位、姿態、健康、彈藥及新連線的戰績確認。測試 DLL 會讀回 Unity Mock Runtime 的右手 Vive 設定再確認按鍵。Quest 右手 B、USB 更新流程與頭盔輸入仍待實機驗收。 [測試 DLL 與命令](WINDOWS_PLAYER_PACKAGE.md#本機追蹤整合驗證) · [OpenXR 測試按鍵](https://registry.khronos.org/OpenXR/specs/1.1/man/html/xrSetInputDeviceStateBoolEXT.html)

準備中的撤銷測試使用 `--check-openxr-revocation`。主控撤銷原入場後，房控把同一玩家加回同一席，服務會分配新的入場識別碼。測試保留原連線檔，放開再按 Menu，確認遊戲伺服器拒絕舊票券。換成新票券並重新操作後，原玩家程序才恢復追蹤。桌面席維持原連線，封存回放保留撤銷和拒絕期間的狀態。任務結束後另由管理 API 核對新票券已失效。此選項與 UDP 中斷重連測試分開執行。

## 五房 UDP 中斷複驗

用同一個支援 Vive Menu 的測試 DLL 執行三個 Windows 可攜包。傳入 `--check-vr-venue-tickets --check-quest-vr-partial-map --check-venue-openxr --check-venue-openxr-reconnect` 及 `--openxr-mock-pose-dll`。獨立與合併模式各啟動 24 個桌面客戶端及第 5 房第 2 席的 Unity Mock Runtime 客戶端。

該席在任務中先射擊一次，再關閉自己的 UDP 轉送。房控為原入場發新票，測試只更新玩家程序讀取的副本。確認遊戲與伺服器均觀察到斷線，且持續按住及放開 Menu 都維持離線，再按一次才重連。核對健康、彈匣與備彈延續，封存時由最後一條連線確認戰績。其餘 24 席用各自的原錄製核對整段重連期間的有效姿態。此項為同一台 Windows 電腦上的模擬控制器測試。 [三包操作](WINDOWS_SERVER_PACKAGE.md#三個可攜包整合驗證)
