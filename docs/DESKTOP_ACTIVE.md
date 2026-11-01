# 實際 PC 輸入與25端狀態對照

2026-11-01 新增[`--observer-sequence`零按鍵觀察流程](OBSERVER_TIMING.md)：25接收端、12次有界文字／截圖呼叫、獨立心跳與原姿態診斷同場保存。原8項／52快照／1153回放及25份結果成功，後補guard對關閉來源983幀讀回通過；並非新live第9項或根因修復。原動態流程與失敗樣本保持。

2026-11-01 新增`--operator-ui`，以真正Chromium控制台表單執行原環境／AI情境；Begin／Pause／Resume／End仍由fixture控制，不能稱本輪所有生命週期都經UI。一位實際W／Space／R／Space、24接收端的最終新場14項／182快照／1132完整回放與25份結果／server ack通過；**同輪第一場一幀參戰失效、API啟動逾時及一次確認順序失誤／換彈逾時均保留失敗**，不以最後成功宣稱修復。細節見[PROGRESS](PROGRESS.md)。

```powershell
python scripts/check-desktop-active.py --api-dll <同版API.dll> --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns" --input-timeout 40 --operator-ui --diagnose-visible-pose
```

`--operator-ui`隱含operator-controls，需現有Node與`tests/browser`的Playwright依賴。助手只接受本庫新desktop-active目錄、Simulation／headsets0、canonical HTTP127.0.0.1且非5080的URL與同session五房world header。它使用這次臨時Master登入真正控制台，明確選原場，再以表單reload／fill／submit；只用額外GET核對UI序號，不用Node fetch／Python POST代替這六個SetEnvironment／SetEnemies。玩家動作仍由真正遊戲視窗輸入，沒有管理REST／RPC姿態或武器注入。

最多三組請求，助手以單調時鐘180秒界線與200ms輪詢觀察自己的finish／期限，不是可中斷OS卡死的外部watchdog。每個表單最多三次明確意圖，只有已拒絕409才能refresh再提交新UUID；200即停止、未知結果／5xx不重做。`active-ui-attempts.json`立即保存每次真正POST body、HTTP status及回應，Python另核對原request／session、兩個動作順序、expectedSequence／UUID／非duplicate、精確環境／AI與接受尾界，仍須等Running來源observed fence。

三組回應為`active-ui-response-1..3.json`，`active-operator-controls.json`另外記transport=ConsoleUi；未選UI仍走原API模式，舊缺欄位NotRecorded。新回應時間包含refresh／表單／瀏覽器等待與讀取，非RTT。finish先關瀏覽器、等待自己的helper terminal後寫`active-ui-report.json`／`active-ui-cleanup.json`；complete只代表助手這段生命週期完成，還需三組成功、無page error與原生／全程連續性所有閘門。即使助手關閉／報告IO失敗，也必須獨立執行遊戲／API cleanup，不能跳過writer停止與一次snapshot。

`--diagnose-visible-pose`明確選用既有稀疏收集器，只安裝於server與唯一可見client，僅server加PlayerLoop；不是25份姿態診斷。新`active-pose-programs.json`綁定原程序、目錄與連線，正常在25份結果／精確seal後finish／validate再停程序，失敗cleanup也嘗試finish保留報告。原1200秒／256 streams／4096稀疏列及舊replication240秒界線保持；不是延長UI或遊戲門檻。diagnostic complete不是任務通過，clock／coverage與無world序號限制沿用[POSE_CONTINUITY](POSE_CONTINUITY.md)。

2026-11-01 新增`--operator-controls`：在同一25端任務的實際射擊／換彈前，透過正常管理API切換Storm／Night／lightning／Hold；擊殺後測試Storm／Patrol與Fog／Day／Advance。這不是本輪操作員瀏覽器UI測試，沒有注入玩家動作或敵軍座標。真正13項／182快照／26報告、1359完整回放與25份個別結果／server ack成功，完整證據與限制見[PROGRESS](PROGRESS.md)。

```powershell
python scripts/check-desktop-active.py --api-dll <目前同版API.dll> --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns" --input-timeout 40 --operator-controls
```

每組環境與AI命令先保存兩份原`CommandReceipt`，拒絕外場／duplicate或非遞增接受序號；輪詢要求非suspended、Running、tick前進且`observedSequence>=最後接受序號`，再核對真正來源天氣／日夜／閃電／visibility／behavior／autoAttack。接受不等於套用；逾時仍保留`applied:null`與原回應，不猜Begin或其他場序號。Patrol／Advance從命令前來源基準至少前進20活動tick，原敵軍ID／room／health均保持，至少一個仍活著的敵軍移動>1cm，不能以死敵移動或重生替代策略。

各Pause檢查點仍以實際保存packet為準，比對25個client＋server的weather枚舉／night／lightning、全名冊／連線／姿態／彈藥／健康及敵軍位置／fireSequence；活躍玩家輸入與靜止24人的隔離檢查保持。共用capacity helper只有明確傳入時才接受該組環境，預設仍要求Clear／Day／無閃電，未知枚舉／非bool值拒絕。這是離散檢查點與保存Running樣本，不宣稱連續GPU畫面或每packet到達。

`active-operator-controls.json`保存接受回應及來源首次觀察到符合條件的世界序號／observed／tick／移動量，結果也收錄於`active-result.json`；未選此選項為null，舊缺欄位仍NotRecorded。原default四步流程、40秒UI確認／240秒probe／4096列界線與0.5／1.5秒遊戲政策保持。End、個別結果、精確雙seal／CSV、server ack及全程回放／所有觀察Running列閘門不變。

