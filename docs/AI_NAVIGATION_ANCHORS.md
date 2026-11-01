# 敵軍實際起終點與格點路網

2026-11-01：Unity **0.37.2／code47／NGO29**，API/UI **0.30.1**、world格式與rules0.8.0保持。接續[旋轉掩體格邊修正](AI_NAVIGATION.md)，這次處理任務產生器的0.75m候選座標與0.5m路網之間的連接。

## 可重現問題

舊Find直接四捨五入起終點，要求這兩個格點可走，並只回傳格點路線。出生點本身可走，也可能因四捨五入到掩體中而沒有路線；非格點終點則可能被改成離原端點0.25m的位置，超過原巡邏到達界線0.15m，敵軍停住反覆重算。

兩份凍結來源使用真正ArenaSession任務產生器、相同Program與50個Runtime檔，在自己的C工程執行：

| 配置 | 原始產生座標 | 0.37.1結果 |
|---|---|---|
| 油桶(-4.6,0,-1)、yaw0 | 起點(-3.75,0,-1)，終點(4.5,0,5) | 原起點可走，四捨五入格點(-4,0,-1)被擋；路線0點，320tick仍在原位 |
| 油桶(5.1,0,5)、yaw0 | 起點(-4.5,0,-1)，終點(3.75,0,5) | 原路線30點，320tick仍停在約(4,0,5)，未到原端點 |

舊實際執行exit1／passed=false保存；只換GridNavigation的副本exit0，兩個案例皆30點、保留精確起終點、到達及逐tick通行／速度合格。這是.NET共用規則證據，不當Unity原生或頭盔。

## 連接方式與範圍

實際起點與終點必須先通過既有Walkable。每端最多連接所在半公尺格子的四個角點；起點→角點及角點→終點分別使用原ClearSegment核對方向，擋住的最近格點不排除其他可見角點。多起點／多終點BFS仍只有625格、四方向格邊與既有2500個sbyte快取，最後把實際起終點保留在路線內，不更改出生候選順序、NPC位置、碰撞盒或到達距離。

若近端點共享可見角點，而且兩點間的真實線段可通行，可以直接相連；被旋轉角落阻擋時仍走安全格邊，不走穿牆捷徑。接線只在所在格的角點內搜尋，不掃描全房遠距接線；沒有可用角點的次網格狹窄區域仍受既有網格解析度限制。三維地形、NavMesh、動態障礙與人群避讓仍需後續開發，這不是完整導航驗收。

原0.3m半徑、0.05m通行取樣、每活動tick最多0.1m、巡邏0.15m切換、Move再次檢查、Pause與Hold政策保持。沒有新網路欄位、RPC、Tracked或玩家移動變更。歷史回放讀原保存幀，不重新求路或改寫舊路線。

## 驗證與操作

新增6核心／6真正Editor案例，包括產生器兩種端點、往返與逐tick通行／位移、Linked最外側兩房、同格實際終點，以及不能直接切過旋轉角落；另4個Editor案例檢查有界原生觀察器，最終本機**729核心、199真正Unity Editor**通過。Python新增profile幾何／出生點及非格點目標反例、觀察器身分／完整tick／期限／cleanup反例；navigation13＋artifacts5＋first-person7＝25項成功。這些不是頭盔或25位操作證據。

```powershell
python scripts/check-desktop-navigation.py --case blocked-start --tick-probe --api-dll <本輪 API DLL> --runtime-root <新的 C runtime 根目錄>
python scripts/check-desktop-navigation.py --case non-grid-goal --tick-probe --api-dll <本輪 API DLL> --runtime-root <新的 C runtime 根目錄>
```

不帶case仍為原rotated-edge，不修改既有場次或工具預設runtime。每個新場使用自己的隔離API、真正Windows server及headless client；核對原任務幾何與產生座標，正常Begin／Hold／Pause／Resume／Advance、完整回放與原玩家戰績。沒有遊戲按鍵、姿態／命中注入、GPU／PCM或client逐繪製複本宣稱。

不帶tick-probe仍沿用原端點live串流20秒／256幀、距離<0.2m與1.5秒來源UTC年齡。明確tick-probe改用實際伺服器逐tick觀察核對原<0.2m／20秒界線，原巡邏0.15m切換沒有改；正常world仍10Hz，沒有為測試提高錄製或傳輸頻率。回放從原Begin接受序號實際套用後的全部Running／Paused幀核對，最早回放與live幀分開；保存幀之間缺失tick不插補路徑。End、精確雙seal、原admission結果／CSV／唯一server ACK及cleanup都成功才complete。五helper SHA僅所列來源，不當完整依賴graph。

## 原生逐tick觀察與保留的失敗

