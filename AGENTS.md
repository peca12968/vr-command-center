# 開發指引

Windows可攜玩家包v1見docs/WINDOWS_PLAYER_PACKAGE.md：不改API/UI0.30或Unity0.32／NGO29來源，封裝真正receipt與原runtime，以Framework compiler產生獨立繁中啟動器；不含票券／server config／DB／journal。source fingerprint與原場景ID保持，無新Unity重建證據。檔案manifest是雜湊清單，不是簽章。最終背景雙PC9項含cleanup、原生拒絕15項；GUI安全性提示由使用者自行處理，不得自動操作或把受阻流程稱完整通過。檢查器須將signalCode列入terminal並在全部cleanup成功後才寫checks.json complete；細節與未完成輪次見PROGRESS。

2026-10-31 外部玩家流程見docs/EXTERNAL_CLIENTS.md：API/UI0.30、Unity0.32.0／code39／NGO29，144真正EditMode及同源雙平台成功，717規則／459 HTTP／47串流／67 Node／234 Chromium。connection-endpoint v1只由已附掛stream且有world header的GameServer owner公布，Master／可讀Room讀取，顯式Actor、場次／stream／owner fence、IPv4 canonical unicast及port1024..65535；接受後immutable，Ended metadata不授權配票／重開。worlds.db新增connection_endpoints，原header／envelope7／schema1／rules0.8.0及素材pin保持。Unity listenAddress真正傳UTP第三參數，缺失仍舊Any；新工具明確loopback，不能用忽略欄位的舊server冒充。external不自動claim／領票／開client，headsets及allAcknowledged未知null，server至少36秒非阻塞保留，不把空集合當送達。控制台手動地址保留、選擇／登入／stream fence，兩邊都缺stream不可當相符。兩次同機外部PC各8項、49 local回歸、42檔新runtime與前345檔SHA一致；真正UDP127綁定已核對，非LAN／頭盔／25台，完整目標active。原識別及雙平台fingerprint4f117...3b852保持，詳見PROGRESS。

2026-10-31 API/UI0.29新增docs/PLAYER_READINESS.md：readiness v1唯讀端點限Master／可讀房間控制台，HTTP必傳Actor；用最後已接受幀的Observed名冊比對當前admission／room／seat，不能拿同ID舊身體／名冊分類當在線。來源年齡仍header擷取UTC＋elapsed，unknown／超前／過期／suspended／phase pending／Ended不得綠色；前端從request開始計單調經過、登入／場次／序號／admission fence，不能用到達時間重設年齡。沒有新增Begin閘門或更動姿態／命中規則；只回狀態，不走REST送頭手座標。Unity0.31.0／code38／NGO29及213b...4777c原雙平台receipt保持，本輪未重建141 Editor。698規則／453 HTTP／43串流／64 Node／229 Chromium及真正雙headless PC的8原生＋8 UI檢查通過，仍無頭盔／25台。工具只自己的新runtime，全停writer再一次snapshot，保存SQLite不開；具體失敗／SHA／限制見PROGRESS。

2026-10-31 玩家任務簡報見docs/PLAYER_BRIEFING.md：Unity0.31.0／code38／NGO29、API/UI0.28，Tests門檻141；Prepare原位升29與原ID保持，雙平台最終證據見PROGRESS。BriefingHeader1＋最多80個FixedString512塊保存100字名／10000 UTF16內容，完整長度／SHA驗證後才顯示，不能截斷或用部分metadata當完成；管理更新及晚加入不得重設同一讀頁。本地B/X下一頁、Esc/Y關閉、L/左握柄授權，閱讀抑制射擊／換彈並要求放開再按，姿態繼續、不改Tracked資料／全場Pause／rules0.8.0。mission-fonts-v1官方Noto／OFL／NOTICE pin固定，OTF/TXT/meta納入fingerprint；改字型需新profile，不能改舊pin。頁碼／開關非world錄影欄位。原生check-desktop-briefing只新自有runtime，實際鍵盤／GPU觀察後才done，probe仍240秒／64次；無頭盔／25台，完整目標active。

2026-10-31 長任務／封存規範見 docs/DESKTOP_LONG.md、docs/SEAL_RECOVERY.md：本輪Python／文件／CI，API/UI0.28、Unity0.30.0／code37／NGO28及d430...de53f原receipt保持，未重建131 Editor／雙平台。單PC900秒、8475全回放／8460 Running無bad，原admission跨票券到期／健康80／唯一tick18000End；live跳1序號已完整replay補查，0.363945秒為收到資料時年齡、681ms為保存擷取間隔，非RTT／render／25人或歷史停頓修復。封存503與最終stats503各8秒保持pending後恢復，CSV依Ended+combat seal，玩家final另等world seal及GameServer統計，不可混同兩者。代理新增兩mode仍20秒／240秒／handler join，不記payload不注入；49 Python。新3runtime42檔及舊187檔SHA一致，保存SQLite不開；所有writer停後一次snapshot。完整目標active、頭盔／25台仍待。

2026-10-31 計時失聯規範見 docs/CLOCK_RECOVERY.md：本輪僅Python／文件／CI，遊戲API/UI0.28、Unity0.30.0／code37／NGO28及d430...de53f原receipt不變，未重跑131 Editor／雙平台。60／180秒各8項真正PC：只切管理GET應source suspended／Paused停表但API仍Running；只切world發布應本地精確到期Ready=false、API在接受幀前仍Running，恢復才唯一內部End／雙seal。工具只作用於新自有API，opaque WS不讀payload；8連線、20秒fault／240秒life自動上限不得passed，probe保持240秒／64 captures。完整回放、client原admission結果、tool fingerprint及writer全停snapshot均須核對；新4runtime159檔及前輪28檔SHA一致。44 Python、無新GPU／頭盔／25台／長期驗收；原正式5080不動。

2026-10-31 最新任務計時見 docs/MISSION_CLOCK.md：API／UI0.28、Unity0.30.0／code37／NGO28，131真正EditMode及同源雙平台成功。SetMissionClock僅Preparing明確選用，舊／未設定場次手動；20Hz活動tick、Pause停表，到期先凍結戰鬥，再由API已接受世界幀以內部mission-clock提交正常End／雙seal，不能拿未發布本地時間授權End或給HTTP Internal身分。envelope7讀1–7，world schema1／rules0.8.0／驗票2保持，新寫入不可降舊reader，所有遊戲程序與API/UI協同更新。兩房PC到期／手動超時、結果與回放證據以PROGRESS為準，仍無頭盔／25台；Tests門檻131。

