# 電腦端第一人稱軍服手臂

2026-11-01：Unity **0.37.0／Android code45／NGO29**，API／UI **0.30.1**。Windows 與 ARM64 Quest APK 使用相同來源 fingerprint `09eed85207b33d5304f6aae294a5aebe3237d48eca3f2b0cf9b01679530ed5c8`；原 scene／prefab ID 保持。184 項真正 Editor 測試通過；APK 建置與簽章檢查成功，尚無頭盔實測。

## 遊戲行為

無頭盔的本機玩家現在可看到自己的軍服上臂、前臂及既有手套，視角轉動與換彈時沿用原本保存的武器姿態和換彈 tick。自己的軀幹、雙腿、頭盔在第一人稱隱藏，避免擋住視線；其他玩家仍看到原來完整的第三人稱人物。遠端玩家的歩態、武器與軀幹表現維持原行為。

重用 `player-body-v1` 的五 Mesh／404 面、材質、共享 lease 及 `PlayerPresentation.Pose`，沒有修改舊 profile pin 或新增素材。手臂是裝飾性兩節近似，沒有新 Collider、傷害或命中資料。槍口、pointer、合成手套、Tracked 資料及原 0.5 秒姿態／1.5 秒世界新鮮度政策保持。Tracked owner 會在計算前隱藏並返回，不正規化或驗證其即時 XR 關節；尚未提供追蹤人物的完整手指、腰腳或動畫系統。

自己的四個手臂節點與 Body frame 是兄弟節點，隱藏軀幹不會把手臂一起關掉；回到第三人稱模式時重新啟用軀幹與頭盔。死亡或不再連線則隱藏本機手臂。本輪沒有修改 Shared 規則、API、world header、journal schema、NGO wire 或原有識別，不必重新產生場景／prefab。

## 實際電腦驗證

```powershell
python scripts/check-desktop-first-person.py --api-dll <已驗收的 API DLL> --runtime-root <新的 C 槽 runtime 根目錄>
```

使用自己的隔離 API、server 及一個可見 Windows client，runtime 必須明確指定。操作人員在遊戲視窗實際按 Right／Down、Space 一次、R 一次；腳本不注入輸入、RPC、姿態或命中。依序檢視六張原生 GPU PNG 後才另行建立 `review.done`；診斷明確 finish 後，才獨立 End、核對精確雙 seal、CSV、原 admission 的結果及唯一 server ACK。`complete` 只有 cleanup 成功後才寫入。

`desktop-first-person/20261101-114930-25078562` 原 handle57292 terminal exit0，**4 項成功、6 張實際 framebuffer、1195 幀連續完整回放、5 個原來源檢查點**。從初次檢查點起逐張 Running 核對唯一原玩家仍健康100、connected、Simulated、非 suspended，沒有暫時參戰失效；恢復不會抹除中間失敗。paused pair 的各手臂端點差為0；與已接受來源的 head／原右手套握點最大差 `5.382805623455056e-08` 公尺，小於原1微米界線。左腕確有保存換彈時鐘所驅動的位移，完成後彈匣30／備彈89，1發、0中、0殺、健康100。

實際畫面可見步槍旁左袖及換彈低角度的右袖，沒有自己的頭盔／軀幹遮住相機；槍枝仍可能遮住部分手臂，沒有宣稱每個角度所有肢體都完整可見或已完成動畫品質驗收。視窗焦點切換造成擷取尺寸不同，沒有拿像素數或 tick gap 當效能指標。**此功能場與 Quest 建置時間重疊**，不是乾淨效能基線或因果比較。

原 `--vr-player-body-probe` 仍只在明確 Windows Development／可見 untracked client 安裝，普通遊戲／Editor／Android 不收集；600秒／8張／每張900萬像素上限不變，沒有 PCM／系統錄音或輸入。新增獨立 `firstPerson` 診斷欄位，`players[]` 仍只有遠端人物，`walking` 的就緒判斷仍只看遠端。沒有用本機袖子冒充遠端人物證據。工具只記五個 helper SHA，**不是完整 runtime／OS／computer-use 依賴 graph**。

## 回歸及保留的失敗

