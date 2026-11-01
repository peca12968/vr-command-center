# Windows 遊戲伺服器包

可搭配API0.31.0／控制台0.31.1的[任務收尾](SESSION_CLOSURE.md)顯示雙封存與保留已確認End；原server v3 runtime／SHA保持，不需要因這個唯讀UI更新Unity或頭盔。

`Launch-Server.exe`將既有Unity Windows播放器以獨立Server模式啟動。操作員只需Windows x64與.NET Framework4.8，不需要Python、Unity Editor或.NET SDK。管理網站用[管理服務包](WINDOWS_CONTROL_PACKAGE.md)，玩家使用[玩家包](WINDOWS_PLAYER_PACKAGE.md)，三者分開運行。

本輪PC原型主包為`artifacts/server-packages/windows-server-0.39.0-v3-win-x64.zip`，**82,664,818 bytes**、SHA256 **`6cecfbeeffba1277000f93bc168c4ac387b825c34b73142628098dba28f67500`**，311個manifest檔案／ZIP312含manifest。v1、v2候選原件保留。沿用Unity **0.39.0／code49／NGO29／e0d60e4ed6cefe5cd885e6aabe1621939da945ce00d56b3ed8820c0aed4db879**，API/UI仍0.31.0，沒有修改Unity來源、重建Editor／APK或更新原場景／prefab ID。

## 操作流程與目前限制

1. 完整解壓管理、伺服器及玩家包。先開管理服務，在網頁控制台建立Preparing VR場次。
2. 開`Launch-Server.exe`，選管理服務原資料夾內的`control-instance.json`，選尚未綁定來源的場次，明確填寫公告IPv4、本機綁定IPv4及UDP埠。預設127.0.0.1只供同機；固定綁定地址須已配置於本機且與公告地址相同，或明確選0.0.0.0綁定。
3. 五個Independent場次各開一個啟動器，使用不同UDP埠；五房Linked場次只需一個。新增場次後重選管理實例可更新列表。
4. 伺服器就緒後，由控制台下載每位玩家的短效連線檔，交給玩家包，再在控制台Begin。此啟動器不領取玩家票券、不建立／改變名冊或代替操作員下Begin／End。
5. 在控制台End後，等待戰鬥與世界雙封存，保留36秒供原玩家接收戰績，再停止自己的Unity程序。這是封存後的OS程序終止，**不是Unity正常退出證明，也不能單憑36秒推定所有玩家已收到戰績**。原始journal與玩家／server回條另驗。

**本輪103項Windows CLI／原生整合通過；新GUI完整選檔／啟動流程未完成驗證。** native視窗可見且欄位／標籤正確，但兩次點擊均被非目標`PickerHost.exe`攔住；activate並重新觀察後的一次重試仍回報`point ... is over PickerHost.exe, not target window Launch-Server.exe`，因此停止UI輸入。自己GUI與API已終止，failed、原snapshot及有限觀察保留。這不是產品選檔成功、Windows安全性或PickerHost根因證明。管理服務包原先已成功的GUI95151不替代本輪伺服器GUI。

目前只接受沒有combatStream的Preparing VR場次；不接管Running、MR或舊journal，不做崩潰後重建世界。管理請求失敗、來源改變、就緒90秒逾時或End後30秒未雙封存，均停止自己的子程序並保留不完整結果，不能當正常完成。GUI「中止」也不自動End管理場次。資料預設`%LOCALAPPDATA%/VrCommand/GameServers`，結果在`GameServerReports`；資料內含GameServer私鑰，不能放回共用ZIP。僅在所有writer真正終止後備份。

## 啟動、來源與停止界線

啟動器核對manifest逐檔大小／SHA與完整檔案集合、拒絕連結／越界／額外檔案；清單不是數位簽章。只接受GameServer角色，Unity設定只帶這個key，不帶Master。GUI讀既有管理實例的JSON，不新增或複製角色金鑰。遠端管理可由CLI的私人七欄JSON明確指定；尚無LAN、TLS或乾淨新機驗證。

每輪使用新的包外資料夾／log，核對Preparing、VR與無既有stream，並取得以API地址／場次命名的本機mutex。UDP探查只做啟動前衝突拒絕，不拿埠可開當成就緒；釋放探查與Unity綁定之間仍有競爭，後續必須有真正遊戲啟動紀錄。