2026-10-31 End封包故障見docs/DESKTOP_END_NETWORK.md：本輪Python／CI／文件，遊戲仍0.29.0／code36／NGO27／API UI0.27及a97b...e9d3、原receipt／ID不變，未重建／重跑125 EditMode／雙平台。剛approved、client未記CONNECTED就End的延遲實測仍能收到正確結果，不能臆測丟失而改NGO／Avatar身分。新增單client loopback gate（不讀內容／不存payload、不注入RPC或姿態），join-delay／全部下行drop／只丟>64-byte三場各6項及37幀完整回放通過；後兩者分別connection release與應用DEBRIEF_TIMEOUT，不混稱傳輸根因或RTT。delay1024包／2MiB／8秒、drop40秒、worker90秒有界，自動上限觸發不可passed；來源tool fingerprint及gate停止／writer全停／snapshot亦須成功。45 Python（9 UDP＋36 desktop），10個新runtime140檔及前20份manifest SHA一致；失敗與舊scope保留，見PROGRESS。無GPU／頭盔／25台／跨機證據，完整目標active。

2026-10-31 玩家End戰績見docs/DESKTOP_DEBRIEF.md：Unity0.29.0／code36／NGO27、API UI0.27，真正125 EditMode及同源Windows／Quest成功，完整證據以PROGRESS／receipt為準。End立即解除遊戲binding，只有當下仍相同player／admission／room／seat的既有連線有30秒結果等待（進行中HTTP最多另5秒）。combat及world兩份journal精確seal後才讀授權statistics，target RPC只傳該玩家、ack後斷線；Host自身ack不得先shutdown切掉peer。不能延後移除／換席撤銷、接受Ended新票券、給client管理key或把pending數字當最終。結果留bootstrap至明確Reconnect清除；Ended不送姿態、結果接管HUD，不改Tracked資料／規則／歷史。三個最終PC場的兩端結果／seal及一般啟動器5項真正視窗觀察、30項練習場／49 UI native／8項票券重連回歸與36 Python通過；同機Simulation，非頭盔／25人／跨機／逾時故障驗收。零事件JSON null被Unity讀空字串的反例先以125項中1失敗重現，僅stream seq0且所有玩家零事件健康100才接受缺失來源；一般入口要等ack並保留結果，新場可取代舊結果視窗。舊UI修正前結果、三場零事件timeout與任務草稿400失敗均保留，全停writer後的SSD-F副本逐檔一致。Prepare重用原ID並全部遊戲端一起更新。

2026-10-31 動態25端見docs/DESKTOP_ACTIVE.md：check-desktop-active.py只一位實際W/Space/R/Space、24接收端，合法barrel(-4.125,0,-1)避開候選格得(-3,0,-1)靶位，不能改rules或注入命中。原fan-out case111719雖8項／130快照通過，後查65失效Running列、26報告全不過全程條件；原passed僅舊範圍，勿重寫或稱穩定。新checker每筆初始capture後Running列及參考區間每張保存Running幀都核對完整可參戰，故意Pause另列、不丟壞列。預設capture-batch1減少同時IO，113854分批9項／130快照／19916 Running列／966回放通過；無probe113444僅權威9項、無本地證據。比較不證明根因或遊戲端全局修復，舊主迴圈／姿態問題仍待。artifact family desktop-active/pointer獨立，Role probes短p001，finish時限仍240秒；UI等待最大40秒（無probe可120）只為操作員、不放寬0.5/1.5門檻。UI呼叫或畫面不符時先重觀察，不誤寫ack；兩次末發UI逾時failed及首錯ack保留。9項成功場都有精確seal／CSV、cleanup無殘留、C原件-F snapshot SHA一致；24 Python通過，沒有C#或UI/API變更、未重建／重跑114 EditMode／雙平台，來源仍e8ae...3d0。詳見PROGRESS。all25SimultaneouslyActive/networkCapacityAccepted均false，完整11項active、無頭盔。

2026-10-31 最新Unity0.28.3／code35、API UI0.27／NGO26，真正114 EditMode／同源Windows-Quest成功，來源e8ae6d846dc014e48984a035f2960c043d342a4fe192ff0feaae3891973ba3d0及原ID一致。VenueTransportProfile在Start前套server/host1024／client128的每update共享send/receive packet池，不改MTU／timeout／可靠視窗／wire／舊資料。見docs/DESKTOP_REPLICATION.md：--vr-replication-probe只明確Windows Development，普通／Editor／Android不安裝，240秒／4096列與錯誤／64capture有界，不做RPC／輸入／姿態注入或GPU PCM。短目錄p001＋程序對照，保留失敗capture；JSON需明確Serializable DTO，不能直接匯出WeatherState。client在End前finish，不稱收到Ended；server在seal後停，log階段是最後Update快取非原子send點。0.28.2 driver128兩模式重現112（16組各7，含Running與Paused），0.28.3兩模式22項／280快照／56報告、534檔SSD-F SHA一致，本輪日誌0；無probe25人8項／14檔亦0，入場重連8項通過。新tick間隔不是RTT／FPS，零錯誤只限本輪負載、不稱原主迴圈停頓或任意工作量已修復。networkCapacityAccepted仍false，完整11項active、無頭盔；Source/binary F，新25程序runtime C SSD，不能稱F USB全資料／跨機25台成功。完整結果／失敗／限制見PROGRESS。

2026-10-31 25個原生PC程序見docs/DESKTOP_CAPACITY.md：check-desktop-capacity.py需明確SSD runtime，Linked及五獨立房各25 client／60秒，20項伺服器入場／靜止姿態／場次AI／seal檢查通過，3351穩定期回放幀逐張核對；但Linked原log有105行send queue full，無時間戳／各client複本證據，網路容量驗收未通過，不能從world新鮮推下行正常。之後摘要明示networkCapacityAccepted=false／scope／log findings，最後摘要增補僅離線核對，不重寫歷史。下一步client複本與錯誤階段，不能盲目提高queue。完整11項仍active、無頭盔。Venue.save同目錄唯一temp＋replace、Windows存取有界2秒，read_json不吞格式錯誤；snapshot全停writer後有界5秒等待自有lease共享讀取並持有至一次copy，拒絕既有／巢狀目的地，不強解鎖／改ACL／覆蓋失敗副本。首輪F22／SSD24檔失敗保留，最新容量24／回歸各14檔SHA一致；6＋5 Python、27練習場、49 UI native，無新GPU／Unity建置，原fingerprint與版本不變。容量passed僅這些檢查且須cleanup成功後發布。詳見PROGRESS。

