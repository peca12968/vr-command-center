# 長期開發目標

2026-11-06 Windows 伺服器啟動器 1.3 在公告之前核對原遊戲程序實際綁定的 UDP 位址和埠，並在就緒檔保留啟動時的觀察。 [部署與驗證](WINDOWS_SERVER_PACKAGE.md#本機-udp-綁定確認)

2026-11-06 控制台 0.31.10 顯示場次已接受的戰鬥筆數與錄製格數。即使來源中斷，仍可把保存片段播到固定尾端並逐格檢視。 [回放已保存片段](WORLD_RECORDING.md#回放未封存的已保存片段)

2026-11-06 控制台 0.31.9 可暫停任務回放並逐格檢視保存的戰鬥事件，從選定的快照序號續播。五房連線的 Windows 錄製中，單格與續播內容對上原封存的五筆射擊。 [逐格檢視](WORLD_RECORDING.md#暫停逐格檢視)

2026-11-06 控制台 0.31.8 可按房匯出五房連線場次的最終戰績。主控可取全場或單房，房控畫面固定為所屬房間，分房端點拒絕跨房。348 項 Windows 三包檢查通過，五份分房報表逐列對上同場 25 筆封存戰績。 [分房匯出](REPORTS.md#五房分房匯出)

2026-11-06 任務編輯器可預覽五個出生位到中線的取樣路徑。整排沙包及移開一個沙包後的開口已通過配置檢查與實際瀏覽器修訂。 [出生位通路預覽](LAYOUT.md#出生位通路預覽)

2026-11-06 五房總覽可同時查看各房名冊和有效姿態人數，並分列合成與追蹤。主控與房控的摘要範圍已通過 HTTP 驗證。 [五房總覽](PLAYER_READINESS.md#五房總覽)

2026-11-06 控制台 0.31.5 修正一個兩房操作競態。原場次在刷新時結束，待送出的暫停會停止，其他房間維持原狀。新版管理包與 309 項瀏覽器檢查通過。 [場次切換與操作](SESSION_CLOSURE.md#場次切換與操作)

2026-11-06 Windows 伺服器可按需記錄已入場玩家的實際 UDP 來源。25 筆 Linked 來源對上原入場和戰績確認，五個預設獨立房間均無來源紀錄。同源 Quest 0.41.2 APK 已建置，跨機及頭盔待驗。 [跨機來源診斷](WINDOWS_SERVER_PACKAGE.md#跨機來源診斷)

2026-11-06 三個 Windows 可攜包完成同機整合。五房獨立和五房連線模式各有 25 個模擬玩家同時入場，共 50 份戰績和 6 份 CSV 對上封存與伺服器確認回條。跨機、頭盔與 25 位真人待驗。 [三包整合驗證](WINDOWS_SERVER_PACKAGE.md#三個可攜包整合驗證)

2026-11-06 控制台 0.31.4 可按房間下載連線檔 ZIP，已驗證五房共 25 份入場票券與實際 ZIP 雙玩家入場。跨機、頭盔與 25 位真人待驗。 [整房配票](EXTERNAL_CLIENTS.md#按房間下載連線檔)

2026-11-06 控制台 0.31.3 在配票前驗證 IPv4 與埠號。管理包通過 105 項 Windows 檢查，同機雙玩家入場與封存通過 9 項。 [開發進度](PROGRESS.md)

2026-11-06 已用實際 Windows 伺服器與玩家程序完成本機乙太網路 IPv4 綁定及入場驗證，13 項檢查通過。預設 loopback 的 9 項回歸也通過。部署文件已列出第二台電腦的驗收步驟。 [外部玩家連線](EXTERNAL_CLIENTS.md)

2026-11-06 完成 Windows 玩家連線檔視窗的同機驗證。啟動器 1.1 支援直接貼上路徑，檔案變更後必須重新載入。GUI／CLI 雙玩家 9 項通過，背景雙玩家 13 項通過。跨機、頭盔及實體硬體列為後續驗收。 [玩家連線檔流程](PLAYER_CONFIG_REVIEW.md)

2026-11-02 [電腦端900秒動態長場](DESKTOP_ENDURANCE.md)：Unity0.41.1／52／242真正Editor／4ebd雙平台，Linked25端後五房各5端、18項／51601全回放／51351 Running、50原結果／6CSV／雙seal與原ACK成功，每人90發45reload／45週期。普通入場8／354亦通過；原0.41走道失敗保留，未修復舊31／371等，非真人／跨機／頭盔容量，完整11active。

2026-11-02 新版伺服器包106項／623回放與實際WinForms載入／選場／啟動／封存36秒／停止／關閉成功，首新GUI空名冊409失敗及舊PickerHost失敗均保留。詳見[伺服器包](WINDOWS_SERVER_PACKAGE.md)；以下較舊GUI待驗文字為當時歷史，完整11active。

2026-11-02 [長場生成輸入](DESKTOP_ENDURANCE.md)：Unity0.41／51／238真Editor及同源5d2e雙平台，獨立旗標每20秒兩發一換彈、最多45循環；14 Python／60秒5端597回放及原短控制7項成功。此0.41原候選後來走道失敗，原件保留；新0.41.1結果見上；原長場失效與完整11項active保持。

2026-11-02 [多人動態＋管理命令組合](DESKTOP_EXERCISE.md)：選用operator-controls，25Linked及五房各5端全員移動時套用雨夜Patrol／霧天Advance，30項／2909完整回放／50原結果6CSV雙seal ACK成功。12階段24個原UUID／expectedSequence／來源observed fence、24個精確回放參考；閉源2627 Running幀逐房環境AI時間線一致。11 Python（新4）／27 active／5artifact，預跑7／202、未選用5／179通過。沿用Unity0.40／231／6098雙平台與原包，無新Editor／遊戲重建／GUI／GPU／頭盔；完整11active，舊31／371與跨機真人等仍待。

2026-11-02 [原生多端動態驗證](DESKTOP_EXERCISE.md)：Unity0.40／code50／NGO29、231真正Editor與6098b485...同源雙平台，原Scene／prefab ID保持。明確Windows Development batch Client自動輸入走原Move／RPC，25端Linked及五房各5端18項／1951全回放／50結果CSV ACK成功；Linked154幀25位同時walking。普通8／355、server包106／725、玩家包19成功。這是短場AutomatedSimulation，原31／371未修因，完整11active。

2026-11-02 [硬體回饋離線模擬器](HARDWARE_SIMULATOR.md)：0.1.0以原事件／stream／admission規則重建，測試綁定、重送、虛擬到期與ACK，沒有設備I/O或實體停止保證。新34 Core／完整772、實際API＋.NET ArenaSession及最終38 CLI、解壓同位元結果與原錯權限輸入受控拒絕成功。API0.31／UI0.31.2／Unity0.39與原224雙平台保持；廠商SDK、實機及完整11項仍待驗。

2026-11-02 [場景物件復原／重做](PLACEMENT_HISTORY.md)：控制台0.31.2／API0.31.0，可還原新增、刪除、旋轉、數值與整段拖曳／方向鍵；只在配置圖攔截快捷鍵，儲存中鎖定、換任務／登出清紀錄。6新Node、89完整Node／296 Chromium、專項及實際解壓包各29、Windows管理包105成功；原版本不可變，Unity0.39／224雙平台保持。無新native遊戲／Editor／頭盔驗收，完整11active。

2026-11-02 [伺服器房間／任務清單](SERVER_CATALOG.md)：啟動器1.1可直接輸入管理實例路徑並更新，顯示房間、模式與任務，原UUID／版本另列；明確選取、路徑變更／失敗停用、同實例且仍存在才保留。38 CLI/API＋26真正Framework model與新版原生106／777回放／10結果CSV ACK成功；完整WinForms開場仍受PickerHost阻擋。CI41344259683／a8855cc完整success，738／459／47、83 Node／269 Chromium；1260＋47＝1307 browser證據。API0.31／console0.31.1及Unity0.39／224雙平台保持，11active。

2026-11-02 [任務收尾與End重試](SESSION_CLOSURE.md)：控制台0.31.1／API0.31.0，分開顯示戰鬥與世界封存，異源／讀取失敗不沿用綠色，沒有送達／可關閉保證。真lost-End後sealed duplicate舊篩選反例exit1、新269 Chromium／83 Node及真正UI End＋原生106／619回放／10結果CSV ACK成功；管理包105。Unity0.39／224雙平台保持，新server GUI／跨機頭盔25操作仍待，11active。

2026-11-02 [Windows遊戲伺服器包](WINDOWS_SERVER_PACKAGE.md)：沿用Unity0.39與API0.31，Framework啟動器只使用GameServer角色、Preparing VR新來源／新資料，公告endpoint、雙seal後留36秒再收自己的原程序。103項原生整合／五獨立與後Linked／553全回放／10原admission結果CSV與closed journal尾界成功；Job父程序退出另為未封存反例。GUI被非目標PickerHost攔住，未完成／failed保持；沒有新Editor／APK或跨機／25操作，完整11active。

2026-11-02 [Windows管理服務包](WINDOWS_CONTROL_PACKAGE.md)：API/UI0.31.0、自含.NET/ASP.NET Core10.0.14及繁中啟動器，獨立保存角色／票券key與任務／場次資料。105封裝檢查、6私有管線、7Python邊界、實際GUI啟停／child handle及五房回歸成功；25個管理席位不是25端連線，跨機／乾淨新機仍待。Unity0.39／224／e0d60e4e雙平台保持、無新Editor／頭盔，11項active。

2026-11-02 [電腦端蹲姿](DESKTOP_CROUCH.md)：Unity0.39／49／NGO29、API/UI0.30.2。Ctrl按住／C切換、保留移動高度與失焦恢復；224真正Editor、同源雙平台及實際C／W／視窗操作、792全回放／兩份戰績CSV雙sealACK、五房6項7場成功。Ctrl按住／放開為Editor官方Keyboard證據，原生本輪為C／W；無頭盔／跨機，11項active。

2026-11-01 [AI可見目標](AI_VISIBLE_TARGETS.md)：Unity0.38／48／NGO29、API/UI0.30.2。保持移動與原Cast／傷害／冷卻，受阻時可選後續可命中玩家；738規則／208真正Editor、同源雙平台、三人原生4項32全回放／原結果及五房6項7場成功。舊三人原生exit1及誤分類兩人／未參戰候選保留；不是25人效能或舊姿態修復，11項active。

2026-11-01 [雙擊觀戰場地定位](OBSERVER_GROUND.md)：API/UI0.30.2，保留角度距離／草稿／原書籤權限，房外不移動，回放不seek。78 Node／255 Chromium、54 UI/native與165幀回放／結果成功；Unity原0.37.2／199／同源雙平台不變。原HTTP這次459成功非舊startup根因修復，完整11項active。

2026-11-01 [非格點起終點接線](AI_NAVIGATION_ANCHORS.md)：Unity0.37.2／code47／NGO29、API/UI0.30.1；729核心／199真正Editor、同源雙平台及兩個原生4項／268與148回放通過。原生逐tick觀察保持20秒／.2m，不改10Hz世界錄製；原缺失tick不能補造，首失敗與初候選保留。一般五房6項7場成功，非25位操作或NavMesh／複雜地形完成，11項active。

2026-11-01 [敵軍繞行旋轉掩體](AI_NAVIGATION.md)：Unity0.37.1／code46／NGO29、API/UI0.30.1，格邊以既有步行通行政策核對並有界快取；723核心／189真正Editor、同源Windows／Quest及真正PC巡邏／Hold／Pause／Advance、128完整回放／113已接受來源幀通過。初次getter漏看短暫端點的exit1保留，連續串流不放寬期限／距離；不是完整三維尋路、25位操作或舊姿態根因修復，11項active。

2026-11-01 [電腦端第一人稱軍服手臂](DESKTOP_FIRST_PERSON.md)：Unity0.37.0／code45／NGO29，API/UI0.30.1不變。184真正Editor與同源雙平台建置，6張本機GPU／1195完整回放、遠端人物／Host戰績／五房重用及Linked回歸。可攜包19項核對成功，舊人物工具一次300秒操作逾時保留；尚無封裝GUI／跨機／頭盔實測。完整11項active，原31筆及world371未修復。

2026-11-01 [任務版本讀取恢復](MISSION_READ_RECOVERY.md)：API／UI0.30.1，背景傳輸／5xx失敗不連帶取消明確任務GET，401／403／登出及寫入限制保持。舊版受控503先失敗，新專項15／完整248 Chromium、72 Node、717規則／47串流及原生8項355幀成功；本機完整HTTP啟動拒絕逾時另保留，未當全部通過或前CI根因。Unity0.36.1／原179雙平台不變，完整11項active。

2026-11-01 [PC無按鍵觀察](OBSERVER_TIMING.md)：25接收端／12外部觀察，原8項52快照／26報告28237 Running、1153全回放與25份精確結果成功；983保存幀後補stationary guard讀回成功。時鐘／coverage不合為null，各point裁切聯集不相加，不把呼叫括號當GPU或因果；65 Python、版本／原179及雙平台保持，舊31筆／新371未修復，完整11項active。

2026-11-01 [控制台表單＋動態25端](DESKTOP_ACTIVE.md)：operator-ui六個真正表單命令、正確W／Space／R／Space，最終14項／182快照、21121 Running列、1132全回放／25份結果及server ack成功。但首場1271回放的world371一位參戰失效、26份複本觀察失效仍exit1；另API啟動及操作確認逾時保留。新增只server／visible的稀疏診斷，不將乾淨場或最大gap當根因修復；52 Python／72 Node，遊戲版本／179雙平台保持，完整11項active。

2026-11-01 [動態任務環境／AI命令](DESKTOP_ACTIVE.md)：選用operator-controls，雨夜實際射擊／換彈後測試Patrol／Fog Day Advance；13項、182快照／26報告、28204 Running列、1359完整回放與25份結果／server ack成功。接受回應與來源observed fence另存，原敵軍ID／健康保持；46 Python通過，Unity0.36.1／179及雙平台receipt不變。下一步操作員UI與動態玩家組合、多人持續操作，完整11項active，原31筆／慢碟／實機另驗。

2026-11-01 [CI與瀏覽器fixture](PROGRESS.md)：8d2227a雲端完整success，717規則／459 HTTP／47串流、全部Python／素材及67 Node／235 Chromium通過；原第二分頁截圖逾時仍保存。明確啟用截圖分頁、camera與時鐘中斷各用自己的60秒來源，未放寬政策；遊戲0.36.1／原179 Editor與雙平台receipt保持，11項active。

2026-11-01 [同版動態PC](DESKTOP_ACTIVE.md)：0.36.1／e059來源保持，最終10項／130快照／26報告／33256 Running列、1420全回放與25份個別結果／server ack成功；一位實際W／Space／R／Space、24接收，不是25位同時操作。新增結果閘門與57 Python；首次UI40秒確認逾時保持失敗，原31筆／F吞吐／實機另驗，11項active。

2026-11-01 [同版五獨立房長場](DESKTOP_INDEPENDENT_LONG.md)：0.36.1／e059來源保持，5 server＋25 PC、每房900秒、42341全回放／209420人次與25份原結果／各CSV／雙seal通過。Room1 tick2410停表、其餘四房前進；新獨立讀回器核對JSON／CSV，17新反例及共60 Python通過，無新Editor／雙平台重建。下一步動態PC；原31筆／F吞吐／實機另驗，完整11項active。

2026-11-01 [戰績尾界](DEBRIEF_BOUNDARY.md)：Unity0.36.1／code44、179 Editor與e0594513...雙平台成功。原0.36真正25端900秒場在結果核對exit1，一份8441／實際Ended封存8442，完整失敗保存；pending改綁terminal capture、final仍另核對durable seal。三個原生短場12項／六份結果成功，長場完整驗證見PROGRESS；不把ack／live乾淨當整場接受，完整11項active，原31筆／慢碟／實機另驗。

2026-11-01 [背景世界writer](ASYNC_WORLD_WRITER.md)：Unity0.36／code43、177 Editor與7194dc98...雙平台成功，API/UI0.30／NGO29不變。主線世界幀IO／狀態讀鎖移出，32幀／8MiB bounded queue不冒充durable；F本場Main world GateEnter／Flush皆0但224未確認，仍不通過。SSD8項354幀、一般8項400幀及故障恢復8項743全回放成功；717／459／47、48 Python與19 launcher成功。下一步發布吞吐／SSD部署及長壓，不關durability／跳幀；完整11項active，實機／31筆另驗。

2026-11-01 [journal細分](JOURNAL_STAGES.md)：Unity0.35／code42、169真正Editor與d30cc34c...同源Windows／ARM64 APK成功，API/UI0.30／NGO29保持。最終F有128未確認，Main Frame Flush8.814804秒、Main gate等待3.134420秒（多為CompleteState讀取）、與背景ack flush交集3.133609秒；SSD8項355幀seal／一般8項363幀成功。717規則／459 HTTP／47串流、47 Python／19啟動器與原件保持核對通過。下一步評估保持durability的writer／明確SSD部署，不稱單一硬碟或31筆全局修復；完整11項active。

2026-10-31 [發布區段計時](PUBLICATION_TIMING.md)以原播放器既有trace再次重現F負載逾時，15.243秒窗口的主執行緒WorldJournal聯集9.379684秒、129幀未確認；C SSD同帶trace重疊場8項／354幀seal成功。37 Python及原件保持核對成功，版本／Unity建置不變。區段含鎖／JSON／flush而非單獨fsync，下一步分離frame／背景ack等待與寫入成本、保持durability；完整11項active，原31筆／實機另驗。

2026-10-31 [原入場窗口與journal](STARTUP_WITNESS.md)重現F資料＋真正封裝重疊的Preparing逾時：Begin接受7，來源world137有效Running，live仍Preparing且106幀未確認；明確C SSD同情境8項／358幀與seal成功。新增有界witness、唯讀checksum／序號分析與選用runtime-root，23項Python含Windows lease通過，原Unity／API不變。已定位該場發布積壓，尚未證明所有舊逾時／31筆根因；下一步量測發布階段與多人操作，完整11項active。

2026-10-31 新增[開場接受／套用觀察](STARTUP_WITNESS.md)：3直接＋1受控管理失聯場、八份結果／96完整回放與雙seal成功；HTTP接受與來源Running按序號／tick／suspended分開，4項反例通過。版本及原建置不變。舊逾時缺命令回應，新場無原撤銷／F負載條件，根因仍未證明；接續原情境窗口，完整11項active。

2026-10-31 新增[Quest右B重連](QUEST_RECONNECT.md)：Android原略過桌面重連按鈕，現可明確放開再按B重讀原票券，角色／冷卻／焦點／追蹤及暫停解除沿用原驗票。163真正Editor含3項PlayMode Dynamic官方Touch action、同源Windows／ARM64 APK成功，0.34／code41、NGO29／API UI0.30；最終PC8項372幀通過。五輪測試失敗與Running逾時保存，未稱根因已修復；實機控制器／GUI／跨機另驗，完整11項active。

2026-10-31 新增[玩家入場狀態](PLAYER_CONNECTION_STATUS.md)：Windows啟動器從自己遊戲回報區分入場／拒絕／30秒未確認與Final保留，無網路探測／自動配票；17真正Framework類別、19原生啟動器拒絕及13項雙PC／拒絕／無GameServer整合通過。新版0.33玩家ZIP成功，Unity／API及原建置保持。GUI操作、跨機／頭盔及原31筆根因另驗，完整11項active；接續可操作PC流程及跨機部署。

2026-10-31 新增[五房獨立長任務](DESKTOP_INDEPENDENT_LONG.md)：5 server＋25 client、各900秒，房1實際Pause3.265秒而其他四房前進；各自tick18000、25份結果／五份CSV／雙seal與42293完整回放一致，209235人次無失效。32項Python、原件／快照保存核對成功，版本及原Unity建置保持。這是同機靜止Simulation，原31筆Linked反例未修復、跨機／25台／頭盔另驗；接續多人持續操作與自然失效定位，完整11項active。

2026-10-31 新增[同源未啟用診斷對照／跨場比較](CONTINUITY_COMPARISON.md)：25個PC原程序900秒、8475完整回放／8412 Running／210300人次與25份結果／CSV／雙seal成功。相同c98f1來源的稀疏及未啟用兩場均未重現；舊2幀31筆失效仍未通過，根因／修復未證明。27項Python檢查通過，Unity／API與原建置保持。下一步取得自然失效窗口及因果證據，並接續多玩家操作／五獨立房長任務，跨機／實機另驗；完整11項active。

2026-10-31 新增[長任務稀疏診斷](POSE_CONTINUITY.md)：Unity0.33／code40、152真正Editor與同源雙平台，受控校準及一般8項入場回歸成功；25端新場900秒、8449全回放與26完整報告乾淨。原31筆失效與初次解析／建置失敗保持，根因仍未證明。下一步以新工具取自然失效窗口並與未啟用對照，不能把乾淨一次當修復；完整11項active、實機／跨機另驗。

2026-10-31 新增[五房25程序15分鐘](DESKTOP_MULTIPLAYER_LONG.md)：25原入場／票券到期後延續、唯一tick18000及25份結果／CSV／精確雙seal一致，8463全回放完整；但2幀13／18位、共31筆body失效，acceptancePassed=false且工具exit1，未宣稱容量或根因修復。新11 Python含此恢復反例。下一步定位497ms擷取間隔附近的姿態送出／接收及主迴圈工作；完整11項保持active，實機／跨機分開驗收。

2026-10-31 新增[Windows可攜玩家包](WINDOWS_PLAYER_PACKAGE.md)：繁中選檔啟動器及真正runtime封裝，最終解壓包雙PC背景流程9項及原生拒絕15項通過。API/UI0.30、Unity0.32／NGO29與144 Editor／雙平台為原證據，本輪未重建。互動GUI受Windows安全性提示阻擋，人工確認、跨機及頭盔分開驗收；下一步仍是多玩家持續操作與場館／跨機，完整11項active。

2026-10-31 新增[外部玩家模式](EXTERNAL_CLIENTS.md)：操作員工具只開server，不占用名冊入場；來源公告地址／port與控制台下載接通，真正兩個分開啟動PC入場／End／雙seal及loopback socket已驗。API/UI0.30、Unity0.32.0／code39／NGO29、144真正EditMode及同源雙平台成功，原模式49項回歸通過。這是同機外部程序流程，非跨機／頭盔／25台；下一步實際多玩家操作、場館與跨機部署，完整11項保持active。

2026-10-31 新增[玩家參戰快照](PLAYER_READINESS.md)：API/UI0.29在名冊直接顯示來源／姿態有效數，核對已接受世界與本次admission，不把名冊分類當連線。698規則、453 HTTP／43串流、64 Node／229 Chromium及真正雙PC的8原生＋8 UI通過，已關閉peer／同ID換入場／新端恢復／Begin-Pause-End／雙seal；Unity與原雙平台不變，本輪未重建。完整目標active；接續多玩家持續操作、場館流程與跨機，頭盔／25台另驗。

2026-10-31 新增[玩家任務簡報](PLAYER_BRIEFING.md)：原保存任務名稱／10000字內容送到GameServer及玩家，繁中隨附字型、分頁及本機武器抑制；真正雙PC原生B／Space／Escape／L、晚連線、姿態持續與雙seal結果通過。Unity0.31.0／code38／NGO29、141真正EditMode，雙平台最終receipt見PROGRESS；API/UI0.28及規則／錄影格式保持。完整目標active，頭盔控制器與舒適度、25台／跨機仍待。下一步接續多玩家操作與完整場館流程，實機分開驗收。

2026-10-31 [15分鐘PC任務](DESKTOP_LONG.md)通過8475幀完整回放、8460個Running幀無失效body，原入場跨票券到期、健康80及tick18000／雙seal／結果一致；另[封存失聯](SEAL_RECOVERY.md)兩模式各8項通過，49 Python。仍是單玩家同機Simulation，不能外推4小時／25位／實機；遊戲版本與原雙平台receipt保持，本輪未重建。下一步多玩家持續操作與更長／封存期限情境。

2026-10-31 [計時分通道恢復](CLOCK_RECOVERY.md)新增兩場真正PC、60／180秒各8項：管理失聯停表／原政策接續，發布失聯本地到期不提前End、恢復後唯一End／雙seal／個別結果及整段回放一致。44 Python通過；遊戲仍0.30.0／code37／NGO28，前輪131 Editor及雙平台保留、本輪未重建。180秒不是長期穩定性或實機驗收，下一步更長任務與封存失聯。

2026-10-31 新增[選用任務活動倒數](MISSION_CLOCK.md)：Preparing明確選用、Pause停表、權威到期凍結與API正常End／雙seal。兩個真正PC房間驗證自動tick1200及手動超時，131真正EditMode、同源Windows／Quest、680規則／446 HTTP／43串流／60 Node／223瀏覽器及13項native錄製觀戰通過；仍是Simulation，實機與25台驗收未完成。下一步為管理／發布失聯與長任務，完整11項保持開發中。

2026-10-28 依使用者要求建立，狀態：**開發中**。完整範圍維持原始 11 項需求及 VIVE XR／Quest 3 相容性。各階段完成不代表整個目標完成；有外部依賴時持續推進可獨立驗證工作。

2026-10-29 使用者指定「先用 META QUEST 3」：M2 先交付 Quest 3 垂直切片，暫按 Android 獨立執行規劃；VIVE 的確切型號與接入移至後續相容階段。

2026-10-31 新增[玩家End戰績](DESKTOP_DEBRIEF.md)：兩份journal精確seal後target送出自己的結果，ack斷線仍保留，Host等其他收件人結束才shutdown；移除／換席與Ended入場維持拒絕。真正Space、等待／最終／斷線保留／Reconnect清除與8項原生重連通過，125真正EditMode。此為同機PC Simulation流程，實機、25人持續操作、跨機及故障情境仍待，整體目標保持開發中。

2026-10-31 PC穩定性新證據：外部唯讀取樣在共同loop0.594546秒空窗內，取得三程序CPU時間／cycles增加，且11對相鄰查詢每對均有cycles進展；另一場零時間計數不證明暫停。43 Python與兩場真正三發／精確封存通過，Unity0.28.1／code33／109 EditMode及雙平台為前輪已驗、本輪來源／binary不變。下一步辨識主執行緒與主迴圈外工作／等待，不將全程序CPU當main-thread CPU、不放寬0.5／1.5秒政策。詳見[POSE_TIMING](POSE_TIMING.md)及PROGRESS，非實機／25台驗收。

| 階段 | 交付 | 通過條件 | 目前狀態 |
|---|---|---|---|
| M0 專案與管理核心 | F 槽原始碼、私人 GitHub、需求追蹤、五房場次與任務 API、CI | 可重現建置、核心與 HTTP 驗證、推送成功 | 2026-11-06 已推送 Windows UDP 綁定核對，本機 38 項 CLI 及 33 項 Framework 檢查通過。前輪完整 Windows HTTP 回歸在啟動和程序測試中止。最新 CI 42108137984 因帳務條件未啟動。最近成功為 2026-11-02 CI41368791791（e963e48），涵蓋 Linux 建置、772 核心、459 HTTP、47 串流、6 私有管線、38 硬體離線 CLI、Python、素材及 89 Node、296 Chromium。 |
| M1 場次控制與事件基礎 | 主控／房間權限、準備／開始／暫停／結束狀態、命令與事件、統計核心 | 五房隔離、權限、去重、狀態遷移、紀錄恢復測試 | 管理／統計核心、SQLite 追加、JSON 升級與模擬來源已驗證；建立／加入／離開可持久去重，v2 票券與移除／配票按每次 admission fence；API／SQLite／瀏覽器已驗證；真正 Windows 撤銷／重連已通過；新增 SSD runtime 下五個原生獨立世界、每房一個 client 的權限／命令隔離、單房 End／重用，以及全部封存後新開 Linked |
| M2 Quest 3 優先的遊戲垂直切片 | Unity 工程、Quest Android profile、基本移動／互動與共同場景；再接入 VIVE | Quest 3 實機操作及雙玩家互見；之後驗證混合頭盔、校正與定位 | 真正 Editor 已通過 UPM／ILPP／資產匯入、242 項 Editor、0.41.2 Windows 與 ARM64／IL2CPP Quest APK。兩平台來源指紋與網路識別一致。無頭盔，依使用者指示先繼續 PC。雙 Quest 操作與混合裝置待驗 |
| M3 軍事戰鬥與 AI | 武器、傷害、健康、敵軍尋路／攻擊、操作員覆寫、HUD | 伺服器判定一致、AI 可控、事件與統計相符 | Windows server 加兩個 desktop client 已通過獨立／跨房 Simulation AI 傷害、暫停、封存及回放統計；真正視窗已完成方向鍵／Space／滑鼠射擊、擊殺／命中率、換彈及暫停；控制台自訂任務／動態名冊及 Advance／autoAttack 到真正 native 傷害、Pause／Resume／End 已通過；新增軍事HUD／方位／遮擋標記、自製沙包／油桶及不可變素材版本，真正鍵盤與受傷／淘汰已驗；新增固定玩家步槍、保存朝向／步態的人形敵軍及保存時鐘的換彈／合成手套及原創雙手手槍／裝飾性雙臂、保存射線的玩家及敵軍閃光／後座、原生視窗兩發命中／一擊殺與封存統計；新增404面玩家人物、保存步態及桌面腕點／換彈雙臂，真正雙PC GPU／W／Space／R已驗，另有原生C蹲姿掩體／焦點恢復及792完整回放；完整第一人稱／追蹤人物及武器動畫、啟動旗標／原停頓原因、完整策略、追蹤及實機戰鬥待驗 |
| M4 任務與場景編輯 | 任務視覺編輯器、版本、物件擺設、天氣／日夜／雷電即時控制 | 儲存重載一致、獨立／全館環境正確同步 | 任務版本、2D 配置及環境／AI 控制已有核心／HTTP／瀏覽器證據；新增物件復原／重做及整段手勢、不可變版本保存驗證；Unity 場景／音訊／Shader 匯入與 Storm／Night PC 任務運行通過。已實際以 UI 保存／重載擺設並在 Unity GPU 看見配置、白天／雨夜／Pause；原生新沙包／45° 油桶阻擋、退回／側移已通過；配置圖顯示真實平面包圍盒；新增旋轉越界／重疊／五席出生空間及初始敵軍容量檢查，保存草稿與新開場政策分離，複雜通路／地形仍待；原生GPU閃電與自身DSP雨雷／靜音已量測；聽感／實體輸出、MR校正及頭盔待驗 |
| M5 觀戰、回放與報表 | 自由／跟隨鏡頭、書籤、快照與事件回放、逐玩家統計 | 即時觀戰、跳轉倍速、回放與結束統計一致 | 持久世界、SSE／回放、書籤及統計已有核心／瀏覽器證據；新增已結束且戰鬥精確封存的逐玩家CSV匯出，保留離場者／來源／原任務及尾界；真正 PC 發布／封存及控制台俯視、鏡頭保存／跟隨後讀回、倍速／末幀回放已驗證；SSD 最新五房最大來源年齡0.200379秒、自訂任務0.308984秒。觀戰瀏覽器為軟體 WebGL；已新增精確座標／度數／距離與原生錄製自訂視角保存／封存回放45項整合（含素材版本）；真實GPU／長任務手感、實際頭手及25台待驗 |
| M6 硬體與場館驗收 | 廠商轉接器、MR 場地、斷線恢復、25 人完整任務 | 混合頭盔與實體硬體完整任務、效能紀錄、部署手冊 | PC 同 admission 斷線恢復已有證據；新增25原生客戶端的短自動化移動／射擊／換彈，非25位真人或跨機容量；新增硬體回饋離線模擬與原admission／錯ACK／虛擬期限驗證，無設備I/O；管理API可攜包含執行環境、105封裝檢查及真正GUI啟停／資料重開已驗；遊戲server已有可攜CLI與同機驗證，完整server GUI、跨機／崩潰恢復、MR、硬體與25台仍待 |

## 下一個開發順序

新增[End期間封包故障](DESKTOP_END_NETWORK.md)：現有0.29.0在已approved但client未完成連線log的延遲仍送達正確結果，沒有據假設改遊戲端；另驗pending後全下行loss與>64-byte篩選loss的connection release／應用期限，三場各6項／37幀完整回放、45 Python及原件副本SHA一致。這是兩位同機Simulation，仍需封存中斷／server crash、更多時序、長任務與跨機，完整11項未縮減。

最新[動態操作25端對照](DESKTOP_ACTIVE.md)補入一位PC實際W／Space／R／Space、24端接收與兩發命中／一擊殺／100%。首fan-out場130快照成功卻有65筆失效Running列，新增全程條件後保留反例；分批場9項、130快照／19916 Running列、966幀回放與CSV通過，無probe權威對照9項亦通過。這不是根因證明或25位同時操作；後續擴大多位操作、更多場景與長任務，並繼續釐清原姿態／主迴圈停頓、診斷與GUI觀察的擾動。

最新[接收端25程序檢查](DESKTOP_REPLICATION.md)已補每client／server五檢查點及穩定新tick觀察，原driver128重現Running／Paused共112行queue錯誤；0.28.3 server1024／client128後，兩模式各25 client／60秒、22項、56份完整報告與280個同步快照皆通過，日誌0錯誤；無探針25人對照8項亦0。114真正EditMode、同源雙平台及8項原生入場／重連通過，534／14檔SSD與F SHA一致。下一步用實際移動／射擊、更多場景與長任務驗證25端同步，再推進跨機；不把本地tick觀察間隔或來源新鮮度當網路延遲，原偶發主迴圈停頓仍待，完整容量／頭盔驗收尚未完成。

最新[當前版本時序](POSE_TIMING.md)已在該觀察空窗內取得全程序CPU／cycles進展，不能一概解釋成三程序全程停止；仍未知主執行緒／其他worker的實際工作與等待。診斷與外部工具擾動尚未排除，接續識別main thread及主迴圈外區段，不放寬門檻，不稱修復。

最新[電腦練習場](DESKTOP.md)修復已拒絕目前API的舊0.21 gate，改共用現有0.27來源／admission／精確seal，支援SSD runtime及自動核對CSV。27項無圖形／9項真正W／Space／R與關窗、6項前置／非預期關閉反例、49項既有控制台／native回歸通過；沒有重跑前輪後端／Unity／APK，也不當作頭盔／25台／跨機證據。

最新 API／UI0.27 新增[最終報表 CSV](REPORTS.md)，654 核心／446 HTTP／43 世界／58 Node／217 Chromium，49項真正 Windows 程序資料的 UI／native 整合通過。Unity0.28來源與既有雙平台binary未變，本輪未重跑102 EditMode／APK。報表完整性依戰鬥精確seal，世界錄影完整性分開驗收；完整11項仍開發中。

1. 使用者目前無頭盔，玩家／敵軍射擊音效與PC DSP已完成，接續完整第一人稱／追蹤人物、動畫／聲學、複雜通路／地形、自由鏡頭／長任務操作及跨機部署；原生GPU閃電及DSP已有證據，聽感／實體輸出仍待驗。控制台自訂任務、保存重載配置到真正 PC、天氣／AI／名冊／觀戰及回放已接通，見 DESKTOP_CONTROL；五房與跨機範圍仍分開。
2. 擴大跨機網路、異常中斷及補送驗收，維持 admission fence、防瞬移與 Simulation。避免分平台重建場景，Prepare、231 Tests、Desktop／Quest 已有真正成功結果；嵌入 Transport 修正須保留來源雜湊與原生回歸。
3. 取得 Quest 後驗證控制器／追蹤中斷、雙玩家互見、聲光／效能與封存；之後進行 MR、VIVE、廠商硬體及 5／10／25 人分階段驗收。合成姿態維持 Simulation。
4. GitHub 完整 CI 已恢復，精確來源的成功與失敗見 PROGRESS；每次讀取當前執行狀態，保留 log／artifact 及失敗證據，不以 Linux 雲端取代 Windows、Unity 或實機驗收。

管理介面在 `/console/`；完整結果見 [DESKTOP_CONTROL.md](DESKTOP_CONTROL.md)、[DESKTOP_VENUE.md](DESKTOP_VENUE.md)、[DESKTOP.md](DESKTOP.md)、[RECONNECT.md](RECONNECT.md)、[TRANSPORT_PATCH.md](TRANSPORT_PATCH.md) 及 PROGRESS。五房新工具完成七場獨立／重用／Linked 驗證；一般視窗關閉後五場共 4037 幀封存。程式碼與 binary 仍在 F，成功配置明確使用 SSD runtime；F USB 全資料未達 1.5 秒門檻。上一輪 29 項真正 EditMode、無圖形／視窗各八項 admission 檢查、獨立／Linked 回歸及 Windows／Quest 同源建置成功。視窗場強制離線後保留走離出生點 0.65 公尺的位置與健康／彈藥，1648 幀封存且回放一致。API 0.16／場次 envelope 6／世界 schema 1 保持；Unity v0.18／NGO 18 需全體遊戲程序同版。本輪控制台自訂任務新增 15 項 UI／native 與 17 Node＋122 Chromium，並回歸五房；未混算歷史 .NET 規則／29 EditMode，頭盔／25 台待驗，編譯並行曾超過快照門檻，不宣稱所有負載達標。

最新 v0.18 已完成 [DESKTOP_COLLISION.md](DESKTOP_COLLISION.md) 的真正鍵盤沙包阻擋、退回、側移及旋轉油桶阻擋；34 項 EditMode、485 核心、369 HTTP、43 世界串流及同源 Windows／Quest 建置通過。新 binary 另通過七場五房／Linked、8 項重連及 15 項 UI／native 回歸；證據與限制見 PROGRESS。桌面移動預測不搬動 Tracked XR，也不完成複雜地形／物理場地驗收。

不先承諾日程與成本；取得團隊規模、素材來源、頭盔型號、場地與協議後才能估算。每次交付更新 `PROGRESS.md`，有可驗證成果再更新本表。

最新操作員鏡頭見 [OBSERVER_CAMERA.md](OBSERVER_CAMERA.md)：17 Node／140 Chromium，真正 Windows 遊戲錄製33項整合；數值草稿不被即時快照覆蓋，已有無效值／登出／換場與保存回放驗證，仍不是頭盔或完整人工手感。

原生聲光量測見 [NATIVE_WEATHER.md](NATIVE_WEATHER.md)：v0.19.1再次通過GPU／DSP／穩定靜音，275幀、來源年齡最高0.160839秒；原v0.18.1／code19／34 EditMode及一般可見玩家33項為歷史結果。此為開發診斷，非任務原始音軌、聽感或頭盔驗收。

最新軍事HUD見 [TACTICAL_HUD.md](TACTICAL_HUD.md)：v0.19.1／Android code21／NGO仍18，42真正EditMode、同源雙平台與原生鍵盤／GPU操作通過；一般33項整合為v0.19的歷史結果，本輪未重跑。原圖與世界保存間隔已唯讀核對；新增三次真正loopback封包中斷及不讀GPU／PCM的逐繪製轉換，逾時顯示STALE並恢復同admission射擊。這不解決原停頓原因；啟動旗標短暫警告、3D素材、跨機／實機仍待。

最新場景素材見 [FIELD_PROPS.md](FIELD_PROPS.md)：API／UI0.17、Unity0.20／NGO19／Android code22，46 EditMode、489核心／369 HTTP／43世界、23 Node／142 Chromium與35項UI／native通過。真正PC模型、鍵盤掩體與聲光已驗證，七場五房／Linked及8項無圖形入場／重連回歸亦通過。v1幾何與配色pin固定，舊錄製保留方盒；新外觀仍採粗略包圍盒，原停頓原因、人物／武器與實機仍待。配置檢查新進度見 LAYOUT／PROGRESS。

最新 [VR配置檢查](LAYOUT.md)：API／UI0.18、Unity0.20.1／code23／NGO仍19，51真正EditMode、510核心／403 HTTP／43世界、23 Node／158 Chromium及37項UI／native通過。草稿可保存，無效新VR開場由後端拒絕，歷史／已接受重試不改；MR、完整通路及實體校正不適用。最新binary與PC回歸以PROGRESS為準。

最新 [玩家步槍](SERVICE_RIFLE.md)：API／UI0.19、Unity0.21／code24／NGO20，56真正EditMode、512核心／403 HTTP／43世界、27 Node／162 Chromium及39項UI／native通過。真正鍵盤瞄準／兩發命中／擊殺、GPU日夜／Pause、五房及無圖形重連均已驗證；保持舊素材／回放，完整人物／動畫、頭盔及25台仍待。

最新 [人形敵軍](ENEMY_PRESENTATION.md)：API／UI0.20、Unity0.22／code25／NGO21，61真正EditMode、534核心／403 HTTP／43世界、32 Node／167 Chromium及42項UI／native通過。原生Patrol／Pause非零步態、保存朝向、封存回放與兩發命中／擊殺已驗，五房與無圖形重連亦通過；NPC武器、玩家人物、完整動畫／人群避讓、頭盔與25台仍待。

最新 [換彈與合成手套](WEAPON_ACTIONS.md)：API／UI0.21、Unity0.23／code26／NGO22，66真正EditMode、548核心／403 HTTP／43世界、37 Node／173 Chromium；實際Space／R／換彈中Pause／Resume／封存及5項真正原生錄製觀戰已驗，42項無圖形UI／native、七場五房與8項無圖形重連通過。手套限Simulated，Tracked不搬動資料；頭盔、完整人物／NPC武器、動畫／音效及25台仍待。

最新 [敵軍雙手持槍](ARMED_ENEMIES.md)：API／UI0.22、Unity0.24／code27／NGO仍22，70真正EditMode、555核心／403 HTTP／43世界、41 Node／179 Chromium及44項UI／native通過。原生GPU持槍、AI損耗40／兩次中彈／健康60、巡邏Pause及封存肘腕／槍口矩陣一致；五房七場與8項無圖形入場重連亦通過，Windows／Quest來源與識別一致。閃光／後座、完整人物／動畫、頭盔與25台仍待。

最新 [敵軍閃光與槍身後座](ENEMY_FIRE.md)：API／UI0.23、Unity0.25／code28／NGO23，76真正EditMode、575核心／403 HTTP／43世界、45 Node／184 Chromium及45項UI／native通過。另4項真正AI／GPU流程，日夜脈衝與兩次接受射線在SQLite按float32精確核對，耗彈0／中彈2／損耗40／健康60；診斷明確停止收集後獨立精確seal。五房七場及8項無圖形入場重連、Windows／Quest同源及原識別保持。實際暫停發生於效果歸零，峰值暫停由共用規則／Unity測試證明；玩家效果／音效、完整人物、頭盔與25台仍待。

最新 [玩家閃光與槍身後座](PLAYER_FIRE.md)：API／UI0.24、Unity0.26／code29／NGO24，82真正EditMode、597核心／403 HTTP／43世界、49 Node／189 Chromium及45項UI／native通過。另4項真正Space日夜／Right／GPU流程，兩次22mm後座、世界射線與SQLite接受事件float32精確相符；耗彈2、健康100、回放精確seal。五房七場及8項無圖形重連通過；同源雙平台以最新PROGRESS為準。保持pointer／根槍口／Tracked資料與舊七profile，沒有音效；全身人物／完整動畫、原暫時失聯原因、跨機、頭盔／MR／硬體與25台仍待。

最新 [姿態時序診斷](POSE_TIMING.md)：Unity0.26.1／code30，API／UI0.24與NGO24不變，87真正EditMode及3項Python反例通過。明確選用才啟用32768列／240秒記憶體trace，分RPC呼叫／收件、主線程及journal／GPU讀回耗時；自然60秒沒有發布失聯，受控丟包時玩家仍呼叫、server出現1.222秒收件空窗，原政策及同admission恢復已驗。沒有將乾淨基線當作舊偶發原因或修復證據；五房七場與8項無圖形重連通過，最終雙平台以PROGRESS為準。

最新 [射擊音效](COMBAT_AUDIO.md)：API／UI0.25、Unity0.27／code31／NGO25，93真正EditMode、612核心／403 HTTP／43世界／53 Node／196 Chromium及45項UI／native通過。另4項真正Space／AI／自身PCM流程，玩家1發／NPC2發與保存事件／槍口一致，26.816秒混音非零，基線／Pause／無新發Resume峰值0，原傷害及精確seal不改。七場五房與8項無圖形重連、Windows／Quest同源及原網路識別均通過；舊header0／八個舊外觀保留。人工聽感／實體輸出、完整聲學、玩家全身與原偶發姿態原因仍待，無頭盔或25台證據。

最新 [玩家軍事人物](PLAYER_BODY.md)：API／UI0.26、Unity0.28／code32／NGO26，102真正EditMode、629核心／403 HTTP／43世界／58 Node／201 Chromium及47項UI／native通過。404面原創人物、接受移動與保存tick步態、桌面腕點／換彈雙臂已接PC及觀戰回放，真正雙PC W／Space／R與六張GPU、精確seal已驗；端點／來源時鐘與原資料比對範圍見PROGRESS。最終Windows／Quest同源及原網路識別一致，舊八profile及Tracked資料保持；完整第一人稱、實際腰腳／手指、地形IK／動畫、跨機、頭盔與25台仍待。
