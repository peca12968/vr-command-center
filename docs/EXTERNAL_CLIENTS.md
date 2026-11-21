# 分開啟動玩家與遊戲伺服器

## 遊戲版本相容性

遊戲 0.50.12 使用 NGO 協定 31。Windows 遊戲伺服器、Windows 玩家與 Quest APK 請使用同版。升級時先結束現有場次，再一併更新遊戲伺服器及玩家端。API 0.31.0 供應玩家票券及世界回放，戰績回條搭配管理包 0.31.109 以上。MR 伺服器須搭配支援 `SetRoomAlignment` 的管理服務。 [玩家戰績回條](SESSION_CLOSURE.md#玩家戰績回條) · [鎖定房間校正檔](QUEST3.md#啟動-mr-伺服器前鎖定校正檔)

新版以二進位 UUID、打包整數與欄位旗標傳送角色狀態。連線房間同步完整角色清單，以完整浮點精度傳送位置、面向與射擊向量。

在原生 Windows 驗證中，0.46.0 玩家攜有效票券會在入場核准前遭 0.47.0 伺服器拒絕。同一張票券由 0.47.0 使用時成功入場並取得戰績。 [版本與流量驗證](PROGRESS.md#2026-11-09-壓縮即時角色同步)

### 發送前離線核對交付套件

先完整解壓三個 Windows 套件，把 Quest 開發 APK 與同名的原始 `.receipt.json` 放在一起。使用 Unity 的 Android SDK Build Tools 36.0.0 及 OpenJDK，在儲存庫執行下列命令並替換路徑。

需要帶到另一台電腦時，可在同一命令加上 `--field-kit 'C:\Delivery\VRCommand-Venue.zip'`。指定既有父目錄下的新 ZIP 名稱。工具會打包三套 Windows 程式、Quest APK 與建置回條、部署工具及同一次核對產生的發行報告。交付資料夾不需另放開發環境或玩家憑證。 [包內使用說明](VENUE_FIELD_KIT.md)

```powershell
$release = python scripts/verify-venue-release.py `
  --control 'C:\Delivery\VRCommand-ControlServer' `
  --server 'C:\Delivery\VRCommand-GameServer' `
  --player 'C:\Delivery\VRCommand-Player' `
  --quest-apk 'C:\Delivery\VrCommand.apk' `
  --sdk 'F:\Unity\AndroidPlayer\SDK' --jdk 'F:\Unity\AndroidPlayer\OpenJDK'
if ($LASTEXITCODE -eq 0) {
    $release | Set-Content -LiteralPath .\venue-release.json -Encoding utf8
}
```

通過時輸出一行 `verified: true` 的 JSON，列出管理版本、Windows 共同遊戲檔案數，以及 Quest 版本、雜湊和簽章憑證摘要。工具逐檔核對 Windows 清單與兩包的共用遊戲檔案，再比對 Quest 與 Windows 的建置來源及場景網路識別。APK 會另查驗套件 ID、ARM64、OpenXR 函式庫及 v2 簽章。若拒絕，請保留錯誤與原檔，重新取得配套交付物後再核對。這項唯讀檢查的範圍是交付物一致性，實際連線及頭盔運行請依後文驗收。

`quest.androidManifest` 來自已簽章 APK 內合併後的 AndroidManifest。工具核對同一個可啟動 Activity 是否在同一個 `MAIN` 篩選器宣告 Android 啟動與 Meta VR 分類，以及是否宣告 Quest 3、必要的第 1 版頭部追蹤、MR 透視與多人連線的 Internet 權限。Quest 3 可用 Meta 文件中的 `quest3`，或本專案既有 Unity OpenXR 開發包所產生的 `eureka`。 [Meta Android 開發清單](https://developers.meta.com/vr/documentation/native/android/mobile-native-manifest/) · [AAPT2 說明](https://developer.android.com/tools/aapt2)

`quest.nativeLibraries` 記錄已核對的程式庫數量及 Unity、IL2CPP、OpenXR 與 Meta MR 所需的檔名。工具讀取 APK 裡每個原生程式庫的 ELF 標頭，確認為 ARM64 共用程式庫，並核對程式標頭及載入、動態連結區段的檔案範圍。缺件、重複檔名、錯誤架構或區段超出檔案時會拒絕發行。 [Arm AArch64 ELF 規格](https://github.com/ARM-software/abi-aa/blob/main/aaelf64/aaelf64.rst)

報告也會記錄 `quest.androidManifest.extractNativeLibs`。若 APK 設為從檔案內直接載入，程式庫必須以未壓縮方式存放，資料起點須符合 4 KiB 對齊，核對通過後會列出 `quest.nativeLibraries.directLoadAlignmentBytes`。現行開發 APK 由安裝程式解出原生程式庫，可使用壓縮。 [Android manifest 屬性](https://developer.android.com/guide/topics/manifest/application-element#extractNativeLibs) · [Android APK 對齊](https://developer.android.com/tools/zipalign)

若兩包的建置來源或網路識別不同，錯誤會列出相異欄位，例如 `sourceFingerprint`。Windows 共用遊戲檔案不同時，會列出差異檔案總數及最多三個套件內相對路徑。APK 回條若已記錄套件 ID、SDK 版本、v2 簽章或簽署憑證 SHA-256，工具也會逐欄對照 Android 工具實測結果。較早的回條若省略這些欄位，仍依原 APK 雜湊與簽章檢查驗證。

成功的 `venue-release.json` 可供 Quest 部署工具逐席核對裝置上已安裝的 APK。重新產生的報告也含 `windows.playerManifestSha256`，可供 Windows 玩家啟動器 1.6 在每台電腦核對主控交付的原套件。主控將同一份報告交給各 Windows 席位，玩家連線檔仍按席位個別交付。 [Quest 部署](QUEST3.md#核對頭盔內已安裝的發行-apk) · [Windows 核對](WINDOWS_PLAYER_PACKAGE.md#依場館發行報告核對玩家包)

供遊戲伺服器的發行報告含 `windows.serverManifestSha256`。五房預覽與啟動可讀取同一份報告，逐檔核對解壓後的遊戲伺服器包。只有玩家套件摘要的舊報告，可用同版交付物重新產生。 [伺服器核對](WINDOWS_SERVER_PACKAGE.md#依場館發行報告核對伺服器包)

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
.\scripts\start-windows-vr.ps1 -Executable '<同版VrCommand.exe>' -Config '<自己的玩家連線檔.json>'
```

Quest仍使用[QUEST3](QUEST3.md)的部署方式，實機未驗。工具整場來源維持Simulation；external的`headsets`為null（工具不辨認遠端設備），不能因名冊Quest3分類或Tracked宣告就填成實測頭盔數。取得實機後的GameServer來源整合另驗，不在同一場混用來源。

## 按房間下載連線檔

控制台 0.31.165 在篩選至單一房間的名冊旁提供「下載房間連線檔 ZIP」。從全館開場表進入指定房間後，可直接使用這個按鈕。配票沿用下方的伺服器 IPv4 與埠，並在下載前重新核對該房原名冊。使用前請確認連線設定。

控制台 0.31.166 在名冊下載按鈕旁顯示即將寫入連線檔的 IPv4 與 UDP 埠。套用來源公告或手動調整欄位時會同步更新。端點欄位無效時，名冊下載會停用並提示先完成設定。

控制台 0.31.167 會核對以五房批次公告的原 IPv4 與 UDP 埠。當來源缺少有效畫格時，房間 ZIP 停用，名冊保留公告端點供查閱。手動欄位和原公告不符時，請按「套用場次連線設定」再下載。管理服務也會在簽發前核對，端點不符會回應 409 `ticket-endpoint-mismatch`。未使用批次公告的舊場次仍可手動配票。

控制台 0.31.168 可直接從玩家名冊補發單席連線檔。五房批次公告的場次會採用管理服務在單席票券回應附上的 `endpoint`，即使手動欄位空白或留有其他地址。原來源缺少有效畫格時停用單席配票，來源恢復後可重發。未使用批次公告的場次仍沿用手動欄位；MR 檔案保留該房鎖定的校正雜湊。

Windows 三包整合驗證可在 `--check-venue-roster-ui` 的指令加上 `--check-roster-room-tickets`。Chromium 逐房操作名冊捷徑並下載整房 ZIP。Windows 玩家包使用 ZIP 內原始連線檔入場，再核對原名冊及結算。 [重跑方式](PLAYER_READINESS.md#五房追蹤驗收開場)

控制台 0.31.101 會在新批次公告的端點上檢查原遊戲來源。房卡顯示「遊戲來源暫未確認，暫停配票」時，請等候原來源回傳同階段、最近五秒的有效畫格。管理服務在單席、整房與全館下載時重新檢查。原端點仍可從房卡查閱，已簽發的連線檔沿用原驗票期限及 admission。這項檢查適用於由 0.31.101 以上管理服務首次整批公告的端點。

控制台 0.31.102 的 VR 及混合五房配票預覽會跟隨房卡狀態。原來源暫停更新時，已開啟的預覽會停用下載。原場次、端點及名冊相同且來源恢復後，原預覽可以繼續操作。名冊或場次改變時，請重新讀取。下載仍須由操作員點選。

控制台 0.31.4 的「整房配票」列出本場次中有玩家、且操作員有權配票的房間。核對遊戲伺服器 IPv4 和埠，選擇房間後按「下載房間連線檔 ZIP」。全館主控可逐房操作，房控可為自己的房間配票，Linked 場次也依同樣權限處理。

例如 `room-03-connections.zip` 裡的 `room-03-seat-01.json` 對應房間 3 的席位 1。按控制台名冊核對席位，個別交付 JSON。ZIP 最多含五份連線檔，皆使用五分鐘票券。VR 連線檔採四欄格式，MR 連線檔另帶 `roomAlignmentSha256`。整份 ZIP 由負責配票的操作員保管。

Quest MR 滿席部署可先用清單一次核對五房 ZIP、場次 ID、端點及各房校正檔，再逐席部署。 [五房 25 席部署預檢](QUEST3.md#五房-25-席部署預檢)

`POST /api/sessions/{id}/rooms/{roomId}/join-ticket-bundle` 接受 IPv4、埠與該房間完整的玩家 ID 及 admission ID。服務以一次名冊快照核對整組後才產生 ZIP，成功回應帶 `Cache-Control: no-store`。名冊已變更時回應 409，重新整理後核對席位再下載。MR 的單席與整房配票須先由主控鎖定該房校正檔，否則回應 409 `mr-alignment-required`。遊戲伺服器依當前 admission 驗票，名冊異動會使相應的舊票券失效。

### 下載前再次核對名冊

控制台 0.31.74 收到已簽發的連線檔後會再向管理服務讀取名冊。單席核對原玩家、房間、席位與入場識別。整房核對原本要配票的完整房間名冊。五房 VR、MR 或混合配票會一起核對五房，並對照適用的來源端點及校正版本。如果檔案傳送期間已更換入場或結束原場次，控制台會停止下載。請重新整理、確認新名冊，再重新配票。

控制台 0.31.247 在單席下載前會比對票券內的場次、玩家、房號、席號、原入場及效期。整房 ZIP 使用該次的配票請求編號與 SHA-256 核對檔案。若檔案、來源或名冊已變更，可重新配票。票券簽章仍由遊戲伺服器驗證。

### 在管理台核對 VR 單席連線檔

控制台 0.31.124 可在 VR 場次的玩家名冊下方開啟「VR 席位連線檔核對」。選擇要交付的席位，再上傳原始連線 JSON（最多 2 KiB）。主控可核對整場，房控只能核對本房。管理服務比對原票券簽章、場次、席位、目前入場識別及已公告的 IPv4／UDP 埠，並要求原遊戲來源最近五秒內有同階段的有效畫格。

核對成功時會顯示目的地與票券效期，loopback 顯示「僅同機」。如果畫面顯示原來源尚未公告或畫格過舊，待遊戲端更新後可再用同一份有效連線檔核對。手動填寫的目的地若和公告不同，請核對公告並重新下載。這項核對是管理端的取樣，玩家 UDP 可達性、頭盔追蹤及實體場地各有驗收流程。 [兩端 UDP 預檢](#開場前核對兩端-udp)

API 使用 `POST /api/sessions/{id}/rooms/{roomId}/players/{playerId}/vr-connection-check`，`If-Match-Admission` 帶目前的入場識別，JSON 內的 `connectionFile` 是原檔 Base64。結果回傳狀態、席位、公告端點和成功票券效期，回應帶 `Cache-Control: no-store`。核對時只讀取場次與錄製狀態，原 MR 校正檔仍使用 [MR 席位核對](QUEST3.md#在管理台核對席位部署檔)。

## VR 五房配票

管理包 0.31.41 起，全館主控可在五房總覽點「讀取五房名冊」。先準備五個獨立 VR 場次或一個五房合併 VR 場次，為每房加入五名玩家，並讓各遊戲伺服器公布端點。核對畫面中的任務、端點、房間、席位及玩家姓名，再按「下載五房連線檔 ZIP」。畫面會標示只能同機使用的 loopback 端點。

`vr-venue-connections.zip` 內含 `venue.json`、五個原格式的分房 ZIP 及共 25 份四欄玩家連線檔。分房 ZIP 依房號命名，每個 JSON 依房號與席位命名。票券自簽發起有效五分鐘，請將對應的 JSON 個別交給玩家，整份 ZIP 由主控私下保管。Windows 玩家啟動器可再次核對檔內標示的房間與席位。 [玩家端核對](PLAYER_CONFIG_REVIEW.md#連線檔席位與效期)

管理包 0.31.235 的 VR 五房配票可選每房 1 席或 2 席，對應 5 人與 10 人試場。各房先登記第 1 席或第 1、2 席，等原伺服器公布端點後再讀取五房名冊並下載。每房當前名冊須與選取席數一致。5／10 席 ZIP 的 `venue.json` 另記錄 `playersPerRoom`，並沿用各房原場次、端點與有效票券。 [Quest 試場部署](QUEST3.md#直接使用-vr-五房連線-zip)

管理包 0.31.220 的 VR、MR 與混合五房配票，會先核對此輪的請求編號及 ZIP 原始位元組的 SHA-256，再重新確認原場次、端點與名冊。若回應無法核對，控制台會停在下載前並提示重新配票。核對使用瀏覽器內的檔案內容，無須把已收到的票券傳回管理服務。

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

搭配管理包 0.31.148，工具在寫入暫存目錄前及正式交付前各核對一次原包內所有票券、現行入場、遊戲端點及近期原來源畫格。核對成功後才一次交付對照表中的原 VR 連線檔，例如 `pc-PC-A-room-01-seat-02.json`。若來源在暫存期間停止更新，工具會指出受影響的房間和席位並移除這批暫存。來源恢復且原票券仍有效時，可用同一份 ZIP 重新執行。

選到 Quest 3、MR 房間、重複席位、過期票券或過時名冊時，整批拒絕。成功摘要列出每台電腦的檔名、端點與效期，並記錄 `liveSourceVerified: true`。純 VR 同機排演可使用 loopback，玩家只能在遊戲伺服器所在電腦使用該目的地。跨機仍須使用場館 LAN 端點。

把每份 JSON 私下交給對應電腦。玩家在該電腦用解壓後的 `Launch-Player.exe --config <該台連線檔> --launch --openxr --wait` 加入。Quest 席位可從同一份原場館 ZIP 使用 Quest 的批次部署流程。 [Windows OpenXR 啟動](WINDOWS_PLAYER_PACKAGE.md#windows-openxr-啟動) · [Quest 席位部署](QUEST3.md#部署指定的-quest-席位)

下載使用各來源已公布的位址和埠。五房獨立須使用各自的端點，合併場共用同一端點。若名冊、場次或來源已變更，請重新讀取五房名冊。尚未填滿的場館可沿用單席或整房配票。

主控可用 `GET /api/vr-deployment/venue` 讀取預覽。向 `POST /api/vr-deployment/venue-bundle` 送出同一預覽的 `topology` 以及五個 `rooms`，每房提供 `roomId`、`sessionId`、公布的 `streamId` 和每席的 `playerId`、`admissionId`。5／10 席試場在預覽查詢及配票 JSON 指定相同的 `playersPerRoom`。服務以同一份現行場館快照核對所有房間。任何一房不符時回應 409，附對應房號，整批無 ZIP。

管理包 0.31.42 提供 `POST /api/vr-deployment/venue-check`，限主控。請求提供 `topology` 與五筆 `rooms`。每房提供 `roomId`、`sessionId` 及依席位排序的 Base64 `connectionFiles`。5／10 席試場另附 `playersPerRoom`。結果回傳逐席的票券、端點、現行名冊核對狀態及成功席的裝置類型。Quest 部署工具可直接讀取原 ZIP 使用此端點。 [Quest 部署操作](QUEST3.md#直接使用-vr-五房連線-zip)

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

新版全館及有逐席明細的 Quest 預檢回條會附帶雙端原檔的 SHA-256，封存驗收會對照原檔。Quest 回條的逐席檔案也須與同一房組列出的雙端清單一致。請保留當次監聽端和探測端的原始檔案，包含原編碼及換行。

新版全館及 Quest 回條中的 `networkPlanSessions` 會在收件和封存驗收時與原封存場次比對。工具按房組核對任務版本、遊戲來源附掛時記錄的場次修訂，以及該修訂早於結束指令。有這些欄位的回條，即使未附原網路清單，也須通過這些比對。

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

可一併加入原 Quest 批次報告，每份使用一個 `--batch`。未完成的 Quest 批次也能加入。全館工具依原房席和網路清單重驗已通過席位的雙端檔案、雜湊、交換摘要、樣本與時限。缺少有效報告的房席會留在全館報告的 `groups[].sources`，這些來源仍待補測。只有批次報告時可省略 `--pairs`。

若 Quest 預檢已核對 Windows 原啟動批次，合併時用 `--launch-plan` 和 `--launcher-preview` 提供相同原檔。 [Quest 開場前核對](QUEST3.md#預檢前核對-windows-原啟動批次)

Quest 批次重試後，`--batch` 指向最新的報告。用 `--retry-report` 同時帶入先前未完成的全館報告，可沿用已驗證的來源。兩份報告若指向同一路徑及同一對原始檔案，會合計一次。各輪原始資料夾都須保留。 [重試 Quest 預檢](QUEST3.md#重試-quest-udp-預檢席位)

使用 Windows 批次啟動時，可用 `--launch-plan` 和 `--launcher-preview` 同時提供控制台下載的原啟動計畫，以及啟動器 `--venue-check` 產生的成功預覽。在 UDP 監聽工具啟動前或退出後產生預覽，並使用實際要啟動的那份計畫。計畫的公告 IPv4 和本機綁定 IPv4 都填成網路清單上的同一個具體位址。 [下載啟動計畫](WINDOWS_SERVER_PACKAGE.md#依場館計畫批次啟動)

```powershell
& .\Launch-Server.exe --venue-check 'C:\VRCommand\venue-plan.json' --report 'C:\VRCommand\venue-preview.json'
python .\scripts\check-venue-udp-preflight.py `
  --network-plan .\venue-network.json --pairs .\pairs.json `
  --batch .\quest-a\preflight-report.json `
  --launch-plan 'C:\VRCommand\venue-plan.json' --launcher-preview 'C:\VRCommand\venue-preview.json' `
  --output .\venue-readiness.json
```

報告依房間端點列出各來源涵蓋的席位。`missing` 代表還缺一組，`duplicate-pair` 或 `duplicate-exchange` 代表需排除重複報告，`invalid-or-expired` 代表原雙端報告不符或已超過 30 分鐘。`unmatchedPairs` 和 `unreadablePairs` 分別計算不在本次計畫內及無法讀取的組數。補齊後使用新的輸出檔重跑。所有來源通過且沒有多餘或無法讀取的報告時，程式以 `0` 結束。

指定 `--launcher-preview` 後，預覽的模式、房間、UDP 埠、公告 IPv4 與本機綁定 IPv4 須符合網路清單。若也提供原計畫，`launchBinding.groups` 會逐房核對場次 ID、任務版本 ID、場次序號與端點。任一欄位不符時，即使雙端 UDP 報告已通過，整體仍回報未完成。計畫及預覽均記錄路徑及 SHA-256。場次修改後，請重新下載啟動計畫並產生同一份計畫的預覽。舊版只提供 `--launcher-preview` 的命令仍可核對端點。

可將完整報告的路徑填入封存驗收清單的 `udpPreflightBatch`。請保留原雙端報告，以及 `launchBinding` 所引用的原計畫和預覽，並維持檔案間的路徑。結束後，驗收工具會用遊戲伺服器實際綁定時間與已確認的玩家來源重驗每組，並比對原計畫與封存的場次、任務版本及端點。若透過 `--batch` 重新納入含 `launchBinding` 的報告，須再次提供相同的計畫和預覽。`network` 為 `same-host` 的結果代表同機 UDP，跨機連線與頭盔仍須現場測試。

#### 從資料夾配對 UDP 報告

把本次監聽端及探測端的原始 `.json` 或 `.ndjson` 放入專用收件夾，並用 `--inbox` 直接核對。工具依端點、來源與同一次交換的 SHA-256 配對，檔名可以各自命名。每個資料夾讀取最上層最多 100 份報告。將網路清單、金鑰、啟動資料及輸出的驗收報告放在收件夾外。

```powershell
python .\scripts\check-venue-udp-preflight.py `
  --network-plan .\venue-network.json --inbox .\udp-inbox `
  --launch-plan .\venue-plan.json --launcher-preview .\venue-preview.json `
  --output .\venue-readiness.json
```

`inbox.issues` 列出無法讀取的原始報告、缺少對端的檔案及同一交換中重複提交的檔案。若報告的伺服器端點及探測來源都能對上原網路清單，問題會附對應的房號與席號。缺少對端時，`missingRole` 為 `listener`（監聽端）或 `probe`（探測端）。已配成對的報告仍會核對完整樣本與時限。可另用 `--batch` 加入 Quest 批次，並以同樣的方式提供所用的啟動原檔。

#### 補測未完成的全館 UDP 預檢

管理台 0.31.212 的「核對全館預檢、啟動與封存」可直接開啟全館 `venue-readiness.json` 或另存的補測報告。主控可逐房查看待補席位、逾時原因、缺少的監聽端或探測端，以及尚待處理的收件和計畫問題。報告只在瀏覽器本機解析，畫面會標示原核對時間與同機或私有網路範圍。正式開場仍用原工具重驗雙端檔案及有效期限。

待補席位包含 Quest 時，可將同一份全館報告直接交給 Quest 工具，依原裝置對照表選出仍待補測的席位。 [Quest 補測操作](QUEST3.md#從全館報告選出-quest-補測席位)

可用 `start-verified-venue.py --verify-only` 查閱未完成的全館報告，或在開場前重驗曾通過的報告。加上 `--retry-output .\venue-retry.json`，離線查核會在預檢未完成時保存仍有效的來源及未處理的收件問題，終端機會回傳 `retryReportSaved`。輸出目錄須已存在，檔名須未使用。接著以新檔作為下方指令的 `--retry-report`，只加入找回或補測的雙端報告。 [開場前重驗](WINDOWS_SERVER_PACKAGE.md#以-udp-預檢報告啟動五房)

全館檢查未完成且已提供的啟動資料核對通過時，報告會在 `retrySources` 保留已驗證的來源、雙端報告路徑與雜湊。補測缺漏或失敗來源後，用 `--retry-report` 指定前一份未完成的全館報告，並用 `--pairs`、`--inbox` 或 `--batch` 帶入補測的雙端資料。若只缺對端原檔，可補進同一收件夾後重跑。工具會重新核對先前通過的原檔，同一路徑的同一對檔案只計一次。若某來源重新探測，請把新一對放入補件收件夾，並保留先前的原始檔案供核對。每輪使用新的輸出路徑。重試須沿用同一份網路清單，以及前一輪提供的啟動計畫或預覽原檔。

```powershell
python .\scripts\check-venue-udp-preflight.py `
  --network-plan .\venue-network.json --retry-report .\venue-readiness.json `
  --pairs .\new-pairs.json --launch-plan .\venue-plan.json --launcher-preview .\venue-preview.json `
  --output .\venue-readiness-retry.json
```

重試會重新核對雙端原檔、來源及既有 30 分鐘期限。原檔有變、無法讀取或逾時時，該來源須補測。`retainedSources` 是這輪仍有效的來源數。完整報告可直接交給戰後封存驗收。 [封存方式](#用原網路清單核對封存席位)

逐席直連預檢會在報告保存 `requireDistinctRemoteRoster`。補測、併入完整報告及驗證啟動都會沿用此條件，並重新核對原網路清單。啟動時可省略已記錄在報告的旗標。

#### 依全館報告補測 Windows 席位

從全館報告選定待補測的 Windows 房號與席號。以下是第 5 房第 4 席的例子。工具重驗原始證據後，輸出這一組的伺服器 IPv4、玩家來源 IPv4 與 UDP 埠。若同一端點上的多個席位共用來源，`coveredSeats` 會列出一組探測涵蓋的席位。若原交換仍有效，工具會顯示 `no-windows-retest` 並結束。

```powershell
python .\scripts\check-venue-udp-preflight.py `
  --network-plan .\venue-network.json --retry-report .\venue-readiness.json `
  --launch-plan .\venue-plan.json --launcher-preview .\venue-preview.json `
  --windows-retest-seat 5 4 --output .\windows-r5-s4.json
```

按原本的兩端 UDP 流程產生探測金鑰，將同一份端點檔與金鑰交給這組的伺服器及 Windows 玩家電腦。先在伺服器執行第一條指令，再在玩家電腦執行第二條。兩端的樣本數相同。

```powershell
pwsh -NoProfile -NonInteractive -File .\scripts\check-lan-udp.ps1 -Mode Listen `
  -EndpointFile .\windows-r5-s4.json -KeyFile .\probe.key -Count 5 > .\listener.ndjson

pwsh -NoProfile -NonInteractive -File .\scripts\check-lan-udp.ps1 -Mode Probe `
  -EndpointFile .\windows-r5-s4.json -KeyFile .\probe.key -Count 5 > .\probe.json
```

將新雙端檔加到補測清單，沿用上節的 `--retry-report` 合併。端點檔只用於帶入參數，完成仍以原雙端報告為準。 [金鑰與雙端操作](#開場前核對兩端-udp)

#### 核對 Windows 五房啟動回條

使用 `start-verified-venue.py --start-receipt` 完成封存後，產生全館清單時加上 `--verified-start-receipt .\venue-start.json`。同時保留原 `--launcher-report` 與唯一一份 `--udp-preflight-batch`。若已有清單，可填入 `"verifiedVenueStart": "venue-start.json"`，並沿用原 `venueLauncherReport` 和 `udpPreflightBatch`。回條引用的就緒檔路徑以回條所在目錄為準。

封存驗收核對三份原報告的雜湊，以及就緒與結束報告中的房間、遊戲程序、錄製來源及 UDP 綁定。完整驗收仍會重驗原雙端資料及玩家 UDP 來源。成功摘要中的 `verifiedVenueStart` 列出回條雜湊、原啟動批次 ID、通過的場次數及有啟用時的逐席直連條件。 [啟動方式](WINDOWS_SERVER_PACKAGE.md#以-udp-預檢報告啟動五房)

#### 從原啟動預覽產生網路清單

先在 `seat-addresses.json` 保存本階段所有 Windows 與 Quest 的席位 IPv4。格式為版本 `1`，`seats` 中每列有 `roomId`、`seat` 及 `address`。以下是五房各一席的範例，地址請替換為現場值。

```json
{
  "version": 1,
  "seats": [
    {"roomId": 1, "seat": 1, "address": "192.168.1.21"},
    {"roomId": 2, "seat": 1, "address": "192.168.1.22"},
    {"roomId": 3, "seat": 1, "address": "192.168.1.23"},
    {"roomId": 4, "seat": 1, "address": "192.168.1.24"},
    {"roomId": 5, "seat": 1, "address": "192.168.1.25"}
  ]
}
```

```powershell
python .\scripts\prepare-venue-network-plan.py `
  --launch-plan .\venue-plan.json --launcher-preview .\venue-preview.json `
  --seat-addresses .\seat-addresses.json --players-per-room 1 --output .\venue-network.json
```

預設每房五席，10 人階段用 `--players-per-room 2`。工具先核對原啟動計畫與成功預覽的模式、場次、任務版本、場次序號及 UDP 端點，再將原端點與席位寫成版本 1 網路清單。若要為同一批混合場另產生 Quest 專用清單，再跑一次並加上 `--quest-device-map .\device-map.json`，將 `--output` 改為 `quest-network.json`。Quest 子集的每個裝置須有各自的 IPv4，且每席都須存在於全館席位表。

全館清單可交給 `check-venue-udp-preflight.py`，Quest 子集可交給 `probe-quest-venue.py`。請一併保留原啟動計畫、預覽與席位表。產生清單只核對檔案，實際 UDP 往返仍須依雙端報告驗收。 [Quest 批次預檢](QUEST3.md#批次預檢五房-quest-席位)

若本批要驗收每席各自直連，可在產生全館清單、執行 UDP 預檢及 `start-verified-venue.py` 啟動時加上 `--require-distinct-remote-roster`。各席須使用不同的私有 IPv4，且不能與任一遊戲伺服器公告位址相同。檢查失敗會指出房號及席號。用 `--quest-device-map` 產生子集時，此選項仍會先檢查完整席位表。既有共用工作站及同機排演可沿用原指令。

若伺服器有多張網卡，產生清單時可重複加上 `--server-ip`，列出所有公告位址及其他伺服器 IPv4。清單會保存這些位址並啟用逐席直連檢查。預檢與啟動會讀取同一份清單，任何席位若填到其中一個伺服器位址，工具會指出房號及席號。

管理台 0.31.174 可在「Windows 遊戲伺服器啟動計畫」匯入席位表，於「伺服器其他 IPv4」每行填一個位址，再下載 UDP 預檢清單。公告位址會自動加入。管理台會在下載前指出共用或誤用伺服器位址的房號與席號。

管理台 0.31.175 會核對席位表的每個房號與席號。匯入前先登記準備中場次的席位。若名冊和席位表有差異，面板會列出表內缺少或場次尚未登記的席位。下載時若場次或名冊已變更，請重新讀取五房場次並確認席位表。

管理台 0.31.238 與新版準備工具會在版本 1 網路清單的每個端點保存 `sessionId`、`missionId`、`sessionSequence`。給預檢工具原 Windows 啟動計畫與預覽時，工具會逐組比對這三個值。即使原埠、IPv4 與席號都相同，也會拒絕其他場次或修訂。Quest 子集清單保留同一組原端點及場次。只提供網路清單時，可核對 UDP 來源，啟動仍需原預覽與啟動計畫。既有版本 1 清單可沿用原核對流程。

`check-venue-udp-preflight.py` 會將新版清單的場次欄位保存為 `networkPlanSessions`。用原回條補測時會比對這些欄位與原清單。主控可在控制台 0.31.239 匯入回條，以唯讀方式比對本次取樣的準備狀態及原席位。啟動前仍用 `start-verified-venue.py` 重驗原清單、啟動預覽、雙端 UDP 報告及有效期限。 [啟動前檢查](WINDOWS_SERVER_PACKAGE.md#以-udp-預檢報告啟動五房)

以 `--batch` 收件時，含 `networkPlanSessions` 的全館回條必須配合產出它的同一份網路清單。即使位址、連接埠和席位都相同，場次修訂不同也會拒絕收件。封存驗收可用 `venueNetworkPlan` 比對同一份清單及逐房修訂；有 Windows 啟動預覽的回條也會比對其原啟動計畫。

Windows 啟動器 1.21 的 `--venue-check` 預覽也會記錄各場已登記的房號與席號。產生全館網路清單或驗證 UDP 報告時，若提供這份預覽，工具會逐席比對。準備 Quest 專用清單時會先核對完整席位表，再選出指定的 Quest 席位。正式啟動會以同一份啟動計畫重新向管理服務預覽，確認原場次版本、席位及端點。名冊改動後請重新下載計畫、產生預覽並核對 UDP 報告。舊版預覽仍可用於歷史報告的查核。

#### 用原網路清單核對封存席位

在 `venue.json` 加入 `"venueNetworkPlan": "venue-network.json"`，或在 `prepare-venue-field-manifest.py` 加 `--venue-network-plan .\venue-network.json`。使用開場前的全館清單，涵蓋本階段所有 Windows 與 Quest 席位。工具會比對每房原封存端點及原名冊，再將伺服器已確認戰績的 UDP 來源逐席核對。新版清單另核對原場次、任務版本與伺服器附掛來源時使用的名冊修訂號。收件模式會列出來源不符的 Windows ZIP，並將對應席位列為待補件。

新版全館 UDP 預檢回條會保留 `networkPlanSha256`。同時提交清單和新版回條時，驗收會核對兩者引用同一份原檔。舊回條仍核對原雙端 UDP 報告、場次與逐席來源。若同時提供 `windowsStationAddresses`，兩份位址資料須相符。全 Quest 場可在 `questCaptures.networkPlan` 填同一清單路徑，混合場仍可保留原 Quest 子集清單。

`venueNetworkPlan` 摘要列出原檔雜湊、預期席位、已核對席位及端點數。收件模式的已核對席位數只計入已交回且通過的 Windows ZIP。完整驗收會核對全館 Windows 與 Quest 席位。 [收件方式](#按收件資料夾找缺件及錯批)

若驗收清單同時設定 `requireDistinctRemoteRoster`，工具也會核對預先保存的全館清單，包含所有 `serverIps`。逐席驗收仍以原連線與封存戰績為準。

網路清單若已保存伺服器位址，封存清單的 `serverIps` 須涵蓋這些位址。封存驗收也會檢查後續列入的伺服器位址是否與任何原席位衝突。

### 核對封存戰績與 UDP 來源

離線核對工具使用已完成的一場 Windows 伺服器任務。啟動器 1.7 可勾選「記錄本次玩家連線來源（場館驗收）」，CLI 可加 `--peer-diagnostics on`。將公告及本機綁定都設為這台電腦實際使用的 IPv4，選擇名冊固定的場次。結束後等待原啟動器寫出 `sealed-stopped` 報告，並等玩家寫完戰績與斷線日誌。 [伺服器操作](WINDOWS_SERVER_PACKAGE.md#跨機來源診斷)

將伺服器 `--report`、該次工作目錄的 `server.log`、各玩家的原始 Unity 日誌放在私人資料夾。全館主控可在「任務收尾」選擇「下載場館驗收資料 ZIP」。伺服器確認任務曾開始、雙封存、端點公告，以及最終名冊與統計涵蓋同一組玩家和房間。新版工具可直接讀取原 ZIP。每份包含場館資料，應與同場日誌私下保管。

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
  --evidence-zip .\management-field.zip `
  --player 192.168.1.10 '.\player 1.log' --player 192.168.1.20 '.\player 2.log'
```

也可改用表中的三份原檔，依序傳給 `--session`、`--statistics` 和 `--endpoint`。

每場同時最多 25 位玩家。檢查器逐位比對結束名冊的入場 ID、房間、個人戰績、三種封存序號，以及最終連線的 UDP 來源與伺服器確認。玩家曾重連時使用收到戰績的最後一條連線。文字日誌、JSON 與 ZIP 每份最多 16 MiB。成功輸出可另存 JSON，摘要只含計數、房間、序號及範圍。失敗以退出碼 1 表示，診斷文字省略原始位址、票券和檔案路徑。

#### 核對任務中被移出的玩家

管理包 0.31.203 起，單場「下載場館驗收資料 ZIP」會附上 `roster-departures.json`，記錄結束前由管理端移出且戰績仍在封存統計中的玩家。用 `--evidence-zip` 傳入原 ZIP，並加上該場的 `--combat-journal .\room-01.journal` 及 `--world-journal .\room-01.worldlog`。兩份日誌須已封存。工具重算所有封存戰績，核對離場玩家原入場、移除時的管理序號及有效姿態。如果全體皆已離場，仍可核對日誌和戰績。

摘要的 `rosterDepartures.scoresVerified` 是已核對分數的離場玩家數。`serverAcknowledgements` 逐一核對結束名冊的原戰績確認。`--verify-player-sources` 的玩家日誌證據也以結束名冊為範圍。

#### 核對五房批次中的離場戰績

管理包 0.31.204 起，五房各自運作或全館連線的批次 ZIP 會在有離場紀錄的場次子 ZIP 附上 `roster-departures.json`。在全館「結束批次」選取原批次並下載驗收 ZIP。含回條的版本仍按任務結束時的名冊核對送達。

使用 `prepare-venue-field-manifest.py` 整理原始檔案時，加上 `--final-players-by-room 0 1 1 2 1`，依第 1 至第 5 房填實際結束名冊人數，每房可填 0 到 5。手動建立清單時，相同範例寫成 `"expectedFinalPlayersByRoom": {"1":0,"2":1,"3":1,"4":2,"5":1}`。每個場次附上原伺服器日誌及該場雙封存的 `combatJournal` 和 `worldJournal`。各房人數不一或有空房時，使用結束名冊的逐位玩家日誌填寫來源。

執行 `python scripts/verify-field-results.py --venue-manifest .\venue.json` 後，`departedScoresVerified` 列出全批次核對完成的離場戰績數，`sessions[].rosterDepartures` 列出各原場次的核對結果。`players` 和 `serverAcknowledgements` 計算結束名冊與其回條。5／10／25 人階段驗收沿用每階段的固定席位要求。

#### 用單場 ZIP 核對追蹤開場

管理包 0.31.202 的場次若有已保存的單場 VR 追蹤開場，從該場「任務收尾」下載的驗收 ZIP 會包含 `tracked-vr-start.json`。用 `--evidence-zip` 讀取整包，加上 `--world-journal .\room-01.worldlog` 及 `--require-tracked-vr-start`，確認回條存在並核對原始封存。工具會比對原串流、開場管理序號前一版、擷取偏移與原追蹤名冊，接著查找套用開始後首個有效執行畫格。結果在 `worldJournal.trackedVrStart` 列出兩個世界畫格、管理序號與追蹤席位數。 [開場與回看操作](SESSION_CLOSURE.md#回看單場-vr-追蹤開場)

### 核對原程序的重連歷程

單場可加 `--verify-reconnect-history`，五房清單可填 `"verifyReconnectHistory": true`。開場前先啟用伺服器的 UDP 來源診斷。各席須提供同一原程序的完整 Windows 日誌或單一 PID 的 Quest logcat，並填寫該席本次任務使用的 IPv4。此模式適用於來源 IPv4 相同的重連，UDP 埠可以改變。

驗收會比對每條已連線記錄的伺服器核准及 UDP 來源，確認舊連線在下一條核准前已由伺服器釋放，最後一條才有原戰績確認。無法歸入任何玩家日誌的伺服器來源記錄會使驗收失敗。`reconnectHistory` 提供總連線數、已釋放的舊連線數與重連房號席位。入場識別以最後封存的原戰績核對，歷史來源記錄提供連線識別與順序。 [伺服器來源診斷](WINDOWS_SERVER_PACKAGE.md#跨機來源診斷)

使用 `prepare-venue-field-manifest.py` 時，可加 `--verify-reconnect-history` 保留這項檢查。Windows 收件模式會逐份檢查已交回 ZIP 的原程序及歷次連線。舊連線缺少伺服器釋放紀錄、來源不符，或同一條舊連線出現在兩份玩家日誌時，會列出受影響的檔案與席位。收件摘要只計入通過的 Windows 檔案。收齊後，完整驗收會核對全場 Windows 與 Quest 日誌及伺服器記錄。 [收件方式](#按收件資料夾找缺件及錯批)

#### 核對重連時變更的 IPv4

若現場重連時確認席位的 IPv4 有變，保留開場前的 `venueNetworkPlan`，另外在私人清單記錄受影響席位的歷次 IPv4。每筆對應一條連線，依玩家日誌順序填寫。第一筆須符合開場清單，同一 IPv4 在不同連線重複出現時也須逐筆填寫。`closureRequestId` 使用這批原全館結束回條的識別碼。

```json
{
  "version": 1,
  "closureRequestId": "17166e9f-6035-41ad-b4e3-3cc70b2c0ec4",
  "seats": [{"roomId": 5, "seat": 2, "addresses": ["192.168.1.22", "192.168.1.42"]}]
}
```

在 `venue.json` 加 `"reconnectSourcePlan": "reconnect-sources.json"`、`"verifyReconnectHistory": true` 及原 `venueNetworkPlan`。用工具產生清單時，可傳入 `--reconnect-source-plan .\reconnect-sources.json --verify-reconnect-history --venue-network-plan .\venue-network.json`。此流程與要求每席固定來源的 `requireDistinctRemoteRoster` 擇一。

工具逐條核對同一玩家程序的連線順序、伺服器所見 IPv4、舊連線釋放及最後一條連線的原戰績確認。未列入變更清單的席位沿用原固定來源。開場前 UDP 預檢沿用當時的第一個來源。摘要 `reconnectSourcePlan` 只顯示原檔雜湊、席位數及核對連線數。Windows 收件會列出不符的 ZIP 與席位，Quest 由原 PID 的 logcat 及封存資料核對。

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

同一批次有多次中斷時，可改填 `reconnectWindows`，陣列內放 1 至 32 個相同格式的區間。同一份清單只能選 `reconnectWindow` 或 `reconnectWindows`。每段須通過上述查核，區間不得重複或重疊。每席原 UDP 紀錄中，已釋放且確認先於下一次入場的連線數須涵蓋該席填報的區間數。例如同一席填兩段，就須有至少兩次原連線釋放。摘要 `reconnectWindows` 依錄製時間排序。

### 核對原始回放檔頭與封存

如要一併驗收原生回放檔，等啟動器回報 `sealed-stopped` 後，從其 `workDirectory` 下的 `telemetry` 保留 `<sessionId>.worldlog`。在單場命令加入 `--world-journal .\room-01.worldlog`。工具唯讀檢查每筆記錄的校驗碼與連續影格，並將完整檔頭與啟動器封存報告比對，包含場景物件的位置與角度、任務時鐘、校正設定、規則及呈現版本。物件座標與角度依遊戲的單精度數值比較，舊檔省略的版本欄位依原預設值零比較。它確認原檔含活動中影格及兩種封存的尾界，再輸出檔案 SHA-256、總影格數及活動中影格數。活動中影格須為 `Running`、tick 大於零且未中止來源。原生回放檔逐筆讀取，可超過文字日誌的 16 MiB 上限。 [原生世界紀錄](WORLD_SOURCE.md)

### 從原始戰鬥日誌重算戰績

在同一個 `telemetry` 目錄保留 `<sessionId>.journal`，單場命令加入 `--combat-journal .\room-01.journal`。五房清單則在各 `sessions[]` 填寫 `"combatJournal": "room-01.journal"`，使用相對於清單的路徑。獨立模式需五份，合併模式需一份。可同時提供 `worldJournal`，各自核對戰鬥事件和回放畫格。

工具唯讀核對原場次、來源、每筆事件的校驗碼、連續序號、累計確認和終端封存，逐席重算耗彈、命中、擊殺、中彈、損耗、剩餘健康及命中率，再與已核對的管理統計和玩家結果比較。沒有戰鬥事件的場次也須有原完成與封存紀錄。任一檔案或戰績不一致時，整份驗收以退出碼 1 結束。成功摘要包含逐場 `combatJournal` 的 SHA-256、事件數及核對席位數，全館另有 `combatJournalsVerified`。

加入 `--verify-player-sources` 後，工具也會以原入場連結玩家日誌與封存回放，逐席列出房號、席次、來源、姿態種類及符合條件的活動影格數。Windows OpenXR 日誌須含原啟動順序、執行環境及同一 UDP 埠，回放須有對應的 `Tracked` 姿態。Unity Mock Runtime 會獨立標記為 `windows-openxr-mock-tracked`。一般 Windows OpenXR 回報 `windows-openxr-tracked`，桌面模擬回報 `windows-desktop-simulated`。Quest logcat 須核對原 PID、入場及 `Tracked` 姿態，回報 `quest-logcat-tracked`。名冊上的 VIVE XR 或 Quest 3 分類與實體裝置型號仍由現場核對。姿態與日誌來源不一致，或原席位在活動影格中從未接受連線姿態時，工具會拒絕本次核對。

`same-host` 要求全部觀察到的來源都在宣告的伺服器位址清單。`direct-lan` 要求至少有一個清單外的私有 IPv4，且所有玩家的實際來源均符合各自填入的位址。實體主機數與網路容量仍須現場確認，工具摘要分別保留 `physicalHostsVerified` 與 `networkCapacityAccepted` 為 `false`。NAT 或中繼環境需另記拓撲與轉譯結果。

Quest 3 席位使用 `--quest-player 192.168.1.21 '.\quest logcat.txt' 7342`，依序填頭盔本次使用的 IPv4、原始 logcat 路徑和遊戲程序 PID。可與 Windows 的 `--player` 混用。Quest 3 須登記在原名冊，且其 UDP 來源須在伺服器位址清單外。摘要的 `questLogcatPlayers` 只計算通過原入場及戰績核對的 logcat 檔案數。 [Quest 擷取方式](QUEST3.md#收集-quest-場館驗收日誌)

### 核對單場 Quest 開場追蹤回條

在單場命令加入 `--world-journal .\room-01.worldlog` 和 `--quest-readiness-report .\quest-player-readiness.json`。每份 `--quest-player` 日誌各提供一份開場前成功的 `-VerifyPlayerTracking` 回條，可用任意順序傳入。工具用原場次和入場雜湊配對席位，再確認回條的原管理序號、世界序號和擷取時間能對回封存中的 GameServer 準備畫格，以及畫格中的玩家已連線並有 `Tracked` 姿態。摘要在 `worldJournal.questReadinessFrames` 按畫格列出核對席數。 [保存開場回條](QUEST3.md#單房實機追蹤驗收)

### 核對單場 Quest OpenXR 啟動回條

在原單場驗收命令加上 `--quest-launch-release .\venue-release.json`，每份 `--quest-player` 日誌再各加一份 `--quest-launch-report .\quest-launch.json`。使用本場部署時 `-RequireOpenXR` 回傳、含 `evidenceVersion` 的原始 JSON，以及部署時指定的原發行報告。回條可用任意順序傳入。工具會比對場次、原入場、房間席位、伺服器埠和發行報告摘要，再從同一 PID 的原始日誌核對 OpenXR 啟動標記先於最終戰績。通過時，摘要的 `questOpenXR.verifiedSeats` 列出核對席數。 [單席部署](QUEST3.md#使用頭盔上已安裝的-apk-加入場次)

`evidenceVersion: 2` 回條也會以 SHA-256 核對原公告端點的 IPv4。若同一 UDP 埠的位址已更換，請提供與封存端點相符的原部署回條。仍可讀取舊版回條。

`evidenceVersion: 3` 延續端點核對，並提供裝置指紋供擷取工具比對實際頭盔。使用原啟動回條擷取時，可在工具輸出核對 `deviceIdentityVerified`，再保存原日誌、啟動回條與發行報告供戰後查閱。 [擷取原日誌](QUEST3.md#收集-quest-場館驗收日誌)

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
| `venueLauncherReport` | 使用 Windows 五房批次啟動時，填該批啟動器 `--report` 產生的原終止報告 |
| `venueDebriefReceipts` | 選用。從同一批次下載的戰績回條 JSON 路徑。若 `venueBundle` 已內附回條，省略此欄 |
| `verifyPlayerSources` | 選用。填布林值 `true` 核對所有原席位的日誌與姿態。每場均須提供 `worldJournal` |
| `verifyTrackingBegin` | 選用。填布林值 `true` 核對同一批追蹤開場採用的原始準備中畫格及後續執行畫格。每場均須提供 `worldJournal` |
| `minimumConcurrentMilliseconds` | 選用。填 1,000 至 900,000 的整數，要求本階段全數席位同時連線且遊戲持續執行的最短毫秒數。每場均須提供 `worldJournal` |
| `requireTrackedRoster` | 選用。填 `true` 時須一併設定 `minimumConcurrentMilliseconds`，並逐席核對同一區間的追蹤姿態及原始玩家日誌 |
| `requireConcurrentFire` | 選用。填 `true` 時須一併設定 `minimumConcurrentMilliseconds`，並在每場提供 `worldJournal` 與 `combatJournal`。要求本階段每個原席位在同一段合格區間各有一次已封存射擊 |
| `udpPreflightBatch` 或 `udpPreflightBatches` | 選用。單份完整的場館 UDP 核對報告或原 Quest 批次報告路徑，也可填 1 至 25 份報告路徑的陣列。可搭配逐場 `udpSourcePreflights` |
| `questCaptures` | 選用。填原 Quest 網路計畫、裝置對照表或兩者，以及 1 至 25 份原擷取報告。可與 UDP 預檢報告一併使用 |
| `questDeployments` | 選用。填原離線發行報告及 1 至 25 份正式 Quest 部署報告，核對原入場及 APK 雜湊 |
| `roomAlignmentBundle` | 選用。填原 MR 或混合部署 ZIP 路徑。與 `sessions[].roomAlignments` 擇一，並提供每場原回放檔 |
| `roomAlignmentBundleSha256` | 選用。原部署 ZIP 的 SHA-256。使用準備指令時會自動保存，正式驗收和六批收件會重新比對 |
| `venueReleaseReport` | 選用。核對全館所有 Windows 與 Quest 席位共用的原發行報告。Quest 的 `questDeployments` 此時只填 `reports` |
| `sessions` | 獨立模式填五場，合併模式填一場 |
| `sessions[].launcherReport` 或 `sessions[].sessionId` | 個別啟動時填各場原終止報告路徑。使用 `venueLauncherReport` 時填各場原 `sessionId` |
| `sessions[].serverLog` | 各場原伺服器日誌的路徑 |
| `sessions[].evidenceZip` | 使用 `closure` 時填各場原 ZIP。使用 `venueBundle` 時省略 |
| `sessions[].worldJournal` | 選用。若驗收回放檔，每個場次都填自己關閉後的原始 `.worldlog` 路徑 |
| `sessions[].combatJournal` | 選用。逐場填原始 `.journal` 路徑，以封存事件核對戰績 |
| `sessions[].roomAlignments` | 選用。核對 MR 校正時，每個 MR 場次按房號填原校正檔，例如 `{"2":"room-02-alignment.json"}` |
| `sessions[].udpPreflight` | 選用。每場提供原 UDP 預檢報告的 `listener` 與 `probe` 路徑 |
| `sessions[].udpSourcePreflights` | 選用。每場按實際來源 IPv4 填一組 `listener` 與 `probe`。可補上 Quest 批次以外的來源 |
| `windowsPlayers` | 選用。集中填入所有 Windows 席位，每筆提供玩家裝置實際使用的 IPv4 `address`，再填原日誌路徑 `log` 或原玩家驗收 ZIP 路徑 `evidenceZip` |
| `windowsEvidenceDirectory` | 選用。Windows 玩家 ZIP 收件資料夾。與 `windowsPlayers` 擇一 |
| `windowsSeatMap` | 選用。收件資料夾用的版本 1 Windows 電腦對照表。混合 Quest 場次須指定應收的 Windows 席位 |
| `windowsStationAddresses` | 選用。Windows 電腦標籤與預期 IPv4 的對照表。須搭配 `windowsEvidenceDirectory` 及 `windowsSeatMap` |
| `windowsLinkCriteria` | 選用。場館填入 `minimumReplies` 和 `maximumP95RoundTripMs`，逐席驗收原 Windows 連線量測。 |
| `questLinkCriteria` | 選用。場館填入 `minimumReplies` 和 `maximumP95RoundTripMs`，逐席驗收原 Quest logcat 內的遊戲連線量測。 |
| `sessions[].players` | 逐場填寫尚未由 `windowsPlayers` 或 `questCaptures` 提供的席位，每筆填實際 IPv4 `address` 及原日誌路徑 `log`。手動填入 Quest 3 原 logcat 時另填數字 `logcatPid`，例如 `7342`。該場席位已全部由前兩欄提供時可省略 |

路徑可以是絕對路徑，或相對於 `venue.json` 所在資料夾。同一檔案只能使用一次。以下是五房獨立模式的 Windows 範例，請依現場配置填入實際地址與檔名。混合場可改用 `questCaptures` 或逐場補上 Quest 原 logcat。兩種方式合計每房須有五席。

若 `venueBundle` 已內附 `debrief-receipts.json`，或另有填寫 `venueDebriefReceipts`，驗收會將回條與已通過原始日誌驗證的場次、封存尾界及原入場名冊逐席比對。任何缺席位或未確認回條都會使核對失敗。成功摘要的 `venueDebriefReceipts` 欄位列出回條檔 SHA-256、場次數及已確認席位數。 [合併下載](SESSION_CLOSURE.md#下載驗收-zip-與全員回條)

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

#### 核對五房批次啟動器的原終止報告

若從同一份 Windows 啟動計畫啟動全館，啟動時加上 `--peer-diagnostics on`。待原批次程序結束且報告顯示 `venue-sealed-stopped`，下載同一批次的管理驗收 ZIP。準備指令會比對兩份原檔，逐房確認場次、端點、名冊、伺服器日誌及已封存的回放和戰鬥紀錄，然後寫出新的 `venue.json`。 [批次啟動方式](WINDOWS_SERVER_PACKAGE.md#依場館計畫批次啟動)

```powershell
python scripts/prepare-venue-field-manifest.py `
    --venue-bundle .\management.zip --launcher-report .\venue-final.json `
    --topology direct-lan --server-ip 192.168.1.10 --server-ip 127.0.0.1 `
    --windows-inbox .\returned --venue-release-report .\release.json `
    --udp-preflight-batch .\UDP\readiness.json `
    --minimum-concurrent-ms 2000 --windows-minimum-replies 28 --windows-maximum-p95-ms 40 `
    --output .\venue.json
python scripts/verify-field-results.py --venue-manifest .\venue.json --inspect-windows-inbox
python scripts/verify-field-results.py --venue-manifest .\venue.json
```

每個本機 IPv4 各填一次 `--server-ip`。同機演練將 `--topology` 設為 `same-host`。5 席或 10 席的試跑分別使用 `--players-per-room 1` 或 `2`。若伺服器工作目錄已搬移，填入 `--server-work-root` 並保留其下的 `room-01` 至 `room-05` 或 `linked` 及原 `telemetry` 子目錄。證據與清單放在同一磁碟時，清單會使用相對路徑。將整批資料移到別處時，保留檔案之間的位置。輸出檔名須為新路徑。

將範例的同時在線毫秒數、最低回覆數及最高 p95 換成本次驗收規格。三個選項可省略，Windows 兩個門檻須一起提供。產生器會將門檻寫進新清單，Windows ZIP 尚未收齊時也可先準備清單。收件指令可查看待補席位及量測結果，最後以完整驗收核對原封存的同時在線區間。六批總清單可另外指定共用的 Windows 門檻。 [六批量測規格](#六批共用-windows-連線量測門檻)

使用 Windows 收件資料夾時一併提供原發行報告，混合 Quest 的場次再用 `--windows-seat-map` 指定 Windows 席位。沒有收件資料夾時，可在產生清單後填入 `windowsPlayers` 或逐場玩家證據。有 MR 校正資料時，可加上 `--room-alignment-bundle` 帶入原部署 ZIP。若有開場預檢，可用 `--udp-preflight-batch` 納入原報告，並保留其引用的原計畫、預覽和雙端紀錄。最後執行完整驗收，摘要會列出原終止報告的批次識別、SHA-256 及驗證場次數。 [Windows 收件](#按收件資料夾找缺件及錯批) · [UDP 預檢](#開場前核對五房-udp-報告)

#### 產生 Windows 與 Quest 混合驗收清單

若 Quest 原日誌已收齊，可直接在產生清單時帶入原擷取報告、裝置表、網路計畫及部署報告。擷取及部署報告可各自分批重複帶入。擷取須提供裝置表、網路計畫或兩者。若使用原發行報告驗收，請一併提供對應的原部署報告。

```powershell
python scripts/prepare-venue-field-manifest.py `
    --venue-bundle .\management.zip --launcher-report .\venue-final.json `
    --topology direct-lan --server-ip 192.168.1.10 --server-ip 127.0.0.1 `
    --windows-inbox .\returned --windows-seat-map .\windows-seats.json `
    --venue-release-report .\release.json --quest-device-map .\device-map.json `
    --quest-network-plan .\network-plan.json `
    --quest-capture-report .\quest-capture\capture-report.json `
    --quest-deployment-report .\quest-deployment.json --output .\venue.json
```

產生器會核對 Quest 原日誌、來源位址、部署及戰績，並確認 Windows 與 Quest 席位完整且無重疊。Windows ZIP 尚未交齊時可先產生清單，再用 `--inspect-windows-inbox` 查缺件。收齊後以同一份清單執行完整封存驗收。 [Quest 擷取報告](#直接使用-quest-批次擷取報告)

### 分階段驗收 5 人與 10 人

5 人階段在五房各登記 1 席，10 人階段各登記 2 席。使用全館開始及全館結束，按每個階段與模式保留一份原場館驗收 ZIP、原封存和完整日誌。開啟追蹤或有效姿態政策時，選擇同一階段的每房席數。將 `expectedPlayersPerRoom` 分別填成 `1` 或 `2`，沿用 `verify-field-results.py --venue-manifest`。驗收會逐房確認宣告的席數、原席位、UDP 來源及伺服器戰績確認，結果同時列出每房預期席數與實際人數。

管理包 0.31.236 可為全 MR 或獨立的 VR／MR 混合五房配發 5 人及 10 人試場票券。每房當前名冊須符合選取席數，MR 房仍使用各自鎖定的校正原檔。 [MR 五房部署](QUEST3.md#五房-mr-部署預檢) · [混合部署](QUEST3.md#混合-vr-與-mr-五房部署包)

需要核對同時在線時，加上 `minimumConcurrentMilliseconds` 並提供每場原 `.worldlog`。現場每席有各自的 IPv4 時，也可加上 `requireDistinctRemoteRoster`，用同一個欄位核對該階段每位玩家的原 UDP 來源。25 人階段可省略 `expectedPlayersPerRoom`。

#### 一次驗收兩種模式的三個階段

準備六份 `venue.json`，每份都保留該批原始場館封存、遊戲日誌、原 `.worldlog` 及同一份 `venueReleaseReport`。一般驗收在各批清單啟用 `minimumConcurrentMilliseconds`。將六份清單的路徑填入 `stages.json`。路徑相對於 `stages.json`，清單列出的順序可調整。

也可將六份批次清單交給準備指令，自動按 5、10、25 席及獨立、合併排序。清單可任意順序提供，工具會核對拓撲、席數組合及發行報告的 SHA-256。同磁碟的引用會保存為相對路徑，輸出須使用新檔名。玩家證據尚未收齊時可先建立總清單，再執行收件檢查。

```powershell
python scripts/prepare-venue-stages.py `
    --output .\stages.json --topology direct-lan --minimum-concurrent-ms 2000 `
    --require-complete-venue-release --require-verified-venue-start --windows-minimum-replies 28 --windows-maximum-p95-ms 40 `
    .\5-independent\venue.json .\5-linked\venue.json `
    .\10-independent\venue.json .\10-linked\venue.json `
    .\25-independent\venue.json .\25-linked\venue.json
```

上例的伺服器發行、啟動回條及 Windows 量測門檻可依場館規格選用。另可加上 `--require-tracked-roster`、`--require-concurrent-fire` 或 `--require-distinct-remote-roster`。使用同機封存時將拓撲改為 `same-host`。建立後用同一份總清單執行收件或正式驗收。

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

##### 一次查看六批待補件

```powershell
python scripts/verify-field-results.py --venue-stages .\stages.json --inspect-venue-stages
```

收件檢查依總清單順序逐份核對，`entries` 列出各項的狀態，`issues` 指出受影響的項次及原因，`missingStages` 列出缺少合格資料的模式和人數。個別資料通過但與其他批次衝突時，受影響的項次會標為 `conflict`。可先列入預定的清單路徑，收到檔案後再核對。檢查遇到缺件或衝突時以退出碼 1 回傳 JSON，六批皆通過時以 0 結束。正式封存摘要使用原指令 `--venue-stages`。

準備指令會在 `expectedStages` 保存每個路徑預期的模式及總席數。收件報告即使遇到檔案缺失，也會顯示該項的 `expectedStage`。路徑指向不同模式或席數時，問題會同時列出預期批次與該檔宣告的 `observedStage`，正式驗收亦會拒絕。若手動加上此欄位，請依 `venueManifests` 的順序填入六筆 `{"mode":"Independent","players":5}` 格式的資料，每種模式及席數組合各一次。原清單省略此欄位時，仍接受任意批次順序。

清單或驗收引用的原檔找不到時，`issues[].missingFile` 會列出檔案類型 `kind` 和檔名 `name`，例如 `worldJournal` 或 `windowsReadyReport`。報告只保留檔名，請依 `entries` 的項次回到該批清單核對存放位置。

批次封存清單可讀時，`issues[].missingFiles` 會一次列出該批 `sessions` 引用但找不到的啟動器報告、場次證據 ZIP、伺服器日誌、世界與戰鬥日誌。每筆含從 1 起算的 `sessionEntry`，能對上原封存場次時附 `roomIds`。原場次由清單的識別或既有啟動器回條查找，與項目排列順序無關。補齊後再執行收件檢查及正式驗收。

同一份 `missingFiles` 也列出 `windowsPlayers` 與各場 `players` 引用但缺少的 Windows 玩家日誌、啟動器回條、連線量測、玩家 ZIP 或手動 Quest logcat。玩家項次 `playerEntry` 從 1 起算，若同時有 `sessionEntry`，請在該場的 `players` 查找。Windows 原日誌或 ZIP 仍可讀取，且其場次、玩家與入場識別能對上原名冊時，會附 `roomId` 及從 1 起算的 `seat`。只有檔案項次時，請依原清單查找。

若原批次使用 Windows ZIP 收件資料夾，總表會在該批的 `issues[].windowsInbox` 列出預期及已核對席數、缺少的房號和席號，以及錯批、重複或無法核對的 ZIP 檔名。使用電腦對照表時會附席位的電腦標籤。有連線量測資料時也會保留該次收件的逐席量測摘要。依原批次補齊或移出錯批檔案後，可再執行總表確認。

若批次已設定 `windowsLinkCriteria`，Windows 收件核對完成但量測缺漏或未達門檻，總表會在 `issues[].windowsLinkMetrics` 顯示該批門檻、已核對席數、缺量測的房號與席號，以及已收到的逐席回覆數與 p95 往返時間。`criteriaFailures` 會指出該席未通過的門檻。原始資料可使用散檔、逐席 ZIP 或 Windows 收件資料夾。 [連線量測門檻](#逐席核對-windows-連線量測門檻)

Quest 批次已設定 `questLinkCriteria` 時，`issues[].questLinkMetrics` 會區分缺量測的 `missingSeats`、片段或內容無效的 `invalidReports`，以及原量測有效但未達門檻的 `seats[].criteriaFailures`。席位位置依封存戰績與伺服器確認決定。 [Quest 逐席門檻](#逐席核對-quest-連線量測門檻)

若 Quest 擷取報告尚未涵蓋原計畫席位，`issues[].questCaptures` 會列出預期席數、報告中標示完成的席數、失敗嘗試次數及待補的房號與席號。找不到原擷取或部署報告時，`issues[].missingFile` 會附檔案類型與檔名。 [重試擷取](QUEST3.md#重試未完成的-quest-擷取席位)

若原 UDP 預檢報告尚未完成，`issues[].udpPreflight` 會列出該批引用的報告項次、檔名、已核對數量及 `pendingSeats`。全館報告會指出缺少、過期或重複的來源對應到哪些席位，並列出無法配對的報告數。Quest 報告會指出待補席位及失敗階段，例如裝置未就緒或探測失敗。找不到報告檔時，同一明細會列出缺少的報告。席位狀態取自預檢報告，補測後須保留原雙端紀錄並重跑正式驗收。 [補測全館 UDP](#補測未完成的全館-udp-預檢)

全館 UDP 報告若包含收件問題的席位，總表會在 `inboxSeatIssues` 列出原來源對應的房號、席號及缺少的端別。請回該批原預檢報告查看檔名。無法對上原網路清單的問題仍會計入 `inboxIssues`。

使用離線重驗匯出的補件報告時，`pendingSeats` 也會列出原報告的原因，例如 `changed-original` 表示原檔內容已變更，`expired` 表示已逾時。若能從一端確認來源，`missingRole` 會標示須補的監聽端或探測端。

擷取報告已標示完成的席位，若原日誌缺少、長度或 SHA-256 不符、編碼無效或無法讀取，會一併出現在 `issues[].questCaptures.logIssues`。每筆包含房號、席號、原檔名及原因。請按批次與席號補回同一次擷取的原檔，再重跑收件與正式驗收，由原流程核對部署、日誌內容及伺服器回條。

##### 六批共用 Windows 連線量測門檻

可在 `stages.json` 加入 `"windowsLinkCriteria": {"minimumReplies": 28, "maximumP95RoundTripMs": 40}`，讓六批都核對原 Windows 逐席量測。個別批次可要求更高的最低回覆數或更低的 p95 上限，每項採兩份清單中較嚴的值。總表會顯示共用門檻，並逐批列出實際門檻及核對席數。每批至少須有一席 Windows 量測才能通過這項選用檢查。

六批皆有 Quest 席位時，也可在 `stages.json` 加 `questLinkCriteria`，或使用產生器的 `--quest-minimum-replies` 及 `--quest-maximum-p95-ms`。總表與個別批次逐項取較嚴的門檻。只需驗收其中幾批 Quest 時，在各該批清單指定即可。通過後 `questLinkObserved` 提供該批回覆數最低及 p95 最高的原房號與席位。

若六批都要驗收 Quest 的 OpenXR 啟動，建立總清單時加上 `--require-quest-openxr`，或在 `stages.json` 加 `"requireQuestOpenXR": true`。每批須至少有一個 Quest 席位，且該批所有 Quest 席位均須從原部署及日誌通過核對。只有部分批次使用 Quest 時，可在那些批次的 `venue.json` 個別啟用。收件模式會在該批的 `issues[].questOpenXR` 列出缺少部署啟動證據的 `missingSeats` 和日誌核對失敗的 `invalidReports`。 [單批核對方式](#核對封存席位的-quest-發行-apk)

通過量測門檻的批次會在 `windowsLinkObserved` 列出回覆數最低及 p95 最高的房號、席號和數值。多席同值時顯示房號及席號最前的一席。可在總驗收及收件報告直接找出每批最接近門檻的席位。量測未通過的批次仍會在收件問題中顯示逐席結果。

##### 統一核對追蹤及遊戲射擊

要讓六批都通過同時追蹤及遊戲射擊驗收，在 `stages.json` 加入 `"requireTrackedRoster": true` 及 `"requireConcurrentFire": true`。兩項可各自啟用。各批保留所有原玩家日誌及 `worldJournal`，啟用射擊驗收時另提供 `combatJournal`。啟用任一項後，總清單會將自己的 `minimumConcurrentMilliseconds` 套用到全部六批；若個別清單另有較長門檻，該批使用較長值。

兩項同時啟用時，同一段共同執行區間須包含全體原席位的有效追蹤，以及每席至少一筆已封存的遊戲射擊。批次清單可省略這兩項，總清單仍會照樣核對。摘要逐批列出 `concurrentRoster.rigKind`、`playersWithConfirmedFire` 及實際採用的 `minimumMilliseconds`。若原始證據未通過，錯誤會指出 `venueManifests` 陣列中從 1 開始計算的項次。

在 `--inspect-venue-stages` 的收件報告中，`issues[].concurrentRoster` 會列出共同時段不足的門檻、原錄製可確認的最長共同毫秒數，以及各場次房間組合各自的最長連續時段。若時段達標但沒有一段包含所有席位的封存射擊，`missingFireSeats` 會列出在射擊席位最多的合格時段內仍待補的房號與席號。席數相同時採較長的時段。請依這些資料安排重測，再重跑正式驗收。

每個 `groups` 項目附上 `longestWindow` 的實際 UTC 起訖及 `continuousWindows` 區間數。獨立模式可在這裡看出各房有自己的有效區間，但時間沒有交集。`interruptions` 列出暫停、場次暫緩、畫格間隔超標或 tick 未前進的原畫格。`affectedSeats` 附上原房號、席位與畫格狀態。每類只記錄畫格數與第一、最後一格的原世界序號和 UTC。`disconnected` 取自原世界畫格的 `connected: false`，要區分追蹤失效與網路中斷時請比對玩家及伺服器的原日誌。

只收到一批時，在該批 `venue.json` 設定原 `minimumConcurrentMilliseconds` 及每場的 `worldJournal`，可直接檢查同樣的時段資料。未達門檻時輸出 `concurrentRoster`，退出碼為 1。

```powershell
python scripts/verify-field-results.py --venue-manifest .\venue.json --inspect-concurrent-roster
```

##### 六批使用各自的 Windows 啟動回條

在 `stages.json` 加入 `"requireVerifiedVenueStart": true`，並在六份批次清單各自引用原 `verifiedVenueStart`。驗收會逐批核對原預檢、就緒及結束報告，並拒絕重複使用同一個啟動批次 ID。缺少回條時，錯誤會指出總清單中的項次。摘要會顯示各批已核對的回條及原啟動 ID。 [保存及引用回條](#核對-windows-五房啟動回條)

用 `--inspect-venue-stages` 檢查待補資料。記載的 SHA-256 與所引用的檔案不符時，`issues[].evidenceMismatch` 會列出 `kind`、檔名 `name` 及 `sha256-mismatch`。`kind` 例如 `venueLauncherReport`（結束報告）、`udpPreflightBatch`（原 UDP 預檢）、`windowsReadyReport`（就緒報告）、`windowsLaunchPreview`（啟動預覽）或 `roomAlignmentBundle`（MR 或混合部署 ZIP）。檔案不存在時，查看 `missingFile` 或 `udpPreflight` 的對應項目。這些欄位只列檔名，正式驗收會拒絕缺檔或雜湊不一致的批次。

##### 六批核對同一份 Windows 伺服器發行

準備總清單時指定 `--require-server-release`，或在 `stages.json` 加入 `"requireServerRelease": true`。六批都須引用同一份原場館發行報告，並各自提交原五房終止報告。驗收會核對兩者的 `serverManifestSha256`，在各批的 `serverRelease` 列出摘要和原場次數。提交啟動回條時，也會核對原就緒及預覽報告。各批在自己的 `venue.json` 設定的要求也會套用。 [五房伺服器發行證據](#核對五房伺服器發行版本)

收件檢查的 `issues[].evidenceMismatch` 會指出報告種類及檔名。`missing-report` 表示清單缺少原報告引用，`missing-server-manifest` 表示原報告沒有伺服器清單摘要，`server-manifest-mismatch` 表示伺服器清單摘要不一致。`venue-release-report-mismatch` 表示其中一份證據對應到不同的場館發行報告位元組。若清單已列出報告、檔案仍未收齊，查看 `missingFile`。`missingStages` 列出尚未通過的模式及人數。

##### 六批核對伺服器和每席的完整發行證據

用 `prepare-venue-stages.py --require-complete-venue-release` 建立總清單時，工具會將六批共用原發行 JSON 的 SHA-256 保存到 `venueReleaseReportSha256`。六批的發行 JSON、各自的 Windows 伺服器終止報告、每席 Windows 玩家退出報告或驗收 ZIP，以及每席 Quest 部署報告都須對應到該份原檔。若一個階段只使用其中一種玩家平台，驗收依該批實際提交的席位核對。開場回條、同時追蹤、連線量測與跨機驗收沿用各自條件。

仍可先建立總清單再收件。`--inspect-venue-stages` 的 `issues[].venueReleaseCoverage` 會列出缺少完整摘要的伺服器房間組合及 Windows／Quest 房席。已附摘要但不同時，收件原樣指出不符的證據檔，Windows ZIP 收件則在 `windowsInbox.issues` 列出原檔名。更換整批發行時，用新的原發行報告及該版各批產生的證據建立新總清單。舊封存可沿用原有驗收選項。

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

要核對至少一分鐘，在原場館清單加入 `"minimumConcurrentMilliseconds": 60000`，每場提供關閉後的原 `.worldlog`。工具逐格比對最終已核對的玩家與房號，要求全部原席位同時連線、場次處於執行中且遊戲 tick 向前。管理更新前後可能在同一 tick 各擷取一格。這些畫格仍逐格核對所有席位，區間要等下一個前進 tick 才會延長，且距上一個前進畫格至多 500 毫秒。暫停、管理中斷、席位失效、tick 倒退或超過期限都會切斷區間。

獨立模式按五份錄製的 UTC 擷取時間求共同區間，合併模式直接使用該場錄製。跨機擷取前需校對各遊戲伺服器時鐘。通過時 `concurrentRoster` 會列出最長共同區間的毫秒數與 UTC 起訖。時長不足時，整份驗收會退出並回傳錯誤。這份結果核對的是封存快照，實際時鐘同步、頭盔操作、實體主機數及網路容量須另依場館驗收。

要驗收 25 席同時維持追蹤，在同一份清單再設定 `"requireTrackedRoster": true`。每個合格畫格須同時包含所有原席位的有效 `Tracked` 姿態，並沿用原有的 500 毫秒畫格間隔及執行狀態條件。此選項會自動核對 `playerSources`，逐席接受已配對原入場的 Quest logcat，或已完成 OpenXR 啟動且執行環境未標示為 Unity Mock Runtime 的 Windows 日誌。桌面模擬及已識別的 Mock Runtime 日誌會被拒絕。通過時 `concurrentRoster.rigKind` 為 `Tracked`，並附各場 `playerSources`。實體頭盔與主機身分仍需現場確認。 [驗收紀錄](PROGRESS.md#2026-11-10-核對-25-席同時追蹤的封存區間)

### 核對 25 席在共同區間開火

在原五房場館清單設定 `"requireConcurrentFire": true` 與 `"minimumConcurrentMilliseconds": 10000`，或填入該場驗收所需的毫秒數。每場保留原 `worldJournal` 與 `combatJournal`。25 席連線且任務持續執行時，讓每席至少開火一次，再結束全館並等待雙封存。

工具核對回放射擊與戰鬥日誌中的原事件、射擊、玩家及戰鬥序號。夾住射擊 tick 的前後畫格都須位於同一段五房共同區間。射擊造成的同 tick 額外畫格須等到 500 毫秒內的下一個前進 tick，才計入驗收。合格時 `concurrentRoster.playersWithConfirmedFire` 為 25，時間範圍取符合條件的最長區間。只連線或在共同區間之外射擊的席位會使驗收失敗。可與 `requireTrackedRoster` 一併啟用。實體設備數與跨機容量依現地驗收另行確認。

### 核對五房追蹤開場錄製

使用五房追蹤政策開場，再由主控批次結束並下載原場館驗收 ZIP。在 `venue.json` 設定 `"verifyTrackingBegin": true`，並逐場提供原生 `worldJournal`。工具會核對 `closure.json` 中每場的 `trackingBegin` 指向同一開始批次，逐場查驗原來源、開始前管理序號、擷取時間偏移及所有原席位的追蹤姿態。每場也要有觀察到開始序號的後續有效執行格。

0.31.237 的 5／10 席試場須在 `venue.json` 設定 `expectedPlayersPerRoom` 為 `1` 或 `2`。兩種開場政策都會比對封存中的 `playersPerRoom`、五房每個原席位及當時的錄製畫格。25 席可沿用原清單格式。

結果中的 `trackingBegin` 列出原開始批次、場次數及通過核對的追蹤席位數。逐場 `worldJournal.trackingBegin` 列出原準備畫格、開始序號和第一格符合條件的執行畫格。管理包 0.31.65 或更早的開場仍可走一般封存核對。追蹤姿態、裝置來源與實體容量分別驗收。 [開場操作](PLAYER_READINESS.md#五房追蹤驗收開場)

### 核對五房有效姿態開場

若場次使用五房有效姿態政策，從全館收尾下載原場館驗收 ZIP。在 `venue.json` 設定 `"verifyParticipationBegin": true`，每場提供原 `worldJournal`。此選項與 `verifyTrackingBegin` 擇一。

工具從 `closure.json` 讀取 `participationBegin`，依原錄製核對同一次開場、管理序號、準備中畫格及原名冊玩家及房間，再找出各場在結束前套用開場的第一個有效執行格。VR 開場可核對合成或追蹤姿態，MR 須為追蹤。結果的 `participationBegin` 列出全館及逐場的確認席數，並分列合成與追蹤。 [開場操作](PLAYER_READINESS.md#五房各-5-席有效姿態開場)

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

#### 核對指定獨立房間的環境批次

使用主控台 0.31.229 或更新版本選取獨立房間時，把當時勾選的房號填入該項 `roomIds`，並附上原下載的環境批次 JSON。例如：

```json
{"action": "SetEnvironment", "phaseReport": "rooms-1-and-4.json", "roomIds": [1, 4]}
```

工具核對原批次恰好包含所列房間的原場次，並從各自的錄製找出對應的執行畫格。結果中的 `roomIds` 和 `sessionsVerified` 列出此項已確認的房間及場次數。整批驗收仍使用原五房收尾資料及各場錄製。0.31.264 的指定獨立房敵軍批次直接從原報告的 `latestEnemies.roomIds` 取得範圍，使用 `--venue-control-batch SetEnemies <批次報告>` 即可。其餘未列範圍的批次須涵蓋原收尾的所有場次。

用 `prepare-venue-field-manifest.py` 整理封存時，可直接加上 `--scoped-environment-batch '1,4' '.\rooms-1-and-4.json'`。全館天氣與敵軍報告分別可用 `--venue-control-batch SetEnvironment '.\weather.json'` 和 `--venue-control-batch SetEnemies '.\enemies.json'`。每個原報告各使用一次對應參數。工具會在寫出新清單前核對原環境與敵軍指令的執行畫格。

### 核對合併場的分房敵軍策略

合併場可在 `venue.json` 填入 `roomEnemyPolicyChecks`，並照常保留原 `worldJournal`。`appliedAtSequence` 填入管理 API 套用或恢復策略回條上的序號。`inherited` 表示該房是否沿用全場策略，`behavior` 與 `autoAttack` 則填入預期的實際設定。可在同一序號列出其他房間，確認房間間的策略隔離。 [房控操作](LAYOUT.md#合併場分房敵軍策略)

```json
{
  "roomEnemyPolicyChecks": [
    {"roomId": 2, "appliedAtSequence": 29, "inherited": false, "behavior": "Patrol", "autoAttack": true},
    {"roomId": 1, "appliedAtSequence": 29, "inherited": true, "behavior": "Hold", "autoAttack": false},
    {"roomId": 2, "appliedAtSequence": 31, "inherited": true, "behavior": "Hold", "autoAttack": false}
  ]
}
```

`verify-field-results.py --venue-manifest` 核對該管理序號下每個有效的執行畫格。結果的 `worldJournal.roomEnemyPolicyFrames` 會逐房列出第一個相符畫格的 `worldSequence`，可用於回放。只有較晚序號、暫停或暫緩的畫格時，工具會指出缺少畫格的房間及序號。

### 核對 Quest 開場追蹤回條

在 `direct-lan` 驗收清單的 `questReadinessReports` 加入每一批部署的成功追蹤回條。使用 `prepare-venue-field-manifest.py` 時可重複指定 `--quest-readiness-report`，並照常提供原部署報告、發行報告和玩家日誌。手動編輯時可加入下列欄位。 [保存開場前回條](QUEST3.md#核對本次部署與追蹤席位)

```json
{
  "questReadinessReports": ["quest-a/ready.json", "quest-b/ready.json"]
}
```

`verify-field-results.py --venue-manifest` 會核對回條引用的部署與 ZIP 雜湊，並從各場的原封存世界日誌定位同一格 `Preparing` 畫格。工具比對原擷取時間、管理序號，以及該格內已連線、存活且使用追蹤姿態的玩家。入場識別另由原部署與戰績回條比對。各份回條須涵蓋所有已提交的 Quest 部署席位。同一份回條共用取樣時間，分批回條可以各有自己的取樣時間。

成功時摘要列出 `questReadiness` 的回條數、場次數及席位數。各場的 `worldJournal.questReadinessFrames` 提供可定位回放的世界序號。全館同時開場、持續操作及實機驗收沿用各自的檢查。 [五房追蹤驗收開場](PLAYER_READINESS.md#五房追蹤驗收開場) · [核對同時連線區間](#核對-25-席同時連線的區間)

若同時啟用 `verifyTrackingBegin` 或 `verifyParticipationBegin`，會逐場比對 Quest 取樣和伺服器受理開始時使用的原準備畫格。取樣可以引用同一格或較早的準備畫格。引用較晚的畫格會使本次驗收失敗。

若用 `-DeploymentReportsFile` 產生同輪取樣的第 2 版回條，`questReadinessReports` 只填這一份。工具逐席比對原部署報告摘要、成功啟動席位和原準備畫格，並在 `questReadiness.deploymentReportsMatched` 列出核對的原部署報告數。未完成的原報告可提供先前已啟動席位的證據，整份取樣回條仍須涵蓋五房驗收中所有已部署的 Quest 席位。 [同輪取樣操作](QUEST3.md#同一輪核對分批部署的追蹤)

### 直接使用 Quest 批次擷取報告

若擷取時使用 `--deployment-report`，請在同一份 `venue.json` 的 `questDeployments.reports` 提供擷取所引用的部署原檔。工具會逐份核對 SHA-256、房間、席位、場次與埠，通過時摘要列出 `questCaptureDeploymentReportsMatched`。原部署報告和擷取報告應一起保存。 [Quest 批次擷取](QUEST3.md#一次擷取五房-quest-日誌)

在 `questCaptures` 提供 `deviceMap` 且原擷取報告含 `captureBinding` 時，工具會按每批原席位重算裝置表指紋。重試沿用同一組指紋時，請一併提交首次及後續報告，工具會合併該組原席位。報告與裝置表可任意排序。摘要的 `questCaptureDeviceBindingsVerified` 列出通過核對的指紋組數。擷取同時引用部署報告時，也會比對兩份報告所指的部署 ZIP 摘要。

使用 `--capture-deployed-seats` 時，同時提交該次擷取所引用的原未完成部署報告，以及後續部署與擷取原檔。若沿用累計重試，提交銜接兩份報告的原重試歷程。驗收確認每個提早擷取的席位已包含於它引用的原成功批次，並列出引用的未完成部署報告數 `questPartialDeploymentsReferenced`。全部 Quest 席位仍需有完整擷取後才通過。 [部署中斷後擷取](QUEST3.md#部署中斷時先擷取已啟動的席位)

在 `direct-lan` 場館清單加入下列欄位。保留每份原 `capture-report.json` 與同一資料夾內的原日誌。網路計畫使用 Quest UDP 預檢的版本 1 格式，列出這次五房所有遊戲端點，以及各 Quest 席位實際使用的 IPv4。 [網路計畫格式](QUEST3.md#批次預檢五房-quest-席位) · [整批擷取](QUEST3.md#一次擷取五房-quest-日誌)

```json
{
  "questCaptures": {
    "networkPlan": "network-plan.json",
    "deviceMap": "device-map.json",
    "reports": [
      "quest-capture-a/capture-report.json",
      "quest-capture-b/capture-report.json"
    ]
  }
}
```

首次與重試的原報告可一併列入。各報告保留原成功與失敗記錄，所有成功席位合起來須剛好涵蓋計畫列出的 Quest 席位，每席只接受一次完整擷取。工具重讀完整日誌核對位元組數和 SHA-256，再核對原程序、房號席位、伺服器觀察到的 IPv4、遊戲端點和戰績確認。成功摘要列出 `questCaptureBatchesVerified` 及 `questCaptureSeatsVerified`，若曾有未完成報告，另列 `questCaptureIncompleteReports` 與 `questCaptureFailedAttempts`。混合場可用 `windowsPlayers` 或 `windowsEvidenceDirectory` 補上 Windows 證據。手動提交 Quest 原日誌可沿用 `players` 及 `logcatPid`。 [重試失敗席位](QUEST3.md#重試未完成的-quest-擷取席位)

若報告含 `completedDeviceFingerprints`，請保留每個已完成席位首次寫入該指紋的原報告。封存驗收會核對同一批基準下的歷次指紋，同一頭盔不可對應兩個完成席位。成功摘要的 `questCaptureSeatDeviceFingerprintsVerified` 列出核對過的席位數。

#### 以原 Quest 裝置對照表驗收收尾

收尾時可在 `questCaptures` 同時指定原 `networkPlan` 與部署時的版本 1 `deviceMap`，兩者須涵蓋相同的 Quest 席位。當擷取引用原部署報告時，工具會依該批部署的原席位重新計算裝置表指紋。分批部署可在裝置表合併各批的原席位與 ADB 標籤。`questDeployment.deviceMapsMatched` 會列出通過指紋核對的原部署報告數。使用 `networkPlan` 時，工具會比對伺服器觀察的來源與現場記錄的 IPv4。開場前的 UDP 預檢沿用原網路計畫。 [裝置與網路計畫](QUEST3.md#批次預檢五房-quest-席位)

只填 `deviceMap` 時，工具依各席最後一條獲伺服器戰績確認的連線取得來源 IPv4，核對各席的私有直連位址與遊戲埠。摘要會標示 `questCaptureAddressSource` 為 `server-observed`。

```json
{
  "questCaptures": {
    "deviceMap": "device-map.json",
    "reports": ["quest-capture/capture-report.json", "quest-capture-retry/capture-report.json"]
  }
}
```

### 核對封存席位的 Quest 發行 APK

使用 `-ReleaseReport` 部署時，保存正式部署指令輸出的 JSON，以及用來部署的原 `venue-release.json`。驗收會將部署報告的 `venueReleaseReportSha256` 與原檔比對。`releaseReportSeatsVerified` 列出通過整份發行報告核對的席位數，六批摘要會在各批的 `questRelease` 顯示。更換原發行檔時，即使 APK 摘要相同，收件檢查仍會以 `questDeploymentReport` 指出不符的部署報告。舊報告也可提交，已有的 APK、入場及戰績證據照常核對。

使用 `-RetryIncomplete` 續跑時，可在五房 `venue.json` 只填最新的累計報告，或把它與一路承接的原報告一併填入。檔案可任意排序，請保留原始位元組。使用手動分批清單時，填各份報告，各份成功席位必須互不重複。 [Quest 部署操作](QUEST3.md#從原部署報告重試未完成席位)

使用 `-RequireOpenXR` 的部署報告也會核對逐席原 logcat。原 PID 及本次啟動識別值須相符，且 loader、顯示及輸入子系統的就緒記錄須出現在最終戰績之前。成功摘要會列出 `questDeployment.openXRSeatsVerified`。 [部署時核對每席 OpenXR](QUEST3.md#部署時核對每席-openxr)

場館可在準備清單時加 `prepare-venue-field-manifest.py --require-quest-openxr`，或在 `venue.json` 加 `"requireQuestOpenXR": true`，明確要求原部署與原 logcat 提供每個 Quest 席位的 OpenXR 啟動證據。至少須有一個 Quest 席位。正式驗收會在 `questOpenXR` 輸出預期與核對席數。遇到缺件或日誌不符時，以退出碼 1 列出房號、席號與原因。此處核對的是 OpenXR 程序日誌與原戰績，實體頭盔顯示及追蹤沿用各自的測試流程。只驗收 Windows 的批次可省略此欄位。

```json
{
  "questDeployments": {
    "releaseReport": "venue-release.json",
    "reports": ["quest-deployment.json", "quest-deployment-retry.json"]
  }
}
```

驗收核對每個成功席位的原場次、玩家、入場名額、房號、席位、UDP 埠與 APK 版本。每席須有已核對 APK 及設定檔的啟動紀錄，並與原 Quest logcat、伺服器戰績確認及封存資料一致。提交重試歷史時，工具會核對前一份報告的 SHA-256、同一原部署及已完成席位，累計結果中的每席只計一次。歷史中斷、分岔或修改已完成席位都會拒絕。早期未記錄前一份雜湊的累計報告只需提交最新一份。摘要 `questDeployment` 列出版本代碼、APK 雜湊、報告數及核對席位數，成功核對報告承接時另列 `retryReportsLinked`。實體裝置與運行環境須現場驗收。

新部署報告會針對同一組場次建立可跨分批比對的裝置指紋。重新取得同一組場次的部署 ZIP 時，指紋仍可比對。驗收會拒絕兩份報告把同一裝置算在兩個已啟動席位的情形，並只列出衝突的房號與席號。`questDeployment.venueDeviceSeatsVerified` 計入有此證據且通過比對的席位。仍可提交較早的原報告，沒有此欄位的席位不計入這個數字。 [合併取樣](QUEST3.md#核對頭盔追蹤席位)

### 核對 MR 校正封存

五房驗收可在產生清單的指令加上 `--room-alignment-bundle .\deployment.zip`，直接引用原 MR 或混合部署 ZIP。5 人試場加上 `--players-per-room 1`，10 人試場加上 `--players-per-room 2`。手動建立清單時，填 `roomAlignmentBundle` 為原 ZIP 路徑，另用 `expectedPlayersPerRoom` 設定試場席數。準備與驗收會比對 ZIP 的拓撲、原場次、部署席數及分房連線檔名稱。固定人數批次也會核對封存名冊的房號與席位。離場稽核則以 `expectedFinalPlayersByRoom` 核對結束名冊，可引用開場時較多席位的部署包。混合 ZIP 另核對各房 VR 或 MR 模式及封存 UDP 端點。

準備指令會保存整份原 ZIP 的 `roomAlignmentBundleSha256`。正式驗收與六批收件會重新比對，六批結果會列出原 ZIP 雜湊與通過校正的房間數。工具讀取套件清單、各分房 ZIP 的檔名索引與校正檔，票券內容留在原 ZIP 內。請按部署資料的原存放權限保管。

若逐房提供 JSON，在整批清單的每個 MR 場次填入 `roomAlignments`，混合批次的 VR 場次只填自己的回放檔。單場驗收加入 `--world-journal .\room-02.worldlog --room-alignment 2 .\room-02-alignment.json`。合併 MR 場次每房各加一次 `--room-alignment`。兩種校正來源都須提供全部場次的原 `worldJournal`，並核對原任務的 MR 模式、遊戲伺服器回放的 `quest-room-mr-v1` 設定、校正 JSON 的房號與原始位元。選用校正核對後，任一 MR 房間缺檔或校正檔改寫即拒絕整批。

當前 MR 規格要求原 Quest 3 席位使用原始 logcat，並通過實際 UDP 來源、原入場、戰績確認及封存檢查。摘要列出已核對房號和原檔 SHA-256。場地量測精度、實際透視、跨機容量與設備仍須現場驗收。 [Quest 擷取](QUEST3.md#收集-quest-場館驗收日誌)

## Quest 遊戲內連線量測

啟用 `-RecordLinkMetrics` 的 Quest 開發版玩家在任務執行中實際送出約每秒一筆遊戲內探測，沿用伺服器依原連線及入場核准的回覆限制。客戶端記錄 30 筆結案採樣，區分回覆、0.9 秒逾時及中斷。探測最長從首次執行中狀態起等候 240 秒。摘要用回覆樣本算 p95，另用各採樣窗的 Unity 更新次數及時間算每秒更新數。顯示幀率與網卡頻寬仍依現場量測。 [Quest 部署](QUEST3.md#記錄-quest-遊戲內連線量測)

在原五房驗收清單頂層加入 `"requireQuestLinkMetrics": true`，或在產生清單時加 `--require-quest-link-metrics`。單場驗收也可在原 `--quest-player` 指令加同一旗標。工具逐席從原 logcat 合併報告片段，核對 PID、原連線及伺服器確認的最終戰績。量測片段須位於該條連線建立與最終戰績之間。缺少、重複或順序錯誤的片段會使該席量測驗收失敗。

Quest 0.50.11 起，原程序重連後會在新連線第一次進入執行中時重新採樣，並保留各條連線的報告。若驗收需要量測，從最後一次成功重連起留足時間完成 30 筆，再由主控結束任務。驗收取伺服器確認最終戰績的那條連線。 [Quest 重連操作](QUEST_RECONNECT.md)

五房結果在 `questLinkMetricsVerified` 列出通過數量，並在各場 `questLinkMetrics` 顯示房號、席位、回覆／逾時／中斷與效能摘要。Windows 席位可同時沿用下方量測格式。原 logcat 已保留量測片段，無需把頭盔日誌重新編排成量測檔。 [Android 日誌格式](https://developer.android.com/tools/logcat)

### 逐席核對 Quest 連線量測門檻

若現場有指定的連線門檻，把兩個數值設為場館規格。回覆數為 1 到 30，p95 往返時間上限為 0 到 900 毫秒。

```json
{"questLinkCriteria":{"minimumReplies":28,"maximumP95RoundTripMs":40}}
```

`prepare-venue-field-manifest.py` 可用 `--quest-minimum-replies 28 --quest-maximum-p95-ms 40` 寫入相同欄位。單場模式把這兩個旗標加到原 `verify-field-results.py --quest-player` 驗收指令。每位 Quest 玩家以自身 30 筆原始採樣判定，p95 等於上限時可通過。通過的摘要保存實際門檻與 `seatsVerified`。混合場可另用 `windowsLinkCriteria` 設定 Windows 的門檻。

## Windows 玩家連線量測

自 0.46.0 起，Windows 開發版玩家程式可選用本機量測。以正常玩家票券入場，指定一個尚未存在的 JSON 完整路徑，其上層目錄須已存在。

```powershell
& "<Windows玩家包路徑>/Launch-Player.exe" --config "<玩家連線檔.json>" --launch --wait --link-metrics "<新量測檔的絕對路徑.json>" --log "<新日誌.txt>" --report "<新程序報告.json>"
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

Windows 玩家啟動器 1.17 的原退出報告含 `venueReleaseReportSha256`。收件和正式封存會與頂層 `venueReleaseReport` 原檔比對。Windows 玩家、Quest 部署及伺服器可用同一份原檔提出證據。收件不符時，`windowsInbox.issues` 列出有問題的 ZIP 檔名和 `venue-release-report-mismatch`。六批摘要的 `windowsRelease.releaseReportSeatsVerified` 顯示核對了整份報告的 Windows 席數。較早的玩家報告仍依原套件清單、日誌及戰績核對。

### 核對五房伺服器發行版本

同時提供 `venueReleaseReport` 和含 `serverManifestSha256` 的五房終止報告時，驗收會比對兩份檔案的伺服器清單摘要。成功時 `venueRelease.server` 會列出摘要及核對到的原場次數。若一併提交 `verifiedVenueStart`，也會比對啟動回條引用的原就緒檔與 UDP 報告引用的原預覽。任一檔案的摘要不同，驗收會失敗。

Windows 啟動器 1.26 起會另記錄 `venueReleaseReportSha256`。驗收會比對該摘要與 `venueReleaseReport` 原檔。若有啟動回條，也會核對同次預覽、就緒及收尾是否紀錄同一份原發行報告。舊版只含伺服器清單摘要的封存可沿用原驗收項目。

本次驗收若要求伺服器發行證據，準備清單時同時指定 `--venue-release-report` 和 `--require-server-release`。手動建立的 `venue.json` 可填 `"requireServerRelease": true`。啟動時須用原發行報告執行五房命令，讓終止檔保存核對結果。 [五房啟動方式](WINDOWS_SERVER_PACKAGE.md#依場館發行報告核對伺服器包)

### 收集 Windows 玩家驗收 ZIP

玩家以啟動器 1.10 核對本次發行並完成場次後，從「開啟本次紀錄資料夾」取出 `player-evidence.zip`。請把每位玩家的原 ZIP 放在同批私人資料夾，並記錄該電腦本次使用的 IPv4。在 `venue.json` 保留 `venueReleaseReport`，於 `windowsPlayers` 或逐場 `players` 使用下列格式。

```json
{"address":"192.168.1.20","evidenceZip":"room-01-seat-01/player-evidence.zip"}
```

工具直接讀取 ZIP 內原日誌與退出報告。每席可使用 ZIP 或分開的 `log`、`launcherReport`，同一批可混用不同格式。 [玩家端操作](WINDOWS_PLAYER_PACKAGE.md#依場館發行報告核對玩家包)

需要量測時，Windows 啟動器 1.13 的玩家在視窗核對本次場館發行報告後，勾選「記錄本次連線量測」再開始遊戲。保留任務執行至每席 30 筆量測結案，再由主控結束任務。玩家收到最終戰績並關閉遊戲後，從本次紀錄資料夾交回 ZIP。

使用 1.14.1 時，玩家可在任務仍執行時查看啟動器的量測狀態並回報主控。`30／30` 代表樣本均已結案，實際回覆、逾時及中斷各自列出。提早停止會標示「連線量測已停止」，重新入場會標示先前量測未涵蓋目前連線。 [玩家視窗](WINDOWS_PLAYER_PACKAGE.md#依場館發行報告核對玩家包)

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

第一條指令列出應收及已收的 Windows 席位、缺件與有問題的檔名，缺件或衝突時以退出碼 1 結束。配對依據是原名冊的入場與場次識別、退出報告及原伺服器對該連線的戰績確認，玩家可自行命名 ZIP。每席的最終戰績及管理、世界、戰鬥序號也須與原封存一致。若不符，該檔會出現在 `issues`。尚無有效 ZIP 的席位會列在 `missingSeats`。每席的 IPv4 取自伺服器觀察到的對應 UDP 來源。

收件檢查也會核對 ZIP 內的連線量測。若本批有 Windows 席位提供量測，須由所有 Windows 席位提供，Quest 席位沿用原 logcat 流程。內含量測不符、遺失或覆蓋席位不足時，收件檢查會指出對應的 ZIP。

收件完成後執行第二條指令，工具沿用同一資料夾完成原場次封存及戰績驗收。混合場的 Quest 證據照原欄位提供，可在 Windows 收件檢查後補齊。

#### 核對 Windows 席位的來源 IPv4

開場前，將原 `windowsSeatMap` 中各電腦本次使用的 IPv4 記在私人 `station-addresses.json`。每個電腦標籤填一次，順序可調整，大小寫會視為相同。下例涵蓋兩個 Windows 席位，其他席位可照常使用 Quest 證據。

```json
{"version":1,"stations":[{"station":"PC-A","address":"192.168.1.20"},{"station":"PC-B","address":"192.168.1.21"}]}
```

在 `venue.json` 加入 `"windowsStationAddresses": "station-addresses.json"`，或在產生清單時與 `--windows-seat-map` 一起提供 `--windows-station-addresses`。收件和完整驗收都會比對原伺服器記錄、且已確認戰績的連線來源。若不符，收件會列出 ZIP 檔名、席位及電腦標籤。摘要記錄預期席位數、通過數及位址表 SHA-256。實體設備識別與跨機容量仍依現地驗收。 [準備驗收清單](#核對五房批次啟動器的原終止報告)

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