2026-11-01 同版0.36.1／e059新場10項通過：實際W／Space／R／Space、130快照／26完整報告、1420全回放與25份個別結果／精確雙seal／CSV一致；所有原連線server ack逐一核對後才停程序。仍是一位操作、24接收端、同機Simulation；原逾時與舊失效證據保持，範圍見[PROGRESS](PROGRESS.md)。

`scripts/check-desktop-active.py`使用現有成功的Windows播放器與自己的API、憑證、全新SSD runtime，開一個五房Linked世界、25個原生client。**一位玩家實際操作，24個接收端；不是25位同時移動／射擊，也不是25台或頭盔驗收。** 一個可見視窗由人員或computer-use操作，其餘24端無圖形；合成頭手仍為Simulation。

```powershell
python scripts/check-desktop-active.py --api-dll artifacts/build-report-v1/bin/VrCommand.Api/release/VrCommand.Api.dll --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns" --input-timeout 40
```

任務使用一般API配置：每房一個Hold且不自動攻擊的敵軍，一個位於房內(-4.125,0,-1)的油桶使真正敵軍候選網格避開前兩點、採用(-3,0,-1)。Room3第一席玩家面向正Z，射線從既有真正槍口前進。這不是指定敵軍座標或注入命中；不改rules0.8.0、碰撞盒、追蹤／pointer／muzzle或資料契約。

啟動輸出`active-input`後，依序在唯一的自有遊戲視窗**按一次W、一次Space、一次R、一次Space**，每個階段確認畫面後才在該次目錄建立對應`move.done`、`shot.done`、`reload.done`、`kill.done`。檔案只承認已觀察的操作，不產生遊戲輸入。等待下一階段再按鍵，勿按其他玩家視窗或以滑鼠點擊射擊。W單次短移動須大於0.02且小於0.4公尺，長按超出此訓練流程範圍會失敗。

每一步皆驗伺服器接受的移動／彈藥／命中／擊殺及其他24人未收到本人的輸入。預期敵軍100→50→0、主玩家彈匣30→29→30→29，備彈90→89；最後耗彈2／命中2／擊殺1／100%，健康100。換彈完成才進入下一步。每步由控制台Pause凍結世界，核對所有client與server的全名冊與列出的玩家／敵軍狀態欄位、連線身分、PoseAccepted、頭部位置、彈藥、player及enemy fireSequence。

讀取[本地接收端探針](DESKTOP_REPLICATION.md)原有的唯讀介面；每epoch編號不變，預設`--capture-batch 1`逐端要求及等待輸出，避免26份快照同時序列化／寫檔。可明確用26重現原fan-out觀察，但不得挑掉失效列。相同epoch各快照時間不同，參考tick是下界，並非跨端同一瞬間或封包延遲量測。資料獨立放`artifacts/desktop-active/<時間-識別>/`及自己的latest pointer；不覆蓋desktop-capacity入口。

**檢查點成功仍不足。** 完整report自初次成功capture起，所有觀察到的Running列都須Ready、coherent、玩家25／connected25／健康總和2500；同一連續Running區間的新tick觀察間隔須<1.5秒。刻意Paused的無新tick時間不當遺失；不過濾Running失效列。End後授權SSE從頭回放，序號必須連續，所有保存參考packet／statistics須逐字值一致；初始至最後參考之間每張保存的Running世界幀亦核對全名冊／Simulated／可參戰。這些是保存及觀察到的樣本，不宣稱所有瞬間／每packet或實際RTT。

client探針在End前明確finish，server探針在精確seal後finish；不要求client的探針收到Ended。所有原玩家程序仍保留至自己的final結果送達、確認及斷線：核對原player／admission／room、world stream／sequence、combat acceptedSequence、ledger through與七統計，client只允許一個原連線。另從自己的server log核對25個不重複ack ID，須精確等於原nativeConnectionId集合且無timeout，才停玩家程序。client phase的final＋disconnect不能單獨替代server ack。最終CSV核對25人全部數值與精確戰鬥尾端。所有追蹤writer退出後才一次回F snapshot、保留SSD原件；失敗亦收尾、保留資料，不手工更改passed／failed。輸入等待是操作員觀察時限，不改0.5秒姿態、1.5秒來源或入場授權；probe模式最多每階段40秒以保留原240秒探針上限。

對照可用`--without-replication-probe --input-timeout 90`。該模式只驗權威／保存世界與報表，**沒有接收端報告**，不能把空集合判定當接收端通過；`localReplicaContinuityChecked=false`。它仍核對保存Running幀、實際輸入、原始日誌與精確seal，不修改來源標記。較長等待只讓操作員確認／恢復UI焦點，不放寬遊戲時序。

首次fan-out場雖8個功能檢查／130快照成功，之後逐列稽核仍發現65個失效Running列，26份報告皆不符合新全程條件；原始passed結果保留為舊範圍，不能稱全程通過。分批場及無probe對照的實際結果見[PROGRESS](PROGRESS.md)。一場對照差異不證明失效由診斷取樣引起，也不證明舊主迴圈停頓已修復；原始反例持續保留。實際GPU截圖由Windows視窗觀察，沒有新Unity GPU／PCM探針、FPS／音效／頭盔測量。

新接受檔增加`individualResults`／`acknowledgedResults`，另存`active-player-results.json`的delivery、結果與實際serverAcknowledgedConnections；空集合、missing／duplicate結果、舊admission、錯尾界或ack均失敗。舊檔缺欄位表示未記錄該項，不補造0／成功或改寫原passed範圍。確認檔仍必須在正確active-input階段且已看見操作後才建立；UI或畫面不符先重新觀察，已逾時不得補寫done把失敗翻成成功。
