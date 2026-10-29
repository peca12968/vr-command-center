# 長期開發目標

2026-10-28 依使用者要求建立，狀態：**開發中**。完整範圍維持原始 11 項需求及 VIVE XR／Quest 3 相容性。各階段完成不代表整個目標完成；有外部依賴時持續推進可獨立驗證工作。

2026-10-29 使用者指定「先用 META QUEST 3」：M2 先交付 Quest 3 垂直切片，暫按 Android 獨立執行規劃；VIVE 的確切型號與接入移至後續相容階段。

| 階段 | 交付 | 通過條件 | 目前狀態 |
|---|---|---|---|
| M0 專案與管理核心 | F 槽原始碼、私人 GitHub、需求追蹤、五房場次與任務 API、CI | 可重現建置、核心與 HTTP 驗證、推送成功 | 本機與推送完成；一次 Linux 建置／核心／HTTP 通過，瀏覽器列序斷言已修正並本機通過；修正提交的雲端 CI 再次受帳務限制未啟動 |
| M1 場次控制與事件基礎 | 主控／房間權限、準備／開始／暫停／結束狀態、命令與事件、統計核心 | 五房隔離、權限、去重、狀態遷移、紀錄恢復測試 | 管理／統計核心、SQLite 追加、JSON 升級與模擬來源已驗證；建立／加入／離開可持久去重，v2 票券與移除／配票按每次 admission fence；API／SQLite／瀏覽器已驗證；真正 Windows 撤銷／重連已通過；新增 SSD runtime 下五個原生獨立世界、每房一個 client 的權限／命令隔離、單房 End／重用，以及全部封存後新開 Linked |
| M2 Quest 3 優先的遊戲垂直切片 | Unity 工程、Quest Android profile、基本移動／互動與共同場景；再接入 VIVE | Quest 3 實機操作及雙玩家互見；之後驗證混合頭盔、校正與定位 | 真正 Editor 已通過 UPM／ILPP／資產匯入、34 項 EditMode、Windows 與 ARM64／IL2CPP Quest APK；兩平台來源 fingerprint／網路識別一致。無頭盔，依使用者指示先繼續 PC；雙 Quest 操作與混合裝置待驗 |
| M3 軍事戰鬥與 AI | 武器、傷害、健康、敵軍尋路／攻擊、操作員覆寫、HUD | 伺服器判定一致、AI 可控、事件與統計相符 | Windows server 加兩個 desktop client 已通過獨立／跨房 Simulation AI 傷害、暫停、封存及回放統計；真正視窗已完成方向鍵／Space／滑鼠射擊、擊殺／命中率、換彈及暫停；控制台自訂任務／動態名冊及 Advance／autoAttack 到真正 native 傷害、Pause／Resume／End 已通過；正式美術、完整策略、追蹤及實機戰鬥待驗 |
| M4 任務與場景編輯 | 任務視覺編輯器、版本、物件擺設、天氣／日夜／雷電即時控制 | 儲存重載一致、獨立／全館環境正確同步 | 任務版本、2D 配置及環境／AI 控制已有核心／HTTP／瀏覽器證據；Unity 場景／音訊／Shader 匯入與 Storm／Night PC 任務運行通過。已實際以 UI 保存／重載擺設並在 Unity GPU 看見配置、白天／雨夜／Pause；原生沙包／45° 油桶阻擋、退回／側移已通過；閃電／雷聲、MR 校正及頭盔待驗 |
| M5 觀戰、回放與報表 | 自由／跟隨鏡頭、書籤、快照與事件回放、逐玩家統計 | 即時觀戰、跳轉倍速、回放與結束統計一致 | 持久世界、SSE／回放、書籤及統計已有核心／瀏覽器證據；真正 PC 發布／封存及控制台俯視、鏡頭保存／跟隨後讀回、倍速／末幀回放已驗證；SSD 最新五房最大來源年齡 0.255 秒、自訂任務 0.212 秒。觀戰瀏覽器為軟體 WebGL；實際頭手、自由鏡頭完整人工操作及 25 台待驗 |
| M6 硬體與場館驗收 | 廠商轉接器、MR 場地、斷線恢復、25 人完整任務 | 混合頭盔與實體硬體完整任務、效能紀錄、部署手冊 | PC 同 admission 斷線恢復已有證據；跨機／server 崩潰、MR、硬體與 25 台仍待 |

## 下一個開發順序

1. 使用者目前無頭盔，接續原生閃電／雷聲及自由鏡頭完整人工驗證，擴充複雜地形碰撞，再推進軍事美術。控制台自訂任務、保存重載配置到真正 PC、天氣／AI／名冊／觀戰及回放已接通，見 DESKTOP_CONTROL；五房與跨機範圍仍分開。
2. 擴大跨機網路、異常中斷及補送驗收，維持 admission fence、防瞬移與 Simulation。避免分平台重建場景，Prepare、34 Tests、Desktop／Quest 已有真正成功結果；嵌入 Transport 修正須保留來源雜湊與原生回歸。
3. 取得 Quest 後驗證控制器／追蹤中斷、雙玩家互見、聲光／效能與封存；之後進行 MR、VIVE、廠商硬體及 5／10／25 人分階段驗收。合成姿態維持 Simulation。
4. GitHub 雲端待帳務允許後再驗證完整執行結果；不改帳務、不重跑已知無法啟動的工作。

管理介面在 `/console/`；完整結果見 [DESKTOP_CONTROL.md](DESKTOP_CONTROL.md)、[DESKTOP_VENUE.md](DESKTOP_VENUE.md)、[DESKTOP.md](DESKTOP.md)、[RECONNECT.md](RECONNECT.md)、[TRANSPORT_PATCH.md](TRANSPORT_PATCH.md) 及 PROGRESS。五房新工具完成七場獨立／重用／Linked 驗證；一般視窗關閉後五場共 4037 幀封存。程式碼與 binary 仍在 F，成功配置明確使用 SSD runtime；F USB 全資料未達 1.5 秒門檻。上一輪 29 項真正 EditMode、無圖形／視窗各八項 admission 檢查、獨立／Linked 回歸及 Windows／Quest 同源建置成功。視窗場強制離線後保留走離出生點 0.65 公尺的位置與健康／彈藥，1648 幀封存且回放一致。API 0.16／場次 envelope 6／世界 schema 1 保持；Unity v0.18／NGO 18 需全體遊戲程序同版。本輪控制台自訂任務新增 15 項 UI／native 與 17 Node＋122 Chromium，並回歸五房；未混算歷史 .NET 規則／29 EditMode，頭盔／25 台待驗，編譯並行曾超過快照門檻，不宣稱所有負載達標。

最新 v0.18 已完成 [DESKTOP_COLLISION.md](DESKTOP_COLLISION.md) 的真正鍵盤沙包阻擋、退回、側移及旋轉油桶阻擋；34 項 EditMode、485 核心、369 HTTP、43 世界串流及同源 Windows／Quest 建置通過。新 binary 另通過七場五房／Linked、8 項重連及 15 項 UI／native 回歸；證據與限制見 PROGRESS。桌面移動預測不搬動 Tracked XR，也不完成複雜地形／物理場地驗收。

不先承諾日程與成本；取得團隊規模、素材來源、頭盔型號、場地與協議後才能估算。每次交付更新 `PROGRESS.md`，有可驗證成果再更新本表。
