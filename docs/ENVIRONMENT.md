# 天氣聲光與版本化重現 v0.16

管理台 0.31.120 的「即時環境」與「敵軍設定」分別保存編輯中的草稿。送出其中一項後，另一項的未送出值會保留。場次仍可操作時，名冊、階段或另一項設定的更新不會使原草稿失效。若同項設定已有新版本，管理服務拒絕舊草稿並保留操作員輸入。「載入目前設定」會讀取最新值並取代該項草稿。

單一場次的 `overview` 回應提供 `settingRevisions.environment` 和 `settingRevisions.enemies`。管理台將對應版本放入 `SetEnvironment` 或 `SetEnemies` 的 `expectedSettingSequence`。後者也核對分房策略，避免套用舊的全場設定時清除較新的分房覆寫。舊版用戶端原有的場次序號欄位繼續適用。

## 全館即時環境

Windows 管理包 0.31.35 起，主控可在五房總覽的「全館即時環境」選擇天氣、白天或夜晚，以及閃電開關。確認視窗顯示本次房號與設定。獨立模式會在同一筆管理交易保存各場命令，合併模式只會保存一筆。各遊戲來源收到命令後依自己的活動時間套用。

這個操作只涵蓋執行中的場次，原場的 VR 或 MR 模式與保存的任務版本會保留。若送出前有房間改變階段或更新環境，整批會拒絕，主控可重新整理並確認。回覆遺失時可重送原請求。房卡先顯示「全館環境待確認」，收到對上原環境命令序號和三項設定的有效快照後顯示「已套用」。快照超過原 1.5 秒有效窗會回到待確認。單房後續覆蓋環境時，該房的全館標記會清除。

管理包 0.31.57 的房卡也會確認單一場次的環境指令。全館或單一場次的指令套用後，按「檢視環境快照」可在該房的俯視圖停在原錄製中確認該設定的一格。它是當時保存的畫面。來源過期、場次變更或新指令尚未確認時，入口會隱藏。合併場次的房卡共用原錄製及快照，點選時依房號定位視角。

`GET /api/venue/phase` 的 `environment` 預覽提供房號、場次 ID、階段與環境序號。`POST /api/venue/phase` 使用 `SetEnvironment`、原本的 `sessionId`、`phaseSinceSequence`、`environmentSinceSequence`，以及含 `weather`、`timeOfDay` 和 `lightning` 的 `environment`。同一原請求用同一 `Idempotency-Key` 取回回條。`GET /api/rooms/readiness` 的 `venueEnvironment` 附環境值、原命令序號及有效的世界快照序號。

同一房間回應的 `environment` 同時涵蓋全館和單一場次指令，包含 `setting`、`venue` 與已確認時的 `streamId`。檢視時用同一格的 `fromFrame` 和 `throughFrame` 讀原場次錄製，核對來源、原環境指令序號及三項環境設定。

### 只調整指定獨立房間

管理台 0.31.229 起，可在「全館即時環境」的「套用範圍」選「指定獨立房間」，勾選要調整的執行中房間。送出前會列出原房間與天氣、日夜、閃電設定。若所選房間已換場，必須取消勾選並重新選擇；若在送出時所選場次或環境版本已變更，整批會被拒絕。

五房合併場選「所有執行中場次」，共用同一套環境。指定房間的 `SetEnvironment` 請求多帶 `roomIds`，各房須有對應的原場次及環境序號。省略 `roomIds` 即使用所有執行中場次。最近一批環境指令與世界畫格核對會按原命令的實際房間列出。

### 核對最近一批環境指令

控制台 0.31.71 在「全館即時環境」下顯示最近一批接受的天氣、日夜及閃電設定，並列出每個原目標房間與命令序號。主控重新登入或管理服務重啟後，仍可從原命令紀錄查閱。

各房依目前場次顯示「遊戲端待確認」、「遊戲端已套用」、「已被較新的環境設定覆寫」或「原場次已結束」。同樣的天氣設定若由另一筆命令覆寫，仍依原序號辨識為覆寫。合併場的五房共用原場次及命令序號。結束後即使房間重新使用，也會顯示原場次狀態。

