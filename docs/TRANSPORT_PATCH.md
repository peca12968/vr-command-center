# Unity Transport 失敗接收緩衝區修正

2026-10-29 原生 Windows 測試中，強制結束一個玩家程序後，伺服器程序與 UDP 埠仍存在，但後續連線無法進入 approval callback。用只轉送原封包的本機診斷代理觀察到新 client 持續送出、server 沒有回應；增加等待或啟用桌面背景更新都沒有解決。這些失敗紀錄保留在 artifacts/unity-admission 與 unity-admission-proxy.log，不算通過。

[Unity 工程師確認的問題與修正](https://discussions.unity.com/t/unity-transport-6-6-0-udp-host-stops-receiving-after-abrupt-client-disconnect-on-windows/1736023) 描述相同 Windows／ICMP 失敗接收耗盡佇列的情況。該討論的重現版本較新；本機真正使用的 2.7.4 仍有相同未釋放分支，因此需以本專案原生結果另行確認，不能只套用討論結論。

查詢官方 registry 時 latest 仍是 2.7.4，沒有可直接升級的官方修正版。保留固定 Editor／NGO，將官方 2.7.4 archive 物化為 `clients/unity/Packages/com.unity.transport/` 的 embedded dependency；不修改 Library 快取。`Runtime/UDPNetworkInterface.cs` 的失敗 receive completion 分支只增加一次 `ReceiveQueue.ReleaseBuffer(bufferIndex)`，在 continue 前歸還原請求緩衝區，其餘上游檔案保持原始 bytes。沒有用增大容量來取代回收，也沒有更動防火牆／安全設定或改用不同測試連線路徑宣稱修復。

官方來源為 `https://download.packages.unity.com/com.unity.transport/-/com.unity.transport-2.7.4.tgz`，固定 SHA-1 `98ef8bfec34d7eea791603fc1e45ce86c3484180`。UPSTREAM.json 保存 archive SHA-256、293 份檔案的原始及嵌入 SHA-256、精確修正位置與來源。原 LICENSE／copyright、Samples／Documentation 與 metadata 保留；原套件簽章／attestation 不套用到修改版本，沒有帶入。Git 對此依賴保留原始換行與 bytes。

```powershell
python scripts/check-transport-patch.py
# 從不存在的目錄重建時才使用 --materialize；既有目錄拒絕覆寫。
```

檢查器逐檔比對清單與雜湊，要求只有該檔案的一處修正；不是只搜尋一個程式片段。真正 UPM lock 必須為 embedded，Windows／Android 都須重新建置。建置 receipt 的 source fingerprint 另納入 embedded Transport 的 C#／asmdef 與 UPSTREAM.json，不能用舊 registry binary 的 receipt 充當本次結果。

軟體範圍依原 Unity Transport 的 [Unity Companion License](https://unity.com/legal/licenses/unity-companion-license) 與有效 Editor 授權；維持原通知，並未將第三方程式稱為本專案原創。之後有官方修正版時，需比較修正、更新 pin／receipt 並重跑失敗接收與原生斷線回歸後，才可移除嵌入修正。

真正 Windows 小接收佇列 NetworkDriver 測試已通過，29 項 EditMode 零失敗／零跳過；重新建置後直接 UDP 的無圖形與實際視窗 admission 回歸各八項通過。視窗場強制斷線後恢復相同位置／健康／彈藥，1648 幀完整封存。Windows／Quest receipt 包含相同嵌入來源指紋，詳見 [PROGRESS.md](PROGRESS.md)。這不是跨機 LAN、Quest／VIVE、Relay、任意惡意流量或 25 台效能保證。
