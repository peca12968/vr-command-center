# 原生多客戶端自動化動態驗證

## 五房 UDP 丟包驗證

```powershell
python scripts/check-desktop-exercise.py --api-dll <API-DLL> --player-exe <Windows-Player-EXE> `
  --runtime-root <本機測試目錄> --mode both --players-per-room 5 --seconds 40 `
  --udp-periodic-loss --link-metrics
```

`--udp-periodic-loss` 使用同機 UDP 轉送器。所有原玩家入場後、發出 Begin 前開始丟包。每位玩家的上行、下行各自計數，每遇第 20 個 UDP 封包就丟棄，持續至個人戰績交付。啟用時會一併量測轉送流量。可加 `--link-metrics` 記錄應用層往返探測，並以 `--udp-traffic --link-metrics` 重跑相同條件的零注入對照。

各模式保存原生客戶端、共通 Running 區間的流量和丟包邊界。檢查器要求每一條原連線在該區間的兩個方向都有實際注入丟包，並逐場核對原射擊、換彈、完整回放、雙封存及原連線的個人戰績確認。報表只保存封包計數和負載長度。週期性丟包代表本機受控網路條件，與無線突發丟包、跨機環境和實際場館容量分開驗收。

## 五房射擊與戰績驗證

`--marksmanship` 沿用 Windows Development batch Client 的短場輸入。任務每房放置六個正常油桶，讓敵軍出生候選只在第一列保留五席正前方的位置。五名玩家各對應一個由遊戲伺服器實際配置的原始目標，開場前逐一核對其房號與座標。敵軍守備，關閉自動攻擊。

```powershell
python scripts/check-desktop-exercise.py --api-dll <API-DLL> --player-exe <Windows-Player-EXE> `
  --runtime-root <本機測試目錄> --mode both --players-per-room 5 --seconds 16 `
  --marksmanship --check-frame-review
```

每位玩家經既有武器 RPC 提交兩次射擊及一次換彈。驗證逐筆比對原射線的目標、命中、換彈、擊殺、各格統計和封存事件序號，並要求各席兩發兩中、一擊殺、命中率 100%。連線場次的 ZIP 亦與六份個別 CSV 比對。測試由程式產生輸入，玩家傷害與命中由遊戲伺服器判定。

## 多人動態與正常管理命令組合

