# 敵軍射擊閃光與後座

Unity0.38.0另修正[可見目標選擇](AI_VISIBLE_TARGETS.md)：受阻時改試後續可命中玩家，仍使用原接受事件的保存射線及此處同一外觀契約；沒有新增fire欄位、wire或素材profile。最新建置與驗證見PROGRESS，下方保留原效果交付的歷史範圍。

`combat-effects-v1` 沿用固定armed-combatants-v1／weapon-actions-v1／field-props-v1，再加原創32面封閉星形槍口脈衝。每NPC最大760面；槍口脈衝只有三個保存tick（0.15秒），不是持續光源、火焰模擬、彈道或音效。`generate-combat-effects.py --check` 先驗證舊來源pin，新資料SHA256固定 `b8fe83d66781c2f65816d6873cc08ba01314418d42777a55e9eea2d1ee34a9bb`；Unity Resources與瀏覽器資料一致，無外部素材，舊六profile／pin不改。

API／UI **0.23.0**、Unity **0.25.0／Android code28／NGO23**。新header `enemyFireVersion=1`，新profile同時要求enemyPresentationVersion1及weaponPresentationVersion1。NGO enemy actor row原子新增fireSequence／fireTickPlusOne／fireOrigin／fireDirection；Prepare原位升23、保留場景／prefab ID。來源、API／UI與所有遊戲程序須一起更新，新資料不可降舊reader。rules0.8.0、envelope6、任務schema1、world schema1、票券2及environmentVersion1保持。

## 保存事件與顯示

原AI只有Cast實際命中有效玩家後才Emit EnemyShot，再產生PlayerDamaged。新狀態直接複製該已接受事件的world sequence、tick+1、origin與direction；不由NextShot冷卻或目前feet／forward推測，不改攻擊條件、20-tick間隔、20點傷害或原feet+(0,1.4,0)射擊原點。

每個RecordedEnemy明確保存hasFireState及四欄；從未射擊為true／sequence0／tickPlusOne0／零向量。新Packet驗證逐筆EnemyShot重建每名敵軍最後射擊，再核對保存時鐘／原點／方向，含跨packet延續；移動、改朝向或Patrol不能改寫舊射線。序號不得越過throughSequence，時鐘不得來自未來，射擊原點須仍在該房且Y1.4、方向為單位向量。保留只讀舊世界的缺欄位0語意；舊header不能帶新動作，binary原header／payload／checksum不重寫。

共用C#9 `EnemyFirePresentation` 與JS按 `age=tick-(fireTickPlusOne-1)` 顯示：age0／1／2閃光；槍身後退分別12／18／10／4／1mm，age5起歸零。死亡停止外觀效果，但不刪歷史。Paused／Ended及直接seek使用保存tick；沒有本地動畫計時器，也不對舊錄製補造閃光。網路快照停滯時仍是最後接受姿態，來源新鮮度需依既有STALE／連線狀態判讀，此效果不構成反作弊或網路超時邊界。

閃光Transform固定在保存的射擊世界原點／方向，即使NPC已移動／轉身；它可能短暫落在目前槍口後方，這表示歷史射擊位置。槍口的authority-aligned Gun Transform、雙臂及手套不移動，僅其子Renderer做裝飾性後座；原Gun Renderer執行時停用並借用同一網格，不重建prefab／Collider。這不是追蹤控制器後座、手指動作或實體硬體輸出。

Unity場景池沿用八個人物Mesh，再共享一個flash Mesh／獨立unlit材質；新Shader保留instancing及stereo宏，不受夜間環境光變暗，沒有新增Light或AudioSource。瀏覽器以同資料與MeshBasicMaterial重建，保留各角色材質生命週期。觀戰enemyFirePoses取實際世界矩陣及槍身位移，不能只回傳frame資料代替渲染證據。

## 原生畫面診斷

僅Windows Development、可見的untracked本機玩家，明確 `--vr-enemy-fire-probe <全新絕對目錄>` 才安裝NativeEnemyFireProbe；與weather／HUD probe互斥。一般及Android啟動不掛載。診斷在EndOfFrame擷取自己的遊戲framebuffer，最多8張／180秒、每張最多900萬像素；不擷取OS／其他視窗、不錄麥克風或PCM、不注入輸入／姿態／射擊。

報告記錄Renderer最後實際套用的tick／fireState與Gun／Flash世界Transform，避免拿較晚抵達的NetworkList狀態配舊畫面。可由該次新目錄的 `finish.request` 明確結束**診斷收集**，不修改遊戲；report.complete代表收集完成，observedEnd及stopReason另外說明是否看到End。End撤銷入場可能先銷毀玩家物件，因此不能要求每個client一定看到Ended畫面；任務結束及精確封存仍須由API／journal／SQLite獨立證明。提前despawn／超時保留部分資料並標示失敗。

`scripts/check-desktop-enemy-fire.py --runtime-root <SSD新根目錄>` 使用自己的隔離API／server／可見Simulation client，由真正AI在白天及夜間開火、Pause／Patrol／恢復，核對保存射線及GPU Transform。review.done只表示已檢視PNG，不注入任何遊戲資料。工具先停止診斷再End／精確封存；耗損／中彈／彈藥與回放須一致，writer關閉後才複製快照回F並核對SHA。

最新測試、真正雙平台、成功與失敗場次以PROGRESS及receipt為準。瀏覽器SwiftShader不是原生GPU；原生GPU／Transform不是頭盔或實體聽感。本輪僅敵軍手槍效果，玩家步槍閃光／後座、射擊音效、NPC換彈／死亡、完整人物及實機／25台驗收仍待。
