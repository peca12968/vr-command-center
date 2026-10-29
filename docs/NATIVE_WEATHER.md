# 原生 Windows 天氣畫面與音訊量測

2026-10-30 v0.20的新掩體／URP材質回歸通過：274幀／最大來源年齡0.157371秒、GPU閃電亮度差32.6950、首次觀測flash141／thunder184（預期180，10Hz採樣容差內）；穩定Pause52／Clear57窗口RMS0。PC原生白天／雨夜／Pause及保存的模型回放亦已檢視，見FIELD_PROPS與PROGRESS；不代表頭盔或實體聽感。

2026-10-30 v0.19.1／Android code21／NGO仍18同源建置後，再以 `20261030-005548-22ee28c2` 通過原生GPU／DSP回歸：275幀、最大來源年齡0.160839秒、閃電亮度差27.6674、首次觀測flash141／thunder181（預期180）。穩定Pause52／Clear59窗口RMS0；六次GPU讀回／PNG／寫入18.32–24.30ms，不能回推舊場停頓原因。詳見PROGRESS與TACTICAL_HUD，以下保留首輪v0.18.1紀錄。

需求5的電腦端驗證現在可直接啟動真正 Unity server／可見玩家，量測該玩家實際 AudioListener 混音及 GPU backbuffer。素材仍是開發用合成雨雷聲，頭手及戰鬥來源均為 **Simulation**。這不代表實體喇叭／耳機、人員聽感、Quest／VIVE、MR或25台驗收。

## 啟動

先依 [QUEST3.md](QUEST3.md) 建置目前 Desktop，再依 DESKTOP 建置 API。使用 Python3.12+；影像分析需 [Pillow12.3.0](https://pypi.org/project/pillow/12.3.0/)，可在自己的 Python 環境安裝 `scripts/requirements-desktop-weather.txt`，不需要更動系統音效設定。

```powershell
python -m pip install -r scripts/requirements-desktop-weather.txt
python scripts/check-desktop-weather.py --runtime-root C:/Users/USER/AppData/Local/VrCommand/SimulationRuns
# 可加 --api-dll <同次隔離建置的 API DLL>；若有既存 Pillow 環境，直接使用該 Python。
```

工具只建立自己的 API、臨時憑證、房間3、無敵軍任務、server／可見 client，按序執行：夜間閃電→延遲雷聲→暫停→白天下雨→夜間暴風雨→晴天→End／精確封存。它不注入姿態、tick或音訊，不修改正式5080服務，也不錄麥克風、Windows loopback或其他程式。所有圖像、PCM及報告均由本玩家的引擎產生，Python只讀取／驗證。

需要明確 SSD runtime，以程式印出的實際解析路徑為準；某些桌面執行環境會解析到自己的 C 槽應用程式資料位置。全部 writer 關閉後，工具複製 runtime-snapshot 回 F 的 `artifacts/desktop-venue/<時間-識別>/`，保留 SSD 原件，不搬移既有服務或資料。沒有降低持久錄製頻率或1.5秒來源年齡門檻。

## 量測內容

一般啟動不會附掛探針。只有未追蹤的 Windows Development client，明確帶 `--vr-weather-probe <全新絕對目錄>` 才啟用；現有目錄拒絕覆寫。Quest、Editor、無圖形／batch及非Development啟動無法由此開關啟用。頭盔／玩家設定仍只持有短效票券。

`NativeWeatherProbe` 掛在本玩家 AudioListener，透過 [Unity OnAudioFilterRead](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/MonoBehaviour.OnAudioFilterRead.html) 收到引擎DSP鏈的交錯PCM；不修改音訊資料，也不在音訊執行緒進行檔案I/O或呼叫Unity場景API。只在測試模式配置有界緩衝，記錄每批RMS／peak；End後輸出16-bit PCM WAV，並由Python核對格式、樣本數及量化後能量。

GPU圖像由實際渲染幀結束後的 ReadPixels 取得，保存夜間、閃電、暫停、白天、雨景及暴風雨PNG。比較夜間／閃電同一畫面區域的平均亮度，同時核對實際Light強度與AudioSource狀態。畫面讀回需要正式內建 Image Conversion1.0.0 模組，已經真正UPM匯入及保存lock。這不是軟體WebGL、EditMode畫面或僅檢查設定值。

單次診斷上限約85秒，音訊緩衝容量90秒；溢位、格式／取樣率改變或缺少回呼均會使檢查失敗。此探針會增加讀回、記憶體及I/O成本，不用於正式場館或效能量測。

## 規則與證據邊界

沿用環境v1：140tick閃電週期，40tick後雷聲；初次加入／跳轉不補播錯過的聲音。檢查器用10Hz觀測容差核對首次雷聲開始，再核對真正DSP非零輸出。暫停會停止雨雷聲；關閉雷電不啟動新雷聲，已播放的雷聲尾音會自然結束。晴天雨聲停止，檢查等待既有雷聲尾音結束後再確認靜音。沒有更改原有聲光規則。

2026-10-29 首場 `20261029-230508-0b5e7d5e` 通過：34項真正EditMode及Windows成功建置後，GPU閃電區域平均亮度增加34.54（0–255）；48kHz雙聲道、24.085秒PCM，雷聲／雨聲／暴風雨區間RMS非零，暫停及尾音後晴天區間RMS=0。首次觀測閃電tick141、雷聲tick183（預期cue180，符合觀測容差）；276幀世界精確封存、最大來源年齡0.614726秒、回放／統計一致、活動0、cleanup零錯誤。已檢視night.png／flash.png，詳細及最新回歸見 [PROGRESS.md](PROGRESS.md)。

後續修正10Hz快照與DSP回呼在Resume邊界的分類時點，排除轉換兩側不確定區間，門檻保持。最終 `20261029-232018-64b01ff3` 重驗273幀／0.154812秒，觀測flash140／thunder180、亮度增加34.54；雷聲／雨聲／暴風雨有非零輸出，暫停53批及尾音後晴天57批RMS均0。一般無probe可見玩家的33項控制台整合另通過，完整失敗與限制見PROGRESS。

遊戲端bundle0.18.1／Android code19，NGO仍18；API0.16、世界schema1／environmentVersion1及驗票2不變。這輪沒有新NGO欄位或遊戲規則改動，所有交付仍以成功receipt及保存場景識別為準。

PCM與GPU截圖只在明確啟用的開發診斷中保存，不進入worlds.db，也不是一般任務的原始音軌／影片錄製。控制台回放仍依保存tick重建環境聲光，見 [ENVIRONMENT.md](ENVIRONMENT.md)。人員聽感、音量／聲壓、實體輸出裝置、長任務與混合頭盔仍須另驗，完整11項保持開發中。

v0.19另有互斥的 --vr-hud-probe 模式，285秒／不保存PCM，見 TACTICAL_HUD；weather模式仍85秒與90秒有界音訊緩衝。report新增選用HUD繪製快照，只作診斷，不更改世界／事件資料契約。