控制台 0.31.197 可在已覆寫或已結束的列按「查找原環境畫格」。從原場次與原批次找第一格有效執行畫面，並在當時房間的俯視圖暫停。查找比對原命令序號、天氣、日夜和閃電。若該序號沒有保存執行畫格，畫面會顯示找不到的原因。

管理包 0.31.250 會在原環境設定生效期間找第一格有效執行畫面。遊戲即使在暫停、恢復後才回報，只要原設定仍然生效，便可開啟該格。後續重新下達相同天氣、日夜和閃電的指令也會劃出新界線。查找回應會在有畫格時提供 `observedSequence`，並在原設定已覆寫時提供 `supersededAtSequence`。

只有原場次、環境命令序號、三項設定及遊戲來源都相符的有效畫格可用「檢視環境快照」開啟該房的原錄製俯視圖。畫格過期會撤下捷徑。`GET /api/venue/phase` 的 `latestEnvironment` 只供主控讀取，未接受過全館環境指令的管理實例會省略該欄位。 [驗證紀錄](PROGRESS.md#2026-11-10-最近一批全館環境指令逐房確認)

保存全館環境紀錄的管理資料庫須由 0.31.35 或更新的管理包開啟。

在管理包 0.31.153 的回放中，暫停後選取「設定種類」的「環境變更」，可查閱目前錄製內保存的天氣、日夜或閃電切換。即使後續有更新的環境指令，仍可依原錄製回看先前的變更。 [回放操作](WORLD_RECORDING.md#查閱錄製中的設定切換)

## 聲光與回放

需求 5 的顯示來源為同一份 C# 9／.NET Standard 2.1 `EnvironmentPresentation`。Unity 有雨線網格、霧、日夜光照、閃電及兩個 AudioSource 的接入來源；瀏覽器觀戰／持久世界回放已有實際 Chromium／Web Audio 驗證。後續真正 Unity 已通過整個工程匯入／編譯、Shader／AudioImporter、NGO、34 項 EditMode、Windows 及 Quest APK；五房 PC 已執行各自環境，完整 GPU／聲音聽感與頭盔仍待驗。下方保留初版 v0.16 診斷歷史，最新範圍以 PROGRESS／DESKTOP_VENUE 為準。

已新增 [原生Windows聲光量測](NATIVE_WEATHER.md)：實際GPU閃電截圖、玩家AudioListener雨雷混音與暫停／晴天靜音；沒有錄麥克風或其他應用程式。DSP非零與GPU亮度證據不等同人員聽感、實體裝置／聲壓或頭盔。

## 操作與時間

任務及即時環境命令仍用 Clear／Rain／Fog／Storm、Day／Night、lightning。世界錄製 header 的 `environmentVersion:1` 啟用此版本的重現；主控台在「觀戰與任務回放」顯示版本說明，點「音效：關閉」才建立／恢復 Web Audio 並載入素材。切頁／中斷／暫停停止音源；登出關閉音效。音量是開發預設，尚未有場館音量驗收。

效果僅從權威模擬 tick 取樣，不在客戶端推進戰鬥時間。20 Hz 下每 140 tick（7 秒）一個閃電週期，閃光 3 tick（150 ms），觀察到該次閃電且連續接收後於 40 tick（2 秒）播放一次雷聲。首次加入、倒退、超過 10 tick 的缺口、設定變更及跳轉不補播錯過的雷聲。暫停凍結雨的位置、取消持續閃光並停止聲音；繼續後按新的連續觀察判斷。雷聲間隔固定，並非依聲源距離傳播。

即時觀戰按 UTC 擷取時間判斷新鮮度，未知、超前超過 1 秒或過期超過 1.5 秒即停止聲光活動；重新收到資料不會把舊擷取時間改新。Unity 按最後收到 Presentation 的本機單調時間，超過 1.5 秒視為暫停。日夜／天氣／phase／tick／房間位元遮罩使用同一個 NGO WeatherState，原 v0.16 使用 protocol／Android code 16、bundle 0.16.0；目前 Unity NGO仍18／bundle0.18.1／Android code19、API 仍 0.16，環境規則不變；所有遊戲端與 GameServer 需同版重建。

Rain 每房 64 根雨線，Storm 每房 128 根；最多五房 640 根、1280 頂點，以單一網格繪製。位置在每房 12 × 12 × 6 m 的開發空間依固定公式重建。效果不影響命中、碰撞、尋路或傷害；目前沒有雨遮蔽、積水、風、真實天空、美術材質、MR 透視／錨點或實機效能證據。Fog 使用指數平方霧，Clear 無霧。

## 錄製及升級

新 header 預設 `environmentVersion:1`；缺少欄位或明確 0 保持 legacy，主控台只顯示原有光霧，不補造雨／雷聲。只接受 0／1，既有錄製不能改版本。schema 2 本機模擬回放沒有完整環境欄位，仍走既有顯示。

聲光依保存 tick、weather、night、lightning、phase 及固定素材重建，**不是原始音軌、影片或逐像素錄影**。不同播放器的材質、色彩與音量可能不同；共同向量檢查驗證數值／座標／雷聲判定，未宣稱畫面或聲壓相同。倍速仍按錄製時間派送，聲音本身維持原速；過大的 tick 缺口會抑制雷聲。

先備份 root data 及實際 API data／WAL／key，再一起更新 API、UI 與來源。舊 worlds.db schema 1／session envelope 6 不變，但舊嚴格 reader 不接受新欄位，不能直接降版。讀舊 metadata 只在回應補 0，不改寫資料庫原 header。WorldOutbox 以 codec 正規化後比較語意，保留來源檔原始 header JSON 與 checksum；舊 NDJSON／binary journal 可原樣補送。`captureStartedAtUtc` 現在也由新的 NDJSON 示範提供，既有缺時間的來源仍保持未知。

## 素材與可重現示範

原始 PCM 在 `clients/unity/Assets/VrCommand/Audio/`，雨聲／雷聲均由 `scripts/generate-weather-audio.py` 的固定整數雜訊、濾波與包絡生成；未使用第三方錄音。各 4 秒、單聲道、22050 Hz、16-bit；provenance 保存 SHA-256 與規格。`python scripts/generate-weather-audio.py --check` 精確核對 WAV／provenance 與 meta GUID。API 直接打包同一份 WAV 至 `/console/audio/`，避免重複來源。這是開發用合成聲音。

已建置 Release 後，空房 5 可執行下列 Simulation；檔案必須不存在，工具只控制自己新建的場次：

```powershell
dotnet run --project tools/VrCommand.WorldRelay --configuration Release --no-build -- --world-journal artifacts/weather-demo.worldlog --demo-room 5 --seconds 12 --environment-demo true
```

`--environment-demo true` 僅能搭配新建 `--demo-room`，預設 Storm／Night／lightning；未指定則維持 Clear／Day。完成後在觀戰頁選該場次回放，開啟音效並從頭播放超過 9 秒；直接跳到雷聲時間不會補播。來源、頭手及戰鬥均標記 Simulation，沒有頭盔連線。

## 驗證範圍

本機 472 核心、369 HTTP、43 世界串流、17 Node 資料／跨語言向量、122 Chromium，共 1023 項通過。包含 144 組環境樣式、60 組雨座標、85 組 cue 步驟的 C#／JS 比較，舊 header／journal 補送、拒絕改版、真實 Web Audio 非零輸出及雷聲啟動、回放閃電、跳轉抑制與暫停。音訊圖驗證不代表人員聽感驗收。

初版歷史：26 份 Unity C# 9 語法通過。`scripts/check-weather-unity-api.ps1` 另以已安裝 Editor 的真正 CoreModule／AudioModule DLL 編譯 **UnityWeatherView 單一元件**（0 警告／0 錯誤），不是 SDK stub；沒有編譯 SceneAuthority／NGO 或執行 Unity。18 項 EditMode 尚未執行。最新實際 Prepare 退出 198，日誌明確為找不到有效 Editor 授權。

後續已擴大為 [managed SDK 檢查](UNITY_SDK_CHECK.md)，SceneAuthority、NGO 與所有 runtime／NUnit 來源在 Android／Windows 條件分支均能綁定真正 SDK 編譯；這補充上述較早的窄範圍證據。該較窄工具本身未執行 Unity／ILPP／EditMode 或產出 APK。後續真正 29 項／建置另有證據；沒有頭盔結果。
