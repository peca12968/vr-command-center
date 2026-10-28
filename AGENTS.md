# 開發指引

開發根目錄為 `F:\Projects\vr-command-center`；以此庫的實際 Git 狀態與執行結果為準。

開始接續工作時讀取 `docs/PROGRESS.md`、`docs/ROADMAP.md`、`docs/REQUIREMENTS.md`。使用者的完整目標為 11 項 VR/MR 遊戲需求及 VIVE XR／Quest 3 相容性，不能以管理原型或模擬測試通過替代完整交付。

後端為 .NET 10；Unity 工程位於 `clients/unity/`，固定 Editor 6000.3.27f1，不直接引用後端組件。未知硬體協議使用模擬器，實機整合待廠商文件及設備。

使用者已指定先用 Meta Quest 3；優先推進 Quest 3 的 Android 垂直切片，VIVE 相容性留待後續。模擬戰鬥必須使用 Simulation 標記，不能與 GameServer 資料在同場混用或宣稱頭盔實測完成。

`/api` 端點使用伺服器配發的主控／房間控制台身分。實作新路由時必須傳遞認證身分並檢查操作範圍，不能依賴核心的預設 Internal 身分處理 HTTP 請求。測試用獨立的暫存憑證；不要讀出或提交 `data/operator-keys.local.json`。

後端變更應執行：

```text
dotnet restore VrCommand.slnx --locked-mode
dotnet build VrCommand.slnx --configuration Release --no-restore
dotnet run --project tests/VrCommand.Checks --configuration Release --no-build
python scripts/smoke_api.py
```

`VrCommand.Checks` 是可執行的規則檢查程式，不能只執行 `dotnet test` 就宣稱已完成檢查。依功能實際影響補充有意義的測試，並將驗證結果、限制與下一步更新至 `docs/PROGRESS.md`。

遊戲事件、即時狀態、統計與回放應共享版本化契約；頭盔姿態與逐幀模擬不使用管理 REST API。實機相容、MR 校正、25 台頭盔效能與硬體控制須分別保留驗收證據。

瀏覽器主控台在 `src/VrCommand.Api/wwwroot/console/`，操作與真實瀏覽器檢查見 `docs/CONSOLE.md`。UI 變更執行 `tests/browser/check.cjs`，使用隔離 API 與測試憑證；檢視 `artifacts/console/` 截圖。瀏覽器沒有持久化控制台憑證，保持每次 API 授權與房間範圍；不能用 UI 隱藏按鈕替代後端檢查。平面配置尚未由 Unity 載入，不能宣稱已整合遊戲擺設。

共用射擊／AI 核心唯一來源在 `clients/unity/Packages/com.vrcommand.simulation/Runtime/`；.NET Standard 2.1 建置入口是 `src/VrCommand.Simulation`。保持 C# 9 與無 Unity／.NET 10 相依，新增規則同時驗證 .NET 建置及模擬檢查。`tools/VrCommand.SimulationDemo` 一律使用 Simulation 來源。Unity 場景尚未接入此核心，詳細規則與未完成項目見 `docs/SIMULATION.md`。

Windows 執行中的本機 API 可能鎖住一般輸出 DLL；採 SIMULATION 文件的 `--artifacts-path` 隔離建置，不為測試任意停止現有服務。HTTP／瀏覽器檢查可用 `VR_COMMAND_API_DLL` 指定隔離 API，HTTP 另以 `VR_COMMAND_SIMULATION_DEMO_DLL` 指定同次建置的示範工具。

Quest 接入與建置見 `docs/QUEST3.md`。`scripts/check-unity-source.ps1` 只檢查 C# 9 語法，不能代替 Unity 編譯與 EditMode 測試。2026-10-29 Editor 已安裝至 F 槽，但實際 Prepare 因授權失敗退出 198；Android 模組尚待使用者接受 SDK／NDK 條款。不要重啟已完成的 Editor 安裝或自行宣稱授權已啟用。

頭盔只配置短效玩家票券；GameServer 憑證僅存桌面伺服器設定。所有 `data/`、`artifacts/`、Unity 快取與本機憑證均不得提交。生成場景、APK 或桌面程式須有實際成功結果，不能以來源碼存在宣稱完成。