Unity原bootstrap會先核對自己combat stream的UUID／origin／接受序號／未seal，再StartServer並寫`VR_NETWORK_STARTED ... started=True ... port=...`。啟動器只讀自己新log的這個紀錄，再核對API的同場次GameServer來源／Simulation／world header，才以原GameServer owner PUT不可變connection-endpoint，核對回條場次／stream／IPv4／port。這條既有程式順序是來源的證據鏈，沒有讀取被原writer獨佔的live journal，也不等於玩家即時pose健康或LAN可達。

Windows子程序以suspended建立，先加入私人kill-on-close Job，再Resume，原生OS handle保留至實際退出。只設定KILL_ON_JOB_CLOSE，沒有改優先序、CPU／記憶體限制或系統設定。已加入Job的父程序被終止後，原Unity handle實際退出；這不是斷電恢復、未落盤queue保障，或建立程序到指派Job之間所有崩潰時點的證明。API雙seal＋36秒留存＋原child終止後，報告才complete；玩家送達欄位明確null。參考[Microsoft Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)與[AssignProcessToJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject)。

## CLI與建置

七欄私人設定：`role`為Server，`managementApiUrl`為`http://IPv4:port`且不含結尾斜線，`gameServerKey`、`sessionId`、`address`、`listenAddress`、`port`。拒絕Client／Host、額外欄位、Master／Room角色、混淆IPv4、越界埠與既有輸出。報告採同目錄新暫存檔完成Flush後Move發布，目的檔不覆蓋。

```powershell
Launch-Server.exe --run <私人JSON> --work <全新包外資料夾> --seconds 3600 --ready-report <新就緒檔> --report <新結果檔>
Launch-Server.exe --verify package --report <新結果檔>
```

seconds限制60..86400，從就緒後計算；90秒啟動等待分開。結果與就緒路徑必須互異、位於包外及work外。就緒不宣告任務已Running；報告complete也不是玩法或跨機容量驗收。

```powershell
python scripts/package-windows-server.py --stage-root "$env:LOCALAPPDATA/VrCommand/Pkg" --output <新ZIP>
python scripts/check-server-package.py <VRCommand-GameServer> --control-package <VRCommand-ControlServer> --runtime-root "$env:LOCALAPPDATA/VrCommand/RuntimeEvidence"
python -m unittest discover -s tests -p test_server_package.py
```

package沿用原實際Windows build receipt及素材／Transport授權，保留自己launcher來源SHA；原runtime allowlist拒絕私人設定與journal混入。4項Python邊界測試只驗假bytes的完整性／路徑，不能當Unity或GUI執行證據。`check-server-gui.py`只建自己的CLI測試資料／觀察原child，UI輸入另由computer-use完成；本輪它是failed，後補關窗review有界等待只經語法檢查，沒有冒充新GUI通過。

最終103項包含五個獨立server＋五個接收client，之後一個Linked server＋五個接收client；觀察原Begin的Running／tick／observed／原1.5秒來源界線，六場553完整API回放、10份原admission精確結果／CSV、雙seal與closed journal durable尾界及cleanup全部成功。parent-exit第七場刻意殺父程序，自己的Unity被Job收掉、沒有成功final報告，該journal保持未封存，不混入六個正常完成場。每組只在自己的所有writer終止後一次F snapshot，不開保存SQLite。詳見[PROGRESS](PROGRESS.md)。

這些都是同機Simulation，非25位同時操作、跨機、GPU效能、頭盔／MR或硬體廠商整合。完整11項長期目標仍active；原31筆、world371、舊Windows startup及F吞吐問題不因新包成功而改判。

[精確95411a2的CI41335830454](https://github.com/peca12968/vr-command-center/actions/runs/41335830454)完整success：Linux738／459／47、6私有管線、4新Python邊界及素材、78 Node／256 Chromium。console43與control13檔下載digest核對，1112 browser證據與另13 metadata分開。2 Windows skip不當Framework／Unity／GUI證據；本機103與failed GUI維持各自範圍。後補closed-readback僅讀原件，10 CSV及10原network admission／server ACK精確相符，非新live測試。
