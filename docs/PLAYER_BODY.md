# 玩家軍事人物與保存步態

新 `player-body-v1` 使用原創頭盔／護目鏡、背心／彈袋、雙腿／靴與桌面雙臂，404面，Native跨avatar共用五個Mesh／一材質，Web共用幾何、每人物一材質。生成器 `scripts/generate-player-body.py` 先核對全部舊模型pin；新JSON SHA256固定 `1035ca0dffafc31226616485c58ef530d8e7b809feef2b5e461229424bc9703b`。沿用原玩家步槍264面、合成手套240面與32面射擊閃光、NPC／掩體及combat-audio-v1，八個既有外觀profile及reader完整保留。新外觀不加Collider／NetworkObject，命中與行走仍是原規則的粗略幾何。

API／UI **0.26.0**、Unity **0.28.0／Android code32／NGO26**。新header `playerPresentationVersion=1`；新profile還要求enemyPresentationVersion1／weaponPresentationVersion1／enemyFireVersion1／playerFireVersion1。音效維持獨立combatAudioVersion，新Unity來源仍1。缺失玩家人物版本保持0，舊錄製保留舊方盒／頭部，不從相鄰快照猜步態。每個新玩家packet明確`hasPlayerPresentation=true`與`walking`，無版本不得宣稱新狀態；Preparing／死亡／離線不能walking。未知版本、漏標記或不完整profile由核心／API及瀏覽器各自拒絕。

步態週期／角度、比例及腕點／延展數學也是v1回放契約；變更需新playerPresentationVersion並保留舊求解／reader，不能只改共用常數或重寫舊pin。

伺服器只在原本驗證成功的Running、連線且存活玩家平面移動超過1mm時標記最後移動tick；四tick內保存walking，其後停止。轉頭／只改高度、拒絕姿態及Preparing移動不觸發；沒有改接受條件、0.5秒姿態／1.5秒世界新鮮度、傷害、彈藥或admission。步態為保存tick%12的±18度對向腿部旋轉。Pause／Ended不推進模擬tick，所以腿部姿勢固定；原有頭手追蹤／姿態接受仍可更新，這不是凍結真實人體或強制鎖位置。

NGO既有原子actor walking欄位開始具有玩家語意，與presentationTick一起複製，故protocol26要求全部遊戲程序同版。envelope6、mission／world schema1、票券2、environment1及rules0.8.0保持。來源／API／UI／全體遊戲端一起更新，保存新欄位後不可降舊reader；Prepare只原位升版並重用原scene／prefab ID。

外觀地面根據已接受頭部的平面座標置於場地Y=0；軀幹／腿的垂直比例為eyeHeight／1.65，頭盔放在原頭部位置與旋轉，水平身向取頭部forward的yaw。這是三點頭手資料推算的裝飾性輪廓，沒有實際腰／腳追蹤、屈膝／腳掌IK、腳步鎖定、地形貼合或完整人物動畫。低頭高低也不是身高或校正證據。

只有Simulated桌面玩家顯示雙臂，末端對齊既有合成手套根部的裝飾性腕點；右手由真正muzzle加固定RightGrip，左手依保存換彈截止tick的原LeftHand動作。兩節臂基長0.30／0.32m，為既有桌面合成持槍位置做等比例延展；距離<0.03或>1.24m時隱藏兩臂。這不是人體尺寸校正。Tracked保留原有追蹤手部／pointer與武器路徑，頭盔跟隨原頭部位置，**不把右pointer當握點、不新增合成握持雙臂或搬動追蹤資料**；新裝飾性朝向只對quaternion副本正規化，原rig及接受容差不改。Tracked全身IK與實機舒適度仍待設備。

Unity舊頭部Renderer只在執行時停用；必須查找保存prefab的Visual子物件，桌面頭手舊標記也在執行時停用，不能只查joint父層。新body是脫離avatar縮放的場景物件。跨avatar引用計數共用Mesh／材質，despawn銷毀自己的body，最後lease才釋放資源；不重建已保存prefab。本玩家整個第三人稱body隱藏且不求解，避免在尚未接受的live XR姿態超界時新增呈現例外；原第一人稱步槍／手套及接受政策保持。其他玩家才顯示全身，死亡／離線隱藏新body。遠端即時頭手仍使用既有插值，回放使用保存的接受姿態；不能宣稱每個插值繪製幀均等同10Hz保存快照。暫停並待插值收斂後才作原生／回放數值比對，浮點端點容許1微米；保存時鐘／步態必須相同。

瀏覽器觀戰／回放使用相同固定幾何、C#／JS對照的步態及腕點。手動seek直接從該幀重建，不另設本地動畫時鐘；變換在真正Three.js Mesh節點核對，舊profile不配置新body。軟體WebGL不是原生GPU或頭盔證據。

```powershell
python scripts/generate-player-body.py --check
python scripts/check-desktop-player-body.py --runtime-root C:/Users/USER/AppData/Local/VrCommand/SimulationRuns
```

原生工具啟動自己的API／Room3 server與兩個可見PC玩家。先以真正S／方向鍵設定第一個玩家視角，再操作新開的第二個玩家W、Space／R；stage檔只確認操作或圖片檢視，不注入RPC／姿態／輸入。自己的observer GPU擷取idle、真正非零Running步態、Pause兩張、回到idle及換彈Pause，共六張，另核對最終精確seal與原統計。單次W可能已回idle才收到Pause，不能據此要求暫停仍必須walking。來源及binary在F，runtime明確用SSD；writer全停後才回存F，SQLite檢查只使用額外副本。

`--vr-player-body-probe <全新絕對目錄>` 僅明確Windows Development／可見untracked本玩家AudioListener安裝，與weather／HUD／射擊／音訊探針互斥。最多600秒、8張／單張900萬像素，以本機capture.request標籤請求自己的framebuffer與實際已套用Mesh端點；walking標籤等待真正可見且非零的步態。請求以同目錄暫存檔原子replace發布，reader允許ReadWrite／Delete共享；helper優先讀終止report，不可忽略錯誤而繼續等待舊status。沒有PCM／麥克風／OS畫面、遊戲命令或輸入注入。finish.request只停止診斷，任務另由server End／精確seal。普通啟動、Editor、Android不安裝探針。真正建置、測試及原生結果／失敗以 [PROGRESS.md](PROGRESS.md) 為準；完整玩家動畫、實際頭手與Quest／VIVE／MR／25台均仍待驗。
