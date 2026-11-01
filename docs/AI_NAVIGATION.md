# 敵軍繞行旋轉掩體

2026-11-01 後續[非格點起終點連接](AI_NAVIGATION_ANCHORS.md)已接Unity0.37.2／199真正Editor。以下0.37.1格邊修正與原生取樣範圍保留歷史，不當最新版本或新逐tick證據。

2026-11-01：Unity **0.37.1／code46／NGO29**，API/UI **0.30.1**。本輪修正敵軍的平面格點尋路，不修改角色半徑、速度、傷害、射程、目標選擇、Tracked、world格式或rules0.8.0。

## 問題與修正

舊搜尋只檢查格點是否可站立，便把相鄰兩點相連。旋轉45°的油桶旁，兩個格點都在擴張後的碰撞盒之外，中間路段卻可能穿進盒內。真正移動仍會拒絕穿越，因此敵軍停住後重新計畫，又選回同一條錯誤路線。

凍結的舊來源反例：油桶在(.25,0,.25)、45°，從(-2,0,1)巡邏到(2,0,1)。舊路線9點，其中(0,0,1)→(.5,0,1)不可通行；320個活動tick後仍未到達。只有GridNavigation變更的來源副本產生11點、0條不可通行邊，完成往返且每tick位移／通行檢查合格。兩份原始JSON及凍結C工程分開保存，不覆寫舊反例；這是共用.NET規則證據，非Unity或頭盔。

另一份舊來源反例使用真正任務產生器的原始端點：油桶(.25,0,-1.75)、45°，敵軍(-4.5,0,-1)往(4.5,0,5)。舊路線31點、有1條不可通行邊，320tick後仍卡在約(0,0,-1)。原始檔保留，不能拿後來的新原生場冒充同一次執行。

新搜尋在加入四方向鄰居前，以既有`ArenaWalkSurface.ClearSegment`核對整條格邊，與實際移動使用相同的0.3m半徑／0.05m取樣政策。幾何固定不變，每條無向格邊只計算一次，正反方向共用結果；每房25×25格、2500個sbyte槽，最多1200條無向邊，沒有無界記錄。四鄰居、原搜尋順序及每tick最多0.1m的移動檢查保持，不能穿牆、傳送或放寬碰撞。這不是完整三維NavMesh、斜坡／台階、群體避讓或連續碰撞求解器。

快取只存在於該房原始不可變幾何的GridNavigation實例，不在不同場次／房間間共享。Hold、Pause、Advance沿用正常管理命令，搜尋快取不自行移動敵軍。歷史錄製仍從原保存幀播放，不重新求路或改寫舊路徑；同一rules版本不代表跨軟體版本重新模擬會產生相同AI路線。

## 驗證

本機**723核心檢查**與**189真正Unity Editor測試**通過。新增6個核心檢查及5個Editor案例，涵蓋旋轉角往返、逐tick通行／速度、Pause與Hold、Linked外側兩房原點，以及封閉掩體不傳送。最初測試把x=-4..4的五沙包誤當封閉牆，實際兩側仍可繞行；該次checks原handle非零、log／來源／C binaries保留。改為x=-4.8..4.8、2.4m間距，使擴張後的步行範圍確實封閉；不是修改遊戲半徑或把失敗刪掉。

```powershell
python scripts/check-desktop-navigation.py --api-dll <本輪 C BuildRuns 的 API DLL> --runtime-root <新的 C runtime 根目錄>
```

原生工具開自己隔離API、Windows server及一個headless client，使用正常任務中的單一45°油桶與產生器原始巡邏端點。等待真正玩家入場後Begin，核對每個管理回應的appliedAtSequence、來源observed、Running／tick>0／非suspended，再觀察原NPC到達巡邏端點、Hold、Pause／Resume及Advance。端點使用單一連續live串流，20秒／最多256幀，逐幀確認序號不跳號、原來源擷取UTC＋elapsed年齡<1.5秒，距離仍<0.2m；不是把到達時間當來源時間。沒有遊戲按鍵、座標／姿態／命中注入或GPU／PCM診斷；不是玩家實際操作或client複本逐幀驗收。

