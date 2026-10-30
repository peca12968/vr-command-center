# 玩家步槍閃光與槍身後座

新 `player-fire-v1` 使用保存的玩家射擊事件還原效果，完整沿用七個舊素材 profile 的 reader。資料由 `scripts/generate-player-fire.py` 生成，SHA256 固定為 `187c7df5346419edadafa1cc74a04db0763dda268650e066dbbcaf8304e60ff0`；生成器先核對舊模型 pin，不重寫原網格。玩家步槍／手套沿用 weapon-actions-v1，32 面星形脈衝沿用 combat-effects-v1，倍率1.2。沒有新外部素材。

API／UI 0.24.0、Unity 0.26.0／Android code29／NGO24。新 header `playerFireVersion=1`，缺欄位仍為0；新 profile 同時要求 enemyPresentationVersion1、weaponPresentationVersion1及enemyFireVersion1。玩家 actor 使用既有原子 fire 欄位，NGO24標明其新語意。來源、API、UI及全部遊戲程序一起更新，不能讓新資料降回舊 reader。envelope6、mission schema1、world schema1、票券2、environmentVersion1及rules0.8.0保持；binary原header／payload／checksum不重寫。

ArenaWorld 只在實際接受 `ShotFired` 後保存事件 sequence、tick+1、原點及方向。拒絕的快速連射及已接受 request 的重試不重啟效果，不多扣彈藥。新 packet 必須明確有 `hasFireState=true`；未開火為序號0／時鐘0／零向量，已開火則與前一 packet 及本次事件重建的最後一發精確相符。不得用目前瞄準方向或收到時間替換歷史射線。

效果只依保存的模擬 tick：age0–2顯示閃光（0.15秒），槍身後退依age0–3為14／22／12／4mm，age4復位。3tick能跨越正常10Hz發布間隔；這不是丟包時每發必可見的保證。Pause／Ended及直接seek保持保存時鐘。死亡／離線隱藏效果，歷史射線仍保留；換彈停止槍身後退但保留尚未到期的接受閃光。

真正槍口仍為原pointer前0.15m。只把借用原網格的槍身 Renderer 與原彈匣放在後座子物件下，舊根 Renderer 執行時停用；根、pointer、頭手及合成握點不搬動。Unity閃光為獨立場景物件，保存世界射線，即使XR在before-render更新pointer亦不隨之偏移。Tracked手仍是真實標記，不以合成手套配模型。Mesh／材質跨avatar引用計數，view銷毀自己的閃光，最後一份模型 lease 才釋放共用資源。沒有Collider、Light、聲音、相機震動、實體後座或遊戲規則變更。

`--vr-player-fire-probe <全新絕對目錄>` 僅Windows Development／可見untracked client且有本玩家AudioListener時啟用，與enemy-fire／weather／HUD診斷互斥。最多300秒、8張／每張900萬像素，於EndOfFrame記錄本玩家實際套用的時鐘、歷史射線、後座與Transform並擷取自己的framebuffer；不錄PCM／OS畫面，不注入輸入或姿態。一般啟動不掛探針。`finish.request` 只明確結束診斷收集，`complete`與`observedEnd`分開；真正遊戲結束及精確seal另由伺服器證明。

```powershell
python scripts/generate-player-fire.py --check
python scripts/check-desktop-player-fire.py --runtime-root C:/Users/USER/AppData/Local/VrCommand/SimulationRuns
```

後者必須配合真正Space兩次及Right一次，stage marker只確認操作及圖片檢視，不能取代按鍵。使用自己的隔離API／憑證／資料，程式與binary在F、runtime明確用SSD，所有writer停止後才回存F。逐輪結果、失敗與限制以 [PROGRESS.md](PROGRESS.md) 為準。此功能不完成玩家全身、完整握持／手指／死亡動畫、音效或頭盔驗收。
