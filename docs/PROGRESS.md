# 開發進度

## 2026-10-28：建立長期目標及 M0

長期目標已在本對話建立，維持開發中；本地開發根目錄為 `F:\Projects\vr-command-center`。本檔保存接續工作的事實與依賴，整體需求見 `REQUIREMENTS.md`。

GitHub 長期開發追蹤：[Issue #1](https://github.com/peca12968/vr-command-center/issues/1)。階段完成後更新此追蹤與本地文件。

已建立管理核心、REST API、任務 JSON 範例、核心規則檢查與 GitHub Actions 工作流程。後端使用本機已有的 .NET SDK 10.0.400；尚未安裝或建立 Unity 工程。

Release 建置成功：0 警告、0 錯誤。15 項核心檢查全部通過，包含五房獨立、全館 25 人名額、併發加入限制、快照隔離、任務持久化與場次釋放。66 項 HTTP 斷言全部通過，包含實際服務啟動、JSON 往返、錯誤碼與完整名額操作。

上述測試在 Windows 本機執行。私人 GitHub 儲存庫已建立，首次提交 `f4b836a` 已推送至 `main`，遠端私有狀態與分支已確認。實際指令見根目錄 README；CI 設定使用相同建置、核心檢查及 HTTP 整合腳本。

GitHub Actions [首次執行](https://github.com/peca12968/vr-command-center/actions/runs/40720827902) 在任何 step 啟動前失敗。check-run `122930936531` 的 annotation 明確回報：最近帳戶付款失敗，或需要提高 spending limit。第二次提交的執行也於啟動前失敗。**雲端 CI 尚未驗證，不能標示通過**；未變更帳務或啟用付費執行器。本機測試仍可執行，M1 開發不受影響。

## 未完成與外部資料

- 尚無 Unity 客戶端、軍事畫面、遊戲同步、實際 AI、物件編輯畫面、硬體通訊、觀戰、回放或戰鬥統計。
- 尚未收到廠商 SDK／協議；需依 `HARDWARE.md` 取得資料。
- VIVE XR 確切型號、Android 一體機／PCVR、場館尺寸與網路架構待確認。
- 沒有頭盔或硬體實測證據；25 個玩家記錄通過不代表 25 人實際連線達標。

## 接續位置

GitHub 與 M0 本機驗證完成，接續依 `ROADMAP.md` 的 M1 開發場次狀態、命令及事件資料。GitHub 帳戶付款／支出限制解除後才可補驗雲端 CI。每次開始先讀本檔與實際 Git 狀態，避免把規劃當成已交付功能。
