# 任務版本讀取恢復

API／UI **0.30.1** 修正背景列表刷新失敗連帶取消任務讀取的缺口。操作員選取已保存版本、按「載入選取版本」時，舊程式先等正在進行的列表刷新；若該刷新回傳503，便在發出所選版本的GET前結束，草稿仍是原版本。

現在「載入最新版」、「載入選取版本」及版本分頁仍先等正在進行的刷新；相同登入下的傳輸／無HTTP狀態錯誤或5xx失敗後，可以繼續這次明確的任務GET。它從伺服器重新讀取history／version，沒有以快取冒充結果。讀取成功仍顯示「已讀取任務；背景列表更新失敗，請稍後重新整理」，不把其他列表／場次資料標成已更新。

401／403及其他4xx不走此恢復；登出／登入epoch變更會取消尚未開始的讀取。所選history／version本身失敗時，保留先前草稿並顯示錯誤，不改用其他版本。建立／修訂任務、場次控制、加入／移除玩家及原樣重試維持原刷新失敗限制與待確認請求鎖定。這次只給三個明確的任務讀取入口選用恢復，沒有將例外套到所有操作。

沒有改API路由、權限、不可變任務版本、expectedSequence／UUID／入場或姿態政策。Unity0.36.1／code44／NGO29、rules0.8.0、原scene／prefab及Windows／Quest receipt不變；不需要重新Prepare或重建頭盔場景。新API與UI一起部署，開發工具版本檢查同步0.30.1；既有玩家包與此版API的原生驗票／重連相容性另有實測。

## 驗證

`tests/browser/mission-read-recovery.cjs`使用隔離真API與實際Chromium。它建立自己的任務及22個不可變版本，只對自己的瀏覽器頁面注入列表GET的503／網路失敗／403／401；玩家姿態、武器與戰鬥沒有注入。

一般`pnpm --dir tests/browser test`包含這組回歸。也可只跑此情境；focused輸出明確標示範圍，不能冒充完整瀏覽器回歸：

```powershell
$env:VR_COMMAND_API_DLL = '<新建置的0.30.1 API.dll>'
$env:VR_COMMAND_BROWSER_ARTIFACTS = 'F:/Projects/vr-command-center/artifacts/console-mission-read-new-run'
node tests/browser/check.cjs --mission-read-only
```

輸出必須是新的直屬artifacts/console-*目錄，既有目錄會拒絕。測試核對歷史／最新定義、未提前換草稿、保留列表警告、所選history自身失敗、寫入未發出、403拒絕、401登出、等待途中登出後沒有舊讀取／草稿恢復，以及真正20筆分頁後取得餘下2版且不重載草稿。最多256筆任務路徑／方法metadata，截斷不得成功；不存headers／票券／回應payload，失敗另存當時狀態及畫面。

2026-11-01 舊0.30.0 API的受控503在原handle46558 **exit1**重現：第一版已選、草稿仍第二版，沒有發出所選history讀取。新0.30.1的專項10項及擴充15項通過；新增情境包含於完整回歸。這是新的受控缺口與修正證據，**不能據此宣稱已證明前輪雲端歷史載入逾時的根因**。

真正Windows遊戲端非互動入場／驗票／重連8項、355幀及cleanup成功，仍是同機Simulation、無新Unity建置／179 Editor重跑或頭盔操作。完整回歸、失敗、CI與原件保存證據見[PROGRESS](PROGRESS.md)。舊31筆／world371姿態失效、跨機／25位同時操作、MR及硬體另驗，完整11項維持開發中。

[2c33d1d完整雲端CI](https://github.com/peca12968/vr-command-center/actions/runs/41268781091)成功，717規則／459 HTTP／47串流、Python／素材及72 Node／248 Chromium通過。本機248瀏覽器亦成功；本機完整HTTP在invalid credential程序退出等待逾時仍未解，沒有因Linux成功而改判。候選啟動調整未納入發布，正式憑證規則與期限保持，完整範圍見PROGRESS。
