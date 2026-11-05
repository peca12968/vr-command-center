# Windows 遊戲伺服器包

## 跨機來源診斷

2026-11-06 新版 `windows-server-0.41.2-win-x64.zip` 為 82,674,494 bytes，SHA256 `a8e4a529adbe744cdc11450dae209795adbfe52be0581e0ed652169220a86646`，包含 311 筆檔案清單及清單本身。

伺服器啟動器 1.2 搭配遊戲 0.41.2，可在一般 CLI 啟動參數後加入 `--peer-diagnostics on`。實際的 Windows 遊戲伺服器在核准的玩家連上後，由 Unity Transport 讀取來源位址與埠，記錄於自己的 `server.log`。可用同一連線編號核對玩家入場及伺服器的戰績確認回條。來源埠是玩家的 UDP 埠，通常會與伺服器的公告埠不同。

每次啟動最多記錄 256 筆，超出時記錄一筆 `VR_SERVER_PEER_LIMIT`。若當下無法讀取來源，該筆記為 `unavailable`。預設 CLI、WinForms、頭盔與玩家程式均不開啟診斷。這些記錄含來源位址，請保留在私人資料夾。地址表示伺服器這一端實際觀察的網路來源，經 NAT 時可能是轉譯後位址。 [第二台電腦的驗收步驟](EXTERNAL_CLIENTS.md#第二台電腦的驗收步驟)

在三包整合測試命令加上 `--peer-diagnostics`，可在 Linked 核對來源與原玩家回條，同時驗證獨立房間的預設流程沒有來源記錄。

## 三個可攜包整合驗證

2026-11-06 使用既有管理包 0.31.4、遊戲伺服器包 0.41.1 v2 與玩家包 0.41.1 v2 完成同機測試。五個獨立房間先各以一個伺服器運行，之後改用一個伺服器執行 Linked。每種模式各有 25 個背景玩家同時入場，每房五席。遊戲 UDP 綁定同一台電腦的乙太網路 IPv4，管理服務保留在 loopback。10 份整房 ZIP 直接取自管理包，由 `Launch-Player.exe` 使用對應席位檔。 [整房配票操作](EXTERNAL_CLIENTS.md#按房間下載連線檔)

319 項通過，六個正常場次共 812 幀完整回放、50 份玩家戰績及 6 份 CSV。測試核對戰績的原 admission、戰鬥與世界封存，以及伺服器對每條原連線的確認回條。這是同機 Simulation 的 CLI 流程，跨機、WinForms 多人操作、頭盔與 25 位真人待驗。

在測試機將下列三個資料夾與 IPv4 換成實際解壓路徑及本機私有位址。省略最後兩個選項會執行原 loopback 驗證，每種模式共五個玩家。

```powershell
python scripts/check-server-package.py <VRCommand-GameServer> `
  --control-package <VRCommand-ControlServer> `
  --runtime-root "$env:LOCALAPPDATA/VrCommand/RuntimeEvidence" `
  --player-package <VRCommand-Player> --game-address 192.168.1.100
```

2026-11-02 本輪同源Unity0.41.1／code52／NGO29／242真正Editor、4ebd雙平台：新server主包 `windows-server-0.41.1-v2-win-x64.zip`，**82,673,732 bytes／SHA256 `ca285a42e0c22bdde17f62eb6dd8a65523c9d3a5cae19a33cad41636899fb368`**、311 manifest／ZIP312。啟動器1.1來源fb57807d...不變但重新編譯binary不同，runtime逐byte同v1；v1與所有舊包保持。包說明改引用Runtime/build-receipt.json，不再寫死Unity0.39。

實際F解壓包106項／623全回放、五房後Linked／10原結果與CSV／雙seal／原server ACK／無active成功，parent-death是另留的未封存反例；closure UI新增Running與Archived兩PNG、精確原session/stream/final world，nativeUI9＋2＝11，非雲端CI檔。

**實際WinForms流程已成功**（run-3d179468...／真正handle64853 exit0）：直接輸入既有實例路徑、載入兩房清單、明確選房1完整UUID／任務版本、設定127.0.0.1及本次UDP、按啟動，fixture API Begin後原來源Running/tick>0/observed fence，再API End、雙seal保留36秒、原child停止、畫面「任務已封存並停止」後按關閉。原實例marker／三key檔hash不變；GUI exit0／closed journal精確ACK尾界／cleanup空、C14→F raw同hash。名冊只有fixture roster一位，**未啟動玩家client**；不宣稱玩家送達／操作／LAN／頭盔。此次沒有測系統「選擇檔案」視窗、GUI建立key或透過GUI按Begin/End；Begin/End仍是fixture正常API。

使用者自行關PickerHost後重驗，舊PickerHost失敗保持。首新GUI run-e615...已選對並啟動，但fixture空名冊Begin被原API409拒絕、helper finally清理後C9→F同hash，仍failed；只修fixture先加一位明確roster，不改產品／API／啟動器或Begin原規則，py_compile與新真GUI成功。期間自動化bounds變更後重新選取/擷取再操作，沒有繞過任何安全提示。上述GUI不代表舊Windows startup／31／world371／F吞吐修復，完整11active。

以下為歷史交付與當時驗證狀態；目前版本與新GUI結果以上段為準。

前主包`windows-server-0.40.0-win-x64.zip`，**82,672,917 bytes／SHA256 `642e5307cf3d62af7b136d9baaca06c2d9cd9c3bd1ed66c7d4e915803a7f8710`**，原啟動器1.1／source fb57807d...及新Unity0.40 runtime／6098b485...，311 manifest／ZIP312。106項實際包驗證／725回放／原結果CSV及cleanup成功，原生自動化25端與普通入場另見[DESKTOP_EXERCISE](DESKTOP_EXERCISE.md)。不是新的Windows launcher GUI、LAN／25真人或頭盔驗收。

前版[啟動器1.1／房間任務清單](SERVER_CATALOG.md)的`windows-server-0.39.0-v5-win-x64.zip`保持，82,669,350 bytes／SHA3eef78fbe8319e366afa80cdfad31557bf42fb8bc3992402b6f252525e2857a2。CLI38／Framework model26／原生106成功，完整GUI開場仍被PickerHost擋住；以下v3與舊failed證據保留，不能只看同一Unity版本選包。

可搭配API0.31.0／控制台0.31.1的[任務收尾](SESSION_CLOSURE.md)顯示雙封存與保留已確認End；原server v3 runtime／SHA保持，不需要因這個唯讀UI更新Unity或頭盔。

`Launch-Server.exe`將既有Unity Windows播放器以獨立Server模式啟動。操作員只需Windows x64與.NET Framework4.8，不需要Python、Unity Editor或.NET SDK。管理網站用[管理服務包](WINDOWS_CONTROL_PACKAGE.md)，玩家使用[玩家包](WINDOWS_PLAYER_PACKAGE.md)，三者分開運行。

原PC原型v3主包為`artifacts/server-packages/windows-server-0.39.0-v3-win-x64.zip`，**82,664,818 bytes**、SHA256 **`6cecfbeeffba1277000f93bc168c4ac387b825c34b73142628098dba28f67500`**，311個manifest檔案／ZIP312含manifest。v1、v2候選原件保留。沿用Unity **0.39.0／code49／NGO29／e0d60e4ed6cefe5cd885e6aabe1621939da945ce00d56b3ed8820c0aed4db879**，API/UI仍0.31.0，沒有修改Unity來源、重建Editor／APK或更新原場景／prefab ID。

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
