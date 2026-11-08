# VR 場地配置檢查

## MR 場地水平校正試算

控制台 0.31.11 在「任務庫與編輯」提供三點校正試算。全館主控先選房間，再輸入同三個地面標記的遊戲房間本地 X、Z 和同一追蹤座標系的 X、Z，單位為公尺。預填的房間標記可依場地位置調整。輸入完成後按「核對校正」。

A 定位原點偏移，A 到 B 定出方向。A、B 在兩套座標中都須相距至少 0.5 公尺，遊戲標記 C 須離開 A、B 連線至少 0.5 公尺。只用 A、B 求旋轉與位移，C 用來獨立核對方向及誤差。比例固定為一比一。三個標記的平面誤差都在 5 公分內，才可下載房間專用 JSON。5 公分是目前軟體試算門檻，場館安全及跨裝置定位須實測。

`POST /api/room-alignment` 接受 `roomId` 及三個依 A、B、C 排列的 `markers`，每組含 `room`、`tracking`，各有 `x` 和 `z`。房間座標在 ±6 公尺內，追蹤座標在 ±100 公尺內。回應 `room-floor-alignment-v1` 包含原量測值、各標記的對齊座標與誤差、`yawDegrees`、房間本地 `translation` 和全館 `roomOrigin`。JSON 以遊戲 Y 軸旋轉方向計算，正 90° 會把追蹤 +Z 轉到房間 +X。換算全館座標時，先將追蹤點旋轉並加上本地位移，再加全館房間原點。

