# 玩家步槍素材 service-rifle-v1

API／UI 0.19、Unity 0.21／Android code24／NGO20 加入原創低多邊形玩家步槍。玩家視窗、其他連線玩家及新錄製的觀戰／回放使用相同位置、法線、頂點色及三角索引。NPC、人物身體、左手與頭部仍為原型；模型是靜態外觀，沒有加入握持 IK、換彈／後座動畫、槍械音效或實體武器整合，也沒有頭盔手感驗收。

固定生成器 `scripts/generate-service-rifle.py` 產出虛構遊戲用輪廓：槍托、機匣、握把、彈匣、護木、槍管、瞄具與識別色塊；不使用外部模型、紋理、字型、下載或隨機輸入。264 個三角形、長0.735m、寬0.16m、高0.378m。provenance保存SHA-256及來源；v1資料與配色發布後固定，改動必須新assetSet並保留舊檔，不能更新pin改變已保存錄製。

```powershell
python scripts/generate-service-rifle.py --check
```

原點使用既有 `muzzle` 定義，局部 +Z 為射擊方向，整個模型在槍口後方。這與以握把為原點的模型不同：不把裝飾槍管末端拿來重新定義伺服器射線。本地畫面跟隨輸入預測，其他玩家使用插值姿態，並非逐幀伺服器確認影像；觀戰使用保存的已接受muzzle／forward。沒有新增Collider、NetworkObject、命中或導航幾何，沒有更動彈藥、傷害、射速、換彈或rules0.8.0。

Unity原右手pointer的縮放為(.12,.12,.2)，舊Weapon方盒繼承後很小。新模型是avatar根下的等比物件，LateUpdate以既有右手pointer前方0.15m的伺服器槍口為原點並跟隨其旋轉；模型、伺服器及HUD共用同一常數，不改實體XR座標、旋轉、縮放或追蹤來源。舊Weapon物件仍保留file ID但執行時停用；原pointer方盒位於射線原點，會遮住新槍口，因此只隱藏它的Renderer，不把pointer假稱量測的握把或手掌。桌面合成pointer從原相對頭(.3,-.35,.4)調整為(.18,-.12,.75)，使槍管／機匣前端在原60°視野內；這是明確的桌面輸入預設變更，頭部與XR輸入不變，保存的射擊原點隨實際接受姿態記錄，舊回放不重算。左手marker保持，模型沒有推算握姿。每個程序跨avatar共用一個Mesh／材質，引用計數到最後一名釋放才銷毀。

觀戰以保存的muzzle／forward定位；若右手旋轉的+Z與保存射線方向一致，保留完整roll，缺失或不相符則沿保存forward重建朝向。這些舊／外部來源沒有可證明的完整握持旋轉，不能由模型推算真實手掌或硬體校正。瀏覽器共用geometry但每個玩家有自己的淡出材質，死亡／離線淡出不影響其他玩家；移除一名角色不銷毀其他角色仍使用的geometry，換錄製時釋放舊池。

三種明確素材版本：

- `primitives-v1`：原方盒掩體與原武器，缺欄位舊匯出與Create預設維持此值。
- `field-props-v1`：固定沙包／油桶與原武器，舊錄製不換新步槍。
- `service-rifle-v1`：完全沿用固定field-props-v1掩體，玩家使用新步槍；只有新Unity來源明確指定。

開發驗證可在Editor／IL2CPP建置結束後執行 `python scripts/check-desktop-rifle.py --runtime-root C:/Users/USER/AppData/Local/VrCommand/SimulationRuns`。它只開自己的API／room3世界及一般可見玩家，不掛診斷、不注入pose或combat。依該次輸出的stage，在真正視窗按Left14／Down5瞄準，再分別按兩次Space；檢視後於該次資料夾寫aim.done／fire.done／review.done。marker只確認已操作，必須由實際世界與封存報表證明ammo2／hit2／kill1／100%才會通過。這是開發檢查器，一般遊玩使用DESKTOP的練習場。

API會拒絕未知版本及修改已接受header的重試。binary原始header／checksum不改寫，任務schema1、事件envelope6、world schema1、environmentVersion1及票券2不變；不能因DB schema相同而降回不認識此版本的reader。先備份正式兩處資料及WAL，再協同部署新API／UI與全部遊戲程序。NGO20隔離不同玩家外觀，Prepare原位升級並重用Arena／PlayerAvatar識別，不能分目標RebuildArena。原5080及歷史資料不為測試替換，新場只用自己的隔離API／資料／憑證。

真正Editor、56項EditMode、Windows／Quest、GPU、實際按鍵射擊／換彈及觀戰回放的本輪實際結果以 [PROGRESS](PROGRESS.md) 為準。27 Node／162 Chromium包含同源資料／pin、外向法線、槍口／方向／roll、資源壽命、真正WebGL的新舊面數差異與反覆切換；軟體WebGL不是原生GPU或頭盔證據。managed SDK僅補充型別綁定，不能替代真正匯入／ILPP／執行與APK。完整人物／武器動畫、Quest／VIVE、MR、廠商硬體及25台仍待。
