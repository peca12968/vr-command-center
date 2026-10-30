# 保存換彈時鐘與桌面合成手套

API／UI **0.21.0**、Unity **0.23.0／Android code26／NGO22**。新 `weapon-actions-v1` 沿用固定掩體與人形敵軍，將原264面步槍分成240面槍身及24面彈匣，加兩個各120面的原創手套。四Mesh／一材質共用引用計數，無Collider／NetworkObject，槍口根與原pointer前0.15m保持一致；不移動輸入／追蹤資料，不改rules0.8.0的射線、射速、彈藥或換彈規則。

生成器 `scripts/generate-weapon-actions.py` 先驗證舊步槍pin，再依原三角形分離彈匣；還原到原位時264面的頂點、法線及色彩與舊版相同。新資料SHA-256固定 `517c3616ec12dad34f25cc50f5309eae1033b62bcbbb636b4a3f378a5c12cab3`；`--check` 同時核對Unity JSON、瀏覽器module及provenance。舊四個profile及原pin保留，改模型要新profile，不能改舊回放。沒有外部模型、貼圖或下載。

## 狀態、動畫及相容性

新header明確指定 `weaponPresentationVersion=1`，新profile另外要求enemyPresentationVersion1。每個玩家保存 `hasWeaponPresentation=true` 及 `reloadUntilTick`；沒有換彈時為0，換彈時直接取原ArenaWorld的完成tick，不另設本地計時器。來源／API／UI／所有遊戲端協同更新；NGO玩家row原子包含presentationTick與reloadUntilTick。Prepare只原位升22並重用scene／prefab ID。

共用驗證以先前玩家狀態及已保存ReloadStarted／ReloadCompleted事件核對截止時間，拒絕憑空換彈、重疊換彈或改時間；完成事件必須在原始30-tick截止點。API現有world發布仍每次檢查來源擁有者與範圍，沒有新增繞過認證的路由。新schema2匯入另要求明確connected／rig及合法關節，不能把舊沒有rig的範例當成已追蹤資料。

`WeaponPresentation` 與JS按保存tick重建：前5 tick左手從前護木移向彈匣，5–11抽出，12–17隱藏彈匣表示替換，18–25插回，25–30回到握持；最大下移0.32m、側移0.16m及傾斜20°。原20Hz／30 tick的遊戲換彈時間不改。Paused／Ended保留原tick及截止時間，seek還原同一局部姿勢；完成後時鐘歸0、彈匣回原位，消耗彈數仍由原遊戲事件決定。

手套只在Simulated且連線／存活的玩家顯示，取代該模式的手部方盒顯示；原rig數值不改。Tracked玩家保留實際左手標記，不套合成手套；彈匣仍是按鍵驅動的程序動畫，不代表實體換匣、量測握持或手指追蹤。槍口根繼續跟隨實際pointer／保存的muzzle與forward，動畫只動子物件。玩家端包含原有輸入預測及遠端插值，不宣稱與觀戰逐pixel相同。

死亡／離線停止合成手套動作；死亡時原規則可能仍留有過期reloading旗標，本版容許保存原狀態但不繼續動畫，沒有趁外觀更新改死亡規則。NPC尚無武器握持，玩家身體仍為原型；這不是完整骨架／前臂IK、物品庫、掉落彈匣、後座／死亡動畫、音效或廠商硬體整合。

缺欄位舊header及Create／Capture預設保持weaponPresentationVersion0，舊玩家時鐘0／has=false，舊外觀不補造動作。binary原header／payload／checksum保留；envelope6、任務schema1、world schema1及票券2保持，但新欄位／profile寫入後不能降舊reader。

## 檢查與電腦端操作

原遊戲使用Space射擊、R換彈。獨立驗證工具如下，所有資料／憑證均為自己的新場次，程式及binary在F、runtime明確使用SSD：

```powershell
python scripts/check-desktop-reload.py --runtime-root C:/Users/USER/AppData/Local/VrCommand/SimulationRuns
```

依其stage在可見遊戲實際按Space一次並建立fire.done，再按R；工具觀察真正保存的換彈後，在抽出／替換階段由管理API暫停。檢視GPU後實際按一次Space，建立pause.done；恢復至30／89後檢視並建立complete.done。標記只確認人工操作，沒有注入pose／combat。人工review等待600秒，既有1.5秒來源新鮮度、0.5秒參戰姿態與30-tick換彈門檻沒有放寬。

此工具明確啟用既有Windows Development `--vr-hud-probe`，285秒有界、無PCM／麥克風／OS擷取。遊戲自身GPU PNG在該次reload-probe；一般啟動不掛載探針。正常桌面視窗的補充截圖與探針來源分開，非遊戲視窗不能作證據。

暫停期間可執行 `node tests/browser/check-reload-native.cjs <該次artifacts/desktop-venue/目錄>`，以該次自己的憑證開真正觀戰，讀取原生已保存frame並比較實際WebGL子物件位移／角度／隱藏狀態及手套，保存數值與近距離鏡頭。此項為Chromium SwiftShader，不當作原生GPU或頭盔效能。一般瀏覽器seek測例使用明確Synthetic的新增事件／rig，與真正原生證據分開。

核心、66項真正EditMode、兩平台receipt、原生操作／封存、五房及重連的最新結果與失敗紀錄見 [PROGRESS](PROGRESS.md)。完整頭盔／MR／25台驗收仍待。
