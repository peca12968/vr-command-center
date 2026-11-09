# Windows 遊戲伺服器包

2026-11-10 `windows-server-0.49.0-launcher1.7-win-x64.zip` 為 84,787,603 bytes，SHA-256 `f5ecb57361f981e6f66497bb987598a3f57a83f623ddb14d9e5ad05647002d39`。解壓核對 330 個清單檔案。此版本與 Windows 玩家包使用同源遊戲建置。

2026-11-09 `windows-server-0.48.1-launcher1.7-win-x64.zip` 為 83,470,147 bytes，SHA-256 `c3d15a8fc23fec76b5a127c8ffc977719eb538074b0e2bfd693974c6be368bd0`。解壓核對 328 個清單檔案。搭配同源 0.48.1 Windows 玩家及 Quest APK。 [版本相容性](EXTERNAL_CLIENTS.md#遊戲版本相容性)

2026-11-09 `windows-server-0.48.0-launcher1.7-win-x64.zip` 為 83,469,619 bytes，SHA-256 `dce833f49f6a94e630666a6d36d152e80ae5fa693d8a7ad5ffd6f744798a03ef`。解壓核對 328 個清單檔案，321 個 Unity 0.48.0 執行檔案與 1.6 逐檔一致。Windows 啟動器新增場館驗收的來源紀錄開關。 [操作方式](#跨機來源診斷)

2026-11-09 `windows-server-0.48.0-launcher1.6-win-x64.zip` 為 83,468,953 bytes，SHA-256 `aeb7b59c58a43f86918ec6135227658596d58afab5a397cfeaf2badda777fb92`。解壓後核對 328 個清單檔案，321 個 `Runtime/` 檔案逐檔符合 1.5 的 Unity 0.48.0 執行內容。新版會在啟動前核對 MR 場次的房間校正鎖定。 [操作方式](SERVER_CATALOG.md#mr-校正鎖定與啟動資格)

2026-11-09 `windows-server-0.48.0-launcher1.5-win-x64.zip` 為 83,468,072 bytes，SHA-256 `fa6baef98f2d52a5fff9e0d0a3a09cff9dbc2aab3c2111b18b86b88fd8335e82`。解壓後核對 328 個清單檔案。MR 場次須在啟動前鎖定全部房間的校正檔。 [主控操作](QUEST3.md#啟動-mr-伺服器前鎖定校正檔)

2026-11-09 `windows-server-0.47.1-launcher1.5-win-x64.zip` 為 83,466,797 bytes，SHA-256 `f885bc1b2fc7c3131dd59498f965d408749e60b00c8b9dbcc98209927907a9a7`。解壓後核對 328 個清單檔案。 [版本相容性](EXTERNAL_CLIENTS.md#遊戲版本相容性)

Unity 0.47.0 伺服器可搭配控制台 0.31.14。啟動器 1.5 可選擇待開的 VR 或 MR 場次，並在就緒後容許短暫管理服務中斷。場中增援由配套管理服務核對場地容量與錄製版本。 [場中敵軍增援](LAYOUT.md#場中敵軍增援)

## 選檔啟動及結算驗收

2026-11-10 以伺服器包 0.49.0 和管理包 0.31.64 實測。管理服務運行時，在啟動器按「選擇檔案」，開啟該實例的 `control-instance.json`。場次清單載入後，選定房間並核對場次與任務版本。設定公告與綁定位址、UDP 埠，需要保存來源時勾選「記錄本次玩家連線來源（場館驗收）」，再按「啟動伺服器」。收尾時等畫面顯示「任務已封存並停止」後關閉。

本輪單房的一名 Windows 模擬玩家在同機入場。開始與結束由測試程式經管理 API 送出，UDP 來源、原戰績、伺服器確認回條與 79 格回放均通過核對。原遊戲程序停止後從視窗正常關閉，診斷選項清除。 [實測紀錄](PROGRESS.md#2026-11-10-windows-遊戲伺服器選檔至結算驗收)

## 管理服務短暫中斷

2026-11-09 主包 `artifacts/server-packages/windows-server-0.47.0-launcher1.5-win-x64.zip`，83,466,340 bytes，SHA-256 `89cdef1e26468a25cd4a145a817f8b5fe11fddbf2ecd834cfdf3f4394b13a891`。解壓後逐檔核對 328 筆。遊戲執行內容使用 0.47.0 的原建置，配套管理包為控制台 0.31.14。 [實測結果](PROGRESS.md#2026-11-09-遊戲伺服器保留原場次等待管理恢復)

就緒後，遊戲伺服器啟動器遇到暫時性 HTTP 讀取錯誤時，會保留自己已啟動的遊戲程序。請以相同 IPv4 與埠號重新啟動原管理實例。啟動器給予 15 秒恢復窗口，自首筆失敗的讀取開始計算，回應到達後重新核對原場次、戰鬥來源與單調增加的序號。既有的每次 HTTP 讀取期限也適用於進行中的讀取。

恢復只適用於可判定的暫時性連線錯誤或 HTTP 502、503、504。認證或權限錯誤、找不到原場次、資料不符與期限到達時，啟動器會停止自己的遊戲程序並留下未完成報告。遊戲引擎依管理可用狀態處理暫停與續行。End 後的雙封存檢查、原玩家戰績與 36 秒保留仍由各自的既有流程處理。

結果報告的 `managementRecovery` 提供 `outages`、`recoveries` 及 `longestMilliseconds`，可核對啟動器觀察到的讀取中斷。玩家戰績送達應另對原伺服器和玩家日誌。 [封存戰績核對](EXTERNAL_CLIENTS.md#核對封存戰績與-udp-來源)

## 遊戲程序退出後補送錄製

Windows 錄製補送工具 0.1.0 使用原遊戲伺服器工作資料夾中的 `server-config.json`，以及設定指向的 `telemetry` 下同一場次的 `.journal` 與 `.worldlog`。遊戲程序退出後，先在原管理實例結束該場次並釋放房間，再解壓補送工具。原設定檔含該伺服器的 GameServer 金鑰，請與日誌一併私下保管。

```powershell
.\Recover-Recording.exe --recover-server 'C:\private\server-work\server-config.json' `
  --work 'C:\private\recovered-room1'
```

工作資料夾必須是新路徑，上層須已存在。工具在兩份原檔保持唯讀獨占的期間建立工作副本，核對原場次、原錄製來源及原管理端接受序號後補送。獨立五房可分別處理受影響的場次，合併場只需處理其原伺服器一次。

退出碼 0 會在工作資料夾留下 `recovery.json`，列出兩份日誌補送前後的接受序號與各自封存狀態。若原日誌未完成結尾，主控台可播放已保存片段，場次仍顯示未完整封存。只在有原完成紀錄且服務確認精確尾端時封存。補送之後可另行開新場次。 [回放保存片段](WORLD_RECORDING.md#回放未封存的已保存片段)

退出碼 1 會在終端顯示原因，並保留可用的工作副本。若戰鬥已補送、世界暫時失聯，待服務恢復後用同一原設定及原日誌、另開工作資料夾重試。伺服器會核對已接受的原資料，再接續未接受部分。損壞或仍由原程序鎖住的日誌需先排除問題，工具不截斷原檔。

## 本機 UDP 綁定確認

2026-11-06 主包為 `artifacts/server-packages/windows-server-0.41.2-launcher1.3-win-x64.zip`，82,676,182 bytes，SHA256 `0f5448df34c5857286d8e29d4feb497fd72961685359033e65b926747fb3555c`。清單有 311 筆，內含 304 份與啟動器 1.2 相同的遊戲執行檔及相依檔。

啟動器 1.3 在公告場次連線設定之前，向 Windows 核對本次遊戲子程序的 PID、本機 IPv4 與 UDP 埠。明確綁定時必須完全相符，設定 `0.0.0.0` 時則核對萬用位址。等待綁定仍受原 90 秒就緒期限限制。

CLI 的就緒及結果檔新增 `udpBinding`，含 `processId`、`address`、`port` 及 `observedAtUtc`。原就緒檔的 `address` 仍表示玩家要連到的公告地址。WinForms 運行狀態會顯示啟動時已核對的本機 UDP 位址。Windows 的紀錄用於確認啟動時的綁定，跨機可達性另以第二台電腦入場驗證。 [Microsoft Windows UDP 端點表](https://learn.microsoft.com/en-us/windows/win32/api/udpmib/ns-udpmib-mib_udprow_owner_pid)

遊戲啟動前可先用 PowerShell 在規劃的同一個位址與埠測試 UDP 往返。探測程序退出後再交由遊戲伺服器綁定。 [兩端探測操作](EXTERNAL_CLIENTS.md#開場前核對兩端-udp)

私有乙太網路位址與預設 loopback 的解壓包分別通過 374 及 124 項整合檢查。兩次都另有一場核對 `0.0.0.0`，並保留不同的玩家公告位址。 [驗證紀錄](PROGRESS.md#2026-11-06-遊戲伺服器公告前的-udp-綁定核對)

## 跨機來源診斷

啟動器 1.7 可在 WinForms 選定場次並填好 UDP 位址與埠後，勾選「記錄本次玩家連線來源（場館驗收）」，再啟動伺服器。選項預設關閉，運行期間鎖定，收尾後會取消勾選。CLI 仍使用 `--peer-diagnostics on`。就緒及結果檔的 `peerDiagnosticsEnabled` 會顯示原遊戲子程序啟動時的選擇。結果檔的 `workDirectory` 可定位本次的 `server.log`。 [戰績與來源核對](EXTERNAL_CLIENTS.md#核對封存戰績與-udp-來源)

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

搭配控制台 0.31.18，可加上 `--check-room-reports`。測試會對照同一個五房連線場次的封存全場 CSV、五份分房 CSV 和戰績 ZIP，並確認房控指定別房時收到 403。再加 `--check-room-combat` 可讓兩種模式的每位原玩家都實際收到敵軍傷害，核對敵軍射線、同房傷害事件、逐格統計與最終戰績。 [分房匯出](REPORTS.md#五房分房匯出)

搭配管理包 0.31.46，可加上 `--prepare-independent-set --check-independent-room-missions`。測試用一筆 API 請求為五個獨立房指定不同的 VR 任務。逐房核對已進入 Running 的原遊戲快照及標頭，包括任務時間、天氣、日夜、雷電、敵軍策略與數量，以及掩體座標與角度。接著按原流程核對回放、雙封存及原玩家戰績。 [逐房操作](MISSION_VERSIONS.md#逐房指定任務版本)

Quest 小批次驗證可在三包命令加上 `--check-vr-venue-tickets --check-quest-vr-partial-map`。獨立與合併的名冊各登記 15 個 Quest 3 席位與 10 個 VIVE XR 席位。工具從原控制台 ZIP 測試錯列 VIVE 的拒絕，再把五份指定設定送至模擬 ADB。MR 可省略 `--player-package`，保留本機 `--game-address`，改用 `--mr-venue-bundle-only --check-mapped-quest`，核對完整清單與五席清單各自使用的原鎖定校正檔。 [小批次操作](QUEST3.md#部署指定的-quest-席位)

五房 VR 追蹤驗證可在上述小批次命令再加 `--check-venue-openxr --openxr-mock-pose-dll '<測試 DLL 路徑>' --check-room-readiness --check-venue-begin --check-venue-end --check-room-reports --check-venue-reports`。兩種模式各以一個 Windows OpenXR 模擬玩家和 24 個桌面玩家同時入場。工具沿用控制台下載的原 ZIP，核對第 5 房第 2 席的就緒、中斷及恢復，並保存其餘 24 席的狀態與原場次回放。VIVE XR 是該席在名冊上的裝置分類，驗證使用 Unity Mock Runtime。 [測試 DLL 建置](WINDOWS_PLAYER_PACKAGE.md#本機追蹤整合驗證)

搭配控制台 0.31.10，可加上 `--check-interrupted-replay`。測試在另一個獨立場次錄到敵軍實際傷害後終止該次啟動器，核對原遊戲程序退出，再檢查保存片段的尾端、戰績及未封存狀態。 [中斷場次回放](WORLD_RECORDING.md#回放未封存的已保存片段)

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

啟動器接受尚未綁定戰鬥來源的 Preparing VR 或 MR 場次。就緒前的管理讀取失敗、來源改變、就緒 90 秒逾時，或觀察到 End 後 30 秒仍未雙封存時，啟動器停止自己的子程序並保留不完整結果。GUI「中止」會停止本次子程序。資料預設在 `%LOCALAPPDATA%/VrCommand/GameServers`，結果在 `GameServerReports`。伺服器私鑰保留在包外資料夾。所有寫入程序停止後再備份。 [MR 開場方式](QUEST3.md#主控建立-mr-場次)

## 啟動、來源與停止界線

啟動器核對manifest逐檔大小／SHA與完整檔案集合、拒絕連結／越界／額外檔案；清單不是數位簽章。只接受GameServer角色，Unity設定只帶這個key，不帶Master。GUI讀既有管理實例的JSON，不新增或複製角色金鑰。遠端管理可由CLI的私人七欄JSON明確指定；尚無LAN、TLS或乾淨新機驗證。

每輪使用新的包外資料夾與日誌，核對 Preparing、VR／MR 模式及來源未綁定，再取得以 API 地址及場次命名的本機 mutex。UDP 探查會拒絕啟動前衝突，正式就緒另由原 Unity 程序的綁定與錄製來源確認。

Unity 先核對自己的戰鬥串流識別、來源、接受序號與封存狀態，再啟動伺服器並記下 `VR_NETWORK_STARTED ... started=True ... port=...`。啟動器讀取本次啟動日誌，並透過 API 核對同場次的戰鬥串流和世界錄製來源。VR 使用 Simulation，MR 使用 GameServer。核對後以原 GameServer 角色公告連線端點，並比對回條的場次、串流、IPv4 與埠。

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
