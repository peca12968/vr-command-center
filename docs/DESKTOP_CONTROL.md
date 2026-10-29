# 從控制台開啟電腦任務

`scripts/start-desktop-control.py` 啟動自己的 API／任務庫，將操作員在該控制台建立的 Preparing VR 場次接到真正 Windows Unity server。從實際名冊配發短效票券並啟動玩家；開始、暫停、環境、AI 及結束都由控制台操作，不預先代替操作員建立任務或開始遊戲。這是 **Simulation**，頭盔分類不代表實際連線設備。

API／UI v0.18 增加 [場地檢查](LAYOUT.md)：保存草稿後，選定保存版本與單房／全館模式，通過配置檢查才建立新 VR 場次。問題可點選回物件修正並保存下一版；不能以尚未保存的草稿放行舊版。工具在建立任何場次前拒絕舊 API。MR／實體校正與複雜通路仍待驗。

先依 DESKTOP 建置目前 API 與 Desktop，於專案根目錄執行：

```powershell
$operatorData = Join-Path $env:LOCALAPPDATA 'VrCommand\SimulationRuns'
python scripts/start-desktop-control.py --runtime-root $operatorData --visible-room 1
```

程式碼與播放器在 F 槽，SSD runtime／關閉後複製回 F 的規則與 DESKTOP_VENUE 相同。可指定 `--api-dll`／`--player-exe`；播放器 receipt 必須符合目前來源。預設 900 秒，`--duration 60..1800`；`--visible-room 0` 為全部無圖形，1–5 選擇第一個可操作玩家所在房間。每程序預設兩個 job worker。

## 操作

1. 開啟工具顯示的控制台 URL；只用該次 `artifacts/desktop-venue/<時間-識別>/keys.json` 的臨時 Master 值登入。不要使用正式 5080 憑證。控制台憑證只在頁面記憶體；玩家設定沒有 Master／GameServer key。
2. 在「任務庫與編輯」設定名稱、時間、內容與初始天氣／敵軍，擺放沙包／油桶並儲存。可清除草稿、重新載入保存版本，再明確選擇其開場。修訂不改變已存在的場次。
3. 目前本機遊戲接入使用 **VR**：物件素材為 sandbag／barrel、Y=0、X／Z 在各房中心 ±6 公尺內；配置圖仍可編輯更大範圍，但這不表示目前 Arena 接受。沒有自動縮放／裁切或 MR 校正。
4. 在「房間與場次」選任務及房間，建立 Preparing 場次。獨立或全部房間 Linked 都沿用 API 權限／占用規則。工具只接自己這個 API 的全新 Preparing、尚未綁來源的 VR 場次，不接管執行中或已有 journal 的世界。
5. 加入玩家。工具按名冊的 playerId＋admissionId 啟動真正 client；選定房間的第一位玩家開視窗，其他玩家背景運行。Preparing 時移除／換入場會關閉舊 client，新增名冊會啟動新 client；舊統計仍保留。看見玩家視窗或在觀戰中確認已連線後再開始任務，避免在 native recording 尚未建立時提前 Begin。
6. 透過控制台開始、暫停、繼續，調整場次天氣／日夜／閃電及敵軍數量／策略／自動攻擊。表單過時依原 409 規則重新載入，不強行覆寫。設定須由 server 接受後才出現在世界；頭手與戰鬥走 NGO，不走管理 REST。
7. 在「觀戰與任務回放」選該實際錄製，即時全景／俯視／跟隨／自由調整，命名保存鏡頭。End 後等待精確封存，再從頭回放、跳轉或切換保存鏡頭。觀察不占名額。

亦可輸入看向世界座標、水平／俯視角與距離，精確切換視角；讀取目前鏡頭、草稿及書籤操作見 [OBSERVER_CAMERA.md](OBSERVER_CAMERA.md)。

操作員 End 某場後，工具等雙管道封存並停止該場自有 native 程序，仍可在時限內開下一場；舊回放／統計保留。關閉可操作玩家、Ctrl+C、時限到，或在該次目錄建立空白 `end.request`，會結束所有已接入場次並收尾。工具不是正式場館服務管理器、世界崩潰恢復或任意外部 API 啟動器。

`ready.json` 保存自己的 URL／runtime 及 build receipt；`operator-status.json` 從實際接受的世界幀記錄 phase／tick／環境／AI／連線玩家，不是自造控制回應。持續量測來源 UTC 年齡，維持原 1.5 秒門檻，過期即失敗並保留 journal。`summary.json` 及 `cleanup.json` 分開記錄封存／報表一致性與清理／runtime 快照；清理失敗非零退出。動態名冊的最終統計按持久 PlayerJoined 歷史核對，不丟掉已離場者。

## 重複驗證

工具顯示自己的目錄後，另一個終端可執行：

```powershell
pnpm --dir tests/browser exec node check-operator-native.cjs F:/Projects/vr-command-center/artifacts/desktop-venue/<該次識別>/ready.json
# --manual-inspection 在白天／雨夜／暫停階段等待真正原生視窗檢查；
# 各階段的 .done 只推進測試，不注入任何遊戲姿態或戰鬥事件。
```

此檢查器只接受本庫該目錄形狀、Simulation／0 頭盔、localhost 非 5080 的 ready，不接受任意正式憑證或遠端 API。它透過真正瀏覽器 UI 建立／重載任務、配置、名冊、移除替換玩家，控制環境／AI，再對照真正 Unity 世界與報表、保存／切換鏡頭及回放；結束時只建立該 fixture 的 end.request。測試瀏覽器為 Chromium SwiftShader，原生 GPU 畫面須另外由 computer-use 檢查，不能把軟體 WebGL 或 API 接受當成頭盔／原生畫面證據。

最新成功、失敗與截圖見 PROGRESS。已觀察 PC 白天、雨夜與暫停；原生雷聲聽感、完整聲光／碰撞／自由鏡頭人工操作、軍事美術、MR、Quest／VIVE、跨機與 25 台仍待分別驗收。
