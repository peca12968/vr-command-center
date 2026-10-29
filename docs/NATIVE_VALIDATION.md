# 真正 Unity 建置與電腦端驗證

後續桌面可操作練習場與 GPU／鍵鼠結果見 [DESKTOP.md](DESKTOP.md) 及 PROGRESS：最新為 25 項 EditMode、實際射擊／擊殺／換彈／暫停與統計封存。下方保留第一輪 21 項建置與觀戰排隊修正的證據。

2026-10-29 使用者確認 Hub 已有有效授權後，Editor 6000.3.27f1 已完成真正套件解析、編譯／ILPP、資產匯入、場景生成、21 項 EditMode、Windows 播放器與同源 Quest APK。這取代先前「只有 SDK 型別檢查／Prepare 198」的狀態。使用者目前沒有頭盔，後續先驗證電腦端；APK 的產出不代表已安裝或通過 Quest／VIVE 實機驗收。

## 建置與穩定識別

```powershell
./scripts/build-unity.ps1 -Target Prepare
./scripts/build-unity.ps1 -Target Tests
./scripts/build-unity.ps1 -Target Desktop
./scripts/build-unity.ps1 -Target Quest
```

Tests 要求新結果 XML、Passed、至少 25 項且零失敗（首輪為 21 項）。建置助手明確回傳 exit 0／1；找不到 Editor 的反例已確認回 1。Desktop／Quest 以新鮮的 build-receipt.json 判定這一次是否成功，不能只看 exe 的時間：Unity 增量建置可能保留未改動的啟動 exe，同時更新資料／managed 程式。

receipt 只在 BuildReport 成功後寫入，包含目標、Unity 版本、完成 UTC、輸出路徑、程式／asmdef／套件鎖定的 SHA-256 fingerprint，以及 scene／prefab 的 GlobalObjectId。比較 Desktop／Quest 時，兩者應使用同一份來源 fingerprint 與網路物件識別；不部署 SDK 診斷產物。

Prepare 現在重用已保存的 Arena 與 PlayerAvatar，載入已保存物件讓 NGO 生成有效識別，再明確保存 scene／prefab。實測舊生成器第二次 Prepare 把 scene NetworkObject 本地 ID 從 1665048235 改成 1444571642；這會使分開生成的伺服器／客戶端識別不一致。修正後 Prepare、Desktop 及最終 Quest 都保持相同 GUID／file ID，scene／prefab 的 serialized NGO hash 均非零。場景重建由明確的 RebuildArena 執行，之後必須一起重建全部平台。

新增三項整合測試實際載入生成資產：重複 Prepare 的識別穩定、scene／prefab／音訊引用與缺失腳本檢查、Android OpenXR loader／Meta Quest／Touch profile 與 ARM64 設定。原 18 項姿態／契約／codec／天氣測試保持，合計 21 項全部通過。這些是 EditMode，不是頭盔、GPU 畫面或 25 人效能測試。

真正 UPM 首輪發現不存在的 com.unity.modules.textrendering，已移除；uGUI 的 UI／IMGUI 相依保持。TestAssemblies 會自動加入 TestRunner，原本重複明列的兩個 reference 已移除。真正 packages-lock.json 保存 Editor 的最低版本覆寫結果，與較早的 managed SDK 診斷圖分開記錄。原模板資產升級結果及生成物／meta／OpenXR 設定須一起保存。

## 真正 Windows 伺服器與兩個客戶端

先建置最新 API 與 Desktop，再執行：

```powershell
python scripts/smoke-unity-player.py
python scripts/smoke-unity-player.py --linked
# 隔離 .NET 建置時，可用 --api-dll 指定同次輸出：
# --api-dll artifacts/build-unity-first/bin/VrCommand.Api/release/VrCommand.Api.dll
```

工具啟動自己的隔離 API／SQLite、全新 Master／GameServer 憑證、一個真正 Windows Unity server 及兩個真正 Unity client，使用 v2 票券與 UDP／NGO。預設房間 5 獨立；--linked 合併五房，兩個客戶端分別加入房間 1／5。玩家雖使用契約內的 Quest3 分類，實際都是桌面合成頭手，origin 明確為 Simulation，沒有頭盔或硬體連接。

驗證兩位玩家入場及 Simulated rig、Running tick、敵軍 AI 的已確認傷害、暫停凍結、End 後戰鬥與世界精確封存、回放末幀／統計一致及活動場次清空。預設以本機共同 UTC 驗證取樣的 Running 來源年齡小於控制台既有 1.5 秒門檻；這是本機 smoke 條件，不是跨網路或 25 人的 SLA。

所有鍵、連線檔、API／player log、journal 與 summary 留在 Git 忽略的 artifacts/unity-player-smoke；不輸出憑證。工具只結束自己建立的場次與程序，不讀取／修改正式預覽資料。這是 -batchmode -nographics 執行，不含 GPU 畫面、鍵鼠射擊操作、音量聽感或實體追蹤驗收。

## 觀戰排隊修正

首輪實際 player 顯示：本地世界已到 tick 549，但 API 只收到 tick 63，戰鬥 journal 卻已持久確認序號 2。另一輪雖可封存，取樣觀戰仍落後約 12 秒；因此不能僅憑最後封存就稱為即時。

WorldPublisher 的網路 await 現在不捕捉 Unity 同步內容，WorldRecordingDelivery 成功送出後不再額外等固定 50 ms；無可送幀／中斷才維持等待。仍保留單份 outstanding、combat ack 依賴、durable world ack 與 seal，沒有跳過或丟棄世界幀。codec 接入須可在背景處理獨立純 DTO；UnityWorldCodec 不操作 scene／UnityEngine.Object，[Unity 6.3 的 JsonUtility 文件](https://docs.unity.com/en-us/engine/6000.3/manual/programming-environment/code-reload-serialization/script-serialization/json-serialization) 支援這類背景序列化，並要求避免同時修改同一物件。

修正後獨立模式的一次正式 smoke：116 幀完整封存、兩個客戶端、暫停 tick 167，取樣最大來源年齡 0.46213 秒、AI 傷害合計 40；五房 Linked 一次 smoke：115 幀封存、玩家分別在房間 1／5、暫停 tick 172，最大來源年齡 0.424355 秒、AI 傷害合計 100。兩次回放末幀與報表一致，活動場次皆 0。資料不是所有網路條件的延遲分布，也沒有 25 台量測；最終 binary receipt 結果另見 PROGRESS。Quest APK SHA-256 為 `3d62e37f8aba408316c6f88d142c87287eb6dec246780923dbe211cb4b47b06a`，67,969,388 bytes；v2 簽章與六份 ARM64 native library／IL2CPP ELF header 均核對通過。Desktop／Quest 來源指紋相同，詳見 artifacts/native-build-validation.json。

## 待驗收

Quest／VIVE 的實際安裝、控制器、追蹤中斷、混合頭盔共用座標、MR 透視／遮擋、硬體供應商介接、正式軍事美術、圖形／音量與 25 人效能尚未完成。使用者目前明確要求先繼續電腦端，不再等待或要求立即連頭盔。
