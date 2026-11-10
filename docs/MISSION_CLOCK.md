# 任務活動時間與自動結束

管理與發布失聯的真正 PC 回歸見 [CLOCK_RECOVERY](CLOCK_RECOVERY.md)：分通道故障、到期等待、恢復補送與封存；不是整個 API／世界崩潰恢復驗收。

API／UI 0.28、Unity 0.30.0／Android code37／NGO28。本功能是選用的場次政策；rules0.8.0、命中與傷害規則不變。

控制台在準備中的場次提供「依任務時間自動結束」，遊戲伺服器綁定支援計時的來源後才能設定。勾選並套用後，再開始任務；未套用、未勾選與舊場次都由操作員手動結束。設定草稿不代表已套用，旁邊的文字顯示伺服器接受的政策；可按「載入目前時間設定」重新載入。開始後不能變更政策或任務秒數，修正任務需保存下一版本並新開場次。

計時依共用 ArenaWorld 的 20 Hz 權威 tick。Preparing、Pause、管理來源中斷不消耗活動時間。60 秒的期限為 tick1200，剩餘秒數向上取整；恢復後接續原 tick。程式卡頓或來源中斷可能使活動時間慢於現實時間，這不是 UTC 截止時間或不中斷的牆鐘計時器。

啟用時，ArenaSession 到期停止 tick、射擊／換彈與新遊戲 binding。Unity 保存到期邊界並繼續發布；API 每250ms讀取已接受的世界幀，確認同一 stream、設定序號及期限後，以固定內部 mission-clock 身分提交正常 End。只有本機服務可呼叫此內部入口；HTTP 沒有取得 Internal 身分的新途徑，玩家只持短效票券。未發布或尚未接受的本地時間不能直接結束場次。若 API／發布中斷，遊戲保持到期凍結，等待恢復或操作員結束，不能宣稱已封存。

End 仍走原有 combat／world 雙 journal 補送、精確 seal、玩家個別戰績及 ack 流程；自動結束不等於立即拿到最終報表。操作員先 End 會勝出，不多追加第二筆 End。到期證據保留 streamId、observedSequence、tick，原任務定義、歷史場次與錄製不重寫。補送不是世界崩潰恢復。

PC HUD 顯示 REMAIN，手動模式顯示 ELAPSED／PLAN；數值取自 NGO 複製的權威 tick，不用本機時間自行倒數。Android 標籤接相同來源，未有頭盔顯示證據。觀戰／回放依新錄製 header 的 missionClockVersion=1、missionDurationSeconds 顯示「活動時間／計畫」，不把 header 的支援能力誤認為場次已啟用自動結束。舊 header 缺欄位為0，不補造舊倒數。

## 五房房卡

Windows 管理包 0.31.30 起，「房間與場次」直接顯示各房的任務計時。準備中顯示保存版本的計畫時間。執行中及暫停時，手動結束的房間顯示活動時間及計畫時間，自動結束的房間顯示剩餘時間。合併場的五房使用同一份世界快照，獨立場各自計時。房控只能查看本房。

房卡採用已接受的快照，等待最新階段同步或來源超過原本的 1.5 秒有效窗時顯示「活動時間未確認」。暫停期間保留當前快照的活動時間。收到已到期快照時顯示「等待結束確認」，待原 End 流程完成才釋放房間。

`GET /api/rooms/readiness` 在有可信任計時的房間附加 `clock`，包含 `phase`、`elapsedSeconds`、`remainingSeconds`、`durationSeconds` 和 `autoEnd`。支援計時的來源須觀察到最近一次階段變更後才可提供數值。短時間內暫停又繼續時，舊的執行中快照不會重新成為房卡時間。

## 全館開始

