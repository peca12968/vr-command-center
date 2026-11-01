# PC 視窗觀察與姿態間隔

`check-desktop-active.py --observer-sequence`建立自己的隔離API、一個server、25個原生Windows client，其中一個可見。這是零按鍵、25接收端的同機Simulation；延續原始入場、0.5秒姿態／1.5秒來源、完整Running連續性、個別戰績、CSV及精確雙seal檢查。它不提交環境／AI命令；選用`--operator-ui`只開啟閒置Chromium控制台，應有零個表單請求。不可與`--operator-controls`合用。

```powershell
python scripts/check-desktop-active.py --api-dll <同版API.dll> --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns" --observer-sequence --operator-ui
```

需由操作員或computer-use執行以下觀察；腳本不注入遊戲輸入，也不自行啟動桌面自動化。只能操作這次`observer-config.json`指定的原可見遊戲程序／視窗。

1. `observer-ready`階段先選取並檢視唯一自有遊戲視窗，檢視後另寫`observer-ready.done`，限40秒。此選取不屬於量測中的12次呼叫。
2. 腳本啟動自己的normal-priority獨立心跳、8秒基線，進入`observer-sequence`後開始120秒有界窗口。
3. 固定順序執行Accessibility三次、Screenshot三次，再重複一輪，共12次。Accessibility只取文字，Screenshot需實際返回至少一個image；SDK可能只回變動區域，不能據此宣稱全畫面像素測量。全程不送按鍵／點擊遊戲動作。
4. 每次在**呼叫端**以UTC及單調時鐘括住API，僅保存index／epoch／mode／同一windowId／起訖／image數量／成功返回旗標，以及原session／player／PID／win32與主機名稱SHA256。JSON最多64KiB，不保存圖像、可及性內容或憑證。這不是可信輸入簽章或主機認證。
5. 先檢視實際結果，再獨立保存`observer-operations.json`及`observer-operations.done`；未知／失敗寫`observer-abort.json`並讓本輪失敗，不能補造成功記錄。腳本校驗精確12次順序、同視窗、模式及單調不重疊。
6. 8秒quiet-after後明確finish心跳、Pause及最後26份複本擷取；另行正常End、兩份精確seal、25份原admission結果／server ACK／CSV、完整回放及cleanup。timer子程序被追蹤，寫入未停不能snapshot；診斷失敗也必須收尾原生程序。

`--observer-sequence`隱含既有server＋visible稀疏姿態診斷，只有server包含PlayerLoop；仍是1200秒／4096列／256streams與原replication240秒／4096列上限。一般遊戲／Android不安裝新診斷，沒有新Unity模組。原玩家姿態、槍口、Tracked資料、規則及wire不變。

零彈藥本身無法證明未移動：新guard逐來源sample及完整回放參考窗口核對原玩家名冊、head／muzzle／forward／magazine／reserve／reloading／fireSequence。短暫移動後恢復仍失敗；connected／rig失效另由原參戰檢查判定，不混稱輸入。比較同一資料表現來源，不拿REST的float短格式與raw journal的double展開直接當移動。

原handle確認terminal且cleanup乾淨後，可執行唯讀分析：

```powershell
python scripts/analyze-observer-sequence.py artifacts/desktop-active/<本輪目錄> --output artifacts/<新的分析檔>.json
```

分析器只讀關閉的JSON／原runtime-snapshot，不開SQLite、不改raw；輸出必須是原場及原runtime之外的新檔。驗證原visible connection、只用source1、server／client時鐘、PlayerLoop結構及獨立心跳實際coverage。呼叫端／native的UTC與單調差達0.05秒、不同主機或不足coverage，窗口數值為null，不補零或跨場校準。不同point分開裁切／聯集，不把PoseSend、PoseReceive、PoseAccepted、MainThreadGap與PlayerLoop相加。CPU保留完整原Update sample括號，不按外部呼叫長度比例切CPU或將其歸因於截圖。這些point沒有world序號，不硬配保存世界幀。

## 2026-11-01 實際範圍

`20261101-102507-8f94afad`原handle8001 exit0，**8項／52快照／26完整報告、28237 Running列、1153全回放／2參考、25份原結果／server ACK／CSV／雙seal**成功；world1153／combat0／ledger through31，所有玩家零彈藥／命中／擊殺／損傷、健康100。UI閒置110.018秒、零requests／attempts，全部cleanup乾淨。

12次呼叫都被診斷及心跳覆蓋，未見已記錄target pose gap、MainThreadGap或心跳>100ms gap與這些短呼叫重疊。心跳88.7660042秒、最大wake間隔10.7578ms；Accessibility呼叫33.2628–78.5295ms、Screenshot96.5465–161.07ms。**這是SDK排隊／helper／結果返回的整段時間，不是GPU／CPU／FPS／RTT。** 固定順序、單機單場與零記錄大gap不證明因果、沒有微小jitter或排除觀察擾動。

live場之後才新增stationary guard及回放閘門，沒有將它冒充live第9項；關閉journal以rb／SHA／序號獨立讀回983幀（122–1104），同raw baseline比較通過。第一次讀回混用REST與raw浮點展開，983幀皆誤報head／muzzle差異；失敗檔保留，改用同一raw序號baseline的新v2證據，不改原場／原數字，也沒有放寬遊戲容差。完整來源與保存數量見[PROGRESS](PROGRESS.md)。

API/UI0.30、Unity0.36.1／code44／NGO29、e0594513...、原179 Editor與雙平台receipt保持；本輪沒有Unity／產品.NET／APK重建。舊31筆失效及前場world371／26報告失效仍未修復。完整11項active，25位同時操作、跨機／Wi-Fi／頭盔、MR與廠商硬體另驗。
