# 電腦端軍事戰鬥HUD v0.19.1

玩家畫面新增軍綠／琥珀狀態面板、血量條、大字彈匣／備彈、場地方位及敵我標記。數值來自已接受的NGO狀態，準星仍按原武器與幾何預測；射擊、傷害、換彈及統計仍由伺服器判定。桌面持續顯示 **Simulation／Synthetic rig**。

| 區域 | 顯示 |
|---|---|
| 左上 | 房間、任務階段、Simulation來源 |
| 右上 | VENUE HDG方位與刻度；000°為場景正Z、090°正X，不是地理北方 |
| 左下 | 自身血量與血量條，低血量換色；收到自身血量下降時短暫邊緣提示 |
| 右下 | 彈匣／備彈、換彈中或空彈提示；沒有推算不存在的換彈進度 |
| 中央 | 尚未開始、暫停、結束、追蹤無效、姿態拒絕、姿態串流逾時或淘汰；淘汰優先於追蹤／姿態警告 |
| 場景標記 | HOSTILE／ALLY與穩定短識別、血量條，文字與顏色共同區分 |

## 標記與資料範圍

只考慮同房間、仍參戰且存活的角色，距離20m內。每0.1秒從最多32個最近候選找出最多8個標記；每個繪製幀再以最新收到的狀態核對遮擋，遮擋後不保留舊標記。檢查使用與命中預測相同的旋轉掩體盒及角色盒，忽略自己；其他存活角色也可遮擋。

標記要求胸部中心的直接視線；只露出頭部時可能不顯示標記，角色本身仍照常渲染。這是保守的顯示規則，並非逐像素遮擋或防作弊／資料保密邊界。網路快照與渲染仍有延遲，最終命中不由標記決定。沒有穿牆標籤、迷你地圖或自動瞄準。

XR的既有world-space文字面板共用狀態優先序與血量／彈藥格式；桌面方位列及角色浮標沒有放進頭盔畫面。XR面板的字體、舒適性及實際頭手操作仍待頭盔驗證。3D角色、武器、場景與軍事素材列在後續美術階段。

## 重現真正鍵盤檢查

依QUEST3建置Desktop及API後，執行：

```powershell
python scripts/check-desktop-hud.py --runtime-root C:/Users/USER/AppData/Local/VrCommand/SimulationRuns
# 需要時加 --api-dll <同次隔離建置API DLL>
```

工具只建立自己的API、房間3、server及兩個真正client；無敵軍攻擊時先檢查可見／胸部被油桶擋住的兩個敵軍。依印出的階段在可見玩家視窗操作，然後在該次證據目錄新增空白完成檔：

1. fire.done：空白鍵射擊一次，彈匣30→29。
2. reload.done：R換彈一次，經過RELOADING後30／89。
3. turn.done：方向鍵Right短按20次，方位約060°，看見右方友軍標記。
4. damage-review.done：檢視工具由真正AI造成傷害後的暫停／血量畫面。
5. eliminated-review.done：檢視真正AI淘汰後的ELIMINATED及血量0，再結束。

完成檔只推進測試；接受的世界幀、HUD繪製快照及封存戰鬥數值決定結果，不注入姿態或武器事件。資料使用明確SSD runtime，關閉writer後複製回F並保留原件。狀態來源與限制見 [DESKTOP_CONTROL.md](DESKTOP_CONTROL.md)。

## HUD-only診斷與證據

檢查器明確帶 `--vr-hud-probe <全新絕對目錄>`，沿用NativeWeatherProbe的Windows Development／未追蹤／可見client限制。與weather音訊模式互斥；HUD模式只記錄本玩家HUD及GPU、不配置PCM緩衝、不保存音訊，上限285秒、最多22份自動截圖（HUD名稱集合門檻16，加六種固定聲光狀態）及有界觀測。一般啟動不附掛診斷。HUD快照只在實際OnGUI repaint後收集，仍須配合GPU截圖檢視，不能拿顯示資料替代畫面證據。