2026-10-31 外部CPU取樣見docs/POSE_TIMING.md：helper --process-timing只讀本輪3個自有Popen程序。借原handle查exe／建立FILETIME不關原handle，再以QUERY_LIMITED_INFORMATION＋SYNCHRONIZE開固定唯讀handle核對，不能跟隨重用PID／列舉其他程序或開memory／thread／stack／suspend／priority權限。50ms／5000輪／15000列／240秒有界，基線前ready、明確finish先關handle後一次寫report，process-timing-cleanup也須乾淨。分析只用完整內部查詢括號、不插值、少於2點null；CPU時間／cycles加總全threads，不能指定主線程或由零值證明暫停。cycleCounterVersion缺失保留0／unavailable，不補造舊raw；未知版本拒絕。092109共同loop0.594546秒內三程序CPU時間與cycles皆增加、11對查詢每對有cycles增加，不支持全程停止，但非根因／修復證明；091639零時間計數不能直接推暫停。43 Python（含1真正Windows producer及1timer）、兩個真正三發／各28檔SSD／F SHA一致；Unity0.28.1／code33／109 EditMode與雙平台是前輪結果，本輪未重建或改game source。詳見PROGRESS。

2026-10-31 主迴圈定位見docs/POSE_TIMING.md：Unity0.28.1／code33、NGO26／API UI0.27保持，真正109 EditMode／同源雙平台成功。--vr-pose-loop-trace必須與pose trace明確一起，僅Windows Development，普通／Editor／Android不安裝。從current loop插入兄弟marker保留native function／loop condition／delegate及原順序；512節點／32層、4096稀疏列、240秒；結束只從current tree移除自己的marker，不恢復舊樹或刪NGO。分析須檢查detached／pair／計數／clock／完整觀察覆蓋；CLI完成metadata不可缺。JsonUtility未啟用null會寫空預設物件，只在fixture明確false且物件逐欄空預設才忽略，不能隱藏非空／失敗。實際三Unity after WaitForLastPresentationAndUpdateTime→before TimeUpdate空窗共同0.7167323秒，原Update交集0.727348秒；不是Wait內CPU耗時／底層根因證明，不能假設實際引擎順序、排除觀察工具／診斷擾動或調寬門檻。同版無loop對照乾淨不稱修復。33 Python／49一般UI native、兩個真正三發流程；完整失敗／receipt／資料以PROGRESS為準，普通runtime無診斷report。

2026-10-31 獨立心跳見docs/POSE_TIMING.md：check-desktop-pose-input.py --heartbeat啟動自己的normal-priority Python程序，只量10ms wake／UTC／CPU、無UI／遊戲／網路。4096 gaps／256 anchors／240秒有界，明確finish後才寫report；finally自己的handle收尾，heartbeat-cleanup也須無殘留。--observation-only以window-review.done確認無遊戲按鍵，120秒只是人工作業上限，不改0.5／1.5秒政策。分析器核對時鐘及實際coverage，舊無exact UTC起訖用首末anchor保守覆蓋、不可補寫raw；未覆蓋不能宣稱心跳正常。真正三Unity共同0.7017494秒空窗時獨立timer仍≤13.348ms，不支持OSwide暫停，但不是引擎／排程／音效／GPU／I/O根因或修復證明。文字／截圖與六次同handle輸出poll乾淨不排除特定組合／外部工具／診斷影響。四場各24檔SSD／F SHA一致，7心跳（含一個真正timer）＋12輸入＋3舊分析檢查，未重跑Editor／API／APK；完整結果及失敗見PROGRESS。

2026-10-31 當前版本直接連線時序見docs/POSE_TIMING.md：check-desktop-pose-input.py用API0.27／現有Unity0.28，直接UDP、兩client＋server三份原有NativePoseTrace及visible HUD trace；無丟包代理／原生GPU讀回／PCM或姿態／武器注入。三發必須實際Space及確認檔，先明確finish trace再獨立End／seal。analyze-pose-input.py必須按各client唯一connection ID篩server事件，不能把交錯玩家流量混算；保留階段邊界，UTC步進達50ms不做phases／三方join。MainThreadGap是Update觀察間隔，不是CPU耗時／OSwide證明。實際1121幀重現HUD過期0.133828秒，三程序共同0.6425932秒空窗在兩發之間，不能稱音效、GPU、I/O、NGO或OS根因已證明，更不能宣稱已修復／放寬0.5秒。外部computer-use觀察影響尚未排除，下一步需獨立心跳／PlayerLoop對照。4項真正流程、10項新合成分析反例與原3項分析回歸；未重跑API／Editor／APK，資料及C／F快照只讀比對，詳見PROGRESS。

2026-10-31 電腦練習場已修正舊0.21 gate，見docs/DESKTOP.md。start-desktop-demo.py共用Venue的API0.27／來源fingerprint／Transport pin、admission／擷取UTC1.5秒／精確seal；Unity0.28／NGO26及102 EditMode為前輪結果，本輪不改遊戲來源。Venue artifact_family只允許desktop-venue／desktop-demo，預設路徑及latest pointer保持原五房工具，練習另用自己的pointer。每位client以admission命名，最多五人同房；正常關窗先移除已停handle，End後退場client，只等自己的API／server封存，避免live-child fence誤判。原生非預期client停止仍exit1／stage failed、不產完成summary；cleanup仍獨立End／seal／保留snapshot。final-report.csv經Bearer API及標準csv／Decimal核對全部玩家與尾界，不能將零事件ledger origin=null誤判為不是Simulation（來源已綁header／stream）。成功SSD需明確--runtime-root，writer全停才複製回F、原件不動；不宣稱F USB／跨機或25台。check-desktop-practice.py預設27項真正無圖形、--interactive 9項實際W／Space／R與關窗；check只觀察不注入。最後一張射擊擷取短暫POSE STREAM STALE後恢復，不能稱啟動器已修復原0.5秒姿態原因。詳情及6項反例／49項既有UI原生回歸見PROGRESS；不重算前輪API／Editor／APK檢查。