完整連續world回放逐張檢查原玩家／原敵軍、健康／連線／Simulated、房間、攻擊關閉、保存位置的旋轉碰撞盒與活動tick位移上限；中間失效即使恢復也失敗。**保存幀之間缺少的tick不插值成路徑**，所以這部分只證明保存位置／位移，完整逐tick通行由共用規則／Editor案例另外證明。來源1.5秒及原玩家0.5秒政策不放寬，Begin來源仍15秒。先End及精確combat／world雙seal，再核對原admission結果、CSV與唯一server ACK，cleanup成功才complete。回放錯誤明確保存在獨立report。

Python新增7個觀察器反例，涵蓋原人物失效／替換NPC、保存位置撞盒／越界、NaN／bool、錯tick／傳送／凍結時鐘移動、suspended與不插補缺失tick，以及保留短暫端點／拒絕過期端點；另5 artifacts／7 first-person回歸通過。這19項不是原生或頭盔測試。

最終`desktop-navigation/20261101-125724-93f88fed`，原handle35386 exit0，**4項／128完整回放、113張Begin實際套用後的Running／Paused幀、9個檢查點**，fault0。接受Begin序號4，回放最早納入world15，即時最早讀到world17，兩者分開記錄，沒有排除之前的已接受來源。端點串流69幀連續17–85、tick150，最大收到時來源年齡0.117452秒，非RTT／效能基準；原玩家結果／CSV／雙seal／唯一server ACK與cleanup成功。五helper SHA前後一致，但不是完整依賴graph。

第一場`20261101-125121-d130384b`、41746 exit0／4項／133回放，為舊getter及初次live檢查點起的範圍，不當最終更早回放閘門的新驗收。第二場`20261101-125410-3d188963`、43827 exit1，原20秒getter未讀到短暫端點；關閉journal逐record rb／checksum／序號核對確認world90／91、tick150／152確已到達，最短距離2.861e-6m，不能稱來源沒到達。改為連續串流，沒有延長20秒或放寬0.2m。該場原失敗／無complete結果保持，closed分析不是補造live通過，也不是主機／網路根因證明。前兩場與Quest建置重疊，最終場建置已結束；不同負載不作因果對照。三場cleanup皆無殘留。

Windows與ARM64 Quest皆真正建置成功、同源`69d247a9ecfa7b42ee1e9314e0319869995f1876379850928f5725901e642fc2`且原scene／prefab ID一致。新Windows包`windows-player-0.37.1.zip`為82,642,694 bytes、SHA256 `cba3a25ba590c21f0b38b152042242b373ea656dce4c1ff434a742490f3b841f`，311 runtime檔／原launcher，新C展開19項真正核對／拒絕通過；非完整封裝GUI／跨機。APK60,313,650 bytes、SHA256 `723e57b59320b77a0b32523d092a75c6b5fe937325187be1f9fdc484505a980a`，0.37.1／46／ARM64，v2 debug簽章核對成功；receipt totalBytes不是APK大小，尚無頭盔安裝。

本輪真正build／原生／封存與CI結果統一列在[PROGRESS](PROGRESS.md)。建置前Windows305／Quest3／logs13共321檔及10份來源已精確另存navigation-history，原0.37.0／0.36.1 ZIP保持。第一人稱六張GPU是0.37.0的既有證據，不宣稱這輪重新擷取；本輪沒有改手臂素材或呈現程式。

[精確9959c64的CI41275385420](https://github.com/peca12968/vr-command-center/actions/runs/41275385420)完整成功：Linux723規則／459 HTTP／47 world、Python／素材及72 Node／248 Chromium；2 Windows限定skip不是原生／Editor。保存39檔＋log及ZIP9,675,831 bytes、SHA `565bde8df61294a09f141c7dc60332792c92cda2c25762f5f1d39bd18ec141a5`，與GitHub一致。新4 runtime68與F snapshot相同、前60 runtime3083／前F3540／486份瀏覽器證據保持，合計64場3151 runtime檔；保存SQLite不開連線。之後僅文件skip ci，測試來源不變。

原31筆、world371姿態失效、Windows完整HTTP startup及F吞吐未因這個可重現的尋路修正而解決。完整11項active；仍需多人持續操作、跨機／Wi-Fi、Quest／VIVE／MR與廠商硬體驗收。