功能a58a527的[CI41356457654](https://github.com/peca12968/vr-command-center/actions/runs/41356457654)完整success：772核心／459 HTTP／47 world、6 pipe／38離線硬體CLI、Python含11 exercise／素材、89 Node／296 Chromium。2 Windows限定skip非原生／Editor證據；console49／control13／hardware26及decoded log的完整hash見[PROGRESS](PROGRESS.md)，1513＋49＝1562 browser、nativeUI7＋2保持。後續文件skip ci，測試精確來源a58a527。

原Linked／Independent生成器報告最大活動tick跨度分別361／550（18.05／27.5秒），全部明確Requested收尾；finish後停止生成輸入，但原姿態／結果流程持續。後面五房依序收尾增加了靜止回放，2909全回放或2627 Running幀不能當成全程動態輸入。

新增選用旗標：

```powershell
python scripts/check-desktop-exercise.py --api-dll <同次API0.31.0完整建置的DLL> --runtime-root <SSD runtime根目錄> --mode both --players-per-room 5 --seconds 16 --operator-controls
```

基本輸入窗口後，生成器繼續移動；先等每人兩發接受，再逐場送SetEnvironment／SetEnemies。每房一個原敵軍、autoAttack=false；雨夜雷電Patrol後Fog Day Advance。使用每個原UUID與當下expectedSequence，接受回條先存；同session／非duplicate／原commandId／序號遞增後，另等真正來源observed fence、Running／非suspended、至少20tick及全員walking，原存活敵軍ID／room／health保留、每位至少移動1cm。仍受原60活動秒／240秒儀表窗口限制，沒有為測試延長或重設。正常命令不等於操作員UI或真人操作，沒有新增autoAttack傷害驗收。

最終30項／6場／2909完整回放、50原結果／6CSV／雙seal與原server ACK成功；12階段24命令、24個before／applied參考packet和statistics在回放精確相同。Linked雨夜巡邏11幀、霧天推進12幀全部25位walking；五房各有5位walking。附加closed JSON讀回依每房每個已接受環境／AI序號逐幀核對2627 Running幀及敵軍身分，無跨房狀態不符；這不是第31項live檢查，沒有對齊獨立時鐘。預跑7／202、未選用新旗標5／179也成功，兩模式仍保留每人兩發0中0殺／health100精確斷言。

新4／完整11項Python負向測試涵蓋原意圖／session／順序與回放參考不一致，原27 active及5 artifact通過。新C232／F與666來源snapshot保存核對，前輪C340／326history／666舊來源及原ZIP／APK保持；沒有新Editor／Unity／Quest／本機全browser／GUI／GPU／頭盔，原231 Editor及6098同源版本保持。精確CI另見[PROGRESS](PROGRESS.md)，完整11項與原長場反例保持active。

功能提交a4ff77c的[CI41354866315](https://github.com/peca12968/vr-command-center/actions/runs/41354866315)完整success：772核心／459 HTTP／47 world、6 pipe／38硬體離線CLI、Python含7新exercise／素材、89 Node／296 Chromium。2 Windows限定skip不代替本文件原生／231 Editor證據；console49、control13、hardware26及decoded log的精確hash見[PROGRESS](PROGRESS.md)，前88 CI檔保持。1464＋49＝1513 browser，nativeUI7及本輪serverUI2另列。後續文件skip ci，測試精確來源a4ff77c。

Unity **0.40.0／Android code50／NGO29** 新增明確選用的Windows Development batch Client輸入模式，讓每個原生客戶端透過既有桌面移動及武器意圖路徑執行短測試。它產生的是 **AutomatedSimulation**，不是實體鍵盤、25位真人、頭盔追蹤、LAN或網路容量驗收。

```powershell
python scripts/check-desktop-exercise.py --api-dll <API0.31.0同次完整建置的DLL> --runtime-root <SSD上的runtime根目錄> --mode both --players-per-room 5 --seconds 16
```

工具使用新隔離API、25份原admission／短效票券、真正Unity Server／Client UDP及NGO連線。先Linked25端，全部結束後再五個Independent房間各5端；沒有可見遊戲視窗或GPU觀察。底層旗標為 `--vr-desktop-exercise <新的本機絕對目錄>`，一般啟動沒有元件；Server／Host、Editor、非Development、非Windows、非batch及XR情境不得啟用。Quest端不安裝此模式，沒有搬動Tracked頭手或新增測試RPC。

## 輸入與限制

每位owner從自己的已接收戰鬥tick開始：以0.2方向量通過原 `DesktopPreviewControls.Move`／`ConstrainDesktop` 產生0.4m/s的前後運動，每40tick反向，約0.8m幅度；相對第20tick提供第一次射擊、第60tick換彈、第120tick第二次射擊。武器意圖保留到原武器分支真正呼叫SubmitWeaponRpc才記一次提交，仍經簡報抑制、Ready、Running、原ownership／冷卻／姿態與伺服器規則。提交次數不等於接受次數，後端統計及回放另驗。

測試模式忽略實體桌面移動／射擊／換彈輸入，普通模式不變。Paused／未Ready／結束時不產生動態輸入；第一個有效owner／connection／room固定，變更不重新綁定成功。最多1200活動tick（60秒）及240秒程序收集窗口，超界停輸入、report不當完整。輸入模式只供短測試，未宣稱能在900秒或4小時任務持續操作。

只保存有界計數與自己的player ID／connection／room／PID／起訖tick及時間，不存票券、key、畫面或逐pose清單。每0.1秒查自己的finish.request，明確finish後才寫report；之後停止生成輸入但仍保持原姿態傳送／結果流程。report.complete只表示本次產生器明確收尾，不能單獨證明遊戲成功；退出／timeout／owner變更／tick倒退等不完整。

## 接受條件與實際結果

真正Editor **231／0 skip**（原224＋7）通過。新7項Python證據驗證檢查原Begin fence、實際API名冊的admission／seat／room、失效後恢復仍拒絕、未授權Pause及原程序／連線報告。世界封包本來只有observedSequence，沒有名冊副本；工具分別核對原API名冊及封包到達原Begin的序號，不虛構欄位。

兩個初失敗分開保留：`053940-74608ff9`在啟動玩家前用錯memory helper名稱；`054005-b0589055`在五端已移動後錯讀不存在的packet.observed而KeyError。只修測試腳本，後改用真observedSequence及原名冊，不當遊戲姿態根因或修復。兩場cleanup空、原C／F資料保留，沒有補成功旗標。

`054142-2d7a0827`五端Linked smoke **5項／139完整回放**通過。最終`054350-5fe3e1a0` **18項／6個正常場次／1951完整回放**通過：Linked25端與五房各5端，所有原玩家均有原生提交、接受的移動及換彈幀、每人2發／0命中／0擊殺／health100。50份原admission結果、6份逐場CSV、雙seal及原server ACK一致，無timeout或send queue full，原程序全部terminal才snapshot。

Linked的159個Running保存幀中，有 **154幀全部25位walking=true**。其餘五房各有全部5位移動的保存幀，逐房數字見simultaneous-motion-readback.json；這是原closed replay讀回，不是第19個新live檢查，也不把跨房不同來源時鐘硬配成同一GPU畫面。五房Room1 Pause接受序號另等來源真正Paused，tick停住；其他四房tick前進，Resume使用原accepted fence，不能把任意Paused幀當作例外。

原0.5秒姿態／1.5秒來源、反瞬移、來源年齡、佇列與封存政策不變。完整回放逐幀核對所有Running body，來源擷取gap達1500ms即失敗；失效後恢復不能抹去反例。Paused只限該房明確Pause／Resume序號窗口。即使新短場通過，舊900秒31筆失效與world371仍未解因，不能稱根因修復或25位持續人工操作完成。

未啟用新旗標的普通入場／撤銷／重連另 **8項／355幀**通過。新版server可攜包 **106項／725回放／10份原結果與各CSV／雙seal及ACK**成功，parent-death仍為故意未seal的獨立反例；玩家包19離線檢查成功。server包中的browser只觀察正常UI End與原來源收尾，不能代替Windows server啟動器GUI驗收。原PickerHost阻擋仍待，未再次操作該視窗。

## 交付與保存

Windows／Quest同源fingerprint **6098b4857b36d4b24a6b4ab275cbd64b17aa12353329cad9c96f36a9d339911b**，原Scene／prefab ID保持。

- 玩家ZIP **82,651,129 bytes／SHA256 `24aef191b5fc608430a5f131ffd34aabf2ec0b4938fefd3f2c8461c958cc50e2`**，311 manifest／ZIP312含manifest。
- Server ZIP **82,672,917 bytes／SHA256 `642e5307cf3d62af7b136d9baaca06c2d9cd9c3bd1ed66c7d4e915803a7f8710`**，311 manifest／ZIP312含manifest；啟動器仍1.1.0／source fb57807d...，真正frozen compiler input保持。
- APK **60,358,086 bytes／SHA256 `adb9a8bc6c94b0e9842c1498f5a74417071daf388f79622f742f060e3c098fa5`**，實際aapt確認ARM64、min32／target35、versionName0.40.0／code50；v2 debug簽章，未裝頭盔、不是商店release。

SDK批次入口因PowerShell腳本執行策略未執行，改直接呼叫原Unity executeMethod，沒有調整執行策略或安全性設定。舊0.39的321 binary/log及5來源共326檔先封存並核對C／F；原APK0310fe18...保留於history，current quest/VrCommand.apk是新APK，不能把兩者混稱未改。666份本輪來源凍結於C snapshot，原始碼仍在F及GitHub。

新4個exercise場（含2 failed）、普通admission與server包共 **C340／F snapshot** raw hash一致；舊75硬體runtime、四舊報告117／274／163／327、舊管理／server ZIP及歷史證據保持。保存SQLite不開、正式5080不動。API0.31.0／UI0.31.2不變，本機沒新跑全browser，原1464 browser與nativeUI7保持，新server browser2另列；CI精確來源與artifact見[PROGRESS](PROGRESS.md)。完整11項active，跨機／25位真人、頭盔／MR／廠商硬體、舊31／371／startup／F吞吐及完整GUI仍待。
