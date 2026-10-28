# 開發指引

開發根目錄為 `F:\Projects\vr-command-center`；以此庫的實際 Git 狀態與執行結果為準。

開始接續工作時讀取 `docs/PROGRESS.md`、`docs/ROADMAP.md`、`docs/REQUIREMENTS.md`。使用者的完整目標為 11 項 VR/MR 遊戲需求及 VIVE XR／Quest 3 相容性，不能以管理原型或模擬測試通過替代完整交付。

後端為 .NET 10；Unity 工程尚未建立。不要把後端組件宣稱為 Unity 相容。未知硬體協議使用模擬器，實機整合待廠商文件及設備。

`/api` 端點使用伺服器配發的主控／房間控制台身分。實作新路由時必須傳遞認證身分並檢查操作範圍，不能依賴核心的預設 Internal 身分處理 HTTP 請求。測試用獨立的暫存憑證；不要讀出或提交 `data/operator-keys.local.json`。

後端變更應執行：

```text
dotnet build VrCommand.slnx --configuration Release
dotnet run --project tests/VrCommand.Checks --configuration Release --no-build
python scripts/smoke_api.py
```

`VrCommand.Checks` 是可執行的規則檢查程式，不能只執行 `dotnet test` 就宣稱已完成檢查。依功能實際影響補充有意義的測試，並將驗證結果、限制與下一步更新至 `docs/PROGRESS.md`。

遊戲事件、即時狀態、統計與回放應共享版本化契約；頭盔姿態與逐幀模擬不使用管理 REST API。實機相容、MR 校正、25 台頭盔效能與硬體控制須分別保留驗收證據。
