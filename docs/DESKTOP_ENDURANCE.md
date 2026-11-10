# 長場原生自動化輸入

## Windows 0.50.0 合併場姿態失效

2026-11-10 以 Windows 玩家包 0.50.0 與解壓管理包 0.31.108 測試同機合併場 25 席。原命令使用 `--mode linked --players-per-room 5 --seconds 900 --endurance`。場次 `20261110-210741-90fd6105` 在保存第 6,843 格失敗，退出碼 1。該格擷取時間為 720,607 毫秒，距前格 784 毫秒。第 1、2、5 房共四席姿態無效，下一格全數恢復。

原生回放讀至封存第 6,849 格，確認只有第 6,843 格出現上述失效。25 席原連線均收到原戰績，伺服器逐席確認。原戰鬥日誌封存 1,800 筆射擊，各席發射 72 次及換彈 36 次。C／F 89 檔雜湊相符。診斷結果保存在原場次的 `continuity-readback.json`。目前證據能確認姿態失效及保存空窗，根因仍待定位。

同一工具可在 Linked 長場明確加上 `--pose-continuity`。沿用既有的原生稀疏診斷，伺服器加 PlayerLoop 邊界，所有玩家各自保存傳送及主執行緒紀錄。收到原結算確認後才停止診斷。若原測試失敗，保留原退出碼和回放結果，並另記診斷是否完成。原生報告和程序對照在 `multiplayer-continuity.json`。

