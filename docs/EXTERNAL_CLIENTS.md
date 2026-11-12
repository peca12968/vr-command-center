# 分開啟動玩家與遊戲伺服器

## 遊戲版本相容性

遊戲 0.50.2 使用 NGO 協定 31。Windows 遊戲伺服器、Windows 玩家與 Quest APK 請使用同版。升級時先結束現有場次，再一併更新遊戲伺服器及玩家端。API 0.31.0 供應玩家票券及世界回放，戰績回條搭配管理包 0.31.109。MR 伺服器須搭配支援 `SetRoomAlignment` 的管理服務。 [玩家戰績回條](SESSION_CLOSURE.md#玩家戰績回條) · [鎖定房間校正檔](QUEST3.md#啟動-mr-伺服器前鎖定校正檔)

新版以二進位 UUID、打包整數與欄位旗標傳送角色狀態。連線房間同步完整角色清單，以完整浮點精度傳送位置、面向與射擊向量。

在原生 Windows 驗證中，0.46.0 玩家攜有效票券會在入場核准前遭 0.47.0 伺服器拒絕。同一張票券由 0.47.0 使用時成功入場並取得戰績。 [版本與流量驗證](PROGRESS.md#2026-11-09-壓縮即時角色同步)

### 發送前離線核對交付套件

先完整解壓三個 Windows 套件，把 Quest 開發 APK 與同名的原始 `.receipt.json` 放在一起。使用 Unity 的 Android SDK Build Tools 36.0.0 及 OpenJDK，在儲存庫執行下列命令並替換路徑。

```powershell
$release = python scripts/verify-venue-release.py `
  --control 'C:\Delivery\VRCommand-ControlServer' `
  --server 'C:\Delivery\VRCommand-GameServer' `
  --player 'C:\Delivery\VRCommand-Player' `
  --quest-apk 'C:\Delivery\vr-command-quest-0.50.2-arm64-debug.apk' `
  --sdk 'F:\Unity\AndroidPlayer\SDK' --jdk 'F:\Unity\AndroidPlayer\OpenJDK'
if ($LASTEXITCODE -eq 0) {
    $release | Set-Content -LiteralPath .\venue-release.json -Encoding utf8
}
```

通過時輸出一行 `verified: true` 的 JSON，列出管理版本、Windows 共同遊戲檔案數，以及 Quest 版本、雜湊和簽章憑證摘要。工具逐檔核對 Windows 清單與兩包的共用遊戲檔案，再比對 Quest 與 Windows 的建置來源及場景網路識別。APK 會另查驗套件 ID、ARM64、OpenXR 函式庫及 v2 簽章。若拒絕，請保留錯誤與原檔，重新取得配套交付物後再核對。這項唯讀檢查的範圍是交付物一致性，實際連線及頭盔運行請依後文驗收。

成功的 `venue-release.json` 可供 Quest 部署工具逐席核對裝置上已安裝的 APK。重新產生的報告也含 `windows.playerManifestSha256`，可供 Windows 玩家啟動器 1.6 在每台電腦核對主控交付的原套件。主控將同一份報告交給各 Windows 席位，玩家連線檔仍按席位個別交付。 [Quest 部署](QUEST3.md#核對頭盔內已安裝的發行-apk) · [Windows 核對](WINDOWS_PLAYER_PACKAGE.md#依場館發行報告核對玩家包)

## 分開啟動程式

Windows 遊戲伺服器包可獨立啟動既有 Preparing VR 場次。CLI 已通過同機五房獨立與 Linked，WinForms 已驗證載入場次、啟動和封存後停止。 [Windows 遊戲伺服器包](WINDOWS_SERVER_PACKAGE.md)

啟動器 1.10 可從視窗或命令列使用一份場館計畫，啟動五個獨立來源或一個合併來源。搭配管理包 0.31.100 或以上，等全館就緒檔確認各場的 UDP 綁定及整批端點公告後，再從控制台配票。 [下載場館計畫](WINDOWS_SERVER_PACKAGE.md#從主控台下載場館計畫) [五房視窗操作](WINDOWS_SERVER_PACKAGE.md#從-windows-視窗核對並啟動)

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

控制台 0.31.101 會在新批次公告的端點上檢查原遊戲來源。房卡顯示「遊戲來源暫未確認，暫停配票」時，請等候原來源回傳同階段、最近五秒的有效畫格。管理服務在單席、整房與全館下載時重新檢查。原端點仍可從房卡查閱，已簽發的連線檔沿用原驗票期限及 admission。這項檢查適用於由 0.31.101 以上管理服務首次整批公告的端點。

控制台 0.31.102 的 VR 及混合五房配票預覽會跟隨房卡狀態。原來源暫停更新時，已開啟的預覽會停用下載。原場次、端點及名冊相同且來源恢復後，原預覽可以繼續操作。名冊或場次改變時，請重新讀取。下載仍須由操作員點選。

控制台 0.31.4 的「整房配票」列出本場次中有玩家、且操作員有權配票的房間。核對遊戲伺服器 IPv4 和埠，選擇房間後按「下載房間連線檔 ZIP」。全館主控可逐房操作，房控可為自己的房間配票，Linked 場次也依同樣權限處理。

例如 `room-03-connections.zip` 裡的 `room-03-seat-01.json` 對應房間 3 的席位 1。按控制台名冊核對席位，個別交付 JSON。ZIP 最多含五份連線檔，皆使用五分鐘票券。VR 連線檔採四欄格式，MR 連線檔另帶 `roomAlignmentSha256`。整份 ZIP 由負責配票的操作員保管。

Quest MR 滿席部署可先用清單一次核對五房 ZIP、場次 ID、端點及各房校正檔，再逐席部署。 [五房 25 席部署預檢](QUEST3.md#五房-25-席部署預檢)

`POST /api/sessions/{id}/rooms/{roomId}/join-ticket-bundle` 接受 IPv4、埠與該房間完整的玩家 ID 及 admission ID。服務以一次名冊快照核對整組後才產生 ZIP，成功回應帶 `Cache-Control: no-store`。名冊已變更時回應 409，重新整理後核對席位再下載。MR 的單席與整房配票須先由主控鎖定該房校正檔，否則回應 409 `mr-alignment-required`。遊戲伺服器依當前 admission 驗票，名冊異動會使相應的舊票券失效。

### 下載前再次核對名冊

控制台 0.31.74 收到已簽發的連線檔後會再向管理服務讀取名冊。單席核對原玩家、房間、席位與入場識別。整房核對原本要配票的完整房間名冊。五房 VR、MR 或混合配票會一起核對五房，並對照適用的來源端點及校正版本。如果檔案傳送期間已更換入場或結束原場次，控制台會停止下載。請重新整理、確認新名冊，再重新配票。

### 在管理台核對 VR 單席連線檔

控制台 0.31.124 可在 VR 場次的玩家名冊下方開啟「VR 席位連線檔核對」。選擇要交付的席位，再上傳原始連線 JSON（最多 2 KiB）。主控可核對整場，房控只能核對本房。管理服務比對原票券簽章、場次、席位、目前入場識別及已公告的 IPv4／UDP 埠，並要求原遊戲來源最近五秒內有同階段的有效畫格。

核對成功時會顯示目的地與票券效期，loopback 顯示「僅同機」。如果畫面顯示原來源尚未公告或畫格過舊，待遊戲端更新後可再用同一份有效連線檔核對。手動填寫的目的地若和公告不同，請核對公告並重新下載。這項核對是管理端的取樣，玩家 UDP 可達性、頭盔追蹤及實體場地各有驗收流程。 [兩端 UDP 預檢](#開場前核對兩端-udp)

API 使用 `POST /api/sessions/{id}/rooms/{roomId}/players/{playerId}/vr-connection-check`，`If-Match-Admission` 帶目前的入場識別，JSON 內的 `connectionFile` 是原檔 Base64。結果回傳狀態、席位、公告端點和成功票券效期，回應帶 `Cache-Control: no-store`。核對時只讀取場次與錄製狀態，原 MR 校正檔仍使用 [MR 席位核對](QUEST3.md#在管理台核對席位部署檔)。

## VR 五房配票

管理包 0.31.41 起，全館主控可在五房總覽點「讀取五房名冊」。先準備五個獨立 VR 場次或一個五房合併 VR 場次，為每房加入五名玩家，並讓各遊戲伺服器公布端點。核對畫面中的任務、端點、房間、席位及玩家姓名，再按「下載五房連線檔 ZIP」。畫面會標示只能同機使用的 loopback 端點。

`vr-venue-connections.zip` 內含 `venue.json`、五個原格式的分房 ZIP 及共 25 份四欄玩家連線檔。分房 ZIP 依房號命名，每個 JSON 依房號與席位命名。票券自簽發起有效五分鐘，請將對應的 JSON 個別交給玩家，整份 ZIP 由主控私下保管。Windows 玩家啟動器可再次核對檔內標示的房間與席位。 [玩家端核對](PLAYER_CONFIG_REVIEW.md#連線檔席位與效期)

### 依電腦分發 Windows VR 連線檔

主控可用 PowerShell 7 及原始 `vr-venue-connections.zip` 或 `vr-mr-venue-deployment.zip` 匯出指定 Windows 席位。先準備一份版本 1 的對照表，房號與席位均為 1 到 5。`station` 是電腦標籤，開頭須為英文字母或數字，全長至多 32 字元，可用英文字母、數字與連字號。每台電腦與每個席位只填一次。

```json
{"version":1,"seats":[{"roomId":1,"seat":2,"station":"PC-A"},{"roomId":5,"seat":4,"station":"PC-B"}]}
```

簽發後在主控電腦執行。`-ManagementApi` 使用管理服務的本機 HTTP 或 HTTPS 原點，並在目前程序提供既有的 `VR_COMMAND_MASTER_KEY` 環境變數。輸出目錄須是私人資料夾下的新路徑。

```powershell
pwsh -NoProfile -File .\scripts\deploy-quest.ps1 `
  -VenueBundle .\vr-venue-connections.zip -ManagementApi http://127.0.0.1:5080 `
  -WindowsSeatMap .\windows-seat-map.json -WindowsOutputDirectory 'F:\private\windows-seats'
```

搭配管理包 0.31.148，工具在寫入暫存目錄前及正式交付前各核對一次全館 25 份原票券、現行入場、遊戲端點及近期原來源畫格。核對成功後才一次交付對照表中的原 VR 連線檔，例如 `pc-PC-A-room-01-seat-02.json`。若來源在暫存期間停止更新，工具會指出受影響的房間和席位並移除這批暫存。來源恢復且原票券仍有效時，可用同一份 ZIP 重新執行。

選到 Quest 3、MR 房間、重複席位、過期票券或過時名冊時，整批拒絕。成功摘要列出每台電腦的檔名、端點與效期，並記錄 `liveSourceVerified: true`。純 VR 同機排演可使用 loopback，玩家只能在遊戲伺服器所在電腦使用該目的地。跨機仍須使用場館 LAN 端點。

把每份 JSON 私下交給對應電腦。玩家在該電腦用解壓後的 `Launch-Player.exe --config <該台連線檔> --launch --openxr --wait` 加入。Quest 席位可從同一份原場館 ZIP 使用 Quest 的批次部署流程。 [Windows OpenXR 啟動](WINDOWS_PLAYER_PACKAGE.md#windows-openxr-啟動) · [Quest 席位部署](QUEST3.md#部署指定的-quest-席位)

下載使用各來源已公布的位址和埠。五房獨立須使用各自的端點，合併場共用同一端點。若名冊、場次或來源已變更，請重新讀取五房名冊。尚未填滿的場館可沿用單席或整房配票。

主控可用 `GET /api/vr-deployment/venue` 讀取預覽。向 `POST /api/vr-deployment/venue-bundle` 送出同一預覽的 `topology` 以及五個 `rooms`，每房提供 `roomId`、`sessionId`、公布的 `streamId` 和五筆 `players` 的 `playerId`、`admissionId`。服務以同一份現行場館快照核對所有房間。任何一房不符時回應 409，附對應房號，整批無 ZIP。

管理包 0.31.42 提供 `POST /api/vr-deployment/venue-check`，限主控。請求提供 `topology` 與五筆 `rooms`。每房提供 `roomId`、`sessionId` 及依席位排序的五份 Base64 `connectionFiles`，回傳逐席的票券、端點及現行名冊核對狀態，以及成功席的裝置類型。Quest 部署工具可直接讀取原 ZIP 使用此端點。 [Quest 部署操作](QUEST3.md#直接使用-vr-五房連線-zip)

純 VR Windows 匯出另傳 `requireLiveSource: true` 及 `allowLoopback: true`。後者允許純 VR Windows 同機端點，仍須通過票券、名冊及來源時效核對。Quest 的實機部署依原 LAN 條件檢查。

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

### 將 UDP 預檢納入封存驗收

保留兩端的原始報告。單場驗收可在原指令加上 `--udp-preflight .\listener-room-01.ndjson .\probe-room-01.json`。全館清單可在各 `sessions[]` 加入 `"udpPreflight": {"listener":"listener-room-01.ndjson","probe":"probe-room-01.json"}`。獨立場五房各用自己的原始報告，合併場使用共用端點的一組報告。

驗收工具使用 PowerShell 重新配對兩端報告，核對遊戲伺服器原綁定位址及埠，以及至少一位已收到伺服器戰績確認的玩家 UDP 來源。預檢須使用含 UTC 完成時間的報告，監聽端完成時間須在啟動器觀察綁定前 30 分鐘內。同一場館批次提供預檢時須涵蓋所有場次。摘要只列樣本數與交換摘要。實體主機身分與容量仍需現地驗收。

### 核對每個玩家來源的 UDP 預檢

若要核對所有玩家來源，在每個遊戲端點啟動前，依玩家預計使用的來源 IPv4 各跑一次雙端探測。同一遊戲埠可等上一組監聽程序退出後再使用。保留每組的原報告，最後仍以原入場及戰績確認所對應的實際 UDP 來源核對。獨立場按各自的埠處理，合併場則按共用的埠逐一核對來源。

單場在原驗收指令中重複加入 `--udp-source-preflight LISTENER PROBE`。全館清單在每個 `sessions[]` 填 `udpSourcePreflights`，例如下列兩組原報告。選用這個模式時，該批每場都需要使用相同模式。

```json
{
  "udpSourcePreflights": [
    {"listener": "probe-a-listener.ndjson", "probe": "probe-a.json"},
    {"listener": "probe-b-listener.ndjson", "probe": "probe-b.json"}
  ]
}
```

每個遊戲綁定的實際來源 IPv4 必須恰有一組有效報告。驗收會拒絕缺少、來源重複、未確認來源、重複交換摘要或過期的報告。單場摘要的 `udpSourcePreflight` 列出觀察到及驗證成功的來源數，和各組樣本數與交換摘要。全館另有 `udpSourcePreflightsVerified`。多席共用同一個來源 IPv4 時，在該遊戲埠只算一組。Windows 玩家用 PowerShell 探測，Quest 可使用獨立診斷 APK 產生同格式報告，遊戲入場和戰績仍另留原始 logcat。實體設備數及跨機容量須現場核對。 [Quest UDP 預檢](QUEST3.md#開場前從頭盔執行-udp-預檢) · [Quest 日誌](QUEST3.md#收集-quest-場館驗收日誌)

Quest 批次工具的原報告可直接加入封存驗收清單。只有一份時在頂層填 `udpPreflightBatch`，分批收集時填 `udpPreflightBatches`，例如 `["quest-a/preflight-report.json","quest-b/preflight-report.json"]`。兩個欄位擇一。若場次另有 Windows 玩家，在該場 `sessions[]` 的 `udpSourcePreflights` 補上 Windows 原報告。

驗收依原房號與模式合併。Quest 原始檔路徑以各批次報告所在目錄為準，逐場補上的路徑以封存驗收清單所在目錄為準。所有報告合起來須覆蓋每個原端點和所有已確認來源。若同一個來源 IPv4 在同一端點已有有效報告，只保留一組。原綁定位址、埠、完成時間及已確認來源仍會逐組核對。 [Quest 批次預檢](QUEST3.md#批次預檢五房-quest-席位)

### 開場前核對五房 UDP 報告

Windows 與 Quest 混用時，可在啟動遊戲伺服器前先核對報告是否齊全。沿用版本 1 網路清單的 `mode`、`endpoints` 與 `sources`，在 `sources` 填本次預計使用的房號、席位和來源 IPv4，至少涵蓋五房各一席。共用來源 IPv4 的席位可填相同位址。同一端點只需要一組該來源的報告，五房獨立時則各埠分開核對。整份清單使用私有 LAN 位址或使用 loopback 進行同機演練。 [網路清單格式](QUEST3.md#批次預檢五房-quest-席位)

將手動取得的 Windows 或 Quest 雙端報告列在 `pairs.json`。`listener` 與 `probe` 的相對路徑以這份清單所在的目錄為準。

```json
{
  "version": 1,
  "pairs": [
    {"listener": "windows/room-1-listener.ndjson", "probe": "windows/room-1-probe.json"}
  ]
}
```

可一併加入原 Quest 批次報告，每份使用一個 `--batch`。只有批次報告時可省略 `--pairs`。

Quest 批次重試完成後，`--batch` 指向最新完整的報告，並保留各輪原始資料夾供工具核對。 [重試 Quest 預檢](QUEST3.md#重試-quest-udp-預檢席位)

使用 Windows 批次啟動時，也可提供啟動器 `--venue-check` 產生的原成功預覽。在 UDP 監聽工具啟動前或退出後產生預覽，並使用實際要啟動的那份計畫。要將報告交給原封存驗收，啟動計畫的公告 IPv4 和本機綁定 IPv4 都填成網路清單上的同一個具體位址。

```powershell
& .\Launch-Server.exe --venue-check 'C:\VRCommand\venue-plan.json' --report 'C:\VRCommand\venue-preview.json'
python .\scripts\check-venue-udp-preflight.py `
  --network-plan .\venue-network.json --pairs .\pairs.json `
  --batch .\quest-a\preflight-report.json --launcher-preview 'C:\VRCommand\venue-preview.json' `
  --output .\venue-readiness.json
```

報告依房間端點列出各來源涵蓋的席位。`missing` 代表還缺一組，`duplicate-pair` 或 `duplicate-exchange` 代表需排除重複報告，`invalid-or-expired` 代表原雙端報告不符或已超過 30 分鐘。`unmatchedPairs` 和 `unreadablePairs` 分別計算不在本次計畫內及無法讀取的組數。補齊後使用新的輸出檔重跑。所有來源通過且沒有多餘或無法讀取的報告時，程式以 `0` 結束。

指定 `--launcher-preview` 後，預覽的模式、房間、UDP 埠、公告 IPv4 與本機綁定 IPv4 也須全部相符。`launcherPreview.groups` 會標出哪個房間端點不符，即使各席的雙端報告本身有效，整體仍回報未完成。報告會保存原預覽檔的 SHA-256。修正後請對實際要用的計畫重新產生預覽並核對。

可將完整報告的路徑填入封存驗收清單的 `udpPreflightBatch`。原雙端報告須一併保留。結束後，驗收工具會用遊戲伺服器實際綁定時間與已確認的玩家來源重驗每組。`network` 為 `same-host` 的結果只代表同機 UDP，跨機連線與頭盔仍須現場測試。

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

### 核對原程序的重連歷程

單場可加 `--verify-reconnect-history`，五房清單可填 `"verifyReconnectHistory": true`。開場前先啟用伺服器的 UDP 來源診斷。各席須提供同一原程序的完整 Windows 日誌或單一 PID 的 Quest logcat，並填寫該席本次任務使用的 IPv4。此模式適用於來源 IPv4 相同的重連，UDP 埠可以改變。

驗收會比對每條已連線記錄的伺服器核准及 UDP 來源，確認舊連線在下一條核准前已由伺服器釋放，最後一條才有原戰績確認。無法歸入任何玩家日誌的伺服器來源記錄會使驗收失敗。`reconnectHistory` 提供總連線數、已釋放的舊連線數與重連房號席位。入場識別以最後封存的原戰績核對，歷史來源記錄提供連線識別與順序。 [伺服器來源診斷](WINDOWS_SERVER_PACKAGE.md#跨機來源診斷)

#### 核對重連席位的回放區間

五房清單開啟 `verifyReconnectHistory` 並提供所有原始 `worldJournal` 後，可再填 `reconnectWindow`。從該席原場次的回放取第一格姿態無效與第一格恢復有效姿態的世界序號。房號與席位由 1 起算。

```json
{
  "verifyReconnectHistory": true,
  "reconnectWindow": {
    "roomId": 5,
    "seat": 2,
    "firstUnavailableSequence": 297,
    "recoveredSequence": 603
  }
}
```

工具核對中斷前一格至恢復格均在任務執行中，指定席位至少有兩格連續無有效姿態，恢復格有效，且其餘 24 席維持存活及有效姿態。獨立房間依各自原始 UTC 擷取時鐘對齊。回放有超過 500 毫秒的取樣缺口、停滯，或任何其他席位也中斷時，這段驗收會失敗。摘要列出房席、三個原始畫格、擷取時間與觀察到的無效期間。UDP 日誌另核對歷次連線順序，回放時間代表伺服器接受姿態的畫格時間。

### 核對原始回放檔頭與封存

如要一併驗收原生回放檔，等啟動器回報 `sealed-stopped` 後，從其 `workDirectory` 下的 `telemetry` 保留 `<sessionId>.worldlog`。在單場命令加入 `--world-journal .\room-01.worldlog`。工具唯讀檢查每筆記錄的校驗碼與連續影格，並將完整檔頭與啟動器封存報告比對，包含場景物件的位置與角度、任務時鐘、校正設定、規則及呈現版本。物件座標與角度依遊戲的單精度數值比較，舊檔省略的版本欄位依原預設值零比較。它確認原檔含活動中影格及兩種封存的尾界，再輸出檔案 SHA-256、總影格數及活動中影格數。活動中影格須為 `Running`、tick 大於零且未中止來源。原生回放檔逐筆讀取，可超過文字日誌的 16 MiB 上限。 [原生世界紀錄](WORLD_SOURCE.md)

### 從原始戰鬥日誌重算戰績

在同一個 `telemetry` 目錄保留 `<sessionId>.journal`，單場命令加入 `--combat-journal .\room-01.journal`。五房清單則在各 `sessions[]` 填寫 `"combatJournal": "room-01.journal"`，使用相對於清單的路徑。獨立模式需五份，合併模式需一份。可同時提供 `worldJournal`，各自核對戰鬥事件和回放畫格。

工具唯讀核對原場次、來源、每筆事件的校驗碼、連續序號、累計確認和終端封存，逐席重算耗彈、命中、擊殺、中彈、損耗、剩餘健康及命中率，再與已核對的管理統計和玩家結果比較。沒有戰鬥事件的場次也須有原完成與封存紀錄。任一檔案或戰績不一致時，整份驗收以退出碼 1 結束。成功摘要包含逐場 `combatJournal` 的 SHA-256、事件數及核對席位數，全館另有 `combatJournalsVerified`。

加入 `--verify-player-sources` 後，工具也會以原入場連結玩家日誌與封存回放，逐席列出房號、席次、來源、姿態種類及符合條件的活動影格數。Windows OpenXR 日誌須含原啟動順序、執行環境及同一 UDP 埠，回放須有對應的 `Tracked` 姿態。Unity Mock Runtime 會獨立標記為 `windows-openxr-mock-tracked`。一般 Windows OpenXR 回報 `windows-openxr-tracked`，桌面模擬回報 `windows-desktop-simulated`。Quest logcat 須核對原 PID、入場及 `Tracked` 姿態，回報 `quest-logcat-tracked`。名冊上的 VIVE XR 或 Quest 3 分類與實體裝置型號仍由現場核對。姿態與日誌來源不一致，或原席位在活動影格中從未接受連線姿態時，工具會拒絕本次核對。

`same-host` 要求全部觀察到的來源都在宣告的伺服器位址清單。`direct-lan` 要求至少有一個清單外的私有 IPv4，且所有玩家的實際來源均符合各自填入的位址。實體主機數與網路容量仍須現場確認，工具摘要分別保留 `physicalHostsVerified` 與 `networkCapacityAccepted` 為 `false`。NAT 或中繼環境需另記拓撲與轉譯結果。

Quest 3 席位使用 `--quest-player 192.168.1.21 '.\quest logcat.txt' 7342`，依序填頭盔本次使用的 IPv4、原始 logcat 路徑和遊戲程序 PID。可與 Windows 的 `--player` 混用。Quest 3 須登記在原名冊，且其 UDP 來源須在伺服器位址清單外。摘要的 `questLogcatPlayers` 只計算通過原入場及戰績核對的 logcat 檔案數。 [Quest 擷取方式](QUEST3.md#收集-quest-場館驗收日誌)

### 一次核對五房 25 席

兩種模式各準備一份私人 `venue.json`。使用 `--peer-diagnostics on` 啟動參與驗收的每個遊戲伺服器，並由主控一次結束全館。等待各場雙封存、原伺服器終止及玩家寫完戰績，保留同場啟動器 `--report`、原始 `server.log` 及每位玩家的完整日誌。

Windows 管理包 0.31.40 起，在「全館收尾」選取要驗收的批次，按「下載本批場館驗收 ZIP」，將原 ZIP 路徑填入 `venueBundle`。工具在記憶體內讀取原 `closure.json` 和各場 ZIP，以啟動器報告的原場次識別配對。所有 Windows 玩家日誌可集中填入 `windowsPlayers`，工具會以每份日誌的最終戰績識別配回原場次。兩份清單的順序都可自由排列。 [選取及下載原批次](SESSION_CLOSURE.md#下載本批場館驗收)

逐場保存的資料可沿用 `closure` 及各場 `evidenceZip` 欄位。以主控身分將 `GET /api/venue/closure/{id}` 的回應本文原樣保存為 `closure.json`。`{id}` 是該次全館結束回條的 `requestId`。

| 清單欄位 | 填寫內容 |
| --- | --- |
| `version` | 數字 `1` |
| `mode` | `Independent` 或 `Linked` |
| `topology` | `same-host` 或 `direct-lan` |
| `expectedPlayersPerRoom` | 選用。每房原場次須有的席數，填 1 至 5 的整數。省略時為 5，按全館 25 席核對 |
| `serverIps` | 所有本次伺服器電腦已指派的 IPv4，使用字串陣列 |
| `venueBundle` 或 `closure` | 原批次的場館驗收 ZIP 路徑，或原 `closure.json` 路徑。選一種 |
| `venueDebriefReceipts` | 選用。從同一批次下載的戰績回條 JSON 路徑 |
| `verifyPlayerSources` | 選用。填布林值 `true` 核對所有原席位的日誌與姿態。每場均須提供 `worldJournal` |
| `verifyTrackingBegin` | 選用。填布林值 `true` 核對同一批追蹤開場採用的原始準備中畫格及後續執行畫格。每場均須提供 `worldJournal` |
| `minimumConcurrentMilliseconds` | 選用。填 1,000 至 900,000 的整數，要求本階段全數席位同時連線且遊戲持續執行的最短毫秒數。每場均須提供 `worldJournal` |
| `requireTrackedRoster` | 選用。填 `true` 時須一併設定 `minimumConcurrentMilliseconds`，並逐席核對同一區間的追蹤姿態及原始玩家日誌 |
| `requireConcurrentFire` | 選用。填 `true` 時須一併設定 `minimumConcurrentMilliseconds`，並在每場提供 `worldJournal` 與 `combatJournal`。要求本階段每個原席位在同一段合格區間各有一次已封存射擊 |
| `udpPreflightBatch` 或 `udpPreflightBatches` | 選用。單份完整的場館 UDP 核對報告或原 Quest 批次報告路徑，也可填 1 至 25 份報告路徑的陣列。可搭配逐場 `udpSourcePreflights` |
| `questCaptures` | 選用。填原 Quest 網路計畫或裝置對照表，以及 1 至 25 份原擷取報告。可與 UDP 預檢報告一併使用 |
| `questDeployments` | 選用。填原離線發行報告及 1 至 25 份正式 Quest 部署報告，核對原入場及 APK 雜湊 |
| `venueReleaseReport` | 選用。核對全館所有 Windows 與 Quest 席位共用的原發行報告。Quest 的 `questDeployments` 此時只填 `reports` |
| `sessions` | 獨立模式填五場，合併模式填一場 |
| `sessions[].launcherReport`、`serverLog` | 各場啟動器終止報告及伺服器日誌的路徑 |
| `sessions[].evidenceZip` | 使用 `closure` 時填各場原 ZIP。使用 `venueBundle` 時省略 |
| `sessions[].worldJournal` | 選用。若驗收回放檔，每個場次都填自己關閉後的原始 `.worldlog` 路徑 |
| `sessions[].roomAlignments` | 選用。核對 MR 校正時，每個 MR 場次按房號填原校正檔，例如 `{"2":"room-02-alignment.json"}` |
| `sessions[].udpPreflight` | 選用。每場提供原 UDP 預檢報告的 `listener` 與 `probe` 路徑 |
| `sessions[].udpSourcePreflights` | 選用。每場按實際來源 IPv4 填一組 `listener` 與 `probe`。可補上 Quest 批次以外的來源 |
| `windowsPlayers` | 選用。集中填入所有 Windows 席位，每筆提供玩家裝置實際使用的 IPv4 `address`，再填原日誌路徑 `log` 或原玩家驗收 ZIP 路徑 `evidenceZip` |
| `windowsEvidenceDirectory` | 選用。Windows 玩家 ZIP 收件資料夾。與 `windowsPlayers` 擇一 |
| `windowsSeatMap` | 選用。收件資料夾用的版本 1 Windows 電腦對照表。混合 Quest 場次須指定應收的 Windows 席位 |
| `windowsLinkCriteria` | 選用。場館填入 `minimumReplies` 和 `maximumP95RoundTripMs`，逐席驗收原 Windows 連線量測。 |
| `sessions[].players` | 逐場填寫尚未由 `windowsPlayers` 或 `questCaptures` 提供的席位，每筆填實際 IPv4 `address` 及原日誌路徑 `log`。手動填入 Quest 3 原 logcat 時另填數字 `logcatPid`，例如 `7342`。該場席位已全部由前兩欄提供時可省略 |

路徑可以是絕對路徑，或相對於 `venue.json` 所在資料夾。同一檔案只能使用一次。以下是五房獨立模式的 Windows 範例，請依現場配置填入實際地址與檔名。混合場可改用 `questCaptures` 或逐場補上 Quest 原 logcat。兩種方式合計每房須有五席。

若有填寫 `venueDebriefReceipts`，驗收會將檔案與已通過原始日誌驗證的場次、封存尾界及原入場名冊逐席比對。任何缺席位或未確認回條都會使核對失敗。成功摘要的同名欄位列出回條檔 SHA-256、場次數及 25 個已確認席位。 [下載回條](SESSION_CLOSURE.md#下載本批戰績回條)

```powershell
$sessions = 1..5 | ForEach-Object {
    @{
        launcherReport = "Room $_/server-final.json"
        serverLog = "Room $_/server.log"
        worldJournal = "Room $_/original.worldlog"
    }
}
$windowsPlayers = Import-Csv .\windows-logs.csv -Header address,log |
    ForEach-Object { @{ address = $_.address; log = $_.log } }
@{
    version = 1
    mode = 'Independent'
    topology = 'direct-lan'
    serverIps = @('192.168.1.10', '127.0.0.1')
    venueBundle = 'vr-command-venue-field-v1-<批次 ID>.zip'
    sessions = @($sessions)
    windowsPlayers = @($windowsPlayers)
} | ConvertTo-Json -Depth 6 | Set-Content -Encoding utf8 .\venue.json
python scripts/verify-field-results.py --venue-manifest .\venue.json
```

`windows-logs.csv` 的每列依序填 IPv4、日誌路徑，不加標題列。五房合併模式將 `mode` 設為 `Linked` 並在 `sessions` 填一場，仍提供 25 席的日誌。

摘要核對五房各五個席位、原封存來源、每位玩家的原入場與 UDP 來源，以及 25 筆伺服器戰績確認。它逐房列出在伺服器位址清單以外的玩家數。`direct-lan` 至少須觀察到一筆這類連線，仍須依實際設備及網路拓撲核對主機數、同時遊玩與容量。

提供回放檔的整批驗收會逐場比對完整檔頭，檢查最後影格已觀察到該批結束指令，並輸出 `worldJournalsVerified` 與逐場摘要。回放畫面及遊戲事件內容可用原回放介面另行檢視。

### 分階段驗收 5 人與 10 人

5 人階段在五房各登記 1 席，10 人階段各登記 2 席。使用一般全館開始及全館結束，按每個階段與模式保留一份原場館驗收 ZIP、原封存和完整日誌。將 `expectedPlayersPerRoom` 分別填成 `1` 或 `2`，沿用 `verify-field-results.py --venue-manifest`。驗收會逐房確認宣告的席數、原席位、UDP 來源及伺服器戰績確認，結果同時列出每房預期席數與實際人數。合併場的總人數相符時，仍須核對每房的席數。

需要核對同時在線時，加上 `minimumConcurrentMilliseconds` 並提供每場原 `.worldlog`。現場每席有各自的 IPv4 時，也可加上 `requireDistinctRemoteRoster`，用同一個欄位核對該階段每位玩家的原 UDP 來源。25 人階段可省略 `expectedPlayersPerRoom`。

#### 一次驗收兩種模式的三個階段

準備六份 `venue.json`，每份都保留該批原始場館封存、遊戲日誌及同一份 `venueReleaseReport`。各批清單啟用 `minimumConcurrentMilliseconds`，並提供所有原 `.worldlog`。將六份清單的路徑填入 `stages.json`。路徑相對於 `stages.json`，清單列出的順序可調整。

```json
{
  "version": 1,
  "topology": "direct-lan",
  "minimumConcurrentMilliseconds": 10000,
  "venueManifests": [
    "5-independent/venue.json",
    "5-linked/venue.json",
    "10-independent/venue.json",
    "10-linked/venue.json",
    "25-independent/venue.json",
    "25-linked/venue.json"
  ]
}
```

```powershell
python scripts/verify-field-results.py --venue-stages .\stages.json
```

工具會重驗六批原始資料，要求各模式的 5、10、25 人場次按原開始與結束時間依序完成。各批須符合總清單的拓撲與同時在線門檻，且不得共用原結束回條、場次、世界來源或入場識別。結果列出每批原結束回條、清單雜湊、開始與結束時間、同時在線區間及伺服器戰績確認。若要每席都有不同直連 IPv4，可在 `direct-lan` 總清單與六份批次清單都加上 `"requireDistinctRemoteRoster": true`。同機排演使用 `same-host`，現場實體主機數及網路容量仍須驗收。

### 核對 25 席各自的直連來源

每席使用不同 IPv4 的場館，可在原五房驗收清單加入下列欄位。請完整填寫 `serverIps` 的伺服器介面位址，並保留每席原程序的完整日誌、每場啟用 UDP 來源診斷的伺服器日誌及原封存 `worldJournal`。

```json
{
  "topology": "direct-lan",
  "minimumConcurrentMilliseconds": 10000,
  "requireDistinctRemoteRoster": true
}
```

以原 `verify-field-results.py --venue-manifest` 命令執行。工具先將原玩家日誌、伺服器的核准／UDP 來源／釋放和最終戰績逐席配對，並比對五房原錄製的共同執行時段。同一席重連可換 UDP 埠，IPv4 須維持相同。若兩席共用一個來源 IPv4、任一席使用伺服器位址，或原伺服器有無法配對的核准紀錄，嚴格驗收會拒絕。

成功摘要的 `distinctRemoteRoster` 列出核對席位、不同來源位址及歷次連線的數量。可同時使用 `requireTrackedRoster` 及 `requireConcurrentFire`。原始日誌中的網路位址保留在場館私人資料夾，摘要只列計數。實體裝置數與網路容量依現地驗收。

### 核對 25 席同時連線的區間

要核對至少一分鐘，在原場館清單加入 `"minimumConcurrentMilliseconds": 60000`，每場提供關閉後的原 `.worldlog`。工具逐格比對最終已核對的玩家與房號，要求全部原席位同時連線、場次處於執行中且遊戲 tick 向前。掉線、暫停、管理中斷、tick 停滯或相鄰畫格相差超過 500 毫秒，都會切斷區間。

獨立模式按五份錄製的 UTC 擷取時間求共同區間，合併模式直接使用該場錄製。跨機擷取前需校對各遊戲伺服器時鐘。通過時 `concurrentRoster` 會列出最長共同區間的毫秒數與 UTC 起訖。時長不足時，整份驗收會退出並回傳錯誤。這份結果核對的是封存快照，實際時鐘同步、頭盔操作、實體主機數及網路容量須另依場館驗收。

要驗收 25 席同時維持追蹤，在同一份清單再設定 `"requireTrackedRoster": true`。每個合格畫格須同時包含所有原席位的有效 `Tracked` 姿態，並沿用原有的 500 毫秒畫格間隔及執行狀態條件。此選項會自動核對 `playerSources`，逐席接受已配對原入場的 Quest logcat，或已完成 OpenXR 啟動且執行環境未標示為 Unity Mock Runtime 的 Windows 日誌。桌面模擬及已識別的 Mock Runtime 日誌會被拒絕。通過時 `concurrentRoster.rigKind` 為 `Tracked`，並附各場 `playerSources`。實體頭盔與主機身分仍需現場確認。 [驗收紀錄](PROGRESS.md#2026-11-10-核對-25-席同時追蹤的封存區間)

### 核對 25 席在共同區間開火

在原五房場館清單設定 `"requireConcurrentFire": true` 與 `"minimumConcurrentMilliseconds": 10000`，或填入該場驗收所需的毫秒數。每場保留原 `worldJournal` 與 `combatJournal`。25 席連線且任務持續執行時，讓每席至少開火一次，再結束全館並等待雙封存。

工具核對回放射擊與戰鬥日誌中的原事件、射擊、玩家及戰鬥序號。夾住射擊 tick 的前後畫格都須位於同一段五房共同區間。射擊造成的同 tick 額外畫格須等到 500 毫秒內的下一個前進 tick，才計入驗收。合格時 `concurrentRoster.playersWithConfirmedFire` 為 25，時間範圍取符合條件的最長區間。只連線或在共同區間之外射擊的席位會使驗收失敗。可與 `requireTrackedRoster` 一併啟用。實體設備數與跨機容量依現地驗收另行確認。

### 核對五房追蹤開場錄製

使用管理包 0.31.66 以「五房開場須各有 5 席追蹤就緒」開始，再由主控批次結束並下載原場館驗收 ZIP。在 `venue.json` 設定 `"verifyTrackingBegin": true`，並逐場提供原生 `worldJournal`。工具會核對 `closure.json` 中每場的 `trackingBegin` 指向同一開始批次，逐場查驗原來源、開始前管理序號、該格擷取時間偏移及 25 席的原始追蹤姿態。每場也要有觀察到開始序號的後續有效執行格。

結果中的 `trackingBegin` 列出原開始批次、場次數及通過核對的追蹤席位數。逐場 `worldJournal.trackingBegin` 列出原準備畫格、開始序號和第一格符合條件的執行畫格。管理包 0.31.65 或更早的開場仍可走一般封存核對。追蹤姿態、裝置來源與實體容量分別驗收。 [開場操作](PLAYER_READINESS.md#五房追蹤驗收開場)

### 核對五房有效姿態開場

若場次使用「五房開場須各有 5 席已連線且姿態有效」，用管理包 0.31.79 下載原全館收尾的場館驗收 ZIP。在 `venue.json` 設定 `"verifyParticipationBegin": true`，每場提供原 `worldJournal`。此選項與 `verifyTrackingBegin` 擇一。

工具從 `closure.json` 讀取 `participationBegin`，依原錄製核對同一次開場、管理序號、準備中畫格、25 位原名冊玩家及其房間，再找出各場在結束前套用開場的第一個有效執行格。VR 開場可核對合成或追蹤姿態，MR 須為追蹤。結果的 `participationBegin` 列出全館及逐場的確認席數，並分列合成與追蹤。 [開場操作](PLAYER_READINESS.md#五房各-5-席有效姿態開場)

### 核對五房環境與敵軍指令的執行畫格

在場次執行中送出「全館即時環境」或「全館敵軍策略」後，等各房顯示已套用，再按對應的「下載環境批次 JSON」或「下載敵軍批次 JSON」。控制台 0.31.127 會下載畫面所用的原 `GET /api/venue/phase` 回覆，檔名含批次 ID。每次都保留對應檔案，下一批同類指令會更新最新批次。待全館結束後，和各場原始 `.worldlog`、原場館驗收 ZIP 一併交給 `verify-field-results.py --venue-manifest`。

```json
{
  "venueControlBatches": [
    {"action": "SetEnvironment", "phaseReport": "storm-night.json"},
    {"action": "SetEnemies", "phaseReport": "advance-hold-fire.json"}
  ]
}
```

工具依原場次、房間及管理序號逐場找出有效的執行畫格。環境核對天氣、日夜及閃電；敵軍策略核對行為與自動攻擊開關。可用逐場 `worldJournal.venueControlFrames` 的 `worldSequence` 定位回放。需要確認的批次應在下一個管理變更前取得畫格。僅有較晚序號的相同設定，或只有暫停、暫緩及結束畫格時，該批驗收會失敗。

### 直接使用 Quest 批次擷取報告

在 `direct-lan` 場館清單加入下列欄位。保留每份原 `capture-report.json` 與同一資料夾內的原日誌。網路計畫使用 Quest UDP 預檢的版本 1 格式，列出這次五房所有遊戲端點，以及各 Quest 席位實際使用的 IPv4。 [網路計畫格式](QUEST3.md#批次預檢五房-quest-席位) · [整批擷取](QUEST3.md#一次擷取五房-quest-日誌)

```json
{
  "questCaptures": {
    "networkPlan": "network-plan.json",
    "reports": [
      "quest-capture-a/capture-report.json",
      "quest-capture-b/capture-report.json"
    ]
  }
}
```

首次與重試的原報告可一併列入。各報告保留原成功與失敗記錄，所有成功席位合起來須剛好涵蓋計畫列出的 Quest 席位，每席只接受一次完整擷取。工具重讀完整日誌核對位元組數和 SHA-256，再核對原程序、房號席位、伺服器觀察到的 IPv4、遊戲端點和戰績確認。成功摘要列出 `questCaptureBatchesVerified` 及 `questCaptureSeatsVerified`，若曾有未完成報告，另列 `questCaptureIncompleteReports` 與 `questCaptureFailedAttempts`。混合場可用 `windowsPlayers` 或 `windowsEvidenceDirectory` 補上 Windows 證據。手動提交 Quest 原日誌可沿用 `players` 及 `logcatPid`。 [重試失敗席位](QUEST3.md#重試未完成的-quest-擷取席位)

#### 以原 Quest 裝置對照表驗收收尾

收尾時可在 `questCaptures` 選用部署時的版本 1 `deviceMap` 及原 `reports`。工具依各席原程序的最後連線及伺服器戰績確認取得來源 IPv4，核對每個映射席位有各自的私有直連位址及正確遊戲埠。摘要會標示 `questCaptureAddressSource` 為 `server-observed`。選用原 `networkPlan` 時，工具會將伺服器觀察的來源與現場獨立記錄的 IPv4 比對。開場前的 UDP 預檢沿用原網路計畫。 [裝置與網路計畫](QUEST3.md#批次預檢五房-quest-席位)

```json
{
  "questCaptures": {
    "deviceMap": "device-map.json",
    "reports": ["quest-capture/capture-report.json", "quest-capture-retry/capture-report.json"]
  }
}
```

### 核對封存席位的 Quest 發行 APK

使用 `-ReleaseReport` 部署時，保存正式部署指令輸出的 JSON，以及用來部署的原 `venue-release.json`。使用 `-RetryIncomplete` 續跑時，可在五房 `venue.json` 只填最新的累計報告，或把它與一路承接的原報告一併填入。檔案可任意排序，請保留原始位元組。使用手動分批清單時，填各份報告，各份成功席位必須互不重複。 [Quest 部署操作](QUEST3.md#從原部署報告重試未完成席位)

```json
{
  "questDeployments": {
    "releaseReport": "venue-release.json",
    "reports": ["quest-deployment.json", "quest-deployment-retry.json"]
  }
}
```

驗收核對每個成功席位的原場次、玩家、入場名額、房號、席位、UDP 埠與 APK 版本。每席須有已核對 APK 及設定檔的啟動紀錄，並與原 Quest logcat、伺服器戰績確認及封存資料一致。提交重試歷史時，工具會核對前一份報告的 SHA-256、同一原部署及已完成席位，累計結果中的每席只計一次。歷史中斷、分岔或修改已完成席位都會拒絕。早期未記錄前一份雜湊的累計報告只需提交最新一份。摘要 `questDeployment` 列出版本代碼、APK 雜湊、報告數及核對席位數，成功核對報告承接時另列 `retryReportsLinked`。實體裝置與運行環境須現場驗收。

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

### 將 Windows 連線量測納入五房封存

使用 Windows 玩家啟動器 1.5，為每位 Windows 玩家指定不同的三個新檔案路徑。使用 Windows OpenXR 的席位可另加 `--openxr`。正常入場並讓任務執行至 30 次採樣完成，結束任務後保留玩家收到原戰績的程序日誌。等玩家程序退出且啟動器報告顯示 `exited` 後，再收集原檔。

```powershell
& .\Launch-Player.exe --config '.\room-01-seat-01.json' --launch --wait `
  --log 'C:\Private\room-01-seat-01.log' `
  --report 'C:\Private\room-01-seat-01-launch.json' `
  --link-metrics 'C:\Private\room-01-seat-01-link.json'
```

將 `launcherReport` 和 `linkMetrics` 加到五房清單中的原 `windowsPlayers[]` 列，也可加到逐場 `players[]` 的 Windows 列。選用時須提供全館每位 Windows 玩家的兩個原檔。Quest 席位沿用原 logcat。啟動器報告的 `linkMetrics` 欄位保存日誌及量測檔的 SHA-256，若缺檔則為 `null`。

```json
{"address":"192.168.1.20","log":"room-01-seat-01.log","launcherReport":"room-01-seat-01-launch.json","linkMetrics":"room-01-seat-01-link.json"}
```

`verify-field-results.py --venue-manifest` 會比對檔案雜湊、原玩家程序與伺服器確認戰績的最後一條連線，並檢查每份都有 30 筆已結案樣本。若量測後重連，先前連線的量測無法與最後戰績配對。成功摘要列出每席回覆、逾時、中斷及回覆的 p95；全數未回覆時 p95 為空值。量測反映遊戲訊息往返與排程，跨機網路容量仍需現場驗收。

### 核對全館共用的發行報告

把同一份 `venue-release.json` 用於 Windows 啟動及 Quest 部署。Windows 啟動器 1.9 可從視窗核對報告，遊戲關閉後交回同一資料夾的 `player.log` 和 `launch-report.json`。命令列可從啟動器 1.7 起加上 `--release-report`、`--wait`、`--log` 和 `--report` 留存同等資料。既有 1.6 場次可提供同次已完成的原連線量測檔，沿用其日誌雜湊。 [Windows 啟動操作](WINDOWS_PLAYER_PACKAGE.md#依場館發行報告核對玩家包)

五房封存清單頂層加入 `venueReleaseReport`。每個 Windows 席位在 `windowsPlayers` 或 `sessions[].players` 加入 `launcherReport`；需要驗證原量測時再加 `linkMetrics`。Quest 席位照常提供原 logcat，並把各批原部署報告放入 `questDeployments.reports`，共用頂層的發行報告。全館只有 Windows 席位時可省略 `questDeployments`。

```json
{
  "venueReleaseReport": "venue-release.json",
  "windowsPlayers": [
    {"address":"192.168.1.20","log":"pc-01.log","launcherReport":"pc-01-launch.json"}
  ],
  "questDeployments": {"reports": ["quest-a/deployment-report.json"]}
}
```

同一個 `verify-field-results.py --venue-manifest` 指令會核對所有席位。Windows 核對退出報告的清單雜湊、原日誌及伺服器確認的最終戰績。Quest 核對共用報告的 APK 雜湊、原部署、入場及戰績。缺少任何席位的原證據、換用其他席位的報告或使用不同發行包時，整批拒絕。成功摘要的 `venueRelease` 列出發行報告雜湊及各平台核對席位數。僅核對 Quest 時仍可沿用原有的 `questDeployments.releaseReport` 格式。實體設備與主機身分依現場驗收。

### 收集 Windows 玩家驗收 ZIP

玩家以啟動器 1.10 核對本次發行並完成場次後，從「開啟本次紀錄資料夾」取出 `player-evidence.zip`。請把每位玩家的原 ZIP 放在同批私人資料夾，並記錄該電腦本次使用的 IPv4。在 `venue.json` 保留 `venueReleaseReport`，於 `windowsPlayers` 或逐場 `players` 使用下列格式。

```json
{"address":"192.168.1.20","evidenceZip":"room-01-seat-01/player-evidence.zip"}
```

工具直接讀取 ZIP 內原日誌與退出報告。每席可使用 ZIP 或分開的 `log`、`launcherReport`，同一批可混用不同格式。 [玩家端操作](WINDOWS_PLAYER_PACKAGE.md#依場館發行報告核對玩家包)

需要量測時，Windows 啟動器 1.13 的玩家在視窗核對本次場館發行報告後，勾選「記錄本次連線量測」再開始遊戲。保留任務執行至每席 30 筆量測結案，再由主控結束任務。玩家收到最終戰績並關閉遊戲後，從本次紀錄資料夾交回 ZIP。

使用 1.14 時，玩家可在任務仍執行時查看啟動器的量測狀態並回報主控。`30／30` 代表樣本均已結案，實際回覆、逾時及中斷各自列出。提早停止會標示「連線量測已停止」，重新入場會標示先前量測未涵蓋目前連線。 [玩家視窗](WINDOWS_PLAYER_PACKAGE.md#依場館發行報告核對玩家包)

啟動器 1.12 或更新版本也可從命令列匯出原量測。每個 Windows 席位均使用獨立的新路徑。

```powershell
& .\Launch-Player.exe --config '.\room-01-seat-01.json' --launch --wait `
  --release-report '.\venue-release.json' `
  --log 'C:\Private\room-01-seat-01.log' `
  --report 'C:\Private\room-01-seat-01-launch.json' `
  --link-metrics 'C:\Private\room-01-seat-01-link.json' `
  --evidence-zip 'C:\Private\room-01-seat-01-evidence.zip'
```

交回 ZIP 即可使用收件資料夾或 `evidenceZip`。已有 `link-metrics.json` 的 ZIP 直接使用內含原檔，舊 ZIP 搭配散裝量測則使用逐席的 `evidenceZip` 及 `linkMetrics`。工具會核對原量測雜湊、程序 ID、30 筆樣本及伺服器確認戰績的同一條連線。

#### 按收件資料夾找缺件及錯批

將這一批玩家 ZIP 放進同一個私人資料夾。保留 `venueReleaseReport`、原場館封存、各場原啟動器報告與伺服器日誌，在清單填入 `"windowsEvidenceDirectory": "returned"`。混合 Windows 與 Quest 場次另填 `windowsSeatMap`，使用原本分發連線檔的電腦對照表。 [對照表格式](#依電腦分發-windows-vr-連線檔)

```powershell
python scripts/verify-field-results.py --venue-manifest .\venue.json --inspect-windows-inbox
python scripts/verify-field-results.py --venue-manifest .\venue.json
```

第一條指令列出應收及已收的 Windows 席位、缺件與有問題的檔名，缺件或衝突時以退出碼 1 結束。配對依據是原名冊的入場與場次識別、退出報告及原伺服器對該連線的戰績確認，玩家可自行命名 ZIP。每席的 IPv4 取自伺服器觀察到的對應 UDP 來源。需要另外指定各席預期的 IPv4 時，可沿用 `windowsPlayers`。

收件檢查也會核對 ZIP 內的連線量測。若本批有 Windows 席位提供量測，須由所有 Windows 席位提供，Quest 席位沿用原 logcat 流程。內含量測不符、遺失或覆蓋席位不足時，收件檢查會指出對應的 ZIP。

收件完成後執行第二條指令，工具沿用同一資料夾完成原場次封存及戰績驗收。混合場的 Quest 證據照原欄位提供，可在 Windows 收件檢查後補齊。

#### 逐席核對 Windows 連線量測門檻

收件報告的 `windowsLinkMetrics` 逐席列出 30 筆量測的回覆、逾時、中斷、回覆的 p95 往返時間及缺量測的席位。需要按場館規格驗收時，在 `venue.json` 加入 `windowsLinkCriteria`，將下例的數值替換為本次規格。

```json
{"windowsLinkCriteria":{"minimumReplies":28,"maximumP95RoundTripMs":40}}
```

兩個門檻均為整數。每席最低回覆數可填 1 至 30，最高 p95 可填 0 至 900 毫秒。p95 由收到回覆的樣本計算，回覆數為零時 p95 為空。收件報告保留檔案完整狀態，另以 `meetsCriteria` 表示量測是否齊全且逐席符合門檻，並以 `criteriaFailures` 列出未通過的欄位。收件或完整驗收遇到缺量測或超出門檻時，退出碼為 1。

完整驗收也支援逐席列出 ZIP 或散檔。通過時會保存門檻及核對席位數，多階段驗收亦會列出各批採用的門檻。省略 `windowsLinkCriteria` 時沿用原驗收規則。量測包含遊戲訊息往返和兩端排程，實體網路容量仍依現場驗收。

## 同機 UDP 流量量測

```powershell
python scripts/check-desktop-exercise.py --runtime-root "<新資料根目錄>" --api-dll "<管理 API DLL>" --player-exe "<Windows 遊戲 EXE>" --mode both --players-per-room 5 --seconds 40 --udp-traffic
```

工具為每個原玩家建立獨立 loopback 轉送器，沿用正常入場及遊戲輸入。各場次都觀察到 Running 後才開始，獨立模式還會等暫停房間確認恢復。所有玩家共用同一高解析度單調時鐘邊界，約每秒記一次累積計數。量測在任務結束前收束，報表按玩家、房間、全場及時間區間列出雙向封包數、UDP 負載位元組及平均位元率。

上行是玩家送往伺服器，下行是伺服器送往玩家。計數採本機 socket 成功接受轉送的 UDP 負載長度，只保存長度與數量。網卡線速、IP／媒介額外負擔與跨機實測另驗。需要同時量測往返時可加 `--link-metrics`，報表會標記探測啟用，計數包含這些探測訊息。 [量測驗證](PROGRESS.md#2026-11-09-同機-udp-流量量測)

可用 `--udp-periodic-loss` 量測同機固定比例雙向丟包，並核對原始戰績是否仍由同一連線確認。 [五房丟包驗證](DESKTOP_EXERCISE.md#五房-udp-丟包驗證)