場次執行完畢後，主控可批次結束及查看各場封存。 [全館收尾](SESSION_CLOSURE.md#全館批次結束)

Windows 管理包 0.31.33 起，主控可在五房總覽按「開始準備中的場次」。確認視窗列出本次房號與場次數。它涵蓋目前所有準備中的場次，五房合併只會提交一個場次，五個獨立房各自提交一個場次。

每場要有玩家名冊，遊戲來源也要回傳對應當前場次序號且在原 1.5 秒有效窗內的準備快照。VR 要求名冊內玩家姿態有效，MR 沿用原有 Quest 3 追蹤就緒條件。控制台 0.31.55 在「全館場次控制」逐房顯示空名冊、來源狀態、設定待同步或等待的席位。五房合併時，已備妥的房間會顯示正在等候同場其他房間。快照過期後，逐席提示會清除，等收到新快照再顯示。

控制台 0.31.92 在同一面板列出各房第 1 至第 5 席的狀態。主控可以分辨未編列、等待入場或場次同步、姿態未就緒、合成姿態及追蹤就緒。勾選五房追蹤開場時，合成姿態會標示「需追蹤」。收到舊版名冊的快照時，相關席位維持等待。來源失效時會撤下原姿態狀態，待新快照確認。房控沿用本房名冊。

若有場次尚未就緒或預覽後名冊、設定或階段變動，管理服務會拒絕整批命令。個別場次的開始按鈕仍按各自的規則操作。

管理服務把各場的開始命令放在同一筆交易。房卡會先顯示「全館開始待確認」，收到對應的有效執行中快照後才顯示「全館開始已套用」。回覆遺失時可用原請求確認，包含服務重啟後或原場次已結束時。

`GET /api/venue/phase` 的 `begin` 預覽含每個目標的 `sessionId`、`phaseSinceSequence`、`sessionSequence` 與房號。送出 `Begin` 時每場須附兩個原序號。準備中可從 `GET /api/rooms/readiness` 讀取 `venueBeginReady`，主控同時收到 `venueBegin` 的條件與本房等候席號。控制台核對同一場次和序號後才顯示逐房結果。來源未就緒時回傳 `409`、`venue-begin-not-ready` 與 `roomIds`。

可確認的準備中房間會在主控的 `venueBegin.seats` 提供從 1 起算的席號與狀態。欄位只列已編入名冊的席位，空席由控制台依房間容量呈現。準備快照尚未同步目前名冊時，欄位只會回報入場或場次同步狀態。

## 全館暫停與繼續

Windows 管理包 0.31.31 起，主控可在五房總覽使用「全館暫停與繼續」。按「暫停執行中場次」前會列出本次房號與場次數。合併模式的五個房間會共用一個命令，獨立場的命令則在同一筆管理交易保存。各遊戲來源收到自己的新序號後套用，主控可從房卡查看已接受快照的階段。

「繼續全館暫停的場次」只會列出仍處於全館暫停階段的場次。房控或主控在個別場次操作的暫停由原房間流程管理。任何目標自預覽後變更階段，整批命令就會拒絕。要繼續 MR 場次時，每場仍需目前名冊與有效的暫停追蹤快照。若有場次尚未就緒，整批維持暫停並列出該場次涵蓋的房號。

若回覆遺失，使用「重試確認結果」即可取回同一批場次及原序號，包含管理服務重啟後的重送。`GET /api/venue/phase` 提供主控可操作的 `pause` 與 `resume` 預覽，`POST /api/venue/phase` 需要主控憑證、`Idempotency-Key`、`action` 及每場的 `sessionId`、`phaseSinceSequence`。成功回傳原場次與 `appliedAtSequence`。目標改變或 MR 尚未就緒會回傳 `409`。

管理包 0.31.32 起，房卡會分開顯示「全館暫停／繼續待確認」與「已套用」。遊戲來源須回傳符合目前階段及命令序號的有效快照，才會顯示已套用。逾時、管理連線中斷或等待階段同步時，房卡會標示待確認的原因。房控可查看本房；合併場的五張房卡共用同一個遊戲端確認。個別操作改變階段後，該房會退出原全館狀態。

全館繼續現在要求每個目標的有效暫停快照，VR 與 MR 皆適用。MR 另須滿足當前追蹤條件。任何房間仍在等待時，控制台會列出房號並停用批次繼續。`POST /api/venue/phase` 遇到尚未確認暫停的目標會回傳 `409` 與 `venue-pause-not-observed`。個別房間的暫停與繼續仍可由原場次控制操作。

`GET /api/rooms/readiness` 會在目前階段由全館命令建立時附上 `venuePhase`，包含原命令 `action`、`appliedAtSequence`、有效的 `worldSequence` 與 `readyToResume`。快照無效時 `worldSequence` 為 `null`，命令序號仍保留。重送原管理命令會取得原回條，房卡仍依目前快照判斷遊戲端是否已套用。

### 逐房確認可以繼續的條件

管理包 0.31.85 在「全館場次控制」列出本次可繼續批次的每個原房間。可分辨尚無遊戲來源、等待遊戲端套用暫停、快照過期與可繼續。MR 快照已確認暫停後，還會標示等待最新名冊及設定同步，或指出等待追蹤的席號。合併場已就緒的房間會標示正在等待同場其他房間。等候席位只包含目前仍須追蹤的玩家，已淘汰席位依原規則處理。

房卡會顯示同一份原因。`GET /api/rooms/readiness` 在有有效的 MR 全館暫停畫格時，可從 `venuePhase.mrResume` 讀取 `state` 與該房 `waitingSeats`。房控只收到本房席位。當暫停畫格過期或場次已繼續時，舊席位提示會撤下。整批繼續仍由管理服務在送出時核對各目標的原有條件。

## 契約與升級

- `SetMissionClock` 走原 `/api/sessions/{id}/commands`，包含 `missionClock:{autoEnd:true}` 與正常 commandId／expectedSequence。Master／同房 RoomController 維持原權限；Linked 限 Master。
- 新 `OpenCombatStream.missionClockVersion` 預設0，新 Unity 明確送1；API 逐次驗證來源能力。重試須保留原內容，不能在既有來源上偷偷改能力。
- 新寫入事件 envelope7，讀1–7。`MissionClockStatus` 保存 version／autoEnd／configuredAtSequence；自動 End 的 command 保存 clockExpiration。不得降回不懂新欄位的舊 reader。
- world schema1、驗票2、素材 pin 不變。新 header 必須由 API0.28 核對同一來源與保存的任務秒數；保留舊 binary 原始 header／payload／checksum。schema 不變不表示可降版。
- Prepare 原位升 NGO28，重用 Arena／PlayerAvatar file ID；API／UI 與全部遊戲 server／client 一起更新，不拿新 client 接舊 API。
- 正式5080歷史服務維持原版本／資料；測試只用自己的隔離 API、憑證與全新 runtime。

## 驗證入口

`VrCommand.Checks` 涵蓋權限、來源能力、歷史重試、計時暫停、到期凍結、內部 End 身分、未發布時間拒絕、雙 seal 與重新 projection。真正 Editor 的 MissionClockTests 涵蓋 Unity JSON null 舊設定、NGO 序列化、HUD 及實際 ArenaSession tick 邊界；瀏覽器含草稿保留、遺失回應重試及已結束禁改。

```powershell
$env:VR_COMMAND_API_DLL = "$PWD/artifacts/build-clock-v1/bin/VrCommand.Api/release/VrCommand.Api.dll"
python scripts/check-desktop-clock.py --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns" --inspect-seconds 35
```

此工具需要最新成功 Windows build receipt，建立兩個真正獨立 server／client：一間60秒到期、一間手動。暫停至少5秒並逐次確認 tick 不變；到期須恰好1200、只有一筆內部 End，手動房必須超過1200仍 Running。兩場都核對最終統計／個別結果 ack、整段封存回放連續與結尾。資料在明確指定的 C SSD，全停 writer 才保留副本回F，原件不移動。這是同機PC Simulation驗證，沒有頭盔、MR、25台或跨機容量驗收；本輪結果見 PROGRESS。

原生工具全停並成功後，可執行 `node tests/browser/check-clock-native.cjs artifacts/desktop-clock/<本次場次> --controls`。它只複製 runtime-snapshot 到全新的 C 暫存目錄，在該 audit copy 開自己的 API，核對兩人的 final JSON 與原入場／雙 seal 序號／ledger，以及實際觀戰時間；`--controls` 另驗時間草稿及重試。原件與保留的 snapshot 不開 SQLite；副本保留供稽核，輸出在該場次的 clock-observer。瀏覽器使用 SwiftShader，與真正 PC GPU 觀察分開。