2026-10-31 最終報表見 docs/REPORTS.md：API／UI0.27唯讀report.csv、reportVersion1。FinalReport在同一session gate檢查房間／操作員、Ended及combat精確seal後取ledger，HTTP明確傳Actor，GameServer403，不能只靠UI或把End當完整。Linked房控沿用全場讀取權限。含離場玩家、原任務ID／名稱、來源／throughSequence及stream尾界；零事件有stream用其宣告來源，無來源為None，空場Session列不造玩家。CSVUTF-8 BOM／CRLF／invariant數字，公式／控制文字只在輸出加單引號，原資料不改。下載generation＋login epoch阻擋切離再回／重登入晚回應，不存憑證。這不是world錄影封存或頭盔證書；Unity0.28／code32／NGO26及102 EditMode是前輪已驗結果，本輪未變遊戲來源／binary，不需重建場景。驗證數量以PROGRESS為準。

2026-10-31 玩家人物見 docs/PLAYER_BODY.md：API／UI0.26、Unity0.28／code32／NGO26、102真正EditMode。player-body-v1固定404面／五Mesh pin，保留八個舊profile。header playerPresentationVersion新1／舊缺失0；每玩家hasPlayerPresentation／walking明確保存，只有原本成功接受的Running平面移動>1mm標記四tick步態，不能從相鄰回放幀猜測。NGO既有walking新增玩家語意，全部遊戲程序一起更新。軀幹依頭部／地面近似，桌面腕點跟原合成手套／保存換彈時鐘；Tracked不合成握持雙臂、不把pointer當握點、不改追蹤。裝飾性quaternion只正規化副本，owner body隱藏且不驗證live姿態；原旋轉容差及0.5／1.5秒政策不改。舊head／手標記在Visual子層，須執行時處理而不重建prefab／IDs。跨avatar引用計數，自己的body在despawn釋放。NativePlayerBodyProbe只明確Windows Development／untracked自己的observer framebuffer與實際Mesh端點，600秒／8圖／900萬像素、無PCM或輸入。capture.request原子replace且reader允許ReadWrite／Delete共享，helper優先讀終止report。Running遠端頭手仍插值，不能稱每個繪製幀都精確對到保存packet；Pause時鐘／步態相同，端點1微米界線；精確比對只讀額外SQLite副本，原件／snapshot不動。PC／雙平台及失敗以PROGRESS／receipt為準，完整動畫／腰腳／實機／25台仍待。

2026-10-31 射擊音效見 docs/COMBAT_AUDIO.md：API／UI0.25、Unity0.27／code31／NGO25、93真正EditMode。combat-audio-v1為獨立固定PCM／profile pin，保留player-fire-v1及八個舊幾何profile，舊header combatAudioVersion缺失0不補聲音；新1必須有player／enemyFireVersion1。只播接受事件的新sequence與保存世界槍口，age≤3／gap≤10，加入／seek／過期／重啟先baseline，Pause停止。actor presentationRunning與fire原子複製，故NGO25必須全體遊戲端一起更新；不改rules0.8.0、傷害、射速、pointer或Tracked。32個1–25m線性空間聲源、無遮擋／混響；普通遊戲有聲音但沒有診斷。--vr-combat-audio-probe只在明確Windows Development／可見untracked自己的AudioListener與全新絕對目錄，180秒／1600萬float／12000視窗／1024 cue，與weather／HUD／fire GPU探針互斥。只錄本遊戲PCM、無麥克風／OS／GPU／輸入注入，finish.request先停診斷再真正End／seal。非人工聽感／頭盔證據。fingerprint新增Audio WAV／meta及Resources asset／meta，兩平台以實際receipt核對；原scene／prefab ID重用。資料及來源更新不能降舊reader。PC／建置最新數值以PROGRESS為準。

2026-10-31 姿態時序見 docs/POSE_TIMING.md：Unity0.26.1／code30、87真正EditMode；API／UI0.24、NGO24／所有世界與遊戲契約保持。--vr-pose-trace僅明確Windows Development／全新絕對目錄，server可batch；一般／Editor／Android不安裝。32768列、240秒、保留最早資料並明示截斷，收集期間不寫trace狀態，finish.request才完整停止，最後report序列化／IO在觀察截止後。無位置／旋轉／玩家姓名／憑證／payload／GPU／PCM。PoseSend是RPC呼叫前，不是transport完成；BodyConnection是10Hz發布觀察，不是每tick。MainThreadGap只記>100ms。不能由乾淨基線推定舊偶發原因已修復，不改0.5秒姿態或1.5秒世界新鮮度。check-desktop-pose-trace.py只用自己的loopback gate及真實Space；analyze-pose-trace.py只讀關閉後JSON／不開SQLite，時鐘跳動或控制段主線程停頓使校準失敗。60秒基線／1.2秒丟包／實際GPU結果見PROGRESS，無跨機／頭盔／25台證據。

2026-10-31 玩家射擊效果見 docs/PLAYER_FIRE.md：API／UI0.24、Unity0.26／code29／NGO24，82真正EditMode；雙平台及PC結果以最新PROGRESS／receipt為準。player-fire-v1固定組合pin，保留七個舊profile；header playerFireVersion缺失0／新來源1，玩家fire欄位只由接受ShotFired的sequence／tick+1／世界射線產生，逐packet核對。age0–2閃光、14／22／12／4mm子槍身後座，不移pointer／根槍口／手套／Tracked資料，原rules0.8.0與命中不變。Unity閃光脫離avatar父層以免before-render追蹤移動歷史射線，view銷毀自己的flash、模型最後lease才釋放共用資源。新來源／API／UI／全部遊戲程序一起更新，Prepare重用識別，不降reader。--vr-player-fire-probe僅明確Windows Development／untracked可見client，全新絕對目錄、300秒／8圖／無PCM或輸入。diagnostic complete與真正End／精確seal分開。PC檢查保留短暫pose失聯樣本，實際輸入階段須等待有效Simulated rig，不能放寬來源1.5秒門檻。SQLite稽核在額外副本執行，mode=ro仍可能重建SHM；不要因此改原runtime／封存副本。