| 場次 | 結果與範圍 |
|---|---|
| `desktop-venue/20261101-115513-5ef0869d` | 舊人物工具原300秒 observer 定位逾時，handle72822 exit1；尚未啟動 target，未寫 observer.done，cleanup乾淨。不是完整 GPU 成功場，也不當姿態根因 |
| `desktop-venue/20261101-120615-644b0391` | 原工具／原300秒不變，handle30210 exit0，4項、6張遠端 GPU，實際 W／Space／R。遠端 walking stride非零、paused端點差 `2.384185791015625e-07` 公尺。前景槍／袖及 Pause banner遮住部分遠端身體，沒有宣稱所有像素可見。原工具僅最終 replay／seal統計，不能當新增全程回放／全員ACK |
| `desktop-debrief/20261101-121759-e60ee300` | 實際回傳 terminal exit0、4項，Host等待peer ACK，移除admission不收結果，兩份原結果符合seal |
| `desktop-venue/20261101-121914-2748af54` | 已停止、stage passed／6項／7場及cleanup無殘留；五房隔離、錯房票拒絕、房1環境／AI／Pause不影響其他房、重用席位及後續五房Linked、精確seal。原shell回應遺失於輸出裁切，未補造exit0。這是五房各1位，非25位操作 |

各場只在所有自己的 writer 停止後一次 snapshot 回 F，原 C runtime 不移動；保存 SQLite 只核對 raw bytes，不開資料庫連線。新 helper 的7項反例涵蓋錯 owner／Tracked／遠端分類、過期 tick／phase／rig、來源端點不符、NaN／bool、錯時鐘、finish IO失敗仍 cleanup，以及短暫失效恢復仍失敗。連同5 artifacts／27 active／12 debrief，本機51 Python通過。5個新增 Editor案例加原179為184，涵蓋本機隱藏／端點、Tracked早退、死亡／失聯、切回第三人稱及保存換彈／Pause。

## 建置與可攜包

Windows 與 Quest 都是真正同源建置，不把 receipt 的 `totalBytes` 當實際 APK 大小。APK 為 `com.vrcommand.quest`、0.37.0／code45、arm64-v8a、min32／target35，**60,313,726 bytes**，SHA256 `067c41347a284e05fb5d8695277e0907052a984050c2220313dd23a21bce6e94`。Unity內附Java執行apksigner成功、v2簽章有效；仍是 Android Debug certificate，非商店發佈或實機安裝驗收。第一次 `.bat` 因 JAVA_HOME 缺失失敗的 log 保留，沒有改系統環境。

新包 `artifacts/player-packages/windows-20261101-120352-b2b5c1c3.zip`：**82,642,471 bytes**，SHA256 `08aa93385e4e2b2688714fee56ce6d9dfe6592574d8e7e844e15020e815ae030`，311 runtime檔／manifest／原launcher。新 C 展開目錄的19項真正launcher核對／拒絕成功；沒有完整封裝GUI、跨機或網路安全性提示操作證據。manifest是雜湊清單，不是簽章。

建置前已把舊 desktop305／quest3／logs13共321檔及9份來源精確另存 `first-person-history-*`；舊0.36.1與0.36.0 ZIP保持原處與原hash。詳細原件、runtime與CI結果見 [PROGRESS](PROGRESS.md)。fingerprint只依原明列來源集合，不當完整建置依賴 graph。

[精確81108e1的CI41273127773](https://github.com/peca12968/vr-command-center/actions/runs/41273127773)已完整成功：717規則／459 HTTP／47 world、Python／素材、72 Node／248 Chromium；雲端沒有Unity Editor或頭盔。保存39檔與log、ZIP9,710,227 bytes／SHA `84d3f956d75fbd71e4ec680f03dc809b43266e9f3b924ad3d81a7a4fd787dec0`。新5 runtime102檔與F snapshot一致，前55場2981檔保持，全部60場3083檔；447份前瀏覽器／CI檔另依原manifest核對。後續文件skip ci，沒有冒充再次重跑。

完整11項仍active。原31筆、較新world371、Windows完整HTTP startup、F吞吐皆未因袖子或本場成功而修復。後續仍要多人持續操作、跨機／Wi-Fi、Quest／VIVE／MR、完整人物動畫與廠商硬體驗收；目前沒有頭盔。
