# 長期開發目標

2026-10-28 依使用者要求建立，狀態：**開發中**。完整範圍維持原始 11 項需求及 VIVE XR／Quest 3 相容性。各階段完成不代表整個目標完成；有外部依賴時持續推進可獨立驗證工作。

2026-10-29 使用者指定「先用 META QUEST 3」：M2 先交付 Quest 3 垂直切片，暫按 Android 獨立執行規劃；VIVE 的確切型號與接入移至後續相容階段。

| 階段 | 交付 | 通過條件 | 目前狀態 |
|---|---|---|---|
| M0 專案與管理核心 | F 槽原始碼、私人 GitHub、需求追蹤、五房場次與任務 API、CI | 可重現建置、核心與 HTTP 驗證、推送成功 | 本機與推送完成；一次 Linux 建置／核心／HTTP 通過，瀏覽器列序斷言已修正並本機通過；修正提交的雲端 CI 再次受帳務限制未啟動 |
| M1 場次控制與事件基礎 | 主控／房間權限、準備／開始／暫停／結束狀態、命令與事件、統計核心 | 五房隔離、權限、去重、狀態遷移、紀錄恢復測試 | 管理／統計核心、SQLite 追加、JSON 升級與模擬來源已驗證；建立／加入／離開可持久去重，v2 票券與移除／配票按每次 admission fence；API／SQLite／瀏覽器已驗證；真正 Windows 撤銷／重連已通過；新增 SSD runtime 下五個原生獨立世界、每房一個 client 的權限／命令隔離、單房 End／重用，以及全部封存後新開 Linked |
| M2 Quest 3 優先的遊戲垂直切片 | Unity 工程、Quest Android profile、基本移動／互動與共同場景；再接入 VIVE | Quest 3 實機操作及雙玩家互見；之後驗證混合頭盔、校正與定位 | 真正 Editor 已通過 UPM／ILPP／資產匯入、102 項 EditMode、Windows 與 ARM64／IL2CPP Quest APK；兩平台來源 fingerprint／網路識別一致。無頭盔，依使用者指示先繼續 PC；雙 Quest 操作與混合裝置待驗 |
| M3 軍事戰鬥與 AI | 武器、傷害、健康、敵軍尋路／攻擊、操作員覆寫、HUD | 伺服器判定一致、AI 可控、事件與統計相符 | Windows server 加兩個 desktop client 已通過獨立／跨房 Simulation AI 傷害、暫停、封存及回放統計；真正視窗已完成方向鍵／Space／滑鼠射擊、擊殺／命中率、換彈及暫停；控制台自訂任務／動態名冊及 Advance／autoAttack 到真正 native 傷害、Pause／Resume／End 已通過；新增軍事HUD／方位／遮擋標記、自製沙包／油桶及不可變素材版本，真正鍵盤與受傷／淘汰已驗；新增固定玩家步槍、保存朝向／步態的人形敵軍及保存時鐘的換彈／合成手套及原創雙手手槍／裝飾性雙臂、保存射線的玩家及敵軍閃光／後座、原生視窗兩發命中／一擊殺與封存統計；新增404面玩家人物、保存步態及桌面腕點／換彈雙臂，真正雙PC GPU／W／Space／R已驗，完整第一人稱／追蹤人物及武器動畫、啟動旗標／原停頓原因、完整策略、追蹤及實機戰鬥待驗 |
| M4 任務與場景編輯 | 任務視覺編輯器、版本、物件擺設、天氣／日夜／雷電即時控制 | 儲存重載一致、獨立／全館環境正確同步 | 任務版本、2D 配置及環境／AI 控制已有核心／HTTP／瀏覽器證據；Unity 場景／音訊／Shader 匯入與 Storm／Night PC 任務運行通過。已實際以 UI 保存／重載擺設並在 Unity GPU 看見配置、白天／雨夜／Pause；原生新沙包／45° 油桶阻擋、退回／側移已通過；配置圖顯示真實平面包圍盒；新增旋轉越界／重疊／五席出生空間及初始敵軍容量檢查，保存草稿與新開場政策分離，複雜通路／地形仍待；原生GPU閃電與自身DSP雨雷／靜音已量測；聽感／實體輸出、MR校正及頭盔待驗 |
| M5 觀戰、回放與報表 | 自由／跟隨鏡頭、書籤、快照與事件回放、逐玩家統計 | 即時觀戰、跳轉倍速、回放與結束統計一致 | 持久世界、SSE／回放、書籤及統計已有核心／瀏覽器證據；真正 PC 發布／封存及控制台俯視、鏡頭保存／跟隨後讀回、倍速／末幀回放已驗證；SSD 最新五房最大來源年齡0.200379秒、自訂任務0.308984秒。觀戰瀏覽器為軟體 WebGL；已新增精確座標／度數／距離與原生錄製自訂視角保存／封存回放45項整合（含素材版本）；真實GPU／長任務手感、實際頭手及25台待驗 |
| M6 硬體與場館驗收 | 廠商轉接器、MR 場地、斷線恢復、25 人完整任務 | 混合頭盔與實體硬體完整任務、效能紀錄、部署手冊 | PC 同 admission 斷線恢復已有證據；跨機／server 崩潰、MR、硬體與 25 台仍待 |

## 下一個開發順序

1. 使用者目前無頭盔，玩家／敵軍射擊音效與PC DSP已完成，接續完整第一人稱／追蹤人物、動畫／聲學、複雜通路／地形、自由鏡頭／長任務操作及跨機部署；原生GPU閃電及DSP已有證據，聽感／實體輸出仍待驗。控制台自訂任務、保存重載配置到真正 PC、天氣／AI／名冊／觀戰及回放已接通，見 DESKTOP_CONTROL；五房與跨機範圍仍分開。
2. 擴大跨機網路、異常中斷及補送驗收，維持 admission fence、防瞬移與 Simulation。避免分平台重建場景，Prepare、102 Tests、Desktop／Quest 已有真正成功結果；嵌入 Transport 修正須保留來源雜湊與原生回歸。
3. 取得 Quest 後驗證控制器／追蹤中斷、雙玩家互見、聲光／效能與封存；之後進行 MR、VIVE、廠商硬體及 5／10／25 人分階段驗收。合成姿態維持 Simulation。
4. GitHub 雲端待帳務允許後再驗證完整執行結果；不改帳務、不重跑已知無法啟動的工作。

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