GitHub #1本文接近長度上限，原63864字全文已精確封存於 https://github.com/peca12968/vr-command-center/issues/1#issuecomment-6532297157 。之後本文維持目前目標、最新交付與ROADMAP／PROGRESS連結，舊進度留在文件／封存留言，不遞迴貼入全部舊本文；更新前先讀回當前狀態，完整目標仍open／開發中。

2026-10-31 敵軍射擊效果見 docs/ENEMY_FIRE.md：API／UI0.23、Unity0.25／code28／NGO23，76真正EditMode；雙平台／PC以最新PROGRESS／receipt為準。combat-effects-v1固定32面脈衝pin，沿用728面NPC、保留舊六profile。header enemyFireVersion缺失0／新來源1，hasFireState及fireSequence／fireTickPlusOne／fireOrigin／fireDirection逐EnemyShot核對，不能用目前NPC位置／朝向補造歷史射線或改rules0.8.0。閃光在保存世界射線、後座只移槍身子Renderer，authority Gun／手套／Tracked資料不動。新wire、來源／API／UI／全部遊戲端一起更新，Prepare重用原識別，不可降舊reader。--vr-enemy-fire-probe僅明確Windows Development／untracked可見client全新目錄，最多8圖／180秒，無PCM／輸入；finish.request僅結束收集，report.complete不代表任務End，另看observedEnd／stopReason及伺服器精確seal。不要以被End撤銷前沒收到Ended畫面推定遊戲未封存。

2026-10-31 敵軍持槍見 docs/ARMED_ENEMIES.md：API／UI0.22、Unity0.24／code27／NGO仍22，70真正EditMode；雙平台／PC結果以最新PROGRESS與receipt為準。armed-combatants-v1固定728面／八Mesh／一材質pin，保留舊五profile。要求enemyPresentationVersion1＋weaponPresentationVersion1，不增wire欄位。裝飾性兩節臂upper.22／lower.25；槍口仍feet+(0,1.4,0)，正規化forward後用完整pitch，不搬動feet／Tracked資料、不改rules0.8.0或Collider。新NPC本地位置不插值，使用同一actor row避免槍口偏離保存位置；10Hz階梯感仍待改善。原始binary／舊模型不改；閃光需另存射擊當下原點／方向及事件，不能拿目前姿態補造。原5080不換新版資料／DLL。

2026-10-31 換彈／合成手套見 docs/WEAPON_ACTIONS.md：API／UI0.21、Unity0.23／code26／NGO22，66真正EditMode；雙平台與最新PC以PROGRESS／receipt為準。weapon-actions-v1固定pin，保留四個舊profile；header weaponPresentationVersion缺失為0、新來源1，hasWeaponPresentation及reloadUntilTick按保存事件／tick核對，不另設本地計時器。新profile還要求enemyPresentationVersion1，來源／API／UI／所有遊戲端一起更新。動畫只動子物件，槍口／rig資料及rules0.8.0不改；手套限Simulated且連線／存活，不能搬動Tracked關節或稱實體換匣。原死亡可能留過期reload旗標，僅停止動作，不偷偷改規則。新欄位／profile寫入後不能降reader，binary原header／checksum保留。Native reload工具明確開HUD GPU探針、無PCM；review等待600秒不是放寬1.5秒來源或30-tick規則。控制台狀態檔可能讀到未完成寫入，等待同tick有效讀回且保存前後樣本；不能以重試掩蓋真正tick改變。

2026-10-30 人形敵軍見 docs/ENEMY_PRESENTATION.md：API／UI0.20、Unity0.22／code25／NGO21，61真正EditMode；最新雙平台與原生結果以PROGRESS／實際receipt為準。combatants-v1固定404面資料pin，保留三個舊profile。header enemyPresentationVersion缺失為0，新來源明確1；hasPresentation／forward／walking按保存tick重建，Paused／Ended保留步態，不能以本地時間推測或補造舊NPC姿態。binary原header／payload／checksum不改寫。NPC沒有武器模型／IK，原feet+(0,1.4,0)射擊原點及軸對齊half(.3,.9,.3)命中盒不改；新模型不加Collider／NetworkObject，不改rules0.8.0。NGO enemy row原子含facing／walking／presentationTick，全部遊戲程序一起更新，Prepare只原位升21並重用識別。Advance會在2m停止；移動步態驗證用控制台Patrol／Pause，不能為測試改AI距離或注入pose。42項UI／native、五房七場、8項無圖形入場及真正兩發命中／擊殺見PROGRESS；仍無頭盔／MR／硬體／25台。

2026-10-30 玩家步槍規範見 docs/SERVICE_RIFLE.md：API／UI0.19、Unity0.21／code24／NGO20，56真正EditMode與同源雙平台成功，原生按鍵／GPU及39項UI整合見PROGRESS。service-rifle-v1固定網格pin與生成器，完整保留field-props-v1／primitives-v1，不能改舊資料／回放。模型原點是pointer前0.15m的真正muzzle，與server／HUD共用AvatarPose.MuzzleOffset；桌面合成RightOffset(.18,-.12,.75)不套用Tracked XR。不要把pointer marker當握掌，不能移動追蹤資料來配模型；不加Collider或偷偷改rules0.8.0。資源跨avatar引用計數／場景池，舊Weapon只執行時停用而非重建prefab。API／UI及全體遊戲端一起更新，新profile寫入後不能降舊reader。

2026-10-30 API／UI 0.18 的配置規範見 docs/LAYOUT.md：profile vr-room-v1／version1／rules0.8.0，使用共用 ArenaLayout 的旋轉包圍盒、五席 0.3m 出生空間與真正初始敵軍候選網格。Core 新開 Create 在權限／已接受 request key 確認後才檢查；不能把拒絕政策加入歷史 projection、已接受重試或 ArenaSession 舊世界讀取。無效草稿仍可保存，修正需保存下一版並明確選用；MR applies=false／canStart=null，不能稱校正通過。API／UI 一起更新，新增報告 mode、版本與非同步 epoch／序號／選擇 fence；後端必須獨立拒絕無效新 VR 開場，不能只靠 UI。envelope6／world schema1／NGO19 不變，bundle0.20.1／code23；本輪真正51 EditMode、同源雙平台成功，PC 回歸以最新 PROGRESS 為準。

