# 開發進度

## 2026-11-06 任務配置出生位通路預覽

控制台 0.31.7 在草稿配置圖畫出五席到中線的取樣通路，並在開場區顯示已儲存版本的摘要。服務使用 0.5 公尺格點，逐段使用遊戲實際的通行判定。六個貼齊的沙包可讓基本配置通過，但會讓五席沒有取樣路徑。移開一個沙包後五席皆可經缺口到中線。操作員仍可選用原防線。 [預覽與契約](LAYOUT.md#出生位通路預覽)

- 來源 `f6131a5ba122ab809591c1df67b2f08637a9ccc1` 通過 783 項核心、571 項 HTTP、47 項世界串流、91 項 Node、318 項 Chromium 與 105 項解壓管理包檢查。瀏覽器實際移除沙包、儲存修訂，並確認原版本仍顯示缺少通路。
- Windows 三包測試 `run-67f2f10376634fcebb3b99cd1a54d4ef` exit 0，355 項通過。五房獨立與五房連線各 25 個同機模擬玩家。六場的 30 條預覽路線均通過同一缺口，封存世界共 50 個沙包座標與保存版本相符。共 889 幀完整回放、50 份戰績、6 份 CSV，第一房由控制台結束後核對世界封存序號 211。清理後 C／F 的 221 份原始檔相符，管理包測試另有 27 份相符。通路逐段由共用 C# 通行判定驗證，本輪原生場的玩家維持在出生區。
- Windows 管理包採 API 0.31.0，遊戲使用既有 0.41.2。預覽適用玩家平面取樣，運行中的敵軍路線、實際跨機、頭盔、廠商硬體與 25 位真人仍待驗。GitHub Actions 工作 42097466387／127491166056 因帳務條件未啟動。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42097466387/job/127491166056)

## 2026-11-06 五房有效姿態總覽

控制台 0.31.6 在房卡分列名冊、有效姿態、合成和追蹤人數。主控可同時查看五房，房控只收到自己的房間。五房連線由同一份已接受快照分房計數。畫面不沿用過期、錯場次或讀取失敗的有效人數。 [欄位與操作方式](PLAYER_READINESS.md#五房總覽)

- 來源 `c9cc3bb04591c8763eee88225b0be990991adf4b` 通過 778 項核心、567 項 HTTP、47 項世界串流、91 項 Node、314 項 Chromium 與 105 項解壓管理包檢查。瀏覽器的追蹤數字以測試回應驗證顯示。HTTP 實際驗證匿名與遊戲伺服器角色拒絕、房控只讀自己的房卡及主控讀取五房。
- Windows 三包測試 `run-9d6a1bccc3964d6c9964c6f6ccb6e4a7` exit 0，343 項通過。五房獨立與五房連線各有 25 個同機模擬玩家，兩種模式的房卡資料皆為每房 5 筆合成、0 筆追蹤。新版控制台在五個獨立房間同時運行時顯示所有房卡，從畫面送出第一房的 End 後，世界封存序號 194 對上原伺服器。共 831 幀完整回放、50 份戰績與 6 份 CSV。清理後 C／F 的 221 份原始檔相符，管理包另有 27 份清理後檔案相符。
- Windows 管理包仍採 API 0.31.0，遊戲使用既有 0.41.2 建置。GitHub Actions 工作 42095436816／127484096337 因帳務條件未啟動，沒有執行步驟。跨機、頭盔、廠商硬體及 25 位真人仍待驗。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42095436816/job/127484096337)

## 2026-11-06 五房控制台場次隔離

控制台 0.31.5 修正背景更新期間的場次切換。若選取的場次離開清單，控制台會清空選取並隱藏原操作區。下一筆操作須明確選取場次。操作者已按下但尚未送出的操作會核對原場次，場次已結束或不符時停止。原 End 回條仍保留場次與封存進度。 [操作與隔離方式](SESSION_CLOSURE.md#場次切換與操作)

- 舊版 0.31.4 的兩房受控反例在 `console-room-fence-before` 保留。瀏覽器按下場次 A 的暫停，在外部結束 A 與刷新完成後，實際送出一筆對 B 的暫停，B 變成 Paused。新版重跑時送出零筆，B 維持 Running，選取清空。明確選擇 B 才成功送出一筆正確命令。
- 來源 `2caf8a2944ee39eb49a46226c96109d3091cda98` 通過 89 項 Node、309 項完整 Chromium、20 項聚焦 Chromium 及 105 項解壓管理包檢查。實際解壓包另重跑 20 項聚焦 Chromium。管理包測試清理後 C／F 的 27 份檔案 SHA256 相符。新版管理包使用 API 0.31.0，Unity Windows 與 Quest APK 沿用 0.41.2。 [管理包與 SHA256](WINDOWS_CONTROL_PACKAGE.md)
- 三包測試 `run-7159b1e3b14d4fe69517b0979034a681` exit 0。兩種模式各 25 個同機模擬玩家，338 項、932 幀完整回放、50 份戰績及 6 份 CSV。第一房使用新版控制台實際送出一筆 End，原場次與來源留在頁面，世界封存序號 199 對上原伺服器報告。清理後無活動場次，C／F 的 221 份原始檔 SHA256 相符。
- GitHub Actions 工作 42092953218／127475496332 因帳務條件未啟動，沒有執行步驟。實際跨機、頭盔、廠商硬體及 25 位真人仍待驗。 [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42092953218/job/127475496332)

## 2026-11-06 Windows 遊戲伺服器來源診斷

遊戲 0.41.2 與 Windows 伺服器啟動器 1.2 新增 `--peer-diagnostics on`。核准玩家入場後，專用伺服器從 Unity Transport 取得實際來源位址與 UDP 埠，依原連線編號記錄。每次啟動上限 256 筆。預設關閉，含來源位址的日誌留在私人工作資料夾。 [部署與跨機核對方式](WINDOWS_SERVER_PACKAGE.md#跨機來源診斷)

- 來源 `7f0d98decb2b0e125799d037d1b5b011eb0542d7` 的 `run-3951b15ccdd441aca65bd8a63acf8c61` exit 0。使用實際解壓的三包，兩種模式各 25 個同機模擬玩家，335 項、778 幀回放、50 份戰績及 6 份 CSV。Linked 的 25 筆來源端點都有不同 UDP 來源埠，全部對應原入場編號與伺服器戰績確認回條。五個獨立房間預設無來源列，無效診斷參數被拒絕且未啟動戰場。
- 清理後無活動場次及本輪程序，C／F 的 219 份原始檔 SHA256 相符。新版兩個 Windows ZIP 各有 311 筆檔案清單，玩家包的 19 項解壓測試通過。原 0.41.1 Windows、APK 及 Unity 日誌共 321 份已在 C／F 核對保存。 [伺服器包](WINDOWS_SERVER_PACKAGE.md) · [玩家包](WINDOWS_PLAYER_PACKAGE.md)
- 242 項真正 Unity EditMode 測試全數通過。Windows 與 Quest ARM64 的指紋同為 `bf9299c57e1afd0b3531abf6b0891aee01e55d0b68360ce74531973b55aff379`，場景與玩家網路識別沿用原值。APK 60,362,730 bytes，SHA256 `a9abe4fa6ed41a9afb088dcd6cec72d2e139c3dd8c88630ee4e3234a6ef114e3`，版本 53，minSDK 32、targetSDK 35、v2 開發簽章。 [Quest 3 工具鏈](QUEST3.md)
- 本輪來源紀錄由同一台 Windows 電腦的乙太網路 IPv4 驗證。實際跨機、頭盔、廠商硬體及 25 位真人仍待驗。精確來源的 GitHub Actions 工作 42091327531／127469817419 因帳務條件未啟動，沒有執行步驟。 [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42091327531/job/127469817419)

## 2026-11-06 Windows 三個可攜包整合

使用現有管理包 0.31.4、遊戲伺服器與玩家包 0.41.1，在同一台 Windows 電腦以乙太網路 IPv4 驗證整房配票。五個獨立房間各開一個伺服器，五房連線模式共用一個伺服器。兩種模式各有 25 個模擬玩家同時入場。10 份房間 ZIP 由各房控向實際管理包下載，玩家啟動器直接使用 ZIP 內的席位 JSON。 [部署與重現方式](WINDOWS_SERVER_PACKAGE.md#三個可攜包整合驗證)

- 來源 `df70e9d2745a76fa590d03a3900754d0fe60101b` 的 `run-426f9c0ec56c4942888306e05cb9d91a` exit 0，319 項通過。六場共 812 幀完整回放，50 份戰績與 6 份 CSV、戰鬥與世界封存及原連線的伺服器確認回條一致。另有一場刻意終止伺服器啟動器，驗證自己的子程序隨 Job 停止，該場未封存。
- 玩家收到戰績並離線後，測試持原程序 handle 結束仍執行的玩家程式，再確認啟動器回報同一程序退出。清理後沒有本輪程序或活動場次，C／F 的 218 份原始檔 SHA256 相符。三個既有交付 ZIP 的 SHA256 與先前紀錄一致。
- 原 loopback 模式在同一來源的 `run-593e8ebeb6fb47a3885481a162eb54fe` 重跑成功。103 項、518 幀回放、10 份戰績，清理後 C／F 的 78 份檔案 SHA256 相符。另驗證僅提供其中一個新選項、使用 loopback 位址或使用未配置的私有位址均會拒絕。
- 本次使用背景 CLI 與靜止模擬玩家，實際跨機、頭盔、廠商硬體及 25 位真人待驗。Python 包裝測試執行 18 項，17 項通過、1 項跳過。精確來源的 GitHub Actions 工作 42086684963／127453575830 因帳務條件未啟動，沒有執行步驟。 [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42086684963/job/127453575830)

## 2026-11-06 整房配票 ZIP

控制台 0.31.4 新增整房配票。選擇房間後一次下載最多五份 JSON，檔名標示房間與席位。主控可逐房下載，房控限自己的房間，Linked 場次也採相同權限。API 對照一次名冊快照的完整玩家與 admission，若選取過期或場次已結束，回應 409。遊戲端以當前 admission 驗票。 [操作與 API](EXTERNAL_CLIENTS.md)

- 來源 `bba38f0872f5735a941b4f16b9d0fbe35e826c86` 的本機 HTTP 回歸通過，逐一驗證五房 ZIP 共 25 份連線檔的場次、房間、席位與 admission。另通過 89 Node、304 Chromium、7 Python 與 105 項解壓管理包檢查。保留 51 份瀏覽器證據，管理包測試的 C／F 共 27 檔 SHA256 相符。
- 管理包 `control-server-api0.31.0-ui0.31.4-win-x64.zip` 為 52,489,449 bytes，SHA256 `158e4d10e5bde2e347f3661cbbfeefbe57231668e5ee5f7b7b1aba3a6198d18b`，504 項清單、ZIP 505 項，包含 484 項執行環境檔案。 [Windows 管理包](WINDOWS_CONTROL_PACKAGE.md)
- `0a1b0a6` 的原生測試工具在 `20261106-023142-bf225ec0` 從實際瀏覽器下載房間 ZIP，兩位玩家以解出的席位檔入場。9 項通過，兩份戰績與世界封存序號 180 一致。兩個工具均 exit 0，清理後 C／F 共 14 檔 SHA256 相符。此場為同機乙太網路 IPv4 Simulation。跨機、頭盔及真人容量待驗。
- CI 42084911404／job 127447285124 因付款或支出上限條件未啟動，GitHub 回報無執行步驟。 [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42084911404/job/127447285124)

## 2026-11-06 玩家連線檔配票前驗證

控制台 0.31.3 共用場次公告的 IPv4／埠號規則，在送出配票請求前檢查手動輸入。舊版以 `127.1` 實際產生連線檔，新增瀏覽器斷言失敗，原兩份證據保存在 `artifacts/console-ticket-destination-before`。新版驗證縮寫、綁定位址、群播及越界埠皆送出零筆配票請求，改正後只送出一筆，票券對應原玩家及本次 admission。 [外部玩家連線](EXTERNAL_CLIENTS.md)

- 來源 `e3e4e2edddb3115bd92bc8747c598a535cbb83c9` 的本機回歸通過 89 Node、301 Chromium、13 Python 與 105 項解壓管理包檢查。新版保留 51 份瀏覽器證據。管理包為 52,484,295 bytes、504 項清單、ZIP 505 項與 484 項執行環境檔案，SHA256 `0bc73d3452638f83363ac663eee8f767c114449bd7b58e6789712b8512c682dc`。管理包測試結束後 C／F 共 27 檔核對 SHA256。 [Windows 管理包](WINDOWS_CONTROL_PACKAGE.md)
- 解壓包的 API 搭配現有 0.41.1 玩家包做同機乙太網路 IPv4 測試。首場 `20261106-021912-4885cd6e` 等待來源公告逾時，瀏覽器與伺服器工具均 exit 1，當時尚未配票，C／F 共 12 檔相符。第二場 `20261106-022050-932fd3f1` 沿用相同版本與時限，兩工具 exit 0，9 項通過，兩位玩家各自收到戰績，世界封存序號 227，清理後 C／F 共 14 檔相符。跨機、頭盔與真人容量待驗。
- CI 42083067052／job 127440889457 因付款或支出上限條件未啟動，GitHub 回報無執行步驟。 [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42083067052/job/127440889457)

## 2026-11-06 遊戲伺服器本機網卡驗證

外部玩家測試新增 `--local-game-address=<本機IPv4>`，要求位址已指派給本機且屬私有 IPv4。工具核對指定的公告與監聽位址、控制台欄位、伺服器 PID 的 UDP socket 和兩份下載檔。原 loopback 流程繼續作為預設。變更來源為 `3f243c39e394ac3fc7dc4aafbc7e6fdab787db61`。 [外部玩家與雙機驗收步驟](EXTERNAL_CLIENTS.md)

- 乙太網路 IPv4 場 `20261106-020816-f3207f89` 通過 13 項，兩位玩家入場並收到各自的戰績，世界封存序號 637。實際 UDP socket 綁在指定 IPv4 與埠。包啟動器的入場、拒絕、無伺服器及斷線後戰績狀態均已驗證。
- Loopback 場 `20261106-021033-fbf94c7f` 通過 9 項，兩份戰績與世界封存序號 198 一致。兩場測試工具均 exit 0，程序清理後各 14 檔 C／F SHA256 相符。證據涵蓋同機 Simulation，第二台電腦的實體網路、頭盔與真人容量待驗。
- Node 語法、6 項 Python 與 3 個命令列拒絕案例通過。GitHub Actions 42081624524／job 127435870115 因付款或支出上限條件未啟動，沒有執行步驟。上一輪成功 CI 的測試來源為 `e963e48`。 [本輪 GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42081624524/job/127435870115)

## 2026-11-06 玩家連線檔視窗驗證

玩家啟動器 1.1 交付包 `windows-player-0.41.1-v2.zip` 為 82,652,952 bytes，SHA256 `925a8ac16451ae2c423da1b0cb9c9867af17b8fb5b08ab5824f7ea1b1bca8402`。解壓包通過 19 項檢查，Framework 核對類別 24 項與連線狀態 17 項通過。封裝核對確認 311 項清單內容及同源 Unity 0.41.1 執行檔。 [玩家連線檔載入與核對](PLAYER_CONFIG_REVIEW.md)

`20261106-020135-fbe6ceb7` 的實際 WinForms 流程從貼上路徑開始。載入後顯示檔名與目的地，附加 JSON 空白後拒絕啟動，重新載入後開始遊戲。第一位從 GUI、第二位從 CLI 入場。兩個測試工具均 exit 0，9 項檢查、2 份戰績與世界封存序號 828，程序清理後 C／F 共 14 檔逐一比對 SHA256。另保留 2026-11-02 背景雙玩家 13 項、世界封存序號 387 及 14 檔 C／F 核對。原 GUI 逾時仍保留失敗，當時停在載入前。兩場屬同機 Simulation，LAN、實機及 25 位真人驗收待完成。

CI 41368791791／job 125034572205 測試 `e963e488411927f73bc296e500ea6ae4ee18c7be`。Linux 772 核心、459 HTTP、47 world、6 pipe、38 硬體 CLI、Python、89 Node 與 296 Chromium 通過，另有 3 項 Windows 限定跳過。保存 console 51 檔、control 13 檔、hardware 26 檔及原始 ZIP 和日誌。累計 1870 份瀏覽器 CI 證據，本輪兩張原生流程瀏覽器截圖另計。 [CI 結果](https://github.com/peca12968/vr-command-center/actions/runs/41368791791)

## 2026-11-02：最終GUI fixture來源65b072d完整雲端成功

[CI41367545805](https://github.com/peca12968/vr-command-center/actions/runs/41367545805)／job125030805195，精確 **65b072d31f32afcc5e9da85713caa8b6451a3cd8**完整 **success**：Linux772核心／459 HTTP／47 world、6pipe／38硬體CLI、全部Python含14exercise／4server package及素材、89Node／296Chromium，2Windows限定skip非Editor/native/GUI/頭盔。此提交只補GUI fixture roster；本機實際GUI64853另驗，不由CI替代。

- console51，art13107449934，ZIP **12,027,134 bytes／SHA256 837214959214b8890d3e03481e7011228dba38b9a6bf5eee4e8879e1fb1c384b**。
- control13，art13107449938，ZIP **3,920 bytes／SHA256 bebc5438e939ef101a4c11066102fe740e2287501da1b576729a72f67a75604f**。
- hardware26，art13107514651，ZIP **22,356 bytes／SHA256 6673f4ae64235908856ee698167f4d9443af3fc0d6d23b0b0d2fbd50ae0652c0**。
- decoded log SHA256 **f6297ac22f5daf11cffad1d571d816b4f2ea6b3e184ff3b8613179b7970d4b6c**。GitHub digest/大小/逐檔hash核對；原c55與659成功、三次failed及更早證據保持，1768＋51＝**1819 browser**，nativeUI11另計。held PUT仍fulfilled=true／原1請求／errornull、原鏡頭隔離斷言與15/30秒保持，非舊逾時根因證明。

目前PC里程碑採用0.41.1／code52／NGO29／242真正Editor／4ebd雙平台、900秒18／51601／50原結果6CSV、普通8／354、玩家包19、server v2包106／623及新真GUIexit0；完整11項仍active。新接受metadata只接受上述範圍，server-package-path改為已驗證F解壓v2，舊accepted與所有候選／failed保留。666原生snapshot、328與327歷史、smoke174／long174／ordinary14／package80／failed GUI9／passed GUI14 raw C/F保持，保存SQLite不開／5080不動。後續僅文件skip ci；精確CI65b072d／native4bdf／包說明c55，不以文件HEAD冒充測試來源。

下一步繼續PC跨機部署準備與完整操作者流程；原31／world371／Windows startup根因／F吞吐仍未修復，25真人／Quest／VIVE／MR／廠商硬體仍另驗。以下各段為當時狀態，最新完成以上段為準。

## 2026-11-02：包說明來源c55f21c完整雲端成功

[CI41366924943](https://github.com/peca12968/vr-command-center/actions/runs/41366924943)／job125028931655，精確c55f21ce59bd1601f64f7e4520feec4a75e6bfb1完整success：Linux772／459／47、6pipe／38CLI、全部Python含14exercise與4server package／素材、89Node／296Chromium，2Windows限定skip非Editor/native/GUI/頭盔。console51 art13107323162／ZIP12029146／SHA7cca686b27857c4ac838f3344cdb893f7989e098c67205a489357052595054c6，control13 art13107029055／3918／SHAa3a2a3da9e722296c91578cde8eea22856bc1a27303732fe842a04d367cc6a5a，hardware26 art13107308336／22365／SHAaba8cc04b13179f7f75fe12aa11ec04df3e721daf16e2a9de2c2a54168ebfb01，decoded log SHAcead827ceb618d70158639bfd2a84b248aee6f942e99639afadee6bfa8eaa3bc；GitHub digest/大小/逐檔hash核對。原659成功及各failed CI保持，1717＋51＝1768browser，nativeUI11另列。

c55只包內兩行說明，runtime不變。其後65b072d只補GUI fixture roster，真正新GUI64853已成功，CI41367545805尚待；不拿c55冒充65的精確測試。新GUI失敗9與成功14／包80／smoke174／long174／ordinary14都在各tool terminal及空cleanup後raw C/F同hash；原328與327來源/binary歷史加各manifest保持，首次auditor錯把manifest計入內容數而拒絕，改逐原hash子集＋manifest額外一檔，不改歷史。

原666來源snapshot逐hash保持且與目前選定原生graph一致，沒有把其未收錄的package/gui/browser稱作完整snapshot；新launcher binary實際另驗。保存SQLite不開、完整11active，後續文件skip ci。

## 2026-11-02：新版伺服器包與實際WinForms收尾成功

同源0.41.1的v2 F解壓包真正handle18979 exit0、106項／623完整回放（五房143／123／115／100／86、Linked56）、10原admission結果／CSV／雙seal及server ACK、active0與cleanup空，C80→F raw同hash。parent-death是第七個刻意未封存反例不混作正常場。closure UI兩PNG與原final world同來源，nativeUI9＋2＝11，CI browser另計。

使用者自行關PickerHost後，真正handle64853／GUI run-3d179468... **exit0／passed**：直接輸入既有實例、載入兩房清單、明確選房1、核對完整UUID／任務版本、設定127.0.0.1與64640、按啟動；fixture Begin後原來源Running/tick>0/observed fence，正常API End／雙seal保留36秒後原child25432停止，實際看見「任務已封存並停止」，再按視窗關閉。GUI68392 exit0、原實例marker／三key檔hash不變、closed journal complete/sealed/ACK尾精確、cleanup空後C14→F同hash。只有一位roster、未開玩家client；不是玩家結果送達、25操作、GUI建key或系統檔案picker成功。

首新GUI run-e615...／handle63777 **exit1**：已實際選取/啟動正確來源69716，但fixture空名冊Begin被原API409拒絕，finally收GUI/native/API、cleanup空，C9→F同hash，原failed保留。產品原Begin規則要求非空名冊；只修check-server-gui先加一位明確roster、另存scope證據，不改API/launcher/遊戲。py_compile與新實際GUI驗證成功；功能提交65b072d，對應CI另記。電腦自動化曾遇geometry unavailable／bounds changed，重新選取與fresh state後成功，沒有操作安全／授權提示。舊PickerHost與原31／371／Windows startup／F吞吐仍保持原判，完整11active。

## 2026-11-02：位置回饋900秒兩模式長場完成

原handle33928真正terminal **exit0**，073638-487017bd的18項／**51601全回放／51351 Running**成功；Linked8610／8576，五獨立房8582／8518、8590／8552、8580／8540、8600／8561、8639／8604。50位原admission各90發／45reload／45週期、50原結果／6CSV／combat與world雙seal及原server ACK／無timeout或queue error，活動跨度17943..18003tick、最長收集902.3086214秒。Room1僅原授權Pause窗口例外、其他房前進，原走道與0.5／1.5政策不動。active0／全部cleanup空後C174→F raw逐檔同hash，desktop-endurance-feedback-long-validation.json只接受本場，不接受完整11項。

另073233兩模式60秒18／3760、普通無生成旗標081609入場／撤銷／重連8／354、玩家包19成功。Unity0.41.1／code52／NGO29、242真正Editor與同源4ebd雙平台／原ID保持，沒有為包說明更新重建Unity。原0.41漂移場exit1、原31／world371／startup／F吞吐仍各自未解；同機AutomatedSimulation非25真人／LAN／頭盔／MR／廠商硬體驗收。

使用者已關PickerHost，伺服器GUI接續另驗。新版server v1先在Path.resolve的AppData LocalCache視圖缺DLL，literal原路徑仍在，未啟動fixture；後F長stage超Windows路徑長度，copy失敗於ZIP建立前，原部分stage保留。新F短stage成功生成v2，runtime全部byte同v1、launcher來源fb57807d不變但重新編譯binary不同，不能稱整包二進位相同。初期強相等斷言拒絕也保留，後按實際三差異（launcher／README／manifest）核對。v2 ZIP82673732／SHAca285a42e0c22bdde17f62eb6dd8a65523c9d3a5cae19a33cad41636899fb368，311manifest／ZIP312、實際F短路徑解壓後逐檔驗證；真正包整合與GUI結果另記。包說明移除過期Unity0.39字樣，引用Runtime/build-receipt.json；4 Python package成功，c55f21c CI41366924943尚在執行。此前段落的「live／尚待」是當時狀態，以本節及後續結果為準；所有舊證據保留，保存SQLite不開，5080不動，完整11active。

## 2026-11-02：位置回饋候選的完整CI與held回覆收尾驗證

[CI41364751791](https://github.com/peca12968/vr-command-center/actions/runs/41364751791)／job125022432098，精確來源 **659f026eb13021ed4eb6fd2defde066f5b8bd620**完整 **success**：Linux772核心／459 HTTP／47 world、6pipe／38離線硬體CLI、全部Python含14 exercise／素材、89 Node／296 Chromium，2 Windows限定skip非Editor／原生／GUI／頭盔。

- console51，art13106359427，ZIP **12,016,184 bytes／SHA256 42bbc0d847f8ed767d27dcf6d756992c02b5b5f557c24a7a7a725df39801405c**。
- control13，art13106254966，ZIP **3,918 bytes／SHA256 2bef12d403cda00da3ff32bf3d249390fac08873493275151c1cb81a889833fe**。
- hardware26，art13106513838，ZIP **22,330 bytes／SHA256 06621fbb62648dde3b50b6cded39e7685591646532e6e2e7bb0cfaf393367c22**。
- decoded log SHA256 **4f9fdf901a7251ec29221944d330e057442cdc3f2e9b14f6af56c29ae5d7209f**。GitHub digest／大小與逐檔hash核對，原18a成功89檔及三次failed56／58／57檔與各ZIP保持。

新delivery metadata為fulfilled=true／requests1／errorName=null，且重新登入後camera-save enabled、原延遲回覆隔離斷言通過，不是吞掉取消回覆來變綠。這只證本場；首7ed stalled-read15秒、4bdf relogin-save30秒與1d route already-handled仍failed，原件保留，不能由本場推定原逾時唯一根因。產品JS／API／期限及原15／30秒與隔離斷言保持，659只fixture回呼收尾／文件，未新建置Unity。

1629＋4bdf failed19＋1d failed18＋新51＝**1717 browser檔**；control／hardware與nativeUI7＋2另列，沒有新本機全browser／GUI。242真正Editor／4ebd雙平台與原生helper是4bdf功能來源，CI659不替代它們。原33928／073638長場仍live：Linked8610／8576Running已過，Independent正在900秒；不停止／重啟或提前snapshot。使用者已自行關PickerHost，待長場與cleanup後重驗GUI。後續文件skip ci，CI精確659／native4bdf，完整11active。

## 2026-11-02：重新登入fixture的held PUT回呼失敗保留

來源1d023ff的[CI41364052976](https://github.com/peca12968/vr-command-center/actions/runs/41364052976)／job125020346533 **failure**，772／459／47、6pipe／38CLI、全部Python含14exercise／素材及89Node成功，2Windows限定skip；stalled-read與登出清理斷言已過，隨後world-browser161的held PUT route.fulfill出現「Route is already handled」未處理拒絕，Node終止，非30秒DOM逾時／完整296。

console18（art13106372583／ZIP3935698／SHAe5925243ef5fd2fffa019ad3386d21140043b0b3026a22593791182cdc60ee7c）、control13（13106736338／3918／ba70a60ce4f3b9cb4163ce83095ffeb01bd104ca64f4a78d057199e125cfc3dc）、hardware26（13106606868／22368／2b248dbb21eb75af9defe476931c2db494dafdf54c6edfdd65084e5fb94b2425）及decoded log SHA99fc847414397ad17e5a981aebedd27be0ab09d825fdc6b00a86d6dca789ab7c另存核對。原1648＋18＝1666browser，原58／56失敗CI與89成功CI不覆蓋，nativeUI7＋2保持。

調整僅測試：held回覆必須先完成，再解除route，回呼例外先收集、由主流程明確失敗，不能忽略已取消回覆來讓隔離斷言變綠。新delivery metadata必須fulfilled=true且只有一個原PUT，才會走原「晚到保存不能污染另一actor」斷言；若重新登入本身已失敗則保留原錯誤，不用回呼覆蓋原因。原30秒／100ms輪詢、產品JS／API／期限及所有隔離斷言不變，node syntax過，新CI另驗，不證先前兩次逾時根因。

使用者已自行關閉先前阻擋GUI的PickerHost視窗；目前不打斷原33928／4ebd長場，待它與清理／包檢查完成再重驗WinForms流程。新的Linked完整8610回放／8576Running已通過，Independent正在原場次900秒，writer停前不snapshot，完整11active。

## 2026-11-02：位置回饋來源CI在另一個鏡頭等待點失敗

來源4bdf294的[CI41363335600](https://github.com/peca12968/vr-command-center/actions/runs/41363335600)／job125018189228 **failure**。772核心／459 HTTP／47 world、6pipe／38硬體CLI、Python14 exercise／素材及89 Node成功，2 Windows限定skip；先前stalled-read已通過，這次world-browser196在Room2重新登入並開始原世界後，等待camera-save enabled的原30000ms逾時，未到完整296，不是auth-role等待。初分析標籤誤寫auth-role，原metadata副本保留後更正，不改原log／ZIP。

console19（art13105934910／ZIP4250536／SHA41b6d49b818180e7b2057bc70cb1c5b9957d6cf1128eb4ee2b8b3532dd803465）、control13（13106735184／3919／141b3522228f04f38f3d01e9019a89e34a891a1b7d5131844170fa91e2162058）、hardware26（13106540919／22348／aa5b0d80b987bda4c3571b3f20afda59b396c2255a6ea71c809c7e731ae96b79）與decoded log SHA730a67a0511f3987466070371b09ca1cc8ce0d823223f54f6ee92da8c38255a9保存核對。原1629＋19＝1648browser、nativeUI7＋2保持；所有先前失敗與成功原件不覆蓋。

該場原save診斷只到初始PUT的after-click，沒有重新登入後失敗時的DOM，不能證RAF／產品根因。只把此一按鈕謂詞改polling100、原30000ms與延遲舊保存回應不能污染Room2的斷言不變；明確bringToFront／選原live.header.sessionId，最多8筆控制狀態（原訊息各500字）／截斷旗標，失敗5秒圖遮login-key再原錯重拋，held PUT於finally釋放／解除route。沒有改產品JS／API／路由／期限或新增本機Chromium負載；node syntax成功，新CI結果另記。原33928／4ebd長場仍live，不重啟或提前snapshot，完整11active。

## 2026-11-02：原長場走道失敗保留，位置回饋候選再驗

原0.41／5d2e的064034-7c1ae2b7、真正handle51871終結exit1，cleanup空、C174／F raw同hash，整場failed。Linked5項／8621回放／8587 Running、25原結果／ACK／無timeout及45循環通過；Independent在Room5 world3400／tick7120／elapsed359770ms觸發生成器走道（首Z=-3.4091835），該房仍五位connected／health100／Simulated、在正常房內。完整失敗取證36896：Linked8621、五房3433／4309／5391／6721／8421；Room5三幀3400..3402共8筆走道不符，恢復後仍failed，8381保存Running無失聯。Independent僅36發18reload／活動跨度7074..7127，後段靜止取證及四房continuity綠不當900秒接受。輔助分析首Room-only混跨場ID/minempty原件保留，後依原player IDs重對齊；沒有補造CSV／成功。

原0.41 binary/log321＋7來源＝328先C/F archive，更早327保持。[新0.41.1](DESKTOP_ENDURANCE.md)／code52／NGO29、242真正Editor0skip（新4）及同源4ebdcd12...雙平台原ID一致。長場只讀本機Z作起點..+.8m換向，回±.2、原Move／Constrain／RPC，不clamp／teleport／寫server pose；原短40tick與走道、0.5／1.5、武器彈藥／durability不動。Editor凍結舊換向公式配同一不均步長可漂移、新回饋有界，不補本場deltaTime trace或舊31／371根因。14 exercise／27 active／5 artifact與錯模式CLI通過，失敗另存partial-checks但complete=false。

073233-32121819兩模式60秒18項／3760回放／50原結果6CSV／雙seal ACK成功、每人6發3reload／3週期。長場可選最多5個唯讀回放，各原rate4／期限／每幀與cycle／seal閘門，native先停；此路徑已預跑。玩家包19通過，新ZIP82651927／SHAdcc46...、server82673718／SHAb45d...、APK60361942／SHA766d...完整hash及ARM64/min32/target35/v2debug見文件。Server新包完整原生／普通入場尚待，無新WinForms GUI／頭盔。

新900秒both／25Linked後五房各5端，真正handle33928／073638-487017bd正執行，不能提前接受；兩端建置全停、666新source snapshot在它之前完成，writer停前不runtime snapshot。原0.41 ZIP／APK保留，current APK為0.41.1，不當舊檔同hash；舊18a CI不冒充新候選，新CI另驗。保存SQLite不開／5080不動，完整11active及原31／world371／startup／F吞吐／PickerHost／跨機真人／頭盔MR／硬體仍待。

## 2026-11-02：長場來源與鏡頭等待fixture的完整雲端結果

[CI41359154963](https://github.com/peca12968/vr-command-center/actions/runs/41359154963)／job125005569006、精確來源 **18a72f0cd97fd7c0fdeeeec98ddc3b90d980f754**完整 **success**：Linux772核心／459 HTTP／47 world、6 pipe／38硬體離線CLI、Python含14 exercise（新3長場）／素材、89 Node／296 Chromium，2 Windows限定skip非Editor／原生／GUI／頭盔證據。

- console50，art13104173114，ZIP **12,047,825 bytes／SHA256 dc449ceabe05f40c9317d61e3a420d230207d90d6a5d37a8d8b64c4bfc4f78a3**。
- control13，art13104212927，ZIP **3,918 bytes／SHA256 67e83aca5aee339ab604ef76d3c947d1143cdbd66c3a000370386f99ac292af4**。
- hardware26，art13103849142，ZIP **22,388 bytes／SHA256 8819ff5b35e7726aee53fa3f2e05db7e567d4fc60946b3654c8a54f3b9896592**。
- decoded log SHA256 **e9a216c8fa4914a6d890c85adaf153ee8e7c2b1f0444d9565d2dade3863776ad**，三ZIP的GitHub digest／大小及逐檔hash核對成功；前88成功CI與首失敗56檔／三ZIP保持。

新stalled-read metadata三列：本場visible／focused，before enabled、response-held disabled、約10242.77ms enabled＋error-class、仍1個option。這只描述本場，不能補作首7ed失敗的狀態，也不證RAF根因或產品無缺陷。原15000ms／集合與錯誤斷言及產品程式／期限保持；fixture只DOM polling100、有界診斷與finally釋放held GET。**首CI41358528198仍failure**，17部分browser／日誌保持。

1562＋首failed17＋本次50＝**1629 browser檔**；control／hardware、既有nativeUI7＋2另列，無新本機全browser／GUI。238真正Editor與同源5d2e雙平台是7ed功能來源的先前實際建置，18a只改browser fixture／文件，未重建遊戲。原生900秒handle51871仍執行：Linked輸入窗口已結束，25原結果與25server ACK／無timeout已保存，完整回放與Independent尚待。沒有因CI終結而停止或重啟此原生場；writer停前不snapshot，保存SQLite不開。後續文件skip ci，CI精確來源18a72f0／原生helper7ed，完整11active。

## 2026-11-02：首長場來源CI的鏡頭讀取等待失敗

來源7edb160的[CI41358528198](https://github.com/peca12968/vr-command-center/actions/runs/41358528198)／job125003707285 **failure**：Linux772核心／459 HTTP／47 world、6 pipe／38硬體離線CLI、Python含14 exercise／素材與89 Node已成功，2 Windows限定skip；瀏覽器在world-browser.cjs:131等待刻意stalled camera read的refresh按鈕恢復，原15000ms逾時，未完成296項，不當完整成功。

原console17（art13104158516／ZIP4239456／SHA8e52a5d860f58c3951ba9ec34d8adca4c5177d1442308951d97db1970a521a35）、control13（13104795827／3918／9d47fcb6ac0d997ea42dbf3201621d01b11a3af0b531f5649397302ab7845fe9）、hardware26（13104566898／22343／db32b3f06bf7511389f7aa9477185d5b04dd1581087bc39a457781c501562197）與decoded log SHA6ef00e0f85da8b2982d9efe42b102de9622ebdad9830a3fe7e454a06461c9055已另存、ZIP digest／大小／逐檔hash核對，前88CI檔保持。1562＋17＝1579 browser檔；本機原生仍是原handle51871／同源5d2e，沒有因CI觀察失敗重啟或提前snapshot。

原失敗沒有該等待點的控制狀態，不能證RAF／timer／產品根因。只把同一DOM按鈕謂詞改為polling100，保留15000ms與原集合／錯誤斷言；新增最多4列visibility／focus／disabled／error-class／option-count及caller單調時間，不含input／headers／body／key。失敗最多5秒圖後原錯重拋，held GET於finally釋放；不改產品JS／API、路由、API期限或錄影政策。node syntax通過，雲端結果另記；不在25端長場旁另跑本機Chromium／新建置。原完整11active與舊31／371等反例保持。

## 2026-11-02：長場生成輸入已建置，900秒兩模式驗證進行中

新增[獨立長場旗標](DESKTOP_ENDURANCE.md)，Unity0.41.0／code51／NGO29、238真正Editor／0skip與同源5d2ebd2a...Windows／ARM64、原Scene／prefab ID保持。每20秒fire／reload／fire，45循環最多90發／45換彈，仍走原Move／RPC／彈藥；漏循環失敗不追補。長場19000活動tick／1200收集秒與原短1200／240分開，原0.5／1.5政策保持。14 exercise（新3）／27 active／5 artifact Python及3錯CLI模式拒絕成功；沒有後端產品／UI／rules／wire改動。

五端60秒原生063727-2069ec28，5項／597全回放／577 Running、每人6發／3換彈、3個20秒循環成功；來源活動tick跨度1202..1203。短場＋原管理命令063930-4ee0c139另7項成功；19玩家啟動器離線檢查成功。900秒Linked25後五房各5端，真正handle51871／064034-7c1ae2b7正在執行；此時尚未通過，不提前建立runtime snapshot或接受檔，最終結果另記。

原0.40 binary/log321＋6來源＝327先C/F archive核對；666新來源snapshot只含source，沒有複製正在寫入的DB。新玩家ZIP82651687／SHAf2c84949...、serverZIP82673487／SHAaf8a08b3...／APK60356910／SHA1187dfd2...，完整hash／簽章見文件。首server封裝缺stage-root在建立前拒絕，原觀察exec exit1／native exit未量測保留，補新目錄後成功，不覆蓋原檔。兩端建置全停後才原生測試；API0.31/UI0.31.2保持，保存SQLite不開、5080不動。完整11active，舊31／world371／startup／F吞吐／PickerHost及跨機真人／頭盔MR／硬體未改判。

## 2026-11-02：多人命令組合來源的完整雲端驗證

功能來源 **a58a52786ea4244940b3b2eb2c3dfd8e1ca6a4a1** 的[CI41356457654](https://github.com/peca12968/vr-command-center/actions/runs/41356457654)／job124997439220完整 **success**：Linux建置、772核心／459 HTTP／47 world、6 pipe／38實際API＋.NET硬體離線CLI、全部Python（含11 exercise／4新負向）／素材、89 Node／296 Chromium成功。2 Windows限定skip不當Editor／Windows原生／GUI／頭盔或實體硬體證據；本輪沒有重跑Unity或Quest建置，原231／6098雙平台保持。

- console49，artifact13103641973，ZIP **12,005,675 bytes／SHA256 b17a2b53c8671440a6e629a6d68cab19cc5c99149484a643053d60452e6a4f22**。
- control13，artifact13103766431，ZIP **3,919 bytes／SHA256 d1b8d7be81a4a4921b14a64a91721fbaab0a6932b77ea49a76d5b8e4fcc7597e**。
- hardware26，artifact13103193804，ZIP **22,361 bytes／SHA256 4d31e153f5513cc3b0ca127471bd0a1e75d83582ae4050ccb1de2777b82d522b**。
- decoded job log另存，SHA256 **e7506250d841ad5aabade21798b5d85f2e5cd6cc1f471b1a4de1aef6aaf67cd4**。三ZIP的GitHub digest／大小與逐檔hash核對，前輪88CI檔／三ZIP同hash。

1513＋49＝**1562 browser檔**，control13／hardware26及既有nativeUI7＋2另列，沒有新本機全browser／GUI。新C232／F與666來源snapshot、前C340／326history／666舊來源及原玩家／server ZIP／APK保持，保存SQLite不開、5080不動。後續僅文件使用skip ci，精確測試來源a58a527；30項／2909原生與附加2627 Running閉源讀回不由Linux CI取代。

原Linked／Independent生成器報告最大活動tick跨度分別361／550（18.05／27.5秒），全部明確Requested收尾；finish後停止生成輸入，但原姿態／結果流程持續。後面五房依序收尾增加了靜止回放，2909全回放或2627 Running幀不能當成全程動態輸入。 完整11項仍active，原31／world371／startup／F吞吐／PickerHost GUI、長任務多人與跨機／25真人／頭盔MR／廠商硬體仍待。

## 2026-11-02：25端持續移動與操作員命令組合

[短動態驗證](DESKTOP_EXERCISE.md)新增明確選用 `--operator-controls`。原16秒基本輸入窗口後，玩家繼續走既有生成器／原Move與RPC，先等待每人兩發已被統計接受，再對每個原場次送正常SetEnvironment／SetEnemies：雨夜／雷電／Patrol，接著Fog Day／Advance，autoAttack=false、敵軍數固定每房1位。每次使用自己的新UUID及當下expectedSequence；接受回條先保存，同session／非duplicate／原commandId及遞增序號核對，來源observed到達該序號、Running／非suspended、tick至少再20且全員walking，原存活敵軍ID／room／health保持、每位移動>1cm才成功。接受不當套用，不改原60活動秒／240秒收集上限或0.5／1.5政策；這是ManagementApi組合測試，沒有操作員UI／真人鍵盤／GPU或頭盔觀察。

先五端預跑 `061205-121a2aa8` **7項／202全回放**成功；最終 `061302-f5072feb` **30項／6場／2909完整回放**成功，Linked25後五房各5端。12階段／24個唯一正常命令、24個原before／applied checkpoint的packet及statistics精確重現於回放；50份原admission結果／6份CSV、雙seal／server原connection ACK一致、無timeout或send queue error。Linked Patrol／Storm的11幀及Advance／Fog的12幀為全部25位walking；五獨立房各自也有5位walking來源幀，不硬配跨房時鐘。

原程序terminal且cleanup空後，僅讀closed JSON的 `operator-timeline-readback.json` 對 **2627 Running幀**依該房實際接受的環境／AI序號逐項推導狀態，含兩個命令間可能不同步的序號窗口；weather／lightning／night／visibility／behavior／autoAttack、原敵軍ID／room／health無不符。這是post-terminal附加讀回，不是第31項新live檢查或網路容量／根因證明。所有普通完整回放及Room1明確Pause／Resume、其他四房tick前進門檻保持，未授權Paused不例外。

未選用新開關的 `061538-2e6870ad` **5項／179回放**成功，保留原無敵軍／兩發0中0殺／health100斷言；新模式同樣保持此精確統計。新4項負向證據測試覆蓋錯UUID／session／duplicate／倒序／bool序號、遺失命令及相同sequence卻不同packet／statistics；共 **11 exercise＋27 active＋5 artifact Python**成功。

本輪無新Editor／Unity或Quest建置，沿用Unity0.40／code50／NGO29、原231真正Editor、6098b485...同源Windows／ARM64及原Scene／prefab ID。玩家ZIP24aef...／serverZIP642e...／APKadb9...核對保持；新三組 **C232／F runtime-snapshot**同hash、666份新來源snapshot，前輪C340／326history／666舊來源snapshot也核對保持，保存SQLite不開、5080不動。原1513 browser與nativeUI7＋2保持，本輪未新跑本機全browser或GUI。完整11項仍active；舊31筆／world371／Windows startup／F吞吐／PickerHost、長任務多人操作、LAN／跨機25真人、Quest／VIVE／MR與廠商硬體仍待。

## 2026-11-02：多客戶端動態來源的完整雲端驗證

功能來源 **a4ff77c95553d04cfa90bfb33bd6cce55dcc0679** 的 [CI41354866315](https://github.com/peca12968/vr-command-center/actions/runs/41354866315)／job124992675470完整 **success**。Linux建置、772核心／459 HTTP／47 world、6 private pipe／38實際API＋.NET硬體離線CLI、全部Python（含新7項exercise）／素材、89 Node／296 Chromium成功。2個Windows限定skip不當Unity、Editor、Windows原生／啟動器GUI、頭盔或實體硬體證據。

- console49檔，artifact13102913618，ZIP **12,020,478 bytes／SHA256 4c090653090f17dca468b835df73398afafae73334822d7ffdbec307ca66b436**。
- control13檔，artifact13102684674，ZIP **3,918 bytes／SHA256 019f7e70600567a6f3fbab7994324b73479a950fbadea822d45ad02398a93515**。
- hardware26檔，artifact13103435263，ZIP **22,396 bytes／SHA256 fcb79042cf36c25d03b98dfd13307135383f9fdf66a0b79df2b6c0ce7e912134**。
- decoded job log另存，SHA256 **22deb5e4e9dc2066d79ed3d414862aa2882582da9823f0e582f7ff9f7e2183c8**；ZIP均與GitHub digest／大小相符，逐檔hash及前輪88檔／3ZIP核對成功。

原1464＋本次49＝**1513 browser檔**；control13／hardware26、既有nativeUI7與本輪serverUI2分開計數。這不是新增本機完整瀏覽器或新一輪原生遊戲。Unity0.40.0／code50／231真正Editor、6098b485...同源雙平台、18項／1951回放及兩個失敗fixture、default8／355、server包106／725／10原結果、玩家包19均保持原證據；原生數字不由Linux CI取代。

新C340／F與326份舊binary／source archive、666來源snapshot、舊75硬體及117／274／163／327 raw、9管理／5舊server／歷史玩家ZIP保持，保存SQLite不開。current0.40 APK與歷史0.39 APK分開保存。後續僅文件提交使用skip ci，測試精確來源a4ff77c；完整11項長期目標仍active，舊31筆／world371／startup／F吞吐／PickerHost GUI，以及跨機／25位真人、頭盔／MR／廠商硬體均未改判。

## 2026-11-02：原生多客戶端產生移動／射擊／換彈

新增[Windows batch Client短動態輸入](DESKTOP_EXERCISE.md)，Unity **0.40.0／code50／NGO29**，API0.31.0／UI0.31.2保持。明確新旗標／新目錄才啟用，只接受Windows Development batch Client且無XR，原桌面Move／Constrain與SubmitPose／SubmitWeapon RPC、簡報／Ready／Running及原伺服器門檻保持，沒有test RPC或直接寫server pose。40tick反向／0.4m/s約0.8m幅度、相對20／60／120tick的fire／reload／fire；只計真正呼叫原武器RPC的嘗試，接受另核對。60秒活動tick／240秒總窗口、finish／退出與owner／clock錯誤有界，不把report.complete當任務成功；普通啟動無元件，Tracked不搬動。

真正Editor **231／0skip**（原224＋7）成功，Windows／ARM64 Quest同源 **6098b4857b36d4b24a6b4ab275cbd64b17aa12353329cad9c96f36a9d339911b**、原Scene／prefab ID保持。PowerShell腳本因ExecutionPolicy未執行，原錯誤log保存，改直接呼叫同一Unity批次入口，沒有調整策略／安全性。兩平台建置全結束才跑網路測試，沒有建置負載重疊。

首`desktop-exercise/20261102-053940-74608ff9` memory helper名稱錯誤，在啟動玩家前failed；次`054005-b0589055`五端已移動，測試錯讀不存在的packet.observed而KeyError failed。兩場原C14／29、原log／原資料／cleanup空保持，不補成功旗標。修測試使用memory_status及實際observedSequence，另以原API名冊核對admission／room／seat，無產品pose規則修正。新7項Python證據驗證及5既有artifact檢查成功。

`054142-2d7a0827` **5項／139全回放**的五端smoke通過；`054350-5fe3e1a0` **18項／1951全回放**通過，Linked25原生client後五個Independent server各5client，16秒產生輸入，每位接受移動／reload、2發／0中／0殺／health100。50份原admission結果／6逐場CSV、雙seal與原server ACK／無timeout相符，無send queue full。Room1 Pause接受後等來源真正Paused、tick固定，其他四房tick前進，Resume fence保存；意外Paused不放過。完整回放所有Running body均核對connected／Simulated／健康／房間／位置、1500ms gap不放寬。Linked159 Running保存幀中154幀25位walking=true；各房5位移動的post-terminal讀回另存，不是第19個live檢查，沒有把不同來源時鐘硬配。

普通無旗標`unity-admission/20261102-054643-86ca91ed` **8項／355幀**撤銷／重連／精確seal成功。玩家包19 CLI檢查成功；server包`run-72e81d5697d64b43ace5cb2fb1d59ecb` **106項／725全回放（172/148/132/115/100/58）／10份原結果各CSV**、真browser正常UI End與精確來源／ACK、cleanup成功。parent-death仍是獨立未seal反例；此browser不是Windows launcher GUI，新GUI未驗，原PickerHost保持待解。

新玩家ZIP **82,651,129／SHA24aef191b5fc608430a5f131ffd34aabf2ec0b4938fefd3f2c8461c958cc50e2**，serverZIP **82,672,917／SHA642e5307cf3d62af7b136d9baaca06c2d9cd9c3bd1ed66c7d4e915803a7f8710**，各311 manifest／ZIP312，launcher來源a658／fb578不變且server實際compiler input保持。APK **60,358,086／SHAadb9a8bc6c94b0e9842c1498f5a74417071daf388f79622f742f060e3c098fa5**，aapt確認ARM64／min32／target35／0.40.0／50、v2 debug，非實機／效能／商店release。舊0.39的321 binary/log＋5source＝326先C封存再F同hash，舊APK0310...保留history，current路徑是新APK。

`desktop-exercise-delivery-validation.json`核對新C14＋29＋29＋174＋14＋80＝**340檔**／各F snapshot、666份凍結來源、兩平台receipt／包及原ID、舊C75與四報告117／274／163／327、舊9管理／5server ZIP及玩家ZIP保持，保存SQLite只rb/hash不開。前1464 browser／nativeUI7保持，新server browser2另列，舊77場3399 runtime未全重跑。新場是產生的Simulation輸入、0位實體操作者／1host／0rendered，不是25真人、LAN或完整容量；舊31／world371／Windows startup／F吞吐與完整GUI、頭盔MR／廠商硬體仍未修因／驗收。完整11active，正式5080不動。

## 2026-11-02：硬體離線模擬器CI與證據

[功能574df36](https://github.com/peca12968/vr-command-center/commit/574df36d3cd4246dec0ad67885e8a544fa4f47c1)的[CI41349387031](https://github.com/peca12968/vr-command-center/actions/runs/41349387031)／job124976066366完整 **success**：Linux772核心／459 HTTP／47 world、6 pipe、38實際API／.NET離線模擬CLI、全部Python／素材及89 Node／296 Chromium通過。2 Windows限定skip不是WinForms、Unity／Editor、native遊戲、實體硬體或頭盔驗收。console49 artifact13100741395／ZIP **12,022,752 bytes／SHA256 e24b2ce787ccae8aabb70c3bc32268a064ce9a89cc9c51313c37da983dd51d47**，control13 artifact13100701380／ZIP **3,919／SHA256 a2569dfd539a5c1fef56e3b703f7e83e1bc1dc9aa1eca2046fcff0311239077a**，hardware26 artifact13099889416／ZIP **22,380／SHA256 e8ce6368326ccb6080a5a9e4f7280e7a44bbeacad894929a079d8ad24f508172**，已下載核對GitHub digest／逐檔hash；hardware檢查與原API cleanup讀回成功，artifact不含DB、journal或角色金鑰。完整decoded log SHA256 **53685b090bb76aeb81af85d2c7270473cb3867b64fd50692c046af9eefc0f5fa**保存。`hardware-ci-validation.json`明列1415＋49＝**1464 browser證據**，control13／hardware26各自另列，nativeUI7保持；不是新本機全browser或Unity執行。本機C75／F與原C27／四舊報告、9管理／5server ZIP及原Unity0.39／e0d／224雙平台、玩家ZIP APK保持。後續只有文件提交skip ci，測試來源精確574df36，完整11active。

## 2026-11-02：硬體回饋離線模擬器

新增[HardwareFeedbackSimulation／開發測試台](HARDWARE_SIMULATOR.md) **0.1.0**，不是廠商wire或實機介面。新tool以整段schema6／7重建已Ended且戰鬥精確seal的單場，沿用原SessionManager／CombatLedger／admission與權限；只把ShotFired／PlayerDamaged投影成模擬訊號。原event／stream／report／ObservedSequence及room／admission不丟，晚到的報告不讀最終名冊。設備ID是本地模擬UUID，不是USB序號；無任何設備I/O、輸入事件注入、震動強度或實體停止保證，檔案符合重建規則不等於API來源簽章。

34新核心／**772完整核心**成功；128綁定、4096事件／步、虛擬0..600000ms、每設備32含in-flight、2秒虛擬期限，並不改遊戲0.5／1.5秒政策。重送／倒序拒絕、換綁與重連取消但不自動重播、錯設備／connection／delivery ACK不解除原flight；恰好期限先逾時。所有腳本最後取消殘留項，complete只表示腳本走完，SimulatedHardwareOnly=true／PhysicalDeliveryConfirmed=false。輸入8MiB、輸出64MiB、已有檔不覆蓋，受控錯誤exit1只型別。

五場真正隔離API＋.NET ArenaSession／TelemetryOutbox／原relay補送，初24／33／34／36與最終**38 CLI**各自成功；全部是Simulation，非Unity/native遊戲／設備。最終`hardware-simulator/run-883edf2541fc4063ab6c90e4e5454857`原12 events、2發2中1殺／受傷20／health80，3個訊號逐欄核對原event、report、stream、ObservedSequence、admission、room、kind與damage。原API事件／統計前後同、active0；每場原API私有pipe正常exit0／cleanup空才一次C→F snapshot。CLI真正使用的API／relay／simulator完整binary graph前後同hash。post-terminal逐欄讀回不是新的第39 live項。

最初錯權限輸入`hardware-rejection-before`已不寫報告，但CLI未捕捉原AccessDeniedException，Windows exit **3762504530**；輸入／stdout／無輸出反例保留。修正只將AccessDenied與KeyNotFound列為CLI受控拒絕，不改權限或歷史規則；同一位元原輸入在真正v2解壓包exit1／只型別／仍無輸出。原有效案例和初包保持，不能說先前已有受控拒絕。

初包`hardware-simulator-0.1.0-net10.zip` **122,332／SHAff7b1c6868ed84b8d4f7f9029207b2538047741277e68748c087c4c5ccf0511a**保持；主包 **hardware-simulator-0.1.0-v2-net10.zip** **122,352 bytes／SHA256 72e73214c03948ac312cac52c246338ae061e498fb7f8aa9f5d4e0bd62d7412b**，7 manifest／ZIP8。只有5個自己DLL／deps／runtimeconfig、合成example及README，需要.NET10 runtime，不含apphost／runtime／SDK／金鑰／DB。v2真正解壓執行sample，結果與原run逐位元一致，包保持同hash；manifest不是簽章，不假造實體ACK或stop。

`hardware-delivery-validation.json`核對新五場 **C75／F**、原C27及四舊報告117／274／163／327、9管理／5server ZIP、原玩家ZIP／APK／e0d60e4e...／224 Editor雙平台與原識別保持。最終build `hardware-c128f55c4c9442f5bebed300c9ba87c1`，197凍結輸入及同次輸出圖保存；Windows459 HTTP／47 world成功不改舊startup根因。API routes／UI／Unity來源未改，僅新Core離線類別／CLI／檢查；本機未新跑全browser或native遊戲，前1415 browser／nativeUI7保持。保存SQLite僅rb/hash不開，正式5080不動。完整11active，廠商協議／實機輸入輸出、MR、跨機25操作、原31／world371／startup／F吞吐與PickerHost GUI仍各自待驗。

## 2026-11-02：物件復原交付的CI與證據

[功能fddc59c](https://github.com/peca12968/vr-command-center/commit/fddc59c4f2e2571265fb19a0c81e3622c1b93eb9)的[CI41346124781](https://github.com/peca12968/vr-command-center/actions/runs/41346124781)／job124966206406完整 **success**：Linux738規則／459 HTTP／47 world、6 pipe、全部Python／素材及89 Node／296 Chromium通過。2 Windows限定skip不是Framework、WinForms、Unity、native遊戲或頭盔驗收。console49檔 artifact13099980133／ZIP **12,015,192 bytes／SHA256 d6012c7a79fccd1e2ed44ed13640f669f7708134ae6ca533eaae1328167dc13a**，control13檔 artifact13099004432／ZIP **3,920 bytes／SHA256 b1cde4b7e8ccd8ac06b2ed58c73213e5e300e5f91ca54764907c79d0dfd2db58**，已下載核對GitHub digest、逐檔hash及完整decoded log（SHA256 ffba6bdd60c1066877c19fbb92bd75f041dda4bebc2f22e55ea59f315b4aee8e）。`placement-ci-validation.json`明列1366＋49＝**1415 browser證據**，另13 metadata，nativeUI7保持；前CI60檔及ZIP另核對保持。C27／F及四舊runtime報告、9管理／5server ZIP、原Unity0.39／e0d／224／玩家ZIP APK不變。後續只有文件提交skip ci，測試來源精確fddc59c；完整11active。

## 2026-11-02：場景物件復原與重做

新增[物件編輯紀錄](PLACEMENT_HISTORY.md)，控制台 **0.31.2**／API **0.31.0**。本地物件新增、刪除、數值／素材與旋轉可完整復原／重做，保留順序及selection；一次拖曳／按住方向鍵為一步，放開／取消／失焦／切頁收束。只在配置圖攔截Ctrl／Meta快捷鍵，文字欄不攔截；載入任務／新增草稿／登出清紀錄，Master／busy／pending fence保持。儲存前收手勢，成功後同草稿還能undo，但只標記dirty，不回滾原不可變版本或管理寫入。50步／雙向UTF8序列化2MiB，完整步淘汰、返回值分離，版本／命令／憑證不進歷史。

新6 Node模型含500物件／參考隔離／分支與預算，完整 **89 Node／296 Chromium**成功。專項 **29項**實際拖曳／重複keydown／原物件鍵盤focus／快捷鍵／數值／刪除順序／儲存鎖定／新版保存／原版不可變／新草稿及登出房控；實際解壓包另29項成功。第一專項51184 exit1在保存後仍選已被head取代的原ID，30秒selectOption timeout、4原圖保持；後測真history.headId，不改期限。初隔離build漏複製Checks明確連結的AiTargetingCases.cs，CS2001／初snapshot保留，完成採新完整目錄，不當產品根因。

最終本機build `placement-90b30ba99f884d1cb18d967c6f535ee1`，API130／三tools各9／Checks90檔同次組，Windows **738規則／459 HTTP／47 world**通過；本機HTTP成功不解舊startup。管理服務整組自含publish484檔（.NET/ASP.NET10.0.14），Windows啟動器C#來源266d93c7...不變；新包 **control-server-api0.31.0-ui0.31.2-placement-win-x64.zip**，**52,472,096 bytes／SHA256 1eac2676113b47c58b5649ce444201e612603167a16d1e5bccb0599fc1dcf9a2**、504 manifest／ZIP505含manifest。94860 exit0／`control-package-checks/run-bf4e40038aea4fefb585694a915ae5d6` **105項**管理角色／五房25席／原實例重開／私有管線child停止及cleanup成功，25席不是遊戲端；7 control／4 server Python邊界與腳本語法成功。無新的WinForms GUI啟停操作；原server GUI仍failed。

`placement-delivery-validation.json`核對本輪管理runtime **C27／F snapshot**全raw hash，原四報告各C117／274／163／327及各F保持，原8管理ZIP＋新第9份、5serverZIP、玩家ZIP／APK、原e0d60e4e...／224 Editor雙平台及識別保持。新瀏覽器4failed＋3專項＋49完整＋3包專項＝**59檔**，原1307＋59＝**1366**；native UI7另列，原77場3399 runtime未全重跑。保存SQLite只rb/hash不開，自己writer已terminal且cleanup空才一次snapshot。沒有新native遊戲、Editor／Unity／APK或頭盔；完整11active，舊31／world371／Windows startup／F吞吐、完整server GUI／LAN／跨機／25操作／MR及廠商硬體各自待驗。

## 2026-11-02：伺服器清單交付的CI與證據

[功能a8855cc](https://github.com/peca12968/vr-command-center/commit/a8855cc96bdf8cb0ece5fcc4c2dc5e7e0743e2c0)的[CI41344259683](https://github.com/peca12968/vr-command-center/actions/runs/41344259683)／job124960591099完整 **success**：Linux738規則／459 HTTP／47 world、6 pipe、全部Python／素材及83 Node／269 Chromium通過；2 Windows限定skip不是Framework、WinForms、Unity、native或頭盔驗收。console47檔 artifact13098871115／ZIP **11,451,172 bytes／SHA256 bd4624e686c0f92778b9eee34dd3db57a128ac6d5b1c6f7a773955d0c22ee630**，control13檔 artifact13098607730／ZIP **3,918 bytes／SHA256 d8b15a858f0b43d5f07e934a8e2107bc0ab664d46660a75023526c8a2afd7d58**，均已下載核對GitHub digest、逐檔hash並保存完整decoded log（SHA256 4ad0493f6a621d9cc3d28a4e8a263daadaa9d096b9407c027d5ad24d16742829）。`server-catalog-ci-validation.json`明列1260＋47＝**1307 browser證據**，另13 metadata；既有native UI5與本輪native UI2另列。後續只有文件提交skip ci，測試來源精確a8855cc；本機38＋26與106／777範圍保持，GUI仍未完成。

## 2026-11-02：伺服器房間／任務清單與明確選取

新增[伺服器待開場次清單](SERVER_CATALOG.md)。Launcher **1.1.0**，獨立於原Unity **0.39.0／code49／NGO29**、API **0.31.0**及控制台 **0.31.1**；原e0d60e4e...／224真正Editor／雙平台、Scene／prefab ID與規則／wire保持，沒有新Editor、Unity或本機API build；CI另有Linux build與驗證。

原GUI只列UUID並需重選實例更新；現在直接輸入或選control-instance.json後載入／更新，清單顯示房間、模式、任務與id前綴，完整場次／任務版本ID另列，啟動仍用原UUID。初次不自選；路徑編輯先停用，載入失敗清原Current／Selected，不沿舊目標；更新只保留同path／instance ID／API／GameServer key且原id仍在的選取，不改選別房。Running／bound／MR不供啟動，原Start仍重新核對loaded API的GameServer／Preparing／未綁來源；清單不當預約／就緒。名稱顯示移除control／bidi並保留surrogate boundary，原name／id不改。新CLI --catalog只GET原身分／場次，bounded256Ki字元／5秒／最多5 active，拒絕錯id／mode／room重疊及資料錯型別；public JSON無key，complete只是read finished，不新增key、配票或管理寫入。

五份server ZIP全保留：新v4 **82,669,330 bytes／SHAf75b27e2d5fbcb106943808aa735651f93ebb6516e782716e1f56186529f6f4e**初候選，主包v5 **82,669,350 bytes／SHA3eef78fbe8319e366afa80cdfad31557bf42fb8bc3992402b6f252525e2857a2**、311 manifest／ZIP312，launcher input **fb57807d4744f06f6c2fe4f8737b1e7517543535a3d7eb8498a981f09340f073**；v4 input efec287c...。本輪package先凍結實際ServerLauncher.input.cs再編譯，原v3 source98c1f1...亦另保存；manifest不是簽章，無key／DB／ticket混入。原8份管理ZIP、玩家ZIP／APK及runtime未改。

初catalog／`server-catalog/run-f8663646f3d04ca9963540dca45ba805`有26 wrapper＋26真正Framework assertions成功。最終64877／`run-e7a553783114426daafc864ae27deff5` **exit0／38 CLI/API＋26 Framework**，包含真正五獨立／Linked、bound／MR metadata過濾、原id／version／read-only、role／marker改變、failure清除、原選取消失不換房與public JSON無生成key。proof直接編譯production catalog/state methods、不建立或操作WinForms；只在自己fresh fixture改還原marker/key且hash相同，以Master做一次測試End以證明選取消失，不能當產品catalog寫入或頭盔／校正MR。

新GUI70028／`server-gui/run-31f42864c4a0450a9d4daf9db9f70434` **exit1／未完成**：Window16189230／GUI10992，新增欄位與disabled Start可見；type_text未觀察落地，改用skill允許的ValuePattern後路徑確實改變、編輯提示與disabled Start生效。text-only click因geometry缺失未操作；補snapshot後兩次點擊（含activate／fresh state的一次重試）仍回報點上為PickerHost.exe而非Launch-Server，沒有load／selection／start或native來源成功。停止UI輸入、未操作PickerHost或任何權限／安全設定，只終止自己的GUI，API正常Stop／exit0，cleanup空列、C9／F保持；部分操作不當全GUI成功或根因修復。已向使用者非阻塞詢問是否有停留擷取／選檔視窗，其他PC工作繼續；沒有把未回覆當允許。

新版v5真正CLI31606／`server-package-checks/run-a6f7466c8f25462d86f73b41ad3900d4` **exit0／106項**：五獨立server＋五接收client，後Linked一server＋五接收client，真browser選原Running／一筆正常UI End／同source world GET提示與原native終界；**777完整API回放（185／158／144／124／110／56）**、10份原admission結果／CSV、雙seal／closed world journal durable尾界與原程序cleanup成功。terminal後另讀回10 CSV所有列／10原server network admission與ACK精確、無timeout，非新live／第107項。第七parent-exit仍故意未seal且無success final，不混六正常場；仍同機Simulation／接收者，沒有25位操作或GPU／LAN容量。

`server-catalog-delivery-validation.json`核對新C14＋14＋9failed＋80＝**117檔**與各F snapshot同hash、5份serverZIP／frozen compiler input、原8 controlZIP／玩家ZIP APK及e0d60e4e fingerprint，前C274／C163也同hash。1260 browser與原nativeUI5保持，新native UI2另列，未當新的全browser跑；4既有Python package邊界與新腳本語法成功。writer真正terminal才各一次snapshot，保存SQLite只rb/hash不開連線。完整11active，舊31／world371／Windows startup／F吞吐／完整GUI／乾淨新機／LAN／25操作／頭盔MR／廠商硬體各自待驗，不因本輪改判。

## 2026-11-02：主控台任務收尾與已封存End重試

[功能7a0da65](https://github.com/peca12968/vr-command-center/commit/7a0da6542c039b4de97b212aa67e3a651830a06b)的[CI41339991116](https://github.com/peca12968/vr-command-center/actions/runs/41339991116)／job124947761594／精確7a0da65完整**success**：Linux738規則／459 HTTP／47 world、6真正pipe程序、全部Python／素材與83 Node／269 Chromium通過。2 Windows限定skip不是Framework、Unity、native GUI或頭盔驗收。console47 artifact13097202219／ZIP **11,443,289 bytes／SHA4091035e0016961322021371bf8bae003459fd66238ee78625a768730753a6df**，control13 artifact13097370766／ZIP **3,919 bytes／SHA156cdc83d14a4658b4266fb50e07d2556afb08fbc63ef7efa1829ce4bcb17c97**與完整decoded log保存，ZIP digest與GitHub相符。`closure-ci-validation.json`明列1213＋47＝**1260 browser證據**，另13新CI metadata；本機C274／F、8管理ZIP／3 serverZIP／原玩家ZIP APK與前C163／C52native／C318control保持。文件後skip ci、測試來源精確7a0da65，failed／before不改判，完整11active。

新增[任務收尾](SESSION_CLOSURE.md)。API **0.31.0** REST／資料契約保持、控制台 **0.31.1**，分開顯示combat與world archive。只在選取的Ended來源場次頁可見時GET既有world，每兩秒／五秒逾時；同epoch／key／actor／session／sequence／stream與generation fence，世界header需同來源／rooms／clock、正數accepted與complete，統計精確同session序號／pending=false及combat.sealed才整體完成。隱藏／切頁／選取／登出／未知命令、刷新失敗或world讀取錯誤清除舊完成，401走原登出，404／403／5xx／異源不當綠。API的world seal已核對原Ended幀／combat尾界／統計，前端不讀live或保存journal／SQLite，不將archive當玩家送達／可關閉服務；原Begin、CSV閘門與0.5／1.5秒政策不動。

新增明確before反例：`console-closure-retry-before-20261102`／handle30262 **exit1**。真正API先接受End後GameServer封存0 combat，UI丟失回應、手動重試沿原UUID／expectedSequence，取得真正duplicate=true／sealed=true回條，舊畫面selected空／includeEnded=false／panelHidden=true，原30秒DOM逾時。compiled before API整組在`closure-b0bc5b...`，其WWW三source SHA另保存，沒有替換單DLL。修正只把「已確認End」保留條件改為response.session.state=Ended，已封存／無stream也保持選取，不再限定未seal；沒有自動寫入重試或改UUID。最終完整 **83 Node／269 Chromium**成功，包含原11項closure UI讀取／失敗／390px／登出fence及兩個真End retry檢查；world多狀態部分為明確UI route fixture，不當原生source。

新普通solution兩組各自保留；最終`closure-final-29fb7e09a7b2459aabed648f398c6e93`同次API136／三工具各9／Checks97，最終本機 **738規則／459 HTTP／47 world**成功。Windows HTTP這次成功不是舊startup根因修復。API/UI拆開版本以保持舊GameServer的0.31.0 gate，沒有新endpoint、world schema或Unity修改；Unity **0.39／code49／NGO29／e0d60e4e...／原224真正Editor與同源雙平台／Scene-prefab ID**保持。

兩個自含publication是`control-server-5d23dc...`與最終`control-server-4bb90a...`，各481輸出、原lock依賴群組保持，repository locks不改。兩份新管理ZIP皆 **52,466,368 bytes**，初closure SHA684f1f4d92ce206eff8319486245bcbc6b1ef6f1dfa76266fdf780d3892d61cc為保留候選，最終`control-server-api0.31.0-ui0.31.1-closure-final-win-x64.zip` **SHA7d87669d0f8478feb328697c3d9d58005aa8f0e3331726080374fa6ab5a254e5**、501 manifest（ZIP502）／481 runtime，含consoleVersion metadata。Framework啟動器source266d93...不變、API根版本0.31.0；不能僅用相同大小或版本認定同包。初control42125／`run-86f7aa...`與final93192／`run-709c59...`各 **105項**成功，沒有因本輪重做Windows啟動器GUI或改判原PickerHost。

首新native `server-package-checks/run-ad5b5fdd5ea34effb475ef463701b951`／21777 **exit1**：觀察器在原Running ready後等closure逾時，自己的browser22588正常exit0、cleanup乾淨，五房各已精確seal／回放，但未到Linked／公開10結果檢查。當時從別API通路End而未含Ended，可能被現有篩選移走；缺末刻DOM，不證唯一根因。改用真正UI End並補有限失敗state／五秒圖，60秒觀察期限保持。候選67639／`run-ce7572...` **106項／596完整回放**成功，scope與最終分開。

最終native15604／`run-c8d93c6d2da3455fa95f26db408d24a5` **exit0／106項**：包內API＋原server v3（SHA6cecfbee...）／原Unity，五獨立server＋五接收client，後Linked一server＋五接收client。真正頁面先選中Running，正常End按鈕只送一筆非duplicate 200 POST／原expectedSequence，來源完整回條、頁面自動含Ended、同source的world GET／已封存提示與原native精確尾界一致，沒有route fulfill／UI state注入；browser原process exit0，沒有送達聲稱。六場 **619全API回放（153／129／110／95／76／56）**、10份原admission結果／CSV、雙seal／closed world journal精確durable尾界與原child cleanup成功；第七parent-exit仍刻意未seal且無success final，不混正常六場。terminal後closed-readback另外只讀JSON／CSV／log，10 CSV每列／10原network admission與server ACK精確、無timeout，非新的live檢查或第107項。

本輪五family原C27＋60failed＋80candidate＋27＋80final＝**274檔**，全writer terminal後各一次F snapshot同hash，保存SQLite不開。`closure-delivery-validation.json`核對兩新pub／501主包、8管理ZIP／3 serverZIP、原玩家ZIP／APK／fingerprint及新API整組；`closure-prior-preservation.json`另核對前C52 native／C318 control及F370檔，前server package C163也保持。三browser資料夾47＋7before failed＋47final＝101，前1112＋101＝**1213 browser證據**，另兩成功／一failed native observer共5 PNG保持獨立範圍；原77／3399歷史native不混新family、不稱全重跑。7既有control／4既有server Python邊界成功。完整11active，原31／world371／Windows startup／F吞吐、完整server GUI／乾淨新機／LAN／25操作／頭盔MR／硬體仍待。

## 2026-11-02：Windows遊戲伺服器可攜啟動

[功能95411a2](https://github.com/peca12968/vr-command-center/commit/95411a264ac85894669b9127f3b40989982b30d0)的[CI41335830454](https://github.com/peca12968/vr-command-center/actions/runs/41335830454)／job124935327276／精確95411a2完整**success**：Linux738規則／459 HTTP／47 world、6真正pipe程序／4新Python封裝邊界與原工作流程／素材、78 Node／256 Chromium。2 Windows限定skip不是Framework／原生GUI／Editor／頭盔；本機103與failed GUI分開保持。console43 artifact13094744913／ZIP **10,005,039 bytes／SHAfd9e1fa1995ef18c65339b68308de501138f3a3cd8a91008d89810e3e2de75f4**，control13 artifact13095560953／ZIP **3,919 bytes／SHAacdf31e1d6331e34946ff3a4862814728446453441995d1d28ce6bd5e014b4c5**及完整decoded log保存，ZIP digest與GitHub相符。`server-ci-validation.json`明列1069＋43＝**1112 browser證據**，另13新CI管線metadata，未混入GUI／native；本輪沒有新本機browser場，後續文件skip ci、測試來源精確95411a2。

原handle27088 terminal後的`closed-readback.json`另外只讀既有JSON／CSV／log，核對六場10份CSV每列與sealed ledger一致，10個server admission network ID與10個原ACK集合精確相等、無server timeout。這是後補閉源讀回，不是第104項新live測試或又一場原生；原C78／F snapshot不動。`server-current-source.json`保存目前五份source byte且launcher SHA與v3實際編譯輸入相同，沒有冒充v1／v2來源原件備份。

新增[Windows遊戲伺服器包](WINDOWS_SERVER_PACKAGE.md)，Framework4.8繁中啟動器／CLI與原Unity0.39.0／code49／NGO29整組runtime封裝，操作員不需Python／Editor／SDK。API/UI0.31.0、rules0.8.0／world schema1／envelope7與原224真正Editor、e0d60e4ed6cefe5cd885e6aabe1621939da945ce00d56b3ed8820c0aed4db879同源Windows／ARM64 APK、原Scene／prefab ID保持，本輪沒有新Editor／Unity重建。

只用GameServer角色讀原Preparing VR且無combatStream的場次；新包外資料／私有log、同API／場次mutex，啟動前UDP衝突拒絕，Unity只收到GameServer key，沒有Master／玩家票券或代替管理Begin／End。原bootstrap先核對自己的combat UUID／origin／0 accepted／未seal，再StartServer寫真正network-start log；新啟動器沿這條原順序核對同場次API來源／world header才PUT immutable endpoint並驗回條，不開live獨佔journal。就緒不是玩家pose或Running證明。包內manifest逐檔SHA／大小及完整集合、拒絕連結／越界／額外檔，不是簽章。

Unity程序先suspended建立，加入私人kill-on-close Windows Job再Resume，只設終止旗標，不改CPU／優先序／記憶體／OS設定。正常End30秒內需雙seal，留36秒後以OS終止自己的Unity，原handle退出才complete；不是Unity graceful或玩家全收到／local ack最後落盤證明，玩家送達欄位null。失敗／中止保留journal、不自動End或接管舊Running，來源／管理請求失敗也不冒充正常完成；真頭盔、MR、網路及恢復機制另驗。

三份ZIP原件／receipt保持：v1 82,664,434／SHA26c44bed...、v2 82,664,466／SHAf77bf1a7...、主包v3 **82,664,818 bytes／SHA6cecfbeeffba1277000f93bc168c4ac387b825c34b73142628098dba28f67500**、311 manifest檔案（ZIP312含manifest），launcher來源SHA98c1f1db72049c301e8f1bee9a2835bbe388780027df75d84642131739b14642。v2是71項初輪；v3補完整包集合拒絕及GUI啟動等待中止，不重建Unity。Notices沿原玩家包素材／Transport授權。

真正handle35529 exit0／`server-package-checks/run-681a8591d76a45418b759e64315ab4f4`：71項、五獨立後Linked、原戰績ack／closed journal雙seal，未取完整API replay或精確原admission比對。最終handle27088 exit0／`run-d1463f9bd5be4d1aa5ab0ef98c402179`：**103項**；五獨立各一server／一接收client、後Linked一server／五接收client，10份原admission結果／CSV、Running的原Begin sequence／tick／observed／1.5秒來源界線、六場**553全API回放**（138／114／99／80／66／56）及雙seal／closed journal完整與ack精確尾界成功。每場只取有限live觀察，不是全程姿態健康或25位操作／跨機容量。Master／Room／Client／Host、混淆／多播IPv4、越界與32bit wrap埠、額外key、占用UDP、已End／bound Preparing等拒絕。兩組測試的第七個parent-exit場刻意在就緒後殺父程序，原Unity handle被Job收掉且無final成功報告；該場journal未seal，不能混入六個正常場。

新GUI handle6614／`server-gui/run-3c10b49ef207440aa060af85c0d6af41` **exit1／未完成**。CLI準備自己管理實例／API與Preparing場次，native Window31526058／GUI62088顯示欄位與disabled Start正確；選實例按鈕第一次及activate／新snapshot後一次重試均被非目標PickerHost.exe遮住（工具回報point over PickerHost而非Launch-Server），因此停止所有UI輸入，沒有選檔、啟動或遊戲來源成功。只終止自己的GUI，API正常Stop／exit0，cleanup空列，failed及原C9／F snapshot保存，不當PickerHost／Windows安全性根因或產品選檔驗收。後補helper關窗review在真GUI exit後最多等30秒，僅py_compile，沒有冒充新GUI場。管理服務包原GUI95151成功是另一產品流程。

4項Python package邊界與三新腳本語法檢查成功，假bytes測試不當native。`server-delivery-validation.json`用rb／SHA核對新C76＋C78＋GUI C9＝**163檔**與各F snapshot精確相同；原13場及後補pipe的C52 native／C318 control與F保持，六管理ZIP與主包、原0.39玩家ZIP／APK及source fingerprint同hash。原77場3399歷史native保持，不把這三個封裝family或未seal反例混入原總數，也沒有全重跑。原1069 browser與13 CI metadata保持，本輪尚未新增browser。保存SQLite不開，所有自己writer確認terminal才一次snapshot。完整11active，原31／world371／舊Windows startup／F吞吐與乾淨新機、LAN、25位操作／實機待驗不改判。

## 2026-11-02：Windows可攜管理服務與私有程序收尾

[功能1a959c6](https://github.com/peca12968/vr-command-center/commit/1a959c6b89e627791815537a57784c3bcb4819b1)的[CI41332911824](https://github.com/peca12968/vr-command-center/actions/runs/41332911824)／job124926578810／精確1a959c6完整**success**：Linux738規則／459 HTTP／47 world、6個真正私有管線程序案例、7項新Python封裝邊界與工作流程原檢查／素材、78 Node／256 Chromium全部通過。2 Windows限定skip不是Framework／GUI／Unity或頭盔證據；本機105與GUI／原生另外保存，沒有以CI代替。

CI下載console43檔artifact13093623576／ZIP **10,038,781 bytes／SHA `07e02d8202b099c6d6d21504aef3a89a26edb08cb32a3aee434346c9aa957df0`**，control-pipe13檔artifact13093473878／ZIP **3,918 bytes／SHA `34bc0eb51bdc4540ab33819ff56aa71f77e4fd4f58a47afa961c883f6e43d3b2`**及完整decoded job log，均與GitHub digest相符。control artifact只含6份遮蔽log／6份有限status／checks，closed-pipes stdout未觀察明確null，沒有runtime／key／DB。`control-ci-validation.json`核對前1026 browser／新43＝**1069份browser證據**與另13份CI管線metadata，原14場C52native／C318control與F snapshot、六候選ZIP／主包、478 publish、API整組、原Unity0.39／224及ZIP／APK保持。後續僅文件證據skip ci，測試來源精確1a959c6；Windows本輪459成功仍非舊startup根因修復，完整11項active。

API／控制台 **0.31.0** 新增[管理服務包](WINDOWS_CONTROL_PACKAGE.md)。Framework4.8編譯的繁中啟動器，可新增／選取自己的資料實例，明確選擇本機IPv4／埠、啟動／停止API及開啟控制台。API apphost自含.NET／ASP.NET Core **10.0.14 win-x64**，資料、七角色金鑰與票券簽章key獨立存放；Web／入場／統計／世界契約保持，Unity **0.39.0／code49／NGO29／e0d60e4e...**與原224 Editor／雙平台receipt保持，本輪沒有新Editor或Unity建置。

API只在明確ControlPipeToken配置時監看私有stdin，ApplicationStarted發本次nonce就緒事件。啟動器另核對原child存活、實際包內coreclr及Master身分，自己的stderr／stdout診斷有限且遮蔽全部key／nonce。錯token短行不停止，匹配STOP要求正常停止；EOF／越界／非ASCII／讀取或就緒輸出IO失敗也收尾。普通API沒有此token仍沿原生命週期；沒有公開HTTP停機／取key端點。正常Stop等原child真正退出／exit0，40秒後的強制收尾或未知不能綠，GUI保留未確認狀態。繼承的角色key／資料等設定不能蓋過自己的實例；exclusive lease拒絕同實例雙啟動。

publish採全新C來源snapshot，RID鎖定只在snapshot變動，原repository lock及原依賴群組／contentHash保持。第一次自含publish為`control-server-d9d920...`，後補就緒輸出IOException防護的最終為`control-server-09f992...`；兩組source／locks／478輸出均保留，沒有單換共用DLL。另兩個完整solution C build各自保留；最終regular API及三工具整組在`control-suite-final-0c4b4d...`，控制台／原生工具version gate同步0.31.0。

初候選Notices完整包名／版本／nuspec名稱造成實際resolved檔名290字元（logical237），Python一般路徑失敗、extended同一原件存在；這次檢查在建新實例前失敗，沒有API場次。改短Notices/pN並保留完整package／originalFileName對照，stage採短Pkg根目錄，不改系統long-path設定；六份ZIP／各receipt原件保持。原runtime授權／NuGet metadata及明確版本的上游參考授權已保留，參考SQLitePCLRaw2.1.12的NOTICE不冒充實際2.1.13來源證明，Git blob bytes另有7項邊界測試核對。

舊報告SaveNew在CreateNew後才序列化，第一個真正封裝場`control-package-checks/run-d2c1f2ed9e4143468cb7cbfff24b0815`／40749 **exit1**，讀取ready報告遇到未完成JSON；原runner於finally正常停止、first-final child19788 exit0／graceful及cleanup空列／閉源snapshot保存。修正為exclusive同目錄暫存、完整寫入／Flush後File.Move至新目的檔，不覆蓋既有檔。受控反射呼叫真正編譯方法、讓serializer getter等待時，舊版最終檔可見且0 bytes／原子斷言exit1，新版最終檔不可見／exit0，最後JSON相同；兩份來源／binary／getter proof保持，不把控制情境當原OS排程唯一原因或完整AppDomain證明。

原子候選`run-758d60...`／18136及reviewed候選`run-a6ac68...`／95428，各**105項**完整成功；最終release `run-8ba6cac8c70640e1b14d60bdf3c4bcb6`／61594 **exit0／105項**。包含真正compiled CLI拒絕／資料與report路徑隔離、七角色身分、五獨立房25個原admission、Room隔離與越權403、同實例雙啟動拒絕、原Preparing場次／序號／任務／keys重開相同、正常End後新Linked／active0、原child handle的正常停止及父程序被終止後EOF退出、輸出不含生成key。每項數包含有限診斷逐檔遮蔽檢查；25個名冊席位不是25個遊戲連線。

GUI首場`run-93dd11eb7d134dd5856d5350ab445c68`／77858 **exit1**，只開到舊樹狀資料夾對話框，未完成API啟停，取消／關窗後cleanup空列與snapshot保留。後改選control-instance.json的OpenFileDialog，可直接輸入完整路徑；新場`run-e8f5b5...`／80930及最終`run-8241a1ad5fa24de69ffdd7ac0f923af5`／95151皆**exit0**。實際選檔／Start／Stop／關窗、就緒／正常停止文字與GUI exit0觀察，自己的API48340／37612以原OS handle核對exit0、包內coreclr與Master，原三份私有檔案hash未改。GUI只重開CLI預先建立並暖啟動的實例，沒有UI生成key、剪貼簿或瀏覽器登入；沒有保存GPU probe圖／PCM或把review當程序退出證明。

最終主包`control-server-0.31.0-release-win-x64.zip` **52,456,642 bytes／SHA `b38391f1f72115a98a60ba1bc8f5cb1e7395abe633c1366c0fa9529dce794eb1`**，478 runtime、498 manifest檔案／ZIP499含manifest，角色／票券／DB不放進包。移除測試程序dotnet PATH並設不存在DOTNET_ROOT，實際child coreclr仍在本包，這不是乾淨新機或遠端LAN驗收。舊名稱final／atomic／reviewed／ui為保留候選，不可依檔名認定主包。最終方法反例`control-report-checks/run-6d6a4726f4394b4fadfd3398787ecac9`外層工具exit0，舊方法原斷言exit1／新exit0；先前兩組方法對照也保留。

真正普通API／私有管線最初兩個5案例、之後兩個6案例均保存。最終`control-pipe/run-67f9ec78c4904fd79a65ed08f941ebc0`／38152內6案例成功：普通stdin關閉仍活、非法token拒啟、錯STOP／128字短行不授權、正確STOP、EOF、129字越界與父端輸入輸出皆關閉收尾；這些子情境合計為6個程序案例，closed-pipes沒有觀察stdout，readyEvents明確null／DisabledByFixture，不填成0。GET與POST均無公開停機路由。原default案例以外部terminate結束、不是正常管線收尾成功。

本機最終 **738規則／459 HTTP／47 world、6管線、7新Python封裝邊界、78 Node／256 Chromium**成功。初regular候選與最終各一份43 browser檔，前940＋86＝**1026份browser證據**，不是測試數。原生候選`desktop-venue/20261102-011035-4b788abf`／70763與最終`20261102-012431-fb1c45ff`／21310皆**exit0／6項／7場**，採同版原Unity0.39、各自整組新API0.31；獨立／重用／舊票／後續Linked與精確seal成功，非25位操作或封裝GameServer驗收。

`control-delivery-validation.json`核對13個本輪已terminal場次：原生兩場C52、管理／管線／GUI各原件C275與各F snapshot逐byte相同，失敗仍failed；歷史native75場3347＋新2場52＝77場3399（不混入管理測試）。前940 browser、原0.39 binary／ZIP／APK／224、327 archive、原accepted API134＋三工具各9／Checks96均保持；新舊六ZIP與每份完整publish也核對。後補每pipe案例的接受／退出metadata與CI安全上傳，`run-c876b048f96a433a947e7e102f8c7e52`再6案例成功、原C43與F相同；control-pipe-metadata-validation.json記錄總14場、control318／native52，另13份有限log／status／checks，不把runtime keys／DB加入CI artifact。沒有開啟保存SQLite，自己writer全停才各一次snapshot。完整11項仍active，原31筆／world371姿態失效、Windows startup與F吞吐根因未由本輪修復；跨機／25位操作／頭盔／MR／廠商硬體與完整遊戲伺服器部署另驗。CI精確來源與結果於本節後續更新。

## 2026-11-02：電腦端蹲姿、掩體與焦點恢復

功能[c78be60](https://github.com/peca12968/vr-command-center/commit/c78be6003513ba0e17c55db2ed281e2bd26a1517)的首[CI41324739444](https://github.com/peca12968/vr-command-center/actions/runs/41324739444)／job124902203001最終failure：738規則／459 HTTP／47 world、工作流程Python含6 crouch／素材與78 Node已過，browser在world-browser:141的camera-save點擊等待30秒逾時。原16檔artifact13091095943＋完整decoded log／ZIP **3,831,691 bytes／SHA `7cceb1bce999b8e9b14480a8141feb79772e573eeb55723afa83d166272534ac`**保存且與GitHub digest相符；沒有當刻save按鈕狀態或對應失敗圖，原GET metadata只涵蓋較早reload，不能由此證明disabled、焦點、RAF、渲染負載或產品唯一原因。

後續fixture僅在該保存操作前明確bringToFront，保存最多4筆前／後／失敗control狀態與500字訊息、可見性／焦點／button rectangle／disabled，不收HTML、input值、key、header或payload；失敗另對正確remembered分頁5秒截圖並重拋、釋放save gate／route。原locator click30秒、API期限、60秒relay、所有原斷言及產品JS/API／遊戲政策不改，沒有force點擊或重試寫入。新本機69409原handle exit0：**78 Node／256 Chromium、43檔**，實際before-click為visible／focused／enabled，after-click進入pending、.046秒callback間隔含觀察成本非RTT；這是新場成功，非舊CI根因／修復證明。遊戲及API來源、224／雙平台／原生792與五房結果未重建或改判。前838＋失敗16＋本機43＝**897份browser證據**，不是測試數；新CI結果另記。

[fixture914051c](https://github.com/peca12968/vr-command-center/commit/914051ceaac54a9c9390e201c225fc828df8a27b)的[CI41325529518](https://github.com/peca12968/vr-command-center/actions/runs/41325529518)／job124904550210／精確914051c完整**success**：Linux738規則／459 HTTP／47 world、工作流程Python含6 crouch／素材、78 Node／256 Chromium。2 Windows限定skip不是Unity／原生或頭盔證據；真正224及本機C／W原生另外核對。新CI該相機操作before-click visible／focused／enabled、after-click pending，該時來源已Ended；本機新場同刻Running，各自保存，不當舊CI當刻狀態、唯一原因或修復證明。

43檔artifact13090259562＋完整decoded log／ZIP **10,003,359 bytes／SHA `e6c3cef5cf65c247ee370031d0d8ad4ea2d37a0f9ab8ce13035883e12a4219a4`**已下載且與GitHub digest相符。`desktop-crouch-ci-success-validation.json`核對原40 runtime／F snapshot、327 archive、兩次失敗Editor、API整組及新0.39 binary／ZIP／APK保持，前897 browser＋新43＝**940份browser證據**。首validation文字比對誤用Node舊版`# tests`格式而exit1、尚未產生成功JSON，修正為本輪實際`ℹ tests`／`ℹ pass`後採新driver成功；失敗driver保留，CI本身早已完整success，不改測試數或遊戲。後續只有文件證據提交skip ci，測試來源精確914051c、遊戲來源仍e0d60e4e...。

Unity **0.39.0／Android code49／NGO29**，API/UI0.30.2／rules0.8.0／world schema1保持。無頭盔owner新增左／右Ctrl按住與C切換蹲姿，眼高1.65→1.0m、手與槍口沿原相對旋轉；移動保留高度、原速度／房界／碰撞。HUD讀原server人物位置／有效性，失焦／應用暫停或恢復／停用立即清除stance並恢復本機站立，下一個原Pose再發布。Tracked、wire、header、素材profile、傷害及0.5／1.5政策不改。既有人物依高度縮放，未新增屈膝骨架動畫；完整機制見[DESKTOP_CROUCH](DESKTOP_CROUCH.md)。

新增16項、共**224真正Editor／0失敗／0 skip**，3項是官方Keyboard在真正PlayMode Dynamic消費事件。首場224／218／6：EditMode SendMessage被引擎拒絕及3鍵盤事件未路由；改直接呼叫callback邏輯後第二場224／221／3，保存實際鍵盤值0診斷。測試依本機已安裝InputSystem的Editor鍵盤routing暫時導向GameView、finally恢復設定後才224全過，正式InputSettings未更動。兩次真正exit1的XML／log／選定來源先封存，沒有抑制錯誤或改判；不是完整生命週期引擎派送驗證。另6項Python證據反例與5項原snapshot測試成功。

Windows／ARM64 Quest同源 fingerprint **`e0d60e4ed6cefe5cd885e6aabe1621939da945ce00d56b3ed8820c0aed4db879`**及原scene／prefab ID保持。雙平台建置結束後才執行真正Windows場。Windows包 **82,647,558 bytes／SHA `09f4ac14a9497329080d018dd634ebfdee13cabb0b7e0c7d2ed8b077173e47cc`**、311 runtime／原launcher，新C展開19項通過；第一次檢查指向誤寫的不存在子目錄、未啟動遊戲，修正pointer後採新driver，失敗driver保留。APK **60,334,582 bytes**、0.39.0／49／ARM64／min32 target35及v2簽章成功，尚無頭盔安裝。舊0.38 binary／log321＋6選定來源先封存327檔，不是完整source graph；舊ZIP及APK raw保持。

真正互動場`desktop-crouch/20261102-000305-4f367a90`原handle35883 **exit0／6項**：實際C蹲下、C站起、C與W移動，再在明確Pause後最小化／恢復自有視窗、不按C仍回站姿。792完整回放／739張已接受Begin的Running／Paused幀、11保存參考逐幀相符；本場Paused失效幀0，不把排除規則稱為觀察到失效。原.5／1.5門檻保持，收到時最大來源年齡0.201763秒含輪詢／發布、非RTT。

原席0 head=(-3,1.65,-3)、席1=(-1.5,1.65,-3)、Hold NPC feet=(-4.5,0,-1)，正常任務油桶feet=(-3.75,0,-2) yaw0，不注入姿態／武器。蹲姿source tick473→519維持100血，敵軍同期確實向站立同伴開火3次；站起恰好1發／20傷害，原管理命令關閉AutoAttack。W移動保留1.0m高度，同伴原位置／1.65m高度／彈藥不變。最後兩份原admission結果健康80／0、中彈1／5、耗彈均0；CSV、戰鬥6／world792／through17、雙seal與原兩連線唯一server ACK相符，active0／cleanup空列及writer全停後snapshot成功。官方Ctrl按住／放開僅Editor虛擬Keyboard證據，本輪原生實際輸入為C／W，沒有GPU probe圖檔／PCM／頭盔或跨機驗收。

一般五房`desktop-venue/20261102-000500-7b756ab9`原handle98440 **exit0／6項／7場**，五獨立房、單房End／重用、舊票／越權拒絕、後續Linked及精確seal／active0／cleanup成功。每房一玩家，非25位操作。未重建API或共用Simulation，沿用上一輪accepted C API134＋三工具各9／Checks96的整組0.30.2輸出，沒有單換DLL。

`desktop-crouch-validation.json`逐檔核對兩個新C runtime共40檔及F snapshot相符、新F evidence含snapshot共124檔；前838 browser、AI前4場68 runtime／snapshot、原accepted API整組、舊327 archive及兩次失敗測試5／6檔保持。歷史73場3307＋新2場40＝75場3347 runtime檔，不是全歷史重跑。新APK SHA **`0310fe1870668633e03f2413cb3b927e6eceb922f7cbe534efb7d45f14a2a263`**，raw未重封裝；保存SQLite僅rb雜湊、不開連線。

完整11項仍active；原31筆／world371參戰失效、Windows startup與F吞吐問題未由本輪修復，頭盔、MR、跨機及25位操作仍待實際驗收。完整CI精確來源及raw雜湊核對結果另記於本節後續。

## 2026-11-01：統計來源標籤不能當完整數字讀回

AI功能`17b75e9`的[CI41297698388](https://github.com/peca12968/vr-command-center/actions/runs/41297698388)／job124821936708最終failure：738規則／459 HTTP／47串流、工作流程Python含7 targeting／素材及78 Node已過，browser在check.cjs:205統計列精確斷言失敗。原只等「模擬資料」標籤後立即讀整列，沒有該刻row metadata；失敗後PNG的數字已正確，不能由較晚截圖推定斷言時也正確、或證明唯一CI原因。4檔artifact13080141669＋log／ZIP **1,053,078 bytes／SHA `9297eabd5a6fd7dfb3111cb6fb6ed96d0f01a634a3ce79b62fbd6c3071f78594`**精確保存，原failure不改判。

自己的C BrowserRuns保留原origin-only等待與精確數字斷言，只加入可控的真實較早GET：先接受ShotFired、擷取through13統計但暫不交付；再接受其餘3筆到session16，交付原GET。產品確實顯示「模擬資料」及Alpha 01的1／0／0／0／0%／100，原等待成立、原斷言失敗，16486原handle exit1；metadata與斷言前PNG保留。沒有偽造統計body或重送寫入，只持有同一次授權API實際回應。這證明等待條件不足，不把受控情境套成原CI的時間根因。

正式fixture保留同一受控前提，新增一項必須看見舊prefix的檢查；釋放後用原單一30秒DOM等待核對「來源＋完整統計列」同一讀取，再做原精確斷言，polling100。四筆原報告／ID／順序、產品JS/API／8秒API與遊戲0.5／1.5政策均不改，沒有寫入重試或提高期限；setup的擷取與舊prefix觀察也各有30秒界線，finally釋放兩gate／移除route。失敗另存無憑證的DOM統計列／phase／notice並重拋。

新本機37059原handle exit0：**78 Node／256 Chromium**，42檔`console-ai-target-stats-after-20261101`包含through13／accepted16反例metadata與完整checks。`ai-target-stats-fence-validation.json`核對舊CI4／受控反例7／新42、原68 runtime／F及遊戲binary／ZIP／APK hash未變；702前browser＋初41＋CI失敗4＋反例7＋新42＝**796份browser證據**，不是796項測試。本輪沒有新Unity／API建置或重跑原生，0f8287b0...／208及原三人／五房結果保持，完整11項active。

[fixture8dbb874](https://github.com/peca12968/vr-command-center/commit/8dbb8749a2cb5bbfeda5defb3b1e99a29ceec315)的[完整CI41298762465](https://github.com/peca12968/vr-command-center/actions/runs/41298762465)／job124825142728／精確8dbb874最終success：Linux738規則／459 HTTP／47 world、工作流程Python含7 targeting／素材、78 Node／256 Chromium全部成功。CI也保存through13／accepted16受控前提。2 Windows限定skip不是新Unity／native或頭盔證據，本機各場與雲端分開；原17b CI及受控舊fence均仍failed，不當原CI時間根因／產品修復證明。

42檔artifact13080935513與log／ZIP **10,040,719 bytes／SHA `20f05858ddf4861748e31d5c06414ed59541125acc0441a2c9fd71d4c182fc95`**已保存，下載與GitHub digest相符。`ai-target-ci-success-validation.json`重新核對前796 browser＋新42＝**838份browser證據**、本輪68原runtime／F snapshot、0.38 binary／ZIP／APK及舊327 archive未變。後續僅文件證據skip ci，測試來源精確8dbb874，遊戲來源仍0f8287b0...；ROADMAP目前M2／建置門檻更新208／0.38，不重寫歷史數量。完整11項active，跨機／頭盔／25位操作及原31／world371／startup／F吞吐仍另驗。

## 2026-11-01：AI 受阻後選擇可命中的玩家

從乾淨`5b4ff41`接續第6項，[AI_VISIBLE_TARGETS](AI_VISIBLE_TARGETS.md)修正只嘗試最近玩家的選敵：原同房／connected／存活／天氣日夜射程候選依距離與GUID排序，逐一原Cast，只有真正命中該玩家才接受。仍20tick／20傷害、原槍口、Hold／Patrol／Advance、Pause與0.5／1.5政策，Advance仍朝原最近合格者移動。AimTarget只供冷卻外觀追蹤，每發重新Cast，不改歷史射線、Tracked、wire、schema1／rules0.8.0或素材pin。最多每NPC5候選，完全受阻的Cast量可能增加，沒有據此宣稱25人效能完成。

Unity **0.38.0／code48／NGO29**、API/UI0.30.2；最終fingerprint **0f8287b002f46d0824bf4f3c27a450b672cc7554fdc156a4c238affdcd8f32b0**，原scene／prefab ID一致。Prepare79313、Tests37810、Desktop22837、Quest9574原handle均terminal exit0，**208真正Editor／0skip**；738規則／459 HTTP／47 world-stream、78 Node／255 Chromium與7新Python＋5 snapshot通過。初.NET fixture對nullable射線未明確檢查，CS8629失敗的C build／log保留；修正為pattern確認，採另一新C build，沒有放寬測試。首誤用Windows PowerShell5受執行政策拒絕、未啟動Editor；實際採既有PowerShell7 RemoteSigned，沒有改政策／授權或重裝工具。

真正ArenaSession產生器以六個合法VR地面物件得到NPC(-3,0,-1)與(-3,0,-.25)，玩家原席0／1／2 head在X=-3／-1.5／0、Y1.65、Z-3，原Connect＋有效Pose後才可攻擊。舊來源第1tick健康80／100／100、後NPC無射擊；50個Runtime檔僅換ArenaWorld、Program逐byte相同的副本exit0，健康80／100／80，後NPC首tick選第三位。9個行為案例在.NET與真正Editor共用同一pure fixture，另驗掩體／GUID平手／冷卻重選／Pause停火／射程房間隔離／Advance政策／外觀不改保存射線。

初未Connect、次未Pose候選不能當有效玩家；正確入場的兩人候選，其第二條射線仍被NPC身體邊緣擋住，舊／新不開火合理。這些C來源／log與原兩人native `20261101-145732-14715650` exit1均保留，不稱較遠玩家可見。修正為三人後，舊0.37.2 native `20261101-150050-725e00df`仍exit1、後NPC從未開火，兩場的原戰績／CSV／雙seal及cleanup成功。後續helper另加傷害配對、Pause序號與全回放靜止核對，不能稱native前後完全相同依賴graph；共用來源隔離對照另由相同Program／單Runtime檔提供。

最終新native `20261101-182258-207e5e24`真正exit0／**4項、32全回放／12張已接受Begin後Running／Paused幀**：兩個tick1 EnemyShot及緊接20點傷害、最近玩家仍存活80才後NPC選第三位；三份原admission結果健康80／100／80、中彈1／0／1、CSV／雙seal／三個唯一server ACK、helper SHA前後與cleanup成功。原3玩家全程靜止Simulated／connected、兩NPC Hold原位健康100，無玩家輸入／姿態注入／GPU／PCM；收到時最大來源年齡0.150225秒非RTT。五房 `20261101-182316-77cc9ff6`／8844 exit0，原6項／7場隔離／錯票／重用／後續Linked及精確seal，仍每房1位非25位操作。

新Windows包`windows-player-0.38.0.zip` **82,646,224 bytes／SHA `1f4a27d8ca7b310acfd24a4a018b44449fb73b1c2ac02107ea1af2251ed35d7c`**，311 runtime／原launcher a65846da...，新C展開19項核對／拒絕成功，非完整GUI／跨機。APK **60,330,662 bytes／SHA `7e175d4a4eb566758e454457d17a7adbfac5c615bae184525c2b6ad6ab3d517e`**，0.38.0／48／ARM64／min32 target35、v2簽章成功，無實機安裝。原82,782,417 APK與新檔各105 ZIP項，compressed60,306,850→60,309,211、非索引payload22,475,567→21,451；容器差異不當內容縮減／ELF／性能或唯一Gradle原因，raw不重封裝，receipt totalBytes不是APK大小。兩平台建置結束後才跑新原生，前後不當效能因果對照。

`ai-target-before-validation.json`核對舊327（321binary/log＋6選定來源）archive、50檔Runtime／相同Program、兩失敗native28 runtime／F snapshot、前702 browser／上一場native48／runtime14；`ai-target-delivery-validation.json`新2場40 runtime與F snapshot、新F122，加前失敗F66共188／runtime68，歷史69場3239加4場68為**73場3307 runtime檔**，不是全數重跑。新41 browser與前702保持；原0.30.2 C API134＋三工具各9／Checks96依hash不變，新整組也各自保存，不單換Simulation DLL。全部自有writer停才一次snapshot，保存SQLite不開，原正式5080／舊ZIP與APK均保留。CI結果另補，完整11項active，原31筆／world371／Windows startup／F吞吐與跨機／實機各自未修復。

## 2026-11-01：雙擊場地定位觀戰鏡頭

從乾淨`2e86a34`接續第9／10項，[OBSERVER_GROUND](OBSERVER_GROUND.md)新增即時觀戰與3D模擬回放的左鍵雙擊場地定位。API／UI **0.30.2**；目前渲染鏡頭射線與Y=0投影，只接受來源實際包含的12m房間，保持角度／距離、target高度0.8m，成功才退出follow。間隙／房外／未包含房間／無效射線不移動；草稿不被改寫，書籤仍明確保存與原身分／場次權限，回放不seek。沒有管理／玩家移動或碰撞規則變更。

本機locked restore／零警告build、729規則／**459 HTTP**／47 world-stream、**78 Node／255 Chromium**完整通過。80365原handle terminal exit0；新41份browser證據含ground截圖已檢視，6個新增Node反例與7個browser檢查涵蓋五房幾何、房外、草稿、角度距離、follow、無寫入、書籤重載與回放不seek。本次Windows HTTP完整成功是新場結果，不將以前startup失敗改成通過，也沒有修改OS／auth／期限或證明根因修復。

真正Windows `desktop-venue/20261101-143859-67587c42` helper36250／browser80356均exit0：**54 UI／native、165世界幀**，名冊替換／環境AI／Pause／End、精確雙seal／原玩家結果與CSV／回放ledger一致、active0及cleanup無殘留。最大來源年齡0.191771秒非RTT，SwiftShader觀戰不是新原生GPU。14個C runtime與F snapshot逐檔相符、新F48；歷史68場3225再加14為69場3239，不當25人／跨機／頭盔驗收。

`ground-camera-validation.json`核對前620 browser／上一輪74 runtime與F snapshot／Unity二進位及包hash、新41 browser／48 F及14 runtime。新C API134（新JS與.gz）＋三工具各9、Checks96保存hash；Unity0.37.2／47／NGO29／7d3e...及原199 Editor／雙平台／ID保持，沒有新Editor或APK重建。首次準備腳本cp950讀HTML失敗的初C build保持，完成後採明確UTF-8與新C build；不覆蓋舊API或正式5080。完整11項active，原31／world371／F吞吐及外部依賴未修復。

[功能5df27a8](https://github.com/peca12968/vr-command-center/commit/5df27a8c2ff40ea268a22aa565ad2ce69a3e6f33)的[完整CI41281968515](https://github.com/peca12968/vr-command-center/actions/runs/41281968515)／job124775534858／精確5df27a8最終success：Linux729／459 HTTP／47 world、工作流程Python／素材、78 Node／255 Chromium全過。2 Windows限定skip不當本機Windows／Unity或頭盔證據；本機459是前述獨立成功場，不混為同一次執行。41檔artifact13073935856＋log／**10,018,457 bytes ZIP／SHA `7386c55d2cdbae6b531e384550c9dd98586a000d0b159efd87c5ca7f379fd42d`**下載與GitHub digest相符；`ground-camera-ci-validation.json`核對前620＋本機41＝661 browser、48份native與14 runtime／snapshot、原Unity binaries／ZIP／APK保持；新增CI41後合計702 browser證據。後續僅文件skip ci，測試來源精確5df27a8。

ROADMAP已移除過期的「等待GitHub帳務」待辦並更新現有M2與建置檢查數量199／0.37.2，保留歷史失敗與完整待驗範圍，沒有把SDK或已恢復CI列為目前阻礙。

## 2026-11-01：鏡頭重載 CI 失敗與有界請求觀察

導航功能來源`40f8516da53feb9610dc75bb9fb19d85ddf23dbe`的[CI41279882687](https://github.com/peca12968/vr-command-center/actions/runs/41279882687)／job124769450079最終failure。729規則／459 HTTP／47 world-stream、工作流程Python／素材及72 Node已過；Chromium在新登入觀戰頁等待已保存鏡頭選項30秒逾時，不能稱248項通過。失敗畫面已載入世界，鏡頭提示回應不完整；原資料沒有該GET的狀態／完成時間，不能推定API、body decoding、主機或路由根因。

原15檔artifact13073096399、log及ZIP3,813,684 bytes／SHA `1d2e87c7548e5abaa7be8d7d06e817d17d1be62628e70b2a0e95e57ab0aa8007`完整保留。僅browser fixture加入該新頁重載期間最多128個同源API GET metadata，記path／狀態／回呼相對時間／有限錯誤碼，不記headers、query、body或憑證，不改產品、路由、操作順序、30秒斷言或10秒API期限；超界仍失敗，完成只是觀察未超界，不代表請求全部成功、body已解碼或RTT。finally卸除listener並保存metadata，原failure仍保留。

本機新場`console-navigation-anchors-diagnostic-20261101`完整248 Chromium通過，40檔含13條GET metadata；鏡頭GET 200並正常finished。這是新場成功，不是原逾時的根因或修復證明；使用本輪隔離C API與relay，不動正式5080。僅fixture變更，不重建Unity／APK或改稱另一來源。

[診斷f1dda0a](https://github.com/peca12968/vr-command-center/commit/f1dda0a4a956d2bab598ebccc883fbcd919aa2e9)已推送main；[完整CI41280898186](https://github.com/peca12968/vr-command-center/actions/runs/41280898186)／job124772433249／精確f1dda0a最終success：Linux729規則／459 HTTP／47 world-stream、工作流程Python含13 navigation／素材與72 Node／248 Chromium成功。2 Windows限定skip不是native／Editor或本機Windows完整HTTP通過；原startup失敗不改判。此場13條GET metadata中鏡頭GET 200並finished，仍非原失敗根因證明。

40檔artifact13072709116、log與ZIP **9,683,723 bytes／SHA `e75e9de589076b63e3024fd135a989f3c9a071e989e02a602b482dbe0805d9ba`**已保存，下載與GitHub digest一致。`navigation-anchor-ci-success-validation.json`核對原525 browser／前CI失敗15／本機新40、共580份既有browser證據，新增CI40後合計620；新4場74 runtime與F snapshot、APK／ZIP仍原hash。`navigation-anchor-browser-diagnostic-validation.json`保留本機成功與前失敗hash；沒有覆寫40f失敗。後續僅文件證據skip ci，完整CI來源精確f1dda0a；Unity來源仍7d3e／199／雙平台，完整11項active。

## 2026-11-01：實際非格點起終點接線與原生逐tick端點觀察

從乾淨`13f22c7`接續第6項，[AI_NAVIGATION_ANCHORS](AI_NAVIGATION_ANCHORS.md)修正0.75m任務候選座標接到0.5m路網的問題。Unity **0.37.2／code47／NGO29**，API/UI0.30.1、world格式／rules0.8.0及原scene／prefab ID保持。最終Windows／ARM64 Quest同源 **7d3e1a926f1b1c9176f03809af75de0c2af7be0e5f3e4ec24851664327aa4f92**；最終Tests62491／Desktop70410／Quest21212原handle皆exit0、**199真正Editor全過0skip**。先前Prepare42518／Tests62157的195項／Desktop94888／Quest31685為2c96...初候選，後加觀察器的Prepare78173亦exit0；初候選321檔及XML／receipt另存，不能把相同0.37.2／47當成相同來源。

凍結0.37.1原始ArenaSession產生器兩反例實際exit1：油桶(-4.6,0,-1)使合法出生(-3.75,0,-1)取整到被擋(-4,0,-1)，路線0點／320tick仍不動；油桶(5.1,0,5)使巡邏目標(3.75,0,5)被改為(4,0,5)，路線30點／320tick仍差.25m。相同Program與50個Runtime檔只換GridNavigation，兩例exit0、保留精確起終點、到達與逐tick通行／位移合格，JSON／C工程與binary保存。這是.NET規則證據，非原生或硬體。

實際兩端先Walkable，再各接所在格最多四個可見角點，起點→角點／角點→終點各依原ClearSegment核對；多起點／多終點BFS、625格四方向與2500 sbyte邊快取保持，回傳路線保留實際兩端。共享可見角點的近端點也須真實直線可走才直連；不是修改候選順序、搬動出生、傳送、放寬.3m半徑／.05m取樣／.1m活動tick或.15m巡邏切換。網格解析度與無可用局部角點的狹窄區域仍有限制，沒有完整3D／NavMesh／人群導航宣稱。原回放使用原幀，不重算歷史路線。

新6核心與6導航Editor案例驗產生器兩端點、往返／逐tick安全、Linked外側兩房、同格真實目標及不能切過旋轉角；另4 Editor驗逐tick觀察器的瞬間端點、完整最早tick／row上限、漏tick／倒退拒絕、Editor不安裝。**729核心（原723＋6）、199 Editor（原189＋10）**通過。Python navigation13＋artifacts5＋first-person7＝25通過，包括profile幾何、非格點目標、原生身分／tick／期限及finish IO失敗仍native cleanup；語法／diff、原player-body pin與293官方transport＋1 scoped patch通過。

| 真正原生場／原handle | 結果與範圍 |
|---|---|
| `desktop-navigation/20261101-132748-57972625`，46348 exit1 | 2c96初候選、未開逐tick觀察。20秒live189幀、16–204連續仍無<.2m端點；原failed與cleanup保存。closed209幀中world81／82為tick141／143、位置約(4.5,0,4.799997)、距.20000267m且forward相反；沒有142原始位置，不能插補到達或改判通過 |
| `20261101-134848-394c3763`，30771 exit0 | 最終blocked-start，4項／268完整回放／248已接受Begin來源幀／9 refs，fault0；實際409 row連續tick1–409，端點row142距約.100003m、首次Begin來源row後7.052074秒，worldSequence=null |
| `20261101-135057-d4dc1db0`，92372 exit0 | 最終non-grid-goal，4項／148完整回放／118來源幀／9 refs，fault0；143 row連續tick1–143，最早<.2m為row141距約.1500001m、6.991734秒，worldSequence=null |
| `desktop-venue/20261101-135539-ac75f5f8`，14004 exit0 | 一般五房6項／7場，隔離／錯票／單房環境AI與Pause／席位重用／後續Linked及精確seal、活動0、cleanup成功；沒有navigation-tick-probe目錄，非25位操作或全複本逐幀證據 |

無探針首場的closed rb／checksum／序號分析只證明已保存位置，沒有tick142資料；新場row142不能補舊場、不能用反向或clock校準猜到達／根因。兩個最終場都明確--tick-probe，僅自己的Windows Development server加--vr-navigation-probe：每個真實session.Tick後觀察當下NPC，不改20Hz規則或10Hz world錄製／傳輸；普通／Editor／Android／client不安裝。最多180秒／4096 NPC row，保持完整最早tick，自動上限／漏tick／倒退不可complete，收集中不寫狀態，明確finish停收集／clock後一次report。只輸出NPC欄位、原session／stream、observed及單調seconds，不輸出玩家姿態／憑證／GPU／PCM，不是零擾動。

工具維持<.2m／20秒，原生row須完整1..N、原NPC／room／health、位置／位移、正確session／stream及已接受Begin；不以缺失tick插值或硬配world序號。原生證據獨立存，refs另取真正world，兩場最早replay/live分別20/21與30/32。普通回放仍逐張核對Begin4已套用後所有Running／Paused的原玩家健康100／connected／Simulated、NPC／房間／攻擊關閉與位置／位移。診斷在後續Hold／Pause／Advance與End前已finish；原admission結果、CSV、精確雙seal、唯一server ACK與兩層cleanup成功才complete，5helper SHA前後一致但不是完整graph。兩個場與最終Quest建置重疊，五房在build結束後；不同條件不當因果／效能對照，原31筆／world371未修復。

最終`windows-player-0.37.2-final.zip` **82,645,932 bytes／SHA25dd1ee56234cd7da3da1f9671877b6c8967a41f03d71f903f3008558425d5c4**，311 runtime／原launcher a65846da...；新C展開da4070d46cef4107b80fbb63a6ac3576、28311 exit0／19真正核對拒絕，非完整GUI／跨機。普通0.37.2 ZIP為2c96初候選、5ca9a6f5...，其19項與原件保留。最終APK **82,782,417 bytes／SHAd804087c10e2c0b376d3eb2e3bd875a5ef3bf97760c0a6b30c5a0dadc47b5eaa**，0.37.2／47／ARM64／min32 target35、v2 debug簽章成功，無頭盔安裝。

APK raw比初候選60,310,826 bytes大；ZIP索引仍105項，compressed payload僅從60,289,375增至60,306,850 bytes，非payload區段由21,451增至22,475,567 bytes。libil2cpp raw增67,632 bytes，額外大段位於目前索引payload之間；這是容器範圍觀察，不當完整ELF／遊戲內容增量、執行效能或唯一打包原因證明，raw與簽章保持、不重新封裝，receipt totalBytes不是APK大小。

`navigation-anchor-prior-validation.json`核對前64 runtime3151與各F snapshot／前F3719；`navigation-anchor-runtime-validation.json`新4 C runtime74與F snapshot相符、新F190，合計68場3225 runtime檔，前525份browser／CI、原API三組159／mission accepted與拒絕候選／本輪C API及工具保持。`navigation-anchor-probe-validation.json`另核對兩份完整raw report、原生來源與null world序號、一般五房無probe、兩組321 binary/log＋各10選定來源、4個原Git source blob；另存原CombatAuthority blob，不稱完整依賴graph。全部自己的writer全停才一次snapshot，原C不移動，保存SQLite不開連線。

完整11項active，仍同機Simulation／headsets0。CI結果另補；原31／world371、Windows完整HTTP startup、F吞吐、多人持續操作、跨機／Wi-Fi／Quest／VIVE／MR與廠商硬體各自未完成，不因這兩個導航反例或新場成功改判。

## 2026-11-01：敵軍繞行旋轉掩體，保留端點觀察逾時

從乾淨`0368b33`接續第6項，修正[AI_NAVIGATION](AI_NAVIGATION.md)。Unity **0.37.1／code46／NGO29**，API/UI0.30.1、world格式／rules0.8.0保持。新雙平台fingerprint **69d247a9ecfa7b42ee1e9314e0319869995f1876379850928f5725901e642fc2**，原scene／prefab ID一致；Prepare84165、Tests14853、Desktop55866、Quest67152原handle皆terminal exit0，**189真正Editor全過、0skip**。正式5080不動；新.NET API／三工具／Checks均在自己的C BuildRuns，第一份fixture失敗候選與舊API copies保留，原Windows完整HTTP startup問題沒有在本輪改判。

舊GridNavigation只看格點可站立便相連，Move卻以原ClearSegment檢查實際路段，遇旋轉掩體角落會拒絕移動再選同一路。凍結舊來源反例：45°油桶(.25,0,.25)，(-2,0,1)→(2,0,1)產生9點／1條不可通行邊，320活動tick仍卡住。另一個真正任務產生器端點配置：油桶(.25,0,-1.75)、(-4.5,0,-1)→(4.5,0,5)，舊31點／1壞邊、320tick仍約(0,0,-1)。兩個.NET實際exit1、原JSON／C來源／binary保存，不當原生或頭盔。

只改GridNavigation的凍結來源副本產生11點／0壞邊並可往返；前後50個Runtime檔只有該檔不同、Program逐byte相同。新搜尋以既有ClearSegment核對格邊，正反向共用不可變幾何的有界快取：每房625格／2500個sbyte槽／最多1200無向邊。原四方向／順序、.3m半徑／.05m取樣／.1m活動tick上限與Move再次檢查保持，沒有改傷害、目標、Tracked或封包。歷史回放使用原幀，不重新求路；不是完整3D地形、任意非格點端點／動態目標可達性或人群導航完成。

本機**723核心檢查**（原717＋6）通過；Editor新增5案例含往返／逐tick通行速度、Hold／Pause、Linked兩外側房及封閉牆。首候選CoreChecks在第280項因fixture誤判封閉牆而崩潰退出：x=-4..4的五沙包仍留兩側通路，實際繞行合理；log／兩來源與C候選binary保留。修正fixture為x=-4.8..4.8／2.4m間距後新C建置與723成功，沒有修改遊戲半徑或刪除原失敗。新API採`navigation-final-build-path.txt`下bin，舊／失敗候選不覆蓋。

| 真正原生場／原handle | 結果與範圍 |
|---|---|
| `desktop-navigation/20261101-125121-d130384b`，41746 exit0 | 4項／133完整回放、9 refs，原getter及初次live檢查點起的玩家／NPC核對；不是最後較早的Begin回放閘門 |
| `20261101-125410-3d188963`，43827 exit1 | 提早回放閘門已加入，但原20秒getter沒讀到短暫端點，未進後續控制／完整回放／結果驗收。cleanup成功、原failed保留；closed world90／91、tick150／152確已到達，不當來源未到達 |
| `20261101-125724-93f88fed`，35386 exit0 | 最終4項／**128完整回放／113已接受Begin後Running或Paused幀／9 refs**，fault0；live端點串流69幀連續17–85、tick150，Hold／Pause／Resume／Advance、零戰鬥統計、原admission結果／CSV／精確雙seal／唯一server ACK與cleanup成功 |
| `desktop-venue/20261101-125821-51d9d6e5`，97903 exit0 | 原五房6項／7場、隔離／錯票／房1環境AI與Pause不擾其他房／席位重用／後續Linked及精確seal、活動0、cleanup無殘留。每房1位，非25位操作或逐client複本全程驗收 |

端點getter逾時在writer全停後以closed journal的rb／record checksum／序號metadata另查：保存219幀、world90最短2.861e-6m、91仍<.2m。closed分析不是完整規則重放，不開保存SQLite、不修復／ack，也不把已保存端點補成live成功或推定主機／網路根因。工具改成單一連續live串流、20秒／256幀、序號不能跳、每packet用原header擷取UTC＋elapsed檢查1.5秒來源年齡，**不延長20秒或放寬.2m**。原逾時仍exit1，沒有重寫其結果。

最終接受Begin4，回放最早納入world15、首live Running是17，兩者分開；不是從第一個live檢查點才開始忽略更早來源。每張已接受Begin的Running／Paused保存幀核對原玩家健康100／connected／Simulated、原NPC、房間／攻擊關閉、旋轉盒外位置及活動tick位移上限，中間失效恢復也失敗。保存之間缺少的tick不插補路徑；全20Hz通行另由共用規則／Editor檢查，不當每render或複本封包證據。新5helper SHA前後相同不是完整OS／runtime graph。端點最大收到時來源年齡0.117452秒，不是RTT／FPS或性能基線。前兩場與Quest建置重疊，最終場build已結束；負載不同，不當因果對照。

本機7 navigation＋5 artifacts＋7 first-person＝**19 Python**，含短暫端點先於返回仍被串流觀察、舊來源不可當新鮮、原人物失效／換NPC、NaN／bool、凍結tick移動及缺tick不插補；語法／diff／原player-body pin與293官方transport＋1 scoped patch核對成功。無新GPU／PCM、遊戲按鍵或姿態注入；原0.37.0六張手臂GPU證據保持原範圍。

新Windows包`windows-player-0.37.1.zip` **82,642,694 bytes／SHA cba3a25ba590c21f0b38b152042242b373ea656dce4c1ff434a742490f3b841f**，311 runtime檔／原launcher a65846da...；新C展開navigation-b0e09beb0a734d3f92cccfce3ddacec0、85847 exit0／19真正launcher核對拒絕，非完整封裝GUI／跨機。Quest APK **60,313,650 bytes／SHA723e57b59320b77a0b32523d092a75c6b5fe937325187be1f9fdc484505a980a**，com.vrcommand.quest／0.37.1／46／ARM64／min32 target35、v2 debug簽章成功；receipt建置總量不是APK大小，無實機安裝。建置前321舊binary／logs及10來源精確另存navigation-history-1fc294c6bd3f4748890eb85338834af5，原0.37.0及0.36.1 ZIP保持。

`navigation-prior-validation.json`核對前60 C runtime3083與F snapshot、前F證據3540、舊321＋10與兩個新C build候選／凍結反例來源。`navigation-runtime-validation.json`再核對**新4 C runtime68檔與F snapshot逐檔一致、新F179檔、486份前瀏覽器／CI證據**，總64場3151 runtime檔；原三API組159、accepted mission API及三個舊候選、新accepted navigation API／三工具／Checks都依原hash保持。全部自己的writer停才一次snapshot回F，原件不移動、保存SQLite不開連線。完整CI另補本節。

[功能9959c64](https://github.com/peca12968/vr-command-center/commit/9959c644bc91f93dcb24e87e43539b2fa3e6bf4b)已推送main；[CI41275385420](https://github.com/peca12968/vr-command-center/actions/runs/41275385420)／job124756415659／精確9959c64 **完整success**：Linux restore／build、723規則／459 HTTP／47 world-stream、工作流程Python（新增7 navigation）／素材與72 Node／248 Chromium通過。2 Windows限定skip不當原生、Editor或本機Windows完整HTTP啟動成功；先前startup失敗不改判。

39檔artifact13071202925與log／**9,675,831 bytes ZIP／SHA565bde8df61294a09f141c7dc60332792c92cda2c25762f5f1d39bd18ec141a5**已保存，實際下載與GitHub digest一致。`navigation-ci-validation.json`再核對前486份瀏覽器／CI證據、新runtime68與snapshot、APK／ZIP未變。後續僅文件證據skip ci，測試來源精確9959c64，不重跑冒充另一場。

完整11項active，仍同機Simulation／headsets0。這個可重現的旋轉格邊錯誤與原31筆／world371姿態失效、Windows startup、F吞吐各自不同，後者未修復；多人持續操作、複雜地形、跨機／Wi-Fi／Quest／VIVE／MR與廠商硬體仍待驗。

## 2026-11-01：電腦端第一人稱軍服手臂

從`e8b346a`接續完整11項中的軍事人物介面，新增[DESKTOP_FIRST_PERSON](DESKTOP_FIRST_PERSON.md)。Unity **0.37.0／code45／NGO29**、API/UI0.30.1／rules0.8.0保持；同源Windows與ARM64 Quest fingerprint **09eed85207b33d5304f6aae294a5aebe3237d48eca3f2b0cf9b01679530ed5c8**，原scene／prefab ID一致。Prepare9556、Tests46731、Desktop83079、Quest86239各原handle terminal exit0；**184真正Editor全部通過、0skip**，不是Python或雲端替代。新增5案例保護本機端點／隱藏、Tracked早退、死亡／失聯、切回遠端及保存換彈／Pause。沒有改API、wire、Shared數學或正式5080。

本機桌面owner現在顯示自己的軍服上臂／前臂及既有手套，隱藏自己的軀幹／腿／頭盔；其他玩家仍完整呈現原人物。重用五Mesh／404面與原player-body-v1 pin／lease／PlayerPresentation.Pose，不移動原槍口／pointer／Tracked關節、不新增Collider或改戰鬥規則；Tracked owner計算前隱藏返回。這是裝飾性兩節臂，不當完整追蹤人物、手指／腰腳或動畫完成。原0.5／1.5秒政策保持。

新check-desktop-first-person只開自己隔離API／server／可見client，實際Right／Down、Space、R由computer-use操作；每次action後刷新並經模型觀察，六張原生GPU檢視後另呼叫寫review.done。沒有姿態／輸入注入。**desktop-first-person/20261101-114930-25078562、57292 exit0，4項／6張GPU／1195完整連續回放／5原來源檢查點**；初次checkpoint起全部Running原solo健康100／connected／Simulated／非suspended，無瞬間參戰失效。paused兩張端點delta0、head／右手套握點對來源最大差5.382805623455056e-08m，左腕隨保存換彈tick移動。彈匣30／備彈89、1發0中0殺健康100，原admission最終結果、CSV、精確combat／world seal及唯一server ACK一致。probe明確finish先於End、兩層cleanup乾淨才complete；五helper hash不是完整依賴graph。

實際畫面可見左右袖，自己的頭盔／軀幹沒有擋住相機；槍仍會遮住部分手臂，沒有每角度完整可見或動畫品質宣稱。Quest建置與此功能場重疊、視窗尺寸隨焦點改變，不能作乾淨效能基線、像素benchmark或因果控制。NativePlayerBodyProbe保持明確Windows Development／visible untracked／600秒／8圖／900萬像素、無PCM／輸入；新增獨立firstPerson，遠端players[]及walking就緒語意不變。

舊人物工具第一次`desktop-venue/20261101-115513-5ef0869d`，72822 exit1：原300秒observer定位期限已到、target尚未啟動，沒有observer.done，cleanup乾淨；CUA視窗已關時停止輸入並重觀察，原失敗保留。第二次`20261101-120615-644b0391`，30210 exit0／4項／6圖，原工具與300秒不變；實際組合鍵定位再W／Space／R，遠端walking非零、paused端點差2.384185791015625e-07m。前景槍／袖及Pause文字遮住部分遠端身體，沒有全像素可見宣稱。原工具只有最終replay／seal統計，不冒充新增全程連續性或全員ACK。

Host場`desktop-debrief/20261101-121759-e60ee300`真正terminal exit0／4項：兩份原結果符合seal、移除admission不收結果、Host等peer ACK才shutdown。五房場`desktop-venue/20261101-121914-2748af54`已停止、stage passed／**6項／7場**、cleanup errors／remaining空：五房各1人隔離／錯票拒絕、房1環境與AI／Pause不干擾四房、重用席位及後續Linked、七個不同stream精確seal成功。**五房原shell回應在輸出裁切中遺失，不補造exit0**；依原stage／summary／cleanup及停止程序描述結果，不當25位同時操作。

本機7 first-person＋5 artifacts＋27 active＋12 debrief＝**51 Python通過**；包含私有owner／Tracked／遠端分類、錯phase／tick／rig、端點錯誤、NaN／bool、cleanup IO反例及中途失效恢復仍失敗。語法／diff、原player-body幾何pin及293官方transport檔／1 scoped patch核對成功。CI已加入新suite，完整雲端結果待另錄，不能把本機51當完整.NET／瀏覽器結果。

Quest實際APK **60,313,726 bytes／SHA067c41347a284e05fb5d8695277e0907052a984050c2220313dd23a21bce6e94**，包名com.vrcommand.quest、0.37.0／45、ARM64、min32／target35；receipt totalBytes1050650189是建置摘要、不是APK大小。首次apksigner.bat因JAVA_HOME缺失失敗log保留，之後明確Unity Java執行jar、v2驗證成功（Android Debug certificate），沒有改系統環境或宣稱商店／實機驗收。

新`windows-20261101-120352-b2b5c1c3.zip` **82,642,471 bytes／SHA08aa93385e4e2b2688714fee56ce6d9dfe6592574d8e7e844e15020e815ae030**，311 runtime／manifest、原launcher source a65846da...；新C展開`first-person-2de5107449ec4491b9401a514db4a699`，64171 exit0／19真正launcher核對與拒絕。不是完整封裝GUI／跨機或安全性提示操作驗收；manifest不是簽章。建置前321舊binary／logs及9來源精確另存first-person-history-eb3833ea49864c95930e651b70cada11，原兩ZIP保持。

`first-person-runtime-validation.json`在各場停止與cleanup核對後完成：**新5 C runtime102檔／F snapshot逐檔一致、新F證據221檔；前55 C runtime2981檔與各snapshot保持，合計60場3083檔**。原動態／observer／operator／尾界／獨立房歷史與三組API159、accepted mission API及拒絕候選、舊ZIP與archive321＋9、前CI39檔均核對原hash；保存SQLite只raw bytes、沒有開連線。新場五房shell exit未知另列，不把hash一致或stage成功補成原handle exit證據。

[功能81108e1](https://github.com/peca12968/vr-command-center/commit/81108e1c46a934dc4f90ba59d03a41dadffb3db9)已推送main；[CI41273127773](https://github.com/peca12968/vr-command-center/actions/runs/41273127773)／job124749808406／精確81108e1 **完整success**：Linux restore／build、717規則／459 HTTP／47 world-stream、工作流程Python（含新7 first-person）／素材與72 Node／248 Chromium成功。2 Windows限定skip不當原生或重跑Editor；雲端成功不改判前輪Windows完整HTTP啟動逾時。

保存39檔artifact13069804420、log與**9,710,227 bytes ZIP／SHA84d3f956d75fbd71e4ec680f03dc809b43266e9f3b924ad3d81a7a4fd787dec0**，實際下載與GitHub digest一致。`first-person-ci-validation.json`另核對新runtime102檔與snapshot未變；`first-person-browser-history-validation.json`依既有manifest核對447份前CI／本機瀏覽器檔，包含較早三個console快照及前輪讀取失敗／成功資料，範圍較前313份更廣、不是新增遊戲測試。後續只有文件證據使用skip ci，測試來源精確81108e1。

完整11項active；無頭盔、同機Simulation，原31筆／較新world371、Windows完整HTTP startup與F吞吐各自未修復。下一步仍包括多人持續操作、完整人物動畫／追蹤、跨機／Wi-Fi／Quest／VIVE／MR與廠商硬體，不重寫舊失敗。

## 2026-11-01：任務版本讀取不再被背景刷新失敗取消

上一輪屬實際進展，從乾淨`ada9eee`接續完整11項目標的第8項。[MISSION_READ_RECOVERY](MISSION_READ_RECOVERY.md)更新API／UI **0.30.1**，任務／世界格式、rules0.8.0、NGO29、Unity0.36.1／code44／e0594513...與原scene／prefab ID／179真正Editor及雙平台receipt保持。本輪沒有Unity／APK／launcher重建，正式5080不動；新.NET輸出在C的新BuildRuns，F來源及既有C copies／Windows／Quest原件不覆寫。

舊`run`等待共用refreshPromise，一旦列表刷新失敗便在action前退出。先用真正隔離API0.30.0／Chromium重現：handle46558 terminal exit1，受控catalog503後第一版已選、草稿仍第二版，未發出所選history GET，30秒DOM等待失敗。這是新受控證據，不是原c71 CI歷史載入逾時的根因證明。

只有載入最新版／選定版本／歷史分頁三個明確GET入口選用independentRead：等正在進行的刷新後，原epoch／actor且非HTTP狀態錯誤或5xx可以繼續重新讀history／version；成功仍警告背景列表未更新。401／403／其他4xx不恢復，登出／epoch變更取消尚未發出的讀取。版本本身503保留舊草稿，不取快取或別版。建立／修訂、場次命令、名冊、pending、原UUID／expectedSequence及認證權限保持。三個原生工具API gate同步0.30.1，沒有修改姿態、武器或錄影政策。

新專項handle兩次均exit0：先10項、擴充15項（含原shell2項／情境13項）；真API22個不可變版本、20＋2分頁，受控503／transport／403／401、選定history503、寫入零發出、登出不恢復及警告皆通過。focused檢查有自己的scope，不能當完整回歸。最多256筆方法／path metadata，截斷不得成功，不記headers／key／payload；新目錄拒絕覆蓋。

本機完整handle51663 terminal exit1：72 Node成功，後在原weather night複合斷言失敗，未到新讀取情境。保留weather-first-rain（tick20／sun0.08／非flash）及原畫面／log，該複合斷言沒有同時保存三個條件，不能證明唯一原因。fixture改為排除child啟動前已有session、只取新來源，並在單次JS觀察中同時確認選中錄影／rain128／nonflash／sun0.08／非原始音軌提示，保存night DTO及descriptor；原斷言與時間／天氣政策不放寬。最終handle98198 terminal exit0：**72 Node／248完整Chromium**成功（原235＋新13），39個畫面／資料檔。API／WorldRelay／Checks均指向同次C建置，不混root舊輸出；未將軟體WebGL當原生GPU。

`.NET restore --locked-mode`／build成功、0警告0錯誤，717規則與47 world streaming（handle24781 exit0）成功；5 artifacts＋27 active＋13 capacity＝45 Python、三個工具py_compile／兩個CJS syntax及diff-check成功。**本機完整HTTP沒有通過**：handle93770及49590在invalid credential子程序10秒退出等待逾時，未放寬期限。各自finally停止自己的Popen，後續同build程序清查沒有殘留。

為辨識啟動現象，自己的weak-key API在5秒觀察仍live、log已有Unhandled InvalidOperationException，原handle明確停止／terminal。曾做兩個未發布候選：捕捉後return＋exitCode仍live，explicitExit單次0.921秒exit1，但完整HTTP handle99746在第二個invalid credential仍10秒逾時，另有temp server.log清理Win32共享拒絕。這不足以證明整體修復，**已撤回兩種auth候選**，候選原C build／Program快照／probe及失敗log保留；不刪除殘件、不改ACL／Windows設定。最終Program的SHA與第一0.30.1候選精確相同，原憑證拒絕實作保持，不能稱Windows startup／本機459 HTTP成功或猜WER／防毒／檔案系統根因。

真正遊戲回歸handle37885 terminal exit0，`unity-admission/20261101-110701-fe372a4b` **8項／355幀**，驗票／撤銷／重連、接受來源與精確seal／cleanup成功；沒有輸入／姿態注入、沒有新trace。這是最終採用的第一API候選及原遊戲binary，同機Simulation／非互動／headsets0，不是實際Reconnect按鈕或25台證據。

`mission-read-runtime-validation.json`在全部自有handle terminal後只讀raw：新C runtime14檔／一次F snapshot一致、新F43檔；前54 C runtime2967／各F snapshot與前observer F264、UI1042／動態1138／operator383／F337／history321、原尾界及獨立房、API原三組各159、當前ZIP／APK／receipt及舊ZIP保持。總55 C runtime2981檔。三個.NET候選各API＋三工具159檔與Checks95檔均另存雜湊，只有第一候選採用；五個新瀏覽器目錄3／2／2／19／39共65檔，前失敗／成功不覆寫。Startup三份關閉raw log及HTTP temp殘留log已逐byte另存F並核對hash；暫存清理曾部分失敗，不宣稱保留完整HTTP temp，原殘件不刪／不解鎖。保存SQLite不開連線，native writer全停才snapshot。

採用建置的明確本機指標為`artifacts/mission-read-api-stage-path.txt`及`mission-read-api-stage-validation.json`（0.30.1／API132＋三工具各9＝159檔），指向第一候選的bin；名稱帶final／release的兩個候選**不採用**，原指標及原件仍保存，不能只憑名稱選部署來源。

[CI41268781091](https://github.com/peca12968/vr-command-center/actions/runs/41268781091)／job124737033873／精確`2c33d1d9adec23da4dfe457711836a4037f942c7` **完整success**：Linux restore／build、717規則／459 HTTP／47 world、工作流程Python／素材及72 Node／248 Chromium通過。2 Windows限定案例在Linux skip，不當原生或179 Editor證據。本機Windows完整HTTP仍失敗，不能用此Linux結果改判。保存39檔artifact13068238061與log，ZIP9677130 bytes、實際下載SHA256 `622a0b211f2c3c7f1243945b4f6fa7ba47ce980e7a3e4dd45328202c1ff567a8`與GitHub digest一致；`mission-read-ci-validation.json`核對前209＋本輪65＝274份瀏覽器證據、新native及三個候選build均保持。最後只有文件證據skip ci，測試來源精確2c33d1d。

完整11項active，原31筆／world371、Windows startup與原CI時序問題、F吞吐及跨機／Quest／VIVE／MR／廠商硬體仍各自待驗；本輪不把受控修正當所有歷史逾時修復。

## 2026-11-01：25端零按鍵視窗觀察與同場心跳對照

從乾淨`7bc82a1`接續，詳見[OBSERVER_TIMING](OBSERVER_TIMING.md)。API/UI0.30、Unity0.36.1／code44／NGO29、e0594513140ff7fb4bc084929691b91c15f7d908e8f59c114aa5ab27daaf11eb、原scene／prefab／rules0.8.0保持；本輪Python／文件，沒有Unity、APK、launcher或產品.NET重建，也沒有重跑原179 Editor。正式5080與原雙平台receipt保持。

新增`--observer-sequence`：自己的25個原生client＋server、0位操作／25接收、一個可見；不用W／Space／R或管理環境／AI命令，`--operator-ui`僅閒置控制台零表單。固定A3／S3／A3／S3共12次呼叫，原PID／player／session／同視窗及外部caller UTC＋單調時間，8秒baseline／120秒窗口／8秒quiet有界；metadata64KiB不保存image／可及性內容／憑證。先觀察再獨立ack、失敗abort，選窗在量測外。自己的normal-priority心跳沿用原240秒上限，server＋visible稀疏／server loop、replication原上限及0.5／1.5秒政策保持；timer加入tracked children，明確finish及所有writer全停才一次snapshot，例外也收native程序。

真正場`20261101-102507-8f94afad`／原handle8001 **terminal exit0**：8項／52快照／26 Requested完整報告、28237 Running列無失效，1153完整回放／2參考，25份原admission結果／CSV與精確雙seal及server25唯一ACK成功。world1153／combat0／ledger through31，25位健康100、零彈藥／命中／擊殺／損傷；閒置UI110.018秒零requests／attempts，native／UI／pose／timer cleanup皆乾淨，headsets0／hosts1／networkCapacityAccepted=false。

唯讀`observer-analysis-20261101-102507.json`對12次caller窗口都具有native／獨立timer coverage；原visible connection25／source1的PoseSend、PoseReceive／Accepted與MainThreadGap、timer>100ms記錄皆無重疊。timer88.7660042秒、最大wake10.7578ms、clock step0.0004636秒；caller最大0.0009828秒。Accessibility33.2628–78.5295ms／Screenshot96.5465–161.07ms是**含SDK queue、helper及結果返回的外部括號，非GPU／CPU／FPS／RTT**。Screenshot可能delta region、不當全frame像素量測；小樣本固定順序、零記錄大gap不證因果、不排除觀察擾動／小間隔，也不能配前場world371或舊31筆。

分析器校驗原visible／connection、closed cleanup及報告來源，UTC差>=0.05秒／不同主機／不足coverage返回null；同point裁切聯集、不同point與MainThreadGap／PlayerLoop不相加，CPU保留整個原Update sample括號、不比例切分或歸因。沒有world序號不能硬配。只讀關閉JSON，不開保存SQLite，輸出新檔且不得落原場／原runtime、不覆蓋raw；complete僅join資料完整、missionAcceptancePassed另列、rootCauseProven=false。

live之後補上stationary sample及全回放閘門：名冊、head／muzzle／forward／彈藥／reload／fireSequence不變，短暫移動恢復也失敗，connected／rig另由原參戰規則處理。**原8項沒有冒充新增live第9項**。`observer-closed-stationary-validation.json`第一版把REST float短格式與raw double展開直接比較，983幀誤報，例(-31,1.65,-3)與raw y=1.649999976158142；原失敗檔保留。`...-v2.json`以同一raw序號122作baseline、rb／checksum／連續序號讀完122–1104共983幀全相同，並另核對原journal1153精確seal，沒有改遊戲容差／原runtime或宣稱另一次live。

本機9 observer sequence＋6 analysis＋27 active＋7 heartbeat＋16 input analysis＝**65 Python通過**，含順序／錯場／錯window／clock step／host未知、缺coverage為null、交錯玩家／source不混流、同point union、完整CPU sample不縮放、暫時移動恢復仍失敗及timer報告IO失敗仍cleanup。py_compile／diff-check通過，CI新增兩個suite及新腳本compile。

首CI`41266207153`／job124729421211／精確c71a71d在mission-browser原第60行逾時，沒有完整通過；717規則／459 HTTP／47 world、Python／素材及72 Node成功，但歷史第一版已選取、草稿仍第四版、notice為更新失敗。保存4檔artifact13067331462（ZIP823374 bytes／SHA aab97eb4e5e61e2848138fcde58c7667a57a674687891faba7c3827dea2599d2）與log，前131份CI／本機證據保持；沒有當時request明細，不能證明路由／產品／主機根因。之後本機handle21473 terminal exit1：72 Node成功，原隔離API啟動期限內未就緒且log空，未開始browser checks；新目錄空白保存，原因未知，不當瀏覽器通過。

`8e335d6`僅補fixture失敗診斷：最多128筆GET path／status／完成／時間／failure，不存headers／憑證／body／response payload；啟動失敗保存原attempt／elapsed／exit／signal及既有有界log並遮罩臨時key，terminal包含signalCode。可明確選新的直屬artifacts/console-*目錄，拒絕既有以保留原console資料。本輪未改console產品JS／API、路由情境、斷言或8秒API／30秒DOM／啟動界線，這不是歷史任務載入問題的修復宣稱；兩個CJS syntax及diff-check通過。API8秒計時是瀏覽器GET／管理呼叫，不是原生15秒來源入場政策。

同`8e335d61e428dc37b6627918637bcc187142750d`本機handle46147 **terminal exit0、235 Chromium全部通過**，包含原歷史版本載入情境；37份原畫面／checks另存`console-observer-diagnostic-20261101`，先前空白啟動失敗目錄不動。前一handle21473的72 Node通過另計，不把未進browser的場稱完整成功。

[最終CI41266688006](https://github.com/peca12968/vr-command-center/actions/runs/41266688006)／job124730838741／精確8e335d6 **完整success**：Linux restore／build、717規則／459 HTTP／47 world-stream、工作流程Python（含9 observer／6 analysis）／素材、72 Node／235 Chromium均通過。2 Windows限定案例在Linux skip，不當原生Windows／179 Editor證據。保存37檔artifact13068160426、9464113 bytes ZIP，實際下載SHA256 `c0eb7fe41cf25e7fbe41ad386fed18c967ff734c67d175bd36c08bb8c39bb25c`與GitHub digest一致；另存log與`observer-ci-success-validation.json`，前CI／本機131＋本輪失敗4＋新本機37＝172檔保持。**這是增加診斷後的成功場，不是修復或證明原c71a71d歷史載入逾時／21473啟動失敗根因**；原生姿態反例也不因此變更。最後只有文件證據skip ci，測試來源精確8e335d6。

`observer-runtime-validation.json`：新C runtime176檔與一次F snapshot逐檔SHA一致、新F264檔；前53 C runtime2791檔／各F snapshot及前UI1042／operator383／動態1138／F337、原尾界失敗／獨立房／history321、API三組各159及當前ZIP／APK／receipt與舊ZIP保持。總54 C runtime2967檔；全部原handle terminal才稽核，保存SQLite只raw bytes不開連線。新分析與兩版stationary輸出在原場之外，原成功與失敗檔均不重寫。

完整11項active；下一步仍追查自然姿態空窗並接續多人持續操作。此輪沒有重現不等於修復舊31筆或前場371，沒有完成25人同時操作、跨機／Wi-Fi／Quest／VIVE／MR或廠商硬體驗收。

## 2026-11-01：控制台表單接入25端動態任務，保留新參戰反例

上一輪為實際進展，從乾淨`00d91a5`接續[動態PC](DESKTOP_ACTIVE.md)。**API/UI0.30、Unity0.36.1／code44／NGO29、e0594513140ff7fb4bc084929691b91c15f7d908e8f59c114aa5ab27daaf11eb、原scene／prefab／rules0.8.0保持**；本輪Python／Node驗收與文件，沒有新Unity／APK／launcher或產品.NET建置、沒有重跑原179 Editor；沿用原同源雙平台receipt，正式5080不動。

新增`--operator-ui`，將原三組環境／AI命令改成真正Chromium控制台表單的reload／fill／submit，使用自己隔離API／臨時Master，選定原五房Linked場，保存真正HTTP POST body、status與CommandReceipt；只有GET用於額外讀回，不以直接管理POST代替這六個動作。Python仍核對原request／session、先環境再AI、精確設定／expectedSequence／原UUID／非duplicate／接受尾界及來源Running／observed fence。409最多三個明確意圖、拒絕後才能refresh新提交；200即止、未知結果／5xx不重做。Begin／Pause／Resume／End仍由fixture處理，**不是本輪全生命週期的UI驗收或autoAttack傷害測試**。

助手僅本庫新desktop-active目錄、Simulation／headsets0、canonical127.0.0.1 HTTP非5080，server header必須原session的五房Simulation；不接受任意正式／遠端API或拿頭盔分類當在線。單調180秒／最多3組／每表單3意圖有界，finish輪詢先關browser並等helper terminal；report.complete只助手範圍。Python即使UI shutdown／報告IO例外仍須獨立native cleanup。原40秒UI確認、replication240秒／4096列與0.5秒姿態／1.5秒來源政策保持，沒有改Tracked、槍口、wire或戰鬥規則。

| 真正場／原handle | 結果與範圍 |
|---|---|
| `desktop-active/20261101-093809-9f82680e`，47587 exit1 | 六UI命令、182快照／26完整report、25份精確結果／CSV／雙seal與server ack成功；前13項成功，但最後全程連續性失敗。1271完整回放／11參考中，world371／tick566只有可見玩家參戰失效；26份report各觀察到同tick connected24／health2500／ready及coherent=true。26010 Running觀察列、26 bad列；原active-result.complete／continuityPassed=false、無summary接受檔。沒有當場姿態trace，原因未知 |
| `20261101-094604-d61ce911`，63574 exit1 | 新API health啟動30秒逾時，api.log空；尚未建立遊戲／UI／診斷程序。沒有調寬門檻／重用該場，cleanup空，原因未知 |
| `20261101-094719-ababcf4b`，93035 exit1 | 第一發done在同一orchestration呼叫中先於模型檢視新畫面寫入，不合確認順序；另存operator-observation-issue.json acceptancePassed=false。之後未送R，actual UI reload40秒逾時，沒有補ack／結果接受檔。兩份稀疏報告仍明確finish，UI／native cleanup乾淨；不可當完整操作成功 |
| `20261101-095005-60959386`，26798 exit0 | 正確分開觀察與ack，**14項／182快照／26 Requested完整report、21121 Running列無失效**，1132連續回放／11參考與25份精確結果／CSV／雙seal／server25唯一ack成功；UI與兩份稀疏診斷明確finish、cleanup無殘留。只代表本場 |

第一失效場的closed worldlog已逐record checksum／序號核對；367–370與372–375可見玩家connected=true／rig Simulated，只有371 connected=false／rig None，健康100保持、名冊25。370→371保存capture相隔112ms，371→372為293ms；這不是失效持續時間／RTT或pose收發間隔。當時保存狀態仍Clear／Hold、observed28／非suspended，尚未在該幀觀察到第一組UI接受31／32套用；**不能從此推定接受時間、Begin序號或UI／天氣／GPU／傳輸根因**。每client仍一個原native連線，參戰body狀態不當新的transport重連。恢復、最終戰績或最後乾淨場均不能抹除這一幀；原31筆失效也未修復。

原候選工具與依賴共10檔（含working.patch、無憑證）先精確封存於`active-ui-candidate-a5f5b675638b4ea984d3fcc1fb3311cd`並hash；之後補嚴格UI意圖順序／單調期限／時間metadata、助手cleanup例外仍必須native cleanup的反例，以及明確`--diagnose-visible-pose`。這份10檔不是完整OS／binary依賴graph。新診斷只有server＋visible client，server才PlayerLoop，不擴大舊收集器界線或當零擾動。

程序不合格場的兩份稀疏報告complete／clockJoinValid，client最大PoseSend gap0.5342256秒、server的pose streams最大gap0.5370066秒；關閉journal在初次capture後未找到可見玩家的保存Running connected／rig失效。`active-ui-pose-window-analysis.json`因此沒有可配對的fault窗口，missionAcceptancePassed仍false。**不把最大gap當另一個已保存失效、不能跨場套到原371、不能以本次時鐘檢查校準原無trace場次**。point沒有world序號，不硬配，clock／coverage不足須null。

最終場三組接受31／32、44／45、48／49，Running來源分別world374 observed32 tick466、world1013 observed45 tick1528、world1077 observed49 tick1562。Patrol與Advance只要求命令前基準至少20活動tick後的實際活敵移動；原五敵ID／room／health保持，四個活敵各約0.2m／1.7m，原room3死敵不復活。不是固定速度或精確套用延遲。每檢查點仍逐一比對25端＋server的環境／AI來源、身分、姿態、彈藥／健康與敵軍position／fireSequence；不將其當所有render frame或所有封包。

最終一位實際W／Space／R／Space、24接收端，2發2中1殺／100%，其餘24未受其輸入改動，所有玩家健康100。world1132／combat5／ledger through52的25份原admission結果精確一致；全部server ack對原nativeConnectionId，無timeout／queue error。replication最晚117.630233秒／最多857列，最大相鄰觀察Running tick gap0.1340429秒，非RTT／FPS。client probe End前停、server seal後停，UI助手3組／6次200／無page error、105.863859秒 Requested clean shutdown，才另行核對個別結果。

最終稀疏server／visible client各於118.354362／109.312755秒明確stop，clockJoinValid、最大檢查偏差0.0019386／0.00165秒，未截斷。client gaps0但threadWindows1；不能由稀疏列空集合宣稱全程無主執行緒空窗。報告在25份結果與精確seal後停止，diag complete不是任務接受。Windows雨夜／換彈／擊殺／暫停畫面已觀察；沒有新GPU／PCM量測或頭盔證據，CUA截圖payload未另解碼／保存。

**27 active＋13 capacity＋12 debrief，共52本機Python與72 Node通過**；新增6 Python／5 Node涵蓋外場／錯request、錯表單／尾界／UUID、未知結果、成功後多送／錯意圖序號、單獨server／visible的診斷opt-in及UI cleanup錯誤仍收原生程序。一般235瀏覽器套件本輪由後續CI驗證，不混用前輪本機結果；語法與diff成功，CI既有入口已包括新案例。

原生場後僅補UI cleanup例外／中斷仍在finally執行native cleanup，以及同session world header的顯式核對；27 active／5新Node反例重新成功，保存summary的原world header與UI config session讀回精確相同，沒有改遊戲或重跑整場假裝新的原生證據。[功能4102850](https://github.com/peca12968/vr-command-center/commit/4102850e9c35959cfcd36872f7e1d80f3753333f)的[CI41263637499](https://github.com/peca12968/vr-command-center/actions/runs/41263637499)／job124721781630**真正完整success**：Linux restore／build、717規則／459 HTTP／47 world-stream、工作流程Python／語法／素材及72 Node／235 Chromium通過。兩個Windows限定案例按平台skip，不能當雲端原生或重跑179 Editor的證據。這不改首場原生exit1／新371失效與原31筆狀態。

37檔artifact13066661666、9464550 bytes，ZIP SHA256 `d3748ab2048df8eda10d1b6ee5fc0f07be26e2545e5ab893fe58da7fe5e99690`，下載與log原handle5737 exit0，保存新`ci-41263637499-*`；`active-ui-ci-validation.json`核對成功37檔、前CI37／本機console42／兩失敗CI13＋2共94檔仍相同，log另存SHA。完整CI不是Windows／25人容量驗收；後續僅文件證據提交使用skip ci，測試來源精確為4102850。

`active-ui-closed-analysis.json`／`active-ui-runtime-validation.json`在四個原handle terminal後只讀關閉JSON／journal rb與checksum，保存SQLite不開連線、不ack／修復／截尾；metadata讀回不是完整raw規則重跑。新4 C runtime764檔／F snapshot相符，前49 runtime2027、前F337／四動態1138／前operator383／原尾界及獨立房證據、history321與各API159、當前ZIP／APK／receipt及舊0.36 ZIP保持；總53 C runtime2791檔，新場F1042檔另存hash。所有writer全停才一次snapshot、C原件不動，失敗也保存。

完整11項active。仍同機Simulation／一位操作24接收／headsets0／networkCapacityAccepted=false，不是25位同時操作、跨機／Wi-Fi或頭盔容量；診斷前後條件不同，不當因果對照。下一步以原失效樣本及獨立觀察／可見玩家診斷追查自然姿態空窗，並接續多人操作；原31筆／新371、F吞吐、MR／VIVE／跨機25台及廠商硬體各自待驗。

## 2026-11-01：25端動態任務中的環境與AI管理命令

上一輪為實際進展，從乾淨`cf3c8b4`接續；新增[動態PC選用流程](DESKTOP_ACTIVE.md)。**API/UI0.30、Unity0.36.1／code44／NGO29、e0594513140ff7fb4bc084929691b91c15f7d908e8f59c114aa5ab27daaf11eb與原scene／prefab ID、rules0.8.0保持**，只有Python驗收及文件修改，沒有新Unity／APK／launcher、179 Editor或本機.NET建置。既有雙平台receipt保持；正式5080不動。

舊動態工具只驗Clear／Day／Hold，本輪新增明確`--operator-controls`，在實際W後、Space／R／Space前切Storm／Night／lightning／Hold，擊殺後切Storm／Patrol及Fog／Day／Advance；全程autoAttack=false以保留原動作隔離與健康基線。管理命令走正常API，玩家鍵盤走computer-use，沒有REST／RPC／UDP注入姿態、命中、座標或統計；**這輪沒有重跑操作員瀏覽器UI或自動攻擊傷害**，相關舊證據仍分開。

原生場`desktop-active/20261101-085537-4eed0a0f`，**原handle33469真正exit0、13項成功、cleanup errors／remaining皆空**。一個server＋25個Windows native client，仍一位實際操作、24個無圖形接收端；source／binary在F，runtime明確C SSD、headsets0／hosts1／all25SimultaneouslyActive及networkCapacityAccepted=false。

| 管理命令組 | 保存接受序號 | 第一個符合條件的來源幀／observed／tick | 真正策略移動 |
|---|---|---|---|
| Storm／Night／lightning／Hold，射擊前 | 31、32 | world391／32／483 | 不要求移動，保留原射線目標 |
| Storm／Night／lightning／Patrol，擊殺後 | 44、45 | world1249／45／2043 | 原四個活敵各移動約1.300001m |
| Fog／Day／無閃電／Advance | 48、49 | world1305／49／2075 | 原四個活敵各移動約0.699999m |

兩份CommandReceipt先保存後輪詢，拒絕外場／duplicate／非遞增；來源必須非suspended、Running、tick前進、observed>=接受序號，且天氣／日夜／閃電／visibility／behavior／autoAttack相符。Patrol／Advance另外從命令前來源基準前進至少20 tick，原五敵ID／room／health完全保持，包括原room3死亡目標不復活；只算仍活敵的移動，不由死敵、重生或目前名冊猜測套用。`active-operator-controls.json`保存原回應及來源witness，逾時保留applied:null；這是輪詢首次符合條件的觀察，不是精確命令套用時間／RTT。

七個檢查點（initial／四動作／Patrol／Advance）共**182快照／26 Requested完整報告、28204觀察Running列**無失效。每個快照核對來源packet實際環境與25原連線／全名冊／姿態／彈藥／健康、敵軍位置與fireSequence。最晚145.318062秒finish、最多1134列，原240秒／4096列界線保持。相鄰觀察Running新tick最大間隔0.5542095秒，非RTT／FPS／精確PoseSend間隔；原0.5秒姿態與1.5秒世界政策未改，不能由此數值推根因或宣稱連續畫面。

原handle terminal且cleanup明確空列後，`active-operator-checkpoint-validation.json`另外只讀原JSON／快照，將七段直接對到命令指定環境與原接受fence：initial world120／move342為Clear Day；shot683／reload928／kill1194仍Storm Night Hold且observed35／37／42>=32；Patrol world1254 observed46>=45、Advance1310 observed50>=49。各段26個原client／server快照全部相符，其他身分／姿態／戰鬥閘門仍執行。最初Begin無保存接受回應，這份讀回的initial／move minimumAcceptedFence=null，不猜序號；complete只表示這次182快照讀回，不當新原生run、全量世界規則重算或連續渲染。

實際W短移動、雨夜第一發命中／R後30彈匣89備彈／第二發擊殺成功；主玩家2發2中1殺／100%，中彈與損耗0、健康100；其餘24位未受其輸入改動。25份原admission個別結果／CSV與combat及world精確雙seal一致，**world1359／combat5／ledger through52**，server25唯一ack集合精確對到原nativeConnectionId、沒有timeout／queue error。原probe先finish／server seal後finish、結果確認後才停程序的順序保持。

End後完整API回放**1359連續幀／12參考**精確一致，參考區間每張保存Running世界幀與所有觀察Running列均無參戰失效；這是保存及觀察到的樣本，非25位同時操作或任意負載證明。源環境與接收端為離散檢查點，不把管理接受當連續渲染證明。computer-use兩次get_window_state回報active request：第一次等待後重新取得雨夜畫面才射擊；後一次重試回報foreground未有PID、當時進入結果／收尾階段，沒有再輸入或推定原因，**沒有霧天人工GPU畫面證據**。未保存／解碼CUA截圖payload。

新增4 active＋2 capacity反例，含舊observed／Paused／suspended／未前進tick、正確fence但錯天氣／visibility／策略／autoAttack、死敵或靜止不能當移動、換敵／重生／換房／非有限移動、明確環境不放寬舊預設與未知枚舉／非bool拒絕。**21 active＋13 capacity＋12 debrief，共46本機Python通過**，語法及diff成功；既有CI入口涵蓋新案例。

功能[b014f1a](https://github.com/peca12968/vr-command-center/commit/b014f1a9378a65d4a176fd04d6105fdfeeee6f6b)的[CI41259359885](https://github.com/peca12968/vr-command-center/actions/runs/41259359885)／job124709212647真正執行.NET／717／459／47、Python／素材與67 Node，但最後瀏覽器在`world-browser.cjs:84`等待新登入分頁的camera-positions option 30秒逾時，exit1；這次在舊截圖步驟前失敗，不能稱前輪bringToFront已證明根因修復或整套通過。Chromium安裝步驟01:03:47–01:09:31Z仍正常完成，沒有因等待而重啟工作。原log與artifact13065165755（3517165 bytes、ZIP SHA256 `d40f412408a19ce8cf4693039fd6d7447adbbda3c5d67814fca4966761f7ef54`）下載新`ci-41259359885-console`保留。

瀏覽器fixture進一步在主觀戰及新登入分頁開始載入前明確bringToFront；行動房控分頁在原所有斷言／截圖完成後關閉其context，不讓已測完的viewer繼續占用renderer。沒有改正式UI／API、提高30秒等待或跳過原斷言；camera及clock仍用各自60秒來源。若新登入鏡頭載入再失敗，另外保存該分頁visibility／world及camera message／option count／world sequence與最多5秒失敗截圖，再重拋原錯誤；不記憑證／headers。這是fixture目標與生命週期修正，尚不當作已證明Chromium／CPU／網路根因。

該修正[e12a52a](https://github.com/peca12968/vr-command-center/commit/e12a52a4644ab3809a7ac4217344104e1a861865)本機原handle67605真正exit0，**67 Node／235 Chromium成功**、相機還原畫面已檢視。`operator-browser-evidence-validation.json`核對原console42檔先完整封存、現console42檔及b014失敗CI13檔／log另存hash，前原生runtime／證據不動。但[CI41260301809](https://github.com/peca12968/vr-command-center/actions/runs/41260301809)／job124712001366又真正exit1：.NET717／459／47、Python／素材與67 Node過，瀏覽器更早在`mission-browser.cjs:54`歷史版本草稿名稱等待30秒逾時，尚未到世界觀戰，不能稱相機修正已在這輪雲端驗過。原artifact13064888401為2 PNG、592388 bytes，ZIP SHA256 `e5debca0aff2da793649995aa8572e8cf509814d0de2ec6c4c8748bc062fd750`，與log保存在新`ci-41260301809-*`。

任務fixture原跨主頁／editor後未明確切回，DOM狀態又以`waitForFunction`預設動畫幀輪詢。[Playwright官方文件](https://playwright.dev/docs/api/class-page#page-wait-for-function)說明預設raf與明確毫秒輪詢的差異；新版本僅將該任務DOM等待統一為polling100，啟用editor及結束後主頁，原30秒逾時與所有版本／保存／衝突斷言保持。失敗時在關editor之前另存visibility／草稿名稱／版本選擇／history／notice及最多5秒截圖，仍重拋。這消除測試對動畫幀排程的不必要依賴，但舊CI沒有editor狀態，**尚未證明逾時時DOM已正確、背景RAF停住或產品無缺陷**；不能以推測宣稱根因／修復。修正的本機完整與雲端結果另記。

最終[a1556bf](https://github.com/peca12968/vr-command-center/commit/a1556bfc2b0575ead0810a4c71d7f1ef6841e25f)本機原handle98816真正exit0，**67 Node／235 Chromium再次完整成功**，不是只重跑任務小段。`mission-browser-evidence-validation.json`核對前42 console檔已完整封存（與前manifest逐檔相同）、目前42檔及e12失敗CI的2 PNG／log另存hash，原b014失敗CI13檔保持。以上Node互通檢查有自己的C# fixture，不是新產品API／三工具或Unity建置；既有同版產品DLL與receipt保持。

最終同[a1556bf來源CI41260889785](https://github.com/peca12968/vr-command-center/actions/runs/41260889785)／job124713745724**完整success**。Linux restore／build、717規則／459 HTTP／47 world-stream、工作流程Python／語法／素材及67 Node／235 Chromium成功；process timing與desktop artifacts各一個Windows限定案例按平台skip，不能當雲端真正Windows探針證據，本輪原生證據仍為本機33469。37檔artifact13064982961、9460116 bytes，ZIP SHA256 `19d0573e4bd5afbc6cd635b684c7ba4026915941293643e63fc3a549b30ee5be`；下載／log原handle79468 exit0，保存新`ci-41260889785-*`。`operator-ci-success-validation.json`核對成功37檔、前本機42＋兩失敗CI13／2共57檔完整，完整log另存SHA。這證明本輪修正來源的整套回歸成功，不證明舊逾時的唯一根因；兩次失敗與既有8d成功歷史都保持。後續僅文件證據提交使用skip ci，不把文件SHA當新測試來源。

`active-operator-runtime-validation.json`在原33469 terminal後核對新C runtime300檔／F snapshot完全一致，前48 runtime1727檔／前F337、前四動態F1138、原尾界反例與獨立房F證據、history321及各API159保持。總49 C runtime2027檔，新場F383檔另存hash；當前ZIP／APK／receipt metadata保持。所有writer全停才一次snapshot，C原件不動，保存SQLite只rb雜湊、不開連線／ack修復／截尾。完整11項active，原31筆／F發布吞吐、頭盔／MR／VIVE／跨機25台與廠商硬體仍各自待驗。

## 2026-11-01：同版動態PC與25份最終結果／server ack

上一輪為實際進展；從乾淨 `8938968` 接續[動態PC流程](DESKTOP_ACTIVE.md)。**API/UI0.30、Unity0.36.1／code44／NGO29與e0594513140ff7fb4bc084929691b91c15f7d908e8f59c114aa5ab27daaf11eb保持**。原生階段只有Python驗收／文件修改，沒有重建或重跑原179 Editor／雙平台／APK／launcher；後續雲端.NET及瀏覽器測試修正結果見下文。原scene／prefab／rules0.8.0／Tracked與0.5／1.5秒政策保持，正式5080不動。

以computer-use技能只操作自己本輪唯一可見的Windows遊戲視窗，逐階段實際W／Space／R／Space，畫面確認後才寫該階段done檔；沒有REST／RPC／UDP注入姿態或命中。所有場為25個原native client、1個server，**一位操作、24接收、同機Simulation**；all25SimultaneouslyActive／networkCapacityAccepted=false、headsets0，不能稱25位同時操作或頭盔／跨機／Wi-Fi驗收。GPU畫面只為Windows視窗觀察，沒有新原生GPU／PCM探針、FPS／聲音或XR追蹤證據。

| 真正PC場／原handle | 原結果與範圍 |
|---|---|
| `desktop-active/20261101-075730-56b9ca85`，43305 exit1 | 40秒actual UI move確認逾時；首次畫面不符後重新啟用並確認自己的遊戲視窗，W已送出，但確認時stage已failed，guard拒絕補寫move.done。沒有done、active-result／summary／全程continuity接受檔；26 initial snapshot與raw退出資料保持。cleanup空，不能稱引擎或姿態故障根因 |
| `20261101-075928-d971525e`，8014 exit0 | 修改前9項、130快照／26報告、26599 Running列及1223連續回放／6參考全過。raw有25份final，但工具當時未提供停止前的個別結果／server ack閘門，不補造新接受欄位 |
| `20261101-080727-7ba918cd`，56068 exit0 | 中間10項含25份精確個別結果與client phase，130快照／26報告、24252 Running列、1115全回放／6參考成功；server25 ack另離線相符，該版檔未記錄serverAcknowledgedConnections新閘門，原件保持 |
| `20261101-081224-46713819`，40247 exit0 | 最終來源10項，130快照／26完整報告、**33256觀察Running列**無失效，1420連續全回放／7參考及參考間所有保存Running幀無失效；25份精確結果與實際server ack通過，cleanup無殘留 |

最後三場各自明確finish、精確combat／world雙seal及25人CSV均成功，原生日誌無send queue full。最終26份probe皆reason=Requested、complete=true／truncated=false，各自收集起算最晚151.630929秒停止、最多1320列，沒有延長原240秒／4096列上限；client probe先停、server seal後停，之後才核對玩家結果。相鄰觀察Running新tick最大間隔0.383255秒，非RTT／FPS或每packet保證；不同報告樣本不當同一時刻。

最終實際短W移動0.05公尺，第一發敵軍100→50、彈匣30→29，R顯示RELOADING後30／89，再Space擊倒目標為29／89。權威與所有端列出的狀態欄位一致，其他24位位置／彈藥／統計未被這位玩家輸入改動。最終主玩家耗彈2、命中2、擊殺1、命中率100%、中彈／損耗0、健康100；25人CSV與個別結果逐一等於各自sealed ledger，不能把主玩家數值套給其他人。

原動態工具在seal後會直接stop_round，只核對操作、接收／回放與最終CSV；本輪先保持原9項baseline，再新增停止前等待結果。`validate_final_results`要求25個原native owner／admission／room、非空且精確相同的ack名單、25份無重複final、world stream／sequence／ledger through及實際API combat acceptedSequence。client每份只有一個原連線；server log另須25筆無重複VR_SERVER_DEBRIEF_ACK，ID集合精確等於原nativeConnectionId、沒有DEBRIEF_TIMEOUT。這區分final＋disconnect的client phase與真正server ack，沒有改遊戲30秒等待或斷線政策。

新`active-player-results.json`保存delivery／個別結果／實際serverAcknowledgedConnections，active-result增加individualResults／acknowledgedResults。最終25份皆worldSequence1420／combat5／through42，server確認也全部對到原25條連線；完成驗收後才停原程序。舊缺欄位是NotRecorded，原9項／中間版範圍不改寫，不能由空集合當全部送達。

新增9個反例含空／closed／未知delivery、缺失／重複結果、舊admission、前一幀世界尾界、錯combat tail／room／health及client已收但server ack缺失／重複／外連線／timeout。**17 active＋11 capacity＋12 debrief＋17 independent evidence，共57本機Python通過**，語法／diff成功；CI既有active入口自動包含新案例。這些原生檢查不當新跑179 Editor。

功能[b906236](https://github.com/peca12968/vr-command-center/commit/b906236e874e1112ce3e0c4349933b534f39c16a)的[CI 41256605682](https://github.com/peca12968/vr-command-center/actions/runs/41256605682)這次真正啟動，雲端.NET建置及717規則／459 HTTP／47 world-stream、Python與素材檢查成功，67 Node通過；最後瀏覽器在`world-browser.cjs:86`的第二分頁完整截圖30秒逾時而exit1，不能沿用前輪帳務阻擋的說法或稱整套瀏覽器成功。原job log一檔及artifact13063671486的13檔保存在`artifacts/ci-41256605682-*`，失敗畫面亦顯示原60秒camera來源已結束；這不證明Chromium底層根因。

測試現在先以[Playwright官方bringToFront](https://playwright.dev/docs/api/class-page#page-bring-to-front)明確啟用要截圖的分頁，關閉後啟用原頁。相機儲存／延遲回應流程結束時，停止並正常End自己原場，再為擷取時鐘與中斷測試建立另一個原有60秒上限relay；先核對新場Running且程序仍活著，避免慢CI拿已Ended的相機來源冒充即時資料。沒有提高截圖30秒或relay上限、跳過斷言、改正式UI／API／遊戲新鮮度政策。原第三個完整封存回放流程保持。

最終修正本機原handle30549真正exit0，**67 Node／235 Chromium**（新增一項獨立live來源前提）成功；Chromium151.0.7922.34／Playwright1.62.1，實際相機位置截圖已人工檢視。原console42檔先完整保存到`console-before-ci-focus-549e61a44ca645c785f23a43a576c519`並附hash，未覆寫原失敗或原生runtime證據。`browser-focus-evidence-validation.json`重新核對原42檔完整、現本機console42檔及原CI artifact13檔／job log另存SHA；後續修正CI另記，不把本機結果當雲端通過。

修正[8d2227a](https://github.com/peca12968/vr-command-center/commit/8d2227aa02b3eb384a9926ad498cf9ae7bb3b5ad)的[CI 41258070247](https://github.com/peca12968/vr-command-center/actions/runs/41258070247)／job124705387031**真正完成success**，本機watch原handle73920也exit0。Linux .NET restore／build、**717規則／459 HTTP／47 world-stream**、工作流程全部Python／語法／素材檢查及**67 Node／235真正Chromium**成功，沒有跳過原斷言。artifact13063049447（9453864 bytes、ZIP SHA256 `da8b3ebe38337f86227230e5572167018ebf3b49efa9de3a4d7e76625a8340b6`）下載到新`ci-41258070247-console`，37檔及job log另存SHA；成功相機位置畫面已人工檢視，即使camera來源自然結束，時鐘／中斷流程仍使用自己的新live來源。

`browser-focus-ci-success-validation.json`核對成功37檔、235通過metadata及前55份本機／失敗CI檔完整。兩次CI均保存，這是瀏覽器fixture修正與管理API回歸，不當Chromium底層根因證明、新Unity／XR／原生渲染或跨機容量驗收。後續僅文件證據提交使用`[skip ci]`，上述成功來源精確為8d2227a，沒有為文件重跑整套測試。

`active-e059-runtime-validation.json`核對本輪4 C runtime共836檔／F snapshot逐檔一致，前44 runtime891檔、前F337／原尾界反例F76／獨立房F112／0.36 history321與三組API各159保持；總48 C runtime1727檔，新四場F證據1138檔另存hash，失敗也保存。既有0.36／0.36.1 Windows包、APK與receipt metadata保持，來源／binary仍F、runtime明確C SSD。所有writer全停才一次snapshot保留原件，保存SQLite不開連線、沒有修復／ack補送或截尾。

這是同版實際輸入／接收／個別戰績的進展，不證明舊31筆或F發布吞吐已修復，也不把視窗觀察工具的影響當已排除。完整11項active；下一步推進操作員即時控制與動態玩家組合，原31筆、慢碟、實機／MR／VIVE／跨機25台及廠商硬體各自另驗。

## 2026-11-01：0.36.1五獨立房長任務與閉源證據讀回

功能 [4898c98](https://github.com/peca12968/vr-command-center/commit/4898c988e0cd1a5203d4b30ca7552c0bb5c8dd33) 已推送main、遠端SHA一致。[本功能CI run41254427165](https://github.com/peca12968/vr-command-center/actions/runs/41254427165)／check124694467148為failure、steps空；fresh annotation明確為付款失敗或支出上限，job未啟動，沒有雲端測試結果。未改帳務或手動重跑；下列為本機實際驗證。

上一輪為實際進展；從乾淨 `6fa0d7b` 接續五房獨立驗收。**API/UI0.30、Unity0.36.1／code44／NGO29及e0594513140ff7fb4bc084929691b91c15f7d908e8f59c114aa5ab27daaf11eb來源保持**；本輪只有Python／文件／CI，沒有改遊戲或重建／重跑179 Editor與雙平台，沿用原成功receipt與scene／prefab ID。沒有新.NET、一般瀏覽器、GPU或頭盔結果。

真正場 `desktop-long/20261101-073002-fab40f9a`，**原handle7849真正exit0，executionFinished／acceptancePassed／complete=true**。五個Windows server＋25個headless client，每房5位原admission、各自900秒活動倒數與唯一tick18000自動End。明確C SSD新runtime，來源與遊戲binary仍F；新API／159檔同版執行副本啟動前核對成功，原5080及正式資料不動。各房不同session／world stream／UDP port，Clear日／Fog日／Rain夜／Storm夜／Clear夜、各自barrel／sandbag與旋轉角度；Room控制台對其他房Begin與live watch均403，真正AI初始造成損耗後關閉自動攻擊，沒有玩家輸入／姿態／戰績注入或診斷probe。

Room1 Pause接受13、Resume14，凍結tick2410；在3.094秒觀察窗口內，Room2 2388→2449、Room3 2378→2439、Room4 2355→2418、Room5 2333→2395，皆持續Running。全回放35個Paused幀均在該接受fence且tick相同，原名冊／姿態／健康有效；不計Running人次，其他房的非預期暫停仍算失敗。

五房25份原playerId／admission／room／seat跨票券到期保持、各只一個原連線；每房5份final都對到自己精確world／combat封存，全部ack，CSV七統計／ledger through／stream tail一致。隨後五個4倍回放各自從第1幀到封存尾端，**42,341全幀／41,884 Running／209,420人次**全部核對，最終packet／統計一致：

| 房間 | 全回放幀／世界尾端 | Running幀 | 應核對人次 | 最大保存capture gap ms | 最大觀察時來源年齡秒 |
|---|---:|---:|---:|---:|---:|
| 1 | 8455 | 8352 | 41760 | 112 | 0.350129 |
| 2 | 8500 | 8422 | 42110 | 125 | 0.347735 |
| 3 | 8468 | 8386 | 41930 | 131 | 0.219043 |
| 4 | 8459 | 8367 | 41835 | 125 | 0.301952 |
| 5 | 8459 | 8357 | 41785 | 130 | 0.322635 |

每房live／replay均無body／Paused／環境失效、來源過期或send queue full；live分別跳6／3／3／2／9序號，由全回放補核，不稱丟包／RTT／render FPS。cleanup無錯誤／無殘留，原native script graph為 `40cb2d72a29d7e4bc2df222ca43e83871dbadd22b7dfc7ea6b70277012c0a2f5`，不是完整OS／binary依賴graph。主機其他負載未量測，不能當無負載或隨機因果對照；仍是同機靜止Simulation，headsets0／hosts1／networkCapacityAccepted=false，不是25位同時操作或跨機／Wi-Fi／頭盔驗收。

新增 `scripts/verify-independent-evidence.py`，操作見[五房文件](DESKTOP_INDEPENDENT_LONG.md)。要求原handle先terminal及cleanup明確空列；只讀固定JSON／CSV，逐房交叉核對獨立headers／seal／最後Ended packet、原native admission／room／seat、ack名單、CSV SHA及七統計／session／room／source／雙尾界。檢查Pause witness、Running人次及接受計數；拒絕未知null當乾淨、錯格式／原件內輸出／覆寫。live可coalesce，完整回放仍精確，不新增遊戲政策。輸出complete只表示讀回完成，acceptancePassed另保留失敗；hash非簽章，metadata讀回不是重跑原始規則、歷史OS程序或全量輸入／渲染證據。

新增17項反例涵蓋前一幀尾界、同ID換admission、獨立seal／ack／CSV篡改、統計相符但原body失敗仍false、Pause其他房不前進、replay缺幀、live既有政策及原檔byte保持。最後17＋原10 independent／11 multiplayer／8 comparison／14 journal，**60 Python通過**，語法及diff成功，CI已加入新入口。

舊原工具handle96709已不存在，原exit0與完整cleanup證據保持；新7849也確認terminal後，對舊 `20261031-193917-b2f30b7d` 及新場做兩份各自獨立讀回，`independent-evidence-e059-20261101.json`成功、兩場acceptance保留true。這不是Linked跨場比較器，不推定不同source／主機條件相同，也沒有改寫原0.36尾界失敗或原31筆姿態失效。

五份關閉VRWORLD1另作rb checksum／序號metadata核對，皆Ended tick18000、frame／ack精確相同、completion／seal各一、尾端積壓0；歷史最高本地durable回條積壓依房為4／3／3／3／3，**不是32幀記憶體queue、網路延遲或API拒收**。沒有保存精確Begin回應，applicationBoundaryKnown=false／firstApplied=null，不猜序號或套用延遲；詳見 `independent-e059-journals.json`，未開保存SQLite或outbox、未ack／修復／補送／截尾。

`independent-e059-runtime-validation.json`核對新1個C runtime22檔／F snapshot逐檔一致，前43 runtime869檔、前F337及原失敗場F76、0.36 history321檔保持；新場F證據112檔另存hash。總44 C runtime891檔，所有writer全停才一次snapshot保留原件。舊／0.35／本輪API各159，以及原0.36 ZIP／history與0.36.1 Windows包／APK／receipt metadata保持；本輪沒有新封裝或launcher驗證。

完整11項active。下一步推進同版動態玩家PC操作及連續性，慢碟發布吞吐、原31筆根因／修復、頭盔／MR／VIVE／跨機25台及廠商硬體仍各自待驗。

## 2026-11-01：背景世界錄製的戰績尾界競態

功能 [5443835](https://github.com/peca12968/vr-command-center/commit/544383540896a746a0ac3ac417d4c72681a85a8c) 已推送main、遠端SHA一致。[本功能CI run41252650265](https://github.com/peca12968/vr-command-center/actions/runs/41252650265)／check124689197862為failure、steps空；fresh annotation明確為付款失敗或支出上限，job未啟動、無雲端測試結果。未改帳務或手動重跑，下列均為本機實際驗證。

從 `e387223` 接續電腦端，新增 [結果尾界修正](DEBRIEF_BOUNDARY.md)。**Unity0.36.1／Android code44，API/UI0.30／NGO29保持**。Ended 的 pending context 綁定 writer 已接受的 terminal capture，最終送出另外核對同一 immutable durable State 的 Complete／Sealed／Last／Ack 及 session／stream／origin；不以 buffered 或舊 durable 前綴冒充最終世界。原30秒等待、撤銷／admission、ack／Host收尾、客戶端精確序號及遊戲政策保持。

原0.36的真正25端900秒場 `desktop-long/20261101-064213-cf891c07`，**handle46963真正exit1**，`Debrief world seal differs`。API／closed journal最終8442、Ended tick18000、雙seal成功；25份結果都有ack，但其中一份worldSequence8441，其餘24份8442。原journal8441為Running／observed36、8442為Ended／observed37，兩者tick18000；不能用相同到期tick或最終統計一致放過錯誤尾界。程式在逐玩家建立context時讀當時durable Last，背景End寫入可在迴圈中才完成，與反例一致。

該場live8366幀／8365 Running、209125人次、無bad／來源過期，最大來源年齡0.345400秒，但live跳2序號；在結果檢查就失敗，**沒有完整API回放、final CSV或multiplayer-checks完成檔**，不把抽樣乾淨當整場接受。cleanup空／無殘留，writer全停後一次snapshot保留原件。`debrief-boundary-counterexample`另外用rb核對原checksum／序號與25份結果，不重寫原場；原worldlog SHA `139c158a9fe796d2d37494efccaa3afb1a0f16fc9141103d8378b0d5db71a5c2`。

新增2項真正Editor測試，以自己的FileWorldJournal gate重現durable1／captured2，完整等待／落盤／ack／seal各階段與舊尾界／外場stream／失敗writer反例。**179 Editor全過，failed／skipped0**，包括原3項Editor PlayMode官方Touch虛擬action測試。最終來源 `e0594513140ff7fb4bc084929691b91c15f7d908e8f59c114aa5ab27daaf11eb`；真正Prepare保持原scene／prefab ID，無RebuildArena。

Windows receipt10月31日23:04:56Z、Quest23:14:49Z，同e059來源與原scene／prefab識別；APK60311450 bytes、SHA `263ae66309ef5f1f604286c38277aa74ec3f53418fabc32c6e88dcc75920c2e2`，aapt0.36.1／44、min32／target35、arm64及v2一signer有效。105 entries、indexed compressed60289996／uncompressed160904695、libil2cpp81993392；不把ZIP容器大小當程式碼／效能指標。

新 `windows-player-0.36.1.zip` 82642182 bytes、SHA `483a6f95b2944b622dffddd617559b742e480ee94072fd3b61fcf6b5dc8d3899`，311 runtime檔＋manifest，launcher source仍a65846da...。全新C解壓後19項真正核對／拒絕成功（`player-package-checks/20261101-072420-cde50e4f`），未重跑完整GUI／封裝雙PC瀏覽器或改launcher。封裝／驗包在長場Ended後的回放期執行，不作無負載對照。

| 新e059來源真正PC場 | 結果 |
|---|---|
| `desktop-debrief/20261101-070547-86e98e87`，一般 | handle55675 exit0，4項／兩份精確結果；移除玩家無結果、Ended票券拒絕，cleanup乾淨 |
| `desktop-debrief/20261101-070614-3ace3ad5`，Host | exit0，4項／兩份精確結果，Host等待peer ack後收尾，cleanup乾淨 |
| `desktop-debrief/20261101-070614-d47a6f09`，Preparing取消 | exit0，4項／兩份零事件結果、原拒絕流程，cleanup乾淨 |

新長場 `desktop-long/20261101-070628-e45c2643`，**handle80201真正exit0、executionFinished／acceptancePassed／complete均true**。25個原client＋1個server、900秒活動倒數／唯一tick18000內部End；8414完整回放、8331 Running／208275人次、無bad，25份原admission結果與CSV／combat及world精確雙seal全一致，全部worldSequence8414；cleanup空／無殘留、原生日誌無queue error。live8321幀／8320 Running、208000人次、跳4序號，已由全回放補查；最大保存擷取gap321ms、來源年齡0.173768秒，不當RTT／FPS。票券到期後tick5952仍25份原admission、每份只一個原連線，未重入場。三個短場及長場前段與真正Quest建置重疊（23:14:49Z完成），封裝在Ended後回放期，不稱無負載或隨機因果對照。

三場closed比較 `continuity-comparison/debrief-boundary-20261101` 成功，逐玩家原admission／CSV七統計／世界與combat尾界獨立核對；原0.32失效場仍2幀／31筆／18位、acceptance=false，0.33既有乾淨場與新e059並列。source及診斷欄位不同，causalRootProven／networkCapacityAccepted均false；complete只是比較完成。原0.36的8441反例沒有完成報告，另用明確失敗資料核對，不強塞進要求完整格式的比較器。

新場closed worldlog SHA `cedc9ad30a62e44955ed4677eb15751957eb28d566eaa3c6556865fad9199a89`，8414 frame／8414 ack／一completion與seal；尾端積壓0、歷史peak5，最早world5／ack0／byte82212。沒有保存Begin回應，applicationBoundaryKnown=false，不猜接受序號或套用延遲。這不是32幀writer queue的深度或網路延遲。

離線journal reader新增最高本地持久回條積壓及最早record邊界（byte offset），結束歸零／seal不抹除歷史高峰；反例原場peak4、尾端0，兩者可同時成立。這是已保存幀與本地durable receipt差額，不是32幀記憶體queue／網路延遲，ack沒有獨立UTC，不造持續時間。無Begin回應可省略接受序號，applicationBoundaryKnown=false／firstApplied=null，不猜Begin或補造舊raw欄位。新增3個反例後，14 journal＋10 publication＋10 stages＋8 comparison＋11 multiplayer，**53 Python成功**；CI已含原journal測試入口。

本輪沒有改後端／UI／共享Simulation／wire／rules／素材pin／Tracked，沒有重跑原717規則／459 HTTP／47串流或一般瀏覽器；API三工具仍取上一輪同版159檔C副本，原5080不動。來源／binary仍F，場次runtime明確C SSD；不是F USB吞吐修復、舊31筆修復或跨機／頭盔容量驗收。

`debrief-boundary-runtime-validation.json`核對新4個C runtime56檔／F snapshot相符；前39 runtime813檔（含原失敗場14檔）、前F337檔及該失敗場F證據76檔保持，總43 C runtime869檔。保存SQLite不開、沒有ack／repair／truncate。0.36 Windows／Quest／logs321檔先完整保存於 `debrief-boundary-history-path.txt` 所指目錄，最終逐byte hash仍相符；原0.36 ZIP及更舊／0.35／本輪API三工具各159檔也保持。audit只表示原始資料保持，不是遊戲驗收。

完整11項目標active；下一步推進同版五獨立房長任務及實際動態玩家PC驗收，慢碟發布吞吐、原31筆、實機／MR／跨機／25台及廠商硬體各自保留。

## 2026-11-01：有界背景世界writer與durable狀態快照

功能 [d18aad6](https://github.com/peca12968/vr-command-center/commit/d18aad6c3140628d33392ea3ad4949cda2f2480a) 已推送main、遠端SHA一致。[本功能CI run41249194813](https://github.com/peca12968/vr-command-center/actions/runs/41249194813)／check124678950692為failure、steps空；fresh annotation明確為付款失敗或支出上限，job未啟動，無雲端測試結果。未改帳務或手動重跑，下列為本機實際驗證。

從乾淨`23f3a06`依上輪量測實作[背景世界writer](ASYNC_WORLD_WRITER.md)。**Unity0.36.0／code43，API/UI0.30／NGO29保持**。主執行緒仍擷取Arena／實際頭手及原UTC／事件cursor，僅detach／提交immutable JSON；獨立writer依FIFO執行原Append／逐筆Flush(true)，Ended幀成功才寫completion。publisher另在背景運作，只讀真正durable Pending並等待原combat ack／world ack／雙seal。Outbox immutable State只在成功持久寫入後以Volatile公布，常態讀取不再等待journal gate；寫入／Pending仍使用原gate。

queue最多32幀（含in-flight）／8MiB UTF-8 JSON，單幀仍原record上限。滿載fail closed、停止新提交及暫停combat，已接受幀仍drain；IO失敗不補造frame／ack／completion。停止先拒新提交、等待writer及已取消／完成publisher後才關source lease，不同步阻塞主迴圈。captured／buffered不是durable；live NGO可能領先錄製，非正常process退出可能失去尚未落盤queue，補送仍不是引擎世界恢復。啟動header與combat journal仍可能同步IO，**不稱所有IO已移出主線或F USB吞吐量修復**。

不改world/header／wire／rules0.8.0／素材pin／Tracked／0.5與1.5秒政策。新診斷`WorldEnqueue`僅量主線提交，不和舊`WorldJournal`同步Append混稱；分析器明列Queued／Synchronous、混合模式拒絕。File Flush仍以managed ID分類，時間與重疊區間不加總。專用native checker的journal-trace模式有界讀自己的server.log尾64KiB以fail fast記錄故障計數，一般模式不新增該讀取；本輪F並未觸發queue滿載，不把單元反例當自然滿載實測。

**最終來源`7194dc98ab4466edfd23c9c31b959757b853155fbce657ee5dc0adfa6b96d8c6`**，真正Prepare、兩輪177 Editor全過（failed／skipped0）。新增8項含非主線寫入／durable尚未前進、caller mutation隔離、FIFO／同步原journal逐byte相同、幀數含in-flight／byte上限、IO失敗不假造邊界、Stop／exclusive lease及無效序號不消耗；既有gate測試改為驗證被阻塞receipt時state仍立即可讀。補WorldEnqueue名稱／fault通知後再次177與雙平台，非拿首輪代最終。

Windows receipt10月31日22:22:19Z、ARM64／IL2CPP Quest22:29:57Z同7194來源成功；scene `4314adcd8c63d86469d16497127d8cfb／1444571642`、prefab `6f3f36cb9d710e847b5ecc569665e1ce／5227825248646244841`保持，無RebuildArena。舊d30的0.35 Windows／Quest／logs完整保存於`queued-writer-history-path.txt`所指目錄。

| 真正PC場 | 結果 |
|---|---|
| `unity-admission/20261101-062423-831a1217`，C runtime／無probe | handle15166 exit0，原8項／400幀精確seal、cleanup空。當時另有Quest建置，不稱無負載基線 |
| `desktop-clock-faults/20261101-062942-8e7c8270`，C runtime／原loopback故障工具 | handle21534 exit0、8項。管理中斷於tick114停表，hold5.860秒後同policy恢復；發布中斷仍到精確tick1200凍結，未接受due時間hold6.672秒不授權End，恢復後唯一內部End／雙seal／client結果。743完整連續回放含94個due Running／64個suspended幀，末packet與戰績一致，cleanup／proxy均乾淨 |
| `unity-admission/20261101-063140-798211ab`，F資料＋真正封裝重疊 | parent25274 exit1，admission1／package0，Running15秒逾時、無summary／cleanup空。Begin接受7；45次live皆Preparing，world148→247、年齡19.834→23.996秒；來源world335／tick3已有效Running，擷取為回應後0.404647秒。關閉來源world478／Running tick321、ack254，**224未確認、未seal**，失敗保持 |
| `unity-admission/20261101-063345-d8304c05`，明確C SSD＋同封裝重疊 | parent67128 exit0，admission／package均0，8項／354幀精確seal、cleanup空。first有效live world49／tick5／observed7，單調回應後0.437秒、年齡0.073666秒；ack354、無積壓 |

兩個負載parent為`queued-world-overlap-8f2e4029af9141bb909b88e94b05bcca`及`...4c1f69bdc4b74c0c9de56811a0e4b9b9`，均確認package在native啟動及Begin檔出現時仍存活，無輸入／姿態注入。來源／Unity binary在F，API用本輪獨立159檔C副本；F／SSD只指場次SQLite／journal位置。

| Begin UTC窗口（不跨role加總） | F佇列版反例 | SSD佇列版 |
|---|---|---|
| 窗口／完整細分列 | 15.131338秒／2685列 | 0.430971秒／3271列 |
| 最大UTC／Stopwatch差 | 0.002119秒、可相關 | 0.001360秒、可相關 |
| Main world GateEnter／Main Frame Flush | **皆0秒** | **皆0秒** |
| Background Frame Flush聯集 | 8.864939秒，窗口142筆 | 0.002059秒 |
| Background Ack Flush聯集 | 3.467186秒 | 0.002042秒 |
| Main WorldEnqueue聯集／最大單次 | 0.016539秒／0.000635秒，140筆 | 0.000476秒／0.000118秒，5筆 |

兩份細分trace皆complete／未truncated／inFlight0、failedOperations0；來源Header啟動IO不在這個Begin窗口。0.35已量到main讀鎖／flush，本輪將這兩段世界路徑移到背景；主線仍有擷取／JSON成本，舊新窗口／取樣節奏／主機條件不同，**不作提升倍率、所有停頓／舊31筆或F整體修復證明**。F仍有明確發布積壓且沒有完整seal；不得用main世界IO為0把此場改成通過。UI仍以原UTC年齡顯示過期，WS／API／SQLite／combat未另量測或重構。

observer graph `79e8a90983c6ad01256b0af59b1f48f98b91bbaa662dc529f68738d11bd3262f`；三分析graph `0b0e1dbf6dd2b26a4fb595415be2ac0a8a816e68803ac2ca7b51adea2d94906a`，不是完整OS／binary依賴。F原worldlog SHA `3e8f5712e9a074ff6e1bfb3acf7147e0b78eb071639fdd87cd68ab89d0ff10e8`，原始長度／checksum／序號核對通過，不修復／補送／截尾／開SQLite。

本輪隔離`artifacts/queued-writer-dotnet` locked restore／Release成功、0 warning／error，**717規則／459 HTTP／47串流**成功。新增Queued模式／混合拒絕反例後，**48 Python**成功，語法／diff成功；UI未改，沒有新一般瀏覽器／GPU或頭盔證據。所有.NET DLL與三工具用同次建置整組，不單換Simulation DLL，原5080未動。

可攜包`artifacts/player-packages/windows-player-0.36.0.zip`，311 runtime檔＋manifest、82641883 bytes、SHA `a31af925c432576b2bf0e192085aadeffe2ddcdc5f27d24bd98f288562d2e0df`，launcher source仍a65846da...；新C解壓包19項真正核對／拒絕成功（`player-package-checks/20261101-063002-4e90e1d8`），未重跑完整GUI／封裝雙PC瀏覽器。APK60309566 bytes、SHA `a054dc6fe09b3167c3d937717fef9ff264d160402790411822021540f120b945`；aapt0.36／43、min32／target35／arm64，v2一signer有效。105 entries的compressed60288113／uncompressed160903604、libil2cpp81992416；相較0.35容器少約22MB不是程式碼縮減，indexed內容仍略增，未自行重打包／改簽章／清cache。

`queued-writer-runtime-validation.json`raw核對新3 C runtime72檔／F snapshot一致，前35 runtime727檔及snapshot、前自有F295檔保持；最終F42檔保存。更舊／0.35 API三工具各159檔保持，本輪新159檔來源／C副本一致；0.35 ZIP、封存APK與雙receipt精確hash保持。全停writer後才snapshot，原件保留，不讀正式key或保存SQLite，未動帳務／登入／防火牆。

下一步處理慢碟下發布吞吐／明確SSD部署與長任務壓力，保留原durability／封存、佇列上限及實際年齡；不先跳幀或放寬政策。完整11項active，Quest／VIVE實機、MR、跨機／25台與廠商硬體仍待；原31筆保持未證因／未修復。

## 2026-11-01：journal鎖／flush分段與0.35同源交付

功能 [2e77c8b](https://github.com/peca12968/vr-command-center/commit/2e77c8b1d8d31a3d625fb00d6827762d5af30f34) 已推送main、遠端SHA一致。[本功能CI run41246401262](https://github.com/peca12968/vr-command-center/actions/runs/41246401262)／check124670631224為failure、steps空；fresh annotation明確為付款失敗或支出上限，job未啟動、無雲端測試結果。未改帳務或手動重跑，下列結果均為本機實際驗證。

從乾淨`5332886`接續[細分journal計時](JOURNAL_STAGES.md)。**Unity0.35.0／Android code42，API/UI0.30／NGO29保持**。共享C#9／netstandard2.1 collector及明確Windows Development／專用Server探針分別量測所有outbox gate進入、File Write及真正FileStream.Flush(true)，只保存metadata／managed thread ID／成功旗標。原mutex、逐筆durable flush、exclusive lease、checksum／ack／seal與回放位元組保持；不改world／wire／rules0.8.0／素材pin／Tracked／0.5與1.5秒政策，不是效能修復。

collector上限32768完成列／64 in-flight，原生90秒、停止後最多5秒drain；完整／未truncated／inFlight0才可接受。一般／Editor／Android不安裝，finish.request僅每0.25秒查詢；cleanup先停兩個probe收集，再輸出／End／關閉。分析器用UTC終點減Stopwatch耗時定位、裁切聯集及Main wait與Background ack flush交集，避免raw UTC量化抹掉短呼叫；clock差>0.05秒或未覆蓋則null、不補造0。該診斷容差不是遊戲新政策。

**最終來源`d30cc34c697a612ef05733e4fb116281807151658460c0550df3c5e825a703e3`**，真正Prepare／169 Editor全過（failed／skipped0，新增6項含真實gate阻塞、失敗Write、並行Stop／drain及有／無trace原journal逐byte相同）。10月31日Windows receipt14:12:21Z／Quest14:20:08Z同源成功，原scene `4314adcd8c63d86469d16497127d8cfb／1444571642`、prefab `6f3f36cb9d710e847b5ecc569665e1ce／5227825248646244841`保留，無RebuildArena。中斷後舊handle92079已消失、Editor PID48628亦不存在；重新核對成功log exit0、新receipt／目前fingerprint及XML確認完成，未因觀察中斷重建。

| 最終d30來源的真正PC場 | 結果與來源 |
|---|---|
| `unity-admission/20261031-221302-b8a7421d`，C runtime、無probe | handle74773 exit0，原8項／363幀精確seal、cleanup空；沒有兩份trace。當時另有Quest建置，不當無負載基線 |
| `unity-admission/20261101-055610-ab7c9421`，F資料＋真正封裝重疊 | parent94479 exit1、admission1／package0，Running15秒逾時、無summary、cleanup空。Begin接受7；41次live皆observed6／Preparing tick0、world126→192、年齡9.472→16.056秒。關閉來源world205／tick5已有效Running，擷取為回應後0.667191秒；最後world328／Ended tick321、ack200，**128未確認、未seal** |
| `unity-admission/20261101-055717-fd2b98b6`，明確C SSD＋同封裝重疊 | parent66382 exit0、admission／package均0，原8項／355幀精確seal、cleanup空。接受7；首次有效live／journal皆world48／tick2／observed7，單調回應後0.563秒、年齡0.067086秒；ack355無積壓 |

兩parent為`journal-stage-overlap-29bb544bf3734279bdc08ed11c525c15`與`...7f1e790fc81a4992b4e113661da5f0fb`，均確認封裝程序在native啟動及Begin檔出現時仍活著，非僅排程意圖；無輸入／姿態注入。API用同次159檔C執行副本，來源與Unity binary在F；F／SSD指場次SQLite／journal位置，不能把API副本也說全在F。

| Begin UTC窗口內分段（重疊欄不可加總） | F最終反例 | C SSD最終場 |
|---|---|---|
| 窗口／完整分段列 | 15.077624秒／4328列，43.879866秒觀察 | 0.566151秒／9581列，37.865466秒觀察 |
| 最大UTC／Stopwatch差 | 0.002379秒，可相關 | 0.001252秒，可相關 |
| Main Frame DurableFlush聯集 | **8.814804秒**，窗口116筆 | 0.002560秒 |
| Main GateEnter聯集 | **3.134420秒**；CompleteState讀取占3.134406秒 | 0.000051秒 |
| Background Ack DurableFlush聯集 | 3.562025秒，窗口67筆 | 0.002721秒 |
| Main等待與Background ack flush交集 | **3.133609秒** | 0秒 |

兩份細分report皆complete／未truncated／inFlight0、failedOperations0。這次量到同一outbox gate的**狀態讀取**會等待背景ack持鎖flush；CompleteState讀取在原WorldCapture括號之前，不能漏算成沒有等待。Flush(true)耗時含OS／排程／儲存路徑，非純實體媒體時間；managed ID不是OS ID，File層Frame sequence0是unknown。WS／API／SQLite／combat journal未新增分段，不能由不同窗口比例推效能倍率、單一硬碟／原31筆或所有舊逾時已修復。

observer graph `c5f7aaaddf82ff0ce0ee6f01ef85a1397a562909062df9ad843cb50bdb75d9f9`、三分析腳本graph `017c740ccb43861dbf596b3b09d63176958a121637259aec0700bcf9abb9e50f`，不當完整OS／binary依賴。最終F原worldlog SHA `46ec2c21db389037c344ac8ba208cab883a83973a6b9c703e1a51fe56edf0a6c`／840268 bytes，原checksum／序號核對成功，不截尾／補送／開SQLite。

本輪隔離`--artifacts-path artifacts/journal-timing-dotnet` restore locked／Release成功，**717規則／459 HTTP／47串流**通過；共用.NET DLL及三工具整組使用，不只換單一Simulation DLL，不替換原5080。10項新分段反例（UTC量化／thread分類／unknown等）＋37既有，共**47 Python**成功，語法／diff成功。UI未改，沒有新瀏覽器／GPU或頭盔檢查。

最終玩家包`artifacts/player-packages/windows-player-0.35.0-final.zip`，311個runtime檔＋manifest，82638063 bytes、SHA `a18b27dab40927e10dac50a392eb196037bad23c943cc4f6b9ee235e0e260e81`，launcher source仍a65846da...；全新C解壓通過19項真正啟動器核對／拒絕（`player-package-checks/20261031-221714-ae922d8f`）。這是offline launcher＋上列原生回歸，**未重跑完整GUI按鈕／封裝雙PC瀏覽器流程**。最終APK82742165 bytes、SHA `f4dde150a8cce6cd6b21e11c86476e22502422644b588be1cc7bb2782b5c137c`；aapt核對0.35／42、min32／target35／arm64，apksigner v2一signer有效。105 entries的compressed60278055／uncompressed160864436、libil2cpp81959304；候選APK曾60297850 bytes，容器差異不當功能或程式碼增減。

保留探索／失敗：PS1被執行政策拒載後直接呼叫相同Editor入口，未改政策；.NET nullable CS8604／8602以原gate內明確null拒絕修正；首輪Prepare C#9 CS8773為測試PathFor漏括號。第一輪169實際Editor0／XML全過，但自有runner序列化XML Element時exit1，修正輸出後最終Prepare／Tests／雙平台依序成功，未把runner1稱0。`journal-candidate-path.txt`保存f93dbc9b... Windows／Quest／logs，`journal-timing-history-path.txt`保存更舊c233原0.34。候選正常363幀、F `220457-479bf14d`其實**Paused逾時**（Begin13.313秒才看見、年齡12.780秒，112未確認），候選SSD `220559-538c2cb0`8項354幀成功。初版每幀查結束檔增加干擾，改0.25秒後重新169／雙平台及最終兩場，候選不冒充最終。raw UTC相減探索分析另存，最終改Stopwatch投影並補反例，未修改原生資料。

`journal-stages-runtime-validation.json`raw核對最終新2 C runtime32檔／F snapshot完全一致、前33 runtime695檔及snapshot保持；前自有F253檔／舊API三工具159檔保持，新API三工具159檔亦核對來源／副本，最終F反例42檔保存。writer全停後才snapshot、原件保留，舊0.34 ZIP／歷史APK不覆寫，不讀正式key或保存SQLite；未動登入／帳務／網路安全性設定。

下一步評估已量到的main讀取等待／同步flush所需writer架構或明確SSD部署，不先關閉durability／跳幀／放寬政策。完整11項active；Quest／VIVE實機、MR、跨機／25台、廠商硬體及舊31筆因果驗收仍待。

## 2026-10-31：原生journal區段計時與再次負載重現

功能 [32e6ed7](https://github.com/peca12968/vr-command-center/commit/32e6ed7bb3ef5b7d51517c1315aca08ae5fd9a76) 已推送main、遠端SHA一致。[本次CI run41206671836](https://github.com/peca12968/vr-command-center/actions/runs/41206671836)／check124553038805為failure、steps空；fresh annotation為付款失敗或支出上限，job未啟動，沒有雲端測試結果。未改帳務或手動重跑，下列37項Python與原生結果為本機實際證據。

從乾淨`82ea45b`接續[發布區段計時](PUBLICATION_TIMING.md)，上一輪為實際進展。本輪以**原c233 Windows播放器既有探針**取得新證據，API/UI0.30、Unity0.34／code41／NGO29不變，沒有修改Unity／後端／共享程式、重建163 Editor／雙平台或改原0.5／1.5秒政策。一般玩家不附掛新診斷。

checker選用`--server-trace`只啟用自己的server既有240秒／32768列NativePoseTrace，結束／失敗時先request finish並取得完整report，再End／停止程序；缺report、overflow或cleanup失敗仍exit1。新分析器將原生UTC／Stopwatch與同場Begin窗口對應，先裁切再取同point區間聯集；WorldCapture內含WorldJournal，不相加。trace／witness不完整直接拒絕、時鐘差>0.05秒或未覆蓋窗口則相關數字unknown；該容差不是遊戲新政策。journal另確認sessionId，不能跨場借用接受序號。

| 同主機、真正玩家包編譯／壓縮重疊的新場 | F資料 `unity-admission/20261031-213407-7c213c4e` | 明確C SSD資料 `unity-admission/20261031-213539-3a0d26e6` |
|---|---|---|
| 真正parent終態／cleanup | handle81146 exit1，admission1／package0，無summary；cleanup空 | handle23513 exit0，admission／package均0，原8項／354幀精確seal；cleanup空 |
| Begin與live | 接受7；43次皆observed6／Preparing tick0；live106→180，年齡12.334→16.921秒 | 接受7；4 Preparing＋1 Running，first world47／tick2／observed7，單調回應後0.671秒、年齡0.069796秒 |
| UTC觀察窗口／完整原生trace | 15.242625秒；4752列、41.9633094秒完整／未truncated | 0.673960秒；3494列、37.5978764秒完整／未truncated |
| 最大UTC／單調差；全窗口覆蓋 | 0.011078秒、可相關 | 0.005593秒、可相關；UTC窗口與單調數字分開 |
| 窗口WorldJournal | 115個區段、聯集**9.379684秒**、最大0.182471秒，32個>=0.1秒 | 7個區段、聯集**0.004067秒**、最大0.000625秒，0個>=0.1秒 |
| 關閉來源journal | first有效world198／tick5／observed7，擷取為回應後0.879103秒；最後316／Ended tick312、ack187、**129未確認，未seal** | first有效world47同live，擷取為回應後0.604164秒；最後354／ack354、無積壓、已seal |

兩個parent為`admission-trace-overlap-ea7dad6322dd46b1819a9b08981e6279`與`...945b4146d0bd48f2862299cbba7619a6`，皆保存package在native啟動及Begin檔出現時仍存活的證據，非只排程意圖；沒有輸入／姿態注入或重發Begin。F失敗經cleanup送End後有completion intent，但未seal且無成功summary，不能稱完成。trace停止後仍有4個清理期間來源幀，因此312個journal spans不冒充全部316幀映射。

F窗口WorldCapture聯集9.383359秒、MainThreadGap聯集9.674268秒，與WorldJournal重疊，**不能加總**；MainThreadGap共有68個窗口異常，明細只留最早64、計數及聯集仍全量，這個明細旗標不表示原生trace溢位。這次已量到主執行緒長journal區段，但該區段包括mutex等待、序列化／驗證、append及Flush(true)，**不是單獨fsync或CPU時間**。背景ack鎖／flush、WebSocket及API／SQLite仍未分別量測，也沒有原生span-to-sequence標記。

最終分析`publication-timing-final.json`的兩檔fingerprint為`12c97ca83dd9ea5b0aca93a88d288774ccfb10856d0378c93ce0ebb6df749085`；兩次native observer凍結同`ac3a2d0acef7e7e3591dcd4e39592479cecf8aebf76250b373a4c4fe8dd30bf1`，原receipt皆c233。F最初探索分析採區間相加（9.380564秒），保留原檔，最終改用聯集避免UTC重疊重算；未改native結果。不同時間／窗口長度、trace條件與未控制IO／排程，不能用兩數比例當因果或容量提升倍率；舊場與31筆不合併成同一根因。

9項新相關性／裁切／重疊／unknown／溢位反例、11項journal（含新跨場拒絕）、8 witness、5真正Windows artifact lease及4 startup，共**37項Python成功**，語法／diff成功，CI加入新檢查。`publication-timing-runtime-validation.json`raw bytes核對新C16檔／F snapshot一致、前30 runtime647檔及其snapshot保持；前輪自有F167檔／API三工具159檔及正式0.34 ZIP／APK精確SHA保持。新F反例41檔保存，SQLite不開、5080／帳務／登入／安全性未動。

下一步把frame及背景ack的journal鎖等待與真正Flush耗時分開量測，再評估保持durable ack／完整回放的writer架構；不能為F延遲先關閉持久化、跳幀或放寬姿態政策。完整11項仍active；實機／MR／跨機與廠商硬體待驗。

## 2026-10-31：Preparing逾時重現、來源journal與SSD入場比較

功能 [d0b5f3c](https://github.com/peca12968/vr-command-center/commit/d0b5f3c929a113ef329aaa1ab411176cb1e44d2f) 已推送main、遠端SHA一致。[本次CI run41205865737](https://github.com/peca12968/vr-command-center/actions/runs/41205865737)／check124550701322為failure、steps空；fresh annotation明確為付款失敗或支出上限，job未啟動，沒有雲端測試結果。未改帳務或手動重跑，下列27項Python與原生結果為本機實際證據。

從乾淨`e0ea233`接續[開場觀察](STARTUP_WITNESS.md)，本輪在原撤銷／重新加入流程、真正玩家封裝編譯／壓縮同時執行的情境重現Running逾時，並分開核對live與關閉的來源journal。**API/UI0.30、Unity0.34／code41／NGO29及c233d804...來源保持**，未改遊戲／後端／wire／Tracked／規則或0.5／1.5秒政策；沒有新Editor或雙平台重建，原163與成功receipt仍屬前輪證據。

入場checker新增有界metadata witness，依Begin接受序號、Running／tick>0／非suspended判斷套用，保留來源UTC／年齡和原15秒觀察；新唯讀journal分析器逐筆驗證VRWORLD1長度／SHA／序號與receipt邊界，只輸出metadata、不開SQLite或寫回／修復。8項witness＋10項journal反例＋5項既有真實Windows artifact／writer lease及4項既有startup測試成功，共27項，語法／diff成功；CI加入相應檢查。checksum／序號不冒充完整世界規則驗證。

| 原生自有新場 | 實際終態 | Begin／來源與接收證據 |
|---|---|---|
| `unity-admission/20261031-211904-9cfe99f1`，F資料、無封裝重疊 | 真正handle28285 exit0、原8項／380幀精確seal、cleanup空 | 接受7；首次有效live world57／tick6／observed7，回應後0.984秒、年齡0.788秒；journal同最早有效幀、ack380、無積壓 |
| `unity-admission/20261031-212112-f59b1f99`，F資料、真正封裝重疊 | parent69722 exit1、admission exit1、package exit0；無summary，cleanup空 | 接受7／管理Running；37次live皆observed6／Preparing／tick0，年齡6.748→16.383秒。來源journal有232幀，world136已Running但tick0不算有效；world137／tick8／observed7非suspended才有效，擷取UTC為回應後0.801秒。最後來源world232／tick301，持久ack只126，**106幀未確認、未complete／未seal** |
| `unity-admission/20261031-212633-2f8c41bf`，明確C SSD資料、真正封裝重疊 | parent13610 exit0、admission／package均0；原8項／358幀精確seal、cleanup空 | 接受7；首次有效live與journal皆world49／tick2／observed7，回應後0.531秒、年齡0.083987秒；來源擷取為回應後0.451秒，ack358、無積壓 |

兩次重疊parent各保存獨立ZIP／log／result：`admission-package-overlap-901c47fe8eec4acfb7c8297134ec586a`與`...d8e054cbd7fb4dd68a7b3cbf12d305ab`，均核對package在native啟動及control-Begin檔出現時仍存活，不以排程意圖冒充實際重疊。F反例原始worldlog SHA `df77fc1ccb930cc92751cb9bb2b0ec57f6f1de9e9f87cd4117f64fab2406ae8d`／601712 bytes，全部359筆checksum／邊界核對通過（header1、frame232、ack126）。不是以提高15秒門檻、跳幀、刪掉Preparing或重發Begin取得通過。

這次已證明**該新反例的來源有套用Begin、API/live仍落後**，不能再把此場描述為來源一直停Preparing。發布積壓階段明確，但尚未量測每筆fsync／WS／DB／主機IO的耗時；不同輪次未控制所有排程／負載，**沒有證明單一F硬碟因果或所有舊逾時已修復**。原`204538-5c3e58ba`沒有Begin回應，不能把新場7套回舊場；原31筆姿態失效也不能與本場合併成同一根因。

checker新增明確`--runtime-root`，僅建立自己的新目錄；SQLite與journal移到所指定SSD，來源／binary仍F，不移既有資料。全部writer停止後以共用snapshot fence複製回F並保留C原件。最終observerFingerprint `f028c34d6811305904c44ea2777f189944cda290d404eab6d33822165ae87922`包括兩observer腳本及共用snapshot的venue檔，不當作完整OS／native依賴graph；前一組F baseline／反例的兩腳本graph為`7104ff9e...`。兩者原生receipt同c233；比較明列Python工具差異。

另保留本輪前兩場：`211254-eb2a9de6`／handle7977 exit0、8項365幀為加入witness前基線；`211658-6f8b48ab`／handle78548 exit0、8項377幀為探索輪，過程中曾修改空UTC處理，**不稱最終封閉工具來源結果**。最後F baseline與SSD場分別在工具凍結下完成。

`admission-backlog-runtime-validation.json`raw bytes核對新C runtime14檔／F snapshot一致、前29 runtime633檔及其snapshot未變；前API＋三工具159檔保持，四個本輪自有F run共167檔保存雜湊。初次audit誤把buildCopies陣列當hash字典，exit1、沒有寫成功報告；依實際manifest逐目錄核對後exit0。保存SQLite不開、未動5080／原正式ZIP及APK、未改帳務／登入／安全性設定。

下一步保留自然負載下來源／發布階段的有界因果量測，再檢查多人持續操作與跨機部署；不把一次SSD成功稱F USB效能修復、25台／實機／MR或硬體驗收。完整11項長期目標仍active。

## 2026-10-31：原生Begin接受／套用觀察與受控校準

功能 [395c156](https://github.com/peca12968/vr-command-center/commit/395c156bbae50a67a2b0741db405b3505d946547) 已推送main、遠端SHA一致。[本次CI run41204413573](https://github.com/peca12968/vr-command-center/actions/runs/41204413573)／check124546467295為failure、steps空；fresh annotation為近期付款失敗或支出上限，job未啟動，無雲端測試結果。未改帳務或手動重跑，下列原生與4項Python是本機實際結果。

從乾淨`1c59040`接續[開場觀察](STARTUP_WITNESS.md)。前輪為實際進展，這輪針對Preparing逾時補上可重跑的控制路徑證據；**API/UI0.30、Unity0.34／code41／NGO29與c233d804...來源保持**，未改Unity／後端、姿態、規則或0.5／1.5秒政策，也未新跑163 Editor／雙平台，不把前輪結果稱本輪重建。

新工具保存Begin接受回應／序號、開場前幀、所有live取樣、首次有效Running及完整回放最早幀；要求observedSequence>=接受序號、非suspended、Running且tick>0，來源UTC仍<1.5秒、開場觀察仍15秒。每場兩個真正獨立client，兩份原admission結果／七統計／world及ledger邊界、精確雙seal與全回放一致；沒有輸入或pose注入、沒有新原生診斷模式。4項Python反例／語法／diff檢查成功，CI加入unit／語法。

實際`desktop-clock-faults/20261031-210737-1e370d2d`由真正handle71811走到exit0：3場直接連線與1場受控管理失聯，每場一server＋兩client、新任務／session。Begin皆接受序號5；直接場在收到回應後0.266／0.297／0.718秒觀察到有效Running，live first world17／16／21、tick5／3／2；全回放最早為world16／16／21，兩種最早觀察分開保存。此數字包含本機輪詢、儲存／發布，不稱RTT或來源執行時間。

受控場使用原有loopback VenueHttpGate，明確拒絕管理GET一次、0.187秒後requested release；只在記憶體轉送HTTP憑證／payload，不讀UDP。操作員Begin已被原API接受、管理狀態Running，但來源仍Preparing／tick0且suspended=true，不能當已套用；恢復後同接受序號、world22／tick3有效，回應後0.719秒／release後0.672秒觀察。全回放保留7個suspended Preparing幀，gate無handler／route／容量錯誤或界線自動釋放，關閉後無活躍tunnel／worker。

四場完整回放21／21／26／28，共96幀，第1到各自seal尾端連續、末packet／統計一致；八份個別戰績均經原admission核對。所有actor及gate已關閉，cleanup無錯誤／殘留，startup-checks complete=true、causalRootProven=false、networkCapacityAccepted=false。toolFingerprint只是新腳本SHA，不冒充完整依賴graph；玩家receipt仍同c233來源。

`startup-runtime-validation.json`raw bytes核對新1 runtime／20檔C原件與F snapshot一致、前28 runtime／613檔原件及snapshot未變，保存SQLite不開連線；writer停止才snapshot、保留原件。來源及binary仍F，資料明確C SSD，不能稱F USB、跨機／25台或頭盔通過。未動5080、帳務、登入／授權或防火牆。

**仍未重現或修復舊Running15秒逾時。**舊場沒有保存Begin回應，不能推定observed6就是Begin；受控503會有明確suspended，但舊單幀false不能排除中間曾有其他狀態。新場沒有原撤銷／重加入與同時建置條件，不能以短場乾淨或已知校準當自然根因。下一步在原入場變動／F負載情境保留命令及來源時間窗口；原31筆姿態失效亦保持未解。完整11項active、實機／MR／跨機及硬體另驗。

## 2026-10-31：Quest右手B鍵重連與暫停解除

功能 [8eabda9](https://github.com/peca12968/vr-command-center/commit/8eabda9d987ba684e46e46446b6b19a3b5f0ae40) 已推送main、遠端SHA一致。[本次CI run41203749271](https://github.com/peca12968/vr-command-center/actions/runs/41203749271)／check124544547164為failure、steps空；fresh annotation為近期付款失敗或支出上限，job未啟動，沒有雲端測試結果。未改帳務或手動重跑；下列真正Editor／建置／原生結果為本機實際證據。

前輪玩家狀態為實際進展；從乾淨`8dcc61d`補上[Quest控制器重連](QUEST_RECONNECT.md)。原Android會略過桌面OnGUI，故其Reconnect按鈕無法在頭盔使用；新增獨立於avatar的右手secondaryButton（Quest B）及等待畫面提示，重用原`ReconnectClient`重讀原路徑票券與GameServer驗票。**Unity0.34.0／code41，NGO29、API/UI0.30保持**；不改wire、world schema、票券／admission政策、Tracked姿態、模型／槍口、命中或0.5／1.5秒規則。

Client且NGO停止listening／shutdown、兩秒間隔到期才可嘗試，焦點及右控制器isTracked＋位置／旋轉trackingState均有效；必須先放開B再按，不能從斷線／冷卻／失焦／追蹤缺失帶入一直按住的狀態。另以OnApplicationFocus、OnApplicationPause及OnDisable明確解除準備，避免Unity停止Update時漏掉失焦。Server／Host不提供此控制，左Y不當右B；不自行配票、呼叫主控API、清除未重試的戰績或改追蹤資料。輸入action在bootstrap銷毀時釋放，原桌面按鈕共用同一可重連判定。

真正Prepare成功並保留原Scene `4314adcd8c63d86469d16497127d8cfb／1444571642`、prefab `6f3f36cb9d710e847b5ecc569665e1ce／5227825248646244841`，沒有RebuildArena。**最終163項真正Editor檢查全過、failed／skipped均0**，含新增8項政策／暫停解除及3項官方Oculus Touch配置的真實InputAction綁定。三項在空場景EnterPlayMode後，僅以自己的虛擬裝置／state event，在真正Dynamic更新回呼核對原控制值與action結果；臨時InputSettings還原、裝置／layout移除，沒有正式程式的輸入／姿態注入。測試asmdef直接參考Unity.InputSystem及Unity.XR.OpenXR，不靠隱含傳遞。

保留五輪真正失敗XML／log：159／3、160／2、160／2、159／3、159／3。先是InputState.Change不支援Touch bitfield，再是無焦點Editor更新未將controller event送進玩家action；只改成StateEvent仍不足，EnterPlayMode後同步呼叫Update也仍讀到Editor狀態。最終改用真正Dynamic回呼、同時斷言原控制值及完整action結果才通過，沒有放寬斷言或接受界線。最初162項成功候選（source `bd4c6419...`，Windows12:33:35Z／Quest12:42:58Z、PC8項445幀）另完整保存；補生命週期解除後重新163項與雙平台，不能拿候選當最終來源。

最終Windows receipt `2026-10-31T12:45:18.9215215Z`、Quest ARM64 IL2CPP receipt `12:52:48.9499476Z`真正成功，來源重算及兩receipt同為 **`c233d8048101109508490a9ff7b04a8c772fe71b1401223f3f69323a4cf74f5d`**，原網路ID相同。aapt確認bundle0.34／code41、min32／target35、arm64-v8a；APK實際**82,676,953 bytes**、SHA `fb5d1b469aa48202fbc0e46110ec46d1c6208142e6b28507a5ae5a7caae1fd97`。apksigner verify成功、v2 true、1 signer；ZIP checksum成功，metadata包含新輸入類別。沒有頭盔安裝或按鍵／焦點／面板實測。

APK的libil2cpp81,867,888／metadata9,270,596 bytes；有效ZIP項目總解壓160,769,828 bytes，比0.33僅多5069，索引壓縮資料60,244,012 bytes。容器另有約22.4MB空間，libil2cpp索引移至後段；未將此差稱成新增22MB程式，沒有重封、重簽或清Library cache，體積整理另列待辦。BuildReport totalBytes不是APK大小。URP匯入過程的暫時資源list變動最終回復原保存設定，沒有提交外觀／資產pin變更；兩個新.meta、測試asmdef及實際bundle設定保存。

最終原生回歸首場`unity-admission/20261031-204538-5c3e58ba`在等待Running15秒逾時、工具exit1，原last packet119／elapsed17261／observed6、Preparing／tick0／suspended=false、無summary，全部raw／journal保留。它與Quest建置及封裝並行，**未證明其原因**，不能推成新輸入bug、磁碟或建置已證實根因。原checker早期失敗不更新latest指標，因此仍指舊成功場；已補starting、命令回應、失敗state／world／events與cleanup紀錄，保留原15秒界線及所有接受條件，不把stale指標當本場結果。

等建置停止後，以同c233來源及原接受條件重跑`unity-admission/20261031-205415-cb4efdfa`，**8項／372幀**、真正handle5548 exit0，撤銷／舊admission拒絕、同次入場重連位置／健康／彈藥保持、Ended拒絕、精確雙seal及回放統計一致。這是自己的F資料、無圖形Simulation及原程序啟停，非頭盔B鍵、桌面GUI按鈕、GPU或C SSD效能；無法由一次重跑通過宣稱前場逾時已修復。cleanup errors／remainingTrackedChildren空，所有自有actor terminal；測試主動停止的exit1屬清理，非自然失敗。

正式`windows-player-0.34.0.zip` **82,634,575 bytes**、SHA `0862df2c0bc3d3e7daa62f05a10bd91e10e2be7cd53d988428702ce04e98f9f4`，311檔＋manifest；實際解壓新C目錄、Python全檔及真正Launch-Player.exe --verify成功，沿用launcher SHA `a65846da6f3a77de38356dbd9e448e55a220288ef170a407bba52cb227e63d57`。未重跑舊17／19／13啟動器套件，也不宣稱本輪GUI／跨機。首個bd4候選ZIP、APK／receipts／logs及舊0.33 APK（原fc0054... SHA）均保存於自己的history，未覆寫成新來源證據。

`quest-reconnect-validation.json`以raw bytes核對前**28 runtime／613檔**C原件及F snapshot未變、C API／三工具159檔保持；不開保存SQLite。本輪兩次成功及一次失敗admission皆用自己的F runtime，沒有新C SQLite試跑或移動正式資料。首五測試反例XML／log SHA、原生逾時raw hashes、最終receipt／APK／ZIP均記錄；原5080、帳務、登入／授權及防火牆未動。沒有新後端／瀏覽器UI變更，未把原.NET／完整瀏覽器結果當本輪重跑。

完整11項目標active。仍需Quest實際B鍵／失焦／追蹤／暫停、原票券檔USB更新、面板可讀性及實體重連；文檔提供不force-stop的暫存push成功後更名流程，尚未實機驗。原Linked31筆失效與本輪早期Running逾時都未證明根因／修復，接續因果證據、多人PC／跨機；VIVE／MR／25台／廠商硬體分開驗收。

## 2026-10-31：Windows玩家的入場／拒絕／未確認與戰績狀態

功能 [ddfc617](https://github.com/peca12968/vr-command-center/commit/ddfc6179dbe78da46683248b0ae86cda807fbde7) 已推送main、遠端SHA一致。[本次CI run41200268833](https://github.com/peca12968/vr-command-center/actions/runs/41200268833)／check124534526644為failure、steps空；fresh annotation為近期付款失敗或支出上限，job未啟動，沒有雲端測試結果。未改帳務或手動重跑，本機真正Framework／原生結果如下。

前輪五房長測為實際進展；從乾淨`aa4b866`接續[玩家連線狀態](PLAYER_CONNECTION_STATUS.md)。現有external地址公告及四欄連線檔已可分開啟動玩家，這輪補上啟動器只顯示「程式啟動」卻無法辨別真正入場的操作缺口。**API/UI0.30、Unity0.33.0／code40／NGO29保持**，不改後端、Unity、Tracked、票券、規則或世界格式；沒有新Editor／雙平台重建，原152真正EditMode與成功receipt保持。目前重算及Windows／Quest receipt仍`c98f1e1d9b6857de6fc17ea3c9d585ba41881ac528314f5e7fc0073ee5958b1f`，原Scene／prefab ID不變。

原生.NET Framework啟動器新增同類別的有界日誌監看，顯示Waiting／Connected／Rejected／Disconnected／Unconfirmed／Final；Connected必須由自己這次遊戲的精確marker回報，不從程序啟動、ping或TCP推成入場。至少30秒未確認只請人核對IPv4／UDP埠／版本，不猜防火牆或其他網路根因。Final不被正常結束斷線覆蓋，新Connected才開始新狀態；記錄不可讀時明示僅是先前回報，控制台readiness仍是另一個權威快照。

GUI來源在每次啟動將Unity原生日誌指定到自己的LocalAppData PlayerRuns新目錄，不讀全域Player.log或其他程序；關閉啟動器仍不終止遊戲／End。每次最多64KiB、跨讀UTF8 decoder、完整換行才辨認、單列4096字元／過長整列忽略，狀態歷史64筆，日誌倒退或積壓>2MiB停止推定；不新增姿態／GPU／PCM或網路探測，不讀其他程序memory或OS畫面。普通GUI不寫狀態報告，原CLI未要求監看則保持原流程。

選用`--status-report`必須搭配waited launch與自己的新log，僅保存固定state／PID／exited／availability／有界transitions，不保存ticket、actor ID或raw結果。只在內容改變時寫入；大小寫路徑別名、包內輸出或覆寫輸入／舊檔在啟動前拒絕。complete僅表示狀態快照未超界，exited是獨立的退出欄位，均不代表任務、網路或設備成功。

真正Framework compiler編譯同一`PlayerConnectionMonitor`、**17項C#檢查**通過：等待30秒不假裝連線、拒絕／斷線／重連、Final保留、半列／UTF8半字元、prefix假marker／超長列、日誌倒退／2MiB及64筆界線、不洩漏內容。來源SHA `a65846da6f3a77de38356dbd9e448e55a220288ef170a407bba52cb227e63d57`；檢查來源SHA `d78e44aed9ad1e2178068cb21a8780b97099146ec71fceab44b4a0ebadb9aebf`。初次手動csc相對路徑參數未找到來源（CS1504），改實際絕對路徑重跑才成功；正式`check-player-connection-status.py`固定使用絕對來源並保存compile／run log。這是fixture parser檢查，不是Unity、原生入場或GUI證據。

新玩家包`windows-player-0.33.0-status-v1.zip` **82,633,458 bytes**、SHA `cff0c88aeaf89262f09f3efffb263a2980f7df68e13dae7d7a81f4ccdcf2e691`，311檔＋manifest；真正複製原runtime／編譯／ZIP成功，實際解壓新C目錄並核對全部檔案。原生啟動器**19項**核對／拒絕檢查成功（增加狀態輸出需wait、大小寫重疊、包內及舊檔保留）；Python包規則6成功／1因Windows symlink權限skip，語法、Node --check及diff檢查成功。ZIP／EXE／SDK／票券／資料不提交Git。

實際external場`desktop-venue/20261031-200737-de93284a`使用自己全新API／C SSD runtime、loopback／Simulation；Node的`--launcher-status`模式完成**13項原生／控制台整合**，真正handle58435 exit0。兩個獨立玩家使用控制台實際下載的票券、原解壓包啟動，其狀態皆Waiting→Connected→Final；原生與控制台readiness一致，Begin／Pause／End、380幀世界及七統計／原admission／精確雙seal一致，正常斷線不覆蓋Final。這是同機背景程序及Chromium SwiftShader，沒有GUI啟動器按鈕／截圖、GPU或跨機證據。

另兩個自有原生玩家分別使用錯誤票券、自己的不回應UDP端點（無GameServer，不讀payload）：真正狀態Waiting→Rejected及Waiting→Unconfirmed，均未出現Connected，原兩位參與者未受影響。Unconfirmed是本次30秒未收到確認，不當作已證明網路／防火牆故障。四個原生玩家／啟動器全清理、status報告exited=true且無ticket／actor ID／raw結果；部分由測試主動停止、native exit1屬清理，不拿它當自然退出或登入失敗。external helper自身仍allAcknowledged=null、headsets=null，兩份結果由獨立檢查器核對，不以空集合偽造全部收到。

原helper handle23787真正exit0，全部自有actor terminal，cleanup／native-cleanup無錯誤。`launcher-status-runtime-validation.json`raw bytes核對新**1 runtime／14檔**C原件與F snapshot一致、前**27 runtime／599檔**原件及snapshot未變、C API／三工具159檔保持；不開保存SQLite。writer停後一次snapshot、保留原件，source／binary仍F，資料明確C SSD，不是F USB效能。原5080、帳務、登入／授權／防火牆未動，既有GUI安全性提示由使用者自行處理。

這輪交付玩家端狀態來源與實際背景原生證據，**GUI完整操作、跨機／25台、頭盔與原Linked31筆根因／修復仍未驗證**。沒有新後端／瀏覽器UI行為變更，未重跑.NET／完整瀏覽器套件或Unity。完整11項目標保持active，後續取得安全性提示人工處理後驗GUI與實際跨機；仍可接續PC多人操作、原姿態自然窗口定位，Quest／VIVE／MR及廠商硬體分開驗收。

## 2026-10-31：五個獨立世界／25程序的15分鐘任務

功能 [171dabc](https://github.com/peca12968/vr-command-center/commit/171dabcf1c835924213e87ef7dc7d6fa3bd5a19b) 已推送main、遠端SHA一致。[本次CI run41199169762](https://github.com/peca12968/vr-command-center/actions/runs/41199169762)／check124531368540為failure且steps空；fresh annotation為近期付款失敗或支出上限，job未啟動，沒有雲端測試結果。沒有改帳務或手動重跑；下列本機原生與32項Python為實際結果。

前輪為實際進展；從乾淨`2e69066`接續[五房獨立長任務](DESKTOP_INDEPENDENT_LONG.md)，補上Linked長場之外，五份獨立世界同時運行、單房Pause及各自倒數／封存的證據。**API/UI0.30、Unity0.33.0／code40／NGO29保持**；只新增Python原生檢查器／10項反例與文件，未改後端、Unity、Tracked資料、0.5／1.5秒政策或幾何規則。沒有新跑Editor／雙平台，沿用原152真正EditMode與Windows／Quest成功receipt；目前來源重算及兩receipt皆為`c98f1e1d9b6857de6fc17ea3c9d585ba41881ac528314f5e7fc0073ee5958b1f`，原Scene／prefab ID保持。

真正場`desktop-long/20261031-193917-b2f30b7d`：5個Windows server＋25 headless client，每房5人、不同mission／session／world stream／UDP port、各自900秒活動任務；Clear日／Fog日／Rain夜／Storm夜／Clear夜與各房旋轉物件分開保存。原生程序分批入場、每次新增前檢查至少2 GiB可用記憶體，所有程序job workers=2，沒有啟用pose／replication probe或注入姿態／武器。名冊Quest3欄位只是分類，實際headsets0／hosts1、來源全為Simulation、networkCapacityAccepted=false。

各房Room控制台對其他房的Begin及live watch都被後端403拒絕；原5份header確認房間、來源、900秒、stream與物件範圍。每房真正AI造成一次20損耗後停止自動攻擊，個別健康各1位80／4位100；25個原playerId／admission／room／seat跨原票券到期保持，房1於tick5792、房2–5於5880–5882再次核對，未用過期票券重入。

房1自己的Pause接受序號13、Resume14，實際停在tick2404，主觀察3.265秒；同一期間房2由2384→2445、房3由2362→2424、房4由2343→2405、房5由2322→2388，皆持續Running。完整回放35個Paused幀都屬原接受序號區間且tick不變，逐玩家姿態／健康正常；不把它們算Running人次。其他房出現Pause仍算反例，沒有以本輪有暫停測試免除所有Pause。

五個live SSE獨立讀取，來源UTC及heartbeat保持原1.5秒界線；五房各自唯一tick18000自動End，**每房5份、共25份原admission戰績全部ack**，逐玩家七統計、world stream／sequence、ledger through及combat final一致。房1through16、房2–5 through14，各combat final1；五份CSV各5列與sealed ledger核對。之後五個4倍回放並行讀取各自第1幀到精確封存尾端，全部**42,293幀／41,847 Running／209,235應核對人次**，最終packet／統計一致，明細如下。

| 房間 | 全回放幀 | Running幀 | 應核對人次 | 最大capture gap ms | 最大來源年齡秒 |
|---|---:|---:|---:|---:|---:|
| 1 | 8417 | 8320 | 41600 | 118 | 0.155906 |
| 2 | 8457 | 8385 | 41925 | 132 | 0.155804 |
| 3 | 8469 | 8386 | 41930 | 117 | 0.155610 |
| 4 | 8471 | 8379 | 41895 | 133 | 0.156270 |
| 5 | 8479 | 8377 | 41885 | 132 | 0.153763 |

每房live／replay badFrames0、badPausedFrames0、badEnvironmentFrames0，>=1500ms capture gap0、來源過期0、send queue full0。`independent-checks.json`的executionFinished／acceptancePassed／complete=true，真正原工具handle96709最終exit0，未從stage或等待逾時重啟。五場是各自保留的世界、統計與歷史，沒有合併進新Linked。

新10 Python含Pause fence／原tick、最後一位玩家失效、其他房意外Pause、環境／suspended／敵軍跨房、保存gap與512界線及獨立header反例；既有11多人及11容量解析共**32項**實際通過，語法及git diff --check成功，CI加入新unit／語法。沒有後端／UI行為變更，本輪未重跑.NET／HTTP／瀏覽器，不把前輪結果當新跑。

`independent-long-runtime-validation.json`以raw bytes核對新**1 runtime／22檔**C原件與F snapshot一致，前**26 runtime／577檔**原件及snapshot完全未變，C API與三工具159檔保持；不開保存SQLite。所有actor及父handle皆terminal，cleanup errors／remainingTrackedChildren空，writer停後才一次snapshot並保留C原件；來源及binary仍F，資料明確C SSD，不是F USB效能。工具fingerprint `40cb2d72a29d7e4bc2df222ca43e83871dbadd22b7dfc7ea6b70277012c0a2f5`與結束後來源重算一致；原5080、帳務、登入／授權及防火牆未動，GUI安全性提示仍由使用者自行處理。

這證明本輪五個獨立、靜止、同機PC世界的長任務與封存，**不證明25位持續操作、25台、跨機／Wi-Fi、GPU／FPS或頭盔容量**。原Linked的31筆失效仍未通過，未證明根因／修復；不同模式未重現不能替代自然窗口定位。完整11項長期目標保持active，下一步多玩家持續操作與跨機部署、自然姿態失效的因果證據；Quest／VIVE／MR與廠商硬體另驗。

## 2026-10-31：同源25程序未啟用診斷對照與跨場核對

功能 [a12fd01](https://github.com/peca12968/vr-command-center/commit/a12fd0180560ad966991187440b10667f5311fa3) 已推送main、遠端SHA一致。[本次CI run41197458889](https://github.com/peca12968/vr-command-center/actions/runs/41197458889)／check124526402137為failure且steps空；fresh annotation為近期付款失敗或支出上限，job未啟動，沒有雲端測試結果。沒有改帳務或手動重跑；下列本機原生及27項Python為實際結果。

從乾淨`4497e9a`接續電腦端，補上[跨場證據比較](CONTINUITY_COMPARISON.md)與同源未啟用診斷的自然長場。**API/UI0.30、Unity0.33.0／code40／NGO29保持**；本輪只新增Python比較／測試及文件，未改Unity、後端、姿態／碰撞或0.5／1.5秒政策，也未重跑Editor／雙平台。沿用原152真正EditMode與成功receipt，不把它們稱本輪重建；目前來源重算及Windows／Quest receipt皆為`c98f1e1d9b6857de6fc17ea3c9d585ba41881ac528314f5e7fc0073ee5958b1f`，原Scene／prefab ID保持。

真正未帶`--pose-continuity`長場`desktop-long/20261031-191455-4bd7c8c7`：一個Windows server＋25 headless client、五房Linked各5、固定900秒，全部Simulation／同機靜止；報告明確poseContinuity=null且沒有manifest，模式為DisabledByTool。保留同一工具handle10367直到真正exit0，不從stage／無輸出或等待逾時重啟；全部actor結束、cleanup errors及remainingTrackedChildren均空後才作離線比較。

原25個playerId／admission／room跨票券到期保持，tick5960再次核對，AI損耗後個別健康5位80／20位100。唯一tick18000自動End，25份各自結果全部ack，七統計／through38／combat final5／world8475與CSV25列逐玩家一致、精確雙seal完成。CSV SHA `7d2a262ec8611d26e598b196bb50da616ba4150c5527c8d240dd8b1a65de4cde`。完整4倍回放**8475幀／8412 Running／210300應核對玩家人次**，badFrames0、保存最大capture gap123ms、>=1500ms為0、來源UTC最大0.153497秒／過期0、send queue full0；executionFinished／acceptancePassed／complete=true。是本場連續性通過，不是25位操作、實體網路或頭盔容量通過。

新`compare-desktop-continuity.py`只讀已結束場次的JSON／CSV，核對cleanup、獨立seal／diagnostic manifest、原入場／room、全部ack、七統計、world／ledger／combat邊界及CSV SHA；依全程live／replay、來源年齡、capture gap與queue反例重新核對接受結果。拒絕受控校準、未結束或不一致證據；輸出只寫全新artifacts，保存輸入檔SHA、不開保存SQLite或讀憑證。NotRecorded表示舊報告未保存模式，不能因欄位缺少當DisabledByTool。complete只表示比較完成，不表示每場成功。

實際三場比較與同源開／關比較都exit0：舊0.32／4f1173場8400 Running／210000人次、**2幀／31筆失效仍未通過**；0.33／c98f1稀疏場8391 Running／209775人次、0失效；本輪同c98f1未啟用場8412 Running／210300人次、0失效。三場已記錄差異為sourceFingerprint及diagnosticMode；同源兩場差異為diagnosticMode。這是先後進行的觀察，未量測主機條件並未因此受控，**causalRootProven=false、networkCapacityAccepted=false**。沒有依已證明原因作行為修正，不能說原31筆根因已解或已修復；下一步仍需捕捉自然失效窗口及送出／接收／loop／CPU括號重疊證據，再作針對性修正。

新8項Python反例、既有11項多人連續性及8項稀疏解析共**27項**實際通過，語法與git diff --check成功，CI加入新unit／語法。本輪沒有.NET／UI行為變更，未把原717規則／459 HTTP／47串流／234瀏覽器或Unity結果當新跑。

`continuity-comparison-runtime-validation.json`以raw bytes核對新**1 runtime／14檔**C原件與F snapshot一致，前**25 runtime／563檔**原件及snapshot完全未變；原C API與三工具159檔保持。所有writer停止才一次snapshot，保留C原件，來源及遊戲binary仍F、資料明確C SSD，非F USB效能。長工具指紋`a6d8d68f53bec2279f0625199a41e80a63b7807477a970790d6d61d1a3402499`仍與目前來源一致；原5080服務、帳務、登入／授權／防火牆未動，GUI安全性提示仍由使用者自行處理。

完整11項長期目標保持active。自然失效定位、多玩家持續操作、五獨立房長任務、跨機／25台、Quest／VIVE／MR及廠商硬體各自保留待驗收，不用同機靜止乾淨場取代完整交付。

## 2026-10-31：長任務稀疏收發／主執行緒診斷

功能 [6018e88](https://github.com/peca12968/vr-command-center/commit/6018e882c7262b03fdb6312b9465842484552363) 已推送main且遠端SHA一致。[本次CI run41195892102](https://github.com/peca12968/vr-command-center/actions/runs/41195892102)／check124521846878為failure、steps空，fresh annotation仍為近期付款失敗或支出上限，job未啟動；沒有雲端測試結果，未更改帳務或手動重跑。本機實際測試與未解限制如下。

前輪為實際進展；從乾淨`223613b`接續[POSE_CONTINUITY](POSE_CONTINUITY.md)，補上原240秒逐事件工具不能涵蓋第12分鐘失效的缺口。**Unity0.33.0／code40／NGO29，API/UI0.30保持**。新Windows Development opt-in獨立為1200秒／256聚合streams／各4096稀疏gap、body轉換及主執行緒窗口，超界保留最早證據並判不完整；舊pose32768列／240秒及replication240秒保持且與舊pose模式互斥。一般／Editor／Android不安裝，不修改世界、DB、命中規則0.8.0、Tracked資料或原0.5／1.5秒政策。

沿用原RPC前PoseSend、入口Receive／accepted／rejected／throttled與journal／capture／publish量測點，正常事件僅聚合，間隔／量測>200ms才留兩端，body只記轉換與接受姿態年齡；沒有位置、玩家姓名、key／ticket、UDP payload、GPU／PCM／OS畫面。只有server附加既有PlayerLoop邊界，client不裝loop。ManagementApply約0.5秒輪詢也會產生稀疏gap，不把總筆數稱姿態異常。

Install與本收集器Update只查自己的呼叫執行緒GetThreadTimes／QueryThreadCycleTime，用pseudo handle、不列舉／開啟其他thread、不讀memory／stack、不改優先級／OS。保存thread ID／creation FILETIME、kernel／user100ns及cycles、查詢前後UTC／單調括號；僅留>200ms Update-to-Update窗口，另計總samples。CPU值屬整個sample括號，不是engine node內CPU；cycles不轉秒，量化或零值不證明全程停住。數值／身份倒退拒絕，clock step達50ms不做跨程序join。

真正Editor Prepare、**152 EditMode**成功（新增8項聚合／上限／反例／snapshot／模式互斥、64位JSON及真正Windows呼叫thread API）；Windows receipt `2026-10-31T10:29:14.1866454Z`、Quest ARM64 IL2CPP receipt `10:39:20.8575012Z`同源成功，fingerprint `c98f1e1d9b6857de6fc17ea3c9d585ba41881ac528314f5e7fc0073ee5958b1f`與目前重算一致。原Scene `4314adcd8c63d86469d16497127d8cfb／1444571642`及prefab `6f3f36cb9d710e847b5ecc569665e1ce／5227825248646244841`保持，沒有RebuildArena。aapt確認0.33／40、min32／target35／arm64；實際APK60,264,566 bytes、SHA `fc0054d7b6a8bb3d87a82ea8c53ea705d8fd7430466f8cea8274e65571d5fd72`，libil2cpp81,864,328／metadata9,269,280 bytes且含新型別。BuildReport總輸出不當APK大小，仍無頭盔運行。

首次Quest確實失敗，log為Bee／PlayerScriptAssemblies存取UnauthorizedAccessException，exit1與原log保留；不因開頭token warning否定已成功Editor／Desktop授權或要求重新登入。沒有改Library cache／ACL／安全設定，後續真正重試exit0才採為成功；未證明初次檔案存取根因。官方293檔Transport單一修補與原字型pin核對成功，實際匯入的兩個新.meta及版本設定保存。

短校準第一場`desktop-long/20261031-183241-43db1261`完成受控1.2秒單一上行丟棄與恢復，但解析器把JsonUtility產生的未啟用loop初始化空物件誤判已宣告，父工具exit1。原raw／cleanup／封存保留，不補寫成passed。只接受精確空形狀、非空仍拒絕後，第二場`183431-27f2f323`真正重跑exit0：server主玩家PoseReceive gap **1.2776636秒**、body接受姿態年齡約0.5999984秒，sender無>200ms呼叫gap、peer仍有效、同admission恢復，原七統計／兩份結果／雙seal一致。轉送原UDP bytes、不讀payload，不注入姿態或武器；是已知受控原因的校準，不是自然31筆失效的根因證明。收集先停止／移除自己的marker再寫報告，輸出安排在End與全部ack後，與任務內觀察分開。

新版未帶診斷的一般原生入場`unity-admission/20261031-184149-3d3b0b53` **8項、377幀**成功，含撤銷／原程序重連／已接受健康與彈藥保持／Ended拒絕及回放統計。此工具使用自己的F資料，非下方C SSD配置或頭盔，真正handle exit0、沒有GUI／鍵鼠操作。新8 Python解析反例、原11多人連續性及語法通過，JSON clock／role／counter／aggregate fence不以資料缺少當成功；CI加入unit／語法，不稱雲端執行原生。

自然長場`desktop-long/20261031-184355-3b466dac`一server＋25 headless client、五房Linked各5，全部明確啟用新模式，僅server loop。固定900秒、原入場跨票券到期、AI每房一次20損耗後固定5位80／20位100、唯一tick18000、**25份個別ack及CSV／through38／combat final5／world8449精確雙seal一致**。完整4倍回放8449幀／8391 Running、209775應核對人次，badFrames0、保存最大gap114ms、source UTC最大0.220263秒／過期0、send queue full0；工具真正exit0、acceptancePassed及complete=true。是本場靜止Simulation的連續性通過，不是25位操作、物理網路、VIVE／Quest或容量完成。

26份報告皆完整／未截斷、時鐘可對齊；client最短901.9851532秒／至少81157次main-thread samples、server907.3074891秒／81632 samples。任務Running窗口內無body loss、PoseSend／Receive>200ms gap、主執行緒>200ms窗口或PlayerLoop>100ms空窗；server一筆loop空窗在啟動期，不當作任務內根因。server原1769筆稀疏gap主要為正常ManagementApply，沒有把它們當資料遺失。`pose-continuity-analysis.json` complete=true、missionAcceptancePassed=true、**causalRootProven=false**；沒有窗口不能說CPU／frame delta為0。新工具指紋 `a6d8d68f53bec2279f0625199a41e80a63b7807477a970790d6d61d1a3402499`在結束後與目前helpers／analyzer重算相同。

此場與原0.32未啟用的31筆反例條件不同，而且沒有針對已證明原因作行為修正；**沒有宣稱根因已解或修復**。原6931／6932幀13／18位及497ms窗口、完整raw與接受失敗保持不變。後續仍需自然失效窗口與未啟用對照、送出／接收／loop／CPU括號重疊分析，不能用乾淨一次或此校準取代原問題。

`continuity-runtime-validation.json`raw bytes核對新**3 runtime／106檔**C原件與F snapshot一致，前**22 runtime／457檔**未變，原C API／三工具159檔保持。保存SQLite完全不開連線；所有真正actor／fixture handles已terminal，cleanup errors／remainingTrackedChildren空。writer全停才一次snapshot、保留C原件，源碼與遊戲binary仍F，資料明確C SSD，非F USB效能。原5080 API、登入／授權／防火牆未動，GUI安全性提示仍待使用者自行處理，沒有自動操作。

另產生`windows-player-0.33.0.zip` **82,630,594 bytes**、SHA `d54bc0e97b5be90686a70e92e25169b507bafcd96af4dd874276cbfa6c38ca9c`，311檔＋manifest；正常啟動器來源`127a39d1d11a856070e6676ab566c4f4862e8e5ac168e2ed4d9a4a9b4660ab45`不變。已實際解壓C、Python與真正Launch-Player.exe --verify成功；本輪沒有重新完成GUI選檔或ZIP玩家入場流程，不把舊0.32 GUI未完成改成成功。APK／ZIP／SDK／憑證／DB／journal及artifacts不提交。

完整11項保持active。下一步使用此有界診斷取得自然失效與未啟用對照、再依因果證據修正；多玩家持續操作、五獨立房長任務、跨機／25台、Quest／VIVE／MR與廠商硬體分別驗收。

## 2026-10-31：25個PC原生程序的15分鐘Linked反例

功能／反例提交 [3ff94cf](https://github.com/peca12968/vr-command-center/commit/3ff94cfcefdee18b484fe53ba18eb8f66fa8ae9b) 已推送main、遠端SHA一致。[本次CI run41192014101](https://github.com/peca12968/vr-command-center/actions/runs/41192014101)／check124510546996為failure、steps空；fresh annotation仍為近期付款失敗或支出上限，job未啟動，沒有雲端測試結果。未改帳務／手動重跑；這與本機900秒檢查確實執行後因body失效exit1是兩件事。

前輪為實際進展；從乾淨`afc2b21`新增[DESKTOP_MULTIPLAYER_LONG](DESKTOP_MULTIPLAYER_LONG.md)及可重跑工具，將原單玩家900秒與25端短測之間的缺口接上。本輪**API/UI0.30、Unity0.32／code39／NGO29保持**，未修改Unity／規則、未重建或新跑144 Editor／雙平台；沿用原Windows receipt及source fingerprint `4f1173e9eac5aa82e0b37fa58ba73afa64c392b750218b790c85c08638c3b852`，原Scene／prefab ID保持。未以新Python檢查代替Unity或頭盔證據。

真正場`desktop-long/20261031-175042-1ad7c3c8`：一個Windows server、25個headless client、自己的新API／角色憑證及C SSD runtime，五房Linked各5席，按5個一批正常入場；不注入姿態、武器或統計，不附掛240秒replication probe或延長其界線。Source全為Simulation、headsets0／hosts1／networkCapacityAccepted=false；名冊Quest3分類不是設備。25個原生程序持續900秒活動任務，唯一自動End為tick18000。

真正AI在每房造成一次非零損耗，操作員關自動攻擊並於policy sequence36後固定個別健康：5位80、20位100。原票券全部於`09:55:48Z`到期後，`09:55:48.029474Z`／tick5954再次核對全部playerId／admission／room／seat保持，整段每client僅一次本地connected。這驗既有連線延續，不以過期票券重入，也不是25位持續移動／交火。

最終**25份各自current admission戰績全部ack、timedOut空**，七統計欄、world stream／sequence8463、combat finalStreamSequence5與ledger through38一致；CSV25列逐玩家核對，SHA `7318eeab778af2ca47ab22f99fbbdb809cc47f8942ccb9bc08952a270d584e8c`。combat／world雙seal完成，完整4倍速回放從1至8463，8400個Running幀、**210000應核對玩家人次**、最後完整packet與封存統計一致。這些完成項目不代表連續性接受。

**本輪連續性未通過：executionFinished=true、acceptancePassed=false、complete=false，真正工具handle exit1**。live8394幀（Running8393、跳1個live sequence）及完整replay都找到2個相同失效幀，reasonCounts inactiveBody31、18位不同玩家受影響。世界sequence6931／tick14701有13位，6932／tick14703有18位；6933／tick14706全部恢復。全量計數不因反例取樣上限200而丟失，正常Ended退場另排除；未用最後恢復、25份結果一致或少數正常檢查點宣稱全程成功。

封存後以同次授權API另讀6928–6935的原保存packet，另存`multiplayer-fault-window.json`，沒有開保存SQLite或注入／重寫資料。6929→6930的擷取elapsed gap **497ms**、tick14694→14695；之後6931為103ms／+6 tick、6932為100ms／+2、6933為106ms／+3並恢復。失效涵蓋五房及五席，policy36、Running、suspended=false與健康80／100保持。完整保存最大gap497ms、達1500ms的gap0；source UTC live最大年齡0.214368秒、badSamples0，原生日誌send queue full0。這證明僅查1.5秒來源新鮮度或擷取間隔會漏掉body失效；沒有收集此輪內部pose trace／主執行緒或packet時間，因此不能據此斷言GC、OS排程、傳輸、來源I/O或時鐘根因。原0.5秒姿態／1.5秒來源政策均未放寬，既有偶發問題沒有宣稱修復。

新工具指紋 `07a0032e658e476cfba8ae659f60d5d634c09c9830d3d8e10f9a7779c123097d`在cleanup後重算，與實際跑的helper／來源相同。**11新Python**通過，涵蓋最後玩家、錯房／健康／rig、缺少／重複／外來名冊、原admission／席位fence、意外Pause、live跳序與replay不得跳序、原1500ms界線及全量反例計數。新增原生反例形狀的497ms＋13／18失效＋恢復測試，第一位保持健康仍必須判fail，31筆不因恢復而消失；另原single3／capacity11共14項與新語法通過。CI僅加入unit及Python語法，沒有把Linux CI當900秒Windows流程。

`multiplayer-long-validation.json`raw-byte核對本輪**14檔**C原件與F snapshot SHA相同，前**21 runtime／443檔**未變、原C API及三工具159檔仍匹配舊SHA。保存SQLite不開連線；真正tool terminal後核對cleanup errors／remainingTrackedChildren空、沒有剩餘VrCommand程序。所有writer停後才一次snapshot、保留C原件與全部反例；raw audit complete=true是檔案審核完成，不會將acceptancePassed=false改為成功。資料明確C SSD，source及Unity binary仍F，不是F USB效能／跨機證據；5080舊API、登入／授權／安全設定未變，憑證／DB／journal／binary不提交。

完整11項保持active，GUI安全性提示仍待使用者自行處理。本輪已把25端較長任務的失效窗口縮到可重查的原始幀；下一步針對接近0.5秒的窗口收集送出／接收與主迴圈工作證據，再修復並重跑，不能拿降低人數或短測當25端解決。25位操作／5獨立房長任務、跨機、Quest／VIVE／MR與廠商硬體仍另驗。

## 2026-10-31：Windows可攜玩家包與繁中啟動器

功能 [2459725](https://github.com/peca12968/vr-command-center/commit/245972594d9898cde672aab63c25228c5c5b59d9) 已推送main且遠端SHA一致。[本次CI run41189792380](https://github.com/peca12968/vr-command-center/actions/runs/41189792380)／check124504023904為failure、steps空；fresh annotation仍為近期帳戶付款失敗或支出上限，job未啟動。沒有雲端測試結果，未改帳務或手動重跑；本機證據與GUI待驗限制如下。

前輪為實際進展；由乾淨`9c8cd02`接續新增[WINDOWS_PLAYER_PACKAGE](WINDOWS_PLAYER_PACKAGE.md)，補上外部PC不便手動輸入命令的部署缺口。玩家完整解壓後開啟Launch-Player.exe、選擇控制台下載的個別玩家檔並開始。封裝及獨立WinForms啟動器v1，**API/UI0.30、Unity0.32／code39／NGO29保持**，沒有修改Unity來源、重新Prepare或重跑144 Editor／同源雙平台；這些仍是前輪成功receipt，不當作本輪新測試。

封裝器要求真正Windows receipt、原輸出路徑與目前source fingerprint，使用.NET Framework系統compiler產生x64啟動器，/warnaserror編譯成功。玩家端不需Python、Editor或.NET10 SDK，仍需Windows x64／Framework4.8與適用驅動。只收原runtime允許目錄與檔案，DoNotShip debug不收；root其他config不包入，runtime內未知JSON／key／journal／DB／log則拒絕。原receipt與Transport／模板／字型通知保留，不讀正式憑證或歷史任務。

啟動器先限制四欄Client／canonical unicast IPv4／port1024–65535，再核對包內每檔長度與SHA；不顯示或寫出ticket內容，以不經shell的Process.Start及Windows參數引號啟動自己的Unity程式。格式檢查不驗票券簽章、效期或admission，仍由原GameServer驗證。診斷log／report只接受包外新路徑，一般雙擊不需要診斷參數；關閉啟動器不End或關閉已啟動遊戲。雜湊清單不是數位簽章、發行者信任或網路探測。

最終`artifacts/player-packages/windows-player-v3.zip` **82,625,103 bytes**、SHA256 `f477e8ebe196738330013a2cefdae27fc366f617d925395b627cd6703f8807d9`；311個runtime／啟動器／通知檔，另1個manifest，共312檔。launcher source SHA `127a39d1d11a856070e6676ab566c4f4862e8e5ac168e2ed4d9a4a9b4660ab45`，原遊戲source fingerprint仍`4f1173e9eac5aa82e0b37fa58ba73afa64c392b750218b790c85c08638c3b852`，Scene／prefab ID及原receipt保持。真正解壓至C自有`portable 玩家 & v3/VRCommand-Player`，ZIP checksum／全部312檔與解壓檔逐一SHA相同，執行後再核對一致。

**15項真正編譯啟動器檢查**於`player-package-checks/20261031-173359-b97c5a46`通過：完整包、拒Server／Host／管理key／缺或空ticket、URL／縮寫／wildcard／multicast／bool或超界port、過大輸入、缺runtime及越界manifest，不產生玩家PID、不回顯fixture secret。另7項Python中**6通過、1 Windows symlink權限不足明確skip**，不稱7項全過；涵蓋receipt、DoNotShip／root config、runtime私有資料拒絕、hash／缺檔、路徑與大小寫重複。Python語法及Node driver語法通過，CI加入跨平台unit與語法；沒有改後端或控制台來源，不重述前輪717／459／47／67／234為本輪重跑。

最終背景場`desktop-venue/20261031-173702-c7be6c84` **9項完整通過且檢查器exit0**：原真正API／控制台UI建任務與名冊、來源公布及實際loopback UDP，兩份實際UI下載檔含空白／繁中／&的路徑，分別透過解壓包的真Launch-Player.exe開兩個Unity client，正常原票券／admission入場；Begin／Pause／End與Simulation來源保持。78世界幀精確seal、through8／finalStream0，兩位各自己的current admission；七統計欄位逐一等於sealed ledger，耗彈／命中／擊殺／中彈／損耗0、健康100。未注入姿態、射擊或統計。

最終tool fingerprint `8e4ddbea48c9c3ff9d1787fbbbca42c4fc77b2a003b964387110870894c2b23f`與當前helper／venue／driver／packager／launcher來源重算相同。native-cleanup兩份nativeGone=true、errors空；測試主動關閉自己Unity，兩個launcher轉傳exit1是測試關閉結果，不是遊戲自然exit0。helper真正handle exit0、36秒結果保留與雙seal後完成，allAcknowledged／headsets仍null，不能用本測試知道的兩個PC改成全體送達或設備證明。Chromium為SwiftShader、兩端headless，沒有本輪GPU／PCM／原生戰鬥輸入或跨機證據。

未完成輪次全部保留：`172855-7fb29031`只過前三步，測試spawn誤用windowsHide將互動啟動器藏起；確認自有parent／child後停止自己的driver與launcher、End並保存空戰鬥世界，非通過。`173050-78ddc807`在v2真正繁中GUI顯示下載檔，以computer-use實際按開始並成功雙PC入場、416幀及九項工作流程核對，但cleanup把signalCode=SIGTERM／exitCode=null誤當仍活著，15秒後失敗。原先過早寫出的checks.json complete保留，**不能用它聲稱整場成功**；自己第二位native／driver經確認後停止、helper精確封存且exit0。新driver以exitCode或signalCode判terminal、逐一cleanup／關browser／End，先寫workflowComplete且cleanupPending的檔案，全部cleanup成功才寫最終checks.json；最終背景場已驗。

GUI檢視亦發現WinForms檔名Label將&當助記符，v3設定UseMnemonic=false並重新封裝。`173413-5efdc8c1`的最終v3互動重跑因Windows防火牆提示遮住啟動器，已請使用者自行決定關閉，未代按安全性提示。等待240秒後檢查器按原期限失敗，沒有啟動該玩家、沒有complete checks；自己的GUI以SIGTERM收尾、native-cleanup成功、helper也精確封存及exit0。GUI選檔dialog曾開啟，但computer-use對焦點／set_value回報不一致，未把未完成輸入稱成功；最後完整選檔互動及安全性提示後回歸仍待。v2的按鈕成功不替代最終v3完整GUI驗收。

`player-package-validation.json`用raw bytes核對本輪**4 runtime／56檔**C原件與F snapshot一致，前**17 runtime／387檔**未變，既有C API／三工具159檔與前輪SHA相同；保存SQLite完全不開連線。全部writer停後由helper一次snapshot、保留C原件，四個helper真正handle均exit0，cleanup errors／remainingTrackedChildren空；未改5080舊API、登入／授權／OS或防火牆設定。原件、未完成與成功紀錄都保留，DB／journal／ticket／binary／ZIP不提交Git。source／Unity binary原件仍F，本輪玩家使用C解壓副本、runtime亦C SSD，不稱F USB效能或另一台PC成功。

完整11項保持active，仍優先電腦端。接續多玩家持續操作、實際場館／跨機部署，以及使用者處理提示後的GUI選檔／重連流程；Quest／VIVE／MR、廠商硬體及25台分別驗收。

## 2026-10-31：來源連線公告、只開伺服器與下載檔玩家入場

功能提交 [b699ccd](https://github.com/peca12968/vr-command-center/commit/b699ccdb5009d9d5ad46f9b3d50320335b2e07e7) 已推送main並核對遠端相同。[本次CI run41188116962](https://github.com/peca12968/vr-command-center/actions/runs/41188116962)／check124499094625為failure、steps空；fresh annotation確認因近期帳戶付款失敗或支出上限，job未啟動，沒有雲端測試結果。未更改帳務或手動重跑，本機各項成功證據如下；完整目標仍active。

前輪屬實際進展；從乾淨`f2c278c`接續[EXTERNAL_CLIENTS](EXTERNAL_CLIENTS.md)。**API／UI0.30、Unity0.32.0／code39／NGO29**。修補操作員流程缺口：原本local工具會替所有名冊自動開PC client，外部玩家可能撞同一admission；新增external只開server、不領玩家票券／不占用入場。local維持預設，兩種模式分開記錄，不以外部未知設備填0或虛構ack。

來源在world header存在後，用同server的GameServer身分公告所選IPv4與該場配置port。新GET／PUT connection-endpoint v1逐次傳Actor，限owner寫、Master／可讀Room讀，GameServer／Internal不能當控制台讀取捷徑；綁session／stream／完整owner，接受後不可換址或port。原內容重試保留createdAt，房間重用不繼承；Ended公告僅metadata，不開場或授權配票。worlds.db新增connection_endpoints，world schema1／envelope7、原header／checksum、rules0.8.0與素材pin不改；不將公告當連通性或裝置證明。

控制台從相符stream採用空白的地址／port，保留人工修改、提供明確套用，切場／登出清草稿並fence晚回應。下載仍只有role／address／port／joinTicket，沒有Master／GameServer key。external必須明確提供advertise-address，預設listen0.0.0.0；local預設127.0.0.1。v1只canonical dotted IPv4 unicast／1024–65535，未支援DNS／IPv6／NAT／中繼。管理API仍loopback，沒有改OS／防火牆／安全設定。

發現Unity原程式不論config.address都硬寫監聽0.0.0.0；現新增server listenAddress並真正傳入UTP第三參數。缺失／空值保留原Any，提供值才驗canonical IPv4；新managed工具明確寫loopback。**144真正EditMode成功**，新增3項舊JSON預設、真UnityTransport分開advertise／listen及錯誤地址反例。Prepare重用原ID，沒有更動NGO wire、追蹤資料、碰撞、槍口、AI或命中規則。

真正Windows receipt `2026-10-31T08:42:39.7814594Z`、Quest ARM64 IL2CPP receipt `2026-10-31T08:51:27.5208986Z`成功，同一fingerprint `4f1173e9eac5aa82e0b37fa58ba73afa64c392b750218b790c85c08638c3b852`且與目前來源重算一致。原Scene `4314adcd8c63d86469d16497127d8cfb／1444571642`、prefab `6f3f36cb9d710e847b5ecc569665e1ce／5227825248646244841`保持。aapt確認0.32.0／39、min32／target35／arm64；實際APK60,187,786 bytes、libil2cpp81,608,584／metadata9,264,400 bytes，含新getter與欄位，見external-build-validation。BuildReport總輸出不當APK大小，仍無頭盔運行。

本機locked restore／隔離Release零警告錯誤，**717規則／459 HTTP／47世界串流、67 Node／234 Chromium**通過；新增19規則、6 HTTP狀態／4世界斷言、3 Node規則與5 UI反例。普通UI fixture只證顯示／保留草稿／跨場／登出；實際來源整合另述。6新external Python＋原17 desktop共23項、語法及293官方Transport單一修補核對成功，CI加入新Python及語法。

兩場真正server-only工具＋兩個另由測試程序啟動的Windows client，各**8項**完整成功：desktop-venue／`20261031-165613-bbc86e3f`（77幀，tool `b2da89ab808ff3faf802eea1bb2a082f25d7c136643dd9f024de986dffeafb8b`）與最終`170638-b2feb08f`（78幀，tool `47fc863ca2c70b15d5a380ba3b002e4fc13189d2d3ff6d98de173e41aafaa1c9`）。實際UI建任務／名冊，來源公告並自動填實際port；netstat只保存對應server PID／port，確認真正UDP綁127.0.0.1，最終PID58040／port58016。兩個名冊先保持未就緒、沒有工具自動client；再用真正UI下載的四欄短票券設定啟動兩個獨立PC程序，admission／seat驗證與正常姿態入場成功。

UI Begin／Pause／End接到真正世界，來源明確Simulation。兩位各收到自己的current admission結果，耗彈／命中／擊殺／中彈／損耗0、健康100；stream／through8／world77或78及全部統計等於精確seal並ack，另raw核對finalStreamSequence皆0。helper本身仍保留allAcknowledged=null／headsets=null，不把本檢查器知道的兩個PC外推所有外部裝置或空集合成功。server非阻塞保留至少36秒，原始30秒＋最多5秒HTTP期限不改；不是送達保證、四小時或崩潰恢復。

原local模式`165936-476c7855` **49項控制台／native回歸**通過，包含任務／配置、動態名冊、AI、觀戰／回放姿態及CSV，126幀精確seal。三場均無新的原生GPU／PCM／鍵盤觀察，Chromium為SwiftShader；只是同機分開程序／loopback，不是LAN、跨機、Quest／VIVE或25台驗收。已檢視來源公告、有效玩家與結束的控制台截圖，沒有把headset分類當實機。

保留前端反例：回應與場次都缺stream時，舊比較會把undefined等同；新增負例先失敗，補非空string fence後3 Node及最後完整67／234再次通過，並重跑最終8項原生下載流程。另將下載提示改稱玩家端、external啟動提示改正；早期C stage保留，不在執行中替換其靜態資產。三個stage只差提示／fence對應JS、gzip與static-web-assets metadata，所有DLL相同；並未放寬來源、入場或測試時限來通過。

`external-runtime-validation.json`核對**3個runtime／42檔**C原件與F snapshot逐檔SHA相同，前14個runtime／345檔亦未變；保存SQLite不開連線。全部writer停後一次snapshot、保留C原件，cleanup errors／tracked child空、測試玩家程序0。最終C API及三工具**159檔**與F輸出逐檔相同；source／遊戲binary仍F、DB／journal明確C SSD，不當F USB效能證據。原5080仍0.16，未動登入／授權／安全設定，憑證／DB／journal／binary不提交。

完整11項保持active。下一步多玩家持續操作、場館流程與實際跨機，再取得Quest／VIVE／MR／廠商硬體與25台驗收；本輪不以server-only模式或APK成功替代實機證據。

## 2026-10-31：名冊旁的玩家參戰快照

前輪有實際功能與驗證進展；從乾淨`01086d7`接續新增[PLAYER_READINESS](PLAYER_READINESS.md)。**API／UI0.29**，操作員可在名冊旁直接查看有效姿態數、等待來源／中斷／過期與本次入場同步，明確標示Simulation及合成／追蹤資料。這是已接受世界幀的觀察，不是裝置在線、型號、戴好頭盔或MR／安全校正證明；沒有加Begin條件、修改射擊授權、Tracked資料、rules0.8.0或DB格式。

新增GET readiness v1端點只限Master及可讀場次的RoomController，每次顯式Actor／範圍檢查，GameServer／Internal也拒絕。只回本次名冊的狀態／admission／room／seat及來源邊界，不含姿態座標、票券或管理key。WorldRecordings用最後已接受幀的observedSequence還原當時名冊，再對照本次管理快照；相同playerId的新admission不能繼承舊frame的connected。每份報告受其sessionSequence與抽樣時點限制，不授權戰鬥。

來源時間仍header擷取UTC＋packet.elapsed，而非收到時間；未知、超前1000ms以外、過期1500ms、suspended、階段未同步或Ended皆不綠色。前端約1Hz診斷、250ms本地老化更新，從請求開始計performance經過時間，包含下載等待；登入／選擇epoch、報告序號及admission fence阻擋晚回應。沒有走REST傳逐幀頭手，沒有修改原0.5／1.5秒政策。暫停仍能有有效姿態，與場次已暫停並列，不當作正在戰鬥。

**698規則檢查**成功，新增18項含真正SQLite／歷史投影、角色／範圍、header不等於frame、source時間雙邊界、舊admission、phase／suspended／End、legacy未知時間與唯讀性。本機locked restore及隔離Release零警告錯誤，**453 HTTP／43世界串流、64 Node／229 Chromium**通過。新增7個HTTP斷言、4個Node規則及6個UI反例；UI中mock的資料明確只驗顯示／時序，不當原生證據。已檢視過期、等待及實際原生資料的控制台截圖，仍為Chromium SwiftShader。

使用同版真正Windows server／兩個headless client、全新自有API／資料／憑證，`desktop-readiness/20261031-161305-e18fecc5` **8個原生＋8個實際API資料UI檢查**通過。tool fingerprint `a474ffcd9a887bdd37919b54907415b2e3c14913eb84277e1de94a49c5e805f2`。啟動前兩個名冊body均PoseUnavailable；兩個真正程序正常送姿態後2份有效。工具只關閉自己的peer程序，該玩家變PoseUnavailable、primary仍有效；同playerId移除／重入後，frame233仍新鮮但新admission為AwaitingAdmission／None／false，不能沿用舊身體。新票券啟動新程序後，frame244兩端皆Simulated且有效。

真正瀏覽器讀未mock的readiness並完成Begin／Pause／End，End後無綠色；兩份結果均為自己原current admission，耗彈／命中／擊殺／受傷0、健康100，combat與world精確seal、pending=false、through10／world287及全部統計等於ledger並ack。這是離散觀察與兩位同機Simulation，不是每render幀／RTT／25人容量，也沒有注入姿態、射擊RPC或統計；本輪沒有GPU／PCM／原生鍵盤／頭盔觀察。

失敗保留：第一個.NET新增fixture把合成雙手留在世界原點，正常世界驗證拒絕Invalid recorded player or tracked rig；只修fixture相對身體位置，未放寬驗證。原生首場`161031-39d9192f`前六步成功，但測試瀏覽器預設dismiss既有End確認，任務仍Paused，UI20秒／工具60秒逾時；已補只對該End接受確認及顯示Ended紀錄後，重新整場成功。首次啟動browser時ready pointer尚未建立，未重開仍活著的native程序，等同一handle出現native-ready後才接上。失敗原件／cleanup／精確seal保留，不改成passed。

`readiness-runtime-validation.json`核對本輪**2個runtime／28檔**C原件與F snapshot逐檔SHA相同，前12個runtime／317檔亦未變；保存SQLite不開連線。所有writer停後才一次snapshot，C原件保留，cleanup errors／tracked child空且測試玩家程序0。新的C API及三工具副本**157檔**與F隔離輸出一致；早期stage保留，最終只有index頁尾及其gzip／兩份static-web-assets metadata四檔不同，gzip分別還原為各自HTML、其餘檔及DLL相同。不是修改舊部署來冒充新證據；資料明確C SSD，遊戲source／binary仍F，原5080仍0.16，未動登入／授權／安全設定。

**遊戲保持Unity0.31.0／code38／NGO29**，本輪未修改Unity來源／wire或重建141 Editor／雙平台。重新計算來源仍 `213b9b04e02d506c73110ba6df23109fc5ce3f14bf8f233b9d803ef8dde4777c`，原Windows／Quest receipt與Scene／prefab ID保持；不能把前輪建置當本輪新的頭盔結果。API/UI一起部署0.29，原生工具gate同步；17個既有desktop Python、語法與293官方Transport單一修補核對亦通過。

完整11項目標保持active，後續持續多玩家操作、完整場館與跨機流程；25端最大長文／並行操作、實體Quest／VIVE、MR、廠商硬體與25台仍待驗收。

功能提交 `fbb9818e30318c50fb4a835a7b65df611150d1a1` 已推送main、遠端一致。[本功能CI run41184537724](https://github.com/peca12968/vr-command-center/actions/runs/41184537724)／check124488624265實際failure、steps空；fresh annotation明示付款失敗或支出上限，job未啟動，沒有雲端測試執行／通過。未更改帳務或手動重跑，本輪上述均為本機證據。

## 2026-10-31：繁中玩家任務簡報與原生輸入

從乾淨`5d4ac95`接續，新增[PLAYER_BRIEFING](PLAYER_BRIEFING.md)。原任務庫保存的名稱／內容，現在由GameServer送至玩家閱讀；不是另建一份任務。遊戲端**0.31.0／Android code38／NGO29**，API/UI保持0.28，envelope7／world schema1／驗票2／rules0.8.0及原素材profile不改。所有遊戲程序一起更新，Prepare原位保存Scene／PlayerAvatar ID，不重建歷史。

名稱100／內容10000 UTF-16單位、最多80個FixedString512塊，不切有效surrogate pair；header1保存完整長度／塊數／SHA，缺塊、內容異動或未知版本不能成為可讀簡報。20個code point一行、10行一頁，純文字標籤原樣保留。管理更新及晚連線不重設同一頁；本地頁碼／開關沒有新增world錄影欄位，不補造舊閱讀過程。

PC用B開啟／下一頁、Escape關閉、L授權，另有面板按鈕；Quest來源使用左X／Y／握柄，實體操作仍待。閱讀只抑制自己的射擊／換彈，關閉後須放開再按；姿態繼續、全場不暫停、仍可能受傷，End戰績接管。Tracked頭手與muzzle不改，XR只新增頭部前0.9m的Canvas。不是防作弊政策或無敵模式，沒有修改碰撞、AI或命中規則。

隨附官方未修改Noto Sans CJK TC Regular2.004，commit `f8d157532fbfaeda587e826d4cd5b21a49186f7c`、OTF16,435,884 bytes；SIL OFL1.1及NOTICE隨包並可在面板閱讀，不依賴OS字型。mission-fonts-v1三份固定SHA／真正OTF cmap檢查通過，OTF／TXT與meta納入來源指紋；改版需新profile，不可重寫舊pin。不是任意emoji／罕見字涵蓋或頭盔閱讀舒適度驗收。

**真正141 EditMode通過**，新增10項涵蓋完整長文／surrogate、部分與錯誤摘要、真正NGO序列化、純文字分頁、重複管理不重設頁、按住射擊須放開、Tracked頭部不搬動、真字型／授權載入與Unity JSON內容。最後不透明底板版再次141成功；Tests門檻與UI直接asmdef參考同步更新。Unity既有nullable／audio／ServerRpc warnings保留，沒有把managed SDK當本次Editor結果。

原生`check-desktop-briefing.py`本輪同一tool fingerprint `5628896249eda2a3f81c863388a7ba069b128d3d8aaf7f05ea37acbfe439d092`，一個server及兩個client，其中第二位在Running後晚連線。Preparing先收到真正10000字、79塊；三程序完整摘要均為 `64dfb429551b908a3000927c91c6f0416b5dd9e602317b387a3be9b700c45216`，頁數51，不截斷文字來通過。

`desktop-briefing/20261031-154143-b0890b35`先完整8項通過，但原生觀察發現底板半透明、後方HUD透出。改為不透明底板、重建Windows及再次141後，最終`20261031-154501-4648aef5`重新**8項**完整通過：真正B開啟繁中第一頁及literal `<b>`、Space被抑制、B第二頁、Escape後仍30／90、下一次Space變29／90；B／L可讀官方字型來源與授權。沒有注入姿態／射擊RPC／統計。UI helper一次active-request錯誤後先重新觀察，未誤標已按鍵。

最終穩定雙玩家閱讀區間，server changed-tick診斷**405列、失效0**，兩個身體connected／ready／coherent且tick持續。此為有界取樣，不是每render幀／網路RTT或完整25人容量。主玩家耗彈1、晚連線者0，兩者健康100、命中／擊殺／受傷0，各自原admission的final／stream／combat及world最終序號與ledger一致並ack；雙精確seal、world sequence758，保存任務原文不變。probe仍240秒／64captures，普通啟動不附掛。

首次`20261031-153913-dcd7167c`等待原生按鍵時逾時，失敗run保留，不當成功。兩個成功run及失敗run共**3個runtime／88檔**原件與F snapshot逐檔SHA一致；之前9個runtime／229檔亦未變，見`briefing-runtime-validation.json`。全停writer才一次snapshot且保留C原件，僅讀JSON／logs／raw bytes、沒有在保存SQLite開連線；cleanup errors空／tracked child空，測試玩家程序0。原5080仍0.16，未替換正式DLL／資料、未操作登入或安全設定。

本機.NET locked restore／Release零警告錯誤、**680規則／446 HTTP／43世界串流**通過，另17個既有desktop Python、字型pin／cmap、語法與293官方Transport單一修補核對成功。web UI沒有修改，本輪未重跑Node／Chromium，不把先前瀏覽器數量當新結果。

兩次從F隔離輸出的HTTP檢查先失敗：競爭writer程序及invalid-key程序各未在原10秒內退出，第一個診斷還被cp950的Unicode輸出遮住；UTF-8重試仍保留逾時。未放寬timeout／認證／安全設定。把本次API及三工具輸出的原樣副本放到全新C BuildRuns後，以相同檢查通過446／43；155檔與F來源逐檔SHA一致。這是測試部署路徑的結果，不證明F延遲或AV根因已查明；新原生試跑用該C API副本，遊戲binary及source仍F、DB／journal明確C SSD，不能稱F USB效能驗收。

真正Windows receipt `2026-10-31T07:44:51.3566843Z`、Quest ARM64 IL2CPP receipt `2026-10-31T07:54:06.8782171Z`成功，source fingerprint同為 `213b9b04e02d506c73110ba6df23109fc5ce3f14bf8f233b9d803ef8dde4777c`，也與目前來源Python重算一致。原Scene `4314adcd8c63d86469d16497127d8cfb／1444571642`、prefab `6f3f36cb9d710e847b5ecc569665e1ce／5227825248646244841`保持。aapt確認0.31.0／code38、min32／target35／arm64；實際APK60,189,546 bytes、libil2cpp81,607,904及metadata9,264,256 bytes，含新簡報型別，見`briefing-apk-validation.json`。receipt totalBytes是BuildReport總輸出，不當APK大小；沒有頭盔安裝／運行證據。

完整11項長期目標保持active。本輪為兩位同機PC Simulation，尚無Quest／VIVE、MR校正、廠商硬體、跨機與25台實機驗收；25端最大長文同時入場頻寬及Android字型記憶體也未量測。後續接續多玩家持續操作與場館流程，實機控制器／追蹤與閱讀舒適度分開驗收。

功能提交 `a579ef5ec82f85024de40e23d818e7d57ce23332` 已推送main並核對遠端一致。[本功能CI run41182512425](https://github.com/peca12968/vr-command-center/actions/runs/41182512425)／check124482634848實際failure、steps空；fresh annotation明示付款失敗或支出上限，job未啟動，不能稱雲端測試執行／通過。未更改帳務或手動重跑，本輪以上均為本機證據。提交前另核對三份字型／OFL／NOTICE的Git blob SHA與固定pin相符，明確保留TXT原行尾，避免Git文字正規化破壞來源證據；沒有改pin來配合正規化。

## 2026-10-31：15分鐘原生任務、完整連續性與封存失聯

前輪有實際進展；從乾淨`524667d`接續新增 [DESKTOP_LONG](DESKTOP_LONG.md)／`check-desktop-long.py` 及 [SEAL_RECOVERY](SEAL_RECOVERY.md)／`check-desktop-seal-faults.py`。本輪只改Python工具／測試／CI與文件；遊戲仍**API／UI0.28、Unity0.30.0／code37／NGO28**、原source fingerprint `d43085f4e6b755649b5da36b0885d6b690d7042f7ce4a871a947bc2e15ede53f`、原ID與同源Windows／Quest receipt。131 Editor／雙平台、680規則／446 HTTP／43串流／60 Node／223 Chromium為前輪成功結果，本輪未重建或重跑，不當新頭盔或UI證據。

**真正15分鐘通過**：`desktop-long/20261031-143453-51928ddf`，一個Windows server／一個headless client、stationary Simulation rig，沒有附掛240秒診斷或故障代理，也未延長其限制。先由真正AI造成20損耗／1次中彈，控制者停攻擊，健康80持續保存。工具fingerprint `7d684e6225dca664259dc78f058633de59497dc8d640acf1a5554ba5f53d1e79`，原player／admission／連線不重建；原票券到期後在tick5961仍收到同一身分的有效Running快照（UTC `2026-10-31T06:39:55.097841+00:00`），這是既有連線延續，不是讓過期票券重新入場。原生client只有一次CONNECTED。

固定900秒活動時間、唯一內部mission-clock End恰好tick18000；combat與world精確seal、pending=false、玩家自己的final JSON與原admission／stream／全部統計及兩個最終序號一致並ack。live觀察8453幀及869份status、來源年齡最大0.363945秒，badActive／badAge均0；live跳過1個序號，不忽略此事，而用完整封存回放逐幀補足。

完整replay自1走到8475，其中8460個Running幀：原玩家存在、connected、rig=Simulated；停攻政策生效後健康維持80，badRunning=0，沒有無意Pause。保存擷取間隔最大681ms、>=1500ms為0，tick不倒退／不超18000，末packet及所有statistics等於精確seal。回放另以4倍速實際讀完約3分45秒。`executionFinished`與`acceptancePassed`分開，任一反例不得complete，沒有篩掉失效幀或改規則來過。

這是**本次單玩家15分鐘的保存與收到快照範圍**；source UTC age是每份收到frame／status的觀察，不是每個時間點的網路延遲／RTT／FPS，也不是原生每render幀或完整0.5秒姿態接收統計。保存幀最大681ms與全Running body有效，仍不證明已修復歷史主迴圈停頓或25人情境。15分鐘不可外推4小時／長期穩定性。

15分鐘活動與雙seal完成後，才在完整replay讀取期間開另外兩個隔離短試跑，未在900秒活動量測中增加第二個原生負載。每場真正一server／一client，先AI造成20損耗／健康80，再Pause及操作員End；工具fingerprint `e0592a83cc72db0715dd50821d73b5db5c121813ea3155e6ade8a8e33a234bb1`，每場**8項**通過：

| desktop-seal-faults／20261031場次 | 模式 | 故障總秒／pending觀察秒 | 實際拒絕 | API狀態與CSV | 完整回放 |
|---|---|---|---|---|---|
| 145042-77e7c9b1 | combat-seal | 8.844／8.344 | 40次503 | combat未seal／pending=true／world未complete／CSV409 | 32幀 |
| 145100-e505c83d | statistics | 8.703／8.063 | 31次503 | 雙seal／pending=false／CSV可匯出，玩家仍pending | 32幀 |

兩種模式都至少8秒維持玩家pending，未接受final、未提早斷線；恢復後原請求重試、自己原admission的非零受傷結果／所有統計／stream及最終序號正確並ack，無DEBRIEF_TIMEOUT。CSV的session／player／room／origin／stream／through／finalStream及7項戰鬥數值、整段回放與ledger逐值一致。CSV既有政策是Ended＋combat seal，玩家final另須world seal及GameServer取得統計；依原契約分辨，沒有把已封存數字錯標pending或提前顯示final。

代理只新增`combat-seal` POST503及`statistics` GET503，原management／publication邊界保持；10項代理測試含舊8回歸及新2分流。8連線／HTTP1MiB／response2MiB／opaque WS64KiB、20秒fault／240秒life及non-daemon handler join均維持。兩場route／handler／capacity錯誤0、無自動上限、收尾tunnels0；不記payload／token／key，不注入姿態／武器／統計，不改OS／安全設定。舊試跑保持其原tool fingerprint，不覆寫歷史。

**49 Python**通過（原36 desktop＋新3 long連續性＋10 gate）；語法／293官方Transport單一修補亦通過，CI新增3項與兩個入口語法。本輪沒有新的.NET／Editor／APK／瀏覽器／GPU／PCM／鍵鼠／頭盔結果。native三場各自新資料／憑證，來源全Simulation，不把名冊Quest3標籤當接了頭盔。

`long-seal-validation.json`核對本輪**3個runtime／42檔**原件與snapshot SHA逐檔一致，之前6個runtime／187檔亦未變；僅JSON／logs／raw bytes，沒有在保存SQLite上開連線。資料明確C SSD、source／binary仍F，全停writer才一次回F且原件保留；三場cleanup無錯／tracked child空、原生玩家程序0，正式5080仍0.16。未操作Unity登入／授權／安全設定，沒有資料／憑證／binary提交。

完整11項長期目標保持active。這次通過一位同機PC的900秒與兩個可恢復約8秒故障，不是多玩家長期、25位持續操作、跨機、完整API／server崩潰、封存超過玩家期限或Quest／VIVE／MR／廠商硬體驗收。後續優先增加多玩家持續操作與更長／封存期限情境，實機項目分開保留。

額外raw JSON稽核也核對三位原生final的finalStreamSequence等於最後世界packet的throughCombatSequence、worldSequence等於精確acceptedSequence、throughSequence等於ledger；900秒End的actor確為mission-clock且證據tick18000。此與上述SHA核對一併記在long-seal-validation，未重開保存SQLite。

功能提交 `60bc110527d02caaeabb869125d942a94bcf9762` 已推送main、遠端一致。[本功能CI run41178736259](https://github.com/peca12968/vr-command-center/actions/runs/41178736259)／check124471590845實際failure、無步驟啟動；fresh annotation為付款失敗或支出上限，沒有雲端測試結果。未改帳務或手動重跑，本輪以上均為本機證據。

## 2026-10-31：管理與發布分通道失聯、原生計時恢復

前輪交付屬實際進展；從乾淨`0d39885`接續驗證 [CLOCK_RECOVERY](CLOCK_RECOVERY.md)。新增 `venue_http_gate.py` 及 `check-desktop-clock-faults.py`，本輪只改Python工具／測試／CI與文件。**遊戲仍API／UI0.28、Unity0.30.0／code37／NGO28**，原source fingerprint `d43085f4e6b755649b5da36b0885d6b690d7042f7ce4a871a947bc2e15ede53f`、Scene／prefab ID及同源Windows／Quest receipt保留。131真正EditMode、680規則／446 HTTP／43串流／60 Node／223 Chromium為前輪成功證據，**本輪未重建或重跑這些套件**，不當作新的頭盔或瀏覽器結果。

只把自己新建的Unity server指向本機代理；client NGO UDP不經代理，操作員觀察及命令直接到自己新建的API。先只拒絕同session管理GET，combat／world仍可發布；真正source保存suspended=true／Paused，原生server複本Ready=false／tick不變，而API管理狀態仍Running。這不是操作員Pause事件。恢復管理後原政策／同一場次接續，沒有重設倒數。

再於期限前約5秒關閉自己world tunnel並拒絕publish upgrade，保留管理與combat HTTP。真正server及client的既有NativeReplicationProbe觀察local tick恰好期限、Ready=false且phase仍Running；API接受序號固定在期限前、管理仍Running。本地到期待接受再維持6.5秒，證明沒有拿未發布時間直接End。恢復publication後原publisher重連同源補送，API才保存唯一mission-clock End；雙seal、pending=false、自己的原入場final JSON／所有統計及序號均一致，client ack後斷線。

同一tool fingerprint `9a842da5ebd55a0cff0d8ca839fda590e4422420206c06707d25e4308a0895d9`，兩個全新獨立runtime、每場一server／一headless client、Simulation頭手，各**8項**成功：

| desktop-clock-faults／20261031場次 | 秒數／凍結tick | 管理失聯總秒／停表觀察秒 | 發布失聯總秒／本地到期待接受秒 | API未接受邊界tick | 完整回放 |
|---|---|---|---|---|---|
| 142318-373dc579 | 60／1200 | 6.141／5.766，tick104固定 | 12.281／6.531 | 1100 | 726幀、60個suspended、85個到期Running |
| 142458-06088e37 | 180／3600 | 6.094／5.750，tick105固定 | 12.297／6.547 | 3502 | 1851幀、59個suspended、87個到期Running |

完整SSE從1走至最後，tick不倒退／不超過期限，末packet與所有statistics等於精確seal；包含暫停幀與到期仍Running等待End幀，不把到期本身冒充已封存。兩場各一次內部End、原stream／設定序號／原admission一致，正常結果的來源為Simulation；combat ledger原本零事件仍保持原null來源，不補造事件。時間含HTTP、取樣及輪詢，不是RTT、FPS或新的期限；未量測完整0.5／1.5秒連續性，不宣稱修復原主迴圈停頓。

每場各一個既有WS被關閉，分別12／12次管理GET回503、23／23次publication upgrade被拒，均2次成功WS連線（初次與恢復）。代理route／handler／capacity error全0、沒有自動block／lifetime上限、收尾active tunnel0。只有同一session所需路由，最多8連線、HTTP1MiB／response2MiB／opaque WS每塊64KiB；故障20秒／代理240秒固定上限。只在記憶體轉送原認證／body與不解析的WS bytes，不保存payload／票券／key，不注入姿態／射擊／RPC，不動OS／防火牆／安全設定。這不保證某個特定ACK曾被丟棄，亦非部署代理或認證邊界。

**44 Python**通過：8項新代理測試（實際loopback HTTP／opaque TCP tunnel、分通道、轉送body／認證、容量、body／scope拒絕、自動故障與lifetime上限、HTTP worker收尾等待）加36項既有desktop，不是原生試跑次數。語法及293官方Transport單一修補核對通過；CI新增8項與語法。最初6項測試中3個錯誤先指出HTTPConnection不支援context manager，改用contextlib.closing後通過，再補lifetime及HTTP worker案例為8；這是工具錯誤，未修改Unity／API或放寬規則來通過。

早期 `141303-3bc506ce`／`141505-ca55d190` 的計時與補送均通過，但代理只等待listener／watchdog，未明確等待HTTP處理執行緒，保留為舊scope，不當最終收尾證據。現改為non-daemon request handlers，server_close等待所有處理執行緒，新增真正in-flight HTTP等待反例；重新60／180秒兩場為上表最終結果，未改Unity／API。

所有probe均complete且未truncated／send queue error，finish在正常client斷線及固定240秒前；本輪沒有GPU／PCM／Windows輸入／頭盔觀察。probe僅讀真正本地複本，不讀仍有exclusive lease的world journal，也不把診斷來源變成Tracked。180秒是有界較長運行，**不是15分鐘、4小時或長期穩定性通過**；沒有改probe上限來湊證據。

資料明確C SSD、source／binary在F，全停writer後一次snapshot回F、原件保留。`clock-recovery-validation.json`核對本輪**4個runtime／159檔**原件與snapshot逐檔SHA一致，前輪兩個clock runtime／28檔亦逐檔未變；只讀JSON／log／raw bytes，未在保留SQLite上開連線。cleanup errors空且無tracked child；原5080仍0.16，Unity serve／原授權與安全設定未動，憑證／資料／binary不提交。

限制與下一步：這只證明一位同機PC在指定管理503／world連線中斷、60及180秒活動期限的恢復，不是整個API重啟、server crash、封存中斷、跨機、25位持續操作或Quest／VIVE／MR／硬體驗收。完整11項長期目標保持active。下一步獨立驗證更長任務及封存階段失聯，不用本工具240秒診斷替代長期驗收。

功能提交 `96f86d5a13f2793ba44f721b6859e0479ade0451` 已推送main、遠端一致。[本功能CI run41176835936](https://github.com/peca12968/vr-command-center/actions/runs/41176835936)／check124466037718實際failure，無步驟啟動；fresh annotation明示付款失敗或支出上限，沒有雲端測試結果。未更改帳務或手動重跑，本輪上述檢查為本機證據。

## 2026-10-31：選用任務活動倒數、到期 End 與兩房原生驗證

從乾淨 `336410b` 接續原始任務「時間」需求，新增 [MISSION_CLOCK](MISSION_CLOCK.md)。API／UI **0.28**、Unity **0.30.0／code37／NGO28**。操作員只在 Preparing 明確選用自動結束；新舊場次預設手動，不把既有 DurationSeconds 靜默改成期限。開始後政策及任務秒數不可變，規則仍0.8.0，原素材 pin／舊資料讀取／原始 binary header及checksum保留。

計時為原 ArenaWorld 20Hz 活動 tick，不是 UTC 或不中斷牆鐘；Preparing／Pause／管理中斷停表，主迴圈卡頓可使活動時間慢於現實。到期 ArenaSession 不再 tick、射擊／換彈或建立新遊戲 binding；Unity 強制保存邊界並持續發布。API 250ms服務只從已接受的同源世界幀確認版本、設定序號與期限，以固定內部 mission-clock 身分提交正常 End，再走原雙 journal／精確 seal／個人戰績 ack。未發布的本地時間不能授權 End，HTTP 沒有 Internal 捷徑；API失聯時只凍結等待，不能聲稱已結束／封存。手動 End 可先勝出，不追加第二筆。

新寫入事件 **envelope7，讀1–7**，SetMissionClock／source capability／自動End證據持久化。新 header missionClockVersion1與保存任務秒數由API獨立核對；world schema1、驗票2不變，不代表可降回舊reader。Prepare原位升28、原Scene及PlayerAvatar ID保持；API／UI／全部遊戲程序須協同更新。原5080仍0.16，不拿新來源接它或替換歷史。

**真正 Editor 131 EditMode**通過（6項新增：邊界／NGO序列化／HUD／Pause凍結／Unity null預設手動／header能力）。Windows receipt `2026-10-31T05:56:16.0212938Z`，Quest ARM64 IL2CPP receipt `2026-10-31T06:05:38.2561465Z`；同一來源 fingerprint `d43085f4e6b755649b5da36b0885d6b690d7042f7ce4a871a947bc2e15ede53f`。原Scene `4314adcd8c63d86469d16497127d8cfb／1444571642`、prefab `6f3f36cb9d710e847b5ecc569665e1ce／5227825248646244841`未變。aapt確認0.30.0／code37、min32／target35／arm64，實際APK46,416,866 bytes，包內libil2cpp81,313,216及metadata9,259,300 bytes，含MissionClockState；見clock-apk-validation.json。receipt totalBytes為BuildReport總輸出，不能當作APK實際大小。建置不是頭盔運行證據。

本機隔離 .NET locked restore／Release零警告錯誤、**680規則、446 HTTP、43世界串流**通過。**60 Node／223 Chromium**全回歸成功，另有 **13項**新時間控制／真正native錄製觀戰／最終結果核對，最後提示文字更新後再次13項成功。瀏覽器為SwiftShader，沒有當作原生GPU。17項既有desktop debrief／snapshot Python及語法、293官方Transport／單一修補核對通過；本輪未重跑25端容量。

真正Windows兩個獨立server／每房一個client，`desktop-clock/20261031-135731-313ea995` **8項完整通過**。60秒自動房Pause在tick103，35.157秒內每次採樣不變；恢復後恰好tick1200停表，只有一筆schema7／mission-clock End及同源證據。手動房在tick1906仍Running，未自動加政策，手動End在tick1927。兩場world complete／pending=false、兩位個別結果均ack。整段回放自動947幀／手動952幀，逐幀連續、auto無tick>1200，末統計等於精確ledger。

computer-use實際視窗觀察：Paused REMAIN00:55，真正Space後仍30／90、耗彈0；Running後Space變29／90，依序見00:47與00:16，最後看到自己的SEALED RESULTS、耗彈1／健康100／0%並斷線保留。沒有注入姿態／命中。額外觀戰工具只在C建立新的audit copy，從該副本啟動自己的API；13項核對新header活動時間為自動01:00／計畫01:00、手動01:36／計畫01:00，兩位final JSON的session／player／admission／room／stream／combat與world序號及全部統計一致。沒有在保留的原件／runtime-snapshot上開SQLite。

資料明確在C SSD，source／binary在F；所有writer停止後才回F一次副本。`clock-runtime-validation.json`核對本輪**2個runtime／28檔**原件與snapshot SHA逐檔相同、cleanup errors空且無tracked child；含原生工具初次失敗場次。正式5080／原Unity serve、授權、安全設定未動，沒有憑證／資料庫／binary提交。

保留檢查器失敗：首次瀏覽器用UI編輯前的隔離輸出資產，缺clock欄位，重新build資產；第二次把fieldset拿Playwright isDisabled判斷，改讀真正DOM disabled；第三次未等非同步refresh更新政策文字，加入對應渲染等待。最後完整回歸通過，這些不當作遊戲故障。原生 `135715-168b5367` 使用錯誤start_clients方法名，改成既有clients，失敗原件／seal／清理亦保留。未改規則、期限或放寬權限來通過。

限制：本輪兩位同機PC Simulation與明確暫停／到期案例；非25人同步操作、跨機／頭盔／MR／廠商硬體、長任務或API／server崩潰恢復驗收。原主迴圈停頓亦未證明修復。完整11項長期目標保持active。後續優先驗證計時期間管理／發布失聯與長任務，取得設備後另驗Quest追蹤、控制器、效能及VIVE相容。

功能提交 `3d90c9b8221b49825f11a984d14c8a3af85156e0` 已推送main並核對遠端一致。[本提交CI run41175253162](https://github.com/peca12968/vr-command-center/actions/runs/41175253162)／check124461355970實際failure、無任何步驟啟動；fresh annotation明示付款失敗或支出上限，不能稱雲端測試執行／通過。未更改帳務或手動重跑；以上為本機證據。

## 2026-10-31：End入場延遲、結果丟包與真正期限回歸

前輪交付及推送屬實際進展；本輪從乾淨`34ee9f7`接續驗證尚缺的結束競態。新增[DESKTOP_END_NETWORK](DESKTOP_END_NETWORK.md)／`check-desktop-end-race.py`及只供本輪自有client的`udp_gate.py`。最初推測剛approved的玩家可能因client尚未就緒而丟失結果，但第一個真正延遲實驗實際收到正確結果，**不以未重現的假設修改遊戲端／NGO協定**。

遊戲仍Unity0.29.0／code36／NGO27、API UI0.27，source fingerprint仍`a97b40a2836de7a8c5e8e64596b37feac3d545438a4538df4d403f5d73c4e9d3`，Windows／Quest receipt與原ID不變；125 EditMode及同源雙平台是前輪成功證據，**本輪未重建或重跑Unity／APK**，不是新的頭盔證據。rules0.8.0／資料格式／原資源與所有歷史保持。

兩個真正無圖形Windows client，一位直連、一位只經自己的loopback gate；server及API／世界發布不經gate。合法名冊先加入兩位再Begin，第一位先由真正AI造成中彈2／損耗40／健康60，第二位健康100，因此不能用另一人的結果混過。只延遲或丟棄原始UDP datagram，不注入RPC／姿態／武器／命中，不讀封包內容、不寫PCAP或payload。只綁127.0.0.1及自有server port，固定一個client endpoint，其他sender丟棄；不改MTU／0.5或1.5秒門檻／安全設定。

最終三場同一tool fingerprint `78ebb1f8ca3b7d580b0be3e6aba346a3501d240f19d2b3ec0d6daa94293a1bf8`，每場**6項**通過：入場及故障時機、正常peer自己的雙seal結果、延遲者結果或阻斷期間無final、Ended拒絕且ledger不變、combat stream尾界、整段回放連續且末packet／statistics完全相同。`complete=true`僅在gate停止及自有writer全停／snapshot成功後寫入，工具來源途中變動或自動queue／hold上限觸發都不能passed。

| desktop-end-race／20261031場次 | 模式 | 實際觀察 | 完整封存回放 |
|---|---|---|---|
| 131131-86bb1cda | join-delay | server已approved、client無CONNECTED log時End；暫存320包、188265 bytes，hold1.969秒，seal後釋放；兩人各自正確結果及ack | 37幀、末packet／statistics逐值相同 |
| 131140-00678de7 | result-drop | client先接受pending，再丟5033包下行；hold29.860秒，從End要求起30.578秒觀察connectionReleased，阻斷期間無final，解除後也無final | 37幀、同上；正常peer結果正確 |
| 131218-71180c22 | result-large-drop | pending後丟大於64 bytes的436包，33個較小datagram通過；hold30.218秒，End要求起30.688秒觀察DEBRIEF_TIMEOUT，阻斷及解除後無final | 37幀、同上；正常peer結果正確 |

64 bytes只按長度篩選，沒有把所有小包稱為keepalive。connectionReleased不指定未量測的傳輸根因，與明確的應用層DEBRIEF_TIMEOUT分開；觀察時間含HTTP及輪詢，不是修改後的遊戲期限、每包延遲、RTT或FPS。兩個loss場都先真正CONNECTED／接受pending，才啟用故障。延遲入場者End世界的connected=false／rig=None，未偽造參戰或Tracked，也不能從無CONNECTED log推定avatar尚未spawn；另一位為Simulated。新的Ended連線使用原票券仍被拒且收不到debrief；離線稽核確認拒絕時票券尚未過期，非拿過期冒充Ended拒絕。

所有三場world complete／pending=false／活動0、最終stream／序號與ledger一致；完整SSE回放從1走至37，封存不因client丟包變動。原生沒有新GPU／PCM／UI觀察，只有headless日誌與授權API／回放。**45 Python**為9項真實kernel UDP／有界／順序／單client／下行loss／長度篩選測試，加36項既有desktop規則，非45次原生試跑；語法與293官方Transport／單一修補核對亦過。CI新增這9項與語法步驟，沒有改或重跑後端／全瀏覽器／25端容量。

失敗與舊scope均保留：`125615-c80e9bcc`檢查器誤在Running加名冊被HTTP409拒，改為合法Preparing加入、Running才連線，未放寬政策；`125634-01b64006`原expect-missing假設失敗，結果其實正確，未宣稱遊戲bug；`130124-e1e5386a`過早數ack，把client先記final、server稍後才ack當失敗，改為獨立有界等待；`130402-fb6fc5e9`硬等應用期限，但實際先connection release，舊failed保留，現將兩個結果分型。`130355／130720／130756`先前成功只屬舊scope，未含整段replay／tool fingerprint，不當作最終三場。UDP工具初期drop位置及非原子計數假設由unit測試先擋下，修正後9項全過，未修改Unity Transport來源。

隔離資料明確C SSD、source／binary在F；全停writer才複製回F，未移動原件。`end-network-validation.json`覆核本輪**10個runtime／140檔**原件與副本SHA逐檔相同、cleanup乾淨，前輪20個runtime的保存manifest亦逐一未變。只讀JSON／log／原始bytes，未開SQLite。正式5080仍0.16歷史服務；Unity serve／登入／安全設定未動，沒有憑證／payload／binary提交。

功能提交`56b667b9872557fd9f2aa4a0f8de503834a17748`已推送main並核對遠端。最新[CI run41172328133](https://github.com/peca12968/vr-command-center/actions/runs/41172328133)／check124452732120實際failure、steps=null；annotation仍明示付款失敗或支出上限，job未開始，沒有雲端執行結果。未改帳務或重跑，以上測試為本機證據。

限制：這只驗兩個同機Windows client、選定的一次延遲與兩種loss，不是所有時序／重排、25位同時操作、跨機、頭盔／MR或完整故障／server crash驗收；封存連線中斷及長任務仍待。完整11項長期目標保持active，原主迴圈偶發停頓亦未證明修復。

## 2026-10-31：玩家End戰績、零事件修正與一般PC入口

新增[DESKTOP_DEBRIEF](DESKTOP_DEBRIEF.md)：Unity **0.29.0／code36／NGO27**，API／UI仍0.27，驗票2／rules0.8.0／歷史錄製與素材格式不變。End立即解除遊戲binding，只有原名冊player＋admission＋room＋seat相同的既有連線可等待自己的結果。combat及world journal都精確seal後，GameServer以原有認證statistics路由讀ledger，可靠target RPC只傳該玩家，含來源／session／admission／stream／最終序號；ack後斷線。Host須等peer結束才處理自己的ack／shutdown，不讓主持人先切掉其他結果。移除／換席仍立即撤銷，Ended不接受新入場，玩家不持有管理key。

PC先顯示等待封存，再顯示耗彈／命中／擊殺／中彈／損耗／健康／命中率及來源。結果留在bootstrap，avatar despawn／斷線不清除，真正Reconnect才清除；Ended停止姿態送報且結果接管HUD，不移動Tracked資料。無final只顯示未確認；等待30秒，正在進行的HTTP最多再5秒。沒有新增client永久結果檔，伺服器報表／回放仍保留。Android等候標籤接相同文字，無頭盔排版／操作驗收。

**找到並修正零事件漏測**：原練習場會先停client再seal，無法看結果；改為等送達後，`desktop-practice-checks/20261031-122249-c933da43`原27項仍通過，但五人／一人／兩人三場都只有pending，30秒後8人全部timeout，allAcknowledged=false（43／39／591世界幀）。精確報表封存不等於玩家收到結果，原passed只屬舊檢查範圍，結果及原件保留。真正EditMode新增API JSON `origin:null`反例，125項中1項失敗、訊息`JsonUtility null origin was []`，XML及log在`debrief-null-regression-*`。Unity把null string讀成空字串；現僅允許已封存、final combat sequence=0、全名冊零事件且健康100，來源取綁定stream，不補寫API的null combat origin。非零串流或任何玩家有事件的缺失來源仍拒絕。修正後 **125項真正EditMode全過**，新增共11項身分／序號／來源／不可覆寫／真實JSON驗證；Tests門檻125。

最終fingerprint `a97b40a2836de7a8c5e8e64596b37feac3d545438a4538df4d403f5d73c4e9d3`；Windows receipt `2026-10-31T04:29:48.3629507Z`，Quest receipt `2026-10-31T04:42:20.0862064Z`，同源ARM64／IL2CPP APK成功。aapt為0.29.0／code36、min32／target35／arm64-v8a，實際46,486,635 bytes；包內有81,279,680-byte libil2cpp、9,257,336-byte metadata及新debrief型別（不是實機執行證據）。原Scene `4314adcd8c63d86469d16497127d8cfb／1444571642`及prefab `6f3f36cb9d710e847b5ecc569665e1ce／5227825248646244841`保持，Prepare不重建ID，所有遊戲程序一起更新。

最終來源的原生證據（全為同機Windows、Simulation）：

| 20261031 artifact場次 | 範圍 | 世界幀／結果 |
|---|---|---|
| desktop-debrief/123041-bbe00436 | Begin前取消、4項 | 27幀；兩位零事件結果ack、Ended舊票券拒絕 |
| desktop-debrief/123047-12e8f352 | Host＋peer、4項 | 27幀；玩家一中彈1／損耗20／健康80，peer100；peer ack先於host shutdown |
| desktop-debrief/123052-2b34dd7e | dedicated server、4項 | 27幀；兩份不同結果與精確combat／world seal一致；移除者與Ended舊票券無結果 |
| desktop-demo/123058-1411a4e3 | 一般啟動器、真正GPU／Space及另列5項觀察 | 241幀；耗彈1／命中0／0%／健康100，peer全零；兩位ack、保留畫面、Reconnect清除及票券拒絕 |
| desktop-practice-checks/123148-24d21ff8 | 更新為30項、五人／一人／兩人 | 43／43／589幀；End、end.request、60秒到時均逐位收到並ack、精確seal／CSV／cleanup一致 |
| desktop-venue/123338-129116cb | 控制台49項UI／native，兩位在場及一位離場歷史 | 135幀；兩位結果ack，任務／配置／名冊／聲光設定／AI／觀戰／封存回放／CSV通過，Chromium SwiftShader另列 |
| desktop-venue/123517-5aebaf1b | 操作員工具兩連續場及4項真正GPU觀察 | 55／123幀；第一場結果仍在90秒保留期時新玩家開啟新Preparing視窗，第二場獨立結果；兩場各一位ack |

一般練習場及操作員入口新增`--results-seconds 0..300`（預設30），先等結果ack／斷線再處理保留畫面；操作員的保留期限不阻塞其他房間，新可見玩家優先取代舊結果。關閉結果或`dismiss-results.request`可提早結束保留。`*-player-results.json`將送達、只有斷線、關窗、逾時及空集合分開，空集合不當成功。送達結果以本場次cache固定，保留期限清掉程序後不能以空集合覆蓋已確認的receipt；新增單元反例與`desktop-venue/124502-969f19e5` results-seconds0／21幀及退出後receipt SHA一致。seal只要求自己API／authority存活，已正常關閉的玩家不阻止精確保存；一般等待仍檢查全部必需程序。

同源`unity-admission/20261031-123655-db6519b6` **8項／367幀**通過：重複入場、撤銷、同ID新epoch、舊移除與票券、舊client遲退出、真正transport釋放後同admission重連的已接受位置／健康／彈藥，以及Ended拒絕／封存；這次為無圖形回歸，不補稱0.65公尺實際鍵盤。**36 Python**（8 active＋11 capacity＋5 artifact＋12 debrief／入口生命週期）、語法及293官方Transport／單一修補核對通過。API／UI來源未改，未重跑全後端／201 Chromium／25端容量或PCM／FPS。已檢視本次operator-ui/final-report.png；軟體WebGL不是原生GPU證據，原生結果與新場視窗另以computer-use觀察。

隔離runtime全部明確C SSD，來源／binary仍F；全停writer後才一次複製回F，保留原件，未開SQLite作稽核。`debrief-final-validation.json`覆核**20個runtime、280檔**，原件／副本逐檔SHA一致，最終來源10個runtime（含上述三個練習場）皆乾淨；之前七場已保存manifest也保持不變。早期`120744-0024ac98`因工具誤用description而非必要briefing在HTTP400停止、未啟動遊戲，12檔保留。其餘早期UI修正前`120754／120804／120817`與零事件修正前`121037／121044／121053`各14檔保留；後三場fingerprint `002550...`與其8項／382幀重連不是最終來源。早期HUD曾有POSE REJECTED及斷線Preparing小框，已由最終畫面修正；不重寫舊passed或把舊receipt當新建置。Host早期summary的最後label過廣，debrief-result始終正確區分host shutdown與dedicated票券檢查，現由同一checks陣列產生摘要。原5080歷史服務與Unity serve／登入／安全設定未更動。

功能提交`c4917b6d70fc9e75e4f0361876a445e2d8d9dc32`已推送main、遠端一致。最新[CI run41170023324](https://github.com/peca12968/vr-command-center/actions/runs/41170023324)／check124445771935實際failure、steps=null；annotation明示付款失敗或支出上限，job未開始，不能當作雲端測試失敗或通過。未改帳務／重跑，以上為本機證據。

限制：本輪兩位結果接收及最多五位無圖形練習場，未驗25人同時操作、跨機、Quest／VIVE實機、MR或廠商硬體。真正零事件bug曾觸發30秒timeout，但這不是刻意丟包／斷網／封存中斷的完整故障驗收。近End入場競態及更長任務仍待；原主迴圈偶發停頓未證明修復，完整11項長期目標仍active。

## 2026-10-31：真正W／Space／R／Space與25端回放，補全程失效檢查

從乾淨`d39bd9e`接續PC動態操作。新增[DESKTOP_ACTIVE](DESKTOP_ACTIVE.md)／`check-desktop-active.py`，使用既有Unity0.28.3／code35／NGO26及API UI0.27，**一位實際操作、24個接收端**，一個真正GPU視窗及24個nographics程序。使用computer-use真實按鍵，無測試RPC／姿態／武器注入。合法油桶配置使實際候選網格把Room3靶位安排在(-3,0,-1)，不直接指定NPC位置、不改rules；W實際前進0.05公尺，Space命中50傷害、R補至30／89、第二發擊殺至29／89。主玩家耗彈2／命中2／擊殺1／100%、健康100；其他24人的頭位、彈藥／射擊及統計未被本玩家輸入改動。

第一個`desktop-capacity/20261031-111719-325e1088`舊版檢查器exit0、8功能項／130快照／518世界幀／6個回放參考／CSV一致，原始passed與248檔SSD-F副本保留。但逐列稽核發現**65筆Running失效列**，所有26份報告皆不符後加的全程條件：39列connected16／25、26列24／25，玩家數仍25／健康總和2500／Ready且coherent。server在tick242、244觀察16位，246為24位後恢復；最多本地新tick觀察空窗**0.9258025秒**，最大擷取UTC來源年齡0.569364秒（仍低於原1.5）。這是權威可參戰旗標短暫失效，不能單憑此斷言NGO連線已斷、是哪位玩家姿態／哪段CPU或GPU原因；不把後來的成功快照當作全程成功。稽核`active-first-continuity-audit.json`明示26份皆不通過，未改舊結果。

因此新增嚴格條件：各完整report從初始成功capture起的**所有觀察Running列**須25人／connected25／健康2500／Ready／coherent，同一Running區間相鄰新tick觀察<1.5秒；刻意Pause另列。SSE回放逐序號走完整封存錄製，初始至最後參考間每張保存Running幀亦驗全名冊／Simulated／可參戰，所有保存參考packet與statistics逐值相同；任一失效不能以後續恢復洗掉。這不是每packet、所有瞬間或網路RTT的證明，原0.5秒姿態及1.5秒來源門檻保持。失敗時active-result不改成complete，只有cleanup後成功才passed。

快照輸出從原同時26份改為預設`--capture-batch 1`，逐端要求／等待，同epoch共用參考tick下界、不稱同瞬間。可明確26重現fan-out，不刪失效列、不修改遊戲或放寬條件。新增自己`desktop-active` artifact family與pointer，不覆蓋靜態capacity入口。對照`--without-replication-probe`只檢查權威／回放、`localReplicaContinuityChecked=false`，空集合不算接收端證據。

| desktop-active／20261031場次 | 終態／範圍 | 保存幀／回放參考 | 最大來源年齡 | SSD-F檔數 |
|---|---|---|---|---|
| `112924-5da663bb` | exit1，無probe末發UI等待逾時，三步完成 | 869／未完成新回放核對 | 不作成功時序證據 | 14 |
| `113205-3d172a38` | exit1，無probe末發UI等待逾時，三步完成 | 913／未完成新回放核對 | 不作成功時序證據 | 14 |
| `113444-5c76154c` | exit0，無probe **9項權威／回放對照** | 1127／6 | 0.159532秒 | 14 |
| `113854-7e7d5f31` | exit0，分批probe **9項含全程／接收端檢查** | 966／5 | 0.167574秒 | 248 |

最後分批場26份report完整、**130／130快照**通過，共20658列，其中初始capture後**19916個Running觀察列全符合條件**、本地最大相鄰新tick間隔0.1445342秒，server最後觀察Ended。所有保存Running幀檢查通過，最終CSV25人逐項對ledger／精確尾端，SHA `5bad592a232c48ffe4eb3542116e655d5cba715ebb941c23f1037a6b99c2de07`；兩個完成場raw send queue full皆0。最低抽樣可用實體記憶體分別7,771,242,496／6,481,555,456 bytes，原2GiB保留未觸發。無probe場沒有各端快照／report，最後確認訊息當時沿用「world and local replicas」文字過廣，實際只判world與空本地集合，metadata明確false；已將後續訊息改為world only，未補造資料。

兩個中斷場都在確認畫面／恢復焦點時超過30／40秒的**操作員等待**，不是量到同長的網路延遲。曾收到不符遊戲的截圖，重選唯一自有window／activate後恢復正確畫面，沒有對非遊戲畫面輸入；第一場UI呼叫失敗後我誤寫kill.done，predicate沒有接受，未計擊殺或成功。後續改為呼叫成功、觀察正確畫面後，另一步才寫ack；無probe對照可用90秒等待，僅增加觀察／UI恢復時間，不改網路或姿態門檻。完成對照中的首次R呼叫結果未明，重新觀察29／90後一次重試並確認RELOADING，最後數值30／89及29／89符合；不把未知呼叫當成功。所有中斷場仍精確seal、cleanup無錯誤無殘留，failed及原件保留。

兩個成功／兩個中斷場的全部tracked writer停止才一次回F，原件／副本bytes SHA逐檔一致、稽核前後不變；first場248檔亦已核對。只讀JSON／CSV／bytes，未開原或snapshot SQLite、未重寫副本。摘要`artifacts/active-validation.json`、`active-first-continuity-audit.json`、`active-final-validation.json`。25程序source／binary仍F、新runtime明確C SSD，非F USB全資料或跨機。原5080唯讀仍0.16歷史，Unity serve／登入／安全性設定未碰。

**8 active規則／全程反例＋11容量＋5 artifact，共24項Python**與語法通過，CI新增active入口；不是24次原生試跑。只有Python／CI／文件變更，C#／資產／API UI與資料契約保持；目前來源fingerprint仍`e8ae6d846dc014e48984a035f2960c043d342a4fe192ff0feaae3891973ba3d0`，兩平台既有receipt及原scene／prefab ID一致。本輪沒有重建／重跑前輪114 EditMode或Quest／Windows，未重跑後端／全瀏覽器／49 UI native／27練習場／8重連，不混算。視窗觀察確實看見血條減半、RELOADING、30／89、敵軍移除與29／89；沒有新原生GPU讀回／PCM／FPS或聽感證據。

這組fan-out／無probe／分批比較不足以證明診斷I/O、GUI觀察、GPU、GC、排程或舊主迴圈停頓的根因，**不稱遊戲端全局修復**。它補足真實操作到25端資料／保存回放的證據並消除只看檢查點的漏洞；`all25SimultaneouslyActive=false`及`networkCapacityAccepted=false`。持續25人同時操作、更多場景／長任務、跨機／Wi-Fi、MR／Quest／VIVE／廠商硬體仍待，完整11項與長期目標保持開發中。

功能提交`2cdaa1fd8955166392f2708d14481822f1e701ee`已推送main、遠端一致，提交後來源fingerprint重算仍e8ae6d846dc014e48984a035f2960c043d342a4fe192ff0feaae3891973ba3d0。GitHub #1保持open，原11項及歷史封存連結保留，更新後獨立讀回本文逐字一致。[功能提交CI run41166328563](https://github.com/peca12968/vr-command-center/actions/runs/41166328563)／check124434582620實際failure、steps=null；annotation明示付款失敗或支出上限，工作未開始，沒有雲端測試結果。未改帳務或重跑，本機證據獨立保存。

## 2026-10-31：各玩家端複本證據與伺服器packet池

從乾淨`22c432c`接續前輪105行send queue full，完整目標保持開發中。新增[DESKTOP_REPLICATION](DESKTOP_REPLICATION.md)：明確`--replication-probe`只在Windows Development的自有程序觀察真正本地NGO狀態，普通／Editor／Android不安裝。240秒／4096 tick列／4096錯誤／64次capture有界，保留最早資料；穩定期不逐幀寫檔，明確要求才輸出唯一快照，finish取消threaded log訂閱後一次report。無測試RPC、輸入／姿態注入、PCM／GPU、讀他程序記憶體或OS設定變更。

每client／server五個檢查點（Running起點／60秒後、Pause、Resume、AI傷害後全Pause），核對實際收到的玩家／敵軍ID、房間、健康／彈藥／敵軍fireSequence、位置、avatar connection／owner、Simulated／accepted及Presentation／Actor tick。快照不早於自己的API參考tick；追趕失敗快照保留、不覆寫。起終點間每一筆本地新tick觀察亦須全名冊／健康100／coherent，含端點新tick間隔<1.5秒。這是端上觀察間隔，不是RTT、每packet送達、每張世界幀在所有client顯示或同一瞬間的跨端快照。client在End前明確finish，**不驗每client收到Ended**；server在精確seal後才finish。

0.28.2／code34僅作中間Windows診斷版，保留原driver128，沒有建置或交付該版Quest。以下基線與最終0.28.3完成資料集（desktop-capacity／20261031前綴）已全停writer、JSON／bytes SHA稽核，不開原或snapshot SQLite：

| 場次／版本 | 範圍／檢查 | 完整報告／成功capture | 本地tick列／穩定列 | 最大本地新tick間隔 | queue錯誤／SSD-F檔數 |
|---|---|---|---|---|---|
| `102502-3f9d73db`／0.28.2 | Linked25人60秒／9項 | 26／130 | 18252／17462 | 0.133572秒 | 0／264 |
| `103038-997cffd4`／0.28.2 | Linked及五獨立房各25人60秒／22項 | 56／280（286次嘗試） | 38532／36402 | 0.144540秒 | 112／534 |
| `105445-7f334dae`／0.28.3 | Linked及五獨立房各25人60秒／22項 | 56／280（286次嘗試） | 38087／36456 | 0.144500秒 | 0／534 |

第二場**重現Linked server112行錯誤，probe亦完整捕捉112筆**：15組在最後觀察到的Running tick62–1152，一組在Paused tick1255，每組7筆；本地秒數9.455454–70.160036，server最後已觀察Ended。phase／tick是log callback讀的最近Update快取，不宣稱發送內部的原子狀態。來源端／全部接收端仍達上述檢查，錯誤數不等於丟包數；這不表示可忽略錯誤。首次無錯誤與之後重現分開保留，不挑只過場。原始105行沒有時間戳，不能倒填成同一根因或階段。

官方UnityTransport的MaxPacketQueueSize是整個driver共用的每update send／receive packet容量，原128不是每peer。新增`VenueTransportProfile`，在StartServer／Host／Client前設定**server／host1024、client仍128**，不改MTU、reliable window、timeout、資料欄位、規則／權限或嵌入patch。此為有界伺服器突發保留候選配置，不能由數字本身稱修復。快照額外核對實際本地設定，並以Actors.WriteField只寫暫存記憶體量field bytes、不清dirty／變更集合。真正序列化測試30／125角色分別4232／17627 bytes，排除NGO／UTP包頭、其他狀態、重傳與入場；不當作實際頻寬或100敵軍負載已通過。

新遊戲端**0.28.3／Android code35**，API／UI0.27、NGO26不變；114項真正EditMode（原109＋2個診斷JSON回歸＋3個driver設定／真實序列化檢查）於02:38:39–02:38:45 UTC通過，Windows receipt02:37:53、Quest02:54:30成功。兩份來源fingerprint均`e8ae6d846dc014e48984a035f2960c043d342a4fe192ff0feaae3891973ba3d0`，原scene／prefab ID一致。真正SDK aapt確認APK0.28.3／code35、min32／target35／arm64-v8a；不是裝置啟動證據。IL2CPP過程較久，確認既有build handle及同身分自有compiler仍有CPU／輸出增加，未因觀察逾時重啟，也未改OS／安全政策。

最終兩模式22項及完整cleanup exit0後才stage=passed／complete=true；六世界4147保存幀，3374穩定期回放幀逐張全名冊／出生位／健康／來源核對，六份最終CSV／ledger／末幀一致。56份報告原始錯誤0、原生日誌亦0；六server均觀察到Ended才停止。端上快照實際server1024／client128、Actor field獨立房848／Linked4232 bytes；最小穩定區間60.222563秒、最小可用實體記憶體8,589,647,872 bytes，原2GiB保留未觸發。最大擷取UTC來源年齡0.179819秒，與本地tick間隔分開，不稱RTT／FPS改善。這證明此負載與本輪配置的錯誤由112到0，**不證明所有工作量／網路條件已修復或原偶發主迴圈停頓已解決**。資料摘要`artifacts/replication-validation.json`。

兩個開發失敗保留：`102252-fa8155d0`首次capture KeyError，因直接匯出無Serializable的WeatherState而JSON缺presentation；改明確DTO，實際Unity JSON回歸測試防再漏欄，沒有改遊戲WeatherState／wire。`102700-27f090b1`Linked檢查完成，但獨立房capture因完整暫存路徑過長FileNotFound而整體exit1；改短`replication/p001`目錄並保存程序對照，新增長名稱回歸測試，不改系統長路徑／安全政策。兩場cleanup均無錯誤無殘留，92／292檔SSD原件與失敗F副本SHA一致、稽核前後不變，失敗不改成通過。第一個成功pilot server探針在End前停止，後續完整場改持續到seal，不能替pilot補造End觀察。

同版未啟用probe的Linked25人／60秒對照`110021-8d1dc8e1` **8項**通過，658幀／561穩定回放幀、最大來源年齡0.155637秒，raw queue錯誤0；runtime無replication目錄或對照表，不補接收端證據，14檔SSD／F SHA一致、cleanup無錯誤無殘留／活動0。`unity-admission/20261031-110235-35459427` **8項真正原生入場／撤銷／同admission回連**亦exit0，392幀精確seal、回放／ledger一致、健康60及彈藥保持；沒有interactive按鍵／GPU、沒有移動後位置新證據。該既有小型fixture資料在F，只作正確性，不稱F USB的25人時序成功；37檔收尾後bytes稽核前後不變，全部自有Popen在finally終止／等待。兩場沒有queue錯誤。

**11項容量／接收端Python＋5項共用artifact檢查**及語法通過，包含非有限值／過期tick／owner／connection／敵軍fireSequence／長目錄對照與真正Windows獨占lease釋放等待；不是16次原生或頭盔試跑。補充稽核`artifacts/replication-final-extra-validation.json`。25程序場的來源／binary仍F、runtime明確C SSD，所有writer停止才一次回F並保留原件，只讀JSON／CSV／bytes、不開SQLite或重寫副本。原5080唯讀仍0.16歷史，Unity serve／登入／安全性提示未碰；無憑證提交。

規則0.8.0、envelope6／world schema1、原header／checksum、素材pins、Tracked資料／pointer／muzzle保持；沒有後端／UI／資產版本契約改動，不重跑歷史654核心／446 HTTP／43世界／217 Chromium、49 UI native／27練習場或人工GPU／DSP／主迴圈診斷，不混算前輪結果。沒有持續25玩家真實移動射擊、跨機／Wi-Fi、完整100敵軍／物件負載、長任務、FPS／聲學、Quest／VIVE／MR或廠商硬體證據，`networkCapacityAccepted`仍false。下一步以實際移動／射擊與更多場景驗證25端同步，再推跨機與設備；完整11項及長期目標保持開發中。

功能提交`54ef0c04c2541bfe555e24214dda5702d153db80`已推送main、遠端一致；提交後重算來源fingerprint仍e8ae6d846dc014e48984a035f2960c043d342a4fe192ff0feaae3891973ba3d0。GitHub #1保持open、原11項與歷史封存連結保留，更新後獨立讀回本文逐字一致。[功能提交CI run41163068604](https://github.com/peca12968/vr-command-center/actions/runs/41163068604)／check124424660203實際failure、steps=null；annotation明示付款失敗或支出上限，工作未開始，沒有雲端測試結果。未改帳務或重跑，本機及原生證據獨立記錄。

## 2026-10-31：25個原生PC程序、場次容量檢查與觀察檔修正

從乾淨`980d0c4`接續無頭盔的PC開發。新增[scripts/check-desktop-capacity.py](../scripts/check-desktop-capacity.py)，操作見[DESKTOP_CAPACITY](DESKTOP_CAPACITY.md)。只改Python／CI／文件，API／UI0.27、Unity0.28.1／code33／NGO26及原0.5秒姿態／1.5秒來源門檻保持。來源fingerprint仍`5eee75868e70237e91b4c6be989c0f4421da98e7e41c5c8adc31878bcb7617b6`，兩份既有receipt及原scene／prefab ID一致，沒有重跑109 EditMode或雙平台建置。

全新隔離API／短效玩家票券，先一個Linked server＋25個真正Windows UDP／NGO client，再精確封存、停止該批程序，另開五個獨立server／每房五個client（同時25人）。全部無圖形、job workers=2、Simulation靜止出生姿態；無時序／GPU／PCM探針、姿態／武器注入、視窗自動化或故意丟包。每房席0–4、不同player／admission／PID／同server connection ID與第六人拒絕均核對。兩模式各60秒穩定期；Pause凍結、Resume tick前進，獨立其他房繼續；之後短暫啟用真正AI攻擊，五房皆有中彈，關閉後End／精確seal／六份CSV及授權SSE回放一致。這不是60秒持續25人移動射擊／戰鬥負載。

成功完成的場次檢查run **`desktop-capacity/20261031-100055-1d0cee1d`**，原執行exit0、20項／六世界、complete=true且cleanup後才stage=passed：

| 世界 | 總幀／逐張核對穩定期回放幀 | 最大擷取UTC來源年齡 | 玩家／中彈／損耗 |
|---|---|---|---|
| Linked | 647／556 | 0.157579秒 | 25／5／100 |
| 獨立1 | 650／557 | 0.166231秒 | 5／1／20 |
| 獨立2 | 651／552 | 0.152643秒 | 5／1／20 |
| 獨立3 | 663／558 | 0.158965秒 | 5／1／20 |
| 獨立4 | 668／557 | 0.160492秒 | 5／2／40 |
| 獨立5 | 684／571 | 0.170800秒 | 5／1／20 |

共3963保存幀、3351張穩定期幀逐張確認全名冊／健康100／正確房間出生位／Simulated且connected、Running未suspend；最後幀與ledger相符。來源年齡不是RTT／client延遲。穩定期後的AI傷害分開統計，玩家射擊耗彈／命中／擊殺均0。主機總實體記憶體34,088,247,296 bytes，最小可用8.031555 GiB，2GiB保留檢查未觸發；不是產品效能保證。

**網路容量驗收仍未通過。**最後離線複查原生日誌發現Linked server有**105行send queue full**；其他原生日誌未有相同字串。原行無時間戳，未知發生階段／client接收影響，不能從world新鮮或回放／報表一致推論下行複本正常，也不能把錯誤行數當遺失封包數。20項僅是伺服器入場／靜止姿態／場次與封存證據，不是零網路錯誤或25人完整驗收。之後摘要明確validationScope、networkCapacityAccepted=false並掃描nativeLogFindings／WARN；只對已停原始日誌離線核對這項最後增補，未再啟動25人或重寫歷史capacity-result。下一步量測各client複本／時效與佇列錯誤階段，再判斷修正，不能盲目照log提高容量。

首輪`094657-3a41bb29`雖20功能檢查完成，卻在F snapshot複製exit1；SSD原件24檔完整，失敗F副本22檔，缺兩個空writer lease。稍後僅另複製兩lease到新probe目錄成功，提示短暫存取競爭，但原shutil詳細錯誤未記錄，**不能確定OS根因**。不覆蓋失敗副本、不補改其stage／cleanup。修正共用snapshot_runtime：全部追蹤writer退出後，最多5秒等待自己的mission／session lease可共享讀取，保持read handles才copytree一次；既有／巢狀目的地拒絕，持續錯誤非零、不改ACL／強制解鎖。cleanup保留有界detail，容量passed移到cleanup成功之後。

首輪練習場回歸`capacity-practice-regression.log`前兩case各9項，第三case因latest-frame.json原位截斷寫入而JSONDecodeError，exit1；finally自行End／收尾，不稱27項成功。共用Venue.save改同目錄唯一暫存完整寫入後replace，Windows分享／PermissionError最多2秒等待；read_json同類存取有界等待但不吞JSON格式錯誤，保存路徑不得逃出自有run。它不是journal的durable flush，也不把所有PermissionError直接歸因分享；持續權限錯誤仍失敗。CSV可指定安全檔名、六場各自保存，原練習場預設不變。

修正後**6項容量規則＋5項觀察檔Python檢查**與語法通過，含真正Windows獨占lease釋放等待及並行JSON讀寫，非11次原生試跑。練習場`desktop-practice-checks/20261031-100622-91f27744` **27項**全部通過；控制台`desktop-venue/20261031-101101-c8454660` launcher／checker皆exit0、**49項UI／native整合**，128幀／最大來源年齡0.152128秒。檢視final-report.png，主玩家損耗40／中彈2／健康60，離場Peer02與替換Peer03保留；瀏覽器SwiftShader／native無圖形，沒有新GPU／聽感證據。

容量24檔、三個練習場及控制台各14檔runtime皆全停writer才回F，cleanup無錯誤無殘留、活動0、world完整及精確戰鬥封存。SSD原件／F副本bytes SHA相同，稽核前後不變；只讀JSON／CSV／bytes，未開原SQLite、未重複複製或修改副本。摘要`artifacts/capacity-validation.json`及`capacity-regressions-validation.json`；容量日誌105行錯誤另明列上述限制。來源／binary仍F，runtime明確C SSD，不是F USB全資料成功。原5080唯讀GET仍0.16／原歷史，Unity serve未碰，憑證未輸出或提交。

未驗各client遠端複本、25個玩家持續真實移動／射擊、繪圖FPS／音訊、跨機／Wi-Fi、Quest／VIVE／MR或廠商硬體；原偶發姿態停頓根因亦未修復。沒有重跑歷史後端／完整瀏覽器／七場五房／8項重連；完整11項與長期目標保持開發中。

功能提交`21d746ef64df0aac41178bd282cdd86f22fd0f2f`已推送main並核對遠端一致。GitHub #1保持open，最新本文與原11項／歷史封存連結均保留。[功能提交CI run41159068469](https://github.com/peca12968/vr-command-center/actions/runs/41159068469)／check124412315156實際failure、steps=null；annotation明示付款失敗或支出上限，工作未開始，沒有雲端測試結果。未改帳務或重跑，本機及原生證據獨立保存。

## 2026-10-31：自有程序CPU時間／週期計數與主迴圈空窗

從乾淨`7083906`接續PC穩定性。新增`pose-process-timing.py`／`analyze-process-timing.py`及helper明確`--process-timing`，**僅讀取本輪三個自有Unity程序**。父程序先借用自己的Popen原handle取得建立FILETIME／執行檔，借用結束不關原handle；probe以QUERY_LIMITED_INFORMATION＋SYNCHRONIZE重新開啟唯讀handle，核對建立時間／完整exe，固定持有同一process object、不追隨重用PID。只查GetProcessTimes／QueryProcessCycleTime與零等待存活狀態，不列舉其他程序、不讀記憶體／堆疊、不開thread、不暫停或改優先級／權限／系統設定。

每50ms查三份累積kernel／user時間與CPU cycles；每次查詢有前後perf_counter／UTC括號，最多5000輪／15000列／240秒，保留最早資料、不環狀覆寫。首份ready在基線前一次寫入，收集期除每250ms檢查自己的finish.request，不輸出樣本。明確finish才完整，先關全部唯讀handle、再一次寫report；child handle由helper持有，正常及失敗finally均收尾，另存process-timing-cleanup。這是外部唯讀診斷，沒有新的Unity或後端程式碼／遊戲資料契約。

兩個真正直接loopback場，原Windows0.28.1／code33／NGO26、API／UI0.27、可見玩家＋無圖形peer＋server。都帶原有pose／loop trace、獨立10ms heartbeat與新CPU probe；無丟包控制／姿態或武器注入，computer-use真實Space三次，兩場HUD均29／28／27、權威耗彈3／命中0／擊殺0／健康100，各**4項真正原生流程**通過：

| desktop-venue／20261031前綴 | 世界幀／最大擷取UTC來源年齡 | CPU取樣 | 原Update／三方邊界共同空窗 | 運行期HUD過期後回ACTIVE |
|---|---|---|---|---|
| `091639-4a14adf0` | 793／0.647925秒 | 1556輪／4668列，原始版本未記cycles | 0.642856／0.6374241秒 | 約0.196110秒 |
| `092109-f446e5f7` | 687／0.577435秒 | 1336輪／4008列，cycleCounterVersion1 | 0.6070879／0.594546秒 | 約0.150704秒 |

兩場長空窗都再次位於after `TimeUpdate+WaitForLastPresentationAndUpdateTime`→before `TimeUpdate`，不是該Wait節點的before→after。loop三報告完整／detached並覆蓋全觀察期，CPU UTC／perf guard最大1.3915／2.1863ms；最長單次查詢1.095／1.905ms，最大同程序樣本分隔53.771／56.773ms。獨立heartbeat最大wake14.3472／18.9925ms，完整覆蓋原Update交集。啟動期HUD提示仍明示在觀察區間外，不當作運行期樣本。

第一場共同loop區間內，各程序都有**13個完整查詢括號**、實際首末跨度約0.606秒，kernel／user累積差皆0；相鄰名義等長前後窗口卻都增加（visible前0.21875／後0.15625 CPU秒，peer0.0625／0.03125，server0.078125／0.078125）。這只能記為noAccountedAdvanceObserved，**零值不證明整個程序被暫停**。因此在原場完全終止後，加入唯讀cycle counter再開第二場，沒有重啟仍存活的工作，也沒有補寫第一場raw cycles。

第二場共同loop區間ticks **639290065068466589–639290065074412049**（0.594546秒），每程序12個內部樣本，實測首末跨度約0.5586秒、且前後皆有樣本包住：

| 程序 | kernel＋user累積增加 | CPU cycles增加 | 11對相鄰內部查詢中cycles增加次數 | 前／後比較窗口CPU秒 |
|---|---|---|---|---|
| 可見玩家 | 0.03125秒 | 22,077,542 | 11／11 | 0.15625／0.140625 |
| 背景peer | 0.03125秒 | 20,440,676 | 11／11 | 0.0625／0.046875 |
| server | 0.015625秒 | 18,748,061 | 11／11 | 0.078125／0.046875 |

這次**三個process的計數在主迴圈共同空窗內仍持續增加**，不支持把整段直接解釋成三程序全程停止；但計數加總全部threads，仍不知道主執行緒本身／其他worker各做了什麼，不能據此說主線程正常、證明特定等待／音效／GPU／I/O／排程／transport根因或已修復。第一場粒度受限的零值不能推成與第二場成因相同或相反。取樣及外部視窗／輸出查詢的擾動仍未排除；下一步須辨識主執行緒與主迴圈外工作／等待，維持原0.5秒姿態及1.5秒來源門檻。

分析只用**查詢UTC括號完全落在區間內**的首末樣本差，不插值、不把外側CPU灌入；上界向外取整至100ns，少於兩點明示insufficientInteriorSamples／null。前後為名義等長比較窗口，實際首末樣本跨度不同，不把累積差直接當相同工作量。GetProcessTimes依[官方定義](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes)用100ns時間單位；[QueryProcessCycleTime](https://learn.microsoft.com/en-us/windows/win32/api/realtimeapiset/nf-realtimeapiset-queryprocesscycletime)是全程序threads的cycles，本工具不換算成秒或CPU百分比。檢查manifest身份逐字一致、角色／輪數／單調計數、handle關閉、完整性／clock guard；失敗或UTC差達50ms不做join，CLI非零。原始第一場缺cycle版本仍讀為0／unavailable，不造零cycles；舊0.28.1有／無loop的兩場資料重分析通過。

**43項Python檢查**通過：9個程序計時（8個合成／規則方法＋1個真正Windows唯讀producer與自己的Python CPU worker）、16個輸入、8個loop、7個heartbeat（其中1個真正timer程序）、3個舊分析；Python語法通過。這不是43次原生或頭盔試跑，Linux的Windows producer項明確skip而非冒充執行；本輪只在Windows本機實際跑。兩場先停外部probe與三份native trace，再獨立End／戰鬥與世界精確seal，world complete、回放／ledger一致、pending=false／活動0，三份cleanup均無錯誤無殘留，CPU report各關閉3個唯讀handle。每場**28檔**SSD runtime全停writer後回F、與保留原件SHA一致，稽核前後不變；只讀JSON／bytes，未開原SQLite或重寫snapshot。摘要`artifacts/pose-cpu-validation.json`。

本輪只改Python／CI與文件；Unity來源fingerprint仍 **`5eee75868e70237e91b4c6be989c0f4421da98e7e41c5c8adc31878bcb7617b6`**，既有Windows／Quest receipts及原scene／prefab ID一致。API／UI0.27、Unity0.28.1／code33／NGO26、rules0.8.0、envelope6／world schema1、header／checksum、profile pins與Tracked資料保持。沒有重跑前輪109 EditMode／雙平台、49 UI／native或歷史後端／完整瀏覽器／五房／重連，不混算為本輪通過數。原5080唯讀GET仍0.16／原歷史，Unity serve未碰。來源／binary仍F、新runtime明確C SSD，非F USB全資料、跨機、MR／Quest／VIVE實機、廠商硬體或25台證據；完整11項與長期目標保持開發中。

功能提交`079f3cec0ffaba5c45b1e05a14060b3763966d2a`已推送main並核對遠端一致；GitHub #1保持open，更新後獨立讀回3687字本文逐字一致，保留原11項與歷史封存連結。[功能提交CI run41155920513](https://github.com/peca12968/vr-command-center/actions/runs/41155920513)／check124402566095實際failure、steps=null，annotation明示付款失敗或支出上限、工作未開始，沒有雲端執行結果。未改帳務或重跑，本機／原生證據獨立記錄。

## 2026-10-31：主迴圈邊界定位、同版對照與0.28.1雙平台

從乾淨`19843f2`接續PC姿態過期。Unity **0.28.1／Android code33**，API／UI0.27及NGO26保持。新增明確選用的`--vr-pose-loop-trace`與helper `--player-loop`，只在原Windows Development pose trace一起安裝；一般啟動、Editor與Android不安裝。從目前PlayerLoop在當時既有節點前後插入自己的兄弟觀察點，不改原type／delegate／native function／loop condition與次序。512節點／32層前置界線、4096個>100ms稀疏空窗、240秒上限；保留最早資料，完整性／截斷獨立。每點讀單調時間、UTC、frame並更新有界計數，不做GPU、PCM、網路或收集期間檔案輸出。停止時只移除目前樹中屬於自己的marker，保留後來的NGO／其他變更；剩餘當幀callback由stopped旗標no-op，不還原舊樹快照。

真正Editor Prepare、**109 EditMode**（新增7）及**同源Windows／ARM64 IL2CPP Quest APK**成功。最終Tests XML 00:59:11–00:59:17 UTC、109／0失敗；Windows receipt 00:49:13、Quest 00:58:40 UTC，來源fingerprint皆 **`5eee75868e70237e91b4c6be989c0f4421da98e7e41c5c8adc31878bcb7617b6`**，目前來源再次計算相同，原scene／prefab GlobalObjectId保持。生成設定／新C# meta已保存，沒有重建Arena或舊profile／pin。首輪Desktop因我新增的`owner`區域變數與參數同名，在Windows Development分支CS0136／exit1；Editor條件未涵蓋該段，不能以109測試代替Windows編譯。失敗日誌`pose-loop-desktop-first-failure.log`保留，修為traceOwner後真正Desktop／Quest及最後Editor檢查皆成功。原有兩個audio名稱遮蔽警告仍在，不稱零警告。

同一新版本、直接loopback、可見玩家＋無圖形peer＋server、真正Space三次（兩場HUD均29／28／27），無故意丟包、姿態或武器注入。建置與最終Editor全停後才開始時序試跑；各有普通優先級獨立心跳、原有三份NativePoseTrace與visible HUD trace，沒有原生GPU讀回／PCM：

另以SDK真正aapt讀本次APK，確認versionName0.28.1／versionCode33、min API32／target35及arm64-v8a；輸出`artifacts/pose-loop-apk-badging.log`。這是APK內容核對，不是裝置啟動或追蹤驗證。

| 場次desktop-venue／20261031前綴 | 模式 | 幀／最大擷取UTC來源年齡 | 結果 |
|---|---|---|---|
| `085931-26eeed5d` | --heartbeat --player-loop | 649／0.763435秒 | 4項真正流程、再次重現HUD過期及三程序共同空窗 |
| `090053-3cd88fd6` | --heartbeat，未啟用loop記錄 | 850／0.288351秒 | 4項真正流程、觀察期無>100ms Update空窗／HUD過期 |
| `090233-64a95e32` | 一般控制台，未啟用任何pose／loop探針 | 164／0.158143秒 | **49項UI／native回歸**、動態名冊／天氣AI／觀戰回放／最終CSV一致 |

啟用場每程序實際**294個邊界（147節點）**；可見／peer／server callback分別1,605,352／1,706,390／1,721,790，時鐘guard最大1.8584ms，三份報告complete／detached且覆蓋完整觀察期。三程序的>0.5秒相鄰觀察空窗，都從 **`TimeUpdate+WaitForLastPresentationAndUpdateTime` 的after（path /0/0）到 `TimeUpdate` 的before（path /0）**，各0.8695835／0.7297024／0.7255199秒，記錄的frame起訖各自相同。這是**between observers**，不能把整段說成在該Wait節點內執行；可見玩家另有真正before→after的0.1291602秒Wait區段，與此共同長空窗分開。server啟動期ExecuteMainThreadJobs約0.136秒在觀察區間外，沒有混算。

原Update三方交集為 **0.727348秒**；新增三方邊界空窗共同交集是 **0.7167323秒**（ticks639290052032020974–639290052039188297）。兩者起點不同，不能混稱同一精確長度。HUD本次STALE約0.125008秒後ACTIVE，poseAccepted=true；發生於shot-1階段，該階段包含真實輸入後的視窗／輸出觀察與確認等待，不能當扣彈／武器處理耗時。外部Space呼叫時間另存根目錄，不當逐packet序號。獨立心跳6166次、64.0195秒、最大wake **16.4326ms**、UTC步進差1.2168ms，完整覆蓋共同區間，沒有>100ms列；不支持全部程序或整個OS一起暫停。

**定位更精確，底層原因及修復仍未證明。**節點名稱只標實際相鄰觀察點，不能假定引擎每次都依教科書框架順序執行，更不能把wall time當CPU／GPU／音效／排程或transport歸因。未啟用loop的同版單次對照乾淨，不能排除新記錄本身的成本／擾動或特定外部操作；舊版沒有新marker也曾有同類提示，但不能只由症狀相同斷言底層成因相同。接續針對這兩個觀察點間的引擎／訊息處理與各自有程序執行狀態取證，維持原0.5秒姿態與1.5秒來源門檻，不臆測「修正」引擎等待設定。

分析新增pair／系統名稱／計數、gap與最大值一致、時鐘與完整觀察覆蓋檢查；missing／partial／attached／截斷拒絕，UTC偏差達50ms不做loop phase／join，CLI非零。原生fixture完成metadata也是CLI必要條件。未啟用場首次分析exit1，實際發現JsonUtility把null class寫為完整的**空預設物件**，不是JSON null；保留原raw檔，以fixture明確playerLoop=false且物件逐欄等於空預設才忽略，不能藉disabled隱藏callbacks／失敗／非空資料。新增實例反例後兩場重新分析exit0，loop未啟用回null；舊無loop資料亦重新讀取通過。**33項Python檢查**通過：8個loop分析、15個輸入、7個心跳（含一個真正獨立timer程序）、3個舊分析；不是33次原生或頭盔試跑。

兩射擊場皆耗彈3／命中0／擊殺0／健康100，先明確finish三份trace再獨立End／戰鬥與世界精確seal。一般控制台回歸主玩家損耗40／中彈2／健康60，保留離場Peer02及替換Peer03，CSV全部指標／封存界線與ledger／回放一致；檢視`operator-ui/final-report.png`，瀏覽器觀戰為SwiftShader、native client無圖形，不稱新GPU／DSP探針或人工聽感。一般runtime沒有診斷report檔。三場world complete／pending=false／活動0／cleanup無錯誤無殘留；射擊場另heartbeat-cleanup無殘留。24／24／14檔SSD runtime在writer全停後回F，與保留原件SHA相同，稽核前後不變；僅讀JSON／bytes，未開原SQLite或重寫snapshot。摘要`artifacts/pose-loop-validation.json`。

不變：API／UI0.27、NGO26、rules0.8.0、envelope6／world schema1、原header／checksum、全部素材pin、追蹤資料與pointer／槍口。沒有重跑歷史654核心／446 HTTP／43世界／58 Node／217 Chromium、七場五房或8項入場重連，不混入本輪數量。原5080唯讀GET仍0.16／原歷史，unity CLI serve未碰。來源／binary仍F，明確C SSD全新runtime；非F USB全資料、跨機、MR／VIVE／Quest實機、廠商硬體或25台證據。完整11項及長期目標保持開發中。

功能提交`2c79a7308b5923dd370e31e81121b91953370b1c`已推送main、遠端一致；GitHub #1保持open，更新後獨立讀回3581字本文逐字一致，保留原11項及歷史封存連結。[功能提交CI run41153866259](https://github.com/peca12968/vr-command-center/actions/runs/41153866259)／check124396246125實際failure、steps=null；annotation明示付款失敗或支出上限，工作未開始，沒有雲端執行結果。未改帳務或重跑，以上本機／原生證據獨立記錄。

## 2026-10-31：獨立程序心跳與視窗／輸出輪詢對照

從乾淨`bbde0a1`接續PC偶發姿態過期調查。新增`scripts/pose-heartbeat.py`，由原生檢查器以明確`--heartbeat`啟動自己的獨立、一般優先級Python程序，每10ms sleep後量perf_counter、UTC與process CPU；沒有遊戲／網路／UI接入，也不調整優先級、計時器或系統設定。只在記憶體保留>100ms空窗及每秒clock anchor，4096列／256 anchors／240秒上限，明確finish才完整；報告序列化在觀察結束後。檢查器持有Popen handle，正常與失敗finally均收尾，另保存heartbeat-cleanup。沒有改C#、API／UI0.27或Unity0.28／code32／NGO26及原0.5／1.5秒門檻。

增加`--observation-only`的安靜基線→window-review→安靜收尾；過程不得按遊戲鍵，window-review.done只確認觀察。四個完成場皆直接loopback、兩個真正client＋server、原有三份NativePoseTrace及visible HUD trace，無LossGate、姿態／武器注入、原生GPU讀回或PCM：

| 本輪desktop-venue識別 | 實際操作 | 世界幀／最大擷取UTC來源年齡 | 心跳次數／最大wake間隔 | 結果 |
|---|---|---|---|---|
| `082241-c9a91e27` | 15秒基線，5次文字查詢＋5次截圖，無遊戲鍵，再安靜15秒 | 656／0.171283秒 | 6177／18.754ms | 觀察期無>100ms原生Update空窗、無HUD過期 |
| `082536-8cb741cb` | 10秒基線，真正Space三次，HUD29／28／27 | 772／0.612307秒 | 7389／13.348ms | 重現三Unity共同0.7017494秒空窗及HUD過期 |
| `083531-90e11646` | 無UI／遊戲鍵，接續時僅讀log，不能當完整輪詢對照 | 1184／0.166302秒 | 11669／14.518ms | 觀察期無>100ms原生空窗／HUD過期 |
| `083806-990e7dae` | 5秒基線，同一原執行連線連續6次空輸出poll，每次約5秒，無UI／遊戲鍵 | 552／0.162059秒 | 5166／13.205ms | 觀察期無>100ms原生空窗／HUD過期 |

完整目錄皆前綴`20261031-`。第一場保留外部10次查詢時間，先前初次activate及合併查詢另明示；最後一場保留6次實際unified-exec poll起訖時間。中間無UI場原exec handle在接續時不可取回，因此只以原PID、command line與log確認它仍在執行，再正常確認完成，沒有因缺少handle重啟；等原PID消失、sealed／summary及兩份cleanup完整後才另開匹配poll場。最後一場原handle持續保留並取得terminal exit0。這些乾淨對照不排除特定時機／組合操作、診斷或外部工具影響，也不能證明舊問題已修復。

射擊場可見玩家／peer／server最大Update觀察空窗為0.777354／0.702231／0.702255秒，共同區間ticks **639290031824251115–639290031831268609**（0.7017494秒）。同ID server收件最大空窗可見0.803226、peer0.714325秒；HUD於過期後約0.088214秒回ACTIVE，poseAccepted仍true。**獨立心跳完整覆蓋該共同區間，整場最大wake間隔僅13.348ms、沒有>100ms列**，UTC／perf步進差最大1.456ms，不能稱整個OS／全部程序同時暫停。仍不能從Update間隔歸因CPU、Unity引擎共用資源、選擇性排程、音效、GPU、I/O或transport；未量測的PlayerLoop區段與外部影響繼續取證，不臆測修復。啟動期HUD短暫STALE獨立標記withinPoseObservation=false，沒有當成本輪運行期重現。

分析器增加心跳完整性、單調counter／UTC guard、覆蓋區間與三方交集；不完整／缺失報告拒絕，UTC偏差達50ms時不做心跳join，不能以未覆蓋的時間宣稱獨立程序正常。前兩場raw report尚無exact起訖UTC欄位，使用首末clock anchors的保守覆蓋；不補寫或重造舊raw檔。後兩場及真正producer單元程序已有明確起訖欄位。階段自動支援window-review／quiet-after，舊無心跳075207場重新分析exit0且heartbeat=null，保持相容。

**7項心跳檢查**（6個合成分析方法及1個真正獨立timer程序）、**12項輸入分析反例**及原**3項分析回歸**通過；Python語法通過，CI加入心跳步驟。這22項不是22次原生／頭盔試跑。四個完成原生場各4項流程、三份trace明確finish後獨立End／世界與戰鬥精確seal，world complete／pending=false／活動0、回放／ledger一致；無輸入三場耗彈0、射擊場3，健康100。每場24檔SSD runtime在全部writer停止後回F，與保留原件SHA一致，稽核前後不變；只讀JSON／bytes，未開原SQLite或覆寫snapshot。摘要`artifacts/pose-heartbeat-validation.json`。確認本輪沒有剩餘native／heartbeat／helper程序，未碰unity CLI／正式5080。

首輪`081944-8218348a`未完成：外部視窗觀察在原60秒人工作業等待內未確認，helper timeout／exit1後關窗，第五次查詢因此找不到原視窗。失敗log與資料保留，核對原程序終止、無殘留視窗後才開新場；將**診斷人工作業確認上限**調為120秒，不是放寬0.5／1.5秒遊戲政策，240秒trace上限仍維持。此場不列入上述完成結果。

本輪僅Python診斷／分析、CI與文件，沒有重跑歷史後端／瀏覽器／102 EditMode／APK。Unity fingerprint仍`792a3aaac9a7903159718a898324def8f6ba4769f908f1f46f30a6c77744c725`，Windows／Quest既有receipts及原scene／prefab ID一致；原5080唯讀GET仍0.16／原歷史。來源與binary在F、全新runtime明確在C SSD，非F USB全資料、跨機、頭盔／MR／VIVE／廠商硬體或25台證據。完整11項與長期目標保持開發中。

功能提交`575216bc1820872bcf953d8f0567527cb2176771`已推送main並核對遠端一致；GitHub #1保持open，更新後獨立讀回3200字本文逐字一致，原11項與歷史封存連結保留。[功能提交CI run41151496751](https://github.com/peca12968/vr-command-center/actions/runs/41151496751)／check124388817676實際failure、steps=null，annotation明示付款失敗或支出上限、工作未開始，沒有雲端執行結果；未改帳務或重跑。本機檢查與原生證據如上，不把雲端未啟動當作通過。

## 2026-10-31：目前版本雙玩家姿態提示重現與三程序時序

從乾淨`e5fa9fa`接續PC穩定性。舊時序原生證據在Unity0.26.1、未含後續射擊音效及完整玩家人物；本輪新增[POSE_TIMING.md](POSE_TIMING.md)的`check-desktop-pose-input.py`／`analyze-pose-input.py`，用既有API／UI0.27及Unity0.28／code32／NGO26。自己的房間3、server、可見玩家及無圖形同伴直接loopback連線，沒有LossGate、故意丟包或payload改寫；三程序明確啟用原有NativePoseTrace，可見玩家另用原HUD trace。沒有改C#／正式輸入、防瞬移、傷害或0.5／1.5秒門檻，沒有原生GPU讀回／PCM／麥克風。

`desktop-venue/20261031-075207-5621fa8a` **4項真正原生流程**通過。先15.171秒無射擊基線，透過computer-use真實視窗Space三次，HUD依序29／28／27；第二發前亦實按W一步，沒有姿態／武器RPC注入。三份trace在觀察結束後明確finish，complete=true／truncated=false，再獨立End與戰鬥／世界精確seal；1121幀、最大擷取UTC來源年齡0.624341秒、健康100／耗彈3／命中0／擊殺0，回放／ledger一致，pending=false／活動0／cleanup零錯誤、無追蹤子程序。22檔SSD runtime在writer全停後回F，與保留原件SHA一致；分析只讀JSON／檔案bytes，不開原DB或重寫snapshot。摘要`artifacts/pose-input-validation.json`。

這次**取得真正POSE STREAM STALE樣本**，而非只重跑乾淨基線。HUD每渲染幀的五次狀態轉換保留，過期約0.133828秒後ACTIVE，poseAccepted=true／connected=false與原過期政策相符，沒有把它當姿態拒絕。可見client connection2，peer connection1；分析按ID篩server，不能用兩人交錯流量掩蓋其中一人的空窗：

| 觀察 | 可見玩家 | 背景同伴 | 伺服器 |
|---|---|---|---|
| 基線最大RPC呼叫／同ID入口 | 55.741／55.718ms | 55.801／57.281ms | 無發布過期或>100ms主執行緒空窗 |
| 全觀察最大RPC呼叫／同ID入口 | 0.812241／0.811725秒 | 0.744546／0.745023秒 | 兩個ID均曾發布過期 |
| 最大Update觀察空窗 | 0.810708秒 | 0.719134秒 | 0.646577秒 |
| 發布過期時接受姿態年齡 | 0.711310秒 | 0.700172秒 | 保持原0.5秒政策 |

三程序空窗共同交集為**0.6425932秒**，UTC2026-10-30 23:53:08.870723–23:53:09.513316（本機10/31上午）。第一發彈藥29已於23:53:04.242605被世界取樣觀察，第二發彈藥28在23:53:38.753050才被觀察，交集在兩發之間，並非扣彈當刻。這不是每packet／每發精確CPU時間；shot階段包含操作者觀察／確認等待。UTC對Stopwatch步進差最大1.5285ms，通過本機join guard；已量測的server記錄／發布區段在觀察期最長2.7402ms，尚未涵蓋停頓處，不能將全trace含啟動期18.8318ms與此區段混算。

**尚未證明底層根因或修復。**MainThreadGap只量兩次Update之間wall time，不是CPU耗時或整個OS暫停的證明。三程序同時缺口不能直接歸因於音效、GPU、磁碟、排程器、NGO／transport；也未排除診斷本身及外部computer-use視窗查詢／輸入的影響，不能推論一般人操作或頭盔同樣成因。這個新樣本改變下一步：對未量測的PlayerLoop及獨立時間心跳做對照，維持原警告與門檻，沒有把這輪診斷稱為修好。

新分析保留跨階段邊界的收／發間隔，按connection篩BodyConnection；connection變動拒絕分析，不把重連併成單流。三份trace完整性獨立驗證，HUD末尾沒有下一狀態明示rightCensored／未知duration，UTC步進達50ms時phases與三方join留null且CLI非零。**10項合成反例**通過，涵蓋peer掩蓋／邊界間隔／三方交集／缺少交集／時鐘步進／connection變更／trace截斷／誤錄GPU／HUD未知尾端；另原**3項時序分析回歸**通過。這13項是合成分析規則，不能當13次原生或頭盔試跑。CI新增新單元測試與Python語法步驟，py_compile本機通過。

本輪只新增Python診斷／分析及文件／CI，沒有重跑前輪後端／瀏覽器／102 EditMode／APK。Unity source fingerprint仍`792a3aaac9a7903159718a898324def8f6ba4769f908f1f46f30a6c77744c725`，既有Windows／Quest receipts及原scene／prefab識別一致；不改schema、資源pin、header或checksum。原5080確認仍API0.16／原歷史，未替換。全11項保持開發中；這是同機Simulation量測，不是Quest／VIVE、MR、廠商硬體、跨機或25台效能證據。

功能提交`54a724258e1407515bcf14365e0724b95526146c`已推送main並核對遠端；GitHub #1仍open，更新後獨立讀回3072字本文一致，原11項及歷史封存連結保留。[功能提交CI run41148997649](https://github.com/peca12968/vr-command-center/actions/runs/41148997649)／check124380747557實際failure、steps=null，annotation明示付款失敗或支出上限、工作未開始，沒有雲端執行結果；未改帳務或重跑。下一步繼續對未量測區段取證，沒有宣稱修復或完成整體目標。

## 2026-10-31：修復電腦練習場入口、五人同房與關窗封存

從乾淨`35bff7f`接續PC主線。實際執行舊`start-desktop-demo.py`搭本輪既有API0.27，程式在建立場次前因仍要求**0.21.0**而exit1，保留`artifacts/practice-old-launcher-failure.log`。原DESKTOP文件另仍寫0.16，兩者均已修正；沒有改回舊reader或替換5080歷史來配合。

練習場改共用已驗證Venue：API0.27版本gate、Windows receipt／當前Unity source fingerprint及嵌入Transport293檔檢查、短效admission票券、同一份CSV／世界／戰鬥精確seal與原擷取UTC1.5秒門檻。明確`--runtime-root`可將全新runtime放C SSD，來源／binary／設定仍F；每程序job workers預設2，沒有當作F USB或姿態偶發的修復。Venue新增受限artifact_family，預設desktop-venue及其latest pointer保持；練習獨立desktop-demo／latest-desktop-demo-path.txt，不覆蓋五房入口。來源／API／UI及NGO版本均不新增，本輪沒有任何Unity或後端產品變更。

每位client以admissionId命名，不再沿用同房號互相覆蓋；支援主玩家加0–4同伴，同房最多5個真正PC程序。正常關窗移除已停止handle，End後退場其餘自有client，只等API／server精確封存，不讓已關窗client誤觸live-child fence。控制台End、end.request、到時及Ctrl+C保留既有語意，duration為包含Pause的wall-clock上限。完成後從授權report.csv取得CSV，以標準csv／Decimal檢查玩家集合、身份／房間、全部指標、來源及stream尾界，再保存final-report.csv／SHA。舊summary頂層world／statistics／replayStatisticsMatch保留，新增stopReason／runtime／workers／finalReport；cleanup失敗仍exit非零，資料／原件保留。

新增可重現的`scripts/check-desktop-practice.py`。**27項真正無圖形流程**及**9項實際視窗流程**通過，來源皆Simulation；不是5台硬體、跨機或25台測試：

| 場次／結束方式 | 玩家／世界幀 | 最大來源年齡 | 結果 |
|---|---|---|---|
| `072944-8717ce7a`／控制台End | 5／48 | 0.145045秒 | 五席全部連線、Pause凍結tick／Resume、精確seal／CSV及14檔snapshot一致 |
| `072953-e2edc784`／end.request | 1／43 | 0.140979秒 | 同上單人收尾，stopReason=endRequested |
| `073000-1d385f64`／60秒到時 | 2／578 | 0.164424秒 | 同上雙人，stopReason=durationElapsed，不冒充遊戲內精確扣Pause倒數 |
| `073121-5b3def38`／正常關窗 | 2／582 | 0.303067秒 | 真正W／Space／R與Alt+F4；stopReason=windowClosed、精確seal／CSV及14檔snapshot一致 |

四場位於`artifacts/desktop-demo/20261031-<表內識別>`，活動0／pending=false／cleanup零錯誤且無剩餘追蹤程序，世界complete及回放／ledger一致。無圖形27項在`desktop-practice-checks/20261031-072944-7d9e81ba`，實際視窗9項在`20261031-073121-140758c9`。用computer-use技能的真實視窗按鍵；接受的玩家從(25,1.65,-3)移到(25,1.65,-2.95)，一次Space耗彈1／命中0／擊殺0／健康100，R完成後HUD及接受狀態30／89。普通遊戲影像／HUD已檢視，不是新的GPU探針或音效量測；射擊後一張擷取出現POSE STREAM STALE、下一張恢復，原0.5秒政策、歷史偶發根因均未改或證實修復。關窗後沒有強制停止正式服務或注入姿態／RPC。

另**3項preflight反例**通過：刻意錯誤fingerprint的自有假exe／receipt在新建run／API前以exit2拒絕、第六個玩家由參數拒絕、artifact family路徑穿越在建立資料前拒絕。新加入starting階段於API／native啟動前提供本輪目錄，checker的startup觀察界線涵蓋既有API／recording／admission等待；它不是放寬來源新鮮度，未就觀察逾時重新啟動程序。

**3項受控原生失敗檢查**亦通過：`20261031-073747-3ab76c77`在ready後，以launcher parent PID、exe絕對路徑、本輪config目錄及practice-client名稱確認兩個自有無圖形client，才停止其中一個。launcher實際exit1／stage failed，沒有完成summary；cleanup仍精確封存、停止全部自有程序且無錯誤，journal／snapshot保留，不能把這場當正常完成。詳見`artifacts/practice-expected-client-failure.json`。

共用Venue預設路徑的**49項既有UI／native回歸**重新通過，`desktop-venue/20261031-073345-0ae94b64`，166幀／0.172879秒，動態名冊、操作員天氣／AI／觀戰／回放及CSV一致、活動0／cleanup零錯誤；client無圖形、觀戰SwiftShader。全部正常練習與此回歸的SSD runtime在writer全停後各14檔複製回F，SHA與保留原件一致；稽核只讀檔案bytes／JSON／CSV，沒有開原DB或再覆寫snapshot。摘要`artifacts/practice-validation.json`。

僅Python啟動／檢查器、文件及CI語法步驟變更，`py_compile`通過；Linux CI此步不代表Windows程序曾執行。Unity fingerprint仍`792a3aaac9a7903159718a898324def8f6ba4769f908f1f46f30a6c77744c725`，Windows／Quest receipts及原識別保持，API／UI0.27、Unity0.28／code32／NGO26、rules0.8.0、header／checksum不變。沒有重跑前輪654核心／446 HTTP／43世界／58 Node／217 Chromium或102 EditMode／APK，沒有將歷史檢查計入本輪。原5080再次確認0.16／原歷史。本輪修復的是可操作入口與收尾；完整人物／動畫／聲學、複雜通路、長任務／跨機，以及頭盔／MR／VIVE／硬體／25台仍分別待驗，完整11項目標保持開發中。

功能提交`e397b443254ec5ccaad16150dcfc706a2463d94f`已推送main並核對遠端一致；GitHub #1仍open，更新後獨立讀回3152字本文一致，原11項及歷史封存連結保留。[功能提交CI run41146227105](https://github.com/peca12968/vr-command-center/actions/runs/41146227105)／check124371855173實際failure、steps=null，annotation明示付款失敗或支出上限，工作未開始，沒有雲端執行結果；未改帳務或重跑。

## 2026-10-31：最終任務 CSV、封存界線與原生報表整合

從乾淨 `95eae21` 接續PC主線，新增 [REPORTS.md](REPORTS.md) 的 `GET /api/sessions/{id}/report.csv` 與「下載最終報表 CSV」。API／UI **0.27.0**，reportVersion1；Unity仍0.28／code32／NGO26。這是最終戰鬥 ledger 匯出，包含離場玩家、原任務ID／名稱、來源、throughSequence、stream ID／接受尾界與原11項中的全部玩家統計，不依目前名冊重算。不宣稱世界錄影已完整、頭盔在線或25台通過。

FinalReport在同一session gate內授權、檢查Ended及combat精確seal後取metadata／statistics，拒絕進行中、Pause、僅End及尚未seal的尾端。來源／房間先檢查；HTTP明確傳入Actor，GameServer403／未驗證401。Linked房控沿既有全場讀取政策，外房獨立場拒絕。未綁stream的已結束歷史可匯出；合法空stream保留宣告來源及尾界0，無來源明示None。空場只有Session metadata列，不造玩家。沒有新的持久資料、事件或schema。

CSV為UTF-8 BOM、全欄引用、逗號／CRLF，數字invariant、accuracyPercent沿用原兩位小數；任務秒數標planned，不冒充扣Pause的實玩時間。公式開頭／控制文字只在CSV加單引號，原名字與JSON不變。重複下載、接受tail／seal重試與SQLite重啟位元組一致；不是簽章證書。HTTP attachment、no-store，檔名只含UUID；沒有憑證／地址或伺服器匯出檔案。前端以Bearer fetch下載、抑制重複並釋放ObjectURL；generation＋login epoch阻擋切離再回同場／登出再登入晚回應。讀header及blob後重查，錯誤MIME不下載，409可重試，當前401登出。一般輪詢不抹掉下載成功／錯誤文字。

locked restore、Release build **0警告／錯誤**、真正執行VrCommand.Checks **654項**（新增25）、**446 HTTP、43世界、58 Node／217 Chromium**全部通過。包含並行seal只能觀察拒絕或完整快照、返回陣列不可改ledger、離場／零發／空場、fr-FR小數、CSV公式／引號／換行、SQLite及HTTP真正重啟／key輪替後完全相同、實際瀏覽器下載bytes／檔名與read-only序號、切離再回及重登入晚回應、409／錯誤MIME／401與既有回放／素材回歸。API／UI來源與該次隔離輸出的三個JS／HTML逐位核對，檢視 `artifacts/console/final-report.png`；軟體WebGL不是原生GPU證據。

真正 Windows operator run **`desktop-venue/20261031-072120-4e03e4bb`**，**49項UI／native**（新增2）通過。使用現有同源0.28原生server／clients、Simulation rigs及自己的API0.27／C SSD runtime；不是注入姿態或新GPU／頭盔測試。163幀、最大來源年齡 **0.176034秒**，世界complete、回放／ledger一致、pending=false、活動0、cleanup零錯誤且無追蹤子程序。CSV含Operator01／已移除Peer02／替換Peer03共3列，throughSequence21／combat尾界2，Operator01中彈2／耗損40／健康60，三人耗彈／擊殺皆0；每項與該次ledger及封存回放一致。真正下載CSV SHA `f0de1ae7c3b095c02f722bb10e8c5eaebee2bb19ca801d434345bb85a727d0b5`，獨立Python標準csv parser再次核對。原生流程觀戰瀏覽器仍SwiftShader，client無圖形，沒有新增GPU／聽感證據。

writer全停後helper回F的runtime-snapshot共14檔與保留C SSD原件SHA一致，唯讀稽核前後皆保持；本輪沒有直接開原DB／snapshot SQLite，沒有二次覆寫snapshot。來源／binary仍F，非F USB全資料或跨機／25台驗收。`artifacts/report-v1-validation.json`保存本輪完整摘要。Unity source fingerprint仍 `792a3aaac9a7903159718a898324def8f6ba4769f908f1f46f30a6c77744c725`，既有Windows／Quest receipts及原scene／prefab識別相同；沒有改Unity來源／資產pin／shader、rules0.8.0、envelope6／world schema1／原binary header／checksum，未重建Editor／102 EditMode／APK，前輪結果保持歷史證據。只同步API／UI及兩個PC helper的明確版本gate，不需因報表重新生成場景。原5080確認仍0.16／原歷史，沒有替換。

首輪HTTP在既有無效憑證啟動檢查等待退出10秒逾時，finally另有臨時server.log sharing violation；失敗 `artifacts/report-v1-http.log`保留，未放寬timeout／修改憑證政策。確認本輪owned dotnet已無存活後，正常完整重跑446通過，根因未證實。瀏覽器先有214通過；補輪詢提示保持及精確MIME後，下載比對另曾失敗，記錄在report-v1-browser-selection-failed.log。檢視發現selectSession等待背景更新前尚未清掉舊場狀態，改為立即取消下載／清統計／隱藏面板，再以selection epoch只接受最後選擇；新增明確hold背景更新的兩個回歸。新測試的首輪unroute早於delayed fulfill，觸發Route already handled，失敗report-v1-browser-gate-failed.log保留，改等fulfill完成才unroute；未放寬產品政策或斷言。最終58／217全部通過，包含text/csv-fake拒絕。最終原生49重新執行；先前071253-1dc01ef2的49項／143幀／0.296376秒證據及14檔snapshot另保留，不混算成最終場。完整11項仍開發中，接續完整人物／動畫／聲學、複雜通路、長任務／跨機及實機／MR／硬體／25台，沒有因報表完成縮減目標。

功能提交 `46794a09d5e7d6439c704e537affc81fab5b4e1d` 已推送main並確認遠端一致；GitHub #1保持open，更新後獨立讀回2955字本文一致，保留原11項、完整目標及原63864字封存連結。[本次CI run41144100763](https://github.com/peca12968/vr-command-center/actions/runs/41144100763)／check124365009147實際failure、steps=null，annotation明示帳戶付款失敗或支出上限、工作未開始，沒有雲端測試執行結果；未改帳務／重跑。完整目標繼續進行。

## 2026-10-31：軍事玩家人物、保存步態與桌面換彈雙臂

從乾淨 `35ad78e` 接續無頭盔PC主線，新增 [PLAYER_BODY.md](PLAYER_BODY.md) 的 `player-body-v1`：原創頭盔／護目鏡、背心／彈袋、雙腿／靴及桌面雙臂，404面、五個Mesh／一材質，SHA `1035ca0dffafc31226616485c58ef530d8e7b809feef2b5e461229424bc9703b` 固定。原步槍／手套／閃光／NPC／掩體及獨立combat-audio-v1沿用，八個既有外觀與reader保留。

API／UI **0.26.0**、Unity **0.28.0／Android code32／NGO26**。header playerPresentationVersion新1／缺失0，每玩家hasPlayerPresentation及walking明確保存；新profile要求原敵軍／武器／雙方fire版本1。NGO既有walking欄位新增玩家語意並與presentationTick原子複製，需來源／API／UI／全部遊戲程序一起更新，不降reader。rules0.8.0、envelope6、mission／world schema1、票券2、environment1及原始binary header／checksum保持，沒有更動傷害、射速、命中、碰撞、0.5秒姿態／1.5秒世界新鮮度或admission。

只有原本接受成功、Running／存活／連線玩家的平面移動>1mm會標記移動tick，四tick內walking；轉頭／高度、拒絕及Preparing不觸發。保存tick%12產生±18度對向腿旋轉，Pause不推進步態時鐘，但原頭手追蹤仍可更新。根在頭部平面座標／地面Y0、軀幹垂直比例eyeHeight／1.65，身向取頭部yaw；這是裝飾性三點推算，不是腰腳追蹤、屈膝或腳掌IK。桌面腕點跟隨既有合成手套／保存換彈時鐘，兩節臂可延展、超出範圍隱藏；Tracked不把pointer當握點、不合成雙臂或改追蹤資料。只對新視覺的quaternion副本正規化，本玩家body隱藏且不求解live姿態，原接受旋轉容差／界線保持。

真正Prepare、**102項EditMode（0 failed／skipped）**、Desktop成功，原scene／prefab ID保持，未RebuildArena。測試覆蓋共用資源最後lease釋放、實際頭／腿／腕Mesh矩陣、NGO walking／Equals、owner隱藏、合法非單位四元數、JsonUtility新／舊契約，以及真正保存prefab的Visual子物件。Desktop receipt UTC2026-10-30T22:28:56.4385532Z，fingerprint `792a3aaac9a7903159718a898324def8f6ba4769f908f1f46f30a6c77744c725`。locked restore／Release build零警告錯誤、**629核心、403 HTTP、43世界、58 Node／201 Chromium**通過；涵蓋接受／拒絕／idle／Pause步態、新資料不能漏標記、舊外觀、C#／JS向量及實際Mesh跳轉還原。瀏覽器為SwiftShader，不當作原生GPU。

最終 `desktop-venue/20261031-063112-834f3646` **4項真正雙PC流程**通過。第一玩家實際S／Down／Right到z=-4.504、heading54／pitch15，第二玩家實際W、Space一次及R，六張自己的observer GPU PNG均已檢視。新頭盔／背心／腿／靴可見，舊綠色頭手標記已在Visual子層正確停用；只改執行時Renderer，不改prefab／joint Transform。Probe只在明確Windows Development／可見untracked owner及全新絕對目錄安裝，600秒／8張／900萬像素，沒有PCM／麥克風／OS畫面／RPC或姿態輸入；一般／Editor／Android不安裝。

| 原生取樣 | 實際結果 |
|---|---|
| Running移動 | tick4496、walking=true、stride=-15.58844°，真正步態PNG。該幀遠端頭部仍插值中，與保存的接受位置相差0.02246647m；不能把它稱為精確保存的繪製幀 |
| 兩張Pause | 同tick4499／walking=true／stride=-9°，步態與時鐘相同；端點逐軸最大差2.38419e-7m，在1微米界線內。回到Running的tick4522為idle／stride0 |
| 換彈Pause | tick4787、reloadUntil4790，即第27tick；左腕依原換彈回位動作改變，非峰值抽匣畫面。槍口／原動作／彈藥規則不改 |
| 任務封存 | 2536幀、耗彈1／命中0／擊殺0／雙玩家損耗0／健康100，回放與ledger一致、pending=false、活動0；最大來源年齡0.243825秒 |

六個取樣已在**額外完整SQLite副本**稽核。兩張Pause與換彈為相同保存tick，頭部／腕點與保存資料求解的最大世界端點差約3.15e-7m。Running／idle有兩張NGO取樣比最近10Hz保存packet晚1tick，按實際觀察tick及相對腕點比較；沒有假稱每張都精確對到保存幀。原件及F snapshot的24檔SHA於稽核前後保持，沒有直接開原DB／SHM。

新增47項控制台UI／native整合，`20261031-063618-c4df481b` 167幀／最大來源年齡0.308984秒；含真實來源的404面人物及封存後頭部／步態／腕點核對，client為無圖形、瀏覽器SwiftShader。普通無probe的 `20261031-063915-8b74dc78` 七場五房獨立／重用／封存後Linked通過，583幀／0.200379秒；`unity-admission/20261031-063937-7264fe3b` 八項無圖形入場／撤銷／transport釋放／同admission重連通過，373幀。成功組cleanup零錯誤、活動0，三組venue自己的SSD runtime在writer全停後回F，24／14／26檔與保留原件SHA一致；來源／binary仍F，非F USB全資料或跨機／25台驗收。

失敗及修正保留：首輪向量輸出Yaw／yaw大小寫衝突，改為inputYaw後Node通過。原生首輪150秒視角定位超時，次輪在單次W已回idle後要求非零Pause而等待超時；其後改直接擷取真正Running步態，保留原四tick呈現政策。原生圖另揭露head／hand Renderer在Visual子物件，修正層級停用並新增保存prefab回歸。`060538-b116deea` 是明確停止自有target的失敗組，cleanup另有seal錯誤、原資料保留，不列為通過；其他失敗組及成功組分開。`061347-f54c8112` 的暫停字典逐位相等斷言被2.38e-7m浮點差觸發，改明示1微米門檻及保存實測差值。`061931-a2d2b497` 診斷請求原位寫入造成Sharing violation，改同目錄原子replace、reader共享ReadWrite／Delete，helper優先讀終止report而非繼續等舊status；最終來源／102 Tests／Desktop及原生均重跑。HTTP首輪無效憑證程序10秒退出逾時，未放寬timeout，後續完整403／43通過；未證實根因。

Quest首輪在Bee後處理exit3／Editor exit1，UnityLinker成功且沒有具體編譯錯誤；已保存Editor／Bee／buildreport失敗檔，程序終止且F空間足夠後以同來源重試，沒有改Library／ACL／安全設定。重試Editor exit0，Quest receipt UTC2026-10-30T22:52:26.8221840Z，與Desktop相同fingerprint及原scene／prefab ID。APK46,309,126 bytes、SHA `a445f8e1e18d9114df5787dda60d3069ec5346ebb0ce6564f14155d2e2865583`，v2簽章、min32／target35、code32／bundle0.28.0及六個ELF64 AArch64庫含libil2cpp已核對；沒有手動重封裝／重簽或頭盔安裝。成功的三組venue及admission共39個原生／API log未見指定NullReference／MissingReference／ObjectDisposed／IndexOutOfRange／Shader error，完整本機證據在artifacts/player-body-validation.json。原5080仍API0.16／原歷史，未替換。完整11項目標保持開發中；第一人稱全身、真正腰腳／手指及完整動畫、複雜地形、原偶發姿態原因、跨機，以及Quest／VIVE／MR／廠商硬體／25台仍分別待驗。

功能提交 `241f2acb0dc4e4b8ca6313f1407c4576c9de1090` 已推送main並核對遠端。GitHub #1已更新，讀回open／3470字與送出本文完全一致；原11項範圍與63864字封存留言連結保留。[CI run41141572882](https://github.com/peca12968/vr-command-center/actions/runs/41141572882)／check124356841079實際failure、steps=null，annotation明示付款失敗或支出上限，工作未開始，不能稱雲端測試通過。另有ubuntu-latest遷移通知；未改帳務或重跑。

## 2026-10-31：接受射擊事件的玩家／敵軍空間音效

從乾淨 `f25b097` 接續使用者「無頭盔，先繼續電腦端」。新增獨立固定的 `combat-audio-v1`、原創合成步槍／手槍PCM與Unity／瀏覽器共用接受事件游標；規範、操作及pin見 [COMBAT_AUDIO.md](COMBAT_AUDIO.md)。API／UI **0.25.0**、Unity **0.27.0／code31／NGO25**。header combatAudioVersion缺失0／新來源1，必須有player／enemyFireVersion1；actor presentationRunning與原fire欄位原子複製。固定player-fire-v1與八個舊幾何profile、rules0.8.0、envelope6、mission／world schema1、票券2及environment1保持。協同更新來源／API／UI／全部遊戲程序，不能降reader或重寫歷史header／checksum。

聲音只來自已接受的新sequence，保留世界槍口；最多age3 tick／相鄰觀察差10 tick，首次加入、seek、長缺口、重新啟用先baseline，Pause／Ended停止。每listener32個同房空間聲源，1–25m線性衰減／doppler0；滿載重用最舊。沒有本地射擊預測、傷害／射速／碰撞／姿態規則改動，pointer／Tracked不搬動。瀏覽器明確點音效才啟用，換錄製／登出關閉，手動定位不補播；回放依事件重建短聲音，非原始音軌。沒有遮擋／混響／完整聲學設計或漏包每發可聞保證。

locked restore、Release build **0警告／錯誤**，**612核心、403 HTTP、43世界、53 Node／196 Chromium**通過；包含舊header0、未知版本拒絕、新版本fire witness條件、已接受stream不能移除音效政策、C#／JS游標對照、實際Web Audio非零、歷史序號／tick／槍口一致、Pause釋放聲源、舊錄製及按鈕狀態。真正Prepare、**93項EditMode（0 failed／skipped）**、Desktop成功；測例逐sample比對匯入PCM、32個無Collider聲源與明確釋放、NGO phase原子複製／Equals及重複Prepare資源GUID保持。未RebuildArena，原scene／prefab ID保持。Desktop receipt UTC2026-10-30T21:20:34.0971906Z，fingerprint `a62c4eb5139e5e64a2074f86bfe5954fd1067a544899cda3ee8a7238d7c0324e`；現在也包含WAV／meta與Resources資產引用。

首輪Prepare因測試組件直接引用與AudioImporter舊API失敗，改為正確Editor測試組件及defaultSampleSettings.preloadAudioData；93測試首輪92通過、1個EditMode清理反例失敗，新增明確IDisposable／despawn釋放後93全通過。瀏覽器首輪用environmentVersion0 fixture卻等待weather峰值，改為獨立combat峰值；後續196通過，另補換錄製音效狀態／epoch及reset後再全跑。兩次HTTP無效憑證程序10秒退出逾時，保留失敗log、未放寬timeout；其後以UTF-8正常完整403及43世界通過，沒有證實逾時原因。原生新helper首輪Python comprehension iterable內assignment expression語法錯誤，啟動前即失敗，改為明確predicate後才實際運行；不把該次當原生證據。

`desktop-venue/20261031-052256-580e3a99` **4項真正原生流程**通過。Sky實際Space一次、HUD30→29，之後操作員開AI至兩次原20點傷害，再停止AI／Pause／Resume，沒有姿態／RPC／武器注入。自己的AudioListener probe明確finish後才真正End／精確seal：

| 證據 | 實際結果 |
|---|---|
| 保存的聲源序號 | 玩家1／敵軍2、4；事件tick287／439／459，播放觀察tick288／440／459，保存槍口逐軸核對一致，沒有重複cue |
| PCM | 48000Hz stereo16-bit、1,287,168 frames／26.816秒、1257 callbacks、2,574,336 float samples；峰值0.158417、RMS0.00290234；WAV SHA `62e6035abbe5a8647d7b351d039a14032dc27749403449132a9458b675ddd648` |
| 靜音 | AI尚未啟用／玩家尚未開火基線、Pause穩定段與無新發的Resume尾段峰值均0，cue總數保持3 |
| 遊戲封存 | 314幀、耗彈1／命中0／擊殺0／中彈2／損耗40／健康60，回放與ledger一致、pending=false、活動0；最大來源年齡0.374625秒 |

這些是本遊戲混音DSP與實際播放呼叫，沒有麥克風／OS loopback、GPU擷取或人員聽感。Probe只在明確Windows Development／可見untracked owner、全新絕對目錄才安裝；180秒／1600萬float／12000視窗／1024 cue，超限或格式變更不算complete。普通遊戲有音效但無診斷，Editor／Android不裝探針。所有播放射線已在**額外完整SQLite副本**核對，未直接開保留原DB或snapshot；稽核後18檔原件／snapshot SHA不變。

普通無音訊診斷的 `20261031-052512-bdd7f05b` 七場五房獨立／單房重用／封存後Linked通過，581幀、最大來源年齡0.223837秒；不是25台。`20261031-052417-d15f5c04` 控制台自訂任務／動態名冊／觀戰及封存回放 **45項UI／native整合**通過，152幀、最大來源年齡0.137755秒；該組client為無圖形，瀏覽器SwiftShader。三組cleanup零錯誤、活動0，自己的SSD runtime在writer停止後由helper回F，18／14／26檔與保留原件逐檔SHA一致；來源及binary仍F，非F USB全資料配置。`unity-admission/20261031-052534-604e8f45` **8項無圖形**入場／撤銷／transport釋放／同admission重連通過，448幀、封存與回放一致、活動0。

Quest真正Editor exit0，receipt UTC2026-10-30T21:34:56.0225326Z，與Desktop相同fingerprint及原scene／prefab ID；APK46,285,274 bytes、SHA `c1df68caf967e819c1ae0b9f9ca1dcd958c55cab9185419de386a81f2d244351`，v2簽章、min32／target35、code31／bundle0.27.0與六個ELF64 AArch64庫含libil2cpp核對通過。這次APK為Unity原始建置，沒有手動重封裝／重簽，未安裝頭盔。三組venue及admission共38個原生／API log未見指定Exception／NullReference／MissingReference／ObjectDisposed／IndexOutOfRange／Shader error；完整本機證據為artifacts/combat-audio-validation.json。本機原5080仍原API0.16／原歷史，未被測試替換。完整11項長期目標持續開發；玩家全身、完整動畫／聲學、複雜場地、原偶發姿態原因、長任務／跨機，以及Quest／VIVE／MR／廠商硬體／25台仍分別待驗。

功能提交 `32725d1467b2e8990b793e9d90a33a416a31daef` 已推送main並核對遠端，GitHub #1已更新且讀回open／2925字與送出本文完全一致；原11項範圍與63864字歷史封存留言連結保留。[CI run41132393727](https://github.com/peca12968/vr-command-center/actions/runs/41132393727)／check124326302315實際failure、steps=null，annotation明示帳戶付款失敗或支出上限，工作未開始，不能稱雲端測試通過；未改帳務或重跑。另有ubuntu-latest遷移通知，不影響本輪本機結果。

## 2026-10-31：兩端姿態時序與受控丟包校準

前輪玩家射擊效果已提交，屬實際進度；本輪從乾淨 `bcdeed9` 接續無頭盔PC主線，追查偶發姿態過期。新增明確選用的NativePoseTrace，分開記錄owner的RPC呼叫、server RPC接收／格式／節流／接受或拒絕、發布時的參戰轉換，以及>100ms主線程空窗。WorldCapture／WorldJournal／CombatJournal／ManagementApply／WorldPublish與玩家GPU讀回／PNG編碼／寫檔各自量測，使用Stopwatch及UTC ticks保留同主機階段時間。規範及操作見 [POSE_TIMING.md](POSE_TIMING.md)。

Unity **0.26.1／Android code30**，API／UI **0.24.0**、NGO **24**及原player-fire-v1／所有pin、header版本、envelope／schema／rules保持。沒有新wire、沒有改0.5秒姿態新鮮度、防瞬移、Tracked座標、碰撞、射擊、admission或HUD警告，也沒有改1.5秒世界來源門檻。一般不帶旗標、Editor及Android不安裝；Windows Development明確--vr-pose-trace且全新絕對目錄才建立。普通呼叫只經未啟用guard，不另建資料／背景worker。

緩衝上限32768列／正常240秒，溢出明示truncated=true／complete=false並保留最早證據；主線程阻塞時須待Update恢復才能截止。只在記憶體收集，每0.25秒檢查finish.request，截止後才序列化／寫出最終report，該段輸出不在觀察內。沒有姿態位置／旋轉、姓名、憑證、UDP payload、GPU或PCM；可以配合另選用的GPU探針量測其區段。report.complete只代表診斷收集，真正End／精確seal另驗。

真正Prepare、**87項EditMode（0 failed／skipped）**、Desktop均成功；5項新測例覆蓋有界保留最早資料、不可變快照、無效時鐘／容量、JsonUtility精確64位UTC、一般未啟用行為，以及非法來源byte255仍可記錄而權威拒絕保持。原scene／prefab ID保持，未RebuildArena。Desktop receipt UTC2026-10-30T20:34:15.2740417Z，fingerprint `6615ee45cb079cc5c342c68f797669944671153412780358364727d3f811e239`。另**3項Python分析反例**通過，涵蓋跨邊界收件間隔、玩家主線程停頓混雜與UTC跳動；已加入CI。這輪沒有後端／管理UI／共用simulation變更，未重算前輪597核心／403 HTTP／43世界／49 Node／189 Chromium為本輪執行。

初版86 Tests、a65來源的雙平台與041743-af6d8459校準雖已成功，覆核發現記錄器僅接受source0–2，會在原驗證拒絕非法來源byte前先拋錯。改為保存完整原始byte0–255，仍由原AvatarPose.Valid拒絕非法姿態；補第87項反例後重跑Tests／Desktop與最終原生。初版receipt／資料保留，不配用最終來源。

新增check-desktop-pose-trace.py：自己的API／room3 server／可見Simulated玩家與loopback gate，先自然60秒（沒有GPU readback），再原樣丟棄單一玩家上行1.2秒，下行維持，最後真正Space一次與原生GPU探針。沒有RPC／姿態／武器注入、沒有防火牆變更。analyze-pose-trace.py只讀關閉後JSON及階段時間，不開SQLite／憑證，不會重建原資料SHM；若控制段玩家或server停頓、或時鐘跳動造成混雜，不能稱校準通過。

`desktop-venue/20261031-043445-1af91e65` **4項原生流程及分析校準通過**：

| 階段 | 實際觀察 |
|---|---|
| 自然60.151秒 | 1084個間隔，玩家RPC呼叫最大56.089ms、server接收66.677ms／接受66.677ms；沒有發布非參戰轉換、拒絕或>100ms主線程空窗。約18次／秒是這個場的實際取樣呼叫頻率，20Hz仍為設定目標，不冒充精確20Hz或頭盔實測 |
| 上行丟包1.2秒 | gate丟棄53 datagrams；玩家呼叫最大55.717ms且兩端沒有>100ms主線程空窗，server接收／接受空窗1.222318秒；最後接受姿態年齡0.588976秒時發布非參戰，恢復後同admission／原位置／健康／彈藥。沒有將發布觀察年齡當成政策閾值或RTT |
| 真正Space與GPU | 彈藥30→29、tick2091閃光／22mm後座、tick2128 Pause歸零，兩張原生PNG已檢視。GPU讀回最大38.168ms、PNG編碼13.939ms、寫檔1.086ms；該段玩家呼叫最大134.974ms、server接收183.526ms、一次主線程空窗134.971ms，沒有0.5秒收件空窗／發布失聯。不能把134.971ms全部歸因於GPU |

此場client／server分別2116／10842列，觀察118.471／122.482秒，complete=true、未截斷。相鄰UTC與單調時鐘步進差最大1.456／1.284ms，控制段未受大時鐘跳動混雜。GPU probe另以明確local stop完成，observedEnd=false、audioSamples／callbackCount0；遊戲另精確seal，耗彈1／命中0／擊殺0／耗損0／健康100，回放／ledger一致。1153幀、最大來源年齡0.188868秒，活動0、cleanup及gate-cleanup零錯誤。

普通未啟用旗標的 `20261031-043659-71fdf936` 七場五房／單房重用／封存後Linked通過，607幀、最大來源年齡0.229533秒，沒有產生trace目錄；非25台。兩場均自己的SSD runtime，writer停止後23／26檔由helper回存F，與保留SSD原件逐檔SHA一致，沒有另開SQLite改動副本。來源與binary仍F，不能稱F USB全資料通過。另 `unity-admission/20261031-043721-aa8aa0da` **8項無圖形**入場／撤銷／transport釋放／同admission重連通過，397幀、精確封存／回放一致／活動0。三組33個log未見指定NullReference／MissingReference／ObjectDisposed／IndexOutOfRange或Shader error。機器證據在artifacts/pose-timing-validation.json。

受控恢復另外在額外完整SQLite副本唯讀核對：保存packet616為非參戰、623已恢復，head／muzzle／forward／health／magazine／reserve完全一致；所有writer早已停止。檢查後再次核對保留SSD原件與F snapshot全部SHA未變，沒有直接開原DB／SHM。檢查器亦補上這些欄位的直接保存／比較；本場以封存副本核對作為證據。

這次診斷能辨別受控上行收件空窗與本機大停頓，但**沒有重現或證明歷史偶發原因，也沒有宣稱已修好失聯**。PoseSend只是RPC呼叫前，不是transport完成；無逐packet配對，不能單靠它分辨NGO排程與網路。BodyConnection只在10Hz發布觀察，不是每tick；乾淨樣本不能排除更短中間狀態。主線程最大值0只是沒有記到>100ms空窗。資料只證明此單次同主機／單房情境，不是跨機RTT、FPS或25台／頭盔效能。

最終Quest首次重建在建立Library/Bee/PlayerScriptAssemblies時Access denied，Editor明確exit1，未產生新receipt；失敗log保留。程序退出後該目錄已不存在，F空間足夠、無活躍Editor／編譯子程序；未改快取內容／ACL／安全設定，以相同來源重試。重試Editor exit0，Quest receipt UTC2026-10-30T20:47:25.4333944Z，fingerprint `6615ee45cb079cc5c342c68f797669944671153412780358364727d3f811e239` 及原scene／prefab ID與最終Desktop完全一致。APK68,404,947 bytes、SHA `4fe0ded3395f6dcb4136ff982cc29d9622c7bf610e151b5154e7a5591851bd14`；v2簽章、min32／target35、code30／bundle0.26.1及六個ELF64 AArch64庫含libil2cpp核對通過，沒有頭盔安裝。體積覆核發現ZIP中央目錄引用的壓縮資料46,239,658 bytes，另兩段未引用間隙共22,144,012 bytes，已保存包裝稽核；沒有重封裝或重簽，保留Unity原始成功產物，不把APK體積變化當作診斷／裝置效能證據。完整11項長期目標保持開發中；後續持續取證偶發原因，並接續射擊音效、玩家全身、完整動畫／場地操作與跨機。Quest／VIVE／MR、廠商硬體及25台仍待分別驗收。

功能提交 `2b4f1396a25350010ac38c87a63ee3137352f9f5` 已推送，遠端main核對相同。GitHub #1更新為本輪結果，讀回open／2946字與提交內容完全相同，原11項範圍、後續依賴及原63864字封存留言連結保留。[CI run41126416900](https://github.com/peca12968/vr-command-center/actions/runs/41126416900)／check124305993088實際failure、steps=null；讀回annotation明示付款失敗或支出上限，工作未開始，不能稱雲端通過。另有ubuntu-latest遷移通知；未改帳務或重跑。

## 2026-10-31：玩家接受射線、原生閃光與槍身後座

從乾淨 `141652d` 接續使用者「目前沒有頭盔，先繼續電腦端」。新增 `player-fire-v1`，組合固定264面玩家步槍、原合成手套、728面NPC與32面閃光；玩家脈衝倍率1.2，沒有外部素材。組合資料SHA `187c7df5346419edadafa1cc74a04db0763dda268650e066dbbcaf8304e60ff0` 固定，生成器先驗舊pin，原七profile／網格／色彩／reader完整保留。規範見 [PLAYER_FIRE.md](PLAYER_FIRE.md)。

API／UI **0.24.0**、Unity **0.26.0／code29／NGO24**。新header playerFireVersion1，缺失仍0，新profile同時要求enemy1／weapon1／enemyFire1；NGO既有原子fire欄位加入玩家語意，全部來源／API／UI／遊戲程序一起更新，不能降reader。envelope6、mission schema1、world schema1、票券2、environmentVersion1及rules0.8.0保持，binary原header／payload／checksum不重寫。

只在實際接受ShotFired後保存sequence、tick+1、原點及方向；去重／拒絕快速射擊不重啟效果或多扣彈藥。逐packet以上次狀態及本次事件核對最後一發，原合法muzzle範圍保持。閃光age0–2（0.15秒）跨正常10Hz發布，槍身後退依age0–3為14／22／12／4mm，age4復位。暫停／結束／seek只依保存tick，死亡／離線隱藏、換彈停止槍身後退但不抹去接受閃光。沒有聲音、Light、Collider或規則變更。

只把借用原Mesh的槍身Renderer及原彈匣放在後座子物件；原根Renderer執行時停用並排除通用顯示列表，真正根槍口／pointer／握點／Tracked資料不移動。Unity閃光脫離avatar父層，避免before-render追蹤更新挪動歷史射線。view銷毀自己的flash，最後model lease才釋放共享網格／材質，沒有重建prefab。

locked restore、Release build0警告／錯誤，**597核心、403 HTTP、43世界、49 Node／189 Chromium**通過。涵蓋tick0接受、去重、拒絕快速連射、同tick換彈、原邊界、事件射線不可改寫、SQLite非零玩家射擊重開、legacy缺欄位及原binary。C#／JS向量、實際WebGL非零後座／歷史閃光／直接seek及最終統計一致，瀏覽器為SwiftShader。真正Prepare、**82 EditMode（0 failed／skipped）**及最終Desktop成功；未RebuildArena，原scene／prefab ID保持。Desktop receipt UTC2026-10-30T19:52:40.1413652Z，fingerprint `9c9d9539bf209f2f66a4ac23483e8e67ab9cbcaf8ef2022de30da0208f0adef7`。完整本機證據在artifacts/player-fire-validation.json。

首次Prepare漏引VrCommand.Simulation造成CS0246，補直接using後通過，失敗log保留。早期暫用2tick脈衝，在發布取樣覆核後於未發布profile定為3tick並固定最終pin；重新生成、82 Tests、Desktop與完整核心／Node／瀏覽器皆用最終3tick來源。HTTP首輪在競爭writer程序10秒退出檢查逾時，接著cp950輸出失敗；第二輪在無效憑證程序10秒退出逾時且temp log清理遭鎖。兩份失敗log保留，未放寬timeout；第三輪以UTF-8完整403通過。未證實逾時的根因，不能歸結為已修復。

新NativePlayerFireProbe僅明確Windows Development／可見untracked client／全新絕對目錄，300秒／8圖／每圖900萬像素上限，無PCM／OS擷取／輸入。首場 `035311-ec9f5ddb` 白天實際Space扣彈並擷取閃光後，觀察到frame338／tick592短暫connected=false／rig=None，檢查器assert中止；frame340／tick597已恢復。cleanup正常、原場資料保留，不列全通過。檢查器改保留此類樣本，實際輸入階段只接受有效Simulated rig，不改遊戲或1.5秒新鮮度門檻，原暫時失聯根因仍待。

| 最終PC場（前綴20261031） | 幀／最大來源年齡 | 證據 |
|---|---|---|
| 035502-2fb88aa3 | 779／0.301179秒 | **4項真正按鍵／GPU流程**：Space白天與夜間各一次，兩張實際脈衝在tick740／909、後座均22mm；接受事件tick739／908，SQLite event packet398／487，射線float32精確相符。GPU時鐘與10Hz存幀不必同tick。Right一次後HUD方位003°、瞄準改變但保存射線不改；真正根仍pointer前0.15m。Pause在770／1120，效果已歸零，沒有峰值暫停GPU宣稱；峰值Pause由核心與Unity測試證明。四張GPU圖已檢視；complete=true／observedEnd=false／明確local diagnostic stop，audioSamples／callbackCount皆0。遊戲另精確seal，耗彈2／命中0／擊殺0／中彈0／健康100，回放一致 |
| 035635-194329c4 | 153／0.159144秒 | **45 UI／native，client無圖形**：任務保存／配置、動態名冊、天氣／AI／Patrol／Pause／End、鏡頭及封存回放，含真正NPC接受射線與WebGL效果核對。沒有本輪原生雨夜／雷聲人工檢視 |
| 035735-8b13eb6c | 七場580／0.192192秒 | 五個真正server／每房一個client隔離、單房End／重用、全部seal後Linked、舊票／升權拒絕及七個stream精確封存，新profile／playerFire1；非25台負載 |

三組均Simulation／Simulated、pendingTelemetry=false、活動0、cleanup零錯誤；writer停止後21／14／26檔回F並與保留SSD原件逐檔SHA相同。首次SQLite唯讀稽核重建了封存副本的worlds.db-shm（mode=ro仍可寫派生index）；已保留該派生SHM於額外artifact並從未變動的原件恢復，重新核對全部檔案一致。正式數值稽核改在另一份完整副本執行，前後再次確認原件及封存SHA不變。未重寫DB／WAL／journal／事件。程式及binary仍F、runtime明確SSD，source age非RTT／FPS，不能稱F USB全資料或25台通過。

另 `unity-admission/20261031-035827-e474b2ca` **8項無圖形**入場／撤銷／transport釋放／同admission重連通過，365幀、精確seal／回放一致與活動0。四組38個log未見指定NullReference／MissingReference／ObjectDisposed／IndexOutOfRange或Shader error。本輪未重跑真正按鍵擊殺／R換彈、互動走離出生點的重連、完整碰撞、GPU閃電或DSP／聽感；較窄SDK未另跑。原5080唯讀health ok，仍API0.16／原歷史，沒有替換DLL／資料／憑證。

Quest ARM64／IL2CPP亦exit0，receipt UTC2026-10-30T20:06:54.3684764Z，來源fingerprint與原scene／prefab ID和最終Desktop完全一致。APK46,228,012 bytes、SHA `6651622b5695d968f7222fa306a501b3cefb41330864050090abe8ab5cea1e71`，簽章v2、min32／target35、code29／bundle0.26及六個ELF64 AArch64庫含libil2cpp核對通過。沒有頭盔安裝。完整11項長期目標保持開發中；玩家／敵軍射擊音效、全身人物、完整動畫、原暫時失聯原因與跨機仍需推進，Quest／VIVE實機、MR、廠商硬體及25台須分別驗收。

功能提交 `96ab34918d8fa2619f7f674557d356cd70f0ccbf` 已推送，遠端main核對相同。GitHub #1原63864字本文已[完整封存於留言](https://github.com/peca12968/vr-command-center/issues/1#issuecomment-6532297157)，讀回確認原文完整後，本文改為目前11項目標／最新交付／後續及文件連結，保持open。原文SHA `d56064c431b1d8c83e5eef3f6cf3945f6270752b9582b83416a182f862c42fed`；新本文2413字讀回相同。[CI run41120847295](https://github.com/peca12968/vr-command-center/actions/runs/41120847295)／check124286744394目前queued、尚無步驟或雲端通過結果；不拿前輪帳務annotation推定本輪狀態，未改帳務或重跑。

## 2026-10-31：按接受射線還原敵軍閃光與槍身後座

從乾淨 `d8ee348` 接續無頭盔的PC主線。新增 `combat-effects-v1`，沿用固定728面持槍NPC／玩家換彈／掩體，再加原創32面封閉星形脈衝，每NPC最大760面。資料SHA `b8fe83d66781c2f65816d6873cc08ba01314418d42777a55e9eea2d1ee34a9bb` 固定，生成器先驗舊pin、Unity／瀏覽器共源；原六profile、原網格／色彩及reader保留，沒有外部素材。新unlit Shader保留instancing／stereo宏，不加Light或音效。規範見 [ENEMY_FIRE.md](ENEMY_FIRE.md)。

API／UI **0.23.0**、Unity **0.25.0／code28／NGO23**。新header enemyFireVersion1，缺失仍0；新profile還要求enemy1／weapon1。NGO enemy row原子新增fireSequence、fireTickPlusOne及原點／方向；來源／API／UI及全部遊戲端一起更新。envelope6、任務schema1、world schema1、票券2、environmentVersion1及rules0.8.0保持，不能降reader，binary原header／payload／checksum不重寫。

ArenaWorld只在原AI實際Emit EnemyShot後複製接受事件，逐packet驗證以上次狀態＋本次事件重建最後射擊；拒絕缺旗標、未來時鐘、憑空序號、改原點／方向或後續改寫。從未射擊明確true／sequence0／tick0／零向量。閃光使用保存世界射線，即使NPC已移動／轉向；age0–2顯示，槍身後退依tick為12／18／10／4／1mm、age5復位。僅停用原Gun Renderer並借同網格到子Renderer，真正槍口／手套／雙臂／Tracked資料、射速、原20點傷害與命中盒不動。Pause／Ended／seek保持保存tick，死亡隱藏效果但不刪歷史。沒有玩家步槍效果、聲音或實體後座，亦未完成完整人體／死亡／換彈動畫。

locked restore／Release build0警告錯誤、**575核心、403 HTTP、43世界、45 Node／184 Chromium**通過。新增事件證據、跨packet移動／改向、真實ArenaWorld暫停、死亡、SQLite非零射擊狀態重開、舊binary缺欄位與原位元組保留；C#／JS向量核對及實際WebGL閃光／位移／歷史射線／直接seek與統計一致。瀏覽器為SwiftShader。真正Prepare、**76 EditMode**及最終Desktop通過，原scene／prefab ID保持，未RebuildArena。最終Desktop receipt UTC2026-10-30T18:58:01.7951618Z，fingerprint `e2c4dba4f763a7109be018342b8e01154f0b247d921eddc383ed81da59470dbd`；Quest ARM64／IL2CPP亦exit0，receipt UTC2026-10-30T19:16:28.8845657Z，來源fingerprint及scene／prefab ID與最終Desktop完全一致；APK46,210,244 bytes、SHA `c7c4a34d13ef5126c2998cd597b863d4006bfbfad0bfe535ef139b48ae328013`，簽章v2、min32／target35、code28／bundle0.25及六個ELF64 AArch64庫含libil2cpp核對通過。沒有頭盔安裝。完整機器證據在artifacts/fire-validation.json。

首輪76 Tests有2項失敗：生成測例仍預期NGO22、Transform精確float相等；改預期23及1e-5m容差後重跑通過。首次世界smoke的固定fromMs200且假設必有非初始frame失敗，未保留當時數值，不能回推精確原因；改從來源實際保存的第6個packet時間求rightmost preceding sequence，要求精確序號且>1，另保存world-smoke-seek.json。最終requested409ms／expected6／actual6，43項通過；未放寬1.5秒來源或遊戲規則。Node測例的-0與0比較改驗證位移絕對值零，實際渲染／資料不改。失敗XML／log保留。

新NativeEnemyFireProbe只在明確Windows Development／可見untracked client／全新絕對目錄安裝，最多8圖／180秒、無PCM／輸入／OS擷取。EndOfFrame記錄實際套用而非較晚到的actor row，GPU影像與時鐘／Transform同行。首場 `025342-d1194176` 確有日夜GPU脈衝（tick1／22、12／18mm），但End撤銷入場會先despawn頭部，診斷未收到Ended而收尾失敗，不列全通過；cleanup正常、部分圖／資料保留。增加只停止診斷的本機finish.request，complete明確為收集完成，另有observedEnd／stopReason；伺服器seal獨立證明遊戲結束。重跑76及Desktop後才做最終原生。未使用的等待控制台場 `025526-971d0c03` 在未建立任何場次時正常停止，未算功能驗收。

| 最終PC場（前綴20261031） | 幀／最大來源年齡 | 證據 |
|---|---|---|
| 025840-cfe18ea8 | 582／0.158654秒 | **4項原生AI／GPU流程**：白天tick1及夜間tick21均有閃光／12mm槍身位移，圖片已檢視；對應world序號1／3及兩次傷害。Pause在tick11／32／43，效果已歸零，沒有宣稱此場在閃光中暫停。Patrol移動後仍保留原射線。兩張GPU擷取另外唯讀與封存SQLite逐event／float32射線精確核對。診斷complete=true／observedEnd=false／明確local stop，audioSamples及callbackCount皆0；真正場次另精確封存，耗彈0／中彈2／損耗40／健康60及回放一致 |
| 030033-6c7e1a82 | 155／0.163004秒 | **45 UI／native，client無圖形**：配置／任務保存、動態名冊、天氣／AI／Patrol／Pause／End、鏡頭及封存回放；新增實際WebGL射線／fire clock／flash與recoil核對，資料含真正接受射擊，非fixture注入。沒有人工GPU雨夜／雷聲檢視 |
| 030258-ac140d8d | 七場601／0.224976秒 | 五個真正server／每房一個client隔離、單房End／重用、全部seal後Linked、舊票／升權拒絕與七個精確stream封存，皆新profile／enemyFire1；非25台負載 |

三組均Simulation／Simulated、pendingTelemetry=false、活動0、cleanup零錯誤，writer停止後22／14／26檔回F並與保留SSD原件逐檔SHA相同。程式及binary仍F、這些runtime明確SSD，不是F USB全資料通過，source age非RTT／FPS。另 `unity-admission/20261031-030456-f7254c15` **8項無圖形**入場／撤銷／transport釋放／同admission重連通過，401幀、精確seal／回放一致與活動0。四組38個log未見指定NullReference／MissingReference／ObjectDisposed／IndexOutOfRange或Shader error。本輪未重跑真正按鍵擊殺／換彈、互動走離出生點重連、完整碰撞、GPU閃電或DSP／聽感；較窄SDK未另外重跑。原5080仍API0.16／health ok及原歷史，沒有替換正式DLL／憑證。完整11項長期目標保持開發中，實際Quest／VIVE、MR、廠商硬體、跨機與25台仍待。

功能提交 `7fb5ce2b376dd076255ae8a7de0358c7bfb3a36b` 已推送，遠端main核對相同。GitHub #1已同步本輪，讀回open／63864字，原62127字內容完整保留。 [CI run41114384316](https://github.com/peca12968/vr-command-center/actions/runs/41114384316)／check124264676068實際failure、steps=null；annotation明示付款失敗或支出上限，工作未啟動，不能稱雲端測試通過。未改帳務或重跑。

## 2026-10-31：敵軍雙手手槍與裝飾性雙臂

從乾淨 `3c3d71b` 接續無頭盔的PC主線。新增 `armed-combatants-v1`：原創緊湊型手槍、分離上下臂及合成手套，每NPC728面、八個共用Mesh／一材質；頭及腿取固定combatants-v1、手套為固定weapon-actions-v1的0.65倍副本，原五profile／pin完整保留。生成器先驗舊pin，新資料SHA `cc011e951163d4b846c4e2c217592251906844c0dfcee2f795618c8c1c388102`；check與記憶體改色反例拒絕通過。無外部素材／下載，規範見 [ARMED_ENEMIES.md](ARMED_ENEMIES.md)。

API／UI **0.22.0**、Unity **0.24.0／code27／NGO仍22**。新profile要求enemyPresentationVersion1及weaponPresentationVersion1，未加wire欄位；來源／API／UI與全部遊戲端一起更新。envelope6、任務schema1、world schema1、票券2、environmentVersion1與rules0.8.0保持，binary原header／payload／checksum與舊外觀不改，不能降舊reader。

共用C#9／JS依保存forward／tick求解雙臂，upper .22m／lower .25m，wrist附槍握點、elbow朝外下hint；不靠移動feet／追蹤資料補救。槍口仍feet+(0,1.4,0)、完整±90°pitch，頭仍±45°，命中half(.3,.9,.3)與AI射速／傷害不改。軀幹／頭位置是新裝飾性外觀，不改保存feet。Unity改用同一atomic actor row的原始位置，避免本地插值讓槍口偏離；10Hz階梯感未解。Paused／Ended及seek還原同姿勢，無Collider／NetworkObject。開火閃光需另保存射擊當下位置／方向及事件，本輪沒有補造；後座／NPC換彈／死亡、完整人體／手指／腳底IK、極端姿勢防穿插與音效仍待。

locked restore／Release build0警告／錯誤，**555核心、403 HTTP、43世界串流、41 Node／179 Chromium**通過。核心181個pitch核對方向／臂長、共線fallback／不可達拒絕、新profile版本政策及原20點傷害；SQLite保存重開新profile，保留舊reader測例。C#／JS向量、真正WebGL面數／子物件世界矩陣、直接seek、舊profile切換及精確結束統計通過，瀏覽器為SwiftShader。真正Prepare與**70 EditMode**通過，新增4項涵蓋外向網格、八Mesh重用／無碰撞、實際槍口／腕點及seek。Editor保存實際新增meta；曾暫時更新URP清單，最終Android匯入後與原檔無差異，未RebuildArena，原scene／prefab ID保持。

第一版Windows成功後覆核發現合法forward有微小長度容差，補上槍pitch前正規化及近單位向量測例，再重跑70 Tests／555核心／41 Node及179 Chromium，最終Desktop exit0。舊成功receipt另存artifacts/armed-desktop-before-normalization.json，最終receipt UTC2026-10-30T18:11:01.5598325Z，fingerprint `a712a41accad34ab19d2032cd1e204a2885e9158fd5decd4c6ea5fe74f27357f`；不能拿初版receipt配最終來源。較窄SDK在正規化修正前通過兩分支18 runtime／16 NUnit型別綁定，未當作最終Editor／APK證據。

| 最終PC場（前綴20261031） | 幀／最大來源年齡 | 證據 |
|---|---|---|
| 021117-c7d69f7a | 831／0.266805秒 | **44 UI／native**：保存配置／preflight、動態名冊、白天／雨夜／Pause的真正GPU畫面，近距離NPC雙手槍已檢視；AI傷害後GPU健康60／彈藥30/90、Patrol中Pause保留非零步態。封存回放的真正渲染槍口／完整方向／肘腕世界矩陣與保存frame核對一致，書籤／精確鏡頭及歷史玩家統計一致 |
| 021329-c5842479 | 七場605／0.165719秒 | 五個真正server／每房一個client隔離、單房End／重用、全部封存後Linked；舊票／升權拒絕，七個獨立stream精確封存且皆新profile／enemy1／weapon1 |

兩組均Simulation／Simulated、pendingTelemetry=false、活動0、cleanup零錯誤；14／26檔由helper在writer關閉後複製回F，再與保留SSD原件逐檔SHA一致。首次手動複製前的assert發現helper已產生snapshot，未覆寫；改核對既有副本。程式與binary仍F、上述runtime明確SSD，非F USB全資料或25台負載。source age為擷取新鮮度，非RTT／FPS。

另 `unity-admission/20261031-021401-e1fdfde9` **8項無圖形**入場／撤銷／transport釋放／同admission重連通過，381幀、精確封存／回放統計及活動0。三組共35個log未見NullReference／MissingReference／ObjectDisposed／IndexOutOfRange例外。本輪未重跑真正按鍵兩發擊殺、走離出生點的互動重連、完整碰撞、GPU閃電或DSP／聽感；既有結果保留為歷史，不混算新binary驗收。

Quest ARM64／IL2CPP亦exit0，receipt UTC2026-10-30T18:24:52.1314526Z；與最終Desktop來源fingerprint及scene／prefab ID完全一致。APK46,190,262 bytes、SHA `ad974f992046c7d70adcb19c7f9d0731e8e21ea79e869178fc96565d763caf5b`，簽章v2、min32／target35、code27／bundle0.24及六個ELF64 AArch64庫含libil2cpp核對通過。四張原生GPU截圖為Sky原始JPEG位元組，副檔名已對齊；完整機器證據在artifacts/armed-validation.json，未將舊APK或較窄SDK當本輪結果，沒有頭盔安裝。原5080已唯讀確認health ok、仍API0.16／原歷史，未替換DLL／正式憑證。完整11項長期目標持續開發中；後續接射擊事件及閃光／後座、玩家人物、完整動畫／音效、複雜地形／跨機與原停頓原因。Quest／VIVE實機、MR、廠商硬體及25台仍待分階段驗收。

功能提交 `5031250791b47da74363999659d41eb74c959064` 已推送，遠端main核對相同。GitHub #1已同步最新交付並完整保留原60538字內容，讀回open／62127字確認。 [CI run41106904487](https://github.com/peca12968/vr-command-center/actions/runs/41106904487)／check124239002725實際failure、steps=null；annotation明示近期付款失敗或支出上限，工作未啟動，非本輪雲端測試執行結果。未改帳務或重跑；本機結果獨立保存。

## 2026-10-31：保存換彈時鐘、分離彈匣及合成手套

從乾淨 `df2e649` 接續無頭盔的PC主線。新增 `weapon-actions-v1`，完整沿用既有人形敵軍／掩體，將固定264面步槍分為槍身240／彈匣24，加各120面的兩個原創手套；四Mesh／一材質跨avatar引用計數，無Collider或NetworkObject。生成器先驗證舊pin，再分離原三角形，新資料SHA `517c3616ec12dad34f25cc50f5309eae1033b62bcbbb636b4a3f378a5c12cab3` 固定；原四個profile及pin保留，沒有外部模型／貼圖。新舊原位264面的位置／法線／色彩已逐三角形核對，不能改舊回放。規範見 [WEAPON_ACTIONS.md](WEAPON_ACTIONS.md)。

API／UI **0.21.0**、Unity **0.23.0／code26／NGO22**。新header weaponPresentationVersion1及hasWeaponPresentation／reloadUntilTick直接保存原世界的30-tick完成點；共用驗證逐事件核對ReloadStarted／Completed，拒絕憑空、重疊或改時鐘。NGO玩家row原子含tick及until，來源／API／UI／遊戲端一起更新。預設及缺欄位舊header仍0，不補造動作，binary原header／payload／checksum保持；envelope6、任務schema1、world schema1、票券2、environmentVersion1與rules0.8.0不改，新資料不可降舊reader。

Unity／JS按保存tick做左手移向彈匣、抽出、短暫隱藏表示替換、插回與回握；Paused／Ended保留局部姿勢，seek不依本地wall clock。合成手套限Simulated且連線／存活，Tracked仍保留實際左手標記，不搬動關節資料配模型。槍口仍為原pointer前0.15m，動畫只動子物件；原射線、射速、換彈時間與彈藥規則不改。死亡／離線停止合成動作，原死亡可能留過期reloading旗標的規則保留；玩家身體／NPC武器、前臂／手指IK、物品庫、後座／死亡動畫、音效及真實換匣仍待，不能稱完整人物或追蹤握持。

locked restore／Release build通過、0警告／錯誤，**548核心、403 HTTP、43世界串流、37 Node／173 Chromium**通過。新增時鐘／事件證據、Pause／完成／原彈藥、無效及死亡狀態、原位幾何與資源生命週期、C#／JS全部30 tick與Tracked政策、真正WebGL子物件／非零位移／直接seek及統計。SQLite新profile保存／重開已覆蓋。原重複event交易反例因新換彈證據先被ArgumentException拒絕，補齊合法換彈狀態後仍確認原SQL唯一性拒絕，未放寬產品規則。

瀏覽器第一輪因API輸出目錄仍舊field-props.js而不識新profile，重新整包build；第二輪範例原無connected／rig，不能冒充合成手套，新增明確Synthetic測例rig並讓新版本匯入嚴格驗證；最後全套通過。舊無rig範例保持舊政策，沒有改其射線。失敗log／圖片保留。66項真正EditMode（0 failed／skipped）及Prepare／Desktop／Quest均exit0；新增5項覆蓋真正網格、共享無Collider、實際子Transform／根不動、Tracked資料不改、NGO及JsonUtility。另補強前輪舊NPC JSON測例為完整合法packet並驗證legacy讀取。未RebuildArena，原scene／prefab ID保持；Desktop receipt UTC2026-10-30T15:24:17.9621245Z，fingerprint `ab159159d9dbc182b4477d99125019db8052b6287485b362d8443bab0a1e8ef4`。離線SDK兩分支17 runtime／15 NUnit只證型別綁定。Quest receipt UTC2026-10-30T17:38:54.7872925Z，fingerprint與識別同Desktop；中斷前後來源再次核對一致。APK46,172,166 bytes，SHA `ae974c5fd51c5b34af2a346502a3dbba09cb102f313b1582fb3783b3b0602dde`，v2、min32／target35、code26／bundle0.23及六個ELF64 AArch64庫含libil2cpp核對通過；沒有頭盔安裝。

原生第一場 `20261030-232831-54ea8099` 在實際R／Pause後被中斷並斷線，不能算完整通過；`20261031-011139-67be926f` 早期第4 tick暫停、Space及30／89已觀察，但complete review標記逾時，亦不算全通過。兩場cleanup正常且原資料／快照保留。最終流程等到抽出階段才Pause，人工review等待改600秒，未放寬遊戲時間／來源新鮮度門檻。曾取到非遊戲視窗影像，未保存為遊戲證據；改用明確HUD影像探針，再以重新確認的遊戲視窗補完成畫面。探針有界285秒且audioSamples／callbackCount皆0，非聽感或頭盔證據；初期POSE REJECTED／STALE擷取亦保留，未宣稱原啟動旗標問題已解決。

| 最終PC場（前綴20261031） | 幀／最大來源年齡 | 證據 |
|---|---|---|
| 011829-38a0829c | 1938／0.160171秒 | **4項實際鍵盤／GPU流程**：Space1→29、R1，保存tick616／until632、elapsed14；GPU交換期手套／彈匣狀態已檢視，暫停再Space不耗彈，Resume後30／89、until0及回握畫面已確認。另**5項真正原生錄製觀戰**核對實際WebGL彈匣／手套位置、旋轉與隱藏狀態；保存完整數值及近距離鏡頭。封存耗彈1、命中／擊殺0、健康100且回放一致，無pose／combat注入 |
| 012755-8c66b16b | 115／0.156563秒 | **42 UI／native，客戶端無圖形**：保存配置／preflight、動態名冊、天氣／AI、Patrol／Pause／Resume／End、鏡頭、封存及最後姿勢；瀏覽器SwiftShader。此場沒有重做原生雨夜GPU／DSP |
| 012959-c53acede | 七場530／0.202684秒 | 五個真正server／每房一個client隔離、End／重用、封存後Linked、舊票／升權拒絕與七個精確stream封存；全為新profile／weapon version1，非25台 |

控制台前場 `012543-62053ba3` 單次讀狀態檔的暫停斷言未通過；其SQLite共722個Paused幀均tick62，沒有保存當下失敗讀回的原值，不能回推精確原因。改為等待同tick的有效讀回並保存前後樣本，若實際tick改變仍會失敗；最終42項通過。原生觀戰新工具首輪把option可見性當選單存在條件而timeout，改等attached後5項通過，不改產品。

最終三組均Simulation／Simulated、pendingTelemetry=false、活動0、cleanup零錯誤；writer關閉後25／14／26檔複製回F與SSD逐檔SHA一致且保留原件。另 `unity-admission/20261031-013124-c61855d2` 8項無圖形入場／撤銷／transport釋放／同admission重連通過，369幀、回放報表一致及活動0。沒有重跑走離出生點的互動重連、完整鍵盤碰撞、DSP／聽感、跨機或F USB全資料；source age為擷取新鮮度，非RTT或FPS。程式與binary仍F、runtime明確SSD。

最終原生39個log未見NullReference／MissingReference／ObjectDisposed／IndexOutOfRange例外。機器證據彙整於artifacts/actions-validation.json；原5080仍API0.16與原歷史且health ok，未替換正式資料／憑證。功能提交 `4ca6a59d059154c74a574541103dd3ab6e3d7052` 已推送並核對遠端main相同。[CI run41101273280](https://github.com/peca12968/vr-command-center/actions/runs/41101273280)／check124218763936目前queued、steps=null，尚無執行結果；不以歷史帳務失敗推定本輪結果，亦未改帳務或重跑。GitHub #1已同步目前ROADMAP、結果及限制，讀回確認open且保留前次完整內容。完整11項長期目標維持開發中；接續玩家人物／NPC武器、完整動畫／音效、複雜通路／地形、原停頓原因／啟動旗標、長任務與跨機；Quest／VIVE、MR、廠商硬體與25台仍待分階段實測。

## 2026-10-30：人形敵軍、權威朝向及可還原步態

從乾淨 `0170bb0` 接續使用者無頭盔的PC主線；前輪已交付玩家步槍，本輪新增原創404三角形人形敵軍（軀幹180、頭104、腿60重用兩次），含頭盔／護目鏡、背心／彈袋、紅色臂帶、護膝及靴子。生成器產出相同Unity Resources／瀏覽器頂點、法線、色彩與索引，固定資料SHA `39fa5e9baceec0eb71ce6a4664fc4460e7b0f212f2c58b75c7b4d75b3565fdf2`。生成check及記憶體改色反例拒絕通過；沒有外部模型／貼圖／下載，原掩體與步槍pin不改。NPC尚無武器模型、握持／換彈／死亡動畫或腳底IK，玩家身體與頭手仍為原型，不能稱完整人物美術。規範見 [ENEMY_PRESENTATION.md](ENEMY_PRESENTATION.md)。

新header assetSet=`combatants-v1`沿用固定掩體／玩家步槍，要求明確 `enemyPresentationVersion=1`；每個敵軍保存hasPresentation、單位forward及walking，未知／缺失版本拒絕。預設Create／Capture及缺欄位舊header仍0，完整保留三個舊profile與NPC外觀；binary原header／payload／checksum不改寫，codec只正規化舊缺失零向量。API／UI **0.20.0**、Unity **0.22.0／Android code25／NGO21**；envelope6、任務schema1、world schema1、票券2、environmentVersion1與rules0.8.0保持。新欄位及profile不能降舊reader，所有API／UI／遊戲程序一起更新。

ArenaWorld只在成功移動後標記walking及方向，有autoAttack目標時使用原射擊原點到目標的單位向量作朝向。沒有改目標選擇、導航、兩公尺Advance停止距離、攻擊間隔、原feet+(0,1.4,0)射擊原點或命中盒。NGO每個敵軍row原子複製facing／walking／presentationTick；Unity與觀戰共用保存tick規則，頭pitch視覺±45°、雙腿相反sin步態±18°。Paused／Ended保留最後模式與tick，直接seek相同；Unity位置仍插值，非逐pixel伺服器影像。模型無Collider／NetworkObject，原軸對齊敵軍half(.3,.9,.3)命中盒保留，擺腿輪廓不改命中；同點重疊／人群避讓仍待。

locked restore／Release build通過，0警告／錯誤；**534核心、403 HTTP、43世界串流、32 Node／167 Chromium**通過。涵蓋實際移動與原射線傷害、版本拒絕、SQLite重開與原binary逐byte保留、三Mesh資源池、固定法線、C#／JS時鐘向量及真正WebGL非零步態／seek／統計。審查發現JS原通用unit容差.011比renderer的.01寬，新NPC檢查已對齊.01並加1.0105反例，最後完整瀏覽器重跑通過；沒有改舊玩家容差。桌面／近距離回放截圖已檢視，瀏覽器為SwiftShader。首輪.NET建置抓到nullable約束，修正缺packet與forward guard；新核心測例先漏合成rig而被拒，補正測例，未放寬參戰姿態驗證。

真正Prepare、**61 EditMode（0 failed／skipped）**、Desktop／Quest均exit0，未RebuildArena，原scene／prefab識別保持。新增5項測試涵蓋真正匯入網格、共享資源／無Collider、實際Transform與seek、NGO序列化、JsonUtility舊資料；Tests門檻61。Desktop receipt UTC2026-10-29T20:04:05.5902819Z，fingerprint `7c4d759065020885b43d7dc5d4c04d42a91d822813b33c054434880f288ab2b3`。離線managed SDK兩分支各16 runtime／14 NUnit來源僅型別綁定，不冒充Editor／音訊／Shader／APK執行。Quest receipt UTC2026-10-30T14:53:43.7390900Z，fingerprint與識別同Desktop；兩次建置間有工作中斷，來源重新核對未變。APK46,147,574 bytes，SHA `11f8280ebcde4d30d1415bd6ac680c2650787be4a514fd63d816e633a3824200`，v2簽章、min32／target35、code25／bundle0.22及六個ELF64 AArch64庫含libil2cpp核對通過，沒有頭盔安裝。

人工檢視第一場 `040445-dde5b466` 因跨回合中斷逾時，不能稱UI全通過；helper到期後8250幀封存、清理正常。第二場 `223112-3335acc2` 實際看見敵軍前進／傷害及停止，最後walking=false使原測試要求移動的斷言失敗；因Advance已到原兩公尺門檻，改以真正控制台Patrol／Resume／Pause另驗非零步態，沒有為測試改AI停止距離或注入pose。失敗log／圖片／原資料與snapshot均保留，不能混作最終42項證據。

| 最終PC場（前綴20261030） | 幀／最大來源年齡 | 證據 |
|---|---|---|
| 223557-d36552a9 | 2757／0.175022秒 | **42 UI／native**：配置保存／preflight、動態名冊、天氣／AI Advance傷害、Patrol移動、Pause／Resume／End、鏡頭與封存回放；真正GPU白天全身、雨夜、Pause及巡邏中暫停均已檢視。最後保存tick3169、兩敵walking=true，實際觀戰物件yaw／head pitch／相反腿角與原生frame一致；自身健康60 |
| 224124-1ecc97e0 | 七場537／0.201650秒 | 五個真正server／每房一個client的隔離、單房End／重用、封存後Linked、舊票／升權拒絕與七個stream精確封存；每場combatants-v1／presentation1，非25台 |
| 224306-4ae70119 | 1587／0.171834秒 | 一般未掛探針的可見玩家，真正Left14／Down5瞄準及Space兩次，GPU看見新人形敵軍100→50→0、彈匣30→29→28，封存ammo2／hit2／kill1／100%、自身健康100，回放一致；無pose／combat注入 |

以上最終三組均Simulation／Simulated、pendingTelemetry=false、活動0、cleanup零錯誤；writer關閉後14／26／14檔複製回F與SSD逐檔SHA-256一致且保留原件。另 `unity-admission/20261030-224203-4dd71abf` **8項無圖形**入場／撤銷／transport釋放／同admission重連通過，370幀、封存回放一致、活動0；未重跑走離出生點的互動重連。本輪不重做DSP／聽感／完整鍵盤碰撞，舊證據保留；source age為擷取新鮮度，非RTT或FPS。程式與binary仍F、runtime明確SSD，不代表F USB全資料、跨機、25台或頭盔通過。

最終原生各自log共38檔未見NullReference／MissingReference／ObjectDisposed／IndexOutOfRange例外；機器證據彙整於artifacts/enemy-validation.json。原5080仍API0.16與原歷史且health ok，未替換正式資料／憑證。功能提交 `f4d9c749629101558ed419600d70c65cb82356b5` 已推送並核對遠端main相同。[CI run41076508175](https://github.com/peca12968/vr-command-center/actions/runs/41076508175)／check124134028244已結束，steps=null、annotation明確為近期付款失敗或支出限制、工作未啟動；另有ubuntu遷移通知，未改帳務或重跑。GitHub #1已同步ROADMAP、新結果與限制，讀回確認open且保留前次完整內容。完整11項長期目標維持開發中；下一步為NPC武器握持／玩家人物、換彈與死亡動畫、複雜通路／地形、原停頓原因／啟動旗標、長任務與跨機；Quest／VIVE實機、MR、廠商硬體及25台仍待設備與分階段驗收。

## 2026-10-30：玩家步槍、槍口對齊及實際命中

上一輪配置檢查已交付，從乾淨 `245ddb0` 接續使用者無頭盔的PC主線。新增自製264三角形步槍，槍托、機匣、握把、彈匣、護木、槍管及瞄具共用固定位置／法線／頂點色。生成器與Unity Resources／瀏覽器ES module同源，資料SHA `b054b9780b19104c6ff33a2384df15e9e4f6e2c73293297c4f70e2dd0d8eda25` 固定；生成check及記憶體改色反例拒絕通過。沒有外部模型／紋理／下載，沒有改field-props-v1 pin。人物／NPC、左手／頭部仍為原型，武器是靜態外觀，非完整人物、握持IK、換彈／後座動畫、槍械音效或廠商武器整合。

新header assetSet=`service-rifle-v1`明確由新Unity來源指定，完全沿用field-props-v1掩體、只換玩家步槍；field-props-v1及primitives-v1仍保留原武器，Create預設與缺欄位舊匯出維持legacy。API／UI **0.19.0**支援三種版本，未知／已接受header換版本拒絕；原binary header／checksum不改寫。envelope6／任務schema1／world schema1／environmentVersion1／票券2及rules0.8.0保持，不能降回不認識新profile的reader。NGO **20**隔離不同遊戲外觀與桌面預設，全部遊戲端一起更新。規範見 [SERVICE_RIFLE.md](SERVICE_RIFLE.md)。

Unity新模型為avatar根下的完整尺寸物件，跟隨pointer的旋轉及前方0.15m槍口；不繼承手部(.12,.12,.2)縮放。舊Weapon物件保留file ID但只在執行時停用；隱藏位於pointer的方盒Renderer，不假稱量測的握把／手掌。模型／server／HUD共用原0.15m常數，射擊仍由同一接受流程／射線確認，無新增Collider／NetworkObject或權威幾何。程序跨avatar共用Mesh／材質及引用計數；瀏覽器共用geometry、各角色獨立淡出材質，移除單一角色不釋放仍使用的共用網格。觀戰按已保存muzzle／forward，匹配的rightRotation保留roll，缺失／不匹配則按保存射線重建；本地畫面仍屬輸入預測／遠端插值，非逐幀伺服器影像。

候選場 `030454-deb7b4a2` 實際Space／R／Right20及傷害／Pause／淘汰基線雖通過（2393幀、最大來源年齡0.414904秒、30檔snapshot一致），GPU卻顯示自身武器在視野外。又從真正AcceptPose確認模型原點需要pointer前0.15m，原候選未對齊，不能稱視覺整合完成。已共用原常數並將**僅桌面合成**pointer預設由(.3,-.35,.4)改(.18,-.12,.75)，初始及更新一致；頭部、實體XR座標／來源與權威規則不改，保存的射擊原點沿實際接受姿態，舊錄製不重算。這是明確的桌面輸入預設變更，不能稱原姿態完全不變。新56項測試覆蓋原60°視野及多pitch／yaw、槍管前端可見與既有槍口範圍，真正GPU再驗如下。

locked restore／Release build通過，0警告／錯誤；**512核心、403 HTTP、43世界串流、27 Node／162 Chromium**通過。新profile實際經SQLite／canonical header／不可變重試與禁止降回field profile驗證；Node核對相同資料／pin、法線、槍口／方向／roll、資源池及壞資料。真正WebGL比較新舊玩家武器面數差異、seek統計及反覆切換，桌面／近距離回放截圖已檢視，瀏覽器為SwiftShader。首輪Prepare在測試的namespace解析出現CS0234，補global::；首輪55測試54通過／1項lossyScale精確相等失敗，改1e-5浮點容差而非放寬武器尺寸，再加視野測試後**56真正EditMode（0 failed／skipped）**全部通過。失敗wrapper保留，Editor標準路徑為最後成功log；managed SDK兩分支各15 runtime／13 NUnit來源僅型別綁定，不當作執行／Shader／APK證據。

真正Prepare、最終Desktop／Quest均exit0，未RebuildArena；scene／prefab識別保持，生成場景僅NGO19→20。bundle **0.21.0／Android code24**，兩端fingerprint同為 `32e2db5110d59fd3ce4a262b6a1d4bc59efacbef4732afafe5a391a6eb4b9523`。Desktop receipt UTC19:12:16.2548406Z、Quest19:27:52.6538646Z（10/29）；APK46,145,650 bytes，SHA `ebb3ad08021b74acf78bc9ab385b7175f6d74db11cec20f8c8f510739b7b49c4`，v2、min32／target35、六個ELF64 AArch64含libil2cpp已核對；沒有頭盔安裝。

| 最終PC場（前綴20261030） | 幀／最大來源年齡 | 證據 |
|---|---|---|
| 031303-baf6e9b4 | 2144／0.186412秒 | 真正Space1／R1／Right20，GPU看見自身與同伴步槍，彈藥29→30／89、方位60°，AI血量60／Pause／淘汰0與隱藏自身武器；封存耗彈1／中彈5／耗損100，無PCM |
| 031732-438e779c | 1800／0.195382秒 | **39 UI／native**：保存配置與preflight、動態名冊、天氣／AI／Pause／Resume／End、鏡頭及封存回放；新profile即時／末幀玩家步槍264面、掩體642面均保留，原生day／storm／pause實際檢視 |
| 032205-e46fb4ea | 七場509／0.220640秒 | 五個真正server／每房一個client隔離、單房End／重用、之後Linked、舊票／升權拒絕、七個stream封存；每場均service-rifle-v1，非25台負載 |
| 032841-f0e9103e | 2573／0.379273秒 | 新check-desktop-rifle.py，一般未掛診斷的可見玩家；真正Left14／Down5瞄準黃準星、Space兩次，敵軍100→50→0、彈匣30→29→28；封存ammo2／hit2／kill1／100%、自身血量100，回放一致；沒有注入pose／combat |

四場組均Simulation／Simulated、pendingTelemetry=false、活動0、cleanup零錯誤；writer關閉後30／14／26／14檔複製回F與SSD原件逐檔SHA-256一致且保留原件。另 `unity-admission/20261030-032225-ed6333fe` **8項無圖形**入場／撤銷／transport釋放／同admission重連通過，375幀、封存回放一致、活動0；未重跑走離出生點的互動重連。自有原生程序清空，相關log無NullReference／MissingReference／ObjectDisposed等異常。程式與binary仍F、runtime明確SSD；F USB全資料、跨機及25台未驗收。source age是擷取新鮮度，非玩家RTT或FPS。本輪雨夜／Pause看見新武器但沒有重做DSP量測；舊聲光／鍵盤碰撞證據保留，不混算新版。

機器證據彙整於artifacts/rifle-validation.json，包含原生接受的pointer到muzzle0.15m及資料／圖片／snapshot雜湊。原5080仍API0.16與原歷史且health ok，未替換正式資料／憑證。功能提交 `b33d76074d1362a74f573b2aae1c855e35a1d703` 已推送並核對遠端main相同。[CI run40942043585](https://github.com/peca12968/vr-command-center/actions/runs/40942043585)／check123687654479已結束，steps=null、annotation為近期付款失敗或支出限制、工作未啟動；另有ubuntu遷移通知。未改帳務或重跑；GitHub #1已同步新ROADMAP、結果與限制，保持open並保留前次完整內容。完整11項長期目標維持開發中；接續人物／敵軍美術、握持／換彈動畫、複雜通路／地形、原停頓原因／啟動旗標、長任務／跨機；Quest／VIVE、MR、廠商硬體及25台待設備與分階段驗收。

## 2026-10-30：新開 VR 場地配置檢查與草稿／歷史分離

依使用者「目前沒有頭盔，先繼續電腦端」，從乾淨 `acbdb9c` 接續。API／控制台 **0.18.0** 新增配置預覽及真正新開場的後端檢查，Unity **0.20.1／Android code23／NGO仍19**。共用 `ArenaLayout` 使用現有旋轉沙包／油桶包圍盒，檢查 Y 地面、角度／素材、整體 ±6m 邊界、四軸 SAT 重疊及真正五席出生位的 0.3m 通行空間。貼齊沙包允許；初始敵軍容量與實際規劃共用有序 0.75m 網格，單房需求為總數、Linked 為每房最多 ceil(總數／5)。未改 rules0.8.0 的碰撞／命中／導航，不能把容量當效能、通路可達性或運行中增援保證。

報告 version1／profile vr-room-v1／rulesVersion0.8.0／明確 mode，最多500物件、128問題但保留完整數量及全部無效索引。Master 的 POST `/api/mission-layout` 只預覽不保存；GET 精確任務版本 `/layout?mode=...` 沿用已認證共用範本讀取政策，每次明確 Actor。新 Create 的檢查在權限、已接受 request key 及房間衝突之後、任何提交之前，無效時400帶layout且不占房、不消耗未接受key。草稿仍可另存／修訂，舊場次投影、歷史世界及已接受原樣重試不重新套拒絕政策；測試涵蓋舊無效配置恢復、End後舊key只確認、修正後可重用先前未接受key。MR applies=false／canStart=null，不能稱校正通過。envelope6／任務schema1／world schema1／驗票2／NGO19不變；Core明確參考netstandard2.1 Simulation，Unity不引用後端。

控制台草稿自動檢查、紅色全部問題物件、真實出生空間及可點選問題；開場區讀精確保存版本／模式，未完成或未知版本不放行，未保存修正不會批准舊版。各請求序號、登入epoch、精確草稿／選擇及每次登入快取防止晚回應誤批准；後端另獨立檢查。API／UI須一起升0.18。操作與限制見 [LAYOUT.md](LAYOUT.md)，仍無MR、硬體、複雜通路／地形、25台或頭盔證據。

locked restore／Release build通過、0警告／錯誤，**510核心、403 HTTP、43世界串流、23 Node／158 Chromium**通過。新增旋轉角落／相切／AABB重疊但OBB分離、真正出生半徑、84格初始敵軍容量、128問題截斷、歷史與權限、草稿保存／修訂／新舊開場、模式切換與晚回應／登出／未知版本拒絕等檢查；沒有以dotnet test取代Checks。Core→Simulation新直接參考已更新全部相依lock，沒有套件升版。首次舊任務版本測試使用5.5m／45°沙包，角落出界，被正確擋住；改為4.5m並保留版本／重試目的。新增UI測試第二次嘗試從最新版選單直接選已移入歷史的原版而失敗，改以另一個現存無效head測換選晚回應，未放寬產品規則。桌面及390px截圖實際檢視，無頁面錯誤／CSP違反；失敗log／圖片保留在artifacts。

真正Prepare、**51 EditMode（0 failed／skipped）**、Desktop／Quest均exit0，未RebuildArena；新增5項涵蓋實際初始規劃84／85差異、出生／旋轉／截斷與舊重疊世界仍可讀。scene／prefab識別保持，兩端fingerprint同為 `2173ae32671877346fb6d0dfb33c3335928ba834c7a2ac12928d45a4ea6582a1`。Desktop receipt UTC18:35:10.0418215Z、Quest18:42:38.6848331Z（10/29）；APK46,142,410 bytes，SHA-256 `3e3c1a3be70f5770bc1a964d4cdd4266f12e3445175d90686dda821c2cf72e72`，v2簽章、min32／target35及六個ELF64 AArch64含libil2cpp已核對。managed SDK兩分支各14 runtime／12 NUnit來源僅型別綁定，與真正執行分開。field-props-v1／音訊生成check及293官方Transport檔唯一補丁核對通過；素材pin與wire規則未變。

新binary自己的SSD場 `desktop-venue/20261030-024255-e19b9185` **37項UI／native**通過，包含保存版本的UI／伺服器preflight、兩個真正client及替代peer、Begin／StormNight／Pause／Advance傷害／Resume／End、精確鏡頭與封存回放。已用computer-use檢視並保存白天、雨夜及Pause原生GPU原圖。736幀、最大來源年齡0.167620秒；回放／ledger一致、pendingTelemetry=false、活動0、cleanup零錯誤。停止writer後14檔複製回F與SSD逐檔SHA-256一致且保留原件；程式與binary仍在F，來源全部Simulation／Simulated。瀏覽器觀戰是SwiftShader，非真實GPU／頭盔效能。本輪未重跑聲光DSP或完整鍵盤碰撞，上一輪相同規則的證據仍保留，不能混算為新版重驗。

新binary另於 `desktop-venue/20261030-024533-f361585a` 通過五個真正server／每房一個client、權限與環境／AI隔離、單房End／重用、全部封存後Linked及舊票拒絕；七場58／93／99／104／107／58／64幀（共583），最大來源年齡0.149419秒，全部回放一致、pendingTelemetry=false／活動0／cleanup零錯誤。writer停止後26檔SSD與F snapshot逐檔SHA-256一致，原件保留；不是25台負載。`unity-admission/20261030-024637-eb92d672` 8項無圖形入場／撤銷／真正transport釋放／同admission重連回歸通過，364幀、封存回放一致、活動0；本輪沒有走離出生點的互動重連，舊證據保留。機器證據彙整於artifacts/layout-validation.json；自有原生程序已清空。功能提交 `921abb58b40e010c8130b4068810ad257729c27f` 已推送並核對遠端main相同。[CI run40934368225](https://github.com/peca12968/vr-command-center/actions/runs/40934368225)／check123660878977已結束，steps=null、annotation明確為近期付款失敗或支出限制，工作未啟動；另有ubuntu遷移通知，未改帳務或重跑。GitHub #1已同步目前ROADMAP、新結果與限制，讀回確認open且保留前次完整內容。原5080仍為原v0.16 DLL／資料且health ok，沒有為測試替換正式歷史。完整11項長期目標維持開發中；下一主線為人物／武器美術、複雜通路／地形、原停頓原因／啟動旗標、長任務與跨機，取得設備後再做Quest／VIVE、MR、廠商硬體及25台。

## 2026-10-30：原創沙包／油桶、保存素材版本及新舊觀戰

上一輪姿態分類與診斷屬實際進度。本輪從乾淨 `389eaa5` 接續無頭盔的PC主線，將玩家原方盒掩體換成自製低多邊形三層沙包／十二邊油桶，含縫線、桶箍、封蓋與警示色。固定生成器產出相同Unity Resources／瀏覽器ES module位置、法線、索引及頂點色；沙包256／油桶386三角形，重用兩個Mesh及單一材質，不新增Physics Collider。自製URP光照／霧shader引用既有URP shadow／depth pass，玩家、NPC、武器其餘幾何仍為原型；不是完整人物美術或頭盔驗收。

新增明確assetSet=`field-props-v1`，只由新Unity來源指定；Create預設、既有來源及缺欄位舊匯出保持primitives-v1。API／UI **0.17.0**支援兩個已知版本、未知拒絕、已接受header不可變；world schema1、rules0.8.0、environmentVersion1、envelope6／票券2不變。原binary header／checksum不改寫，DB結構未變不表示可降舊reader。NGO **19**隔離舊遊戲程序的不同外觀，全部遊戲端需一起更新；沒有RebuildArena。shader／Resources JSON已納入兩端來源fingerprint。v1資料SHA `7911140960f5e947f4cb7c474913608d7db5c1bec7c3558ffd9aac81eb6e3dc2`固定，生成器check與記憶體改色反例拒絕均通過；改模型須新ID且保留v1，不能覆寫pin改舊回放。

外觀不改碰撞／命中／導航：沙包2×.9×.7m，油桶.7×1.2×.7m，仍使用原旋轉方盒；桶邊角與袋體倒角／縫隙可能擋射線或行走，非逐pixel命中。觀戰明示包圍盒。配置圖原沙包僅畫1.6m、桶半徑.4m，現校正2m／.35m並畫虛線包圍盒；尚無擺放重疊／可玩區域檢查，沒有把示意圖稱MR校正。模型與操作／升級見[FIELD_PROPS.md](FIELD_PROPS.md)。

真正Prepare／**46 EditMode（0 failed／skipped）**／Desktop／Quest均exit0。新增4項EditMode涵蓋原碰撞尺寸、400面預算、有限頂點／外向法線、資源重用／無Collider及壞網格；直接資產匯入與native GPU另驗，SDK Android／Windows各14 runtime／11 NUnit檔只證型別綁定，不含URP shader執行。bundle **0.20.0／Android code22／NGO19**；原scene／prefab ID保持，兩平台fingerprint同為 `638b0543095bf79ee3e54a682171cfc6858cc0b4d3d06bad52ac65b617d4b7ef`。APK46,128,950 bytes、SHA-256 `55b3c366c33409289823c643549233795da06f7b0ce78f08bad3443c212866d5`，v2簽章、min32／target35及六個ELF64 AArch64庫含libil2cpp核對通過；未安裝頭盔。

locked restore／Release build通過、0警告／錯誤，**489核心、369 HTTP、43世界串流**通過。新增新舊profile、預設保留舊值、未知拒絕與重試不可換外觀。首次核心檢查發現API canonical header重建仍固定legacy，導致新profile被拒；保留field-checks-before-profile-fix.log，改為先驗證已知profile再以該profile重建canonical幾何後通過，房間／作者／身分檢查未放寬。

**23 Node／142 Chromium**通過，包含Unity／Web資料一致、資料範圍、舊串流仍12面方盒、配置尺寸及原權限／任務／鏡頭／聲光。首次瀏覽器在夜間sun=.08斷言失敗，原PNG／log保留；舊檢查只等待雨線，而閃電期間也有雨線，現明確等待下雨且非閃電狀態。首輪沒有保存原始sun值，未回推其精確tick／成因；後續weather-first-rain.json記錄tick20／sun.08／非flash。這是採樣條件修正，不改聲光規則或放寬亮度值。頁尾升v0.17後另有完整native UI流程與截圖覆蓋，沒有再重跑所有純瀏覽器項目。

| 原生場 | 範圍 | 幀／最高取樣來源年齡 | 結果 |
|---|---|---|---|
| 012703-9bbae7cd | 真正鍵盤掩體 | 5555／0.603690秒 | W17→沙包z=-2.6500003、S5→-2.9、D10→x=-2.5000005、W20→45°油桶z=-2.219239；各階段connected=true、健康100／30+90不變。先Down8觀看模型，移動仍只取yaw；輸入工具一次busy後重新觀測焦點及已接受z=-2.7000003，再完成原流程，未放寬斷言 |
| 013745-0900ae86 | 真正GPU／本玩家DSP | 274／0.157371秒 | 新模型／shader的flash亮度增32.6950，首次採樣flash141／thunder184（預期180，既定4tick容差內）；雨／雷／storm非零，穩定Pause52／Clear57窗口RMS0、PCM能量核對通過 |
| 013854-b0fa652b | 控制台＋真正PC | 1351／0.158653秒 | **35 UI／native**：保存／重載配置到GPU、新profile642面即時觀戰、精確鏡頭及封存末幀保留同版本、AI傷害與歷史名冊／回放一致；白天／雨夜／Pause／新素材回放均實際檢視 |
| 014757-f97348ee | 五房獨立／重用／Linked | 七場共533／0.204837秒 | 五個真正server／每房一個client的環境／AI／權限隔離、單房End／重用、之後五房Linked、舊票／升權拒絕及七個獨立stream精確封存均通過；所有header為field-props-v1，非25台負載 |

以上目錄前綴均20261030，來源維持Simulation／Simulated，全部pendingTelemetry=false、活動0、cleanup零錯誤。14／23／14／26檔於writer停止後複製回F，與SSD原件逐檔SHA-256一致並保留原件。原始GPU截圖未美化；瀏覽器為SwiftShader，不是頭盔／真實GPU效能。另 `unity-admission/20261030-015042-da81b3b3` **8項無圖形**入場／撤銷／真正transport release／同admission重連通過，370幀；這輪沒有重驗走離出生點後的視窗重連，舊互動證據保留。

機器證據在artifacts/field-validation.json，原生成物、.meta及成功匯入狀態保存；上游Three／Transport未修改。原5080仍為原v0.16 DLL／歷史，health ok；新程式使用自己的v0.17 API及新runtime，沒有移動或替換正式資料。人物／武器、擺放合法性、原停頓原因／啟動旗標、長任務／跨機、頭盔／MR／VIVE、廠商硬體及25台仍待，完整11項長期目標維持開發中。


功能提交 `df3a86552a3b2facb9c2d4f6dd89c615352cf055` 已推送並核對遠端main相同。[CI run40926478858](https://github.com/peca12968/vr-command-center/actions/runs/40926478858)／check123633239506已結束，steps=null、annotation為近期付款失敗或支出限制，工作未啟動；另有ubuntu遷移通知。未改帳務或重跑，新增生成器check尚未在雲端執行。GitHub #1已同步新版ROADMAP、證據及未解限制，保持開啟並保留前次內容。

## 2026-10-30：姿態逾時分類與可重現封包中斷

上一輪HUD屬實際進度。本輪從乾淨 `60713ba` 接續使用者「無頭盔、先繼續電腦端」。唯讀核對原場 `20261030-000040-9a2f550c` 的worlds.db：666→667幀相差688ms，tick仍1328；668幀connected=false，669幀100ms後恢復，頭部位置／健康100／彈藥29不變。先前警告把tracking、PoseAccepted及connected合併成POSE REJECTED，原PNG與0.25秒觀測不能分辨原因。這些新證據確認一次保存停頓與短暫非參戰狀態，不足以判定GPU、收件間隔、封包、CPU／IO或其他停頓根因；保留原資料，未宣稱修好延遲。

HUD現在分別顯示TRACKING INVALID、POSE REJECTED（PoseAccepted=false）及POSE STREAM STALE（前兩者有效但body.connected=false），桌面／XR文字共用。STALE維持紅色警告、非ACTIVE時不顯示準星／標籤；沒有延遲隱藏警告，也沒有改伺服器0.5秒姿態新鮮度、防瞬移、碰撞、admission或射擊規則。各複製旗標不是原子快照，不能把標題當封包根因或跨機時間證明。

NativeWeatherProbe新增互斥 `--vr-hud-trace`，只限明確選用、全新絕對目錄、Windows Development自己的未追蹤可見玩家。不配置PCM、不讀GPU／輸出PNG；0.25秒狀態之外，每個實際HUD Repaint保存狀態／原始旗標轉換，512筆有界、截斷明示且保留最初證據，結束才寫出轉換。快照含引擎時間／frame delta；原圖像模式另保存ReadPixels／PNG／寫檔耗時。一般啟動不附掛，沒有麥克風、OS loopback、遠端輸入注入或新網路欄位。

新增 `check-desktop-pose.py`：自己的API／room3 server／可見玩家，僅兩個127.0.0.1端點間原樣轉送UDP，暫時丟棄該玩家上行1.2／1.2／6秒，下行維持。不解析／保存payload、不改防火牆或正式服務。原生場 `20261030-005407-10c17163` 三次均驗證body.connected=false及HUD的poseAccepted／ready／tracking=true；已用computer-use實際看見紅色STALE、無準星，恢復後同admission／原位置／健康／彈藥維持，真正Space一次30→29，封存耗彈1／耗損0與回放一致。共丟棄386 datagrams、保存618幀、最大來源年齡0.160829秒；這是世界發布新鮮度，不能拿來充當被丟棄的玩家上行延遲。

逐繪製trace保存10次轉換，三次受控STALE到下一次ACTIVE為約0.8002／0.7009／5.5004秒。另捕捉入場初期POSE REJECTED約0.0369秒、其後STALE約0.0887秒才到AWAITING START，反映初始false及分開複製的到達順序；未隱藏這些警告、未把初始化當作實際拒絕封包證明。ACTIVE之後除了三次指定中斷沒有其他警告轉換；單次本機場不能證明零抖動。trace模式audioSamples=callbackCount=0、captures及captureTimings空、無PNG／WAV；三份Windows GPU截圖另存證據。

Prepare／**42項真正EditMode（0 failed／skipped）**／Desktop／Quest均exit0。新增3項測試涵蓋分類、短於週期採樣的轉換及容量／首筆保留；離線SDK Android／Windows各13 runtime／10 NUnit檔型別綁定通過，非執行證據。Transport的293官方檔／唯一修正驗證通過，未改上游補丁。沒有RebuildArena，原scene／prefab ID不變；bundle **0.19.1／Android code21／NGO仍18**，兩平台fingerprint同為 `b555847946006ec29716f4b302d9b331d15d914672774f308187c3d0bb7b4b93`。APK46,113,704 bytes、SHA-256 `36c8c52b9cfde24ae066ceb6649224d4018b0a879a4af2bca0b628e109dfff42`，v2簽章、min32／target35及六個ELF64 AArch64庫含libil2cpp核對通過；沒有頭盔運行。

同binary原生weather回歸 `20261030-005548-22ee28c2`：275幀／最大來源年齡0.160839秒；GPU閃電區域亮度增加27.6674，首次採樣flash141／thunder181（預期180，10Hz觀測容差內）。雨／雷／storm DSP非零，穩定Pause52／Clear59音訊窗口RMS均0，PCM量化核對通過；night／flash PNG已實際檢視。六次GPU讀回／編碼／寫檔耗時18.32–24.30ms，不能回推舊場停頓原因。兩場均pendingTelemetry=false、活動0、cleanup零錯誤；16／23檔於writer關閉後複製回F，與SSD原件SHA-256一致，原件保留。

完整機器證據在 `artifacts/pose-validation.json`、原資料核對在 `pose-historical-evidence.json`；操作／限制見 [TACTICAL_HUD.md](TACTICAL_HUD.md)。本輪無共享遊戲規則、後端或管理Web UI變更，不重算歷史485核心／369 HTTP／43世界／140 Chromium。5080 health仍ok，正式資料／DLL未換。啟動旗標提示、原停頓根因、長任務／跨機、3D軍事素材、頭盔／MR／VIVE、硬體與25台仍待；完整長期目標維持開發中。


功能提交 `b835d8c0327a3999ed6c2b756ded859c7b610558` 已推送並核對遠端main相同。[CI run 40917071587](https://github.com/peca12968/vr-command-center/actions/runs/40917071587)／check123600047504已結束，jobs.steps=null；annotation明確為近期付款失敗或支出限制、工作未啟動，另有ubuntu遷移通知。未重跑、改帳務或將其算測試失敗；本機證據與雲端未執行分開記錄。GitHub #1已同步新證據、未解限制及目前ROADMAP，重新讀取確認保持open、前次內容完整保留。

## 2026-10-30：軍事戰鬥HUD、場地方位與遮擋標記

上一輪原生聲光屬實際進度。本輪從乾淨 `65d5185` 接續無頭盔的電腦端與原始11項目標，新增 `TacticalHud`：軍綠狀態面板、血量條、大字彈匣／備彈、場地方位刻度、受遮擋限制的HOSTILE／ALLY短識別及血量條，桌面保留Simulation來源。準星沿用武器／掩體預測，射擊／換彈／傷害仍由server確認。XR既有world-space文字共用狀態優先序，修正淘汰被追蹤異常蓋過的情況；沒有把桌面方位或浮標直接套進HMD。

標記只讀同房、存活參戰者及已複製幾何，以與命中預測相同的盒檢查胸部視線，其他活角色亦可遮擋。候選10Hz、最多32個／8標記，每繪製幀用最新收到狀態重新檢查；不在掩體後保留舊標籤。這是保守顯示，部分露頭可能無標記，非逐pixel遮擋或防作弊／保密邊界。000°是場景正Z、不是地理北。原本角色／武器／物件幾何未改，primitives-v1、rules0.8.0、NGO18／API0.16及所有世界／事件契約保持。

首次真正Prepare抓到NetworkList不實作IEnumerable的CS1503，改為重用當幀自有快照後通過；最終 **39項真正EditMode（0 failed／skipped）**、Desktop／Quest均exit0，保存場景／玩家識別保持，無RebuildArena。生成設定依成功匯入結果保留；Quest建置後URP清單無最終差異。bundle **0.19.0／Android code20／NGO仍18**，兩平台fingerprint同為 `8fa5a0e8609b8f3521d14f98effa437075aecef2fcaed05963c8e585c48053df`。APK46,106,368 bytes，SHA-256 `2cd48b1c9371e4d8bbccb807ce133a0f0a718557982abbe8742bc7a6b44bbe9c`；簽章v2、min32／target35及六個AArch64庫含libil2cpp核對通過，無頭盔運行。

新增5個有意義EditMode檢查，涵蓋狀態優先序、方位、旋轉掩體／角色遮擋、同房／參戰／死亡／距離及移動後的新遮擋。離線SDK Android／Windows各13 runtime／10 test型別編譯通過。另核對 `65d5185` 的腳本，確實已定義DEVELOPMENT_BUILD；上一輪文件寫成未定義是記錄錯誤，已更正UNITY_SDK_CHECK及歷史段落。這補正編譯範圍，不把型別綁定當執行、GPU或DSP證據。

新增 `check-desktop-hud.py`，自己的API／room3 server、可見玩家及真正peer。HUD-only診斷與weather音訊模式互斥，285秒上限，不配置／保存PCM；GPU讀回與HUD繪製快照有界，正常啟動不附掛。原生場 `20261030-000040-9a2f550c` 以computer-use真正按鍵：Space1次→30降29，R→30／89並看見RELOADING，Right20次→060°及右方友軍；初始兩名敵軍只標記胸部未被油桶擋住的一名。AI造成血量60後Pause，之後淘汰血量0顯示ELIMINATED；全部已實際檢視截圖。2680幀、最大來源年齡0.767627秒；耗彈1／中彈5／耗損100、回放ledger一致、活動0、cleanup零錯誤。14份引擎截圖與五份Windows畫面保存，audioSamples=callbackCount=0且無audio.wav。

同場一份自動PNG亦實際看見短暫POSE_REJECTED；0.25秒保存觀測未捕捉該狀態，各輸入檢查點為ACTIVE且body.connected=true，後續射擊／換彈／轉向正常。保留原圖，未量測該次原因／確切持續時間；不宣稱全程無短暫拒絕或診斷模式效能。HUD忠實顯示拒絕狀態，未放寬權威姿態／時間檢查或以隱藏警告修飾結果，後續需在一般模式補充抖動定位。

新binary再跑weather模式 `20261030-000808-6ae72ca2`：274幀／最大年齡0.167383秒，GPU閃電區域亮度增加27.6674（新HUD遮住部分比較區域），flash140／thunder180，雨雷非零／穩定暫停及晴天RMS0，PCM量化能量一致。一般無probe、visible-room1場 `20261030-001934-4bc01194` **33項 UI／native**也通過，127幀／0.167325秒，控制台任務、動態名冊、環境／AI、鏡頭及封存回放一致。三場全數精確封存、pendingTelemetry=false、活動0、cleanup零錯誤；30／23／14檔在writer關閉後複製回F，與SSD原件SHA-256一致，保留原件，未移動5080資料。

完整驗證在 artifacts/tactical-validation.json，操作及界線見 [TACTICAL_HUD.md](TACTICAL_HUD.md)。本輪無後端／共享遊戲規則或管理Web UI變更，不重算歷史485核心／140 Chromium。3D軍事素材、完整長任務／一般模式抖動、頭盔／MR／VIVE、硬體、跨機及25台仍待，完整長期目標保持開發中。

功能提交 `0678c8f57aab2d20bc5c9bb25ac82bf8c4cef8af` 已推送並核對遠端main相同。CI run `40912886942`／check `123585281027` 已結束，steps=[]、日誌404 BlobNotFound；annotation仍為近期付款失敗或支出限制，另有ubuntu遷移通知，未改帳務或重跑。GitHub #1同步新HUD、原生證據與短暫姿態拒絕限制，保持開啟。原5080 health ok，自有Unity程序清空，正式DLL／資料未換。

## 2026-10-29：原生GPU閃電與本玩家DSP雨雷輸出

上一輪精確觀戰屬實際進度。本輪從乾淨 `893332e` 接續無頭盔的PC主線，針對需求5補強原生證據。新增 `NativeWeatherProbe` 與 `scripts/check-desktop-weather.py`：只有未追蹤、可見的Windows Development玩家，在明確CLI開關及全新絕對目錄下才附掛；一般啟動、Editor、Android或batch不附掛。只讀本玩家AudioListener DSP及GPU backbuffer，沒有麥克風、OS loopback、其他應用程式或遊戲輸入注入。兩個AudioSource仍由既有權威tick規則控制，僅增加LastApplied本地觀測欄位；不改戰鬥、網路或環境v1語意。

首次真正Prepare發現未宣告Image Conversion模組而出現CS1061；新增正式builtin imageconversion1.0.0後，UPM成功匯入並保存lock，Prepare／**34項EditMode**／Desktop／Quest均exit0。保存Arena／PlayerAvatar識別未變，無RebuildArena。bundle **0.18.1／Android code19／NGO仍18**，API0.16／驗票2／envelope6／world schema1／environmentVersion1保持。兩平台fingerprint相同：`ce2222224a687942a6492e9e861e72e4c5452134cf7cf6bb5537b09289faa7f5`。Quest ARM64／IL2CPP APK為46,085,944 bytes、SHA-256 `b0fd3ba170e953af7e2b388e52e51916b293e5cd0edefa2ee734c63c483094a0`，v2簽章、code19／0.18.1、min32／target35及六個AArch64原生庫含libil2cpp核對通過，沒有頭盔安裝或運行。

固定雨雷素材 `generate-weather-audio.py --check` 通過；離線managed SDK Android／Windows各12 runtime／9 test型別編譯通過，單一WeatherView Core／Audio窄檢查也通過。當時誤記「窄SDK圖沒有DEVELOPMENT_BUILD」；2026-10-30核對當時腳本已有該旗標，已更正文件。此圖仍只做型別綁定，真正Windows另有建置與運行；不把SDK當Editor／DSP或GPU證據。原生probe使用有界緩衝及音訊執行緒純記憶體採樣，End後才輸出PCM WAV並核對格式／樣本／量化能量，截圖於真實渲染幀結束後讀回。分析使用現有bundled Python／Pillow12.3.0，沒有全域安裝或更改系統音效設定。

第一場 `20261029-230508-0b5e7d5e` CLI通過：276幀、最大來源年齡0.614726秒，GPU閃電區域平均亮度比夜間增加34.5419（0–255）；48kHz雙聲道／24.085秒PCM，已檢視night.png及flash.png。第二場 `20261029-231752-cb648d31` 的靜音分類檢查失敗：10Hz主執行緒觀測把Resume後的兩個非零DSP回呼，誤歸到前一筆Paused快照；原始回呼時間12.532／12.551秒，第一筆已保存Running快照在12.554秒，穩定暫停區間均為零。保留失敗及278幀封存，修正分析器同時檢查狀態切換兩側、只分類穩定內部區間，不降低1e-6靜音或1.5秒來源門檻，也不更改遊戲播放邏輯。

最終 `20261029-232018-64b01ff3` 完整重驗通過：273幀、最大來源年齡0.154812秒；首次觀測閃電tick140、雷聲tick180，符合既有40tick延遲及10Hz觀測容差。2,263,040個交錯樣本／48kHz雙聲道、WAV RMS0.0164812；穩定雷聲／雨聲／暴風雨最大RMS0.0715666／0.0106800／0.0679965，暫停53批、尾音後晴天57批RMS皆0。閃電區域亮度增加34.5419，六份GPU截圖保存。關閉雷電不啟動新雷聲，但既有雷聲保留尾音；Pause停止聲音。這是原有規則，檢查不把自然尾音誤稱立即靜音。完整操作與範圍見 [NATIVE_WEATHER.md](NATIVE_WEATHER.md)。

一般未啟用probe、visible-room1的新binary場 `20261029-232121-aeab2eb8` **33項 UI／native**回歸通過，124幀、最大來源年齡0.133583秒。任務配置／動態名冊、天氣／AI／暫停、鏡頭保存及封存回放統計一致；所有自有場次皆精確封存、pendingTelemetry=false、活動0、cleanup零錯誤。三個聲光場各23檔及一般場14檔，在writer全停後複製回F，與實際解析的SSD原件逐檔SHA-256一致；原件保留。診斷PCM不進入worlds.db或一般回放，不等同任務原始音軌／影片交付。總驗證在 artifacts/weather-probe-validation.json，原5080 health ok，自有Unity程序清空，未更換正式服務DLL／資料。

本輪沒有後端／共享遊戲規則或管理Web UI變更，不重算歷史485核心／140 Chromium；新34 EditMode與33 native分開記錄。GPU擷取證明真正Windows閃光，DSP證明本遊戲混音有雨雷及穩定靜音，仍不證明人員聽感、實體喇叭／耳機、聲壓、Quest／VIVE、MR或25台。長期目標及完整11項保持開發中，接續軍事美術／長任務操作、跨機、頭盔／MR／硬體及25台分階段驗收。

功能提交 `dca912244e4e564c063b7850f93dd6612d9a5a7f` 已推送並核對遠端main相同。CI run `40902074120`／check `123546776707` 已結束，steps=[]、日誌404 BlobNotFound；annotation仍為近期付款失敗或支出限制，另有ubuntu遷移通知，未改帳務或重跑。GitHub #1同步原生聲光證據、失敗原因及限制，保持開啟。沒有以雲端未執行取代本機結果或宣布完整驗收。

## 2026-10-29：精確觀戰位置、角度與原生錄製回放

上一輪屬實際進度：掩體修正與 Windows／Quest v0.18 已交付。本輪從乾淨 `c46ea42` 接續完整長期目標與使用者「先繼續電腦端」。在既有自由觀戰旁新增看向 X／Y／Z、水平角／俯視角（度）、距離，以及讀取／套用按鈕及 Enter 操作；配合原拖曳、平移、縮放、角色跟隨及書籤，不占玩家席位。欄位是全館世界座標的觀看中心，不冒充相機位置或玩家姿態。

本地草稿只在明確套用時改動畫面，背景即時快照／書籤讀取不覆蓋編輯，錯誤或空白輸入不移動相機。登出／換場次清空並停用，讀取新錄製後啟用；同場回放／倍速重連不清草稿。套用切自由鏡頭，持久保存仍沿用身分／房間隔離、原樣重試與 tombstone 的既有書籤 API，沒有新增管理路由或移動玩家的能力。輸入範圍與既有書籤一致，參數以度數轉換後保存；操作見 [OBSERVER_CAMERA.md](OBSERVER_CAMERA.md)。

新增共用 camera-controls 瀏覽器檢查：數值對照實際 rendered camera、讀回角度、快照抵達仍保留草稿、空白／座標121／距離1／俯視0拒絕、真正左／右／Shift拖曳、wheel、方向鍵與±縮放，以及操作期間無管理寫入。新 native 檢查保存數值視角後核對 API 參數，切跟隨／舊書籤，再從封存回放讀回自訂位置。第一輪完整測試將換場清空斷言放在新 header 已填入預設值之後而失敗；保留 artifacts/camera-browser.log，修正為換場後、開始讀取新場之前檢查，不更改產品來迎合錯誤時點。

鎖定還原、隔離及一般 Release 皆成功，0警告／0錯誤。最終 **17 Node 資料＋140 Chromium** 通過，沒有頁面錯誤／CSP違反；已檢視 artifacts/console/world-camera-precise.png 與 world-replay-mobile.png，桌面數值／視角可見、390px沒有水平溢位。資料驗證與瀏覽器軟體 WebGL 證據分開，不重算歷史485核心／34 Unity EditMode。後端C#與Unity來源未改，API0.16／NGO18／世界及書籤格式保持；沿用 fingerprint `db5433bed1791b8e0b9be4587a657a005cb7471aa1f35a16d6fda0121c95eea1` 的 Windows／Quest，不為純管理UI重建二進位。

真正 Windows server／兩個 client 場 `20261029-224032-95b1d5c4`，以自己的隔離API／短票券與SSD runtime跑 **33項 UI／native**：看向(-28,1.25,0.4)、水平45°、俯視45°、距離12m保存後，已封存回放恢復完全相同的 rendered camera `-22.00,9.74,-5.60`。共126幀、最大來源年齡0.186783秒，保持1.5秒門檻；pendingTelemetry=false、回放統計一致、活動0、cleanup零錯誤。關閉writer後14檔複製回F並與SSD原件SHA-256一致，原件保留，沒有搬動5080資料。機器可讀證據在 artifacts/camera-validation.json。

更新一般 Release 的靜態資產後，以不帶 --api-dll 的預設啟動方式再跑 `20261029-224353-c5c71ac0`：同樣33項通過，116幀、最大來源年齡0.140497秒，精確視角／回放／統計保持一致、活動0、cleanup零錯誤，14檔SSD／F snapshot雜湊一致。原5080仍health ok，自有Unity程序清空。已檢視桌面與手機截圖，沒有替換原服務DLL／資料。

觀戰為 Chromium SwiftShader，這輪證明真實瀏覽器事件／操作與原生遊戲資料互通，不稱完整人工手感／真實GPU或頭盔驗收。原生閃電／雷聲、長任務鏡頭操作、正式軍事美術、跨機、Quest／VIVE、MR、硬體與25台仍待；完整11項保持開發中。

功能提交 `e15603b1d3a8cf25d48fb0dce6507512d4220574` 已推送並核對遠端main相同。CI run `40895099022`／check `123521924481` 已結束，steps=[]、日誌404 BlobNotFound；annotation仍為近期付款失敗或支出限制，另有ubuntu遷移通知，未改帳務或重跑。GitHub #1同步新功能、驗證與限制，保持開啟；原5080服務未換DLL或資料。

## 2026-10-29：電腦掩體移動 v0.18 與真正鍵盤驗證

從乾淨 `3106708` 接續使用者「沒有頭盔，先繼續電腦端」及完整長期目標。先在舊 v0.17 真正 Windows 玩家視窗重現問題：對沙包連續 W 17 次，伺服器保留最後合法 z=-2.65，但相機繼續向前、HUD 顯示 POSE REJECTED、connected=false。反例 `20261029-214952-e8fee276` 正常結束封存，只計為問題重現。

新增共用 `ArenaWalkSurface`，抽出原 GridNavigation 的 0.3m 半徑／旋轉矩形足跡及每最多 0.05m 線段取樣，供權威、AI 與桌面預測使用。桌面按同房間已複製幾何裁切移動、比較原位置出發的單軸候選，拒絕後回到最後接受的合成姿態；伺服器時間／位移／掩體檢查保持。不是解析掃掠或完整物理，Tracked XR 不被搬動。`CombatPropState` 新增 room 是 wire 變更，**NGO 18／bundle 0.18.0／Android code 18**，所有遊戲程序一起更新。API 0.16／驗票 2／envelope 6／world schema 1／rules 0.8.0 保持。Prepare 原位保存，沒有 RebuildArena，兩平台網路識別一致。

真正 Editor Prepare、**34 項 EditMode（0 failed／skipped）**、Windows 與 Quest 均 exit 0。Windows receipt 完成 UTC 14:07:11、Quest 14:15:35，來源 fingerprint 同為 `db5433bed1791b8e0b9be4587a657a005cb7471aa1f35a16d6fda0121c95eea1`。APK 45,993,624 bytes，SHA-256 `3f1303df47e52427f189f7305104f7dd9441e5b900239ed973db9cbb9aa24d41`；apksigner v2、code 18／0.18.0、min 32／target 35、六個 ELF64 AArch64 原生庫含 libil2cpp 核對通過。只是建置及靜態檢查，沒有安裝至頭盔。

鎖定還原及隔離／一般 Release 均成功、0 警告／0 錯誤；本輪實際 **485 核心、369 HTTP、43 世界串流** 通過。離線 managed 診斷 Android／Windows 各 11 runtime／9 test 型別編譯通過；Editor SDK 947 managed sources／13 assemblies 綁定及缺少 MetaQuest 直接參考的預期拒絕亦通過。診斷沒有執行 NUnit／UPM／ILPP／原生輸入，不能代替上方真正 Editor／binary 證據。嵌入 Transport 293 檔來源檢查保持通過。

新增可重現的 `scripts/check-desktop-collision.py`，自己的 API、room 3 server／可見 client、臨時票券與 SSD runtime；只接受外部操作完成檔，不注入姿態。`20261029-221556-be8bb604` 以 computer-use 真正鍵盤 W17／S5／D10／W20 四階段全部通過：沙包停在 (-3,1.65,-2.6500003)，退回 z=-2.9，側移 x=-2.5000005，再停在 45° 油桶前 z=-2.219239。每階段 connected=true、Simulated、健康100／彈匣30／備彈90；原生 HUD 沒有姿態拒絕，截圖 sandbag.png／barrel.png。共 **3889 幀**完整封存、最大量測來源年齡 **0.689724 秒**，回放／ledger 一致、活動0、cleanup零錯誤。

新 binary 另重驗：五房 `20261029-222305-af15ab00` 六組檢查、七場 **62／95／100／104／108／56／64 幀**，最大年齡 **0.22675 秒**；同 admission 撤銷／斷線恢復 `20261029-222346-d37c759b` **8 項／377 幀**，保留位置與健康／彈藥；控制台任務 `20261029-222449-7e99ae21` **15 項 UI／native／103 幀**、最大年齡 **0.164206 秒**，包含保存重載擺設、動態名冊、環境／AI／暫停、觀戰書籤與回放。全部精確封存、pendingTelemetry=false、統計一致及活動0。瀏覽器仍 SwiftShader，此輪沒有改 Web UI，不重算歷史 17 Node／122 Chromium。

三個 Venue runtime 在關閉 writer 後複製回 F，14／26／14 檔逐檔 SHA-256 與 SSD 原件一致，保留原件；不能宣稱 F USB 配置通過。機器可讀總驗證在 `artifacts/collision-validation.json`，各 build／check log 均保留。Unity 測試產生的 PerformanceTestRun JSON 明確忽略，不提交機器資訊或生成執行資料。操作與規則見 [DESKTOP_COLLISION.md](DESKTOP_COLLISION.md)。下一步是原生閃電／雷聲、自由鏡頭完整人工操作、軍事美術及跨機部署；Quest／VIVE、MR、廠商硬體、25 台及完整 11 項仍待驗，長期目標保持開發中。

功能提交 `c2ad954418f7dcc75cdb34392ad039a254e994d8` 已推送並核對遠端 main 相同。CI run `40891989275`／check `123510980195` 已結束，steps=[]、無可下載日誌（404 BlobNotFound）；annotation 明確為近期付款失敗或支出限制，另有 ubuntu-latest 遷移通知，未改帳務或重跑。原 5080 health ok，自有 Unity 程序已清空，沒有換正式 DLL／資料。GitHub #1 同步本輪與限制並保持開啟。

## 2026-10-29：控制台自訂任務接到真正 PC、圖形環境與原生觀戰

上一輪五房已交付，本輪從乾淨 `9c14d4d` 接續完整 11 項目標。新增 `scripts/start-desktop-control.py`，由操作員在自己的控制台建立／儲存／重載任務、建立 Preparing VR 場次與名冊；工具才啟動真正 Unity server，按 playerId＋admissionId 配發短效票券並啟動 client。開始、暫停、天氣與 AI 仍由控制台發令，不預先代替操作員建立固定任務。只接本工具自己新建 API，拒絕接管 Running／既有 combat source，玩家檔沒有 Master／GameServer key。

動態名冊可啟動新 client、關閉被移除入場的舊 client，並保留離場統計；最終按持久 PlayerJoined 事件分頁核對所有曾入場 ID，不用當前名冊取代歷史。共用 Venue 抽出 receipt／來源驗證及 server 啟動，舊五房工具沿用。operator-status 取自真正已接受世界幀的 phase／tick／環境／AI／連線玩家，持續維持 UTC 來源年齡 1.5 秒門檻。所有世界、頭手及戰鬥來源仍 Simulation。

`tests/browser/check-operator-native.cjs` 只接受本庫隔離目錄及 localhost 非 5080 的 Simulation ready；憑證直接讀自己的檔案進入頁面記憶體，不輸出值、不用正式預覽憑證。它實際透過 UI 配置沙包 (-3,0,0)／15°、油桶 (-1,0,1.5)／90°，儲存後清草稿、重新載入，再選已保存任務開房間 1。真正 native header 的世界座標為沙包 x=-31、油桶 z=1.5，與房間原點一致；兩名 client 以真實票券入場。測試亦在 Preparing 移除 Peer02，啟動 Peer03，最終統計保留三位歷史玩家。

首輪 `20261029-210117-f04e557f` 使用 computer-use 檢視真正 Direct3D 玩家視窗，看到配置、Clear／Day、由控制台改成 Storm／Night 後的暗場與雨線，以及 Pause HUD。原始截圖另複製到 artifacts/operator-ui/native-day.png／native-storm.png／native-paused.png。沒有錄到原生閃電瞬間或驗證雷聲聽感；不能把閃電設定啟用或瀏覽器音效圖當作原生聲光全驗收。此輪瀏覽器測試漏處理 End 確認框，最後 exact-seal 等待失敗，完整瀏覽器流程不算通過；修正對自己測試場確認框的處理後重驗。原場由工具正常 End，2730 幀完整封存、回放統計一致、活動數 0、cleanup 零錯誤，未動其他程序或預覽資料。

最終整合另確認真正世界 Running、Storm／Night／lightning、Paused tick 400 ms 不變、兩名 Advance／autoAttack 敵軍與確認傷害，並從 native recording 的控制台即時俯視、保存鏡頭、切跟隨後讀回位置、倍速與跳至末幀回放。**15 項 UI／native 檢查全過**，不是只檢查管理命令回應。隔離 API 場 `20261029-212125-ef9f8c83` 封存 **92 幀**、最大量測來源年齡 **0.15173 秒**。更新一般 Release 後，以不帶 --api-dll 的預設命令再重驗 `20261029-212436-81187953`：同樣 15 項通過、**94 幀**、最大年齡 **0.170777 秒**；Operator01 中彈 2／耗損 40／健康 60，Peer02 的歷史及 Peer03 均保留。兩場 pendingTelemetry=false、回放末幀／ledger 一致、活動 0。

測試觀戰瀏覽器明確為 Chromium SwiftShader，原生 GPU 畫面是上方獨立的 computer-use 證據；沒有稱瀏覽器已測真實 GPU、實際頭手或頭盔。控制台三處過時提示已更新為目前接入與仍待實機範圍。鎖定還原、隔離／一般 Release 建置都 0 警告／0 錯誤；完整既有瀏覽器回歸 **17 Node 資料＋122 Chromium** 通過，已檢視 artifacts/console/mission-planner.png 及 native-live-overhead 圖。

共用工具改動後，五房原生回歸 `20261029-211936-917f7f56` 也全過：七場 **62／100／104／108／114／56／63 幀**，最大來源年齡 **0.254718 秒**、回放統計一致、活動 0。仍使用明確 SSD runtime，關閉 writer 後複製回 F，與原件逐檔 SHA-256 一致；F USB 硬碟的限制不因本輪通過而解除。整體機器可讀驗證在 artifacts/operator-ui/validation.json，兩個啟動器的舊 receipt 反例均在建立場次前拒絕。

最後補強 UI 檢查器的版本競態：刷新允許已前進的較新序號，控制命令若確實收到 409，才由 UI 重新刷新並提出新操作，不重送已接受命令或移除版本／入場限制。全新預設命令場 `20261029-213239-26180ff6` 再通過 15 項、92 幀、最大來源年齡 0.212172 秒，雙管道精確封存、回放一致、活動 0、cleanup 零錯誤。可操作玩家原始日誌也確認 Direct3D 12 [level 12.2]，與觀戰的 SwiftShader 分開記錄。

Unity C#／NGO 17／bundle 0.17.0 及管理契約未變，沿用同源 fingerprint `d6baeb56101bc7adea85f4173d3e0a31788f1d5546ff6a2ab872a789ff242a20`，沒有為 Python／提示文字重建播放器，也不把歷史 29 EditMode／.NET 規則數字算成本輪新結果。操作見 [DESKTOP_CONTROL.md](DESKTOP_CONTROL.md)。下一步仍有原生完整聲光／碰撞／鏡頭人工操作、軍事美術、跨機部署／效能、Quest／VIVE、MR、硬體與 25 台；本機端到端操作不完成整體驗收。

功能提交 `86b7b32e7544133ba83d8ed454563ade4e325edb` 已推送並核對遠端 main 相同。CI run `40883545618`／check `123481119824` 已結束，steps／logs 為空；annotation 明確仍為近期付款失敗或支出限制，另有 ubuntu-latest 遷移通知。未改帳務或重跑；本機結果與雲端未執行分開。原 5080／PID 52992 仍 health ok，未換 DLL／資料；自有 native 程序均已停止。GitHub #1 同步本輪操作與限制，保持開發中。

## 2026-10-29：五房同時獨立、房間重用與之後的全館連線

上一輪已交付 PC 撤銷／重連，本輪從乾淨 `b36ac5d` 接續使用者「先繼續電腦端」，完整 11 項與 Quest／VIVE 目標保持開發中。新增 `scripts/start-desktop-venue.py`：自己的 API／七份臨時控制台與來源憑證、五個獨立任務、五個真正 Windows Unity server、每房一個真正 client，使用不同 UDP 埠及持久來源。可選一個房間顯示玩家視窗，其餘背景運行，控制台 URL／room/session/port／PID 存於 ready.json；玩家只有短效票券，所有頭手與戰鬥來源均為 Simulation。

新增 `--check` 原生流程，不注入戰鬥或姿態：五房不同天氣／日夜、敵軍 1–5、不同數量與角度的沙包／油桶，核對真正保存的世界、幾何及名冊。逐房控制台僅列自己的場次，跨房快照／統計／world／watch／Pause 全拒絕；有效 room-1 券送到 room-2 真正 server 亦拒絕。Room1 更新 Storm／Night／雷電及六名 Advance／autoAttack 敵軍，取得確認傷害後暫停，其他四房仍 Running、tick 前進且環境／AI／健康不變。

結束 room-1 後只釋放該房，其餘四房繼續；保留原統計與錄製並在房間 1 開新獨立場。四房仍占用時，全館 Linked 建立回 409。六個獨立歷史場次都精確封存後，Master 以一份任務新開五房 Linked、一個權威 server 加五個 client；舊獨立票券在仍未過期時拒絕，名冊使用新 admission。房間控制台不可 Begin／修改整個 Linked 環境，Master 控制通過。Linked 確認 AI 傷害、共同暫停 tick 凍結、End 與回放統計一致；七場保留不同 stream，最後活動數 0。這是新開共享世界，不合併舊世界或舊報表。

首次 F 槽全資料試跑落後 **13.996307 秒**，維持原 1.5 秒門檻而失敗；每程序兩個 job worker 的修正後試跑仍落後 **13.350486 秒**，移除物件的診斷也累積到約 23 秒，不能稱為成功。F 實際為 Seagate One Touch Hub／USB，C 為 Kingston NVMe；24 次 4 KiB flush+fsync 短測平均 F **17.166 ms**、C **1.754 ms**，支持同步持久寫入吞吐不足的判斷，並非完整磁碟／全負載保證。未關閉 flush、降低錄製頻率、丟棄幀、提高門檻、移除正式擺設或修改安全設定。

工具新增明確 `--runtime-root`。本輪使用 C 槽本機 AppData 下全新隔離目錄保存 SQLite／journal；程式碼、播放器、設定與證據目錄仍在 F 槽，沒有搬動原 5080 或既有資料。未指定時仍使用 F artifacts，不能宣稱 USB 配置已通過五房新鮮度。全部自有寫入程序停止後，才將 runtime 完整複製回 F 的 runtime-snapshot，保留 SSD 原件；逐檔 SHA-256 與來源一致。每程序兩個 job worker 是明確記錄的配置，並非延遲修復的單獨證據，官方參數見 DESKTOP_VENUE。

第一次兩 worker 探索因工具新增量測分支縮排錯誤而失敗，清理也被同一非預期例外中斷。已先查核該隔離 API 五場 End／世界全部封存，保存 manual-cleanup-seals，再僅停止該 fixture 的十個 native 與 API，未動正式預覽。現收尾各場獨立容錯、最外層 finally 一律停止自有程序；注入非預期 End／seal 例外的實際子程序守衛也通過。任何清理／快照錯誤均非零退出，不把該失敗試跑算成通過。

SSD 第一輪 `20261029-204334-40372c18` 七場封存幀數為 **63／95／99／104／109／56／65**，最大量測來源年齡 **0.195271 秒**。補上幾何精確位置、舊券尚未到期、新 admission、空來源統計及清理守衛後，最終 `20261029-204521-bf4bf7ff` 再完整通過：幀數 **53／85／89／98／104／60／64**，七場回放／報表一致，最大來源年齡 **0.275004 秒**，活動數 0。六個斷言群組涵蓋上述原生流程；不是 25 人或跨機效能數字。

一般可操作模式 `20261029-204600-12e42550` 也實測：computer-use 選取真正玩家視窗，看到 Running／Room1／100 血量／30/90 彈藥與場景；關閉標題列按鈕後，工具自動 End 五場，各封存 **797／801／810／814／815 幀**，合計 **4037 幀**、回放統計一致、活動數 0，CLI 退出 0。此輪只驗證可操作視窗啟動與關窗，不重複宣稱測過射擊或五房觀戰圖形。截圖為 artifacts/venue-ui/room1-running.png。

機器可讀驗證在 `artifacts/venue-ui/validation.json`：三次成功 runtime-snapshot 與 SSD 原件逐檔一致、cleanup 零錯誤／零剩餘程序；播放器 receipt 指紋仍為 `d6baeb56101bc7adea85f4173d3e0a31788f1d5546ff6a2ab872a789ff242a20`，舊 receipt 反例在建立場次前拒絕。此次未改 C#／後端／管理 Web UI，不重建同源播放器，也不混算歷史 29 EditMode／.NET／Chromium。文件同步修正 API 舊票券範例及過時驗證狀態。下一步為圖形聲光／擺設、操作員控制與觀戰操作驗收，後續仍須跨機、Quest／VIVE、MR、廠商硬體及 25 台。操作見 [DESKTOP_VENUE.md](DESKTOP_VENUE.md)。

功能提交 `1c86e627c1a8fe24e23137e55a520bcf1d7df708` 已推送並核對遠端 main 相同。CI run `40876982663`／check `123458210322` 在任何 step 開始前結束，steps／logs 為空；annotation 仍為近期付款失敗或支出限制，另有 ubuntu-latest 遷移通知。未改帳務或重跑。原預覽 5080／PID 52992 仍 health ok，本輪沒有換 DLL／資料；自有 native 視窗及程序均已停止。GitHub #1 同步本輪 SSD 條件及五房成果並保持開發中。

## 2026-10-29：電腦重連、入場撤銷與 Windows UDP 接收修正

從乾淨 `2601c7d` 接續使用者「沒有頭盔，先繼續電腦端」。本輪遊戲端升為 **v0.17.0／Android code 17／NGO protocol 17**；API 仍為 0.16.0、驗票 protocol 2、場次 envelope 6／世界 schema 1 不變。所有遊戲 server／client 須一起更新，不混用 NGO 16／17。完整 11 項及 VIVE／Quest 相容目標仍開發中。

新增桌面斷線後的 **Reconnect / reload player ticket**：重讀原玩家設定檔，只能以 Client 及短效票券重新連線。操作員移除舊 admission 後，即使相同 playerId／席位重新加入，舊票券及舊 If-Match-Admission 仍拒絕；更新玩家檔後可在原程序按鈕重連，不把 Master／GameServer key 放進玩家。連線日誌只記狀態及 transport client ID，不輸出票券或密鑰。

同次 admission 的桌面恢復快取只保存權威核心已接受的 Simulated 頭手姿態。新玩家物件先接收該初始姿態，再送自己的輸入，避免走遠後從出生點重送而違反既有防瞬移規則。健康／彈藥保留於原戰鬥世界；快取按 playerId＋admissionId 隔離，名冊移除／換 admission 清除，Tracked 來源不使用桌面快取。這是單一 server 程序內的恢復，不是持久世界或頭盔追蹤恢復。

真正 Windows 強制斷線揭露另一個問題：server 與 UDP 埠仍存在，新 client 卻進不了 approval。延長等待及背景更新都未修復；只轉送原封包的診斷代理觀察 client 送出而 server 無回應，這些試跑均保留為失敗，不算通過。真正使用的 Transport 2.7.4 在失敗 receive completion 分支未歸還 buffer；[Unity 工程師的確認](https://discussions.unity.com/t/unity-transport-6-6-0-udp-host-stops-receiving-after-abrupt-client-disconnect-on-windows/1736023) 支持該原因，但討論版本較新，本機結果仍須分別驗證。最初的舊版重連失敗同時受傳輸與姿態問題影響，不能把單次失敗全歸因於姿態。

官方 registry 當下最新仍為 2.7.4，因此以固定官方 archive 嵌入 `Packages/com.unity.transport`，只在該分支增加 `ReceiveQueue.ReleaseBuffer(bufferIndex)`。保留 293 份官方檔案／授權／metadata，另存來源與逐檔雜湊；不修改 Library 快取、防火牆或接收容量。`check-transport-patch.py` 離線核對完整清單，隔離反例證明來源／ledger／額外檔案改動都拒絕；CI 亦加入核對。UPM lock 為 embedded，建置指紋納入嵌入來源與 UPSTREAM.json，詳見 TRANSPORT_PATCH。

真正 Editor 新增三項 admission／姿態快取測試及一項 Windows 原生 NetworkDriver 小佇列強制斷線回歸，合計 **29 項 EditMode 全通過，零失敗／零跳過**。最初 coroutine 測試誤用 Temp allocator，已改為 Persistent 後重驗。第一次 Desktop 建置遇到 PlayerDataCache 目錄存取失敗，保留 `unity-reconnect-desktop-first-failure.log`；未刪快取／改權限，重新執行同一建置後成功。SDK 診斷補上真正已匯入的 UnityEngine.TestRunner DLL 與直接 Transport 參考，Android／Windows 均通過 11 runtime／8 test 來源型別編譯；它不執行測試，也不驗證嵌入 Transport 原生行為。

Windows／Quest 最終成功 receipt 的來源指紋同為 `d6baeb56101bc7adea85f4173d3e0a31788f1d5546ff6a2ab872a789ff242a20`；scene file ID `1444571642`、prefab file ID `5227825248646244841` 保持，未重建場景。Prepare 在保存的 Arena 上將 NGO 16 升至 17。Windows 完成 UTC 11:56:05，Quest 完成 UTC 12:13:46；APK **45,987,512 bytes**、SHA-256 `a1d790645afab03bb9bb389e2856bf4392e4ee5daf2fb9b853504be7188fbccf`，v2 簽章、com.vrcommand.quest、版本 0.17.0／17、minSdk 32／targetSdk 35、六份 ARM64 native library 及 IL2CPP ELF64 AArch64 核對通過。這是 Development 建置，沒有頭盔安裝／執行證據。

新 `check-unity-admission.py` 使用自己的 API／資料／憑證與真正 Windows UDP／NGO server 加 clients，八項入場／撤銷／重連／End 斷言全過。無圖形場 `20261029-195957-8a81f78a` 封存 **369 幀**；實際視窗場 `20261029-200137-a3569013` 封存 **1648 幀**。互動場在原 PID 23396 重新配票後點 Reconnect，再以 Space 射擊、W 前進 **0.65 公尺**；強制結束玩家程序、等真正 transport-left 回呼後重啟同 admission，權威位置仍為 **(25, 1.65, -2.35)**，健康 **60**、彈匣 **29**、備彈 **90** 均相同。統計耗彈 1／中彈 2／傷害 40；pendingTelemetry=false、末幀回放與報表一致、活動場次 0。全部是 Simulation／Simulated rig，沒有注入姿態或戰鬥 RPC。

第一個修正後試跑曾完成封存卻因工具 finally 使用不同 End commandId 得到 409，CLI 失敗，不能算完整通過。已統一 End ID，清理路徑容許失敗回覆並停止所有自有程序；僅清理該隔離 fixture 程序，再以上述兩個全新場重驗成功。正常 Independent／Linked 連線亦回歸通過，目錄分別 `20261029-200542-b9edbf40`／`20261029-200557-c2c87ae6`，各 **113 幀**，最大來源年齡 **0.572172／0.48822 秒**，維持原 1.5 秒門檻。這只是本機該次量測，不能當跨機 LAN 或 25 台 SLA。

完整機器可讀驗證在 `artifacts/reconnect-ui/validation.json`；原始日誌、失敗及截圖保留於忽略的 artifacts。ProjectBuilder 的較窄 Editor SDK 圖亦重新通過 947 來源／13 組件及移除 MetaQuestSupport 的編譯失敗反例，仍不含 URP 專用驗證分支。未變更後端／管理 Web UI，未混算歷史 .NET／Chromium 結果；末端原預覽 5080／PID 52992 仍回 health ok／API 0.16，本輪未換 DLL 或資料。操作見 [RECONNECT.md](RECONNECT.md)，一般練習場見 [DESKTOP.md](DESKTOP.md)。下一步為五場同時獨立與圖形聲光／操作員控制；跨機網路、server 崩潰恢復、Quest／VIVE、MR、硬體及 25 台仍待分別驗收。

功能提交 `94c49fc935ba233c72e72098c2bbb8f675626b22` 已推送，核對遠端 main 相同。GitHub CI run `40873523761`／check `123446386429` 已結束，steps／logs 為空；annotation 明確為近期付款失敗或支出限制，工作尚未啟動，另有 ubuntu-latest 遷移通知。未改帳務或重跑，沒有將雲端未執行稱為通過。GitHub 長期追蹤 #1 保持開發中；本機結果與完整實機目標分開。

## 2026-10-29：可操作電腦練習場、瞄準與真實視窗射擊統計

上一輪 990b946／1b4f3a7 已完成真正 Unity 建置與雙 client 無圖形驗證，屬於具體進展。本輪依使用者「目前沒有頭盔，先繼續電腦端」從乾淨 1b4f3a7 接續，不縮減完整 11 項需求。沒有登入、SDK 重裝或頭盔操作。

新增 scripts/start-desktop-demo.py，直接啟動自己的 API／SQLite／Master 與 GameServer 憑證、無圖形 Unity server、一個可操作視窗及預設一個無圖形同伴。Clear／Day、Hold 且不自動攻擊的練習任務含沙包／油桶；玩家只有短效票券，來源明確 Simulation。關閉玩家視窗、Ctrl+C 或時間結束後送 End，等待雙管道精確封存並比對回放／報表，再停止自有程序。產物與私密設定都留在忽略的 artifacts/desktop-demo，不讀取正式預覽憑證或改動 5080 資料。

桌面 HUD 改為可讀的畫面固定血量／彈藥／房間／phase 與操作提示，保留頭盔的原 world-space HUD。準星依收到的幾何與槍口預測投影，不把預覽當命中確認；伺服器仍處理姿態／射速／傷害。新增上下瞄準、方向鍵、Space 射擊；WASD 依水平視角前進、斜走不加速，按房間而非各出生席位根物件限制邊界，長幀不大幅跳位。掩體碰撞仍由核心拒絕，尚無完整本地移動預測。

實際視窗先證實滑鼠能扣彈，但自動鍵盤未改變畫面；補上短按 wasPressedThisFrame 後仍無效，不能只憑推測稱為修復。新增裝置診斷確認 keyboard／mouse 均存在，再接入視窗 key event 的後備路徑，才取得真正方向鍵／Space／R／W 操作證據。後備輸入在下一次 Update 與 InputSystem 狀態合併，避免同一原始按鍵重複套用；這是系統視窗事件相容，不是測試 RPC、直接寫命中或繞過伺服器。實體鍵盤的所有組合／手感仍待人工量測。

最終 Windows receipt 來源 fingerprint `05d97ef51db1b3f505fc6da89867325dcd8aff5af7f4a9382053fb74f64e5ef8`。在真正 Direct3D 玩家視窗以 computer-use 執行方向鍵轉向、Space 與左鍵射擊：兩次命中造成一個擊殺，再打一發空槍。API 報表為耗彈 **3**、命中 **2**、擊殺 **1**、命中率 **66.67%**，同伴耗彈 0。R 換彈由 27／90 到 **30／87**；W 前進後權威頭部位置由 (25, 1.65, -3) 到 (24.966543, 1.65, -2.9628427)，Up 後 forward.y 約 0.052336。Pause 後 Space 不扣彈，tick 保持 3505。

關閉真正玩家視窗後啟動器完成 **1967 幀**世界封存，pendingTelemetry=false、回放末幀統計與報表一致、活動場次 0。證據在 artifacts/desktop-demo/20261029-183207-5901bf78，實際畫面為 artifacts/desktop-ui/aim-hit.png 與 paused-reloaded.png。這是單機桌面 GPU 畫面與合成頭手操作，不是頭盔、軍事美術定稿、音效聽感、完整觀戰畫面或 25 人量測。

空事件試跑曾因統計 origin=null 被工具誤判來源混用；無戰鬥事件的空報表合法為 null。已改為只允許空計數的 null 或 Simulation，世界 header 仍須 Simulation，不允許 GameServer 混入。空場重驗保存 325 幀、完整封存／回放統計一致／活動 0，證據在 artifacts/desktop-demo/20261029-183610-a85e5ea9。新增四項真正 EditMode 測試驗證俯仰／無翻滾、水平相對移動／斜走速度、長幀及五席房界，總數 **25 項全通過**，Tests 門檻同步為 25。未改後端／管理 Web UI，沒有重跑或混算上一輪 .NET／Chromium 數字。

最終 Quest Development APK 亦成功，來源 fingerprint／scene／prefab 識別與上述 Windows 一致，沒有另建場景。APK 67,977,028 bytes、SHA-256 `f78b2ace8765109d39860d49754c501c4f12b3b7b6052222dbd348ff87a3d055`，v2 簽章、com.vrcommand.quest、minSdk 32／targetSdk 35、六份 ARM64 native library 與 IL2CPP ELF64 AArch64 核對通過。這不是頭盔執行證據。完整機器可讀驗證在 artifacts/desktop-ui/validation.json。

與 Android 建置並行的第一個連線回歸因快照來源年齡 6.263257 秒超過原 1.5 秒門檻而失敗，保留 artifacts/unity-pc-input-independent-smoke.log；沒有放寬門檻或宣稱該次封存成功。建置終止後，以新隔離場重驗 Independent：108 幀、tick 167、最大取樣年齡 0.405851 秒；Linked：112 幀、tick 171、0.39335 秒。兩者雙 client、AI 傷害、Pause、精確封存與回放統計均通過，證據目錄分別 20261029-184230-c46bf89a／20261029-184314-3cf58642。這證明本機該次條件；編譯並行或其他負載的延遲不達標仍需場館效能驗收，不能稱為所有負載的 SLA。

末端 health 檢查發現原 5080 無 listener、舊 PID 17748 已不存在；本輪自己的 API 都使用隨機埠且已停止，未宣稱原預覽一直健康。先將 root data 與 src/VrCommand.Api/data 的 21 檔備份並逐檔核對 SHA-256，再用原 build-v016 API DLL、原憑證與明確原 missions／sessions 路徑恢復，沒有重建空資料庫或升級後端。新自有 PID 52992／0.16.0／health ok，三個 SQLite 邏輯內容雜湊與重啟前完全相同，9 場歷史、10 任務版本／9 heads、4 world recording、活動 0。證據在 artifacts/pc-preview-restart-backup.json／pc-preview-restart-verified.json。

功能提交 b080a39 已推送並核對遠端 main 相同。CI run 40860603854／check 123402555735 在任何 step 開始前即結束，steps／logs 為空；annotation 仍明確為近期付款失敗或支出限制，另有 ubuntu-latest 遷移通知。未修改帳務或重跑受限工作，本機實際驗證與雲端未執行分開記錄。

交付前另外實測不帶 --api-dll 的預設命令，發現一般 Release 目錄仍是舊 API，雖能 health 卻無法發布目前世界。新增建立場次前的 API 0.16.0 檢查；舊 DLL 的反例立即拒絕（desktop-demo-stale-api-rejection.log），不以檔案存在當同版。鎖定還原與一般 Release 建置完成、0 警告／0 錯誤後，以預設 API 再成功啟動並收尾（artifacts/desktop-demo/20261029-185350-7c435723）；DESKTOP 已列出完整建置／啟動命令。原預覽仍使用自己的 build-v016 DLL 與原資料，沒有為更新一般輸出停止預覽。這次只更新啟動器及文件，不需重新建置相同 Unity 來源。

操作見 DESKTOP。原始完整目標仍開發中；接續 PC 重連／撤銷、五場同時隔離、圖形聲光與操作員控制驗收，取得設備後再做 Quest／VIVE、MR、硬體與 25 人。當前可繼續 PC 工作，沒有因缺頭盔或 CI 帳務限制宣告整個目標 blocked。

## 2026-10-29：真正 Unity 建置、穩定跨平台識別與電腦雙玩家驗證

使用者確認 Hub 有效授權後，真正 Editor 6000.3.27f1 已成功解析 UPM、編譯／ILPP、匯入音訊／Shader、Prepare、執行 **21 項 EditMode 全數通過**，並完成 Windows 播放器與 ARM64／IL2CPP Quest APK。這是目前狀態；下方舊 CLI session／Prepare 198 僅為歷史。使用者目前沒有頭盔，明確指定先繼續電腦端；完整 11 項與 VIVE／Quest 相容目標仍開發中。

真正匯入揭露並修正 Editor asmdef 缺少直接 MetaQuestSupport 引用、不存在的 textrendering module，以及 TestAssemblies 重複 TestRunner 引用。新增可離線的真正 Editor SDK 診斷工具及移除引用的 CS0234 反例；其較窄範圍見 UNITY_SDK_CHECK，不代替此輪真正 Editor 結果。保存實際 packages-lock.json、URP 升級結果、生成資產與全部 meta／OpenXR 設定。UPM 實際選用 Transport 2.7.4、Collections 2.7.1、Burst 1.8.31 等，與較早診斷圖分開記錄。

原 Prepare 每次重建場景會改變本地 file ID，不能將 Desktop／Quest 各生成一個世界。現在重用保存的 Arena／PlayerAvatar，驗證並持久保存非零 NGO hash；明確 RebuildArena 後須重建所有平台。新增三項實際資產整合測試，涵蓋重複 Prepare 識別、scene／prefab／音訊引用及 Android XR 設定。建置腳本最低 21 Tests，成功／失敗明確 exit 0／1；失敗反例已確認。增量建置的啟動 exe 可能維持舊時間，改以真正成功 BuildReport 後產生的新 receipt 驗證此次輸出。

最終 Desktop／Quest receipt 的來源 fingerprint 同為 `563c2b38ff5c0b079b0b5bfbf0e72db72348f5046494f02d8c27fa3a866c616b`，scene GlobalObjectId 尾端 `1444571642-0`、prefab 尾端 `5227825248646244841-0` 相同。Quest 最終完成 UTC 2026-10-29T03:46:02Z，APK 67,969,388 bytes，application-id com.vrcommand.quest、minSdk 32／targetSdk 35、簽章 v2 驗證成功；ARM64 與檔案雜湊詳見 artifacts/native-build-validation.json。Windows 完整播放器在 artifacts/desktop，不能只複製啟動 exe。兩者為 Development 建置，不是發行包或頭盔驗收。

新增 scripts/smoke-unity-player.py，建立自己的隔離 API／SQLite／短效玩家票券與憑證，啟動真正 Windows Unity server 加兩個真正 desktop client，使用 UDP／NGO。獨立房間 5 與五房 Linked（客戶端分別在房間 1／5）均驗證入場、兩份 Simulated rig、Running、敵軍確認傷害、Pause tick 凍結、End 戰鬥／世界精確封存及回放末幀統計一致；最終活動場次 0。全部使用 Simulation，沒有頭盔或正式服務資料寫入。

首次原生觀戰雖可封存，卻觀察約 12 秒排隊。WorldPublisher 網路 await 改為不捕捉 Unity 同步內容，成功送幀後移除額外固定 50 ms 等候，保留單份 outstanding、戰鬥依賴及 durable ack／seal。修正後獨立 smoke 保存 116 幀、暫停 tick 167、最大取樣來源年齡 0.46213 秒、AI 確認傷害合計 40；Linked 保存 115 幀、暫停 tick 172、最大取樣年齡 0.424355 秒、傷害 100。證據分別為 artifacts/unity-player-smoke/20261029-113725-8744e1bd 與 20261029-113913-7fc522c5。這是本機三個 Unity 程序的無圖形 smoke，不是所有網路條件的延遲分布、鍵鼠射擊、GPU、聲音聽感或 25 人證據。

共用發布器變更後，鎖定還原／隔離 Release 建置 0 警告／0 錯誤，重新通過 **472 核心、369 HTTP、43 世界串流**；Unity **21 項 EditMode** 實際執行通過。UI 未改，本輪沒有重跑先前 17 Node／122 Chromium，不將舊 1023 項混算為此次新結果。完整規範與限制見 NATIVE_VALIDATION。正式預覽 5080 未停止、未更換 DLL 或資料庫。ADB 最近為 0 裝置，使用者已明確無頭盔，不再要求立即連接。

下一步繼續電腦端的可操作畫面、鍵鼠射擊、重入／撤銷與斷線驗證；之後取得設備再做 Quest 控制器／追蹤、聲光／圖形、MR、VIVE／廠商硬體與 25 台效能。完整長期目標不以此輪建置成功結案。

功能提交 990b946 已推送並核對遠端 main 相同。CI run 40814450437／check 123252141894 已結束，steps／logs 為空；annotation 明確為近期付款失敗或支出限制，工作未啟動，另有 ubuntu-latest 遷移通知。本機與雲端結果分開記錄，未修改帳務或重跑受限工作。預覽 health 仍 ok。

## 2026-10-29：擴大 Quest managed SDK 綁定與 URP 版本對齊

上一輪 v0.16 已推送、部署並完成資料保留／模擬聲光驗證，屬於具體進展；本輪從乾淨 e6b6d86 接續，完整目標與 Quest 3 優先保持。最新真正 Prepare 仍是上一輪授權退出 198；本輪沒有新授權可用的證據，也沒有重複啟動相同失敗工作、重裝工具或操作登入／安全性提示。

新增 scripts/check-unity-sdk.py，將原本僅語法／單一天氣元件的檢查擴為 10 runtime／5 NUnit 檔案的實際 managed API 型別編譯。官方 NGO 2.7.0、Input 1.17.0、Transport 2.6.0、Burst 1.8.24、Collections 2.4.3、Math 1.3.2，綁定本機真正 Editor Core／Audio／UI／XR 等 DLL 與隨附 UI／NUnit。每個 Android／Windows 分支編譯 976 份 managed 來源（含上游），另引用共用 Simulation；沒有自製 stub，不修改上游來源。

本機實際 Unity.exe ProductVersion 為 6000.3.27f1_672d562a42a7，BuiltInPackages 的 URP／SRP Core 為 17.3.0，而 manifest 還指定 17.0.4，已對齊 17.3.0；Core 的 Collections 相依為 2.4.3。這是檔案／版本設定證據，不是 UPM 解析成功；原 17.1 範本資產及授權仍保留，匯入／升級待真正 Editor 驗證。API／bundle 0.16／NGO wire 16 不變，沒有替換預覽 DLL 或操作資料。

六份官方 registry archive 下載時核對固定 SHA-1，來源 receipt 另記各檔 SHA-256，快取改動／遺失／新增來源會拒絕。首五份從本輪已驗證的探索快取保留原文初始化正式快取，Collections 2.4.3 由正式工具下載驗證；原 2.2.1 探索資料保留在 artifacts。產物與報告在 artifacts/unity-sdk-check，僅編譯所需來源／支援 DLL／授權文件保留於正式快取，第三方內容不提交。報告開始即設 complete=false，成功記時間、檢查器與來源／DLL 雜湊、符號及退出碼，避免舊成功冒充新嘗試。

Android／Windows 與最終 --offline 重跑均通過，零錯誤；完整重建分別 18／19 警告（上游未使用欄位／隱藏成員、本工程 JsonUtility DTO 反射填入欄位的 CS0649），沒有宣稱零警告。18 項 NUnit 方法只完成型別編譯，沒有執行。另以自己的暫存 fixture 確認舊 URP pin 在編譯前拒絕；刻意修改自己的 Mathematics 快取來源後拒絕，finally 恢復原文及 receipt 核對成功，再實際離線編譯兩分支。證據為 artifacts/unity-sdk-guards.log、unity-sdk-offline.log 與 unity-sdk-check/report.json。

探索工具首次漏列舊 Unity 版本符號、誤納 Unity 忽略的 bee~ 來源，以及將隨附 ILSupport DLL 誤當空白 C# 專案，已依官方來源／README 改正工具選檔與引用，沒有修改上游程式來讓它通過。正式工具使用對齊 Core 的 Collections 2.4.3 及兩個明確條件分支，通過的是 managed 綁定；沒有模擬完整 Unity CompilationPipeline／UPM。ProjectBuilder／OpenXR／URP 渲染程式、NGO／Burst／Collections ILPP、原生執行、Shader／音訊匯入、EditMode／Desktop／IL2CPP／APK／頭盔均仍待驗收，診斷 DLL 不可部署。

文件已同步至 UNITY_SDK_CHECK、QUEST3、README、ROADMAP、REQUIREMENTS 與 AGENTS。管理服務 5080 當下 PID 17748、API 0.16.0／health 正常；沒有停止、換資料庫或新建場次。本輪未變更業務／UI，因此沒有重跑 v0.16 的 1023 項管理／模擬／瀏覽器檢查，該結果仍只是上一輪證據。下一主線仍為有效 Editor 授權、真正 Prepare／18 Tests／Desktop／Quest 及雙 Quest 實測；本輪可重複的完整 runtime 型別證據不能替代它們。CI 按推送實際結果另記，長期目標保持開發中。

fc44414 已推送，遠端 main 核對相同。CI run 40792806909／check 123181895880 已終止且 steps／logs 為空，annotation 再次明確為近期付款失敗或支出限制，工作未啟動；另有 ubuntu-latest 遷移 notice。沒有雲端通過證據，未修改帳務或重跑受限工作；本機 SDK 檢查結果與範圍如上。

## 2026-10-29：v0.16 天氣聲光、共用時間規則與舊錄製相容

從乾淨 a3e2dee 接續完整長期目標，Quest 3 仍優先。本輪再次實際執行 Prepare，退出 198，日誌為「No valid Unity Editor license found」，沒有待執行中的建置；未操作登入／安全性提示、重裝已整理的 SDK 或重問已同意的條款。CLI 登入狀態不能單獨否定 Hub 授權，這裡以實際 Editor 結果為準。整個 Unity／NGO／ILPP／Shader／AudioImporter／18 項 EditMode／桌面程式／APK／頭盔均沒有成功證據。

需求 5 新增共用 EnvironmentPresentation（C# 9／.NET Standard 2.1）：依權威 tick 決定雨、霧、日夜、閃電與延遲雷聲，不用本機時間推進戰鬥。每房 64／128 雨線，最多 640 根、1280 頂點單網格；聲音兩個可重用音源，都是顯示效果，不改命中／碰撞／尋路。首次觀察、倒退、長缺口及設定變更不補播錯過的雷聲，暫停／過期停止聲光活動。Unity 已接原子 WeatherState 與網格／AudioSource，生成器 NGO protocol／Android code 16、bundle 0.16.0，所有遊戲端需同版重建。

新增 check-weather-unity-api.ps1，以本機真正 Unity 6000.3.27f1 的 CoreModule／AudioModule DLL 編譯單一 UnityWeatherView 與共用核心，0 警告／0 錯誤；不是 stub，但不涵蓋 SceneAuthority／NGO 或整個 Unity 工程。26 份 C# 9 語法檢查通過。新增三項未執行 EditMode，總數 18；沒有以部分 SDK 編譯替代實際 Editor 結果。

世界 header 新增選用 environmentVersion，新來源預設 1、舊缺欄位保持 0，拒絕未知版本與改既有版本。舊資料庫 header 原文與 binary JSON／checksum 不改寫，WorldOutbox 用 codec 正規化後比對。新 NDJSON 也附擷取 UTC，舊來源仍保持原本未知／有時間狀態。worlds.db schema 1、session envelope 6 不變，但嚴格舊 reader 不接受新欄位，需 API／UI／來源協同升級且不可直接降版。schema 2 本機模擬回放沒有完整環境欄位，仍用既有顯示。

瀏覽器觀戰／持久回放以同一時間規則重建雨、霧、日夜與閃電；按音效開關後才建立／恢復 Web Audio。兩份原創合成 PCM 由固定整數 DSP 生成，各 4 秒 mono／22050 Hz／16-bit，provenance 記 SHA-256，API 直接打包 Unity 同一份來源。重現不是原始音軌或影片，沒有聽感／聲壓或 MR 驗收；legacy 保留原光霧且音效關閉。規範、操作與可重現旗標 --environment-demo true 見 ENVIRONMENT。

鎖定還原與 Release 建置通過，0 警告／0 錯誤；**472 核心、369 HTTP、43 世界串流、17 Node、122 Chromium，共 1023 項通過**。涵蓋 144 組 C#／JS 樣式、60 組雨座標、85 組雷聲步驟向量、舊 header／journal 恢復、版本拒絕、實際 Web Audio 非零輸出／延遲 cue、回放閃電、跳轉不補播、暫停與 legacy 顯示。世界測試首輪 43 項通過後，新增 fixture 的 Python sqlite connection 尚未關閉導致 Windows 清理失敗；已顯式 close，重跑整個世界測試退出 0。語法檢查首次誤用 Windows PowerShell 不支援 utf8NoBOM，改以環境的 PowerShell 7 執行後通過；腳本原本無需修改。已檢視 world-environment-rain-night.png，仍是基本幾何、合成頭手及軟體 WebGL，沒有頭盔證據。

預覽確認活動 0／自有 PID 25348 後停止，root data 及實際 src/VrCommand.Api/data 完整備份至 artifacts/backups/pre-v016-20261029-075351，共 21 檔雜湊一致，pointer 為 artifacts/pre-v016-backup-path.txt。隔離 v0.16 DLL 明確指定資料目錄啟動，新 exec 29871。原 8 場歷史、9 任務版本／8 heads、3 world metadata 與主控鏡頭位置保留；metadata 僅在回應增加 legacy environmentVersion 0，另以備份 DB 比對確認原始 header 完全沒改寫。

真實舊 v0.13 binary 來源 clocked-20261029-052526.worldlog 由 v0.16 工具恢復，64 幀 ack／complete 保持、整檔雜湊不變，API metadata 亦不變。另在自己的空房 5 新建 Simulation 夜間雷雨 d23778f9-1834-4afe-a50e-52a2760690b4，共 244 幀、environmentVersion 1、含 UTC 及 tick 140／180，完整封存後活動 0。所有原資料與鏡頭逐欄保留，兩份實際預覽 WAV 與 canonical bytes 一致；來源及摘要在 artifacts/v016-live-demo.json 與 artifacts/world-source-demo/weather-20261029-075426.worldlog。這不是 Quest 遊戲運行。

後續先完成有效 Editor 授權與真正 Prepare／18 Tests／Desktop／Quest、雙 Quest 互見／頭手／撤銷／排空及聲光同步；再推進正式美術、MR、廠商硬體、VIVE 相容及 25 台效能。完整 11 項保持開發中，CI 按本輪推送實際結果另記，不改帳務或重跑已知受限工作。

功能提交 6df4d3a 已推送並確認遠端 main 相同。CI run 40790759521／check 123175098637 已結束，沒有 steps 或 logs；annotation 明確為近期付款失敗或支出限制，工作未啟動。ubuntu-latest 遷移通知不是測試失敗。本機 1023 項結果保持有效，雲端尚未通過；未修改帳務或重跑受限工作。

## 2026-10-29：v0.15 不可變任務修訂、歷史與新舊版開場

上一輪 v0.14.1 已推送及部署鏡頭位置，屬於具體進展。本輪從乾淨的 9639a32 接續，CLI 仍 loggedIn=false、active=false／licenses 空，未找到新的常見授權檔；沒有重跑同一個 Prepare 或重啟舊回呼。最近 Editor 結果仍為 198，Hub 登入／有效授權待本機確認。沒有新的 Unity／15 項 EditMode／桌面程式／APK／頭盔結果，也沒有操作登入、安全提示或重裝 SDK。Quest 3 主線優先及原始完整 11 項範圍保持。

需求 8 新增 Persistence.SqliteMissionLibrary：DataDirectory/missions.db，WAL／FULL／獨占 writer lease，完整 schema 1 Mission、series／number／previous、服務端作者及 request 同交易。根版本為 series 自身，修訂只從當前 head 新增不可變 ID，並行舊 base 只有一個可成功。新任務的 key 選用以相容舊工具，修訂 key 必須提供；UI 兩者固定提供。相同請求綁作者／kind／parent／全部定義，之後 head 前進仍回原接受版本。任務本體、場次 envelope 6、世界 schema 1 及 NGO protocol 14 不變，既有場次不跟著任務庫更新。

首次啟動把原 GUID.json 在同一交易匯入各自第 1 版，保留原檔 bytes；壞資料／不一致鏈失敗即回滾，後續只讀 catalog。目前 Core 的舊 JSON helper 讀寫已版本化目錄會拒絕，不混跑不同版 API。ReadMission 明確驗證已認證身分，共用範本對配置角色可讀，AuthorMission 限 Master／受信任 in-process Internal；所有 HTTP 路由傳入 Actor，不用隱含 Internal。history 只取有界 metadata（預設 20／最多 100），選取才讀完整定義，主控台輪詢 /mission-library 的各系列 head，舊 /missions 保留全部快照契約。

UI 新增保存下一版、歷史分頁／讀回及「選用草稿原版開場」。背景更新保留草稿、已知 head 不倒退、開場版本不偷偷跳到最新版；已知舊草稿不得修訂，409 保留內容供載入新版本或另存新任務。網路、逾時及 5xx 保留完整原請求；保存已接受但後續資料讀回失敗仍保留重試，不再重複建立新任務。登出清理草稿／版本／配置並阻擋晚回應。手機保存列移除多餘的固定高度空白，已檢視 mission-versions-desktop.png 與 mission-versions-mobile.png。

鎖定還原、Release 0 警告／0 錯誤；**451 核心、369 HTTP、39 世界串流、12 回放資料、108 Chromium，共 979 項通過**。驗證含匯入原檔不變、失敗回滾與修復重試、writer lease、非法身分、線性並行、保存 key 衝突／跨作者拒絕、游標分頁、重啟後請求／head／舊場次保持、新舊版實際 API 開場、主控回應遺失後 head 前進、保存後讀回 503、舊 catalog 晚到不倒退與登出競態。本輪未改 Unity／共享 Runtime，這些是管理／Simulation／軟體 WebGL 證據，不代表 Unity 場景還原或頭盔測試。

升級前空陣列檢查因直接 @(Invoke-RestMethod) 的包裝誤判，檢查退出後仍錯誤啟動新版，被既有 events writer lease 拒絕；原服務與資料未動，也未建立 missions.db。已改為先賦值再檢查並分步驗證成功後才啟動相依操作。真正確認活動 0／自有程序後停止，root data 及 src/VrCommand.Api/data 完整備份至 artifacts/backups/pre-v015-20261028-231232，17 檔雜湊一致，pointer 為 artifacts/pre-v015-backup-path.txt。新 exec 49439 為 0.15.0，原 8 任務／8 場歷史／3 份 world metadata／主控鏡頭位置逐欄一致，任務皆匯入第 1 版。前置快照的鏡頭陣列亦有額外包裝，僅比對時解包，原 artifact 留存，證據為 artifacts/v015-migration-check.json。

於自己既有 clocked Simulation 任務 f71fb223-dcc0-4a4a-8166-35b06ec47379 建立第 2 版 913a28f2-9826-4c8e-a8e0-34fc76c1bdd2「Quest 3・夜霧巡邏（開發示範）」，保存 1800 秒、Fog／Night、2 名 Patrol 敵軍；同 key 再送回同一版本。原 v1 及歷史場次 e382ddcc-733b-440a-ab6a-395f5aa37a35 完全不變，活動仍 0。主控可直接在任務編輯器查閱新舊版；沒有把此任務保存宣稱為遊戲運行。摘要在忽略的 artifacts/v015-live-mission.json。

完整契約與備份／不可直接降版見 MISSION_VERSIONS，已更新相關需求、路線、API 與儲存文件。接續仍先取得有效 Unity 授權及實際 Prepare／Tests／Desktop／Quest、雙 Quest 頭手／重連／撤銷／排空，再做正式軍事素材、硬體、MR、VIVE 及 25 台效能。CI 依推送結果另記，不改帳務或重跑已知受限工作；長期目標保持開發中。

3430a67 已推送；功能 CI run 40786700224／check 123161576652 已終止且 steps 空，失敗 annotation 為付款／支出限制，工作未啟動。另有 ubuntu-latest 遷移 notice，不是本輪測試失敗。本機 979 項結果有效，未宣稱雲端通過，未更改帳務或重跑受限工作。

## 2026-10-29：v0.14.1 觀戰鏡頭位置持久保存與重試

上一輪已安裝、驗證並啟動 Hub，屬於實際工具鏈進展。本輪從乾淨的 28cdac3 接續；CLI 仍無登入／授權，但不單獨據此否定 Hub。Hub 及 Licensing Client 已在執行，實際 Prepare 再驗仍因「No valid Unity Editor license」退出 198，已結束。沒有新登入／安全性操作、重裝 SDK 或重問已同意條款；Unity／15 項 EditMode／桌面程式／APK／頭盔仍未通過，Quest 3 主線保持優先。

需求 10 的觀戰新增命名保存、切換、移除與重新讀取鏡頭位置，保存世界目標、theta／phi／radius；跟隨時只保存當下固定位置。位置存在同一 worlds.db 的新增 camera_bookmarks 表，按完整 OperatorIdentity 及場次隔離，只有 Master／RoomController 可用，每次重查可讀房間及錄製。每身分／場次最多 24 個有效位置，名稱／座標／角度／距離有界，不寫瀏覽器儲存或影響玩家名額、世界幀、統計、錄製 updatedAtUtc。

PUT 以客戶端新 GUID 保存不可變內容，相同內容重試回原建立時間，不同內容 409；DELETE 留 tombstone，可原樣確認。已接受後被其他視窗移除的舊 PUT 回 Deleted，不重新建立位置。UI 保存／移除遇網路中斷、10 秒逾時或 5xx 保留原 ID／名稱／視角，凍結新寫入及換場，提供重試；登出清理，epoch 阻擋晚回應進入另一身分。修正全部房間取景把 'all' 轉為 NaN；窄視窗全館所需較大距離可保存，縮放／保存範圍一致為 2–240 m。共享 Runtime、envelope 6、world schema 1 及 NGO protocol 14 不變，API／UI 版本為 0.14.1。

鎖定還原與 Release 建置 0 警告／0 錯誤；**420 核心、322 原 HTTP、39 世界串流、12 回放資料、90 Chromium，共 883 項通過**。覆蓋 SQLite 重啟、完整身分隔離／房間及角色拒絕、配額、非法視角、保存／移除遺失回應、舊保存晚到不復活、任意平移旋轉還原、新登入讀回、登出後舊保存回應不污染另一控制台。已檢視 world-camera-positions.png 及 world-replay-mobile.png，桌面／手機鏡頭介面可操作。本輪未改 Unity 來源；這些結果是 Simulation／軟體 WebGL，不能代替 Unity、真實 GPU 或頭盔驗收。

確認預覽活動場次 0 及自有程序後停止，完整備份 root data 與實際 src/VrCommand.Api/data（含 WAL／keys）；16 份 API data 檔逐檔雜湊相符。路徑為 artifacts/backups/pre-v0141-20261028-223839，pointer 為 artifacts/pre-v0141-backup-path.txt。隔離 DLL 以明確 DataDirectory／SessionDataDirectory 啟動，新 exec 16894 服務 0.14.1；原 8 份歷史場次與 3 份 world metadata 逐欄完全一致，活動仍 0。於自己既有 clocked Simulation e382ddcc-733b-440a-ab6a-395f5aa37a35 保存「房間5・開發示範全景」鏡頭，ID 45f90259-b86c-4053-a146-3cbf3b9fcbd6，主控可直接選取回放及切換。來源／升級摘要在忽略的 artifacts/v0141-*。

接續仍先完成本機 Hub 有效授權及真正 Prepare／Tests／Desktop／Quest、雙 Quest 頭手／重連／撤銷／排空；再推進正式軍事素材、任務版本、硬體協議、MR、VIVE 及 25 台效能。完整 11 項驗收範圍維持，長期目標開發中。本輪 CI 以推送實際結果另記，不改帳務或重跑受限工作。

a8cc007 已推送；功能 CI run 40782250833／check 123146580012 已終止、steps 空。失敗 annotation 明確為近期付款失敗或支出限制，工作沒有啟動；另有 ubuntu-latest 映像遷移通知，不能把它當成本次測試失敗原因。本機 883 項結果有效，未宣稱雲端通過、未修改帳務或重跑受限工作。

## 2026-10-29：Unity Hub 安裝與授權診斷

從乾淨的 19aacf9 接續，先核對 M2 建置阻礙，未擴增遊戲來源或宣稱新功能版本。CLI 仍未登入，license list 空，license status 為 active=false／signedIn=false；先前 Prepare 的 198 結果不變，本輪沒有重跑相同失敗建置。Appx、解除安裝登錄及常見安裝目錄原先未找到 Hub，只有 CLI；也未找到常見位置的本機授權檔。這些診斷不能取代實際 Editor 授權／建置結果。

已從 Windows 套件來源取得 Unity 官方 CDN 的 Hub 3.22.5 x64 MSIX（260081856 bytes），SHA-256 與來源提供值相符，Authenticode Valid／Unity Technologies SF。以 Add-AppxPackage 安裝，註冊版本 3.22.5.65535／Status 0，主程序 49404 及 Unity Hub 3.22.5 視窗均已實際確認。Windows 管理的套件位於 C 槽；工程、6000.3.27f1 Editor、Android 工具與安裝包仍在 F 槽。未重裝 Editor／SDK，原生工具的既有成功結果維持。

Computer Use 觀察到 Windows 安全性對 adb.exe 網路存取提示遮住 Hub；未操作提示、變更防火牆或代填帳戶。已請使用者自行處理提示、在 Hub 登入並到 Settings → Licenses 確認有效授權；若需新增，由使用者選擇適用方案及確認條款。不要求提供密碼／token／序號，也沒有選擇 Personal 資格或購買授權。

QUEST3、ROADMAP 與 AGENTS 已記錄新狀態，避免後續誤稱 Hub 尚未安裝或重啟過期登入回呼。官方 CLI beta.14 支援帳戶啟用；Hub 授權也可能獨立於 CLI 工作階段，後續以實際 Prepare／Tests／Desktop／Quest 為準。授權確認仍待使用者操作；沒有新的 Unity 編譯、EditMode、桌面程式、APK 或頭盔證據。既有 v0.14 的 843 項本機檢查未在本輪重跑；本輪只改文件，未變更後端／遊戲／預覽資料。長期目標保持開發中，完整 11 項驗收範圍不變。

## 2026-10-29：v0.14 每次入場識別、票券 v2 與撤銷接入

上一輪 v0.13 已推送、部署並完成具體驗證。本輪以乾淨的 27242b2 接續原目標，CLI 仍 loggedIn false／license list 空；新的 Prepare 實際退出 198，命令已結束，沒有等待中的 Unity 工作。SDK 條款無須重問，沒有重裝或代填登入。長期目標保持開發中。

新增 Player.admissionId，以原始 PlayerJoined.EventId 為本次入場識別；新 schema 6 payload 明確保存，舊 1–5 從原 EventId 穩定推導，不改寫歷史。相同玩家／房間／席位重新加入仍取得新識別；相同加入 requestId 只確認歷史。PlayerLeft 保存實際 admission 與原始 expectedAdmissionId；同 requestId 改 fence 回 409。DB schema 仍 1，但新 envelope 不能降回舊 reader。

票券改 v2，HMAC 簽 session／player／admission／room／seat／expiry／nonce，仍五分鐘且頭盔只拿四欄連線檔。舊 v1 即使原簽章／期限有效也拒絕。配票及新的 HTTP 玩家移除必須 If-Match-Admission，缺／壞 header 400、入場變更 409；已接受的舊移除只確認，不影響後來入場者，未接受的舊 fence 不可移除新成員。舊版已接受且無 fence 的 requestId 仍可確認。

GameServer 驗票需 protocolVersion:2，驗簽後原子比對當前 admission／room／seat／state，回 throughSequence 及 expiry。ArenaSession.Connect 必帶 admission，Preparing 輪詢即使跳過離場／同 ID 重入也能撤銷舊 binding，舊姿態／武器不影響新身體。Running 不得換 epoch／重生。Preparing 重新入場變更名稱的世界統計 metadata 亦對齊最終 ledger，避免封存名稱不一致。

Unity 來源碼加入驗後取得至少 throughSequence 的快照、expiry／epoch 比對、即時清除內部過時 binding、遠端斷線／Host 關閉，以及合併串行管理 fetch，避免多個 approval 回應造成快照倒退。approval buffer 20 秒；既有連線撤銷仍依管理觀察，正常目標 0.5 秒，管理過期 1.5 秒暫停，未承諾實機零延遲。生成器 bundle／Android／NGO protocol 14。新增三項待執行 EditMode，總數 15；JSON 舊管理範例補 admission，不以忽略 epoch 作相容解法。

鎖定還原／Release 0 警告／0 錯誤，**399 核心、322 HTTP、32 世界串流、12 回放資料、78 Chromium，共 843 項通過**。23 份 C# 9 語法通過；同源 Runtime 仍真正建置 .NET Standard 2.1，沒有 Unity SDK 編譯。驗證含 SQLite 後撤銷保持、同 ID／同席位重入、簽章正確的舊 v1 拒絕、過時／空 fence、原始重試內容、舊 schema 派生與無 fence 歷史確認、跨輪詢撤銷、世界 metadata／封存一致；瀏覽器讓移除先接受但丟回應，再由其他操作員重入，原 fence 重試保持新玩家。15 項 EditMode 未執行，沒有 APK 或頭盔證據。

本機 5080 先確認自有程序且活動場次 0，停止後完整備份至 artifacts/backups/pre-v014-*，再升級 API／控制台；新 exec 59527 服務 0.14.0。原七場在 player 新增可推導 admissionId 後逐欄一致，三份 world metadata 完全不變。另以自己的空房 5 新建純 API 驗證場次 deb56282-e99c-49a7-abf4-dcd6c1134272：同 ID／席位取得不同 admission、舊票券拒絕、舊 leave retry 無害、新券有效，驗後 End 釋放房間；目前活動 0。沒有把此 API 驗證稱為遊戲或實機，摘要在忽略的 artifacts/v014-live-admission.json。

規範與升級見 ADMISSION.md。下一步仍先取得工具可讀授權，實際 Prepare／15 Tests／Desktop／Quest，驗雙 Quest 的重連／撤銷／追蹤與排空，再推進 5／25 台、硬體、MR、VIVE、任務版本與書籤等未完成項目。完整 11 項及雙平台範圍保留；CI 依本輪推送另記，不改帳務或盲目重跑受限工作。

5e77123 已推送；雲端 run 40778846449／check 123135061355 steps 為空，annotation 指出付款／支出限制，工作未啟動。只有本機 843 項通過，沒有本輪雲端成功證據；未修改帳務或盲目重跑。

## 2026-10-29：v0.13 共用世界來源、Unity 頭手接入與擷取時間

上一輪 v0.12 已推送並部署，屬於實際進展。本輪依目前乾淨的 418decb 接續，CLI auth 仍 loggedIn false／license list 空。完成來源接入後實際 Prepare 再次退出 198，log 為 No valid Unity Editor license；該 exec 32393 已結束，沒有仍在等待的安裝或建置，也沒有 Unity／APK／頭盔通過證據。長期目標持續開發。

新增共用 WorldOutbox／WorldPublisher／WorldWebSocket，真正建置 C# 9／.NET Standard 2.1，Unity 與 Native 工具只替換 JSON codec。來源 binary journal 以 VRWORLD1／length／SHA-256、獨占 lease 及 Flush(true) 保存 header／幀／ack／completion／seal，逐筆重開且只保留最後／待送幀。失敗 ack 不推進 cursor；丟回應／封存重試維持同一內容，壞尾端不自動截斷。發布等待 combat durable ack，世界封存另等 combat sealed；來源補送仍不是世界運算恢復。

Unity 來源新增接受後的世界頭／左右手及旋轉、None／Simulated／Tracked 宣告、追蹤中斷停送、10 Hz 世界錄製、管理前後邊界、suspended Pause、Ended completion 與非同步排空／取消生命週期。頭與雙控制器需同時 isTracked，trackingState 含 Position／Rotation。右手 aim、左手 device pose，尚無手指骨架。Tracked 是客戶端宣告經位置／格式驗證後保留，不能當作裝置認證。AvatarPose 新 source byte 由生成器 NGO ProtocolVersion 13 區隔；bundle 0.13／Android code 13。

Native WorldRelay 新 --world-journal 走相同 Runtime 發布器與校驗來源；--combat-journal 可對應 Unity 原始 journal，恢復前核對 session／stream／origin。原 --recording NDJSON 保留。新增實際來源重開、獨占、掉 ack、掉 seal、磁碟 receipt／completion 失敗、世界對統計依賴、並行發送拒絕與 damaged-tail 測試。Unity 新增五個待執行 EditMode 測試，總數 12；腳本不能再以舊七個結果宣稱通過。

另修正補送新鮮度：header 保存不可重設的 UTC 擷取基準，elapsed 保留來源單調時間，API capturedAtUtc 對照擷取時間，updatedAtUtc 仍為接收時間。觀戰以正在顯示幀的擷取時間判斷，持續收到舊幀仍標過期，無時間標未知、超前時鐘標未同步。v0.12 舊 header 補空值可讀／去重；SQLite schema 1／session envelope 5 未變，但舊嚴格 reader 不接受新欄位，不能把 v0.13 來源配舊 API 或直接降版。

鎖定還原及 Release 建置 0 警告／0 錯誤，**363 核心、302 原 HTTP、32 真實世界串流、12 回放資料、76 Chromium 通過，共 785 項**。22 份 C# 9 語法通過；12 項 Unity EditMode 僅有來源，沒有結果。真實 WebSocket／SQLite／SSE／瀏覽器皆使用共用 Native 發布器驗證，仍不等同 Unity SDK／ILPP／IL2CPP、頭盔或 25 台效能。已檢視 world-old-capture.png，確認有新資料抵達但擷取時間老舊仍顯示過期。

現有 5080 自有預覽先確認活動場次 0，停止後備份完整 API data 至 artifacts/backups/pre-v013-*，再升級前後端，新 exec session 17719 版本 0.13.0。原六份歷史完全一致、兩份 world metadata 僅新增預設 captureStartedAtUtc 空值／capturedAtUtc null。實際重送舊 v0.12 NDJSON 64 幀後 metadata 不變，驗證舊 header 缺欄位的相容性。另新增自己的房 5 clocked Simulation：e382ddcc-733b-440a-ab6a-395f5aa37a35，64 幀 complete、UTC 擷取時間保存、彈藥 2／擊殺 1／血量 80；另一程序恢復 ack 64 後不變，舊六場均保持一致，活動場次仍 0。前面另一次未升級預覽的 shared-source 示範也保留，所有示範均無頭盔。

本輪 ADB 實際讀取 ready 0／unauthorized 0，只表示當下沒有可用 ADB 裝置，未宣稱有頭盔實測。來源／驗證摘要在忽略的 artifacts/world-source-demo 與 artifacts/v013-live-demo.json。接入與補送見 WORLD_SOURCE.md。下一步仍需工具可讀的 Unity 授權及真正 Prepare／12 Tests／Desktop／Quest，驗兩位 Quest 的頭手／追蹤中斷、HTTP／WS 分別斷線、Pause／End、完整排空，再做效能、MR、硬體與 VIVE。未把來源接線當成 Unity 運行完成，完整 11 項需求保持原範圍。CI 依本輪推送另記；未改帳務或重跑已知受限工作。

7c4ddb9 已推送；CI run 40773104321／check 123115220952 的 steps 空白，annotation 指出付款／支出限制，工作沒有啟動。本機 785 項結果有效，但不宣稱雲端成功；未修改帳務或盲目重跑相同工作。

## 2026-10-29：v0.12 持久世界、即時觀戰與伺服器回放

上一輪 v0.11 已推送並部署，屬於實際進展。本輪接續同一 F 槽儲存庫，Unity CLI 仍未讀到登入／授權；沒有啟動新登入或盲目重裝，沒有新的 Unity 編譯／APK／頭盔結果。長期目標保持開發中。

新增 engine-independent WorldRecording field DTO：schema 1、rules 0.8.0、primitives-v1／uncalibrated-vr，保存頭／槍口／方向、頭旋轉／左右手位置旋轉與來源、健康／彈藥／換彈／參戰、敵軍、完整世界事件及環境／AI 政策。此 schema 與既有本機 schema 2 模擬檔不同。未知版本、非有限資料、壞旋轉、幀／世界事件／戰鬥邊界不連續、越界／缺少名冊／政策衝突均拒絕。

新增 GameServer owner 專用 WebSocket world/publish，與既有 combat-stream 同 ID／origin／身分。先 header 再 frame／seal；UTF-8 文字最多 1 MiB。每份四種統計事件逐筆對照 durable combat witness，核對 ID／順序／來源／玩家／shot／enemy／damage／觀察時序，血量及剩餘彈藥也對上此事件前綴。未知來源不會變成真人／物理證據。沒有以世界渲染重新推算權威射擊。

世界另存 SessionDataDirectory/worlds.db（SQLite schema 1、WAL／FULL），管理 events.db／envelope 5 不變。每幀、統計、唯一事件 ID 及 cursor 同交易，拒絕／寫入失敗沒有部分幀。以 sequence／elapsed 索引讀取，不在啟動時載入整場幀。最後 Ended、精確 finalSequence、combat sealed、相同戰鬥邊界及最終統計都對上，才 complete=true；API End 不製造世界末幀。

主控台新增「觀戰與任務回放」，用有 Bearer 標頭的 fetch SSE 讀取 latest／replay，不加入玩家席位。支援房間與角色、自由／俯視／跟隨、暫停、時間索引跳轉、0.25–4 倍速及逐幀統計；頭手來源明示 None／Simulated／Tracked。來源超過 1.5 秒沒有新快照即標過期，心跳不能掩蓋停送；登出／切頁／換場取消串流。刪除離場角色的渲染資源，並修正即時時間軸長度及手機標題排列。

新增 VrCommand.WorldRelay：只建立自己的 Simulation 任務，以真正共用核心產生射擊／擊殺／AI 傷害／暫停／天氣／Ended。原始 NDJSON Flush(true) 後才逐幀送出並核對 ack，旁邊保留既有 combat journal；另一程序可逐行重送，同序內容只確認。來源損壞不自動截斷，缺少完成記錄不補造 seal；目前網路錯誤保留檔案後退出，尚無自動世界重連／恢復運算。

鎖定還原與 Release 建置 0 警告／0 錯誤，**333 核心、302 原 HTTP、24 真實世界串流、12 回放資料、72 Chromium 檢查通過，共 743 項**。17 份 Unity／共享 C# 語法通過，embedded Runtime 亦真正以 .NET Standard 2.1 建置，但沒有綁定 Unity SDK／ILPP。已檢視 world-live.png、world-stale.png 與 world-replay-mobile.png；含真實發布／SSE、來源強制中止後過期、房間範圍、回放統計、SQLite 重啟、整份來源跨程序重送、衝突重試及交易回滾。本機軟體 WebGL 不能代替頭盔／GPU 效能驗收。

本機預覽先確認自有舊程序及活動場次為 0，停止後備份完整 API data 至 artifacts/backups/pre-v012-*，再升級前後端。新 exec session 82831 服務版本 0.12.0，原四份歷史場次逐欄完全一致。新增自己的房 5 Simulation：b15507b1-d4cf-45a7-a830-7c2b4192ac6d，64 幀封存，彈藥 2／擊殺 1／健康 80；用新程序補送後世界 metadata 及五份歷史場次均不變，活動場次仍 0。來源／驗證摘要在忽略的 artifacts/world-demo*，預覽可直接選取此場回放。

Unity 目前只有共享錄製 DTO，**尚未接上世界發布器或真正頭手採樣**；既有統計 outbox 來源碼也仍未編譯運行。接續先完成工具可讀的 Unity 授權及真實 Prepare／Tests／Desktop／Quest，再接世界發送、頭手、雙玩家及斷線驗收。書籤、保留／壓縮、長任務／25 台吞吐量、正式資產、硬體、MR、VIVE 與實機仍待做。GitHub CI 依本輪推送結果另記，沒有修改帳務或重跑已知受限工作。

87e7a6c 已推送。其雲端 CI run 40766549749／check 123092115458 的 steps 為空，annotation 明確指出近期付款失敗或支出限制，因此工作未啟動。不能宣稱本輪雲端測試通過；本機 743 項結果仍有效。未修改帳務、未盲目重跑相同受限工作。

## 2026-10-29：v0.11 持久戰鬥補送、結束封存與主控台完整性

上一輪 v0.10 已推送來源碼與測試修正，屬於實際進展。本輪以該工作樹接續：CLI 仍未登入、license list 空，完成程式後實際 Unity Prepare 再次退出 198；命令已結束，不是仍在等待的建置。整體長期目標開發中，沒有 Unity 編譯、APK 或頭盔結果。

新增 GameServer 專用 combat-stream／reports／batch／seal 端點，Preparing 綁定唯一 streamId、origin 與來源身分。streamSequence 連續，observedSequence 指向事件產生時最後觀察的 Running 管理快照，以稀疏管理索引驗證當時狀態及名冊。Pause／End 後仍接受原觀察尾端，未來／暫停／已離場觀察不能偽造新射擊；既有報告可原樣去重，來源及內容不可換手。綁定後舊 combat 端點不可繞過。

End 釋放房間但 pendingTelemetry 維持 true；精確 finalSequence 已收到且來源送出 seal 後才標為完整。主控台 End 時自動保留待確認歷史，顯示補送／封存提示；新房間場次不受舊尾端影響。新 envelope schema 5 保留舊 1–4，SQLite user_version 仍 1；不得直接降版。批次最多 128 筆、逐筆持久化，失敗可已提交前綴，原樣重試去重續送，不宣稱跨批次原子性。

共用 Runtime 新增 TelemetryOutbox：獨占 journal、版本與身分、SHA-256 frame 完整性、批次 Flush、累計 acknowledgment、completion 及 seal。穩定 eventId 轉 reportId，只選四種統計事件，AI 射線／reload 不冒充玩家彈藥。檔案損壞／截斷不自動丟棄尾端；磁碟失敗不推進記憶體 cursor／ack。補送恢復不是世界恢復，尚無自動修復、壓縮或保留政策。

Unity 來源碼已在伺服器建立 journal／綁來源後開放戰鬥，武器及 tick 在保存後才發佈快照，網路／5xx 保留重試，永久拒絕／磁碟錯誤暫停戰鬥；在管理 End 前先保存原觀察尾端，再完成／補送／封存。預設明確 Simulation，server.json 指到 F 槽 data/telemetry，頭盔四欄設定不含密鑰。尚未編譯／運行發送器，不宣稱實機報表已一致。

新增 VrCommand.TelemetryRelay，可在原程序停止後以同一 journal 補送；只有 completion 存在才嘗試封存，否則保留未確認完整。其 demo 模式在空閒房建立自己的 Simulation 世界，以真正兩次射擊／命中／擊殺及一次 AI 傷害生成六份報告，先 End 並退出；另一程序才讀檔補送。HTTP fixture 另先接受一筆但不保存回應、重啟 API，再跑補送，驗證同一前綴不重複計數。

鎖定還原及 Release 建置 0 警告／0 錯誤，**295 項核心（新增 41 項）、302 項 HTTP、12 項回放資料、59 項 Chromium 通過**；16 份 C# 9 語法通過，embedded Runtime 真正建置 .NET Standard 2.1，Unity SDK／ILPP 未綁定。已檢視 telemetry-pending.png，畫面及測試區分 Ended／待補送／已封存。測試含競爭來源、失序、觀察資格、來源混用、批次部分提交／重試、兩邊獨立重啟、磁碟失敗、壞尾端及確認邊界。

本機原 5080 服務先驗證為本任務程序且活動場次 0，停止後備份完整 API data 至忽略的 artifacts/backups/pre-v011-*，再升級前後端；新 exec session 24293 正在服務，版本 0.11.0，原三份歷史快照在新增 null combatStream 相容欄位後完全一致。舊服務已停止。另於自有房 5 執行 demo 及恢復，場次 bafd9eb0-9309-4e10-b422-0a27a2e9cd78 六筆確認、sealed true、pending false、彈藥 2／擊殺 1／血量 80；只操作新建示範場次。journal 與摘要在忽略的 artifacts/telemetry-demo。

接續優先真正編譯／實測 Unity 管道與 Quest 雙玩家，並開發完整世界持久化、頭手錄製及即時觀戰；25 台吞吐量、硬體、MR、VIVE 型號與實機仍待驗收。沒有把這次統計補送當作完整遊戲完成。GitHub CI 先前曾部分運行但最新受帳務限制，待本次推送再依實際狀態記錄，沒有改帳務或盲目重跑受限工作。

## 2026-10-29：v0.10 Quest 任務與戰鬥接入來源碼

上一輪 v0.9 已推送並更新本機服務，屬於具體進展。本輪再次查核 Unity CLI，仍未登入且無 license；完成接入程式後實際 Prepare 仍退出 198，日誌為 No valid Unity Editor license found。該命令已結束，沒有執行中的安裝／建置等待，也沒有 APK 或 Unity 編譯通過證據。長期目標保持開發中。

embedded package 升至 0.10.0，新增無引擎 ArenaSession 與 field DTO，以真實管理 SessionView JSON 建立世界、名冊、任務掩體、固定席位與全場敵軍。重複刷新保持物件身分；敵軍增減不復活既有死者。VR 場地、資產、地面高度、出生點及範圍會驗證，拒絕不支援的 MR／幾何。遊戲伺服器須從 Preparing 啟動，不以新世界假冒 Running／Ended 的恢復。

以經驗票的連線 ID 綁定玩家，姿態不能指定玩家／傷害。新增核心 Connected 參戰狀態及粗略平面位移檢查；未連線、姿態超過 0.5 秒、斷線或名冊移除者不射擊、不擋彈、不被 AI 選取，保留血量／彈藥。新連線有獨立輸入 ID 域，晚到輸入／舊斷線不影響新連線。Preparing 移除已綁定玩家會安全重建未開局世界；管理 Begin 後全員離開而被輪詢跳過時，也不補造玩家或卡死轉移。

Unity Runtime asmdef 已引用核心，新增 CombatAuthority、伺服器固定步進與管理新鮮度暫停、伺服器 NetworkList、同源掩體及敵軍渲染、右手 OpenXR aim／扳機／A 鍵、桌面左鍵／R、owner 武器 RPC、健康／彈藥／換彈 HUD 與有效參戰顯示。生成器移除未與核心一致的展示掩體，改由任務資料提供，增加武器盒與 CombatAuthority。來源碼要求 Floor tracking origin，尚不可用時暫用 1.65m offset；並非 MR 校正方案。

依本機官方 NGO 2.7.0 原始碼確認 HostServerInitialize 不等待非同步 approval，改為啟動前驗 Host 票券，再同步回答；過期 pending client 不保留綁定。輪詢名冊後斷開被撤銷／結束的遠端連線；Host 玩家被撤銷則關閉 Host。這些都是尚待 Unity 運行的路徑，不能把原始碼檢視當作網路測試。

本機鎖定還原與 Release 建置 0 警告／0 錯誤，**254 項核心（新增 41 項）、282 項 HTTP、12 項回放資料、56 項 Chromium 通過**。15 份 C# 9 語法通過；embedded Runtime 真正型別建置為 .NET Standard 2.1，Unity SDK／ILPP 未綁定。新增三個待執行 EditMode 測試，合計七個；腳本要求至少七個通過，不能用舊四個結果宣稱新接入驗證。新檔案有穩定 meta GUID。

管理 API／瀏覽器仍為 v0.9，本輪未停用或更新原 5080 服務。Unity WorldEvent 目前只在記憶體，未送入 API CombatReport，頭盔 HUD 尚不會自動更新主控台統計。持久 outbox、Pause／End 事件排空、正式世界錄製及即時觀戰列為接續工作，詳見 GAMEPLAY。既有 SimulationDemo 維持明確 Simulation，舊回放規則／格式保留。

下一步仍先讓 Unity 授權可讀並真正 Prepare／Tests／Desktop／Quest，再實測雙玩家、武器／掩體／AI、管理中斷及撤銷；並行可做正式 outbox 與任務結束契約。沒有重新要求已同意的 SDK 條款，沒有代填登入、購買授權或改 GitHub 帳務。

de972be 的雲端 CI（40755707968）已實際啟動，故先前「帳務未讓工作啟動」已不適用本次；Linux 建置、254 項核心、282 項 HTTP 及 12 項回放資料通過。瀏覽器失敗在把隨機 UUID 排序報表的第一列誤認為 Alpha；新增 Temporary 玩家後列序不保證。改以明確玩家列核對，保留六項數值要求，再驗本機及雲端結果。

修正提交 76ab77d 以固定低 UUID 的離場玩家穩定重現此列序，本機 56 項 Chromium 通過。其雲端 run 40756358256／check 123056213471 再次因付款／支出限制未啟動（steps 空，annotation 明確指出帳務原因）。故只可聲明前次 Linux 部分檢查及修正後本機通過，不能宣稱完整雲端成功，也不能認定帳務依賴已永久解除。未修改帳務或盲目重跑相同受限工作。

## 2026-10-29：v0.9 場次與名冊的持久重試

上一輪 v0.8 已推送，屬於有實際程式與驗證結果的進展。本輪再次查核 Unity CLI，仍無登入 session、license list 為空；沒有啟動新登入或重裝 SDK，繼續可獨立開發的連線可靠性工作。整體長期目標保持開發中。

建立場次、加入玩家與移除玩家支援選用 `Idempotency-Key` UUID，與原事件在同一筆 SQLite append 交易中接受。跨三種操作與全館場次共用 key 索引，綁定身分、種類、目標及內容，持久化後重啟重建，失敗 append 不保留 key。每次重試仍檢查房間權限；改內容／身分／操作回傳 409，無效／全零／多值標頭回傳 400。不帶 key 的舊 API 行為保留。

重試回傳原操作已接受的確認與目前快照，不重播舊狀態：已離開玩家不因舊加入重試復活，重新入場者不因舊離開重試被移除；封存場次的建立重試不會占用新場次房間。新事件 envelope 為 schema 4，增加 requestId 與 PlayerLeft.roomId，保留 schema 1–3 讀取；資料庫 user_version 仍 1。不得在寫入新事件後直接降版。

瀏覽器三種操作都保存原 key、路徑、玩家 ID 與 body；遇到連線中斷／5xx 時鎖定後續寫入、切換與輪詢，在工作區頂端保留重試入口，無選中場次也可確認建立結果。成功後重新載入目前狀態。控制命令原去重保留，API 回應 body 讀完後也再次核對登入 epoch；登出後舊回應不能改寫新狀態。待確認操作只在頁面記憶體，關頁不持久保存。

本機鎖定還原及 Release 建置 0 警告／0 錯誤；**213 項核心、282 項 HTTP、12 項回放資料及 56 項 Chromium 檢查通過**。新增並行建立／加入／離開、內容及身分衝突、跨操作 key、容量已滿仍可確認原加入、晚到重試、封存／新場次隔離、SQLite 重啟、append 失敗恢復及 schema 相容／重複 key 拒絕。瀏覽器實際讓伺服器先完成操作再丟棄回應，驗證原 key／body 重送與單筆事件。HTTP 檢查失敗日誌亦改為容錯解碼及遮蔽測試憑證，避免 Windows 編碼錯誤蓋過原失敗。

原本 5080 服務已確認為本任務建立的程序且活動場次為 0。停止後將完整 API data 備份至忽略的 `artifacts/backups/pre-v09-*`，再建置並以原 `scripts/start-local.ps1` 升級主控台與後端；新 exec session 81620 正在服務，`GET /` 為 0.9.0、`/console/` 為 200，升級前後三份歷史場次快照完全一致。舊程序已停止，不要再當作活程序。前後端需一同升級，沒有將可重試前端留給忽略 key 的舊 API。

本輪只完成管理連線可靠性，不代表裝置重連、票券即時撤銷、Unity／APK／頭盔或正式世界串流驗收。接續優先取得工具可讀的 Unity 授權並接入已驗證共用核心；可獨立進行每次入場票券撤銷版本、遊戲伺服器與世界儲存工作。GitHub CI 帳務限制尚無解除證據。

## 2026-10-29：v0.8 3D 模擬回放與 Android 工具修復

新增「3D 模擬回放」頁，可載入實際幾何模擬紀錄或本機檔案，支援播放／暫停、逐格、時間跳轉、0.25–4 倍速、自由旋轉／平移／縮放、俯視及跟隨／點選角色。以快照還原角色、武器與實際掩體盒，顯示已記錄的射線，統計按快照 throughSequence 重建並與結束報表核對，不重新運行 AI。Three.js 0.186.1 由官方套件取得、SHA-512 核對，原始碼及 MIT／provenance 保留，不使用 CDN。

紀錄升至 schema 2／rules 0.8.0，增加 world props、射擊當下槍口／方向／距離／碰撞目標、快照的 AI／能見度／夜間設定。示範新增 10 秒巡邏，實際輸出 216 份快照、8 筆世界事件、10.4 秒邏輯時間；來源強制 Simulation。範例已保存為公開合成資產，沒有控制台憑證或真人資料。舊 schema 1 檔案保留但回放拒絕猜測缺少的資料。正式持久世界、頭盔六軸／雙手、即時觀戰與長任務串流仍待整合。

本機 Release 建置 0 警告／0 錯誤；**181 項核心、234 項 HTTP、12 項回放資料及 50 項 Chromium 檢查通過**。新增射線／快照設定驗證、資料因果與統計一致性、真實軟體 WebGL、鏡頭及時間控制、390px 版面、錯誤檔拒絕、文字渲染與登出後延遲回應不恢復舊檔。已檢視 `artifacts/console/replay-combat.png`、`replay-mobile.png`；這不是實機 GPU／頭盔效能證據。操作及限制見 `REPLAY.md`。

已將新版靜態資產更新到原本 5080 預覽輸出，`/console/` 與回放模組實際 200；沒有為此停止原 API 或改資料庫。管理 API 契約維持 v0.6，主控台／共用核心為 v0.8。

使用者已明確回覆「同意條款並安裝」，已執行 Android 模組安裝。原程序（exec session 34308／CLI PID 40596）已終止，不要再當作活程序重啟：Android、OpenJDK、SDK parent、platform 34 登錄成功，八個子模組回報失敗；單獨重試 Platform Tools 也回報失敗。檔案實際已解壓，部分留在巢狀目錄。

依官方 6000.3.27f1 module metadata 建立 `repair-android-layout.ps1`，先 WhatIf 核對來源／最終絕對目標，再整理限定 AndroidPlayer 內的 NDK、CMake、Build Tools、command-line tools；沒有覆寫／刪除既有目標。再次 WhatIf 無待移動。ADB 37.0.1、Temurin 17.0.18+8、NDK r27c／27.2.12479018（clang 18.0.3）、CMake 3.22.1、aapt2 均可執行；SDK Manager 辨識 Build Tools 36 及 platform 34／35／36。經使用者同意的 android-sdk-license 已用官方 SDK Manager 登錄。

`check-android-toolchain.ps1` 已實際以 CMake／Ninja／NDK 編譯及連結 C++17、Android log／STL、API 32 arm64-v8a 共享庫，驗證 ELF64 AArch64；輸出 `artifacts/android-toolchain-check/build/libvr_command_probe.so`。這是主要原生工具可用的證據，CLI 失敗登錄仍保留，不能宣稱 Unity APK 或 Quest 執行通過。

使用者另回覆「已登入並啟用」，但工具端 `auth status` 仍 loggedIn false、`license list` 空陣列；實際 Prepare 再次退出 198。已啟動一次 Unity 瀏覽器登入（exec session 1845），Chrome 標題停在 Unity ID Account Login，CLI 最終 AUTH_LOGIN_FAILED／登入逾時；該 session 已終止。後續需由使用者本機重新執行登入並等成功，再核對適用授權；不得把使用者回覆本身當作編輯器授權成功證據。沒有購買授權或代填登入。新詢問已提出，繼續其他可獨立開發工作。

整體目標仍開發中。下一步先取得工具端可讀的 Unity 授權並真正 Prepare／Tests／Desktop／Quest，接入共用核心與任務；同時仍需建立正式世界儲存、即時觀戰、硬體與頭盔實機流程。GitHub 雲端 CI 的既有帳務限制未有解除證據。

## 2026-10-29：v0.7 同源射擊、掩體、武器與 AI 模擬

新增 Unity embedded package `com.vrcommand.simulation`，Runtime 四份 C# 是唯一來源；`src/VrCommand.Simulation` 直接編譯為 .NET Standard 2.1／C# 9，不引用 .NET 10 後端或 UnityEngine。已實作固定 20 Hz 時間、準備／執行／暫停／結束、可旋轉掩體與身體盒射線、最近碰撞、隊友阻擋、射擊去重、射速、有限彈匣／備彈、換彈及傷害／死亡。

AI 核心已有 Hold／Patrol／Advance、自動攻擊開關、0.5m 四鄰 BFS 繞障與不可達處理、每步移動上限、視線及攻擊冷卻、霧／暴風雨／夜間範圍。這是簡化平面遊戲規則，沒有群體避讓、進階戰術、垂直地形、硬體或真實戰術模型。每個世界保留穩定事件 ID／序號，以及含武器姿態與 throughSequence 的隔離快照，尚非完整回放或持久世界。

新增 `tools/VrCommand.SimulationDemo`，只建立空閒房的自有場次，以真實射線計算低槍口被油桶擋住、AI 命中、操作設定關閉自動攻擊、側移後兩次命中擊殺；將核心事件依序送進 API 並固定標記 Simulation。預期為彈藥 3、命中 2、擊殺 1、耗損 20、中彈 1、命中率 66.67%、血量 80。API 的幾何場景／槍械輸入仍由外部受信任遊戲伺服器負責，此工具不是頭盔遊戲或持續運作的遊戲伺服器。

新增 51 項有意義的模擬檢查；本機 **179 項核心、234 項 HTTP 斷言、36 項 Chromium 檢查通過**。HTTP 測試用隔離服務實際執行新工具、驗證世界檔與 SQLite 統計及釋放房間。12 份 Unity／套件 C# 語法通過；其中共用 Runtime 另外通過真正的 .NET Standard API 型別綁定，仍不能取代 Unity 編譯／IL2CPP。

一般建置曾因現有主控台程序鎖住 API 的依賴 DLL 而失敗；改用 `artifacts/build-v07` 隔離輸出後，鎖定還原與完整 Release 建置 0 警告、0 錯誤。測試腳本新增 `VR_COMMAND_API_DLL`／`VR_COMMAND_SIMULATION_DEMO_DLL` 路徑選項，保持既有 5080 服務執行，不重啟或停止使用中的主控台。

在本機服務另實際執行房 5 幾何模擬並完成場次，保留 Simulation 歷史供主控台查閱；只操作示範自己建立的場次。除錯檔於忽略的 `artifacts/simulation-demo/latest.json`。完整規則、隔離建置、示範及限制見 `SIMULATION.md`。

下一步仍是 Unity 工程授權／Android 模組完成後匯入編譯，再將此核心接入任務、玩家輸入、擺設／敵軍渲染、NGO 世界快照與可靠統計傳送。現有 Unity 場景未呼叫此核心，管理介面也尚不會自動驅動它；沒有 APK、實機射擊／AI、實機混用或 25 人效能證據。整體長期目標維持開發中。

## 2026-10-29：v0.6 瀏覽器主控台、任務與平面配置

在 Unity 授權／Android 模組等待期間推進可獨立驗證的管理操作。新增 `/console/`，與 API 同程序提供繁體中文軍事風格主控／房間介面。可查看五房名額、從任務建立獨立／五房 Linked 場次、操作開始／暫停／繼續／結束、設定環境與敵軍、管理自房玩家及下載短效玩家連線檔。統計含六項需求指標、剩餘血量、明確來源與歷史查閱；操作紀錄不是 3D 回放。

任務編輯器支援名稱、內容、時間、環境／敵軍及沙包／油桶上視圖配置，可拖曳、方向鍵移動、輸入座標與旋轉、移除，再儲存為新的不可變任務；重新載入保留配置。尚無碰撞檢查、場館校正、任務版本鏈、覆寫或 Unity 載入這份配置。

控制台憑證僅保留在頁面記憶體，登出或重新載入需重新登入；所有資料仍由既有 API 授權，房間控制台不能修改 Linked 整場設定或其他房玩家。下載檔只含玩家票券與遊戲連線資料。使用獨立 JS／CSS 檔案、CSP、文字渲染，不載入第三方 CDN。靜態 web root 固定在輸出目錄，實際 DLL 從儲存庫根目錄啟動亦可服務，不依賴 Development 的來源映射。

管理命令失去回應時保留原 commandId／body／expectedSequence，鎖定後續寫入並提供重試；暫停與 End 的實際已接受／回應遺失情境均驗證只追加一次。待確認時停止刷新，避免已結束場次從活動列表消失而藏住重試入口。表單保存載入序號，舊設定不能覆寫他人命令，背景更新不會悄悄改掉正在輸入的草稿。建立／加入／離開去重與跨頁面重試恢復仍未完成。

本機 Release 建置 0 警告、0 錯誤；**128 項核心、229 項 HTTP 與 36 項真實 Chromium 檢查通過**。瀏覽器使用獨立 API、SQLite 與隨機憑證；驗證拖曳／重載、單房與 Linked 開局、環境／敵軍命令、權限、票券、過期表單、失去回應後重試、模擬統計、未信任文字、登出與手機寬度。已檢視截圖，位於忽略的 `artifacts/console/`。測試原先將 fieldset 當作 Playwright disabled 目標，已改驗實際輸入與按鈕；拖曳測試先捲動到可見圖面後操作。

瀏覽器相依固定 Playwright 1.62.1／pnpm 11.25.0，鎖定檔已產生。F 槽 exFAT 導致 pnpm 預設符號連結安裝失敗；確認 pnpm 11 改從 `pnpm-workspace.yaml` 讀取 `nodeLinker`，新增 hoisted 設定後，已鎖定安裝到隔離的 `artifacts/browser-hoisted` 並以該處套件執行 36 項檢查通過。未更改系統執行原則。CI 已加入鎖定安裝及瀏覽器檢查，雲端執行仍須解除既有 GitHub 帳戶付款／支出限制。操作說明見 `CONSOLE.md`。

當次已用 `start-local.ps1` 啟動本機 API，`/health` 及 `/console/` 實際回傳 200，確認 Production 也能載入介面；不是已部署的 Windows 常駐服務，後續先檢查實際程序，避免重複啟動。

完整長期目標仍未完成。Unity 仍無成功編譯／APK／頭盔證據；實際戰鬥、AI、硬體、MR、自由觀戰、世界快照與 3D 回放尚待開發。

## 2026-10-29：v0.5 Quest 3 工程來源碼與玩家票券

依「先用 META QUEST 3」建立 `clients/unity/`，固定 Unity 6000.3.27f1、OpenXR 1.19.0、XR Management 4.6.1、NGO 2.7.0、Input System 1.17.0、URP 17.0.4。採官方 URP Blank 17.1.0 的專案／渲染設定並保留授權，不含模板快取或雲端專案連結。來源碼包含簡化五區軍事場景生成、頭手姿態、桌面伺服器／玩家模式、玩家審核、狀態與霧／日夜／閃光同步。這些仍待 Unity 實際編譯與運行。

後端新增 HMAC-SHA256 五分鐘玩家入場票券。主控／自房控制台可配發，僅 GameServer 可驗證；驗證包含場次、名冊、到期與已結束狀態。簽章鑰保存在忽略的本機資料目錄，可重啟沿用；不寫進事件。每房固定 `seat` 0–4，離開時其他玩家不移位；舊事件沒有席位時依原加入順序重建。頭盔設定僅含地址、埠及自己的票券，不含控制台／GameServer 憑證。完整撤銷／重連與已連線玩家踢出仍待整合。

新增 `prepare-vr-session.py` 產生自己的單房 Preparing 場次與連線檔、`build-unity.ps1` 建置／EditMode 入口、`deploy-quest.ps1` 型號與設定欄位檢查及部署入口。詳細操作與限制見 `QUEST3.md`。HTTP 測試實際驗證設定助手與票券，但沒有執行 Unity 玩家或 ADB。

本機鎖定還原與 Release 建置通過，0 警告、0 錯誤；**128 項核心檢查及 229 項 HTTP 斷言通過**。包含票券竄改／到期／跨場次／錯誤角色／離開與結束拒絕、API 重啟後票券可驗、舊名冊恢復席位及玩家檔案不含伺服器憑證。8 份 Unity C# 通過 C# 9 純語法解析；PowerShell 腳本通過語法解析。語法檢查未綁定 Unity SDK，不能代替 Unity 編譯。

工具鏈：Unity CLI 1.0.0-beta.14 已安裝；Editor 已完整安裝至 `F:\Tools\UnityEditors\6000.3.27f1`，原安裝程序已成功結束，Package Manager 已就緒。實際 `build-unity.ps1 -Target Prepare` **退出 198：未登入／未啟用有效 Unity 授權**，日誌在 `artifacts/unity-logs/prepare.log`。已請使用者本機執行 `unity auth login` 並啟用適用授權；沒有自行建立帳戶、判定 Personal 資格或購買授權。

Android 模組尚未安裝。Unity 安裝器要求 `--accept-eula` 才能繼續 SDK／NDK 等模組安裝，已請使用者確認條款；尚未代為接受。**沒有成功的 Unity 編譯、生成場景／prefab、EditMode 結果、桌面程式、APK、雙玩家互見或頭盔實測**。下一個 Unity 步驟須先解決授權，再依 QUEST3.md 實際 Prepare／Tests／Desktop／Quest，修正編譯與執行問題。GitHub CI 的帳戶付款／支出限制仍無解除證據。

## 2026-10-29：v0.4 SQLite、戰鬥統計與 Quest 3 優先

使用者回覆「先用 META QUEST 3」。已同步路線、需求及開發指引：先實作 Quest 3 垂直切片，暫按 Android 獨立執行規劃，VIVE 後續接入；未將原始雙平台與 11 項需求縮減為後端原型。

新增 `VrCommand.Persistence`，使用 Microsoft.Data.Sqlite 10.0.14 與版本鎖定檔。預設事件改為 SQLite 交易逐筆追加，管理與戰鬥共用連續序號，記憶體採追加清單、命令／報告索引及增量統計；不再為每次射擊重寫全部歷史。舊 schema 1／2 JSON 先驗證後一次匯入，交易全有全無，原檔保留。單一寫入程序鎖、資料列／envelope 身分驗證與啟動恢復檢查均保留。

新增 schema 3 的 `CombatRecorded`、GameServer 認證接入、明確的 Simulation／GameServer 來源、射擊與命中關聯、唯一敵軍擊殺，以及傷害／血量投影。統計提供彈藥、命中數／命中率、擊殺、中彈、實際耗損及剩餘血量，保留已離開玩家並可重啟重建。主控與房間控制台不能提交戰鬥報告；模擬與 GameServer 來源不能同場混用。

新增 `scripts/demo_combat.py`：只在空閒房間建立自己的模擬場次，使用 Quest3 玩家分類，產生彈藥 3、命中率 66.67%、擊殺 1、中彈 1、耗損 20、血量 80，結束後保留歷史。HTTP 測試實際執行此腳本，並確認沒有占用既有場次或殘留房間名額。

本機鎖定還原與 Release 建置通過（0 警告、0 錯誤）。**119 項核心檢查、207 項 HTTP 斷言通過**，並將測試資料庫放在 `F:\Projects\vr-command-center\artifacts\temp` 重驗 SQLite、交易、鎖定及程序重啟。檢查涵蓋 schema 2 JSON 升級、錯誤匯入重試、唯一約束回滾、重複報告／射擊／擊殺拒絕、因果順序、傷害截斷、離開與暫停、事件不含憑證、兩次 API 重啟與統計一致。

五房 25 個 Quest3 分類的模擬玩家，合計 175 筆戰鬥報告，連同名冊／生命週期共 203 筆事件；總彈藥 75、命中 50、擊殺 25、耗損 500，各玩家血量 80。這是資料與儲存驗證，沒有 25 台頭盔、實際射擊／碰撞／AI 或 FPS／延遲證據。接收端信任 GameServer 來源的已分類事件，尚未獨立判斷真實場景命中。

契約、限制與升級流程見 `COMBAT_PROTOCOL.md`、`STORAGE.md`；CI 已加入 `--locked-mode`，但帳戶付款／支出限制造成雲端工作無法開始的問題尚無通過證據。完整長期目標仍在開發中。

## 2026-10-29：v0.3 控制台認證、五房權限與事件身分

所有 `/api` 端點現在要求 Bearer 控制台憑證，`/health` 保持公開。主控可管理全館；Room1–Room5 的列表／快照限制在自房及包含自房的共享場次，只能控制自己的獨立任務，以及管理本房玩家名額。全連線的整場命令只允許主控。GameServer 身分可讀取場次，不能管理任務、名額或場次；預留作為後續戰鬥事件來源。

新事件 envelope schema 2 保存伺服器驗證的控制台 ID／角色／房間，不保存憑證值。復原時重新檢查事件身分的權限；去重 ID 不能由另一控制台接管。舊 schema 1 保持可讀與 `actor: null`，不補造身分。核心的 Internal 身分僅供受信任的程序內部呼叫；HTTP 不會配發。

新增 `scripts/start-local.ps1`，首次產生七份不同的隨機本機憑證到 Git 忽略的 `data/operator-keys.local.json`，不在畫面印出鑰匙。也可使用環境變數或 `--OperatorKeyFile`；缺少主控、過短、重複或未知憑證設定會拒絕啟動。換鑰在重啟後生效。控制台認證尚不等同人員個別登入、TLS 部署或頭盔設備註冊。

本機驗證：Release 建置 0 警告、0 錯誤；**70 項核心檢查及 163 項 HTTP 斷言通過**，涵蓋五房列表／操作範圍、跨房讀寫拒絕、全連線權限、body 偽造角色無效、錯誤設定拒絕啟動、憑證檔載入、重啟換鑰與舊鑰失效、事件不含憑證，以及既有場次恢復與併發去重。啟動助手已通過 PowerShell 語法解析；HTTP 測試驗證其使用的憑證檔啟動方式，未對實際開發憑證檔進行操作。

文件已同步至 `AUTHORIZATION.md`、README、API 與事件契約。戰鬥統計尚未實作；下一步先選定可持續接收戰鬥事件的儲存方式，避免將高頻事件塞入目前逐次重寫完整檔案的低頻管理事件儲存，再實作統計與模擬器。M1 與完整長期目標均未完成。

## 2026-10-29：v0.2 場次生命週期與持久化管理事件

已實作 `Preparing → Running ↔ Paused → Ended` 管理狀態，建立場次與真正開始分開。新增環境與敵軍設定命令、命令去重 ID、可選預期序號及活動／歷史場次列表。結束後保留名冊與事件，並釋放房間與玩家名額。

事件包含版本、事件 ID、場次 ID、連續序號、後端 UTC 時間及資料；以相同轉移規則在重啟時重建狀態。採單一寫入程序鎖與暫存檔替換；寫入成功才更新記憶體。第二個 API 程序無法同時取得同一事件目錄。未知 schema、損壞資料與序號缺口會使啟動失敗，不重設歷史。

驗證於 Windows 本機完成：Release 建置 0 警告、0 錯誤；**50 項核心檢查及 116 項 HTTP 斷言通過**。包含 20 次併發核心命令重送、12 次併發 HTTP 重送、兩次實際 API 程序重啟、活動與結束場次恢復、第二個 API 寫入程序被拒絕、版本衝突、磁碟錯誤不推進狀態與損壞檔案拒絕恢復。測試資料與子程序在結束後清理。

契約與操作範例見 `SESSION_PROTOCOL.md`、`API.md` 及 README。v0.1 的 `GET` 已結束場次由 404 改為可讀取歷史；`StartedAtUtc` 改為在 `Begin` 前可為 null。建立／加入／離開操作尚未提供客戶端去重 ID；優先使用 `/commands` 進行可重試的控制。

這些是管理事件，尚無操作者身分、戰鬥事件、傷害、3D 世界快照或頭盔同步；環境／敵軍命令僅更新設定，尚未接到渲染或 AI。M1 仍在進行中。GitHub 雲端 CI 的帳戶付款／支出限制尚未解除，本次結果僅宣稱本機驗證。

## 2026-10-28：建立長期目標及 M0

長期目標已在本對話建立，維持開發中；本地開發根目錄為 `F:\Projects\vr-command-center`。本檔保存接續工作的事實與依賴，整體需求見 `REQUIREMENTS.md`。

GitHub 長期開發追蹤：[Issue #1](https://github.com/peca12968/vr-command-center/issues/1)。階段完成後更新此追蹤與本地文件。

已建立管理核心、REST API、任務 JSON 範例、核心規則檢查與 GitHub Actions 工作流程。後端使用本機已有的 .NET SDK 10.0.400；尚未安裝或建立 Unity 工程。

Release 建置成功：0 警告、0 錯誤。15 項核心檢查全部通過，包含五房獨立、全館 25 人名額、併發加入限制、快照隔離、任務持久化與場次釋放。66 項 HTTP 斷言全部通過，包含實際服務啟動、JSON 往返、錯誤碼與完整名額操作。

上述測試在 Windows 本機執行。私人 GitHub 儲存庫已建立，首次提交 `f4b836a` 已推送至 `main`，遠端私有狀態與分支已確認。實際指令見根目錄 README；CI 設定使用相同建置、核心檢查及 HTTP 整合腳本。

GitHub Actions [首次執行](https://github.com/peca12968/vr-command-center/actions/runs/40720827902) 在任何 step 啟動前失敗。check-run `122930936531` 的 annotation 明確回報：最近帳戶付款失敗，或需要提高 spending limit。第二次提交的執行也於啟動前失敗。**雲端 CI 尚未驗證，不能標示通過**；未變更帳務或啟用付費執行器。本機測試仍可執行，M1 開發不受影響。

## 未完成與外部資料

- Unity 工程尚未編譯或運行；共用核心已有 .NET 驗證，管理／配置 UI 與 3D 模擬回放可操作。Unity／頭盔遊戲、硬體通訊、正式持久錄影與即時觀戰仍待整合。
- 尚未收到廠商 SDK／協議；需依 `HARDWARE.md` 取得資料。
- VIVE XR 確切型號、Android 一體機／PCVR、場館尺寸與網路架構待確認。
- 沒有頭盔或硬體實測證據；25 個玩家記錄通過不代表 25 人實際連線達標。

## 接續位置

下一主線是解決 Unity 授權與 Android 模組條款後實際匯入／編譯，接入共用戰鬥核心、任務擺設、輸入與世界同步，完成 Quest 3 雙玩家切片。管理建立／加入／離開去重、裝置準備與重連、可靠世界儲存、自由觀戰及 3D 回放仍需補齊。等待使用者操作期間可繼續不依賴 Unity 的世界資料與回放工具；雲端 CI 須等 GitHub 帳戶付款／支出限制解除。每次開始先查實際 Git／程序與最新證據，不把無頭盔模擬當成已驗證的遊戲。
