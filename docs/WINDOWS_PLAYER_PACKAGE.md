# Windows 可攜玩家包

2026-11-10 `VRCommand-Player-0.49.1-launcher1.7.0-win-x64.zip` 為 84,765,133 bytes，SHA-256 `fa10a1a931d8c43e2b8c3531ea14aad57456299307a5be14e4969c6301c0af74`。解壓核對 330 個清單檔案及 39 項實際啟動器檢查。 [全館封存操作](EXTERNAL_CLIENTS.md#核對全館共用的發行報告)

2026-11-10 `VRCommand-Player-0.49.1-launcher1.6.0-final-win-x64.zip` 為 84,765,095 bytes，SHA-256 `8450efd4603eccf3c442c82cd1e6f0156b1169206a09bdcfc81a8b922541d626`。解壓核對 330 個清單檔案及 39 項實際啟動器檢查。 [依場館發行報告核對玩家包](#依場館發行報告核對玩家包)

2026-11-10 `VRCommand-Player-0.49.1-launcher1.5.0-final-win-x64.zip` 為 84,765,041 bytes，SHA-256 `3629cda8fab5513116498527180f4fdbd9b9b55b1d46efeae6308716a6149ada`。解壓核對 330 個清單檔案及 29 項實際啟動器檢查。選用 `--link-metrics` 時，啟動器將原量測與玩家日誌的雜湊寫入終止報告。 [操作方式](EXTERNAL_CLIENTS.md#將-windows-連線量測納入五房封存)

2026-11-10 `VRCommand-Player-0.49.1-launcher1.4.0-win-x64.zip` 為 84,763,776 bytes，SHA-256 `64e3e46861bd435b0f5b4b96e0bc6ee7b0620a81370b7e660ce096ddc5e31bd5`。解壓核對 330 個清單檔案及 22 項啟動器檢查。遊戲沿用 Windows 0.49.1，啟動器新增等待最終戰績及中斷提示。 [玩家狀態](PLAYER_CONNECTION_STATUS.md)

2026-11-10 `windows-player-0.49.0-launcher-1.3.zip` 為 84,763,077 bytes，SHA-256 `20144d9ec2184923e4b4d165db3a857b9ed81af63377740722e054500426c707`。解壓核對 330 個清單檔案，23 項實際啟動器檢查通過，含缺少 OpenXR 執行環境時於入場前退出。 [Windows OpenXR 啟動](#windows-openxr-啟動)

2026-11-09 `windows-player-0.48.1-launcher-1.2.zip` 為 83,445,374 bytes，SHA-256 `ba90488aa06ed3b7154f71600b58bb974968a92db99a962571967005afd95f8c`。解壓核對 328 個清單檔案，19 項 Windows 啟動器檢查通過。遊戲端 0.48.1 使用同源的 Windows 與 Quest 建置。 [版本相容性](EXTERNAL_CLIENTS.md#遊戲版本相容性)

2026-11-09 `windows-player-0.48.0-launcher-1.2.zip` 為 83,444,831 bytes，SHA-256 `e02e98a60c14de1993715b888c0dd6cbf21f01393fe43f5195179bb2429914ce`。解壓後核對 328 個清單檔案及 19 項封裝檢查。啟動器顯示房間、席位和到期倒數，遊戲執行環境沿用 0.48.0。 [連線檔席位與效期](PLAYER_CONFIG_REVIEW.md#連線檔席位與效期)

2026-11-09 `windows-player-0.48.0.zip` 為 83,443,442 bytes，SHA-256 `7cf02151f7c662130172cc4be5a42fbbf6b73b74394200bff9b45b1994ae25d2`。解壓後核對 328 個清單檔案，玩家啟動器通過 19 項檢查。 [版本相容性](EXTERNAL_CLIENTS.md#遊戲版本相容性)

2026-11-09 `windows-player-0.47.1.zip` 為 83,442,173 bytes，SHA-256 `ac0c39822bb819466c39519e5c0d14b9bb59e6f9e09268f007768edbc411c843`。解壓後核對 328 個清單檔案，啟動器通過 19 項檢查。 [版本相容性](EXTERNAL_CLIENTS.md#遊戲版本相容性)

2026-11-06 新版 `windows-player-0.41.2.zip` 為 82,653,510 bytes，SHA256 `95c2a63a9d5d48b844af0bff47da263e7fbb46edf6d5d1c1e210589fcbaab897`。啟動器沿用 1.1，實際解壓後通過 19 項檢查。與遊戲伺服器包 0.41.2 的 Unity 建置來源一致。 [伺服器來源診斷](WINDOWS_SERVER_PACKAGE.md#跨機來源診斷)

2026-11-06 採用 `windows-player-0.41.1-v2.zip`，82,652,952 bytes，SHA256 `925a8ac16451ae2c423da1b0cb9c9867af17b8fb5b08ab5824f7ea1b1bca8402`。啟動器 1.1 支援貼上完整路徑與「載入／更新」。已驗證檔案變更時拒絕啟動，重新載入後成功加入同機雙玩家場次。 [玩家連線檔流程](PLAYER_CONFIG_REVIEW.md)

2026-11-02 舊包 `windows-player-0.41.1.zip`，**82,651,927 bytes／SHA256 `dcc46c80c68d0a2861957c7d534b1abacd15964fb22f310ecdd1e60dddf7d2df`**，311 manifest／ZIP312，原launcher來源a65846da...；19項實際包檢查通過。Unity0.41.1／code52／NGO29、242真正Editor與同源4ebd雙平台／原ID保持。900秒兩模式18／51601／50原結果6CSV與普通入場8／354見[DESKTOP_ENDURANCE](DESKTOP_ENDURANCE.md)；長場只在明確Development batch旗標啟用生成輸入。APK60361942／SHA766d8018...、ARM64／min32／target35／v2 debug已驗，未裝頭盔。伺服器新包106與WinForms流程另見[WINDOWS_SERVER_PACKAGE](WINDOWS_SERVER_PACKAGE.md)；不是玩家完整GUI、25真人／LAN或頭盔驗收。以下較舊「最新」是當時歷史，原ZIP保持。

2026-11-02 最新`windows-player-0.40.0.zip`為[原生多端動態驗證](DESKTOP_EXERCISE.md)的同源runtime，**82,651,129 bytes／SHA256 `24aef191b5fc608430a5f131ffd34aabf2ec0b4938fefd3f2c8461c958cc50e2`**、311 manifest／ZIP312。231真正Editor、6098b485...雙平台、原ID及新19項包檢查成功。明確開發batch Client模式才能產生測試輸入，普通玩家流程未自動啟用；25端自動化、普通入場8項及server包106範圍見PROGRESS。不是25真人／跨機、完整GUI或頭盔驗收；原0.39與更早包保持。

2026-11-02 最新`windows-player-0.39.0.zip`加入[電腦端蹲姿](DESKTOP_CROUCH.md)，82,647,558 bytes／SHA `09f4ac14a9497329080d018dd634ebfdee13cabb0b7e0c7d2ed8b077173e47cc`、311 runtime檔及原launcher，新C展開19項核對／拒絕成功。224真正Editor、同源雙平台與unpacked原生C／W／視窗實測見PROGRESS；未重跑完整封裝GUI／跨機或頭盔驗收。舊0.38與其他ZIP保持，以下為歷史。

最新`windows-player-0.38.0.zip`使用[AI可見目標](AI_VISIBLE_TARGETS.md)的同源Windows建置，82,646,224 bytes／SHA1f4a27d8...、311 runtime檔及原launcher，新C展開19項核對成功。完整receipt／APK及原生三人／五房證據見PROGRESS，仍非完整GUI／跨機或頭盔驗收。

2026-11-01 主包`windows-player-0.37.2-final.zip`為[非格點端點修正](AI_NAVIGATION_ANCHORS.md)，7d3e1a92...／311 runtime與原launcher；82,645,932 bytes／SHA `25dd1ee56234cd7da3da1f9671877b6c8967a41f03d71f903f3008558425d5c4`。新C展開19項真正核對／拒絕成功，非完整GUI／跨機。無final的0.37.2 ZIP為2c96...初候選、未包含最終逐tick觀察來源，原件保持。199真正Editor、雙平台及原生／CI範圍見PROGRESS，不能僅依檔名或相同版本號判定同源。

2026-11-01 `windows-player-0.37.1.zip`為[敵軍繞行旋轉掩體修正](AI_NAVIGATION.md)，69d247a9...／311 runtime檔與原launcher；82,642,694 bytes／SHA256 `cba3a25ba590c21f0b38b152042242b373ea656dce4c1ff434a742490f3b841f`。新C展開19項真正launcher核對／拒絕成功，非完整GUI／跨機；原0.37.0與0.36.1 ZIP保留。189真正Editor與同源Windows／Quest、原生及CI範圍見PROGRESS。

2026-11-01 新包`windows-20261101-120352-b2b5c1c3.zip`為Unity0.37.0／09eed852...的[第一人稱軍服手臂](DESKTOP_FIRST_PERSON.md)，311 runtime檔／manifest／原launcher；82,642,471 bytes，SHA256 `08aa93385e4e2b2688714fee56ce6d9dfe6592574d8e7e844e15020e815ae030`。新C展開目錄19項真正launcher核對／拒絕成功；未當完整封裝GUI或跨機連線。舊0.36.1／0.36.0 ZIP與建置前321檔archive保持，雙平台建置／原生功能範圍見PROGRESS。以下版本為歷史。

2026-11-01 最新`windows-player-0.36.1.zip`（e0594513...）修正[Ended結果尾界](DEBRIEF_BOUNDARY.md)，311 runtime檔＋manifest／原launcher，新C解壓19項真正核對／拒絕成功。179 Editor與同源Windows／Quest建置、原生結果與長場範圍見PROGRESS；沒有新完整GUI／封裝雙PC瀏覽器或頭盔證據。原0.36 ZIP及Windows／Quest／logs另存history，精確hash保持。

2026-11-01 上一版`windows-player-0.36.0.zip`（7194dc98...）原311 runtime檔＋manifest／相同launcher，C新解壓19項核對／拒絕成功。一般原生8項400幀／SSD負載8項354幀與故障恢復8項，是本輪unpacked玩家回歸，未重跑完整GUI／封裝雙PC瀏覽器。0.35兩包及舊history保留；精確hash與限制見PROGRESS。

2026-11-01 最後來源包為`windows-player-0.35.0-final.zip`（d30cc34c...），原311 runtime檔＋manifest／launcher source保持，真正新C解壓19項核對／拒絕通過；本輪一般原生8項363幀與SSD負載8項355幀是unpacked玩家回歸，未重跑完整GUI／封裝雙PC瀏覽器流程。非final檔名的0.35 ZIP屬f93候選，兩者皆保留，精確SHA／範圍見PROGRESS。

新版啟動器加入[玩家入場狀態](PLAYER_CONNECTION_STATUS.md)：區分程式啟動、遊戲回報入場／拒絕／中斷、30秒未確認與最終戰績；Unity0.33／code40來源與原成功建置保持。新版ZIP、真正類別／原生背景驗證及GUI／跨機限制見PROGRESS。

本輪另產生Unity0.33／code40同源Windows玩家包，啟動器邏輯不變；ZIP與解壓核對及新版DLL的一般原生回歸見PROGRESS。一般雙擊不開長診斷，診斷必須明確CLI選用；0.32舊包及其原始驗證保持，沒有將未完成的GUI安全性提示驗收改為成功。

玩家包 v1 使用現有 Unity0.32.0／NGO29 的真正 Windows 建置，API／UI0.30不變。控制人員可交付一份 ZIP，玩家完整解壓後開啟 `Launch-Player.exe`、選擇自己的控制台下載連線檔，再按「開始遊戲」。玩家電腦不需要 Unity Editor、Python或.NET 10 SDK；啟動器使用 Windows 的.NET Framework 4.8，遊戲仍使用原 Unity runtime。不同電腦的相容性仍須實測。

## 建立與交付

先成功建置目前來源的 Desktop，再執行：

```powershell
python scripts/package-windows-player.py
# 可指定新的輸出檔，不會覆蓋既有包：
python scripts/package-windows-player.py --output artifacts/player-packages/venue-player.zip
```

封裝器核對真正 StandaloneWindows64 receipt、原輸出路徑及目前 Unity source fingerprint，複製原 runtime 到自己的暫存目錄，以系統.NET Framework compiler編譯獨立啟動器，產出ZIP、外部receipt及內部player-package.json。不修改Unity建置、Scene／prefab ID、source規則或資料格式，也不需要重新Prepare。

runtime只收VrCommand.exe／UnityPlayer／CrashHandler／WinPix及D3D12、MonoBleedingEdge、VrCommand_Data；原build-receipt保留。DoNotShip debug資料夾不納入，root的其他設定檔不收取；runtime樹內出現未知JSON、金鑰、journal、DB或log則拒絕封裝。原Transport／模板／字型授權及Transport來源通知一併保留；不讀取既有任務資料或控制台憑證。

玩家包可共用，但每位玩家的短效連線檔必須個別交付，不要加入共用ZIP。控制台操作與server-only模式見[EXTERNAL_CLIENTS](EXTERNAL_CLIENTS.md)。連線檔仍只有role／address／port／joinTicket；不把主控或GameServer key放在玩家端。

## 玩家操作

1. 將ZIP完整解壓到本機資料夾，保留VrCommand_Data等所有檔案。不要直接在壓縮檔中執行，也不要只複製EXE。
2. 開啟Launch-Player.exe，按「選擇連線檔…」，選擇控制人員提供的JSON。啟動器只顯示檔名與IPv4／port，不顯示票券。
3. 按「開始遊戲」。啟動器核對玩家包中列出的全部檔案雜湊，再用獨立程序開啟遊戲；同一啟動器不重複開啟同一玩家。
4. 用WASD移動、Ctrl按住或C切換蹲姿、方向鍵或右鍵拖曳瞄準、Space／左鍵射擊、R換彈、B任務簡報。完整操作見[DESKTOP](DESKTOP.md)。結束時等待最終戰績。

關閉啟動器不會終止已開啟的遊戲或替操作員End。遊戲結束後啟動器可再次使用，但仍須有效短票券；重新配票後，將新檔存回相同路徑可使用遊戲原Reconnect流程。連線檔的角色／四欄結構、IPv4及port先離線檢查；票券簽章、效期、admission、room／seat仍由遊戲伺服器驗證，格式正確不代表可入場。

### Windows OpenXR 啟動

五房場館的主控可先用原 ZIP 和電腦對照表匯出各 Windows 席位的連線檔。 [分發連線檔](EXTERNAL_CLIENTS.md#依電腦分發-windows-vr-連線檔)

Windows 玩家包 0.49.0 的圖形玩家端可以選用 OpenXR。先讓相容的頭盔連上 Windows OpenXR 執行環境，再由解壓後的玩家包資料夾執行。使用主控簽發的四欄 VR 玩家連線檔。

```powershell
.\Launch-Player.exe --config 'C:\Venue\player.json' --launch --openxr --wait
```

啟動器使用 Direct3D 11。OpenXR 顯示和輸入子系統開始運作後，遊戲才送出入場請求。OpenXR 無法啟動時，玩家程序退出碼為 2。可加上 `--log` 和 `--status-report` 指定包外兩個新檔，檢查 `OpenXRUnavailable`。平常雙擊啟動器仍使用桌面模式。

Windows 建置啟用 Touch 與 Unity 的 HTC Vive Controller 兩個 OpenXR 互動設定。Touch 沿用右扳機射擊、A 換彈、B 重讀票券，左手 X／Y 翻頁及關閉簡報。HTC Vive Controller 使用右扳機射擊、右握把換彈、右 Menu 重讀票券，左觸控板按下翻頁、左 Menu 關閉、左握把查看字型授權。實際控制器由 Windows OpenXR 執行環境回報，VIVE XR 的確切型號及相符設定仍待頭盔到場驗收。MR 透視與房間對位沿用 Quest 3 Android 路徑。 [Unity XR 手動啟動](https://docs.unity3d.com/Packages/com.unity.xr.management@4.6/manual/EndUser.html#load-xr-plug-ins) · [HTC Vive 控制器設定](https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.19/manual/features/htcvivecontrollerprofile.html)

#### 依場館發行報告核對玩家包

在啟動器 1.6 加上 `--release-report`，選用主控為本次交付產生的原始 `venue-release.json`。先以 `--verify` 做離線檢查，也可在桌面或 OpenXR 的直接啟動命令加上同一選項，讓每次啟動都重新核對。

```powershell
& .\Launch-Player.exe --verify --release-report 'C:\Delivery\venue-release.json' --report 'C:\Private\package-check.json'
& .\Launch-Player.exe --config 'C:\Private\my-seat.json' --launch --openxr --wait `
  --release-report 'C:\Delivery\venue-release.json' --log 'C:\Private\player.log' --report 'C:\Private\launch-report.json'
```

啟動器先以發行報告比對原清單的 SHA-256，再按該清單逐檔核對本機玩家包。清單屬於不同發行批次、檔案被更換或資料夾內有清單外檔案時，會以退出碼 1 停在啟動前。連線檔、發行報告及本次程序報告均放在解壓目錄外。成功時，程序報告保留核對過的 `playerManifestSha256`，可搭配原入場日誌留存。選用此模式須使用含 Windows 清單雜湊的新報告。雜湊依賴主控交付的原報告，發行者身分與實體頭盔由現場核對。 [產生場館發行報告](EXTERNAL_CLIENTS.md#發送前離線核對交付套件)

啟動器 1.7 搭配 `--wait`、`--log`、`--report` 時，退出報告也會保存原玩家日誌的 SHA-256。若日誌缺失、為空、無法讀取或超過 16 MiB，欄位為空值。封存驗收可直接配對原日誌及退出報告。 [全館封存操作](EXTERNAL_CLIENTS.md#核對全館共用的發行報告)

#### 本機追蹤整合驗證

測試使用 Unity OpenXR 套件附的 Windows Mock Runtime，另外由測試 DLL 提供固定頭手座標。只有測試玩家程序的 `XR_RUNTIME_JSON` 會指向測試環境。遊戲由解壓玩家包的啟動器執行，用主控簽發的原票券入場，走正常追蹤、回放和戰績流程。另一席使用桌面玩家作對照。這項驗證使用模擬裝置。 [Khronos 載入器規格](https://registry.khronos.org/OpenXR/specs/1.1/loader.html#overriding-the-default-runtime-usage)

任務執行中，測試 DLL 保留控制器最後座標並撤下追蹤旗標。測試核對受影響的席位維持「姿態待確認」、桌面席持續就緒。恢復時使用移動 0.2 公尺的新頭手座標，核對原程序、連線、票券、房號及席位。封存後逐格比對追蹤、失效及恢復。 [OpenXR 空間追蹤規格](https://registry.khronos.org/OpenXR/specs/1.1/man/html/xrLocateSpace.html)

同一場以模擬執行環境的 Conformance Automation 在失去追蹤時扣住右扳機，並維持到恢復。確認沒有消耗彈藥後，先放開，再短扣 100 毫秒。原伺服器只接受一次射擊，回放、玩家戰績及 CSV 的彈藥數均相符。 [OpenXR 測試輸入擴充](https://registry.khronos.org/OpenXR/specs/1.1/man/html/XR_EXT_conformance_automation.html)

先用 Unity Editor 還原專案套件，再取 Khronos OpenXR SDK 1.1.53 的 `openxr.h`、`openxr_platform_defines.h` 和 `openxr_loader_negotiation.h` 放在同一標頭目錄。從 x64 Visual Studio 開發終端在專案根目錄編譯測試 DLL，輸出放在 `artifacts`。 [Khronos SDK 標頭](https://github.com/KhronosGroup/OpenXR-SDK/tree/release-1.1.53/include/openxr)

```powershell
cl /nologo /std:c11 /O2 /LD /W4 /WX /wd4191 /I"C:\XR\include\openxr" `
    /Fo"artifacts\openxr-mock-pose.obj" tests\fixtures\openxr-mock-pose.c `
    /link /OUT:artifacts\openxr-mock-pose.dll
python scripts/check-server-package.py '<解壓遊戲伺服器包>' `
    --control-package '<解壓管理包>' --player-package '<解壓玩家包>' `
    --runtime-root '<新隔離執行目錄>' --openxr-mock-only `
    --openxr-mock-pose-dll artifacts/openxr-mock-pose.dll
```

可加上 `--observe-closure-ui`，用專案的 Playwright Chromium 驗證房卡顯示與清除待確認席位，核對兩席彈藥數，並由實際控制台結束和核對封存。

加上 `--check-openxr-reconnect` 可用支援 Vive 右手 Menu 的測試 DLL 驗證同機重連。測試只關閉 OpenXR 席的 UDP 轉送，並在原玩家程序內重新讀取同一入場的新票券。 [重連驗證](QUEST_RECONNECT.md#windows-openxr-重連複驗)

可再加上 `--hardware-simulator-package '<解壓目錄>/VRCommand-HardwareSimulator'`，用 .NET 10 執行硬體模擬包，為兩席分別綁定虛擬裝置。測試確認追蹤失效、恢復後扣住及放開時，兩個裝置都沒有收到回饋。重新扣下扳機後，TCP 模擬裝置只為射擊席確認一筆 `ShotFired` 後座力訊號，並與主控接受的原報告及封存射擊逐筆核對。驗證範圍是軟體路由與模擬確認，實際裝置輸出另行驗收。 [硬體模擬器](HARDWARE_SIMULATOR.md)

硬體模擬器 0.2.3 搭配管理包 0.31.61 時，測試從原始座位及設備清單呼叫 `--bind-room`。產出的綁定逐欄比對兩席目前的原入場，再用該設定啟動模擬閘道。 [座位綁定](HARDWARE.md#依現行名冊建立座位綁定)

127.*僅供同機；不同電腦必須能連到公告的伺服器IPv4及UDP埠。此工具不修改安全性／防火牆、不安裝驅動，也不提供NAT／中繼或網路可達性探測。若Windows出現安全性提示，由使用者自行決定。包內沒有伺服器啟動器、管理API或控制台金鑰。

## 完整性與診斷

player-package.json記錄原Unity receipt、launcher source SHA及每檔長度／SHA256。可在開發電腦另行核對解壓結果：

```powershell
python scripts/package-windows-player.py --verify '<解壓目錄>/VRCommand-Player'
python scripts/check-player-package.py '<解壓目錄>/VRCommand-Player'
```

這份清單不是數位簽章、可信發行者或惡意程式檢測；不能以清單證明任意來源的ZIP可信。離線核對不證明網路、實機、MR或25台相容性。

啟動器另有選用診斷：`--verify`只核對包，`--config <檔案>`預選連線檔，`--launch`直接啟動，`--headless`及`--wait`僅搭配直接啟動。`--log <全新絕對路徑>`指定遊戲原生日誌，`--report <全新絕對路徑>`保存啟動／退出狀態及自有子程序PID；兩者必須位於玩家包外，不覆蓋既有檔或輸入。一般雙擊不產生診斷報告，新版GUI將Unity原生日誌放入自己的LocalAppData PlayerRuns目錄供入場狀態使用；原CLI未指定log時仍沿用Unity預設。選用`--status-report`條件及有界範圍見PLAYER_CONNECTION_STATUS。

真正API下載、兩個獨立原生玩家與封存的驗證入口：

```powershell
node tests/browser/check-external-native.cjs '<本次隔離ready.json>' '<解壓目錄>/VRCommand-Player'
# 第一位使用真正啟動器按鈕，第二位背景啟動；需要人工／允許的UI操作：
node tests/browser/check-external-native.cjs '<本次隔離ready.json>' '<解壓目錄>/VRCommand-Player' --package-interactive
```

檢查器只接受自己新開的external／Simulation／loopback fixture。workflow結果與程序cleanup分開保存，只有cleanup也成功才寫complete的checks.json；實際退出可能是測試主動關閉的signal，不能只以exitCode非空判定。各輪成功、未完成原因與Windows安全性提示限制見[PROGRESS](PROGRESS.md)。原生GUI與背景流程、同機與跨機、模擬與頭盔證據須分開陳述。