2026-10-30 前輪為 API／UI 0.17、Unity 0.20.0／Android code22／NGO19，真正46項EditMode、同源Windows／Quest與原生掩體／聲光／35項UI整合均已通過；完整結果與限制以PROGRESS為準，仍無頭盔／25台。field-props-v1自製沙包／油桶在玩家與觀戰共用固定資料，舊primitives-v1保留舊外觀。原命中／行走仍為旋轉包圍盒（圓桶角落／沙包縫隙非逐像素碰撞），不得以外觀變更偷偷改rules0.8.0。見docs/FIELD_PROPS.md。

新assetSet寫入後不可降回舊API／UI reader，schema不變不代表可降版。Prepare僅原位升NGO19並重用scene／prefab ID；新來源、API／UI及所有遊戲程序一起更新。原5080仍用原v0.16 DLL／資料，新測試用自己的v0.18 API／SSD runtime，不能為測試替換正式歷史。來源fingerprint已包含Resources JSON／shader；生成資料以python scripts/generate-field-props.py --check核對。已發布v1幾何／配色SHA pin固定，改模型需新assetSet並保留舊檔／reader，不能重寫pin來改舊回放。

2026-10-29 使用者已確認 Hub 有效授權，真正 Editor 已成功 Prepare、執行 39 項 EditMode，並產出同源 Windows 播放器與 ARM64／IL2CPP Quest APK；舊 CLI／198 是歷史狀態，不再當作目前阻礙。已有真正 PC 視窗的方向鍵／Space／滑鼠射擊、擊殺／命中率、換彈／暫停與封存證據；練習場操作見 docs/DESKTOP.md。沒有頭盔連線／實測證據。最新二進位與觀戰延遲修正驗證以 PROGRESS／實際 build log 為準，不能拿 SDK 檢查代替。

歷史遊戲端 v0.19.0／Android code20／NGO protocol18，API 為 0.16.0、驗票 protocol 2。Prepare 可在保存 Arena 上從 16／17 升至 18，不能改 file ID；全部遊戲程序一起更新。PC 撤銷／重連與已接受 Simulated 姿態的 admission 快取見 docs/RECONNECT.md。真正視窗已驗證強制離線後 0.65 公尺外位置與健康／彈藥保持，仍非頭盔／server 崩潰恢復。

Transport 2.7.4 固定官方來源嵌入 Packages/com.unity.transport，只修失敗 receive completion 釋放 buffer；保留通知／逐檔雜湊，以 python scripts/check-transport-patch.py 驗證，不改 Library 快取或安全設定。UPM lock 為 embedded，receipt 指紋包含嵌入 C#／asmdef／UPSTREAM.json。來源及原生反例見 docs/TRANSPORT_PATCH.md；29 Tests 含真正 Windows 小佇列 UDP 回歸。scripts/check-unity-admission.py 使用自有隔離資料／憑證，--interactive 才驗證原程序按鈕／鍵鼠，不可注入姿態取代。

桌面碰撞見 docs/DESKTOP_COLLISION.md：ArenaWalkSurface 與權威／AI 共用 0.3m 足跡及 0.05m 線段取樣，只有 untracked 桌面預測裁切／拒絕後回到接受姿態，不能搬動 Tracked XR。CombatPropState 新增 room 是 NGO 18 wire 變更；API 0.16／驗票 2 保持。build-unity Tests 當前門檻125。真正鍵盤四階段、五房／Linked、重連及同源雙平台證據以 PROGRESS 為準。

Prepare 必須重用已保存 Arena／PlayerAvatar 的本地 file ID；先前每次重建新 scene 會改變 NGO 識別、破壞跨目標連線。需重建時用 RebuildArena 並一起重建全部玩家；不能 Desktop／Quest 分別重建不同場景。生成物、OpenXR 設定與 packages-lock.json 應隨成功匯入結果保存。ProjectGeneration 測試涵蓋重複 Prepare 識別、非零 hash、場景／音訊引用與 Android XR 設定；build-unity Tests 當前門檻為125，腳本明確回傳 exit 0／1。

生成器另外有 scripts/check-unity-editor-sdk.py --offline --verify-missing-reference：重新檢查 Windows player 基線，再以真正 Editor／XR SDK 綁定 ProjectBuilder，直接讀自己的 asmdef 參考、禁止隱含傳遞 ProjectReference。MetaQuestFeature 位於 Unity.XR.OpenXR.Features.MetaQuestSupport，Editor asmdef 必須直接參考它；反例只修改生成的診斷 csproj，應重現 CS0234。此圖明確不含 URP 專用驗證分支（見報告），不是完整 Editor／UPM／資產生成／ILPP／APK 證據。範圍見 docs/UNITY_SDK_CHECK.md。

Unity 接入另有 scripts/check-unity-sdk.py（Windows／Python 3.12+），以官方固定來源與真正 Editor DLL 編譯 17 runtime／15 test 檔案的 Android／Windows 分支；UnityTest 引用真正匯入的 Library/ScriptAssemblies/UnityEngine.TestRunner.dll，不使用 stub。快取與報告在 artifacts/unity-sdk-check，--offline 會拒絕來源 hash 改動。這不是 Unity CompilationPipeline、Editor／UPM／ILPP／EditMode／APK；不要部署診斷 DLL。manifest URP 已對齊 Editor 隨附 17.3.0，Collections 診斷 pin 2.4.3；此較窄圖仍用 registry Transport 2.6.0，不驗證正式嵌入修正。範圍與剩餘驗收見 docs/UNITY_SDK_CHECK.md；舊語法／單一天氣型別檢查仍只是較窄證據。

v0.16 聲光規範見 docs/ENVIRONMENT.md：EnvironmentPresentation 為共用 tick 規則，header.environmentVersion 缺少保持 legacy 0、新來源 1，不補造舊音效；保留 binary 原始 header／checksum，以 codec 正規化比較。API／UI／來源一起升級，NGO protocol／Android code 16、bundle 0.16.0，18 項 EditMode 待驗。單一 UnityWeatherView 已綁真正 Core／Audio DLL 通過，不代表整個 Unity／NGO／shader／音訊匯入或 APK。新增天氣檢查需設 VR_COMMAND_CHECKS_DLL 指向同次隔離建置，聲音素材以 generate-weather-audio.py --check 驗證。

觀戰精確數值控制在 world-camera-form.js，操作見 docs/OBSERVER_CAMERA.md；欄位為看向目標、度數與距離，套用不自動保存。快照不蓋草稿，登出／換錄製清空，同場回放不清。camera-controls.cjs 由一般／native 檢查器共用；不可將軟體 WebGL 或33項整合當人工GPU／頭盔證據。

