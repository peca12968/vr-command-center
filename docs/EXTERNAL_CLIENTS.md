# 分開啟動玩家與遊戲伺服器

## 遊戲版本相容性

遊戲 0.48.1 使用 NGO 協定 31。Windows 遊戲伺服器、Windows 玩家與 Quest APK 請使用同版。升級時先結束現有場次，再一併更新遊戲伺服器及玩家端。API 0.31.0 供應玩家票券及世界回放，MR 伺服器須搭配支援 `SetRoomAlignment` 的管理服務。 [鎖定房間校正檔](QUEST3.md#啟動-mr-伺服器前鎖定校正檔)

新版以二進位 UUID、打包整數與欄位旗標傳送角色狀態。連線房間同步完整角色清單，以完整浮點精度傳送位置、面向與射擊向量。

在原生 Windows 驗證中，0.46.0 玩家攜有效票券會在入場核准前遭 0.47.0 伺服器拒絕。同一張票券由 0.47.0 使用時成功入場並取得戰績。 [版本與流量驗證](PROGRESS.md#2026-11-09-壓縮即時角色同步)

## 分開啟動程式

Windows 遊戲伺服器包可獨立啟動既有 Preparing VR 場次。CLI 已通過同機五房獨立與 Linked，WinForms 已驗證載入場次、啟動和封存後停止。 [Windows 遊戲伺服器包](WINDOWS_SERVER_PACKAGE.md)

API／控制台0.31.0可另用[Windows可攜管理服務](WINDOWS_CONTROL_PACKAGE.md)部署管理網站，含自己的.NET執行環境與繁中啟動器。已用真正GUI／封裝API驗證啟停、資料與角色重開，原Unity0.39／NGO29保持；管理服務、遊戲伺服器和玩家仍分開運行。以下0.30工具段落保留原功能範圍，實際LAN／頭盔仍待。

玩家端新版[連線狀態](PLAYER_CONNECTION_STATUS.md)可區分程式啟動與遊戲回報入場、拒絕、未確認及戰績保留；這不新增網路可達性探測，也不以同機驗證宣稱跨機成功。

Windows 玩家完整解壓玩家包後開啟 `Launch-Player.exe`。可選取自己的下載檔，或貼上完整路徑後按「載入／更新」。已驗證 WinForms 載入、檔案變更時拒絕啟動，以及重新載入後完成同機雙玩家入場與封存。跨機連線待驗。 [可攜玩家包](WINDOWS_PLAYER_PACKAGE.md)

API／控制台0.30、Unity0.32.0／Android code39／NGO29。操作員啟動器新增external模式：只啟動自己場次的server，不自動替名冊中的每個人開本機client、領票或占用入場。原本local模式仍是預設，供同機PC練習。

## 啟動

```powershell
python scripts/start-desktop-control.py --api-dll <本次API.dll> --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns" --client-mode external --advertise-address 192.168.1.100
```

地址是玩家應連到的這台遊戲伺服器IPv4，必須由操作員明確提供；工具不猜地址或證明遠端可達。external預設監聽0.0.0.0，local預設127.0.0.1。可用`--listen-address`明確綁定特定網卡；特定地址須與公告地址相同。只有本機測試時，兩個選項都設127.0.0.1；這種設定不能當成跨機證據。

本節外部玩家工具的管理API仍在loopback，管理網站的獨立部署另見[管理服務包](WINDOWS_CONTROL_PACKAGE.md)；NAT／中繼、TLS與OS防火牆仍由場館另行部署。尚未驗證實體LAN／頭盔。公告v1採canonical dotted-decimal unicast IPv4及1024–65535埠，不接受DNS、URL、IPv6、縮寫、前置零、wildcard或multicast目的地。

在該次控制台登入，正常保存／選取VR任務、建立Preparing場次及名冊。工具等真正來源建立world header後，使用與server相同的GameServer身分公告該場實際配置的埠與操作員指定的地址。Independent各有自己的port，Linked共用該場一個port；不把五場歷史合併成一場。

名冊下方會顯示「來源公布」的地址／port，與本次stream吻合後填入空白欄位。手動編輯不被背景更新覆蓋，可按「套用場次連線設定」重新採用公告；切場／登出清空草稿及隔離晚回應。公告是設定，不是連線成功或設備就緒；有效姿態另見[PLAYER_READINESS](PLAYER_READINESS.md)。

控制台 0.31.3 會在配票前核對連線目的地。請輸入四段十進位 IPv4，例如 `192.168.1.100`，每段使用標準數字格式，第一段介於 1–223，埠號介於 1024–65535。確認後按各玩家的「下載連線檔」，將檔案交給對應玩家。每張票券有效五分鐘，依本次 admission、房間與席位驗票。檔案包含 `role`、`address`、`port` 與 `joinTicket`。Windows 玩家也可執行下列命令。

```powershell
& <同版VrCommand.exe> --vr-config <自己的玩家連線檔.json>
```

Quest仍使用[QUEST3](QUEST3.md)的部署方式，實機未驗。工具整場來源維持Simulation；external的`headsets`為null（工具不辨認遠端設備），不能因名冊Quest3分類或Tracked宣告就填成實測頭盔數。取得實機後的GameServer來源整合另驗，不在同一場混用來源。

## 按房間下載連線檔

控制台 0.31.4 的「整房配票」列出本場次中有玩家、且操作員有權配票的房間。核對遊戲伺服器 IPv4 和埠，選擇房間後按「下載房間連線檔 ZIP」。全館主控可逐房操作，房控可為自己的房間配票，Linked 場次也依同樣權限處理。

例如 `room-03-connections.zip` 裡的 `room-03-seat-01.json` 對應房間 3 的席位 1。按控制台名冊核對席位，個別交付 JSON。ZIP 最多含五份連線檔，皆使用五分鐘票券。VR 連線檔採四欄格式，MR 連線檔另帶 `roomAlignmentSha256`。整份 ZIP 由負責配票的操作員保管。

Quest MR 滿席部署可先用清單一次核對五房 ZIP、場次 ID、端點及各房校正檔，再逐席部署。 [五房 25 席部署預檢](QUEST3.md#五房-25-席部署預檢)

`POST /api/sessions/{id}/rooms/{roomId}/join-ticket-bundle` 接受 IPv4、埠與該房間完整的玩家 ID 及 admission ID。服務以一次名冊快照核對整組後才產生 ZIP，成功回應帶 `Cache-Control: no-store`。名冊已變更時回應 409，重新整理後核對席位再下載。MR 的單席與整房配票須先由主控鎖定該房校正檔，否則回應 409 `mr-alignment-required`。遊戲伺服器依當前 admission 驗票，名冊異動會使相應的舊票券失效。

## VR 五房配票

管理包 0.31.41 起，全館主控可在五房總覽點「讀取五房名冊」。先準備五個獨立 VR 場次或一個五房合併 VR 場次，為每房加入五名玩家，並讓各遊戲伺服器公布端點。核對畫面中的任務、端點、房間、席位及玩家姓名，再按「下載五房連線檔 ZIP」。畫面會標示只能同機使用的 loopback 端點。

`vr-venue-connections.zip` 內含 `venue.json`、五個原格式的分房 ZIP 及共 25 份四欄玩家連線檔。分房 ZIP 依房號命名，每個 JSON 依房號與席位命名。票券自簽發起有效五分鐘，請將對應的 JSON 個別交給玩家，整份 ZIP 由主控私下保管。Windows 玩家啟動器可再次核對檔內標示的房間與席位。 [玩家端核對](PLAYER_CONFIG_REVIEW.md#連線檔席位與效期)

下載使用各來源已公布的位址和埠。五房獨立須使用各自的端點，合併場共用同一端點。若名冊、場次或來源已變更，請重新讀取五房名冊。尚未填滿的場館可沿用單席或整房配票。

主控可用 `GET /api/vr-deployment/venue` 讀取預覽。向 `POST /api/vr-deployment/venue-bundle` 送出同一預覽的 `topology` 以及五個 `rooms`，每房提供 `roomId`、`sessionId`、公布的 `streamId` 和五筆 `players` 的 `playerId`、`admissionId`。服務以同一份現行場館快照核對所有房間。任何一房不符時回應 409，附對應房號，整批無 ZIP。

管理包 0.31.42 提供 `POST /api/vr-deployment/venue-check`，限主控。請求提供 `topology` 與五筆 `rooms`。每房提供 `roomId`、`sessionId` 及依席位排序的五份 Base64 `connectionFiles`，回傳逐席的票券、端點及現行名冊核對狀態，以及成功席的裝置類型。Quest 部署工具可直接讀取原 ZIP 使用此端點。 [Quest 部署操作](QUEST3.md#直接使用-vr-五房連線-zip)

## 結束與保存

操作員End、end.request、時限或正常退出會沿用原雙journal精確seal。external不持有玩家程序或其結果log，所以`allAcknowledged=null`，不把空集合當全部收到；server非阻塞保留至少36秒，涵蓋原30秒結果期限與進行中最多5秒HTTP，`--results-seconds`較大時採較大值。這是保留時間，不是送達保證；例外／再次中斷仍可能提早結束，不能當崩潰恢復。

只關閉外部玩家不會自動End場次。工具只停止自己server／API；正常保留期內可處理其他場次。全部runtime writer停後才一次snapshot回F，保留C原件。原有local模式仍觀察自己client的結果ack，與external未知結果分開記錄。

## 公告契約與監聽設定

GET `/api/sessions/{id}/connection-endpoint`僅Master／可讀此場的RoomController，無公告為404；PUT僅已附掛combat stream的GameServer owner且world header已存在。每次傳Actor／重查範圍；Internal不是HTTP捷徑。PUT body為`{version:1, streamId, address, port}`，接受後不可改址／port，原內容重試回原createdAt。以場次／stream／完整owner綁定，房間重用不承襲舊公告。

公告是獨立metadata，儲存在worlds.db新增的connection_endpoints表；world schema1、envelope7、原header／checksum／命中規則0.8.0與素材pin保持。Ended也可保存原來源的歷史公告，GET回報當前sessionEnded；不重新開場或授權Ended配票。沒有連通性探測、外送命令或將地址當認證。

Unity新增server-only `listenAddress`，真正傳給UnityTransport的第三個參數。省略／空值仍是原0.0.0.0，保留舊設定語意；新managed工具明確寫127.0.0.1或選定地址。此前程式硬寫0.0.0.0，不可用忽略新欄位的舊server冒充loopback綁定。NGO wire不變，但本輪Windows／Quest需使用同源新版，Prepare重用Scene／prefab ID。

### 五房房卡的連線端點

控制台 0.31.48 在「房間與場次」的房卡顯示該場伺服器公布的 IPv4 與 UDP 埠。合併場的五個房卡使用同一端點並標為「五房共用」。位址在 `127.0.0.0/8` 時會標明「僅同機」。獨立房間各顯示自己的端點，尚未公布時顯示等待。開場前可直接在總覽核對各房，並按「查看場次」進入原連線檔與配票流程。

房卡核對目前房間、場次與遊戲來源。場次更換、舊來源回覆或讀取失敗會移除原端點。已公告的地址仍可能遇到防火牆或路由限制。跨機可達性以兩端 UDP 探測與正式玩家入場確認。 [兩端探測操作](#開場前核對兩端-udp)

`GET /api/rooms/readiness` 的各房資料在已公告時附上 `endpoint`，內容與原場次的 `connection-endpoint` 一致。主控可讀五房，房控僅收到本房，已結束場次的端點仍留在歷史場次。

## 驗證範圍

144真正EditMode、同源Windows／Quest、717規則、459 HTTP／47串流、67 Node／234 Chromium及6新Python檢查通過，完整結果見[PROGRESS](PROGRESS.md)。普通UI fixture只驗顯示，不能當可達性證明。

`tests/browser/check-external-native.cjs` 使用新建的 external／Simulation 測試場次。它透過控制台建任務與名冊，下載兩份連線檔，以真正的 Windows 玩家程序核對入場、Begin／Pause／End、個別戰績與雙封存。預設遊戲端使用 `127.0.0.1`。驗證本機網卡時，先用以下命令指定已指派給這台電腦的私有 IPv4，並在測試工具傳入同一個位址。

```powershell
python scripts/start-desktop-control.py --api-dll <本次API.dll> --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns" --client-mode external --advertise-address <本機IPv4> --listen-address <本機IPv4>
node tests/browser/check-external-native.cjs <本次ready.json> <解壓玩家包> --local-game-address=<本機IPv4> --launcher-status
```

工具會核對本機網卡、場次公告、控制台欄位、該遊戲伺服器 PID 的 UDP socket，以及兩份下載檔的目的地。管理 API 使用 loopback。結果記錄 `same-host private IPv4` 或 `same-host loopback`，供後續區分。Chromium 使用 SwiftShader。

## 第二台電腦的驗收步驟

1. 在伺服器電腦啟動管理服務和遊戲伺服器，選定本機 LAN IPv4 與 UDP 埠。啟動器 1.3 會在公告前核對遊戲程序的 UDP 綁定，可用就緒檔的 `udpBinding` 確認本機端點，再核對控制台給玩家的公告。Independent 每場使用不同的 UDP 埠，Linked 共用該場一個埠。CLI 可另加 `--peer-diagnostics on` 記錄各已入場玩家的實際來源位址。 [本機 UDP 綁定確認](WINDOWS_SERVER_PACKAGE.md#本機-udp-綁定確認) · [來源診斷](WINDOWS_SERVER_PACKAGE.md#跨機來源診斷)
2. 從控制台分別下載兩份連線檔，其中一份在第二台 Windows 電腦使用同源玩家包開啟。將檔案個別交給對應玩家，並在五分鐘票券期限內加入。保存測試機角色、包版本、公告位址及埠，將連線檔與金鑰留在私有資料夾。
3. 在控制台核對兩位玩家均可參戰後，執行 Begin、Pause、Resume 和 End。保存兩端玩家的入場與最終戰績，核對玩家身分、本次 admission、場次與世界封存序號，並確認戰鬥及世界均封存。以第二台玩家日誌的 `VR_CLIENT_CONNECTED id=` 核對伺服器的 `VR_SERVER_PEER id=` 和 `VR_SERVER_DEBRIEF_ACK id=`。在直連 LAN，應觀察到第二台電腦本次使用的網卡位址與伺服器端來源位址相符。來源無法取得或曾跨 NAT 時，記錄實際觀察的值及網路拓撲。含來源位址的原始日誌留在私有資料夾。
4. 將結果標記為雙機測試，記錄使用的有線或無線網路。分開保存雙機、五房與實機的證據，以便後續擴至 5／10／25 人。

### 開場前核對兩端 UDP

在啟動遊戲伺服器之前，可在兩台 Windows 電腦執行 `scripts/check-lan-udp.ps1`。工具使用 Windows PowerShell 5.1 或 PowerShell 7，先以指定的 IPv4 和遊戲 UDP 埠往返，再釋放該埠交給 Unity。請選擇兩台電腦實際使用的網卡位址。以下 `192.168.1.10` 為伺服器，`192.168.1.20` 為玩家。

1. 在伺服器電腦產生一次性探測金鑰，將金鑰檔和腳本交給本次測試的玩家電腦。兩端的金鑰檔路徑可各自指定，請放在私人位置。

   ```powershell
   $tool = (Resolve-Path .\scripts\check-lan-udp.ps1).Path
   $probeKey = Join-Path $env:LOCALAPPDATA ('vr-lan-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.key')
   powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File $tool -NewKey -KeyFile $probeKey
   ```

2. 在伺服器電腦使用本次規劃的遊戲埠啟動監聽。出現 `listening` 後，玩家端即可送出探測。

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File $tool -Mode Listen `
     -KeyFile $probeKey -LocalAddress 192.168.1.10 -PeerAddress 192.168.1.20 -Port 7777 -Count 5 -Seconds 60 |
     Tee-Object -FilePath .\listener-room-01.ndjson
   ```

3. 在玩家電腦設定自己的 `$tool` 與 `$probeKey`，交換兩端位址後執行。

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File $tool -Mode Probe `
     -KeyFile $probeKey -LocalAddress 192.168.1.20 -PeerAddress 192.168.1.10 -Port 7777 -Count 5 |
     Tee-Object -FilePath .\probe-room-01.json
   ```

4. 等兩端程序退出並關閉輸出檔後，把兩份原始報告放在同一台電腦配對核對。工具比對互為對端的位址、遊戲埠、完整樣本數和 `exchangeSha256`，同一次探測回報 `pair-verified` 並以退出碼 0 結束。核對只讀取報告檔。

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File $tool `
     -ListenerReport .\listener-room-01.ndjson -ProbeReport .\probe-room-01.json
   ```

   核對後用相同位址和埠啟動遊戲伺服器。五房獨立逐房探測各自的埠，每次保存一組新檔。合併場使用該場共同埠。

工具接受三段常用私有 IPv4 網段及 loopback，並只回覆指定來源位址、正確金鑰和新挑戰碼的固定長度封包。逾時樣本的 `roundTripMs` 為空值，整次有任一樣本未完成時以退出碼 1 結束。若出現 `failed`，`step` 可定位到金鑰、位址、綁定或封包交換階段。結果含現場位址，請和原日誌分開私下保存。

這項結果表示兩端的 PowerShell UDP 封包往返。遊戲程式的防火牆規則、票券、Unity 同步及容量，仍要用正式遊戲入場確認。上述執行政策參數只作用於該次 PowerShell 程序。

### 核對封存戰績與 UDP 來源

離線核對工具使用已完成的一場 Windows 伺服器任務。啟動器 1.7 可勾選「記錄本次玩家連線來源（場館驗收）」，CLI 可加 `--peer-diagnostics on`。將公告及本機綁定都設為這台電腦實際使用的 IPv4，選擇名冊固定的場次。結束後等待原啟動器寫出 `sealed-stopped` 報告，並等玩家寫完戰績與斷線日誌。 [伺服器操作](WINDOWS_SERVER_PACKAGE.md#跨機來源診斷)

將伺服器 `--report`、該次工作目錄的 `server.log`、各玩家的原始 Unity 日誌放在私人資料夾。控制台 0.31.14 起，全館主控可在「任務收尾」選擇「下載場館驗收資料 ZIP」。伺服器確認任務曾開始、雙封存、端點公告，以及最終名冊與統計涵蓋同一組玩家和房間。解壓後會得到下表三個檔案。每份包含場館資料，應與同場日誌私下保管。

需要分開保存時，可從同一管理實例以全館主控身分讀取以下三個 GET 回應。連線票券和金鑰應留在各自的私人位置。

| 路徑 | 保存檔案 |
| --- | --- |
| `/api/sessions/{id}` | `session.json` |
| `/api/sessions/{id}/statistics` | `statistics.json` |
| `/api/sessions/{id}/connection-endpoint` | `endpoint.json` |

以 `Get-NetIPAddress -AddressFamily IPv4` 記錄當次伺服器的所有 IPv4，逐一傳入 `--server-ip`。每位玩家各傳一組 `--player`，其中的 IPv4 由該玩家所在電腦獨立確認。下列命令的兩個私有位址是範例，操作時依實際介面填寫。

```powershell
python scripts/verify-field-results.py --topology direct-lan `
  --server-ip 192.168.1.10 --server-ip 127.0.0.1 `
  --launcher-report .\server-final.json --server-log .\server.log `
  --session .\session.json --statistics .\statistics.json --endpoint .\endpoint.json `
  --player 192.168.1.10 '.\player 1.log' --player 192.168.1.20 '.\player 2.log'
```

每場最多 25 位玩家。檢查器逐位比對結束名冊的入場 ID、房間、個人戰績、三種封存序號，以及最終連線的 UDP 來源與伺服器確認。玩家曾重連時使用收到戰績的最後一條連線。名冊異動造成最終統計包含已離場玩家時，這套固定名冊驗收會拒絕。文字日誌、JSON 與 ZIP 每份最多 16 MiB。成功輸出可另存 JSON，摘要只含計數、房間、序號及範圍。失敗以退出碼 1 表示，診斷文字省略原始位址、票券和檔案路徑。

如要一併驗收原生回放檔，等啟動器回報 `sealed-stopped` 後，從其 `workDirectory` 下的 `telemetry` 保留 `<sessionId>.worldlog`。在單場命令加入 `--world-journal .\room-01.worldlog`。工具唯讀檢查每筆記錄的校驗碼與連續影格，核對場次、來源、房間、校正設定和最後封存。它確認原檔含活動中影格及兩種封存的尾界，再輸出檔案 SHA-256、總影格數及活動中影格數。活動中影格須為 `Running`、tick 大於零且未中止來源。原生回放檔逐筆讀取，可超過文字日誌的 16 MiB 上限。 [原生世界紀錄](WORLD_SOURCE.md)

`same-host` 要求全部觀察到的來源都在宣告的伺服器位址清單。`direct-lan` 要求至少有一個清單外的私有 IPv4，且所有玩家的實際來源均符合各自填入的位址。實體主機數與網路容量仍須現場確認，工具摘要分別保留 `physicalHostsVerified` 與 `networkCapacityAccepted` 為 `false`。NAT 或中繼環境需另記拓撲與轉譯結果。

Quest 3 席位使用 `--quest-player 192.168.1.21 '.\quest logcat.txt' 7342`，依序填頭盔本次使用的 IPv4、原始 logcat 路徑和遊戲程序 PID。可與 Windows 的 `--player` 混用。Quest 3 須登記在原名冊，且其 UDP 來源須在伺服器位址清單外。摘要的 `questLogcatPlayers` 只計算通過原入場及戰績核對的 logcat 檔案數。 [Quest 擷取方式](QUEST3.md#收集-quest-場館驗收日誌)

### 一次核對五房 25 席

兩種模式各準備一份私人 `venue.json`。使用 `--peer-diagnostics on` 啟動參與驗收的每個遊戲伺服器，並由主控一次結束全館。等待各場雙封存、原伺服器終止及玩家寫完戰績，保留同場啟動器 `--report`、原始 `server.log` 及每位玩家的完整日誌。

Windows 管理包 0.31.40 起，在「全館收尾」選取要驗收的批次，按「下載本批場館驗收 ZIP」，再解壓到私人資料夾。解壓後的 `closure.json` 及各場原 ZIP 可直接填入清單。合併場用 `linked.zip`，獨立場依房號使用 `room-01.zip` 至 `room-05.zip`。請保留內層 ZIP 檔案供核對工具讀取。 [選取及下載原批次](SESSION_CLOSURE.md#下載本批場館驗收)

舊版管理包可逐場下載「場館驗收資料 ZIP」，並以主控身分將 `GET /api/venue/closure/{id}` 的回應本文原樣保存為 `closure.json`。`{id}` 是該次全館結束回條的 `requestId`。

| 清單欄位 | 填寫內容 |
| --- | --- |
| `version` | 數字 `1` |
| `mode` | `Independent` 或 `Linked` |
| `topology` | `same-host` 或 `direct-lan` |
| `serverIps` | 所有本次伺服器電腦已指派的 IPv4，使用字串陣列 |
| `closure` | 原批次的 `closure.json` 路徑 |
| `sessions` | 獨立模式填五場，合併模式填一場 |
| `sessions[].evidenceZip`、`launcherReport`、`serverLog` | 各場原 ZIP、啟動器終止報告及伺服器日誌的路徑 |
| `sessions[].worldJournal` | 選用。若驗收回放檔，每個場次都填自己關閉後的原始 `.worldlog` 路徑 |
| `sessions[].roomAlignments` | 選用。核對 MR 校正時，每個 MR 場次按房號填原校正檔，例如 `{"2":"room-02-alignment.json"}` |
| `sessions[].players` | 每房五筆。每筆填玩家裝置實際使用的 IPv4 字串 `address` 及原日誌路徑 `log`。Quest 3 原 logcat 另填數字 `logcatPid`，例如 `7342` |

路徑可以是絕對路徑，或相對於 `venue.json` 所在資料夾。同一檔案只能使用一次。例如獨立模式下，第 1 房的清單項目可由下列 PowerShell 建立。請依實際驗收配置填入各席地址與檔名。

```powershell
$room1 = @{
    evidenceZip = 'room-01.zip'
    launcherReport = 'Room 1/server-final.json'
    serverLog = 'Room 1/server.log'
    players = 1..5 | ForEach-Object {
        @{ address = '192.168.1.20'; log = "Room 1/seat-$_.log" }
    }
}
# 準備 $room2 到 $room5 後，與第 1 房一起寫入私人清單。
@{
    version = 1
    mode = 'Independent'
    topology = 'direct-lan'
    serverIps = @('192.168.1.10', '127.0.0.1')
    closure = 'closure.json'
    sessions = @($room1, $room2, $room3, $room4, $room5)
} | ConvertTo-Json -Depth 6 | Set-Content -Encoding utf8 .\venue.json
python scripts/verify-field-results.py --venue-manifest .\venue.json
```

摘要核對五房各五個席位、原封存來源、每位玩家的原入場與 UDP 來源，以及 25 筆伺服器戰績確認。它逐房列出在伺服器位址清單以外的玩家數。`direct-lan` 至少須觀察到一筆這類連線，仍須依實際設備及網路拓撲核對主機數、同時遊玩與容量。

提供回放檔的整批驗收會檢查每場最後影格已觀察到該批結束指令，並輸出 `worldJournalsVerified` 與逐場摘要。回放畫面及遊戲事件內容可用原回放介面另行檢視。

### 核對 MR 校正封存

保留原 MR 或混合部署 ZIP 內的各房校正 JSON。從 ZIP 取出原檔供驗收，維持檔案位元不變。單場驗收加入 `--world-journal .\room-02.worldlog --room-alignment 2 .\room-02-alignment.json`。合併 MR 場次每房各加一次 `--room-alignment`。

若使用整批清單，在每個 MR 場次填入 `roomAlignments`，每一場都填 `worldJournal`。混合批次的 VR 場次只填自己的回放檔。選用校正核對後，任一 MR 房間缺檔即拒絕整批。工具核對原任務的 MR 模式、遊戲伺服器回放的 `quest-room-mr-v1` 設定，以及校正 JSON 的房號和 SHA-256。原檔重新序列化後，即使量測數值相同，仍須改用原部署 ZIP 的位元。

當前 MR 規格要求原 Quest 3 席位使用原始 logcat，並通過實際 UDP 來源、原入場、戰績確認及封存檢查。摘要列出已核對房號和原檔 SHA-256。場地量測精度、實際透視、跨機容量與設備仍須現場驗收。 [Quest 擷取](QUEST3.md#收集-quest-場館驗收日誌)

## Windows 玩家連線量測

自 0.46.0 起，Windows 開發版玩家程式可選用本機量測。以正常玩家票券入場，指定一個尚未存在的 JSON 完整路徑，其上層目錄須已存在。

```powershell
& "<Windows玩家包路徑>/VrCommand.exe" --vr-config "<玩家連線檔.json>" --vr-link-metrics "<新量測檔的絕對路徑.json>"
```

客戶端在收到 Running 狀態後，每約一秒送出一筆 NGO 不可靠訊息。伺服器只回覆已核准且仍連線的玩家，依連線限制回覆頻率。報表逐筆區分回覆、0.9 秒逾時與階段中斷。回覆時間用玩家端單調時鐘計算，包含兩端的遊戲排程與網路傳輸。Unity 更新次數及經過秒數另列，供計算更新頻率。報表以程序與連線編號對應本次玩家，採樣上限為 30 筆，啟動後最多等待 240 秒。提早結束或離線會留下未滿額的結果。

`complete` 表示 30 筆採樣均已結案。統計往返時間時，只使用 `result: "Reply"` 的數值。其餘結果依 `Timeout` 或 `Interrupted` 分別計數。

同機驗證可執行 `scripts/check-desktop-exercise.py --runtime-root <新資料根目錄> --mode both --players-per-room 5 --seconds 40 --link-metrics`。檢查器核對每份報表的原程序與原連線，保留逾時分母，再計算回覆的 p50／p95。無圖形程序只提供 Unity 更新頻率。實際渲染幀率和跨機門檻另行量測。 [驗證結果](PROGRESS.md#2026-11-09-windows-玩家連線量測)

## 同機 UDP 流量量測

```powershell
python scripts/check-desktop-exercise.py --runtime-root "<新資料根目錄>" --api-dll "<管理 API DLL>" --player-exe "<Windows 遊戲 EXE>" --mode both --players-per-room 5 --seconds 40 --udp-traffic
```

工具為每個原玩家建立獨立 loopback 轉送器，沿用正常入場及遊戲輸入。各場次都觀察到 Running 後才開始，獨立模式還會等暫停房間確認恢復。所有玩家共用同一高解析度單調時鐘邊界，約每秒記一次累積計數。量測在任務結束前收束，報表按玩家、房間、全場及時間區間列出雙向封包數、UDP 負載位元組及平均位元率。

上行是玩家送往伺服器，下行是伺服器送往玩家。計數採本機 socket 成功接受轉送的 UDP 負載長度，只保存長度與數量。網卡線速、IP／媒介額外負擔與跨機實測另驗。需要同時量測往返時可加 `--link-metrics`，報表會標記探測啟用，計數包含這些探測訊息。 [量測驗證](PROGRESS.md#2026-11-09-同機-udp-流量量測)

可用 `--udp-periodic-loss` 量測同機固定比例雙向丟包，並核對原始戰績是否仍由同一連線確認。 [五房丟包驗證](DESKTOP_EXERCISE.md#五房-udp-丟包驗證)