初候選`desktop-navigation/20261101-132748-57972625`原handle46348 exit1：20秒連續live收189幀、16–204不跳號，但沒有<0.2m端點，原failed／cleanup保持。關閉journal只rb／checksum／序號metadata核對，world81／82是tick141／143，位置皆約(4.5,0,4.799997)，距端點0.20000267m、forward相反；沒有tick142的位置，不能插補、用反向推定到達或改成通過，也不能據此推定主機／網路根因。初候選195 Editor及同源2c96a381...雙平台、初ZIP／19 launcher結果另存，不混稱最終199來源。

`--tick-probe`只讓本工具在自己Windows Development server明確傳`--vr-navigation-probe <新絕對目錄>`。普通遊戲、Editor、Android及client不安裝；從同一authority每次真正session.Tick後觀察當下NPC，沒有RPC、控制輸入、GPU／PCM或玩家姿態輸出。只收Running活動tick，最多180秒／4096個NPC row，保持完整最早tick；自動上限、倒退或漏tick皆不可當complete。準備時寫ready，收集期間不寫狀態，明確finish先停clock／收集再一次寫report；不是零擾動或效能基線。

每row有原NPC ID／room／health／feet、實際tick、同源observed管理序號與單調seconds；report綁原session／stream。工具要求完整tick1..N、原NPC、來源身分、位置／每tick位移及首次接受Begin的原生觀察起20秒內實際<0.2m，沒有把10Hz缺失位置補進來。原生tick證據的worldSequence明確null，回放檢查點另外讀取，不能依tick或時鐘硬配world序號。原生診斷先finish，再作後續Hold／Pause／Advance與End；其complete僅收集範圍，任務仍需正常結果／seal／cleanup。即使finish／report IO失敗，finally仍執行原生cleanup。

最終blocked-start場`20261101-134848-394c3763`，原30771 exit0／4項、268完整回放／248個已接受Begin來源幀；原生409 row連續tick1–409，實際端點tick142、距目標約0.100003m、首次Begin來源觀察後7.052074秒。non-grid-goal場`20261101-135057-d4dc1db0`，92372 exit0／4項、148完整回放／118來源幀；原生143 row連續tick1–143，最早<0.2m在tick141、距目標約0.1500001m，後續資料亦保存。兩者各9個回放檢查點、原玩家結果／CSV／雙seal／唯一server ACK、明確finish及cleanup成功。原生tick的world序號皆null；這是新場資料，不能補回首失敗場的tick142。兩場與最終Quest建置重疊，不當效能基線／因果對照。

一般五房`desktop-venue/20261101-135539-ac75f5f8`，14004 exit0／6項／7場，隔離／錯票／單房控制／重用／後續Linked及精確seal成功；runtime沒有navigation-tick-probe目錄，仍每房1位而非25位操作。

最終Windows／ARM64 Quest fingerprint `7d3e1a926f1b1c9176f03809af75de0c2af7be0e5f3e4ec24851664327aa4f92`、原scene／prefab ID一致。真正199 Editor與最終Desktop70410／Quest21212均exit0；初候選2c96...的195 Editor／雙平台及普通0.37.2 ZIP另存，不用檔名或版本號冒充同一來源。可攜主包為`windows-player-0.37.2-final.zip`：82,645,932 bytes／SHA `25dd1ee56234cd7da3da1f9671877b6c8967a41f03d71f903f3008558425d5c4`，311 runtime檔／原launcher，新C展開19項真正核對／拒絕成功，非完整GUI／跨機。

最終APK82,782,417 bytes／SHA `d804087c10e2c0b376d3eb2e3bd875a5ef3bf97760c0a6b30c5a0dadc47b5eaa`，0.37.2／47／ARM64／min32 target35、v2 debug簽章成功，未安裝頭盔。ZIP索引105項的compressed資料為60,306,850 bytes，非payload區段22,475,567 bytes；初候選則60,310,826／60,289,375／21,451 bytes。實際APK增量主要不屬現行ZIP索引資料，不能當成遊戲內容增量／執行效能或唯一原因證明；兩份raw均保留、不重新封裝，receipt totalBytes不當APK大小。

正式build、封存與CI以[PROGRESS](PROGRESS.md)本輪紀錄為準。原64 runtime3151與F snapshot、前F3719保持；新4 runtime74逐檔相符，合計68場3225檔，新F190及525份前瀏覽器證據核對。舊321 binary／logs及10選定來源、初候選另一組321／10與原ZIP先精確封存，另存4份原commit來源blob，不當完整來源備份。原端點getter逾時、31筆／world371姿態失效、Windows完整HTTP startup、F吞吐與實機驗收各自保留，未由本輪修復。

完整11項active，仍無頭盔。持續推進多人操作、複雜場地、跨機／Wi-Fi、Quest／VIVE／MR及廠商硬體。
