# Quest 3 接入原型與工具鏈 v0.8

使用者指定先用 Meta Quest 3；暫按 Android 獨立執行規劃。工程在 `clients/unity/`，後端仍獨立使用 .NET 10，不把後端 DLL 放進 Unity。

## 已有程式與驗證邊界

已有五區簡化軍事訓練場的生成器、玩家頭部／雙手物件、OpenXR 輸入、NGO 連線審核、房間固定出生席位，以及管理狀態／霧／日夜／閃光的同步程式。伺服器輪詢管理 API；姿態透過 NGO 傳送，不走 REST。玩家上傳目標頻率 20 Hz，伺服器檢查數值範圍並限制接受頻率；這不是定位校正或防作弊驗收。

**目前僅完成來源碼原型，沒有成功的 Unity 編譯、生成場景、EditMode 結果、桌面執行檔或 APK。** 2026-10-29 本機 Editor 已完整安裝，實際 Prepare 因無有效授權退出 198。8 份 C# 通過 C# 9 語法檢查；此檢查沒有綁定 Unity SDK。後端票券與設定產生流程已納入 128 項核心、229 項 HTTP 驗證。

沒有實機互見、Unity 武器／AI 或碰撞傷害接入、雨粒子／雷聲、MR 透視／錨點、遊戲內物件編輯、自由觀戰或 3D 回放。桌面鏡頭固定，不能作為需求 10 的完成證據。所有頻率與效能值仍須量測。

後續新增 v0.7 embedded package `com.vrcommand.simulation`，同一份 Runtime 已在 .NET Standard 2.1／C# 9 下建置與執行射擊／AI 模擬，詳見 `SIMULATION.md`。現有 Unity 場景仍未建立此世界，Runtime asmdef 與輸入／渲染／NGO 轉接尚待接入；不能將 .NET 核心的通過結果當作 Unity 工程成功編譯。

## 固定工具鏈

| 項目 | 版本／位置 |
|---|---|
| Unity Editor | 6000.3.27f1，revision `672d562a42a7` |
| 本機 Editor | `F:\Tools\UnityEditors\6000.3.27f1\Editor\Unity.exe` |
| Unity CLI | 1.0.0-beta.14，已安裝 |
| OpenXR / XR Management | 1.19.0 / 4.6.1 |
| NGO / Transport | 2.7.0 / 由 NGO 相依解析（2.6.0） |
| Input System / URP | 1.17.0 / 17.0.4 |
| Test Framework / UGUI | 1.6.0 / 2.0.0 |
| Quest 建置設定 | IL2CPP、ARM64、Vulkan、min API 32、target API 35，Development APK |

版本由官方 Unity release feed、套件 metadata 與 URP Blank 17.1.0 模板選定；不是最新版套件一律升級。模板 ProjectSettings／URP 設定附原始授權於 `clients/unity/ThirdPartyNotices/`。Unity 套件鎖定檔尚待第一次成功套件解析產生並提交。

使用者已明確同意 SDK／NDK 條款；Android Build Support 與 OpenJDK 已由 CLI 安裝，SDK／NDK 目錄修復及實際原生編譯結果見下節，不再等待條款確認。

使用者另回覆已登入／啟用，但工具端驗證仍為 CLI `loggedIn: false`、`unity license list` 空陣列，實際 Prepare 再次退出 198。已啟動一次瀏覽器登入流程，觀察到 Chrome 停在 Unity 登入頁；CLI 未收到成功回呼並回報登入逾時。後續請在本機重新執行 `unity auth login`，等待命令成功，再以 `unity auth status --format json` 及 `unity license list --format json` 核對適用帳戶／授權。不要把密碼、token 或序號貼入對話；沒有自行購買或選擇 Personal 資格。

## Android 工具實測

安裝命令使用已同意的 `--accept-eula`。CLI 結束時回報 Android、OpenJDK、SDK parent、platform 34 成功，其餘八個子模組失敗；原始登錄並非全部成功。實際解壓檔案已存在，NDK、CMake、Build Tools、command-line tools 留在未整理的 archive 根目錄。

依官方 release metadata 的 extractedPathRename，`scripts/repair-android-layout.ps1` 已先用 `-WhatIf` 核對，再以限定在此 Editor 的絕對路徑移動新解壓元件；不合併／覆寫既有目標或刪除資料。整理後再次 WhatIf 沒有待移動項目。

| 元件 | 已實際驗證 |
|---|---|
| NDK | r27c／27.2.12479018，clang 18.0.3 可執行 |
| OpenJDK | Temurin 17.0.18+8 可執行 |
| CMake | 3.22.1 可執行，搭配內建 Ninja 完成組態及建置 |
| SDK | SDK Manager 辨識 Build Tools 36.0.0、Platform Tools 37.0.1、platform 34／35／36 |
| 工具與條款 | command-line tools 16.0 可執行；使用者已同意的 android-sdk-license 已由官方 SDK Manager 登錄 |
| 原生編譯 | C++17、Android log／STL、API 32、arm64-v8a 的共享庫編譯／連結通過，ELF header 驗證為 64-bit AArch64 |