原生天氣驗證見 docs/NATIVE_WEATHER.md；NativeWeatherProbe 僅 Windows Development、未追蹤可見client且明確 --vr-weather-probe 全新絕對目錄啟用。只記錄本玩家AudioListener混音與GPU，沒有麥克風／OS loopback，不把DSP／截圖當聽感／頭盔。一般啟動不掛載探針；診斷有85秒／有界緩衝限制。新增正式builtin imageconversion模組與lock，NGO18／environmentVersion1保持。

軍事HUD見 docs/TACTICAL_HUD.md：方位000為場景正Z，不是地理北；標記只依同房、存活參戰者及複製幾何的胸部視線，候選10Hz／32個，最多8標記，每繪製幀重查遮擋。顯示不授權命中／傷害，也不是防作弊邊界。--vr-hud-probe 為285秒、不錄PCM的獨立診斷模式，與weather模式互斥；一般啟動不附掛。HUD快照要配合真正GPU截圖。

開發根目錄為 `F:\Projects\vr-command-center`；以此庫的實際 Git 狀態與執行結果為準。

五房 PC 工具為 scripts/start-desktop-venue.py，操作見 docs/DESKTOP_VENUE.md。--check 啟動五個真正獨立 server／每房一個 client，驗證隔離／權限、單房重用，再於全部 End／精確封存後開新 Linked 世界；不合併歷史。F 為 USB 硬碟，五房資料全放 F 的原生試跑未達 1.5 秒門檻；成功證據為明確 --runtime-root 指向 C NVMe 的全新自有 SQLite／journal，來源及 binary 仍在 F，不得稱為 F USB 或跨機／25 台通過。全部 writer 停止後才複製 runtime-snapshot 回 F，保留原件；不可搬動既有預覽資料。每程序 job workers=2 已記錄，降低 workers 本身未修復 F 延遲。最終七場最大取樣來源年齡 0.275004 秒、回放／報表一致；可操作模式關窗五場共 4037 幀封存。來源與頭手仍 Simulation。

操作員自訂 PC 流程為 scripts/start-desktop-control.py，操作見 docs/DESKTOP_CONTROL.md。僅監看自己新建的隔離 API，全新 Preparing VR、無既有 combat source 才啟動 server；名冊以 playerId＋admissionId 啟停短效票券 client，玩家不持有控制台／GameServer key。dynamicRoster 最終按持久 PlayerJoined 分頁核對所有歷史玩家，不只看目前名冊。operator-status 來自真正世界幀，維持 UTC 1.5 秒門檻。tests/browser/check-operator-native.cjs 需要該次 ready.json，15 項 UI／native／動態名冊／回放通過；不是一般 Linux CI 或頭盔測試。Native 白天／雨夜／Pause 截圖與 Chromium SwiftShader 觀戰分開；不能把 lightning=true 或 Web Audio 當原生閃電／雷聲聽感。

開始接續工作時讀取 `docs/PROGRESS.md`、`docs/ROADMAP.md`、`docs/REQUIREMENTS.md`。使用者的完整目標為 11 項 VR/MR 遊戲需求及 VIVE XR／Quest 3 相容性，不能以管理原型或模擬測試通過替代完整交付。

後端為 .NET 10；Unity 工程位於 `clients/unity/`，固定 Editor 6000.3.27f1，不直接引用後端組件。未知硬體協議使用模擬器，實機整合待廠商文件及設備。

使用者已指定先用 Meta Quest 3；優先推進 Quest 3 的 Android 垂直切片，VIVE 相容性留待後續。模擬戰鬥必須使用 Simulation 標記，不能與 GameServer 資料在同場混用或宣稱頭盔實測完成。

`/api` 端點使用伺服器配發的主控／房間控制台身分。實作新路由時必須傳遞認證身分並檢查操作範圍，不能依賴核心的預設 Internal 身分處理 HTTP 請求。測試用獨立的暫存憑證；不要讀出或提交 `data/operator-keys.local.json`。

後端變更應執行：

```text
dotnet restore VrCommand.slnx --locked-mode
dotnet build VrCommand.slnx --configuration Release --no-restore
dotnet run --project tests/VrCommand.Checks --configuration Release --no-build
python scripts/smoke_api.py
```

`VrCommand.Checks` 是可執行的規則檢查程式，不能只執行 `dotnet test` 就宣稱已完成檢查。依功能實際影響補充有意義的測試，並將驗證結果、限制與下一步更新至 `docs/PROGRESS.md`。

遊戲事件、即時狀態、統計與回放應共享版本化契約；頭盔姿態與逐幀模擬不使用管理 REST API。實機相容、MR 校正、25 台頭盔效能與硬體控制須分別保留驗收證據。

瀏覽器主控台在 `src/VrCommand.Api/wwwroot/console/`，操作與真實瀏覽器檢查見 `docs/CONSOLE.md`。UI 變更執行 `tests/browser/check.cjs`，使用隔離 API 與測試憑證；檢視 `artifacts/console/` 截圖。瀏覽器沒有持久化控制台憑證，保持每次 API 授權與房間範圍；不能用 UI 隱藏按鈕替代後端檢查。平面配置已有任務／Unity 接入來源碼，但尚無 Unity 運行證據。

共用射擊／AI、ArenaSession 及 TelemetryOutbox 唯一來源在 `clients/unity/Packages/com.vrcommand.simulation/Runtime/`；.NET Standard 2.1 建置入口是 `src/VrCommand.Simulation`。保持 C# 9 與無 Unity／.NET 10 相依。SimulationDemo 與 TelemetryRelay 示範一律使用 Simulation。Unity 的遊戲及補送接入已有來源碼，仍未編譯運行；不得將 .NET 管道通過當作頭盔報表整合成功。規則／接入／管道見 SIMULATION、GAMEPLAY、TELEMETRY。

Windows 執行中的本機 API 可能鎖住一般輸出 DLL；採 SIMULATION 文件的 `--artifacts-path` 隔離建置，不為測試任意停止現有服務。HTTP／瀏覽器檢查可用 `VR_COMMAND_API_DLL` 指定隔離 API，HTTP 另以 `VR_COMMAND_SIMULATION_DEMO_DLL` 指定同次建置的示範工具。

