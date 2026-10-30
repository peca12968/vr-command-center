# 敵軍雙手持槍

`armed-combatants-v1` 增加原創緊湊型手槍、分離上下臂及雙手手套，沿用既有軍事掩體、玩家步槍／換彈。每名728三角形、八個共用Mesh及一材質；頭104、腿60重用兩次，取自固定combatants-v1；手套各120面，為固定weapon-actions-v1的0.65倍副本。軀幹84、上下臂各24重用兩次、手槍84面為本次原創，無外部素材。生成器先驗證舊pin，所有舊檔／reader保留。

`python scripts/generate-armed-combatants.py --check` 核對Unity JSON、瀏覽器module及provenance，SHA256為 `cc011e951163d4b846c4e2c217592251906844c0dfcee2f795618c8c1c388102`。發布後改模型必須新profile，不能重寫pin或舊回放。控制台可直接依保存header選模型，舊五個profile保持舊外觀。

API／UI **0.22.0**、Unity **0.24.0／Android code27**；NGO仍22，未增加wire欄位。新來源／API／UI與全部遊戲端一起更新；新profile需要明確enemyPresentationVersion1及weaponPresentationVersion1。rules0.8.0、envelope6、任務schema1、world schema1、票券2及environmentVersion1保持，不能因schema未變就降舊reader。Prepare重用已保存Arena／PlayerAvatar識別。

## 原射擊原點與姿勢

敵軍原有射擊原點為feet+(0,1.4,0)，未向前延伸。新外觀使用壓縮雙手持槍姿勢、軀幹／頭稍後傾的低多邊形設計；不能把玩家長步槍直接插入此位置，亦不能搬動權威槍口來配美術。槍管+Z從該原點沿保存forward，槍身主要向後延伸0.175m。頭部仍夾±45°，槍pitch使用完整±90°。腳底位置、原AI選擇／射速／20點傷害與軸對齊half(.3,.9,.3)命中盒都不改。

`ArmedEnemyPresentation`為C#9／無Unity相依的裝飾性兩節手臂求解器，瀏覽器有同規則。肩點固定在yaw-local身體空間；upper .22m、lower .25m，wrist依槍口及固定握點求出，elbow朝外下方hint彎折。共線hint有確定fallback，無法到達的目標明確拒絕，不能靠移動feet或muzzle補救。手套與槍共父層，雙臂末端接手套外側腕點；不是手指IK、追蹤關節或實體控制器握持。

身體yaw／頭部／腿步態依原EnemyPresentation1及保存tick；Paused／Ended及直接seek還原同一姿勢，不跑本地計時器。Unity新敵軍位置使用同一atomic actor row的原始position，移除舊外觀的本地位置插值，避免槍口落在不同於權威的中間點；10Hz位置更新可能有階梯感，沒有宣稱已完成平滑預測。舊錄製外觀資料仍保持，未改歷史資料或binary原header／payload／checksum。

Unity由每個CombatAuthority場景池管理八Mesh／一材質，跨NPC重用；無Collider或NetworkObject，刪除一名不釋放其他人的網格。觀戰每NPC獨立淡出材質、共用geometry，死亡沿用淡出／玩家端隱藏政策。玩家合成手套／Tracked政策維持WEAPON_ACTIONS。

## 驗證及範圍

核心以181個pitch核對原射擊方向與固定臂長；C#／JS向量涵蓋yaw、垂直極值與tick邊界。真正EditMode檢查外向網格、共享資源、無Collider、實際Transform／槍口／腕點及seek。SQLite保存／重開使用新profile；瀏覽器實際WebGL比較新舊面數、保存姿勢、直接seek與最終統計。觀戰canvas的armedPoses取自真正子物件世界矩陣，非回傳原frame充數。

最新真正雙平台與PC結果、失敗及限制以PROGRESS／實際receipt為準。原生工具使用自有隔離API及SSD runtime，關閉writer後才複製快照回F並核對雜湊，不能取代正式5080歷史。

開火閃光、後座／NPC換彈／死亡動畫、完整人體與腳底IK、手指／物品庫／音效尚未加入。本輪刻意不以當前forward／位置補造舊射擊效果；後續需先保存並驗證射擊當下的原點／方向與事件。極端角度的關節造型仍是風格化原型，未完成完整姿勢限制或防穿插。沒有頭盔、MR、廠商硬體、跨機或25台驗收。
