# 開發進度

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

完整11項目標保持active，後續持續多玩家操作、完整場館與跨機流程；25端最大長文／並行操作、實體Quest／VIVE、MR、廠商硬體與25台仍待驗收。GitHub提交／fresh CI紀錄接續補充於此輪末。

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
