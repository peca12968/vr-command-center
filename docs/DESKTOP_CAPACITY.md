# 25個原生PC玩家的同機驗證

`scripts/check-desktop-capacity.py`使用自己的API／憑證／全新runtime，依序驗證一個Linked世界的25個原生client，再將該世界結束、精確封存並停止自有程序，另開五個獨立世界、每房五個client。這是Windows／UDP／NGO實際程序與合成頭手 **Simulation**，不是25台電腦或頭盔，也不合併歷史世界。

```powershell
python scripts/check-desktop-capacity.py --api-dll artifacts/build-report-v1/bin/VrCommand.Api/release/VrCommand.Api.dll --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns"
```

預設`--mode both --players-per-room 5 --seconds 60`；可選linked／independent、每房1–5人、穩定期30–300秒。降低人數只作較小範圍檢查，不算25人通過。必須有目前成功Windows build receipt／source fingerprint及API0.27，官方嵌入Transport檢查仍保留；沒有重新建置或重建Arena。所有client均無圖形、每程序兩個job worker，沒有時序／GPU／PCM探針、視窗自動化、姿態／武器注入或故意丟包。頭盔欄位Quest3只是名冊分類，rig來源保持Simulated。

名冊核對五個不同出生席0–4、playerId／admissionId、每房上限及第六位拒絕。每個client以admission ID命名，獨立Popen／設定／日誌，不以同房號覆蓋。分批等待已啟動玩家被真正server接受，核對各client日誌的單一NGO connection ID與獨立PID，同一server下ID不可重複，結束後再次核對未換連線。這證明實際入場與server接受的姿態，**不代表已量測每個client的完整遠端複本／互見**。

穩定期以原擷取UTC檢查來源年齡<1.5秒，不能用收到時間替代；每張取樣須有全部玩家、正確房間／出生位置、Simulated rig、健康100與connected=true，並維持Running且未因管理連線失去而suspend。接著驗證Pause凍結目標tick、Resume前進；獨立模式的其他四房維持運行。啟用真正server敵軍Advance／autoAttack，等各房都有權威中彈統計後關閉攻擊，不注入戰鬥事件。穩定期與AI階段分開：這不是60秒持續25人射擊／移動或高強度AI負載測試。

End之後先等戰鬥與世界精確seal，核對CSV全玩家、來源、序號與ledger／回放統計。停止全部自有native後，透過授權API以4倍速順序回放，穩定期起點前至最終幀必須序號連續；每張穩定期已保存幀皆重新驗證完整名冊／出生位置／健康及姿態有效，不能以少數live取樣代替。回放最後一幀須等於精確封存結果；不直接開原SQLite或snapshot SQLite。

來源／binary仍在F；F為USB硬碟時，應如上明確指定C SSD的全新runtime。工具不搬動既有預覽資料。每次啟動及定期檢查[GlobalMemoryStatusEx](https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/nf-sysinfoapi-globalmemorystatusex)的可用實體記憶體，少於2 GiB停止新增／繼續檢查並走自己的End／seal／cleanup；這是揮發性的主機資源保留檢查，不是產品效能門檻或記憶體保證，不會關閉其他應用或更改分頁設定。原1.5秒新鮮度不放寬。

資料在`artifacts/desktop-capacity/<時間-識別>/`，有自己的latest-desktop-capacity-path.txt，不蓋五房／練習場pointer。capacity-result記錄同機／headsets0／renderedClients0與各模式；native-clients保存自有PID／player／admission／connection對應，設定和臨時憑證保持私有。各場report.csv另命名，避免互相覆寫；沿用練習場預設報表檔名的呼叫不變。全部writer停止後一次複製runtime-snapshot回F，保留SSD原件。失敗非零、保留資料；只有所有檢查與精確seal成功、活動場次0才有成功結果。

共用Venue的觀察／設定JSON改為同目錄暫存檔完成寫入後原子replace；對Windows短暫PermissionError／分享衝突有最多2秒等待，消費者`read_json`對同類存取錯誤也有有界等待，格式錯誤立即失敗，持續權限錯誤仍失敗、不改ACL。這是觀察檔一致性，不替代SQLite／journal的durable flush。快照在所有追蹤writer退出後，最多5秒等自己的兩個writer lease可共享讀取，持有read handles時才copy一次；不強制解鎖、不改ACL，不重試覆蓋既有或失敗副本。完整成功需cleanup無錯誤、capacity-result.complete=true及最後stage=passed；sealed僅代表功能封存完成。原不完整副本保留供調查，不手工改成成功。

20261031-100055-1d0cee1d的20項上述檢查及cleanup成功，但離線日誌複查發現Linked server有105行`send queue full`，無逐行時間戳，尚不能確定發生階段或各client的影響。因此stage=passed只表示列出的伺服器／生命週期檢查，**網路容量驗收仍未通過**。之後工具額外輸出`validationScope`、固定`networkCapacityAccepted=false`及`nativeLogFindings`，有佇列錯誤時明示WARN；這個最後的摘要增補只在已停止的本輪原始日誌離線核對，沒有再開25 client或改寫既有結果。錯誤數不是遺失封包數，不能由來源新鮮或封存一致推出各client皆正常。

這個範圍不涵蓋每個client的遠端複本收斂、實際玩家移動／射擊輸入、繪圖FPS／音訊、跨機／Wi-Fi、Quest／VIVE追蹤／MR、廠商硬體或25台完整任務驗收。時序偶發的根因與修復仍以[POSE_TIMING](POSE_TIMING.md)及PROGRESS為準，不把容量試跑當作修復證明。實際成功／失敗數據見PROGRESS。