Quest 接入與建置見 `docs/QUEST3.md`。`scripts/check-unity-source.ps1` 只檢查 C# 9 語法，不能代替 Unity 編譯與 EditMode。Editor 與 Android 工具已安裝至 F 槽，使用者已明確同意 SDK／NDK 條款，不再要求相同確認或盲目重裝。Hub 3.22.5 已安裝，使用者完成本機授權確認後，真正 Editor 已可編譯／建置；先前 CLI 無 session／198、過期回呼與 Windows 提示均只保留為歷史診斷。不要自動操作登入／安全性提示，不因 CLI 狀態否定已通過的 Editor 建置。

3D 模擬回放在 `replay-*.js`，資料與操作見 `docs/REPLAY.md`。維護 schema 2／rules 0.8.0、明確 Simulation 來源、射線與快照／統計的一致性。`tests/browser` 的 test 會執行資料驗證與軟體 WebGL 檢查，不能視為真實 GPU、Unity 或頭盔測試。Three.js 上游原始檔、MIT 及 provenance 一併保留，不混入 CDN 執行相依。

頭盔只配置短效玩家票券；GameServer 憑證僅存桌面伺服器設定。所有 `data/`、`artifacts/`、Unity 快取與本機憑證均不得提交。生成場景、APK 或桌面程式須有實際成功結果，不能以來源碼存在宣稱完成。

v0.9 的建立／加入／離開以選用 Idempotency-Key 去重，事件 schema 4 的 requestId 與業務事件一起持久化；重試只確認歷史接受，不重施新狀態。保留 schema 1–3 讀取與不帶 key 的相容性。前端與後端需一起升級，不能把 v0.9 的可重試前端放到忽略 key 的舊後端；寫入新 schema 後不可直接降版。契約見 SESSION_PROTOCOL。

v0.11 新事件 schema 5，讀取 schema 1–4；戰鬥串流綁定唯一來源／origin，接受有 Running 觀察位置的已保存尾端，封存後只允許既有報告去重確認。End 釋放房間但 pendingTelemetry 保持 true 到精確 seal；不能把未封存報表當作最終結果。批次可能已提交前綴，須原樣重試。journal 壞尾端不自動截斷；補送不是世界恢復。HTTP 隔離檢查另設 VR_COMMAND_TELEMETRY_RELAY_DLL。備份資料後再升級，不能降版讀取 schema 5。

v0.12 世界發布為 WebSocket、觀察為帶 Bearer 的 fetch SSE，來源規範在 WORLD_RECORDING.md。新增 worlds.db 與每幀統計／combat witness 核對；管理 events.db schema 不變。必要另跑 python scripts/smoke_world.py，隔離指定 VR_COMMAND_WORLD_RELAY_DLL；瀏覽器檢查包含 world-browser.cjs。共享 WorldRecording DTO 仍須 C# 9／netstandard2.1；Unity 尚未發布世界或採樣頭手，不能把合成 Simulated rig 宣稱為 Tracked。

v0.13 共用 WorldOutbox／WorldPublisher 與 Unity 頭手來源／追蹤／管理邊界已接源碼，尚未編譯運行。binary journal 有 checksum、exclusive lease、durable ack 與 completion/seal；Native --world-journal 使用同一發布器，--recording 留舊 NDJSON，恢復 Unity 可另指定 --combat-journal。header UTC 擷取時間需 v0.13 API，舊資料預設空值；DB schema 不變不表示可直接降回舊 reader。新鮮度不可用收到時間代替擷取時間。NGO source byte 改 wire format，生成器 protocol 13；EditMode 至少 12 項，來源／證據／限制見 WORLD_SOURCE.md。

v0.14 入場規範見 ADMISSION.md：envelope 6 讀 1–5，以原加入 EventId 派生／保存 admissionId；v2 票券簽 admission／seat，v1 全拒。新 HTTP 移除及配票必須 If-Match-Admission，已接受的歷史 leave 重試仍保留原 fence 只確認；不要以當前入場覆蓋舊 pending 操作。GameServer 驗票 protocolVersion 2，ArenaSession.Connect 必帶 admissionId；Unity 以 throughSequence 快照及 expiry 驗後綁定，管理 fetch 合併串行。15 項 EditMode 仍待執行；協同更新 API／UI／所有 GameServer／頭盔來源並重發票券，不以舊來源忽略 epoch 作相容解法。

v0.14.1 僅管理／觀戰新增相同 worlds.db 的 camera_bookmarks 表，envelope 6／world schema 1／NGO protocol 14 不變。鏡頭以完整 OperatorIdentity 及場次隔離，僅 Master／RoomController，24 個有效位置；PUT 同 ID／內容確認原結果、DELETE 留 tombstone，舊保存重試不得重建已移除位置。新路由每次重查錄製及房間範圍。camera-ui.js 待確認操作保留原內容，logout／換身分 epoch 阻擋晚回應；鏡頭設定存伺服器，憑證仍限頁面記憶體。規範見 WORLD_RECORDING。預覽資料實際在 src/VrCommand.Api/data，root data 是控制台 key／來源設定；隔離 DLL 啟動須顯式 DataDirectory／SessionDataDirectory，備份兩處及 WAL，不以空白新資料庫替代原歷史。

v0.15 任務庫由 Persistence.SqliteMissionLibrary 的 missions.db／schema 1 管理，原 GUID.json 一次交易匯入後只保留備份；目前 Core.MissionStore 不能讀寫已版本化目錄，不混跑舊 API。任務本體 schema 1／場次 envelope 6／world schema 1／NGO protocol 14 不變。series 的版本不可變且線性，revision route 的 baseId 必須當前 head；任務 request key 綁完整作者／kind／base／definition，已接受重試回原版本不重施。所有 HTTP 讀寫明確傳 Actor；ReadMission 為共用範本政策，AuthorMission 限 Master。UI 待確認寫入保留原請求，保存成功但後續讀回失敗也保留；已知 head 於單次登入只前進，背景更新不換掉已選的開場版本或草稿。history 只傳分頁 metadata，控制台輪詢 /mission-library，不載入全部歷史定義。見 MISSION_VERSIONS。PowerShell 直接 @(Invoke-RestMethod ...) 會多包一層陣列；安全檢查先賦值再檢查 Count，檢查／備份非零退出時不得啟動下一個相依步驟。