診斷旗標已在同機 25 席的 60 秒排演取得 26 份報告。另短暫暫停一個受控測試玩家，驗證原測試仍以退出碼 1 保留失效，六個原生程序均寫完報告。 [測試紀錄](PROGRESS.md#2026-11-10-windows-0500-合併長場與姿態取證)

## Windows 0.49.0 長場複驗

2026-11-10 以 Windows 0.49.0 的解壓遊戲執行檔搭配管理包 0.31.83，沿用 `--mode both --players-per-room 5 --seconds 900 --endurance --replay-workers 5`。合併場有 25 席，獨立場每房 5 席。兩種模式各運行 900 秒，每席從正常輸入路徑送出 90 次射擊及 45 次換彈。獨立第 1 房暫停期間維持 tick 42，另外四房仍各前進 49 至 50 tick。

`artifacts/desktop-exercise/20261110-112148-71bac159` 退出碼 0，18 項通過。合併場核對 8,558 格回放，獨立五房依序核對 8,513、8,516、8,566、8,527、8,531 格。六場共 51,211 格，其中 51,003 格為執行中。逐席比對 50 份戰績、50 次伺服器確認及 6 份 CSV。世界回放到達各自的封存末格，另外由六個原戰鬥日誌的封存紀錄重算 4,500 筆射擊事件，與全部原戰績相符。

完成後活動場次及剩餘測試程序均為零，C／F 的 174 檔執行資料逐檔 SHA-256 一致。證據涵蓋單台 Windows 的自動化桌面輸入，跨機 25 人、頭盔追蹤及實體場地容量各自待驗。 [開發進度](PROGRESS.md#2026-11-10-windows-0490-雙模式長場複驗)

## Windows 0.48.1 長場複驗

2026-11-09 用 Windows 遊戲 0.48.1 及既有管理包 0.31.48 重跑兩種拓撲。合併場 25 席，獨立五房各 5 席。兩種模式各持續 900 秒生成移動、射擊及換彈，使用原生玩家程序及正常遊戲輸入路徑。執行命令沿用下方 `--mode both --players-per-room 5 --seconds 900 --endurance --replay-workers 5`。

`artifacts/desktop-exercise/20261109-151952-6c10c16e` 退出碼 0，18 項通過。每席完成 90 發射擊、45 次換彈。六場逐格核對 51,342 格完整回放，其中 51,079 格為執行中。50 份玩家戰績、50 次原伺服器確認、6 份 CSV 與雙封存一致。活動場次和剩餘測試程序均為零，C 與 F 的 174 檔執行資料副本逐檔 SHA-256 相同。此輪為單台 Windows 的自動化桌面測試，跨機、真人操作、頭盔與實體場館容量待實地驗收。 [進度](PROGRESS.md#2026-11-09-windows-0481-雙模式長場複驗)

## 0.41.1 歷史長場

最新[CI41367545805](https://github.com/peca12968/vr-command-center/actions/runs/41367545805)對65b072d完整success：772/459/47/6pipe/38CLI/Python/素材89Node296Chromium，2Windows限定skip。新51browser與control13/hardware26原ZIP逐hash保存，總1819browser/nativeUI11分列；65只GUI fixture roster，native4bdf、包說明c55、242/4ebd雙平台與新900秒長場均另有本機證據。以下659/c55及failed為歷史，最新交付以上述及PROGRESS為準。

[CI41364751791](https://github.com/peca12968/vr-command-center/actions/runs/41364751791)對fixture來源659f026完整success：772／459／47、6pipe／38CLI、全部Python含14 exercise／素材、89 Node／296 Chromium，2 Windows限定skip非原生／Editor證據。console51／control13／hardware26與完整hash見[PROGRESS](PROGRESS.md)；原三次CI失敗保持、1717 browser／nativeUI7＋2另列。原held PUT必須fulfilled=true／只有1請求後隔離斷言才過，原15／30秒／產品期限不變，不證舊逾時根因。659只fixture／文件，242 Editor／4ebd建置與原生helper仍4bdf；新900秒另以真正handle33928完成；CI不代替原生接受。

當時候選 **Unity0.41.1／code52／NGO29**、242真正Editor／0skip，同源Windows／ARM64 fingerprint **4ebdcd12b9cbf1d00f342cb25dbec21d84f60c048284d8333cb8fa01c42a495c**，原Scene／prefab ID保持。兩模式60秒預測試與900秒長場均已通過；舊0.41失敗保留，兩者分開記錄。這是AutomatedSimulation，非真人鍵盤、頭盔、LAN或網路容量驗收。

```powershell
python scripts/check-desktop-exercise.py --api-dll <同次API0.31完整建置DLL> --runtime-root <SSD runtime根目錄> --mode both --players-per-room 5 --seconds 900 --endurance --replay-workers 5
```

先Linked25端，再五個Independent房間各5端，每種模式執行900個caller單調秒；60秒只作預測試。底層 `--vr-desktop-endurance <新本機絕對目錄>` 僅Windows Development batch Client／無XR，與原短旗標互斥。普通啟動沒有生成器；短模式仍只接受12..40秒、1200活動tick／240秒。長場只接受60或900秒，不能合用operator-controls。

## 位置回饋、排程與界線

0.41.1長場只讀自己的head.localPosition.z，以首次有效位置至前方0.8m作換向依據，只回傳±0.2方向量，通過原Move／Constrain／SubmitPose RPC產生0.4m/s移動。不設定或clamp座標、不teleport／寫server pose、不搬動Tracked頭手。短模式保留原每40tick換向。

武器仍以來源tick排程，每400tick（20秒）相對20／60／120提供fire／reload／fire，等原SubmitWeaponRpc真正提交才記一次。最多45週期90發／45次換彈，使用原30發彈匣＋90備彈，不生成彈藥。簡報、Ready、Running、冷卻、ownership／驗票與伺服器規則保持；漏掉或未完成整週期就失敗，不追補射擊。

長場19000活動tick（950秒）／1200收集秒是儀表界線，非已驗收時長；900秒後不新增武器意圖，只留移動收尾窗口。report仍version1／AutomatedSimulation，長場profile=Endurance／motion=LocalPositionFeedback／maximumActiveTicks=19000／maximumCollectionSeconds=1200，短場motion=TickAlternation。finish後停止生成輸入、原姿態與結果流程保留；complete僅儀表收尾。

原0.5秒姿態／1.5秒來源、反瞬移、幾何／命中、佇列與durable政策保持。每位實際活動tick跨度至少達要求時間減5秒，是額外的執行證據條件，不是放寬姿態新鮮度；最後仍明列實測跨度。

## 完整驗證

每個保存Running body均核對原名冊／connected／health100／Simulated／房間／站姿與原測試走道Z=-3.4..-1.6、X原seat、Y1.65。capture gap達1500ms失敗，恢復不能抹去反例。依每位首tick分20秒區間，每區須有移動>0.1m、walking／reload來源幀及精確累計兩發，不能只看最後總數。

每個原admission結果／CSV、combat與world尾界／雙seal／原server connection ACK另驗。Room1僅對原Pause／Resume接受序號窗口例外，該房tick停住時其他四房須前進。所有原生先停才逐房完整回放；選用replay-workers5允許最多五個唯讀SSE讀者，各自仍rate4、從0逐幀到原seal、原期限與全部斷言。預設1讀者保持；任一失敗仍令整個工具failed，其他讀者完成／關閉後才cleanup。

所有writer停才C→F snapshot，保存SQLite不開、5080不動。partial-checks.json僅記失敗前完成斷言、complete=false，不當整場成功。

## 原0.41失敗與保留

原0.41／code51／5d2ebd2a...的064034-7c1ae2b7，真正exec **exit1**、cleanup空，整場failed。Linked5項／8621回放／8587 Running、25原結果／ACK／無timeout與每人45週期成功，活動跨度17996..17999；Independent在Room5 world3400／tick7120／elapsed359770ms，首一位Z=-3.4091835越過測試-3.4下界。該房五位仍connected／health100／Simulated且在正常房內，非舊31筆失聯。

原輸入按收到的tick每40tick換向，本機位移卻依deltaTime積分，不均步長下不能保證長時間回到原位置。新Editor回歸以凍結舊換向公式＋同一Move／不均步長重現漂移，位置回饋在相同測試有界。這支持修正機制，不補造本場deltaTime trace或唯一主機因果。

原失敗完整取證共36896回放：Linked8621、五房3433／4309／5391／6721／8421。Room5的8381保存Running沒有無效連線／健康／rig，三幀3400..3402有8筆走道不符，恢復後仍failed；首週期最低約-3.009，末第18週期約-3.396..-3.432。Independent僅每人36發18reload／活動跨度7074..7127，後段靜止取證不當900秒操作，四房continuity綠亦不當整體接受，沒有補CSV或成功旗標。C174／F raw同hash。

輔助離線分析首Room-only混到Linked另一組ID而min(empty)失敗，原腳本／錯誤保留；後依該錄影原player IDs重對齊才生成readback，原資料不動。原0.41 binary/log321＋7來源＝328先C/F archive，更早0.40的327亦保持。

## 0.41.1 候選證據與交付

242真正Editor／0skip（原238＋4），含位置換向、不變tick仍可換向、不均步長舊漂移／新有界、非有限值拒絕。Python14 exercise／27 active／5 artifact與錯模式CLI拒絕成功。新報告必須明確motion=LocalPositionFeedback，舊0.41報告不能冒充新模式。

073233-32121819兩模式60秒 **18項／3760回放／50原結果／6CSV／雙seal及原ACK**成功，每人6發3reload／3週期、無queue error，五路回放到原seal且cleanup空。玩家包19通過；新的900秒073638-487017bd／handle33928已terminal exit0：18項／51601完整回放／51351 Running、50原結果／6CSV／雙seal及原server ACK、無timeout或queue error，每人90發／45reload／45週期。Linked8610／8576 Running；Independent8582／8518、8590／8552、8580／8540、8600／8561、8639／8604。活動跨度17943..18003tick、最長收集902.3086214秒；active0／cleanup空後C174→F逐檔同hash。另普通無生成旗標入場／撤銷／重連8項／354幀成功。666新來源snapshot只含source，於新長場之前完成，兩端建置全停才原生。

- 玩家ZIP **82,651,927 bytes／SHA256 dcc46c80c68d0a2861957c7d534b1abacd15964fb22f310ecdd1e60dddf7d2df**，311 manifest／ZIP312，原啟動器source a65846da...。
- Server v2 ZIP **82,673,732 bytes／SHA256 ca285a42e0c22bdde17f62eb6dd8a65523c9d3a5cae19a33cad41636899fb368**，311 manifest／ZIP312、啟動器1.1.0／source fb57807d...；106項／623回放及實際WinForms流程成功，v1保留。直接輸入路徑、選場次／啟動／封存保留36秒停止／關閉的範圍見[WINDOWS_SERVER_PACKAGE](WINDOWS_SERVER_PACKAGE.md)。
- APK **60,361,942 bytes／SHA256 766d80180c0facf67136412d4f9a4b9e35ae0d6dc5f5cac9b128261282188e48**，ARM64／min32／target35／0.41.1／code52、v2 debug簽章，未裝頭盔。

原0.41 ZIP／APK1187dfd2...保留，當前APK是0.41.1，不混稱原檔同hash；首server缺stage-root拒絕與後補新目錄成功的紀錄保持。API0.31／UI0.31.2／rules0.8.0與wire不變，沒有新的後端產品或頭盔驗收；新WinForms流程另記。

舊18a72f0的[CI41359154963](https://github.com/peca12968/vr-command-center/actions/runs/41359154963)完整772／459／47／6pipe／38CLI／14Python／89Node／296 Chromium，但它測舊0.41功能＋鏡頭fixture，不當本候選CI。首7ed鏡頭等待CI failure／17部分browser保留，18a僅DOM polling100／有界診斷、原15000ms／斷言／產品期限不變，不證首失敗根因。原1629browser／nativeUI7＋2保持，新CI另記。

完整11項active，PickerHost已由使用者關閉、GUI重驗另記；舊31／world371／startup／F吞吐、跨機25真人、Quest／VIVE／MR與廠商SDK／實體硬體仍待；生成器修正不當這些根因修復。精確來源、CI與原生結果見[PROGRESS](PROGRESS.md)。