2026-10-30 `20261030-000040-9a2f550c`：真正鍵盤射擊／換彈／轉向，軍事HUD、受遮擋敵軍、友軍060°、血量60暫停、血量0淘汰均已檢視；2680幀、最大來源年齡0.767627秒、回放／ledger一致、活動0、cleanup零錯誤。耗彈1、中彈5／耗損100，HUD模式audioSamples=callbackCount=0且沒有audio.wav。原始Windows截圖與14份引擎截圖／報告在該次artifacts目錄，沒有提交影像或私有票券。

診斷截圖亦記錄過短暫POSE_REJECTED。後續唯讀檢查同場原始worlds.db：666→667幀的保存時間差688ms、tick仍1328；668幀connected=false，669幀（100ms後）恢復，位置／健康／彈藥不變。這證明保存資料存在停頓及短暫非參戰狀態，不能還原完整姿態收件間隔、警告時長、PoseAccepted或停頓原因，亦不證明GPU截圖造成它。原始失敗證據保留。

## 區分姿態警告及逐繪製轉換診斷

v0.19.1保留警告，依序顯示TRACKING INVALID（本機追蹤未就緒）、POSE REJECTED（伺服器PoseAccepted=false）、POSE STREAM STALE（前兩項有效但複製body.connected=false）。非參戰狀態仍不顯示準星或敵我標籤；不加延遲遮掩、不放寬0.5秒姿態新鮮度、防瞬移、碰撞、入場或權限檢查。這些狀態是各自複製／本機觀測，並非原子網路快照；例如斷線與死亡亦會影響connected，不能把標題當封包根因。

使用 `python scripts/check-desktop-hud.py --trace-only --runtime-root C:/Users/USER/AppData/Local/VrCommand/SimulationRuns` 可改用 `--vr-hud-trace <全新絕對目錄>`。三種診斷模式互斥，維持Windows Development／自己的未追蹤可見玩家限制；此模式不配置PCM、不呼叫GPU ReadPixels或PNG輸出。每0.25秒保存狀態，並在每個實際HUD Repaint後，將狀態或ready／poseAccepted／connected／tracking的轉換存入記憶體，上限512筆。結束時才寫出hudTransitions，含probe相對時間、HUD原始旗標、引擎renderedAtSeconds與frameDeltaSeconds；超出容量明確標示hudTransitionsTruncated，不覆寫最初證據。一般啟動沒有診斷收集。

原有weather／HUD圖像模式也保存轉換及captureTimings（ReadPixels、PNG編碼及檔案寫入整段耗時），有助比對停頓；不能藉此斷言因果。舊報告沒有這些新增欄位，不補造旗標。trace-only報告不是GPU像素證據，仍需實際檢視玩家視窗；同主機多程序測試不代替跨機或頭盔效能。

`python scripts/check-desktop-pose.py --runtime-root C:/Users/USER/AppData/Local/VrCommand/SimulationRuns` 另建立自己的API、room3、真正server及可見client。先檢視ACTIVE並在該證據目錄建立loss.done；工具僅在兩個127.0.0.1端點間轉送原樣UDP，不解析或保存payload，對單一測試玩家依序丟棄上行1.2／1.2／6秒，下行維持，驗證body.connected=false、HUD顯示STALE而poseAccepted仍true。恢復封包後不重配票，核對原位置／健康／彈藥及ACTIVE；最後依fire階段真正按Space一次，再建立該證據目錄的fire.done，核對耗彈1與最終封存。此工具不改防火牆、網卡、正式5080或其他服務，所有來源仍Simulation；測試結束關閉自己的程序、socket及thread。固定封包中斷是可重現的保護／恢復驗證，不能回推舊場停頓原因。

42項真正EditMode包含原有狀態／方位／遮擋檢查及新增警告分類、短於週期採樣的轉換、容量與保留最初證據。實際建置、最新回歸及限制見 [PROGRESS.md](PROGRESS.md)。bundle0.19.1／Android code21、NGO仍18；API0.16、rules0.8.0、primitives-v1及世界／事件契約保持。這輪是HUD與診斷呈現，原本的物件幾何及命中盒未改；沒有頭盔或25台驗收。