試算與下載獨立於任務版本及開場。 [驗證紀錄](PROGRESS.md#2026-11-08-mr-場地水平校正試算)

### Quest 3 場地對位

Unity 0.42.0 可讀取對應入場房間的校正檔。用 `deploy-quest.ps1 -AlignmentFile` 隨玩家設定部署。匯出的檔案提供房間 A、B、C 的位置。每台頭盔在進入 Preparing 或 Paused 後，依畫面提示把左控制器的追蹤點放到 A、B、C 正上方，逐點按左扳機。使用同一控制器握法與朝向，並維持頭部及雙手追蹤。程式使用 OpenXR 的地板原點及控制器 X、Z，三點都通過原 5 公分門檻後才將頭部、雙手和瞄準方向轉換到全館座標。

首次量完請回到頭盔顯示的房間本地 X、Z。伺服器沿用原有規則，第一筆姿態須在指定出生位 0.5 公尺內。已送過有效姿態時，提示會顯示最後一筆有效姿態的 X、Z。追蹤原點更新或應用程式暫停後，需在 Preparing 或 Paused 重新量測。錯房、三點不符或地板追蹤不可用時，頭盔會暫停送出姿態與武器輸入。 [Unity 追蹤原點事件](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/XR.XRInputSubsystem-trackingOriginUpdated.html)

目前驗證使用 Unity Editor 模擬的追蹤座標。Quest 3 實機量測、房間地板高度、MR 透視和跨頭盔共用定位仍待驗。 [Quest 3 部署](QUEST3.md#quest-3-場地對位部署)

Quest 3 開發版可選用透視查看實體標記，再依相同的 A、B、C 流程對位。 [透視部署](QUEST3.md#quest-3-透視呈現)

## 出生位通路預覽

控制台 0.31.7 可預覽五個出生位到場地中線的路徑。草稿通過基本配置檢查後，虛線會畫出找到的路徑，橘色出生位表示未找到取樣路徑。開場區顯示所選已儲存版本的摘要。操作員可保留刻意設計的封閉防線。

預覽從房間本地座標的 `Z = 0` 中線開始搜尋，使用 0.5 公尺格點和四方向相鄰格。每段沿用遊戲既有的 0.3 公尺通行半徑與 `ArenaWalkSurface.ClearSegment`。結果表示取樣路徑；細窄或非格點通路、運行中的敵軍路線與 MR 場地另行驗證。

VR 草稿與已儲存配置報告可回傳 `routePreview`。其中有 `step`、`targetZ` 及五席的 `path`，路徑點包含 `x` 和 `z`。空路徑表示未找到取樣路徑。未通過基本檢查與 MR 的配置沒有預覽。 [測試與版本](PROGRESS.md)

Windows 三包測試可加 `--check-layout-preview`，使用有缺口的已儲存配置，核對預覽和封存世界中的沙包位置。 [三包測試方式](WINDOWS_SERVER_PACKAGE.md#三個可攜包整合驗證)

另一組核心對照在已入場的共用遊戲權威端核對移動。完整沙包牆會拒絕掩體內及跨牆姿態；移除正前方沙包後，原席位的七個預覽取樣點都能依序接受。Windows 鍵盤對照工具 `scripts/check-desktop-walkway.py` 會啟動兩個保存版本各自的場次，核對實際姿態、完整回放和封存戰績。這次 Windows 安全提示遮住遊戲，鍵盤驗收待重跑。 [執行紀錄](PROGRESS.md#2026-11-06-通路預覽的移動判定與鍵盤驗收準備)

此配置契約由v0.18導入，v0.19新增步槍素材後維持version1／vr-room-v1。最新API／UI須一起部署，配置檢查不依裝飾武器模型改變。

API／控制台 v0.18，檢查契約 version 1、profile `vr-room-v1`、rules `0.8.0`。供現有每房 12 × 12 公尺的 VR 原型使用，MR 回傳 `applies=false`、`canStart=null`；沒有實體場地、錨點或校正證據。

在「任務庫與編輯」加入／移動／旋轉物件後，控制台自動檢查草稿，紅色標示涉及的物件。點擊問題可選取物件並修改數值；五個圓形為真正出生位的 0.3 公尺通行預留。預覽可切換單房／全館，以核對初始敵軍需求。畫布顯示 ±10 公尺供編輯，框內 ±6 才是目前 VR 場地。

草稿有問題仍能另存或保存下一版。開場選用的是不可變的已保存版本；修正未保存的草稿不會放行舊版。選取版本及連線模式後，開場區重新讀取該版本的報告；檢查未完成或不支援版本時不啟用建立按鈕。後端也獨立拒絕無效的新 VR 場次，不能繞過介面建立。問題修正後保存下一版，再明確選用該版。

| 規則 | 實際判定 |
|---|---|
| 素材與數值 | 目前只支援 `sandbag`／`barrel`，有限座標／角度，角度 -360° 至 360° |
| 地面 | Y 絕對值最多 0.001 公尺 |
| 場地 | 旋轉後整個包圍盒在 X／Z ±6 公尺內，容差 0.0001 公尺 |
| 重疊 | 旋轉方盒四軸 SAT，有超過容差的正面積重疊即拒絕；貼齊的連續沙包允許 |
| 出生點 | 五席均使用 `ArenaSession.Spawn`，以真正 `ArenaWalkSurface` 的 0.3 公尺通行規則核對 |
| 初始敵軍 | 與真正初始規劃共用 0.75 公尺有序候選網格；單房需求為全部數量，全館為每房最多 ceil(總數／5) |

沙包仍為 2 × 0.9 × 0.7 公尺、油桶 0.7 × 1.2 × 0.7 公尺的粗略方盒，與 [FIELD_PROPS](FIELD_PROPS.md) 的視覺模型有所差別。本功能不改碰撞／命中／移動規則，不代表掩體間所有通道可通行、所有區域相互可達或具備良好戰術設計。容量是初始空世界的出生候選數，不能保證運行中增援有空位，也不是 FPS／25 台效能承諾。

共用檢查唯一來源為 `com.vrcommand.simulation/Runtime/ArenaLayout.cs`；Core 明確參考 .NET Standard 2.1 的 Simulation。Unity 保持不參考後端，舊 `ArenaSession`／世界回放不套用新的拒絕政策。建立場次先確認權限與已接受 request key，才檢查新配置；舊版曾接受的場次與已接受的原樣建立重試不會被新規則改寫或重新建立。未接受的檢查失敗不消耗 key，也不占房。事件 envelope 6／任務 schema 1／世界 schema 1／NGO 19 皆不變；新增報告不寫入舊事件。

API：

- `POST /api/mission-layout`：Master 專用，body 為 `{ experienceMode:"VR", mode:"Independent", enemyCount:8, props:[...] }`，純計算且不保存任務。
- `GET /api/missions/{id}/layout?mode=Independent`：明確 Actor 的共用任務範本讀取政策，省略 mode 預設 Independent；不是場次管理授權。
- `POST /api/sessions`：無效新 VR 配置回 400 `{ error, layout }`，其餘既有 401／403／409 權限與衝突規則保留。

報告含 version／profile／rulesVersion／mode、applies／canStart、場地與出生位、每房候選容量／需求及問題。每個問題的 `propIndex`／`otherPropIndex`／`seat` 為零起算，沒有對象為 -1；UI 顯示時加一。最多 500 個物件，僅傳前 128 個問題，`totalIssueCount` 保留完整數量、`truncated` 明示，`invalidProps` 仍列出全部涉及索引。無效數值／越界物件不進一步參與容量推算，容量為 null，不能當作通過。

草稿與保存版本各有請求序號、登入 epoch 及精確內容／選擇核對。舊回應不得改寫新草稿、切換模式後的批准或登出後的畫面；快取僅本次登入、以不可變版本與模式索引。憑證仍限頁面記憶體。API 和控制台須一起更新至 v0.18，不能以舊 API 的無檢查建立當作相容解法。

驗證命令沿用後端四項、`smoke_world.py`、完整 `tests/browser`、真正 Unity Prepare／EditMode／Desktop／Quest。新增測試包含旋轉與接觸邊界、五席出生阻擋、真正初始敵軍容量／舊重疊世界可讀、128 問題上限、舊事件恢復與已接受重試、HTTP 權限及 UI 延遲回應；本輪實際結果、binary 與 PC 運行證據見 [PROGRESS](PROGRESS.md)。
