# 天氣聲光與版本化重現 v0.16

需求 5 的顯示來源為同一份 C# 9／.NET Standard 2.1 `EnvironmentPresentation`。Unity 有雨線網格、霧、日夜光照、閃電及兩個 AudioSource 的接入來源；瀏覽器觀戰／持久世界回放已有實際 Chromium／Web Audio 驗證。Unity 整個工程、Shader／AudioImporter、NGO、EditMode、APK 與頭盔仍未通過，不能把部分 SDK 型別檢查當成 Quest 驗收。

## 操作與時間

任務及即時環境命令仍用 Clear／Rain／Fog／Storm、Day／Night、lightning。世界錄製 header 的 `environmentVersion:1` 啟用此版本的重現；主控台在「觀戰與任務回放」顯示版本說明，點「音效：關閉」才建立／恢復 Web Audio 並載入素材。切頁／中斷／暫停停止音源；登出關閉音效。音量是開發預設，尚未有場館音量驗收。

效果僅從權威模擬 tick 取樣，不在客戶端推進戰鬥時間。20 Hz 下每 140 tick（7 秒）一個閃電週期，閃光 3 tick（150 ms），觀察到該次閃電且連續接收後於 40 tick（2 秒）播放一次雷聲。首次加入、倒退、超過 10 tick 的缺口、設定變更及跳轉不補播錯過的雷聲。暫停凍結雨的位置、取消持續閃光並停止聲音；繼續後按新的連續觀察判斷。雷聲間隔固定，並非依聲源距離傳播。

即時觀戰按 UTC 擷取時間判斷新鮮度，未知、超前超過 1 秒或過期超過 1.5 秒即停止聲光活動；重新收到資料不會把舊擷取時間改新。Unity 按最後收到 Presentation 的本機單調時間，超過 1.5 秒視為暫停。日夜／天氣／phase／tick／房間位元遮罩使用同一個 NGO WeatherState，生成器 protocol／Android code 16、bundle 0.16.0；所有遊戲端與 GameServer 需同版重建。

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

26 份 Unity C# 9 語法通過。`scripts/check-weather-unity-api.ps1` 另以已安裝 Editor 的真正 CoreModule／AudioModule DLL 編譯 **UnityWeatherView 單一元件**（0 警告／0 錯誤），不是 SDK stub；沒有編譯 SceneAuthority／NGO 或執行 Unity。18 項 EditMode 尚未執行。最新實際 Prepare 退出 198，日誌明確為找不到有效 Editor 授權。

後續已擴大為 [managed SDK 檢查](UNITY_SDK_CHECK.md)，SceneAuthority、NGO 與所有 runtime／NUnit 來源在 Android／Windows 條件分支均能綁定真正 SDK 編譯；這補充上述較早的窄範圍證據。仍未執行 Unity／ILPP／18 項 EditMode，沒有 APK 或頭盔結果。