可重驗 `.\scripts\check-android-toolchain.ps1`，輸出在忽略的 `artifacts/android-toolchain-check/`。這證明主要原生工具可協同工作；CLI 八個子模組的失敗登錄仍保留，Unity Editor 偵測及 APK 建置還須實際驗證。沒有把原生 `.so` 當成 APK 或 Quest 執行結果。

來源：[Unity CLI 使用方式](https://docs.unity.com/en-us/unity-cli/use-unity-cli)、[Meta Unity requirements](https://developers.meta.com/vr/documentation/unity/unity-development-requirements/)、[Unity 套件庫](https://packages.unity.com/)、[Android SDK 條款](https://developer.android.com/studio/terms)。

## 待授權就緒後執行的建置

在儲存庫根目錄執行：

```powershell
.\scripts\build-unity.ps1 -Target Prepare
.\scripts\build-unity.ps1 -Target Tests
.\scripts\build-unity.ps1 -Target Desktop
.\scripts\build-unity.ps1 -Target Quest
```

`Prepare` 建立 `Assets/VrCommand/Generated/Arena.unity`、玩家 prefab 與 XR 設定；同一路徑會重建，不應直接在生成場景加入手工內容。Tests 執行 EditMode 並要求 XML 中測試通過。Desktop 輸出 `artifacts/desktop/VrCommand.exe`，Quest 輸出 `artifacts/quest/VrCommand.apk`。腳本檢查退出碼及本次輸出時間，日誌與結果位於 `artifacts/unity-logs/`。成功編譯後仍須執行下列雙玩家檢查。

無授權時可先執行 `.\scripts\check-unity-source.ps1`，但只能回報語法檢查結果。不得把其輸出視為可執行的 Unity 工程。

## 區域網路原型操作

以下步驟尚未完成 Unity 執行與頭盔驗證。管理 API 預設留在伺服器本機 `127.0.0.1:5080`；頭盔只連遊戲伺服器的 UDP 7777。同一場館網路與防火牆須允許該連線；此原型沒有遠端中繼或網際網路部署。

1. 用 `.\scripts\start-local.ps1` 啟動 API，保留其視窗。
2. 建置桌面與 Quest 後，再產生連線資料，避免票券在建置期間到期：

   ```powershell
   python scripts/prepare-vr-session.py --server-address 192.168.1.100 --room 1 --players 2
   ```

   把範例 IP 換成頭盔能連到的桌面 LAN IP。助手只在空閒房間新建自己的 Independent 場次，保留 `Preparing`，輸出場次 ID 與 `data/vr-connections/<場次ID>/` 路徑。`server.json` 含 GameServer 憑證，只留在桌面；`player-1.json`／`player-2.json` 各含自己的五分鐘票券，不含控制台憑證。
3. 啟動桌面伺服器（請替換 GUID 路徑）：

   ```powershell
   & .\artifacts\desktop\VrCommand.exe --vr-config F:\Projects\vr-command-center\data\vr-connections\<場次ID>\server.json
   ```

   同一台桌面可用另一份玩家設定啟動 Client，WASD／按住滑鼠右鍵僅供桌面預覽；這不是 VR 移動功能驗收。
4. Quest 3 須開啟開發者模式，USB 連接並在頭盔內授權 ADB。部署每台不同玩家設定：

   ```powershell
   .\scripts\deploy-quest.ps1 -ClientConfig .\data\vr-connections\<場次ID>\player-1.json
   ```

   多台裝置須用 `-Serial` 指定；腳本核對裝置型號、只接受玩家欄位、安裝本專案 APK 並複製設定後啟動。此腳本尚未實機執行。
5. 兩名玩家應互見頭手；用既有 `/commands` 發送 Begin、Pause、Resume、SetEnvironment，核對所有裝置階段及視覺狀態一致。管理 API 暫時不可用時場景狀態轉 Paused；目前並無射擊可停用。
6. 測試後以 End 結束自己建立的場次，保留歷史並釋放房間。票券過期時由有權控制台對同一玩家重新配發；不用刪除其他場次。已結束場次不能再配發或驗證。

## 連線與仍待實作事項

一個桌面伺服器程序綁定一個管理場次；五房 Independent 使用各自程序／UDP 埠，全連線則使用一份 Linked 場次與共同伺服器。助手目前只產生單房 Independent 設定；Linked 名冊與票券可透過 API 建立。場景用房間原點平移安排五區，尚無實體場館對位或共用錨點。

入場時伺服器用自己的 GameServer 憑證向 API 驗證票券、目前名冊及固定席位，拒絕同一玩家的同時重複連線。票券不是一次性使用；斷線後在未過期及仍在名冊的條件下可再驗證。尚無完整重連、裝置就緒回報、已連線玩家移除時即時踢出、場次結束時主動斷線，以及伺服器崩潰恢復的整合驗證。

一般 NGO 連線尚未加入應用層加密或設備證明，票券應視為短效憑證；目前用途限受控開發 LAN。正式部署還須完成傳輸保護及權限分場強化。先以兩台 Quest 3 取得實際幀率／頻寬／延遲與拒絕案例，再推進 5／10／25 人。
