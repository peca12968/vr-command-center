# Unity managed API 接入檢查

`scripts/check-unity-sdk.py` 將遊戲執行端的 10 份 C#、5 份 NUnit 來源及其官方套件來源，以 .NET Standard 2.1／C# 9 編譯並綁定本機 Unity 6000.3.27f1 的真正 managed DLL。它補足只有語法檢查、或只綁定單一天氣元件的證據缺口；**不是整個 Unity 工程建置**。

## 執行

需要 Windows、Python 3.12+、.NET SDK，以及本機固定 Editor 的完整 managed DLL／BuiltInPackages。從專案根目錄執行：

```powershell
python scripts/check-unity-sdk.py
python scripts/check-unity-sdk.py --offline
# 可選：--profile android 或 --profile windows
# 可選：--editor-directory F:/Tools/UnityEditors/6000.3.27f1/Editor
```

首次下載官方固定套件（合計約 600 MB，Burst 約 470 MB），核對腳本固定的 registry tarball SHA-1，僅保留編譯所需的來源、asmdef、支援 DLL 及授權文件；套件原文不修改、不提交。快取每份檔案另記 SHA-256，重跑必須與 receipt 一致；新增、遺失或改動的編譯來源都會拒絕。`--offline` 不下載 SDK 套件；.NET 的 targeting packs／還原快取需先備妥。沒有完整 receipt 的快取不自動信任或覆寫。

產物均在 Git 忽略的 `artifacts/unity-sdk-check/`。`android.log`／`windows.log` 保留完整編譯診斷，`report.json` 保存嘗試時間、檢查器 SHA-256、Editor 版本、來源與引用 DLL 的 SHA-256、每個 assembly 的符號及退出碼；開始時清除舊成功標記，僅指定的分支全數通過才有 complete=true。不要把這些診斷 DLL 部署到 Unity 或頭盔；Unity 必須自行匯入、解析套件並產生正式組件。

## 來源與分支

| 元件 | 固定來源 |
|---|---|
| Unity engine、UI、NUnit DLL／UI 來源 | 已安裝 Editor 6000.3.27f1（672d562a42a7） |
| Netcode for GameObjects | 官方 2.7.0 |
| Input System | 官方 1.17.0 |
| Transport | 官方 2.6.0，依 NGO 相依 |
| Burst | 官方 1.8.24，依 Transport 相依 |
| Collections | 官方 2.4.3，依本機 SRP Core 17.3.0 相依 |
| Mathematics | 官方 1.3.2 |

兩個分支均使用 Editor 的 managed API 表面與明確列出的開發版符號。Android 分支啟用 UNITY_ANDROID／ENABLE_IL2CPP；Windows 分支啟用 UNITY_STANDALONE_WIN／ENABLE_MONO。這只是條件編譯，不執行 IL2CPP、Mono player 或 Android 原生工具。套件 asmdef 的來源邊界及此範圍的版本符號由腳本列出，沒有完整模擬 Unity CompilationPipeline 或 UPM 圖形。

每分支目前編譯 976 份 managed 來源（含 10 runtime／5 test 檔案），另透過 ProjectReference 編譯共用 Simulation。涵蓋 VenueBootstrap、NetworkAvatar、CombatAuthority、SceneAuthority、世界發送、連線設定、HUD、天氣及 codec 的型別綁定；NUnit 來源中的 18 個測試方法能編譯，**未執行**。沒有替身或自製 Unity／NGO stub。

## URP 與先行檢查

這次檢查發現原 manifest 的 URP 17.0.4 與所固定 Editor 隨附的 URP／SRP Core 17.3.0 不一致，已將 manifest 對齊 17.3.0。腳本先核對真正 Unity.exe 的 ProductVersion、直接指定的內建套件版本與 SDK pin；舊 17.0.4 fixture 會在編譯前拒絕。這是版本設定修正，尚無 UPM 解析或 Unity 內匯入成功證據。原 17.1 範本資產與其授權仍保留，資產升級須由真正 Editor 驗證。

此診斷圖不是 `Packages/packages-lock.json`；真正 UPM 首次成功解析後仍須核對並提交其鎖定檔。URP 渲染程式、XR／OpenXR 及 ProjectBuilder 的 Editor 來源沒有在此工具編譯，不能因檢查成功就認為這些接入成功。

## 結果與剩餘驗收

兩分支零錯誤；完整重建 Android 18 個、Windows 19 個警告，包含上游未使用欄位、隱藏成員，以及本工程 JsonUtility 反射填入的 receipt DTO 欄位 CS0649。警告保留在 log，未宣稱零警告。已驗證舊 URP pin 拒絕、快取來源刻意改動拒絕及原文恢復後離線成功。

最新真正 Prepare 結果仍為上一輪的授權退出 198；本輪沒有重複相同失敗建置。尚未執行 Unity 場景／資產匯入、ProjectBuilder、NGO／Collections／Burst IL postprocessor、Shader／音訊匯入、18 項 EditMode、Desktop／APK、網路雙玩家或頭盔測試。沒有以 managed 編譯結果替代任何一項。
