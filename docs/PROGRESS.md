# 開發進度

## 2026-11-13 Windows 玩家包 1.15 內建 OpenXR 預檢

- 場館可從解壓後的玩家包執行 `Launch-Player.exe --check-openxr --report`，檢查 64 位元登錄或目前程序所選的 OpenXR 清單及 x64 DLL 標頭。報告只包含來源及檔案檢查狀態。發行核對通過，與同源 1.14.1 包比對有 329 個清單檔案雜湊一致。 [操作方式與下載](WINDOWS_PLAYER_PACKAGE.md#windows-openxr-啟動)
- 解壓玩家包通過 45 項檢查，包含 21 項 WinForms 處理程式檢查及 14 個預檢執行案例。Unity Mock Runtime 的雙玩家同機驗證通過 80 項，回放 105 格。額外的 Vive Menu 重連案例起初使用缺少重連確認功能的舊測試 DLL，等待確認逾時。以目前測試原始碼重編 DLL 後，87 項通過，含 UDP 中斷、同一玩家程序重入及 458 格雙封存回放。三次執行皆已清理，初次逾時紀錄保留。 [驗證摘要](../artifacts/windows-player-1.15-validation.json)
- 功能提交 `03496fb` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3 與 VIVE 實機、跨機 25 人、MR 場地與廠商硬體仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43403573918)

## 2026-11-13 Windows OpenXR 執行環境預檢

- `check-windows-openxr.ps1` 唯讀檢查 64 位元登錄中的 `ActiveRuntime` 或目前程序的 `XR_RUNTIME_JSON`，辨識缺少的清單、無法定位的 DLL 及錯誤架構。本機登錄設定與 Unity Mock Runtime 都通過檔案預檢，缺失的環境變數指定清單回報 `manifest-missing`。登錄值及模擬執行環境檔案經前後比對一致。三項 Windows 測試通過。本機 Windows PowerShell 的執行原則拒絕載入腳本，驗證以 PowerShell 7 完成。 [操作方式](WINDOWS_PLAYER_PACKAGE.md#windows-openxr-啟動)
- 解壓玩家包通過 43 項檢查，缺少 OpenXR 執行環境時在入場前退出。Windows 三包另通過 80 項模擬 OpenXR 整合，核對頭手追蹤、中斷與同一連線恢復，兩位同機玩家的戰績與 107 格雙封存回放。清理後 C／F 的 39 個非資料庫檔案雜湊相符。 [驗證摘要](../artifacts/windows-openxr-preflight-validation.json)
- `cdb601f` 已推送，GitHub Actions 因帳務或支出上限未啟動。VIVE 型號、實機控制器與追蹤、Quest 實機、跨機 25 人、MR 場地及廠商硬體待驗。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43402537901)

## 2026-11-13 Quest 單席安裝核對原發行 APK

- `deploy-quest.ps1` 的單席流程可搭配 `-ReleaseReport` 與 `-ApkPath`。`-CheckOnly` 可在無頭盔時核對本機 APK 與原連線檔。正式安裝以核對過的暫存副本執行，讀回裝置 APK 雜湊後才傳送及啟用玩家設定。 [操作方式](QUEST3.md#powershell-部署)
- 實際 0.50.7 APK 通過第 4 房第 2 席的本機預檢，混入 0.50.6 在 ADB 呼叫前被拒絕。以同一份原 APK 搭配模擬 ADB，確認裝置雜湊不符時未傳送玩家設定，雜湊相符時才傳送設定並送出啟動。兩次暫存檔均清理，3 個原檔雜湊相符。 [驗證摘要](../artifacts/quest-single-seat-release-validation.json)
- 55 項 Quest 部署回歸及追加的 1 項 ZIP 單席預檢通過，另通過 8 項發行核對。功能 `92b71eb` 和測試 `47271c2` 已推送，兩次 GitHub Actions 因帳務或支出上限未啟動。Quest 實機安裝、VIVE、跨機、MR 場地及廠商硬體待驗。 [功能 CI](https://github.com/peca12968/vr-command-center/actions/runs/43401667855) · [測試 CI](https://github.com/peca12968/vr-command-center/actions/runs/43401900230)

## 2026-11-13 離線發行核對指出混版與 APK 簽署差異

- `verify-venue-release.py` 可指出 Windows 與 Quest 建置來源或網路識別的差異欄位。Windows 共用檔不一致時，列出差異數量及最多三個套件內相對路徑。APK 發行回條有記載簽署憑證指紋時，會與 Android 工具驗出的憑證核對，並逐欄核對有記載的套件 ID、SDK 及 v2 簽章。 [操作說明](EXTERNAL_CLIENTS.md#發送前離線核對交付套件)
- 以實際套件執行五種案例。原 Windows 0.50.7、管理 0.31.187、Quest 0.50.7 通過，報告與既有版本相同。混入 Windows 0.50.6 玩家包或 Quest 0.50.6 APK 時指出 `sourceFingerprint`。原簽署 APK 搭配改動憑證指紋的回條被拒絕，省略選用欄位的回條通過。8 個原始 APK、回條與套件清單的雜湊相符。 [驗證摘要](../artifacts/venue-release-mismatch-validation.json)
- 通過 8 項發行核對、10 項伺服器封裝、7 項玩家封裝及 7 項管理封裝檢查。玩家封裝的符號連結測試因本機 Windows 權限跳過。`61f6bbd` 已推送，GitHub Actions 因帳務或支出上限未啟動。跨機、頭盔、MR 場地及廠商硬體仍待實機驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43401091452)

## 2026-11-13 全館戰績 ZIP 包含分房與全館合計

- 管理包 0.31.187 的「下載本批戰績 ZIP」新增 `scores.csv`，與獨立下載的分房合計逐位元相同。清單以 `scoresFile` 標示檔名。API 加 `includeScores=true` 可取得新版內容，省略參數沿用既有格式。開發版與解壓版各通過 20 項戰績瀏覽器檢查，另通過 133 項全館流程。首輪瀏覽器驗證取到空的回應正文，改以獨立 API 讀取比對下載檔後通過。 [操作方式](REPORTS.md#下載全館結束批次) · [驗證摘要](../artifacts/venue-score-zip-187-validation.json)
- 434 項 Windows 三包檢查通過。五房獨立與合併各 25 位同機模擬玩家，共核對 50 份戰績回條、1,350 格回放及雙封存。兩種 ZIP 均保留原逐房 CSV，並逐位元核對合計檔。房間重用後可從瀏覽器下載原獨立批次的同一份 ZIP。程序清理後 C／F 215 個非資料庫檔案雜湊相符。 [本機檢查](../artifacts/server-package-checks/run-036cd6df0d3c4863ba6d8ae288fef060/checks.json)
- 通過 1,109 項核心、825 項 HTTP 及 107 項管理包檢查。解壓核對 567 筆清單及 `2a3925f` 的 193 個建置來源，29 檔按換行正規化比對。既有 Windows 與 Quest APK 通過相容性與簽章核對。功能和瀏覽器驗證提交已推送，兩次 GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地及廠商硬體待驗。 [管理包](../artifacts/VRCommand-ControlServer-0.31.187.zip) · [功能 CI](https://github.com/peca12968/vr-command-center/actions/runs/43400049492) · [測試 CI](https://github.com/peca12968/vr-command-center/actions/runs/43400327741)

## 2026-11-13 UDP 離線重驗指出缺件端別

- `start-verified-venue.py --verify-only` 可從可讀的一端對照原計畫，在待補席位標示 `missingRole` 為 `listener` 或 `probe`。雙端都無法確認時，仍列待補席位及配對數量。合併模式共用來源時會列出該來源涵蓋的全部席位。 [操作方式](WINDOWS_SERVER_PACKAGE.md#以-udp-預檢報告啟動五房)
- Windows 三包通過 449 項檢查。用同機 UDP 原報告測試缺任一端，獨立模式每次指出 5 席，合併模式指出 25 席。原檔齊備後兩種模式各以 25 位同機模擬玩家開場，核對兩份啟動回條、50 份戰績回條、6 份 CSV 與 1,243 格回放。清理後 C／F 的 215 個非資料庫檔案雜湊相符。 [驗證摘要](../artifacts/venue-udp-offline-counterpart-validation.json)
- 16 項 LAN、122 項封存與 12 項 Quest UDP 測試通過，既有六批正式驗收與收件摘要逐位元相符。`d95dd20` 已推送，GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地及廠商硬體仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43398946590)

## 2026-11-13 下載尚未儲存的任務草稿

- 0.31.186 在「任務範本」提供「下載草稿範本」。可將目前任務及物件保留在本機，再用既有範本流程取回。儲存回應遺失時，下載原送出的任務內容並保留待確認請求。開發版與解壓包各通過 53 項 Chromium 檢查，兩份下載檔雜湊相同，匯入後保留原簡報換行、修改後的 180 秒任務及 X 4.25 公尺物件位置。 [操作方式](MISSION_VERSIONS.md#在管理實例間交接任務範本) · [驗證摘要](../artifacts/mission-draft-186-validation.json)
- 將瀏覽器下載的原檔交給隔離的 Windows 管理服務後，五房獨立與合併的原生世界均核對任務時間、環境、敵軍及物件設定。各 25 位同機模擬玩家，共核對 50 份伺服器戰績回條、6 份 CSV、1,075 格回放及雙封存。401 項三包檢查通過，程序清理後 C／F 的 213 個非資料庫檔案雜湊相符。驗證摘要首輪把瀏覽器報告整份比對，改核對實際欄位後通過。 [原生檢查](../artifacts/server-package-checks/run-1eca2bae49e54463907e57808e5e6032/checks.json)
- 通過 1,109 項核心、107 項管理包及 7 項封裝檢查。解壓核對 567 筆清單及 `a1969da` 的 193 個建置來源，29 檔按換行正規化比對。既有 Windows 遊戲及 Quest APK 通過相容性與 APK 簽章核對。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地及廠商硬體待驗。 [下載管理包](../artifacts/VRCommand-ControlServer-0.31.186.zip) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43397978726)

## 2026-11-13 玩家循環播放本機回放片段

- 控制台 0.31.185 的玩家回放可循環播放原匯出片段，保留速度及房間視角。用解壓管理包在 390 像素寬的 Chromium 載入原 Windows 全場檔及第 4 房檔，兩份均按第 100 → 90 → 100 格播放，取消後停在第 100 格。另核對暫停保留畫面、跳到遊戲來源恢復及全程零 API 請求。兩份既有匯出檔雜湊相符。 [操作方式](WORLD_RECORDING.md) · [原檔播放證據](../artifacts/console-player-loop-185-native/checks.json)
- 開發版及解壓包各通過 143 項觀戰回放檢查，另通過 107 項管理包、5 項 Node 及 7 項封裝檢查。解壓核對 567 筆清單及 `240a3e3` 的 193 個建置來源，29 檔按換行正規化比對。首輪打包因版本檢查仍為 0.31.184 退出，更新打包及驗收腳本後通過。原檔播放初次啟動的隔離 API 缺測試金鑰，補上後重跑通過。 [驗證摘要](../artifacts/player-replay-loop-185-validation.json)
- 功能與打包修正 `240a3e3`、`a72b9fb` 已推送。兩次 GitHub Actions 均因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地及廠商硬體仍待驗收。 [功能提交 CI](https://github.com/peca12968/vr-command-center/actions/runs/43396812109) · [打包修正 CI](https://github.com/peca12968/vr-command-center/actions/runs/43396963442)

## 2026-11-13 Windows 啟動器複製本輪五房報告路徑

- 1.23 批次視窗在報告寫出後啟用「複製就緒路徑」與「複製結果路徑」。結束後可取本輪兩份報告，修改或重新核對計畫會清除按鈕。實際 WinForms 按鈕處理通過六項專項，含 Unicode 路徑、剪貼簿忙碌、檔案移除與清除舊路徑。測試以替身接收複製內容。桌面工具初始化仍回報 Windows 錯誤 3，本輪未驗證實際桌面剪貼簿。 [操作方式](WINDOWS_SERVER_PACKAGE.md#從-windows-視窗核對並啟動) · [驗證摘要](../artifacts/server-launcher-1.23-report-copy-validation.json)
- 新 ZIP 解壓後核對 331 筆清單，324 個遊戲執行檔案與 1.22 相同。初次打包指定 1.22 包內的複本，建置收據的原始路徑檢查拒絕；改從收據指定的原 Windows 建置打包後成功。管理包 0.31.184、玩家包與原 Quest 0.50.7 APK 通過相容性及 APK 簽章核對。 [下載 ZIP](../artifacts/server-packages/VRCommand-GameServer-0.50.7-1.23-win-x64.zip) · [發行核對](../artifacts/server-launcher-1.23-venue-release.json)
- 通過 51 項啟動器、70 項 Framework、10 項封裝及 393 項 Windows 三包檢查。獨立及合併各 25 位同機模擬玩家，核對 50 份伺服器戰績回條、6 份 CSV、1,187 格回放及雙封存。程序清理後 C／F 的 213 個非資料庫檔案雜湊相符。`c379996` 已推送，GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地及廠商硬體待驗。 [本機檢查](../artifacts/server-package-checks/run-a14f94f74c51461db8f8a3f5bace0d45/checks.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43395977465)

## 2026-11-13 硬體排演顯示管理連線故障原因

- 模擬器 0.2.15 在本機單房終端與五房狀態提供三種管理故障碼。以隔離的管理服務和模擬接收端實測第 4 房收到 HTTP 503、逾時及傳輸中斷。恢復後以新連線附掛，取消舊待確認批次，保留舊確認並只新增一筆新確認。新版可讀取舊版未附原因的狀態。 [操作說明](HARDWARE.md#查看五房排演狀態) · [故障快照](../artifacts/live-hardware-gateway/run-d7d4d4cfcb93481da411ace169286d1b/linked-fleet-management-statuses.json)
- Windows 通過 1,109 項核心、38 項離線與 82 項即時模擬檢查，含五房獨立及合併。解壓核對 8 個清單檔案，並用解壓版重跑 38 項離線檢查。前兩次直接把即時證據寫到 F 槽，分別在既有批次等待及既有房間狀態斷言中止，兩次測試程序均清理。完成場先將證據寫到 C 槽，停止程序後複製，163 檔在 C／F 逐檔雜湊相符。 [即時檢查](../artifacts/live-hardware-gateway/run-d7d4d4cfcb93481da411ace169286d1b/checks.json) · [解壓版檢查](../artifacts/hardware-simulator/run-a5460179c040480dafe7aa68ade23c07/checks.json)
- `484273e` 已推送。GitHub Actions 因帳務或支出上限未啟動。桌面仍有「Windows 安全性」視窗，本輪驗證使用命令列。六台工作站直連、跨機 25 人、頭盔、MR 場地及廠商硬體仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43394966139)

## 2026-11-13 命令列列出工作站回條問題

- `check-venue-operator.py --verify-workstations` 可混用瀏覽器原回條與命令列 JSON。可先提供一至六份檔案，本機列出缺少或重複的角色。收齊後，會從管理服務的拒絕回應擷取已知角色及原因。 [命令列操作](WINDOWS_CONTROL_PACKAGE.md#命令列操作)
- 通過 12 項命令列、31 項實際 HTTPS 與 18 項工作站瀏覽器檢查。只提供四份時，命令列指出缺第 4、5 房，無需主控金鑰。混合格式的六份同機簽署回條經管理服務逐房拒絕。沿用管理包 0.31.184，ZIP 雜湊相符。六個來源相符時的瀏覽器畫面沿用模擬回應。 [驗證摘要](../artifacts/venue-workstation-cli-validation.json)
- `22deaeb` 已推送。GitHub Actions 因帳務或支出上限未啟動。六台工作站直連、跨機 25 人、頭盔、MR 場地及廠商硬體仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43394019423)

## 2026-11-13 主控台逐台列出工作站回條問題

- 管理台 0.31.184 可在本機檢查部分回條，列出缺少或重複的主控與房控角色。收齊後由管理服務核對簽章、來源及 15 分鐘期限，回應只列未通過的角色和原因。 [操作說明](WINDOWS_CONTROL_PACKAGE.md#核對主控與五房控的直連來源) · [Windows 管理包](../artifacts/VRCommand-ControlServer-0.31.184.zip)
- 解壓包通過 30 項 HTTPS 與 18 項 Chromium 工作站檢查。實際從同一台 Windows 電腦下載六個角色的簽署回條，管理服務逐房拒絕不符的來源。選四份回條時瀏覽器列出缺少的兩房，且未送出回條。六個來源相符時的畫面以模擬回應驗證。 [驗證摘要](../artifacts/console-workstation-diagnostics-validation.json)
- 通過 1,109 項核心、825 項 HTTP、11 項命令列、107 項管理包及 1,166 項完整瀏覽器檢查。解壓核對 567 筆清單與提交 `924e531` 的 193 個建置來源，其中 29 檔按換行正規化比對。GitHub Actions 因帳務或支出上限未啟動。六台工作站直連、跨機 25 人、頭盔、MR 場地與廠商硬體仍待驗收。 [離線核對](../artifacts/console-workstation-diagnostics-release.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43392605582)

## 2026-11-13 UDP 離線重驗指出待補原因

- `--verify-only` 的待補席位可附原因，包含原檔無法讀取、量測逾期、時間戳未早於核對時間、雙端屬不同交換、端點不符及報告無效。沿用原配對及 30 分鐘規則。 [操作說明](WINDOWS_SERVER_PACKAGE.md#以-udp-預檢報告啟動五房)
- Windows 三包通過 688 項。缺一份探測原檔時，獨立 5 席與合併 25 席均指出原檔無法讀取。兩種模式各 25 位同機模擬玩家，核對 50 份戰績回條、6 份 CSV 與 1,072 格回放。清理後 C／F 259 個非資料庫檔案雜湊相符。 [驗證摘要](../artifacts/venue-udp-offline-reasons-validation.json)
- 通過 150 項封存及 UDP 測試，六批既有正式與收件摘要逐位元相符。首輪 LAN 測試的區域變數覆蓋既有報告，修正測試變數後通過。`b4b658f` 已推送，GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地及廠商硬體待驗。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43391738372)

## 2026-11-13 Windows 啟動前離線重驗 UDP 原檔

- `start-verified-venue.py --verify-only` 沿用正式啟動的原計畫、預覽和雙端 UDP 證據核對，輸出可重用的來源數及待補席位。只做檔案與時限核對，實際啟動仍會確認最新場次與名冊。 [操作說明](WINDOWS_SERVER_PACKAGE.md#以-udp-預檢報告啟動五房)
- Windows 三包通過 688 項。離線重驗核對獨立五個來源與合併一個來源，缺一份探測原檔時分別列出 5 席與 25 席，管理端場次不變。正式啟動後兩種模式各 25 位同機模擬玩家，核對 50 份戰績回條、6 份 CSV 與 1,117 格回放。隔離程序清理後 C／F 259 個非資料庫檔案雜湊相符。 [驗證摘要](../artifacts/venue-udp-offline-recheck-validation.json)
- 122 項封存、16 項 LAN、12 項 Quest UDP 測試通過。首輪 LAN 測試把共用來源誤預期為每房一席，按原清單修正為每房三席後通過。`3c18006` 已推送，GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、實體頭盔、MR 場地與廠商硬體待驗。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43390852330)

## 2026-11-13 全館 UDP 收件列出待補席位與端別

- UDP 收件問題若可對上原網路清單中的伺服器端點與探測來源，會附受影響的房號與席號。缺對端會指出監聽端或探測端。六批總表列出席位與端別，原檔名留在個別 UDP 預檢報告。 [操作說明](EXTERNAL_CLIENTS.md#從資料夾配對-udp-報告)
- 以兩次同機 UDP 交換各留一端，總表指出合併 10 席的兩類缺件，其他五批通過。補回原檔後重試核對兩個來源。122 項封存、16 項 LAN、12 項 Quest UDP 測試通過，六批原正式與收件摘要逐位元相符，共 80 份伺服器回條。 [驗證摘要](../artifacts/venue-udp-inbox-seat-validation.json) · [收件範例](../artifacts/venue-udp-inbox-seat-inspection.json)
- `3577adc` 已推送，GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、實體頭盔、MR 場地與廠商硬體待驗。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43390127390)

## 2026-11-13 補齊原收件夾後重跑全館 UDP 預檢

- 缺少監聽端或探測端原檔時，補進同一收件夾即可使用 `--retry-report` 重跑。原路徑的同一對檔案只計一次，工具仍重新核對原雜湊和有效期限。原檔變更及重複角色檔案仍會使預檢不完整。 [操作說明](EXTERNAL_CLIENTS.md#補測未完成的全館-udp-預檢)
- 以兩次實際同機 UDP 交換重現舊版重試退出 1，新版退出 0 並保留一個原來源。核對四份雙端原檔雜湊相同。首輪對照的隔離目錄漏帶 PowerShell 驗證腳本，補齊後在新目錄重跑。另通過 16 項 LAN、12 項 Quest UDP 與 122 項封存測試，六批原收件與正式摘要逐位元相符，共 80 份伺服器回條。 [驗證摘要](../artifacts/venue-udp-original-inbox-retry-validation.json)
- 功能提交 `73ccf3e` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地與廠商硬體仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43389457530)

## 2026-11-13 從 Windows 結束報告開啟原批次戰績

- 管理台 0.31.183 核對全館結束報告後，可直接選取原批次的戰績與回條。點選時重新讀取並比對原場次、房號、錄製來源與封存尾端。解壓版在兩種模式各以替換尾端的回應驗證會保留原選取。逐房個別結束的場次仍可開啟其原回放。 [操作說明](WINDOWS_SERVER_PACKAGE.md#核對未確認的啟動報告) · [Windows 管理包](../artifacts/VRCommand-ControlServer-0.31.183.zip)
- Windows 三包通過 686 項。獨立與合併各 25 位同機模擬玩家，兩份原結束報告各開啟對應批次及五房回放，核對共 50 份戰績回條、6 份 CSV 與 1,031 格回放。隔離程序清理後 C／F 的 259 個非資料庫檔案雜湊相符。 [驗證摘要](../artifacts/console-venue-terminal-closure-validation.json)
- 通過 825 項 HTTP、107 項管理包、來源及解壓包各 31 項報告專項、1,166 項完整瀏覽器檢查。解壓核對 567 筆清單與提交 `996e85e` 的 193 個建置來源，其中 29 檔以換行正規化比對。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、實體頭盔、完整桌面操作、MR 場地及廠商硬體仍待驗收。 [離線核對](../artifacts/console-venue-terminal-closure-release.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43388243938)

## 2026-11-13 從 Windows 結束報告對齊獨立房間回放

- 管理台 0.31.182 在管理實例、五房雙封存及同一筆全館結束命令均核對後，從 Windows 報告開啟的回放可按 UTC 或任務活動時間對齊同批房間。合併場繼續在同一錄製內切換房間。首次核心測試發現同批房間的 End 時間戳可不同，改按原命令及完整場次核對，並覆蓋重啟、房間重用及不同批次。 [操作說明](WORLD_RECORDING.md#對齊同批獨立房間的回放) · [Windows 管理包](../artifacts/VRCommand-ControlServer-0.31.182.zip)
- 解壓三包通過 592 項。獨立與合併各 25 個同機模擬玩家，核對 10 個房間回放入口、50 份戰績回條、6 份 CSV 和 1,163 格回放。從原獨立結束報告開啟第 1 房，任務刻 4 對齊同批第 2 房刻 3。隔離程序清理後 C／F 259 個非資料庫檔案雜湊相符。 [本機驗證](../artifacts/console-venue-terminal-alignment-validation.json)
- 另通過 1,108 項核心、825 項 HTTP、107 項管理包、來源及解壓包各 30 項報告專項、29 項時間對齊專項，以及 1,165 項完整瀏覽器檢查。解壓核對 567 筆清單及 `fa7850d` 的 193 個建置來源，其中 29 檔以換行正規化比對。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、完整桌面操作、頭盔、MR 場地與廠商硬體待驗。 [離線核對](../artifacts/console-venue-terminal-alignment-release.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43387013950)

## 2026-11-13 從 Windows 封存結果開啟原房間回放

- 管理台 0.31.181 在管理實例和雙封存相符後，提供逐房回放捷徑。觀戰頁重新比對原場次、來源、房間與封存尾端。瀏覽器專項覆蓋房間已重用及錄製尾端變動，來源與解壓包各通過 29 項。首次專項等待了錯誤的提示欄位，修正測試選擇器後通過。 [操作說明](WINDOWS_SERVER_PACKAGE.md#核對未確認的啟動報告) · [Windows 管理包](../artifacts/VRCommand-ControlServer-0.31.181.zip)
- 三包整合通過 591 項。以兩份原生結束報告在解壓版各開啟五房，獨立場對上五份原錄製，合併場對上同一錄製內五個房間。兩種模式各 25 位同機模擬玩家，共核對 50 份戰績回條、6 份 CSV 及 1,104 格回放。清理後 C／F 259 個非資料庫檔案雜湊相符。 [本機驗證](../artifacts/console-venue-terminal-replay-validation.json)
- 另通過 107 項管理包及 1,164 項完整瀏覽器檢查。解壓核對 567 筆清單與提交 `5250e6f` 的 193 個建置來源，其中 29 檔以換行正規化比對。Windows 套件與既有 Quest APK 通過離線相容性核對。GitHub Actions 因帳務或支出上限未啟動。完整桌面操作、跨機 25 人、頭盔、MR 場地與廠商硬體仍待驗。 [離線核對](../artifacts/console-venue-terminal-replay-release.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43385591290)

## 2026-11-13 管理台核對 Windows 全館結束報告

- 管理台 0.31.180 的「核對全館啟動與封存」接受第四版計畫正常結束的 `venue-sealed-stopped` JSON。逐組核對原場次、批次、來源及戰鬥與回放封存尾端。測試確認尚未雙封存、任一序號不同或來源類型不同時，畫面不會顯示相符。 [操作說明](WINDOWS_SERVER_PACKAGE.md#核對未確認的啟動報告) · [Windows 管理包](../artifacts/VRCommand-ControlServer-0.31.180.zip)
- 三包整合通過 591 項。五房獨立及合併模式各 25 位同機模擬玩家，原生結束報告匯入解壓管理台後，六場雙封存序號都相符。核對 50 份伺服器戰績回條、6 份 CSV、1,125 格回放，清理後 C／F 的 259 個非資料庫檔案雜湊相符。 [本機驗證](../artifacts/console-venue-terminal-review-validation.json)
- 另通過 1,105 項核心、825 項 HTTP、107 項管理包、來源與解壓包各 27 項瀏覽器專項，以及 1,162 項完整瀏覽器檢查。先前兩次專項停在 Chromium 檔案不存在或缺少 V8 資料，改用本機完整 Chromium 後通過。解壓核對 567 筆清單與提交 `58111b0` 的 193 個建置來源，其中 29 檔以換行正規化比對。GitHub Actions 因帳務或支出上限未啟動。桌面完整操作、跨機 25 人、頭盔、MR 場地與廠商硬體仍待驗。 [離線版本核對](../artifacts/console-venue-terminal-review-release.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43384245983)

## 2026-11-13 Windows 批次啟動器顯示逐房席位

- Windows 啟動器 1.22 在啟動前列出五房各自登記的席號，保留空出的席位。合併場的五列共用同一場次與端點。第一版計畫顯示「計畫未提供」，已核對的空名冊顯示「尚未登記」。啟動時仍會重新核對原場次與名冊。 [操作說明](WINDOWS_SERVER_PACKAGE.md#從-windows-視窗核對並啟動) · [伺服器包](../artifacts/server-packages/VRCommand-GameServer-0.50.7-1.22-win-x64.zip)
- 解壓包通過 51 項啟動器、64 項 Framework、10 項封裝及 587 項 Windows 三包整合檢查。獨立與合併各 25 個同機模擬玩家，核對六份 CSV、50 份伺服器戰績回條、1,272 格完整回放及雙封存。隔離程序正常清理，C／F 的 259 個非資料庫檔案雜湊相符。首次三包命令漏帶本機 IPv4，參數檢查退出後以完整參數重跑。 [驗證摘要](../artifacts/server-launcher-1.22-seat-preview-validation.json)
- 解壓後核對 331 筆清單，其中 324 個遊戲執行檔與 1.21 相同。管理包、玩家包與原 Quest APK 通過離線相容性及簽章核對。`dec5b0c` 已推送，GitHub Actions 因帳務或支出上限未啟動。桌面工具仍在初始化回報 Windows 錯誤 3，完整可見視窗操作、跨機 25 人、實體頭盔、MR 場地與廠商硬體待驗。 [離線核對](../artifacts/server-launcher-1.22-venue-release.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43383024954)

## 2026-11-13 六批收件總表辨識啟動回條雜湊不符

- 六批收件檢查會列出與 Windows 啟動回條雜湊不符的原報告類別和檔名。以六批同機資料的副本驗證，結束報告、UDP 預檢及就緒報告的三種雜湊不一致各自被辨識，缺少就緒報告也會列出檔名。其餘兩批通過，正式驗收拒絕缺件的總清單。 [操作說明](EXTERNAL_CLIENTS.md#六批使用各自的-windows-啟動回條) · [缺件範例](../artifacts/staged-venue-start-evidence-inspection.json)
- 六批正式與收件摘要均與封存逐位元相符，共核對 80 份伺服器戰績回條。核對前後 31 個原始清單及回條相關檔案雜湊相符，另重新產生一份獨立場清單並通過五場啟動核對。122 項封存、16 項 LAN 預檢、12 項 Quest UDP 測試通過。`e6d0338` 已推送，GitHub Actions 因帳務或支出上限未啟動。 [驗證摘要](../artifacts/staged-venue-start-evidence-validation.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43381998552)
- 使用者已關閉先前的遮擋視窗。桌面複驗停在自動化工具初始化，重設後仍無法寫入執行環境檔案（Windows 錯誤 3）。完整桌面流程、跨機 25 人、頭盔、MR 場地及廠商硬體仍待驗收。

## 2026-11-13 六批收件總表列出 UDP 待補席位

- `--inspect-venue-stages` 在 `issues[].udpPreflight` 列出未完成的全館與 Quest UDP 預檢。回報包含原報告的檔名、項次、待補房號與席號。若缺少原報告、來源重複或啟動計畫比對失敗，也會列出相應狀態。正式驗收仍要求原預檢完整通過。 [操作說明](EXTERNAL_CLIENTS.md#一次查看六批待補件)
- 以 25 席獨立及合併的既有同機資料重新產生兩份缺件預檢，總表指出 30 席缺少來源與 20 席紀錄已過期。另四批通過，兩份待補批次均遭正式驗收拒絕。首輪驗證只預期列出刻意移除的來源，補入原交換已超過有效時間的實際結果後重新核對。六批原封存的收件及正式摘要逐位元相符，共核對 80 份戰績回條。 [缺件範例](../artifacts/staged-venue-udp-intake-final-inspection.json)
- 通過 121 項封存、16 項 LAN 預檢及 12 項 Quest UDP 測試。功能來源 `b261ff6` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地及廠商硬體仍待驗收。 [驗證摘要](../artifacts/staged-venue-udp-intake-validation.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43381012798)

## 2026-11-13 全館命令遭拒時顯示受影響房間

- Windows 管理台 0.31.179 從管理服務回應取得受影響房號。五房獨立列出有變更的房間。五房合併共用同一場次版本，因此該版本變更時會列出五房。批次遭拒後，主控重新整理並核對開場條件，再確認一次。 [操作說明](PLAYER_READINESS.md#五房追蹤驗收開場) · [Windows 管理包](../artifacts/VRCommand-ControlServer-0.31.179.zip)
- Chromium 在開場請求抵達管理服務前為第 2 房加一席，收到 409 並顯示第 2 房，原批次所有場次維持準備中。原生排演也以過期開場計畫分別核對獨立的第 5 房及合併的五房。重新讀取後兩種模式各 25 位同機模擬玩家完成入場及結算，通過 539 項三包整合，核對 50 筆戰績回條、6 份 CSV、1,094 格回放與雙封存。清理後 C／F 共 255 個非資料庫檔案雜湊一致。 [三包驗收](../artifacts/server-package-checks/run-4fc2b62e9b1744b6ad26cfb4967d0776/checks.json)
- 通過 1,105 項核心、825 項 HTTP、107 項管理包、來源及解壓包各 133 項場次瀏覽器檢查，以及 1,157 項完整瀏覽器回歸。解壓核對 567 筆清單，193 個建置來源與提交 `16b1248` 相符，其中 29 檔按 Git 換行正規化比對。Windows 套件與原 Quest APK 通過離線版本及簽章核對。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地及廠商硬體仍待驗收。 [驗證摘要](../artifacts/console-venue-phase-conflict-validation.json) · [離線核對](../artifacts/console-venue-phase-conflict-venue-release.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43379348348)

## 2026-11-13 全館就緒結果顯示即時開場席位

- Windows 管理台 0.31.178 在核對原來源與端點後，於逐房名冊捷徑旁顯示準備中場次的席號與姿態狀態。未編列、入場待同步、姿態未就緒、合成及追蹤各自標示。快照過期會撤下原席位結果。開場仍由全館場次控制確認。 [操作說明](WINDOWS_SERVER_PACKAGE.md#核對未確認的啟動報告) · [Windows 管理包](../artifacts/VRCommand-ControlServer-0.31.178.zip)
- Windows 三包整合通過 537 項。從兩種模式的原始就緒檔核對各五房 25 個合成姿態席位。原開場序號一致，兩批共 50 筆戰績回條、6 份 CSV、1,084 格回放。停止後 C／F 共 255 個非資料庫檔案雜湊一致。 [三包驗收](../artifacts/server-package-checks/run-543527daeed84cb59b6035fbefdc2439/checks.json)
- 通過 825 項 HTTP、107 項管理包、91 項追蹤政策專項、來源與解壓包各 22 項就緒核對，以及 1,156 項完整瀏覽器回歸。首次專項的任務有敵軍，但測試快照未提供敵軍，修正測試任務後通過。解壓核對 567 筆清單，193 個建置來源與提交 `c06876c` 相符，核對時比對換行正規化後的 Git 檔案。Windows 套件及原 Quest APK 通過離線版本及簽章核對。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、實體頭盔、MR 場地及廠商硬體仍待驗收。 [驗證摘要](../artifacts/console-ready-live-seats-validation.json) · [離線核對](../artifacts/console-ready-live-seats-venue-release.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43378128134)

## 2026-11-13 從全館就緒結果開啟原房間名冊

- Windows 管理台 0.31.177 在核對到原管理實例、場次來源及公告端點後，提供逐房名冊捷徑。合併場可從共用端點的結果選擇任一房。點選時重讀原場次，若已結束或來源不符，畫面要求重新核對就緒檔。 [操作說明](WINDOWS_SERVER_PACKAGE.md#核對未確認的啟動報告) · [Windows 管理包](../artifacts/VRCommand-ControlServer-0.31.177.zip)
- 用原 Windows 就緒檔在獨立及合併模式各開啟五房名冊，逐房核對原場次、房號、五席及原開場序號。兩種模式各 25 個同機模擬玩家完成入場與結算，537 項整合通過，核對 50 筆戰績回條、6 份 CSV 和 1,005 格回放。程序清理後 C／F 共 255 個非資料庫檔案雜湊一致。 [三包驗收](../artifacts/server-package-checks/run-63af21a432ee48f6a025ddcb2228b66b/checks.json)
- 通過 825 項 HTTP、107 項管理包、來源及解壓包各 20 項 Chromium 專項，以及 1,154 項完整瀏覽器回歸。解壓核對 567 筆清單，193 個建置來源與提交 `64324cb` 相符。Windows 套件與原 Quest 0.50.7 APK 通過離線版本及簽章核對。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、實體頭盔、MR 場地及廠商硬體仍待驗收。 [驗證摘要](../artifacts/console-ready-roster-shortcuts-validation.json) · [離線核對](../artifacts/console-ready-roster-shortcuts-venue-release.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43376869325)

## 2026-11-13 主控台核對 Windows 全館就緒檔

- 管理台 0.31.176 可從「核對全館伺服器就緒」讀取 Windows 啟動器的原就緒檔。按下核對後，管理服務逐組比對原場次、遊戲來源、公告 IPv4、UDP 埠與近期快照。當遊戲綁定所有網卡，仍以原公告位址比對。面板也可讀取原未確認啟動結果。 [操作說明](WINDOWS_SERVER_PACKAGE.md#核對未確認的啟動報告) · [Windows 管理包](../artifacts/VRCommand-ControlServer-0.31.176.zip)
- 解壓包 Chromium 匯入五房獨立與合併的原就緒檔，開場前分別對上五組及一組遊戲來源及端點。匯入前後的開場序號一致。537 項三包整合通過，兩種模式各 25 個同機 Windows 模擬玩家，核對 50 筆伺服器戰績回條、6 份 CSV、1,076 格回放及雙封存。成功場 C／F 共 255 個非資料庫檔案雜湊相符。 [三包檢查](../artifacts/server-package-checks/run-e9bd8ec29b0043178fc4d86b0b336497/checks.json)
- 另通過 1,105 項核心、825 項 HTTP、15 項解壓版 Chromium 與 107 項管理包檢查。解壓核對 567 筆清單，193 個建置來源檔與提交 `6fc7f3a` 相符。首次瀏覽器專項缺少世界標頭及時鐘欄位，首次三包測試覆蓋開場斷言變數，均保留失敗紀錄並修正測試。Windows 包與原 Quest 0.50.7 APK 已通過離線版本及簽章核對。跨機 25 人、頭盔、MR 場地及廠商硬體仍待驗收。 [離線交付核對](../artifacts/console-windows-ready-review-venue-release.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43375240281)
- 首次完整瀏覽器回歸因舊測試假設錄製只有兩頁而失敗。測試改沿原游標讀到尾頁並檢查原錄製只出現一次，重新通過 1,149 項。`6fc7f3a` 及測試提交 `f099530` 的 GitHub Actions 均因帳務或支出上限未啟動。 [本機驗證摘要](../artifacts/console-windows-ready-review-validation.json) · [測試提交的 GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43375722928)

## 2026-11-13 Windows 正式啟動重新核對五房席位

- Windows 伺服器啟動器 1.21 的場館預覽帶入原場次房號與已登記席號。命令列產生清單及 UDP 預檢會核對完整席位，正式啟動再以原計畫向管理服務讀取一次。若預檢後名冊變更，需重新下載啟動計畫並核對預檢。 [伺服器包](../artifacts/server-packages/VRCommand-GameServer-0.50.7-1.21-win-x64.zip) · [操作說明](WINDOWS_SERVER_PACKAGE.md#從主控台下載場館計畫)
- Windows 三包整合通過 587 項。五房獨立與合併均實測移除一席後舊預檢被拒，且未建立原生工作目錄。重新登記後各以 25 個同機模擬玩家入場，核對 50 筆伺服器戰績回條、6 份 CSV、1,080 格完整回放及雙封存。清理後 C／F 共 259 個非資料庫檔案雜湊相符。 [本機驗收](../artifacts/server-launcher-1.21-roster-validation.json)
- 另通過 51 項啟動器、59 項 Framework、16 項 LAN、12 項 Quest UDP、120 項封存與 10 項封裝測試。解壓核對 331 筆清單，Windows 套件和原 Quest 0.50.7 APK 通過離線來源及簽章核對。功能來源 `190787f` 已推送，GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、實體頭盔、MR 場地及廠商硬體仍待驗收。 [離線交付核對](../artifacts/server-launcher-1.21-venue-release.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43374098622)

## 2026-11-13 UDP 預檢清單核對五房名冊

- 控制台 0.31.175 逐席比對上傳的 IPv4 表與準備中場次。若名冊與檔案有差異，會列出缺漏及未登記的房號與席號。按下載時再讀取原場次，可擋下預覽後換席的舊清單。Windows 啟動計畫仍可在空名冊時下載。 [操作說明](EXTERNAL_CLIENTS.md#從原啟動預覽產生網路清單) · [Windows 管理包](../artifacts/VRCommand-ControlServer-0.31.175.zip)
- 五房獨立與合併均從解壓包的控制台下載原清單，沿用至同機 UDP 預檢、原生啟動與封存。575 項三包整合通過，兩種模式各 25 個同機 Windows 模擬玩家，核對 50 筆原戰績回條、6 份 CSV、1,060 格回放及雙封存。隔離程序已停止，C／F 共 257 個非資料庫檔案雜湊相符。 [三包驗收](../artifacts/server-package-checks/run-98b3554ccbfc4814a6a6eb2ee8b81b55/checks.json)
- 另通過 1,105 項核心、825 項 HTTP、1,144 項完整 Chromium、解壓包 36 項 Chromium、107 項 Windows 管理包及 15 項 UDP 測試。首次套件核對將 ZIP 傳給需要解壓目錄的參數，改用解壓目錄後 567 筆清單全數通過。發行回條在提交前產生，193 個建置來源檔案已與提交 `4ac554b` 逐檔核對。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 與廠商硬體仍待現場驗收。 [驗證摘要](../artifacts/console-venue-network-roster-validation.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43372683603)

## 2026-11-13 管理台匯出五房伺服器 IPv4 清單

- 控制台 0.31.174 的五房啟動計畫可逐行填入伺服器其他 IPv4。公告位址會自動加入 UDP 預檢清單。下載前會指出衝突房號及席號，欄位與席位表只在瀏覽器處理。 [操作說明](EXTERNAL_CLIENTS.md#從原啟動預覽產生網路清單) · [Windows 管理包](../artifacts/VRCommand-ControlServer-0.31.174.zip)
- 套件版 Chromium 通過 30 項啟動計畫檢查。以瀏覽器匯出的五席、三伺服器位址清單讀回預檢，確認自動套用逐席直連。測試副本若將一席改為第二網卡位址，預檢會指出該席並拒絕輸出。另通過 825 項 HTTP 與 107 項套件啟停檢查。 [本機驗證摘要](../artifacts/console-venue-server-ip-inventory-validation.json)
- 功能來源 `5bd3909` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 與廠商硬體仍待現場驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43371754542)

## 2026-11-13 五房預檢核對伺服器其他 IPv4

- 產生網路清單時可重複使用 `--server-ip` 登記伺服器的其他網卡位址。UDP 預檢、驗證啟動及封存清單會核對原位址表。若席位誤用伺服器位址，工具會指出房號與席號。 [操作說明](EXTERNAL_CLIENTS.md#從原啟動預覽產生網路清單)
- 獨立及合併各以 25 席受控清單測試第二個伺服器位址衝突，兩批均在原生啟動前遭拒。修正位址表後可產生清單。15 項 LAN、12 項 Quest UDP 及逐席封存專項通過。既有六批同機封存的 80 份戰績確認輸出逐位元相符。 [本機驗證摘要](../artifacts/venue-server-ip-inventory-validation.json)
- 功能來源 `0d52570` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 與廠商硬體仍待現場驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43371277150)

## 2026-11-13 逐席直連條件沿用至五房啟動

- UDP 預檢報告會保留逐席直連條件。補測、合併報告及驗證啟動會重新套用，啟動時可省略已保存的旗標。正式啟動回條會記下此條件，封存驗收會拒絕遺漏條件的回條。 [操作說明](EXTERNAL_CLIENTS.md#補測未完成的全館-udp-預檢)
- 獨立與合併各用 25 對受控 UDP 報告測試補測與合併。兩份原同機 25 席清單即使省略旗標，也在啟動前遭拒。沿用原設定重驗六批已封存資料，80 份戰績確認與既有輸出逐位元相符。另通過 14 項 LAN 與 12 項 Quest UDP 本機測試。 [本機驗證摘要](../artifacts/distinct-roster-handoff-validation.json)
- 功能來源 `e0dbdfd` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 與廠商硬體仍待現場驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43370752384)

## 2026-11-13 五房逐席直連的開場前檢查

- 場館可在產生網路清單、UDP 預檢及驗證啟動時選用 `--require-distinct-remote-roster`。工具會指出共用 IPv4 或與伺服器位址衝突的房號、席號。封存驗收也會核對原清單與完整伺服器位址表。 [操作說明](EXTERNAL_CLIENTS.md#從原啟動預覽產生網路清單)
- 獨立與合併各 5、10、25 席的原同機資料在逐席直連模式下均於啟動前遭拒，沒有產生新啟動報告。用原模式重驗六批封存，80 份戰績確認與既有輸出逐位元相符。 [本機驗證摘要](../artifacts/distinct-remote-roster-preflight-validation.json)
- 功能來源 `5a4bb8f` 已推送。首次本機測試遇到診斷字串更新與 Java 編譯逾時，重新執行通過 LAN 與 Quest UDP 各 12 項。120 項封存回歸也通過。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 與廠商硬體仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43369923133)

## 2026-11-13 玩家回放顯示任務活動時間與來源暫停

- 管理包 0.31.173 的玩家回放可分別查看片段播放時間與任務活動時間，並可跳到保存的遊戲來源暫停或恢復畫格。全場版及單房版均支援，舊檔缺少計時或暫停資訊時仍可開啟。 [操作說明](WORLD_RECORDING.md) · [Windows 管理包](../artifacts/VRCommand-ControlServer-0.31.173.zip)
- 用一份已封存的 Windows 25 席合併錄製匯出全場與第 4 房各 11 格，逐格核對來源資料。兩份檔案皆在 390 像素寬的 Chromium 播放器跳到第 91 格暫停和第 98 格恢復，暫停期間片段時間前進而任務活動時間停在 6 秒。播放器未發出 API 請求。另通過 140 項觀戰回放、138 項串流、107 項套件及 7 項單元測試。 [本機驗證摘要](../artifacts/player-replay-source-pause-validation.json)
- 功能來源 `ce2209c` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機、頭盔、MR 與廠商硬體仍待現場驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43369041992)

## 2026-11-13 觀戰與回放定位遊戲來源暫停及恢復

- 控制台 0.31.172 新增「遊戲來源暫停／恢復」篩選。即時觀戰可定位最近一筆，暫停回放後可用清單或上一筆／下一筆跳到原畫格。手動暫停可從「場次階段」查閱。若讀回的暫停狀態與搜尋結果不符，保留目前畫面。 [操作說明](WORLD_RECORDING.md) · [Windows 管理包](../artifacts/VRCommand-ControlServer-0.31.172.zip)
- 從已封存的 Windows 25 席合併錄製獨立複製資料，以新版管理包及 Chromium 驗證主控與第 4 房視角均跳到第 91 格暫停、第 98 格恢復。另以新的五席合併排演核對階段、環境與策略搜尋，8 項通過。107 項套件、1,105 項核心、138 項串流、32 項 Python，以及開發版和套件各 18 項計時、38 項環境及設定瀏覽器測試通過。 [本機驗證摘要](../artifacts/source-suspension-search-validation.json)
- 初次封存檢查對唯讀版面查詢的 HTTP 方法及第 4 房鏡頭選擇假設有誤，修正驗證腳本後重跑通過。功能來源 `6c8a18e` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機、頭盔、MR 及廠商硬體仍待現場驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43368438083)

## 2026-11-13 房間卡片顯示遊戲來源暫停

- 控制台 0.31.171 在收到有效的暫停畫格時顯示凍結的任務時間。畫格過期會清除時間，恢復畫格會接續顯示。即時觀戰及回放把「遊戲來源暫停」放在畫格階段，天氣與雷電維持在環境欄。 [操作說明](CLOCK_RECOVERY.md) · [管理服務包](../artifacts/VRCommand-ControlServer-0.31.171.zip)
- 用新版管理包和 Windows 0.50.7 執行五房合併同機驗收。五張房間卡片的 API 資料同時報告第 131 tick 暫停，剩餘 54 秒，並沿用管理序號 29 恢復。原 25 位模擬玩家收到戰績，核對 610 格完整回放。套件通過 107 項啟動器檢查及 14 項 Chromium 計時檢查，另通過 1,105 項核心、825 項 HTTP、138 項世界串流、23 項 Node、7 項 Python、14 項開發版計時與 137 項觀戰回放檢查。 [本機驗證摘要](../artifacts/game-source-frozen-clock-validation.json)
- 首輪測試的 tick 與畫格序號預期值已修正，套件瀏覽器首輪也因提前讀取解壓中的檔案而失敗，均重新執行通過。功能來源 `4690761` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機、頭盔、MR 及廠商硬體仍待現場驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43367558719)

## 2026-11-13 五房合併模式管理延遲驗收

- Windows 0.50.7 同機以五房各 5 位模擬玩家進入同一場。暫留共用管理 GET 後，五房時鐘停在 tick 125，沿用管理序號 29 恢復。第 125 與第 129 tick 的房間畫格讀回通過，五房各只讀到自己的 5 位玩家與戰績，10 次跨房查詢均收到 403。 [重跑方式](CLOCK_RECOVERY.md)
- 合併場在 tick 1200 自動結束一次，保留原本的 25 條 UDP 連線至收到結果，核對 25 份原入場戰績確認與 613 格完整回放。使用同一版測試工具複驗獨立模式，五場通過，共 25 份戰績確認與 2,978 格回放。兩輪 C／F 的 36 個關閉後快照檔逐檔雜湊相符。另通過 72 項本機測試。 [本機驗證摘要](../artifacts/native-linked-management-delay-validation.json)
- 功能來源 `77cf710` 已推送。GitHub Actions 因帳務或支出上限未啟動。舊 25 席偶發暫停原因、跨機、頭盔、MR 與廠商硬體仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43366562411)

## 2026-11-13 五房獨立模式管理延遲驗收

- Windows 0.50.7 同機開啟五個獨立房間及 25 個模擬玩家端。第 1 房的管理 GET 暫留後，遊戲時鐘停在 tick 133，隨後沿用原管理序號 9 恢復。其他四房同期各前進 11、11、10、7 tick，且原席位的姿態持續更新。五場各在 tick 1200 自動結束，核對 25 份原入場戰績確認及 2,980 格封存回放。 [重跑方式](CLOCK_RECOVERY.md) · [本機驗證摘要](../artifacts/native-five-room-management-isolation-validation.json)
- 首輪仍保留為失敗。當時檢查器將畫格的姿態有效狀態當成 UDP 連線狀態。新版以擷取時間比對精確畫格，並用原生客戶端日誌與原入場戰績回條驗證連線。第 1 房五位玩家的姿態在恢復後重新更新。另通過 72 項本機測試及原單房 9 項回歸、699 格回放。三輪 C／F 的 83 個關閉後快照檔逐檔雜湊相符。
- 功能來源 `773cbdf` 已推送。GitHub Actions 因帳務或支出上限未啟動。Windows 桌面自動化重設後仍在初始化時回報找不到路徑（OS error 3），本次未操作啟動器。跨機、頭盔、MR、廠商硬體及舊 25 席偶發暫停原因仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43365822033)

## 2026-11-13 管理更新延遲與暫停原因驗收

- Windows 原生測試新增 `--delay-management`。單次管理 GET 等待時，原計時器在 1.502 秒觸發 `ManagementWatchdog`。HTTP 503 對照則記下 `ManagementRefresh`。兩場都沿用管理序號 5 恢復，確認遊戲時鐘到期、完整封存及原入場戰績。 [操作方式](CLOCK_RECOVERY.md)
- 兩場各通過 9 項，共核對 1,437 格回放。首輪因測試進行中修改腳本，來源一致性檢查未通過。以固定來源重跑後通過，三輪 C／F 共 119 份關閉後快照檔雜湊相同。另通過 11 項代理測試。 [驗證摘要](../artifacts/native-management-watchdog-validation.json)
- 功能來源 `4c981f7` 已推送，沿用已交付的 Windows 0.50.7 診斷版。GitHub Actions 因帳務或支出上限未啟動。原 25 席偶發暫停原因、跨機、頭盔、MR 場地及廠商硬體仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43364456954)

## 2026-11-13 新版暫停診斷的 25 席丟包複驗

- 用新增暫停標記的 Windows 0.50.7 重跑雙向每 20 個 UDP 封包丟棄 1 個的測試。合併與獨立各 25 個同機模擬玩家，通過 24 項，核對 4,140 格封存回放、6 份 CSV 與 50 份戰績確認。六場均未出現非預期暫停。先前偶發暫停的原因仍待查。 [驗證摘要](../artifacts/authority-diagnostics-25-seat-validation.json)
- 測試工具新增逐場暫停診斷摘要，通過五席實際程序收尾及原 503 測試日誌讀回。兩輪 C／F 共 253 份封存快照檔雜湊相同。另通過 32 項動態驗證與 17 項 UDP 轉送測試。 [操作方式](DESKTOP_EXERCISE.md#五房-udp-丟包驗證)
- 功能來源 `f1796ca` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地及廠商硬體仍待現場驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43363659328)

## 2026-11-13 遊戲伺服器暫停與恢復診斷

- 遊戲伺服器日誌可區分管理更新失敗、管理更新逾時及封存錯誤，並保存恢復序號。Windows 受控 503 複驗通過 9 項。原管理序號 5 暫停後恢復，另在世界發布中斷後核對 772 格封存回放、到期時鐘及原入場的戰績回條。上一輪 25 席合併場的暫停原因仍待查。 [操作方式](CLOCK_RECOVERY.md) · [驗證摘要](../artifacts/management-suspension-diagnostics-validation.json)
- 前兩次故障驗收保留為失敗。測試代理曾拒絕新版戰績回條，加入同場原路由後，管理端收到原入場確認，代理未再拒絕路由。三次 C／F 共 116 個已關閉快照檔雜湊相符。273 項 Unity Editor 與 10 項代理測試通過。
- Windows 伺服器、玩家包與 Quest 開發 APK 完成同源建置及離線一致性驗證。功能來源 `e45f4a2`、測試工具來源 `0826c18` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地及廠商硬體仍待現場驗收。 [離線交付報告](../artifacts/venue-release-control-0.31.170-game-0.50.7-authority-diagnostics.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43363065632)

## 2026-11-13 Windows 0.50.7 五房丟包複驗

- 用已交付的 Windows 0.50.7 與管理 API 0.31.170，在同機用每條連線的上、下行各每 20 個 UDP 封包丟棄 1 個。複驗通過 24 項，獨立與合併各 25 個模擬玩家端，核對 3,995 格回放、六份 CSV、100 次伺服器接受的射擊及 50 份戰績確認。無注入丟包的同機對照通過 22 項及 3,996 格回放。 [重跑方式](DESKTOP_EXERCISE.md#五房-udp-丟包驗證)
- 首輪合併場在第 164 格出現暫停，當下 25 位仍連線。封存有 6 格暫停且在收尾收到 25 份戰績確認。首輪仍未通過，暫停原因待確認。檢查器已加入失敗當下的封包計數及近期畫格摘要。三輪均完成程序及轉送器清理，C／F 共 562 份關閉後快照檔雜湊相同。 [驗證摘要](../artifacts/current-windows-udp-loss-validation.json)
- 通過 17 項 UDP 轉送及 31 項動態驗證測試。功能來源 `d226e6a` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地及廠商硬體仍待現場驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43360669342)

## 2026-11-13 六批收件定位預期批次

- 準備工具會保存每個路徑的預期模式與席數。即使清單缺失，收件報告也可指出預期批次。路徑指向另一批時，會顯示兩者的模式與席數，並拒絕正式驗收。 [操作方式](EXTERNAL_CLIENTS.md#一次查看六批待補件)
- 用 Windows 同機原始封存重驗 18 場啟動、80 份量測及戰績回條。測試副本互換兩份 10 席批次並移除 25 席合併清單，總表正確定位三項問題。舊版總清單的正式輸出逐位元相符。 [本機驗證摘要](../artifacts/staged-venue-expected-stage-validation.json)
- 通過 120 項封存及 12 項 Quest UDP 測試。功能來源 `4a2337c` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地及廠商硬體仍待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43360065275)

## 2026-11-13 自動準備六批場館驗收總清單

- `prepare-venue-stages.py` 可從六份批次清單產生總清單。輸入可任意排序，工具會檢查拓撲、模式與席數組合、重複清單及發行報告的 SHA-256，並可帶入共同的啟動、量測及追蹤驗收條件。 [操作方式](EXTERNAL_CLIENTS.md#一次驗收兩種模式的三個階段)
- 以既有 Windows 同機封存重驗 18 場啟動、80 份連線量測與戰績回條。除了新總清單的 SHA-256，驗收摘要與原結果相同。空白收件資料夾的測試列出第六批 25 席待補，其餘五批通過。 [本機驗證摘要](../artifacts/staged-venue-plan-preparation-validation.json)
- 通過 120 項封存及 12 項 Quest UDP 測試。功能來源 `4405fee` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地及廠商硬體仍待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43359507218)

## 2026-11-13 從原封存準備 Windows 量測驗收清單

- 準備指令可在建立批次清單時填入同時在線時間、Windows 最低回覆數及最高 p95。25 席合併場的缺件測試辨識第 1 房第 1 席，補回原 ZIP 後使用同一清單通過正式驗收。 [操作方式](EXTERNAL_CLIENTS.md#核對五房批次啟動器的原終止報告)
- 從前一輪六批已封存的 Windows 同機資料重建清單，核對 18 場原啟動、80 份連線量測及戰績回條。除新清單及總清單的雜湊外，六批驗收摘要與上一輪相符，237 份原證據雜湊一致。 [本機驗證摘要](../artifacts/staged-venue-prepare-measured-manifest-validation.json)
- 通過 119 項封存及 12 項 Quest UDP 測試。功能來源 `1665dfc` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地與廠商硬體仍待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43358895748)

## 2026-11-13 六批 Windows 啟動與連線量測合併驗收

- 使用管理包 0.31.170 與遊戲 0.50.7，完成 5、10、25 席獨立及合併六批同機排演。總清單核對 18 場原啟動與封存、80 份原連線量測及戰績回條。1,453 項套件檢查通過，含 7,653 格封存回放。三輪皆清理完畢，C／F 共 705 份封存快照檔雜湊相符。 [本機驗證摘要](../artifacts/staged-venue-native-link-and-start-validation.json)
- 六批均通過事先採用的每席至少 28 次回覆及 p95 不超過 40 毫秒門檻。各席均為 30 次回覆，最高 p95 為 38.76 毫秒。總表逐批顯示回覆最少和 p95 最高的席位。測試另以 0 毫秒上限確認六批會被拒絕，並在移除一份 ZIP 的副本指出第六批第 1 房第 1 席。補回原 ZIP 後六批通過。 [六批結果](../artifacts/staged-venue-native-link-and-start/stages-with-start-and-link-criteria-results.json) · [收件方式](EXTERNAL_CLIENTS.md#六批共用-windows-連線量測門檻)
- 通過 118 項封存及 12 項 Quest UDP 測試，舊六批正式摘要重驗後逐位元相符。功能來源 `d8aa725` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43357068140)

## 2026-11-13 六批 Quest 原始日誌缺件與損毀

- 六批收件總表可按房號及席號定位已標示完成但缺少、毀損或無法讀取的 Quest 日誌。兩批測試在同一輪找出五筆問題，補回原檔後核對 80 份模擬回條，正式摘要逐位元一致。既有 Windows 同機六批的 80 份原回條及正式摘要也重驗相符。 [收件方式](EXTERNAL_CLIENTS.md#一次查看六批待補件)
- 通過 118 項封存、12 項 Quest UDP 及 137 項 Windows 原生套件 CLI 檢查。原生五房獨立與合併共核對 501 格封存回放，清理後無遺留程序。使用者關閉擷取視窗後，桌面工具初始化仍回報找不到路徑，圖形介面複驗未開始。 [本機驗證摘要](../artifacts/staged-venue-quest-log-validation.json)
- 功能來源 `5415f2d` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、Quest 3／VIVE XR、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43355909736)

## 2026-11-13 六批 Quest 擷取待補件

- 六批收件總表可列出 Quest 預期席數、報告中標示完成的席數、失敗嘗試數及待補房號與席號。原擷取、部署報告或裝置表缺檔時，回報檔案類型與檔名。收齊後仍由原流程核對日誌內容及伺服器確認。 [收件方式](EXTERNAL_CLIENTS.md#一次查看六批待補件)
- 通過 118 項封存與 12 項 Quest UDP 預檢測試。獨立場與合併場各找出兩席待補，另核對中斷報告及缺檔。初版中斷測試誤帶成功列欄位，修正測試資料後重跑通過。補回原報告後，六批測試資料核對 80 份模擬回條。另重驗既有 Windows 同機六批資料，正式摘要逐位元一致。 [本機驗證摘要](../artifacts/staged-venue-quest-capture-intake-validation.json)
- 功能來源 `e44bf47` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、Quest 3／VIVE XR、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43354942967)

## 2026-11-13 六批共用 Windows 連線量測門檻

- `stages.json` 可一次指定六批共用的最低回覆數與 p95 上限。各批在每項採用總清單與批次清單較嚴的值，收件及正式摘要都會顯示採用的設定。 [驗收方式](EXTERNAL_CLIENTS.md#六批共用-windows-連線量測門檻)
- 通過 117 項封存與 11 項 LAN 預檢測試。六批共 80 席合成量測通過共用門檻，另驗證較嚴的回覆數與 p95 上限各自拒絕相應批次。既有 Windows 同機六批的 80 份戰績回條重驗後，正式摘要逐位元一致。只在總清單副本加門檻時，正確列出六批各自缺少的 5、5、10、10、25、25 席量測。 [本機驗證摘要](../artifacts/staged-venue-shared-windows-link-criteria-validation.json)
- 功能來源 `84e5343` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、Quest 3／VIVE XR、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43354239134)

## 2026-11-13 六批 Windows 連線量測明細

- 批次已設定 `windowsLinkCriteria` 時，收件總表會在 `issues[].windowsLinkMetrics` 提供缺少量測的席位，以及各席回覆數、p95 往返時間和未通過的門檻。散檔、逐席 ZIP 與收件資料夾仍由同一原驗收流程核對，未達門檻時正式驗收仍拒絕。 [收件方式](EXTERNAL_CLIENTS.md#一次查看六批待補件)
- 通過 116 項封存及 11 項 LAN 預檢測試。既有六批 Windows 同機的 80 份戰績回條重驗與原正式摘要逐位元一致。兩份測試副本加上門檻後，總表定位 10 席缺量測，其餘四批仍通過。合成測試另核對回覆數不足、p95 超標及一席缺量測。 [本機驗證摘要](../artifacts/staged-venue-windows-link-metrics-validation.json)
- 功能來源 `d287d32` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、Quest 3／VIVE XR、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43353716836)

## 2026-11-13 六批 Windows 收件的逐席缺件

- 六批收件總表在 `issues[].windowsInbox` 顯示原驗收的 Windows 收件細節，包括預期與實收席數、缺少的房間及席號，以及錯批或重複的 ZIP 檔名。原正式驗收及其退出碼維持。 [收件方式](EXTERNAL_CLIENTS.md#一次查看六批待補件)
- 通過 115 項封存及 11 項 LAN 預檢測試。既有六批 Windows 同機驗收的 80 份戰績回條與 252 個原檔雜湊一致。以 10 席原始日誌和啟動報告製作測試用收件 ZIP，總表同輪辨識缺一席及錯批檔，其他四批保持通過，補件後的正式摘要與副本基準逐位元一致。測試過程修正了初版 fixture 的席位排序與重複包裝。 [本機驗證摘要](../artifacts/staged-venue-windows-inbox-validation.json)
- 功能來源 `337f70e` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、Quest 3／VIVE XR、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43353038158)

## 2026-11-13 全館收尾個人 CSV 內容核對

- 控制台 0.31.170 核對全館與單房席位明細下載的個人 CSV。檔名正確時仍會逐欄比對原場次、遊戲串流、管理與戰鬥封存序號、玩家及七項戰績。瀏覽器攔下三種內容錯置後仍可重試並取回原始檔。 [操作方式](REPORTS.md#從戰績開啟個人回放)
- 通過 1,122 項完整 Chromium、131 項場館專項、107 項 Windows 管理包及 601 項三包整合檢查。獨立與合併各 25 個 Windows 同機模擬玩家，核對 50 份回條及 1,089 格封存回放。兩批的房間 5 逐席核對原下載與個人回放，合併場結束後也重新開啟較早的獨立場原席位。 [本機驗證摘要](../artifacts/venue-verified-debrief-seat-validation.json)
- 功能來源 `483b0f8` 已推送。新版管理包與原 Windows 遊戲包、Quest 0.50.7 APK 通過離線交付一致性核對。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、Quest 3／VIVE XR、MR 場地及廠商硬體仍待實地驗收。 [Windows 管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.170-verified-debrief-seat-win-x64.zip) · [離線交付報告](../artifacts/venue-release-control-0.31.170-game-0.50.7.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43351826877)

## 2026-11-13 最終戰績 CSV 下載核對

- 控制台 0.31.169 會在下載全場、分房或個人 CSV 前，核對原場次、兩個戰鬥與管理序號及每列成績。瀏覽器成功攔下錯場次、錯房、錯玩家及被改動的耗彈值，保留正確檔案的原始位元組。 [操作方式](REPORTS.md#場次與戰績同步)
- 通過 825 項 HTTP、1,118 項完整 Chromium、107 項 Windows 管理包及 543 項三包整合檢查。五房獨立與合併各有 25 個同機模擬玩家，核對瀏覽器實際下載的 6 份最終 CSV、50 列原戰績、50 份伺服器回條及 1,112 格封存回放。第一輪 Windows 整合缺正式啟動回條，保留原結果，改用帶正式回條的啟動流程重跑通過。 [本機驗證摘要](../artifacts/venue-verified-final-reports-validation.json)
- 功能來源 `2cb89ae` 已推送。新版管理包與原 Windows 遊戲包、Quest 0.50.7 APK 通過離線交付一致性核對。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、Quest 3／VIVE XR、MR 場地及廠商硬體仍待實地驗收。 [Windows 管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.169-verified-reports-win-x64.zip) · [離線交付報告](../artifacts/venue-release-control-0.31.169-game-0.50.7.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43350663709)

## 2026-11-13 單席補發採用原公告端點

- 控制台 0.31.168 在五房批次公告後，單席連線檔採用管理服務在同次票券回應提供的 IPv4 與 UDP 埠，手動欄位空白或填錯仍可按原端點補發。來源過期時停用；未使用批次公告的場次仍沿用手動欄位。 [操作方式](EXTERNAL_CLIENTS.md#按房間下載連線檔)
- 0.31.167 對同一測試只回傳票券，缺少端點。新版通過 825 項 HTTP、1,113 項完整 Chromium、107 項 Windows 管理包及 510 項三包整合檢查。原 Unity 程序暫停及恢復時核對端點與名冊，停止後確認阻擋新配票。五房獨立與合併各 25 個同機模擬玩家，核對 10 份原房間 ZIP、50 份戰績回條及 1,143 格封存回放。 [本機驗證摘要](../artifacts/venue-managed-seat-endpoint-validation.json)
- 功能來源 `85ae5d9` 已推送。新版管理包與原 Windows 遊戲包、Quest 0.50.7 APK 通過離線交付一致性核對。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、Quest 3／VIVE XR、MR 場地及廠商硬體仍待實地驗收。 [Windows 管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.168-managed-seat-endpoint-win-x64.zip) · [離線交付報告](../artifacts/venue-release-control-0.31.168-game-0.50.7.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43349394248)

## 2026-11-13 整房配票核對原公告端點

- 控制台 0.31.167 與管理 API 在五房批次公告後，整房 ZIP 使用原 IPv4 與 UDP 埠。來源暫未更新時停用下載，回傳新畫格後可續用原端點與名冊。舊版 0.31.166 對錯誤埠回應 200，新版逐一驗證錯誤位址及埠皆回應 409。 [操作方式](EXTERNAL_CLIENTS.md#按房間下載連線檔)
- 通過 825 項 HTTP、22 項參戰規則、1,111 項完整 Chromium、107 項 Windows 管理包及 495 項三包整合檢查。完整瀏覽器的前兩次測試各在房間狀態斷言讀入新名冊按鈕文字，修正測試擷取範圍後重新通過。五房獨立與合併各 25 個同機模擬玩家，核對 10 份原 ZIP、50 份戰績回條及 1,147 格封存回放。 [本機驗證摘要](../artifacts/venue-managed-room-endpoint-validation.json)
- 新 Windows 管理包、原 Windows 遊戲伺服器及玩家包、Quest 0.50.7 APK 通過離線交付一致性核對。功能來源 `5097c0d`，完整瀏覽器測試來源 `adf0511`。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、Quest 3／VIVE XR、MR 場地及廠商硬體仍待實地驗收。 [Windows 管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.167-managed-room-endpoint-win-x64.zip) · [離線交付報告](../artifacts/venue-release-control-0.31.167-game-0.50.7.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43348051938)

## 2026-11-13 逐房配票端點

- 控制台 0.31.166 在名冊的房間 ZIP 下載按鈕旁顯示目前使用的 IPv4 與 UDP 埠。套用場次公告或編輯手動欄位時會更新顯示，端點無效時停用按鈕。 [操作方式](EXTERNAL_CLIENTS.md#按房間下載連線檔)
- 通過 22 項參戰規則、76 項 Chromium、107 項 Windows 管理包及 495 項三包整合檢查。獨立與合併模式各 25 個 Windows 同機模擬玩家，核對畫面與請求端點、10 份原 ZIP、50 份原連線檔、50 份伺服器戰績回條及 1,060 格封存回放，收尾無遺留程序。 [Windows 管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.166-roster-endpoint-win-x64.zip) · [本機驗證摘要](../artifacts/venue-roster-ticket-endpoint-validation.json)
- 功能來源 `c718d74` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43346170418)

## 2026-11-13 名冊整房連線檔的 Windows 入場與結算

- `--check-roster-room-tickets` 讓 Chromium 逐房使用控制台 0.31.165 的名冊捷徑，將下載的原 ZIP 交給 Windows 玩家包。逐席核對原入場與遊戲端點。 [重跑方式](EXTERNAL_CLIENTS.md#按房間下載連線檔)
- 獨立與合併模式各 25 個同機模擬玩家完成入場與結算。通過 495 項整合檢查及 10 項伺服器包測試。核對 10 份原 ZIP、50 份原連線檔、50 份戰績回條及 1,081 格封存回放，收尾無遺留程序。 [本機驗證摘要](../artifacts/venue-roster-ticket-native-validation.json)
- 驗證來源 `2d91aec` 已推送，控制台來源為 `5fb016d`。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43345337355)

## 2026-11-13 從本房名冊下載整房連線檔

- 控制台 0.31.165 可從指定房間名冊直接下載該房 ZIP，沿用原 IPv4、UDP 埠及名冊再次核對。 [操作方式](EXTERNAL_CLIENTS.md#按房間下載連線檔)
- 通過 75 項 Chromium 及 107 項 Windows 管理包檢查。三種入口均拒絕已簽發但入場被更換的連線檔，重新整理後可從名冊取得新 ZIP。首輪瀏覽器腳本先填位址再切換場次，已修正測試順序並保留原失敗紀錄。 [Windows 管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.165-roster-tickets-win-x64.zip) · [本機驗證摘要](../artifacts/venue-roster-room-tickets-validation.json)
- 功能來源 `5fb016d` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43344967784)

## 2026-11-13 名冊人數與參戰摘要依房間篩選

- 控制台 0.31.164 選定房間後，名冊與有效姿態摘要都使用該房人數。切回全部房間可查看全場，快照效期仍為 1.5 秒。 [操作方式](PLAYER_READINESS.md#五房追蹤驗收開場)
- 通過 22 項參戰規則、44 項 Chromium、107 項 Windows 管理包及 493 項三包整合檢查。Windows 同機獨立與合併模式各有 25 席，十次房間檢查均顯示 5／5 名冊及有效姿態。共核對 50 份戰績回條及 1,007 格封存回放，收尾無遺留程序。 [Windows 管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.164-roster-summary-win-x64.zip) · [本機驗證摘要](../artifacts/venue-roster-summary-validation.json)
- 功能來源 `2a22195` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43344233701)

## 2026-11-13 Windows 原生五房名冊驗收

- 三包整合工具新增 `--check-venue-roster-ui`。Chromium 從控制台 0.31.163 的開場表逐房打開原名冊，比對原入場、席位與遊戲端有效合成姿態，重新整理後核對篩選與原開場目標。 [重跑方式](PLAYER_READINESS.md#五房追蹤驗收開場)
- 獨立與合併模式各用 25 個同機玩家端，通過 493 項整合檢查及 10 項伺服器包測試。50 席瀏覽器名冊與原開場畫格、封存入場一致，另核對 50 份戰績回條及 1,047 格回放。前兩輪分別修正唯讀場地預覽的請求判定與驗收工具的第四版計畫，三輪程序均清理完畢。 [本機驗證摘要](../artifacts/venue-roster-native-validation.json)
- 驗證來源 `44f250d` 已推送，控制台來源為 `8133b22`。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43343389244)

## 2026-11-13 全館開場表直達指定房間名冊

- 控制台 0.31.163 的「查看名冊」會從原開場目標選定房間，顯示該房玩家與即時參戰狀態。合併場可切回全部房間，同一場次重新整理會保留篩選。 [操作方式](PLAYER_READINESS.md#五房追蹤驗收開場)
- 通過 42 項 Chromium 與 107 項 Windows 管理包檢查。合併場及混合 VR／MR 獨立場均核對第 5 房由四席增加至五席。房控測試原先誤以為既有合併名冊會隱藏外房列，已改為核對新捷徑及篩選選項。瀏覽器使用測試姿態與隔離 API。 [Windows 管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.163-venue-roster-final-win-x64.zip) · [本機驗證摘要](../artifacts/venue-opening-roster-validation.json)
- 功能來源 `8133b22` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43342552959)

## 2026-11-13 瀏覽器預檢清單的 Windows 全流程驗收

- 三包整合工具使用控制台 0.31.162 的原始瀏覽器下載，核對啟動計畫、UDP 預檢、Windows 就緒與結束檔。戰後用同一份預檢清單核對伺服器觀察到的各席來源。 [重跑方式](WINDOWS_SERVER_PACKAGE.md#從主控台下載場館計畫)
- 獨立與合併各 25 個同機 Windows 模擬玩家完成入場和結算。581 項套件檢查、26 項 Chromium 檢查及 10 項伺服器包測試通過，共核對 6 組 UDP、50 份戰績回條及 1,024 格封存回放。原下載檔雜湊和啟動回條相符，收尾無遺留程序。 [本機驗證摘要](../artifacts/venue-console-network-native-validation.json)
- 整合驗證來源 `8b6ad24` 已推送，控制台來源為 `eae45ac`。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43341464786)

## 2026-11-13 從控制台下載五房 UDP 預檢清單

- 控制台 0.31.162 可在 Windows 啟動計畫頁選取席位 IPv4 表，依五房獨立或合併模式匯出預檢清單。下載前重新核對場次，席位表留在瀏覽器。 [操作方式](WINDOWS_SERVER_PACKAGE.md#從主控台下載場館計畫)
- 通過 26 項 Chromium、107 項 Windows 管理包及 11 項 LAN 檢查。兩種模式的瀏覽器下載皆與原 Python 清單產生器相符，現有預檢工具可讀取。新版 Windows ZIP 解壓後通過清單與原程序收尾核對。 [Windows 管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.162-venue-network-win-x64.zip) · [本機驗證摘要](../artifacts/venue-console-network-validation.json)
- 功能來源 `eae45ac` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43341121938)

## 2026-11-13 六批驗收定位缺少的原始檔案

- `--inspect-venue-stages` 的 `missingFile` 會顯示原檔類型及檔名。操作員可按批次項次找出缺少的就緒報告、UDP 原檔、回放或玩家日誌。 [操作方式](EXTERNAL_CLIENTS.md#一次查看六批待補件)
- 本機通過 114 項封存及 11 項 LAN 測試。重驗既有六批 Windows 同機的 80 份戰績回條，正式摘要逐位元一致。另用副本一次定位四個缺件，輸出只包含檔名。首次驗證腳本的換行比對已修正為比較收件 JSON 內容，原始清單保持一致。 [本機驗證摘要](../artifacts/staged-venue-missing-files-validation.json)
- 功能來源 `2d824ec` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43340428520)

## 2026-11-13 六批場館驗收收件檢查

- `--inspect-venue-stages` 一次檢查 5、10、25 人的獨立與合併六批資料，列出待補的模式與人數，並指出原清單項次、缺件原因及跨批衝突。 [操作方式](EXTERNAL_CLIENTS.md#一次查看六批待補件)
- 本機通過 114 項測試。重驗既有 Windows 同機六批的 80 份戰績回條，正式驗收摘要與原輸出逐位元一致。另用一份測試清單在同一輪定位缺少清單、重複路徑、缺少啟動回條及誤用其他批次回條，退出碼為 1 並保留完整 JSON。原始清單雜湊一致。 [本機驗證摘要](../artifacts/staged-venue-inspection-validation.json)
- 功能來源 `8f447cf` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43339802247)

## 2026-11-13 六批 Windows 啟動回條驗收

- `stages.json` 可啟用 `requireVerifiedVenueStart`，逐批核對獨立與合併模式的 5、10、25 人啟動回條。摘要保留各批的啟動 ID，並拒絕重複 ID、缺件或其他批次的回條。 [操作方式](EXTERNAL_CLIENTS.md#六批使用各自的-windows-啟動回條)
- 用同一組 Windows 套件依序完成六批同機模擬，通過 1,343 項套件檢查及 113 項封存測試。總清單核對 18 場伺服器封存、80 份戰績回條及 3,057 格回放，六批最短的同時在線區間為 8.562 秒。第六批移除回條或改用第一批回條均遭拒。原檔雜湊一致，三輪收尾皆無遺留程序。 [本機驗證摘要](../artifacts/staged-venue-start-receipts-validation.json)
- 功能來源 `9b687cf` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43338224403)

## 2026-11-13 Windows 五房啟動回條與封存核對

- `start-verified-venue.py --start-receipt` 在正常封存並停止後保存當次預檢、就緒檔與結束檔的雜湊。驗收工具核對相同房間、錄製來源、遊戲程序與 UDP 綁定。可用 `--verified-start-receipt` 將原回條帶入驗收清單。 [操作方式](EXTERNAL_CLIENTS.md#核對-windows-五房啟動回條)
- Windows 同機獨立與合併模式通過 373 項套件檢查及 124 項本機測試。兩種模式各有 5 個模擬玩家，合計 6 組 UDP、10 份戰績回條及 580 格封存回放。新產生的兩份清單重驗結果一致。另確認不同預檢雜湊及被改寫的就緒程序編號會遭拒，原檔保持一致。 [本機驗證摘要](../artifacts/venue-start-receipt-validation.json)
- 功能來源 `736d29b` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43337709588)

## 2026-11-13 Windows 五房開場前重驗 UDP

- 新增 `start-verified-venue.py`，重驗同一份原計畫、網路清單及雙端 UDP 報告後才啟動現有 Windows 套件。缺件、逾時、未完成或計畫有變時，在建立遊戲工作目錄前退出。 [啟動方式](WINDOWS_SERVER_PACKAGE.md#以-udp-預檢報告啟動五房)
- 首輪在限制 `PATH` 的環境找不到 Windows PowerShell，已修正並保留原失敗及清理紀錄。重跑通過 369 項套件檢查，獨立與合併各 5 個同機 Windows 模擬玩家，合計 6 組原 UDP 綁定、10 份戰績回條及 583 格完整回放。另通過 146 項本機測試。用逾時原報告確認拒絕，另以 Windows 測試程序確認強制結束命令後，其啟動器與子程序會退出。 [本機驗證摘要](../artifacts/venue-verified-start-validation.json)
- 功能來源 `f30139f` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43336832354)

## 2026-11-13 五房 UDP 報告收件配對

- `--inbox` 可依遊戲端點、來源與交換雜湊配對原始監聽和探測報告，列出缺少對端、重複及無法讀取的檔名。完整報告可納入封存驗收，未完成報告可接續補件。 [收件方式](EXTERNAL_CLIENTS.md#從資料夾配對-udp-報告)
- Windows 本機通過 11 項 LAN 預檢、12 項 Quest UDP 及 113 項封存測試。以原檢查時間及另存副本的原始位元重驗兩種模式，兩批均先定位缺件，再補交雙端報告，收件與封存摘要均和原驗收一致，合計 50 份玩家 ZIP、6 組 UDP 及 2,502 格回放。 [本機驗證摘要](../artifacts/venue-udp-inbox-validation.json)
- 功能來源 `3583e49` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43335417400)

## 2026-11-13 五房 UDP 預檢補測

- 全館預檢可用 `--retry-report` 重新核對原本通過的雙端資料，並只提交缺漏來源。重試沿用同一份網路清單和原啟動資料，並檢查原檔雜湊、重複來源與既有時限。 [補測方式](EXTERNAL_CLIENTS.md#補測未完成的全館-udp-預檢)
- 本機通過 113 項封存、10 項 LAN 預檢與 12 項 Quest UDP 測試。用原檢查時間重驗 Windows 同機資料，獨立模式保留四組來源後補齊第五組，合併模式補齊唯一一組。兩種模式的收件與封存摘要和原驗收一致，涵蓋 50 份原玩家 ZIP、6 組 UDP 及 2,502 格封存回放。 [本機驗證摘要](../artifacts/venue-udp-resume-validation.json)
- 功能來源 `b89ff79` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43334562104)

## 2026-11-13 五房重連來源 IPv4 核對

- 封存與 Windows 收件可使用原開場網路清單和 `reconnectSourcePlan`，逐條核對同一程序重連前後的 IPv4、舊連線釋放、原入場與戰績確認。開場 UDP 預檢沿用第一個來源。混合場的 Quest 擷取沿用原 PID。 [操作方式](EXTERNAL_CLIENTS.md#核對重連時變更的-ipv4)
- 通過 113 項封存、10 項 LAN 預檢與 12 項 Quest UDP 測試。重驗既有 Windows 同機兩種模式的 50 份玩家 ZIP、52 條連線及 3,361 格封存回放。另在兩份伺服器日誌副本各改一筆最終來源，未列入清單時均在收件遭拒，提供相符清單後通過。原封存資料保持一致。 [本機驗證摘要](../artifacts/venue-reconnect-source-validation.json)
- 功能來源 `d019474` 已推送。GitHub Actions 因帳務或支出上限未啟動。實際換網卡重連、Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43333234951)

## 2026-11-13 Windows 收件核對原程序重連

- 開啟 `verifyReconnectHistory` 後，Windows 收件就會檢查各 ZIP 的原程序啟動、歷次 UDP 來源及舊連線釋放順序。重複認領同一歷史連線時，兩份檔案都會列為待補件。產生場館清單可加 `--verify-reconnect-history`。 [操作方式](EXTERNAL_CLIENTS.md#核對原程序的重連歷程)
- 本機通過 111 項封存、10 項 LAN 預檢及 12 項 Quest UDP 測試。重驗既有 Windows 同機獨立與合併的 50 份原玩家 ZIP、52 條連線及 3,361 格封存回放。兩種模式的測試副本各移除一筆舊連線釋放紀錄，收件均指出第 5 房第 2 席及對應檔案。原資料及完整驗收結果一致。 [本機驗證摘要](../artifacts/windows-inbox-reconnect-validation.json)
- 功能來源 `4b18ed3` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43332405464)

## 2026-11-13 以原網路清單核對封存席位

- 全館收件及封存驗收可引用同一份五房網路清單，依原場次、席位、封存端點及伺服器戰績確認比對 Windows 與 Quest 的 UDP 來源。新版全館 UDP 預檢回條保留清單雜湊。Windows 收件會逐檔標示不符及待補件席位。 [操作方式](EXTERNAL_CLIENTS.md#用原網路清單核對封存席位)
- 本機通過 110 項封存、10 項 LAN 預檢及 12 項 Quest UDP 測試。以原始啟動與預檢資料重建清單，重驗既有 Windows 同機兩種模式的 50 份玩家 ZIP、6 組 UDP 預檢與 2,502 格封存回放，原資料及其餘驗收結果一致。另確認位址錯配及封存端點不符會被拒絕。 [本機驗證摘要](../artifacts/venue-network-seat-readback-validation.json)
- 功能來源 `a0fe5a6` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43331355845)

## 2026-11-13 Windows 五房開場回放原生驗收

- 新的三包驗收選項會等原伺服器退出，再由封存世界日誌定位原開場與首個執行畫格。Chromium 在管理包 0.31.161 上實際切換兩格，逐場核對原錄製、房間與鏡頭，並與離線封存驗收核對同一開場指令及兩個原畫格。 [重跑方式](WINDOWS_SERVER_PACKAGE.md#三個可攜包整合驗證)
- Windows 遊戲 0.50.7 原包完成 506 項整合檢查，五房獨立及合併各有 25 個同機玩家程序。六場雙封存共 833 格完整回放，核對 50 份玩家戰績及伺服器確認、13 份 CSV。收尾後無測試場次或程序殘留，C 槽與 F 槽的 12 份原世界及戰鬥日誌雜湊一致。另通過 10 項 Python 封裝測試。 [本機驗證摘要](../artifacts/native-venue-opening-replay-validation.json)
- 驗收來源 `32ca6df` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43329751026)

## 2026-11-13 比較原開場與首個執行畫格

- Windows 管理包 0.31.161 的全館收尾回放可在原準備畫格與第一個已套用開場指令的有效執行畫格間切換，並保留房間及鏡頭。適用於追蹤開場與有效姿態開場，查詢限於原保存範圍。 [回放操作](SESSION_CLOSURE.md#比較準備與執行畫格)
- 解壓核對 564 筆清單。Windows 管理啟動器 107 項及解壓包 Chromium 專測 81 項通過，涵蓋合併與獨立房、同一錄製多一格準備畫格、錯誤回應與房控權限。瀏覽器專測使用隔離管理服務及測試姿態。 [管理包](WINDOWS_CONTROL_PACKAGE.md)
- 完整本機回歸通過 1,101 項領域、825 項 HTTP、138 項世界串流、7 項 Python 封裝、113 項 Node 及 1,087 項 Chromium 檢查。 [瀏覽器測試](../tests/browser/full-tracking-begin-browser.cjs)
- 使用原 Windows 同機五房獨立及合併的 6 份封存日誌共 923 格，在記憶體 SQLite 執行新版查詢。六場的首個執行格均與原日誌分析一致。 [原生場次紀錄](#2026-11-10-五房-25-席有效姿態開場)
- 功能來源 `a8e9e62` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43328104932)

## 2026-11-13 從原封存核對 Quest 開場追蹤

- 開場前的 Quest 追蹤回條保留原部署 ZIP 雜湊，以及各席場次、世界序號、管理序號與擷取時間。封存驗收會重讀原 `Preparing` 畫格，核對同一房間的玩家已連線、存活並使用追蹤姿態。各場摘要提供可定位回放的原畫格號。 [封存方式](EXTERNAL_CLIENTS.md#核對-quest-開場追蹤回條)
- Windows 本機通過 54 項部署及 109 項封存測試。五房獨立與合併的各 25 席測試資料均完成清單準備與封存核對，錯批、開場後才取樣、逾期、錯格及合成姿態均遭拒。既有 Windows 同機 50 份玩家 ZIP、6 組 UDP 預檢及 2,502 格回放重驗一致。 [測試](../tests/test_field_results.py)
- 功能來源 `6ad0e3b` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43326880211)

## 2026-11-13 Quest 開場追蹤核對原部署

- 開場前的 Quest 追蹤核對可指定完整部署報告。工具先比對原 ZIP 雜湊、原裝置對照表，以及逐席的場次、玩家、入場名額與端口，然後讀取管理服務目前的追蹤狀態。就緒或等待中的回條均保存原部署報告的 SHA-256。 [操作方式](QUEST3.md#核對本次部署與追蹤席位)
- Windows 本機通過 54 項部署測試及 108 項封存測試。兩席 MR 模擬確認同輪就緒、MR 來源尚未就緒，以及 10 種錯批或參數組合在連線前遭拒。追蹤查詢全程未呼叫 ADB。 [測試](../tests/test_quest_deploy.py)
- 功能來源 `4ef2787` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43325247448)

## 2026-11-13 Quest UDP 預檢核對原 Windows 批次

- Quest 批次預檢可在呼叫 ADB 前核對原 Windows 啟動計畫、成功預覽與網路清單。報告保留兩份原檔的路徑與雜湊。重試須沿用原檔，全館核對及封存驗收可直接重讀這項證據。 [操作方式](QUEST3.md#預檢前核對-windows-原啟動批次)
- 12 項 Quest UDP、10 項 LAN 預檢及 108 項封存測試通過。同機 Java 與 PowerShell 兩席 UDP 往返通過全館核對，重試拒絕沿用原埠的新場次，亦拒絕省略原啟動證據。既有 Windows 同機 50 份玩家 ZIP、6 組 UDP 預檢及 2,502 格回放重驗一致。 [驗證紀錄](../artifacts/quest-udp-launch-binding-validation.json)
- 功能來源 `0f7743f` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43324108182)

## 2026-11-13 從原預覽產生五房 UDP 網路清單

- `prepare-venue-network-plan.py` 先比對原 Windows 啟動計畫及成功預覽的模式、場次、任務版本、序號與端點，再用全館席位 IPv4 產生原格式網路清單。可按階段指定每房席數，並使用原裝置表產生 Quest 專用子集。 [操作方式](EXTERNAL_CLIENTS.md#從原啟動預覽產生網路清單)
- 10 項 LAN 預檢、11 項 Quest UDP 及 108 項離線封存測試通過。新清單通過原 PowerShell 雙端 UDP 核對，Quest 子集以同機 Java 探測程式完成兩席往返。既有 Windows 獨立及合併各 25 席的網路清單重建一致，原啟動檔案及證據雜湊一致。 [驗證紀錄](../artifacts/venue-network-plan-preparation-validation.json)
- 功能來源 `68115f7` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43322696693)

## 2026-11-13 五房配置檔平面圖對照

- Windows 管理包 0.31.160 可在五房配置檔預覽中選房，以相同比例對照目前準備與檔案版本的保存物件、角度、出生位及配置問題。對照保留原準備和編輯草稿。 [操作方式](MISSION_VERSIONS.md#在開場前保存五房任務配置)
- 首次瀏覽器檢查等待目前房間的出生位逾時。修正平面圖在場地回報尚未取得時的渲染後，來源與解壓版各通過 81 項五房準備檢查，涵蓋原座標、窄畫面與換檔後晚到的回覆。完整 Chromium 1,078 項、Node 113 項及 Windows 管理包 107 項通過。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [驗證紀錄](../artifacts/venue-mission-maps-160-validation.json)
- 功能來源 `916648a` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43320747293)

## 2026-11-13 任務回放循環播放片段

- Windows 管理包 0.31.159 在「指定回放片段」提供「循環播放片段」。每輪都核對原起訖與串流終點，再回到起點。播放沿用所選房間、鏡頭及個人檢討範圍，支援暫停及取消循環。 [操作方式](WORLD_RECORDING.md#重看指定片段)
- 來源與解壓版各通過 137 項觀戰與回放檢查。瀏覽器核對了原範圍的第二輪、暫停保留畫格、取消後停在原終點，以及缺少終點確認時停止重播。完整 Chromium 1,070 項、Node 113 項與 Windows 管理包 107 項通過。瀏覽器使用真管理服務與 .NET 轉送的模擬錄製。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [驗證紀錄](../artifacts/world-clip-loop-159-validation.json)
- 功能來源 `d34b46d` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43318810676)

## 2026-11-13 合併下載場館驗收與全員回條

- 管理包 0.31.158 在所選原收尾批次提供「下載驗收 ZIP 與全員回條」。資料齊備及名冊全數確認後，ZIP 會保留原封存內容並內附 `debrief-receipts.json`。離線清單產生器及驗收工具可直接使用。 [收尾操作](SESSION_CLOSURE.md#下載驗收-zip-與全員回條)
- 1,101 項核心、825 項 HTTP、138 項世界串流、108 項離線封存與 113 項 Node 測試通過。來源與解壓版各通過 127 項場館瀏覽器檢查，下載內容逐位元核對。Windows 可攜管理包通過 107 項檢查。既有 Windows 同機六批重新封裝後驗證 80 筆原回條，摘要與原紀錄一致。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [驗證紀錄](../artifacts/venue-field-receipts-158-validation.json)
- 首次完整 Chromium 回歸在混合場開場等待回應逾時，保留原紀錄。同一版本重跑通過 1,067 項。功能來源 `3e70369` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43315987891)

## 2026-11-13 統一六場追蹤及遊戲射擊驗收

- 5、10、25 人的獨立與合併驗收可在總清單一次指定全體追蹤與每席封存射擊。兩項皆啟用時，逐批核對同一段共同執行區間。各批有更長時間門檻時沿用其設定。 [操作方式](EXTERNAL_CLIENTS.md#統一核對追蹤及遊戲射擊)
- 107 項封存測試通過。六批受控案例有 80 筆伺服器確認，拒絕缺原戰鬥檔、模擬 OpenXR 或少一席遊戲射擊的證據。既有 Windows 同機六場重驗 18 份世界、18 份戰鬥封存及 80 筆確認，原摘要逐欄一致。新追蹤與射擊門檻分別拒絕未達條件的同機舊場次。 [驗證紀錄](../artifacts/venue-staged-roster-validation.json)
- 功能來源 `07000b5` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43314679173)

## 2026-11-13 從原部署 ZIP 驗收 MR 校正

- 場館驗收清單可直接引用原 MR 或混合部署 ZIP。清單產生器和完整驗收都會核對五房原場次、MR 校正檔 SHA-256，以及混合包的房間模式和 UDP 端點。 [操作方式](EXTERNAL_CLIENTS.md#核對-mr-校正封存)
- 105 項封存、54 項 Quest 部署及 8 項 UDP 測試通過。獨立混合場、獨立全 MR 及合併 MR 的受控案例均與逐房提供校正檔的結果一致。另重驗既有同機 50 份 Windows 玩家 ZIP、6 組 UDP 預檢及 2,502 格回放，摘要與原紀錄一致。 [驗證紀錄](../artifacts/venue-alignment-bundle-validation.json)
- 功能來源 `219f5e1` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43313601106)

## 2026-11-13 產生 Windows 與 Quest 混合驗收清單

- `prepare-venue-field-manifest.py` 可同時帶入原 Quest 擷取、部署、裝置表、網路計畫及 Windows 收件資料夾。產生前核對 Quest 原日誌、戰績回條、來源、部署與席位。Windows ZIP 未齊時可先產生清單，收件後使用原清單完成驗收。 [操作方式](EXTERNAL_CLIENTS.md#產生-windows-與-quest-混合驗收清單)
- 103 項封存、54 項 Quest 部署及 8 項 UDP 測試通過。獨立和合併的受控案例各使用 5 份 Quest 日誌及 20 份 Windows 玩家證據，驗證第 20 份 Windows ZIP 晚交後可直接完成，錯誤來源或重疊席位則不產生清單。原 Windows 同機封存另重驗 50 份玩家 ZIP、6 組 UDP 預檢及 2,502 格回放，與原驗收摘要一致。 [驗證紀錄](../artifacts/mixed-venue-manifest-validation.json)
- 功能來源 `1ebaa60` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43312258682)

## 2026-11-13 Quest 封存一起核對裝置表與來源 IPv4

- 封存清單可同時引用原 Quest 裝置表與網路計畫。驗收依擷取引用的各份部署報告重算原席位和 ADB 標籤指紋，並核對伺服器記錄的來源 IPv4。也修正有擷取引用時，摘要誤以部署報告雜湊取代 APK 雜湊的問題。 [操作方式](EXTERNAL_CLIENTS.md#以原-quest-裝置對照表驗收收尾)
- 102 項封存及 54 項 Quest 部署測試通過。獨立及合併受控案例各用 5 個 Quest 席位和 20 個 Windows 席位，分別核對兩份原部署與裝置表指紋。錯誤 ADB 標籤或來源 IPv4 都會拒絕。兩種模式的摘要均對上既有 Quest 0.50.7 APK 的實際 SHA-256。 [驗證紀錄](../artifacts/quest-device-map-network-validation.json)
- 功能來源 `fdb282f` 已推送。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43310847938)

## 2026-11-13 Quest 日誌擷取核對原部署裝置

- 批次擷取可使用 `--deployment-report`，核對原部署 ZIP、裝置清單、已驗證的 APK 及原入場席位。擷取開始與交付前各核對一次 ADB 裝置識別。若交付前識別改變，保留 `.partial`。擷取重試及封存驗收沿用原部署報告的 SHA-256。 [擷取方式](QUEST3.md#一次擷取五房-quest-日誌)
- 54 項部署及 101 項封存測試通過。實際 PowerShell 部署工具透過模擬 ADB 完成三席重試，Python 隨後核對原報告並保存三份逐位元一致的模擬日誌。受控測試拒絕錯裝置、交付前裝置更換、不同裝置清單與改過的原部署檔。獨立及合併封存皆核對擷取引用。 [驗證紀錄](../artifacts/quest-capture-deployment-validation.json)
- 功能來源 `fdd38a8` 已推送。既有 Quest 0.50.7 APK 與管理包 0.31.157 離線發行核對通過。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人、MR 場地及廠商硬體仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43309910705)

## 2026-11-13 按電腦標籤核對 Windows 席位來源

- 場館可在收件清單加入 `windowsStationAddresses`，把原 Windows 席位對照表中的電腦標籤與預期 IPv4 一起核對。工具使用伺服器原已確認戰績連線的來源。來源不符時會列出檔名、缺件席位及電腦標籤。成功摘要保存位址表 SHA-256 與通過席位數。99 項封存及 8 項 UDP 測試通過，涵蓋受控兩位址互換、缺少標籤與重複標籤。 [操作方式](EXTERNAL_CLIENTS.md#核對-windows-席位的來源-ipv4)
- 沿用原 Windows 同機封存生成獨立與合併清單，各 25 份玩家 ZIP 通過。共核對 6 組 UDP 預檢及 2,502 格回放。兩種模式各修改第五房第五席的預期位址後，舊版仍收 25 席，新版均只收 24 席並拒絕完整驗收。原玩家 ZIP 雜湊一致。 [驗證紀錄](../artifacts/windows-station-address-validation.json)
- 功能來源 `d722ec0` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、Quest 3、VIVE XR、MR 場地及廠商硬體仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43308542651)

## 2026-11-13 在五房準備時核對初始敵軍

- 管理包 0.31.157 在各房選項、配置檔預覽、建立確認和回條列出原任務版本的敵軍數量、行為和自動攻擊。回條若含不同的原保存設定，會保留前一份已確認結果，等候以原請求重試。來源與解壓包各通過 73 項 Chromium 專項。舊版缺少逐房摘要的反例已保存，初版候選的窄螢幕欄位已調整為表格內捲動。 [逐房設定](MISSION_VERSIONS.md#逐房指定任務版本)
- 最終 Windows 包通過 383 項同機整合。獨立及合併各使用 25 個模擬玩家端，瀏覽器選用的五份獨立版本及原合併版本均與遊戲執行格的初始敵軍設定一致。六場雙封存保留 814 格回放、6 份 CSV、50 筆伺服器戰績確認。清理後原生及管理 C／F 快照分別有 215 和 18 個非資料庫檔案雜湊一致。 [驗證紀錄](../artifacts/venue-mission-enemies-0.31.157-validation.json)
- 解壓核對 564 筆清單，並通過 825 項 HTTP 與 107 項管理包檢查。離線發行用原帶收據的 Windows 和 Quest 0.50.7 套件，確認 APK v2 簽章。功能與畫面修正已推送，最終包來源 `63e79e7`。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地及廠商硬體仍待驗收。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [發行核對](../artifacts/venue-release-0.50.7-control-0.31.157.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43306891267)

## 2026-11-13 從原封存產生五房驗收清單

- `prepare-venue-field-manifest.py` 從管理驗收 ZIP 與 Windows 批次終止報告產生 `venue.json`。它逐場核對來源、UDP 端點、原名冊、伺服器日誌及封存的世界與戰鬥紀錄。可帶入 Windows 玩家收件資料夾、發行報告及 UDP 預檢。搬移後以 `--server-work-root` 指定原房間資料夾。98 項封存及 8 項 UDP 測試通過。 [準備方式](EXTERNAL_CLIENTS.md#核對五房批次啟動器的原終止報告)
- 沿用前輪 Windows 0.50.7 的同機原件，在原工作目錄與搬移後目錄分別產生獨立及合併清單。92 份搬移檔案的雜湊一致，整批再從 F 槽複製到 C 槽後，兩種模式的離線摘要仍完全相同。重驗核對 50 份玩家 ZIP、6 組 UDP 預檢及 2,502 格回放。兩種模式均拒絕其他批次報告、缺原日誌的目錄和覆寫既有清單。 [驗證紀錄](../artifacts/venue-manifest-preparation-validation.json)
- 功能來源 `8b50bc4` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、Quest 3、VIVE XR、MR 場地及廠商硬體仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43305222123)

## 2026-11-13 Windows 玩家 ZIP 收件時核對封存戰績

- Windows 收件與完整驗收共用玩家戰績檢查。每份 ZIP 的最終戰績、管理序號、世界回放序號與戰鬥事件序號都要對上管理端原封存。不符的檔名列在 `issues`，尚無有效 ZIP 的席位留在 `missingSeats`。舊版在兩種模式各錯收四種受控修改，修正後 98 項封存及 8 項 UDP 測試通過。 [收件操作](EXTERNAL_CLIENTS.md#按收件資料夾找缺件及錯批)
- Windows 0.50.7、管理包 0.31.155 與玩家啟動器 1.14.1 同機通過 583 項。兩種模式各收 25 份原始 ZIP，並以同一份 Windows 發行報告驗證。六場雙封存保留 2,502 格回放、6 份 CSV、50 筆伺服器戰績確認及 1,500 筆成功量測回覆。離線重驗時，修改第五房第五席的血量或回放序號後，舊版仍各收 25 席，新版四次均只收 24 席並標出檔名。原 ZIP 雜湊保持一致。清理後 C／F 的 372 個非資料庫檔案雜湊一致。 [驗證紀錄](../artifacts/windows-inbox-seal-validation.json)
- 功能來源 `45dae08` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、Quest 3、VIVE XR、MR 場地及廠商硬體仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43303750096)

## 2026-11-13 以五房批次終止報告完成場館封存驗收

- 場館驗收可直接讀取 Windows 批次啟動器的原終止報告，依原場次 ID 與管理端保存的批次識別核對每房來源、端點和封存。原計畫與預覽即使彼此相符，場次序號若與管理端保存的來源附掛序號不同也會拒絕。舊版封存工具用原全館報告會因缺少逐場欄位而中止。新版 97 項場館封存及 8 項 UDP 測試通過。 [驗收方式](EXTERNAL_CLIENTS.md#核對五房批次啟動器的原終止報告)
- Windows 0.50.7 與管理包 0.31.156 同機通過 517 項。獨立及合併各連上 25 個模擬玩家端，兩份管理 ZIP 和原終止報告可離線重驗，與逐場管理 ZIP 的摘要一致。六場雙封存合計有 6 組 UDP 預檢、18 筆認證往返、962 格回放、6 份戰績 CSV 及 50 筆伺服器戰績確認。兩種模式均以原附掛序號拒絕被替換的計畫和預覽。程序清理後 C／F 有 218 個非資料庫檔案雜湊一致。 [驗證紀錄](../artifacts/venue-batch-field-validation.json)
- 功能來源 `d1eb83f` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、Quest 3、VIVE XR、MR 場地及廠商硬體仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43302502073)

## 2026-11-13 核對五房 UDP 預檢的原啟動計畫

- UDP 預檢可同時讀取原啟動計畫及 `--venue-check` 預覽。場次、任務版本、場次序號及端點須逐房相符。封存驗收會重讀原計畫與預覽、驗證檔案雜湊，並核對實際封存場次與端點。8 項 UDP 及 96 項場館驗收測試通過，涵蓋原檔變動和封存資料不符。 [操作方式](EXTERNAL_CLIENTS.md#開場前核對五房-udp-報告)
- Windows 0.50.7 與管理包 0.31.156 同機通過 435 項。獨立及合併各有 25 個模擬玩家端，六組原 UDP 報告共 18 筆認證往返，均與 Unity 實際綁定位址、埠及時間相符。兩種模式均拒絕錯誤埠和端點相同但場次不同的預覽。六場雙封存保留 886 格完整回放、6 份 CSV 及 50 份戰績回條。程序清理後 C／F 有 215 個非資料庫檔案雜湊一致。 [驗證紀錄](../artifacts/udp-launch-plan-validation.json)
- 首輪 Windows 測試用的第一版啟動計畫缺少序號，已保留失敗及清理紀錄。改用第四版測試計畫後完成兩種模式。功能來源 `cdbeb0d` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、Quest 3、VIVE XR、MR 場地及廠商硬體仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43301128994)

## 2026-11-13 匯出五房戰績合計

- 管理包 0.31.156 可從原全館收尾批次下載各房及全批戰績合計 CSV。來源及解壓包各通過 17 項 Chromium 專項，涵蓋待封存時不提供下載、空房保留、加權命中率、房間重用後的歷史下載，以及拒絕批次或數值不符的 CSV。 [分房戰績](REPORTS.md#在全館收尾比較分房戰績)
- Windows 0.50.7 同機通過 435 項。獨立及合併各有 25 個模擬玩家端。兩份合計均含五房及全批共六列，逐欄對上原封存戰績。原逐玩家匯出仍有 11 份 CSV，六場雙封存共 1,564 格完整回放及 50 份伺服器戰績回條。原生及管理 C／F 快照分別有 217、18 個非資料庫檔案雜湊相同。 [驗證紀錄](../artifacts/venue-score-summary-0.31.156-validation.json)
- 解壓核對 564 筆清單，另通過 825 項 HTTP 與 107 項管理包檢查。離線發行核對沿用 Windows／Quest 0.50.7 及 Windows 玩家啟動器 1.14.1。功能來源 `a059e17` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地及廠商硬體仍待驗收。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43298213532)

## 2026-11-13 硬體排演拒絕倒退的管理回覆

- 硬體模擬器 0.2.14 會在同一輪房間排演中核對管理序號及檢查時間。任一值倒退時，該房取消待確認批次並保存原已確認回饋。受控測試中，舊版讀過序號 72 後收到序號 71，仍把待確認批次計入確認。新版在獨立及合併排演共四個反例拒絕序號或時間倒退。兩種模式的第五房均在原連線確認新的回饋。 [操作方式](HARDWARE.md#一次啟動與停止五房排演)
- 1,101 項核心、38 項離線及 80 項即時模擬檢查通過。解壓後核對 8 個檔案，離線範例輸出與原測試逐位元一致。Windows 0.50.7 搭配管理包 0.31.155 完成 420 項同機整合。獨立與合併各 25 個模擬玩家端，十房次共 216 筆模擬確認、50 份原戰績回條、11 份 CSV 及 1,616 格完整回放。六場完成雙封存，程序清理後 C／F 快照有 225 個非資料庫檔案雜湊相同。 [驗證紀錄](../artifacts/hardware-authority-continuity-0.2.14-validation.json)
- 來源 `080e716` 已推送。GitHub Actions 因帳務或支出上限未啟動。廠商設備、跨機 25 人、頭盔及 MR 場地仍待驗收。 [套件資料](HARDWARE_SIMULATOR.md) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43296776903)

## 2026-11-13 玩家視窗在任務中顯示量測結果

- Windows 玩家啟動器 1.14.1 可在任務仍執行時顯示本次量測已完成或提早停止，並列出回覆、逾時和中斷。重新入場時會提示先前量測未涵蓋目前連線。關窗後若 Windows 回報紀錄檔占用，視窗會短暫等候再讀取原檔。44 項啟動器檢查、21 項 WinForms 發行核對及 96 項場館封存測試通過。解壓清單 331 個檔案中有 329 個與 1.13 雜湊相同。 [玩家操作](WINDOWS_PLAYER_PACKAGE.md#依場館發行報告核對玩家包)
- Windows 0.50.7 同機整合通過 518 項。獨立與合併各 25 個模擬玩家端，其中各一席用 WinForms 啟動實際圖形玩家。兩席均在主控結束任務前顯示原 30 筆量測。驗收程式在兩個原遊戲程序退出後短暫占用日誌，確認啟動器等候，並在釋放後將原日誌與量測匯入 ZIP。兩批共 50 份原 ZIP 通過收件與封存核對，1,500 筆量測中有 1,500 筆收到回覆。六場雙封存共 3,733 格回放、6 份 CSV 及 50 筆戰績回條。清理後 C／F 快照有 384 個非資料庫檔案雜湊相同。 [驗證紀錄](../artifacts/player-link-live-1.14.1-validation.json)
- 早期驗收因測試讀取 .NET Framework 陣列型別、取錯場次狀態欄位及未更新斷言數而中止。修正後，1.14 的合併場也曾在圖形程序正常關窗後產生缺雜湊的退出報告，未建立原 ZIP。受控測試重現 Windows 讀取分享衝突，再用 1.14.1 驗證短暫占用解除後正常匯出。原合併場的占用來源未確認。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地及廠商硬體仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43294374893)

## 2026-11-13 即時觀戰定位最近設定

- 管理包 0.31.155 可從即時觀戰定位最近的環境、場次階段或敵軍設定。回看固定於按下時的保存尾端，沿用房間和鏡頭，並可返回同場的最新快照。來源及解壓包各通過 38 項 Chromium 專項，核對原階段跳轉、找不到變更時保留原格及返回後取得新格。即時事件原流程另通過 17 項。 [操作說明](WORLD_RECORDING.md#從即時觀戰定位最近設定)
- Windows 0.50.7 同機 36 項通過。合併與獨立各使用 25 個模擬玩家端，六場執行中各查一次暴風雨與濃霧設定。12 次查詢均與 2,965 格原封存回放中對應的首次變更一致。封存保留 6 份 CSV 及 50 筆伺服器戰績確認。停止後原生和管理 C／F 快照分別有 165、18 個非資料庫檔案一致。 [驗證摘要](../artifacts/live-policy-review-0.31.155-validation.json)
- 來源通過 138 項世界串流檢查。解壓包通過 825 項 HTTP 及 107 項管理包檢查，清單共 564 筆。離線發行核對沿用 Windows 與 Quest 0.50.7 和 Windows 玩家啟動器 1.13。功能來源 `3ad47de` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地及廠商硬體仍待驗收。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43290280041)

## 2026-11-13 跳到上一筆或下一筆回放設定

- 管理包 0.31.154 可從目前回放畫格向前或向後搜尋符合目前種類的設定，並保留房間與鏡頭。來源與解壓包各通過 34 項瀏覽器專項，涵蓋從原暴風雨畫格的前後兩側跳到同一格、無符合結果時留在原格。136 項世界串流檢查包括 1,101 格的錄製，核對兩個方向都能跨過無符合畫格的搜尋頁。 [操作說明](WORLD_RECORDING.md#查閱錄製中的設定切換)
- Windows 0.50.7 同機通過 36 項。獨立及合併各 25 個模擬玩家端，六場的 12 次方向查詢均與 2,923 格完整回放中的原設定變更相符。六場封存保留 6 份 CSV 及 50 筆伺服器戰績回條。程序停止後，原生與管理 C／F 快照分別有 165、18 個非資料庫檔案一致。 [驗證摘要](../artifacts/replay-policy-neighbor-0.31.154-validation.json)
- 解壓核對 564 筆清單，另通過 825 項 HTTP 及 107 項管理包檢查。離線核對沿用 Windows 與 Quest 0.50.7 和 Windows 玩家啟動器 1.13。功能來源 `0aec973` 已推送，GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地及廠商硬體仍待驗收。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43288283108)

## 2026-11-13 依設定種類查閱回放畫格

- 管理包 0.31.153 可在暫停回放中依環境、場次階段、敵軍策略、敵軍增減或首格狀態查閱原保存畫格。點選結果時，控制台核對原設定與名單再跳轉。來源與解壓包各通過 31 項瀏覽器專項，涵蓋篩選出原暴風雨畫格、錯誤的閃電設定保留原畫面，以及更換種類時清除原清單與游標。 [操作說明](WORLD_RECORDING.md#查閱錄製中的設定切換) · [原畫格結果](../artifacts/console-policy-filter-153-package/world-policy-environment-only.png)
- Windows 0.50.7 同機通過 36 項。獨立及合併各 25 個模擬玩家端，六場各經歷暴風雨夜晚與濃霧白天。篩選回傳的 12 格逐一對上 2,862 格完整回放中的原時間與設定。六場封存保留 6 份 CSV 及 50 筆伺服器戰績回條。程序停止後，原生與管理 C／F 快照分別有 165、18 個非資料庫檔案一致。 [驗證摘要](../artifacts/replay-policy-filter-0.31.153-validation.json)
- 解壓核對 564 筆清單。133 項世界串流、825 項 HTTP 及 107 項管理包檢查通過。離線核對沿用 Windows 與 Quest 0.50.7 和 Windows 玩家啟動器 1.13。功能來源 `fa9dc4c` 已推送，GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地及廠商硬體仍待驗收。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43286292835)

## 2026-11-13 開場前核對五房保存環境

- 管理包 0.31.152 在各房任務選項、配置檔預覽、建立確認及已確認的五房建立結果顯示初始天氣、日夜與閃電。來源與解壓包各通過 69 項 Chromium 專項，涵蓋歷史與目前版本並排、保存環境欄位不符的回覆拒絕，以及原保存環境與場次目前環境不同時的回條顯示。 [操作方式](MISSION_VERSIONS.md#逐房指定任務版本) · [配置檔預覽](../artifacts/console-mission-climate-152-package/venue-mission-file-review.png)
- Windows 0.50.7 同機通過 383 項整合。獨立及合併各 25 個模擬玩家端。獨立五房使用四種天氣及不同的日夜與閃電設定，合併場重載歷史版本。六場均從原 Running 畫格核對預覽所用的保存環境，共 852 格回放、6 份 CSV 與 50 筆伺服器戰績回條。程序停止後，原生與管理 C／F 快照分別有 215、18 個非資料庫檔案一致。 [驗證摘要](../artifacts/mission-climate-0.31.152-validation.json)
- 解壓核對 564 筆清單，另通過 825 項 HTTP 及 107 項管理包檢查。離線核對沿用 Windows 與 Quest 0.50.7 和 Windows 玩家啟動器 1.13。功能來源 `86526d9` 已推送，GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地及廠商硬體仍待驗收。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43284376039)

## 2026-11-13 逐席驗收 Windows 連線量測

- 場館驗收工具在 Windows 收件階段逐席列出回覆、逾時、中斷、p95 往返時間及缺量測的席位。場館可選填最低回覆數與 p95 上限。檔案收齊但量測未達門檻時，收件檢查保留完整狀態並指出未達標的欄位，完整驗收則指出房間及席位。省略門檻時，完整驗收輸出與原結果一致。 [操作方式](EXTERNAL_CLIENTS.md#逐席核對-windows-連線量測門檻)
- 唯讀重驗 1.13 的獨立與合併同機資料，核對原 50 份 ZIP、1,500 筆量測及 18 個場次證據檔。兩批各 25 席以最低 30 筆回覆、p95 上限 40 毫秒的測試設定通過。上限設為 20 毫秒時，舊工具回傳成功，新工具指出獨立 1 席與合併 22 席超出，ZIP 收件與散檔的拒絕結果相同。原檔雜湊維持一致。 [驗證摘要](../artifacts/windows-link-criteria-113/validation.json)
- 96 項場館封存 Python 測試通過。功能來源 `0b47ac6` 已推送，GitHub Actions 因帳務或支出上限未啟動。這次驗證沿用已封存的 Windows 0.50.7 同機場次。跨機 25 人、頭盔、MR 場地及廠商硬體仍待驗收。 [測試紀錄](../artifacts/windows-link-criteria-113/field-tests.log) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43283177108)

## 2026-11-13 從 Windows 玩家視窗啟用連線量測

- Windows 玩家啟動器 1.13 可在核對發行報告後勾選本次連線量測。遊戲關閉後從紀錄資料夾取出驗收 ZIP，下一場恢復未勾選。44 項解壓包啟動器檢查及 20 項 WinForms 發行核對通過，包括已核對的發行報告變更時清除量測選擇及拒絕啟動。解壓清單 331 個檔案中，329 個與 1.12 雜湊相同。 [操作方式](WINDOWS_PLAYER_PACKAGE.md#依場館發行報告核對玩家包) · [視窗畫面](../artifacts/player-link-form-1.13-layout.png)
- 516 項 Windows 同機整合通過。獨立及合併各 25 個模擬玩家端，其中各一席透過 WinForms 啟動實際圖形玩家、收到戰績並正常關窗。兩份圖形席位 ZIP 均逐檔核對原始資料，並納入兩批共 50 份原 ZIP 的收件與封存驗收。1,500 筆量測皆取得回覆。六場雙封存共 3,695 格回放、6 份 CSV 及 50 筆伺服器戰績回條。程序停止後，C／F 快照 378 個非資料庫檔案一致。 [驗證摘要](../artifacts/player-link-form-1.13-validation.json)
- 首輪驗收腳本在逐房回放讀完後才發出圖形玩家關窗指令，晚於該測試的期限。修正驗收腳本在收到原最終戰績及結束斷線後關窗，使用同一份 1.13 玩家包重新驗證。功能來源 `fc5bad7` 與測試修正 `db4ded8` 已推送，兩次 GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地及廠商硬體仍待驗收。 [首輪紀錄](../artifacts/player-link-form-1.13-native.log) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43281125222)

## 2026-11-13 Windows 玩家驗收 ZIP 納入連線量測

- Windows 玩家啟動器 1.12 可將同一次的原始連線量測、玩家日誌與退出報告放入驗收 ZIP。主控收件時依原入場、程序、最後連線與伺服器戰績回條核對。Windows 玩家包通過 42 項啟動器檢查及 331 筆解壓清單核對，其中 329 個檔案與 1.11 雜湊相同。 [收件流程](EXTERNAL_CLIENTS.md#收集-windows-玩家驗收-zip) · [玩家包](WINDOWS_PLAYER_PACKAGE.md)
- Windows 0.50.7 同機整合通過 514 項。獨立及合併各 25 個模擬玩家端，50 份原 ZIP 的收件及封存結果與散檔相同。每席 30 筆，共 1,500 筆量測。本次全部取得回覆，兩種模式各有逾 53 秒的共同在線區間。六場雙封存共 3,611 格回放、6 份 CSV 與 50 筆伺服器戰績回條。程序停止後，C／F 快照 372 個非資料庫檔案一致。 [驗證摘要](../artifacts/player-link-archive-1.12-validation.json)
- 原 ZIP 副本移除量測或換入另一席的量測時，收件檢查都指出問題檔案與缺件席位，完整驗收均拒絕。首輪三項 Python 斷言因舊提示字串及舊版回條測試資料不符而失敗。修正測試資料及斷言後，94 項場館封存測試通過。功能來源 `57a0654` 和測試修正 `f96d0f8` 均已推送，兩次 GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地及廠商硬體仍待驗收。 [拒絕紀錄](../artifacts/player-link-archive-1.12-native-negative.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43279025852)

## 2026-11-13 預覽五房任務配置檔

- 管理包 0.31.151 新增「預覽配置」。主控可在載入前逐房比對目前準備與檔案指定的任務版本、VR／MR、時長及場地檢查結果。來源與解壓包各通過 65 項 Chromium 專項，包含歷史版本、場地無效、切頁隔離及原直接載入流程。 [操作方式](MISSION_VERSIONS.md#在開場前保存五房任務配置) · [預覽畫面](../artifacts/console-venue-file-review-151-package/venue-mission-file-review.png)
- Windows 0.50.7 同機通過 383 項整合。兩種模式各核對五房的原版本 ID 與場地結果，再以解壓管理包載入並開場。獨立及合併各有 25 個同機模擬玩家端。六場雙封存共 784 格回放、6 份 CSV 與 50 筆伺服器回條。程序清理後，原生與管理 C／F 快照分別有 215、18 個非資料庫檔案一致。 [驗證摘要](../artifacts/venue-mission-file-review-0.31.151-validation.json)
- 解壓核對 564 筆清單，另通過 825 項 HTTP 及 107 項管理包檢查。離線核對沿用 Windows 與 Quest 0.50.7。功能來源 `3808484e` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地及廠商硬體仍待驗收。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43276384123)

## 2026-11-13 套用物件調整前檢查場地

- 管理包 0.31.150 在成列複製、批次移動及旋轉的預覽中檢查完整候選配置。場地問題會列出原配置編號並在圖上標出涉及的預覽物件。解壓包 69 項 Chromium 專項驗證套用前發現重疊及包圍盒越界、延遲舊結果隔離和檢查失敗時保留草稿，另有 44 項場地專項。 [操作方式](LAYOUT.md#套用前檢查物件預覽) · [預覽畫面](../artifacts/console-placement-proposal-150-package/placement-proposal-outside-room.png)
- Windows 0.50.7 同機通過 376 項整合。將實際瀏覽器保存並匯出的旋轉版本匯入隔離管理台，兩種模式各五房逐件核對共 30 筆沙包位置及角度。獨立及合併各 25 個同機模擬玩家端，六場雙封存、821 格回放與 50 筆伺服器戰績回條。程序清理後，原生與管理 C／F 快照分別有 215、18 個非資料庫檔案一致。 [驗證摘要](../artifacts/layout-proposal-0.31.150-validation.json)
- 解壓核對 564 筆清單，825 項 HTTP 及 107 項管理包檢查通過。離線核對沿用 Windows 與 Quest 0.50.7 遊戲。功能來源 `79ff57ab` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地及廠商硬體仍待驗收。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43274779617)

## 2026-11-13 全館未確認戰績席位

- 管理包 0.31.149 可從所選結束批次一次查閱各房的未確認席位，並直接下載個人 CSV 或開啟原房間回放。另列有名冊但暫無可核對回條的房間。125 項解壓包 Chromium 專項通過，包括獨立場部分封存、合併場重複席號、錯誤串流拒絕及晚到回條。 [操作方式](SESSION_CLOSURE.md#查看全館未確認席位) · [管理台畫面](../artifacts/console-venue-all-seats-149-package/venue-debrief-all.png)
- Windows 0.50.7 同機通過 550 項整合。獨立及合併各有 25 個同機模擬玩家端。兩批全館 API 與原逐房回條、七項戰績及席位一致。以實際解壓包 Chromium 開啟兩批原收尾，確認未確認清單為空，解除篩選各顯示 25 席，合併場結束後再核對原獨立批次。六場雙封存共 809 格回放、6 份 CSV 與 50 筆伺服器回條，活動場次及程序已清理。原生及管理 C／F 快照分別有 220、18 個非資料庫檔案一致。 [驗證摘要](../artifacts/venue-all-seats-0.31.149-validation.json)
- 解壓核對 564 筆清單，另通過 825 項 HTTP、131 項世界串流與 107 項管理包檢查。沿用 Windows 與 Quest 0.50.7 遊戲。功能來源 `1b7d2048` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地及廠商硬體仍待驗收。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43273236104)

## 2026-11-13 Windows 玩家重連後的戰績驗收 ZIP

- 啟動器 1.11 核對等待中的原場次、完整最終戰績及結束斷線。同一份缺少戰績欄位的日誌在舊版進入 Final 並建立 ZIP，新版維持等待，斷線後顯示未確認且保留原檔。46 項實際 Framework 監看測試通過，涵蓋錯場次、重複結果、截斷及合法重連。另通過 44 項解壓包檢查、17 項 WinForms 處理流程及 36 項連線檔檢查。 [驗證摘要](../artifacts/player-evidence-1.11-validation.json)
- Windows 0.50.7 同機通過 566 項整合。獨立與合併各 25 個玩家端，第 5 房第 2 席使用 Unity Mock Runtime，在 UDP 中斷後以原程序及原入場重連並保留彈藥。50 份原玩家 ZIP 和散檔的驗收結果相同，重連席只以最後一條連線取得戰績回條。六場雙封存核對 3,361 格回放、6 份 CSV 與 50 筆原戰績回條。停止隔離程序後，C／F 快照 286 個非資料庫檔案相同。 [原生檢查](../artifacts/server-package-checks/run-8b0af89870184abdb1dd6df583d9bcdd/checks.json)
- 解壓核對 331 筆清單，329 個檔案與 1.10 雜湊相同。離線核對仍使用 Windows 與 Quest 0.50.7 原遊戲及管理包 0.31.148。功能來源 `40565adf` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、MR 場地與廠商硬體仍待驗收。 [玩家包](WINDOWS_PLAYER_PACKAGE.md) · [發行核對](../artifacts/venue-release-0.50.7-player-1.11.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43270609208)

## 2026-11-13 Windows 五房連線檔交付前核對遊戲來源

- 管理包 0.31.148 和部署工具在暫存前、正式交付前各核對 25 份原票券、名冊、端點及近期原畫格。舊工具在來源失效對照仍回傳成功。新版在暫存前拒絕，並在暫存完成後收到失效回條時移除 25 個暫存檔，兩次均無交付目錄。54 項部署工具測試通過。 [分發方式](EXTERNAL_CLIENTS.md#依電腦分發-windows-vr-連線檔) · [驗證摘要](../artifacts/windows-source-gate-0.31.148-validation.json)
- 解壓管理包通過 30 項 Chromium 專項。純 VR Windows loopback 在無原畫格時仍拒絕，接受當前畫格後核對 25 席，Quest 仍要求區網端點。首輪瀏覽器測試的首格時間不為零，伺服器依錄製契約拒絕。更正測試的首格及下一格後通過。 [瀏覽器結果](../artifacts/console-windows-source-gate-148-vr-package/checks.json)
- Windows 遊戲 0.50.7 同機通過 420 項。獨立與合併各交付 10 份原 VIVE 連線檔並各有 25 個同機模擬玩家端，核對六場雙封存、1,285 格回放、6 份 CSV 及 50 筆戰績回條。另停止原合併伺服器，已簽出的原檔在來源過時後被拒絕匯出。混合 VR／MR 另通過 123 項，交付一份原 Windows VR 連線檔，拒絕 Quest 及 MR 席，五房準備後雙封存共 874 格。原生、混合及管理 C／F 快照分別有 227、49、18 個非資料庫檔案一致。 [原生結果](../artifacts/server-package-checks/run-9beee9fe90184ec5a9cc7328d5444dad/checks.json) · [混合場結果](../artifacts/server-package-checks/run-e31e352826d0474d8352869240417673/checks.json)
- 解壓核對 564 筆清單，825 項 HTTP 與 107 項管理包檢查通過。離線發行核對使用具原發行回條的 Quest 0.50.7／72 APK，首次指向工作目錄的 APK 因沒有發行回條而拒絕。功能來源 `84586d11` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔、實體 MR 與廠商硬體仍待驗收。 [發行核對](../artifacts/windows-source-gate-148-release-package.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43268583573)

## 2026-11-13 觀戰錄製清單分頁

- 管理包 0.31.147 先顯示最近 30 筆錄製及使用中的來源，操作員可再載入較早場次。131 項串流檢查比對主控與第 1、5 房控制台可見的 268、121、147 筆錄製，逐頁核對順序、權限和游標。261 項 Chromium 專項包含從全館收尾開啟第一頁以外的原錄製、翻頁保留回放，以及合併場觀戰與收尾。 [操作說明](WORLD_RECORDING.md#載入較早錄製) · [驗證摘要](../artifacts/recording-pages-0.31.147-validation.json)
- Windows 遊戲 0.50.7 同機通過 357 項整合。獨立與合併模式各有 25 個模擬玩家端同時連線，六場核對 844 格回放及 50 筆原戰績回條。Chromium 以控制台結束第 1 房並核對原錄製的封存尾端。場次及程序已清理，原生與管理 C／F 快照分別有 217、18 個非資料庫檔案一致。 [同機驗證](../artifacts/server-package-checks/run-82fe1622261b4935b0e98e07e89118e1/checks.json)
- 解壓核對 564 筆清單，825 項 HTTP 與 107 項管理包檢查通過。功能來源 `acfdbd7e` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、Quest 3／VIVE XR 與廠商硬體仍待現場驗收。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43266633442)

## 2026-11-13 批次讀取觀戰錄製清單

- 管理包 0.31.146 每批查詢至多 128 個可見場次，釋放 SQLite 存取鎖後才解析錄製標頭。123 項串流檢查通過。主控、房控第 1 房及第 5 房各讀到 267、121、147 筆歷史錄製，完整核對順序、內容與權限。歷史測試包含只有標頭的錄製、已封存錄製與沒有錄製的場次。清單請求並行期間，第 5 房原來源持續發布並於第 64 格封存。 [錄製說明](WORLD_RECORDING.md#儲存與驗證邊界)
- 兩個解壓版各做一輪同機對照，每個角色讀取 24 次。主控中位回應時間為 14.79 與 6.86 毫秒，第 1 房為 8.95 與 5.73 毫秒，第 5 房為 10.84 與 5.14 毫秒。這批結果來自本機 .NET 模擬發布與歷史清單測試。 [驗證摘要](../artifacts/archive-list-0.31.146-validation.json)
- Windows 遊戲 0.50.7 通過 357 項整合。獨立及合併各 25 個同機模擬玩家端，六場核對 907 格完整回放與 50 筆原戰績回條。實際 Chromium 以控制台結束第 1 房並核對原錄製封存尾端。另通過 17 項即時觀戰、825 項 HTTP、107 項管理包檢查。解壓核對 564 筆清單，停止後原生及管理 C／F 快照各有 217、18 個非資料庫檔案一致。功能來源 `6653138d` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機、頭盔和廠商設備仍待現場驗收。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43264154882)

## 2026-11-13 下載前核對片段戰績 CSV

- 控制台 0.31.145 會逐列比對下載的場次、串流、起訖格、房間、玩家與戰績。保留原 CSV 的 UTF-8 BOM、跨行名稱及試算表文字防護。空片段也核對範圍列。解壓包通過 116 項 Chromium 專項，113 項 Node 檢查包含替換串流、房間、計數及空片段範圍。 [操作說明](REPORTS.md#下載指定片段的戰績)
- Windows 遊戲 0.50.7 同機通過 9 項整合。舊管理包 0.31.144 的對照下載了串流識別遭替換的 CSV。新版在獨立第 1 房及合併第 2 房均拒絕替換檔、保留表格，重試後下載原檔。兩份下載檔的房號、串流、起訖與中彈數相符。七場共核對 1,132 格原始日誌，場次及程序已清理。 [驗證摘要](../artifacts/clip-csv-0.31.145-validation.json)
- 825 項 HTTP、117 項串流、107 項管理包檢查通過。解壓核對 564 筆清單，停止後原生及管理 C／F 快照各有 17、18 個非資料庫檔案一致。功能來源 `68a5b37f` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機 25 人、頭盔及廠商設備仍待現場驗收。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/43262736382)

## 2026-11-11 本房回放的事件搜尋與跳轉

- 控制台 0.31.144 的本房事件搜尋及前後跳轉使用與回放畫格相同的房間篩選。搜尋結果會核對錄製來源、保存範圍及房號，跳轉再核對原格的時間與相符事件數。舊管理包 0.31.143 的對照重現索引計入本房畫格已過濾的事件。新版解壓包通過 117 項世界串流與 133 項 Chromium 專項。 [操作說明](WORLD_RECORDING.md#依房間與種類搜尋戰鬥事件)
- Windows 遊戲 0.50.7 通過 9 項同機整合。獨立第 1 房與合併第 2 房均從原事件搜尋及跳轉，測試也拒絕替換房號的回覆。兩份瀏覽器下載的 CSV 各一列，核對房號、原片段及中彈數。七場 1,102 格原始日誌與封存相符，場次和程序已清理。 [驗證摘要](../artifacts/projected-events-0.31.144-validation.json)
- 825 項 HTTP、111 項 Node、107 項管理包檢查通過。解壓核對 564 筆清單，停止後原生及管理 C／F 快照各有 17、18 個非資料庫檔案一致。首輪串流測試新增的區域變數碰到既有重啟函式名稱，修正後重跑。功能來源 `86122698` 已推送。GitHub Actions 因帳務或支出上限未啟動，跨機、頭盔與廠商設備仍待現場驗收。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42998663626)

## 2026-11-11 從單一場次的任務收尾直接回放

- 控制台 0.31.143 可從已結束場次直接回放。房控從本房俯視開始，服務只傳本房資料。錄製仍未封存時，可播放當下核對的保存片段。解壓包通過 1,015 項完整 Chromium 檢查，包含房控以本房範圍播放到真實未封存尾端。另有 25 項收尾專項。 [操作說明](WORLD_RECORDING.md#從單一場次的任務收尾回放) · [瀏覽器紀錄](../artifacts/console-closure-replay-143-final/checks.json)
- Windows 遊戲 0.50.7 通過 9 項同機原生整合。第 1 房重開後，房控仍播放原獨立場的 54 格。合併場的第 2 房房控收到同一原錄製的 64 格，逐格核對房間、玩家、敵軍與統計，並確認另一房投影請求遭拒。七場共 922 格原始世界日誌與封存相符。停止後原生及管理 C／F 快照各有 17、18 個非資料庫檔案一致，場次及程序均已清理。 [驗證摘要](../artifacts/closure-replay-0.31.143-validation.json)
- 825 項 HTTP、111 項 Node、107 項管理包檢查通過，解壓核對 564 筆清單。前兩輪瀏覽器回歸在同頁接續測手動重播時讀到舊尾端狀態或停在等待串流，改用獨立房控頁重驗。首輪原生瀏覽器擷取串流回應失敗，複驗核對瀏覽器實際畫格與同身分的原 API 串流。產品來源 `dd28c2d9`、測試修訂 `aa9f473c`。GitHub Actions 因帳務或支出上限未啟動，跨機、頭盔和廠商設備仍待現場驗收。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42996366174)

## 2026-11-11 從單一已結束場次準備原任務

- 控制台 0.31.142 讓房控從本房的獨立歷史場次帶回原版本和房號，主控也可從已結束的合併場帶回五房模式。59 項解壓包瀏覽器檢查通過，包含跨房權限、已占用的房間、異常回覆、原初始天氣和手動建立。 [操作說明](MISSION_VERSIONS.md#從單一已結束場次選用原任務)
- Windows 遊戲 0.50.7 使用解壓後的管理台通過 7 項原生整合。第 1 房原場結束後，房控從瀏覽器建立新場，採用第一版的 60 秒、晴天及沙包配置，儘管原場執行中曾改成暴風雨且任務庫已有新版。這段期間第 2 至 5 房各有 45 至 46 格執行中畫格並持續前進。七場的 666 格原始世界日誌與終端封存相符，場次及程序已清理。 [驗證摘要](../artifacts/session-reprepare-0.31.142-validation.json)
- 825 項 HTTP、111 項 Node、107 項管理包檢查通過。解壓核對 564 筆清單，停止後原生與管理 C／F 快照各有 17、18 個非資料庫檔案一致。離線核對使用原世界封存的戰鬥序號及原最終戰績，管理事件序號另有自己的記錄。功能來源 `342d9f19` 已推送。GitHub Actions 因帳務或支出上限未啟動。這輪為同機桌面模擬，跨機 25 人、頭盔與廠商設備仍待現場驗收。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42995199786)

## 2026-11-11 開場前保存及載入五房任務配置

- 控制台 0.31.141 可下載五房合併或獨立配置 JSON，重新登入後從同一任務庫讀取各房原保存版本。任何版本無法核對時，會指出受影響的房間並保留目前配置。103 項解壓包瀏覽器檢查涵蓋原版、混合 VR／MR、缺版、無效檔、切頁中斷、草稿與占用房間。 [操作說明](MISSION_VERSIONS.md#在開場前保存五房任務配置) · [瀏覽器紀錄](../artifacts/console-venue-missions-141-package/checks.json)
- Windows 遊戲 0.50.7 通過 367 項原生整合。兩份瀏覽器原下載檔均在重新登入後載入並建立場次。獨立五房使用五個不同任務，合併場使用已有新版的歷史任務。原錄製核對時間、環境、敵軍與場地物件。兩種模式各有 25 個同機模擬玩家端，六場雙封存、914 格完整回放及 50 筆伺服器戰績回條相符。場次及程序已清理。 [驗證摘要](../artifacts/venue-mission-file-0.31.141-validation.json)
- 825 項 HTTP、111 項 Node 和 107 項管理包檢查通過，解壓核對 564 筆清單，停止後原生及管理 C／F 快照各有 215、18 個非資料庫檔案一致。首輪瀏覽器測試漏帶修訂請求 ID，首個原生指令漏帶本機遊戲 IPv4，均已補齊重驗。功能來源 `e14d7bac` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機、頭盔和廠商設備仍待現場驗收。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42993836812)

## 2026-11-11 從歷史批次套用五房合併原任務

- 控制台 0.31.140 可從完整合併批次選取「套用本批五房任務版本」。準備區顯示原保存版本並執行合併場地檢查。主控仍須按「建立準備場次」才能建立新場。94 項瀏覽器專項通過，涵蓋已有新版、保留編輯草稿、占用房間、異常回覆及原獨立批次流程。 [操作說明](MISSION_VERSIONS.md#從全館收尾套用五房原版本)
- Windows 遊戲 0.50.7 通過 371 項整合。從歷史批次還原的第一版任務以新場次執行。原錄製核對 420 秒、雨夜與逐房油桶位置及朝向。獨立和合併各使用 25 個同機玩家端，六場雙封存、843 格完整回放和 50 份原戰績與伺服器回條相符，所有場次及程序已清理。 [驗證摘要](../artifacts/linked-archive-0.31.140-validation.json)
- 825 項 HTTP、111 項 Node 及 107 項管理包檢查通過。解壓核對 564 筆清單，停止程序後的遊戲和管理 C／F 快照各有 215、18 個非資料庫檔案雜湊一致。功能來源 `be72e1b2` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機、頭盔及廠商設備仍待現場驗收。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42992344342)

## 2026-11-11 五房場地拒絕保留問題平面圖

- 控制台 0.31.139 在逐房指定任務送件遭拒時，會顯示原回覆的場地報告。使用同一保存版本的房間都會標出問題物件，可從總覽進入詳細檢查。舊版 0.31.138 對照保留錯誤房號但清掉兩房的平面圖。新版通過 41 項五房及 44 項場地編輯的解壓包瀏覽器專項。 [操作說明](MISSION_VERSIONS.md#逐房指定任務版本) · [總覽畫面](../artifacts/console-layout-rejection-139-focused/independent-room-layout-rejection.png)
- Windows 遊戲 0.50.7 完成 376 項整合檢查。真實拒絕回覆指出第 4 房，總覽在第 4、5 房均標出同兩件重疊物件。更換版本後，瀏覽器的五房配置、建立回條及原生遊戲錄製逐房相符。獨立與合併各有 25 個同機玩家端，六場雙封存、865 格完整回放和 50 份原戰績及伺服器回條相符。首輪原生測試在送件前的場地預檢等待逾時並清理，複驗先選明確版本並在測試路由生效時按「重新檢查場地」。 [驗證摘要](../artifacts/room-layout-rejection-0.31.139-validation.json)
- 825 項 HTTP、111 項 Node 與 107 項管理包檢查通過。解壓核對 564 筆清單，停止程序後的遊戲與管理 C／F 快照各有 215、18 個非資料庫檔案雜湊一致。功能來源 `544281ff` 已推送。GitHub Actions 因帳務或支出上限未啟動。頭盔、跨機及廠商設備仍待現場驗收。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42991182497)

## 2026-11-11 Quest 暫存連線檔驗證後重核來源

- Quest 線上部署會在暫存連線檔通過雜湊驗證後，再核對原五房的遊戲來源、端點及入場。批次遇到來源失效會回報 `venue-check-failed` 和 `verify-live-venue-before-stop`。受影響席位保留原正式連線檔，工具會嘗試清除暫存檔。既有中斷報告可供後續重試。單席線上部署也套用這項核對。 [部署操作](QUEST3.md#啟動前核對裝置檔案)
- 舊腳本的受控對照中，第四席暫存後來源失效，該席仍送出啟動，直到第五席才拒絕。新版 54 項部署測試通過。首輪全套件有一個測試仍預期每席一筆線上核對，更新為實際的傳檔前與停止前兩筆後完整複驗。 [部署測試](../artifacts/quest-activation-gate-deployment-tests.log)
- 使用 Windows 遊戲 0.50.7、管理台 0.31.138 和模擬 ADB 通過 156 項原生整合。合併 MR 的原來源在第二席暫存檔雜湊完成後失效，第二席保留正式連線檔、移除暫存檔，且無停止、替換或啟動指令。原來源從第 106 格恢復至第 109 格後，同一份中斷報告只補兩個未完成席位。獨立和合併另完成 25 席及部分清單部署，六場 Preparing 雙封存、636 格回放，C／F 快照 56 個非資料庫檔案一致。場次及程序已清理。 [驗證摘要](../artifacts/quest-activation-gate-validation.json)
- 部署腳本來源 `e95fd233` 已推送。GitHub Actions 因帳務或支出上限未啟動。頭盔、跨機與廠商硬體仍待現場驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42989927304)

## 2026-11-11 重讀五房啟動計畫時保留 UDP 埠

- 控制台 0.31.138 在下載前發現場次變更時會指出受影響的房間，並要求重新讀取。留在「房間與場次」時，重讀保留本頁輸入的 UDP 埠。獨立及合併各有自己的輸入，刻意清空的欄位仍須填寫。舊版 0.31.137 的瀏覽器對照重現埠恢復預設值。新版 21 項瀏覽器專項通過，含場次變更、埠重複、清空、模式切換及離開頁面。 [操作說明](WINDOWS_SERVER_PACKAGE.md#從主控台下載場館計畫) · [瀏覽器結果](../artifacts/console-venue-port-drafts-138-focused/checks.json)
- Windows 啟動器 1.20、遊戲 0.50.7 和管理包 0.31.138 通過 484 項整合檢查。獨立及合併各 25 個同機玩家端。兩模式均先填埠再重讀，用瀏覽器下載的第四版計畫核對六個實際 UDP 綁定和原雙端預檢。改錯埠的兩份預覽均遭拒絕。六場雙封存、989 格完整回放及 50 份原戰績與伺服器回條相符。 [驗證摘要](../artifacts/venue-port-drafts-0.31.138-validation.json)
- 825 項 HTTP、111 項 Node 與 107 項管理包檢查通過。封裝解壓核對 564 筆清單，程序停止後遊戲和管理 C／F 快照各有 254、18 個非資料庫檔案雜湊一致。功能來源 `df090065` 已推送。GitHub Actions 因帳務或支出上限未啟動。跨機、頭盔及廠商設備仍待現場驗收。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42988614844)

## 2026-11-11 從全館席位開啟個人回放

- 控制台 0.31.137 在全館收尾「查看席位」新增「個人回放」。主控可從原批次開啟該玩家及房間，停在封存尾格，再檢視玩家的保存事件。未確認回條的席位也可回看。個人 CSV 會核對原場次及該席玩家識別。 [操作說明](SESSION_CLOSURE.md#從全館收尾查看席位)
- 116 項解壓包 Chromium 專項通過，涵蓋房間重用、未確認席位、重複玩家識別及錯玩家 CSV。首輪測試曾在事件回應內核對房號，既有 API 的房號實際在請求參數，已修正測試。第一輪原生瀏覽器已開啟原場次，但檢查器誤要求第一頁必有事件。保留原紀錄，複驗使用原「繼續搜尋」進到下一頁。 [瀏覽器專項](../artifacts/console-seat-replay-137-final/checks.json) · [首輪原生瀏覽器結果](../artifacts/server-package-checks/run-099c0c47f1e54acc9e11e13b5c9c63b5/independent-venue-field-ui.json)
- 沿用 Windows 遊戲 0.50.7 完成 583 項原生整合。獨立和合併各有 25 個同機玩家端。三次席位操作涵蓋兩種模式及歷史批次，每次均翻到第二頁並跳轉首筆事件，頁面畫格與原遊戲世界日誌相符。六場雙封存、1,600 格完整回放及 50 份原玩家戰績與伺服器確認相符，場次與程序已清理。 [驗證摘要](../artifacts/venue-seat-replay-0.31.137-validation.json)
- 825 項 HTTP、113 項世界串流、111 項 Node 及 107 項管理包檢查通過。管理包 564 筆清單逐檔核對，程序停止後遊戲與管理 C／F 快照分別有 220、18 個非資料庫檔案雜湊一致。產品來源 `9b93a61c` 已推送。GitHub Actions 因帳務或支出上限未啟動。頭盔、跨機與廠商設備仍待現場驗收。 [Windows 管理包](WINDOWS_CONTROL_PACKAGE.md) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42987238524)

## 2026-11-11 五房排演可單獨停止指定房間

- 硬體模擬器 0.2.13 支援五房運行中以 `room-01.stop` 至 `room-05.stop` 停止單房。獨立和合併模式均驗證第二房保留五筆原確認、取消一筆待確認批次，第五房沿用原連線確認第六筆。第二房發布終止狀態後可用同一設定另開閘道，使用新連線和當前游標。兩種模式的遊戲場次仍處於 Running。 [操作說明](HARDWARE.md#停止五房排演中的指定房間) · [即時檢查](../artifacts/live-hardware-gateway/run-739fa4feb63441348900b3ee8bb76806/checks.json)
- 1,101 項核心、38 項離線及 74 項即時模擬檢查通過。0.2.13 解壓包八個檔案與清單相符，範例輸出與原離線結果逐位元相同，舊版 0.2.12 也可照原清單核對。來源 `46e91921` 已推送。GitHub Actions 因帳務或支出上限未啟動。 [套件資料](HARDWARE_SIMULATOR.md) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42985596090)
- 以解壓後的模擬器搭配 Windows 遊戲 0.50.7 及管理包 0.31.136，完成 430 項命令列整合檢查。獨立、合併各 25 個同機玩家端，十房次共 217 筆模擬確認、50 席原戰績及伺服器回條、11 份 CSV、六場雙封存及 1,793 格完整回放。程序已清理，C／F 快照 235 個非資料庫檔案雜湊一致。廠商設備、跨機與頭盔仍待現場驗收。 [驗證摘要](../artifacts/hardware-0.2.13-room-stop-validation.json)

## 2026-11-11 全館收尾顯示逐席原戰績

- 控制台 0.31.136 的全館席位明細顯示原封存的耗彈、命中、擊殺、中彈、耗損、命中率與血量。可用「只顯示未確認」篩選，同時檢視戰績或下載個人 CSV。113 項解壓版收尾專項通過，包含原房間重用、未確認席位、異常數值與手機版面。 [操作說明](SESSION_CLOSURE.md#從全館收尾查看席位)
- 沿用 Windows 遊戲 0.50.7，581 項原生檢查通過。獨立及合併各 25 個同機玩家端，50 席七項戰績逐一與原個人 CSV、封存統計及玩家結果相符。瀏覽器驗證兩種模式並重開較早批次，共 15 次房間明細。六場雙封存、1,658 格完整回放及 50 筆原戰績確認相符，測試場次與程序已清理。 [原生結果](../artifacts/server-package-checks/run-5636cbd252514aa992ddb79d0fbea85e/checks.json)
- 825 項 HTTP、111 項 Node、981 項解壓包 Chromium 及 107 項管理包檢查通過。ZIP 565 檔逐一核對，程序停止後的遊戲及管理 C／F 快照各有 220、18 個非資料庫檔案雜湊相符。GitHub Actions 因帳務或支出上限未啟動。跨機、頭盔及廠商硬體仍待現場驗收。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [核對摘要](../artifacts/seat-scores-0.31.136-validation.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42983849343)

## 2026-11-11 開場前等候追蹤席位就緒

- `deploy-quest.ps1 -VerifyTrackedSeats -WaitForTrackedSeconds` 可在原部署包核對後等待 1 至 120 秒。只有同一輪所有指定席位具有新鮮且對應原入場的追蹤才會成功。逾時只輸出最後一輪結果。原場次、席位、權限變更及票券到期均會停止。52 項部署測試通過，包含兩種模式第三輪同時就緒、交替未就緒的逾時、HTTP 延遲及原身分變更。 [操作說明](QUEST3.md#等候指定席位同時追蹤就緒)
- 沿用控制台 0.31.135 與 Windows 遊戲 0.50.7，384 項原生檢查通過。獨立及合併各 25 個同機桌面玩家。兩種模式各取樣三次後逾時，所有場次序號保持原值。直接從六份封存世界日誌逐房核對最後一輪，50 席都保持連線及合成姿態。六場雙封存、1,445 格完整回放及 50 筆原戰績與伺服器確認相符，C／F 快照 219 個非資料庫檔案雜湊相符。 [驗證摘要](../artifacts/quest-tracked-wait-validation.json)
- GitHub Actions 因帳務或支出上限未啟動。等候後成功就緒的案例使用 HTTP 測試資料。頭盔、跨機 25 人及廠商硬體仍待現場驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42982338680)

## 2026-11-11 即時觀戰定位最近事件

- 控制台 0.31.135 依選定的事件種類及房間，從畫面上的最後保存格往前找，停在符合的原保存格。返回時保留房間與鏡頭。17 項解壓版觀戰專項通過，包含原來源不符、找不到事件、返回更新中的同一來源及手機版面。 [操作說明](WORLD_RECORDING.md#從即時觀戰定位最近事件) · [畫面](../artifacts/console-live-event-135-focused/world-live-event.png)
- 沿用 Windows 遊戲 0.50.7，485 項原生檢查通過。獨立及合併各 25 個同機玩家端，兩種模式逐房驗證共十次定位及返回。六份已關閉的原世界日誌核對十次定位均是按下當時各房最近的原受傷事件。六場雙封存、1,987 格完整回放、50 筆原戰績和伺服器確認相符，隔離場次及程序清理完成。 [原生結果](../artifacts/server-package-checks/run-be796644c6214d48b1b6b4617ac966eb/checks.json)
- 111 項 Node、979 項完整 Chromium 及 107 項 Windows 管理包檢查通過。管理包解壓逐一核對 565 檔。測試停止後，遊戲及管理的 C／F 快照各有 251、18 個非資料庫檔案雜湊相符。GitHub Actions 因帳務或支出上限未啟動。頭盔、跨機及廠商硬體仍待現場驗收。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [核對摘要](../artifacts/live-event-0.31.135-validation.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42980925032)

## 2026-11-11 Quest 部署重試歷史納入收尾驗收

- 累計部署報告保存上一份原檔的 SHA-256。五房收尾可讀取最新報告或一路承接的原始報告，核對同一部署 ZIP、裝置清單及已完成席位。歷史中斷、分岔、修改已完成席位或跨批重複成功席位均會拒絕。手動分批部署的互不重複報告仍可沿用。93 項收尾驗收及 51 項部署測試通過。 [操作說明](EXTERNAL_CLIENTS.md#核對封存席位的-quest-發行-apk)
- 使用實際部署 PowerShell、原 Quest 0.50.7／72 APK 及模擬 ADB 和場館資料，獨立三份與合併兩份部署報告均完成驗收。兩種模式各配對 5 席 Quest、20 席 Windows 和 25 筆模擬伺服器確認。舊驗收工具拒絕重疊報告，新版接受原檔承接並拒絕改過換行的副本。原六批 Windows 5／10／25 席總驗收結果相同。 [命令列整合](../artifacts/quest-deployment-history-0507/deployment-history-results.json)
- 原生混合場使用既有 Windows 遊戲 0.50.7 和控制台 0.31.134。第一輪匯出重排了 JSON，留存原報告雜湊因此與部署當時不同。修正留存方式後重跑 126 項通過，直接以 F 槽原檔核對前一份報告雜湊。五個準備場次封存 649 格、C／F 的 49 個非資料庫檔案相符，活動場次及殘留程序為零。GitHub Actions 因帳務或支出上限未啟動。頭盔、跨機與廠商硬體仍待現場驗收。 [驗證摘要](../artifacts/quest-deployment-history-0507/validation.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42979679910)

## 2026-11-11 Quest 部署按原報告重試

- `deploy-quest.ps1 -RetryIncomplete` 使用原五房 ZIP、原裝置清單及上一份部署報告，只核對與補跑失敗及未執行的席位。待重試裝置的原身分、APK 條件、票券與五房遊戲來源仍須通過檢查。進入寫入階段後的報告會累計原結果。若上一輪的啟動結果不明，腳本會停止自動重試。51 項 Quest 部署測試通過，涵蓋連續中斷、裝置身分錯配、ZIP 或清單變更及 APK 回條保留。 [重試操作](QUEST3.md#從原部署報告重試未完成席位)
- 沿用控制台 0.31.134 與 Windows 遊戲 0.50.7。從原控制台簽發 ZIP 完成獨立、合併及混合 VR／MR 三次模擬 ADB 排演，各保留一席並只補四席。VR 原生 384 項通過，獨立與合併各 25 個同機玩家端，六場雙封存、1,331 格回放及 50 筆原戰績和伺服器確認。混合場 126 項通過，五個原生準備場次封存 631 格並核對 MR 鎖定校正檔。兩次測試結束後均無活動場次或殘留程序。 [核對摘要](../artifacts/quest-deployment-retry-validation.json)
- 首次原生 VR 排演在取得 JSON 回條前中止，原因未確認，原結果保留。通過的 VR 與混合排演各有 219 與 49 個非資料庫檔案在 C／F 快照雜湊相符。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE XR、跨機 25 人及廠商硬體仍待現場驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42978023465)

## 2026-11-11 五房保存配置並排預覽

- 控制台 0.31.134 在逐房指定任務時可並排查看五張同尺度平面圖，核對保存物件、朝向及出生位。更換單房版本時先清除舊圖，其他房可繼續核對。可從每張圖開啟該房的詳細通路檢查。最後一次修正讓登出一併清除圖、標籤及保存版本 ID，已加入瀏覽器斷言。 [操作說明](MISSION_VERSIONS.md#逐房指定任務版本) · [預覽畫面](../artifacts/console-room-layouts-134-final-focused/independent-room-layouts.png)
- 400 項 Windows 原生檢查通過。原瀏覽器建立回條、五房保存版本與 Windows 遊戲世界的物件位置及朝向逐房相符。獨立及合併各有 25 個同機玩家端，六場完成雙封存和 962 格完整回放，六份 CSV 共 50 筆原玩家結果及 50 筆伺服器確認。隔離場次及程序已清理。沿用 Windows 遊戲 0.50.7，跨機、頭盔及廠商硬體仍待現場驗收。 [原生結果](../artifacts/server-package-checks/run-aab495aa64a64b5b8e80fc2ceb7184da/checks.json) · [瀏覽器原回條](../artifacts/server-package-checks/run-aab495aa64a64b5b8e80fc2ceb7184da/native-independent-room-layouts.json)
- 最終管理包通過 111 項 Node、38 項 Chromium 專項、974 項完整 Chromium 及 107 項 Windows 管理包檢查。ZIP 解壓逐一核對 565 檔。遊戲與管理測試停止後，C／F 快照分別有 213、18 個非資料庫檔案雜湊相符。初版 ZIP 在加強後的登出斷言重現問題，原始證據已保留。GitHub Actions 對 `d3c614d6` 因帳務或支出上限未啟動任何步驟。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [核對摘要](../artifacts/room-layouts-0.31.134-validation.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42976283648)

## 2026-11-11 從全館席位下載個人戰績

- 控制台 0.31.133 可從原結束批次的席位明細直接下載個人 CSV。使用原結束名冊的房號及席號核對戰鬥與世界封存，房間重開後仍指向原場次。下載後的回條仍以原遊戲伺服器確認為準。111 項收尾 Chromium 專項通過，包含未確認席位的原檔、房控權限、錯誤檔名、手機版面與切換批次時取消下載。 [操作說明](SESSION_CLOSURE.md#從全館收尾查看席位)
- 571 項 Windows 原生檢查通過。獨立及合併各 25 個同機玩家端，50 份逐席 CSV 均與原封存個人戰績逐位元一致，50 席原戰績均有中彈與耗損。瀏覽器從獨立、合併及較早的獨立批次各下載一份原檔。六場雙封存共 1,579 格完整回放，50 筆原戰績與遊戲伺服器確認相符。跨機、頭盔及廠商硬體仍待現場驗收。 [原生結果](../artifacts/server-package-checks/run-8efd945f6e174910a8f6054519b6b551/checks.json)
- 825 項 HTTP、111 項 Node、970 項解壓包 Chromium 與 107 項 Windows 管理包檢查通過。ZIP 解壓逐一核對 565 檔。隔離遊戲與管理測試停止後，C／F 快照分別有 220、18 個非資料庫檔案雜湊相符。GitHub Actions 對 `531332f3` 因帳務或支出上限未啟動任何步驟。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [核對摘要](../artifacts/seat-report-0.31.133-validation.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42974206955)

## 2026-11-11 全館戰績回條席位明細

- 管理台 0.31.132 可在全館收尾選擇原批次與房間，查看原結束名冊的席號、玩家和回條，或只顯示未確認。原房間已被新場次使用時，仍讀取原場次的雙封存。晚到回條可更新已開啟的明細。107 項收尾 Chromium 專項通過，涵蓋房控拒絕、房間重用、手機版面及切換批次後的延遲回應。 [操作說明](SESSION_CLOSURE.md#從全館收尾查看席位) · [明細畫面](../artifacts/console-debrief-seats-132-focused/venue-debrief-seats.png)
- 482 項 Windows 原生檢查通過。獨立與合併各 25 個同機玩家端，逐房核對瀏覽器顯示的 50 席回條與遊戲伺服器的原確認。合併場後還重開較早的獨立批次並核對五房。六場雙封存共 884 格完整回放，50 筆 CSV 相符，活動場次與隔離程序已清理。跨機、頭盔及廠商硬體仍待現場驗收。 [原生結果](../artifacts/server-package-checks/run-bbf4bfb0f76141cf98dc16bdd2ae810b/checks.json)
- 825 項 HTTP、111 項 Node、966 項解壓包 Chromium 與 107 項 Windows 管理包檢查通過。ZIP 解壓後逐一核對 565 檔，隔離遊戲與管理測試的 C／F 快照分別有 220、18 個非資料庫檔案雜湊相符。GitHub Actions 對 `bc634702` 因帳務或支出上限未啟動任何步驟。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [核對摘要](../artifacts/debrief-seats-0.31.132-validation.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42972682221)

## 2026-11-11 批次旋轉場地物件

- 控制台 0.31.131 支援以所選物件的平均位置為轉軸，先旋轉再依房間本地 X／Z 平移。配置圖顯示原轉軸及帶編號的目的位置與方向。確認後可單步套用、復原或重做。64 項配置編輯 Chromium 專項通過，涵蓋小數角度、錯誤角度、草稿預覽、版本保留和範本匯出。 [操作說明](LAYOUT.md#批次旋轉場地物件) · [配置圖](../artifacts/console-batch-rotation-131-publication/placement-batch-rotation-map.png)
- 將瀏覽器下載的原範本匯入管理包，再由既有 Windows 遊戲 0.50.7 啟動兩種模式。401 項原生檢查通過，獨立與合併各 25 個同機玩家端，兩輪共 30 筆物件位置及角度逐一相符。六場完成雙封存、942 格完整回放，50 筆原戰績、伺服器確認及 CSV 相符。跨機與頭盔仍待實機驗收。 [原範本](../artifacts/console-batch-rotation-131-publication/placement-batch-rotation-template.json) · [原生檢查](../artifacts/server-package-checks/run-d80838d11f984633ba4ac0c064036e88/checks.json)
- 111 項 Node、959 項解壓包 Chromium 及 107 項 Windows 管理包檢查通過。ZIP 解壓後逐一核對 562 檔。程序停止後，遊戲與管理測試的 C／F 快照分別有 213、18 個非資料庫檔案雜湊相符。GitHub Actions 對 `ebdeb7aa` 因帳務或支出上限未啟動任何步驟。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [核對摘要](../artifacts/placement-rotation-0.31.131-validation.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42970778100)

## 2026-11-11 Quest UDP 逐席重試

- 批次工具接受原報告。原裝置、端點、來源或樣本數變更時拒絕沿用。重試逐席核對原雙端報告的雜湊、來源、埠及有效時間。只重新探測未通過的席位，並把仍有效的原報告連同新報告列入本輪結果。探測中按 Ctrl+C 可保存已完成與待補席位。 [操作說明](QUEST3.md#重試-quest-udp-預檢席位)
- 獨立與合併各用 25 席、3 席模擬離線。Windows PowerShell 監聽及 Java UDP 探測實際在本機交換封包，ADB 裝置狀態以測試替身提供。兩次重試各沿用 22 席、只補 3 席，場館工具再驗證兩份完整的 25 席報告。C／F 118 份檔案逐一核對，各輪首批原報告雜湊維持相同。跨機與頭盔實機仍待現場驗收。 [本機驗收摘要](../artifacts/quest-venue-udp-retry-2026-11-11/summary.json)
- 11 項 Quest 預檢、8 項 Windows UDP 及 5 項封存預檢測試通過，包含過期、檔案內容變更及中斷。GitHub Actions 對 `d27a9523` 因帳務或支出上限未啟動任何步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42970040037)

## 2026-11-11 啟動器預覽與五房 UDP 核對

- 場館 UDP 工具可直接讀取 Windows 啟動器 `--venue-check` 產生的原預覽。比對五房模式、房間、埠、公告 IPv4 與本機綁定 IPv4。若其中一房不符，報告指出房間與原因，即使雙端報告都有效，整體仍回報未完成。報告保存原預覽 SHA-256。 [操作說明](EXTERNAL_CLIENTS.md#開場前核對五房-udp-報告)
- 使用從管理台 0.31.130 下載的第四版計畫，與 Windows 啟動器 1.20 及遊戲 0.50.7 解壓包整合。獨立場與合併場各用原計畫、只改最後一個埠的計畫產生預覽。兩份錯埠預覽均被 UDP 工具拒絕，原預覽通過。六組原始 UDP 報告在實際 Unity 程序綁定後，按原時間與埠重驗通過。 [獨立場核對](../artifacts/server-package-checks/run-184a3547c1cd446fb66d376d75b152a6/independent-venue-udp-readiness.json) · [合併場核對](../artifacts/server-package-checks/run-184a3547c1cd446fb66d376d75b152a6/linked-venue-udp-readiness.json)
- 477 項 Windows 原生檢查通過。獨立與合併各 25 個同機玩家端同時入場，六場雙封存共 987 格完整回放，50 筆原戰績、伺服器確認及 CSV 相符。活動場次歸零，隔離程序均已停止，C／F 快照另有 254 個非資料庫檔案雜湊相符。跨機 25 人、Quest／VIVE XR 實機及廠商硬體仍待現場驗收。 [原生驗收摘要](../artifacts/server-package-checks/run-184a3547c1cd446fb66d376d75b152a6/udp-preview-validation.json)
- 本機 8 項 Windows UDP、9 項 Quest 預檢及 1 項封存整合測試通過。GitHub Actions 對 `82314f71` 因帳務或支出上限未啟動任何步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42969046975)

## 2026-11-11 五房開場前 UDP 報告核對

- 場館主控可依五房網路清單核對 Windows 雙端報告和 Quest 原批次報告。共用端點及來源 IPv4 的席位共用一組報告，五房獨立時按各自的遊戲埠核對。缺件、重複、過期、不符或無法讀取時，報告會指出待補的席位或列出多餘組數。完整報告可交給原封存驗收，屆時用實際綁定時間與已確認的玩家來源再查。 [操作說明](EXTERNAL_CLIENTS.md#開場前核對五房-udp-報告)
- 本機 Windows 原生 UDP 探測通過。獨立模式以同一來源核對五個埠、每房一席。合併模式用兩個同機來源涵蓋清單的 25 席，其中一組透過 Quest 批次格式匯入。共七組實際探測、28 份報告與清單保存至 F 槽，逐檔雜湊相符。缺件、錯誤來源、重複輸入與錯誤配對均回報失敗。 [本機核對摘要](../artifacts/venue-udp-readiness-2026-11-11/summary.json)
- 8 項 Windows UDP、9 項 Quest 預檢工具及 92 項封存工具測試通過。兩種模式的封存測試以彙整報告核對 25 筆測試資料的玩家確認，與原逐場輸入結果完全相同。場館報告測試使用同一台 Windows，跨機 25 人、Quest 實機與廠商硬體仍待現場驗收。
- GitHub Actions 對 `377d9abd` 因帳務或支出上限未啟動任何步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42968212820)

## 2026-11-11 批次移動場地物件

- 控制台 0.31.130 支援勾選多個物件及預覽 X／Z 位移。配置圖以原編號標示目的位置，套用與復原各只需一步。56 項場地編輯專項通過，涵蓋手機版面、選取變更後清除預覽、舊版保留及新配置保存重載。 [操作說明](LAYOUT.md#批次移動場地物件) · [配置圖預覽](../artifacts/console-batch-move-130-publication/placement-batch-move-map.png)
- 直接匯入瀏覽器下載的範本，使用既有 Windows 遊戲 0.50.7 啟動獨立與合併模式。兩輪各有 25 個同機客戶端，五房各核對三件物件的新座標與角度。449 項 Windows 整合檢查通過，六場共 944 格完整回放、50 筆原戰績及伺服器確認，兩批皆完成戰鬥與世界封存。 [原匯出範本](../artifacts/console-batch-move-130-publication/placement-batch-move-template.json) · [原生驗收](../artifacts/server-package-checks/run-baff5a6aa1a14b4c838b9d05cdefb20a/checks.json)
- 111 項 Node、從交付 ZIP 解壓執行的 951 項 Chromium 及 107 項 Windows 管理包檢查均通過。ZIP 562 檔逐一核對，管理包與遊戲驗收清理後 C／F 快照分別有 27、254 檔雜湊相符。 [交付包](WINDOWS_CONTROL_PACKAGE.md) · [核對摘要](../artifacts/placement-move-0.31.130-validation.json)
- GitHub Actions 對 `b9126204` 因帳務或支出上限未啟動任何步驟。跨機 25 人、頭盔與廠商硬體仍待現場驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42966280297)

## 2026-11-11 即時切房的 Windows 原生驗收

- 使用控制台 0.31.129 與 Windows 遊戲 0.50.7。獨立和合併模式各有 25 個同機 Windows 客戶端。主控依序選擇第 1、4、2、5、3 房，兩輪各使用五條分房串流，切換時關閉前四條。每房觀察到畫格前進，畫面顯示的五席統計逐欄符合原伺服器該格，包含實際遊戲內中彈及耗損。 [重跑方式](WORLD_RECORDING.md#從觀戰頁切換目前房間) · [合併場畫面](../artifacts/server-package-checks/run-ef9575ca23964ef5bda1fb9a9978918e/linked-live-rooms/live-room.png)
- 驗收通過 483 項。封存後重讀先前觀戰的十個畫格與統計，全部相符。獨立五場完整回放 1,539 格，合併場 285 格。50 筆原戰績與伺服器確認、場次 CSV 及合併分房 ZIP 相符。活動場次歸零，隔離程序已清理，C／F 254 檔雜湊相符。 [驗收摘要](../artifacts/native-live-rooms-0.31.129-validation.json)
- 首輪五個獨立房已通過畫格核對，驗收工具之後把結束命令重試送到錯誤路徑而退出。修正工具後使用新隔離場次重跑，首輪結果保留。GitHub Actions 對 `1e954888` 因帳務或支出上限未執行。跨機 25 人、頭盔及廠商硬體仍待現場驗收。 [首次測試](../artifacts/server-package-checks/run-31d416c258be4b98b511a13265e8f3a3/stage.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42965334311)

## 2026-11-11 觀戰頁直接切換目前房間

- 控制台 0.31.129 提供主控房間入口。獨立模式可直接切換各自錄製，合併模式沿用同一場次，只讀取選定房間的場景與統計。選取後開啟上帝俯視，並標示目前觀戰房間。 [操作說明](WORLD_RECORDING.md#從觀戰頁切換目前房間)
- 使用隔離 API 與 Chromium 核對房間與錄製來源、房控權限、合併模式的分房統計及手機版面。若房間已結束或來源不符，保留原畫面。專項 29 項通過。 [專項結果](../artifacts/console-live-rooms-129-final-publication/checks.json)
- 111 項 Node、從交付 ZIP 解壓執行的 937 項 Chromium 及 107 項 Windows 管理包檢查通過。ZIP 559 檔逐一核對，Windows 管理測試關閉後 C／F 27 檔雜湊相符。最終包使用 `5f08bcbd`，預覽包及因舊回條檔名衝突而未完成的封裝候選均保留。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [驗證摘要](../artifacts/live-rooms-0.31.129-validation.json)
- GitHub Actions 對 `d9a58ee0` 和 `5f08bcbd` 因帳務或支出上限未啟動任何步驟。視窗回歸使用瀏覽器與測試發布的快照，跨機、頭盔及廠商硬體仍待現場驗收。 [初版 GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42963458604) · [交付版 GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42963585426)

## 2026-11-11 五房批次視窗的 25 席同機驗收

- 以遊戲伺服器 0.50.7、啟動器 1.20 及管理包 0.31.128 操作實際 WinForms 視窗。兩次均用 Enter 核對第四版計畫、勾選來源紀錄並用 Alt+S 啟動。合併模式啟動一個伺服器與一個 UDP 端點，獨立模式啟動五個伺服器與五個端點，實際公告皆符合原計畫。 [重跑方式](WINDOWS_SERVER_PACKAGE.md#重跑五房視窗驗收)
- 每種模式在同一台 Windows 電腦啟動 25 個模擬玩家端。管理 API 開始任務後，兩種模式都同時確認五房各五席進入執行中。結束後核對 50 筆原戰績及伺服器確認、6 份 CSV、543 格世界紀錄及六場戰鬥與世界封存。兩個視窗正常關閉，隔離程序已清理，C／F 共 94 個快照檔案雜湊相符。 [驗收摘要](../artifacts/server-venue-gui-0507-validation.json)
- 首次測試在管理服務啟動前讀取簽章檔而中止，保留該場失敗紀錄。修正驗收工具的讀取時機後重跑，10 項伺服器封裝及 92 項場館證據測試通過。GitHub Actions 對 `31551184` 因帳務或支出上限未啟動任何步驟。 [首次測試](../artifacts/server-venue-gui/run-0c350e379a4645c5ab998c5b07042d1e/stages.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42962626541)
- 本輪涵蓋短場啟動、入場、雙封存及結果送達。跨機 25 人、玩家持續操作、頭盔實機與廠商硬體仍待現場驗收。

## 2026-11-11 將歷史任務保存為下一版

- 控制台 0.31.128 可從任務版本比較將選定舊版的完整內容追加為下一版。確認視窗列出來源、接續版本及預計版號。當前草稿、物件復原紀錄、已選開場版本及既有場次保留原內容。 [操作說明](MISSION_VERSIONS.md#將歷史版本保存為下一版)
- 真 API 與 Chromium 驗證取消、同時修訂及回應遺失。確認視窗開啟時若另一位主控先保存，第 4 版的原請求被拒絕。重新整理後以第 5 版為基準將第 1 版完整內容存成第 6 版。即使第 7 版已存在，重試仍以原請求 ID 確認同一個第 6 版。 [專項 50 項](../artifacts/console-mission-restore-128-publication/checks.json)
- 111 項 Node、從 ZIP 解壓執行的 929 項 Chromium 檢查及 107 項 Windows 管理包檢查均通過。ZIP 559 檔逐一與解壓結果比對，管理測試清理後 C／F 27 檔雜湊相符。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [驗證摘要](../artifacts/mission-restore-0.31.128-validation.json)
- GitHub Actions 對 `38c656be` 因帳務或支出上限未啟動任何步驟。本輪驗證使用管理服務與瀏覽器，跨機 25 人、頭盔及廠商硬體仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42960724885)

## 2026-11-11 Windows 伺服器 0.50.7 單房視窗複驗

- 使用既有 Windows 遊戲伺服器 0.50.7、啟動器 1.20 和管理控制台 0.31.127。兩場從 WinForms 貼上隔離實例的完整路徑、載入兩房、核對房間一及任務版本、設定 UDP 埠，再用鍵盤啟動。測試程式以管理 API 開始與結束任務，兩場都等雙封存與原生程序停止後從視窗關閉，退出碼皆為 0。 [鍵盤操作](WINDOWS_SERVER_PACKAGE.md#選檔啟動及結算驗收)
- 第一場核對 463 格世界紀錄，名冊有一席，未啟動玩家端。第二場在視窗啟用來源紀錄，一名同機 Windows 模擬玩家連線。伺服器觀察到的 UDP 來源、原戰績與一份伺服器確認回條相符，世界紀錄封存至第 218 格，沒有待確認的世界幀。 [第一場](../artifacts/server-gui/run-00c7f690d70946ebab2ce0ada5429d4c/checks.json) · [同機來源與戰績](../artifacts/server-gui/run-00f28fc026c04d788d09273ce796a48c/field-results.json)
- 另一次開啟系統選檔對話框時，檔名欄兩次點擊由 `PickerHost.exe` 攔截，該次未選檔、未啟動伺服器，退出碼為 1。三次測試均已清理，C／F 快照分別核對 14、16、9 檔。系統選檔、跨機 25 人、頭盔與廠商硬體仍待驗收。 [選檔阻擋](../artifacts/server-gui/run-f651c72a83894de681badf777efe94c1/gui-blocker.json) · [同機場清理](../artifacts/server-gui/run-00f28fc026c04d788d09273ce796a48c/cleanup.json)

## 2026-11-11 Quest 收尾以原伺服器紀錄核對來源

- 場館驗收的 `questCaptures` 可使用部署時的 `deviceMap`。工具從每席原 Quest 日誌的最後連線取得伺服器確認的 UDP 來源，核對映射席位、不同私有 IPv4、原遊戲埠與封存戰績。摘要標示 `questCaptureAddressSource=server-observed`。選用 `networkPlan` 時仍會核對現場獨立記錄的 IPv4。 [操作說明](EXTERNAL_CLIENTS.md#以原-quest-裝置對照表驗收收尾)
- 以獨立和合併模式各五個模擬 Quest 席位的原擷取與重試資料驗證，核對結果與明列 IPv4 的驗收一致。再搭配每場 20 個 Windows 席位的收件 ZIP 驗證混合流程，兩模式各核對 25 筆模擬戰績確認。原 Quest 報告與日誌各八檔雜湊保持。 [驗證摘要](../artifacts/quest-observed-sources-0507/validation.json)
- 重複的 Quest 來源 IPv4、伺服器自身位址及錯誤連線埠均遭拒絕。上一輪原 Windows 收件與六批分階段總驗收逐位元重驗相符。92 項場館 Python 測試與 9 項 Quest UDP 預檢測試通過。
- GitHub Actions 在 `5cc7730d` 因帳務或支出上限未啟動任何步驟。兩種混合場驗收使用模擬 Quest 與伺服器來源資料。實體跨機、頭盔及廠商硬體仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42958787704)

## 2026-11-11 Quest 日誌擷取中斷後逐席重試

- `capture-quest-field-log.py --retry-incomplete` 會用原部署 ZIP、裝置對照表與首次擷取報告核對房席、場次及連線埠，只對失敗席位重新讀取 logcat。重試使用新資料夾，保留首次已完成的原日誌、擷取報告與 `.partial`。 [重試操作](QUEST3.md#重試未完成的-quest-擷取席位)
- 五房驗收可同時讀取部分完成與重試報告，核對每份原報告的席數和完成狀態，逐席驗證成功的日誌雜湊、原入場及伺服器戰績確認。成功的席位須剛好覆蓋原網路計畫，重複的完整擷取會拒絕。摘要另列未完成報告及失敗嘗試次數。 [驗收清單](EXTERNAL_CLIENTS.md#直接使用-quest-批次擷取報告)
- 模擬 ADB 在獨立與合併模式各產出四席完整日誌與一席 `.partial`，重試只擷取各自缺少的一席。兩種模式都驗證五席 Quest 證據，首次報告與部分日誌雜湊相符。只交首次報告會失敗。另以實際 CLI 及 PowerShell 部署解析器驗證混合場重試第 2 房第 3 席，錯場次或錯埠在擷取前拒絕。 [模擬驗證](../artifacts/quest-capture-retry-0507/validation.json)
- 90 項場館 Python 測試與兩項 Quest 擷取命令列測試通過，含完整 25 席模擬擷取。GitHub Actions 在 `970771e4` 因帳務或支出上限未啟動任何步驟。Quest 3／VIVE XR 實機、跨機與廠商硬體仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42957961103)

## 2026-11-11 Windows 玩家驗收 ZIP 收件核對

- 五房驗收清單可設定 `windowsEvidenceDirectory`，直接從原 ZIP 的場次、入場識別、退出報告及伺服器戰績確認配回席位。`--inspect-windows-inbox` 列出已收、缺件及衝突檔案；缺件時回傳退出碼 1。IPv4 取自原伺服器觀察的 UDP 來源。混合場可沿用 Windows 電腦對照表，Quest 證據依原流程核對。 [收件操作](EXTERNAL_CLIENTS.md#按收件資料夾找缺件及錯批)
- 使用上一輪 0.50.7 Windows 同機封存的 50 份原 ZIP，調整檔名及放入順序後，獨立與合併各 25 席均完成配對。兩份完整驗收摘要與原逐檔驗收逐位元相同，先前六批總驗收輸出亦相同。 [驗證摘要](../artifacts/windows-field-inbox-0507/validation.json)
- 不完整收件資料夾精確列出第 5 房第 4、5 席缺件，並分別列出重複席位、其他場次、配錯的退出報告及不可讀 ZIP。完整驗收拒絕該資料夾。89 項 Python 測試通過，含混合名冊、Quest 檔待補及伺服器逾時的測試。 [缺件範例](../artifacts/windows-field-inbox-0507/incomplete-inbox-status.json)
- GitHub Actions 在 `d10560ee` 因帳務或支出上限未啟動任何步驟。人工視窗、實體跨機、頭盔與廠商硬體仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42956908589)

## 2026-11-11 Windows 玩家驗收 ZIP

- 玩家啟動器 1.10 在核對發行、收到最終戰績、結束斷線且玩家程序以退出碼 0 結束後，封裝 `player.log` 與 `launch-report.json`。封裝前以關閉後的原日誌核對退出報告雜湊。視窗從本次紀錄資料夾取出 `player-evidence.zip`，命令列可用 `--evidence-zip`。 [玩家端操作](WINDOWS_PLAYER_PACKAGE.md#依場館發行報告核對玩家包)
- 主控可直接在原驗收清單填 `evidenceZip`，工具逐席核對原入場、原發行、日誌雜湊和伺服器戰績確認。異常副本中的其他場次 ZIP、配錯席位的退出報告、改動日誌及額外成員均遭拒絕。 [主控操作](EXTERNAL_CLIENTS.md#收集-windows-玩家驗收-zip)
- 原 Windows 0.50.7 的獨立與合併模式各有 25 個同機玩家端，540 項通過。測試工具在已收到原戰績及斷線後結束自有玩家程序，50 份原生 ZIP 只含兩份逐位元相同的原檔，確認未含該席原票券位元組。由 F 槽 ZIP 重驗與散檔摘要一致，含 921 格回放、六場原雙封存及 50 筆伺服器確認。C／F 273 檔一致，活動場次及殘留程序為零。舊六批分階段總驗收的輸出相同。 [驗證摘要](../artifacts/windows-seat-evidence-0507/validation.json)
- 45 項解壓套件、17 項 WinForms 事件及 87 項場館 Python 測試通過。WinForms 驗證包含缺少 OpenXR 執行環境時保留退出報告與日誌，且未產生驗收 ZIP。人工視窗收尾、跨機真人及頭盔仍待驗。GitHub Actions 在 `79e0b52e` 因帳務或支出上限未啟動任何步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42955693336)

## 2026-11-11 五房分階段總驗收

- `verify-field-results.py --venue-stages` 一次重驗獨立與合併模式各自的 5、10、25 席原始封存。核對各模式的原場次時間順序、每批同時在線區間、同一份發行報告及不同的原結束回條、場次、世界來源與入場識別。輸出包含總清單及六份批次清單的原始位元組雜湊。 [總驗收操作](EXTERNAL_CLIENTS.md#一次驗收兩種模式的三個階段)
- 唯讀重驗 F 槽六批 0.50.7 Windows 同機資料，核對 18 份原世界日誌、18 份原戰鬥日誌及 80 筆伺服器戰績確認。要求 2,000 毫秒同時在線，六批最短的共同區間為 8,250 毫秒。六份個別驗收輸出與原報告相同。 [總清單](../artifacts/venue-stage-series-0507/stages.json) · [總驗收結果](../artifacts/venue-stage-series-0507/stages-results.json)
- 六份由原場次衍生的驗收副本均被拒絕，涵蓋缺批、重複階段、發行報告位元組改變、原日誌位元組改變、誤標直連及不足 9,000 毫秒共同在線。86 項 Python 測試通過，另含同批識別重用、時間順序及每席不同直連來源的拒絕案例。 [拒絕案例](../artifacts/venue-stage-series-0507/source-validation.json)
- GitHub Actions 在 `a4165409` 因帳務或支出上限未啟動任何步驟。這一輪重驗先前的同機原始封存。實體跨機、真人分階段、頭盔與廠商硬體仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42954486962)

## 2026-11-11 五房 5、10、25 人分階段驗收

- 場館驗收清單可指定 `expectedPlayersPerRoom`。省略時沿用每房 5 席與全館 25 席。核對原場次、名冊、UDP 來源、戰績確認與原封存時，合併場也逐房比對席數。測試涵蓋總數正確但席位分配錯誤的拒絕案例。 [現場操作](EXTERNAL_CLIENTS.md#分階段驗收-5-人與-10-人)
- 使用原 Windows 0.50.7 與玩家啟動器 1.9 套件，三個階段各完成獨立與合併模式。5 人階段通過 352 項與 832 格，10 人階段通過 392 項與 936 格，25 人階段通過 520 項與 1,149 格。共 80 筆伺服器戰績確認、18 場原世界與戰鬥雙封存，並逐場核對發行清單、批次戰績與 CSV。三批同時在線最短的共同區間為 8,250 毫秒。 [驗證摘要](../artifacts/venue-staged-field-0507/validation.json)
- 5 與 10 人階段均被預設滿席驗收及全員參與開始閘門拒絕，兩種模式可用一般全館開始。25 人階段沿用預設驗收，且全員參與閘門以原 Preparing 畫格接受兩種模式。原 25 席封存以新工具重查，兩份摘要與原件相同。
- 封裝控制台實際下載原場館驗收 ZIP 與戰績回條，各 9 次，含切換到較新的批次後重取前一批。三輪測試程序及活動場次均為零，C／F 103、133、223 檔逐檔相符。F 槽另有六份相對路徑清單，逐份重跑的摘要與本機原生排演一致。 [5 人獨立清單](../artifacts/venue-staged-field-0507/5-independent-manifest.json) · [10 人合併清單](../artifacts/venue-staged-field-0507/10-linked-manifest.json)
- 本機場館驗收 83 與 Windows 伺服器套件 10 項 Python 測試通過。GitHub Actions 在 `c0abefc9` 因帳務或支出上限未啟動任何步驟。上述排演使用同一台 Windows 電腦。實體跨機、真人分階段、頭盔及廠商硬體另待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42952962643)

## 2026-11-11 Windows 玩家視窗的發行核對與紀錄

- 玩家啟動器 1.9 可從圖形介面載入主控發行報告。清單不同或已核對的報告被改動時會停止啟動。核對成功後仍在實際啟動時逐檔檢查。玩家關閉遊戲後可開啟本次私有紀錄資料夾，將原日誌與退出報告一併交回主控。 [操作與套件](WINDOWS_PLAYER_PACKAGE.md#依場館發行報告核對玩家包)
- 41 項解壓後套件檢查及 16 項實際 WinForms 事件檢查通過。後者執行已封裝的視窗處理程式及真 Unity 子程序，以缺少 OpenXR 執行環境驗證退出碼 2、同程序與兩份原始雜湊。兩次測試工具早期失敗各保留原紀錄，修正 AppDomain 路徑結尾與 Unity 標準輸出混入測試結果。人工操作及 OpenXR 頭盔入場待實機。 [視窗驗證](../artifacts/player-package-checks/20261111-111419-233d7006/release-form-checks.json)
- 三包命令列同機驗收通過 444 項。獨立及合併各 25 席，核對 50 筆伺服器戰績確認、六個世界與戰鬥雙封存、943 格回放及 50 份與新版清單相符的原程序紀錄。活動場次及殘留程序為零，C／F 221 檔雜湊相符。使用原 Windows 與 Quest 0.50.7 遊戲來源，Windows 玩家與伺服器 324 個遊戲檔逐檔相同。 [驗證摘要](../artifacts/player-release-form-1.9/validation.json) · [新發行報告](../artifacts/venue-release-0.50.7-player-1.9.json)
- GitHub Actions 在 `d8bf4ac3` 上因帳戶付款或支出上限未啟動任何步驟。跨機 25 席、Quest 3／VIVE XR 實機及廠商硬體整合仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42951573694)

## 2026-11-11 回放檔頭與原場景設定驗收

- 封存驗收將原始 `.worldlog` 的完整檔頭與啟動器封存報告比對，涵蓋每個擺設物件的位置與角度、任務時鐘、校正、規則與呈現版本。物件座標依原 `System.Single` 值比較，舊檔缺少的能力欄位依原定義以零比較。單場及五房驗收都使用同一套比對。 [操作說明](EXTERNAL_CLIENTS.md#核對原始回放檔頭與封存)
- 從已封存且含八個場景物件的原場次各複製一份回放，分別更動物件位置、角度、任務時長或素材版本。四份副本各重算檔頭校驗碼，後續記錄逐位元相同。原工具四份均接受，新工具均拒絕，原檔在兩版皆通過。 [原始檔對照](../artifacts/world-header-field-0507/native-header-mutations.json)
- 以 Windows 0.50.7 的玩家與伺服器套件及原管理套件重跑，獨立五房與合併各 25 個同機玩家端。478 項通過，核對六份回放與六份戰鬥封存、915 格、80 筆場景物件與 50 筆原伺服器戰績確認。活動場次與殘留程序為零，C／F 221 檔雜湊相符。0.50.6 原封存六份也通過唯讀重查。 [驗證摘要](../artifacts/world-header-field-0507/validation.json)
- 首次整館驗證遇到清單讀取器的 `Decimal` 座標被拒絕。修正後同一批五份獨立房封存通過唯讀重查，原失敗與 C／F 130 檔保留。場館驗收 81、回放 14、姿態連續性 10 項 Python 測試通過。GitHub 在 `5d75e647` 上因帳戶付款或支出上限未啟動任何步驟。 [首次執行](../artifacts/world-header-field-0507/native-before-decimal.log) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42950059229)
- 玩家圖形啟動器複驗時仍被 Windows 防火牆提示遮住。本次完成同機套件與封存驗收，跨機 25 席、Quest 3／VIVE XR 實機及廠商硬體整合另待驗收。

## 2026-11-11 Windows Unity 編輯器連線限制為本機

- Windows 0.50.6 的原執行檔在遊戲連線啟動前監聽所有介面的 TCP 並發布 Unity 發現廣播。只移除設定或將模式寫成 `None` 都仍會監聽。同一執行檔改為本機監聽並停用廣播後，實際量測只剩 `127.0.0.1` 的 TCP 監聽。 [原對照](../artifacts/windows-local-profiler-0507/results.json) · [本機監聽對照](../artifacts/windows-local-profiler-0507/local-results.json)
- Windows 0.50.7 在建置時套用本機監聽與停用廣播。解壓的原 0.50.6 包遭新增的監聽檢查拒絕，新包通過全部 40 項檢查，含缺少 OpenXR 執行環境時在入場前退出。合併場伺服器在實際執行時以指定網卡監聽遊戲 UDP、以本機監聽 Unity 編輯器 TCP。 [舊包量測](../artifacts/player-package-checks/20261111-104143-c213fa07/local-profiler.json) · [新包量測](../artifacts/player-package-checks/20261111-104705-59cf5b5e/local-profiler.json) · [伺服器量測](../artifacts/windows-local-profiler-0507/linked-server-sockets.json)
- OpenXR 模擬及桌面兩席通過 82 項、116 格回放與兩份戰績。獨立五房與合併各 25 個同機玩家端通過 399 項、954 格回放及 50 份戰績確認。C／F 分別核對 42 與 219 檔，程序均已清理。模擬場的補充取樣在玩家斷線後取得，實際遊戲監聽以合併場就緒時的資料為準。 [模擬](../artifacts/server-package-checks/run-dc7dc71d87494ea59fe2e0d4c9323bcf/evidence.json) · [雙模式](../artifacts/server-package-checks/run-7e4fe46a9d5a4eb196e16e652f316c8a/evidence.json)
- Unity 273 項 EditMode 檢查通過。Windows 及 Quest 0.50.7／72 同源並核對原網路識別，Windows 兩包核對 324 個共用執行檔案。既有防火牆提示及玩家啟動器視窗仍待複驗，跨機真人、頭盔、MR 場地及廠商硬體依原目標繼續驗收。 [核對摘要](../artifacts/windows-local-profiler-0507/validation.json) · [發行核對](../artifacts/venue-release-0.50.7-local-profiler.json)
- 功能來源 `a4ed5f01` 已推送，建置腳本只與 Git 相差換行，版本設定和玩家檢查腳本逐位元組相符。GitHub Actions `42948735527` 的 job `130287713995` 因帳務或支出上限未啟動。 [來源核對](../artifacts/windows-local-profiler-0507/source-validation.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42948735527)

## 2026-11-11 主控下載環境與敵軍批次

- 控制台 0.31.127 可從兩種批次區塊下載畫面使用的原 `/api/venue/phase` JSON。檔名含原批次 ID，主控重新登入後也可下載仍列為最近一批的已結束場次資料。 [操作方式](EXTERNAL_CLIENTS.md#核對五房環境與敵軍指令的執行畫格)
- 用實際解壓的管理包在獨立五房與合併場各運行 25 個同機 Windows 玩家端。Chromium 下載的四個 JSON 與原 API 回覆逐位元組相符，直接納入各場封存驗收。506 項檢查、1,830 格完整回放、50 份原戰績確認通過，程序清理完成，C／F 221 檔相符。 [原生結果](../artifacts/server-package-checks/run-e3383a7378ce461aaab4db0307f2d773/evidence.json) · [下載及來源核對](../artifacts/venue-setting-download-127/validation.json)
- 管理包 107 項檢查、C／F 27 檔相符，封裝 7 項及封存操作的 Chromium 專項 100 項通過。首次專項的舊斷言計算整個區塊的按鈕數，新增下載按鈕後失敗。把選取器限定為原回放按鈕，再重跑全部專項。 [管理包驗證](../artifacts/control-package-checks/run-a41755a566074d9b961be0648a1ba601/checks.json) · [瀏覽器專項](../artifacts/console-venue-setting-download-127-final/checks.json)
- 完整回歸通過 111 項 Node 測試與 920 項 Chromium 檢查。首輪 Node 測試通過，但相對輸出路徑從 pnpm 子目錄解析，瀏覽器未啟動。以專案的絕對輸出路徑重跑後通過。 [完整回歸](../artifacts/console-venue-setting-full-127/checks.json)
- Windows／Quest 發行核對使用遊戲 0.50.6 及新版管理包。玩家啟動器視窗、跨機真人、頭盔、MR 場地及廠商硬體依原驗收範圍續驗。 [發行核對](../artifacts/venue-release-0.50.6-console-127.json)
- 發行來源為 `ac6ed21f`，最終驗證來源為 `d355174c`。解壓的 HTML 與 JavaScript 及凍結的測試來源與對應 Git 提交逐位元組相符。GitHub Actions `42946903308` 的 job `130281773299` 因帳務或支出上限未啟動。 [來源核對](../artifacts/venue-setting-download-127/source-validation.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42946903308)

## 2026-11-11 五房環境與敵軍指令的封存核對

- `verify-field-results.py` 可用原主控 `/api/venue/phase` JSON 核對環境及敵軍策略。每個原場次須在封存世界日誌中保存同一管理序號的執行畫格。摘要列出每批指令及各場回放格。 [操作方式](EXTERNAL_CLIENTS.md#核對五房環境與敵軍指令的執行畫格)
- Windows 0.50.6、玩家啟動器 1.8、伺服器啟動器 1.20 在同一台電腦的私有 IPv4 各運行 25 席。獨立五房及合併場各核對四批指令，合計 24 個原執行畫格。490 項原生檢查、1,670 格完整回放、50 份原戰績與伺服器確認通過。C／F 221 檔逐一相符，程序清理完成。 [原生結果](../artifacts/server-package-checks/run-bd83049719e447479afc92074bca520d/evidence.json) · [F 槽副本重查](../artifacts/venue-control-batches-0506/native-readback-validation.json)
- 80 項 Python 驗證通過。首輪新增測試讓準備格序號高於後續執行格，原驗證正確拒絕，修正測試資料後重跑全組。兩種模式各用修改過的天氣報告副本重查，均在原執行畫格的值不符時拒絕。 [測試結果](../artifacts/venue-control-batches-0506/python-final.log)
- 沿用既有 Windows 與 Quest 發行檔。本輪使用同機玩家端與主控 API 操作。玩家啟動器視窗複驗、跨機真人、頭盔、MR 場地與廠商硬體仍待驗收。
- 功能來源 `7c14e9e4` 已推送。驗收工具、原生測試及最終 Python 測試與 Git 逐位元組相符。GitHub Actions `42945386529` 的 job `130276809944` 因帳務或支出上限未啟動。 [來源核對](../artifacts/venue-control-batches-0506/source-validation.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42945386529)

## 2026-11-11 玩家啟動器的桌面與 OpenXR 模式

- Windows 玩家啟動器 1.8 預選桌面模式。視窗內可用 Alt+D 選桌面、Alt+O 選 OpenXR、Alt+S 啟動，貼上連線檔路徑後可按 Enter 載入。遊戲執行期間鎖定模式和連線檔，程序退出後可在同一視窗重試。 [玩家操作](WINDOWS_PLAYER_PACKAGE.md#玩家操作)
- 實際編譯的 WinForms 類別通過 9 項模式、Enter 和連線檔狀態檢查。原連線檔與狀態監測各通過 36、26 項。首場實際視窗顯示預選桌面，Windows 防火牆提示遮住視窗，測試等待玩家啟動逾時，未開啟玩家程序。原測試保持失敗，程序清理及 C／F 14 檔相符。 [檢查摘要](../artifacts/player-mode-18/validation.json) · [視窗測試清理](../artifacts/desktop-venue/20261111-100051-c4e7fc32/external-ui/native-cleanup.json)
- 解壓後的啟動器通過 39 項 CLI 檢查，包含缺少 OpenXR 執行環境時在入場前退出。新版啟動器以 CLI 執行 OpenXR 模擬與桌面席，通過 82 項、106 格封存回放、兩席原戰績、CSV 及原確認，C／F 42 檔相符。實際視窗選模式後入場仍待複驗。 [CLI 核對](../artifacts/player-package-checks/20261111-100545-3f9a9f1d/openxr-status.json) · [OpenXR 模擬](../artifacts/server-package-checks/run-81f7b3e4c73549db86f3034650bcaf2b/evidence.json)
- 新包的 331 個清單檔案中有 329 個與前版相符，使用同一個 0.50.6 Windows 遊戲及 Quest APK。新發行報告核對 324 個玩家與伺服器共用檔案。 [發行核對](../artifacts/venue-release-0.50.6-player-1.8.json)
- 功能來源 `a957c880` 已推送，啟動器、封裝工具及驗證腳本與 Git 逐位元組相符。GitHub Actions `42943934951` 的 job `130272055275` 因帳務或支出上限未啟動。 [來源核對](../artifacts/player-mode-18/source-validation.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42943934951)

## 2026-11-11 Windows 桌面與 OpenXR 啟動

- Windows 0.50.6 在明確選用 OpenXR 時才探測執行環境。Windows 建置排除只供 Android 使用的 Meta OpenXR 管理元件引用，建置後還原原設定檔。0.50.5 的對照只移除原生預載設定，頭盔外形錯誤消失，12 筆序列化錯誤仍在。第一個 0.50.6 執行檔的兩種錯誤均消失，但 Unity 把暫時移除的引用寫成空值，封裝拒絕了該候選。最終建置逐位元組還原原設定，通過來源和封裝核對。 [原對照](../artifacts/desktop-xr-startup-0506/0505-boot-ab/evidence.json) · [最終核對](../artifacts/desktop-xr-startup-0506/validation.json)
- 解壓後的 Windows 玩家端顯示房間 HUD，畫面沒有啟動診斷遮罩。實際鍵盤輸入經伺服器接受，兩份原戰績、送達確認及雙封存相符。4 項檢查通過，C／F 14 檔逐一相符。 [桌面操作](../artifacts/desktop-debrief/20261111-094907-aff2be9e/summary.json)
- 解壓後的伺服器及玩家包通過 82 項 OpenXR 模擬及啟動器檢查。OpenXR 在傳輸與入場前就緒，追蹤中斷、恢復和重新按下扳機在 111 格原回放中相符。C／F 42 檔逐一相符。玩家包另外通過 39 項檢查，執行環境缺失時回報 `OpenXRUnavailable` 並以代碼 2 退出。 [OpenXR 模擬](../artifacts/server-package-checks/run-351e0d5593984310bdb937bfc5b7b367/evidence.json) · [缺失執行環境](../artifacts/player-package-checks/20261111-095152-40f1e3b0/openxr-status.json)
- Unity 273 項 EditMode 檢查通過。Windows 玩家與伺服器共用的 324 個執行檔案相符，Quest 0.50.6／71 APK 保有原生 OpenXR 預載。兩平台的來源指紋與場景、預製物件網路識別相符。Quest 3、VIVE XR、雙顯示卡組合、跨機真人及廠商硬體仍待現場驗收。 [發行核對](../artifacts/venue-release-0.50.6-xr-startup.json)
- 功能來源 `c3fe7cc1` 已推送。建置用的 ProjectBuilder 原檔與 Git 只差換行，版本及 OpenXR 設定檔逐位元組相符。GitHub Actions `42942315444` 的 job `130266796749` 因帳務或支出上限未啟動。 [來源核對](../artifacts/desktop-xr-startup-0506/source-validation.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42942315444)

## 2026-11-11 五房批次啟動鍵盤流程

- Windows 啟動器 1.20 支援 Alt+V 開啟五房批次視窗、在計畫路徑欄按 Enter 核對，以及 Alt+S 啟動。整輪結束或計畫重核失敗後，視窗會清除舊清單。 [操作方式](WINDOWS_SERVER_PACKAGE.md#從-windows-視窗核對並啟動)
- 實際解壓包視窗 `run-0265f1863fc5403b9ca7dd33b9e42b89` 以鍵盤核對第四版計畫。核對後更換第五房 UDP 埠，原視窗拒絕啟動並清除舊清單，五場均未登記來源或公告端點。重新核對後以 Alt+S 啟動五房，所有端點與新計畫相符。 [拒絕證據](../artifacts/server-venue-gui/run-0265f1863fc5403b9ca7dd33b9e42b89/stale-plan-rejection.json) · [五房就緒](../artifacts/server-venue-gui/run-0265f1863fc5403b9ca7dd33b9e42b89/venue-ready.json)
- 每房一個同機 Windows 玩家完成入場、測試 API 開始與結束、戰績確認及雙封存。五房共 217 格世界日誌，原伺服器均停止，兩個視窗正常關閉，測試程序已退出，C／F 40 檔逐檔相符。首輪驗證器在 API 啟動前讀取簽章檔而失敗，保留原紀錄並調整讀取時機。 [五房結果](../artifacts/server-venue-gui/run-0265f1863fc5403b9ca7dd33b9e42b89/checks.json)
- 封裝 10 項、清單 51 項及 Framework 59 項通過，涵蓋單場視窗 Enter 載入、按住 Enter 與原選擇規則。新包沿用同版 0.50.5 遊戲，Windows 伺服器及玩家的 323 個共用檔案相符，Quest APK 離線發行核對通過。 [封裝與副本核對](../artifacts/server-venue-keyboard-120-validation.json) · [發行核對](../artifacts/venue-release-0.50.5-server-120.json)
- 功能提交 `721e394b` 的啟動器來源與封裝輸入逐位元組相符。GitHub 長期追蹤已更新。GitHub Actions `42939684319` 的 job `130258254131` 因帳務或支出上限未啟動。 [長期追蹤](https://github.com/peca12968/vr-command-center/issues/1) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42939684319)

## 2026-11-11 伺服器啟動器的鍵盤選房與啟動

- Windows 啟動器 1.19 在單場視窗加入 Alt+R、Alt+P、Alt+S。實際按 Enter 載入管理實例後，先確認未選場時 Alt+S 維持停用，再用 Alt+R 及方向鍵選第 1 房、Alt+P 設定 UDP 埠、Alt+S 啟動。原程序公告正確端點。 [操作方式](SERVER_CATALOG.md)
- 實際解壓包視窗場 `run-58f3717e0f014de0aa62730d7e6b8522` 完成同機 Windows 玩家入場、API 測試開始與結束、戰績伺服器確認、雙封存、235 格世界日誌及 Alt+F4 關閉。測試程序皆退出，C／F 16 檔逐檔相符。 [視窗驗收](../artifacts/server-gui/run-58f3717e0f014de0aa62730d7e6b8522/checks.json)
- 封裝 10 項、清單 51 項及 Framework 59 項通過。首次清單檢查在舊按鈕文字定位失敗，保留原失敗，更新驗證器後通過。兩次清單場的 C／F 快照為 17 與 22 檔。Windows 伺服器及玩家套件的 323 個共用執行檔案相符，並通過同版 Quest 0.50.5 APK 離線發行核對。 [封裝與快照](../artifacts/server-keyboard-119-validation.json) · [發行核對](../artifacts/venue-release-0.50.5-server-119.json)
- 功能提交 `5d5521e9` 的啟動器來源與封裝輸入逐位元組相符。[GitHub 長期追蹤](https://github.com/peca12968/vr-command-center/issues/1) 已更新。GitHub Actions `42938334581` 的 job `130253817200` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42938334581)

## 2026-11-11 長場結束前的環境切換與敵軍回擊

- 長場射擊工具可搭配 `--incoming-fire`，在全部原分批射擊及換彈完成後，讓同一批原玩家接受新敵軍回擊並停火。明確加上 `--incoming-environment` 時，回擊前切為雨夜與閃電設定，確認停火後切為霧天白晝。逐頁對照原環境／敵軍策略時間線與完整回放。回擊發生在長時間操作完成後，持續全程交火另驗。 [操作方式](DESKTOP_ENDURANCE.md#長場射擊後的環境切換與敵軍回擊)
- 31 項射擊／戰績與 22 項封存證據 Python 檢查通過。受傷只允許出現在原攻擊啟用序號之後，必須保留原玩家及正值健康；原中彈、損耗、健康與戰鬥日誌尾界須相符。原世界日誌亦核對雨夜與霧天檢查點。舊的不含回擊排演 `20261111-064615-4ae3699b` 通過新版重查。 [舊場重查](../artifacts/incoming-endurance-prior-readback.json)
- 60 秒雙模式排演 `20261111-082444-5ceed344` 退出碼 0，37 項通過。每席三批目標、六發命中、三次擊殺及三次換彈，六場共 300 次命中、150 次擊殺、75 次敵軍命中與 1,500 點損耗。50 份原戰績及確認、6 份 CSV、4,449 格完整回放相符；原政策時間線各 7 格，第 1 獨立房含暫停／恢復為 9 格。原生與管理程序已退出，C／F 174 檔相符，獨立五房原日誌重查通過。 [原排演](../artifacts/desktop-exercise/20261111-082444-5ceed344/exercise-result.json) · [核對](../artifacts/incoming-endurance-smoke-validation.json) · [原日誌重查](../artifacts/incoming-endurance-smoke-readback.json)
- 本輪沿用 Windows／Quest 0.50.5 與管理包 0.31.126，未重建遊戲或 APK。驗證為同機 Windows 程式產生的輸入，原生畫面／音效、跨機真人、頭盔及廠商硬體仍依完整十一項目標驗收。
- 功能來源 `15539c87` 已推送 GitHub。14 份檢查工具／測試輸入已在長場前凍結，11 份與 Git 逐位元組相符、3 份只差換行。整輪結束後再確認這 14 份輸入、原 API DLL 與玩家建置回條保持。GitHub Actions `42931733893` 的 job `130231897425` 因帳務或支出上限未啟動，步驟為空，仍為失敗。 [來源核對](../artifacts/incoming-endurance-source-validation.json) · [結束後核對](../artifacts/incoming-endurance-final-source-validation.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42931733893)
- 原 900 秒雙模式長場 `20261111-082953-583de9b9` 退出碼 0，37 項通過。先合併 25 席，再獨立五房各 5 席。每席完成 45 批目標、90 發命中、45 次擊殺及 45 次換彈，活動跨度 17,942 至 18,003 刻，最長收集 901.867 秒。受控回擊為各原席位一次中彈，所有玩家最終健康 80。六場共 4,500 發命中、2,250 次擊殺、50 次中彈與 1,000 點損耗。 [原長場結果](../artifacts/desktop-exercise/20261111-082953-583de9b9/exercise-result.json) · [合併子階段紀錄](../artifacts/incoming-endurance-linked-stage.json)
- 六場共 52,639 格完整回放，其中 52,433 格為 Running。828 個來源檢查點、44 個政策時間線格、50 份原戰績及確認、6 份 CSV 與雙封存相符。獨立五房原世界及戰鬥日誌重查通過，每房兩個環境檢查點均相符；原畫格的共同執行區間為 908.743 秒，25 席均有該區間內的確認射擊。活動場次及殘留測試程序歸零後，C／F 的 174 檔逐檔雜湊相符。 [整輪核對](../artifacts/incoming-endurance-long-validation.json) · [原日誌重查](../artifacts/incoming-endurance-long-readback.json)
- [GitHub 長期追蹤](https://github.com/peca12968/vr-command-center/issues/1) 的整理前本文已達 65,536 字元。原文 111,762 bytes 逐位元組封存，遠端 Git 內容與本機相符，原十一項需求及更早封存連結均保留。 [追蹤原文](history/GITHUB_ISSUE_1_2026-11-11.md)

## 2026-11-11 桌面玩家淘汰後的武器請求

- Unity 0.50.5／Android code 70 將存活、身體連線與姿態確認納入桌面和追蹤玩家共用的武器提交條件。保留追蹤玩家放開按鍵後重新允許觸發的原有檢查，伺服器武器規則與 NGO 31 沿用。明確開啟 HUD 診斷時，可核對本機按鍵數與既有提交序號。 [操作及驗證](DESKTOP_WEAPON_INPUT.md)
- 修正前診斷場 `20261111-075500-de5f99b6` 以四次實際鍵盤操作重現淘汰後多送兩筆武器請求，累計數為 0／1／2／2／3／4，退出碼 1 保持。0.50.5 解壓玩家包場 `20261111-080011-af9fb3c5` 完成相同四次實際按鍵，累計數為 0／1／2／2／2／2，退出碼 0。兩場本機按鍵計數均為 0／1／2／2／3／4，淘汰時管理就緒、姿態確認、連線及追蹤旗標均有效。 [修正前](../artifacts/desktop-venue/20261111-075500-de5f99b6/weapon-gate-result.json) · [修正後](../artifacts/desktop-venue/20261111-080011-af9fb3c5/weapon-gate-result.json)
- 兩場均核對原玩家的一發耗彈、五次中彈、100 點損耗及健康 0，原戰績、同一原生連線的伺服器確認、CSV、雙封存與 941／812 格完整回放相符。每場 C／F 執行資料快照 16 檔逐檔相符，兩次驗證使用相同檢查工具，清理無殘留。較早的舊 HUD 工具在等待操作時超過原 1.5 秒來源新鮮度，退出碼 1 及原證據保持。 [核對紀錄](../artifacts/weapon-gate-native-validation.json) · [較早來源逾時](../artifacts/desktop-weapon-gate-ui-baseline.log)
- 真正 Unity Editor 273 項測試全數通過，零跳過。Windows 玩家與伺服器新 ZIP 各核對 330 筆清單，Windows 玩家啟動器 38 項檢查通過。原 0.50.4 Windows、Quest、建置日誌及來源封存在 `unity-0.50.4-before-weapon-gate-20261111-074158`，修正前診斷版本另存。 [Editor 結果](../artifacts/weapon-gate-after-build/editmode-results.xml) · [玩家包](WINDOWS_PLAYER_PACKAGE.md) · [伺服器包](WINDOWS_SERVER_PACKAGE.md)
- Windows 與 Quest 0.50.5 使用相同 `a9caeb4f...` 指紋與原場景／玩家 prefab 網路識別，管理包維持 0.31.126。Quest APK 已核對 ARM64、最低 SDK 32、目標 SDK 35 及 v2 開發簽章，尚未安裝頭盔。保存本次成功 Editor 匯入的 XR Simulation 設定與 GUID 參照及既有 PC 渲染設定序列化更新，個人模擬／Composition Layers 偏好維持忽略。 [同源發行核對](../artifacts/venue-release-0.50.5-weapon-gate.json)
- 解壓 0.50.5 玩家包完成合併 25 席與獨立五房各 5 席的短場射擊及敵軍回擊回歸，場次 `20261111-080817-c8326858` 退出碼 0、37 項通過。六場 2,729 格完整回放、100 發命中、50 次擊殺及 75 次原敵軍命中／1,500 點損耗，與 50 份原戰績、50 次原連線確認及 6 份 CSV 相符。活動場次歸零，C／F 174 檔雜湊相符，測試程序均已退出。來源為同機程式產生的操作輸入，跨機真人、MR 場地、頭盔及廠商硬體仍待現場驗收。 [原多人結果](../artifacts/desktop-exercise/20261111-080817-c8326858/exercise-result.json) · [核對紀錄](../artifacts/weapon-gate-multiplayer-validation.json)
- 功能來源 `489751f9` 已推送 GitHub。709 份 Unity／選定檢查工具輸入凍結保存，698 份入庫來源與該提交相符，其中 592 份逐位元組相同、106 份只差文字換行，11 份個人偏好留在本機封存。GitHub Actions `42929789490` 的 job `130225331336` 因帳務或支出上限未啟動，執行步驟為空，雲端仍為失敗。完整十一項長期目標持續開發。 [來源核對](../artifacts/weapon-gate-source-commit-validation.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42929789490)
- 使用者關閉擷取視窗後，1.18 啟動器成功輸入隔離管理實例路徑並以 Enter 載入，未自選場次。點擊房間選單時兩次由 `PickerHost.exe` 攔截，停止桌面點擊並清理本輪實例，未啟動遊戲伺服器。該場仍為失敗，完整 GUI 開場驗收持續追蹤。 [遮擋紀錄](../artifacts/server-gui/run-fa60524b52494d9b83d80831f09d6972/gui-blocker.json) · [清理](../artifacts/server-gui/run-fa60524b52494d9b83d80831f09d6972/cleanup.json)

## 2026-11-11 掩體與分批射擊長場

- 既有 `--marksmanship` 可搭配 60 或 900 秒 `--endurance`。每房六個標準油桶保留五席正前方的原生敵軍出生位置，各席每週期兩次命中及一擊殺。由正常管理命令補充新目標，原名冊與入場識別持續使用。保存每批命令與來源畫格，完整回放核對原目標、武器事件順序及逐格統計。敵軍採 Hold 且關閉自動攻擊。 [操作方式](DESKTOP_ENDURANCE.md#掩體與分批目標)
- 29 項輸入／戰績與 18 項封存證據 Python 測試通過。60 秒雙模式排演 `20261111-064615-4ae3699b` 退出碼 0，19 項通過。合併場 25 席的三批目標已核對 150 發、150 次命中、75 次擊殺。獨立五房的原戰鬥與世界日誌、原戰績及 CSV 封存重查通過，測試程序清理完畢。六場共 3,745 格回放，C／F 174 檔相符。 [排演結果](../artifacts/desktop-exercise/20261111-064615-4ae3699b/exercise-result.json) · [排演核對](../artifacts/marksmanship-endurance-smoke-validation.json) · [獨立封存重查](../artifacts/marksmanship-endurance-smoke-readback.json)
- 功能來源 `a766af58` 搭配 Windows 0.50.4 及管理包 0.31.126，完成合併與獨立各 25 席、各 900 秒的長場。原場次 `20261111-065021-67ff3e71` 退出碼 0，19 項通過。每席完成 45 批原目標、90 發命中及 45 次擊殺。六場共 52,028 格完整回放，原日誌重算 4,500 發、4,500 次命中、2,250 次擊殺。50 份戰績、50 次原連線確認及 6 份 CSV 相符，合併報告 ZIP 與整場及五房個別 CSV 相符。 [原長場結果](../artifacts/desktop-exercise/20261111-065021-67ff3e71/exercise-result.json) · [完整來源及統計核對](../artifacts/marksmanship-endurance-long-validation.json)
- 2,250 個原生目標識別彼此相異，528 筆補充命令及 792 個來源檢查點與完整回放相符。原世界日誌按 float32 模型精度逐格比對 API 回放。合併場共同執行 900.312 秒，獨立五房共同執行 896.081 秒，每個共同區間均含各原席位的確認射擊。活動場次歸零、測試程序無殘留，C／F 174 檔逐檔雜湊相符，九份檢查工具及原遊戲／API 執行檔雜湊相符。 [獨立原日誌重查](../artifacts/marksmanship-endurance-long-readback.json) · [本輪來源](../artifacts/desktop-0504-marksmanship-inputs.json)
- 本輪為同機自動化輸入、守備且關閉自動攻擊的敵軍。接續驗證敵軍回擊與環境變更的長場，跨機真人、頭盔及廠商硬體仍待現場驗收。GitHub Actions `42918165696` 的 job `130185867895` 因帳務或支出上限未啟動執行步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42918165696)

## 2026-11-11 Windows 0.50.4 雙模式長場驗收

- 使用解壓 Windows 玩家包 0.50.4、管理包 0.31.126 及既有長場工具，五房合併與獨立各執行 900 秒。場次 `20261111-055659-c1a606db` 退出碼 0，18 項通過。兩種模式各 25 個同機玩家端，每席由正常桌面輸入流程提交 90 次射擊及 45 次換彈，活動跨度 17,950 至 18,004 刻。場景採空敵軍。跨機、真人持續操作、頭盔與廠商硬體待現場驗收。 [原驗收結果](../artifacts/desktop-exercise/20261111-055659-c1a606db/exercise-result.json) · [輸入來源](../artifacts/desktop-0504-endurance-inputs.json)
- 六場完整回放依序為合併 8,597 格、獨立 8,541／8,551／8,606／8,577／8,599 格，合計 51,471 格。每位原玩家的 45 個週期均有接受的移動、換彈及精確累計射擊數。原戰鬥日誌重算 4,500 發，與 50 份原戰績、50 次伺服器確認及 6 份 CSV 相符。合併場 25 席共同執行 900.291 秒，獨立五房共同執行 896.010 秒，兩種模式的共同區間均含各原席位的確認射擊。 [合併封存重查](../artifacts/desktop-0504-linked-closure-verification.json) · [獨立封存重查](../artifacts/desktop-0504-independent-closure-verification.json)
- 第 1 房保存 25 格暫停，刻數固定 42。同一保存時間區間，其他四房各自前進。API 回放與原世界日誌逐格按共用 float32 欄位型別比對一致。首個補充比對直接使用 Python 的雙精度 JSON 數字，因來源的 `1.649999976158142` 與 API 的 `1.65` 表示方式而失敗，依 `RecordedVector` 等實際 float 欄位核對後通過。原測試與產品皆沿用本輪來源。原始日誌內有 51,255 格 Running 且 tick 大於零，回放檢查另計六格 Running 的 tick 零起點。 [逐格與來源核對](../artifacts/desktop-0504-endurance-validation.json)
- 所有原程序退出後，活動場次及殘留測試程序均為零，C／F 的 174 檔逐檔雜湊相符，九份檢查工具雜湊相符。首次命令誤填玩家包內路徑，前置檢查在建場前停止，修正後另存完整長場紀錄。舊姿態失效根因持續追蹤。接續擴充有敵軍與掩體的長任務操作，並依場館部署流程推進第二台電腦及實體裝置驗收。 [首輪前置錯誤](../artifacts/desktop-0504-endurance.log) · [長場日誌](../artifacts/desktop-0504-endurance-live.log) · [清理](../artifacts/desktop-exercise/20261111-055659-c1a606db/cleanup.json)

## 2026-11-11 啟動器鍵盤載入管理實例

- Windows 啟動器 1.18 的管理實例路徑欄接受 Enter，送到既有的載入按鈕流程。按住 Enter 的重複鍵會被消耗，讀取期間維持原控制項鎖定、明確選房及啟動資格核對。介面與包內操作說明已加入按鍵提示。 [操作方式](SERVER_CATALOG.md)
- 重新解壓發行包後，51 項待開清單 CLI／API 與 59 項真正 Framework 檢查通過。訊息迴圈測試從路徑控制項的原生 Enter 訊息載入及更新，核對初次明確選房、保留原選取、等待回應時停用、錯誤清除及等候期間關窗。Windows、Quest 與管理包的離線發行一致性核對通過。 [清單驗收](../artifacts/server-catalog/run-893bce33d1b344fd81a8f25968c67cdb/checks.json) · [訊息迴圈](../artifacts/server-catalog/run-893bce33d1b344fd81a8f25968c67cdb/framework-proof.json) · [發行核對](../artifacts/venue-release-0.50.4-server-keyboard.json)
- 實際桌面驗收已列出本次 1.18 視窗，但取得焦點及重新選取的嘗試皆回傳 `GetCursorPos` 存取拒絕 `0x80070005`。這輪停在桌面輸入前，隔離啟動器、管理服務及測試客戶端均已清理。 [桌面錯誤](../artifacts/server-gui/run-d974dcbc7872446abded7efd4c46df58/gui-blocker.json) · [清理](../artifacts/server-gui/run-d974dcbc7872446abded7efd4c46df58/cleanup.json)
- 10 項 Python 封裝測試通過，清單及桌面失敗場的 C／F 快照各 22、9 檔逐檔相符。解壓三包通過 421 項原生檢查，五房獨立及合併各 25 個同機玩家端，六場共 1,527 格完整回放、50 份原戰績、11 份結算 CSV、雙封存與原伺服器確認。第 3 房單人第 105 至 210 格 CSV 與原 5 次受傷及 100 點實際損耗一致。活動場次歸零，清理無殘留，原生 C／F 220 檔相符。跨機、實體頭盔與廠商設備待現場驗收。 [封裝與快照](../artifacts/server-keyboard-package-validation.json) · [原生驗收](../artifacts/server-package-checks/run-424649612a0546c8a4cdad47f22c73eb/checks.json) · [回放與戰績核對](../artifacts/server-keyboard-native-validation.json)
- 功能來源 `41820748`，編譯輸入與 Git 原始碼逐位元組相符，323 個遊戲 runtime 檔案與前版相符。GitHub Actions `42909292501` 的 job `130155381496` 沒有執行步驟，失敗註記為帳務或支出上限。 [來源核對](../artifacts/server-keyboard-source-validation.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42909292501)

## 2026-11-11 片段戰績 CSV 與命中率分子

- 控制台 0.31.126 顯示計入片段命中率的射擊數，並從同一原錄製與選定的起訖格、房間及玩家下載 CSV。報表保留原命中數、分子、實際損耗及保存範圍。未發射時命中率留空，空片段保留範圍列。沿用試算表文字防護與房間權限。舊 0.31.125 解壓包在新增端點回傳 404。 [操作與 API](REPORTS.md#下載指定片段的戰績) · [舊版對照](../artifacts/clip-csv-world-baseline.log)
- Release 零警告，1,101 項核心、825 項 HTTP、107 項管理包通過。來源與解壓包各通過 113 項世界串流，包含逐欄 CSV、原報表範圍、試算表引號與換行、空片段及拒絕錯誤來源。發行來源 `e2a0bc4c` 的 189 個檔案雜湊相符，29 個與 Git 只差換行。Windows 與 Quest 0.50.4 離線發行核對通過。GitHub Actions job `130145764985` 因帳務或支出上限未啟動。 [世界串流](../artifacts/clip-csv-world-package.log) · [來源與 ZIP](../artifacts/clip-csv-source-validation.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42906511353)
- 首輪 Chromium 與 Windows 原生回放皆在下載位元組的測試比對失敗，原紀錄保留。重跑的 Chromium 讀到的網路事件內容為 0 bytes，而下載檔與同一授權端點的二進位回應皆為 444 bytes，含 BOM 且逐位元組相同。測試改用二進位回應比對，保留原請求範圍與欄位斷言，沿用同一發行包。首輪 Windows 原生場已清理，C／F 215 檔相符。 [首輪瀏覽器](../artifacts/clip-csv-full.log) · [首輪原生](../artifacts/clip-csv-native.log) · [重跑位元組證據](../artifacts/console-clip-csv-binary/world-clip-statistics-byte-readback.json)
- 使用者關閉擷取視窗後重驗 WinForms 1.17。測試實例路徑已填入，兩次載入點擊都由 `PickerHost.exe` 攔截。隔離測試停在選房及原生啟動前，啟動器、管理服務及測試客戶端皆已清理，C／F 9 檔相符。 [遮擋紀錄](../artifacts/server-gui/run-8a9c26bf32f348e6a442e67e0bf2f069/gui-blocker.json) · [清理與雜湊](../artifacts/clip-csv-first-runs-validation.json)
- 解壓的 Windows 三包通過 421 項原生檢查。第 3 房控制台下載單人第 115 至 218 格的 CSV。原回放核對 5 次受傷、血量由 100 降至 0，期間未發射，命中率欄位留空。獨立與合併模式各有 25 個同機玩家端，六場共 1,596 格完整回放、50 份戰績、11 份結算 CSV、雙封存及原伺服器確認。活動場次歸零，原生及管理包的 C／F 快照各 220、27 檔相符。跨機玩家、實體頭盔與廠商設備待現場驗收。 [原生驗收](../artifacts/server-package-checks/run-06059370408148f38037e4f7bf6ce1dd/checks.json) · [原回放與 CSV 核對](../artifacts/clip-csv-native-validation.json)
- 解壓管理包通過 111 項 Node 測試與 918 項 Chromium 回歸。片段匯出覆蓋報表範圍、命中率分子、錯誤回應格式和切換房間時取消舊下載。 [瀏覽器核對](../artifacts/clip-csv-full-validation.json)

## 2026-11-11 依任務活動時間對齊獨立房回放

- 控制台 0.31.125 的「同批房間回放」可按原擷取時間或任務活動時間對齊。同批獨立房各自封存後，以保存刻數找不晚於基準、差距最多 10 刻的原畫格。遇到暫停等原因讓同一刻有多格時，使用最早保存格。切回基準房會回到原畫格。鏡頭操作尚未確認時，兩種模式都會保留原房。 [操作與 API](WORLD_RECORDING.md#對齊同批獨立房間的回放)
- 來源與解壓包各通過 21 項 Chromium 專項，包括 UTC 時間不重疊、缺 UTC、無任務時鐘、重複刻數、超出封存範圍及舊回應隔離。舊 0.31.124 解壓包缺少新端點。首輪測試把缺 UTC 的空字串當作 null，後按實際契約驗證。Release 零警告，1,101 項核心、825 項 HTTP、107 項管理包通過。發行來源 `aeaca7bc` 的 188 個檔案雜湊相符，29 個與 Git 只差換行。Windows 與 Quest 0.50.4 離線發行核對通過。GitHub Actions job `130137556317` 因帳務或支出上限未啟動。 [對齊專項](../artifacts/console-mission-time-replay-package/checks.json) · [來源與 ZIP](../artifacts/mission-time-replay-source-validation.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42904134703)
- Windows 三包通過 415 項原生檢查。獨立場的 Chromium 依任務時間從第 1 房第 185 格切到第 2 房第 147 格，兩格皆是第 2 刻，目標為該刻最早保存格。原 UTC 對齊從第 178 格切到第 141 格，時間差 51 毫秒。合併場沿用一份錄製。兩種模式各有 25 個同機玩家端，六場核對 897 格回放、50 份戰績、11 份 CSV、雙封存及原伺服器確認。活動場次歸零，原生及管理包 C／F 各 220、27 檔相符。跨機玩家、實體頭盔與廠商設備待現場驗收。 [原生驗收](../artifacts/server-package-checks/run-46fa72d7d6f347b9b88d6993a7565d00/checks.json) · [原畫格核對](../artifacts/mission-time-replay-native-validation.json)
- 同一解壓包通過 111 項 Node 與 915 項完整 Chromium 回歸。八個任務列表故障均確認各攔截一筆並送達，保存 145 個瀏覽器證據檔。 [完整回歸](../artifacts/console-mission-time-replay-full/checks.json) · [回歸雜湊](../artifacts/mission-time-replay-full-validation.json)

## 2026-11-11 VR 單席連線檔交付前核對

- 控制台 0.31.124 在 VR 場次提供逐席連線檔核對。主控可核對整場，房控只可核對本房。服務用目前入場識別、票券簽章、場次、席位、原公告端點及近期有效畫格判定。畫面顯示票券效期並標記只能同機使用的位址。切換席位或名冊更換時會清除舊結果。舊 0.31.123 解壓包回傳 404，首輪合成畫格缺名冊中的玩家身體亦遭拒，修正測試資料後才通過。 [操作與 API](EXTERNAL_CLIENTS.md#在管理台核對-vr-單席連線檔) · [舊版對照](../artifacts/vr-seat-file-baseline.log) · [首輪測試](../artifacts/vr-seat-file-source.log)
- Release 零警告，1,101 項核心、825 項 HTTP、107 項管理包檢查通過。來源與解壓包各通過 14 項 VR 單席專項及 16 項 MR 部署回歸。發行來源 `0a8b4c37` 的 188 個來源檔雜湊相符，29 個與 Git 只差換行。Windows 與 Quest 0.50.4 離線發行核對通過。GitHub Actions job `130128160802` 因帳務或支出上限未啟動。 [VR 專項](../artifacts/console-vr-seat-file-package-vr-connection-check/checks.json) · [MR 專項](../artifacts/console-vr-seat-file-package-mr-deployment/checks.json) · [來源與 ZIP](../artifacts/vr-seat-file-source-validation.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42901447037)
- Windows 三包通過 377 項原生檢查。從 Chromium 下載的兩份五房 ZIP 逐一核對 50 個原始票券、席位、端點及效期，每種模式都能指出修改的埠。獨立及合併模式各有 25 個同機玩家端用原檔連線，六場共 1,104 格完整回放、50 份原戰績、11 份 CSV、雙封存與伺服器確認。活動場次歸零，原生及管理包 C／F 各 222、27 檔相符。跨機玩家、實體頭盔與廠商硬體仍待現場驗收。 [原生驗收](../artifacts/server-package-checks/run-7918d9ba406c42d39550bebc26b1cf37/checks.json) · [原檔與封存核對](../artifacts/vr-seat-file-native-validation.json)
- 同一解壓包通過 111 項 Node 與 907 項完整 Chromium 回歸。八個任務列表故障均確認各攔截一筆並送達，保存 144 個瀏覽器證據檔。 [完整回歸](../artifacts/console-vr-seat-file-full/checks.json) · [回歸雜湊](../artifacts/vr-seat-file-full-validation.json)

## 2026-11-11 從管理台核對六台操作工作站

- 控制台 0.31.123 在場館 HTTPS 顯示「主控與五房控連線核對」。主控可產生代號，六台各自下載本站簽章回條，主控選取原配置與六份 JSON 後送回原管理程序。沿用實際 TCP 來源、角色、簽章及 15 分鐘期限。可匯入瀏覽器回條或命令列報告。離開場次頁或登出會清除本輪資料。舊 0.31.122 解壓包缺少這個畫面，瀏覽器對照保留。 [操作方式](WINDOWS_CONTROL_PACKAGE.md#核對主控與五房控的直連來源) · [舊版對照](../artifacts/operator-network-browser-baseline.log)
- Windows 解壓包通過 40 項 HTTPS 整合與 17 項 Chromium 專項。六個角色確實從本機場館 IPv4 取得簽章，管理服務拒絕六份相同來源的回條。六台成功畫面使用模擬回應，核心測試另驗六個私有來源的簽章與過期拒絕。原生一場同機 Windows 玩家經 HTTPS 配票及 UDP 入場，遊戲端用指定憑證指紋連接 HTTPS／WSS，核對本房原畫格 21、戰鬥與世界雙封存至第 26 格及一筆原入場戰績確認。HTTP 與 HTTPS 監聽正常關閉，管理包 C／F 27 檔相符。實體六台工作站、跨機玩家、頭盔及廠商硬體仍待現場驗收。 [HTTPS 整合](../artifacts/control-https-checks/run-2b52798a71d541928e959729c22673fd/checks.json) · [瀏覽器專項](../artifacts/control-https-checks/run-2b52798a71d541928e959729c22673fd/workstation-browser-checks.json) · [雜湊核對](../artifacts/operator-network-browser-tls-validation.json)
- Release 零警告，1,101 項核心、825 項 HTTP、11 項命令列工具、107 項管理包通過。發行來源 `1a938458` 的 188 個檔案雜湊相符，29 個與 Git 只差換行。Windows 與 Quest 0.50.4 離線發行核對通過。GitHub Actions job `130121529689` 因帳務或支出上限未啟動。 [發行核對](../artifacts/venue-release-0.50.4-workstation-console.json) · [來源與 ZIP](../artifacts/operator-network-browser-source-validation.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42899545558)
- 同一解壓包通過 111 項 Node 與 896 項完整 Chromium 回歸。核對八個任務列表故障均攔截一筆請求並確認送達，保存 143 個瀏覽器證據檔。 [完整回歸](../artifacts/console-workstation-123-full/checks.json) · [回歸雜湊](../artifacts/operator-network-browser-full-validation.json)

## 2026-11-11 場景旋轉方向與玩家通行邊界

- 舊 0.31.121 解壓包在 Chromium 重現非直角掩體的鏡像。0.31.122 使用遊戲座標轉換後的角度繪製草稿、保存版本與複製預覽。草稿與開場平面圖可顯示玩家中心距牆 0.3 公尺的邊界，以及掩體沿局部 X／Z 擴張 0.3 公尺後的阻擋範圍。圖層預設關閉，配置通過檢查後可勾選，切換時保留任務草稿狀態。 [操作說明](LAYOUT.md#開場前查看保存版本平面圖) · [舊版對照](../artifacts/layout-clearance-baseline.log) · [新版平面圖](../artifacts/console-layout-clearance-package/layout-valid-launch.png)
- 來源 `6804d5d0` 的 Release 零警告，通過 1,101 項核心、825 項 HTTP、111 項 Node 和 107 項管理包檢查。來源與解壓包各通過 44 項場景專項，包含正 45° 沙包、負 30° 油桶，以及旋轉掩體在通行與命中規則下的邊界對照。發行記錄核對 187 個來源檔，其中 29 個與 Git 只差換行。Windows 與 Quest 0.50.4 離線發行核對通過。GitHub Actions job `130110884205` 因帳務或支出上限未啟動。 [場景專項](../artifacts/console-layout-clearance-package/checks.json) · [來源及 ZIP 核對](../artifacts/layout-clearance-source-validation.json) · [離線發行核對](../artifacts/venue-release-0.50.4-layout-clearance.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42896498552)
- Windows 三包通過 386 項原生檢查。獨立及合併模式各有 25 個同機玩家端同時連線，六場回放合計 768 格，核對 50 份戰績、11 份 CSV、雙封存及原伺服器確認。各房封存世界保留旋轉沙包與油桶的原座標及角度。每場的五席皆使用 0.125 公尺細格預覽原窄缺口。活動場次歸零，原生及管理包 C／F 各 218、27 檔相符。沿用 0.50.4 的遊戲執行檔，跨機、實體頭盔與廠商設備待實測。 [原生驗收](../artifacts/server-package-checks/run-1e1530449daa461c80a494bbb7d16455/checks.json) · [場景、封存與雜湊核對](../artifacts/layout-clearance-native-validation.json)
- 同一解壓包通過 896 項完整 Chromium 回歸，八個任務列表故障均攔截一筆請求並確認送達。保存 143 個瀏覽器證據檔，核對結果、日誌及原 ZIP 雜湊。 [完整回歸](../artifacts/console-layout-clearance-full/checks.json) · [瀏覽器證據核對](../artifacts/layout-clearance-browser-validation.json)

## 2026-11-11 觀戰錄製身分與姿態標示

- 0.31.121 的即時觀戰及回放會先核對標頭，後續狀態與封存訊息須沿用同一來源及房間。即時狀態序號倒退或撤回已接受的封存會停止該次串流，保留原畫格及鏡頭。0.31.120 解壓包可重現外來狀態把原錄製誤標為封存。新版另標記最後保存格，房間卡改顯示該格存活玩家的有效姿態數，角色保留頭手來源與淘汰狀態。 [操作說明](WORLD_RECORDING.md#即時觀戰斷線後重新連接) · [舊版對照](../artifacts/observer-integrity-baseline.log)
- Release 零警告，1,100 項核心、825 項 HTTP、108 項世界串流、111 項 Node 及 107 項管理包檢查通過。來源與解壓包各通過 21 項即時觀戰、32 項姿態中斷專項。發行來源 `ade9b977` 的 187 個工作樹檔案雜湊相符，其中 29 個既有檔案與 Git 只差換行。C／F 管理包測試 27 檔相符，Windows 與 Quest 0.50.4 離線發行核對通過。兩次 GitHub Actions 因帳務或支出上限未啟動。 [即時觀戰專項](../artifacts/console-observer-integrity-package-live/checks.json) · [姿態專項](../artifacts/console-observer-integrity-package-pose/checks.json) · [發行核對](../artifacts/venue-release-0.50.4-observer-integrity.json) · [發行來源 CI](https://github.com/peca12968/vr-command-center/actions/runs/42892151748) · [測試來源 CI](https://github.com/peca12968/vr-command-center/actions/runs/42893314643)
- 首輪 Windows 場已通過兩種拓撲的追蹤及 UDP 恢復，之後測試錯誤地在本房專用畫面尋找多房按鈕，場次驗收失敗。測試來源 `4f85b628` 明確區分兩種畫面，在共用畫面核對原畫格的姿態計數，本房專用畫面則確認多房按鈕隱藏。首輪清理完畢，C／F 232 檔相符。 [首輪測試](../artifacts/observer-integrity-native.log) · [清理及雜湊](../artifacts/observer-integrity-native-initial-validation.json)
- 第二輪到達本房專用串流的幾何核對，測試任務缺少別房掩體，場次仍失敗。`14cc1ff4` 在合併觀戰的測試任務配置油桶，保留原隔離斷言。第二輪同樣清理完畢，C／F 232 檔相符。 [第二輪測試](../artifacts/observer-integrity-native-final.log) · [清理及雜湊](../artifacts/observer-integrity-native-second-validation.json)
- 同一解壓管理包通過 891 項完整 Chromium 回歸。核對八個任務列表故障均送達，並保存 143 份證據及原日誌與結果雜湊。測試來源 `4f85b628`，管理包來源 `ade9b977`。 [完整回歸](../artifacts/console-observer-integrity-full/checks.json) · [回歸核對](../artifacts/observer-integrity-browser-validation.json)
- 測試來源 `14cc1ff4` 搭配原解壓包通過 441 項 Windows 原生檢查。獨立與合併模式各 25 個同機玩家端，第 5 房第 2 席使用 Unity Mock Runtime。姿態回放從原中斷格 215／206 返回即時格 223／215，原房間、席位及鏡頭保留。另行切斷 UDP 後，原玩家程序重連並保留健康及彈藥，兩段封存區間 320／315 格核對其餘 24 席。合併第 4 房專用串流回傳本房 5 席、掩體與戰績，由原格 593 重新連到 598。六場共 3,577 格回放、50 份戰績、11 份 CSV、原伺服器確認及雙封存，活動場次歸零，C／F 237 檔相符。測試來源 CI job `130103035828` 因帳務或支出上限未啟動。實體頭盔、跨機及廠商設備待實測。 [Windows 驗收](../artifacts/server-package-checks/run-16413070e86f452eb8b68de79b0b562f/checks.json) · [原生核對](../artifacts/observer-integrity-native-validation.json) · [測試來源 CI](https://github.com/peca12968/vr-command-center/actions/runs/42894242299)

## 2026-11-11 即時環境與敵軍各自保留草稿

- 0.31.119 的解壓包重現套用環境時會重設尚未送出的敵軍設定。0.31.120 分別保留環境與敵軍草稿，依設定版本套用。其他設定、名冊及可操作的階段變更不會使原草稿失效。全場敵軍版本包含分房策略變更，同一設定的舊稿被拒絕後仍可查看，按「載入目前設定」才取代。舊 API 場次序號繼續適用。 [操作與 API](ENVIRONMENT.md) · [舊版對照](../artifacts/setting-drafts-baseline.log) · [套件專項](../artifacts/console-setting-drafts-package/checks.json)
- Release 零警告，1,100 項核心、28 項 Python、111 項 Node、107 項管理包、825 項 HTTP 通過。首輪 HTTP 的精確回應未列出新增的設定版本而失敗，測試來源 `9311c546` 改用原命令回條驗證兩個欄位，其他欄位仍精確相等。沿用 `8a9a23a9` 發行的同一套件重跑。187 個來源檔與發行記錄相符，其中 29 個既有檔案與 Git 只差換行。管理包 C／F 27 檔相符。Windows 與 Quest 0.50.4 的離線發行核對通過。兩個 GitHub Actions job 均因帳務或支出上限未啟動。 [首輪 HTTP](../artifacts/setting-drafts-http.log) · [新版 HTTP](../artifacts/setting-drafts-http-final.log) · [發行核對](../artifacts/venue-release-0.50.4-setting-drafts.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42890054210)
- Windows 三包通過 396 項。獨立第 1 房用同一份場次概覽送出環境版本 10 與敵軍版本 1，接受序號 11、12。原保存格 228 觀察到序號 12，同時記錄暴風雨、夜晚、閃電與巡邏，另外四房的版本保持。合併場另驗天氣切換與第 2 房的策略套用、恢復及回放。兩種拓撲各 25 個同機玩家端同時連線，六場核對 1,009 格回放、50 份原戰績、11 份 CSV、原伺服器確認及雙封存。活動場次歸零，原生 C／F 218 檔相符。跨機、頭盔及廠商設備待實測。 [原生驗收](../artifacts/server-package-checks/run-a7677063b6994721b720491d408426f0/checks.json) · [原畫格及核對](../artifacts/setting-drafts-validation.json)
- 解壓套件通過 10 項設定草稿、9 項分房策略專項與 885 項完整 Chromium 回歸。完整回歸保留八筆任務列表故障的逐筆送達證據。來源 `9311c546` 與套件 `8a9a23a9` 分別記錄，完整結果及日誌已核對雜湊。 [完整結果](../artifacts/console-setting-drafts-full/checks.json) · [瀏覽器驗收核對](../artifacts/setting-drafts-browser-validation.json)

## 2026-11-11 任務列表故障測試與完整回歸

- 測試 `16c1c3b0` 在原五秒內等待確實攔截下一筆任務列表 GET，最多注入一次故障。若更新按鈕共用舊請求，測試可再觸發唯讀更新。各案例保留攔截及送達證據，原讀寫斷言和管理服務期限均維持。獨立對照確認舊請求扣住期間，手動更新未另發請求，釋放後可攔截新請求並送出 HTTP 503。原逾時當下的請求順序未取得。 [重疊對照](../artifacts/catalog-refresh-overlap-probe.log) · [任務讀取專項](../artifacts/console-catalog-fault-recovery/checks.json)
- 沿用 `d3f999c3` 發行的 Windows 管理包 0.31.119，ZIP SHA-256 為 `5c31c8fd898b3a05f771c9df8fbbbd4efaa4a699316d93407f71a87579d2c55c`。這次修改測試夾具。GitHub Actions job `130081861186` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42888151970)
- 使用 Playwright 1.62.1 的 Chromium Headless Shell 151.0.7922.34，31 項任務專項與 878 項完整回歸均通過。兩次各八個故障案例均攔截一筆請求並確認送達，完整流程涵蓋逐房策略、任務編輯、觀戰、回放及戰績。核對 143 個完整回歸證據檔的目錄數量，以及日誌、結果、故障紀錄和原套件的 SHA-256。先前系統 Chrome 的滾輪失敗及鎖定 Chromium 的任務列表逾時均保留。這次使用隔離管理服務與瀏覽器，原 386 項 Windows 原生驗收另列。 [完整結果](../artifacts/console-catalog-fault-full/checks.json) · [故障紀錄](../artifacts/console-catalog-fault-full/mission-catalog-faults.json) · [來源與雜湊](../artifacts/catalog-fault-full-validation.json)

## 2026-11-11 分房敵軍策略的並行編輯

- 管理台 0.31.119 以場次概覽提供的本房序號送出策略。管理服務在原命令交易內核對。較新的本房修改、恢復沿用或全場策略會使原草稿過期，其他房的策略更新可以獨立完成。套用回覆未確認時，同一份命令可取回原接受序號。舊版 API 請求可省略新增的 `expectedPolicySequence`，沿用原行為。 [操作說明](LAYOUT.md#合併場分房敵軍策略)
- 解壓 0.31.118 與實際 Chromium 重現同房較新的命令被舊草稿覆蓋，原送出得到 HTTP 200。0.31.119 同一流程得到 HTTP 409，管理資料及草稿仍保留。來源與套件均通過 9 項逐房編輯及 98 項全館操作瀏覽器檢查。錯誤回覆後以原請求內容重試，核對原接受序號。核心另核對重開後的序號、回條及房間範圍。 [舊版對照](../artifacts/room-enemy-edit-baseline-status.log) · [逐房瀏覽器](../artifacts/console-room-enemy-edit-package/checks.json) · [全館瀏覽器](../artifacts/console-room-enemy-edit-venue-package/checks.json)
- Release 零警告，1,097 項核心、825 項套件 HTTP、111 項 Node、107 項管理包檢查通過。套件由 `d3f999c3` 發行，187 個來源檔雜湊相符，29 個既有檔案與 Git 只差換行。管理包測試 C／F 27 檔相符，既有 Windows 與 Quest 0.50.4 套件一致性通過。GitHub Actions job `130074231245` 因帳務或支出上限未啟動。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [發行核對](../artifacts/venue-release-0.50.4-room-enemy-edit.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42885960617)
- Windows 解壓三包通過 386 項。第 2 房從 Chromium 送出帶版本的巡邏與開火命令，原保存格 157 確認套用。回放核對巡邏與射擊僅發生於第 2 房，恢復沿用後停止開火，第 1 房維持守備。五房獨立和合併各有 25 個同機 Windows 玩家端同時連線。六場共 903 格回放、50 份原戰績與伺服器確認、11 份 CSV 及雙封存。活動場次歸零，原生 C／F 218 檔相符。跨機、頭盔與廠商設備另待實測。 [Windows 驗收](../artifacts/server-package-checks/run-4e30695d11a34c17b8a1370819d1c299/checks.json) · [原畫格與序號](../artifacts/room-enemy-edit-native-validation.json)
- 完整瀏覽器回歸仍有失敗。系統 Chrome 在舊版一次、新版兩次均未通過觀戰滾輪檢查。專案鎖定的 Chromium 通過滾輪，但完整流程後續未在五秒內取得任務列表故障測試所等待的請求，同套件單獨重跑任務讀取則通過 31 項。各次結果保留。 [舊包對照](../artifacts/room-enemy-edit-full-baseline.log) · [鎖定 Chromium 完整流程](../artifacts/room-enemy-edit-full-pinned.log) · [任務讀取專項](../artifacts/console-room-enemy-edit-mission-read-pinned/checks.json)

## 2026-11-11 任務文字與版本核對

- 管理台 0.31.118 保留已載入名稱的前後空白及任務簡報的原始換行。修改時間或場地設定再儲存時，未編輯的文字沿用原值。載入及比對核對任務系列、識別與版號。保存已受理但讀回舊版時保留原請求，供操作員用同一筆請求確認。 [操作說明](MISSION_VERSIONS.md)
- 解壓 0.31.117 套件，以實際 Chromium 重現只改時間卻改變原文字的失敗。首輪 0.31.118 來源測試通過文字核對，但通用通知未顯示版本不符，加入明確通知後，來源與解壓套件各通過 31 項任務讀取及 41 項版本、範本測試。錯誤回覆測試以原請求識別及內容重送，核對資料庫只新增一次。 [舊版對照](../artifacts/mission-text-browser-baseline-chrome.log) · [套件讀取](../artifacts/console-mission-text-package/checks.json) · [套件版本](../artifacts/console-mission-versions-text-package/checks.json)
- Release 零警告，1,093 項核心、825 項套件 HTTP、107 項管理包檢查通過。管理服務依 535 個發行檔及 555 筆解壓清單核對。套件來源 `9872aa36` 的 187 個工作樹檔案雜湊相符，其中 29 個既有檔案與 Git 只差換行。沿用 Windows 與 Quest 0.50.4 的離線發行核對通過。GitHub Actions job `130066602513` 因帳務或支出上限未啟動。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [發行核對](../artifacts/venue-release-0.50.4-mission-text.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42883769157)
- 使用者關閉擷取視窗後重驗 WinForms 1.17。路徑已輸入，兩次「載入／更新」點擊均回報被 `PickerHost.exe` 遮擋。停止點擊，清理隔離的啟動器及管理服務。未選房或啟動原生來源，C／F 9 個測試存檔雜湊相符。 [桌面驗收紀錄](../artifacts/server-gui/run-b180f68f62ee4cada039b24eba8c61b7/gui-blocker.json)
- 0.31.118、啟動器 1.17 及 Windows 遊戲 0.50.4 解壓整合通過 446 項。從 Chromium 下載的場館計畫帶有各場次及任務版本，過期計畫未能啟動來源。五房獨立場逐一套用各自保存的時長、環境、敵軍與掩體。獨立和合併模式各有 25 個同機玩家端同時連線，六場核對 943 格完整回放、50 份原戰績與伺服器確認、11 份 CSV 及雙封存。活動場次歸零，原生 C／F 254 檔及管理包測試 27 檔雜湊相符。跨機、頭盔與廠商設備另待實測。 [Windows 驗收](../artifacts/server-package-checks/run-fb62ddf93fa041768bd45d06780e4248/checks.json) · [驗收統計](../artifacts/mission-text-native-validation.json)

## 2026-11-11 合併場本房觀戰串流

- 管理包 0.31.117 增加房卡「僅接收本房資料」。從此入口開始，管理服務投影本房的場景物件、玩家、敵軍、事件及戰績，保留原錄製識別與序號。逐格、即時回看及重連沿用選定房間。原「即時觀戰」仍可開啟既有共用檢視。 [操作說明](WORLD_RECORDING.md#從房卡或全館收尾開啟)
- 0.31.116 對新 `observerRoomId` 參數回應共用串流。0.31.117 使用同一個合併場測試本房即時串流、逐格、固定範圍回放，以及指定別房時的 403。省略參數仍取得共用畫格。Release 零警告，1,093 項核心、108 項世界串流、111 項瀏覽器模組、825 項 HTTP 及 107 項管理包檢查通過。 [舊版對照](../artifacts/room-observation-opt-in-baseline.log) · [套件串流測試](../artifacts/room-observation-package-world.log)
- 套件來源 `629809cc`，187 個工作樹來源雜湊相符，其中 29 個既有檔案與 Git 只差換行。Windows 與 Quest 0.50.4 發行一致性通過。GitHub Actions job `130058315685` 因帳務或支出上限未啟動。 [發行核對](../artifacts/venue-release-0.50.4-room-observation.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42881401239)
- 首輪原生場在本房重連與逐格資料核對後，因測試任務未放置掩體而未通過幾何斷言。原失敗保留，清理完成，C／F 214 檔一致。後續重驗用同一套件及包含每房掩體的既有測試選項。 [首輪紀錄](../artifacts/room-observation-native.log)
- 含掩體的 Windows 原生場通過 422 項，含 9 項 Chromium 觀戰檢查。原共用串流可從第 4 房切到第 2 房及全館 25 席。第 4 房專用串流只回傳本房掩體、敵軍、5 席及本房戰績。第 187 格斷線後從同一來源恢復到第 191 格，回看後可用逐格查詢到原第 190 格。觀戰操作沒有管理寫入。兩種拓撲各 25 席同機入場，核對 50 份原戰績與伺服器確認、1,636 格回放、11 份 CSV 及雙封存。活動場次歸零，原生 C／F 221 檔及管理包測試 27 檔一致。跨機、頭盔與廠商設備另待實測。 [原生驗收](../artifacts/server-package-checks/run-e84c912edeaf471fa0f5ae5a1221bc67/checks.json) · [本房畫面](../artifacts/server-package-checks/run-e84c912edeaf471fa0f5ae5a1221bc67/room-observer/room-only-replay.png)

## 2026-11-11 回放耗損與最終戰績一致

- 管理包 0.31.116 讓逐格與最終戰績使用同一個生命值耗損規則。片段以起點前一格的生命值計算損失，保留原事件傷害和中彈次數。舊資料的零生命值超額耗損在讀取時修正。測試以原封存條件成功封存舊格式資料，原存檔的事件與統計內容均保留。 [片段戰績](WORLD_RECORDING.md#重看指定片段)
- 舊版 0.31.115 收到剩 50 點時的 90 點事件，接受原戰鬥事件及世界畫格後，因最終戰績不符而拒絕封存。0.31.116 使用相同情境通過原 WebSocket 封存，片段只計 50 點耗損。首輪核心夾具的 200 點超出世界事件上限，已保留。兩次串流夾具分別補正建立場次的 201 回覆及新場次的幾何識別後通過。 [舊版串流對照](../artifacts/overkill-world-http-old-package-detail.log) · [新版套件串流](../artifacts/overkill-world-package-http.log)
- Release 零警告，1,093 項核心、104 項世界串流、825 項 HTTP 及 107 項解壓管理包檢查通過。發行來源 `0b860a90`，186 個工作樹來源雜湊相符，其中 30 個既有檔案與 Git 只差換行。沿用 Windows 與 Quest 0.50.4 的發行一致性核對通過。GitHub Actions job `130049505543` 因帳務或支出上限未啟動。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [發行核對](../artifacts/venue-release-0.50.4-replay-loss.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42878887960)
- Windows 0.50.4、啟動器 1.17 與解壓管理包的同機整合通過 421 項。獨立及合併各 25 席同時入場，六場共 1,509 格完整回放、212 筆傷害、50 份原戰績及伺服器確認、11 份 CSV 及雙封存。合併場第 3 房房控以 Chromium 從原中彈畫格標記第 181 至 244 格，該席顯示 1 次中彈、20 點耗損。全部測試程序已清理，原生 C／F 220 檔及管理包驗收 27 檔雜湊相符。跨機、頭盔和廠商硬體仍待驗收。 [Windows 驗收](../artifacts/server-package-checks/run-da066e9c00724d72934d281e6040381d/checks.json) · [片段畫面](../artifacts/server-package-checks/run-da066e9c00724d72934d281e6040381d/linked-room-03-clip-statistics.png)

## 2026-11-11 Windows 啟動器背景載入待開場次

- 啟動器 1.17 在背景讀取單房清單。等候時暫停選房及啟動，視窗仍可關閉。成功時只保留同一實例中仍可用的原選取，失敗時清空清單。隔離的 WinForms 程序以實際管理服務及本機代理扣住清單回覆。1.16 在等候期間未通過訊息迴圈檢查。1.17 通過 55 項 Framework 與 51 項清單檢查，涵蓋原場次保留、503 後清除及回覆仍被扣住時關閉。 [新版驗收](../artifacts/server-catalog/run-6e05c627462f421cad7cc9775c6ef71f/checks.json) · [舊版對照](../artifacts/server-catalog-baseline-117-packaged/artifacts/server-catalog/run-34b572c5ebe449bc96269364ad004313/framework-proof.json)
- 新版首輪代理漏轉管理根路由，第二輪測試程式逾時。代理補上根路由，測試在建立表單前保存執行緒的同步內容，訊息迴圈結束後還原，正式重跑通過。首次舊版取證的 Git 檔案換行與原包編譯輸入不同，對照場改用雜湊吻合的原編譯輸入。上述試次與原門檻皆保留。 [首輪](../artifacts/server-117-catalog.log) · [第二輪](../artifacts/server-117-catalog-final.log)
- 另外以 1.16 操作實際可見桌面視窗。輸入隔離管理路徑後，兩次載入點擊均由 `PickerHost.exe` 攔截，未載入場次。停止桌面輸入後清理原程序，C／F 9 檔相符。1.17 的 WinForms 檢查在測試程序內進行，完整桌面操作另待複驗。 [桌面遮擋](../artifacts/server-gui/run-521f12cd822e4a45a3d103274bd3ee1e/gui-blocker.json)
- 解壓 1.17 套件通過 400 項同機原生整合檢查。獨立及合併各有 25 席同時連線，六場共 929 格完整回放、50 份原戰績和伺服器確認、11 份 CSV 及雙封存。活動場次歸零，C／F 216 檔相符。套件中 328 檔與 1.16 雜湊相同，沿用 0.50.4 Windows 遊戲與 Quest ARM64 開發 APK。 [Windows 驗收](../artifacts/server-package-checks/run-35591fb182ff4b4e866fc082e6ef7301/checks.json) · [發行核對](../artifacts/venue-release-0.50.4-catalog-117.json)
- 套件的啟動器來源雜湊與 GitHub 提交 `4ec8226c` 相符。GitHub Actions job `130044587030` 因帳務或支出上限未啟動。跨機、實體頭盔及廠商設備仍待驗收。 [伺服器包](WINDOWS_SERVER_PACKAGE.md) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42877492400)

## 2026-11-11 硬體模擬閘道核對戰鬥來源

- 模擬器 0.2.12 在附掛前核對戰鬥串流、來源及階段序號。已附掛的同一串流若回報另一種來源，該房以 `management-invalid-response` 結束，取消待確認批次並保留原確認。其他房可繼續排演。 [操作說明](HARDWARE.md#一次啟動與停止五房排演)
- 0.2.11 對照場在收到改報來源的回覆後，第 4 房沒有發布終止結果。0.2.12 的第 4 房先遇到短暫 503，關閉原連線並取消原批次，恢復後使用新連線確認新回饋。之後注入來源矛盾時，第 4 房保存兩筆原確認與兩筆取消紀錄，第 5 房仍在原連線確認。啟動前缺少戰鬥來源的案例在模擬握手前被拒絕。 [舊版對照](../artifacts/hardware-0212-baseline.log) · [新版房間報告](../artifacts/live-hardware-gateway/run-b06b5bcb2ad947148fdf3cf8fded3d52/linked-fleet-authority-faults/room-04-report.json)
- Release 零警告，1,086 項核心、38 項離線及 72 項即時檢查通過。解壓驗證的 0.2.12 套件八個檔案與清單相符，範例輸出與原檢查結果逐位元相同。來源 `c600534d` 已推送。GitHub Actions job `130036533084` 因帳務或支出上限未啟動。 [套件資料](HARDWARE_SIMULATOR.md) · [即時檢查](../artifacts/live-hardware-gateway/run-b06b5bcb2ad947148fdf3cf8fded3d52/checks.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42875201022)
- Windows 遊戲 0.50.4、啟動器 1.16、管理包 0.31.115 與解壓模擬器 0.2.12 的命令列整合測試通過 430 項。獨立與合併模式各 25 席同機連線，十房次累計 212 筆模擬確認，對應 50 個原入場識別。六場共 1,765 格完整回放，50 份戰績、11 份 CSV、雙封存與原伺服器確認皆相符。程序清理完成，C／F 快照 238 檔雜湊一致。WinForms、跨機、頭盔及廠商設備另待驗收。 [Windows 驗收](../artifacts/server-package-checks/run-9547b73f0c434c158d298e155c9b9c54/checks.json)

## 2026-11-11 在主控台核對未確認的全館啟動報告

- 管理包 0.31.115 新增主控唯讀核對。瀏覽器解析第四版啟動結果，只送出原批次、場次、來源識別及 UDP 綁定欄位。管理包會核對實例，逐房顯示原場次、來源、端點與近期快照狀態。綁定為 `0.0.0.0` 時核對埠號，公告位址由管理端讀取。 [操作方式](WINDOWS_SERVER_PACKAGE.md#核對未確認的啟動報告)
- Windows 三包 `run-3e0a640cd90942cdb9305675112793f7` 退出 0、475 項通過。實際匯入兩份 1.16 啟動器報告。第一份顯示原五房準備中且全數未綁定。第二份在管理端已保存合併端點、但兩個成功回條均被代理換成 502 後產生，主控台找到原來源及端點，並顯示無近期快照。用錯誤埠號再次核對時顯示不符。核對前後的原場次與端點相同。 [未綁定結果](../artifacts/server-package-checks/run-3e0a640cd90942cdb9305675112793f7/independent-venue-unbound-browser-review.json) · [已公告結果](../artifacts/server-package-checks/run-3e0a640cd90942cdb9305675112793f7/lost-endpoint-browser-review.json)
- 同一驗收中的正常五房獨立及合併各 25 席同機連線，50 份戰績、6 份 CSV、959 格完整回放及雙封存。兩個報告故障案例另列。活動場次歸零，C／F 快照 289 檔雜湊相符。首輪在管理服務就緒前逾時，未啟動遊戲，C／F 快照 9 檔相符。第二輪在新實例以測試專用的四處理器設定通過，仍使用原 40 秒門檻。 [Windows 驗收](../artifacts/server-package-checks/run-3e0a640cd90942cdb9305675112793f7/checks.json) · [首輪紀錄](../artifacts/venue-launch-review-native.log)
- Release 零警告，1,086 項核心、11 項 Chromium、825 項 HTTP、107 項管理包及 27 項 Python 檢查通過。管理包來源 `28b80322`，186 個來源雜湊相符。沿用啟動器 1.16、Windows 遊戲與 Quest 0.50.4，發行一致性核對通過。GitHub Actions job `130029775694` 因帳務或支出上限未啟動。跨機、頭盔及廠商硬體仍待驗收。 [瀏覽器驗收](../artifacts/console-venue-launch-review/checks.json) · [發行核對](../artifacts/venue-release-0.50.4-launch-review.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42873262957)

## 2026-11-11 啟動器重送原全館回條請求

- Windows 啟動器 1.16 遇到暫時性傳輸錯誤或 HTTP 502、503、504 時，會在原程序可用的條件下，將同一份來源登記或端點公告資料重送一次。回條仍須符合原場次及來源，端點公告前後也會核對原程序的 UDP 綁定。報告記錄是否重送。兩次都無法確認時會停止並保留 `unconfirmed` 結果。 [操作與報告](WINDOWS_SERVER_PACKAGE.md#依場館計畫批次啟動)
- Windows 故障驗收 `run-69a3f0dc284c40869803dbbc17359597` 退出 0、478 項。代理讓原管理服務先提交來源及端點，再把第一次成功回條換成 502。五房獨立及合併各自的兩個重送均與原請求及原回條雜湊相同，兩種模式各 25 席同機連線，完成 50 份戰績、6 份 CSV、976 格全回放及雙封存。另驗證兩次 503 後停止全部五個遊戲程序，直接 409 只送一次，第五房端點資料庫寫入失敗會回復整批公告。活動場次歸零，C／F 快照 303 檔同雜湊。 [Windows 驗收](../artifacts/server-package-checks/run-69a3f0dc284c40869803dbbc17359597/checks.json) · [獨立回條](../artifacts/server-package-checks/run-69a3f0dc284c40869803dbbc17359597/independent-venue-receipt-gate.json) · [合併回條](../artifacts/server-package-checks/run-69a3f0dc284c40869803dbbc17359597/linked-venue-receipt-gate.json)
- 固定指紋 HTTPS／WSS 回歸 `run-1c213f320ec6441fa06def2b64f7ceb6` 退出 0、476 項。兩種模式正常各 25 席同機連線，來源及公告均一次成功，50 份戰績、6 份 CSV、966 格全回放及雙封存。兩個日誌工具可讀回合併場原封存來源。活動場次歸零，C／F 快照 268 檔同雜湊。場次清單與 MR 校正門檻另通過 51 項套件及 48 項 Framework 檢查。 [HTTPS 回歸](../artifacts/server-package-checks/run-1c213f320ec6441fa06def2b64f7ceb6/checks.json) · [場次清單](../artifacts/venue-receipt-retry-catalog.log)
- 20 項 Python 檢查通過。來源 `172d2c21`，GitHub Actions job `130020025484` 因帳務或支出上限未啟動。伺服器包與 1.15 相比，328 個清單檔案相同，只有啟動器與包內說明變更。沿用管理包 0.31.114、Windows 玩家端與 Quest ARM64 0.50.4／69，發行一致性及原開發簽章通過核對。跨機、頭盔與廠商硬體仍待驗收。 [發行核對](../artifacts/venue-release-0.50.4-receipt-retry.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42870452707)

## 2026-11-11 一次登記五房的原始遊戲來源

- 控制台 0.31.114 下載第四版計畫。Windows 啟動器 1.15 等遊戲 0.50.4 準備各自的日誌來源，再由管理服務在同一筆 SQLite 交易核對序號及寫入全部來源。各遊戲核對原批次回條後才開啟 UDP。舊版 1.14 拒絕第四版計畫，新版啟動器連到 0.31.113 管理包也會在建立工作目錄前拒絕。既有第二、三版保留逐場登記流程。 [操作與版本](WINDOWS_SERVER_PACKAGE.md#依場館計畫批次啟動) · [混版結果](../artifacts/venue-source-batch-0504-build/old-management/run.json)
- Windows 三包 `run-489a7427d47f4fb88e18cc4210008a15` 退出 0、476 項通過。測試等五個遊戲程序準備好才推進第五房序號，管理服務回 409，五房皆維持未綁定，五個程序都在開啟 UDP 前停止。合併場同樣通過晚到變更的拒絕測試。重新下載原場次後，兩種模式各 25 席同機連線，50 份戰績、6 份 CSV、六場共 1,016 格完整回放及雙封存。終止時活動場次歸零，C／F 快照 268 檔雜湊相符。 [Windows 驗收](../artifacts/server-package-checks/run-489a7427d47f4fb88e18cc4210008a15/checks.json) · [五房拒絕結果](../artifacts/server-package-checks/run-489a7427d47f4fb88e18cc4210008a15/independent-venue-source-stale.json)
- 兩個日誌工具以原 GameServer 身分讀回合併場封存副本，核對 154 格世界與零筆戰鬥事件的尾界。管理端場次與世界紀錄保持相同。來源登記後若另有 UDP 或遊戲程序故障，仍保留已登記來源供主控收尾。 [日誌讀回](../artifacts/server-package-checks/run-489a7427d47f4fb88e18cc4210008a15/linked-relay-readback.json)
- 273 項 Unity EditMode 通過。Windows 與 Quest 0.50.4／69 的來源指紋、場景與玩家網路識別相符。Quest ARM64 APK 為 61,039,738 bytes，SHA-256 `5f2ebbdbf8ae1bf28677991954876f1d8842a4b14e2ff01f3ac2eb3264893263`，v2 開發簽章已核對。Windows 玩家包為 84,773,997 bytes，SHA-256 `7f40e6cafb33de50da9056a96b094bf9159d7a87db8df8dcff20d4bcde942910`。中間提交帶入 Unity 暫時產生的預載清單，最終提交已恢復原本清單。跨機、頭盔及廠商硬體仍待驗收。 [Editor 結果](../artifacts/venue-source-batch-0504-build/EditMode.xml) · [發行核對](../artifacts/venue-release-0.50.4-source-batch.json)
- Release 零警告，1,086 項核心、14 項 Chromium、804 項 HTTP、102 項世界串流、107 項管理包、38 項玩家包及 17 項 Python 套件檢查通過。HTTP 使用測試程序專用的四處理器設定。管理包建置來源 `2388e357`，184 個來源雜湊相符，兩個日誌工具及驗收程式使用 `4ceb31c4`。GitHub Actions job `130009944656` 因帳務或支出上限未啟動。 [HTTP 結果](../artifacts/venue-source-batch-0504-build/http-smoke.log) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42867582936)

## 2026-11-11 在遊戲來源登記時核對場次序號

- 控制台 0.31.113 匯出第三版計畫。Windows 啟動器 1.14 將原序號傳給遊戲 0.50.3，管理服務在寫入來源的同一次操作內比對序號。遊戲確認原序號回條才啟動 UDP。舊 1.13 拒絕第三版計畫，使用第三版的 1.14 也在建立遊戲工作目錄前拒絕缺少此能力的舊管理包。新啟動器仍可讀取第二版並使用登記檢查，第一版手動計畫保留原流程。 [操作與版本](WINDOWS_SERVER_PACKAGE.md#依場館計畫批次啟動)
- Windows 三包 `run-b0ee6c2a4c954dcc961e344742c41c1f` 退出 0、459 項。測試在原 Unity 的來源請求抵達時以 SetEnvironment 推進同一場次序號。管理服務回 409，遊戲退出碼 2，無來源、UDP 綁定或就緒公告。重新下載後，五房獨立及合併各 25 席同機連線，最終來源仍保存各計畫序號，50 份戰績與原伺服器確認相符，六場共 939 格完整回放、6 份 CSV 及雙封存。活動場次歸零，C／F 快照 242 檔雜湊相符。核對是逐場執行，先登記的其他獨立房間仍保留來源供收尾。 [Windows 驗收](../artifacts/server-package-checks/run-b0ee6c2a4c954dcc961e344742c41c1f/checks.json) · [競態結果](../artifacts/server-package-checks/run-b0ee6c2a4c954dcc961e344742c41c1f/linked-venue-source-stale.json)
- 前兩輪保留為失敗。第一輪轉送測試請求時誤用二進位 Content-Type，實際收到 415。第二輪由 Chromium 拒絕 loopback 1719 埠，尚未啟動遊戲。只修正測試轉送及高位埠選取，原套件及核對條件相同。兩輪均清理，C／F 快照 152 與 36 檔各自雜湊相符。 [415 紀錄](../artifacts/guarded-source-0503-build/native-suite.log) · [連接埠紀錄](../artifacts/guarded-source-0503-build/native-suite-json-forwarded.log)
- 273 項 Unity EditMode 通過，Windows 與 Quest 0.50.3／68 的來源指紋、場景及玩家網路識別相符。Quest ARM64 開發 APK 61,030,026 bytes，SHA-256 `8951cc81c078c39f436a1737e45f7a78dfc61b4b349b2e43b05832b1aeec0a0d`，原 v2 開發簽章核對通過。Windows 玩家包 84,773,048 bytes，SHA-256 `8fe90c6541ae1f5f6b79f611e504c0466e5627aeb9a6bfb18296ea602a3c8ea2`。跨機、頭盔及廠商硬體仍待現場驗收。 [Editor 結果](../artifacts/guarded-source-0503-build/EditMode.xml) · [發行核對](../artifacts/venue-release-0.50.3-guarded-source.json)
- Release 零警告，1,079 項核心、14 項 Chromium、107 項管理包、38 項玩家包及 17 項 Python 套件檢查通過。管理包建置來源 `bb6a2b83`，184 個來源雜湊相符。最終 Windows 驗收程式來源 `000bd136`，GitHub Actions job `129997244080` 因帳務或支出上限未啟動。 [瀏覽器結果](../artifacts/console-guarded-source-plan/checks.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42863975238)
- 解壓管理包以測試程序專用 `DOTNET_PROCESSOR_COUNT=4` 通過 785 項 HTTP。預設設定的首輪在重複憑證案例輸出預期診斷後仍超過 10 秒門檻，保留失敗與子程序輸出。兩次測試使用同一套件及原期限。來源建置另通過 102 項世界串流檢查。 [HTTP 通過](../artifacts/guarded-source-0503-build/http-smoke-four-processors.log) · [首輪 HTTP](../artifacts/guarded-source-0503-build/http-smoke.log) · [世界串流](../artifacts/guarded-source-0503-build/world-smoke.log)

## 2026-11-11 核對五房啟動計畫的場次序號

- 控制台 0.31.112 下載第二版計畫，逐場寫入序號與任務版本。Windows 啟動器 1.13 在讀取計畫及取得全館本機啟動鎖後各核對一次。若場次變更，先回主控台重讀並下載。既有第一版手動計畫仍使用原房間、場次及 UDP 核對。 [操作方式](WINDOWS_SERVER_PACKAGE.md#依場館計畫批次啟動)
- Chromium 14 項通過。實際 Windows 三包驗收 `run-b2fd4e8d5dbe4198913cd4709001eda8` 退出 0、451 項通過。兩種拓撲都拒絕舊下載檔。測試在啟動器取得鎖後改動第五房，五個工作程序都未寫入遊戲設定，原場次無來源。重新下載後經同機固定指紋 HTTPS／WSS 啟動，五房獨立及合併各有 25 席同時連線，50 份原戰績及伺服器確認一致，六場共 943 格完整回放、6 份 CSV 及雙封存。活動場次歸零，C／F 快照 234 檔雜湊相符。 [瀏覽器驗收](../artifacts/console-venue-plan-revisions/checks.json) · [Windows 驗收](../artifacts/server-package-checks/run-b2fd4e8d5dbe4198913cd4709001eda8/checks.json)
- 使用者關閉先前的遮擋視窗後，WinForms 已輸入隔離實例路徑。兩次「載入／更新」仍回報 `PickerHost.exe` 遮擋。測試停在讀取場次前，退出碼 1。已清理本次視窗與管理服務，C／F 快照 9 檔雜湊相符。 [遮擋紀錄](../artifacts/server-gui/run-3a672de014cf412abe6d29225a32ca31/gui-blocker.json) · [清理](../artifacts/server-gui/run-3a672de014cf412abe6d29225a32ca31/cleanup.json)
- Release 零警告，1,074 項核心、102 項世界串流及 17 項 Python 套件檢查通過。解壓管理包通過 107 項檢查，原 API 程序通過 769 項 HTTP。來源 `69b8fa1a`，管理包收據的 184 個來源雜湊相符。沿用 Windows／Quest 0.50.2，解壓清單及原 Quest 67 開發簽章的離線一致性核對通過。GitHub Actions job `129982850290` 因帳務或支出上限未啟動。跨機、頭盔與廠商硬體驗收仍待。 [管理包驗收](../artifacts/control-package-checks/run-fd73f939963d432bb87ad6e341b7fcb5/checks.json) · [HTTP 驗收](../artifacts/http-smoke-venue-plan-revisions.log) · [發行核對](../artifacts/venue-release-0.50.2-plan-revisions.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42859887316)

## 2026-11-11 全館戰績回條下載與離線核對

- 管理包 0.31.111 在「全館收尾」增加主控專用的批次回條 JSON。雙封存後可保存各原場次、尾界和入場確認狀態，原場館驗收 ZIP 維持原格式。離線清單可選填 `venueDebriefReceipts`，逐席比對原始玩家與伺服器日誌核對過的結果，輸出原檔 SHA-256。 [下載方式](SESSION_CLOSURE.md#下載本批戰績回條) · [驗收設定](EXTERNAL_CLIENTS.md#一次核對五房-25-席)
- 79 項離線證據測試及 98 項 Chromium 場館流程檢查通過。涵蓋錯批、封存尾界或入場識別、缺席位及未確認拒絕，另以實際瀏覽器核對部分回條 JSON 的下載原位元組、權限、雙封存門檻及原 ZIP。首次瀏覽器場的驗收程式引用錯誤變數後失敗，修正後使用新隔離場通過。 [瀏覽器驗證](../artifacts/console-venue-debrief-export-final/checks.json) · [下載畫面](../artifacts/console-venue-debrief-export-final/venue-debrief-export.png)
- 三個解壓 Windows 套件的 `run-5027a81c5da04f92a3fa1208ea68f620` 退出 0、469 項通過。五房獨立與合併各 25 席同機模擬玩家，50 份回條與原伺服器確認及玩家結果一致，六場完整回放 857 格、6 份 CSV 及雙封存通過。兩種模式的完整 ZIP 與分場檔得出同一核對結果，Chrome 從最新及歷史批次下載相同原位元組。將一席回條改為未確認後，兩種模式都拒絕離線驗收。活動場次及測試程序已清理，C／F 快照 223 檔同雜湊。 [原生驗證](../artifacts/server-package-checks/run-5027a81c5da04f92a3fa1208ea68f620/checks.json) · [合併場離線報告](../artifacts/server-package-checks/run-5027a81c5da04f92a3fa1208ea68f620/linked-venue-field-results.json)
- Release 零警告，1,074 項核心、102 項世界串流、107 項管理包及 769 項完整 HTTP 通過。最終 HTTP 使用 Windows 預設設定獨立啟動解壓包。首次與套件檢查並行的 HTTP 在任務庫寫入鎖案例逾時，未輸出預期診斷，保留失敗紀錄，原 10 秒門檻未調整。 [管理包測試](../artifacts/control-package-checks/run-0d9035fd7425421abed66e88f53b58a4/checks.json) · [HTTP 通過](../artifacts/http-smoke-receipt-export-package-isolated.log) · [首輪 HTTP](../artifacts/http-smoke-receipt-export-package.log)
- 管理包來源 `9f545a62`，建置收據 184 個來源雜湊吻合。沿用遊戲 0.50.2／Quest 67，發行一致性核對通過。GitHub Actions job `129972452748` 因帳務或支出上限未啟動。 [發行核對](../artifacts/venue-release-0.50.2-receipt-export.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42856947151)

## 2026-11-11 管理服務的啟動拒絕與完整 HTTP 驗收

- 已知的操作員憑證設定錯誤、工作階段寫入鎖及任務庫寫入鎖取得失敗，現在由管理服務寫出對應診斷，結束新程序並回傳退出碼 1。憑證先於資料存取驗證，診斷不含憑證或資料路徑。寫入鎖沿用原排他規則，既有服務及原場次保持。 [管理包](WINDOWS_CONTROL_PACKAGE.md)
- 原版在 10 秒門檻內仍曾逾時。第一個修正版讓四種無效憑證正常退出，但解壓套件的完整測試隨後在原工作階段鎖的未處理例外逾時。測試初版另曾因 Windows 輸出編碼假設失敗，改以 ASCII 診斷片段核對原始位元。舊證據保留。 [原版 HTTP](../artifacts/http-smoke-before-controlled-operator-exit.log) · [首包 HTTP](../artifacts/http-smoke-operator-startup-packaged.log)
- 最終完整 HTTP 兩場均退出 0、769 項通過。第一場以測試程序專用的 `DOTNET_PROCESSOR_COUNT=4` 執行來源建置，第二場使用 Windows 預設設定直接啟動最終解壓包的 API。原 10 秒門檻保留。驗證四種無效憑證及兩種寫入鎖拒絕，原服務仍可讀取同一份場次狀態。前幾次 Windows 逾時的環境原因仍未確定。 [最終管理包 HTTP](../artifacts/http-smoke-startup-validation-package-default.log) · [四處理器診斷場](../artifacts/http-smoke-controlled-startup-four-processors.log) · [.NET 處理器數設定](https://learn.microsoft.com/en-us/dotnet/core/compatibility/core-libraries/6.0/environment-processorcount-on-windows)
- Release 零警告，1,074 項核心、102 項世界串流及 107 項解壓管理包檢查通過。 [管理包測試](../artifacts/control-package-checks/run-d5f42704a8a04949aed7ac1cd3468013/checks.json)
- 最終解壓包另完成 HTTPS／WSS 隔離場 `run-876c37a301cc4ae39ce0e14828707b03`，退出碼 0、39 項通過。一席同機 Windows 模擬玩家的原戰績及回條相符，世界尾界 26 格，戰鬥尾界 0 筆，雙封存完成。管理與原生程序均已清理。 [加密場測試](../artifacts/control-https-checks/run-876c37a301cc4ae39ce0e14828707b03/checks.json)
- 來源 `dfcbe039`，管理包收據 184 個建置來源雜湊吻合，沿用遊戲 0.50.2／Quest 67，發行一致性核對通過。GitHub Actions job `129965749156` 因帳務或支出上限未啟動。 [發行核對](../artifacts/venue-release-0.50.2-startup-validation.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42855064723)

## 2026-11-11 全館收尾逐房顯示戰績回條

- 管理包 0.31.110 在全館收尾逐房顯示已確認與未確認的名冊席數。五房合併仍分列各房。等待雙封存、無來源及尚無回條分開顯示。歷史批次依原場次更新，個別玩家可從「查看場次」追查。主控讀取可加 `includeDebriefReceipts=true`，回應只含各房計數。 [操作說明](SESSION_CLOSURE.md#全館批次結束)
- 實際解壓場 `run-19c2d1f03d584c0ea0a501feb18b7bb2` 退出碼 0，441 項通過。固定指紋的 HTTPS／WSS 五房獨立、五房合併各 25 席同機 Windows 模擬玩家。兩種模式共 50 份回條與原戰績相符，實際 Chrome 都顯示五房各 5／5 席，六場完整回放 961 格、6 份 CSV 及雙封存通過。活動場次和測試程序已清理，C／F 229 檔同雜湊。 [原生驗收](../artifacts/server-package-checks/run-19c2d1f03d584c0ea0a501feb18b7bb2/checks.json) · [合併場畫面](../artifacts/server-package-checks/run-19c2d1f03d584c0ea0a501feb18b7bb2/linked-venue-debrief-receipts.png)
- 96 項場館操作及 10 項批次統計的 Chrome 測試通過。測試以合成回條確認歷史房間從 0／2 更新成 1／2，原驗收 ZIP 位元一致，錯批回條不顯示，房控無法讀取整批計數。 [歷史批次畫面](../artifacts/console-venue-debrief-phases/venue-debrief-partial.png)
- Release 零警告，1,074 項核心、102 項世界串流及 107 項解壓管理包檢查通過。Windows 的完整 HTTP 測試兩次都在錯誤憑證案例等待程序退出時逾時，未執行整套 HTTP 斷言。另以同一二進位檢查原程序模式和只套用於測試程序的錯誤回報模式，兩者在 10 秒內都未完成，均輸出預期的憑證拒絕且未開啟測試埠，延遲原因未定。 [管理包測試](../artifacts/control-package-checks/run-3540055edf46451cb9599d3486cc8c12/checks.json) · [程序退出診斷](../artifacts/http-credential-exit-venue-debrief.json) · [Windows 程序錯誤模式](https://learn.microsoft.com/en-us/windows/win32/api/errhandlingapi/nf-errhandlingapi-seterrormode)
- 管理包來源 `66bb18e0` 與收據中的 183 個檔案雜湊相符。沿用遊戲 0.50.2／Quest 67，發行一致性核對通過。GitHub Actions job `129954057729` 因帳務或支出上限未啟動。跨機玩家、實體頭盔與廠商硬體仍待現場驗收。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [發行核對](../artifacts/venue-release-0.50.2-venue-debrief.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42851763815)

## 2026-11-11 控制台查看玩家戰績回條

- 管理包 0.31.109 搭配遊戲 0.50.2。在個別場次的「任務收尾」展開回條，依終止名冊查看確認席數。主控看整場，房控看本房。回條只接受原遊戲來源及原入場，核對場次序號和雙封存尾界。保存後可重送及重啟讀回，原場次、統計和錄製序號保持。 [操作方式](SESSION_CLOSURE.md#玩家戰績回條)
- 以三個 Windows 解壓包執行 `run-b41952417c2742469866a2912f8e4750`，372 項通過。五房獨立與合併各 25 席同機模擬玩家，50 份回條逐席與原玩家戰績及伺服器確認相符。六場完整回放共 1,019 格，6 份 CSV，兩種模式均完成雙封存。合併場五個房控各只讀原房五席。實際 Chrome 控制台送出房間 1 的 End 並顯示 5／5 席已確認。活動場次和測試程序已清理，C／F 220 檔同雜湊。 [原生驗收](../artifacts/server-package-checks/run-b41952417c2742469866a2912f8e4750/checks.json) · [控制台實拍](../artifacts/server-package-checks/run-b41952417c2742469866a2912f8e4750/closure-ui/debrief-receipts.png)
- 獨立 HTTPS／WSS 場 `run-ab449025280c4a1797edfd32999ca709` 39 項通過。一席同機原生模擬玩家的回條由原遊戲程序經固定指紋的 HTTPS 提交，與原入場、21 格世界封存及零事件戰鬥封存相符。其他房控無法讀取該場回條。原遊戲與管理程序已退出。 [加密場驗收](../artifacts/control-https-checks/run-ab449025280c4a1797edfd32999ca709/checks.json)
- 本機 Release 零警告，1,074 項核心、768 項 HTTP、102 項世界串流、107 項管理包、111 項 Node、23 項 Chrome 收尾及 273 項 Unity EditMode 通過。首次 Chrome 使用過期的發行靜態檔而逾時，重建並核對靜態檔後以相同斷言通過。 [瀏覽器測試](../artifacts/console-debrief-closure-fresh/checks.json)
- Windows 和 Quest 0.50.2／67 同源 `8166c7096af52399b95896c265a5f25112025a7ec27729dc3e7b293351e8bf1d`，Windows 兩包 323 個共同檔案、Quest ARM64 及 APK v2 開發簽章核對通過。管理包在提交前由相同工作目錄建置，收據記載基底 `d6fb7278`，另逐檔核對 183 個來源雜湊。首次 APK 核對因收據檔名錯誤被拒，正名後同一份 APK 通過。 [發行核對](../artifacts/venue-release-0.50.2-debrief.json)
- 功能源碼已推送 `9a777200`。GitHub Actions job `129948867553` 因帳務或支出上限未啟動。跨機 25 位玩家、Quest 3／VIVE XR 頭盔與廠商硬體仍待現場驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42850315522)

## 2026-11-10 Windows 啟動器圖形介面重驗

- 使用啟動器 1.12、Windows 遊戲 0.50.1 和管理包 0.31.108 重試。已在啟動器輸入隔離管理實例路徑。「載入／更新」兩次被 `PickerHost.exe` 攔截，第二次已重新啟用並擷取目標視窗。停止桌面輸入後終止本次啟動器，測試以退出碼 1 收尾，未觀察到原生遊戲程序啟動。隔離管理服務正常退出，C／F 的 9 份快照檔案逐檔雜湊一致。 [圖形介面阻擋](../artifacts/server-gui/run-3ed4533cb2b345e1ab43a48193bb6e7c/gui-blocker.json) · [清理結果](../artifacts/server-gui/run-3ed4533cb2b345e1ab43a48193bb6e7c/cleanup.json)
- 沿用同一套件改走命令列。新隔離場退出碼 0、38 項通過。以測試 CA 和固定憑證指紋走 HTTPS／WSS，一名同機 Windows 模擬玩家由配票進場，取得正式戰績，伺服器收到一份回條。世界封存尾界 26 格，另完成戰鬥封存（0 筆事件），已核對一格原即時畫面與封存回放完全相符。遊戲、玩家與管理程序均已停止。 [命令列報告](../artifacts/control-https-checks/run-d1eef7c82c5c4b4fbb1fbd5c1d6a4ba6/checks.json) · [玩家戰績核對](../artifacts/control-https-checks/run-d1eef7c82c5c4b4fbb1fbd5c1d6a4ba6/native-field-results.json)

## 2026-11-10 主控與五房控的管理連線回條

- 可攜管理包的直接 HTTPS 監聽會記下原 TCP 連線來源。主控與房控可用同一輪代號取得各自的簽章回條，主控再以獨立配置表核對六個私有 IPv4 位址。回條有效 15 分鐘，由原管理程序驗證。無需保存新場次或工作站資料。 [操作方式](WINDOWS_CONTROL_PACKAGE.md#核對主控與五房控的直連來源)
- 新解壓包 `run-d4c00632fe4047ecafa38cd329668291` 退出碼 0、38 項通過。實際 HTTPS 的六角色均取得回條，保存同一台電腦的原來源位址，偽造轉送位址也無法替代。主控以六個相異的預期位址送回六份回條，服務在來源核對階段拒絕，CLI `complete` 為 `false`。另測明文、角色權限及超大回條拒絕。原生 Windows 遊戲伺服器仍以 HTTPS／WSS 完成一席同機入場、21 格回放、雙封存及一份原戰績確認。管理及遊戲程序已停止。 [實際套件驗證](../artifacts/control-https-checks/run-d4c00632fe4047ecafa38cd329668291/checks.json)
- 六個獨立私有來源的成功路徑以核心測試驗證，另核對修改來源或簽章、重複角色、過期、不同監聽位址及服務重啟均遭拒。Release 零警告、1,074 項核心、768 項 HTTP、97 項世界串流、107 項原管理包、11 項工作站工具及 7 項封包邊界通過。
- 功能源碼 `a7bba9d325eb21bd01c73f5a81640fcc7b2124e1`，三個新編譯來源的雜湊與封包收據一致。發行核對通過，沿用 Windows 和 Quest 0.50.1／66 及啟動器 1.12。GitHub Actions job `129932575121` 因帳務或支出上限未啟動。六台實體工作站、玩家跨機、頭盔及廠商硬體仍待現場驗收。 [發行核對](../artifacts/venue-release-operator-workstations.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42845737115)

## 2026-11-10 HTTPS 五房批次啟動

- 啟動器 1.12 可從遊戲主機的私人 `control-instance.json` 取得管理 HTTPS 原點、指紋及 GameServer 金鑰。相同設定供待開清單、個別圖形啟動及五房計畫使用。圖形介面在啟動前重讀連線設定，若憑證指紋已換則清除選取。計畫格式維持原樣。 [分機設定](WINDOWS_SERVER_PACKAGE.md#建立遊戲主機的-https-連線設定)
- 最終解壓場 `run-dd8711553f2c4f56a5c5950a8ad15ebc` 退出碼 0、446 項通過。從實際 Chrome 下載兩種原計畫，Windows 啟動器以 HTTPS 讀取及公告端點，原生遊戲以 WSS 上傳世界。獨立和合併各 25 席同機模擬玩家，開場保留逐席原有效姿態。六場共 940 格完整回放、50 份原玩家結果與伺服器確認、6 份 CSV，雙封存與原始結果一致。活動場次和程序均清理，C／F 249 檔逐檔同雜湊，對外測試 JSON 無金鑰及指紋。 [批次報告](../artifacts/server-package-checks/run-dd8711553f2c4f56a5c5950a8ad15ebc/checks.json)
- 錯誤指紋、明文位址及錯誤角色在原生程序啟動前遭拒，原場次保持。另驗證第五房公告寫入失敗時整批回滾，五個原程序均由啟動器清理。Framework 模型通過 48 項，實際待開清單通過 51 項，含圖形選取變更保護。封裝邊界通過 10 項。 [待開清單報告](../artifacts/server-catalog/run-105285026c0f4d19928b9339b7f45f99/checks.json)
- 首候選 `run-4d78ec12d1f94c92a4df8a6618951764` 的清單請求仍走未配置指紋的路徑，改用共用請求設定後通過。第二場 `run-2a56d9602299409a805af927902138f4` 在瀏覽器環境失敗，F 槽 headless 執行檔的獨立重試也未啟動。最終用這台已安裝的 Chrome 重跑原斷言。前兩場失敗、原包及清理紀錄保留。
- 功能源碼 `a829db03287973d2d74295cc10930cce1ee7ee52`。Windows 遊戲及 Quest 0.50.1／66 沿用原建置，離線報告核對新啟動器及原遊戲檔案。GitHub Actions job `129925249859` 因帳務或支出上限未啟動。正式跨機、實體頭盔及廠商硬體仍待驗收。 [發行核對](../artifacts/venue-release-game-0501-launcher112.json) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42843664490)

## 2026-11-10 遊戲主機的 HTTPS 與 WSS 管理連線

- Windows 0.50.1 及啟動器 1.11 可透過個別場次 CLI 連線到管理站台。設定用管理員提供的葉憑證 SHA-256 核對 HTTPS 管理請求及 WSS 世界串流。原生遊戲的 HTTP 管理請求拒絕轉址。 [設定與套件](WINDOWS_SERVER_PACKAGE.md#遊戲主機連到遠端管理-https)
- 原生候選 `run-ded7fd8ae2ac4237873a2e6dbfbe9379` 已建立 HTTPS 戰鬥來源，世界串流未就緒。候選 Mono 程式庫的 `ClientWebSocket` 保存憑證回呼，但實際握手路徑沒有呼叫它。改用獨立 TLS 串流完成有界 WebSocket 升級，再沿用框架的訊框傳輸。保留原候選與失敗報告。 [WebSocket 升級協定](https://www.rfc-editor.org/rfc/rfc6455#section-4.1)
- 最終解壓場 `run-7fc08d164b724dbf808c9cf81f94bf74` 退出碼 0、33 項通過。同台 Windows 使用實際區網 IPv4、測試 CA 及管理包 0.31.108。三種不合規指紋在啟動原生程序前遭拒。成功場用 HTTPS 管理與 WSS 上傳，HTTPS 房控配票讓一席 Windows 模擬玩家入場，第 26 格即時與封存內容相符。尾界 31 格、0 筆戰鬥事件，原玩家戰績及伺服器確認各一。 [加密場報告](../artifacts/control-https-checks/run-7fc08d164b724dbf808c9cf81f94bf74/checks.json)
- 原有本機 HTTP 場 `run-8f65f3c25f6445d685f1d188e7ea580e` 退出碼 0、137 項通過。五房獨立與一個五房合併場共 591 格完整回放、10 份原玩家結果及 10 份 CSV，管理活動場次為零，隔離程序均清理。 [本機場報告](../artifacts/server-package-checks/run-8f65f3c25f6445d685f1d188e7ea580e/checks.json)
- Windows 玩家、Windows 伺服器與 Quest 0.50.1／66 使用同一來源 `9ae1da50d4fb74875add4c6d3bcef20716528e375e892b8ae279bf42d70ad8ca` 及原網路識別。發行工具核對 Windows 兩包 323 份共同檔案與 Quest ARM64、SDK 32／35、APK v2 簽章。首次兩次核對因缺少發行收據或只放 Unity 原收據而拒絕，補齊發行收據後通過。 [發行報告](../artifacts/venue-release-game-0501-https.json)
- Release 零警告、1,059 項核心、97 項世界串流、273 項 Unity EditMode 及 10 項伺服器封裝邊界通過。精確來源 `f8ecc23e8c01db67404d8147293cc5a7b8bdb32d`。GitHub Actions job `129913798215` 因帳務或支出上限未啟動。實際跨機、實體頭盔與廠商硬體待場館驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42840408793)

## 2026-11-10 Windows 管理包的場館 HTTPS

- 啟動器讀取私人實例內的 `control-https.json` 與管理員提供的 PFX。Kestrel 在指定場館 IPv4 監聽 HTTPS，原管理 HTTP 留在 `127.0.0.1` 給同機遊戲伺服器。舊實例可照原方式啟動。HTTPS 模式拒絕外部 HTTP 設定，並忽略繼承的額外 Kestrel 端點。 [場館設定與套件](WINDOWS_CONTROL_PACKAGE.md#啟用場館-https)
- Windows 實際解壓包含 552 筆清單、532 個發行檔案，管理服務舊流程通過 107 項。新 HTTPS 場在同一台 Windows 的區網 IPv4 通過 24 項，含六角色、只信任合成根憑證時驗證中繼鏈、七個拒絕啟動案例、區網 HTTP 拒絕、主控寫入與房控權限。
- 同包接 Windows 0.50.0 原生伺服器及一個模擬玩家，最終 `run-899b3a2ae45c4bdabdbad007d34f8f7e` 退出碼 0，30 項通過。HTTPS 房控簽發票券及觀察原生場，房外觀察被拒。封存後第 16 格與即時畫格相同，雙封存尾端為 21 格、0 筆戰鬥事件，原玩家戰績與伺服器確認各一筆。兩個管理監聽器與原遊戲伺服器均已停止。 [原生報告](../artifacts/control-https-checks/run-899b3a2ae45c4bdabdbad007d34f8f7e/checks.json)
- 原生首場 `run-d1be96bc8225412683f93f08c4626e3f` 用錯查詢路徑，收到 HTTP 405。次場 `run-349750783ec54af09f8656c841f6d013` 用開場時的公告驗證結束狀態而被拒。兩場失敗與原封存保持，修正驗證腳本後以第三場通過。
- Release 零警告、1,053 項核心、768 項 HTTP、97 項世界串流、6 項管理管線、7 項封包邊界及 8 項房控預檢通過。功能來源 `e127ce0a1fd1c25485633eb73f51473ecc524b9b`。GitHub Actions job `129903015566` 因帳務或支出上限未啟動。正式憑證、六台工作站跨機、實體頭盔與廠商硬體仍待場館驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42837359749)

## 2026-11-10 場館主控與五房管理入口預檢

- `check-venue-operator.py` 從指定工作站讀取管理網站的 HTTPS 入口，每次請求先核對信任鏈、站台名稱與管理員提供的葉憑證指紋，再檢查匿名拒絕、角色及房間。工具只用 GET，結果不含操作員金鑰、操作員 ID 或場次。 [操作方式](WINDOWS_CONTROL_PACKAGE.md#從房控電腦核對管理服務)
- 8 項專項、6 項套件驗證及 6 項 UDP 預檢測試通過。`vop-fdffcd45` 用同一台 Windows 的 HTTPS 測試代理接上隔離管理包 0.31.108，12 個案例符合預期。主控看見五房，五個房控各只看見自己的房間。錯誤房控、無效金鑰和轉址皆拒絕。錯誤指紋、名稱和不信任 CA 三案都未送出 HTTP 請求。測試代理與隔離服務已停止。 [本機報告](../artifacts/venue-operator/vop-fdffcd45/checks.json)
- 重驗 Windows 遊戲伺服器啟動器 1.10.0 時，測試畫面可輸入既有管理實例路徑。`PickerHost.exe` 兩次遮住載入按鈕，測試未到伺服器啟動，原 360 秒到期後退出碼 1。`run-96c1595722604444a69a445066cd0bfe` 保留操作觀察和失敗資料。隔離 GUI 與管理服務均已清理。
- 預檢來源 `e25e176bef54d597087bf1c54408813368143530`，GitHub Actions job `129894658494` 因帳務或支出上限未啟動。場館的正式 HTTPS 入口、六台工作站、實際玩家跨機與頭盔待現場驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42834976696)

## 2026-11-10 硬體排演保留管理異常的終止結果

- 模擬器 0.2.11 在管理服務拒絕或回覆無效時關閉該房模擬連線，取消待確認批次、保留先前確認，並在完成該房報告後發布 `stopped`。原生五房測試分別注入拒絕、無法解析的 JSON 與無效回饋內容。三房各保留一筆原確認並取消一筆待確認回饋，房 5 仍在原連線成功確認。全館以退出碼 1 保存三房失敗。 [五房操作](HARDWARE.md#一次啟動與停止五房排演)
- 0.2.10 基準場 `run-c4018ab8ebf1435c8609c643b497ad6b` 已觀察到原連線關閉，房 1 仍留在 `awaiting-ack` 且未寫終止報告，測試失敗後程序清理完成。0.2.11 第一輪解壓場 `run-b51267e2bbc14a7a889d688b62ddf4f5` 在既有重連檢查等不到新回饋而失敗。重連測試之後分開核對握手前的讀取與 ready 後的附掛，保留原斷言與期限。
- Release 零警告、1,053 項核心、38 項離線及 70 項即時檢查通過。最終解壓場 `run-b6f6a3940c9d407ba544c2480b809b79` 再通過 70 項，八個套件檔案及範例輸出雜湊相符。 [套件資料](HARDWARE_SIMULATOR.md)
- Windows 0.50.0、管理包 0.31.108 與解壓模擬器 0.2.11 的原生場 `run-aa4fff925c284b20b3affd85cb49c3ad` 通過 444 項。獨立與合併各 25 席，十房次核對原設備、座位與入場，共 50 席收到模擬傷害回饋，212 筆模擬確認。六場 1,584 格完整回放、50 份原戰績與伺服器確認、11 份 CSV 及雙封存通過，C／F 238 檔一致，全部程序已清理。
- 功能來源 `a647e4127fae567d0877231515b3b0cd5b6ebaa7`，重連測試 `725eb89a7dbcb17a71ef4b283f2a8a6e3cfc0cfd`，原生測試工具 `712539647ccdefeefef87d2b78e5b905dbb7e11c`。三個 GitHub Actions 工作因帳務或支出上限未啟動。廠商協議、實體設備停止與輸出、跨機和頭盔仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42832944431)

## 2026-11-10 Windows 0.50.0 獨立五房長場複驗

- Windows 0.50.0 及管理包 0.31.108 的同機獨立五房 `20261110-214953-c8e65da7` 完成 900 秒測試，退出碼 0，13 項通過。五房各五席，42,804 格完整回放、25 份原戰績及伺服器確認、五份 CSV 及雙封存相符。每席發射 90 次、換彈 45 次。C／F 97 檔一致，活動場次及剩餘程序均為零。
- 封存工具逐房重查五個原世界日誌、五個原戰鬥日誌、25 份玩家日誌及五份 CSV。房 1 的 25 個暫停畫格維持 tick 42，同一 UTC 區間內另四房分別前進 50、50、51、50 tick。共同運行區間為 895.670 秒，每席皆有區間內發射紀錄。封存核對保存在 `artifacts/desktop-0500-independent-closure-verification.json`。
- 同工具重查 0.49.0 原封存，確認 896.079 秒的共同運行、25 席發射及各房暫停隔離。首輪離線重查因戰績精度型別而拒絕，保留原錯誤，改用與場館工具一致的小數型別後通過。18 項獨立封存、78 項場館、26 項長場及 14 項世界日誌檢查通過。 [封存重查操作](DESKTOP_ENDURANCE.md#獨立五房封存重查)
- 封存工具來源 `b1cc8f4d0b853f82f1b58197ad2706900d7a4ba8`。GitHub Actions job `129873737422` 因帳務或支出上限未啟動。跨機 25 人、Quest 3、VIVE XR、實體 MR 與廠商硬體仍待現場驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42828996753)

## 2026-11-10 Windows 0.50.0 合併長場診斷複驗

- Windows 0.50.0 及解壓管理包 0.31.108 的 25 席同機合併場 `20261110-212904-c88bec46` 運行 900 秒，退出碼 0，6 項通過。8,593 格完整回放、25 份原戰績與伺服器確認、CSV 及雙封存相符。逐席 90 發、45 次換彈，原戰鬥日誌 2,250 發。無活動場次或剩餘測試程序，C／F 141 檔一致。
- `analyze-pose-continuity.py --exercise` 可從原封存按席位核對失效與恢復畫格，依原連線對照 26 份診斷。本次中斷數為零，執行中最大擷取間隔 199 毫秒，上一輪失效時間範圍的九格皆有 25 席有效姿態。既有受控失效案例則辨識房 1 席 1 第 46 至 50 格失效、第 51 格恢復，對應客戶端 RPC 送出、伺服器接收與姿態接受空窗。10 項診斷、26 項長短場工具及 14 項世界日誌測試通過。 [診斷操作](POSE_CONTINUITY.md#校準與分析)
- 診斷工具來源 `60ee0b8b66bab149c2cc16d235910f77f1f81920`。GitHub Actions job `129861648130` 因帳務或支出上限未啟動。上一輪原生失效保持未通過，原因尚未確認。跨機 25 人、頭盔、實體 MR 與廠商硬體仍待現場驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42825509086)

## 2026-11-10 Windows 0.50.0 合併長場與姿態取證

- 原生 25 席 900 秒目標場 `20261110-210741-90fd6105` 在 720,607 毫秒的第 6,843 格出現四席姿態失效，以退出碼 1 結束。前格至失效格相隔 784 毫秒，下一格四席均恢復。6,849 格讀到封存尾端，25 份原戰績及伺服器確認、1,800 筆原戰鬥事件雙封存和程序清理通過。實際每席 72 發及 36 次換彈。C／F 89 檔同雜湊。首次取證比對直接比較 JSON 小數與原二進位單精度表示而中止，依單精度核對後確認失效格相符。
- 原測試場使用 Windows 0.50.0 與管理包 0.31.108。新增的 `--pose-continuity` 將既有診斷接入 Linked 長場測試。25 席 60 秒場 `20261110-212320-ec738926` 以退出碼 0 通過 6 項、605 格完整回放、25 筆戰績確認、26 份診斷，C／F 141 檔相符。未開啟診斷的五席短場另通過 5 項與 141 格回放，C／F 29 檔相符。
- 受控場 `20261110-212720-cf7c8ff2` 暫停並恢復房 1 測試玩家原程序的 60 個執行緒，驗證第 46 至 50 格姿態失效，原測試維持退出碼 1。57 格完整回放、六份診斷及 C／F 41 檔相符。受控玩家最大姿態送出間隔 0.983 秒、伺服器接收間隔 0.978 秒。此場驗證失敗後仍可收集診斷，原自然失效的成因仍待取證。26 項長短場工具及 8 項姿態分析測試通過。
- 診斷工具來源 `07ee33d8582d4a3c40de588efd13b634757dec11`。GitHub Actions job `129858320795` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42824548186) · [長場操作](DESKTOP_ENDURANCE.md#windows-0500-合併場姿態失效)

## 2026-11-10 五房逐席直連驗收

場館驗收新增 `requireDistinctRemoteRoster`。開啟時須核對共同執行時段、25 個原名額各自不同的外部 IPv4、歷次核准與 UDP 來源、原戰績及伺服器確認。重連可換 UDP 埠，IPv4 須維持一致。摘要只列數量。 [直連驗收](EXTERNAL_CLIENTS.md#核對-25-席各自的直連來源)

- 78 項場館驗收及 6 項 UDP 預檢測試通過。合成證據在獨立及合併模式各核對 25 席、26 條歷次連線。反例涵蓋兩席共用來源、來源屬伺服器、重連改變 IPv4、原啟動埠不符及缺少核准連線的配對。
- 唯讀重驗原生 `run-916fc4ad016b429f94d2b45c71688450` 的兩份同機封存資料。原選項產生的摘要與先前保存一致；原合併及獨立場可分別核對 3,500 與 3,401 毫秒的 25 席共同執行時段。套用嚴格直連驗收後兩者皆因沒有每席獨立的外部來源而拒絕。前後雜湊核對合併 30 檔、獨立 42 檔相符，證據為 `artifacts/field-distinct-remote-readback-01/summary.json`。
- 功能來源 `0fdcbc5b43b616d057d514dcf4a5eeaf3c504ec7`。GitHub Actions job `129850726864` 因帳務或支出上限未啟動。實際 25 席跨機與頭盔、MR、廠商硬體仍待現場驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42822332154)

## 2026-11-10 回放追查同發射擊

控制台 0.31.108 可由暫停回放的發射、命中或擊殺事件追查同發射擊的已保存畫格。主控可選擇全場或單房，房控限本房，個人檢討沿用原玩家。查詢使用原戰鬥報告及已接受的保存畫格，並遵守本次回放的固定尾端。 [射擊檢討](WORLD_RECORDING.md#追查同發射擊)

- 核心 1,053 項、世界串流 97 項、Node 110 項及解壓管理包 107 項通過。核心測試使用跨格發射與命中，核對較早尾端不會讀到已上報但未在範圍內保存的命中。世界串流使用實際 API、WebSocket 與 SQLite，核對本房、外房拒絕及重新啟動後由既有記錄重建同發關聯。管理包 C／F 共 27 檔雜湊一致。
- 解壓包 Chromium 通過 848 項。實際從個人檢討的擊殺列追查，顯示該發的三筆同格紀錄，停留於原畫格；更換房間會清除追查並保留個人檢討。畫面保存在 `artifacts/console-shot-trace108/world-shot-trace.png`。
- Windows 原生短場 `20261110-210129-3b5eb0d9` 通過 25 項。合併及獨立模式各有 25 個同機自動化客戶端，六場完整回放 1,928 格。100 組同發追查與原保存紀錄逐欄相符，涵蓋 100 筆發射、100 筆命中、50 筆擊殺。這六場的同發事件均保存在同格，跨格由核心測試核對。六份 CSV、戰績送達與伺服器確認、雙封存及清理通過，C／F 174 檔一致。
- 發行一致性報告 `artifacts/venue-release-shot-trace108.json` 核對管理包來源 `ce3fb49c14cfc99a5fc9f1265b3baeab2cb4cc0c` 與既有 Windows／Quest 0.50.0。GitHub Actions job `129845039989` 因帳務或支出上限未啟動，執行步驟為零。Quest 3、VIVE XR、實體 MR 場地、跨機 25 人及廠商硬體待驗。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42820653201)

## 2026-11-10 回放片段戰績

管理包 0.31.107 可在回放標記後讀取 300 格以內的片段戰績。起訖格皆計入，沿用房間及個人檢討範圍。使用已接受的原戰鬥事件計算耗彈、命中、擊殺、中彈與耗損。片段命中率以同房、同一片段內發射並確認命中的原射擊 ID 配對。 [片段操作](WORLD_RECORDING.md#重看指定片段)

- 核心 1,048 項、世界串流 94 項、Node 110 項、解壓管理包 107 項及解壓包 Chromium 843 項通過。SQLite 測試核對跨界命中、空片段與別房拒絕。首輪新增測試誤將敵軍 ID 寫入戰鬥傷害請求而遭既有驗證拒絕，修正測試資料後通過。管理包 C／F 27 檔雜湊一致。
- 首輪原生 `run-3b6478737f0f4a3dae69cf761988595b` 已完成原世界、戰績封存與逐房傷害核對，後續瀏覽器分房匯出斷言失敗，仍列為未通過。測試預期更新為依房間保留有效策略欄位，產品及套件沿用同一版本。首輪清理完成，C／F 215 檔同雜湊。
- 原生重跑 `run-e221df3f749b453bb1a8c1f1df4a7418` 通過 435 項。合併場房控從第 3 房個人檢討讀取第 187–250 格，畫面顯示該席 1 次中彈、20 點耗損，與原保存事件一致；無發射時顯示無命中率。查詢維持原回放位置及原玩家範圍，未發出寫入。獨立與合併各 25 個同機 Windows 客戶端，六場 1,615 格完整回放、215 筆傷害、50 筆原戰績及伺服器確認、雙封存與分房 CSV 通過。C／F 220 檔一致，程序已清理。
- 發行一致性報告 `artifacts/venue-release-clip-stats107.json` 核對管理包來源 `3a5b06a2ecdcb38fdecfddc19284b810134ee1fe` 與既有 Windows／Quest 0.50.0。GitHub Actions job `129836905649` 因帳務或支出上限未啟動。實機頭盔、MR 場地、跨機 25 人與廠商硬體待驗。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42818282071)

## 2026-11-10 主控五房共同取樣與中斷回放

控制台 0.31.106 在原房卡請求內取得五房共同取樣。場次版本於讀取期間一致時，主控能看到取樣時間及各房原畫格號。出現姿態中斷時，可由該房總覽直接開啟原回放，並返回同房即時觀戰。超過原 1.5 秒期限的畫格會撤下確認席數、畫格號及回放入口。 [追蹤總覽](PLAYER_READINESS.md#執行中五房追蹤總覽)

- 本機 .NET 建置、核心 1,045 項、世界串流 92 項及 Node 110 項通過。工作區 Chromium 專項 70 項、最終解壓包 Chromium 841 項通過。解壓包涵蓋合併與混合模式的共同取樣、原畫格定位、返回即時觀戰及期限。
- 三包整合首兩輪 `run-ad2aaa753c2e4117b1a0af91b37ca757` 與 `run-84a77b5751934756b25dcf07c904fd7a` 保留未通過。兩輪均開啟原中斷畫格，第二輪診斷確認失敗在「全部 API 都用 GET」的測試斷言。主控登入會以 `POST /api/mission-layout` 試算草稿，端點只讀。修正測試僅將這一個端點分類為讀取，其餘非 GET 仍視為寫入。兩輪清理完成，C／F 各 132 檔同雜湊。
- 同一管理包第三輪 `run-c40b015fb8e645d6960da97f9920a885` 通過 435 項。獨立與合併模式各有 25 個同機 Windows 客戶端，主控從總覽開啟第 5 房第 2 席的原中斷畫格，獨立 229 → 238、合併 228 → 238，兩輪各見一筆唯讀版面試算、原回放與即時各一筆串流，無寫入。六場 1,657 格完整回放、50 筆原戰績及伺服器確認、雙封存及 CSV 通過。C／F 226 檔一致、程序清理，管理包另通過 107 項與 27 檔 C／F 一致。
- 發行一致性報告 `artifacts/venue-release-monitor106.json` 核對管理包來源 `ddb06454ee2a350a4364705799da0dccef07f621` 與既有 Windows／Quest 0.50.0。GitHub Actions job `129827747330` 因帳務或支出上限未啟動。實機頭盔、MR 場地、跨機 25 人與廠商硬體仍待驗。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42815592735)

## 2026-11-10 五房追蹤共用取樣時間

管理包 0.31.105 提供主控限定的五房追蹤取樣。管理服務在同一次讀取內核對五房場次與版本，合併場回傳一份原場次快照，獨立場回傳五份共用 `sampledAtUtc` 的快照。Quest 工具把請求與接收耗時納入 1.5 秒期限，再逐席核對原入場與追蹤。 [追蹤驗收](QUEST3.md#核對頭盔追蹤席位)

- 延遲測試讓第一房的畫格在傳輸期間過期，該房五席回報 `source-expired-in-transit`，其餘 20 席仍按原快照判定。不同取樣時間的快照整批拒絕。首輪測試未還原刻意變更的時間，修正測試資料後通過。Quest 工具 50 項、核心 1,045 項、世界串流 92 項與解壓管理包 107 項通過。
- 原生首兩輪 `run-a7dd630ebbaa42f5821f477c474f8a04`、`run-2e8e1a7322aa457395497547ca4e2965` 在管理服務就緒之前逾時。兩個啟動器回報 `WebException` 並確認子程序已退出，原因尚未確定。原證據保留，隔離複本各 9 檔 C／F 同雜湊。單獨管理包另驗啟動與重開，27 檔同雜湊。
- 第三輪原生 `run-2bc022b4d2b6454ea84edeec9ac8f58b` 通過 427 項。獨立與合併各啟動 25 個同機 Windows 客戶端，其中第 5 房第 2 席使用 Unity 模擬 OpenXR。兩模式都用原 ZIP 核對該席就緒、中斷及恢復，並將整批取樣逐場比對原錄製畫格。獨立場有五份同時間快照，合併場有一份。六場 1,593 格完整回放、50 筆原戰績與伺服器確認、雙封存及 CSV 核對通過。隔離程序已清理，224 檔 C／F 同雜湊。解壓管理包另通過 VR 28 項及 MR 10 項瀏覽器專項。
- 發行一致性報告 `artifacts/venue-release-tracking105.json` 核對管理包來源 `2c9666b9b6bc5dd17919d28d910365c0c10a3a46` 與既有 Windows／Quest 0.50.0。GitHub Actions job `129820965914` 因帳務或支出上限未啟動。實機頭盔、MR 場地、跨機 25 人及廠商硬體待驗。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42813608043)

## 2026-11-10 Quest 逐席寫入前核對原五房來源

部署工具搭配管理包 0.31.104，會在每席開始寫入前重新核對整份原部署 ZIP 的 25 個入場、端點及最新遊戲畫格。VR、MR、混合與部分裝置清單皆適用。線上單席安裝在 APK 安裝前後各核對一次。只讀預檢仍可在來源暫停時核對原票券。 [部署操作](QUEST3.md#用裝置清單部署-25-席)

- MR 合併場以解壓 Windows 原生 Unity 來源與三個模擬 ADB 裝置驗證。第一席送出啟動後暫停原 Unity 執行緒，嚴格核對回報 25 個 `source-stale`，只讀仍能核對原 25 個入場。工具在第二席寫入前回報 `venue-check-failed`，第三席未嘗試。恢復同一來源後，接受畫格由 86 前進到 90。同一份 ZIP 搭配新清單只重試後兩席，第一席位元組一致。另以有效票券改寫 UDP 埠，嚴格核對精確拒絕該席。
- MR 原生 `run-fc2f107171e94fb2825125d9c9724359` 通過 154 項。合併與獨立各核對完整 25 席及部分 5 席模擬 ADB 寫入，六個 Preparing 至 Ended 場次通過雙封存與 600 格完整回放。混合原生 `run-d9426317ed104ca280e90805bc27bc13` 通過 120 項，核對五個指定模擬裝置、活躍檔案驗證故障、只重試剩餘席位，以及五場 589 格完整回放。MR、混合及管理包的 C／F 複本分別有 59、52 與 27 個檔案雜湊一致，測試程序已清理。
- 本機 .NET 建置、核心 1,045 項、世界串流 92 項、解壓管理包 107 項、Quest CLI 50 項、VR 瀏覽器專項 26 項與最終管理包 Chromium 833 項通過。線上單席測試在模擬 APK 安裝後才讓來源失效，檔案未寫入。VR 專項驗證已簽檔案仍可做只讀核對，實際寫入驗證會拒絕 loopback 與未發布有效畫格的舊端點。
- 發行一致性報告 `artifacts/venue-release-quest-write104.json` 核對管理包來源 `18890ea5ca25a08b9c095811534bf1d739768bee` 與 Windows／Quest 0.50.0。GitHub Actions job `129814804143` 因帳務或支出上限未啟動。Quest 實機、跨機 25 人、MR 實體校正及廠商硬體待驗。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42811791421)

## 2026-11-10 Quest 3 MR 五房部署包交付前核對來源

控制台 0.31.103 在 MR 五房部署區顯示各房原 UDP，並使用現有房間就緒回報停用缺少可用端點的下載。來源恢復時保留五份已選校正檔，等待操作員重新點選。收到已簽 ZIP 後，會重新核對場次、校正雜湊、入場名冊及原端點。 [部署操作](QUEST3.md#從主控台下載五房部署包)

- 解壓包原生測試 `run-1007f626603145e5a757711bd583772a` 通過 133 項。暫停受控合併場原 Unity 程序的 69 個執行緒後，新配票回 `409 venue-endpoint-stale`。測試將一份已簽回應交給原 Chromium 頁面，頁面擋下下載並保留五份校正檔。恢復原程序後，原場次、UDP 與世界標頭一致，接受畫格由 14 前進到 17。同一頁在下一次點選後下載，驗證原始校正位元組及 25 個已簽入場。獨立模式另驗五個原生端點及 25 席。六場皆由 Preparing 進入 Ended，雙封存及 299 格完整回放通過，隔離程序清理、C／F 共 59 檔雜湊一致。
- 核心 1,045 項、世界串流 92 項、Node 110 項、解壓管理包 107 項與最終包 Chromium 831 項通過。候選包另外通過 MR 專項 10 項。管理包 C／F 27 檔雜湊一致。首次最終打包遇到既有候選收據而中止，保留原輸出並在新暫存路徑打包。發行報告核對管理包來源 `06d24d683496b785f25b1d19d7c05ade8f0f817d`，遊戲沿用 Windows 與 Quest 0.50.0。 [管理包](WINDOWS_CONTROL_PACKAGE.md)
- GitHub Actions job `129807846050` 因帳務或支出上限未啟動。Quest 3 實機安裝、MR 實體校正、跨機 25 人與廠商硬體待驗。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42809731853)

## 2026-11-10 五房配票預覽跟隨原遊戲來源恢復

控制台 0.31.102 使用同一份房卡回報核對已開啟的 VR 或混合五房配票預覽。原來源停止更新會停用下載，原場次、UDP 及名冊相同且來源恢復後可在原預覽繼續。管理服務仍在簽票時檢查來源，操作員點選下載後仍核對同一組端點及 admission。 [配票操作](EXTERNAL_CLIENTS.md#按房間下載連線檔)

- 解壓三包 `run-562a53f7745345f9ba1972df5ec28d41` 通過 438 項。獨立與合併各 25 個同機 Windows 玩家程序由瀏覽器下載的原票券入場。正常六場 961 格回放、50 筆戰績及伺服器確認、6 份 CSV。整批端點寫入回復與永久中止來源的配票拒絕亦通過。原生 C／F 250 檔雜湊一致，隔離程序已清理。
- 在另一個合併場，以 Windows 執行緒暫停功能短暫停止測試用 Unity 程序。保持原 Chromium 頁面及已讀取的預覽，實際驗證管理服務暫停簽票及瀏覽器停用下載。恢復原 69 個執行緒後，原程序 handle、場次、世界來源、UDP 及入場名冊一致，接受畫格由 13 前進至 16。同一預覽重新開放，操作員點選後成功下載五房 ZIP。這是受控的本機程序暫停／恢復。 [Windows SuspendThread](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-suspendthread)
- 核心 1,045 項、世界串流 92 項、解壓管理包 107 項、Node 110 項及 Chromium 831 項通過。管理包 C／F 27 檔雜湊一致。完整 HTTP 測試前三個無效憑證案例通過，第四個程序在原 10 秒退出期限逾時，該次維持未通過。
- 管理包來源 `7d59aca0be1d316a448260f9e4be9fa44c203ea8`。沿用 Windows、Quest 0.50.0 與啟動器 1.10，離線一致性報告為 `artifacts/venue-release-ticket-recovery102.json`。GitHub Actions job `129800166483` 因帳務或支出上限未啟動。跨機、頭盔與廠商硬體仍待現場驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42807457823)

## 2026-11-10 遊戲來源停止更新時暫停配票

管理包 0.31.101 記錄新批次公告的端點。新發單席、整房及全館連線檔前，服務要求同一場次最近五秒內有未暫停發布且階段相符的原世界畫格。控制台保留原 UDP，並標示暫停配票。已簽票券依原期限與 admission 驗證。舊公告仍依原配票條件。 [配票操作](EXTERNAL_CLIENTS.md#按房間下載連線檔)

- 解壓三包 `run-7a412748f91f4af2a18086ec5546ed54` 通過 434 項。獨立與合併模式皆從實際 Chromium 下載五房連線檔，各有 25 個同機 Windows 玩家程序用原票券入場。正常六場共 999 格完整回放、50 筆原戰績與伺服器確認、6 份 CSV。第 5 房公告失敗時的整批回復同樣通過。C／F 原生快照 248 檔雜湊一致，隔離程序已清理。
- 另開一個已公告的 Windows 合併場，來源有效時成功簽出單席、整房與五房票券。停止該啟動器並確認原 Unity 程序已退出後，新發三種票券均回 409。五張房卡標示暫停配票，Chromium 停用五房下載。原 UDP、第 9 格錄製與已簽票券的 admission 仍可查核。測試使用 `--check-venue-ticket-freshness --check-vr-venue-tickets --check-room-endpoints` 搭配三包場館批次旗標。
- 核心 1,045 項、世界串流 92 項、Node 109 項及解壓包 Chromium 831 項通過。初兩次以工作區 DLL、第三次以解壓管理包 DLL 跑完整 HTTP 測試，都在無效憑證程序的原 10 秒退出等待逾時。另用 0.31.100／0.31.101 解壓包單獨測試空白及過短憑證，四次均記錄拒絕且未監聽，未確定前三次逾時原因。首次獨立管理包測試於原服務就緒前拒絕，報告為 `WebException` 並確認原子程序已退出。隔離重跑 `run-9232206467f94b89a5411cfe770b16cb` 通過 107 項。首輪及重跑快照分別 9 與 27 檔 C／F 一致，原失敗證據保留。
- 管理包來源 `258bd11357ca847e41da43dcfc5d003b27be86d0`。Windows 與 Quest 0.50.0 搭配新版管理包通過離線一致性核對，報告為 `artifacts/venue-release-ticket-source101.json`。GitHub Actions job `129792257187` 因帳務或支出上限未啟動。頭盔、跨機及實體硬體仍待現場驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42805148932)

## 2026-11-10 五房端點整批公告

Windows 啟動器 1.10 等所有原遊戲程序與 UDP 綁定都確認後，由管理包 0.31.100 以同一筆 SQLite 交易公告端點。全館就緒檔須等回條核對後才寫出。啟動前會驗證管理服務能力。以原批次重送可取得同一組端點與原建立時間。 [場館啟動](WINDOWS_SERVER_PACKAGE.md#依場館計畫批次啟動)

- 核心 1,045 項、HTTP 768 項、世界串流 92 項、解壓管理包 107 項、Node 109 項及 Chromium 831 項通過。另在隔離的 0.31.99 管理服務確認新版批次命令在建立工作目錄、遊戲來源及就緒檔前拒絕啟動。
- 首次原生 `run-cef434120bbe4067bacf5e9701276f5f` 通過 420 項。兩種模式各 25 個同機玩家程序，正常六場 945 格回放、50 筆戰績與伺服器確認、6 份 CSV。另在新建隔離資料庫的第 5 房端點寫入設定受控故障，管理服務記錄實際觸發的拒絕，前四筆一併撤回。五房端點均回 404，房卡未公告，五個原遊戲程序停止，已附掛的場次及錄製仍保留。這次故障輪的證據與正常六場分開。
- 首次 F 快照在測試用 SQLite 連線明確關閉前複製，帶有當時的 WAL／SHM。程序結束後 C 的資料庫已完成檢查點，兩份快照的檔案組合與世界資料庫雜湊不同。原兩份保留。後續測試工具會在離開故障設定區段時明確關閉測試連線。
- 修正測試後以相同三個套件重跑 `run-c0cfaae4d77f44d0b5d064bb03eb610a`，420 項通過。兩種模式各 25 個同機玩家程序，正常六場 935 格完整回放、50 筆戰績及 6 份 CSV。原生故障再確認五房均無端點、五個原程序已停止、管理服務記錄實際 SQLite 拒絕。原生 C／F 238 檔雜湊一致，管理包測試另有 27 檔一致。重跑使用 `--check-venue-launcher --check-venue-plan-ui --check-venue-preview --check-venue-endpoint-batch` 及三包場館開場／收尾旗標。Windows 視窗點擊、頭盔及跨機另驗。
- 發行一致性報告 `artifacts/venue-release-endpoints100.json` 使用原 Windows 與 Quest 0.50.0。伺服器包 330 筆清單，其中 328 筆與 1.9 相同。功能提交 `ec4cadb721e9d7970de1c3d7b8358e5f6e81b7c0`。GitHub Actions job `129784155147` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42802752021)

## 2026-11-10 Windows 五房批次啟動視窗

啟動器 1.9 可從主視窗開啟「五房批次啟動」，核對控制台下載的 JSON，顯示房號、任務、原場次與 UDP。啟動前會重讀計畫與原管理實例，並比較操作員剛核對的目標。視窗與命令列共用啟動、封存與清理流程。另提供 `--venue-check` 查閱同一份唯讀預覽。 [操作方式](WINDOWS_SERVER_PACKAGE.md#從-windows-視窗核對並啟動)

- 解壓三包原生 `run-4f9e261a3540461f8834966ab76deb1b` 通過 410 項。Chromium 下載兩種原計畫，實際啟動器先核對，確認場次沒有變動或提前公告，再用同一份計畫批次啟動。核對拒絕錯配房間、占用第 5 房的 UDP 與未鎖定校正的合併 MR。啟動階段仍檢查原場次鎖。獨立與合併模式各 25 個同機 Windows 玩家程序，六場 899 格完整回放、50 筆原戰績與伺服器確認、6 份 CSV 及戰鬥／世界雙封存通過。C／F 217 檔雜湊一致，隔離程序已清理。
- 真 WinForms `venue-155030b7ab6d40fc8d3d72f5bccb901f` 以 `--venue-window` 開啟，已觀察原計畫路徑、四個欄位及核對前停用的「啟動全館」。兩次點擊「核對計畫」都由桌面工具判定遭 PickerHost 遮擋。此次停在核對前，沒有從視窗啟動來源。隔離視窗及 API 已停止，C／F 10 檔雜湊一致。
- 新伺服器包核對 330 筆清單。1.8 與 1.9 的啟動器及說明有更新，其他 328 個檔案逐檔相同。管理包 0.31.99、Windows 遊戲與 Quest APK 0.50.0 通過離線一致性核對，報告為 `artifacts/venue-release-launcher19.json`。功能提交 `8110e2e0d7954ba1ce1dfdd9859aa0106d959268`。GitHub Actions job `129780006892` 因帳務或支出上限未啟動。實體頭盔、跨機及廠商硬體仍待現場驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42801536027)

## 2026-11-10 確認分房敵軍策略恢復與保護全館預覽

控制台 0.31.99 以原逐房命令序號保留恢復沿用的房卡狀態。使用者可開啟確認該命令的原房間保存格。全館預覽會列出將清除的分房策略。房控在預覽後改動或恢復策略時，管理服務拒絕舊預覽，主控重讀後可依新條件送出。已保存的舊請求可用原內容取回原回條。 [操作方式](LAYOUT.md#合併場分房敵軍策略)

- 核心 1,045 項、HTTP 768 項、世界串流 92 項、解壓後管理包 107 項、Node 109 項及 Chromium 831 項通過。核心測試核對套用及恢復後的舊預覽、原事件重開、原回條重試及舊版事件相容。瀏覽器證據在 `artifacts/console-room-enemy-fences99-package`。
- 解壓三包原生 `run-8ec54c1c6a98437997cf2ffd79a2f07a` 通過 379 項。獨立與合併模式各有 25 個同機 Windows 玩家程序。第 2 房改用巡邏與自動攻擊，主控在 Chromium 看到會清除本房策略的提示。管理服務拒絕三次舊預覽送出，接受新預覽並原樣重送回條。第 2 房恢復命令為 31，Chromium 房卡開啟原保存第 180 格，該格觀察到管理序號 32。封存回放再次核對原格、同房策略及射擊隔離。六場 849 格、50 筆戰績及伺服器確認、6 份 CSV、戰鬥與世界雙封存通過。程序已清理，管理與原生快照共 245 檔的 C／F 雜湊一致。
- 管理包來源 `2fd259189c45ea85c0550af4d8e8c57003bb73b4`。沿用 Windows 與 Quest 0.50.0，與新管理包的離線一致性報告為 `artifacts/venue-release-room-fences99.json`。本輪涵蓋桌面與瀏覽器，頭盔、跨機及實體硬體仍待現場驗收。GitHub Actions job `129773323466` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42799565321)

## 2026-11-10 合併場分房敵軍策略

控制台 0.31.98 與遊戲 0.50.0 讓合併場的房控操作本房守備、巡邏、推進及自動攻擊。主控可指定任一房，也可套用全場設定以清除逐房覆寫。敵軍數量由全場控制。房卡以保存畫格確認本房策略，觀戰、回放及片段可讀取當時的有效策略。遊戲來源以原戰鬥串流宣告能力，管理服務沿用原命令權限及錄製核對。 [操作方式](LAYOUT.md#合併場分房敵軍策略)

- 核心 1,038 項、HTTP 768 項、世界串流 92 項及真 Unity Editor 272 項通過。解壓管理包通過管理 107 項、Node 109 項及 Chromium 831 項完整回歸。另用解壓包與獨立的測試場次核對第 2 房 Chromium 權限、原命令內容、回條及畫面。
- Windows／Quest 0.50.0 真建置完成，Android code 65、NGO 31。兩端來源指紋為 `e06fd32af6403707e9ac98154d994b17a0571462bf05551a9f06ea86da634bc8`，場景與玩家 prefab 網路識別相同。發行一致性報告為 `artifacts/venue-release-room-enemies98.json`，核對管理包、Windows 伺服器、Windows 玩家及 Quest ARM64 開發簽章。 [版本與套件](EXTERNAL_CLIENTS.md#遊戲版本相容性)
- 首次原生批次 `run-1f78f204a9a545cebf7b46d87b964409` 的獨立場已完成，合併場的房控測試在送出前的停用欄位斷言失敗。原失敗保留。測試改核對欄位的 DOM disabled 與實際按鈕的 disabled，另依原 API 使用 `roomId` 及逐頁查閱回放。產品套件沿用。
- 解壓三包原生 `run-d6089a22eea9449ab63f7daf2cc15adc` 通過 373 項。獨立與合併模式各有 25 個同機 Windows 玩家程序。合併場拒絕第 1 房和遊戲伺服器以憑證改第 2 房。第 2 房在 Chromium 改為巡邏及開火，房卡連至原保存畫格；原回放確認僅第 2 房巡邏、一次射擊只影響第 2 房，恢復沿用後停止開火。逐房回放設定記錄第 2 房兩次切換，第 1 房全程守備。六場 866 格回放、50 筆原戰績及伺服器確認、6 份 CSV 與戰鬥／世界雙封存通過。隔離程序已清理，C／F 的 218 個檔案雜湊一致。重跑使用 `scripts/check-server-package.py --check-venue-begin --check-venue-end --check-linked-room-enemies` 並傳入三個解壓包。
- 使用者關閉視窗後，以 0.50.0 伺服器包重驗 Windows 選檔。`run-cecd7420a6b94a4b8d6e96f756bd3f87` 兩次點擊「選擇檔案」皆由桌面工具判定遭 `PickerHost.exe` 遮擋。測試停在開啟選檔視窗前，沒有啟動遊戲伺服器。隔離 API 和啟動器已結束，C／F 的 9 個檔案雜湊一致。
- 功能提交與管理包來源 `15df0b771745653e91f47c9c594ac61ac52c4940`。GitHub Actions job `129764258435` 因帳務或支出上限未啟動。實體頭盔、跨機玩家及廠商硬體仍待現場驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42796897407)

## 2026-11-10 從主控台下載 Windows 五房啟動計畫

控制台 0.31.97 顯示五房的原任務、場次與啟動條件。主控填入本機管理實例路徑、IPv4 與 UDP 埠後，可下載給啟動器 1.8 使用的 JSON。瀏覽器在下載前再查一次場次與序號，若已有新來源或場次改變便停止。管理實例路徑只組入本機檔案，憑證仍由原 Windows 啟動器從管理實例取得。 [下載操作](WINDOWS_SERVER_PACKAGE.md#從主控台下載場館計畫)

- 專項 Chromium 通過 13 項，包含空房、房控與遊戲伺服器權限、獨立 VR／MR 混合房、MR 校正鎖定、重複 UDP 埠、合併場單一端點，以及來源先附掛時拒絕下載。核心 1,030 項、HTTP 768 項、世界串流 92 項及管理包 107 項通過。
- 解壓管理包的 Node 109 項及 Chromium 831 項完整回歸通過。證據為 `artifacts/console-server-plan97-package`，包含兩種模式的原下載與控制台畫面。
- 三包原生批次 `run-2b3559d7158e439a8ee39840a57fce16` 通過 400 項。兩種模式均在實際管理包中用 Chromium 下載計畫，直接交給原啟動器 1.8。獨立與合併場各 25 個同機 Windows 玩家程序，六場 850 格完整回放、50 筆原戰績確認及 6 份 CSV。兩份原計畫隨關閉後的快照保存。原程序清理完成，C／F 的 217 個檔案雜湊一致。頭盔、實際跨機與廠商硬體仍待現場驗收。
- 功能來源及管理包建置為 `d187ba72870e29dfb6f7d3f051a80e3545bcf8e5`。管理包、Windows 啟動器 1.8、Windows 玩家 0.49.1 與 Quest 0.49.1／64 的離線一致性報告為 `artifacts/venue-release-server-plan97.json`。GitHub Actions job `129753420150` 因帳務或支出上限未啟動。 [管理包](WINDOWS_CONTROL_PACKAGE.md) [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42793732969)

## 2026-11-10 依場館計畫啟動 Windows 遊戲伺服器

啟動器 1.8 的 `--venue-run` 讀取指定管理實例與原場次計畫。五個獨立場各有自己的遊戲程序和 UDP 埠，合併場使用一個程序。通過全館啟動檢查及本機場次鎖後才建立程序，所有原遊戲來源、Windows UDP 綁定及公告就緒後才寫出全館就緒檔。每場分別保留原收尾結果。 [場館操作](WINDOWS_SERVER_PACKAGE.md#依場館計畫批次啟動)

- 解壓首候選 `run-524eb3baddeb4d849cda6e7822ee0435` 通過 392 項，兩種模式各 25 個同機 Windows 玩家程序，六場 1,049 格回放與 50 筆戰績確認。最終套件另加入建立任何子程序前的全館場次鎖檢查。首候選套件與證據保留。
- 最終解壓包 `run-2c11025ad1914d4dabb03c5b48e4595e` 通過 413 項。錯配房間、占用第 5 房 UDP 埠或場次鎖、缺少合併 MR 校正鎖定皆拒絕啟動，測試核對場次來源仍未附掛。兩種 VR 模式各 25 個同機玩家程序，六場共 1,370 格完整回放、50 筆原戰績確認及 6 份 CSV。五個獨立房逐房核對已保存的任務時間、環境、敵軍與掩體。另用單場流程啟動已鎖定校正的 MR 伺服器，核對未追蹤玩家拒絕入場、場次維持 Preparing，及結束後 23 格封存回放。原程序清理完成，C／F 的 225 個檔案雜湊一致。實際頭盔、跨機及廠商硬體待驗。
- 最終 ZIP 的 330 筆清單均已核對。與原 0.49.1 伺服器包共有 328 個相同檔案。管理包 0.31.96、Windows 玩家 0.49.1 及 Quest 0.49.1／64 通過原發行一致性核對，報告為 `artifacts/venue-release-launcher18.json`。 [套件與雜湊](WINDOWS_SERVER_PACKAGE.md)
- 功能來源 `13b61a68b1cd6363ee7d7af51614d0d6918cae88`。GitHub Actions job `129749242731` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42792512816)

## 2026-11-10 一次啟停五房硬體排演

模擬器 0.2.10 的 `--live-venue` 讀取既有的五房綁定，核對各房憑證、現行入場與本機資源後啟動五個獨立閘道。可用同一個標記停止仍在運作的房間。每房維持自己的連線、游標和報告，整批等各房結束後再發布 `venue-report.json`。 [五房操作](HARDWARE.md#一次啟動與停止五房排演)

- 本機即時批次 `run-b051e080ab3b4ac1b21c8278f0f672e6` 通過 69 項。合併場五房各確認 5 筆後，以全館標記取消第 3 房待確認批次，五房均正常停止。獨立場五房各先確認 5 筆。撤銷第 3 房入場後，該房原批次取消並回報失效，第 4 房仍在原連線確認第 6 筆。總結果保留該房失敗。也驗證錯房憑證、不同管理來源、過期入場及既有第 5 房資源鎖均會在連接前拒絕整批。
- 首兩次完整測試保留原結果。兩次均已通過新的五房回饋案例。第一次後續在執行中的房間新增入場被回絕，第二次測試使用錯誤的結束路徑。最終測試先結束及封存原第 3 房，再用新的準備中場次完成原逐房回歸。管理 API 規則沿用。
- 核心 1,030 項及離線 38 項通過。解壓 ZIP 的 8 個檔案通過清單核對，原範例重跑與離線報告的 SHA-256 相同。解壓後的模擬器與模擬設備配合管理包 0.31.96，在 `run-ee270f16816c465693c77b40a5bba761` 再通過 69 項，程序均已清理。實體硬體、廠商協議、設備停止、頭盔與跨機仍待現場驗收。 [套件與雜湊](HARDWARE_SIMULATOR.md)
- 功能來源 `98530ce553ec4d01095fd084c9145b3214abc1dc`。GitHub Actions job `129744463084` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42791103923)

## 2026-11-10 回放敵軍增援與撤除

控制台 0.31.96 在暫停回放後，依觀看房間或全場列出敵軍名單變更與在場、存活、增援和撤除數。點選畫格會核對敵軍識別碼與存活數，再保留視角跳轉。原設定查詢預設沿用原格式。 [回放操作](WORLD_RECORDING.md#查閱錄製中的設定切換)

- 最終同機 Windows 原生批次 `run-b8f4bc65a89b46db9e1db3f7d12b765c` 通過 384 項。獨立與合併場各 25 個玩家程序，六場 1,043 格完整回放、50 筆原戰績確認及 6 份 CSV。另有 54 格完整增援回放和一筆玩家戰績確認。第 10 格在場總數仍為 1，名單替換一個識別碼。第 42 格增援 83 名，第 48 格撤除 83 名，保留原識別碼。首輪 `run-c2a5865e01164e0bb39ced8e4768b120` 原斷言把準備階段替換算入開戰後增撤總數而失敗，保留原證據。重測分開核對整場名單和原命令區間。清理後 C／F 的 225 個檔案雜湊一致。
- 核心 1,030 項、HTTP 768 項、世界串流 92 項、Node 109 項、管理包 107 項通過。三個 Windows 套件與 Quest 0.49.1／64 APK 的離線報告為 `artifacts/venue-release-roster96.json`。本輪涵蓋同機 Windows，頭盔、跨機與廠商設備待實機驗收。 [管理套件](WINDOWS_CONTROL_PACKAGE.md)
- 解壓管理包的 Chromium 獨立重跑通過 821 項。涵蓋房間篩選、核對原畫格，以及替換敵軍名單時保留畫面。首輪在第 739 項後遇到混合五房 24 席開場的斷言失敗，保留當次證據。獨立重跑通過同一斷言，原期限、斷言與產品規則沿用。證據為 `artifacts/console-roster96-chromium` 及 `artifacts/console-roster96-chromium-serial`。
- 重新操作 Windows 啟動器 `run-189e057ea9c64701bf80b58d726f4070` 時已輸入隔離管理路徑，兩次「載入／更新」皆由 PickerHost 遮擋。依 computer-use 技能的非目標視窗規則停止，這次未進入場次清單。隔離程序已清理，C／F 九檔雜湊一致。
- 功能來源 `72e3e62e4bb23ad644b2edbd0abdbf527ecec26b`。GitHub Actions job `129735560378` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42788474250)

## 2026-11-10 五房封存核對共用發行報告

五房驗收清單可指定一份 `venueReleaseReport`。Windows 以退出報告中的玩家清單雜湊和原日誌核對最終戰績。Quest 用同一份報告核對原 APK、原部署、入場與戰績。所有席位都要有對應證據。Windows 啟動器 1.7 在退出後直接留下原日誌雜湊，可省略連線量測。 [封存操作](EXTERNAL_CLIENTS.md#核對全館共用的發行報告)

- 同機 Windows 三包 `run-f10c7d9d608e4aafbec0d2d0d5270384` 通過 449 項。獨立與合併模式各 25 個 0.49.1 玩家程序，全程未啟用連線量測。驗收逐席比對 50 份退出報告、原日誌及原戰績確認。兩種模式均拒絕互換同一發行版本的原退出報告。六場共 914 格完整回放。清理後 C／F 221 個檔案雜湊一致。
- 1.6 原封存批次另外唯讀複驗，兩種模式各 25 席可沿用原量測雜湊核對。換用 1.5 報告會拒絕，原封存結果保持相同。證據為 `artifacts/venue-release16-closed-readback.json`。兩種模式另以 15 個 Windows 和 10 個 Quest 測試席位驗證共用報告，涵蓋缺席、調換及不符 APK。頭盔、跨機及廠商設備仍待實機驗收。
- 最終解壓玩家包通過 39 項檢查。1.7 原發行報告為 `artifacts/venue-release-player17.json`，SHA-256 `7224f784ef7de0c8ebc35ab0f1b8646e83118840e10d18d549530988bb9a5b54`。離線核對使用管理包 0.31.95、Windows 0.49.1 伺服器和原 Quest 0.49.1／64 APK。 [套件與雜湊](WINDOWS_PLAYER_PACKAGE.md)
- 封存驗收 76 項及離線發行 6 項通過。Python 玩家包檢查 7 項通過，另 1 項因 Windows 符號連結建立權限跳過。
- 功能來源 `93c651bfda81bacd78095b1f1415489c9c92c31f`。GitHub Actions job `129729878801` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42786778521)

## 2026-11-10 Windows 玩家啟動前核對場館發行包

場館發行工具會在原報告附上 Windows 玩家清單的 SHA-256。啟動器 1.6 選用 `--release-report` 時，先核對原清單及其全部檔案，再核對解壓目錄的檔案集合。啟動和退出報告都保留原清單雜湊。 [Windows 核對操作](WINDOWS_PLAYER_PACKAGE.md#依場館發行報告核對玩家包)

- 最終解壓套件通過 39 項啟動器檢查。使用實際管理包 0.31.95、Windows 0.49.1 伺服器及原 Quest 0.49.1／64 APK，為 1.5 與 1.6 玩家包各產生一份離線發行報告。1.6 只接受本次指定報告，持同版遊戲的 1.5 報告時在建立玩家程序前拒絕。另覆蓋檔案缺失、清單外 DLL、舊報告與重複參數。發行工具 6 項、Quest 發行相關 3 項通過。Python 玩家包測試 7 項通過，另 1 項因 Windows 連結建立權限跳過。首候選 ZIP 保留，最終版納入清單外檔案檢查。 [套件與雜湊](WINDOWS_PLAYER_PACKAGE.md)
- 同機 Windows 三包 `run-b7fbfcd6a8c44132987bdccc71909dfb` 通過 449 項。獨立與合併模式各 25 個玩家程序。50 份終止報告保留相同的發行清單雜湊，逐一核對量測及日誌檔。六場共 2,509 格完整回放、50 筆原戰績確認及 1,500 次量測回覆。清理後 C／F 的 271 個檔案雜湊一致。實體頭盔、跨機與廠商設備仍待驗收。
- 最終報告為 `artifacts/venue-release-player16.json`，其 SHA-256 為 `ff39cc75118439c6bbf92c543a4bb6ee5ed3a70264348a4568234a21fc9f266e`。功能來源 `be77953e4db0d95fc18bcd469d4e4fd370968d68`。GitHub Actions job `129725205228` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42785395788)

## 2026-11-10 標記戰鬥事件前後的原保存片段

控制台 0.31.95 在暫停的回放中，對符合目前房間、玩家與事件篩選的畫格提供「標記事件前後各 5 秒」。服務從同一錄製查找起訖，沿用固定的保存尾端，最多 300 格。成功時保留目前事件格，操作者可用原片段控制播放或保存。 [回放操作](WORLD_RECORDING.md#重看指定片段)

- 同機 Windows 三包 `run-2dc4d0bc8c9b4dbaa5461a2d91d2f655` 通過 419 項。獨立與合併模式各 25 個 Windows 0.49.1 玩家程序，六場核對 1,695 格完整回放及 50 筆原戰績確認。第 3 房房控從原第 189 格中彈標記第 138 至 241 格，播放在第 241 格停止。起訖 13,743／23,631 毫秒與完整原錄製相同，保留第 3 房及玩家受傷篩選，管理寫入 0。清理後 C／F 220 個檔案雜湊一致。
- 核心 1,030 項、HTTP 768 項、世界串流 89 項、Node 109 項、解壓管理包 Chromium 818 項及管理包 107 項通過。涵蓋固定尾端、單格、房間權限及錯誤時間回應不覆蓋原標記。三個 Windows 套件與原 Quest 0.49.1／64 APK 的離線一致性核對通過，報告為 `artifacts/venue-release-context95.json`。本輪遊戲端使用同機 Windows 程序，頭盔、跨機及廠商設備仍待驗收。 [套件與雜湊](WINDOWS_CONTROL_PACKAGE.md)
- 功能來源 `3b5bf61bbb1bcbe3d5580cd74ca1d6af1d894893`。GitHub Actions job `129719013698` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42783524144)

## 2026-11-10 五房封存核對 Windows 玩家連線量測

Windows 玩家啟動器 1.5 的 `--link-metrics` 會啟用原遊戲內的量測。在玩家程序退出後，啟動器把原玩家日誌與量測檔的 SHA-256 寫入終止報告。五房封存驗收核對原檔、程序 ID 及伺服器確認最終戰績的同一條連線，再逐席彙整回覆、逾時、中斷及回覆的 p95。 [操作方式](EXTERNAL_CLIENTS.md#將-windows-連線量測納入五房封存)

- 同機 Windows 三包 `run-df03bec2a3484e90805c2478b2889ad0` 通過 447 項。獨立與合併模式各 25 個原玩家程序及 750 次有回覆的量測。兩種模式均拒絕交換兩份原量測檔。六場核對 2,480 格完整回放、50 份原戰績及伺服器確認。清理後 C／F 的 271 個檔案雜湊一致，並從快照重查 50 組原量測、啟動器報告和日誌。量測來自同機的無圖形玩家程序，跨機容量及實體頭盔仍待驗收。
- 最終解壓套件通過 29 項。首候選在重複量測選項時過早進入互動錯誤視窗，原測試逾時。最終版會完成診斷路徑解析再拒絕該選項。新舊玩家包 330 個清單項目有 328 個雜湊相同。離線發行核對以管理包 0.31.94、Windows 0.49.1 伺服器及玩家和原 Quest 0.49.1／64 APK 通過，報告為 `artifacts/venue-release-launcher1.5.json`。 [套件與雜湊](WINDOWS_PLAYER_PACKAGE.md)
- 封存工具回歸 73 項通過，包含混合 Windows 與 Quest、檔案調換、缺席、錯程序及異常採樣。玩家封裝 Python 回歸 7 項通過，另 1 項因 Windows 連結建立權限跳過。
- 功能來源 `e4b93488d4de7764985008db5d5ac045c885d301`。GitHub Actions job `129713599208` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42781877233)

## 2026-11-10 五房硬體排演狀態與重啟

模擬器 0.2.9 的 `--venue-status` 可唯讀查詢五房狀態。各閘道選用同一個本機狀態目錄。執行中超過三秒未更新會顯示 `stale` 並隱藏舊計數。重啟用新的 `runId`，正常結束時先完成報告再發布 `stopped`。 [五房操作](HARDWARE.md#查看五房排演狀態)

- 原編譯輸出 `run-67d4fd190a5041aa8006ddd4dfb8e42e` 和解壓後 `run-b7d79f4e97ac4c8aba24c8510009ddb6` 各通過 64 項。以管理包 0.31.94 和本機 TCP 模擬設備核對合併及獨立各 25 席。兩種模式均驗證讀取端保持開檔時仍可替換狀態。合併房 1 被強制停止後顯示逾期，其他四房保留原連線，各由 6 筆增為 7 筆確認。房 1 重啟後從 0 開始，只確認新的一筆，所有測試程序均已清理。
- 核心 1,030 項及離線 38 項通過。最終 ZIP 解壓核對 8 筆清單，離線報告與原建置逐位元相同。首輪解壓的即時測試 `run-0b3a55bee81444e8991bed62eadfa29a` 在既有重新附掛案例等候逾時，保留原失敗與清理結果。以相同解壓套件重跑通過。狀態只代表本機模擬，實體廠商設備與跨機仍待驗。 [套件與雜湊](HARDWARE_SIMULATOR.md)
- 使用者關閉視窗後重驗啟動器 1.7.0。隔離測試 `run-131c1313583d49af82c86a448ed7fdc0` 已輸入實例路徑，但 `PickerHost.exe` 仍遮擋「載入／更新」。停止前尚未載入場次或啟動遊戲伺服器。隔離程序已清理，C／F 9 檔雜湊相同。較早一次以歷史 1.1 包執行，來源核對即拒絕，未啟動介面。
- 功能來源 `8ce5e758940e3518626f6c846b57bf27d7e01277`。GitHub Actions job `129709611490` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42780656100)

## 2026-11-10 一次建立五房硬體排演綁定

硬體模擬器 0.2.8 的 `--bind-venue` 使用管理包 0.31.94 的同一份現行名冊快照，核對合併或獨立五房的原場次、席位、模擬埠及設備 ID。核對完才一起發布五份版本 2 設定和名冊序號。排演仍各用房控金鑰。 [五房操作](HARDWARE.md#一次建立五房設備綁定)

- 即時排演的原建置 `run-4714ca2c38064ec6ab33232386cebe51` 及解壓版 `run-5fc0d4d1cba347ef87350a199beb1b06` 各通過 54 項。解壓版合併和獨立模式各核對 25 個席位的 30 筆模擬確認，逐筆對上原場次、玩家、當次入場及設備 ID。重複資源、錯場次、空席和錯權限不發布設定。排演清理無殘留管理程序，唯讀核對見 `artifacts/venue-hardware-packaged-readback.json`。
- 離線模擬 38 項、核心 1,030 項、HTTP 768 項、管理包 107 項通過。解壓後的離線範例報告與原建置逐位元相同。這輪硬體回饋使用本機模擬設備，實體廠商協議、設備輸入輸出及停止方式仍待驗收。 [硬體模擬器](HARDWARE_SIMULATOR.md) · [Windows 管理包](WINDOWS_CONTROL_PACKAGE.md)
- 功能來源 `fcc10c1939ca770b0e109b4743d784adea4c2501`。GitHub Actions job `129704219879` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42779003443)

## 2026-11-10 同批獨立房間回放對齊

控制台 0.31.93 可從「全館收尾」開啟同一批次的獨立房回放，在暫停畫格與其他房間對齊。服務依各原錄製 UTC 擷取時間取最接近且不晚於對照時間的一格，上限 500 毫秒。連續切房沿用第一次選定的擷取時間。資料不符或時間不重疊時保留目前畫面。 [回放操作](WORLD_RECORDING.md#對齊同批獨立房間的回放)

- 同機 Windows 三包 `run-f6c15986bea04321b341a39f2adc2b5c` 通過 415 項，合併及獨立模式各 25 個 Windows 0.49.1 客戶端。原生瀏覽器從房間 1 第 197 格對齊房間 2 第 152 格，原時間差約 3.56 毫秒。按原錄製另核對下一格晚於對照時間。合併場沿用同一錄製，較舊獨立批次仍可選取。六場共 974 格完整回放與 50 次戰績確認。唯讀核對在 `artifacts/venue-time-native-readback.json`。
- 13 項 Chromium 專測驗證非重疊、取樣間隔、500 毫秒邊界、房間重用、連續切換與不同錄製來源的拒絕。完整解壓版 Chromium 通過 814 項，結果在 `artifacts/console-venue-time-full/checks.json`。管理包解壓通過 107 項、核心 1,030 項、HTTP 768 項、世界串流 86 項及 Node 109 項。原生整合使用同機 Windows，實機與跨機仍待驗收。 [Windows 管理包](WINDOWS_CONTROL_PACKAGE.md)
- 功能來源 `08a87a4a6439006dd4d3ea4bdc665ec28c02a227`。GitHub Actions job `129698283581` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42777171245)

## 2026-11-10 全館開場逐席狀態

控制台 0.31.92 的主控可在同一張表查閱五房各席的名冊、入場同步、姿態及追蹤狀態。嚴格追蹤政策會指出仍需追蹤的合成席位。舊版名冊、過期或缺少的來源不會顯示原姿態為就緒。 [開場操作](MISSION_CLOCK.md#全館開始)

- 同機 Windows 三包 `run-ef3f55f85ef54b578e19c229ddbdcf9a` 通過 399 項。合併與獨立模式各 25 個 Windows 0.49.1 客戶端，準備快照每房五席均為合成姿態。嚴格追蹤政策拒絕原批次，有效姿態政策可開場。六場完整回放共 1,034 格，50 份戰績和 50 次伺服器確認。額外唯讀核對見 `artifacts/begin-seats-native-readback.json`。
- 管理包解壓 107 項、1,030 項核心、768 項 HTTP、109 項 Node、50 項 MR 與 66 項全館追蹤專項 Chromium 通過。完整解壓版 Chromium 通過 804 項，結果在 `artifacts/console-begin-seats-full/checks.json`。原生為同機 Windows 合成姿態，瀏覽器 MR 使用測試來源。實體頭盔、場地及跨機仍待驗收。 [Windows 管理包](WINDOWS_CONTROL_PACKAGE.md)
- 功能來源 `06d288cfd9789c617563efedbce1c4a57246b8f2`。GitHub Actions job `129692005759` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42775216907)

## 2026-11-10 封存核對 Quest 入場的發行 APK

使用 `-ReleaseReport` 的正式部署報告在成功席位附上原場次、玩家、入場名額及連線埠。五房封存清單可用 `questDeployments` 將原報告、原 Quest logcat、伺服器戰績確認與 APK 雜湊逐席核對。可合併中斷前的成功席位和後續只重試未完成席位的報告。 [封存操作](EXTERNAL_CLIENTS.md#核對封存席位的-quest-發行-apk)

- 整合通過 15 項。以實際管理包 0.31.91 簽發兩種模式各 25 席的票券，原 0.49.1／64 APK 配合模擬 ADB 產生實際部署報告。合併模式在第 13 席遇到 APK 雜湊改變，前 12 席原報告與後 13 席重試報告可合併驗收。封存日誌、網路來源及戰績屬測試資料，實體頭盔、跨機及廠商設備仍待驗收。結果在 `artifacts/quest-sealed-release-binding/acceptance.json`。
- 封存驗收 70 項、Quest 部署 48 項通過。首次並行部署回歸有三項未產出預期 JSON 或 ADB 日誌，保留原失敗日誌，結束其他部署後重跑通過。功能來源 `985f4e321f934879c78113c17b9103cbc653acae`。GitHub Actions job `129689177737` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42774326768)

## 2026-11-10 逐席核對 Quest 已安裝的發行 APK

Quest 批次部署可用 `-ReleaseReport` 讀取四件套件的離線驗證報告，逐席核對裝置的版本代碼與原 APK SHA-256。整批先做唯讀預檢，部署逐席寫入前再核對。若 APK 已更換、無法讀取或回傳多個 APK，該席不寫入。 [部署操作](QUEST3.md#核對頭盔內已安裝的發行-apk)

- 0.31.91 管理包、0.49.1 Windows 伺服器與玩家包、原 Quest 0.49.1／64 APK 通過離線一致性核對，APK v2 簽章由 Android 工具驗證。報告在 `artifacts/quest-installed-apk-gate/venue-release.json`，SHA-256 `9a041f5d8cc5307a68ebc386f4c21cb31c5f63549659e8e1b93bc516a2442a77`。
- 整合通過 11 項，實際管理服務對合併及獨立模式各簽發 25 份原票券。模擬 ADB 對實際 APK 檔案計算雜湊，各模式 25 席預檢及部署成功，部署後的連線檔與原簽發內容一致。同版號不同雜湊案例在任何裝置寫入前回傳退出碼 1。結果在 `artifacts/quest-installed-apk-gate/acceptance.json`。本輪未執行頭盔端命令、實體入場或跨機連線。
- Quest 部署回歸 48 項、離線發行回歸 5 項。功能來源 `96ecd86037e709d18a144e20e28d15a9d3f81ea6`。GitHub Actions job `129686337008` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42773440017)

## 2026-11-10 從結案批次套用五房原任務版本

控制台 0.31.91 的「全館收尾」可帶回五個獨立房間的原保存版本。逐房重新檢查場地，保留編輯器草稿，待五房空閒並由主控確認才建立新場次。合併或缺房批次不提供此操作。 [操作說明](MISSION_VERSIONS.md#從全館收尾套用五房原版本)

- 五房專項 34 項及解壓管理包的完整 792 項 Chromium 檢查通過。混合 VR／MR 舊批次在任務庫改版及房間重用後，仍回傳原五個場次和版本 ID。測試核對舊版 MR 的 440 秒與油桶位置、未保存的 499 秒草稿、占用中的第 4 房、錯配回覆及主控確認後的五個新場次。完整回歸結果在 `artifacts/console-archived-plan-full/checks.json`。
- 1,030 項核心、768 項 HTTP、86 項世界串流、109 項 Node 及 107 項解壓管理包檢查通過。ZIP 與 SHA-256 記錄見 Windows 管理包說明。本輪驗證範圍為電腦端管理服務及瀏覽器。實體頭盔、跨機與廠商設備仍待驗收。 [Windows 管理包](WINDOWS_CONTROL_PACKAGE.md)
- 功能來源 `0eb16d667b805fda2b71d2032bed421365974721`。GitHub Actions job `129681776302` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42772013808)

## 2026-11-10 從觀戰統計直接跟隨玩家

控制台 0.31.90 的快照統計表新增玩家列「跟隨」按鈕。依原玩家識別重用統計列，保留鍵盤焦點，並限制動作於目前房間範圍和快照中仍存在的角色。 [觀戰操作](WORLD_RECORDING.md#操作)

- Windows 原生 `run-d52f4707c8754ac1be6c327907904401` 退出碼 0，354 項通過。五房獨立及合併各 25 個同機 Windows 0.49.1 客戶端，六場雙封存、1,136 格完整回放、50 份原戰績與伺服器確認。第 4 房房控從第 168 格保留焦點至第 171 格，再用 Enter 跟隨原玩家，沿用單一串流，觀戰全程唯讀。切到第 2 房解除舊跟隨，回看原第 79 至 176 格後接回第 203 格，受控串流中斷後接回第 208 格。清理後 C／F 219 檔雜湊相符。
- 109 項 Node、784 項 Chromium 及 107 項解壓管理包檢查通過。Chromium 核對玩家名稱以文字顯示、玩家列跟隨與移除玩家後停用。解壓 `VRCommand-ControlServer-0.31.90-win-x64.zip` 核對 543 筆清單與 523 個執行檔。功能來源 `4ff1830d0a7469a03b80529b28a1d9f2e03629f1`。GitHub Actions job `129677704929` 因帳務或支出上限未啟動。頭盔、跨機與廠商設備仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42770751576)

## 2026-11-10 房控匯出個人封存戰績

控制台 0.31.89 的「任務統計」新增「下載個人戰績 CSV」。選定原玩家後，檔案僅保留全場封存報表中的該玩家一列。房控限本房，已離場的原戰績列可匯出。個人下載使用戰鬥封存條件，個人回放仍須完成世界封存。 [操作說明](REPORTS.md#從戰績開啟個人回放)

- Windows `20261110-143657-9082b936` 退出碼 0，8 項通過。兩位同機原生玩家中，一位正常收到戰績，另一位受控下行丟包後保持 `ResultInterrupted`。房控從原雙封存場次取得中斷玩家的單列 CSV，原識別及七項統計與全場報表相符。完整回放 44 格，清理後 C／F 14 檔雜湊一致。
- 1,030 項核心、768 項 HTTP、86 項世界串流、109 項 Node、782 項 Chromium 及 107 項解壓管理包檢查通過。個人 CSV 在管理服務重啟和金鑰輪替後逐位元相同。跨房與不存在玩家的個人下載均回應 404。Chromium 核對未封存停用、世界回放待封存時可下載戰績、切換玩家取消舊下載及本房原列。
- Windows 管理包 `VRCommand-ControlServer-0.31.89-win-x64.zip` 解壓核對 543 筆清單與 523 個執行檔。功能來源 `2544a7131248a476937970130761160966e3ff9a`。GitHub Actions job `129674845463` 因帳務或支出上限未啟動。實體頭盔、跨機與廠商設備仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42769854574)

## 2026-11-10 Windows 玩家等待戰績及中斷提示

啟動器 1.4 從原遊戲日誌區分等待、已收到與等待時中斷。程序退出時先讀完已保存且未超過 2 MiB 的尾段，避免正常結束後漏讀最終戰績。狀態報告只保留固定狀態與程序欄位。 [玩家狀態](PLAYER_CONNECTION_STATUS.md)

- `20261110-143016-69d09f39` 退出碼 0，7 項通過。兩位玩家都以實際解壓套件啟動。受影響端確認已進入 `ResultPending`，同機下行阻斷約 29.94 秒，丟棄 3,485 包，伺服器釋放原連線，原生日誌有斷線而無最終戰績。檢查器在解除阻斷前停止自己的玩家程序，最後狀態為 `ResultInterrupted`。正常端經 `ResultPending` 到 `Final`，其戰績與雙封存一致。全場回放 37 格，清理後 C／F 14 檔相符。
- 原 `join-delay` 流程 `20261110-143118-4cd91909` 通過 6 項，兩位原玩家均收到戰績，32 格回放，C／F 14 檔相符。真正 Windows Framework 監看類別通過 26 項，解壓玩家包通過 22 項。原 0.49.1 套件與新版有 328 個內容檔雜湊相同。此輪沿用遊戲建置及管理包 0.31.88，實體頭盔與跨機待驗。
- 功能來源 `a7717b66bb8b6402bd22ad552ba9b53426074aa4`。GitHub Actions job `129672480438` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42769114586)

## 2026-11-10 從封存戰績跳到最近中彈

控制台 0.31.88 在選定的原玩家有中彈紀錄且雙封存完成時提供「跳到最近中彈」。從封存尾端向前搜尋，沿用原玩家與房間，核對畫格時間及符合事件筆數後才跳轉。沒有符合事件時保留封存尾端。 [房控操作](REPORTS.md#從戰績開啟個人回放)

- 109 項 Node、778 項 Chromium、7 項封裝邊界及 107 項解壓管理包檢查通過。Chromium 使用解壓後的 API，覆蓋沒有中彈、未完成封存、替換畫格事件及成功跳轉。先前兩次啟動停在測試路徑與瀏覽器依賴，完成回歸使用解壓套件及專用 Chromium 路徑。
- 原生 `run-c6022c516645427b8fd397228e989474` 退出碼 0，412 項通過。獨立與合併各 25 個同機 Windows 0.49.1 客戶端，六場雙封存、1,688 格完整回放及 50 份戰績確認。第 3 房房控從合併場尾端第 279 格跳到原第 216 格，找到 1 筆該玩家受傷事件。讀回畫格逐欄與完整原回放相同，管理寫入 0。程序清理後 C／F 核對 220 檔。實體頭盔、跨機與廠商硬體另驗。
- Windows 管理包 `VRCommand-ControlServer-0.31.88-win-x64.zip` 核對 543 筆清單、523 個執行檔與 174 個來源檔。功能來源 `8730d536b73e41d7b230a0fdaccfa60ba136b750`。GitHub Actions job `129669254139` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42768098802)

## 2026-11-10 同場驗證五房射擊、中彈與戰績

Windows 原生短場工具新增 `--incoming-fire`。原玩家射擊和換彈完成後，使用正常管理命令換入新敵軍並啟用自動攻擊。每位原玩家中彈後停止攻擊，完整回放核對同房射線、傷害及每格戰績。 [複驗方式](DESKTOP_EXERCISE.md#同場驗證玩家射擊與敵軍傷害)

- `20261110-141055-8ddf31dc` 退出碼 0，37 項通過。合併與五房獨立各 25 個 Windows 0.49.1 客戶端，管理包 0.31.87。六場共 2,801 格完整回放、24 個原管理畫格、100 發 100 中、50 次擊殺、55 次中彈與 1,100 點健康損失。第 5 個獨立房每人中彈兩次、剩餘 60 點健康，其餘場次每人一次、剩餘 80 點。
- 六場都完成世界與戰鬥封存，50 份個人戰績逐筆符合原入場與伺服器確認。全場 CSV 與逐格戰績一致，合併 ZIP 的五份分房 CSV 合計恰為原全場 25 列。清理後 C／F 核對 174 個檔案。資料摘要為 `combat-summary-readback.json`。測試使用同機 Windows 程式產生的輸入，跨機容量、頭盔和實體設備仍待驗收。
- 完整 Python 回歸執行 469 項，468 項通過、1 項跳過。26 項專項全數通過，包含錯房、攻擊窗外、射線與傷害不符、戰績與角色健康不符。來源 `1a5013d4a838bf69be2bb3d3c19d67acb98926fc`。GitHub Actions job `129665666039` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42766983631)

## 2026-11-10 硬體排演的即時閘道狀態

硬體模擬器 0.2.7 支援 `--live ... --status`，房控可在報告寫出前查看暫停、握手、批次等待、失聯、重新附掛和停止。輸出為逐行 JSON，只在狀態或計數變動時更新。每筆僅標記模擬結果，不包含金鑰、玩家識別或位址。 [排演操作](HARDWARE.md#查看排演中的閘道狀態)

- 原編譯輸出 `run-6334da33454b4e468bd7ffa29ca0e6ad` 與實際解壓套件 `run-a42e9bcb1c3448f49e6eeddf4972ac68` 各通過 48 項即時檢查。使用隔離 Windows 管理服務 0.31.87 與本機 TCP 模擬設備。斷線批次保持零確認，重新握手後新批次確認一筆，第三批等待時由房控停止並取消。第 12 筆狀態的 `stopped` 和報告一致，所有測試程序正常結束。
- 離線 `run-41bb6c3786554278a15401a77992f6ed` 通過 38 項。`VRCommand-HardwareSimulator-0.2.7.zip` 共 200,097 bytes，SHA-256 `91d2daafe8b17b24c5296a3da4f4ac41778fb021216cde57f00529277ab2ff23`，解壓核對 8 筆清單。包內離線範例執行結果與原測試報告位元組相同。實體設備協議、停止與訊號送達仍待廠商資料及實機驗收。
- 重試 Windows 啟動器 1.7.0 的連線來源驗收。`run-341640c7247548f8996dddcd4229ac20` 已在畫面核對隔離管理實例路徑。重新切到前景再試時，桌面工具仍回報「載入」位置由 `PickerHost.exe` 遮擋。此次停在載入前，測試退出碼 1。清理無錯誤，隔離 API 正常停止，未啟動遊戲伺服器或玩家。
- 硬體模擬器來源 `33c913e9714a18780d548e367adbf1a045a6d696`。GitHub Actions job `129663294110` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42766242722)

## 2026-11-10 姿態中斷快照返回即時觀戰

控制台 0.31.87 在尚未封存的姿態中斷快照提供「返回即時觀戰」，核對原錄製來源並保留房間及鏡頭。 [房卡操作](PLAYER_READINESS.md#從房卡查看姿態中斷快照)

- Windows 原生 `run-4fff855e1885496196057474c68b549f` 退出碼 0，387 項通過。獨立與合併各 25 個客戶端，由第 5 房房控查看第 2 席的原中斷畫格，恢復後回到即時畫面。獨立為第 248 格及第 258 格，合併為第 279 格及第 288 格，四格都與封存回放相符。瀏覽器無管理寫入，六場雙封存及 1,806 格完整回放，50 份戰績與伺服器確認一致。清理後 C／F 226 檔雜湊一致。
- 109 項 Node、28 項瀏覽器 VR 專項及 18 項瀏覽器即時觀戰回歸通過。Windows 管理包 `VRCommand-ControlServer-0.31.87-win-x64.zip` 實際解壓驗證 107 項，543 筆清單、523 個執行檔與 174 個來源檔核對。遊戲沿用 Windows 0.49.1，指定席使用 Unity Mock Runtime，實體頭盔及跨機仍待驗收。
- 來源 `c236c3f1458ad62d91dc10480d0fad2ade34733a`。GitHub Actions job `129659143187` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42764954583)

## 2026-11-10 VR／MR 房卡姿態中斷快照

控制台 0.31.86 新增「檢視姿態中斷快照」。原場次在執行中、原畫格新鮮且本房有存活席位的姿態中斷時，房卡才顯示入口。房控可查看本房，主控可查看五房。回放停在原場次、原來源及原世界序號，核對原管理序號與受影響席位。已淘汰席位不列入。 [房卡操作](PLAYER_READINESS.md#從房卡查看姿態中斷快照)

- 實際 Windows .NET 建置零警告、零錯誤，1,025 項核心、758 項 HTTP、86 項世界串流、20 項 Node 及 7 項封裝邊界檢查通過。HTTP 與串流使用新版發布檔。
- 新版發布檔的 Chromium 專項通過 VR 26 項及 MR 46 項。獨立與合併 VR 的房控均可開啟原畫格，MR 顯示失去追蹤的存活席位並排除已淘汰席位。恢復或過期會撤下入口，改動管理序號的串流副本遭拒。首輪 VR 的文字定位逾時、首輪 MR fixture 缺少 assert 匯入，各保留原日誌。最終測試使用 VR／MR 合成世界來源。
- Windows 管理包 `VRCommand-ControlServer-0.31.86-win-x64.zip` 以 .NET 10.0.14 自含執行環境發布，實際解壓驗證 107 項通過。ZIP、解壓內容及發布收據逐檔核對 543 筆清單、523 個執行檔及 174 個來源檔。 [管理包](WINDOWS_CONTROL_PACKAGE.md)
- 發布來源 `6bab0021234e472b8c0e2216b91f67855f41b1a1`，MR fixture 最終來源 `a84091d9cc0538c9229051f02b0606b7b8f6953b`。GitHub Actions jobs `129657087862` 與 `129657243532` 因帳務或支出上限未啟動。實體頭盔與跨機仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42764364273)

## 2026-11-10 五房重連姿態區間驗收

在場館清單加入 `reconnectWindow`，可用原始重連日誌及所有原始世界錄製驗證指定席位的第一格無效姿態與恢復格。前一格、完整中斷區間與恢復格皆須仍在執行中，其他 24 席需保持存活及有效姿態。獨立場用原 UTC 擷取時間對齊。 [操作方式](EXTERNAL_CLIENTS.md#核對重連席位的回放區間)

- 68 項驗收測試全數通過。反例包括其他席位也中斷、獨立房時段不重疊、暫停、未恢復、取樣缺口、擷取時鐘停滯、缺少舊連線釋放證據及錯誤範圍。
- 以 `run-5fe82fdb51ca4690a441bd1cd280fe03` 兩種拓撲的原封存重讀。第 5 房第 2 席獨立場第 297 至 602 格無效，603 格恢復，觀察時間 32,779 毫秒。合併場第 276 至 582 格無效，583 格恢復，觀察時間 32,932 毫秒。兩場各有 24 席持續有效，原整館 ZIP 與分房證據得到相同結果。各場兩個挪動邊界的反例皆拒絕，未開啟新選項時仍得到原摘要。獨立 54 檔、合併 34 檔前後雜湊一致，證據 `field-reconnect-window-final-readback.json`。本輪讀取既有同機 Windows／Unity Mock Runtime 錄製。
- 來源 `da569ce226804724271fcd858bc02e2591261823`。GitHub Actions job `129654801686` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42763600455)

## 2026-11-10 封存驗收核對原程序重連歷程

單場 `--verify-reconnect-history` 與場館清單 `verifyReconnectHistory` 可核對同一原程序的歷次連線。逐筆比對原伺服器核准、同一來源 IPv4、舊連線釋放順序與最後一條連線的原戰績確認。摘要僅列計數及房號席位。Windows 與 Quest 日誌沿用原輸入格式，舊模式仍只核對最終連線。 [驗收操作](EXTERNAL_CLIENTS.md#核對原程序的重連歷程)

- 65 項驗收工具測試、10 項伺服器套件測試通過。Windows 與 Quest 的重連歷程可與原姿態來源驗證並用。反例包含缺少釋放、釋放順序錯誤、來源位址不符、跨日誌重用識別、伺服器多餘來源、釋放後才確認戰績，以及缺少或重複玩家啟動紀錄。另重新讀取先前 `run-22d2c8aaf04544b6af4937d64d4573bb` 的兩種拓撲，未開啟歷程檢查的摘要與原檔完全相符。
- 原生 `run-5fe82fdb51ca4690a441bd1cd280fe03` 退出碼 0，495 項通過。Windows 0.49.1／管理包 0.31.85 的獨立及合併場各核對 26 條連線、25 份戰績及第 5 房第 2 席釋放一條舊連線。原整館 ZIP 與分場資料產生相同摘要，兩份各刪除一筆原釋放紀錄的測試副本都遭拒。六場雙封存與 3,795 格完整回放，六份 CSV 共 50 份戰績。清理後 C／F 237 檔相符。Unity Mock Runtime 使用同機轉送，原生回放核對姿態。實機及跨機仍待驗收。
- 來源 `f39981062990301ede13327272798326cf628f12`。GitHub Actions job `129651522456` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42762575879)

## 2026-11-10 五房 OpenXR 玩家原程序重連

新增 `--check-venue-openxr-reconnect`，對兩種五房拓撲的第 5 房第 2 席切斷本機 UDP 轉送。該席以 Unity Mock Runtime 射擊一發，等待客戶端與伺服器均回報斷線，由房控重發同次入場票券，放開並再按 Vive Menu 後用原程序恢復追蹤。原配票檔保留，僅更新玩家讀取的測試副本。 [複驗命令](QUEST_RECONNECT.md#五房-udp-中斷複驗)

- 沿用 Windows 0.49.1 和管理包 0.31.85。獨立場原連線 `5` 恢復為 `6`，合併場 `25` 恢復為 `26`。兩輪的原玩家均維持健康 100、彈匣 29、備彈 90。按住及放開 Menu 時均沒有新連線。
- 原生 `run-9ae755bf097648e8a8e8e234b47ca105` 退出碼 0，407 項通過。六場雙封存與 3,817 格完整回放，其中 1,894 格覆蓋重連驗證區間，逐格確認每輪其餘 24 席持續有效。50 份戰績與六份 CSV 相符，伺服器只對最後有效連線確認戰績。清理後無活躍場次、殘留程序或轉送，C／F 234 檔雜湊相符。
- UDP 工具 17 項、伺服器套件 10 項及四個互斥／缺少參數的拒絕檢查通過。測試 DLL SHA-256 為 `19db8f79819444793bf026a6a23d6d6bb5eae4d99fc12239b727a93d811692b1`。同機模擬控制器驗證，Quest 3／VIVE XR 實機、MR 場館及跨機仍待驗收。
- 來源 `500e2b8d01f404056231f235ba22f93555d63ffb`。GitHub Actions job `129648879577` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42761768146)

## 2026-11-10 Quest 批次部署失敗定位與席位重試

批次部署在失敗席位增加 `failedStep`，區分暫存、停止、啟用、正式檔驗證及啟動失敗。原 `status` 欄位與成功回報維持原格式。排除故障後可從部分裝置清單重試，重新核對現行簽章及效期，沿用已安裝的 APK。 [部署與重試操作](QUEST3.md#啟動前核對裝置檔案)

- 舊程式在七項故障情境缺少階段資訊，針對性斷言退出碼 1，原記錄 `quest-failed-step-before-assertions.log` 保留。新版 45 項部署測試通過，驗證暫存損壞、裝置資料夾、校正檔、停止、切換、正式檔核對和啟動失敗各回報不同階段，成功與未嘗試席位皆無該欄位。
- Windows 0.49.1、管理包 0.31.85 的混合 VR／MR 獨立五房 `run-0f480ba16e6843ac81daa18e4196717e` 通過 123 項。以真實簽發的五房 ZIP 及模擬 ADB 使第 2 房第 3 席正式檔雜湊不符，首席回報已送啟動指令，後三席未嘗試。只重試這四席，連線檔與完整部署對照逐位元一致，首席未收到裝置指令。五房封存 653 格準備中回放，清理後 C／F 52 檔相符。實體頭盔部署及入場待驗。
- 來源 `99e0235d31526385b2e2c893c0536eef8cab2a02`。GitHub Actions job `129645218964` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42760632702)

## 2026-11-10 Quest 部署先核對再停止遊戲

Quest 部署先核對原 MR 校正檔及暫存連線檔，再檢查票券效期、停止遊戲、啟用並核對最終連線檔。最後才送出啟動。已預先安裝 APK 的批次在暫存檔驗證失敗時，保留該席的原連線檔及運行中的遊戲。單席流程另含 APK 安裝。 [部署操作](QUEST3.md#啟動前核對裝置檔案)

- 以舊部署順序跑新斷言，四項針對性測試退出碼 1，記錄 `quest-staging-before-38f02a.log`。新版 44 項通過，涵蓋暫存內容損壞、停止指令失敗、啟用失敗及第 4 席暫存損壞。後者保留已成功的三席，該席未收到停止指令，後續 21 席保持未嘗試。
- 原生 MR Windows `run-3b5da687c6ab4ef8882a62789b53e8e3` 通過 144 項。合併及獨立各測完整 25 席及部分 5 席。模擬 ADB 逐席核對原簽章部署檔、校正檔與先驗檔再停止的命令順序。六場共封存 587 格準備中回放，清理後 C／F 57 檔相符。
- 原生 VR Windows `run-1dde01239f0443458ea5b40662a3321b` 通過 361 項。合併與獨立兩輪各有 25 個同機原生客戶端同時連線，各以模擬 ADB 核對全 25 席的檔案與停止順序。六場共 1,606 格回放，其中 281 格為任務進行中，六份 CSV 合計 50 筆原始戰績，逐席比對 50 筆伺服器確認。清理後 C／F 222 檔相符。
- 混合 VR／MR 獨立五房 `run-b3aaf9e32cff4ffaa44acc68dbdca9c3` 通過 121 項。管理服務核對 25 席簽章，從同一部署包驗證指定五席的模擬 Quest 部署及一份 Windows VIVE XR 的 VR 連線檔。五場共封存 628 格準備中回放，清理後 C／F 52 檔相符。
- 部署工具來源 `a589c4b6bff1196317ae91c19562bf7b29658a57`。GitHub Actions job `129641365469` 因帳務或支出上限未啟動。遊戲測試沿用 Windows 0.49.1 和管理包 0.31.85。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42759427295)

## 2026-11-10 追蹤控制器扳機短按

遊戲 0.49.1 會保留同一次 Unity 輸入更新中已按下又放開的右手扳機。短按進入原有射擊流程，受追蹤、焦點、放開門檻及射速限制；未就緒的輸入不會延後補射。 [Quest 3 操作](QUEST3.md)

- 官方 Touch 虛擬裝置在同一個 Dynamic 更新送入按下及放開。沿用舊射擊判斷時，Editor 專測 6 項中 5 項通過、短按案例失敗，退出碼 2。修正後完整 Editor 通過 272 項，無失敗或略過。快速短按在恢復第一幀仍被門檻擋下，先觀察放開後才接受下一次短按，隨後空白更新沒有補射。原測試與日誌各保存在 `quick-trigger-editor-before-fb29c4` 和 `quick-trigger-build-fb29c4`。
- Windows 與 ARM64 Quest 開發 APK 均由 Unity 6000.3.27f1 建置，來源指紋同為 `ea6e60ab5885a0faa53bcc0a81632bfbdbe1274b9a1c5a12109aeb7c913ab0ae`。依目前工作樹的 277 個來源檔重算相符，兩平台場景及玩家 prefab 網路識別一致。NGO 協定 31，Quest 版本代碼 64、SDK 32／35，v2 開發簽章通過實際 Android 工具核對。
- F 槽玩家 ZIP 為 84,763,369 bytes，SHA-256 `4805755c13f7c2279bf1e91258cfefbfe7a49e09d110a0a4e46ed2538857279b`。伺服器 ZIP 為 84,787,894 bytes，SHA-256 `0639c99d3aca2cc41bdf98400bd286af24ac25004302fcaba62035f4d4d2ef03`。Quest APK 為 60,965,774 bytes，SHA-256 `3d8f65100df4c1bbf1661c83af294ffa8ae81f14b16f56b1cf39653d684a6a7d`。兩個遊戲包各核對 330 檔，搭配管理包 0.31.85 通過四件離線交付核對，玩家啟動器通過 22 項檢查。舊 0.49.0 輸出、日誌及相關來源共 344 檔另存 C／F 並逐檔核對。
- 新版原生 `run-a668bdfb13a8442090955b864c8488cc` 通過 80 項，使用 Windows OpenXR 模擬及一個桌面同伴。追蹤恢復後持續按住未開火，放開再按下只扣一發。兩份戰績與伺服器確認、110 格完整回放、CSV 及雙封存相符，清理後 C／F 42 檔相符。單次 Dynamic 更新的短按由 Editor 裝置案例驗證。實體 Quest、VIVE XR、MR 場地、跨機 25 人及廠商硬體待驗。
- 同一 Windows 0.49.1 遊戲端的桌面短場 `20261110-125352-861d25e7` 通過 18 項。合併與獨立各 25 個同機模擬席，每席兩發及一次換彈。六場核對 1,864 格完整回放、50 份戰績、50 次伺服器確認、6 份 CSV 與雙封存。清理完成後 C／F 174 檔相符。
- 遊戲來源 `7ef5efb787180b406f511a72af5074f01f05e231`。GitHub Actions job `129639068103` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42758713965)

## 2026-11-10 全館繼續逐房確認

管理包 0.31.85 在「全館場次控制」與房卡顯示暫停確認、快照過期、MR 設定待同步及等候追蹤的原席位。合併場中已就緒的房間會顯示正在等候同場其他房間。送出繼續時，管理服務仍核對各場的原有條件。 [操作與 API](MISSION_CLOCK.md#逐房確認可以繼續的條件)

- 舊 0.31.84 解壓包未顯示原目標房間的原因，新增斷言退出碼 1，保留 `venue-resume-before-a4f620.log`。新版通過 91 項全館與 45 項 MR Chromium 專測。MR 追蹤測試使用 25 席的模擬來源，第 4 房第 2 席掉線時其餘四房各顯示等待同場。房控只能讀本房等候席位。變更環境後，舊暫停畫格被標為待同步，繼續回傳 409。新畫格確認恢復後，從控制台繼續同一場。
- Windows 遊戲 0.49.0 以解壓的三件套執行 `run-5722649d17a540448c0f3642bbf57c66`，367 項通過。獨立及合併各 25 個同機模擬席。獨立房的批次各套用四場，第 2 房的手動暫停計時維持 7 秒，另外四房繼續；合併的五房共用一筆暫停及一筆繼續，計時從 4 到 5 秒。
- 六場核對 1,321 格完整回放、50 份原戰績及伺服器確認、6 份 CSV 和世界／戰鬥雙封存。活動場次與測試程序清理後均為零，C／F 的 218 檔雜湊一致。另行故意中止的啟動器案例依原測試保留未封存紀錄。實體頭盔、跨機 25 人、MR 場地與廠商設備待驗。
- Windows 管理包 `artifacts/windows-control-console-0.31.85-venue-resume-win-x64.zip` 為 52,865,889 bytes，SHA-256 `80e34c31ebf85efcd18f377a4a8ce1cfa8b33e467adde478ea3549664a131904`。核對 174 份發布來源、523 個執行檔案及 543 筆清單。實際發布來源 `c463d1d070412627f66c8531a46883f3f8d8b6ca`。GitHub Actions job `129629003821` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42755559146)
- 通過 1,021 項領域檢查，解壓包通過 758 項 HTTP、86 項世界串流及 107 項管理包檢查，管理包的 C／F 27 檔雜湊一致。現行 Windows 0.49.0 伺服器及玩家、Quest APK 和新版管理包一併通過離線交付核對。
- 解壓包的完整控制台回歸通過 108 項 Node 與 768 項 Chromium。紀錄 `venue-resume-full-a4f620.log`。

## 2026-11-10 從任務回放定位設定切換

控制台 0.31.84 會列出原錄製首格及相鄰畫格之間的階段、環境、敵軍策略差異。暫停後可從第一格或目前格查閱，點選一筆可直接跳回當格，保留選取房間及鏡頭。合併場的設定適用全場，獨立房使用各自的原錄製。 [操作與端點](WORLD_RECORDING.md#查閱錄製中的設定切換)

- 原生 Windows 0.49.0 使用解壓管理包，合併 25 席與獨立每房 5 席，共 36 項通過。六場共核對 2,675 格完整回放，設定清單有 32 格，包含 12 格原生環境與敵軍策略切換。合併場第 186 格為暴風雨／夜晚／巡邏，第 202 格為濃霧／白天／推進。獨立第一房另核對第 50 格暫停及第 75 格恢復。
- 原生 `artifacts/desktop-exercise/20261110-121107-e8f866cc` 的 50 份戰績、50 次伺服器確認與 6 份 CSV 均與原封存相符。完成後無活動場次或剩餘測試程序，C／F 174 檔雜湊一致。此輪使用 Windows 模擬席位，跨機 25 人、頭盔、MR 場地及廠商設備待驗。
- Windows 管理包 `artifacts/windows-control-console-0.31.84-policy-replay-win-x64.zip` 為 52,864,065 bytes，SHA-256 `a072965d1c5a231dd2c951fe6176e22b763a933183fac7c1024388a899e54bca`。核對 174 份發布來源、523 個執行檔案及 543 筆清單。第一次封裝被舊版號檢查攔截，保留 `policy-frames-package-d62f6a.log`，改正後重新發布並解壓核對。
- 本機通過 1,021 項領域檢查，解壓包通過 758 項 HTTP、86 項世界串流及 107 項管理包檢查，後者 C／F 的 27 檔雜湊一致。管理包與現行 Windows 0.49.0 伺服器、玩家及 Quest 0.49.0 APK 亦通過四件離線交付核對。
- Chromium 專測通過 22 項。解壓包完整回歸通過 108 項 Node 及 759 項 Chromium，含原畫格跳轉、房間及鏡頭保留、相同設定重送與切頁清除。紀錄 `console-policy-frames-packaged-f9c20e.log`。
- 實際發布來源 `eec3ddb1763d3f685df437b5880b81ad8e765686`。GitHub Actions job `129624535443` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42754168346)

## 2026-11-10 Windows 0.49.0 雙模式長場複驗

使用 Windows 0.49.0 遊戲包與管理包 0.31.83。合併場 25 席，獨立場五房各 5 席。兩種模式各運行 900 秒，使用原生玩家程序及原移動、射擊和換彈路徑。 [長場設定與結果](DESKTOP_ENDURANCE.md#windows-0490-長場複驗)

- `artifacts/desktop-exercise/20261110-112148-71bac159` 退出碼 0，18 項通過。六場核對 51,211 格完整回放，其中 51,003 格為執行中。每席 90 發射擊、45 次換彈。獨立第 1 房暫停並繼續原場次，另四房同期間各前進 49 至 50 tick。
- 50 份原戰績、50 次伺服器確認及 6 份 CSV 逐席相符。六場世界與戰鬥均已封存。停寫後用 `verify-field-results.py` 的既有日誌核對器重算六份原戰鬥日誌的 4,500 筆事件，對上全部原戰績，結果保存在 `closed-combat-audit.json`。
- 活動場次與剩餘測試程序皆為零，C／F 的 174 檔執行資料逐檔 SHA-256 一致。本次為單機 Windows 模擬輸入，實體頭盔、MR 場地、跨機 25 人及廠商設備待驗。

## 2026-11-10 場館交付套件離線核對

新增 `scripts/verify-venue-release.py`，在發送前核對已解壓的管理、Windows 伺服器、Windows 玩家與 Quest 開發 APK。逐檔核對 Windows 清單及兩份遊戲執行檔案，並用原建置憑證比對 Unity 來源和場景、玩家的網路識別。Quest 另用本機 Android 工具核實套件資訊及 v2 簽章。 [操作](EXTERNAL_CLIENTS.md#發送前離線核對交付套件)

- 管理包 0.31.83／API 0.31.0 核對 540 檔，兩個 Windows 0.49.0 遊戲包各 330 檔，其中 323 個共同檔案的內容一致。Quest 0.49.0／63 為 60,963,642 bytes，SHA-256 `ad996caf883c962ed8b2b489c1dbd465b1456abd45f33c2f119da83b87fd0dd2`。實際 SDK 工具確認 ARM64、SDK 32／35、OpenXR 函式庫和 v2 簽章，通過紀錄 `artifacts/venue-release-0490-7631dc.log`。
- 舊 0.48.1 Windows 伺服器單獨通過其 328 檔核對，與現行 0.49.0 玩家配對時遭拒絕。換回配套的 0.48.1 玩家後，仍會因建置識別拒絕 0.49.0 Quest APK。兩次均退出碼 1，保留 `artifacts/venue-release-mixed-7631dc.log` 與 `artifacts/venue-release-mixed-quest-7631dc.log`。
- 本機通過 5 項新增測試，既有套件測試 25 項中 24 項通過、1 項略過。工具來源 `45257db525b84e7df6654746bb8cdee058c87cad`。GitHub Actions job `129610332660` 因帳務或支出上限未啟動。頭盔安裝、跨機連線與場地測試各自驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42749755565)

## 2026-11-10 從 VR 房卡確認席位恢復並繼續

管理包 0.31.83 在席位中斷暫停期間顯示各房等候席位。最新暫停畫格須觀察到目前序號，且目前名冊內的存活席位均有可參戰姿態。獨立房或合併場的操作員仍須明確確認繼續，伺服器收到命令後重查。 [恢復操作](PLAYER_READINESS.md#從-vr-房卡確認恢復並繼續)

- 舊 0.31.82 解壓包在遊戲端尚未觀察暫停時接受 `Resume`，對照 `vr-resume-before-b80b6c.log` 的 HTTP 200 與預期 409 不符，退出碼 1。新版通過 21 項解壓包專測，涵蓋缺席、確認期間再次中斷、合併場跨房等待、房控權限及原命令重試。另通過 1,021 項領域、758 項 HTTP、83 項世界串流及 17 項封裝工具檢查。
- 管理包 `artifacts/windows-control-console-0.31.83-vr-resume-win-x64.zip` 為 52,852,966 bytes，SHA-256 `d203ce5545ff84d2c553898e9494a327a03f2991b343d7c24e85bf3476ca1c4d`。核對 172 份發布來源、520 個執行檔案及 540 筆清單。管理包通過 107 項檢查，`run-a01bc71d8de94bd885db18f6192ea960` 的 C／F 副本 27 檔雜湊一致。
- 沿用 Windows 0.49.0 伺服器與玩家。原生 `run-2f5a9b4f2b3343d882d62ef19b5a9f00` 通過 406 項，獨立與合併各 25 個同機模擬席。第四房第三席斷線時，直接繼續均遭拒絕。原席重連並送回姿態後，分別由房控與主控從第四房房卡繼續原場次。
- 獨立第四房第 427 格與合併第 484 格仍為暫停，並已確認各自範圍內的所有原席位。後續第 428 與 485 格各自觀察到繼續，tick 恢復前進。獨立其餘四房在同一期間持續運行。六場共 2,924 格原回放、50 份原戰績與 50 筆伺服器確認，世界與戰鬥均封存。程序退出後 C／F 共 228 檔雜湊一致。
- 解壓包完整回歸通過 108 項 Node 與 754 項 Chromium。紀錄 `vr-resume-full-076d31.log`。
- 功能及管理包來源 `ac0428a4c5bdcf290077e8ec364ba4929a1d4e6c`。GitHub Actions job `129604730617` 因帳務或支出上限未啟動。實體頭盔、跨機 25 人、實體 MR 與廠商設備待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42748031640)

## 2026-11-10 從 VR 房卡暫停檢查席位

管理包 0.31.82 可在原 VR 席位明確失去連線或姿態時，從受影響房卡確認暫停。獨立場只暫停本房，合併場由主控暫停全場。管理服務於命令送達時重查最新快照及序號，房卡在原遊戲來源觀察到暫停後才顯示已套用。 [房卡操作](PLAYER_READINESS.md#從-vr-房卡暫停檢查席位)

- 舊 0.31.81 解壓包接受帶錯房號的暫停，對照 `vr-pause-before-1721cb.log` 的 HTTP 200 與期望 409 不符，退出碼 1。新版解壓包通過 13 項專測，涵蓋確認期間恢復、合併場房控權限、原命令重試及遊戲端套用。另通過 1,016 項領域、758 項 HTTP、83 項世界串流與 17 項封裝工具檢查。
- 管理包 `artifacts/windows-control-console-0.31.82-vr-pause-win-x64.zip` 為 52,850,515 bytes，SHA-256 `9f2f4bf1390a25307cd0cc2966639409db81f45113fabb28c6e7370c7d4404ed`。核對 172 份發布來源、520 個執行檔案及 540 筆清單。管理包通過 107 項檢查，`run-c58609b8f71e413097b93b71b0f8776c` 的 C／F 副本 27 檔雜湊一致。
- 沿用 Windows 0.49.0 伺服器與玩家。原生 `run-f74480923ac64afe9d09b6ef28b54f72` 通過 404 項，獨立與合併各 25 個同機模擬席。第四房第三席斷線後，獨立場由房控從房卡暫停，合併場由主控從第四房房卡暫停。兩場均使用原入場重連，由操作員繼續原場次並恢復 25 席。
- 房卡的套用來源逐筆對上獨立第四房第 146 格與合併第 204 格。原回放顯示兩場的暫停 tick 分別保持 284 與 281 格，獨立其餘四房在同一期間持續前進。六場共 2,764 格回放、50 份原戰績與 50 筆伺服器確認，雙封存。程序退出後 C／F 共 226 檔雜湊一致。
- 解壓包完整回歸通過 108 項 Node 與 746 項 Chromium，包含既有 MR 暫停與追蹤恢復。紀錄 `vr-pause-full-f5a291.log`。
- 功能與管理包來源 `29068b55780975c21289c56444a9dc9cf1e0d271`。GitHub Actions job `129599725186` 因帳務或支出上限未啟動。實體頭盔、跨機 25 人、實體 MR 與廠商設備待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42746483676)

## 2026-11-10 全館收尾分房戰績

Windows 管理包 0.31.81 可從全館收尾直接比較所選批次的分房戰績與本批合計。以原批次的最終報表為資料來源，等最後一場戰鬥封存後顯示。合計命中率依總命中及總耗彈重算，世界回放仍獨立顯示封存狀態。 [戰績操作](REPORTS.md#在全館收尾比較分房戰績)

- 舊 0.31.80 的解壓包在最後一場封存後仍沒有批次戰績，對照測試 `venue-scores-before-9e07ab.log` 退出碼 1。新版解壓包通過 10 項專測，涵蓋未封存、空房、加權命中率、房間重用及其他批次的替換回應。另通過 1,010 項領域、758 項 HTTP、83 項世界串流及 17 項封裝工具檢查。
- 管理包 `artifacts/windows-control-console-0.31.81-venue-scores-win-x64.zip` 為 52,847,763 bytes，SHA-256 `1dd1051f1462d54af63bccd5caa1574224e636f43cf1bdd96ef1da64e429a555`。核對 172 份發布來源、520 個執行檔案及 540 筆清單。管理包通過 107 項檢查，`run-8a2b10f6820f4dbc9be6d3555e0a22b7` 的 C／F 副本 27 檔雜湊一致。
- 沿用 Windows 0.49.0 伺服器及玩家。原生 `run-a7b3c5c588ba4a09b4535c063194bc03` 通過 485 項。獨立與合併各 25 個同機模擬席，表格逐欄核對原封存 CSV，每房五位、耗彈十發，各批合計 25 位、50 發。共同開火區間分別為 16,349 與 16,364 毫秒。六場共 1,446 格回放、50 份戰績與 50 筆伺服器確認，雙封存。程序退出後 C／F 共 223 檔雜湊一致。
- 原生敵軍攻擊補驗 `run-f56e868345b548488b65c38ac0ebd57d` 通過 432 項。兩種模式各 25 席都受到原生攻擊。獨立場表格合計 111 次中彈與 2,220 點耗損，合併場為 105 次及 2,100 點，均逐房對上原封存 CSV。六場 1,854 格回放、50 份戰績、50 筆伺服器確認及雙封存，程序退出後 C／F 共 220 檔雜湊一致。
- 功能及管理包來源 `ca49dd1680daa44eca67d74b91c27bfb7bb4abba`。首輪完整瀏覽器測試的 503 攔截器仍比對無查詢參數的網址，原逾時紀錄 `venue-scores-full-7bf6a1.log` 保留。`9f49010a31b75f36cf6451f7257c95c4e3fa726f` 只修測試攔截及清空戰績的斷言。原解壓包重跑通過 88 項全館操作專測，以及完整的 108 項 Node 與 736 項 Chromium。
- 兩個來源的 GitHub Actions 工作均因帳務或支出上限未啟動。實體頭盔、跨機 25 人、實體 MR 與廠商設備待現地驗收。 [功能 CI](https://github.com/peca12968/vr-command-center/actions/runs/42744394143) · [測試 CI](https://github.com/peca12968/vr-command-center/actions/runs/42745043209)

## 2026-11-10 核對五房 25 席在共同區間開火

五房封存驗收可選用 `requireConcurrentFire`，要求每個原席位在同一段持續連線區間各有一次已封存射擊。射擊識別、玩家與戰鬥序號逐筆比對原世界及戰鬥日誌。同 tick 的額外畫格須由 500 毫秒內的下一個前進 tick 確認。 [驗收操作](EXTERNAL_CLIENTS.md#核對-25-席在共同區間開火)

- 使用 `run-c3b7edd5b1e74f91b1ddeb7c2cfdd250` 的原封存檔，舊工具接受獨立 3,479 毫秒與合併 3,522 毫秒的 25 席連線區間。該批無玩家射擊，新工具啟用射擊條件後拒絕兩份原檔。63 項離線驗收與 10 項伺服器封裝工具檢查通過，涵蓋無射擊席、區間邊界、替換事件識別與 tick 停滯。
- 首次實際射擊測試 `run-0fc0437ca1ef4080b9bf138b53794c95` 的獨立場已有 50 筆射擊，但同 tick 畫格把區間切開，原次退出碼 1。修正後唯讀重查同一批，證實 25 席在 16,323 毫秒共同區間內開火。更早的命令參數、執行檔路徑及預先建立輸入目錄三次失敗各自保留。
- 沿用 Windows 0.49.0 伺服器與玩家、管理包 0.31.80。新原生 `run-55eef56acbdd4e6f8d62334935f8e5bb` 通過 457 項，獨立與合併各用 25 個同機模擬席，分別核對 16,204 與 16,369 毫秒的共同區間。每個原席位有兩次正常輸入路徑接受的射擊。六場共 1,287 格原回放、100 筆射擊事件、50 份戰績與 50 筆伺服器確認。世界及戰鬥均封存，程序退出後 C／F 共 221 檔雜湊一致。
- 最終驗證來源 `081c3f359e9fcd9e4ab74e11244262bf21bb4e94`。GitHub Actions job `129589612450` 因帳務或支出上限未啟動。實體頭盔、跨機 25 人、實體 MR 與廠商設備待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42743376933)

## 2026-11-10 從全館收尾回看有效姿態開場

Windows 管理包 0.31.80 在全館收尾提供「回看有效姿態開場」。主控可停在當初採信的準備中畫格，查看追蹤與合成席位數，再逐格檢查同一份錄製。五房獨立場顯示原房俯視，合併場顯示全場。歷史批次在房間重新使用後仍指向原場次。 [回放操作](SESSION_CLOSURE.md#回看有效姿態開場)

- 舊 0.31.79 的解壓包已有開場畫格指標，但瀏覽器測試因缺少回看按鈕而退出碼 1，紀錄 `participation-replay-before-894ad3.log`。新版解壓包通過 23 項專測，涵蓋拒絕 VR 斷線席與被替換為合成姿態的 MR 席。完整回歸通過 108 項 Node、729 項 Chromium 和 17 項 Python 封裝測試。
- `artifacts/windows-control-console-0.31.80-participation-replay-win-x64.zip` 為 52,842,586 bytes，SHA-256 `ed34a4a3e8cf1170e21e335f72a074058c3b5389d78fa32b833119c550132ce7`。核對 172 份發布來源、4 個獨立 RID 鎖檔、520 個執行檔案及 540 筆清單。管理包通過 107 項檢查，`run-6b63b96dadde418ba6ca28b43b0215a7` 的 C／F 執行資料 27 檔雜湊一致。
- 沿用 Windows 0.49.0 的伺服器及玩家包。`run-087307b691ab4225a18dee2e19596fa0` 通過 412 項，獨立與合併各用 25 個同機模擬席。六場均能在解壓控制台開啟原採信畫格及下一格，舊第三房第 130 格也能從歷史批次重開。逐筆核對 1,037 格回放、世界與戰鬥雙封存、50 份戰績及 50 筆伺服器確認。這次的原生測試涵蓋開場、回放與收尾，沒有戰鬥事件。測試程序退出後，C／F 的 220 檔雜湊一致。
- 功能與管理包來源 `5d3f57d6da0cebb8275dff68df97b244e69f1e30`。GitHub Actions job `129582482393` 因帳務或支出上限未啟動。實體頭盔、跨機 25 人、實體 MR 與廠商設備待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42741227270)

## 2026-11-10 五房有效姿態開場的封存核對

管理包 0.31.79 會在全館收尾及場館驗收 ZIP 帶出原開場採信畫格。離線工具可使用 `verifyParticipationBegin` 核對原準備中畫格、同批開場序號及後續第一個有效執行格，分列合成與追蹤席位。 [驗收操作](EXTERNAL_CLIENTS.md#核對五房有效姿態開場)

- 舊 0.31.78 的真實收尾回應沒有 `participationBegin`，反例 `participation-closure-api-before-48753a.log`。舊離線工具在兩種模式略過 `verifyParticipationBegin`，反例 `participation-closure-before-06bb4c.log`。新版解壓專測 17 項、離線驗收 57 項及封裝工具 17 項通過。離線測試涵蓋缺失指標、斷線、結束後才觀察到執行格、追蹤政策替換及 MR 合成姿態拒絕。另有 1,010 項領域、758 項 HTTP、83 項世界串流通過。
- 管理包 `artifacts/windows-control-console-0.31.79-participation-closure-win-x64.zip` 為 52,841,556 bytes，SHA-256 `36f9afd313e021339f17ac06327e90a3111d2c95d84447e4e9d27927de966114`，核對 172 份發布來源、520 個執行檔案及 540 筆清單。管理包 CLI 通過 107 項，`run-7ecfd2bfcf2f4fc5a203c99bd9aaf65d` 的 C／F 副本 27 檔雜湊一致。
- Windows 0.49.0 原生 `run-c3b7edd5b1e74f91b1ddeb7c2cfdd250` 通過 495 項。獨立與合併各有 25 個同機模擬席，直接使用原 ZIP 及拆分原檔的結果一致。六場的原準備畫格與第一個執行格均對上封存回放，兩批都拒絕改用全追蹤核對。六場共 1,702 格回放、212 筆戰鬥事件、50 份原戰績及伺服器確認，清理後 C／F 221 檔雜湊一致。
- 解壓包完整回歸通過 108 項 Node 與 723 項 Chromium，紀錄 `participation-closure-full-469f32.log`。
- 功能與管理包來源 `b476c0fb6b3423e9cf697d36f2d67fe971cd060b`。GitHub Actions job `129578425763` 因帳務或支出上限未啟動。實體頭盔、跨機 25 人、實體 MR 及廠商設備仍待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42740004333)

## 2026-11-10 五房 25 席有效姿態開場

管理包 0.31.78 提供可選的五房開場條件，要求每房五席已連線且姿態有效。VR 可使用合成或追蹤姿態，MR 仍須通過原 Quest 3 追蹤條件。原 Begin 事件保存採信的準備中畫格。 [開場操作](PLAYER_READINESS.md#五房各-5-席有效姿態開場)

- 舊 0.31.77 忽略新請求欄位，24 席送出該條件仍回 HTTP 200。原反例 `participation-before-f1333d.log`。新版解壓包 15 項專測通過，合併與混合獨立場均拒絕 24 席，亦在名冊有 25 席、其中一席斷線時只指出受影響房間。全數就緒後才開始，回條重試保留原政策及畫格。第一次新版測試在清理時重複送出 End，紀錄 `participation-dev-396eb5.log`。修正測試清單後的解壓證據為 `console-participation-focused-145bd8`。
- 1,010 項領域、758 項 HTTP 與 83 項世界串流檢查通過，紀錄 `participation-backend-396eb5.log`。領域測試核對 SQLite 重開後的原政策與準備畫格，以及重試時拒絕降低條件。另有 17 項管理及伺服器封裝工具檢查通過。
- 管理包 `artifacts/windows-control-console-0.31.78-full-participation-win-x64.zip` 為 52,840,795 bytes，SHA-256 `d4cdbbdb51b399596f846853c543f57a9756bb1a5dbe514b678bc005fa513292`，核對 172 份發布來源、520 個執行檔案及 540 筆清單。解壓包 CLI 通過 107 項，`run-bc4b169c2158444f8a80b99987c6978b` 的 C／F 副本 27 檔雜湊一致。
- Windows 0.49.0 原生 `run-8851d1dc846442129892f45d228bf661` 通過 385 項。五房獨立與合併各有 25 個同機模擬席。全追蹤選項各拒絕一次同批席位，切換有效姿態條件才接受。六張原準備中畫格逐欄對上封存回放，逐房均為五席有效合成姿態。六場雙封存共 923 格回放、50 份原戰績及伺服器確認，清理後 C／F 218 檔雜湊一致。
- 解壓包完整回歸通過 108 項 Node 與 721 項 Chromium，紀錄 `participation-full-145bd8.log`。
- 功能及管理包來源 `ca58d80a3ca3a3388dbe6ee153146e6e785038e8`。GitHub Actions job `129574536288` 因帳務或支出上限未啟動。實體頭盔、跨機 25 人、實體 MR 和廠商設備仍待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42738815959)

## 2026-11-10 即時觀戰斷線重連

控制台 0.31.77 在已確認錄製中斷時重連同一來源，保留房間、鏡頭及最後快照。六秒未收到快照或心跳會關閉舊連線，連續中斷最多重試三次。切換操作會取消等待中的重連。 [觀戰操作](WORLD_RECORDING.md#即時觀戰斷線後重新連接)

- 舊 0.31.76 在真正 SSE 回應已顯示快照後，受控關閉瀏覽器串流仍無法接收新格，原失敗 `live-watch-before-79b60f.log` 及 `console-live-watch-before-79b60f/failure.png` 保留。首次嘗試因預設 Chromium 快取路徑無執行檔而未進入操作，紀錄 `live-watch-before-27aa1e.log`。新版解壓包專測 18 項通過，涵蓋串流關閉、無心跳、異來源、三次暫時錯誤及離開觀戰時取消。截圖 `console-live-watch-focused-f33483/live-watch-stalled.png`。
- 管理包 `artifacts/windows-control-console-0.31.77-live-watch-win-x64.zip` 為 52,839,148 bytes，SHA-256 `43f7dd9454adf46b3bf0aec1441451417aa7568199c50929bcf84c5d445f08f7`，核對 172 份發布來源、520 個執行檔案及 540 筆清單。管理包 CLI 通過 107 項，`run-12e072bc5dcd419c953e01cbce09b8ba` 的 C／F 兩份 27 檔雜湊相同。另通過 17 項管理及伺服器封裝工具檢查。
- 解壓包完整回歸通過 108 項 Node 與 709 項 Chromium，紀錄 `live-watch-full-471b21.log`。Windows 0.49.0 的 `run-131156f4bba443909b6f8f451ac48bad` 通過 376 項，五房獨立與合併各有 25 個同機模擬席。合併場第 2 房俯視從第 205 格切斷瀏覽器 SSE，單次自動連接後到第 210 格，鏡頭與房間相同。兩格都與同一份原 Running 回放對上。六場雙封存共 1,002 格回放、50 份原戰績及伺服器確認，清理後 C／F 219 檔雜湊一致。
- 功能及管理包來源 `b80ba9894251a2454f9eabb74ead680f56284f8a`。GitHub Actions job `129569465176` 因帳務或支出上限未啟動。實體頭盔、跨機 25 人、實體 MR 及廠商硬體仍待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42737274613)

## 2026-11-10 模擬設備隨任務暫停斷線

硬體模擬器 0.2.6 在任務執行且有戰鬥來源時才握手。每條模擬連線對應一段執行期間，暫停時關閉閒置及待確認連線，繼續後以目前游標重新附掛。遲到的握手回覆會再核對來源及執行序號。 [排演操作](HARDWARE.md#暫停與繼續模擬連線)

- 解壓舊 0.2.5 的反例 `run-e7d40c3746754218ab8971f368b103fe` 以實際 TCP 連線觀察到閒置暫停後 2 秒仍開啟，退出碼 1，所有測試程序已清理。新版 `run-9f92037587324c809d030e768cd67310` 通過 40 項，涵蓋 Preparing 等候、閒置關線、暫停期間無新握手、繼續後新連線，以及跨越暫停與繼續的舊回覆遭拒。
- 模擬包 `artifacts/hardware-simulator-0.2.6-net10.zip` 為 196,646 bytes，SHA-256 `888bb4dd41e1874eac44bf890c2533e78a17b2aa6ed1af34fcd7647daf4cc93a`。核對 8 筆清單，解壓版 `run-96927533f94e444795333982679af5dd` 重跑 40 項即時檢查通過。離線 `run-b96320af39a34b39927a5453259cb5cf` 通過 38 項，C／F 17 檔雜湊一致，解壓範例結果也與原報告逐位元一致。另通過 17 項伺服器與管理包封裝工具檢查。
- Windows 0.49.0 搭配管理包 0.31.76 與解壓模擬器，原生 `run-83f9f15e2eaf442e9a5715794480015d` 通過 470 項。五房獨立及合併各有 25 個同機模擬席，十組房間閘道都以新連線確認繼續，獨立第 2 房等自己的繼續指令才重新握手。十份終止報告各有兩次附掛，模擬確認合計 213 筆相異事件。六場雙封存共 2,008 格原回放、50 份原戰績及伺服器確認。清理後無活躍場次，C／F 238 檔雜湊一致。
- 功能來源 `bd7163b26d7ae926512a170dcec1bb0b65de7179`。GitHub Actions job `129565309031` 因帳務或支出上限未啟動。實體頭盔、跨機 25 人、實體 MR、廠商協議與實際設備停止仍待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42736011255)

## 2026-11-10 以原始戰鬥日誌核對封存戰績

單場及五房離線驗收可讀取原 `.journal`，核對事件順序、累計確認與終端封存，重算每席耗彈、命中、擊殺、中彈、損耗、健康及命中率。 [操作方式](EXTERNAL_CLIENTS.md#從原始戰鬥日誌重算戰績)

- 舊工具在獨立及合併清單都略過未封存的戰鬥日誌，反例 `field-combat-journal-before-2cda0e.log`。新版拒絕遺失封存、損壞、錯來源、錯確認、無原射擊的命中及與已對齊戰績不同的傷害。首次回歸誤把原跨機測試的四項斷言留在新同機案例，保留 `field-combat-journal-tests-4bead6.log`。歸回原案例後 56 項場館驗收及 10 項伺服器封裝測試通過。
- 沿用 Windows 0.49.0 和管理包 0.31.76。原生 `run-8ce72be04b3b4d9895c3c2756b14cca0` 通過 481 項，獨立與合併各有 25 個同機 Windows 模擬席，六份戰鬥日誌重算共 212 筆受傷，對上 50 份原戰績、伺服器確認及 CSV。原生雙封存回放 1,675 格，C／F 副本 221 檔雜湊一致。兩種模式均拒絕去除最後封存紀錄的副本，單房 CLI 重驗五席、21 筆事件及 354 格原回放，結果與批次逐房摘要一致。
- 另從已結束的原生射擊場 `20261109-131846-924cdd5e` 唯讀重算六份日誌、250 筆事件。50 個原玩家結果合計耗彈 100、命中 100、擊殺 50。紀錄 `field-combat-journal-marksmanship-9f802c.log`，首輪以錯誤檔名前綴讀取的 `field-combat-journal-marksmanship-15da3d.log` 保留。
- 功能來源 `cebb75b4a25a14c8cbfc29801ca7a34617111f54`。GitHub Actions job `129562470275` 因帳務或支出上限未啟動。實體頭盔、跨機 25 人、實體 MR 與廠商硬體仍待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42735153886)

## 2026-11-10 窄缺口的細格通路預覽

控制台 0.31.76 對原 0.5 公尺格點未找到路徑的出生位補查 0.125 公尺格點。每段使用原 `ArenaWalkSurface.ClearSegment`，草稿及保存版本都標示採用細格的席位。 [場地操作](LAYOUT.md#出生位通路預覽)

- 舊版對偏移的 0.8 公尺沙包與油桶缺口回報無路徑，原反例 `layout-fine-before-8890638a.log`。新版五席都找到取樣通路，一席依序通過原遊戲權威端的姿態檢查並到達中線。縮至約 0.58 公尺仍找不到路徑。領域 1,006 項、HTTP 758 項、世界串流 83 項通過。證據 `layout-fine-backend.log`。
- Chromium 解壓版場地專測 39 項，從草稿實際輸入六件物件的小數座標，保存後開場平面圖逐點與原草稿相符。證據 `console-layout-fine-focused-86028cea`。管理包 `artifacts/windows-control-console-0.31.76-fine-opening-win-x64.zip` 為 52,837,112 bytes，SHA-256 `9296a87ff50338c8a35862dda7d45f36326751ff614def8cacf99a844a0490e5`，核對 172 個發布來源、520 個執行檔案與 540 筆清單。管理包 CLI 通過 107 項，執行紀錄 `control-package-checks/run-fc8d18ad774145068c47fbd30183cc22` 的 C/F 兩份 27 檔雜湊相同。管理包及伺服器包的 Python 測試共 17 項通過。
- 沿用 Windows 遊戲端與伺服器 0.49.0，五房獨立與五房合併共 387 項原生檢查通過。六場的保存通路共 30 條均經過偏移缺口，原生世界載入的六件掩體座標也逐房核對。兩種模式合計 50 筆原始結果，六場回放共 979 幀，核對雙封存與伺服器確認後清理。執行紀錄 `server-package-checks/run-855ff482f9a1436cafda03b3b18ba62c` 的 C/F 兩份 218 檔雜湊相同。
- 解壓版完整回歸通過 108 項 Node 與 708 項 Chromium 檢查。紀錄 `layout-fine-browser-full-86028cea.log`，截圖 `console-layout-fine-full-86028cea`。
- 功能與管理包來源 `e8174fc7fa8e9983ca0ac2f43cf3a6046290438d`。GitHub Actions job `129557139334` 因帳務或支出上限未啟動。實體頭盔、跨機 25 人、實體 MR 與廠商硬體仍待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42733534003)

## 2026-11-10 五房硬體模擬資源互斥

硬體模擬器 0.2.5 在原場次／房間互斥之外，鎖定同機同帳戶的模擬 TCP 埠及每個已綁設備 ID。發生衝突時在連線前拒絕，釋放本次已取得的鎖定。模擬接收程序可指定房號，後續回饋須符合原握手房號及連線。 [操作方式](HARDWARE.md#五房資源互斥)

- 舊 0.2.4 實測由兩個有效房控連線，向相同模擬設備 ID 分別送出兩筆原場次事件。原失敗 `hardware-ownership-before-2b0fcb1b.log` 與 `run-42731f9c011e4e43850dc8623289d30a/shared-device-witness.json` 保留。新版 `run-2de5cda4bef2447eb0686a7cc1547d90` 通過 35 項，包含埠或設備 ID 衝突拒絕、正確五房可隨後啟動、錯房握手及錯連線批次拒絕。
- 離線 `run-30766e7d2cbc4eb9abf0c2717e3166be` 通過 38 項。模擬包 `artifacts/hardware-simulator-0.2.5-net10.zip` 為 195,589 bytes，SHA-256 `943fe2ce8a5b71195e635f4f93e6a2b397c6af32261df2d46821e7b3a2484d2f`。核對 8 筆清單，解壓重跑離線範例的報告與原測試逐位元相符，解壓版 `run-4ff37062abb840c59583707b4a0058f4` 重跑 35 項即時檢查全數通過。另通過 1,003 項領域及 17 項封裝工具檢查。
- 沿用 Windows 0.49.0 及管理包 0.31.75。原生五房 `run-8612ed3d1e9049e9ade0a346847324b6` 通過 445 項，獨立及合併各有 25 個同機 Windows 模擬玩家。十組房間閘道各用正確的設備 ID、入場及席位，只建立一條連線並正常隨 End 停止。十份原回饋清單與模擬確認逐欄逐序相等，共 218 筆相異傷害事件。六場雙封存 2,025 格與 50 份原戰績確認，C／F 238 檔相符。
- OpenXR Mock Runtime `run-1bb6026a58fd4108bb227627a1f50d33` 通過 92 項。兩席均綁定，追蹤失效及恢復時維持扣扳機均無模擬回饋，放開後再扣僅產生一發和一筆模擬確認。115 格封存回放、兩份原戰績與伺服器確認、C／F 44 檔相符。測試沿用 `weapon-v1` 的原 DLL，SHA-256 `20a9140c20eb468742abc3596878994f94ecb51b3b9747dfd1b21b5121dbb3ce`。兩組原生驗證清理完成，輸出為 `hardware-ownership-native-{venue,openxr}-6181c2.log`。
- 功能來源 `48573b6ace7de15ae8154d0e645621c61258a9e3`。GitHub Actions job `129551928459` 因帳務或支出上限未啟動。實體頭盔、跨機 25 人、實體 MR、設備輸入與停止及廠商協議仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42731964194)

## 2026-11-10 匯出合併場的分房玩家回放

控制台 0.31.75 可選擇一房匯出已封存的共用片段。版本 2 分房檔保留原場次、原保存格及時間，僅交付指定房間的物件、角色和可確認歸屬的事件，省略全場計數。新版玩家頁可開啟全場及分房檔。 [回放操作](WORLD_RECORDING.md#讓玩家開啟回放)

- 舊 0.31.74 API 忽略 `roomId` 並回傳版本 1 原檔。反例 `player-room-replay-before-24ee52eb.log`。新版 83 項世界串流檢查通過，涵蓋房間範圍、主控權限、起訖及匯出前後全場原資料相等。另通過 1,003 項領域與 755 項 HTTP 檢查。
- 管理包 `artifacts/windows-control-console-0.31.75-player-room-replay-win-x64.zip` 為 52,835,923 bytes，SHA-256 `ce937ef5e582d9bf73b63ecac789719e8ab5ef387fb7cfe26947675fe5f7b1ea`。172 份來源、520 個執行檔案及 540 筆清單核對。解壓包通過 107 項管理包、83 項世界串流、108 項 Node、706 項 Chromium，以及 7 項管理和 10 項伺服器封裝工具檢查。管理包 `run-4c72ecd913d14432a83e2bbdf54ab5c4` 的 C／F 27 檔相符，瀏覽器證據 `console-player-room-replay-c9657163`。
- Windows 原生 `run-2cc69bdbd5234caa8cb8d9058ae550c8` 通過 416 項。獨立與合併各以 25 個同機 Windows 模擬玩家交戰，212 筆原傷害、1,755 格雙封存回放、50 份原戰績與伺服器確認。第三房檔逐格對上合併場原第 184–185 格，保留第三房 1 件物件和 10 筆事件，排除另四房 40 筆事件。玩家頁在 390px 視窗只提供第三房視角，無登入與 API 請求，播放到原第 185 格停止。證據 `linked-venue-replay-ui.json` 與 `linked-player-room-03.png`。C／F 220 檔相符，無活躍場次或殘留測試程序。
- 功能與管理包來源 `fa1dc28fa27878f070b25217be9fb82848ccf881`。GitHub Actions job `129547292043` 因帳務或支出上限未啟動。實體頭盔、跨機 25 人、實體 MR 與廠商硬體仍待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42730597459)

## 2026-11-10 配票下載前再次核對名冊

控制台 0.31.74 收到原簽發回應後再讀取有效場次及名冊，核對單席、整房與五房配票範圍。VR 及混合五房也比對原公告端點，MR 核對校正鎖定值。名冊或場次變更時停止下載。玩家入場時仍由遊戲伺服器核對原票券。 [配票操作](EXTERNAL_CLIENTS.md#下載前再次核對名冊)

- 舊 0.31.73 單席、整房、合併 VR 和獨立 MR 在另一位操作員更換原入場後各下載一份失效檔案。受控測試保留真正的 HTTP 200 簽發回應，於改名冊後送達瀏覽器，四例原結果保存在 `console-ticket-download-before-5e4ec95a`、`console-ticket-vr-venue-tickets-before-9afe2340` 與 `console-ticket-mr-venue-bundle-before-9afe2340`。新版四例皆收到一次簽發回應且零下載。
- 管理包 `artifacts/windows-control-console-0.31.74-ticket-download-win-x64.zip` 為 52,829,273 bytes，SHA-256 `5d42f2497a03df275644c5a06f71c4c60abe1048089c34da81750d315351fe80`。172 份來源、520 個執行檔案及 540 筆清單核對。解壓包專測 5 項單席與整房、24 項五房 VR、10 項五房 MR。完整回歸通過 105 項 Node、706 項 Chromium、755 項 HTTP、7 項管理包工具及 10 項伺服器封裝工具檢查。瀏覽器證據 `console-ticket-download-*-d5274842`。管理包 `run-1fce0b23524e4e09ac1c03ab2df19aa8` 通過 107 項，C／F 27 檔雜湊一致。
- Windows 0.49.0 純 MR `run-f90cadae838045959f4a208c21927bdf` 通過 140 項，獨立與合併各核對 25 個模擬 ADB 席位及指定 5 席，準備中共封存 620 格，C／F 57 檔相符。混合場館 `run-3cb9b4c0538a451793f29965b7ca768e` 通過 123 項，主控台 25 席 ZIP 與五個原端點相符，核對指定 5 個 Quest 模擬席與 Windows 票券交接。封存 562 格，C／F 52 檔相符。
- 純 VR `run-4227b1058e924b26878175858785fd44` 通過 381 項。獨立與合併都從主控台下載原 25 席 ZIP，各有 25 個同機 Windows 模擬玩家以原票券入場。六場共 1,572 格雙封存回放、50 份原戰績及伺服器確認，C／F 222 檔相符。三組測試皆清理完成且無活躍場次，原生輸出為 `ticket-download-native-{mr,mixed,vr}-cbd413.log`。
- 功能與管理包來源 `30c152f70c88add29a150afa3d47bbfb150bc3cf`。GitHub Actions job `129540649299` 因帳務或支出上限未啟動。實體頭盔、跨機 25 人、實體 MR 與廠商硬體仍待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42728628806)

## 2026-11-10 場次與戰績採用同一序號

控制台 0.31.73 從同一次管理服務讀取顯示場次狀態、玩家戰績和最近 20 筆事件，沿用原統計公式、報表及權限。 [操作方式](REPORTS.md#場次與戰績同步)

- 舊 0.31.72 控制台在真正的戰績 GET 延遲時顯示第 4 筆戰績，但場次標頭與最近事件已顯示第 7 筆。原失敗保存為 `console-statistics-snapshot-before-82b1ecc1`。新版解壓包專測 4 項通過，三者一起顯示第 4 筆，再一起更新至第 7 筆。證據 `console-statistics-snapshot-focused-3d264e82`。
- 通過 1,003 項領域、755 項 HTTP 與 81 項世界串流檢查，紀錄 `statistics-snapshot-backend-f8774729.log`。HTTP 核對最近 20 筆順序、房間權限、等待補送與 API 重開後的戰鬥封存。
- 管理包 `artifacts/windows-control-console-0.31.73-statistics-snapshot-win-x64.zip` 為 52,827,832 bytes，SHA-256 `d5e948cacbdda15a9093cd6806ea287a20313e98efaed5c7ea133dde5daac5d6`。172 份來源、520 個執行檔案、540 筆清單核對。首輪管理包驗證器仍寫死 0.31.72，保留失敗 `run-ba7e0ebd692844f9b40d0a251223a779`。更新檢查後，同一解壓包通過 107 項，證據 `run-74234f3d26d0469a98bcccecd5b22363`。兩場清理後 C／F 各 9、27 檔雜湊相符。
- 最終解壓包通過 105 項 Node、702 項 Chromium 及 7 項管理封裝工具測試。完整瀏覽器證據 `console-statistics-snapshot-full-7c763400`。
- Windows 原生 `run-03ee6aa86554499c84ea479bcd7989e8` 通過 395 項。獨立與合併各有 25 個同機 Windows 玩家入場，213 筆原傷害事件、六場共 1,842 格封存回放、50 份戰績與原伺服器確認。從實際主控台結束第 1 房，封存後五名玩家每欄戰績、場次序號及最新事件皆與原 API 核對，第 33 筆為戰鬥封存。證據 `closure-ui/archive-battle-overview.json`。C／F 220 檔雜湊一致，無活躍場次或殘留測試程序。
- 功能與管理包來源 `42ccb83a868df1b8485698709f13d49d7f796762`，原生與管理包驗證器來源 `075795fed57b02435eb4e4c197820ddc992c31a0`。兩個 GitHub Actions job `129534749311`、`129537248155` 因帳務或支出上限未啟動。跨機 25 人、Quest 3、VIVE XR、實體 MR 與廠商硬體仍待現地驗收。 [功能 Actions](https://github.com/peca12968/vr-command-center/actions/runs/42726906379) · [驗證 Actions](https://github.com/peca12968/vr-command-center/actions/runs/42727634462)

## 2026-11-10 Quest 3 批次部署核對裝置身分

完整與部分 Quest 裝置清單均讀取裝置回報的 Android 序號。多個 ADB 連線識別碼回報同一序號時，整批在預檢停止。每席寫入前再次核對，若連線指向不同裝置或序號已不可讀，保留前面各席結果並停止。報告只保留席位及狀態。 [部署操作](QUEST3.md#用裝置清單部署-25-席)

- 舊工具在兩個連線識別碼回報相同序號、另有缺失及無效序號時預檢成功，也在第四席裝置更換後回報整批成功。兩個反例保留在 `quest-device-identity-before-9df70d24.log`。新版拒絕兩例，第四席更換時前三席保留原核對與啟動結果，第四席未執行裝置寫入，後 21 席未嘗試。44 項 Quest 工具、9 項 Quest UDP 探測、10 項伺服器封裝測試通過，紀錄 `quest-device-identity-after-d0101599.log`。
- 沿用 Windows 0.49.0 與管理包 0.31.72。MR 原生 `run-8da053a1c2d4486fa0fc391ff6e4c418` 通過 140 項。獨立及合併各驗證原簽章 ZIP 的完整 25 席與指定 5 席，全部模擬 ADB 裝置都通過身分與檔案核對。共 639 格準備中錄製、C／F 57 檔雜湊一致。混合場館 `run-20b7339f251640c4bd85e0685fe59b00` 通過 123 項，驗證指定 5 個 Quest 模擬席涵蓋 VR 及 MR，核對 VIVE Windows 原票券交接。封存 627 格、C／F 52 檔雜湊一致。兩組皆清理完成。
- 純 VR 原生 `run-91c6649b163b4919842460abbdaa717b` 通過 381 項。獨立與合併各用原瀏覽器 ZIP 核對 25 個模擬 ADB 裝置，另由各 25 個同機 Windows 玩家用原票券入場。六場戰鬥與世界雙封存共 1,550 格回放、50 份原戰績及伺服器確認。C／F 222 檔雜湊一致，無活躍場次或殘留測試程序。三組工具輸出為 `quest-device-identity-{mr,mixed,vr}-e2104b.log`，純 VR 使用最後的票券期限修正。
- 功能來源 `77d7554a6283f800a49e8a6546256a65282ba8df`。後續 `e6c14d70b72d4175873961183fe02f72299180f1` 把每席票券期限檢查放在裝置讀取之後及寫入之前，三項部署專測通過，紀錄 `quest-device-identity-write-boundary-813424dc.log`。兩個 GitHub Actions job `129529267865`、`129531114181` 因帳務或支出上限未啟動。當輪 ADB 裝置清單為空，Quest 3、VIVE XR、跨機 25 人、實體 MR 與廠商硬體仍待現地驗收。 [功能 Actions](https://github.com/peca12968/vr-command-center/actions/runs/42725298528) · [最後修正 Actions](https://github.com/peca12968/vr-command-center/actions/runs/42725838671)

## 2026-11-10 執行中五房追蹤總覽

控制台 0.31.72 顯示五房各自最新確認的追蹤席位數，分列合成、待確認、已淘汰及未編列席位。原快照須有有效來源，並對應目前執行階段及原入場名冊。 [操作方式](PLAYER_READINESS.md#執行中五房追蹤總覽)

- 舊 0.31.71 合併場開場後沒有總覽，保留 `console-live-tracking-before-16d2b473769d45f89f693dc4d6f20d25.log`。新版解壓包專項 38 項通過，證據 `console-live-tracking-focused-7a1fb3b039b74dc99e2766d2425a1ed0`。合併與混合獨立均驗證 25／25、合成與中斷後 23／25、天氣更新、繼續指令未套用、快照過期、恢復及房控權限。25 個追蹤姿態為測試發布器資料。
- 管理包 `artifacts/windows-control-console-0.31.72-live-tracking-win-x64.zip` 為 52,827,383 bytes，SHA-256 `51d69438ecb3b8565d92a0cae98926ddb52d048fdef9a24b00e0af0b40afc737`。172 份來源、520 個執行檔案、540 筆清單核對。解壓管理包檢查 106 項通過，證據 `run-fe8d0e6cf71241bd9f8a30514aef631a`。另有 1,003 項領域、747 項 HTTP、81 項世界串流、10 項伺服器封裝工具檢查通過。
- 最終解壓包完整回歸通過 105 項 Node 與 701 項 Chromium 檢查。證據 `console-live-tracking-full-098e35f9bca143fd9e8afa6bd027c7a1`。
- Windows 原生 `run-e4d0f2bfd46d47e994cdf829878abb25` 通過 488 項。獨立及合併各用 24 個桌面玩家及第 5 房第 2 席的 Unity Mock Runtime 玩家。追蹤就緒、中斷、持續中斷及恢復分別核對獨立第 222、238、246、247 格及合併第 213、228、236、239 格，八格均與完整封存回放相符。六場雙封存共 1,722 格、50 份原戰績及伺服器確認。C／F 227 檔雜湊一致，無活躍場次與殘留測試程序。
- 功能來源 `197d3b3294319bde20c892206725e40bb82d8bb2`。GitHub Actions job `129525642823` 因帳務或支出上限未啟動。跨機 25 人、Quest 3、VIVE XR、實體 MR 與廠商硬體仍待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42724238436)

## 2026-11-10 核對 25 席同時追蹤的封存區間

場館驗收清單可同時設定 `requireTrackedRoster: true` 及 `minimumConcurrentMilliseconds`。逐格核對 25 席同時連線並具有 `Tracked` 姿態，再用原 Quest logcat 或 Windows OpenXR 日誌核對各席來源。桌面模擬或已識別的 Unity Mock Runtime 會回報原房號、席位與來源類別。 [操作方式](EXTERNAL_CLIENTS.md#核對-25-席同時連線的區間)

- 通過 54 項場館、14 項世界日誌及 10 項伺服器封裝測試。測試錄製測得合併 7,700 毫秒、獨立共同 7,100 毫秒，並覆蓋追蹤中斷、姿態和日誌不符、桌面、Mock 與門檻設定。舊工具忽略新條件的反例保存在 `venue-tracked-window-before-b2387d932ccb479dad7aa363dc75c10c.log`。首輪新測試為全 Quest 場景附上了空的 `windowsPlayers`，因清單格式被拒絕。保留 `venue-tracked-window-tests-c99ce72fe10e4850be33c82c05c1c960.log`，移除測試清單的空欄位後，全套 `venue-tracked-window-tests-1ca96d83177c471982cb519d4dcfc7bc.log` 通過。
- 重讀 60 秒桌面場 `run-22d2c8aaf04544b6af4937d64d4573bb` 與一席 Unity Mock Runtime 場 `run-9f36fa0fb07a4ea0b966dac7d0e7ebab`。兩組各含獨立及合併原錄製，普通核對與原保存摘要相符，開啟追蹤條件後四組均拒絕。Mock 兩組均定位第 5 房第 2 席。原輸入與摘要前後雜湊一致。證據 `venue-tracked-window-original-readback-a05bf8319c2147f895971ec6ad4ca106.json`。
- Windows 原生 `run-e71847372f7f48db9d0ebfd90a7bc81f` 通過 445 項。兩種模式各 25 個同機 Windows 模擬席，普通 12 秒門檻皆通過，獨立最長 18,322 毫秒、合併最長 18,401 毫秒，均從完整 API 回放另行重算起訖與時長。改用追蹤條件兩組皆拒絕。六場雙封存共 1,842 格回放與 50 份原戰績及伺服器確認。無活躍場次及殘留測試程序，C／F 221 檔雜湊一致。原生輸出 `venue-tracked-window-native-6553a2.log`。
- 功能來源 `470393b8d7f4e16529008cbbd95abdb3a7c688da`。GitHub Actions job `129521567327` 因帳務或支出上限未啟動。兩種模式的全追蹤正向測試使用測試錄製，現地仍須驗收 Quest 3、VIVE XR、跨機 25 人、實體 MR 及廠商硬體。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42723050881)

## 2026-11-10 Quest 3 啟動前核對部署檔案

Quest 單席及整批部署會核對裝置上暫存與啟用後的連線檔。MR 另外核對原校正檔及其鎖定雜湊。只有完成核對才送出啟動指令，整批回報逐席區分 `filesVerified` 及 `file-verification-failed`。 [部署操作](QUEST3.md#啟動前核對裝置檔案)

- 舊工具在暫存 MR 校正檔、暫存連線檔及啟用後的連線檔被更動時仍回傳成功，三個原反例保存於 `quest-file-verify-before-54becfc1629b435dbbdd4af091a79051.log`。新版拒絕三個反例。暫存核對失敗時保留原連線檔，已啟用檔案核對失敗時不送啟動。整批測試在第 4 席失敗，保留前三席已核對結果，其餘 21 席未寫入。
- 42 項 Quest 工具、9 項 Quest UDP 探測及 10 項伺服器封裝測試通過。Quest 紀錄 `quest-file-verify-tests-13d9a4d1e35b4dd3b3b0bf4f8782b2b3.log`。ADB 裝置清單為空，頭盔安裝、入場及實體 MR 校正仍待設備驗收。
- 沿用 Windows 0.49.0 和管理包 0.31.71。MR 原生 `run-f1724f82e71e46429b4316f663457834` 通過 140 項。獨立及合併各用原簽章部署 ZIP 驗證 25 席及指定 5 席，所有模擬裝置均回報 `filesVerified`，共 614 格準備中錄製。混合 `run-e00c626d7d114b1f9b6216cc7da19aae` 通過 123 項，指定 5 個 Quest 模擬裝置涵蓋 VR 與 MR，另核對 VIVE Windows 原票券交接，封存 627 格。兩組完成清理，C／F 分別 57、52 檔雜湊一致。
- 純 VR 原生 `run-600fb6833ae3467a805bdf8816c4bb5c` 通過 381 項。獨立與合併各用原瀏覽器 ZIP 對 25 個模擬 ADB 裝置完成檔案核對，另由各 25 個同機 Windows 模擬玩家以原票券入場。六場雙封存共 1,492 格回放及 50 份原戰績。C／F 兩側 222 檔雜湊一致，無活躍場次或殘留測試程序。三組原生工具輸出為 `quest-file-verify-{mr,mixed,vr}-e22fdc.log`。
- 功能來源 `e9acdeb3cb1114c4bebfd54256b8714f54b01685`。GitHub Actions job `129515747900` 因帳務或支出上限未啟動。跨機 25 人、Quest 3、VIVE XR、實體 MR 與廠商硬體仍待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42721332271)

## 2026-11-10 最近一批全館環境指令逐房確認

控制台 0.31.71 從原命令紀錄還原最近一筆全館天氣、日夜及閃電設定，逐房列出原命令序號與確認、覆寫、結束狀態。有效快照可開啟原場次指定房間的俯視回放。 [環境核對](ENVIRONMENT.md#核對最近一批環境指令)

- 舊 0.31.70 解壓包專項在核對 `latestEnvironment` 時失敗，保留 `console-environment-batch-before-b16d828bf0054be4a2727465fde4f874`。新版解壓包專項通過 88 項，證據 `console-environment-batch-focused-effd3cff25604c028fe90471bb687b6e`。包含僅一房有確認、快照過期、覆寫、替換畫格、房間重用、重新登入及房控權限。
- Windows 管理包 `artifacts/windows-control-console-0.31.71-environment-batch-win-x64.zip` 為 52,823,437 bytes，SHA-256 `daad337381f86a80dd65889a5405d2ec846d40d0fed9c45f9bb3c07d162fcb43`。核對 172 份來源、520 個執行檔案及 540 筆清單。解壓包通過 106 項管理檢查，證據 `run-be163a4d92bd40b887fb9bfcb8c0e731`。
- 通過 1,003 項領域、747 項 HTTP、81 項世界串流及 10 項伺服器封裝工具檢查。SQLite 重啟後保留原環境與覆寫狀態，重送舊指令不會蓋掉設定相同但序號較新的批次。
- 最終解壓包完整回歸通過 104 項 Node 與 689 項 Chromium 檢查，證據 `console-environment-batch-full-482ef6461c9b4ec780d71593cc089a66`。首輪完整回歸因執行命令預先建立應由測試建立的目錄，未開始 Chromium，原 `console-environment-batch-full-9af46d310d6a4b76a7fa18ef257fe9e4/test-output.log` 保留。重跑以獨立日誌檔收集輸出。
- Windows 原生 `run-916fc4ad016b429f94d2b45c71688450` 通過 483 項。兩模式各有 25 個同機 Windows 模擬席，核對暴風雨夜間和晴朗白天。第 4 房捷徑在獨立場開啟第 125 格、合併場開啟第 181 格，原命令序號 10 與 30，兩格均與完整封存回放相符。共享的驗收流程也通過兩模式的敵軍策略回歸。六場雙封存共 1,837 格回放、50 份原戰績及伺服器確認。C／F 兩側 221 檔雜湊一致，無活躍場次與殘留測試程序。
- 功能來源 `1ff782c71c97077c26ab2fcfd560a64ddc753829`。GitHub Actions job `129512077150` 因帳務或支出上限未啟動。跨機 25 人、Quest 3、VIVE XR、實體 MR 與廠商硬體仍待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42720249695)

## 2026-11-10 保存版本的 Windows 鍵盤通路驗收

沿用 Windows 0.49.0 與控制台 0.31.70。用第 3 房首席的兩個保存版本對照完整沙包牆與缺口。兩場均從 `(X=-3, Z=-3)` 出生。完整牆按 W 72 次抵達 `Z=-1.6500013`，再按 36 次仍在同一座標。缺口版按 W 120 次通過牆帶及中線，抵達 `Z=3.0000038`。 [複驗操作](LAYOUT.md#複驗保存版本的鍵盤通路)

- 首輪 `20261110-071150-08a4d122` 的 Unity 開發畫面在 Running 顯示 OpenXR 找不到 HMD 的訊息。收合視窗內的開發訊息同時觸發一發射擊，該輪中止並保留原失敗證據。清理後 C／F 14 檔一致。新版驗收工具在 Preparing 先等待原視窗確認，再開始任務。沿用原座標、彈藥及回放斷言。
- 最終 `20261110-071400-ca8d7942` 退出碼 0，三項原生檢查。完整牆 527 格，牆帶內 0 格。缺口版 347 格，牆帶內 20 格。五個即時取樣點逐格與封存回放相符。兩場均有戰鬥及世界封存、原戰績與 CSV、原連線的伺服器確認。各場用彈及受傷均為 0，健康 100。無活躍場次或殘留測試程序，C／F 16 檔雜湊一致。
- 驗收工具來源 `b50add792cc2010372b740ed872bd9086d052357`。GitHub Actions job `129508538859` 因帳務或支出上限未啟動。此輪為 Windows 桌面模擬；跨機 25 人、Quest 3、VIVE XR、實體 MR 與廠商硬體仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42719206446)

## 2026-11-10 場景物件成列複製與小數儲存

控制台 0.31.70 的任務編輯器可預覽一批複本、整批套用，再一次復原或重做。物件檢查欄接受小數座標與角度，保存版本、重新載入與匯出均使用輸入的精度。 [操作方式](LAYOUT.md#複製物件成列)

- 舊 0.31.69 解壓包在 `console-precision-before-f82f40bb1a524271b9e549e6c4707b5a` 重現 `X=3.125`、旋轉 `47.5°` 被瀏覽器的表單步長阻擋。首輪新版專項將「已載入」誤判為應顯示「已儲存」，保留 `console-placement-row-focused-6dc0ef67c34844e083445d662baac9a7`。更正測試比對預覽前後同一草稿狀態，解壓包專項 42 項通過。證據 `console-placement-row-focused-b955dfa7cd1d4a7482d31399fcefe9ef` 含預覽截圖及由正常下載流程匯出的範本。
- 交付包 `artifacts/windows-control-console-0.31.70-placement-row-win-x64.zip` 為 52,820,861 bytes，SHA-256 `612da6dea5dad1381f59c473ceddb5d8fb4a9c4dbf8c95e09f54de0f5d413cc2`。核對 172 份來源、520 個執行檔案及 540 筆清單。解壓包通過 106 項管理檢查，證據 `run-c15492ad85e04ebb8b29e0d009b84067`。
- 最終解壓包完整回歸通過 104 項 Node 與 683 項 Chromium 檢查，證據 `console-placement-row-full-5d604f67aa1a45c0853e7112d0eb58b2`。
- Windows 原生 `run-cd0ca33542484a0c82e8341f5ee99824` 通過 449 項。從瀏覽器下載的範本在隔離管理實例匯入一次。五房各自獨立時，每份世界錄製標頭有 3 個沙包，合併時有 15 個。以匯出的房間座標和房間原點逐一核對，世界座標及 `12.5°` 旋轉完全相同。兩模式各 25 個同機 Windows 模擬席，六場共 993 格完整回放、50 份原戰績與伺服器確認。C／F 兩側 221 檔雜湊一致，無活躍場次及殘留測試程序。
- 功能來源 `2324322bcfda018060fc574c12fba5756aa07f58`。GitHub Actions job `129503839657` 因帳務或支出上限未啟動。跨機 25 人、Quest 3、VIVE XR、實體 MR 與廠商硬體仍待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42717835674)

## 2026-11-10 最近一批全館敵軍策略逐房確認

控制台 0.31.69 從原命令紀錄還原最近一筆全館敵軍策略。主控逐房查看原命令序號、原目標數、待確認、已套用、覆寫或結束。只有對應原場次、策略與序號的有效遊戲快照可開啟俯視回放。 [操作方式](LAYOUT.md#核對最近一批敵軍策略)

- 交付包 `artifacts/windows-control-console-0.31.69-enemy-batch-win-x64.zip` 為 52,818,502 bytes，SHA-256 `c11e0ae8199fc2778032b0b970b33f3f732133c0b3e7f982b1f5617c7b4e1ce9`。核對 172 份來源、520 份執行檔及 540 筆清單，解壓包通過 106 項管理包檢查，證據 `run-e63092741b784c27b604328dea20e1a3`。
- 通過 1,000 項領域、747 項 HTTP 與 81 項世界串流檢查。原批次在 SQLite 重啟後可讀，單房覆寫及結束保留原序號，重試較早批次後仍顯示較新的命令。首輪領域測試因測試區域變數同名未通過編譯，改正後重新建置與執行成功。
- 首輪瀏覽器專項 80 項通過，證據 `console-enemy-batch-focused-fa1bbab42d0149ceaef3332d83636aed`。核對部分房已套用、其他房仍等待、單房覆寫、俯視快照及房間重用後重新登入的原批次。
- 最終解壓包通過 104 項 Node 與 671 項 Chromium 檢查，證據 `console-enemy-batch-full-e0acd504ff304067a84137d305bba042`。另核對快照過期取消確認、390 像素畫面及切換房控後隱藏原主控批次。
- 原生 `run-432cdd9f08ad4a1d88b621ee1e4f941b` 使用 Windows 0.49.0 與新解壓管理包，通過 471 項。兩模式各有 25 個同機模擬席。先啟用守備及自動攻擊，再套用推進及關閉攻擊，主控畫面逐房確認。第 4 房捷徑分別停在獨立第 229 格、合併第 269 格，與原命令序號 31、135 及封存回放相符。六場共 1,659 格完整回放及 50 份原戰績與伺服器確認。C／F 兩側 223 份檔案雜湊一致，無活躍場次及殘留測試程序。
- 功能來源 `79c68f9afdd0ef1a4a0ea7e75cee9a134e36f2d6`。GitHub Actions job `129498464116` 因帳務或支出上限未啟動。跨機 25 人、Quest 3、VIVE XR、實體 MR 與廠商硬體仍待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42716263740)

## 2026-11-10 核對 25 席同時連線的封存區間

離線場館工具可用 `minimumConcurrentMilliseconds` 要求指定時長。每場逐格核對全數原玩家、房號、連線狀態與遞增的遊戲 tick，超過 500 毫秒的保存間隔會切斷區間。獨立場以各原 UTC 擷取時間求共同區間，合併場使用同一份錄製。 [清單與操作](EXTERNAL_CLIENTS.md#核對-25-席同時連線的區間)

- 通過 51 項場館、14 項原世界日誌與 10 項伺服器封裝測試。驗證各房不同時間滿席、錯誤房號、掉線、暫停、管理中斷、tick 停滯、500／501 毫秒間隔及要求時長超過證據。重讀先前 `run-d58685574ad6442689ca3d48d89f39ba` 的原 ZIP 與日誌，未選用新條件時摘要與保存原件相符。新條件測得獨立 4,989 毫秒、合併 5,516 毫秒，各增加一毫秒的門檻即拒絕。
- 原生 `run-5e173dda46a1469ea871c769e77d328b` 通過 473 項。兩模式各 25 個同機 Windows 玩家通過 12 秒門檻，獨立最長 15,356 毫秒、合併最長 15,423 毫秒。另從管理 API 完整回放以相鄰格重算起訖與時長。六場雙封存共 2,512 格，核對 50 份原戰績及伺服器確認。C／F 兩側 221 份檔案雜湊一致，無活躍場次與殘留測試程序。
- 一分鐘原生 `run-22d2c8aaf04544b6af4937d64d4573bb` 通過 443 項。兩模式各 25 個同機 Windows 玩家，獨立最長 66,379 毫秒、合併最長 66,604 毫秒。原 ZIP 與逐場清單結果一致，從管理 API 完整回放另行重算共同起訖也相符。六場雙封存共 4,444 格，核對 50 份原戰績、UDP 來源及伺服器確認。無活躍場次或殘留測試程序，C／F 兩側 221 份檔案雜湊一致。
- 功能來源 `0a990a89488de472854fed8dbe7fab8e7331015c`。GitHub Actions job `129489974722` 因帳務或支出上限未啟動。快照證據與實際時鐘同步、跨機 25 人、Quest 3、VIVE XR、實體 MR 與廠商硬體分開驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42713806122)

## 2026-11-10 防止同房硬體模擬閘道重複啟動

硬體模擬器 0.2.4 在同機同帳戶以場次與房間鎖定即時閘道。第二個程序在模擬設備握手前退出。原程序退出後，新閘道從當前游標接上，可與同場其他房間同時排演。 [操作方式](HARDWARE.md#同房閘道的互斥與重新啟動)

- 原 0.2.3 解壓包的反例 `run-4441f66c0c0441b0bb380fec5d7ca109` 讓同一筆原射擊訊號進入兩條不同連線，保留兩個原批次與清理紀錄。新版拒絕第二個設定、埠與報告的組合。強制結束持有待確認批次的程序後，模擬設備記錄 TCP reset，新程序只確認重新接上後的新事件。首輪新版測試 `run-923105858ba7480e8414d046947303ea` 只辨識 EOF，未取得關閉紀錄。調整模擬設備辨識 EOF 與 reset 後，建置包與解壓包均通過 30 項，證據 `run-151d2173b84f4fc2a145cb4fda3e361c` 與 `run-36358494ef1c45eba1c594b54e019af7`。
- `artifacts/hardware-simulator-0.2.4-net10.zip` 為 190,714 bytes，SHA-256 `b2a322350e284c30b711c142f81071f246c3cb5fbdaccad3badb1c2c4a528a71`，核對 8 筆清單。38 項離線驗證通過，解壓包重跑範例與原輸出逐位元一致。另通過 996 項領域與 17 項管理／伺服器封裝測試。
- 原生 `run-d58685574ad6442689ca3d48d89f39ba` 使用解壓模擬器、Windows 遊戲 0.49.0 及管理包 0.31.68，通過 511 項。五房獨立與合併各 25 個同機玩家，十個版本 2 房間設定對上 50 個原入場。獨立 108 筆、合併 105 筆受傷訊號各有原模擬確認，事件識別無重複。六場雙封存，共 1,741 格回放及 50 份原戰績與伺服器確認。清理後無活躍場次與殘留程序，C／F 兩側 241 份檔案雜湊一致。
- 功能來源 `7031ba6c0f10db14bd3d15a21680f4243c6e0ddc`。GitHub Actions job `129485252575` 因帳務或支出上限未啟動。跨帳戶、跨電腦的閘道協調、廠商協議與實體設備停止仍待介接驗收。跨機 25 人、Quest 3、VIVE XR 與實體 MR 仍待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42712447709)

## 2026-11-10 從即時觀戰回看最近 10 秒

控制台 0.31.68 可依按下時已顯示的保存格固定回放尾端。正常錄製依保存時間向前找十秒，短錄製從原第一格開始。回看可逐格檢視，並保留目前房間與鏡頭返回同一錄製的即時快照。 [操作方式](WORLD_RECORDING.md#從即時觀戰回看最近-10-秒)

- 交付包 `artifacts/windows-control-console-0.31.68-instant-replay-win-x64.zip` 為 52,813,246 bytes，SHA-256 `a8b5c15480155eebf2ef38315bcc4de1a1451d9f9e92197be1ac16af73428943`。核對 172 份來源、520 份執行檔案與 540 筆封裝清單，解壓包通過 106 項管理包檢查，證據 `run-15af59f55e8643b8b1acbf88623746d9`。
- 解壓包完整回歸通過 104 項 Node 與 665 項 Chromium 檢查，證據 `console-instant-replay-full-966951b1d40c409eb6ba7f79a5eb6b51`。房控案例核對短錄製首格和終局戰績、替換來源拒絕、逐格後返回與離開頁籤清除。
- 原生 `run-55fb06c27fb54b539f3a910d348cd8cc` 通過 472 項。同機五房獨立和合併各 25 席。合併場第 2 房從第 94 格回看到第 190 格，含 97 個連續格，返回後收到第 217 格。房間與俯視相符，起點、尾端和返回格皆對上原封存來源。該片段橫跨準備與執行，隨後的 AI 測試逐席核對傷害及戰鬥帳本。六場共 1,670 格完整回放及 50 份原戰績、UDP 來源與伺服器確認。清理後無活躍場次與殘留程序，C／F 兩側 222 份檔案雜湊一致。
- 首輪 `run-6da63125598e4c7e9f31e18f3ea1224e` 的 Chromium 開發工具無法讀取已串流的回應本文，測試退出碼 1，清理後 C／F 216 份檔案相符。第二輪沿同一固定網址另讀保存格，並在原頁確認顯示尾端和返回。兩輪使用同一管理包。
- 功能來源 `c12fe6be2b42e0e7875256e2304047f768b9fccf`。GitHub Actions job `129480010677` 因帳務或支出上限未啟動。跨機 25 人、Quest 3、VIVE XR、實體 MR 與廠商硬體仍待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42710950195)

## 2026-11-10 直接核對整批場館 ZIP 與 Windows 日誌

離線驗收工具可直接讀取管理端下載的原場館 ZIP。依原批次及啟動器終止報告識別各場，按最終戰績的場次識別分配集中提交的 Windows 日誌。逐場清單、手動 Quest logcat 與 Quest 批次擷取報告可沿用。 [清單格式與操作](EXTERNAL_CLIENTS.md#一次核對五房-25-席)

- 本機通過 47 項場館驗收、14 項世界日誌及 41 項 Quest 部署測試。新增案例涵蓋兩種模式、混合場、Quest 擷取相容、證據來源衝突、異場日誌、UDP 位址不符、房間錯置、ZIP 成員與解壓大小限制。
- 原生 `run-c86a333ce56b46049d6288c2c20eba42` 使用 Windows 0.49.0 和管理包 0.31.67，通過 452 項。同機的獨立五房及合併場各有 25 席，兩種清單核對結果一致，保存 50 份原戰績、UDP 來源及伺服器確認。六場雙封存，共驗證 1,176 格完整回放。已確認舊批次 ZIP 在新場結束後逐位元一致。清理後無活躍場次或殘留測試程序，C／F 兩側 227 份檔案雜湊一致。
- 用新清單重讀 `run-7ee8f3f58478489a8f865fc30ce3fb28` 的兩份原場館 ZIP，結果與各自保存的摘要一致。兩份舊 ZIP、清單及摘要的雜湊保持一致。新場館 ZIP 的 SHA-256 分別為 `9225eac437493223618590f49f7a93cb7a96359f216114270bd8234d8cecdec0`（獨立）與 `c30958ff882103bc377fe0e134ee53e2ff360e680a407d7b382e830f06b6c81f`（合併）。
- 功能來源 `50d28a9e0527e630e58c2f152b3a9374af455363`。GitHub Actions job `129473404506` 因帳務或支出上限未啟動。跨機 25 人、Quest 3、VIVE XR、實體 MR 與廠商硬體仍待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42709046582)

## 2026-11-10 從全館收尾回看追蹤開場

控制台 0.31.67 可從全館收尾直接回看主控追蹤開場所採信的準備中畫格。捷徑先對錄製來源、房間、開始前管理序號、擷取偏移及每房五席有效追蹤，再停在原格。合併場以全場檢視，獨立場直接定位原房間俯視，並可逐格檢查相鄰已保存畫格。 [操作說明](SESSION_CLOSURE.md#回看追蹤開場)

- 交付包 `artifacts/windows-control-console-0.31.67-tracking-replay-win-x64.zip` 為 52,812,069 bytes，SHA-256 `cd24d62ccaa976b8551b0dee286e351e2013bf89597e1a4e207f7c389b0ffb41`。核對 172 份來源、520 份執行內容及 540 筆清單，解壓包 `run-2ec716c7edfe4ab6be50aae2612f3562` 通過 106 項。
- 26 項 Chromium 專項使用實際 API、SQLite、接受的合成追蹤與 3D 回放。涵蓋合併及混合獨立場各 25 席、未封存片段、封存後前後逐格、替換來源或姿態的拒絕、房間重用後開啟原批次及角色權限。證據 `console-tracking-replay-verified-5472097fd39f4209a1a2dd10e5a53d30`。
- 最終包完整回歸通過 104 項 Node 與 661 項 Chromium 檢查，證據 `console-tracking-replay-full-733253bbbaa944978e4283070a37ef1b`。Windows 原生 452 項見 0.31.66 里程碑。
- 初版回放將錄製的 `Simulation` 來源和個別玩家的姿態來源混在同一句，且先於畫面展開計算鏡頭比例。最終版分開呈現錄製設定與角色姿態，先展開畫面再定位鏡頭。獨立房專項截圖及距離檢查確認使用 15 公尺的俯視距離，原候選截圖顯示 56.25 公尺。
- 含舊鏡頭順序的候選在新增比例斷言退出碼 1，證據 `console-tracking-replay-suite-839dfef7fd08411d8c5802dd510150db`，保留原封裝及截圖。
- 功能來源 `032e5ab49512f62e319e8be9e7ad9f2ba2930ecf`。GitHub Actions job `129468095730` 因帳務或支出上限未啟動。跨機 25 人、Quest 3、VIVE XR、實體 MR 與廠商硬體仍待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42707506342)

## 2026-11-10 核對追蹤開場所採信的原始畫格

管理包 0.31.66 在接受五房追蹤開場時，保存每個場次所採信的原始準備中畫格。主控的原收尾批次及場館 ZIP 都提供同一個開始批次識別、開始序號、錄製來源、畫格序號與擷取偏移。離線驗收可選擇對照原 `.worldlog`，逐場核對開始前原名冊的追蹤，並確認後續有效執行畫格已觀察到該開始序號。 [操作說明](EXTERNAL_CLIENTS.md#核對五房追蹤開場錄製)

- `artifacts/windows-control-console-0.31.66-win-x64.zip` 為 52,809,723 bytes，SHA-256 `1e48371fea45c3391823f36397f387222db0698d17b802485e5876f32acddbb8`。核對 172 份來源、520 份執行內容與 540 筆 ZIP 清單。解壓包 `run-456cd53b5029449eb3b3fef58c62212e` 通過 106 項檢查。
- 996 項領域、44 項驗收工具及 14 項原日誌檢查通過。追蹤畫格指標在 SQLite 重開後一致，過往只有開場條件的紀錄仍可重試。離線專項覆蓋合併和混合場，拒絕缺少見證、錯誤來源、不同開始批次、錯誤開始前序號及合成姿態。
- 最終包 20 項瀏覽器專項使用合成追蹤快照、實際 API 與 SQLite。合併及三 VR／兩 MR 各走 25 席開始、結束、雙封存及下載，逐場把 ZIP 內的 `trackingBegin` 對回原已接受準備中畫格。樣本在 `console-tracking-begin-final-fc8859dc38c94a6192a57fcd680ae34c`。首輪測試在開啟錄製前公布端點收到 404，調整測試端點公布時機後通過。
- 最終包完整回歸通過 104 項 Node 與 654 項 Chromium 檢查，證據 `console-tracking-begin-suite-5c1b6065e59848038ec00140d9418903`。
- 原生 `run-7ee8f3f58478489a8f865fc30ce3fb28` 通過 452 項，使用 Windows 0.49.0。同機桌面模擬的獨立五房與合併場各 25 席，追蹤開場均拒絕，一般開場各完成 25 份原戰績、UDP 來源、伺服器確認及原封存 ZIP 核對。六場共 1,253 格完整回放，C／F 235 份檔案雜湊一致，無殘留測試程序。
- 功能來源 `e95ec1c21436eec1a831932f6207de20187d2313`。GitHub Actions job `129462366635` 因帳務或支出上限未啟動。跨機 25 人、Quest 3、VIVE XR、實體 MR 與廠商硬體仍待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42705869128)

## 2026-11-10 五房追蹤驗收開場

控制台 0.31.65 在全館場次控制新增選項，要求五房都是本次準備中的目標，每房五席皆有當前有效追蹤，才接受同一批 Begin。伺服器重查原場次、名冊序號及快照，並保存選項供原請求重試。一般開場條件可用於模擬操作。 [操作說明](PLAYER_READINESS.md#五房追蹤驗收開場)

- 最終包 `artifacts/windows-control-console-0.31.65-final-win-x64.zip` 為 52,807,645 bytes，SHA-256 `db218f9e26179134052cc1b722c9c3a9e89cab9bec398da1c20f87fab5ef95dd`。核對 172 份來源、540 筆清單及 520 份執行檔案，解壓包 `run-6453ee086ef1464180f7d3ed5da8aa8f` 通過 106 項。另通過 991 項領域檢查、HTTP 回歸與 81 項世界串流檢查。
- 最終包的 16 項 Chromium 專項檢查使用實際 API、SQLite 與合成追蹤快照。五房合併及三 VR、兩 MR 的獨立場，均驗證房 1 有合成姿態、房 5 少一席時整批拒絕，全部 25 席追蹤後成功。拒絕同一請求變更追蹤條件，並驗證重開 SQLite 後的原回條。證據 `console-full-tracking-final-c4d78876dc80414bac0bd12f30285a55`。
- 最終包完整 Node 與 Chromium 回歸退出碼 0，含 650 項瀏覽器檢查，證據 `console-full-tracking-suite-5fc04c2df86841e19a288422431806b1`。原生 `run-db26d8ec29d94ad199537a92b26ca1be` 通過 386 項。五房獨立及合併各有 25 個同機桌面玩家，追蹤開場均回傳五房拒絕，原預覽序號未前進。原名冊以一般開場運行及結算，六場共 1,284 格完整回放、50 份原戰績及伺服器確認，清理後 C／F 222 份檔案雜湊相符。
- 首輪封裝命令誤傳 `publication` 子目錄，在產生 ZIP 前退出。首個成功封裝的候選畫面在按鈕停用時仍顯示「目標場次已就緒」，已修正總覽條件並加入明確斷言。原候選的 `console-full-tracking-regression-e95ac9d82c934eadb0a519dbf6687b80` 在新增的總覽斷言退出碼 1。候選的原生 `run-03440422a73d4437a18985545ae59567` 另通過 386 項，保留其 1,222 格及 222 份 C／F 檔案核對。最終包重新封裝並獨立驗證。
- 功能來源 `1aadc124aaa467c3899ac372278e1b59bebedc18`。GitHub Actions job `129455791992` 因帳務或支出上限未啟動。跨機 25 人、實體頭盔、MR 場地與廠商硬體仍待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42703982682)

## 2026-11-10 依電腦分發 Windows VR 連線檔

五房場館可由主控依電腦對照表匯出 1 到 25 個 Windows VR 席位。工具先用原 VR 或混合場館 ZIP 向管理服務核對全部 25 份票券、現行入場與端點，只將所選 VIVE XR 的原四欄 JSON 寫入新目錄。混合場的 MR 房間仍沿用 Quest 部署。 [操作說明](EXTERNAL_CLIENTS.md#依電腦分發-windows-vr-連線檔)

- PowerShell 部署工具通過 41 項 Python 測試。新增案例以測試管理回應核對 25 份原始位元組、同目錄拒絕覆蓋、重複電腦、無效名稱、Quest 分類、變更後名冊和混合場的 MR 拒絕。
- `run-849fa487c74844f4bc80ff3ffcff0351` 通過 404 項。實際管理包下載的原 ZIP 在獨立五房及合併場各匯出 10 份 Windows 連線檔。每個檔案與原 ZIP 內容逐位元相符，實際由玩家啟動器讀取。兩種模式各有 25 個同機桌面模擬玩家，六場共核對 1,467 格回放、50 份原戰績及伺服器確認。兩種模式另各走五席模擬 ADB。
- `run-a8c0ea8f50eb4e1492d69283592594a2` 通過 120 項。三個 VR 房及兩個 MR 房使用實際伺服器與管理包，由原混合 ZIP 匯出一份 VIVE XR 連線檔，拒絕 MR 房及 Quest 3 席位，無玩家程序入場。五場準備階段共封存 616 格。兩組測試無活躍場次與殘留程序，C／F 分別核對 224 與 52 份檔案雜湊。
- `run-f7e72ea4308a44ce8f5ac6b48ce69296` 通過 422 項。獨立五房及合併場各有 24 個桌面玩家及一個 Unity OpenXR 模擬玩家。第 5 房第 2 席直接用匯出的原 JSON 啟動，兩場均核對追蹤就緒、中斷、持續中斷及原連線恢復，也收到原戰績。六場共封存 1,641 格與 50 份原戰績，C／F 的 226 份檔案雜湊一致，無活躍場次及殘留程序。
- 功能來源 `dcd1126478a71f36b5114080e547deee5bba1def`。沿用 Windows 遊戲 0.49.0 與管理包 0.31.64。GitHub Actions 的 `checks` 因帳務或支出上限未啟動。跨機 25 人、Quest 3、VIVE XR、實體 MR 與廠商硬體仍待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42701997328)

## 2026-11-10 Windows 遊戲伺服器選檔至結算驗收

- Windows 伺服器包 0.49.0、啟動器 1.7 與管理包 0.31.64 完成新一輪 WinForms 驗收。用「選擇檔案」開啟隔離實例的 `control-instance.json`，確認清單載入兩個獨立房，選擇第 1 房與原任務版本，指定本機 UDP 埠並勾選來源紀錄。原生程序公告的位址及埠與畫面選擇一致。 [伺服器包](WINDOWS_SERVER_PACKAGE.md#選檔啟動及結算驗收)
- `artifacts/server-gui/run-5968c463c17d4ab29be34a2dd91b7cc7` 的工具與 WinForms 皆退出碼 0。一位同機 Windows 模擬玩家以原票券入場，測試程式經管理 API 開始及結束任務。核對同一條連線的 UDP 來源、原戰績與一筆伺服器確認回條。戰鬥與世界錄製均封存，原世界日誌完整至第 79 格。啟動器顯示已封存並停止，來源勾選清除，隨後從視窗關閉。
- 管理實例設定、角色金鑰與票券簽章金鑰的原檔雜湊驗證通過，所有測試程序均已退出。清理後 C／F 兩側共 16 份對應檔案雜湊一致，伺服器解壓包與原 ZIP 的 330 筆清單項目相符。本輪是單房、單名同機模擬玩家，使用既有程式包。跨機 25 人、Quest 3、VIVE XR、實體 MR 與廠商硬體仍待現地驗收。

## 2026-11-10 從 MR 追蹤警示暫停

控制台 0.31.64 在房卡提供重新對位暫停。獨立房由房控或主控操作，合併場由主控確認五房一起暫停。服務受理前重新核對原房號、場次序號及最新有效的追蹤中斷。管理端接受後先顯示待確認，同一來源回傳套用原暫停序號的快照才顯示已套用。 [操作說明](PLAYER_READINESS.md#從追蹤警示暫停)

- `artifacts/windows-control-console-0.31.64-win-x64.zip` 共 52,804,843 bytes，SHA-256 `a16b0633630986f7f77fd6ce01e22889e7802879a7996a9843fd0d484ecf39bd`。核對 172 份來源、520 份執行環境檔案與 540 筆封裝清單。通過 106 項解壓啟動器、986 項領域、747 項 HTTP、81 項世界串流及 104 項 Node 檢查。
- 最終解壓包的 39 項 MR 專項檢查使用真實 API、SQLite 與合成的追蹤資料。合併場 25 席核對只有主控可暫停、取消確認、確認期間恢復追蹤、遺失回應的原命令重試，以及五房共用的暫停套用快照。獨立場核對房控只暫停本房、其他房序號保持不變。證據 `console-mr-tracking-pause-package-focus-fb40b30778a3457799d6b554f8eb985a`。首輪缺少 Room4 測試憑證，HTTP 回應 401，保留原結果 `console-mr-tracking-pause-focus-1daf3a424e5f4d588021fa08d7d61ecb`。
- 最終解壓包通過 637 項 Chromium 檢查，證據 `console-mr-tracking-pause-package-6ff0f106ba6e486ba7c19c2c906edcf4`。同包搭配 Windows 0.49.0 原生遊戲的 `run-ab31b73881e24ee0bb74d95db86d0fe4` 通過 408 項。獨立五房及合併場各有 25 個同機 VR 模擬玩家程序，均確認原生全館暫停、繼續與活動時鐘。六場共核對 1,229 格完整回放、50 份原戰績及六份場次 CSV，雙封存後無活躍場次、遺留程序或清理錯誤。
- 發布來源 `e0628a26e28af1ae45f3ec15a7e5126347ea73d8`。GitHub Actions job `129440890892` 因帳務或支出上限未啟動。Quest 3、VIVE XR、實體 MR、廠商硬體與跨機 25 人仍待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42699717398)

## 2026-11-10 Windows 遊戲錄製補送工具

Windows 錄製補送工具 0.1.0 讀取原伺服器的設定，先以唯讀獨占方式開啟兩份原日誌，再用工作副本補送至原管理場次。須由操作員先結束場次。結果分列戰鬥及世界的接受序號與封存狀態，未保存完整結尾的場次仍可查看已保存片段。 [操作方式](WINDOWS_SERVER_PACKAGE.md#遊戲程序退出後補送錄製)

- `artifacts/windows-recording-recovery-0.1.0-win-x64.zip` 共 32,100,731 bytes，SHA-256 `083c266c1bbe437b59492c6494703115791fda1cfd8c1a162d2cfd2959c34f32`。核對 82 份發布來源及四份清單檔。工具自含 Windows x64 .NET 10.0.14，原生測試移除 SDK 的 PATH 後仍可執行。初版封裝的鎖檔檢查遇到單檔發布新增的分析器套件，最終只允許原有鎖檔之外的同版本分析器，原相依套件維持鎖定。
- 通過 981 項領域、81 項世界串流及 10 項測試代理檢查。最終解壓工具在已封存的隔離管理服務重建兩個缺少的本機封存回條，副本與完整日誌逐位元一致。有效但角色不符的金鑰、來源不符及截斷日誌都被拒絕，原檔及管理端資料保持一致。
- 原生 Windows 0.49.0 與管理包 0.31.63 的 `20261110-045845-cb0e4911` 及 `20261110-045919-504192bb` 分別把同場已保存畫格從 16 補到 48、從 29 補到 59。每場在回放失聯時先將戰鬥事件從 1 筆補到 4 筆，回放恢復後重試，結果與原日誌相符。瀏覽器確認可從第 30 格接續到第 59 格，損耗 80，且仍顯示未封存。重複補送無新資料，兩組 C／F 各 24 檔逐一核對雜湊。
- 原生測試也確認原程序仍鎖檔及管理場次未結束時拒絕補送。兩個中斷場皆未有原完成紀錄，最終 CSV 與場館 ZIP 仍回應 409，玩家未收到最終戰績。首輪 `20261110-045711-b2aceb87` 的短 JSON 請求被隔離代理拒絕，原結果保留，最終改用固定長度的請求。
- 發布來源 `e04721d00399576e66bc43dda16815c2d5bf4114`。GitHub Actions job `129435669376` 因帳務或支出上限未啟動。Quest 3、VIVE XR、實體 MR、廠商硬體及跨機 25 人仍待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42698215637)

## 2026-11-10 玩家開啟原任務回放片段

控制台 0.31.63 可由主控匯出已封存的共用片段。玩家在獨立頁面從本機開啟檔案，依原保存時間播放、逐格、調整速度與切換房間俯視。每份上限 300 格及 8 MiB。匯出包含原場景、角色及戰鬥事件，欄位不含操作憑證、入場票券、名冊姓名或戰績明細。 [操作說明](WORLD_RECORDING.md#讓玩家開啟回放)

- 最終 Windows 管理包 `artifacts/windows-control-console-0.31.63-win-x64.zip` 共 52,800,201 bytes，SHA-256 `bfc92a07f5ecd5d54d5c7155c732d5654900a9599dd9bf8caffc265a477ce83f`。已核對 172 份來源、520 份執行環境檔案及 540 筆封裝清單。解壓包通過 106 項啟動器與 76 項世界串流檢查，另通過 981 項領域與 102 項 Node 檢查。
- 最終解壓包通過 626 項 Chromium 檢查。下載逐欄比對 22 格原封存內容，另一來源的回應遭拒。未登入的新瀏覽器在 390 像素寬度讀檔、逐格並播至原終點，無管理 API 請求，截斷檔案會清除顯示。證據 `console-player-replay-72657f9e51494c559a3716009751c5c9`。
- 首輪原生測試 `run-8d8113584d9c42f6995aa8a31e2056c8` 的獨立房封存成功，瀏覽器因未指向已安裝的 Chromium 快取而中止，收尾無遺留程序。指定原快取後，初版套件 `run-9b0a1bb464f34066899eff242ca318bb` 的兩種模式通過 400 項。最終套件另調整手機版面及初始鏡頭。
- 最終解壓包搭配 Windows 0.49.0 原生遊戲的 `run-9f17f8c6e3fb41cfbbda5594cb59a2e1` 通過 400 項。獨立五房與合併場各接入 25 個同機模擬玩家程序。獨立房第 222 至 223 格及合併場第 128 至 129 格的檔案均逐欄對上原錄製，未登入的播放器到達各自終點，管理 API 請求為零。六場共核對 1,024 格完整回放、50 份原戰績及六份場次 CSV，雙封存後無活躍場次、遺留程序或清理錯誤。
- 發布來源 `18adff5dd7e09e28da084377cba79e3536501cd9`。GitHub Actions job `129427793422` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42695975062)
- Quest 3、VIVE XR、實體 MR、廠商硬體及跨機 25 人仍待現地驗收。

## 2026-11-10 直接核對 Quest 原批次擷取報告

五房驗收清單可引用 Quest 網路計畫和一份或多份完整的擷取報告。工具逐席核對日誌原始位元組、SHA-256、PID、房號、席位、IPv4、遊戲端點及伺服器戰績確認。Windows 席位可在同一清單補入。 [驗收操作](EXTERNAL_CLIENTS.md#直接使用-quest-批次擷取報告)

- 本機通過 98 項 Python 測試，包含 43 項戰績驗收及擷取、40 項 Quest 部署、9 項 Quest UDP 預檢、6 項 LAN 預檢。其中一項以同一清單核對 25 席 Quest 日誌、25 份逐來源 UDP 配對及 25 筆戰績確認。
- 以模擬 ADB 執行擷取工具及驗收命令。獨立五房使用兩份報告，核對 10 席 Quest、15 席 Windows 與 25 筆模擬戰績確認。合併場使用兩份報告，核對 25 席 Quest 與 25 筆模擬戰績確認。證據在 `artifacts/quest-capture-acceptance/run-efa2433fcf354f2997fbb7b6dac2f455`。
- 重讀先前 Windows 同機測試 `run-91564904c33346809effddd207da53a3` 的原清單與封存。兩種模式各核對 25 筆原伺服器戰績確認及共六份原回放，摘要與前次完全相同。Quest 3、VIVE XR、MR 場地、廠商硬體及跨機 25 人仍待現地驗收。
- 發布來源 `45090eaff9246b8ab6891a960790d9bd3288f578`。GitHub Actions job `129420022445` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42693755827)

## 2026-11-10 在管理實例間交接任務範本

控制台 0.31.62 可下載指定保存版本的 JSON 範本，再於另一個管理實例檢查及載入為新草稿。匯出包含原任務定義，目的端明確儲存後建立自己的版本。 [操作說明](MISSION_VERSIONS.md#在管理實例間交接任務範本)

- `artifacts/windows-control-console-0.31.62-win-x64.zip` 共 52,781,202 bytes，SHA-256 `57537d986b5838c356c7d12ffa544c30e4066610db7513b9a5e1b3247db3e6e5`。169 份來源、511 份執行環境檔案及 531 筆封裝清單已核對。解壓包通過 106 項啟動器檢查，另通過 981 項領域及 17 項管理包與伺服器包邊界檢查。
- 本機任務專項通過 39 項。來源端下載歷史版本，目的端以不同金鑰和 SQLite 資料目錄檢查、載入、儲存及建立五個準備場次。比對原文字、環境、敵軍與兩件掩體。來源任務維持原版，兩端保存 ID 不同。證據 `console-mission-template-focus-c76870512cb44ca1807fb89d4ea741ec`。
- 最終解壓包通過 102 項 Node 及 619 項 Chromium 檢查。加入不完整成功回應、過期預覽、取消替換、檔案大小及 500 件物件與完整文字長度的檢查。兩次瀏覽器匯出逐位元一致，範本 SHA-256 為 `e1677ec325fa51d77803f8db49c50ee3f6724d3c23ac29012e938dfc9c321898`。最終證據 `console-mission-template-package-b61d94b6cbd74be597784e8d096a2437`。
- Windows 0.49.0 與最終管理包的 `run-fa33feb452a54844851c4b909117c1e9` 通過 370 項。匯入同一份範本後，五房獨立和合併各以 25 個同機玩家程序執行。六場皆核對 120 秒、雨夜、雷電開關、兩名巡邏敵軍及各房的沙包與油桶位置、旋轉。共核對 954 格完整回放、50 份原戰績與六份 CSV，雙封存後無活躍場次或遺留程序。
- 發布來源 `e2b7891077e13744bcd16d05aaa1bdcd8826a71d`。GitHub Actions job `129411160887` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42691226534)
- Quest 3、VIVE XR、MR 場地、廠商硬體及跨機 25 人仍待現地驗收。可用同一任務範本交接場地配置，MR 校正及入場配票依目的端場次處理。

## 2026-11-10 硬體排演的座位及入場綁定

硬體模擬器 0.2.3 搭配 Windows 管理包 0.31.61，可由本房房控將設備座位清單轉成目前入場綁定。版本 2 設定在握手、讀取回饋及確認批次時核對同一入場。入場失效時關閉該房模擬連線並取消待確認批次。 [操作說明](HARDWARE.md#依現行名冊建立座位綁定)

- 硬體包 `hardware-simulator-0.2.3-net10.zip` 共 187,001 bytes，SHA-256 `459271d2ca4c6d58030d913fba36f2f0f0c9e8b8f2b7f1b102ab753dd816c4fb`，8 筆清單。管理包 `windows-control-console-0.31.61-win-x64.zip` 共 52,776,263 bytes，SHA-256 `fc801536a82b40e348d945ebc42d8cd83f9b43ee9c0a9ab9882b2268d6071f6d`，531 筆清單。兩包解壓核對通過，管理啟動器另通過 106 項。
- 981 項領域檢查及 38 項離線模擬通過，硬體解壓包的離線範例輸出與原驗證逐位元一致。實際 API 與模擬 TCP 程序通過 27 項，原建置證據 `run-ecbc32e8d9e945e8be33e75c954358db`，兩個解壓包複驗證據 `run-aa302f645543484f8422f89d0b5f7737`。同玩家 ID、同座位的新入場會使舊設定在握手前停止。移除房 1 原入場時取消指定批次，其他四房在原連線各完成兩次模擬確認。首輪 `run-faf7a873853f4799a7cd7c1f0e90719f` 使用兩房建立 Linked 測試場時被原五房規則拒絕。
- Windows 原生遊戲 0.49.0、Unity OpenXR 模擬執行環境與兩個新解壓包的 `run-976388292bfe42bfb08f59041be27b08` 通過 92 項。兩席使用版本 2 綁定，117 格封存中第 101 格的唯一射擊與原戰鬥報告、入場及一筆 TCP 模擬確認相符。兩份玩家戰績、CSV 及雙封存通過，收尾無活躍場次或遺留程序。
- 發布來源 `22ebdde64d020a3a2eed50c728c0be4629be7cdf`。GitHub Actions job `129404626924` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42689344339)
- 廠商協議、設備輸入、強度映射及實體停止待取得技術資料後整合。Quest 3、VIVE XR、實體 MR 與跨機 25 人仍待現地驗收。

## 2026-11-10 保存及交接共用回放片段

控制台 0.31.60 可將標記的起訖命名保存，主控可新增及移除，房控依原錄製權限讀取並載入同一對畫格。兩端的時間從原快照取得，寫入與重試均核對錄製來源。 [操作說明](WORLD_RECORDING.md#保存共用片段)

- `artifacts/windows-control-console-0.31.60-win-x64.zip` 共 52,775,228 bytes，SHA-256 `14d2ee5ecc8c1802dd373120b79b54092935fced783610096235b43100d4155c`。168 份建置來源、511 份執行檔案及 531 筆封裝清單已核對。解壓包啟動器通過 106 項，管理包及伺服器包邊界通過 17 項。
- 通過 981 項領域與 74 項串流檢查。涵蓋房間權限、另一來源、倒置及尚未保存的範圍、24 段上限、精確重試、移除後的遲送寫入，以及 SQLite 重啟。以原 0.31.59 解壓包建立的 24 格測試錄製，升級 0.31.60 後原錄製資訊與指定原格相同，重啟後可讀新片段，無 SQLite 外鍵違規。證據 `replay-clips-upgrade-511f3378a807431dacebe1ca316c258a.json`。
- 最終解壓包通過 102 項 Node 與 608 項 Chromium 檢查。真實 API 與瀏覽器核對保存已接受但回應中斷時的同識別重試、房控重新登入後載入並播放、移除後仍保留原畫格。證據 `console-shared-clips-6080e85a6294460cbcb2ff5da0240a6d`。
- Windows 0.49.0 原生遊戲端與新管理包的 `run-0161bfbbc7fd4a50b25439fd346b6e33` 通過 369 項。五房獨立與合併各接入 25 個同機玩家程序，共核對 993 格完整回放、50 份原戰績及六份 CSV。獨立場第 205 至 206 格、合併場第 140 至 141 格均從主控命名保存、重新載入並播至原終點。同房權限讀到一致的片段 ID、來源、範圍及結束時間。收尾後無活躍場次、遺留程序或清理錯誤。
- 發布來源 `37685b6bb89e19e6a15f98121acfffeb5ecfd2db`。GitHub Actions job `129395978193` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42686889287)
- Quest 3、VIVE XR、實體 MR、廠商硬體及跨機 25 人仍待現地驗收。設備到場後，可用共用片段標記原頭盔錄製中的關鍵畫格，配合原日誌與戰績核對。

## 2026-11-10 任務回放指定片段

控制台 0.31.59 在逐格檢視加入起點與終點標記，可暫停、變速續播或重播指定片段。起訖使用原保存序號，讀到終點確認才顯示完成。完整錄製及未封存的原保存尾端仍可檢視。標記保留在目前的回放頁，適用於戰後檢討。 [操作說明](WORLD_RECORDING.md#重看指定片段)

- `artifacts/windows-control-console-0.31.59-win-x64.zip` 共 52,761,717 bytes，SHA-256 `33416e78f38a5abc387cfb97ddf3ce91f0e378155c47d2b2bf44cc260795f8ea`。166 份建置來源、508 份執行檔案及 528 筆封裝清單已核對。解壓包啟動器通過 106 項，管理包與伺服器包邊界另通過 17 項。
- 最終解壓包通過 102 項 Node 與 603 項 Chromium 檢查，另通過 981 項領域及 68 項世界串流檢查。瀏覽器證據為 `console-replay-interval-package-e81dd75ec90f43128562292a0a31811d`。包含首格送達前暫停、保留續播序號、未封存尾端及故意省略串流尾端後重試。
- 管理包搭配 Windows 0.49.0 原生遊戲端的 `run-9443a8b71faa4c78821b3cd80254866e` 通過 367 項。獨立五房與合併五房各接入 25 個同機玩家程序，核對 1,042 格完整回放、50 份原戰績及六份 CSV。獨立房 1 第 204 至 205 格與合併場第 144 至 145 格均在指定終點停止，並核對原格時間及 Running 階段。收尾後無活躍場次、遺留程序或清理錯誤。
- 發布來源 `4ef9d9e1b70476ad24f0a511c28f8c595753b4d6`，原生驗收程式 `26035442e43e6b9f0b40092974711a7eabdc3fbb`。GitHub Actions job `129389065945` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42684936042)
- Quest 3、VIVE XR、實體 MR、廠商硬體及跨機 25 人仍待現地驗收。設備到場後，可用原始頭盔日誌及場館證據核對實際錄製與戰績。

## 2026-11-10 混合 Windows 與 Quest 的 UDP 封存驗收

場館清單可引用多份 Quest 批次報告，並逐場補上 Windows 原始報告。批次內路徑以各批次報告所在資料夾為準，逐場補充路徑以場館清單為準。驗收逐遊戲端點核對收到戰績確認的來源，要求每個來源只對應一組原始交換。 [操作說明](EXTERNAL_CLIENTS.md#核對每個玩家來源的-udp-預檢)

- 本機通過 38 項封存、9 項 Quest 探測及 6 項 Windows UDP 測試，涵蓋獨立與合併模式、同名原檔分目錄、缺漏來源與重複證據。
- `artifacts/quest-udp-probe/mixed-readback-01d705824eef4edea00d2105657c3026` 保存 26 份報告及索引。每種模式把兩批各 10 組既有 Java 探測與 5 組新增的 Windows PowerShell 探測合併核對，共 50 組實際同機 UDP 交換及 150 個樣本。這輪的封存玩家資料是測試資料。
- 另以新清單格式唯讀核對 Windows 原生場次 `run-91564904c33346809effddd207da53a3`，兩種模式的 50 筆戰績確認、六個原預檢端點及驗收摘要均與原封存一致。Quest 3、VIVE XR、實體 MR、廠商硬體與跨機 25 人仍待現地驗收。
- 來源 `d31b89f33dd7bbd9b09a55fb012a9c9455138008`。GitHub Actions job `129383576549` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42683373836)

## 2026-11-10 五房 Quest 批次 UDP 預檢

批次工具沿用原 Quest 席位清單和開場前網路配置，依序在每個正式遊戲埠核對原始 UDP 報告。失敗席保留診斷階段，其他席繼續。端點內安排的席位全數通過後才提供逐來源清單。封存驗收可用 `udpPreflightBatch` 直接引用整批報告，再核對原實際端點、時間窗及已確認玩家來源。 [操作說明](QUEST3.md#批次預檢五房-quest-席位)

- 本機通過 9 項 Quest 探測、6 項 Windows UDP 與 37 項封存驗收測試。原端點已占用時，監聽失敗不會執行頭盔探測，也不會停止原 socket。無 ADB 裝置的實際 CLI 檢查留下失敗摘要，未執行 UDP。
- 在 `venue-interop-0ffce5cd25f4472da01a8a80f7245930` 保留 108 份證據。獨立及合併模式各由 25 個不同同機 IPv4 的 Java 探測端和真正 PowerShell 監聽完成 75 個樣本。50 組交換摘要互異，六個端點都能在監聽退出後重新綁定。ADB 裝置層使用替代測試，頭盔 Wi-Fi 仍待現地驗收。
- 以新批次索引唯讀核對已封存的 Windows `run-91564904c33346809effddd207da53a3` 原證據。兩種模式的逐來源驗收摘要均與原結果一致，共 50 筆玩家戰績確認、六組原預檢及六份原世界日誌。這次重讀使用原 Windows 證據。Quest 3、VIVE XR、實體 MR、廠商硬體及跨機 25 人仍待驗收。
- 來源 `ed1e95ebf04003497e6bf063394b9f68e45e7c8d`。GitHub Actions job `129379176826` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42682128644)

## 2026-11-10 Quest UDP 預檢診斷 APK

獨立 Android 診斷 APK 0.1.0 可由指定的 ADB 裝置執行，從指定的頭盔 IPv4 發送與 Windows 監聽端相容的 UDP 挑戰。診斷報告可直接供逐來源封存驗收。Windows 主控可用同一套監聽流程收集 Windows 與 Quest 來源的報告。 [操作說明](QUEST3.md#開場前從頭盔執行-udp-預檢)

- F 槽 `vr-command-quest-udp-probe-0.1.0.apk` 共 16,588 bytes，SHA-256 `478bcd63b9d79aca638d49049388021241245a6f046f3221fd95b0ba6e2f4c1f`。已以 Android SDK 建置、對齊和簽章，獨立核對 v2、最低 API 32、目標 API 35、3 個 APK 項目及 DEX 內的探測與 instrumentation 類別。初始建置檢查被 SDK 欄位名稱與簽章方案擋下，最終依 aapt2 的 `minSdkVersion` 與明確 v2 設定核對通過。
- 本機通過 5 項探測專項、6 項 UDP 測試與 36 項封存驗收測試。Java 共用核心與真正 Windows PowerShell 監聽完成 3 個 UDP 樣本，原交換摘要相同。錯誤來源埠、驗證碼及過長封包遭拒絕。另在 `interop-04780f974f0a4c3ba525f45c19ed1b2f` 保存 Java 與 PowerShell 先後使用同一埠的 4 份原報告及完整來源摘要，核對 2 個同機 IPv4、各 3 個樣本。ADB 金鑰傳遞、清理及錯誤回應是模擬測試，ADB 未偵測到實機。
- 來源 `b5de23c49ed42b169035888e74169d20303504b7`。GitHub Actions job `129373652727` 因帳務或支出上限未啟動。Quest 3、VIVE XR、實體 MR、廠商硬體與跨機 25 人仍待現地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42680566365)

## 2026-11-10 場館 UDP 預檢的完整來源核對

場館驗收工具可按每個原遊戲綁定，要求收到戰績確認的所有來源 IPv4 各有一組原始 UDP 預檢。獨立場逐房使用各自的埠，合併場以共用埠核對全部來源。單組驗收流程仍可用，摘要只列來源數、樣本數及交換摘要。 [操作說明](EXTERNAL_CLIENTS.md#核對每個玩家來源的-udp-預檢)

- 36 項封存證據測試通過。Linked 的 25 個來源測試資料核對到 25 組原格式報告，缺一組即拒絕。另驗證重複來源、重複交換、未知來源、CLI 重複參數及摘要隱私。首輪一項測試因 Python 房號鍵與 JSON 字串鍵直接比較而失敗，改為對照序列化結果後重跑通過。
- Windows PowerShell 5.1 及 PowerShell 7 各通過 6 項 UDP 測試，同埠先後接收兩個不同的本機 loopback IPv4，核對兩組原交換。來源 `da25ecb3b68e04a35afaa690ca00badabe0ffcf2`。GitHub Actions job `129366568542` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42678578427)
- 管理包 0.31.58 與原 Windows 0.49.0 的 `run-91564904c33346809effddd207da53a3` 通過 457 項。獨立五房與合併五房各有 25 個同機原生玩家程序，六個遊戲端點先完成共六組原始 UDP 預檢，再由各自遊戲程序綁定。封存後完整來源核對確認 50 筆伺服器戰績回覆、1,004 格原錄製及全部六組預檢。兩種模式都拒絕把同機證據標為跨機。收尾後無活躍場次，C／F 副本 229 檔一致。Quest 3、VIVE XR、實體 MR、廠商硬體及跨機 25 人仍待現地驗收。

## 2026-11-10 敵軍策略與實際人數快照

控制台 0.31.58 在房卡確認全館及個別場次的敵軍策略，分列管理端全場目標、本房在場及存活數。「檢視敵軍快照」定位該房的原保存格。快照過期會清除實際人數及入口，觀戰與回放顯示各格保存的行為與自動攻擊開關。 [操作說明](LAYOUT.md#全館敵軍策略)

- 75 項場次專項在真實 API、SQLite 與 Chromium 通過。測試發布器的部分增援驗證全場目標 2 名、本房在場及存活各 1 名，並核對全館巡邏／開啟攻擊及單房推進／關閉攻擊。替換人數的回放回應遭拒絕。
- `windows-control-console-0.31.58-win-x64.zip` 共 52,759,246 bytes，SHA-256 `67496776809b41225327d05eee60c415a4dbe2e5fdaab89e7052fe4194e28aa1`。528 筆清單檔、166 份來源檔及管理啟動器 `run-122d4b6d401848eb814d3bf1196cce9b` 的 C／F 副本 27 檔已核對。啟動器 106 項及領域 981 項通過。
- 最終管理包搭配原 Windows 0.49.0 遊戲端的 `run-5c1c543ffd754f46a42fc0c85dfdbc0a` 通過 400 項。獨立五房與合併五房各有 25 個同機原生玩家程序，每房 5 名敵軍。在守備並開啟自動攻擊後，50 份玩家結果均有受傷及中彈紀錄。改為推進並關閉攻擊後，逐場確認原指令序號。20 筆房卡資料核對到 12 格原保存快照，另核對 1,555 格完整回放、戰績 CSV 及合併場 ZIP，雙封存後無活躍場次，C／F 副本 218 檔一致。Quest 3、VIVE XR、實體 MR、廠商硬體及跨機 25 人仍待驗收。
- 最終解壓包通過 Node 102 項及 Chromium 592 項。來源 `df585f90ba0b8a23967f6be06b2ed66148f463c7`。GitHub Actions job `129359423907` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42676577446)

## 2026-11-10 從房卡檢視已確認的環境快照

控制台 0.31.57 在房卡確認全館及單一場次環境設定。只有來源、原指令序號、有效時間及天氣／日夜／雷電都符合時，才顯示「檢視環境快照」。開啟後定位該房的俯視圖，停在同一格保存畫面。 [操作說明](ENVIRONMENT.md#全館即時環境)

- 真實 API、SQLite 與 Chromium 的 69 項場次專項通過。測試發布器確認全館暴風雨／夜晚／雷電與單房雨天／關閉雷電各自定位正確的快照。單房覆蓋後不能重用舊指令快照，替換雷電值的回應被拒絕，快照過期後入口清除。房控的就緒資料仍只含本房。
- `windows-control-console-0.31.57-win-x64.zip` 共 52,755,555 bytes，SHA-256 `3b726cec35550113b224dbbefbde063ab456f456b735ce3ce28ea23f832a0924`。528 筆清單檔、166 份來源檔與管理啟動器 `run-b20bad9d59f2449cb402c1d740a58848` 的 C／F 副本 27 檔已核對。啟動器 106 項及領域 981 項通過。
- 最終管理包搭配原 Windows 0.49.0 遊戲端的 `run-4101fba2eeb3412bbb942c76040d0340` 通過 375 項。獨立五房及合併五房各接入 25 個同機原生玩家程序，均完成暴風雨／夜晚／雷電及晴朗／白天／無雷電兩次切換。20 筆房卡資料核對到原來源及 12 格確認快照，另完成雙封存、979 格完整回放、50 份玩家結果與六份 CSV。收尾後無活躍場次，C／F 副本 218 檔一致。Quest 3、VIVE XR、實體 MR、廠商硬體與跨機 25 人仍待驗收。
- 最終解壓包通過 Node 102 項及 Chromium 586 項。來源 `906f2c6881896e17f78f7a2c98a04272057adf22`。GitHub Actions job `129353879135` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42674993727)

## 2026-11-10 分房統計與個人檢討

控制台 0.31.56 在五房合併場次提供共用的「統計與檢討範圍」。主控可查看全場或單房，房間控制台顯示本房。選擇同時套用至戰績表、個人檢討名單與最終 CSV，並保留已離場玩家。從分房開啟個人回放時，視角及首次事件搜尋會定位到原房。 [操作說明](REPORTS.md#從戰績開啟個人回放)

- 63 項場次專項在真實 API、SQLite 與 Chromium 通過。測試發布器保存的 Linked 場次驗證同房名單、清除上一房選取、已離場玩家及帶有原玩家與房號的首次搜尋。五房 ZIP 沿用原全場匯出，CSV 與個人回放各自沿用原有封存門檻。
- `windows-control-console-0.31.56-win-x64.zip` 共 52,753,315 bytes，SHA-256 `afe40345b207b5cd897cafc6cd7024d546a1d2485bb1748707e8e39dc0439e4b`。528 筆清單檔、166 份來源檔與管理啟動器 `run-3937e5c3ee1c471583ffe4fbf930056f` 的 C／F 副本 27 檔已核對，啟動器 106 項通過。
- 最終解壓包通過 Node 102 項及 Chromium 580 項。封存前可切換房間，CSV 仍須等原封存；分房畫面和實際下載的 CSV 核對到相同房間及玩家。另驗證空房、重新整理、切換場次與登出，以及 390 像素手機版面。這輪驗證控制台與管理包，遊戲端沿用原建置。Quest 3、VIVE XR、實體 MR、廠商硬體與跨機 25 人仍待驗收。
- 來源 `483028f74f9f14d563780fffe95f48efa59969cb`。GitHub Actions job `129351091709` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42673720540)

## 2026-11-10 全館開始的逐房就緒狀態

控制台 0.31.55 在「全館場次控制」顯示各準備房的開場條件。主控可以分辨空名冊、缺少或過期的快照、設定待同步及等待姿態的席號。合併場次中，已就緒的房間會提示正在等候同場其他房間。診斷沿用原開始條件，並核對同一場次、序號及快照的 1.5 秒有效窗。 [操作說明](MISSION_CLOCK.md#全館開始)

- 最終解壓包通過 Node 102 項及 Chromium 571 項。MR 專項 28 項使用真實 API 與合成追蹤發布器，驗證 25 席中第四房第 2、5 席未就緒、房間控制者取不到主控診斷、過期快照清除提示，以及較舊管理序號無法啟用全館開始。獨立 VR 測試分辨一房就緒與另一房空名冊，並驗證原批次開始與執行中來源確認。
- `windows-control-console-0.31.55-win-x64.zip` 共 52,752,220 bytes，SHA-256 `b9ca880b911e0ba51d4f0a07598496e94ec29d44612d9c19cf65e76fc88323b5`。528 筆清單檔、166 份來源檔、管理啟動器 `run-c1735caf41fd42808d898603a927ca63` 的 C／F 副本 27 檔已核對，啟動器 106 項及領域 981 項通過。
- 最終管理包與 Windows 遊戲端 0.49.0 的 `run-57a7b7f88f9f4e55a91036f0c11279f0` 通過 367 項。獨立五房及合併五房各有 25 個同機原生 VR 玩家程序，分別以同一批開始五個及一個原場次。每房五席的準備快照、原批次重試、執行中確認、雙封存、974 格完整回放、50 份玩家結果及六份 CSV 已核對。測試結束後無活躍場次，C／F 副本 218 檔一致。
- 來源 `5d427dd0326b0cc7534767dee1c90609cc00117b`。GitHub Actions job `129348937249` 因帳務或支出上限未啟動。Quest 3、VIVE XR、實體 MR、廠商硬體及跨機 25 人仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42672249862)

## 2026-11-10 五房版本確認與建立結果

控制台 0.31.54 在各房選單下顯示模式、任務時間和場地檢查。逐房指定送出前，確認視窗列出五房的保存版本。伺服器回覆後，最近確認的建立結果顯示各房實際場次 ID、版本、模式與時間。先前的結果會保留到收到與原確認內容一致的新批次回覆；登出時清除。 [操作說明](MISSION_VERSIONS.md#逐房指定任務版本)

- `console-five-receipt-before` 在 0.31.53 重現只有總體提示、缺少逐房結果。新版 26 項專項核對取消不寫入、比較過的歷史版本只套到預覽房、送出回覆遺失後用原請求重試、內容錯置的回覆不覆蓋前一批，以及真正的 VR／MR 混合批次結果。首版手機結果需橫向捲動，最終調整欄位換行並核對 390 像素截圖，各房場次 ID 完整可見。
- 最終 `windows-control-console-0.31.54-final-win-x64.zip` 共 52,749,517 bytes，SHA-256 `75adf202951c3c3d804d50cf333a25b65f79b2978f7e0a0a414bae025eaac49b`，528 筆清單檔及 166 份來源檔已核對。管理啟動器 `run-e5c661ce0d7f4988ad55bb535ac1ef89` 通過 106 項，C／F 副本 27 檔一致。
- 最終管理包搭配 Windows 0.49.0 執行 `run-81b31f44bab64985a90ebeaa3dd57cc5`，120 項、690 格保存回放、C／F 副本 52 檔一致。三個 VR 房及兩個 MR 房以原生伺服器發佈五個 Preparing 端點，瀏覽器下載與工具核對 25 份原簽發票券及 MR 校正檔。ADB 為模擬，原場未進入遊玩，回放僅涵蓋準備及封存。
- 完整回歸在最終解壓包通過 Node 102 項及 Chromium 562 項。保留首版包與其 562 項結果，最終採用手機欄位換行版。來源 `bcea5bf86b4ac28417528cecd845c126ba126a7b`。GitHub Actions job `129346637646` 因帳務或支出上限未啟動。Quest 3、VIVE XR、實體 MR、廠商硬體及跨機 25 人仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42670845773)

## 2026-11-10 任務版本比較與開場選擇

控制台 0.31.53 可將目前草稿與選定的保存版本並列，核對名稱、簡報、時間、環境、敵軍及依清單順序顯示的物件配置。草稿或選擇改變時會清除舊比較。可直接選用比較過的保存版本開場，保留草稿。保存草稿後，開場區保留已選版本。 [操作說明](MISSION_VERSIONS.md)

- `console-mission-compare-before` 在 0.31.52 重現另一位主控先保存第三版後，確認自己第二版的儲存會改掉原本選定的第一版。新版在真正 API 與 Chromium 核對保存重試、歷史內容與未儲存配置、從比較直接建立原版本場次、行動版及登出後遲到的回應。最終解壓包專項 30 項，五房獨立指定及批次重試 18 項通過。
- `windows-control-console-0.31.53-win-x64.zip` 共 52,747,755 bytes，SHA-256 `d192c4a8ec01f806a650a31b66e79d1da40745caa570bf434fbdffb98ffd54d0`，528 筆清單檔及 166 份來源檔已核對。Windows 管理啟動器 `run-da96fd93875248deba87168497a52635` 通過 106 項，C／F 副本 27 檔一致。
- 完整回歸通過 Node 102 項、Chromium 554 項，來源 `dbd189deb18658a204e271574100b2ab22fc5d3a`。GitHub Actions job `129341895589` 因帳務或支出上限未啟動。本次驗收涵蓋管理包與場次準備，頭盔、實體 MR、廠商硬體及跨機 25 人仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42669487411)

## 2026-11-10 任務草稿捨棄確認

控制台 0.31.52 在有未儲存修改時，會在載入最新版或歷史版、建立新草稿、手動登出及重新整理前提醒。取消後保留原任務欄位、場地物件和復原紀錄，且不發出載入或寫入。確認載入後，等所選版本成功讀回才換掉草稿。保存進行中取消登出會留在原登入與編輯鎖定狀態。憑證失效仍會由授權流程直接清除工作區。 [操作說明](MISSION_VERSIONS.md)

- 舊管理包在 `console-draft-guard-before` 重現直接覆蓋草稿。新版任務讀取專項 24 項通過，從最終 ZIP 解壓的物件編輯專項 30 項通過。首輪完整及解壓專項誤要求持有未回覆的儲存請求時顯示重試欄，保留原失敗。複驗核對取消登出、原登入及欄位鎖定，再放行原請求確認保存。
- `windows-control-console-0.31.52-win-x64.zip` 共 52,744,302 bytes，SHA-256 `f4a5dcb32e4e778f5e27c1b67ce98b533213c39dffccc7eeb2d0c285da7dfbeb`，528 筆清單檔，ZIP 與解壓逐檔核對。管理啟動器 `run-c91fb71f6a2344339cf476c9a7f78b83` 通過 106 項，C／F 副本 27 檔一致。Windows 0.49.0 原生 `run-51a48d9c25ef49d4af78a196a4933e5a` 以新版管理包核對五房獨立與全連線的已存配置，149 項、575 格回放及 10 份戰績，C／F 副本 78 檔一致。原生場使用同機桌面程序。
- 最終完整回歸通過 Node 102 項及 Chromium 546 項。Windows 發行收據的 166 份來源檔與目前專案相符，測試來源 `24b0d74905bae4564fa58a4cf22917b5f56f92d6`。GitHub Actions job `129337484528` 因帳務或支出上限未啟動。本次未進行頭盔、實體 MR、廠商硬體及跨機 25 人的驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42668222501)

## 2026-11-10 Windows OpenXR 撤銷票券與原席替換

沿用 Windows 0.49.0 遊戲包、0.31.51 管理包及 Vive Menu 測試 DLL。主控在準備階段撤銷原入場，房控再把同一位玩家加回同一席。原票券在撤銷前有效。替換後，管理 API 拒絕原票券，原入場識別碼也無法再用來移除新席。原玩家程序透過模擬 Menu 向遊戲伺服器重送原票券，該 UDP 嘗試被拒。換發新票券並放開再按後，同一程序以新入場恢復追蹤。 [複驗方式](QUEST_RECONNECT.md#windows-openxr-重連複驗)

- `run-85e3099195794932b3a43604698e78b7` 退出碼 0，92 項、171 格回放。原連線 2 撤銷，嘗試 3 遭拒，連線 4 帶新入場加入。回放第 52、61、77、86、121、123 格對應原入場、撤銷、替換等待、拒絕、放開及重新入場。雙封存、兩份原戰績與 CSV 相符，只有連線 1、4 收到伺服器確認。管理 API 在 End 後拒絕新票券。活動場次與剩餘程序均為零，C／F 隔離副本 44 檔一致。
- 首場 `run-50ff448532f7452ca06e3bc261d4ab45` 退出碼 1，保留 190 格及 39 檔 C／F 副本。首輪把桌面席姿態視為須跨名冊重建連續，回放第 80 格顯示新名冊版本剛套用時仍等候新姿態。複驗第 67 格亦記錄同一類情形。現在分開核對原桌面 UDP 連線與每個名冊版本的姿態，逐格確認原票券從撤銷到新票券啟用前未恢復參與。
- 原 UDP 中斷後重連同一入場的 `run-ac8966a279284ec38a589e2382af2e56` 退出碼 0，87 項、430 格回放、44 檔 C／F 副本一致。另有伺服器封裝 10 項及 CLI 選項拒絕 2 項通過。
- 來源 `49a64bbf03db6192bf1bb73b6488aa1a3af2df0b`。GitHub Actions job `129331809718` 因帳務或支出上限未啟動。此次為 Windows OpenXR 同機模擬，Quest 3、VIVE XR、MR 場地、跨機 25 人及廠商硬體仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42666602006)

## 2026-11-10 Windows OpenXR 用 Vive Menu 重連

沿用 Windows 0.49.0 玩家與伺服器包及 0.31.51 管理包。OpenXR 席先經本機 UDP 轉送入場，在原任務射擊一發後關閉轉送，等伺服器與客戶端均記錄斷線。更新原連線檔為同一入場的新票券及原伺服器端點。Unity Mock Runtime 回報右手使用 Vive 設定。按住 Menu 或放開都沒有建立連線，重新按下才由原玩家程序讀檔，在同一場次恢復追蹤。 [複驗方式](QUEST_RECONNECT.md#windows-openxr-重連複驗)

- `run-4e9a7cffedf14fdfb8c594f4dcea3eb4` 退出碼 0，87 項、423 格回放。原 OpenXR 連線 2 斷線後，同一入場改由連線 3 恢復。回放第 383、407、414、416 格逐格核對斷線、持續按住、放開及重連。健康維持 100，彈匣 29 發、備彈 90 發，原桌面席持續參與。雙封存、兩份戰績、CSV 及伺服器對連線 1、3 的確認相符。活動場次、剩餘程序及轉送均為零，C／F 隔離副本 44 檔一致。
- 四次未通過的原證據保留。`run-2907b72411c94d8da5528d805acc7811` 使用了開場序號 5，原回放顯示射擊後已到 6。`run-0a2ea54b94094c9fa8e012b252e0002e` 的模擬 B 同步後未建立新連線，`run-3cdca755e7c94a7f9a013de0a59f4a87` 未讀到預期的 Oculus Touch 設定。`run-f4f748625ca74f778558588dde7464a5` 的 Vive Menu 已重連且原伺服器確認新連線，但檢查器誤比對斷線前的編號。最終按射擊後序號及最後接受的連線核對，沿用遊戲原有重連及封存流程。
- 使用同一測試 DLL、未啟用重連選項的射擊及硬體模擬複驗 `run-517cdfc3f961489ca6991b6dd8872053` 退出碼 0，91 項、106 格回放及 43 檔 C／F 副本一致。另有伺服器封裝 10 項及 CLI 選項拒絕 2 項通過。
- 來源 `b0c498e031ea8d6f2c6844ffd0da621136da4e54`，最終測試 DLL SHA-256 `19db8f79819444793bf026a6a23d6d6bb5eae4d99fc12239b727a93d811692b1`。GitHub Actions job `129327230350` 因帳務或支出上限未啟動。Quest 右手 B、VIVE XR 與 Quest 3 實機、MR 場地、跨機 25 人及廠商硬體仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42665295878)

## 2026-11-10 場館封存逐席核對玩家來源

單場驗收可加 `--verify-player-sources`，五房清單可填 `verifyPlayerSources: true`。核對原玩家日誌、入場戰績、UDP 來源及封存回放中的活動姿態。報告區分桌面模擬、Windows OpenXR、Unity Mock Runtime 和 Quest logcat，逐席輸出通過核對的活動影格數。日誌與姿態不一致，或席位從未在活動影格送達有效姿態時，驗收會失敗。 [操作方式](EXTERNAL_CLIENTS.md#核對封存戰績與-udp-來源)

- Windows 0.49.0 與管理包 0.31.51 原生場 `run-9f36fa0fb07a4ea0b966dac7d0e7ebab` 退出碼 0，457 項通過。獨立五房與全連線各從原封存 ZIP、UDP 記錄及閉合回放辨識 24 個桌面席與第 5 房第 2 席的 OpenXR 模擬姿態。該席在兩種模式各有 54 格符合條件。六場共 1,573 格回放及 50 筆原戰績與伺服器確認。活動場次與剩餘程序均為零，C／F 副本 235 檔一致。
- 單場 CLI 可用同一份原始資料重現房 5 的摘要。用副本移除該席的 OpenXR 啟動及執行環境記錄後，以同一回放複驗得到預期的拒絕。場館工具 34 項、回放檔分析 14 項及伺服器封裝 10 項通過。Quest logcat 與其他 Windows 執行環境的分類以測試資料核對，仍需實機確認裝置型號與連線。
- 來源 `730019d61dd89d26ae9b72c299ec69500d63955c`。GitHub Actions job `129319435861` 因帳務或支出上限未啟動。本次驗收使用 Windows 同機程序，Quest 3、VIVE XR、MR 實體場地、廠商硬體與跨機 25 人仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42663076916)

## 2026-11-10 五房 VR 追蹤中斷與恢復

沿用 Windows 0.49.0 遊戲及 0.31.51 管理包。從實際控制台下載原五房配票 ZIP，五房獨立及全連線各同時啟動 25 個玩家程序。第 5 房第 2 席以 Unity Mock Runtime 傳送 OpenXR 頭手姿態，其餘 24 席為桌面玩家。每種模式都用部署工具核對 25 席，只有指定席依序回報 `tracked-ready`、`awaiting-tracked-pose`、`tracked-ready`。恢復時原玩家程序、票券及連線保留，接受位移 0.2 公尺的新頭手姿態。 [複驗方式](WINDOWS_SERVER_PACKAGE.md#三個可攜包整合驗證)

- `run-8758fdcf635c4d50ade2aab1c1c4c4f5` 退出碼 0，417 項通過。五個獨立場次共 1,550 格回放，全連線 256 格。兩種模式各由全館命令開場與結束，核對雙封存、50 份原玩家戰績、原連線的伺服器確認及戰績 CSV。活動場次與剩餘程序均為零，C／F 隔離副本 224 檔雜湊一致。
- 獨立房第 236、250、257、259 格及全連線第 222、236、243、244 格，逐格核對原就緒、失效、持續失效及恢復。失效區間的回放中，獨立場的原房仍有 4 席參與，全連線場的其餘 24 席持續參與。獨立模式在失效的兩次五房快照中，其餘四房皆為 5 席就緒。
- 原單房 OpenXR 射擊與硬體模擬路徑 `run-810b9971d5b54d0d9dc52b23b2fde938` 重新通過 91 項、112 格回放、43 檔 C／F 副本一致。另有封裝工具 10 項及 CLI 參數拒絕 4 項通過。
- 來源 `136decb7962e1da32c90d6babebc47e24e01fdc2`。GitHub Actions job `129315228605` 因帳務或支出上限未啟動。場內 VIVE XR 為名冊分類，Quest 3、VIVE XR、MR 實體場地、廠商硬體及跨機 25 人仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42661864749)

## 2026-11-10 Windows OpenXR 射擊與硬體模擬回饋

沿用 Windows 遊戲 0.49.0、管理包 0.31.51 及硬體模擬包 0.2.2。原生玩家、伺服器、主控 API、.NET 閘道和 TCP 模擬裝置使用各自的封裝。兩席各綁定一個裝置，另一房的金鑰無法讀取原房回饋。追蹤失效、恢復後扣住及放開扳機時，兩個裝置都未收到回饋。重新扣下後，OpenXR 席用彈 1 發，桌面席 0 發。第 104 格的射擊識別碼、API 接受的戰鬥報告及原席位的一筆模擬後座力訊號相符。模擬裝置確認一次，閘道於 End 正常結束。 [複驗方式](WINDOWS_PLAYER_PACKAGE.md#本機追蹤整合驗證)

- 整合場 `run-f546c8eccbb54f0882f715ca033a5c6d` 退出碼 0，97 項、120 格回放。無硬體模擬的原 CLI 路徑 `run-473212f295244ac1a3e6d5cfed7d0dd3` 退出碼 0，80 項、106 格回放。兩場各核對雙封存、兩份戰績、CSV 及兩次伺服器確認。活動場次與剩餘程序均為零，C／F 隔離副本分別 45／42 檔雜湊一致。另有封裝工具 10 項及閘道隔離與停止 20 項通過。
- 首場 `run-2e274928a18b40b6b8a8c259a2274198` 在替換測試扳機命令檔時收到 Windows 存取拒絕，於放開扳機前退出。保留原失敗與 40 檔 C／F 副本。複驗只針對該測試檔的原子替換加入一秒重試上限，沿用每次扳機狀態的確認條件。
- 測試來源 `c5c4d5f9aed8f8786b039f86560eb20593debc35`。GitHub Actions job `129310386178` 因帳務或支出上限未啟動，執行步驟為零。此次只驗收軟體模擬回饋，Quest 3、VIVE、MR 場地、跨機 25 人及廠商硬體仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42660480352)

## 2026-11-10 Windows OpenXR 追蹤恢復後的扳機

沿用 0.49.0 Windows 遊戲包與 0.31.51 管理包。測試 DLL 用 Unity Mock Runtime 的 OpenXR Conformance Automation 傳送扳機狀態，並保存每次成功同步的回條。中斷追蹤時扣住扳機，恢復後仍維持扣住，伺服器未扣彈。放開再短扣 100 毫秒後接受一發。 [複驗方式](WINDOWS_PLAYER_PACKAGE.md#本機追蹤整合驗證)

- 伺服器封裝工具 10 項通過。原生 API 場 `run-d6bf73437cee4bd28de8e4550a0ddff3` 退出碼 0，80 項、106 格回放。實際控制台場 `run-e1515e92db234578803d0a3e490a7bfe` 退出碼 0，86 項、135 格回放。兩場都核對原玩家、同一 UDP 連線、雙封存、兩份戰績及兩次伺服器確認。活動場次和剩餘程序均為零，兩場各 42／44 檔 C／F 隔離副本雜湊一致。
- 最終控制台於執行中顯示 OpenXR 席用彈 1 發、桌面席 0 發。回放第 111 格有一筆原射擊事件，附射線且未命中。追蹤失效、恢復後持續扣住及放開的所有保存格都維持原彈匣數。玩家最終戰績與原 CSV 相符。
- 測試來源 `16a46b351054332992c58b5ccf5baea4cb5ed4ef`，測試 DLL SHA-256 `20a9140c20eb468742abc3596878994f94ecb51b3b9747dfd1b21b5121dbb3ce`。GitHub Actions job `129306543935` 因帳務或支出上限未啟動。Quest 3、VIVE、MR 場地、跨機 25 人及廠商硬體仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42659396193)

## 2026-11-10 Windows OpenXR 追蹤中斷與恢復

沿用 0.49.0 Windows 遊戲包及 0.31.51 管理包，在同機獨立房模擬雙手控制器暫時失去追蹤。OpenXR 仍提供最後的有效座標，但撤下追蹤旗標。主控只撤下受影響席位的就緒狀態，任務與桌面席持續執行。恢復後用原程序、UDP 連線、票券及名額接受位移 0.2 公尺的新頭手姿態。 [複驗方式](WINDOWS_PLAYER_PACKAGE.md#本機追蹤整合驗證)

- 伺服器封裝工具 10 項通過。原生 API 場 `run-1188069c510546d48b6a1e625d2fe962` 退出碼 0，73 項、82 格回放。控制台首輪 `run-f21617159d854092a127860010007252` 的測試誤要求四個空房有就緒欄位，載入後逾時。原失敗紀錄保留，瀏覽器和測試程序已清理。複驗依實際房卡結構核對五個房卡及唯一活動房的欄位。
- 最終 `run-545f890e4edb41a5acde78d1602723a8` 退出碼 0，78 項通過。實際控制台房 1 只顯示第 2 席姿態待確認，恢復後清除提示，並由控制台結束原場次。105 格回放逐格比對追蹤、失效、持續失效及恢復，失效觀察區間的桌面席持續可用。雙封存、兩份戰績與兩次伺服器確認相符。活動場次及剩餘程序皆為零，C／F 隔離副本 42 檔雜湊相符。
- 測試來源 `c3ffe8c594ac57b9857906575b8605f73326269f`，測試 DLL SHA-256 `3ead13e3f25e89a3ee30b91d0decdeb8fb1eac9f9d87fe380f41932b88685013`。GitHub Actions job `129303283668` 因帳務或支出上限未啟動。Quest 3、VIVE、MR 場地、跨機 25 人及廠商硬體仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42658473975)

## 2026-11-10 Windows OpenXR 追蹤入場複驗

沿用 0.49.0 Windows 玩家及伺服器包，新增可重跑的 OpenXR 整合驗證。測試 DLL 只為 Unity Mock Runtime 提供固定頭手座標，遊戲沿用原 OpenXR 輸入、簽章票券、UDP 入場、追蹤驗證及結束流程。 [複驗方式](WINDOWS_PLAYER_PACKAGE.md#本機追蹤整合驗證)

- 本機伺服器封裝測試 10 項通過。首個原生房 `run-ceb9c7e6817a49399f499fe0f7adda6d` 使用 Unity 原始模擬執行環境，兩席均入場。桌面席是 `Simulated`，OpenXR 席是 `PoseUnavailable`。等待有效追蹤逾時退出碼 1，原始資料保留，測試程序已清理。
- 使用固定座標後，原生房 `run-bcfeead236fe45c79306f9ab1a7ceed9` 69 項通過。最終逐座標複驗 `run-4bb05b00bf884848a294022728f0073d` 退出碼 0，70 項通過。OpenXR 在原連線前啟動，主控用原入場識別區分 `Tracked` 與 `Simulated`。頭部與雙手座標符合測試輸入。66 格完整回放包含該筆執行中畫面，兩份戰績、兩次伺服器確認、原 CSV 和雙封存一致。活動場次及剩餘程序均為零，C／F 隔離副本 40 檔雜湊相符。
- 本次使用 Unity OpenXR 1.19.0 附的 Mock Runtime。測試 DLL SHA-256 `7a9b14696ea33ef8025e7542a4563c3f68144345e32a797945892ceb80d740b2`。測試來源 `c4c44b9231f88ffce01e2559d5915465e238df2d`。GitHub Actions job `129299113845` 因帳務或支出上限未啟動。Quest 3 與 VIVE 實機、MR 場地、跨機 25 人及廠商硬體仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42657300164)

## 2026-11-10 Windows OpenXR 玩家啟動

Windows 玩家包 0.49.0 新增 `Launch-Player.exe --config <玩家連線檔> --launch --openxr --wait`。顯示與輸入子系統開始運作後才送出 VR 入場請求。支援的互動設定包含 Unity OpenXR Touch 和 HTC Vive Controller。 [玩家操作](WINDOWS_PLAYER_PACKAGE.md#windows-openxr-啟動)

- Unity Editor 272 項全數通過。驗證 Windows loader 只接受圖形玩家端、兩平台載入設定、官方虛擬 Vive 握把與 Menu 操作。Windows 背景程序帶 OpenXR 旗標時以退出碼 2 在入場前拒絕。實際解壓玩家包 23 項通過，含 Direct3D 11 圖形啟動對單一程序設定無效 OpenXR 執行環境。Unity 原生回報 `XR_ERROR_RUNTIME_UNAVAILABLE`，原遊戲程序退出碼 2，啟動器回報 `OpenXRUnavailable`，未送出遊戲連線。證據在 `artifacts/player-package-checks/20261110-002237-6d9e86d6`。
- Windows 與 Quest 3 共用來源指紋 `67e22a3bb22771b1b5c0bfa60420db9005015a88b995f15a7d66c104ba3dc7e3`，場景及玩家預製物網路識別一致。兩個 Windows ZIP 分別核對 330 檔。Quest 開發 APK `artifacts/quest-packages/vr-command-quest-0.49.0-arm64-debug.apk` 為 60,963,642 bytes，SHA-256 `ad996caf883c962ed8b2b489c1dbd465b1456abd45f33c2f119da83b87fd0dd2`，已核對 ARM64、OpenXR、min 32、target 35 和 APK v2 開發簽章。前版建置與日誌的 329 檔已逐檔核對 C／F 封存。
- Windows 三包 `run-a685ea02976d4b80a557a92155abbf23` 退出碼 0，457 項通過。獨立五房與合併場各 25 個同機桌面玩家，兩種模式共 50 份戰績與伺服器確認、6 份原戰績 CSV、六場雙封存及 1,482 格回放。回讀 50 份玩家及 7 份伺服器原日誌，均無 OpenXR 啟動或載入插件的記錄。第七份為終止啟動器的清理反例。活動場次與剩餘測試程序均為零。
- 功能來源 `e1d956c45398bdf5b491e7348a045ffb5770cc12`。後續提交 `01f128863717cfe32b08379a17bd76fe053b8253` 保留 Unity 結束 Android 建置後還原的專案設定，平台預載資料由建置流程各自套用。Quest 3、VIVE 確切型號與 Windows OpenXR 成功入場、MR 實地、跨機 25 人及廠商設備仍待驗收。
- GitHub Actions 兩次均因帳務或支出上限未啟動。job `129290488785` 與 `129291719085` 皆為零步驟。 [功能 CI](https://github.com/peca12968/vr-command-center/actions/runs/42654855665) · [專案設定 CI](https://github.com/peca12968/vr-command-center/actions/runs/42655197195)

## 2026-11-09 五房頭盔追蹤核對

`deploy-quest.ps1 -VerifyTrackedSeats -AllHeadsets` 用原部署 ZIP 驗證全部 25 席。沿用管理服務的入場及快照核對，報告加入每席的名冊頭盔類型。全部 25 席達到 `tracked-ready` 才回傳完成。 [操作方式](QUEST3.md#核對頭盔追蹤席位)

- Windows 單獨執行 Quest 工具 40 項與伺服器封裝工具 10 項全數通過。模擬管理快照驗證獨立五房各讀一次、合併場只讀一次，以及僅一個 VIVE 席位未追蹤就會回傳失敗。先前並行執行兩個 Quest 測試批次時，兩項部署測試遭既有互斥鎖拒絕，單獨重跑通過。
- Windows 三包 `run-6c99ffad560f45e093716d1d09b709ae` 退出碼 0，457 項通過。獨立與合併各 25 個同機 Windows 模擬玩家，兩種模式各核對 15 個 Quest 3 與 10 個 VIVE 名冊席位，均為 `Fresh` 且 `not-tracked`。六場共 1,474 格回放、50 份戰績與伺服器確認、6 份原戰績 CSV 及雙封存。活動場次及剩餘測試程序均為零。
- 原生混合場 `run-b801e1d748644bd7962600e536c1913e` 退出碼 0，117 項通過。三個 VR 房及兩個 MR 房共核對 24 個 Quest 3 和 1 個 VIVE 名冊席位。25 席均為 `Fresh` 且等待追蹤。五場在準備階段封存，共 530 格回放。兩個 MR 房的原鎖定校正檔與封存一致，活動場次及剩餘測試程序均為零。
- 原生首輪 `run-4be18e9ec9e24dcda397a54d333365e0` 退出碼 1。原 VR 啟動器使用 `Simulation` 作為原生世界來源，因此不能用來源名稱判斷頭盔追蹤。複驗沿用原逐席 `Tracked` 判定與 MR 來源檢查。
- WinForms `run-a72b0d0d81a84b7f85e2802081a8f497` 仍被 `vrcommand.exe` 的 Windows 防火牆提示遮住，停在載入管理實例前。依 computer-use 技能規則停止桌面輸入。測試逾時退出碼 1，GUI 與 API 均已清理，9 檔隔離副本的 C／F 雜湊相符。
- 功能來源 `48218ac143de320e132ac30aa1cdbb4db1d822c1`，使用遊戲 0.48.1 及管理包 0.31.51。GitHub Actions job `129086972924` 因帳務或支出上限未啟動，零步驟。Quest 3、VIVE、MR 場地、跨機 25 人及廠商設備仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42595486707)

## 2026-11-09 UDP 預檢與封存端點核對

場館驗收可選用原 UDP 監聽與探測報告，比對遊戲伺服器原綁定、埠、已收到戰績確認的玩家來源，以及綁定觀察前 30 分鐘的監聽完成時間。獨立五房逐場核對，合併場核對共用端點。 [操作方式](EXTERNAL_CLIENTS.md#將-udp-預檢納入封存驗收)

- 通過 32 項場館證據、6 項原生 UDP 探測及 10 項伺服器封裝工具測試。涵蓋錯埠、未知玩家來源、探測時間過早或過晚、缺少房間報告及重用交換摘要。
- 原生 Windows 三包 `run-3bddb75e62a34ccda6373c200a25fdef` 退出碼 0，458 項通過。獨立五組、合併一組，各三筆真實 UDP 往返，六組均與原 Unity 綁定及封存玩家來源相符。兩種模式各 25 個同機桌面玩家，共 50 份戰績與伺服器確認、1,074 幀回放及六場雙封存，活動場次和剩餘程序皆為零。另以兩房原完整探測報告對調驗證，錯配被拒絕，原清單雜湊一致。
- 功能來源 `ba08ebfa2a636cd0f923f64abaaabee35c32beab`。本輪使用 Windows 管理包 0.31.51 和遊戲 0.48.1。GitHub Actions job `129082875014` 因帳務或支出上限未啟動。頭盔、MR 場地、跨機 25 人及廠商設備仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42594228664)

## 2026-11-09 保存戰鬥事件雙向跳轉

控制台 0.31.51 加入「上一筆事件」與「下一筆事件」。暫停回放時可沿用房間、事件類型及原玩家篩選，從目前格向前或向後找最近的相符保存格。每次查詢最多 2,048 格，控制台在固定保存尾端內接續搜尋。 [操作方式](WORLD_RECORDING.md#依房間與種類搜尋戰鬥事件)

- 本機通過 981 項核心、68 項世界串流、102 項 Node、536 項 Chromium 與 106 項管理包檢查。測試核對兩個方向、原房間及玩家範圍、略過目前格、固定保存尾端與未授權讀取。
- Windows 原 900 秒合併場封存副本共 8,510 格。取一位玩家的 90 個原射擊格逐一建立比對資料。向前及向後的射擊跳轉與原始保存格相符。無受傷事件時，HTTP 各方向皆查完五段，瀏覽器同樣查完五段並停在第 8,510 格，改選射擊後跳到第 8,377 格。複驗使用 `artifacts/event-neighbor-900s/checks.json` 所載隔離副本，原六個資料庫及 WAL 檔雜湊一致。
- Windows 管理包 `artifacts/control-packages/windows-control-server-0.31.51-win-x64.zip` 為 52,744,069 bytes，SHA-256 `bf22eb267194306de7728b07a5b521a84eefc3e82338b2d72e3d275d433c1001`。已核對 528 個解壓檔及 166 個來源檔。功能來源 `7bc0bdfc8417603f75ec6866162b7d288331b10d`。GitHub Actions job `129080295835` 因帳務或支出上限未啟動。頭盔、MR 實地、跨機 25 人及廠商設備仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42593433438)

## 2026-11-09 分房觀戰角色與跟隨

控制台 0.31.50 依所選房間篩選角色清單與場景點選。玩家名稱取自該格已接受統計。跟隨目標消失時保留最後視角，等候操作員重新選取。 [觀戰操作](WORLD_RECORDING.md#操作)

- 本機 981 項核心、102 項 Node、533 項 Chromium 及 106 項解壓管理包檢查通過。瀏覽器以已接受的合併快照驗證分房名稱、玩家移除後鏡頭位置不變，以及恢復全館角色清單。
- Windows 原生整合 `run-bc8c26d275b245198451a4450418bbed` 退出碼 0，365 項通過。獨立與合併各 25 個同機桌面玩家。合併場從第 4 房房卡開始觀戰，切換第 2 房與全館，在單一原串流核對各房角色、25 個玩家名稱、跟隨解除及場次序號不變。50 份原戰績與伺服器確認、982 幀回放及六場封存核對完成，活動場次與剩餘程序為零。
- 首輪 `run-bc401d9a057145ec85fdf3ff6dd3abe9` 因驗證器拒絕任何 POST 退出碼 1，原始記錄保留。複驗限定允許唯讀 `POST /api/mission-layout`，其餘非 GET 請求仍會拒絕，並另外比對場次序號及 25 席。複驗實際只觀察到該版面預覽 POST。
- Windows 管理包 `artifacts/control-packages/windows-control-server-0.31.50-win-x64.zip` 為 52,738,906 bytes，SHA-256 `46a690a8e851dd900431f8e42d137ef97ed1af4108e57054e9c1a41b2a4d4659`。528 個解壓內容檔及 166 個發行來源檔均已核對。功能 `ca15429314ad1d0c8e8765b91d279248d39e2103`、驗證器 `e28996e9ce50e5705b3d5cd266f82ec743f5e16f`。兩次 GitHub Actions 均因帳務或支出上限未啟動。實機頭盔、MR 場地、跨機 25 人及廠商設備仍待驗收。 [功能 CI](https://github.com/peca12968/vr-command-center/actions/runs/42591623486) · [驗證器 CI](https://github.com/peca12968/vr-command-center/actions/runs/42591894638)

## 2026-11-09 VR 房卡席位提示

控制台 0.31.49 在準備中及執行中的 VR 房卡列出等待入場同步、姿態待確認及淘汰席位。依房間、入場及已觀察的管理階段核對，來源失效時撤下舊提示。 [房卡操作](PLAYER_READINESS.md#vr-房卡的席位提示)

- 本機通過 981 項核心、747 項 HTTP、65 項世界串流、102 項 Node、530 項 Chromium 及 106 項解壓管理包檢查。早期核心測試直接改生命值時被原世界驗證拒絕，後續使用已接受的傷害回報。另依原準備階段換席規則驗證待同步提示。
- 原生整合 `run-ce6eaf81968d43c08a3583ae99a1b662` 退出碼 0，376 項通過。兩種模式各啟動 25 個同機桌面玩家，第 4 房第 3 席原程序終止後，其餘 24 席持續有效。等原 UDP 連線釋放，以原票券從新程序重連，五房恢復 5／5。實際獨立模式控制台核對提示、恢復及結束。50 份戰績、原伺服器確認、2,814 幀回放與六場封存相符，活動場次及剩餘程序均為零。
- Windows 管理包 `artifacts/control-packages/windows-control-server-0.31.49-win-x64.zip` 為 52,737,796 bytes，SHA-256 `5c38a77341a93627f4724c4afd951a902cda2424f04a634880c445dfdf397019`。解壓後核對 528 個內容檔及 166 個發行來源檔。原生測試使用遊戲 0.48.1。
- 功能來源 `bbbd5307cd8920403de1e4574150b0ec2682e272`。GitHub Actions job `129069879906` 因帳務或支出上限未啟動。Quest 3、VIVE、MR 場地、跨機 25 人及廠商設備仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42590259813)

## 2026-11-09 Quest 原入場票券更新

新增 `deploy-quest.ps1 -RefreshPlayerTicket`，供同一入場用新票券按 B 重連。比對原場次、玩家、席位、端點及鎖定 MR 校正，只更新 `joinTicket`。在頭盔端核對原檔與暫存檔雜湊後替換。 [票券更新](QUEST_RECONNECT.md#保留遊戲程序並更新票券)

- Windows 的 Quest 部署套件 40 項通過。以模擬 ADB 和實際 POSIX 檔案命令核對逾期原票券、MR 與 VR 透視設定、同票券重試、錯席位、端點、校正及較早效期。原設定或暫存檔在替換前變動時會拒絕並清理自己的暫存檔。
- Windows 原生場 `20261109-165122-925d0c74` 退出碼 0，8 項入場與重連檢查、354 幀回放。待舊連線釋放後，新桌面玩家程序以同一入場恢復原位置及健康 60、彈匣 30、備彈 90。原回放與封存統計相符，活動場次和剩餘程序皆為零。另用該場實際簽發的原票券通過模擬 ADB 更新並拒絕撤銷的舊入場，原始設定檔雜湊相符。證據見同目錄 `quest-ticket-refresh-readback.json`。
- 功能來源 `743edaede5ac269b1173cdee3e67769b294a08e9`。GitHub Actions job `129066324133` 因帳務或支出上限未啟動。Quest 3 USB 更新與原程序 B 鍵重連、VIVE、MR 實地、跨機 25 人及廠商設備仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42589186598)

## 2026-11-09 Quest 五房整批日誌擷取

用原五房 VR、MR 或混合部署 ZIP 和版本 1 裝置清單並行擷取。預設完整 25 席，可選用 `--allow-partial-map` 擷取指定的 Quest 席位。逐席保存原 logcat、PID 和校驗值，失敗席位保留可用的 `.partial`，其他席位繼續擷取。 [整批操作](QUEST3.md#一次擷取五房-quest-日誌)

- Windows Python 3.12.10／PowerShell 7.6.9 通過 Quest 部署 37 項和場館驗收 30 項。25 個模擬 ADB 連線全部讀到原啟動記錄後才釋放終止戰績。另核對已過期原票券、混合五房的指定席位、錯誤入場只影響該席，以及拒絕重用原輸出路徑。
- 使用 Windows 原生場 `run-07f1951bf8e74fbeaf6e90c6832f153c` 保存的兩份 VR 部署 ZIP 與 50 份原玩家日誌。模擬 ADB 以生成的 logcat 格式讀入原 Windows 戰績標記，獨立和合併各 25 席，原入場、程序標記、戰績及輸出雜湊相符。兩份 ZIP 及 50 份原日誌校驗值維持一致。複驗摘要在 `artifacts/quest-venue-capture/windows-archive-07f1951/readback.json`。
- 功能來源 `4ffc02c8dc493b3a23256d550d18d9637fac4add`。GitHub Actions job `129063923230` 因帳務或支出上限未啟動。Quest 3／VIVE 真正裝置擷取、MR 實地、跨機 25 人與廠商設備仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42588469791)

## 2026-11-09 單房硬體模擬停止

Windows 硬體模擬器 0.2.2 加入 `--stop-file`。每個房間閘道可用自己的本機標記檔停止，等待確認的批次保留 `cancelled`，報告終止原因為 `operator-stop`。 [停止操作](HARDWARE.md#停止單房模擬閘道)

- 即時模擬 20 項通過，最終 ZIP 解壓後再通過 20 項。涵蓋既有標記、輸出同路徑、握手中、閒置及待確認批次。待確認測試核對原連線及批次 ID，該閘道確認數為零，另一房在原連線上繼續確認。離線 CLI 38 項、封裝工具 10 項及 .NET 核心 974 項通過。解壓後離線範例與原報告逐位元相同。
- Windows 原生整合 `run-8342b5268d1e413886ef02c537789e21` 退出碼 0，420 項通過。五房獨立及合併各 25 個同機桌面玩家，分別核對 108 與 105 筆模擬確認，合計 1,692 幀回放及 50 份原戰績與伺服器確認。活動場次為零，原管理、遊戲、玩家及硬體模擬程序均已清理。
- 最終包 `artifacts/hardware-packages/hardware-simulator-0.2.2-final-net10.zip` 為 182,028 bytes，SHA-256 `15e64996efb8420e89407faa707708755b84d3a75e8b5e04f041e97b1f0e13af`。八個解壓內容檔與原生整合所用初包一致，最終 manifest 指向完成附掛驗證後的測試證據。0.2.1 的 ZIP 校驗值與歷史紀錄相符。
- 功能來源 `de44f15752f5dc84e00683874bef92a8d06ead7b`。GitHub Actions job `129060167914` 因帳務或支出上限未啟動。廠商協議、實體設備輸入、輸出與停止、Quest 3、VIVE、MR 實體場地與跨機 25 人仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42587330947)

## 2026-11-09 MR 校正封存驗收

主控可選用 `--room-alignment` 或在整批 `roomAlignments` 提供部署 ZIP 的原校正檔。核對當次任務模式、`quest-room-mr-v1` 回放來源、各房鎖定 SHA-256 與原 Quest 戰績。選用後，整批每個 MR 房間都需原檔，每場都需原回放。 [校正封存](EXTERNAL_CLIENTS.md#核對-mr-校正封存)

- 場館驗收 30 項、回放分析 14 項、封裝工具 10 項及既有 .NET 核心 974 項通過。合成對戰資料覆蓋混合五房及全 MR 合併模式，也檢查重寫原檔、錯房、缺檔、錯回放來源與缺 Quest 日誌。原 Windows VR 三包的兩份 v1 摘要唯讀重驗完全一致。
- 混合 Windows 原生場 `run-e8b0163c89b1445591b37537fbcf2704` 退出碼 0，119 項通過。五間各自封存，共 496 格回放。兩間 MR 的原校正檔與封存鎖定相符，交叉送檔均被拒絕。全 MR 原生場 `run-6a9d6bb06ad64e37a3167e24f31303b1` 退出碼 0，128 項通過。合併一場及五個獨立場核對十次房間鎖定及 272 格回放。八個 MR 原生場都只到準備階段，均依預期無法通過正式對戰驗收。兩次活動場次與剩餘程序均為零。
- 功能來源 `43fc4036a48f0dcbcdd116ab3b2c14d702f8d00f`。GitHub Actions job `129056833825` 因帳務或支出上限未啟動。Quest 3、VIVE、MR 實體量測與透視、跨機 25 人及廠商設備仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42586297102)

## 2026-11-09 場館原生回放檔驗收

單場驗收可選用 `--world-journal`，五房清單可為每場提供 `worldJournal`。沿用閉源讀取器檢查每筆記錄的 SHA-256、連續影格、場次與校正設定、活動中影格、最後戰鬥序號及原世界收據。整批同時核對最後影格已觀察到該批結束指令。 [封存操作](EXTERNAL_CLIENTS.md#核對封存戰績與-udp-來源)

- 場館驗收 27 項、回放檔分析 14 項及封裝工具 10 項通過。覆蓋原來源不符、校驗碼損壞、缺最後收據、戰鬥尾界不符、只停留在準備階段、晚於最後狀態的時間及批次缺檔。原先只驗收戰績的指令仍可使用。
- 唯讀複查 `field-journal-readback-cfcf9103` 的六個原 900 秒 Windows 封存檔，51,342 格回放逐場與原 API 回放相同。首次複查將舊 `Running` 統計直接比對活動影格而失敗。原回放證明每場有一格 tick 0，改依原回放逐格核對活動定義後得到 51,073 格。原準備後結束的 MR 檔案亦按預期被活動場次條件拒絕。
- Windows 三包 `run-e93bcab4ff474112ae3ccf906cff02e3` 退出碼 0，462 項通過。獨立與合併各 25 個同機桌面玩家，六份原生回放檔共 1,659 格及 953 格活動影格。50 份戰績與伺服器確認、212 筆 AI 傷害、雙封存及整批驗收相符。活動場次與剩餘測試程序均為零。
- 功能來源 `3373a8036b33a3dacd4cba9cc7b2deeeedd7da09`。GitHub Actions job `129053981203` 因帳務或支出上限未啟動。頭盔、MR 場地、跨機 25 人及廠商設備仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42585426018)

## 2026-11-09 Quest 場館日誌持續擷取

`capture-quest-field-log.py` 由原玩家連線檔取得 UDP 埠及入場識別。遊戲啟動後開始串流指定 PID 的原 `threadtime` 日誌，保留重連，直到原入場戰績與最後斷線。寫出完整檔案前再核對 PID，並回傳 PID 及 SHA-256。擷取上限 16 MiB，失敗時保留已擷取的 `.partial`。 [現場操作](QUEST3.md#收集-quest-場館驗收日誌)

- 場館驗收測試 25 項通過，含 9 項新擷取測試。覆蓋原檔逐位元、重連後最後戰績、同埠舊入場、錯誤啟動來源、PID 更換、ADB 串流中斷、逾時、大小上限與既有檔保護。實際本機 ADB 在沒有裝置時拒絕，未建立日誌。
- `artifacts/quest-live-capture-919acb59` 用原 Windows 三包封存的 50 份玩家連線檔與 Unity 事件，分別以 25 個模擬 ADB CLI 擷取獨立及合併模式。原事件文字、入場及最終結果逐份相符，日誌檔與報告 SHA-256 一致。模擬只提供 Android 日誌外層和 ADB 串流，測試程序均退出。Quest 3 真機擷取、VIVE、MR 場地、跨機 25 人及廠商設備仍待實地驗證。
- Windows 三包 `run-7561c3bf2d4e4c8a9830f160a722d932` 退出碼 0，417 項通過。獨立和合併各 25 個同機桌面玩家。使用各原伺服器及玩家日誌，核對 50 個入場、UDP 來源、戰績及伺服器確認，並比對 6 份 CSV、910 格回放和雙封存。兩個整批驗收 ZIP 都拒絕將同機結果申報為跨機，後一批也未改動原獨立批 ZIP。活動場次和剩餘程序均為零。
- 功能來源 `2234d5091f9d25b24ced2e120fa04e3d843376cf`。GitHub Actions job `129049370742` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42584023496)

## 2026-11-09 Windows 0.48.1 雙模式長場複驗

現行 Windows 0.48.1 與管理包 0.31.48 依原門檻執行兩種 900 秒原生長場。先驗合併 25 席，再驗獨立五房各 5 席。遊戲來源指紋 `00fdc5bb2f905a08b36c85749367de91c106cd829d338cf2c3981f497c84633e`。這次沿用既有建置與測試工具。 [長場操作](DESKTOP_ENDURANCE.md#windows-0481-長場複驗)

- `20261109-151952-6c10c16e` 退出碼 0，18 項通過。每席完成 90 發射擊與 45 次換彈，所有生成器均明確收尾。原輸入活動跨度 17,947 至 18,001 tick，最長本機收集 902.532 秒。
- 合併場核對 8,510 格回放，其中 8,470 格為執行中。獨立五房分別核對 8,569／8,558／8,559／8,549／8,597 格。六場共 51,342 格完整回放、51,079 格執行中回放、50 份戰績與確認、6 份 CSV 和雙封存，沒有原生送出佇列錯誤。活動場次與剩餘程序均為零。關閉寫入後逐檔核對 SSD 與 F 槽的 174 檔副本，SHA-256 全數相同。
- 範圍為單台 Windows 的自動化桌面輸入。實機 Quest 3、VIVE、MR 場地、跨機 25 人及廠商設備仍待驗收。

## 2026-11-09 開場前 UDP 報告配對

UDP 探測工具可讀取兩端原始報告，核對互為對端的 IPv4、同一 UDP 埠、完整樣本與同次交換摘要。配對成功回報 `pair-verified`。核對時只需兩份已關閉的原始報告。 [兩端操作](EXTERNAL_CLIENTS.md#開場前核對兩端-udp)

- Windows PowerShell 5.1 與 PowerShell 7 各 6 項通過，涵蓋兩個不同 loopback 位址、BOM 報告、錯誤簽章與重送、同一埠的不同探測、逾時與埠重新綁定。首次正向測試發現測試仍持有監聽輸出檔，改在關閉後核對。另修正 5.1 將小數往返時間解析成 `Decimal` 的相容性。伺服器封裝工具另 10 項通過。
- `artifacts/lan-pair-native-a12fc24f` 以本機私有 IPv4 執行同一封裝驗證函式，五個獨立埠及一個合併埠各完成三筆往返。六份交換摘要各自不同，兩端原始報告逐組相符，六個原埠均可重新綁定。本次六埠只量測 PowerShell UDP，實際跨機與 Unity 入場另驗。
- Windows 三包 `run-93b4735ae8364d53ac4be25544f7e5f2` 退出碼 0，371 項通過。五個獨立房與合併場的六組原始探測報告均配對成功。各 Unity 子程序實際接手原埠後才公告端點。兩種模式各 25 個同機桌面玩家同時入場，六場核對 1,039 格回放、50 份戰績、50 次伺服器確認、6 份 CSV 和雙封存。活動場次及剩餘測試程序均為零。
- 功能來源 `55739448b159f4e9e53a1f8c2cec59e9ebeed58b`。GitHub Actions job `129034386539` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42579426094)

## 2026-11-09 Quest 部署後逐席追蹤核對

Quest 部署工具的 `-VerifyTrackedSeats` 可從主控電腦用原五房 VR、MR 或混合 ZIP 核對追蹤。先由管理服務驗證原連線檔，再讀同一場次的一份就緒快照，逐席比對玩家、入場、場次版本與 `Tracked` 姿態。可用裝置清單選取部分席位，核對不呼叫 ADB。 [部署後核對](QUEST3.md#核對頭盔追蹤席位)

- 35 項 PowerShell 部署工具測試通過。模擬回覆覆蓋就緒、舊入場、過期來源、尚未套用的序號、重複席位、無回覆與 MR 來源設定。合併場只讀一份快照，獨立場按原場次讀取。輸出只含房號、席位及狀態等驗收資訊。
- 首次 Windows 三包 `run-4d43de0de05446409b558b652c2b6255` 缺少專案鎖定的 Chromium，退出碼 1 並正常清理。F 槽安裝測試瀏覽器時遇到安裝鎖逾時，改用 SSD 快取並核對版本 `151.0.7922.34`。
- Windows 三包重跑 `run-90e578c3d90c4dd99a33fd8ee6068ac2` 退出碼 0，363 項通過。獨立五房與合併場各有 25 個同機 Windows 模擬玩家同時連線，兩種模式全部回報 `Fresh` 與 `not-tracked`，均未判成頭盔就緒。六場核對 50 份原戰績、50 次伺服器確認、6 份 CSV、雙封存及 1,482 格回放。活動場次及剩餘測試程序均為零。
- 混合場前兩輪 `run-296bd4ae871d4f3988cbda3b8fe41135` 和 `run-b1c18413d49b466e896336cb1bff8cfd` 在席位斷言退出碼 1。第二輪保留報告，確認工具正確略過房 1 席 2，測試將 API 從 0 起算的席位直接拿去比對操作員從 1 起算的報告。只修正測試對照並先留存報告。最終 `run-1ddfab6155f8492babe9204d2881dded` 退出碼 0，113 項通過。3 間 VR、2 間 MR 的快照新鮮，24 個 Quest 席位均等待追蹤，略過 1 個 VIVE 名額。五場共 448 格封存回放，活動場次與測試程序均已清理。
- 功能來源 `05306a0c9af5544447b0daaa072131b5a70987f9`，混合測試修正 `a839bb141886b4132a8dac6414cf4f7673d1bbfa`。兩次 GitHub Actions job `129029946316` 和 `129031121213` 因帳務或支出上限未啟動，零步驟。這次使用既有 Windows 遊戲 0.48.1 與管理包 0.31.48。實機追蹤、MR 場地、VIVE、跨機 25 人及廠商設備仍待驗證。 [功能 CI](https://github.com/peca12968/vr-command-center/actions/runs/42577992336) · [測試修正 CI](https://github.com/peca12968/vr-command-center/actions/runs/42578376188)

## 2026-11-09 XR 焦點恢復與按鍵重新啟用

遊戲 0.48.1 失去應用程式或 OpenXR 輸入焦點時停止發布本機追蹤姿態。恢復焦點後，射擊、換彈、B 重連與 MR 左扳機取點都需先放開再按下。失焦會清除尚未完成的 MR 量測。單純失焦保留已完成校正，應用程式暫停或追蹤原點改變則清除。 [操作方式](QUEST3.md#追蹤恢復後的武器輸入)

- 最終 Unity Editor 269 項全數通過，含虛擬 Touch 的持續按住、放開後再按與焦點模擬。另有 974 項核心及 10 項封裝工具檢查通過。Windows 與 Android 由來源指紋 `00fdc5bb2f905a08b36c85749367de91c106cd829d338cf2c3981f497c84633e` 建置，場景與玩家預製物網路識別相符。Quest APK 0.48.1／62 經 ARM64、OpenXR 程式庫與 APK v2 開發簽章核對。舊版建置與日誌共 338 檔逐檔核對後封存。
- Windows 玩家包與伺服器包均解壓核對 328 檔，玩家啟動器 19 項檢查通過。 [玩家包](WINDOWS_PLAYER_PACKAGE.md) · [伺服器包](WINDOWS_SERVER_PACKAGE.md)
- Windows 首輪 `20261109-144811-b561388b` 的合併 25 席通過，啟動獨立場時觸發既有 2 GiB 可用記憶體保護並退出碼 1。Quest 建置結束後依原門檻重跑 `20261109-145527-aaaeced1`，退出碼 0，19 項通過。合併一場與獨立五場各有 25 個同機模擬玩家同時入場，每席兩發、兩中、一殺，完成換彈、50 份原玩家結果與確認、6 份 CSV、雙封存及 1,932 格完整回放。測試活動場次與剩餘程序均為零。
- 解壓伺服器包 `run-7b630066d4f9489c9f078b615f35f9b9` 退出碼 0，152 項通過。五個獨立 VR 場及合併 VR 場核對 10 份原玩家結果與 CSV。獨立 MR 測試確認缺校正鎖定資料時拒絕啟動，正確鎖定後拒絕桌面玩家，缺已追蹤名冊時維持 Preparing，並封存操作員套用的夜間雷雨。七場共 552 格完整回放。另有刻意終止啟動器的反例保持未封存。測試活動場次及剩餘程序均為零。
- 使用者關閉原畫面擷取視窗後，WinForms 重試 `run-0533d07f3b4746378f13094bd7fd4108` 看見 `vrcommand.exe` 的 Windows 防火牆提示遮住啟動器。依 computer-use 技能規則停止桌面輸入。360 秒後退出碼 1，未載入管理實例或從圖形介面啟動遊戲伺服器。測試 GUI 與 API 已退出，清理無錯誤。
- 功能來源 `a2908ef5c84c262e4572046c927c8494937d625b`。GitHub Actions job `129024129873` 因帳務或支出上限未啟動，零步驟。Quest 3 真機焦點、MR 場地、VIVE、跨機 25 人及廠商硬體仍待實地驗證。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42576126265)

## 2026-11-09 五房房卡的連線端點

Windows 管理包 0.31.48 在五房房卡顯示該場遊戲伺服器公布的 IPv4 與 UDP 埠，標明合併場共用與 loopback 僅同機。主控看全館，房控僅讀本房。房卡核對房間、場次、來源及當前名冊，房間更換或回覆不符時移除舊端點。 [操作方式](EXTERNAL_CLIENTS.md#五房房卡的連線端點)

- 974 項核心、747 項 HTTP、65 項世界串流、106 項管理包、17 項封裝工具、101 項 Node 與 530 項 Chromium 檢查通過。瀏覽器核對合併場 loopback 標示、獨立端點及換場後的舊回覆，歷史場次端點保留且從房卡移除。
- Windows 原生混合場 `run-11fcf8dcff534c16927a1befcbe45de3` 退出碼 0，112 項通過。3 間 VR、2 間 MR 使用自己的 UDP 綁定，五個房控都只收到本房端點。真實解壓版 Chromium 在 390 像素寬顯示五個端點，並完成原混合 ZIP 及模擬 ADB 回歸。五個準備場共封存 498 格。
- Windows 三包 `run-07f1951bf8e74fbeaf6e90c6832f153c` 退出碼 0，352 項通過。獨立五房與合併模式的房卡分別對上五個不同綁定及同一共用綁定。兩種拓撲各 25 個同機模擬玩家同時入場，六場共核對 1,236 格回放、50 份原玩家戰績、50 次伺服器確認及 6 份 CSV。兩次原生測試均確認活動場次和剩餘程序為零。頭盔、跨機與廠商硬體仍待實機。
- 功能來源 `b0e8e402986f5dbcf61e5d30b6784fa04b08dc2d`。GitHub Actions job `129017459584` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42573983804)

## 2026-11-09 伺服器啟動器的連線來源紀錄

Windows 遊戲伺服器啟動器 1.7 加入圖形介面的來源紀錄開關，預設關閉，每場明確選用，運行中鎖定，收尾後重設。沿用 Unity 0.48.0 的伺服器來源紀錄。結果檔的 `peerDiagnosticsEnabled` 及 `workDirectory` 可核對該次啟動設定與原 `server.log`。 [操作方式](WINDOWS_SERVER_PACKAGE.md#跨機來源診斷)

- F 槽新 ZIP 解壓核對 328 個清單檔案，321 個 Unity 執行檔案與 1.6 逐檔一致。伺服器工具 10 項、場館戰績驗收 16 項及 Windows 場次清單 51 項通過，另有 46 項實際編譯的 Framework 狀態檢查。
- 三包命令列 `run-034584ef3e744e77b2dae223e074879e` 退出碼 0，388 項通過。獨立與合併各 25 個同機 Windows 模擬玩家同時入場。獨立五房的關閉設定保留至結果，原日誌無來源記錄。合併場開啟後 25 個來源端點分別與原玩家連線及伺服器戰績確認相符。六場 50 份原戰績、6 份 CSV 與 965 格完整回放核對通過。另有 MR 準備場確認校正鎖定、桌面拒絕及 22 格封存回放。活動場次與剩餘測試程序皆為零。
- WinForms `run-17ee38baf50641e1a3f6f54c69c01539` 已看見未勾選的來源選項。Windows 防火牆提示遮住視窗，依 computer-use 技能規則停止桌面輸入。360 秒後該輪退出碼 1，未載入場次或啟動遊戲子程序，測試 GUI 與 API 已退出，清理無錯誤。圖形介面勾選至實際記錄的流程、實體跨機、頭盔及廠商設備仍待驗證。
- 功能來源 `c843224615133bc454842bebf579819dd69f58ac`。GitHub Actions job `129013879678` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42572831703)

## 2026-11-09 Quest 場館戰績驗收日誌

場館驗收工具可把 Quest 3 的原始 logcat 與 Windows 玩家日誌一起核對。單場用 `--quest-player`，全館清單為 Quest 席位加上 `logcatPid`。核對同一程序的啟動、最終連線及戰績，再對照原 Quest 3 入場名額、伺服器觀察到的 UDP 來源、戰績確認及雙封存。 [擷取與核對](QUEST3.md#收集-quest-場館驗收日誌)

- 16 項場館驗收、10 項伺服器工具及 5 項 LAN 預檢測試通過。測試日誌涵蓋全連線 25 席 Quest 格式、獨立五房各一席 Quest 和四席 Windows，以及重連後使用最後一條有戰績確認的連線。其他 PID、錯誤埠、錯誤入場、來源地址及封存序號不符皆拒絕。
- 唯讀重驗 Windows 原生封存 `run-564cff2a85b14aa2b1a68a82d4ec6234`。獨立與合併各 25 席，兩份摘要均與原結果相同。50 份原 Windows 玩家標記另用合成 logcat 外框測試，保留原連線及戰績，錯 PID 全數拒絕。本機驗證摘要存於 `artifacts/quest-field-logcat-20261109/readback.json`。Quest 真機擷取、實際場館網路容量、VIVE 及廠商硬體仍待驗證。
- 功能來源 `87ea9b911dbfef7278e3bb0539a2371038a5878b`。GitHub Actions job `129011660453` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42572132563)

## 2026-11-09 混合 VR／MR 五房部署

Windows 管理包 0.31.47 可為含 VR 與 MR 的五個獨立房間一次下載部署 ZIP。主控依原場次、UDP 端點、來源及名冊配票，只有 MR 房需上傳原始校正檔。部署腳本整包核對 25 席，再依房間模式部署單席或清單。 [操作方式](QUEST3.md#混合-vr-與-mr-五房部署包)

- Windows 管理及伺服器包 `run-e5f2380d140e4bc58dfa0efba3f411aa` 退出碼 0，98 項通過。實際 3 個 VR、2 個 MR 原生 Windows 伺服器各公布 UDP 端點。控制台下載的 ZIP 通過 25 席原簽章、席位頭盔類型、兩份原始校正檔及端點核對，拒絕修改校正檔、過期來源和變更端點。
- 指定每房一席共五席，在模擬 ADB 依序核對各序號，三席 VR 使用原設定，兩席 MR 另寫入逐位元相同的校正檔並啟用透視設定。原場次資料在配票、預檢和模擬部署期間一致。五場結束後完成雙封存，逐場核對共 457 格完整回放，活動場次及剩餘程序皆為零。此輪驗證在準備階段執行，實體 Quest 3、VIVE、跨機及廠商硬體仍待驗。
- 核心 974 項、HTTP 747 項、世界串流 64 項、解壓管理包 106 項、部署腳本 34 項、伺服器工具 10 項、Node 100 項及解壓版 Chromium 527 項通過。
- 功能來源 `381c2c766c50c1ec15874778b16ec1444b99618f`。GitHub Actions job `129009132416` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42571327228)

## 2026-11-09 Quest 指定席位小批次部署

部署腳本新增 `-AllowPartialMap`，可從原五房 VR 或 MR ZIP 選擇 1 至 25 個 Quest 席位。正式部署仍核對原 25 份連線檔、名冊與端點，裝置檢查和寫入只針對清單上的序號。預設全席清單維持 25 席。管理包 0.31.46 與遊戲 0.48.0 沿用原建置。 [小批次操作](QUEST3.md#部署指定的-quest-席位)

- 33 項部署腳本與 10 項伺服器工具測試通過。涵蓋單席、空清單、重複席位或序號、未選票券失效、混合 VR 名冊、原設定與 MR 原校正檔保留，以及完整 25 席回歸。
- VR Windows 三包 `run-6b5f6a212fe842e6a2e756e38cebc7c3` 退出碼 0，346 項通過。獨立與合併各以 15 席 Quest 3、10 席 VIVE XR 的原名冊下載控制台 ZIP。兩種模式皆拒絕把 VIVE 席位加進 Quest 部署清單，並只對五個指定模擬 ADB 序號寫入原設定及請求啟動。另以每種模式 25 個同機 Windows 模擬玩家入場，六場核對 1,330 格完整回放、50 份戰績、50 次伺服器確認、6 份 CSV 及雙封存。活動場次和剩餘測試程序皆為零。
- MR Windows 管理及伺服器包 `run-94a7daef7e4d4b0b9fea8cd21e9a58f2` 退出碼 0，109 項通過。獨立與合併的原 ZIP 都通過完整 25 席及指定五席兩種模擬 ADB 測試。各模式核對原公告端點、原鎖定校正檔及設定，指定序號的校正檔逐位元一致。六個準備場共封存 536 格回放，活動場次與剩餘測試程序皆為零。
- 功能來源 `36927b7f94ff6b7e359702e5add5f91ddd2a603b`。GitHub Actions job `129004181757` 因帳務或支出上限未啟動，零步驟。Quest 3、VIVE、跨機及廠商硬體仍待實機驗證。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42569762925)

## 2026-11-09 五房逐房指定任務版本

控制台 0.31.46 可在「五房各自獨立」為每房指定保存版本，並逐房查看時間、初始環境、敵軍與平面圖。五房共用一次交易，重送取回原場次及版本分配。原共用版本入口仍可使用。 [逐房操作](MISSION_VERSIONS.md#逐房指定任務版本)

- 974 項核心、747 項 HTTP、64 項世界串流、106 項解壓管理包、18 項解壓版 Chromium 專項及 527 項完整瀏覽器檢查通過。核對不完整計畫與錯房配置的拒絕、實際 SQLite 第三筆寫入失敗整批回滾，以及重啟後原分配。瀏覽器核對 390 像素視窗、配置未通過阻擋建立，以及回覆遺失與新版本保存後的原樣重送。
- Windows 三包 `run-8f852fce23014193956fe888381c8dd8` 退出碼 0，346 項通過。五個獨立房各用不同的保存 VR 任務，遊戲錄製逐房核對 210 至 330 秒的計畫時間、天氣／日夜／雷電、2 至 6 個敵軍及各自的油桶座標與角度。獨立和合併各有 25 個同機模擬玩家同時入場。六場共核對 1,005 格完整回放、50 份戰績、50 次伺服器確認、6 份 CSV 和雙封存。活動場次為零，所有原測試程序均已退出。
- 功能來源 `d35e5536666b0b1ea63fe282302aa1a61706d33c`。GitHub Actions job `129001576670` 因帳務或支出上限未啟動，零步驟。Quest 3、VIVE、跨機及廠商硬體仍待實機驗證。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42568933364)

## 2026-11-09 保存版本的開場平面圖

控制台 0.31.45 在準備場次前可展開保存版本平面圖，核對掩體位置、旋轉、碰撞包圍盒、出生位及到中線的取樣通路。圖層沿用所選版本與模式的場地檢查，編輯草稿保持獨立。 [開場平面圖](LAYOUT.md#開場前查看保存版本平面圖)

- 968 項核心、725 項 HTTP、64 項世界串流、106 項解壓管理包及 521 項解壓版 Chromium 檢查通過。瀏覽器核對舊版及修正版、圖層與草稿隔離、錯誤版本清圖、遲到回應隔離、封閉防線及 390 像素視窗。
- Windows 同機 `20261109-132908-75fd3f6a` 的 Chromium 與原生工具都以退出碼 0 結束。從解壓管理包選歷史第 1 版，沙包未儲存的位移留在草稿。平面圖的兩個物件、五個出生位和五條路徑與原版檢查一致。透過實際控制台建立及開始五房合併場次，每房一個模擬玩家。遊戲來源的 10 個物件與原保存座標和角度一致。雨夜、雷電和各房初始敵軍 2／2／1／1／1 已核對，封存 91 格、五份玩家戰績已確認送達，活動場次與剩餘程序皆為零。
- Windows 管理及伺服器包 `run-74f7e304784b44f4b74612f786a29169` 退出碼 0，136 項通過。五房獨立及合併各每房一個同機模擬玩家，核對六場原保存沙包位置和中線缺口、536 格完整封存回放與 10 份原玩家戰績。測試後活動場次歸零，原管理、伺服器與玩家程序均退出。
- 功能來源 `7b5cc66117efd6e6289d8adfa25553b8e223f01e`。GitHub Actions job `128997959491` 因帳務或支出上限未啟動，零步驟。Quest 3、VIVE、跨機及廠商硬體仍待實機驗證。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42567771797)

## 2026-11-09 從戰績開啟個人回放

控制台 0.31.44 在雙封存後可從「任務統計」選擇玩家。開啟時核對原場次及戰鬥與世界封存序號，停在最後一格並搜尋該玩家的事件。選單含已離場的玩家，依玩家 ID 歸屬事件。 [戰後檢討](REPORTS.md#從戰績開啟個人回放)

- 968 項核心、725 項 HTTP、64 項世界串流、22 項短場工具測試、106 項解壓管理包與 514 項解壓版 Chromium 檢查通過。瀏覽器核對未封存及封存序號不符時拒絕開啟、正常封存的原序號跳轉、個人事件筆數與清除篩選。
- Windows 同機原生 `20261109-131846-924cdd5e` 退出碼 0，25 項通過。五房合併與五房獨立各有 25 個同時連線的模擬玩家。六場共 2,044 格封存回放，核對 50 組個人搜尋的 160 頁、100 筆射擊及各玩家的最終彈藥統計。每位玩家兩發兩中、一擊殺。原 50 份戰績、50 次伺服器確認和雙封存均通過。活動場次為零，原測試程序均退出。
- 功能來源 `8d30515bb7a359e3adb1b160c07a2813b144b018`。GitHub Actions job `128994921718` 因帳務或支出上限未啟動，零步驟。Quest 3、VIVE、跨機及廠商硬體仍待實機驗證。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42566796111)

## 2026-11-09 任務回放戰鬥事件搜尋

控制台 0.31.43 在回放暫停後可依房間和事件種類搜尋，從結果直接跳到原始保存格。未封存片段沿用原本固定的保存尾端，既有錄製可直接搜尋。 [回放操作](WORLD_RECORDING.md#依房間與種類搜尋戰鬥事件)

- 968 項核心、725 項 HTTP、62 項世界串流、22 項短場驗證工具測試、106 項解壓管理包、100 項 Node 與 509 項解壓版 Chromium 檢查通過。瀏覽器用保存的玩家受傷事件驗證搜尋、原序號跳格和篩選切換，並核對未封存片段的搜尋請求。
- Windows 同機原生 `20261109-130941-2954c691` 退出碼 0，24 項通過。五房合併和五房獨立各有 25 個同時連線的模擬玩家。以 1,981 格完整保存回放核對 10 組房間搜尋、32 頁與 100 筆射擊，其中 7 頁無相符格但仍有後續游標。六場各有雙封存，核對 50 份戰績及伺服器確認與 6 份 CSV。活動場次歸零，原測試程序全數退出。
- 功能來源 `f540d6873818cbf0889f0adad7e004bdcf3c77d3`。GitHub Actions job `128992200308` 因帳務或支出上限未啟動，零步驟。Quest 3、VIVE、跨機及廠商硬體仍待實機驗證。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42565893105)

## 2026-11-09 Quest 直接部署 VR 五房 ZIP

Quest 部署工具可直接讀取管理台原始 VR 五房配票 ZIP，預檢 25 席、選定單席或依裝置清單部署。管理包 0.31.42 從同一場館快照核對票券、名冊與公布端點。寫入前核對目標席位的 Quest 3 登記，整批部署須 25 席均相符。 [部署操作](QUEST3.md#直接使用-vr-五房連線-zip)

- 968 項核心、725 項 HTTP、58 項世界串流、31 項 Quest 部署、106 項解壓管理包、100 項 Node 與 506 項完整 Chromium 檢查通過。建置版和解壓版各通過 20 項 Chromium 專項，包含兩種模式的原始簽發檔、VIVE 與 Quest 席位標記、改寫端點及替換入場的拒絕。首輪部署回歸因 MR ZIP 多餘檔案的提示文字變更而失敗，修正後重跑。
- VR 原生 `run-564cff2a85b14aa2b1a68a82d4ec6234` 通過 422 項，退出碼 0。獨立與合併各從實際主控台下載整批 ZIP，經原管理服務核對並對 25 台模擬 ADB 裝置逐席寫入四欄設定及請求啟動。同一批原檔亦供同機 Windows 遊戲入場，每種模式 25 個同時連線的模擬玩家，六場核對 50 份戰績及伺服器確認、1,343 幀雙封存回放。
- MR 原生回歸 `run-a4734586b7c5435aade4d08b38b24364` 通過 103 項，退出碼 0。獨立與合併各有 25 台模擬 ADB 裝置通過部署，原校正檔與設定依序號核對，六個準備場封存 498 幀回放。兩次原生測試皆無活動場次或剩餘測試程序。Quest 3、VIVE、跨機與廠商硬體待實機驗證。
- 功能來源 `f6f6ed7bb6b52ebaf631ac1809977ad4788aab44`。GitHub Actions job `128988959115` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42564824993)

## 2026-11-09 VR 五房配票

Windows 管理包 0.31.41 可在五房總覽預覽 VR 名冊、任務及遊戲來源端點，再一次下載五個分房 ZIP。獨立與合併皆核對現行五房各五席、原場次及原公布來源。 [操作方式](EXTERNAL_CLIENTS.md#vr-五房配票)

- 968 項核心、725 項 HTTP、58 項世界串流、106 項解壓管理包、100 項 Node 與 502 項完整 Chromium 檢查通過。建置版與解壓版各通過 16 項 Chromium 專項，涵蓋主控權限、少一席、未公告、獨立端點重複、舊來源、房間重用、席位替換、離頁晚回應及 50 份實際簽發票券的逐席核對。
- 同機 Windows 原生 `run-94dcc7d96ae442beb4d1edc59cd69f13` 退出碼 0，通過 438 項。0.31.41 解壓管理包分別從實際畫面下載兩份整館 ZIP，啟動器 1.2 使用各席原始 JSON 開啟 Unity 0.48.0 玩家。獨立與合併各有 25 個同時連線的模擬玩家。六場共核對 1,815 幀回放、50 份戰績和伺服器確認、11 份 CSV 及雙封存。活動場次為零，測試程序已退出。跨機、Quest 3、VIVE 與廠商硬體待實機驗證。
- 功能來源 `72e498d064758ab7404e58b5f2f39b4ceada08e6`。GitHub Actions job `128985837706` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42563818673)

## 2026-11-09 Windows 玩家席位與票券效期

玩家啟動器 1.2 顯示連線檔標示的房間、席位與本機效期。更換路徑會清除舊提示，遊戲開始後保留房間與席位。遊戲伺服器驗證入場。 [玩家操作](PLAYER_CONFIG_REVIEW.md#連線檔席位與效期)

- 36 項實際 .NET Framework 連線檔檢查、17 項遊戲狀態檢查及 19 項解壓玩家包檢查通過。新包 328 個清單檔案中，326 個與 0.48.0 原包雜湊一致。首個 Python 驅動仍預期 24 項而失敗，更新測試計數後通過。
- 首輪 `20261109-123602-acfb751d` 的 Windows UI 自動化把 WinForms 路徑欄當成一般容器，退出碼 1，當時未啟動玩家。修正為只辨識並操作自有程序的原生控制項後，`20261109-123824-f1a85098` 的測試與伺服器工具均退出碼 0。10 項驗證涵蓋實際視窗的過期測試檔、改路徑清除、有效簽發檔的第 3 房第 1 席及倒數、兩名同機原生玩家入場、Begin、Pause、兩份原戰績和雙封存的 136 幀回放。測試程序均已退出。跨機、Quest 3、VIVE 與廠商硬體待實機驗證。
- 功能來源 `8329a441392617217d19f4aaf84f6ed2fe9359e8`。GitHub Actions job `128983302503` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42562998575)

## 2026-11-09 遊戲開場前 UDP 探測

新增 PowerShell 工具 `scripts/check-lan-udp.ps1`。兩端以實際 IPv4、規劃的遊戲 UDP 埠及一次性探測金鑰交換封包。監聽結束後釋放原埠，讓遊戲伺服器接手。工具逐筆保存往返時間或逾時，供場館分開檢查網路與遊戲入場。 [兩端操作](EXTERNAL_CLIENTS.md#開場前核對兩端-udp)

- Windows PowerShell 5.1.26100.9711 與 PowerShell 7.6.9 各通過 5 項程序測試。測試涵蓋原埠互斥及重新綁定、已存在金鑰、錯誤驗證碼、重送、不同來源位址與來源埠，以及逾時。另通過 10 項伺服器包與 12 項封存核對測試。
- 同機 Windows 原生 `run-7379e633e2a444329f3a6f358dcd2efc` 退出碼 0，通過 456 項。以同一台電腦的乙太網路 IPv4，先測五個獨立房及一個合併場的原定遊戲埠，共 18 筆有效往返。每次等 PowerShell 監聽程序退出，再由 Windows UDP 端點表核對原 Unity 子程序持有相同位址與埠。兩種模式各 25 個同時連線的模擬玩家，六場核對 1,605 幀回放、50 份戰績與伺服器確認、11 份 CSV。活動場次為零，測試程序均已退出。第二台電腦、實際網路容量、頭盔與廠商硬體另待驗證。
- 功能來源 `f470c170ae6aa3f968ddb1cd22420927f2b67f2a`。GitHub Actions job `128980539190` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42562094069)

## 2026-11-09 整批場館驗收 ZIP

Windows 管理包 0.31.40 可從全館收尾一次下載指定批次的明細及各原場次的場館驗收 ZIP。五房獨立依房號存放，五房合併使用一份內層 ZIP。各場資料可直接供五房離線核對工具讀取。 [下載及驗收操作](SESSION_CLOSURE.md#下載本批場館驗收)

- 968 項核心、725 項 HTTP、58 項世界串流、12 項場館核對、10 項伺服器包、106 項解壓管理包、100 項 Node 與 489 項完整 Chromium 檢查通過。建置版與解壓版各通過 54 項 Chromium 專項，涵蓋未公布端點時拒絕、主控權限、正確歷史批次、內外層資料一致，以及延遲下載在批次切換後失效。
- 同機 Windows 原生 `run-47226659c0ba4d639e04c9f9a4b42d2a` 退出碼 0，通過 446 項。獨立與合併兩種模式各 25 個同時連線的模擬玩家，六場共核對 1,577 幀回放、50 份原戰績與伺服器確認及 11 份 CSV。實際管理台下載本批與歷史批次，六份內層 ZIP 逐位元組對上單場原檔。合併場結束後再次下載獨立整批 ZIP，位元組一致。從整批 ZIP 取出的資料已配合原生日誌通過離線核對。活動場次為零，測試程序均已退出。跨機、Quest 3、VIVE 與廠商硬體待實機驗證。
- 功能來源 `cbbe0165f52abfd0c732f4dc7d81686ec150241f`。GitHub Actions job `128977273341` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42561034836)

## 2026-11-09 五房 25 席場館驗收核對

`scripts/verify-field-results.py --venue-manifest` 讀取選定的全館結束批次、各場原始管理 ZIP、啟動器終止報告及遊戲日誌。五房獨立與五房合併均核對各房五席、原入場、UDP 來源、戰績及伺服器確認。摘要逐房列出來源位址落在伺服器清單以外的玩家數。 [場館驗收操作](EXTERNAL_CLIENTS.md#一次核對五房-25-席)

- 12 項場館核對、10 項伺服器包及 10 項解壓管理包 Chromium 專項通過。涵蓋缺房、混入其他場次、重複席位、日誌重用、封存尾端不符及同機資料拒絕標成直連跨機。
- 首輪原生 `run-045a4cbb17b34f6fa9c48de1bcaaabe4` 已核對獨立 25 席並拒絕重標跨機。測試腳本在保存交付紀錄時因變數作用域中止，退出碼 1，清理完成。修正後以新執行目錄重跑。
- 最終原生 `run-1aa2d348217e466eb41038cdf4465cd4` 退出碼 0，通過 439 項。解壓 Windows 管理包 0.31.39 與遊戲 0.48.0 在同一台電腦執行。兩種模式各 25 個同時連線的模擬玩家，逐房各五席，六份管理 ZIP 與管理 API 原資料逐欄相符。六場共核對 1,549 幀回放、50 份原玩家戰績、50 筆伺服器確認及 11 份 CSV。兩份原始資料均拒絕以直連跨機模式驗收。活動場次為零，測試程序均已退出。跨機容量、Quest 3、VIVE 與廠商硬體待實機驗證。
- 功能來源 `30e425a9da0216139206c46837e80da12bf286f4`。GitHub Actions job `128974610778` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42560162635)

## 2026-11-09 全館收尾歷史

Windows 管理包 0.31.39 在全館收尾加入分頁清單。主控可指定較早的批次，從原場次查看封存、開啟回放及下載戰績。選取後，新批次結束時仍顯示指定的歷史批次。 [操作方式](SESSION_CLOSURE.md#歷史批次)

- 968 項核心、725 項 HTTP、58 項世界串流、100 項 Node、484 項完整 Chromium、兩次各 49 項 Chromium 專項及 106 項解壓管理包檢查通過。涵蓋 21 批分頁、房控權限、SQLite 重啟後還原、選取保留，以及回放與 ZIP 對上原批次。
- 搭配解壓 Windows 遊戲 0.48.0 通過 434 項同機原生檢查，獨立與合併兩種模式各有 25 個同時連線的模擬玩家。較新的合併批次結束後，主控從歷史清單開啟獨立批次第 3 房的原錄製，核對原錄製尾端第 324 格，下載的 ZIP 與原檔逐位元組一致。六場共核對 1,949 幀回放、50 份原玩家戰績、11 份 CSV 及雙封存。活動場次為零，測試程序均已退出。原生證據在 `artifacts/server-package-checks/run-f81955cb147b46e4bb82e219f43a4808`。Quest 3、VIVE、跨機與廠商硬體待實機驗證。
- 功能來源 `974bbe88d25fd4d429fda8962d38e6673b7c9d71`。GitHub Actions job `128971263619` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42559077055)

## 2026-11-09 房卡觀戰與全館原場次回放

Windows 管理包 0.31.38 讓房卡直接開啟本房即時俯視觀戰。全館收尾依原場次及錄製來源開啟回放，未封存片段以收尾表確認的尾端為播放界線。 [操作方式](WORLD_RECORDING.md#從房卡或全館收尾開啟)

- 963 項核心、725 項 HTTP、58 項世界串流及 43 項 Chromium 專項通過。涵蓋本房視角、房間重用、精確片段界線、原錄製不在清單時保留未選取，以及無錄製房間的操作狀態。
- 100 項 Node、478 項完整 Chromium、解壓包 43 項 Chromium 專項及 106 項管理包檢查通過。
- 搭配解壓 Windows 遊戲 0.48.0 通過 433 項同機原生檢查。兩種模式各有 25 個同時連線的模擬玩家。實際管理台從收尾表開啟五個獨立錄製及一個五房合併錄製，逐場核對來源、第一格播放請求、房間視角與封存尾端。六場共核對 1,829 幀回放、50 份原玩家戰績、11 份 CSV 及雙封存。活動場次為零，測試程序均已退出。Quest 3、VIVE、跨機與廠商硬體待實機驗證。
- 功能來源 `68c05acb2c0c81e2880ceda55caa30c8e28b419e`。GitHub Actions job `128968096020` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42558050459)

## 2026-11-09 全館結束批次戰績 ZIP

Windows 管理包 0.31.37 在全館收尾提供「下載本批戰績 ZIP」。批次內原場次的最終戰鬥報表全數可匯出時，ZIP 會包含各房 CSV 與原場次清單。 [報表操作](REPORTS.md#下載全館結束批次)

- 963 項核心、725 項 HTTP、58 項世界串流及 38 項 Chromium 專項通過。涵蓋原批次授權、部分戰鬥未封存、世界回放仍待封存時匯出、SQLite 重啟後讀取、房間重用、新批次及舊 ZIP 位元組一致。
- 100 項 Node、473 項完整 Chromium、解壓包 38 項 Chromium 專項及 106 項管理包檢查通過。瀏覽器下載的測試 ZIP 含三份原場次報表，其中一份保留未連接戰鬥來源的空場資料列。
- 搭配解壓 Windows 遊戲 0.48.0 通過 429 項同機原生檢查。獨立與合併各有 25 個同時連線的模擬玩家。獨立 ZIP 含五份分房 CSV，合併 ZIP 含全場及五份分房 CSV。兩個清單對上各場原結束序號，所有 CSV 逐位元組對上直接下載，並核對 50 份原玩家戰績。新合併批次成立後，原獨立 ZIP 再下載仍逐位元組一致。六場共 1,898 幀回放與雙封存，活動場次為零，測試程序皆已退出。Quest 3、VIVE、跨機及廠商硬體待實機驗證。
- 功能來源 `88adc675410f24f498d98a8889f4c121bb12c981`。GitHub Actions job `128964985134` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42557039331)

## 2026-11-09 全館敵軍策略

Windows 管理包 0.31.36 讓主控一次調整執行中場次的攻擊方式與自動攻擊。各場保留自己的敵軍目標數，房卡依原命令序號與有效遊戲快照確認。 [操作方式](LAYOUT.md#全館敵軍策略)

- 959 項核心、725 項 HTTP、58 項世界串流及 33 項 Chromium 專項通過。涵蓋不同敵軍目標數、單房改寫使舊預覽失效、重啟後重送、送出前確認及遊戲端逐房套用。首次瀏覽器專項在測試讀取無回應內容的 HTTP 400 時失敗，改驗證狀態碼後重跑通過。
- 100 項 Node、468 項完整 Chromium、解壓包 33 項 Chromium 專項及 106 項管理包檢查通過。
- 搭配解壓 Windows 遊戲 0.48.0 通過 414 項同機原生檢查。五房獨立與合併各有 25 個同時連線的模擬玩家。每種模式先全館守備並開啟自動攻擊，再切到推進並關閉自動攻擊，原目標數保留。兩種模式各有 105 筆傷害，所有原玩家均受傷，傷害只出現在各場自動攻擊開啟期間。12 個策略確認快照對上封存回放。六場共核對 1,908 幀回放、50 份玩家戰績、11 份 CSV 及雙封存。活動場次為零，測試程序均已退出。Quest 3、VIVE、跨機與廠商硬體待實機驗證。
- 功能來源 `f91ff0d15d1882452dd5224a01702ac8d5a09307`。GitHub Actions job `128961537977` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42555945107)

## 2026-11-09 全館即時環境

Windows 管理包 0.31.35 讓主控一次設定執行中場次的天氣、日夜與閃電。管理端核對目標的階段與環境序號，房卡依各場有效快照確認套用。 [操作方式](ENVIRONMENT.md#全館即時環境)

- 954 項核心、725 項 HTTP、58 項世界串流及 29 項 Chromium 專項通過。覆蓋 VR／MR 模式保留、單房環境改寫造成舊預覽失效、SQLite 重啟後重送、過期快照及逐房確認。初次建置找到五房準備路徑漏帶環境初始序號，補齊後重新建置通過。
- 100 項 Node、464 項完整 Chromium、解壓包 29 項 Chromium 專項、106 項管理包及原雨雷素材位元組檢查通過。
- 搭配解壓 Windows 遊戲 0.48.0 通過 388 項同機原生檢查。五房獨立與合併各有 25 個同時連線的模擬玩家，均由暴風雨夜開啟閃電切換到晴朗白天關閉閃電。12 個遊戲端確認封包與同場封存回放逐欄一致。六場共核對 1,276 幀回放、50 份玩家戰績、11 份 CSV 及雙封存。活動場次為零，測試程序已退出。Quest 3、VIVE、跨機與廠商硬體待實機驗證。
- 功能來源 `0336bf900fb20923dab523674651c1b56d60b0c7`。GitHub Actions job `128957881664` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42554756144)

## 2026-11-09 全館批次結束與封存總覽

Windows 管理包 0.31.34 讓主控確認房號後一次結束所有未結束的場次。最近一次全館收尾逐場顯示戰鬥統計與世界回放封存，並可開啟原場次。 [操作方式](SESSION_CLOSURE.md#全館批次結束)

- 948 項核心、725 項 HTTP、58 項世界串流與 25 項 Chromium 專項通過。覆蓋第二筆寫入失敗的 SQLite 回滾、過期預覽、取消操作、遺失回覆與重啟後重送、戰鬥與世界分開封存，以及房間重用後仍可開啟原紀錄。
- 100 項 Node、460 項完整 Chromium、解壓包 25 項 Chromium 專項及 106 項管理包檢查通過。
- 搭配解壓的 Windows 遊戲 0.48.0 通過 380 項同機原生檢查。五房獨立與合併各有 25 個同時連線的模擬玩家，分別用一批五筆及一批一筆的結束命令。收尾總覽對上各原場次序號及戰鬥、世界雙封存，兩種模式重送都取得原回條。六場核對 1,080 幀回放、50 份原玩家戰績與 11 份 CSV。活動場次為零，所有測試程序已退出。Quest 3、VIVE、跨機與廠商硬體待實機驗證。
- 功能來源 `3672d3989f9a82a7d37bb6a31f9fe0930d090455`。GitHub Actions job `128954542247` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42553671302)

## 2026-11-09 全館批次開始

Windows 管理包 0.31.33 讓主控一次開始當前所有準備場次。各目標須有名冊與當前序號的有效準備快照，VR 要求有效姿態，MR 要求 Quest 3 追蹤就緒。提交後房卡等待同場遊戲來源回傳執行中快照。 [操作方式](MISSION_CLOCK.md#全館開始)

- 941 項核心、725 項 HTTP、58 項世界串流及 18 項 Chromium 專項通過。涵蓋批次中的缺席、準備中名冊變更、過期 MR 快照、SQLite 重啟後重送及逐房開始確認。首次核心測試的重啟斷言漏查已結束場次，修正篩選後通過。HTTP 精確欄位檢查已加入準備中的 `venueBeginReady`。
- 100 項 Node、453 項完整 Chromium、解壓包 18 項 Chromium 專項及 106 項管理包檢查通過。
- 搭配解壓的 Windows 遊戲 0.48.0 通過 372 項同機原生檢查。兩種模式各有 25 個同時連線的模擬玩家。獨立場一次保存五個開始序號，各房回傳自己的快照。合併場只保存一個開始序號，五房共用同一個快照。兩種模式的晚到重送均取回原回條。六場共核對 1,100 幀回放、50 份戰績、11 份 CSV、戰鬥及世界雙封存。活動場次為零，測試程序已退出。Quest 3、VIVE、跨機及廠商硬體待實機驗證。
- 功能來源 `34abbfabada4dc21f7f10f248421f32ea1cb5b74`。GitHub Actions job `128951508081` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42552680211)

## 2026-11-09 全館命令的遊戲端確認

Windows 管理包 0.31.32 依各場遊戲端回傳的有效快照，在房卡顯示全館暫停或繼續的待確認與已套用狀態。全館繼續須等每個目標確認目前的暫停階段。VR 與 MR 都使用原有 1.5 秒快照有效窗，MR 另須通過當前追蹤檢查。 [全館操作](MISSION_CLOCK.md#全館暫停與繼續)

- 933 項核心、725 項 HTTP、58 項世界串流、100 項 Node、449 項完整 Chromium、解壓包 14 項 Chromium 專項及 106 項管理包檢查通過。涵蓋回覆遺失、晚到或過期快照、VR 與 MR 繼續限制、合併來源與個別房間操作隔離。
- 使用解壓管理包及 Windows 遊戲 0.48.0 通過 366 項同機原生檢查。五個獨立場與五房合併各有 25 個同時連線的模擬玩家。獨立場四個目標確認對應的暫停與繼續序號，房間 2 保留個別暫停。合併場五房共用同一筆暫停確認及同一筆繼續確認。六場共核對 1,194 幀回放、50 份戰績、11 份 CSV 及雙封存。活動場次為零，測試程序全部退出。Quest 3、VIVE、跨機與廠商硬體待實機驗證。
- 功能來源 `25ee02497bcf9ef60a1e522e951d29c5396124e5`。GitHub Actions job `128948108919` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42551574563)

## 2026-11-09 全館暫停與繼續

Windows 管理包 0.31.31 可由主控一次暫停預覽中的執行中場次。繼續只涵蓋仍處於全館暫停階段的場次。目標階段已變或任一 MR 場的追蹤尚未就緒時，整批拒絕。回覆遺失或管理服務重啟後，可用原請求取回同一份回條。 [全館操作](MISSION_CLOCK.md#全館暫停與繼續)

- 923 項核心、725 項 HTTP、58 項世界串流、99 項 Node、445 項完整 Chromium、解壓包 10 項 Chromium 專項及 106 項管理包檢查通過。驗證 SQLite 第二筆寫入失敗的完整回滾、同鍵並行重送、重啟重建原回條、過期預覽、個別暫停隔離及 MR 追蹤就緒。合併場五個房間只寫入一個場次命令。
- 以解壓管理包及 Windows 遊戲 0.48.0 通過 366 項同機原生檢查，合併及獨立模式各有 25 個同時連線的模擬玩家。獨立場四個目標收到批次暫停與繼續，房間 2 的個別暫停與活動時間維持不變。合併場各用一個命令同步五房；兩種模式的晚到暫停重送都取回原回條。六場共核對 1,140 幀回放、50 份戰績、11 份 CSV 及雙封存，活動場次為零且測試程序退出。實體頭盔、跨機與廠商硬體待驗。
- 功能來源 `82afb954208521b4f1959f0b979d6a8c4fd44bbf`。GitHub Actions job `128944659248` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42550465179)

## 2026-11-09 五房房卡任務計時

Windows 管理包 0.31.30 在「房間與場次」總覽顯示活動時間或自動結束倒數。五房合併共用同一快照，五個獨立場各顯示自己的時間與政策。控制台會清除過期或階段未同步的時間。房控只讀取本房。 [房卡操作](MISSION_CLOCK.md#五房房卡)

- 903 項核心、725 項 HTTP、58 項世界串流、99 項 Node、438 項完整 Chromium、解壓包 9 項 Chromium 專項與 106 項管理包檢查通過。測試涵蓋暫停又立即繼續、階段序號由原事件歷史重建、暫停時間不變、其他房間繼續與房控範圍。
- 用解壓管理包、Windows 伺服器與玩家 0.48.0 通過 360 項同機原生檢查。兩種拓撲各有 25 個同時連線的模擬玩家。獨立場房間 1 暫停在 5 秒，房間 2 從 5 秒前進到 6 秒，房間 1 恢復後才前進。合併場五個房卡來源暫停在同一個 3 秒，恢復後一同前進。六場共核對 1,037 幀回放、50 份戰績、11 份 CSV 及雙封存，活動場次為零，測試程序已退出。頭盔、跨機及廠商硬體待實機驗收。
- 功能來源 `cdc9a1ddb89829554de358ac46d8fecf40ce2eee`。GitHub Actions job `128940360674` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42549072359)

## 2026-11-09 Quest 3 裝置清單與 25 席批次部署

Quest 部署工具可用 `-DeviceMap` 把 25 席對應到唯一的 ADB 裝置序號。預檢確認連線授權、Quest 3 型號及啟用的 APK 版本。`-DeployMappedSeats` 要求線上核對 25 張票券、現行名冊、校正原檔及各場端點，再依房號及席位順序套用設定並請求啟動。批次使用預先安裝的 APK，若中途出錯會停止，逐席回報已請求啟動、失敗與未嘗試。 [操作方式](QUEST3.md#用裝置清單部署-25-席)

- 本機 Android 工具核對現有 Quest APK 為 `com.vrcommand.quest` 0.48.0／版本代碼 61。模擬 ADB 驗證無效清單、缺席、未授權、離線、型號／版本錯誤及第四席設定啟用失敗。失敗席保留原設定，後 21 席無裝置寫入。
- 28 項 PowerShell 部署、10 項伺服器包及解壓包 9 項 Chromium 專項通過。首次把部署回歸和原生排演並行時，主機部署鎖拒絕其中一個單席寫入。保存該次失敗輸出，原生程序退出後單獨重跑，28 項全部通過。
- 使用解壓管理包 0.31.29 與 Windows 遊戲 0.48.0 通過 103 項原生檢查。合併及獨立模式各由原生伺服器公布端點，再將實際簽發的 25 份設定與校正原檔逐席核對到模擬 ADB 裝置。兩種模式各確認 25 個啟動請求，未向其他裝置寫入。六個 MR 準備場完成雙封存、476 幀回放，活動場次為零，測試程序全部退出。實際頭盔部署、入場、跨機、VIVE 與廠商設備待驗。
- 功能來源 `57cacd68ac21b541b9636bdd7ebc7e1da0b509d5`。GitHub Actions job `128937540043` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42548148669)

## 2026-11-09 直接從五房 ZIP 部署 Quest 席位

Quest 部署工具可直接讀取管理包 0.31.29 匯出的 `quest-mr-venue.zip`。可預檢五房 25 席，也可指定房號與席位預檢或部署。正式部署須提供裝置序號，沿用原 Quest 3 型號檢查與檔案啟用流程。選用管理服務時，先核對簽章、名冊、校正檔及各場目前公布的端點。 [操作方式](QUEST3.md#直接用-zip-預檢或部署單席)

- 25 項 PowerShell 測試、10 項伺服器包測試及解壓管理包的 9 項 Chromium 專項通過。合併與獨立 ZIP 的直接預檢結果與舊清單流程一致。模擬 ADB 驗證只寫入指定席位與原始校正位元組，且端點、校正檔或 ZIP 結構不符時在裝置操作前停止。
- 解壓管理包 0.31.29 與 Windows 遊戲 0.48.0 通過 97 項同機原生檢查。合併場及五個獨立場各以 25 份實際簽發票券直接從 ZIP 完成線上預檢，並各自確認第 4 房第 2 席及原始校正雜湊。六個 MR 準備場完成雙封存及 286 幀回放，活動場次為零，所有測試程序已退出。原生驗證使用合成校正量測及 Windows 端點，Quest 3 裝置安裝、VIVE、跨機及廠商硬體待驗。
- 功能來源 `ebe5d846f811d188b78593c8c956f280a1b3ee1c`。GitHub Actions job `128935192017` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42547379596)

## 2026-11-09 Quest 3 MR 五房部署包

Windows 管理包 0.31.29 可一次產生 Quest 3 MR 五房部署包。主控選擇五份鎖定的原始校正檔後，服務以伺服器已公布的端點及當前名冊建立五房 ZIP、保留校正原檔，並附現有 PowerShell 預檢可直接使用的 `venue.json`。五房合併與五個獨立場皆支援，服務在全部驗證完成後才交付 ZIP。 [部署操作](QUEST3.md#從主控台下載五房部署包)

- 892 項核心、725 項 HTTP、58 項世界串流、97 項 Node、432 項完整 Chromium，以及解壓包 9 項 Chromium 專項和 106 項管理包檢查通過。兩種模式的 25 份檔案均經既有 PowerShell 預檢及管理服務核對。另驗證房控權限、未公布端點、原檔重排及入場重配。
- 使用解壓管理包與既有 Windows 遊戲 0.48.0、伺服器啟動器 1.6，通過 95 項原生檢查。合併模式由一個實際遊戲程序公布端點，獨立模式由五個程序各公布自己的端點。每種模式的 25 席都通過 PowerShell 線上預檢，並逐房對上原校正檔雜湊及 Windows UDP 綁定。六個 MR 準備場完成雙封存、287 幀回放，活動場次為零，所有測試程序均已退出。測試使用合成校正資料，未連接頭盔，實際場地量測、跨機及廠商設備待驗。
- 功能來源 `1f4ff7f53ed691f7426bea3aa571da02a1ee3c6c`。GitHub Actions job `128932578975` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42546517393)

## 2026-11-09 五房獨立場次一次準備

主控可在 Windows 管理包 0.31.28 選擇「五房各自獨立」，從同一個已保存的 VR 或 MR 任務版本一次建立五個準備場次。任一房被占用就回報房號，五場都不會建立。每房有獨立的場次 ID、名冊與開場控制。 [操作方式](MISSION_VERSIONS.md#五房各自獨立)

- 892 項核心、725 項 HTTP、58 項世界串流、97 項 Node、426 項完整 Chromium、12 項解壓包 Chromium 專項及 106 項 Windows 管理包檢查通過。驗證 SQLite 第三筆寫入故障的整批回滾、兩個請求競爭、重啟後取回原五場、歷史場次與新場次分離、瀏覽器回覆遺失後以原請求確認，以及房控結束本房後其他四房仍在準備。
- 使用解壓的管理包 0.31.28、伺服器啟動器 1.6 及 Windows 玩家 0.48.0，通過 378 項同機原生檢查。五房獨立共用同一任務版本並沿用批次回傳的五個 ID，隨後另跑五房合併。兩種模式各有 25 個同時連線的 Unity 玩家程序，均逐席核對原生傷害。六場共完成 1,683 幀回放、50 份原玩家戰績、11 份 CSV 及雙封存。活動場次為零，測試程序皆已退出。原生排演使用 VR 的桌面模擬，Quest 3、VIVE、場館跨機及廠商設備待驗。
- 功能來源 `08c37f94564923f6a560395a0219e687df36052a`。GitHub Actions job `128928748124` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42545258202)

## 2026-11-09 即時模擬閘道取消待確認批次

模擬器 0.2.1 在等待 ACK 期間持續讀取管理狀態。批次失效時取消本次讀取並關閉原模擬連線，重連從最新序號開始。ACK 到達後仍會重新核對事件、入場與階段。 [操作方式](HARDWARE.md#即時模擬閘道)

- 同機扣住 ACK 的案例，自模擬設備收到批次到關閉連線，新版暫停／結束分別為 140／141 毫秒。解壓包另測為 156／156 毫秒。舊 0.2.0 實測 891／906 毫秒，暫停批次記為逾時，房間 2 閘道未在測試的 8 秒觀察窗口退出。比較只涵蓋該次本機模擬連線。
- 879 項核心、38 項離線、16 項即時及解壓後 16 項檢查通過。離線範例的解壓包結果與建置測試逐位元相同。 [模擬器](HARDWARE_SIMULATOR.md)
- 用解壓的管理、伺服器、玩家和模擬器包，完成 407 項同機原生檢查。五房獨立及五房合併各有 25 個 Unity 玩家程序。原生遊戲受傷事件經管理 API、房間閘道送達模擬設備，兩種模式分別取得 108 及 105 筆模擬確認。逐筆核對原事件、回報、傷害、房間與入場。完成 1,694 幀回放、50 份原玩家戰績及程序清理，活動場次為零。廠商實體設備、頭盔和跨機仍待驗收。
- 功能來源 `90df932579994bdd300a73391fee05ba2162b1f6`。GitHub Actions job `128924353216` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42543802908)

## 2026-11-09 即時硬體模擬閘道

模擬器 0.2.0 可用本房房控身分讀取管理包 0.31.27 的即時回饋，依玩家、入場及席位綁定送到獨立本機模擬程序。每次一批，模擬回覆須符合連線及批次，確認前再讀回管理服務的現行階段及原事件。錯誤回覆、逾時、斷線、暫停或結束中的批次不計入模擬確認。重連從最新序號開始。 [操作方式](HARDWARE.md#即時模擬閘道)

- 879 項核心、38 項離線 CLI、14 項即時雙房檢查及解壓後同樣 14 項通過。雙房包含七筆成功模擬訊號、錯誤 ACK、逾時、斷線、暫停及 End 後的拒絕；過期入場綁定沒有收到訊號。解壓後離線範例報告與原測試逐位元相同。
- 用解壓包及自含管理服務驗證五房獨立與五房合併，各由五個閘道和五個模擬程序核對 25 筆合成戰鬥訊號。每房五筆模擬確認對上原玩家、入場及事件。活動場次為零，測試程序均已退出。實體廠商協議、設備輸入與輸出、實機停止及場館跨機仍待驗收。 [模擬器](HARDWARE_SIMULATOR.md)
- 功能來源 `80e4985f5258c38b151085663efc9150908232c1`。GitHub Actions job `128921827500` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42542988118)

## 2026-11-09 房間即時戰鬥回饋

Windows 管理包 0.31.27 提供唯讀房間回饋。主控可讀場次內各房，房控限本房。初次讀取與積壓超限會跳到目前序號。續讀以目前 Running 階段及原入場識別篩選射擊和受傷事件，保留原事件、回報及戰鬥來源。暫停、離場、結束、前一個 Running 階段的遲送回報，以及距管理事件接受達兩秒的資料均有測試。 [介面操作](HARDWARE.md#即時戰鬥回饋介面)

- 879 項核心、704 項 HTTP、58 項世界串流、38 項原離線模擬器 CLI、106 項管理包及 16 項解壓包 Chromium 專項通過。核心測試涵蓋重啟後重建階段序號、重讀保留同一事件 ID，以及精確期限。
- 使用三個解壓包及同一台 Windows 電腦，387 項原生檢查通過。五房獨立與五房合併各 25 個 Unity 玩家程序。兩種模式每房五席皆有受傷訊號，獨立場 107 筆與合併場 105 筆逐筆對回正式接受的傷害事件與原入場名額。各房 End 後讀取為空。完成 1,609 幀回放、50 份玩家原戰績及清理。來源為 Unity Simulation，設備輸入、輸出、實體停止及跨機場館仍待驗收。
- 功能來源 `7fa86c3162878e67d7095a4a1efd51092bd261c9`。GitHub Actions job `128917782526` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42541682674)

## 2026-11-09 五房 MR 部署線上核對

管理包 0.31.26 新增主控專用五房線上部署核對。PowerShell 讀取既有 `venue.json` 及原始檔案，完成離線檢查後送出一次請求。管理服務用同一次讀取的場次與名冊驗證 25 份票券簽章、入場名額及五房校正原檔。API 報告只提供房號、席位、結果及有效票券到期時間，成功的 CLI 輸出增加 `managementVerified: true`。 [操作方式](QUEST3.md#向管理服務核對五房名冊)

- 用解壓後的管理服務及實際配發的房間 ZIP，五房合併與五房獨立均通過 25 席。兩種模式都拒絕一張格式有效的偽造票券及一張名額重配前的票券，重下載受影響房間的 ZIP 後恢復 25 席。房控金鑰遭拒。六個測試場次結束，活動場次為零，原管理程序正常退出。
- 866 項核心、697 項 HTTP、58 項世界串流、21 項 PowerShell、97 項 Node、417 項 Chromium、16 項解壓包 Chromium 專項及 106 項 Windows 管理包檢查通過。此輪驗證管理及部署資料，Quest 3 實機、VIVE、場館跨機與廠商硬體另驗。 [Windows 管理包](WINDOWS_CONTROL_PACKAGE.md)
- 功能來源 `4bbc2e7d46d919e180e50830dad4a19eabf75db3`。GitHub Actions job `128915182679` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42540847623)

## 2026-11-09 MR 伺服器啟動前核對

Windows 伺服器啟動器 1.6 將未鎖定的 MR 場次保留在清單，列出待鎖定的房間。WinForms 與 CLI 共用房間鎖定判斷，實際啟動前會向原管理服務重新讀取。 [操作方式](SERVER_CATALOG.md#mr-校正鎖定與啟動資格)

- 解壓包通過 51 項實際 CLI／API、46 項 .NET Framework 及 137 項原生伺服器包檢查。單房及五房合併未鎖定時，CLI 回傳缺少鎖定，無子程序、工作目錄、就緒檔或戰鬥來源。主控鎖定後，唯讀清單以同一場次 ID 顯示可啟動，原遊戲程式也保留自己的拒絕機制。
- 另以 25 席五房合併 MR 名冊經 CLI 啟動原生伺服器，核對原子程序的 UDP 綁定與 `GameServer` 來源。缺少實體追蹤時 Begin 回應 `mr-readiness-required`。測試 End 後保留 15 個世界幀，雙封存、子程序及管理服務收尾成功，活動場次為零。
- Windows 防火牆提示覆蓋 WinForms 啟動器，本輪只觀察初始畫面，未完成 GUI 選取或按鈕互動。Unity 0.48.0 的 321 個執行內容檔案與前包雜湊一致。 [Windows 伺服器包](WINDOWS_SERVER_PACKAGE.md)
- 功能來源 `a9390c27988787e38f04e06b30e64ac5fc7bbc12`。GitHub Actions job `128913080071` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42540162892)

## 2026-11-09 Quest 3 MR 席位部署核對

控制台 0.31.25 加入逐席部署檔核對。管理服務使用目前的場次和名冊，驗證票券簽章、期限與入場名額，並比對連線檔內的校正雜湊及校正檔原始位元組。結果指向所選房間與席位，房控僅能核對本房。核對無場次寫入或新票券，切換席位、名額變更及登出會清除舊結果。 [操作流程](QUEST3.md#在管理台核對席位部署檔)

- 解壓後以 `Start-Control.exe` 啟動自含管理服務，共核對 173 筆 HTTP。五房合併與五房獨立各 25 席符合目前名冊及原始校正檔，30 筆錯席、改檔與跨房請求遭拒。全部六個測試場次結束，活動場次為零，啟動器及原管理程序正常停止。這輪覆蓋部署檔案，實際頭盔、透視與跨機連線另驗。
- 866 項核心、637 項 HTTP、58 項世界串流、97 項 Node、417 項 Chromium、解壓後 16 項 Chromium 專項與 106 項管理包檢查通過。專項涵蓋已簽章但過期的票券、名額更換、舊場次票券、逾期回應及窄螢幕。 [Windows 管理包](WINDOWS_CONTROL_PACKAGE.md)
- 功能來源 `ecf4f0d836bfbceefdc97f75ee6c8228a996e4ce`。GitHub Actions job `128909683706` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42539048680)

## 2026-11-09 MR 連線檔與部署預檢交接

控制台 0.31.24 的 MR 單席與整房連線檔帶有該房鎖定的校正檔 SHA-256，配票須等主控鎖定。PowerShell 部署工具依連線檔選用 MR 並核對原檔，若同房檔案內容有變動會在呼叫 ADB 前停止。五房預檢逐席核對鎖定值。原四欄 VR 格式及手動指定 MR 的舊部署檔仍可讀取。 [部署操作](QUEST3.md#quest-3-場地對位部署)

- 866 項核心、637 項 HTTP、58 項世界串流及 19 項 PowerShell 測試通過。HTTP 核對未鎖定時兩條配票路徑皆回應 409，鎖定後配票帶同一原始雜湊，票券依原 v2 admission 驗簽。22 項 Chromium 專項驗證房控的單席及 ZIP 下載與畫面提示。
- 完整 97 項 Node、404 項 Chromium 回歸及解壓管理包的 22 項 Chromium 專項通過。解壓核對 510 個清單檔案及 106 項管理包檢查，原資料與 F 槽快照 27 個檔案一致。 [Windows 管理包](WINDOWS_CONTROL_PACKAGE.md)
- 用解壓後的管理服務送出 140 筆 HTTP，驗簽 50 張實際配發的票券。全連線和五房獨立各 25 席通過原檔核對。兩種模式各拒絕一個變動過的同房檔案及一份錯場清單。取實際 ZIP 的單席檔進行模擬 ADB 部署，核對錯檔零 ADB 呼叫，正確檔案依原始位元組寫入並自動設定 MR。活動場次為零，原管理程序正常結束。實體安裝、頭盔定位、VIVE 和場館連線仍待驗。
- 功能來源 `63768aefed5359d7ef67920b212ab783a9a3d341`。GitHub Actions job `128906909843` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42538136246)

## 2026-11-09 主控台鎖定 MR 校正檔

控制台 0.31.23 在 MR 場次面板為主控列出各房的檔案選擇、核對結果與完整 SHA-256。單房和五房皆須核對該場全部房間，確認後透過原場次命令鎖定。管理服務核對標記順序、重算房間原點與量測誤差，並以原始 UTF-8 位元組計算雜湊。場次事件保存雜湊。 [操作方式](QUEST3.md#啟動-mr-伺服器前鎖定校正檔)

- 866 項核心、629 項 HTTP、58 項世界串流及 7 項管理包工具測試通過。瀏覽器專項核對 BOM 和 CRLF、錯房與錯誤量測拒絕、切換場次後丟棄舊回應，以及五房鎖定回應遺失時以原 UUID 重試並只保存一筆事件。已鎖定的歷史場次顯示原雜湊；房控看不到主控選檔介面。
- 最終版通過 97 項 Node、401 項 Chromium 回歸及獨立的 19 項瀏覽器專項。解壓最終 Windows 管理包核對 510 個清單檔案並通過 106 項檢查，原資料與 F 槽快照 27 個檔案一致。早期 400 項瀏覽器結果與第一份候選 ZIP 另行保留。 [Windows 管理包](WINDOWS_CONTROL_PACKAGE.md)
- 用最終管理包在 Chromium 鎖定五房原檔，實際 0.48.0 Windows 伺服器隨後啟動同一個 MR 場次，核對本機 UDP 綁定及原 25 席名冊。缺少追蹤時 Begin 回傳 409，結束後戰鬥和世界資料雙封存，逐格讀回 10 幀且活動場次為零。使用管理名冊與同機程序，頭盔實機追蹤、VIVE 相容、透視及跨機驗收仍待。
- 第一輪 .NET 建置因串流 API 的具名參數寫錯而停止，修正後建置成功。首輪 Chromium 因未指定本機瀏覽器快取而未啟動，指定既有快取後完成。兩份日誌保留。
- 功能來源 `e3e532513d8a48aba87493ac8a36baa33374fb0a`，歷史場次顯示修正 `64a3788db1ff0a160ed29cf97bc1ceceab3ee427`。兩次 GitHub Actions 因帳務或支出上限未啟動，零步驟。 [功能工作](https://github.com/peca12968/vr-command-center/actions/runs/42536969497) · [最終工作](https://github.com/peca12968/vr-command-center/actions/runs/42537242716)

## 2026-11-09 MR 校正檔入場鎖定

遊戲 0.48.0 使用 NGO 協定 31。主控在 MR 場次準備中透過管理 API 一次鎖定該場各房的校正檔 SHA-256，並在配票部署時沿用相同原檔。伺服器要求完整的房間集合，入場再核對房號、校正檔雜湊及原票券。 [操作方式](QUEST3.md#啟動-mr-伺服器前鎖定校正檔)

- 862 項核心、629 項 HTTP、58 項世界串流、265 項 Unity EditMode 通過。解壓新版管理包通過 106 項檢查。另以實際管理包核對五房鎖定後正常重開，18 筆 HTTP，原場次與五份雜湊一致，重送回原序號且只有一筆鎖定事件。房控、缺房及更換校正檔均遭拒絕。
- 解壓 Windows 伺服器與管理包的 137 項同機檢查通過。未鎖定的 MR 伺服器未開始監聽、綁定來源或寫入遙測。鎖定後正常進入 Preparing，拒絕一般桌面玩家的票券連線，保留原 MR 環境控制及雙封存。七場共核對 624 幀完整回放和 VR 的 10 份個人戰績 CSV。活動場次為零，C 槽原資料與 F 槽快照核對 87 個檔案一致。
- 另以相同正式 Windows 伺服器及真正簽發票券測試五個入場請求。同一房的另一份有效校正檔、錯房、舊 MR 格式與一般 VR 格式均遭拒，正確雜湊成功連線。測試只替換獨立 Windows 玩家副本送出的入場資料，正式包經雜湊核對，原伺服器完成雙封存及 127 幀寫入。先前兩次 Editor 測試客戶端在播放模式初始化失敗，均在送出封包前，原紀錄保留。實體追蹤、透視、VIVE 與場館跨機待驗。
- 使用解壓 Windows 玩家包的原程式另跑 25 端同機回歸。五房全連線 25 端、五個獨立房各 5 端，25 項檢查通過。六場共 100 發、100 中、50 擊殺，50 份原戰績均取得伺服器確認，6 份 CSV 及雙封存通過。完整回放 1,856 幀，含 1,653 幀執行中畫面。原資料與 F 槽快照核對 174 個檔案一致，活動場次為零。測試以同機桌面輸入執行。
- Windows 與 Quest ARM64／IL2CPP 建置的來源指紋均為 `ca14a87b0745da15ccff0d7cc049837215d6695e8b108b297c5da2f76969f613`，場景及玩家 prefab 的網路 ID 與 0.47.1 相同。Quest APK 版本碼 61，min SDK 32，target SDK 35，v2 開發簽章通過，60,954,358 bytes，SHA-256 `911db80a3221ef08339127b04cf60c99bfa127502ddde07e4c667c85ae29d1ac`。保留前一版 Windows 與 Quest 共 325 個原始檔案並逐檔核對雜湊。 [Windows 玩家包](WINDOWS_PLAYER_PACKAGE.md) · [Windows 伺服器包](WINDOWS_SERVER_PACKAGE.md) · [Windows 管理包](WINDOWS_CONTROL_PACKAGE.md)
- 首次 Unity EditMode 有 3 項失敗，建置器的相容上限及一項測試仍用舊協定 30。統一建置器的協定值並更新序列化斷言後重跑通過。Windows 建置後，驗證腳本重用 XML 型別的變數讀 JSON 而退出，後續獨立核對新組件及建置回條，並將驗證日誌從 F 槽根目錄移回專案。兩次原失敗紀錄均保留。
- 功能來源 `ae0fb815695e4563c022d023936a1ef142b0ee43`，最終遊戲來源 `11a48ea420c2a6127956c1d624111574d95be2d1`。兩次 GitHub Actions 因帳務或支出上限未啟動，零步驟。 [功能工作](https://github.com/peca12968/vr-command-center/actions/runs/42534524252) · [最終遊戲工作](https://github.com/peca12968/vr-command-center/actions/runs/42534632857)

## 2026-11-09 Quest 五房部署預檢

`deploy-quest.ps1 -VenueManifest` 直接讀取控制台的五份整房連線 ZIP，依操作員填入的場次 ID 核對 25 席、各房校正檔與連線端點。全連線共用場次與端點，獨立模式各房分開。成功報告列各房端點、校正檔 SHA-256 與最早到期 UTC，無票券或玩家識別。 [操作方式](QUEST3.md#五房-25-席部署預檢)

- 16 項 PowerShell 部署測試通過，涵蓋 7 項全館測試及原 9 項單機流程。驗證錯場、錯席、重複玩家或入場識別、過期、混用端點、錯房校正、異常 ZIP 成員與裝置參數隔離。
- 以解壓控制台 0.31.22 管理包跑獨立實例，134 筆 HTTP 成功。管理服務產生 5 份校正檔、全連線及獨立模式各 5 份 ZIP，50 張實際票券逐張通過簽章和原 admission 核對，再由 CLI 預檢。兩種模式各接受 25 席，另各拒絕一份填錯場次的清單。原輸入逐檔雜湊與場次資料核對一致，結束後活動場次為零，原管理程序正常退出。ADB 安裝、頭盔追蹤與場館 UDP 待驗。
- 功能來源 `e23630502aec7ad2f17e2f563983b42ee2267e34`。GitHub Actions job `128893286962` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42533713440)

## 2026-11-09 XR 追蹤恢復與武器重新啟用

遊戲 0.47.1 對 VR 與 MR 追蹤玩家停用失效期間的武器輸入。場次允許參戰、本機姿態有效且伺服器的姿態接受狀態為真時，玩家須先放開右手扳機與換彈鍵，下一次主動按下才可送出。 [操作方式](QUEST3.md#追蹤恢復後的武器輸入)

- Unity 6000.3.27f1 EditMode 263 項全數通過。其中 3 項新增測試涵蓋釋放當幀、暫停與中斷後重新啟用，以及虛擬右手 Touch 的追蹤與按鍵事件。PlayMode 階段使用 Input System 的 Touch 裝置配置，測試以合成狀態提供參戰與姿態條件。頭盔、控制器實機、MR 透視、VIVE 及跨機仍待驗。
- Windows 與 Quest ARM64／IL2CPP 建置的來源指紋均為 `07f2358686318272c9f656a42949bb778e76748f1ed4aa0a529dc65349bd47cf`，場景與玩家 prefab 的網路 ID 與上一版相同。Quest APK 版本碼 60，min SDK 32，target SDK 35，開發簽章 v2 通過，60,952,530 bytes，SHA-256 `6255211a859dc38d22f0917954e75df5f3e7083bdea8a50b5c9fe99764fea319`。兩個 Windows ZIP 各解壓核對 328 筆，玩家啟動器另通過 19 項檢查。舊 Windows／Quest 原始產物 325 個檔案先依 SHA-256 核對並保存。 [玩家包](WINDOWS_PLAYER_PACKAGE.md) · [伺服器包](WINDOWS_SERVER_PACKAGE.md)
- 以解壓玩家包的 Unity 程式與獨立管理服務跑同機回歸。五房全連線 25 端、五個獨立房各 5 端，25 項檢查通過。六場共 100 發、100 中、50 擊殺，50 份個人戰績全部由原伺服器確認，6 份場次 CSV 與戰鬥及世界雙封存核對通過。完整回放 1,848 幀，包含 1,646 幀執行中畫面。結束後無活動場次或殘留子程序，C 槽原始資料與 F 槽快照的 174 個檔案雜湊一致。使用同機生成的桌面輸入。
- 首次 Windows 檢查誤以保留原時間戳的啟動檔判定新舊，Unity 本身正常結束，後續核對新的建置回條與遊戲組件。Quest 首次指令的類別名稱不完整，保留失敗日誌，改用完整名稱後成功。功能來源 `237d11f7b3aae95f4184a27f0f6ae63f5256cbb1`。GitHub Actions job `128888235682` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42532071585)

## 2026-11-09 MR 執行中追蹤提示

控制台 0.31.22 在執行中的 MR 場次顯示追蹤提示。房卡標示缺少追蹤的存活席位數，場次面板列出席位與已淘汰人數。操作員可從同場控制區暫停，再確認追蹤後繼續。 [執行中追蹤](PLAYER_READINESS.md#執行中追蹤)

- 五房 25 席以實際 API／WebSocket 發布合成追蹤及戰鬥快照。房間 4 第 2 席失去追蹤時只有房間 4 亮起提示，房內仍是 3／4 存活席位就緒，第 5 席保留淘汰紀錄。快照過期時撤下舊警示與人數，恢復的快照顯示 4／4。再失去追蹤後由操作員暫停，恢復後繼續原場並完成雙封存。.NET 模擬另核對姿態過期玩家無法開火。
- 首輪 HTTP 回歸指出一般 VR 房卡收到新增的空欄位。只在適用的 MR 報告輸出欄位後，原 API 格式檢查通過。最終 852 項核心、621 項 HTTP、58 項世界串流、97 項 Node 及 385 項 Chromium 通過。解壓管理包通過 106 項與 22 項 MR 專項，關閉後 C／F 核對 27 份檔案。 [Windows 管理包](WINDOWS_CONTROL_PACKAGE.md)
- 功能來源 `6498b72a92805b9b3881871aa649b1f7eabccfe9`。[GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42531048443) job `128885086362` 因帳務或支出上限未啟動，零步驟。頭盔實機追蹤、MR 透視與跨機仍待驗收。

## 2026-11-09 MR 暫停後恢復追蹤

控制台 0.31.21 在暫停場次顯示「MR 繼續檢查」。伺服器以最新場次序號的 MR 暫停快照核對存活席位。已確認淘汰的玩家保留名冊與戰績。已接受的同一繼續命令可重試取得原回條。 [繼續操作](PLAYER_READINESS.md#暫停後繼續)

- 五房 25 席的 Chromium 與實際 API／WebSocket 測試中，暫停前的執行中快照遭拒。新暫停快照顯示房間 4 第 2 席等待追蹤、第 5 席已淘汰。拒絕時維持原暫停序號。補齊第 2 席後，保留原 25 席與開始時間繼續，重送得到原回條，結束後完成戰鬥與世界雙封存。.NET 測試另核對暫停中的原入場姿態回復、武器與任務 tick 停止、過期與舊序號遭拒，以及重送舊繼續命令不會覆蓋後來的暫停。
- 首輪專項測試在合成戰鬥事件後未等控制台更新序號便送出 Pause，收到 409。補上精確序號核對後通過。首輪完整瀏覽器回歸發現新增的繼續提示會覆蓋原開場提示，已修正分支並增加專項檢查，首輪結果及候選 ZIP 保留。
- 最終 847 項核心、621 項 HTTP、58 項世界串流、95 項 Node 及 382 項 Chromium 通過。最終管理包解壓後另通過 106 項與 19 項 MR 專項檢查，關閉後 C／F 逐檔核對 27 份。測試使用合成追蹤與戰鬥事件，Quest 3 重新對位、透視和場館跨機仍待實測。 [Windows 管理包](WINDOWS_CONTROL_PACKAGE.md)
- 追蹤閘門提交 `8ae7a33a2792cbbe3de9cd88b389cce4e9ca3d14`，最終提示修正 `fb1060dd4dcfc4617fefd4ab68cd0136eff05edb`。兩次 GitHub Actions 都因帳務或支出上限未啟動，零步驟。 [閘門工作](https://github.com/peca12968/vr-command-center/actions/runs/42529882909) · [最終工作](https://github.com/peca12968/vr-command-center/actions/runs/42530141149)

## 2026-11-09 MR 開場檢查與等候席位

控制台 0.31.20 將 MR 開場檢查放在開始按鈕旁。主控可看到各房的追蹤就緒人數與等候席位。房控在此區查看自己房間。API 的 `mrStartState` 與 Begin 使用同一判定，涵蓋空名冊、來源新鮮度、MR 錄製來源、管理序號與原入場。 [操作與狀態](PLAYER_READINESS.md#mr-開場條件)

- Chromium 透過實際 WebSocket 發布五房 25 席的合成追蹤測試快照。房間 4 的第 2、5 席等待，其他四房各 5 人就緒。補齊姿態、快照過期及更新環境序號都在控制台對照。最新序號到達後，主控從 UI 發出 Begin，原 25 席開始夜間場次，最後完成戰鬥與世界雙封存。
- 832 項核心、621 項 HTTP、58 項世界串流、94 項 Node 與 375 項 Chromium 通過。第一次 Chromium 啟動使用預設快取路徑而找不到已安裝的瀏覽器，指定現有快取後重驗通過。解壓後管理包通過 106 項檢查及 12 項開場專項檢查，關閉後 C／F 比對 27 份檔案一致。 [Windows 管理包](WINDOWS_CONTROL_PACKAGE.md)
- 功能來源 `c0c6f9b05a0e99b4e75937a12ad880dff8c1f269`。[GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42528950179) job `128878635229` 因帳務或支出上限未啟動，零步驟。Quest 3 實機追蹤、MR 透視與跨機場館驗收仍待。

## 2026-11-09 Quest 3 部署檔離線預檢

`deploy-quest.ps1 -CheckOnly` 可在接頭盔前核對玩家票券房號與席位、UTC 到期時間、校正檔房號與 A／B／C 欄位。預檢輸出只含房間、席位、到期時間、模式與校正檔雜湊。正式部署先執行相同檢查，並以當次讀取的校正檔內容計算雜湊及複製。 [PowerShell 7 操作](QUEST3.md#quest-3-場地對位部署)

- 隔離 API 0.31.0 建立五房連線 MR 場次，實際簽發五包共 25 份玩家設定，輸出五房各自的校正檔。25 份同房配對的席位、效期及 SHA-256 均對上原始 API 資料，五組錯房配對在離線預檢拒絕。名冊未變，測試結束後活動場次歸零。摘要 `artifacts/quest-deploy-preflight/api-preflight-summary.json` 未保存票券。
- PowerShell 7 的 9 項檢查與 621 項 HTTP 回歸通過。模擬 ADB 驗證一般 VR、MR 與複製失敗的處理，包含原檔在安裝階段變動時仍複製已核對的內容，以及啟用新玩家設定失敗時保留舊檔並清除暫存。Windows PowerShell 5.1 入口受本機腳本執行政策限制，本輪以 PowerShell 7 驗證。
- 現有 Quest 0.47.0／版本碼 59 APK 靜態複驗為 ARM64、min SDK 32、target SDK 35，有效 v2 開發簽章，SHA-256 `18d23e591223754c7d03af3e8bbb79b48491bfe168547db5e01c091b00bfbc14`。實機 USB 安裝、追蹤及 MR 透視仍待驗收。
- 功能來源 `020d47d948741e6a2d4ca28ce96f587135484050`。[GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42527893009) job `128875467419` 因帳務或支出上限未啟動，零步驟。

## 2026-11-09 五房 UDP 丟包驗證

新增 `--udp-periodic-loss`。所有原玩家入場後、開始前啟用。每條原遊戲連線的上行、下行各自計數，每 20 個封包丟棄 1 個，持續至個人戰績交付。使用 Windows 0.47.0 及 API 0.31.0，丟包只在本機測試轉送器注入。 [重跑命令](DESKTOP_EXERCISE.md#五房-udp-丟包驗證)

- `20261109-054459-cc881344` 通過 24 項原生檢查。五房全連線及五個獨立房間各 25 位同機模擬玩家。全連線的共通 Running 區間 38.54 秒，上／下行分別丟棄 2,467／3,292 個封包。獨立模式的共通區間 34.14 秒，分別丟棄 2,008／1,383 個。逐條連線核對兩個方向均有實際丟包。
- 六場共 100 發由伺服器接受，逐位回放核對移動與換彈。4,111 幀完整回放、50 份原個人戰績、六份 CSV 及雙封存對上伺服器的原連線確認，活動場次歸零。50 個轉送器均關閉，C／F 核對 224 份關閉後檔案。
- 應用層探測共 1,500 次，回覆 1,317 次、逾時 183 次。各玩家已回覆探測的 p95 往返約 11.1 至 22.3 毫秒。探測逾時與戰績確認分開計數。實際無線突發丟包、跨機、渲染幀率與 25 位真人仍待驗收。
- UDP 轉送 17 項、動態驗證 22 項、參戰驗證 27 項及檔案保存 5 項 Python 測試通過。驗證來源 `4943faf859d2d42f3da403aa5dc33b5213a98e5f`。[GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42526857101) job `128872275966` 因帳務或支出上限未啟動，零步驟。

## 2026-11-09 掩體移除通路試算

控制台 0.31.19 可在任務草稿中試算移除一件掩體後，哪些原本受阻的出生位會取得通往中線的取樣路徑。沿用場地檢查規則，並以黃色虛線疊加結果。要採用結果，仍須實際修改物件及儲存任務版本。 [操作方式](LAYOUT.md#出生位通路預覽)

- 366 項 Chromium 檢查通過。測試中試移除牆上一段沙包可讓五席通往中線，試移除遠處油桶則維持阻隔。試算保留七件草稿物件，切換物件後收到的舊結果會被捨棄。首輪找到單純選物件也會標記草稿已修改的問題，已修正並在同一套瀏覽器測試重驗。
- 825 項核心、621 項 HTTP 及 106 項解壓後管理包檢查通過。Windows 0.47.0 既有遊戲包搭配新版管理包另通過 136 項檢查。五個獨立房間及全連線場次均對上已保存的掩體座標及缺口，六場核對 544 幀回放及 10 份原模擬玩家戰績。程序關閉後，管理及原生測試各有 27、78 份檔案通過 C／F 逐檔核對。 [Windows 管理包](WINDOWS_CONTROL_PACKAGE.md)
- 功能來源 `d871b52c035349f74c172192fd0277b4d35babef`。[GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42526265393) job `128870463123` 因帳務或支出上限未啟動，零步驟。此輪原生檢查對照已保存配置與場景幾何。實地行走、跨機及頭盔仍待驗收。

## 2026-11-09 五房原生玩家射擊與戰績

新增短場驗證選項 `--marksmanship`。以既有 Windows 0.47.0 原生執行檔和 API 0.31.0 驗證。每房六個油桶把五個敵軍出生位留在各席正前方。原生桌面模擬客戶端透過既有移動、開火與換彈路徑提交輸入。 [重跑命令](DESKTOP_EXERCISE.md#五房射擊與戰績驗證)

- `20261109-052619-1b7e0c7d` 的五房連線及五房獨立各 25 位同機模擬玩家。25 項原生檢查通過，所有玩家均為兩發兩中、一次換彈、一擊殺及命中率 100%。六場共 100 發、100 中、50 次擊殺、1,976 幀回放及 50 份伺服器確認的個人戰績。六場逐格核對原射線、目標、戰鬥帳本和精確續播。
- 連線 ZIP 內六份 CSV 與個別匯出逐位元一致，5,503 bytes，SHA-256 `e8a7b593ea6837bab9e2c4677346961c2e40435ff9deedec56a26455c5579d0c`。活動場次歸零，停止後 C／F 核對 174 份原始檔案。此輪使用守備敵軍與關閉自動攻擊，測試範圍為玩家對目標射擊。上一輪 AI 傷害另有獨立證據。
- 既有短場 `20261109-052855-acbe203d` 的五人回歸另通過 5 項、138 幀回放，關閉後 C／F 核對 29 份。22 項 Python 檢查及三組不相容參數拒絕通過。驗證來源 `a595be0eca3475c940316c569f6aa78025e04678`。[GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42525329858) job `128867587079` 因帳務或支出上限未啟動，零步驟。此輪使用既有開發版遊戲執行檔及自動合成輸入。

## 2026-11-09 五房原生交火與戰績對照

三包驗證新增 `--check-room-combat`，搭配 `--check-room-reports` 使用。以 Windows 0.47.0 遊戲及玩家包、0.31.18 管理包執行。每房五位原生模擬玩家與五名敵軍。由正常管理命令啟停 AI 攻擊，回放逐筆核對敵軍、同房目標、傷害與每格統計，再比對封存帳本、個人戰績及 CSV。 [驗證命令](WINDOWS_SERVER_PACKAGE.md#三個可攜包整合驗證)

- `run-4425c4b3087e409db8ff028797797e34` 通過 377 項檢查。五房獨立及全連線各 25 個同機模擬玩家，兩種模式每位原玩家都受傷。獨立場次核對 110 筆，Linked 核對 105 筆。共 1,620 幀完整回放、50 份原玩家戰績及伺服器確認，活動場次歸零。Linked 每位耗損 20 至 100，玩家沒有發射武器。
- Linked ZIP 為 5,451 bytes，SHA-256 `ac0ce24092b34fdd37ae59e4110fa009d576f83c0926b66179683568de234451`。全場 25 列及五房各 5 列逐位元對上原 CSV，傷害及中彈數與回放重建一致。所有程序關閉後，C／F 逐檔核對 218 份。
- 10 項伺服器包 Python 檢查通過，包含新增的跨房、重複事件、關閉攻擊後仍有傷害、統計不符及漏人反例。驗證來源 `25092b5fa57c9e6d8cbba84648a893d1b1839266`。[GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42524680190) job `128865554958` 因帳務或支出上限未啟動，零步驟。此次同機測試使用既有可攜包，實體跨機、頭盔及廠商硬體仍待驗收。

## 2026-11-09 五房戰績 ZIP

控制台 0.31.18 的「下載五房戰績 ZIP」讓全館主控一次取得全場及五份分房 CSV。管理服務擷取一份最終戰鬥報表，六份檔案使用相同的場次與戰鬥封存序號。保留空房資料列與離場玩家戰績。 [報表操作](REPORTS.md#一次下載五房戰績)

- Windows 三個可攜包 `run-c6ae134835ea49e59fb7c80cdc63af67` 通過 347 項檢查。五個獨立房間與五房連線各 25 個同機模擬玩家，六場共 878 幀回放及 50 份原玩家戰績獲伺服器確認，活動場次歸零。Linked ZIP 為 5,372 bytes，SHA-256 `88cbdd1faf21fff0efdcb52cd7a69cdefa1ae5395570f6a9a75678da86f685f0`。全場 25 列與五房各 5 列逐位元對上六個既有 CSV 回應。該原生測試為零交火，非零統計以 HTTP 測試核對。
- 825 項核心、621 項 HTTP、362 項 Chromium 及 106 項解壓後 Windows 管理包檢查通過。HTTP 核對只限全館主控、拒絕未完成場次、六份檔案一致及 API 重啟、金鑰輪替後位元組相同。Chromium 下載驗證另核對三間空房的資料列。原生及管理包清理後，C／F 分別核對 218、27 份檔案。 [Windows 管理包](WINDOWS_CONTROL_PACKAGE.md)
- 功能來源 `63da0283b229a1f2cbe8267e8eacfc51bbc4b741`。[GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42523999292) job `128863397194` 因帳務或支出上限未啟動，零步驟。實體跨機、25 位真人、頭盔及廠商硬體仍待驗收。

## 2026-11-09 五房觀戰快速切換

控制台 0.31.17 在多房觀戰及回放提供全場和各房按鈕，從同一快照顯示連線玩家及存活敵軍數。選房會聚焦鏡頭與下方玩家統計，俯視模式可連續切房。 [觀戰操作](WORLD_RECORDING.md)

- Windows 0.47.0 原生場次 `20261109-050344-dae129c1` 的五個模擬玩家各入一房，由主控在遊戲中啟用自動攻擊。實際 Chromium 的全場第 45 格、房間 1 第 46 格、房間 2 第 53 格、回全場第 54 格及封存回放房間 5 第 77 格，均與 API 同序號的房間計數和統計逐欄相符。房間 1 俯視目標 X −28 公尺，俯角約 85.42°，玩家耗損 80。雙封存及五份玩家戰績確認通過，活動場次歸零。
- 首輪原生瀏覽器未在 30 秒內觀察到封存，原紀錄保留；收尾程序後來封存。重跑等實際 AI 戰鬥事件停止後刷新場次，並查證 UI End 回應 200，再核對封存回放。原生及管理包關閉後，C／F 分別核對 14、27 份檔案。
- 359 項 Chromium、92 項 Node、58 項世界串流及 106 項解壓後 Windows 管理包檢查通過。功能來源 `f17408d3365cac7e1c2fcf865113833565ec0aad`。[GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42523418102) job `128861641200` 因帳務或支出上限未啟動，零步驟。此次為同機模擬及軟體 WebGL。 [Windows 管理包](WINDOWS_CONTROL_PACKAGE.md)

## 2026-11-09 五房開場條件預覽

控制台 0.31.16 在建立準備場次前顯示選定版本、目標房間、時間、初始天氣、敵軍策略、每房物件數及完整簡報。預覽與建立請求使用同一個已保存版本。場地檢查、房控權限與房間占用仍由管理服務核對。 [任務版本操作](MISSION_VERSIONS.md)

- 原生 Windows 0.47.0 場次 `20261109-045452-089ffe33` 有兩個不同的已保存版本。主控在實際 Chromium 選回第 1 版、留下不同的未存草稿，並以五房全連線建立原版本。五個原生玩家程序各入一房。Running 快照核對原 120 秒、暴風雨夜間及閃電、巡邏且關閉自動攻擊、7 名敵軍按房分為 2／2／1／1／1，以及每房的沙包、油桶及角度。雙封存到第 31 格，五份玩家戰績均獲伺服器確認，活動場次歸零。C／F 核對 14 份關閉後檔案。
- 357 項 Chromium 和 603 項 HTTP 檢查通過。新版 Windows 管理包解壓後通過 106 項檢查，507 筆封裝清單與 C／F 27 份關閉後檔案相符。首輪原生測試因測試端未傳修訂必要的 Idempotency-Key 停在 400。原結果保留，補上鍵後重新建立隔離場次並通過。 [Windows 管理包](WINDOWS_CONTROL_PACKAGE.md)
- 功能來源 `db6c9cfe08b357dda8fd8f9934acc37e69b1979e`。[GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42522638107) job `128859272083` 因帳務或支出上限未啟動，零步驟。這次驗證採同機模擬玩家，跨機、頭盔與廠商硬體仍待驗。

## 2026-11-09 接續補送後的新保存片段

控制台 0.31.15 在未封存回放的已保存尾端提供「接續新保存片段」。它查詢同場次與同一來源的尾端，從下一格起播放到本次確認的序號。相同尾端會保留畫面，切換場次、頁籤或登出會取消查詢。 [操作說明](WORLD_RECORDING.md#回放未封存的已保存片段)

- 原生 Windows 測試 `20261109-044528-25e507e1` 使用 0.47.0。房間管理員在 Chromium 看完第 16 格，檢查無新格時留在原處。WorldRelay 補送後，只發出第 17 至 46 格的續播請求。第 46 格損耗 80，未封存標示、逐格尾端及原始完整 46 幀一致。原伺服器、資料庫及瀏覽器關閉後核對 C／F 20 份。
- 92 項 Node、354 項 Chromium、825 項核心與 58 項世界串流通過。管理包 `run-bf0350ff4cfe417cb5f3fd8c6c451f53` 通過 106 項檢查，核對 507 筆封裝清單與 C／F 27 份關閉後檔案。首輪瀏覽器測試在回放播放器顯示前嘗試選擇速度而逾時，首輪封裝檢查傳入 ZIP 路徑。原結果保留，重跑以正常畫面順序和解壓目錄通過。 [Windows 管理包](WINDOWS_CONTROL_PACKAGE.md)
- 功能來源 `ffff9e6a303e3961820844276ce36ed66f3658e9`。[GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42521882313) job `128856950353` 因帳務或支出上限未啟動，零步驟。原生測試使用同機模擬玩家，頭盔與跨機容量仍待驗。

## 2026-11-09 遊戲程序中斷後補送原始回放

WorldRelay 從世界 journal 讀取任務時鐘版本，並以該版本確認同一戰鬥串流。只有戰鬥 journal 時，TelemetryRelay 先從原管理實例核對場次及串流，再採用該版本。兩個工具都核對接受序號與本地確認範圍。操作時保留原件，使用副本補送。 [世界回放操作](WORLD_SOURCE.md#工具操作) · [戰鬥補送操作](TELEMETRY.md#中斷後補送)

- Windows 0.47.0 原生測試 `20261109-043747-f104250c` 先允許實際 AI 命中，再阻斷同場戰鬥批次與世界發布，最後終止原遊戲子程序。舊 WorldRelay 與 TelemetryRelay 均因版本不符收到 HTTP 409，API 和原紀錄均未改動。
- 新 WorldRelay 補送後，原場次由 18 幀增至 46 幀、戰鬥事件由 1 筆增至 4 筆、玩家損耗由 20 增至 80。兩個工具再送同一資料時接受序號與副本雜湊一致。原始兩份 journal 雜湊保持一致，停止後 C／F 核對 20 份檔案。
- 管理端以正常 End 釋放房間。房間管理權限完整回放 46 幀，封包逐欄核對原 journal，Unity 與 API 的浮點欄位按原始 32 位元值比對。回放以 `saved-end` 收束，世界與戰鬥保持未封存，最終 CSV 與場館 ZIP 均回應 409，原玩家沒有最終戰績。此流程保留已落盤紀錄，遊戲程序結束後由操作員管理場次。
- 前三個測試候選分別在 Running 期間誤期待待確認旗標、誤把 SSE 狀態訊息視為影格，以及直接比較不同精度的浮點 JSON。原始結果保留，最後以正確的管理階段、事件分類及 32 位元數值重跑。此場使用一個同機模擬玩家，未重跑頭盔或跨機。
- 功能來源 `560da7b86f69579b09ed71fbaedf211926e3ecbb`。Windows Release 建置及 825 項核心、603 項 HTTP、58 項世界串流通過。[GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42521177480) job `128854789406` 因帳務或支出上限未啟動，零步驟。

## 2026-11-09 遊戲伺服器保留原場次等待管理恢復

Windows 啟動器 1.5 在就緒後遇到暫時性管理 HTTP 讀取失敗時，給予原服務 15 秒恢復窗口。它保留原 Unity 子程序，恢復時核對同一場次、戰鬥來源、階段與接受序號。權限、來源或資料錯誤會使該次運行失敗。報告記錄中斷次數、恢復次數及最長觀察間隔。 [管理恢復與部署](WINDOWS_SERVER_PACKAGE.md#管理服務短暫中斷)

- 原啟動器 1.4 的 `run-b9bb52f8aca54b5499e7a94c0de79f4d` 終止自建管理 API 後收到 HTTP 0，隨即停止原遊戲子程序。原實例重開後保有場次、名冊與 22 幀已保存紀錄，原玩家沒有最終戰績。9 項反例觀察通過。
- 新版 `run-1bd65e62404d49b8804954dac7f1c586` 通過 16 項。終止原管理 API 並於同一實例重開，啟動器記錄一次中斷與一次恢復，最長 9,292 ms。原遊戲程序、場次、戰鬥來源、入場及玩家連線延續。119 幀完整回放中，78 幀管理中斷畫面皆為 Paused，時鐘固定在第 31 tick。最終傷害 60，原玩家戰績、伺服器確認、CSV、場館 ZIP 和雙封存一致，活動場次歸零。
- 新版持續中斷 `run-2d5d6e0c56b84c759d28de9683d31dd4` 通過 11 項。恢復次數零，啟動器觀察 15,286 ms 後以未完成結束並清理自己的子程序。管理實例重開可讀原保存資料，世界未封存，玩家未收到最終戰績。上述三場清理後各核對 C／F 16 份檔案。
- 首輪短中斷候選未錄到失敗輪詢。另一輪記錄 9,288 ms 並通過回放、雙封存與戰績斷言，測試摘要在序列化小數時失敗。兩輪失敗及更早的測試初始化錯誤均已保留，最終使用同一份已封裝遊戲執行檔重跑。
- 一般伺服器包另通過 147 項原生檢查、581 幀完整回放與 10 份 CSV，包含五房獨立、全連線、MR 開場閘門及增援。清單通過 38 項 CLI／API 及 42 項 Windows Framework 檢查。清理後 C／F 分別核對 92 與 14 份檔案。解壓包 328 筆，兩版 321 份 `Runtime/` 檔逐檔相符，封裝內容差異為啟動器與說明。跨機、25 位真人、頭盔與廠商硬體待驗。
- 功能來源 `540197c7dbaf2932b55f229a3135852795273c2e`。[GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42520163910) job `128851706245` 因帳務或支出上限未啟動，零步驟。

## 2026-11-09 主控下載場館驗收資料

控制台 0.31.14 在「任務收尾」新增「下載場館驗收資料 ZIP」。只有全館主控可以下載。API 核對任務曾開始、世界與戰鬥同源封存、端點公告及結束名冊與統計一致，再輸出 `session.json`、`statistics.json` 和 `endpoint.json`。檔名使用場次 UUID，回應為 `application/zip` 和 `Cache-Control: no-store`。切換場次、頁籤或登出會取消待送達的下載。ZIP 資料供既有離線工具與原始日誌合併核對。 [操作流程](EXTERNAL_CLIENTS.md#核對封存戰績與-udp-來源)

- 功能來源 `ef9e5a659091ceb838596e00fdb0458feed0f0b9`。Windows Release 建置、825 項核心、603 項 HTTP、58 項世界串流、92 項 Node 和 352 項 Chromium 通過。另有 10 項專項瀏覽器檢查，透過實際 API、WorldRelay 與 Chromium 下載，核對三個 ZIP 檔案逐一等於 API 資料、只讀序號與身分切換。首兩次瀏覽器啟動在缺少指定執行檔時退出，F 槽下載快取另有鎖更新逾時，改用全新的 C 槽快取取得版本相符的 Chromium 後通過。原紀錄保留。
- Windows 管理 ZIP 為 52,531,647 bytes，SHA-256 `fb2df7651f01d1cbd1990083bf89d4730beef34918601f3b30a514d5af5addea`。自含 .NET／ASP.NET Core 10.0.14，487 份執行內容，解壓後逐檔核對 507 筆及 106 項 Windows 管理包檢查，停止後 C／F 核對 27 份。 [管理服務包](WINDOWS_CONTROL_PACKAGE.md)
- 三包場次 `run-3f30c4e40fc14a8285021330616347b0` 使用新版管理包和 Windows 0.47.0 遊戲包。五房獨立與全連線各 25 個同機模擬玩家，360 項原生檢查、913 幀完整回放、50 份戰績確認及 6 份 CSV 通過。全連線 ZIP 為 3,415 bytes，SHA-256 `4883582ffa26ac667c968142696f29ac62fed43e2cfd14687915c2318db63f88`，最終世界序號 149。解壓後獨立執行既有 CLI，25 份原戰績與伺服器 UDP 來源及確認相符。活動場次歸零，清理後 C／F 核對 219 份。實際雙機與場館容量待驗。
- [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42518470088) 的 job `128846550929` 因帳務或支出上限未啟動，零步驟。

## 2026-11-09 場館連線與戰績核對

新增 `scripts/verify-field-results.py`。工具讀取 Windows 啟動器的終止報告、管理服務的封存快照、公告端點，以及伺服器和玩家原始日誌。它將每位玩家的最後一條連線對到伺服器觀察的 UDP 來源及戰績確認，再比對結束名冊、房間、入場 ID、世界與戰鬥封存序號、統計。摘要只輸出計數、房間、序號與範圍。 [驗收操作](EXTERNAL_CLIENTS.md#核對封存戰績與-udp-來源)

- 0.47.0 三個 Windows 可攜包以本機乙太網路的私有 IPv4 執行 `run-7b1aded46dfd49a3af34fdc932ee2e8e`。五房獨立及全連線各 25 個模擬玩家，356 項原生檢查、895 幀完整回放、50 份戰績確認及 6 份 CSV 通過，活動場次為零。清理後 C／F 逐檔核對 219 份。
- Linked 的 25 位玩家各有原始來源記錄與伺服器確認，雙封存世界序號為 159，戰鬥事件數為零。最終版 CLI 對同一批已關閉的原始資料再次取得同一份摘要。只將模式改成 `direct-lan` 後退出碼為 1，診斷只回報缺少清單外的私有來源。非零戰鬥及小數命中率以單元測試驗證。實體主機與 LAN 容量待場館驗收。
- 新增 8 項 Python 核對測試，另有 4 項伺服器封裝單元測試通過。GitHub 功能源為 `621acbbd6d1e39b9575e11a902382b4707004616`。[Actions](https://github.com/peca12968/vr-command-center/actions/runs/42517511914) 的 job `128843654860` 因帳務或支出上限未啟動，零步驟。

## 2026-11-09 壓縮即時角色同步

遊戲 0.47.0 將角色 UUID 改為 16 bytes，打包整數及布林旗標，省略零值的面向、換彈計時與射擊欄位。已開火角色傳送最後一次射擊的序號、時間及原始向量。讀取器會清除本次省略的欄位，以完整浮點精度解讀位置和向量。同步涵蓋該場全部角色。協定升至 NGO 30，Windows 玩家、遊戲伺服器及 Quest APK 須一起更新。 [版本相容性](EXTERNAL_CLIENTS.md#遊戲版本相容性)

- 功能來源 `ccb18b6c1ab4934c9b0529fa29992beab713be6d`。Unity 6000.3.27f1 的 260 項 EditMode 全部通過。30 個角色的序列化測試由 4,232 降至 1,952 bytes，125 個角色由 17,627 降至 8,127 bytes，兩者均約減少 54%。此處只計角色資料。測試同時核對數值邊界及重用讀取欄位清除。首輪測試仍有一個字串指派，修正後的一輪仍有舊協定 29 的測試期待，兩輪原失敗紀錄均保存，最終改為核對協定 30。
- 原生相容性場次 `20261109-032903-5fc26be7` 以有效票券嘗試從 0.46.0 加入 0.47.0。伺服器於 NGO 設定比對階段拒絕，當時名冊連線數為零。同一張票券隨後由 0.47.0 入場，完成 Running、雙封存與戰績確認，最後世界序號 40。程式退出碼為 0，清理後 C／F 核對 14 份檔案。首輪 `20261109-032736-d1588af5` 已錄下舊版拒絕與新版戰績，測試工具在產生摘要時缺少設定並退出碼 1，原紀錄保留。
- 兩版各以同一套 `--mode both --players-per-room 5 --seconds 40 --udp-traffic` 測試。0.46.0 場次 `20261109-030309-c87fdc6e` 為基準，0.47.0 場次 `20261109-032938-e24ab2cb` 通過 20 項、4299 幀完整回放、50 份戰績與伺服器確認、6 份 CSV。六場雙封存，活動場次為零，清理後 C／F 核對 174 份檔案。兩版轉送器都完整停止，記錄中的丟棄、外來封包及 socket 錯誤為零。
- 全連線角色複本場次 `20261109-034335-e8ea569a` 通過 9 項。25 個玩家端與 1 個伺服器在 Running 起訖、Pause、Resume 與 AI 攻擊後 Pause 共通過 130 次複本核對，每次均含五房的同一組 25 位玩家。另核對敵軍、生命值、位置、彈量、連線身分、412 幀完整回放與 25 人封存 CSV。C／F 核對 248 份檔案。首輪 `20261109-033350-c695d2eb` 在啟動序列 `linked-client-19` 時可用記憶體低於 2 GiB，測試退出碼 1，C／F 核對 31 份檔案。Quest 建置程序退出後以原門檻重跑通過。
- Windows 玩家 ZIP `artifacts/player-packages/windows-player-0.47.0.zip` 為 83,441,701 bytes，SHA-256 `e66ddd31d9f51b51254db756196ba1e234c258e46d6180fe49e8a1a9aa70a937`。伺服器 ZIP `artifacts/server-packages/windows-server-0.47.0-launcher1.4-win-x64.zip` 為 83,464,893 bytes，SHA-256 `f9cb4e5fee1854c90c830cd6f4aeb6c563f83d220c3f412c1fd0b0a358aea8a5`。兩包解壓後各驗 328 筆，遊戲執行檔與 Unity 建置結果的雜湊相符。玩家啟動器通過 19 項檢查。
- 伺服器包 `run-cfb53c5532a74372988d32d235ef1df9` 通過 147 項 Windows 命令列與原生整合檢查。核對五房獨立、全連線、MR 缺追蹤拒絕開場、場中增援和啟動器子程序收尾，共 812 幀完整回放、10 份原戰績 CSV。清理後 C／F 核對 92 份檔案。
- Windows 和 Quest 3 的來源指紋均為 `8deb359a48a40d8da8ff53aae8ccaaf9c56a919f26e9df16a9ec4ae963697728`，兩個目標的場景與玩家 Prefab 網路識別對上 0.46.0 建置收據。APK `artifacts/quest/VrCommand.apk` 為 60,957,982 bytes，SHA-256 `18d23e591223754c7d03af3e8bbb79b48491bfe168547db5e01c091b00bfbc14`。確認 ARM64／IL2CPP、版本碼 59、min SDK 32、target SDK 35、透視功能及 v2 Debug 簽章。頭盔實測待驗。0.46.0 歷史建置與日誌共 338 份已逐檔核對。
- WinForms 首輪 `run-a37a9be00cc64fd492d1b5f244dfa7fd` 在管理包初始化階段逾時，當時尚未建立視窗。逐檔核對的 C 槽管理包可完成第二輪 `run-7d32031bedf4458e998bf077a32b849c` 的初始化並顯示新版遊戲伺服器啟動器。畫面出現 `vrcommand.exe` 的 Windows 防火牆提示，桌面操作停在實例欄位之前。360 秒後測試結束，自己的 GUI 與管理程序已停止，C／F 核對 9 份檔案。此輪 WinForms 啟動流程待驗。
- [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42514739682) 對應上述來源，job `128835167649` 回報帳務或支出上限而未啟動，零步驟。另有本機 Python 套件檢查 18 項通過、1 項跳過。

| 25 端模式 | 舊版量測窗 | 新版量測窗 | 舊版下行 | 新版下行 | 下行減少 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 五房全連線 | 39.314 秒 | 39.194 秒 | 17.523 Mbit/s | 13.186 Mbit/s | 24.75% |
| 五房獨立 | 34.357 秒 | 31.410 秒 | 3.759 Mbit/s | 2.909 Mbit/s | 22.60% |

統計是本機 loopback 中轉送器接受的 UDP 負載位元率。全連線上行由 0.646 降至 0.642 Mbit/s，獨立房由 0.623 降至 0.620 Mbit/s。兩版實際量測窗長度不同，表中以各自的有效時間換算。跨機網路、實體網卡及頭盔待驗。 [量測方法](EXTERNAL_CLIENTS.md#同機-udp-流量量測)

## 2026-11-09 同機 UDP 流量量測

功能來源 `f40bc5f73b309b33ea12545a9c0fabbd3c998eab` 加入 `--udp-traffic`，以原 0.46.0 Windows 遊戲程序和 API 0.31.0 進行。每個玩家各有透明 loopback 轉送器，使用共同單調時間邊界核對雙向 UDP 負載，並彙整到各房、全場及約一秒區間。全連線觀察到 Begin 後開始，獨立另等暫停房間套用 Resume。 [操作與欄位](EXTERNAL_CLIENTS.md#同機-udp-流量量測)

- 14 項 UDP 與 17 項動態驗證測試通過。第一輪 Windows 快速封包測試遇到兩個時間戳相同。保留失敗後改用 Windows 上由 QueryPerformanceCounter 提供的單調高解析度計數，原單調前進斷言保留。原生既有 UDP 延遲回歸 `20261109-030219-8fc3207a` 通過 6 項。
- 同機無圖形自動操作 25 端的平均 UDP 負載如下。此輪關閉額外往返探測。

| 模式 | 共同量測秒數 | 上行 Mbit/s | 下行 Mbit/s |
| --- | ---: | ---: | ---: |
| 五房全連線 | 39.31 | 0.646 | 17.523 |
| 五房獨立，各五端 | 34.36 | 0.623 | 3.759 |

- 最終 `20261109-030309-c87fdc6e` 通過 20 項、3,937 幀完整回放、50 份原戰績及 6 份 CSV。全連線上／下行為 3,174,886／86,112,325 負載位元組，獨立為 2,677,686／16,143,230。逐玩家重算位元組差，核對原程序、原名冊、各連線的獨立轉送埠、38／32 個時間區間及暫停房間的恢復序號。50 個轉送器均正常停止。
- 五端預跑 `20261109-030149-b53cd744` 同時啟用往返量測，7 項檢查、150 筆探測、402 幀回放和 5 份原戰績通過。最終、預跑與延遲回歸清理後的 C／F 檔案分別核對 174、34、14 份。
- GitHub Actions 因帳務條件未啟動，工作共 0 個執行步驟。 [工具工作](https://github.com/peca12968/vr-command-center/actions/runs/42513081225/job/128830153949)
- 跨機、網卡層頻寬、渲染幀率、25 位真人、Quest 3／VIVE 實機及廠商硬體仍待驗。

## 2026-11-09 Windows 玩家連線量測

Windows 0.46.0 開發版可選用 `--vr-link-metrics`。玩家入場後，在 Running 狀態以同一 NGO 連線收集應用層往返時間與 Unity 更新頻率。伺服器只回覆仍連線的已核准玩家，最多保留 25 條連線的限速狀態。報表最多 30 筆，逐筆區分回覆、逾時及中斷。 [操作與欄位](EXTERNAL_CLIENTS.md#windows-玩家連線量測)

- 功能來源 `c6e5d2cab90d1d35815ba3a62e613149841a4af5` 通過 259 項 Unity Editor 與 17 項 Python 動態驗證檢查。首次 Python 負向案例發現可接受負的首筆 tick，修正後完整通過並保留首次日誌。管理服務沿用已驗的 API 0.31.0 與控制台 0.31.13。
- 五端預跑 `20261109-024104-148ea5bb` 通過 6 項、150 次有回覆的採樣、486 幀完整回放與 5 份原結果。最終由解壓伺服器包的 Unity 程序執行 `20261109-024412-1c14106c`。五房全連線 25 端及五房獨立各五端通過 20 項、4,501 幀完整回放、50 份原結果及 6 份 CSV。兩輪各 750 筆均收到回覆。全連線 p50／p95 約 11.09／22.24 毫秒，獨立約 11.07／22.18 毫秒。各程序更新頻率介於 89.79 至 90.00 Hz。這是同機無圖形自動操作的應用層量測。
- 0.45.0 伺服器未實作回覆的對照中，0.46.0 玩家仍可入場及接收原戰績，30 次均逾時。首輪 `20261109-024050-a8416255` 未通過即時輪詢斷言，保留 30 筆原逾時。重跑 `20261109-024324-a594f9d5` 以 772 幀完整回放核對 Running 的原玩家持續在線。清理後四輪 C／F 分別核對 224、34、15、15 份檔案。
- 最終 Windows 玩家包 `artifacts/player-packages/windows-player-0.46.0-metrics-ready.zip` 為 83,440,627 bytes，SHA-256 `2f0fd896bf6f59e44466ee3dbf648dd53f605b304f604547488214abd55a457d`。初包說明誤將執行檔列在 Runtime，修正後重新打包，初包保留。伺服器包 `artifacts/server-packages/windows-server-0.46.0-launcher1.4-win-x64.zip` 為 83,463,766 bytes，SHA-256 `a140c15df77668c1f060b34b28a4e6f443821271a7df350c13e3238feb0bd95b`。解壓各核對 328 筆，兩包的實際遊戲程式與建置收據相符。最終玩家啟動器 19 項離線檢查與伺服器原生套件核對通過。
- 用解壓伺服器包執行既有場次 `run-e031782385404e35bedff58d1b9cd952` 通過 135 項。五房獨立、全連線及 MR 準備共 612 幀回放，並核對 10 份原戰績與 10 份 CSV。清理後 C／F 的 85 份檔案相符。
- Unity 6000.3.27f1 同源建置 Windows 與 Quest 0.46.0，來源指紋 `f5a0b8f93dd01f6e7083a5499f35794d586e6d1dd30dc9f662ee6c4448520cdf`，場景及玩家 Prefab 網路識別沿用 0.45.0。APK `artifacts/quest/VrCommand.apk` 為 60,961,286 bytes，SHA-256 `d0ccb8e21a3256f03f1a37e5b1f599f4a07e72687189c94fcb115d47c49dffa4`。已核對 ARM64／IL2CPP、版本碼 58、min SDK 32、target SDK 35、透視功能及 v2 Debug 簽章。前版 338 份檔案已逐一核對並封存。
- GitHub Actions 因帳務條件未啟動，工作共 0 個執行步驟。 [功能工作](https://github.com/peca12968/vr-command-center/actions/runs/42510281112/job/128821658880)
- 頻寬、渲染幀率、跨機 25 位真人、Quest 3 與 VIVE 實機及廠商硬體仍待驗。

## 2026-11-09 場中敵軍增援

控制台 0.31.13 在管理服務寫入前檢查場地的敵軍上限。暫時沒有安全空位時，遊戲伺服器保留待補名額，場次與其他控制指令繼續運行。觀戰及回放顯示快照內的實際敵軍與存活數。 [操作與錄製規則](LAYOUT.md#場中敵軍增援)

- 舊核心實際接受上限 84 的場地設為 85 名，新增斷言在第 462 項後失敗，原日誌保留。功能來源 `ae6135b05941546e791f949e551e6f615a0c1c3e` 通過 825 項核心、603 項 HTTP、58 項世界串流和 258 項 Unity Editor 檢查。實際巡邏占住三個候選點時，新增 Editor 案例驗證缺額、原敵軍身分、雷雨、暫停、恢復後補入，以及減量後結束。錄製案例驗證舊版精確總數、新版準備幀精確總數，以及進行中按各房目標核對。
- 最終 92 項 Node 與 344 項 Chromium 通過。實際控制台把 85 名保留在表單並顯示 84 名上限，修正後可從同一表單提交。首輪使用相對證據路徑未開始 Chromium，第二輪舊文字斷言逾時，兩輪原件保留。管理包 `artifacts/control-packages/control-server-api0.31.0-ui0.31.13-win-x64.zip` 為 52,527,269 bytes，SHA-256 `f8bcf3400e521e43c2cf56c719ecc6e7a09ba5a6a0d734e5cb29daa5748dd3cb`，解壓核對 507 筆，`run-54b898f1ab804945a38d972a19ecfe05` 通過 106 項檢查。
- Windows 玩家包 `artifacts/player-packages/windows-player-0.45.0.zip` 為 83,437,249 bytes，SHA-256 `eb67ce40ec09196efa8a1bf83b9d5b4d84eb958b36862561cf54744f30924170`，實際啟動器通過 19 項檢查。伺服器包 `artifacts/server-packages/windows-server-0.45.0-launcher1.4-win-x64.zip` 為 83,460,502 bytes，SHA-256 `62a19a434465d6802369801a6cc6292f6b6be31b322821fb85d77f8fecf0881e`。兩包均解壓核對 328 筆。伺服器內附說明已更新至啟動器 1.4 與 VR／MR 部署。
- 實際 Windows 伺服器 `run-d3907229d7ff4c068542611c07f2a1ab` 通過 147 項，包含五房獨立、全館連線、MR 準備與增援。八場共 670 幀完整回放、11 份原玩家戰績與 10 份 CSV。增援場拒絕 85 名設定後，44 幀回放保存補到 84 名及減至 1 名並暫停的原快照，保留原敵軍識別。該場完成雙封存，遊戲伺服器確認一筆原玩家戰績。清理後伺服器 C／F 的 92 份檔案及管理包的 27 份檔案相符。
- Unity 6000.3.27f1 同源建置 Windows 與 Quest 0.45.0，來源指紋 `5fcc0b34cc747cab4b24fccae00dfe08f0c9110f6bfe77cbb88f7d3a370351e8`，場景與玩家 Prefab 網路識別沿用 0.44.0。APK `artifacts/quest/VrCommand.apk` 為 60,954,218 bytes，SHA-256 `d01af1575643b7e414b60000bf1cf0c4d8ae1484913d150b98b41c0e12f1a0c5`，已核對 ARM64／IL2CPP、版本碼 57、min SDK 32、target SDK 35、透視功能及 v2 Debug 簽章。首輪 Windows 快取存取失敗日誌保留，重跑成功。上一版 338 份檔案已逐一核對並封存。
- GitHub Actions 因帳務條件未啟動，工作共 0 個執行步驟。 [功能工作](https://github.com/peca12968/vr-command-center/actions/runs/42508501461/job/128816255866)
- Quest 3 實機、VIVE、跨機 25 位真人和廠商硬體仍待驗。

## 2026-11-09 主控建立 MR 場次

控制台 0.31.12 可從已保存的 MR 任務建立單房或五房全連線場次。虛擬配置沿用共用場地規則，Windows 伺服器啟動器 1.4 提供 MR 選項。遊戲伺服器核對 Quest 3 名冊、票券及入場校正房間。開始命令要求最新 GameServer 錄製幀對上場次管理序號與全名冊的有效追蹤姿態。場次模式固定，主控仍可調整天氣、時段和雷電。 [部署與開場](QUEST3.md#主控建立-mr-場次)

- 遊戲來源 `06924fab1d9093651a5d11ee92e72e28a4754375` 通過 257 項 Unity Editor 測試及五項模擬 ADB 部署案例。API 與提示來源 `3247b57bebae1c936a81ff006c895ccf164b49c8` 通過 818 項核心、594 項 HTTP、58 項世界串流、92 項 Node 與 342 項 Chromium 檢查。核心測試以兩房測試追蹤資料驗證少人、過期、管理序號更新、跨權限和重試。瀏覽器實際建立 MR 場次，確認尚無有效追蹤時拒絕開始、保留名冊並顯示等待追蹤的提示。首輪檢查停用選項時中止，第二輪以原生 DOM 驗證後通過，第三輪核對新版提示。三輪日誌與截圖分別保留。
- 最終控制台管理包 `artifacts/control-packages/control-server-api0.31.0-ui0.31.12-mr-ready-win-x64.zip` 為 52,524,955 bytes，SHA-256 `a854f243d97d04122e380fe1cc6e1689e5106c2dfc1bca7b61ecfe81622e3c16`。解壓核對 507 筆檔案，自含 .NET 10.0.14，`run-54ca2655ff904ef78ee054f8964665c6` 通過 106 項檢查。最初管理包的 106 項結果另行保存，兩次清理後各核對 C／F 的 27 份檔案。建置前已依 SHA-256 封存前版 338 份執行檔、收據與 Unity 日誌。
- Windows 玩家包 `artifacts/player-packages/windows-player-0.44.0.zip` 為 83,437,123 bytes，SHA-256 `c64f61a38dd30c4e674672f5c0d029b5f0c3187f65d37a5e089d385e52e55a45`，解壓核對 328 筆，實際啟動器通過 19 項離線檢查。首輪伺服器包在 VR 場次通過後，因寫入 Simulation 而無法啟動 MR。原 `run-f0a9ee77f0d94617b2d1e9ec998953f8` 退出失敗，清理後保留 C／F 相符的 76 份檔案。啟動器修正來源 `87a579af2a0bcd72c8274090179e45676832aac9`，依管理模式選擇 GameServer 或 Simulation，並核對就緒與封存的來源。新版包 `artifacts/server-packages/windows-server-0.44.0-launcher1.4-mr-ready-win-x64.zip` 為 83,460,355 bytes，SHA-256 `5405d1e309d002d56be3dbc3abc060330499b6844e671c58858d49eff4a31e47`。
- 修正來源的伺服器包通過 135 項，五房獨立與全館連線六場共有 554 幀 VR 回放、10 份原玩家戰績及 10 份 CSV。另有一場實際 MR 伺服器共 27 幀回放，拒絕桌面票券，缺追蹤的 Begin 維持 Preparing，成功套用雷雨夜、完成雙封存並保留 36 秒後收尾。原生程序和管理服務清理完成，C／F 的 85 份檔案相符。清單測試另通過 38 項 CLI 與 33 項實際 Framework 檢查，C／F 的 14 份檔案相符。
- Unity 6000.3.27f1 成功建置 Windows 與 Quest 0.44.0，兩端來源指紋均為 `92ff455649f16bdf686e62a1da705e686f3d79d6659c2c09d3cd88a49d0068bc`，原場景和玩家 Prefab 網路識別相同。Quest APK `artifacts/quest/VrCommand.apk` 為 60,911,034 bytes，SHA-256 `713af54b0052423af72295a40e6bb3ada9edbbdddda04f840b8489fb09afc614`。已核對 ARM64／IL2CPP、版本碼 56、min SDK 32、target SDK 35、透視功能為必要、Meta 原生函式庫及有效的 v2 Debug 簽章。
- 觀察實際 Windows 視窗時發現清單標籤仍只寫 VR，`ba756db68871bcdd647da858f2629f069e4e04ed` 改為「尚未綁定來源的 VR 或 MR 場次」。最終伺服器包 `artifacts/server-packages/windows-server-0.44.0-launcher1.4-win-x64-final.zip` 為 83,460,353 bytes，SHA-256 `05e763eb4b449c55fe438a7dadecf93a9375007ca09cc82b28a2a5a7f463be0d`，解壓後逐一核對 328 筆清單。
- 最終伺服器包重跑 `run-630f229dfc28420b9d7e31bf704ebeba` 通過 135 項，六場 VR 共 511 幀回放、10 份原玩家戰績與 10 份 CSV，另有 22 幀 MR 準備與封存回放。清單 `run-aea316a28543414e8a419d5f704d76a4` 重跑通過 38 項 CLI 與 33 項 Framework 檢查。清理後各有 85 與 14 份 C／F 相符檔案。
- WinForms 重驗 `run-858894feba4142f4bf3eb8cb02494b58` 已輸入測試管理實例路徑。Windows 防火牆提示遮住啟動器，桌面操作停在載入前。測試在 360 秒後逾時，測試程序清理完成，C／F 的 9 份檔案相符。此輪完整視窗流程待驗。
- GitHub Actions 的四個工作因帳務條件未啟動，各為 0 個執行步驟。 [遊戲與管理工作](https://github.com/peca12968/vr-command-center/actions/runs/42505158151/job/128806100237) · [主控提示工作](https://github.com/peca12968/vr-command-center/actions/runs/42505963940/job/128808548490) · [啟動器工作](https://github.com/peca12968/vr-command-center/actions/runs/42506218411/job/128809319448) · [啟動器標籤工作](https://github.com/peca12968/vr-command-center/actions/runs/42506810174/job/128811100682)
- Quest 3 實機入場、透視與遮擋、跨裝置定位、VIVE 相容、跨機 25 位真人及廠商硬體仍待驗。

## 2026-11-09 Quest 3 透視呈現

Unity 0.43.0 為既有 VR 場次加入 Quest 3 的選用透視呈現。玩家部署時附經檢查的房間校正檔，以 Meta OpenXR 合成層呈現實景，再套用當次 A、B、C 量測。虛擬擺設、敵軍、HUD、雨線和聲光沿用場次，地板保留碰撞。合成層或校正未就緒時暫停姿態及武器輸入。 [操作說明](QUEST3.md#quest-3-透視呈現)

- 遊戲來源 `55c52924fd6b3266840c6d09c54734d38b69b2a1` 通過 800 項核心、581 項 HTTP、58 項世界串流與 257 項 Unity Editor 測試。新增測試核對透明背景、地板與擺設、日夜與閃電，以及暫停或離場後復原混色。四個模擬 ADB 案例核對透視部署與校正檔門檻。
- Unity 套件解析為 Meta OpenXR 2.3.2、AR Foundation 6.3.5、Composition Layers 2.6.0。首輪 Windows 編譯因 Meta 原生相機型別未提供給 Windows 玩家而中止，已限制 Android 才編譯該段。保存首輪日誌、初次 256 項 Editor 結果及新版結果。
- Windows `20261109-005746-df4eee80` 通過 18 項同機檢查。五房連線與五房獨立各五名模擬玩家，六場共 2,013 幀完整回放、10 份原玩家戰績、10 筆伺服器確認及 6 份 CSV。清理後 C／F 的 54 份檔案相符。
- 打包來源 `be219c9c16fae4e0a6dea612255ec7362ee3b9ff` 只接受官方 Meta OpenXR 2.3.2 的原始子系統清單路徑與 SHA-256。兩個打包器首輪拒絕均保留，7 項玩家打包及 4 項伺服器打包測試通過，1 項 Windows 符號連結測試因權限跳過。
- Windows 玩家包 `artifacts/player-packages/windows-player-0.43.0.zip` 為 83,435,594 bytes，SHA-256 `92d92feb5e6c5662febece326843666344ec0363178787357b92d1917b528fa0`。伺服器包 `artifacts/server-packages/windows-server-0.43.0-launcher1.3-win-x64.zip` 為 83,458,671 bytes，SHA-256 `241c265916c255bd831eb85e4fe4d30380420e05b6ecfe9fdd500455c5149406`。解壓後各核對 328 筆清單，實際玩家啟動器通過 19 項離線檢查。建置前以 SHA-256 封存前版的 321 份執行檔、收據及 Unity 日誌。
- 解壓伺服器包搭配管理包 0.31.11 的 `run-63bf6d7a062649c687e5ad4ba18f1790` 通過 124 項。五房獨立與全館連線各有五名同機模擬玩家，六場共 729 幀完整回放、10 份原玩家戰績及 10 份 CSV。另驗證終止啟動器後，Windows 結束原來的遊戲子程序。清理後 C／F 的 78 份檔案相符。
- Windows 與 Quest 均由 Unity 6000.3.27f1 建置，來源指紋 `adb23d4c4ffc676b13e1ffa9ebdf64500246eca6a42eadb332e9bd49790e849e` 相符，場景及玩家 Prefab 的網路識別均與 0.42.0 相同。Quest APK 為 60,904,794 bytes，SHA-256 `50274106959cac356af56a144166c7e4f6042d3901ea980f0510f3d323f66211`。已核對 ARM64／IL2CPP、版本碼 55、min SDK 32、target SDK 35、v2 Debug 簽章、Meta 原生函式庫及 `com.oculus.feature.PASSTHROUGH`。首輪核對漏比對 aapt 的縮排行，重新檢查同一個 APK 確認透視功能標記為必要。證據存於 `artifacts/quest-passthrough-0.43.0`。
- GitHub Actions 的功能與打包工作均因帳務條件未啟動，各為 0 個執行步驟。 [功能工作](https://github.com/peca12968/vr-command-center/actions/runs/42502509011/job/128798109302) · [打包工作](https://github.com/peca12968/vr-command-center/actions/runs/42502843815/job/128799110749)
- Quest 3 實景、物件遮擋、場控建立 MR 場次、VIVE 相容、跨機 25 位真人及廠商硬體仍待驗。

## 2026-11-09 Unity 場地對位

Unity 0.42.0 可讀取入場房間的校正檔。在 Preparing 或 Paused 以左扳機依序記錄 A、B、C，通過 5 公分門檻後，將同一個追蹤空間套用到頭部、雙手及瞄準方向。地板原點更新或程式暫停會要求重新量測。伺服器仍以最後接受的位置檢查姿態，初次從指定出生位起算。 [操作說明](LAYOUT.md#quest-3-場地對位)

- 來源 `d50419de6db7234bdceb06c93ae01624599fe99c` 通過 800 項核心、581 項 HTTP、58 項世界串流及 254 項 Unity Editor 測試。12 項新增 Editor 測試以 Unity Transform 核對頭手平移、旋轉、錯房、鏡像、誤差邊界和追蹤失效。以管理台實際匯出的第五房 JSON 驗證三個模擬 ADB 案例，包括一般部署、校正檔先於玩家設定啟用，以及校正檔複製失敗時停止。
- Windows 測試 `20261109-002658-1ca14efd` exit 0，18 項通過。五房連線與五房獨立各有五名同機模擬玩家以原遊戲輸入移動、射擊及換彈。六場共 2,022 幀完整回放、10 份原玩家戰績、10 筆伺服器確認及 6 份場次 CSV。測試程序清理完成，C／F 的 54 份原始檔相符。
- F 槽的 Windows 0.42.0 玩家包 `artifacts/player-packages/windows-player-0.42.0.zip` 為 82,659,739 bytes，SHA-256 `ad52280f49bc9e423a901b7da85fac2aad3eb8fc979b73fb89418f57f02edf7f`。伺服器包 `artifacts/server-packages/windows-server-0.42.0-launcher1.3-win-x64.zip` 為 82,682,413 bytes，SHA-256 `1b0551a427c9403c42ca41892b66456849e4fe636f7e24861e1a53d4c76c18f5`。兩包解壓後各核對 311 筆清單，實際玩家啟動器另通過 19 項離線檢查。首次額外核對以系統預設編碼讀取 UTF-8 清單中止，改用 UTF-8 後完成。先以 SHA-256 封存 321 份前版二進位、收據及 Unity 日誌。
- Windows 及 Quest 0.42.0 均由 Unity 6000.3.27f1 成功建置，來源指紋 `31a66d41e61219075ade72e95f3b52df0551d151d0873f9eecfda2dc1f0cf5de` 相符，兩端場景和玩家 Prefab 的網路識別均與 0.41.2 相同。Quest Development APK `artifacts/quest/VrCommand.apk` 為 60,378,130 bytes，SHA-256 `b834e0d0662371edadc22d28f568ae7c7a100d1d8de046de83f8608c172f20a1`。Android 工具核對 ARM64、版本碼 54、min SDK 32、target SDK 35 和有效 v2 Debug 簽章。收據、日誌及核對結果存於 `artifacts/unity-floor-alignment-0.42.0`。
- GitHub Actions 42499467687／128788839838 因帳務條件未啟動，共 0 個執行步驟。 [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42499467687/job/128788839838)
- Quest 3 實機取樣、地板高度、MR 透視、VIVE 相容、廠商硬體及 25 位真人仍待驗。

## 2026-11-08 MR 場地水平校正試算

控制台 0.31.11 可在任務編輯頁選房，輸入三組遊戲與追蹤的地面座標。A、B 用來計算旋轉與位移，C 獨立核對。三點的平面誤差均在 5 公分內才可下載 JSON。 [操作與座標契約](LAYOUT.md#mr-場地水平校正試算)

- 來源 `d9487848cdffb9b5d3227bdd7130aa27a83bd589` 通過 .NET Release 建置和 800 項核心檢查，新增八項涵蓋原房間原點、鏡像、尺度、5 公分邊界、非軸向旋轉、退化幾何及輸入範圍。首輪瀏覽器把缺欄位的空 HTTP 400 當成 JSON 解析，測試改為直接驗證狀態。下一輪通過校正專項，但整輪未產生完成紀錄。恢復後的首次重跑遇到暫存 API 執行檔已不存在，改從同一來源重新建置。三輪原日誌均保留。
- 11 月 9 日的解壓管理包 `run-cc2cdfd4b5ac4ad48e3f47544da5a29f` 通過 106 項 Windows 檢查，實際自含 API 算出第五房的 90° 旋轉，並拒絕房控呼叫校正端點。清理後 C／F 的 27 份原始檔相符。 [管理包](WINDOWS_CONTROL_PACKAGE.md)
- 瀏覽器重跑曾因本機缺少 Chromium 中止，F 槽安裝測試瀏覽器又遇到檔案鎖更新失敗。原日誌保留，改以 C 槽快取安裝 Playwright 鎖定版本的 Chromium headless shell。
- 11 月 9 日重新編譯後，92 項 Node 與 340 項 Chromium 檢查完整通過。瀏覽器實際下載第五房 JSON，逐欄對上 API 回應，並核對鏡像誤差、修改後停用舊匯出及 390 像素版面。校正不會變更任務版本。
- GitHub Actions 42110672529／127537068586 因帳務條件未啟動，沒有執行步驟。 [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42110672529/job/127537068586)
- 頭盔取樣、實際套用、地板高度、透視、跨機、廠商硬體與 25 位真人仍待驗。

## 2026-11-06 遊戲伺服器公告前的 UDP 綁定核對

Windows 啟動器 1.3 在公告之前，核對遊戲子程序實際擁有的本機 UDP 位址及埠。就緒和結果檔保留啟動時的觀察，公告仍記錄玩家要連到的地址。 [部署與檔案欄位](WINDOWS_SERVER_PACKAGE.md#本機-udp-綁定確認)

- 來源 `8e1100a3abf53dc1b3705ead4eb4bea54457542d` 重新編譯 Framework 啟動器，沿用 0.41.2 的 304 份原遊戲執行檔及相依檔。解壓清單 311 筆均已核對。4 項打包工具檢查，以及 `run-e7b94fae4e4d4a05b9ad09f2042414bd` 的 38 項 CLI 和 33 項 Framework 檢查通過，其中 7 項使用實際 UDP socket 核對正確與錯誤 PID、埠、地址及關閉後狀態。清理後 C／F 的 14 份原始檔相符。
- 私有乙太網路位址的三包整合 `run-a881c6850b1744e0ac6f62b3c9462d55` exit 0，374 項通過。Windows 的獨立查詢核對了五個單房端點、一個 Linked 端點及中斷場次的萬用綁定。五房獨立及五房連線各有 25 個同機模擬玩家，六個正常場次共 910 幀、50 份原玩家戰績及 5 份分房 CSV。中斷場次的 23 格仍可回放。清理後 C／F 的 223 份原始檔相符。
- 預設 `127.0.0.1` 的兩包整合 `run-88306d4da6e4472c8db69622123fa539` exit 0，124 項通過。六個正常場次共 506 幀、10 份原玩家戰績。六個明確綁定及一個萬用綁定均經 Windows 獨立查詢確認。清理後 C／F 的 78 份原始檔相符。
- GitHub Actions 42108137984／127528314944 因帳務條件未啟動，沒有執行步驟。 [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42108137984/job/127528314944)
- 1.3 的 WinForms 狀態顯示、跨機、頭盔、廠商硬體與 25 位真人仍待驗。

## 2026-11-06 中斷場次的已保存回放

控制台 0.31.10 在任務收尾顯示已接受的戰鬥筆數與已保存的錄製格數。未封存錄製可回放已保存片段，從第一格播放，在開啟時固定的尾端停止。逐格、時間跳轉、倍速與續播沿用該尾端。 [操作與介面](WORLD_RECORDING.md#回放未封存的已保存片段)

- 來源 `11009cc928de807dfc72defa2c3fee4631fc85d6` 通過 .NET Release 建置、792 項核心及 58 項世界串流。串流核對從第一格開始、固定較短的範圍、時間跳轉的上界、自然關閉，以及完整來源既有封存狀態。首次瀏覽器測試在切換場次後操作了隱藏的倍速控制，原逾時與畫面保留。測試改在原場景仍可見時設定倍速。
- 完整重跑通過 92 項 Node 與 331 項 Chromium。瀏覽器核對實際中斷來源的保存數量、尾端與逐格後續播，並確認最終 CSV 仍停用。當次畫面停在第 17 格，顯示未封存及保存當時的快照階段。
- Windows 整合 `run-116c4e1e5ceb441f803aad69e49e3eeb` exit 0，111 項通過。既有 0.41.2 的六個正常場次共 531 幀、10 份玩家戰績，第一房由主控畫面結束並確認原封存。另一場有一名同機模擬玩家，錄到 20 點傷害後終止其啟動器，核對原遊戲程序退出。管理端結束場次後，依序回放已保存的 22 格，尾端血量 80，戰鬥已接受 1 筆。兩種最終 CSV 均回 409，原玩家沒有收到最終結果。清理後 C／F 的 82 份原始檔相符。 [Windows 整合驗證](WINDOWS_SERVER_PACKAGE.md#三個可攜包整合驗證)
- 管理包 `run-197be69d5adf4a6488f08a181ad852c8` 從交付 ZIP 重新解壓後通過 105 項 Windows 檢查，清理後 C／F 的 27 份原始檔相符。 [管理包](WINDOWS_CONTROL_PACKAGE.md)
- GitHub Actions 42106207634／127521593270 因帳務條件未啟動，沒有執行步驟。 [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42106207634/job/127521593270)
- 實際跨機、頭盔、廠商硬體及 25 位真人仍待驗。

## 2026-11-06 任務回放逐格檢視

控制台 0.31.9 可暫停回放，逐格查看保存的射擊、命中、擊殺、受傷及換彈事件。同格事件與統計共用原快照，續播從選定的快照序號開始。即時觀戰沿用原介面。 [操作與介面](WORLD_RECORDING.md#暫停逐格檢視)

- 來源 `1947ff46a16b1e9098fa8de6ca722f2976cdf210` 通過 .NET Release 建置、792 項核心、53 項世界串流、91 項 Node 及 327 項 Chromium。世界串流驗證房間權限、範圍、精確續播與重啟後同一格的事件和統計。瀏覽器從封存尾端逐格退回，核對第二房保存的 20 點傷害並用原序號續播。首次世界串流測試的隔離目錄缺少工具所需的專案標記，該次失敗已保留，補上原標記後重跑通過。
- Windows 0.41.2 使用既有遊戲執行檔。`20261106-042955-da8f0abc` exit 0，五房連線各一個同機程式自動操作，6 項檢查、178 幀完整回放、5 份原玩家戰績及伺服器確認回條。單格 API 回傳第 30 格的五筆射擊，續播第 30、31 格逐欄對上全場回放。清理後 C／F 的 29 份原始檔相符。
- 管理包 `run-fa4610fcad1c4943852943cef4d3977d` 從交付 ZIP 重新解壓後通過 105 項 Windows 檢查，清理後 C／F 的 27 份原始檔相符。 [管理包](WINDOWS_CONTROL_PACKAGE.md)
- GitHub Actions 42103740969／127513006266 因帳務條件未啟動，沒有執行步驟。Windows 鍵盤穿越、跨機、頭盔、廠商硬體及 25 位真人仍待驗。 [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42103740969/job/127513006266)

## 2026-11-06 五房戰績分房匯出

控制台 0.31.8 支援五房連線場次按房匯出已封存的戰績 CSV。主控可選全場或單房，房控畫面固定為自己的房間，分房端點拒絕跨房請求。分房保留已離場玩家以及原場次、事件與封存序號。空房提供一列場次資料。 [報表欄位與權限](REPORTS.md#五房分房匯出)

- 來源 `9e19232543a59478f3bbf5b4fdc3ea262533b8ea` 通過 .NET Release 建置、792 項核心、91 項 Node、322 項 Chromium 及 105 項解壓管理包檢查。Chromium 使用主控及房控實際下載第二房和第一房報表，分別與同一分房 API 的回應逐位元組相符。管理包測試 `run-e2df992e83b843bdaedd4b2af35b6db4` 清理後 C／F 的 27 份檔案相符。 [管理包](WINDOWS_CONTROL_PACKAGE.md)
- Windows 三包測試 `run-28c1bd25fb2b41c2992f0f259e0fba1c` exit 0，348 項通過。使用既有遊戲 0.41.2，五房獨立與五房連線各有 25 個同機模擬玩家，六場共 851 幀完整回放、50 份原玩家戰績及 6 份場次 CSV。新增的五份分房 CSV 各有五列，逐列對上同一場封存全場報表，跨房回應 403。清理後無剩餘測試程序，C／F 的 221 份檔案相符。 [三包驗證](WINDOWS_SERVER_PACKAGE.md#三個可攜包整合驗證)
- 完整 Windows HTTP 回歸三次均在分房斷言前中止，分別遇到暫存日誌仍被占用、競爭寫入者程序未在原 10 秒內退出，以及無效憑證啟動測試程序未在原 10 秒內退出。原紀錄保留。GitHub Actions 42100962160／127503314612 因帳務條件未啟動，沒有執行步驟。 [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42100962160/job/127503314612)
- 實際跨機、頭盔、廠商硬體與 25 位真人仍待驗。

## 2026-11-06 通路預覽的移動判定與鍵盤驗收準備

核心新增同一席位的對照。完整沙包牆前，原入場玩家可走到牆側，落在掩體內與試圖跨牆的姿態皆被拒絕。移除正前方沙包後，共用遊戲權威端接受預覽中從出生位到中線的七個取樣點。來源 `14f6d460205d5dd57af2047a4ed10b7e109b3512` 的 .NET Release 建置與 785 項核心檢查通過。 [通路預覽](LAYOUT.md#出生位通路預覽)

- Windows 鍵盤工具以已儲存的兩個任務版本比對原席位。首次 `20261106-035625-3cea982c` 缺少修訂的冪等請求鍵，API 回應 400，exit 1，C／F 的 12 份檔案相符。工具已補上請求鍵。
- 第二次 `20261106-035702-61a3a9d2` 啟動了真正遊戲並核對原出生位、名冊及沙包座標。既有 Windows 防火牆提示遮住測試遊戲，等待第一階段鍵盤確認逾時，exit 1，接受的鍵盤測試為零。收尾封存 1741 幀，C／F 的 14 份檔案相符，兩次均確認程序已退出。實際 Windows 鍵盤穿越仍待提示關閉後重跑。
- GitHub Actions 工作 42099308275／127497581684 因帳務條件未啟動，沒有執行步驟。跨機、頭盔、廠商硬體及 25 位真人仍待驗。 [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42099308275/job/127497581684)

## 2026-11-06 任務配置出生位通路預覽

控制台 0.31.7 在草稿配置圖畫出五席到中線的取樣通路，並在開場區顯示已儲存版本的摘要。服務使用 0.5 公尺格點，逐段使用遊戲實際的通行判定。六個貼齊的沙包可讓基本配置通過，但會讓五席沒有取樣路徑。移開一個沙包後五席皆可經缺口到中線。操作員仍可選用原防線。 [預覽與契約](LAYOUT.md#出生位通路預覽)

- 來源 `f6131a5ba122ab809591c1df67b2f08637a9ccc1` 通過 783 項核心、571 項 HTTP、47 項世界串流、91 項 Node、318 項 Chromium 與 105 項解壓管理包檢查。瀏覽器實際移除沙包、儲存修訂，並確認原版本仍顯示缺少通路。
- Windows 三包測試 `run-67f2f10376634fcebb3b99cd1a54d4ef` exit 0，355 項通過。五房獨立與五房連線各 25 個同機模擬玩家。六場的 30 條預覽路線均通過同一缺口，封存世界共 50 個沙包座標與保存版本相符。共 889 幀完整回放、50 份戰績、6 份 CSV，第一房由控制台結束後核對世界封存序號 211。清理後 C／F 的 221 份原始檔相符，管理包測試另有 27 份相符。通路逐段由共用 C# 通行判定驗證，本輪原生場的玩家維持在出生區。
- Windows 管理包採 API 0.31.0，遊戲使用既有 0.41.2。預覽適用玩家平面取樣，運行中的敵軍路線、實際跨機、頭盔、廠商硬體與 25 位真人仍待驗。GitHub Actions 工作 42097466387／127491166056 因帳務條件未啟動。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42097466387/job/127491166056)

## 2026-11-06 五房有效姿態總覽

控制台 0.31.6 在房卡分列名冊、有效姿態、合成和追蹤人數。主控可同時查看五房，房控只收到自己的房間。五房連線由同一份已接受快照分房計數。畫面不沿用過期、錯場次或讀取失敗的有效人數。 [欄位與操作方式](PLAYER_READINESS.md#五房總覽)

- 來源 `c9cc3bb04591c8763eee88225b0be990991adf4b` 通過 778 項核心、567 項 HTTP、47 項世界串流、91 項 Node、314 項 Chromium 與 105 項解壓管理包檢查。瀏覽器的追蹤數字以測試回應驗證顯示。HTTP 實際驗證匿名與遊戲伺服器角色拒絕、房控只讀自己的房卡及主控讀取五房。
- Windows 三包測試 `run-9d6a1bccc3964d6c9964c6f6ccb6e4a7` exit 0，343 項通過。五房獨立與五房連線各有 25 個同機模擬玩家，兩種模式的房卡資料皆為每房 5 筆合成、0 筆追蹤。新版控制台在五個獨立房間同時運行時顯示所有房卡，從畫面送出第一房的 End 後，世界封存序號 194 對上原伺服器。共 831 幀完整回放、50 份戰績與 6 份 CSV。清理後 C／F 的 221 份原始檔相符，管理包另有 27 份清理後檔案相符。
- Windows 管理包仍採 API 0.31.0，遊戲使用既有 0.41.2 建置。GitHub Actions 工作 42095436816／127484096337 因帳務條件未啟動，沒有執行步驟。跨機、頭盔、廠商硬體及 25 位真人仍待驗。 [管理包](WINDOWS_CONTROL_PACKAGE.md) · [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42095436816/job/127484096337)

## 2026-11-06 五房控制台場次隔離

控制台 0.31.5 修正背景更新期間的場次切換。若選取的場次離開清單，控制台會清空選取並隱藏原操作區。下一筆操作須明確選取場次。操作者已按下但尚未送出的操作會核對原場次，場次已結束或不符時停止。原 End 回條仍保留場次與封存進度。 [操作與隔離方式](SESSION_CLOSURE.md#場次切換與操作)

- 舊版 0.31.4 的兩房受控反例在 `console-room-fence-before` 保留。瀏覽器按下場次 A 的暫停，在外部結束 A 與刷新完成後，實際送出一筆對 B 的暫停，B 變成 Paused。新版重跑時送出零筆，B 維持 Running，選取清空。明確選擇 B 才成功送出一筆正確命令。
- 來源 `2caf8a2944ee39eb49a46226c96109d3091cda98` 通過 89 項 Node、309 項完整 Chromium、20 項聚焦 Chromium 及 105 項解壓管理包檢查。實際解壓包另重跑 20 項聚焦 Chromium。管理包測試清理後 C／F 的 27 份檔案 SHA256 相符。新版管理包使用 API 0.31.0，Unity Windows 與 Quest APK 沿用 0.41.2。 [管理包與 SHA256](WINDOWS_CONTROL_PACKAGE.md)
- 三包測試 `run-7159b1e3b14d4fe69517b0979034a681` exit 0。兩種模式各 25 個同機模擬玩家，338 項、932 幀完整回放、50 份戰績及 6 份 CSV。第一房使用新版控制台實際送出一筆 End，原場次與來源留在頁面，世界封存序號 199 對上原伺服器報告。清理後無活動場次，C／F 的 221 份原始檔 SHA256 相符。
- GitHub Actions 工作 42092953218／127475496332 因帳務條件未啟動，沒有執行步驟。實際跨機、頭盔、廠商硬體及 25 位真人仍待驗。 [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42092953218/job/127475496332)

## 2026-11-06 Windows 遊戲伺服器來源診斷

遊戲 0.41.2 與 Windows 伺服器啟動器 1.2 新增 `--peer-diagnostics on`。核准玩家入場後，專用伺服器從 Unity Transport 取得實際來源位址與 UDP 埠，依原連線編號記錄。每次啟動上限 256 筆。預設關閉，含來源位址的日誌留在私人工作資料夾。 [部署與跨機核對方式](WINDOWS_SERVER_PACKAGE.md#跨機來源診斷)

- 來源 `7f0d98decb2b0e125799d037d1b5b011eb0542d7` 的 `run-3951b15ccdd441aca65bd8a63acf8c61` exit 0。使用實際解壓的三包，兩種模式各 25 個同機模擬玩家，335 項、778 幀回放、50 份戰績及 6 份 CSV。Linked 的 25 筆來源端點都有不同 UDP 來源埠，全部對應原入場編號與伺服器戰績確認回條。五個獨立房間預設無來源列，無效診斷參數被拒絕且未啟動戰場。
- 清理後無活動場次及本輪程序，C／F 的 219 份原始檔 SHA256 相符。新版兩個 Windows ZIP 各有 311 筆檔案清單，玩家包的 19 項解壓測試通過。原 0.41.1 Windows、APK 及 Unity 日誌共 321 份已在 C／F 核對保存。 [伺服器包](WINDOWS_SERVER_PACKAGE.md) · [玩家包](WINDOWS_PLAYER_PACKAGE.md)
- 242 項真正 Unity EditMode 測試全數通過。Windows 與 Quest ARM64 的指紋同為 `bf9299c57e1afd0b3531abf6b0891aee01e55d0b68360ce74531973b55aff379`，場景與玩家網路識別沿用原值。APK 60,362,730 bytes，SHA256 `a9abe4fa6ed41a9afb088dcd6cec72d2e139c3dd8c88630ee4e3234a6ef114e3`，版本 53，minSDK 32、targetSDK 35、v2 開發簽章。 [Quest 3 工具鏈](QUEST3.md)
- 本輪來源紀錄由同一台 Windows 電腦的乙太網路 IPv4 驗證。實際跨機、頭盔、廠商硬體及 25 位真人仍待驗。精確來源的 GitHub Actions 工作 42091327531／127469817419 因帳務條件未啟動，沒有執行步驟。 [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42091327531/job/127469817419)

## 2026-11-06 Windows 三個可攜包整合

使用現有管理包 0.31.4、遊戲伺服器與玩家包 0.41.1，在同一台 Windows 電腦以乙太網路 IPv4 驗證整房配票。五個獨立房間各開一個伺服器，五房連線模式共用一個伺服器。兩種模式各有 25 個模擬玩家同時入場。10 份房間 ZIP 由各房控向實際管理包下載，玩家啟動器直接使用 ZIP 內的席位 JSON。 [部署與重現方式](WINDOWS_SERVER_PACKAGE.md#三個可攜包整合驗證)

- 來源 `df70e9d2745a76fa590d03a3900754d0fe60101b` 的 `run-426f9c0ec56c4942888306e05cb9d91a` exit 0，319 項通過。六場共 812 幀完整回放，50 份戰績與 6 份 CSV、戰鬥與世界封存及原連線的伺服器確認回條一致。另有一場刻意終止伺服器啟動器，驗證自己的子程序隨 Job 停止，該場未封存。
- 玩家收到戰績並離線後，測試持原程序 handle 結束仍執行的玩家程式，再確認啟動器回報同一程序退出。清理後沒有本輪程序或活動場次，C／F 的 218 份原始檔 SHA256 相符。三個既有交付 ZIP 的 SHA256 與先前紀錄一致。
- 原 loopback 模式在同一來源的 `run-593e8ebeb6fb47a3885481a162eb54fe` 重跑成功。103 項、518 幀回放、10 份戰績，清理後 C／F 的 78 份檔案 SHA256 相符。另驗證僅提供其中一個新選項、使用 loopback 位址或使用未配置的私有位址均會拒絕。
- 本次使用背景 CLI 與靜止模擬玩家，實際跨機、頭盔、廠商硬體及 25 位真人待驗。Python 包裝測試執行 18 項，17 項通過、1 項跳過。精確來源的 GitHub Actions 工作 42086684963／127453575830 因帳務條件未啟動，沒有執行步驟。 [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42086684963/job/127453575830)

## 2026-11-06 整房配票 ZIP

控制台 0.31.4 新增整房配票。選擇房間後一次下載最多五份 JSON，檔名標示房間與席位。主控可逐房下載，房控限自己的房間，Linked 場次也採相同權限。API 對照一次名冊快照的完整玩家與 admission，若選取過期或場次已結束，回應 409。遊戲端以當前 admission 驗票。 [操作與 API](EXTERNAL_CLIENTS.md)

- 來源 `bba38f0872f5735a941b4f16b9d0fbe35e826c86` 的本機 HTTP 回歸通過，逐一驗證五房 ZIP 共 25 份連線檔的場次、房間、席位與 admission。另通過 89 Node、304 Chromium、7 Python 與 105 項解壓管理包檢查。保留 51 份瀏覽器證據，管理包測試的 C／F 共 27 檔 SHA256 相符。
- 管理包 `control-server-api0.31.0-ui0.31.4-win-x64.zip` 為 52,489,449 bytes，SHA256 `158e4d10e5bde2e347f3661cbbfeefbe57231668e5ee5f7b7b1aba3a6198d18b`，504 項清單、ZIP 505 項，包含 484 項執行環境檔案。 [Windows 管理包](WINDOWS_CONTROL_PACKAGE.md)
- `0a1b0a6` 的原生測試工具在 `20261106-023142-bf225ec0` 從實際瀏覽器下載房間 ZIP，兩位玩家以解出的席位檔入場。9 項通過，兩份戰績與世界封存序號 180 一致。兩個工具均 exit 0，清理後 C／F 共 14 檔 SHA256 相符。此場為同機乙太網路 IPv4 Simulation。跨機、頭盔及真人容量待驗。
- CI 42084911404／job 127447285124 因付款或支出上限條件未啟動，GitHub 回報無執行步驟。 [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42084911404/job/127447285124)

## 2026-11-06 玩家連線檔配票前驗證

控制台 0.31.3 共用場次公告的 IPv4／埠號規則，在送出配票請求前檢查手動輸入。舊版以 `127.1` 實際產生連線檔，新增瀏覽器斷言失敗，原兩份證據保存在 `artifacts/console-ticket-destination-before`。新版驗證縮寫、綁定位址、群播及越界埠皆送出零筆配票請求，改正後只送出一筆，票券對應原玩家及本次 admission。 [外部玩家連線](EXTERNAL_CLIENTS.md)

- 來源 `e3e4e2edddb3115bd92bc8747c598a535cbb83c9` 的本機回歸通過 89 Node、301 Chromium、13 Python 與 105 項解壓管理包檢查。新版保留 51 份瀏覽器證據。管理包為 52,484,295 bytes、504 項清單、ZIP 505 項與 484 項執行環境檔案，SHA256 `0bc73d3452638f83363ac663eee8f767c114449bd7b58e6789712b8512c682dc`。管理包測試結束後 C／F 共 27 檔核對 SHA256。 [Windows 管理包](WINDOWS_CONTROL_PACKAGE.md)
- 解壓包的 API 搭配現有 0.41.1 玩家包做同機乙太網路 IPv4 測試。首場 `20261106-021912-4885cd6e` 等待來源公告逾時，瀏覽器與伺服器工具均 exit 1，當時尚未配票，C／F 共 12 檔相符。第二場 `20261106-022050-932fd3f1` 沿用相同版本與時限，兩工具 exit 0，9 項通過，兩位玩家各自收到戰績，世界封存序號 227，清理後 C／F 共 14 檔相符。跨機、頭盔與真人容量待驗。
- CI 42083067052／job 127440889457 因付款或支出上限條件未啟動，GitHub 回報無執行步驟。 [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42083067052/job/127440889457)

## 2026-11-06 遊戲伺服器本機網卡驗證

外部玩家測試新增 `--local-game-address=<本機IPv4>`，要求位址已指派給本機且屬私有 IPv4。工具核對指定的公告與監聽位址、控制台欄位、伺服器 PID 的 UDP socket 和兩份下載檔。原 loopback 流程繼續作為預設。變更來源為 `3f243c39e394ac3fc7dc4aafbc7e6fdab787db61`。 [外部玩家與雙機驗收步驟](EXTERNAL_CLIENTS.md)

- 乙太網路 IPv4 場 `20261106-020816-f3207f89` 通過 13 項，兩位玩家入場並收到各自的戰績，世界封存序號 637。實際 UDP socket 綁在指定 IPv4 與埠。包啟動器的入場、拒絕、無伺服器及斷線後戰績狀態均已驗證。
- Loopback 場 `20261106-021033-fbf94c7f` 通過 9 項，兩份戰績與世界封存序號 198 一致。兩場測試工具均 exit 0，程序清理後各 14 檔 C／F SHA256 相符。證據涵蓋同機 Simulation，第二台電腦的實體網路、頭盔與真人容量待驗。
- Node 語法、6 項 Python 與 3 個命令列拒絕案例通過。GitHub Actions 42081624524／job 127435870115 因付款或支出上限條件未啟動，沒有執行步驟。上一輪成功 CI 的測試來源為 `e963e48`。 [本輪 GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42081624524/job/127435870115)

## 2026-11-06 玩家連線檔視窗驗證

玩家啟動器 1.1 交付包 `windows-player-0.41.1-v2.zip` 為 82,652,952 bytes，SHA256 `925a8ac16451ae2c423da1b0cb9c9867af17b8fb5b08ab5824f7ea1b1bca8402`。解壓包通過 19 項檢查，Framework 核對類別 24 項與連線狀態 17 項通過。封裝核對確認 311 項清單內容及同源 Unity 0.41.1 執行檔。 [玩家連線檔載入與核對](PLAYER_CONFIG_REVIEW.md)

`20261106-020135-fbe6ceb7` 的實際 WinForms 流程從貼上路徑開始。載入後顯示檔名與目的地，附加 JSON 空白後拒絕啟動，重新載入後開始遊戲。第一位從 GUI、第二位從 CLI 入場。兩個測試工具均 exit 0，9 項檢查、2 份戰績與世界封存序號 828，程序清理後 C／F 共 14 檔逐一比對 SHA256。另保留 2026-11-02 背景雙玩家 13 項、世界封存序號 387 及 14 檔 C／F 核對。原 GUI 逾時仍保留失敗，當時停在載入前。兩場屬同機 Simulation，LAN、實機及 25 位真人驗收待完成。

CI 41368791791／job 125034572205 測試 `e963e488411927f73bc296e500ea6ae4ee18c7be`。Linux 772 核心、459 HTTP、47 world、6 pipe、38 硬體 CLI、Python、89 Node 與 296 Chromium 通過，另有 3 項 Windows 限定跳過。保存 console 51 檔、control 13 檔、hardware 26 檔及原始 ZIP 和日誌。累計 1870 份瀏覽器 CI 證據，本輪兩張原生流程瀏覽器截圖另計。 [CI 結果](https://github.com/peca12968/vr-command-center/actions/runs/41368791791)

## 2026-11-02：最終GUI fixture來源65b072d完整雲端成功

[CI41367545805](https://github.com/peca12968/vr-command-center/actions/runs/41367545805)／job125030805195，精確 **65b072d31f32afcc5e9da85713caa8b6451a3cd8**完整 **success**：Linux772核心／459 HTTP／47 world、6pipe／38硬體CLI、全部Python含14exercise／4server package及素材、89Node／296Chromium，2Windows限定skip非Editor/native/GUI/頭盔。此提交只補GUI fixture roster；本機實際GUI64853另驗，不由CI替代。

- console51，art13107449934，ZIP **12,027,134 bytes／SHA256 837214959214b8890d3e03481e7011228dba38b9a6bf5eee4e8879e1fb1c384b**。
- control13，art13107449938，ZIP **3,920 bytes／SHA256 bebc5438e939ef101a4c11066102fe740e2287501da1b576729a72f67a75604f**。
- hardware26，art13107514651，ZIP **22,356 bytes／SHA256 6673f4ae64235908856ee698167f4d9443af3fc0d6d23b0b0d2fbd50ae0652c0**。
- decoded log SHA256 **f6297ac22f5daf11cffad1d571d816b4f2ea6b3e184ff3b8613179b7970d4b6c**。GitHub digest/大小/逐檔hash核對；原c55與659成功、三次failed及更早證據保持，1768＋51＝**1819 browser**，nativeUI11另計。held PUT仍fulfilled=true／原1請求／errornull、原鏡頭隔離斷言與15/30秒保持，非舊逾時根因證明。

目前PC里程碑採用0.41.1／code52／NGO29／242真正Editor／4ebd雙平台、900秒18／51601／50原結果6CSV、普通8／354、玩家包19、server v2包106／623及新真GUIexit0；完整11項仍active。新接受metadata只接受上述範圍，server-package-path改為已驗證F解壓v2，舊accepted與所有候選／failed保留。666原生snapshot、328與327歷史、smoke174／long174／ordinary14／package80／failed GUI9／passed GUI14 raw C/F保持，保存SQLite不開／5080不動。後續僅文件skip ci；精確CI65b072d／native4bdf／包說明c55，不以文件HEAD冒充測試來源。

下一步繼續PC跨機部署準備與完整操作者流程；原31／world371／Windows startup根因／F吞吐仍未修復，25真人／Quest／VIVE／MR／廠商硬體仍另驗。以下各段為當時狀態，最新完成以上段為準。

## 2026-11-02：包說明來源c55f21c完整雲端成功

[CI41366924943](https://github.com/peca12968/vr-command-center/actions/runs/41366924943)／job125028931655，精確c55f21ce59bd1601f64f7e4520feec4a75e6bfb1完整success：Linux772／459／47、6pipe／38CLI、全部Python含14exercise與4server package／素材、89Node／296Chromium，2Windows限定skip非Editor/native/GUI/頭盔。console51 art13107323162／ZIP12029146／SHA7cca686b27857c4ac838f3344cdb893f7989e098c67205a489357052595054c6，control13 art13107029055／3918／SHAa3a2a3da9e722296c91578cde8eea22856bc1a27303732fe842a04d367cc6a5a，hardware26 art13107308336／22365／SHAaba8cc04b13179f7f75fe12aa11ec04df3e721daf16e2a9de2c2a54168ebfb01，decoded log SHAcead827ceb618d70158639bfd2a84b248aee6f942e99639afadee6bfa8eaa3bc；GitHub digest/大小/逐檔hash核對。原659成功及各failed CI保持，1717＋51＝1768browser，nativeUI11另列。

c55只包內兩行說明，runtime不變。其後65b072d只補GUI fixture roster，真正新GUI64853已成功，CI41367545805尚待；不拿c55冒充65的精確測試。新GUI失敗9與成功14／包80／smoke174／long174／ordinary14都在各tool terminal及空cleanup後raw C/F同hash；原328與327來源/binary歷史加各manifest保持，首次auditor錯把manifest計入內容數而拒絕，改逐原hash子集＋manifest額外一檔，不改歷史。

原666來源snapshot逐hash保持且與目前選定原生graph一致，沒有把其未收錄的package/gui/browser稱作完整snapshot；新launcher binary實際另驗。保存SQLite不開、完整11active，後續文件skip ci。

## 2026-11-02：新版伺服器包與實際WinForms收尾成功

同源0.41.1的v2 F解壓包真正handle18979 exit0、106項／623完整回放（五房143／123／115／100／86、Linked56）、10原admission結果／CSV／雙seal及server ACK、active0與cleanup空，C80→F raw同hash。parent-death是第七個刻意未封存反例不混作正常場。closure UI兩PNG與原final world同來源，nativeUI9＋2＝11，CI browser另計。

使用者自行關PickerHost後，真正handle64853／GUI run-3d179468... **exit0／passed**：直接輸入既有實例、載入兩房清單、明確選房1、核對完整UUID／任務版本、設定127.0.0.1與64640、按啟動；fixture Begin後原來源Running/tick>0/observed fence，正常API End／雙seal保留36秒後原child25432停止，實際看見「任務已封存並停止」，再按視窗關閉。GUI68392 exit0、原實例marker／三key檔hash不變、closed journal complete/sealed/ACK尾精確、cleanup空後C14→F同hash。只有一位roster、未開玩家client；不是玩家結果送達、25操作、GUI建key或系統檔案picker成功。

首新GUI run-e615...／handle63777 **exit1**：已實際選取/啟動正確來源69716，但fixture空名冊Begin被原API409拒絕，finally收GUI/native/API、cleanup空，C9→F同hash，原failed保留。產品原Begin規則要求非空名冊；只修check-server-gui先加一位明確roster、另存scope證據，不改API/launcher/遊戲。py_compile與新實際GUI驗證成功；功能提交65b072d，對應CI另記。電腦自動化曾遇geometry unavailable／bounds changed，重新選取與fresh state後成功，沒有操作安全／授權提示。舊PickerHost與原31／371／Windows startup／F吞吐仍保持原判，完整11active。

## 2026-11-02：位置回饋900秒兩模式長場完成

原handle33928真正terminal **exit0**，073638-487017bd的18項／**51601全回放／51351 Running**成功；Linked8610／8576，五獨立房8582／8518、8590／8552、8580／8540、8600／8561、8639／8604。50位原admission各90發／45reload／45週期、50原結果／6CSV／combat與world雙seal及原server ACK／無timeout或queue error，活動跨度17943..18003tick、最長收集902.3086214秒。Room1僅原授權Pause窗口例外、其他房前進，原走道與0.5／1.5政策不動。active0／全部cleanup空後C174→F raw逐檔同hash，desktop-endurance-feedback-long-validation.json只接受本場，不接受完整11項。

另073233兩模式60秒18／3760、普通無生成旗標081609入場／撤銷／重連8／354、玩家包19成功。Unity0.41.1／code52／NGO29、242真正Editor與同源4ebd雙平台／原ID保持，沒有為包說明更新重建Unity。原0.41漂移場exit1、原31／world371／startup／F吞吐仍各自未解；同機AutomatedSimulation非25真人／LAN／頭盔／MR／廠商硬體驗收。

使用者已關PickerHost，伺服器GUI接續另驗。新版server v1先在Path.resolve的AppData LocalCache視圖缺DLL，literal原路徑仍在，未啟動fixture；後F長stage超Windows路徑長度，copy失敗於ZIP建立前，原部分stage保留。新F短stage成功生成v2，runtime全部byte同v1、launcher來源fb57807d不變但重新編譯binary不同，不能稱整包二進位相同。初期強相等斷言拒絕也保留，後按實際三差異（launcher／README／manifest）核對。v2 ZIP82673732／SHAca285a42e0c22bdde17f62eb6dd8a65523c9d3a5cae19a33cad41636899fb368，311manifest／ZIP312、實際F短路徑解壓後逐檔驗證；真正包整合與GUI結果另記。包說明移除過期Unity0.39字樣，引用Runtime/build-receipt.json；4 Python package成功，c55f21c CI41366924943尚在執行。此前段落的「live／尚待」是當時狀態，以本節及後續結果為準；所有舊證據保留，保存SQLite不開，5080不動，完整11active。

## 2026-11-02：位置回饋候選的完整CI與held回覆收尾驗證

[CI41364751791](https://github.com/peca12968/vr-command-center/actions/runs/41364751791)／job125022432098，精確來源 **659f026eb13021ed4eb6fd2defde066f5b8bd620**完整 **success**：Linux772核心／459 HTTP／47 world、6pipe／38離線硬體CLI、全部Python含14 exercise／素材、89 Node／296 Chromium，2 Windows限定skip非Editor／原生／GUI／頭盔。

- console51，art13106359427，ZIP **12,016,184 bytes／SHA256 42bbc0d847f8ed767d27dcf6d756992c02b5b5f557c24a7a7a725df39801405c**。
- control13，art13106254966，ZIP **3,918 bytes／SHA256 2bef12d403cda00da3ff32bf3d249390fac08873493275151c1cb81a889833fe**。
- hardware26，art13106513838，ZIP **22,330 bytes／SHA256 06621fbb62648dde3b50b6cded39e7685591646532e6e2e7bb0cfaf393367c22**。
- decoded log SHA256 **4f9fdf901a7251ec29221944d330e057442cdc3f2e9b14f6af56c29ae5d7209f**。GitHub digest／大小與逐檔hash核對，原18a成功89檔及三次failed56／58／57檔與各ZIP保持。

新delivery metadata為fulfilled=true／requests1／errorName=null，且重新登入後camera-save enabled、原延遲回覆隔離斷言通過，不是吞掉取消回覆來變綠。這只證本場；首7ed stalled-read15秒、4bdf relogin-save30秒與1d route already-handled仍failed，原件保留，不能由本場推定原逾時唯一根因。產品JS／API／期限及原15／30秒與隔離斷言保持，659只fixture回呼收尾／文件，未新建置Unity。

1629＋4bdf failed19＋1d failed18＋新51＝**1717 browser檔**；control／hardware與nativeUI7＋2另列，沒有新本機全browser／GUI。242真正Editor／4ebd雙平台與原生helper是4bdf功能來源，CI659不替代它們。原33928／073638長場仍live：Linked8610／8576Running已過，Independent正在900秒；不停止／重啟或提前snapshot。使用者已自行關PickerHost，待長場與cleanup後重驗GUI。後續文件skip ci，CI精確659／native4bdf，完整11active。

## 2026-11-02：重新登入fixture的held PUT回呼失敗保留

來源1d023ff的[CI41364052976](https://github.com/peca12968/vr-command-center/actions/runs/41364052976)／job125020346533 **failure**，772／459／47、6pipe／38CLI、全部Python含14exercise／素材及89Node成功，2Windows限定skip；stalled-read與登出清理斷言已過，隨後world-browser161的held PUT route.fulfill出現「Route is already handled」未處理拒絕，Node終止，非30秒DOM逾時／完整296。

console18（art13106372583／ZIP3935698／SHAe5925243ef5fd2fffa019ad3386d21140043b0b3026a22593791182cdc60ee7c）、control13（13106736338／3918／ba70a60ce4f3b9cb4163ce83095ffeb01bd104ca64f4a78d057199e125cfc3dc）、hardware26（13106606868／22368／2b248dbb21eb75af9defe476931c2db494dafdf54c6edfdd65084e5fb94b2425）及decoded log SHA99fc847414397ad17e5a981aebedd27be0ab09d825fdc6b00a86d6dca789ab7c另存核對。原1648＋18＝1666browser，原58／56失敗CI與89成功CI不覆蓋，nativeUI7＋2保持。

調整僅測試：held回覆必須先完成，再解除route，回呼例外先收集、由主流程明確失敗，不能忽略已取消回覆來讓隔離斷言變綠。新delivery metadata必須fulfilled=true且只有一個原PUT，才會走原「晚到保存不能污染另一actor」斷言；若重新登入本身已失敗則保留原錯誤，不用回呼覆蓋原因。原30秒／100ms輪詢、產品JS／API／期限及所有隔離斷言不變，node syntax過，新CI另驗，不證先前兩次逾時根因。

使用者已自行關閉先前阻擋GUI的PickerHost視窗；目前不打斷原33928／4ebd長場，待它與清理／包檢查完成再重驗WinForms流程。新的Linked完整8610回放／8576Running已通過，Independent正在原場次900秒，writer停前不snapshot，完整11active。

## 2026-11-02：位置回饋來源CI在另一個鏡頭等待點失敗

來源4bdf294的[CI41363335600](https://github.com/peca12968/vr-command-center/actions/runs/41363335600)／job125018189228 **failure**。772核心／459 HTTP／47 world、6pipe／38硬體CLI、Python14 exercise／素材及89 Node成功，2 Windows限定skip；先前stalled-read已通過，這次world-browser196在Room2重新登入並開始原世界後，等待camera-save enabled的原30000ms逾時，未到完整296，不是auth-role等待。初分析標籤誤寫auth-role，原metadata副本保留後更正，不改原log／ZIP。

console19（art13105934910／ZIP4250536／SHA41b6d49b818180e7b2057bc70cb1c5b9957d6cf1128eb4ee2b8b3532dd803465）、control13（13106735184／3919／141b3522228f04f38f3d01e9019a89e34a891a1b7d5131844170fa91e2162058）、hardware26（13106540919／22348／aa5b0d80b987bda4c3571b3f20afda59b396c2255a6ea71c809c7e731ae96b79）與decoded log SHA730a67a0511f3987466070371b09ca1cc8ce0d823223f54f6ee92da8c38255a9保存核對。原1629＋19＝1648browser、nativeUI7＋2保持；所有先前失敗與成功原件不覆蓋。

該場原save診斷只到初始PUT的after-click，沒有重新登入後失敗時的DOM，不能證RAF／產品根因。只把此一按鈕謂詞改polling100、原30000ms與延遲舊保存回應不能污染Room2的斷言不變；明確bringToFront／選原live.header.sessionId，最多8筆控制狀態（原訊息各500字）／截斷旗標，失敗5秒圖遮login-key再原錯重拋，held PUT於finally釋放／解除route。沒有改產品JS／API／路由／期限或新增本機Chromium負載；node syntax成功，新CI結果另記。原33928／4ebd長場仍live，不重啟或提前snapshot，完整11active。

## 2026-11-02：原長場走道失敗保留，位置回饋候選再驗

原0.41／5d2e的064034-7c1ae2b7、真正handle51871終結exit1，cleanup空、C174／F raw同hash，整場failed。Linked5項／8621回放／8587 Running、25原結果／ACK／無timeout及45循環通過；Independent在Room5 world3400／tick7120／elapsed359770ms觸發生成器走道（首Z=-3.4091835），該房仍五位connected／health100／Simulated、在正常房內。完整失敗取證36896：Linked8621、五房3433／4309／5391／6721／8421；Room5三幀3400..3402共8筆走道不符，恢復後仍failed，8381保存Running無失聯。Independent僅36發18reload／活動跨度7074..7127，後段靜止取證及四房continuity綠不當900秒接受。輔助分析首Room-only混跨場ID/minempty原件保留，後依原player IDs重對齊；沒有補造CSV／成功。

原0.41 binary/log321＋7來源＝328先C/F archive，更早327保持。[新0.41.1](DESKTOP_ENDURANCE.md)／code52／NGO29、242真正Editor0skip（新4）及同源4ebdcd12...雙平台原ID一致。長場只讀本機Z作起點..+.8m換向，回±.2、原Move／Constrain／RPC，不clamp／teleport／寫server pose；原短40tick與走道、0.5／1.5、武器彈藥／durability不動。Editor凍結舊換向公式配同一不均步長可漂移、新回饋有界，不補本場deltaTime trace或舊31／371根因。14 exercise／27 active／5 artifact與錯模式CLI通過，失敗另存partial-checks但complete=false。

073233-32121819兩模式60秒18項／3760回放／50原結果6CSV／雙seal ACK成功、每人6發3reload／3週期。長場可選最多5個唯讀回放，各原rate4／期限／每幀與cycle／seal閘門，native先停；此路徑已預跑。玩家包19通過，新ZIP82651927／SHAdcc46...、server82673718／SHAb45d...、APK60361942／SHA766d...完整hash及ARM64/min32/target35/v2debug見文件。Server新包完整原生／普通入場尚待，無新WinForms GUI／頭盔。

新900秒both／25Linked後五房各5端，真正handle33928／073638-487017bd正執行，不能提前接受；兩端建置全停、666新source snapshot在它之前完成，writer停前不runtime snapshot。原0.41 ZIP／APK保留，current APK為0.41.1，不當舊檔同hash；舊18a CI不冒充新候選，新CI另驗。保存SQLite不開／5080不動，完整11active及原31／world371／startup／F吞吐／PickerHost／跨機真人／頭盔MR／硬體仍待。

## 2026-11-02：長場來源與鏡頭等待fixture的完整雲端結果

[CI41359154963](https://github.com/peca12968/vr-command-center/actions/runs/41359154963)／job125005569006、精確來源 **18a72f0cd97fd7c0fdeeeec98ddc3b90d980f754**完整 **success**：Linux772核心／459 HTTP／47 world、6 pipe／38硬體離線CLI、Python含14 exercise（新3長場）／素材、89 Node／296 Chromium，2 Windows限定skip非Editor／原生／GUI／頭盔證據。

- console50，art13104173114，ZIP **12,047,825 bytes／SHA256 dc449ceabe05f40c9317d61e3a420d230207d90d6a5d37a8d8b64c4bfc4f78a3**。
- control13，art13104212927，ZIP **3,918 bytes／SHA256 67e83aca5aee339ab604ef76d3c947d1143cdbd66c3a000370386f99ac292af4**。
- hardware26，art13103849142，ZIP **22,388 bytes／SHA256 8819ff5b35e7726aee53fa3f2e05db7e567d4fc60946b3654c8a54f3b9896592**。
- decoded log SHA256 **e9a216c8fa4914a6d890c85adaf153ee8e7c2b1f0444d9565d2dade3863776ad**，三ZIP的GitHub digest／大小及逐檔hash核對成功；前88成功CI與首失敗56檔／三ZIP保持。

新stalled-read metadata三列：本場visible／focused，before enabled、response-held disabled、約10242.77ms enabled＋error-class、仍1個option。這只描述本場，不能補作首7ed失敗的狀態，也不證RAF根因或產品無缺陷。原15000ms／集合與錯誤斷言及產品程式／期限保持；fixture只DOM polling100、有界診斷與finally釋放held GET。**首CI41358528198仍failure**，17部分browser／日誌保持。

1562＋首failed17＋本次50＝**1629 browser檔**；control／hardware、既有nativeUI7＋2另列，無新本機全browser／GUI。238真正Editor與同源5d2e雙平台是7ed功能來源的先前實際建置，18a只改browser fixture／文件，未重建遊戲。原生900秒handle51871仍執行：Linked輸入窗口已結束，25原結果與25server ACK／無timeout已保存，完整回放與Independent尚待。沒有因CI終結而停止或重啟此原生場；writer停前不snapshot，保存SQLite不開。後續文件skip ci，CI精確來源18a72f0／原生helper7ed，完整11active。

## 2026-11-02：首長場來源CI的鏡頭讀取等待失敗

來源7edb160的[CI41358528198](https://github.com/peca12968/vr-command-center/actions/runs/41358528198)／job125003707285 **failure**：Linux772核心／459 HTTP／47 world、6 pipe／38硬體離線CLI、Python含14 exercise／素材與89 Node已成功，2 Windows限定skip；瀏覽器在world-browser.cjs:131等待刻意stalled camera read的refresh按鈕恢復，原15000ms逾時，未完成296項，不當完整成功。

原console17（art13104158516／ZIP4239456／SHA8e52a5d860f58c3951ba9ec34d8adca4c5177d1442308951d97db1970a521a35）、control13（13104795827／3918／9d47fcb6ac0d997ea42dbf3201621d01b11a3af0b531f5649397302ab7845fe9）、hardware26（13104566898／22343／db32b3f06bf7511389f7aa9477185d5b04dd1581087bc39a457781c501562197）與decoded log SHA6ef00e0f85da8b2982d9efe42b102de9622ebdad9830a3fe7e454a06461c9055已另存、ZIP digest／大小／逐檔hash核對，前88CI檔保持。1562＋17＝1579 browser檔；本機原生仍是原handle51871／同源5d2e，沒有因CI觀察失敗重啟或提前snapshot。

原失敗沒有該等待點的控制狀態，不能證RAF／timer／產品根因。只把同一DOM按鈕謂詞改為polling100，保留15000ms與原集合／錯誤斷言；新增最多4列visibility／focus／disabled／error-class／option-count及caller單調時間，不含input／headers／body／key。失敗最多5秒圖後原錯重拋，held GET於finally釋放；不改產品JS／API、路由、API期限或錄影政策。node syntax通過，雲端結果另記；不在25端長場旁另跑本機Chromium／新建置。原完整11active與舊31／371等反例保持。

## 2026-11-02：長場生成輸入已建置，900秒兩模式驗證進行中

新增[獨立長場旗標](DESKTOP_ENDURANCE.md)，Unity0.41.0／code51／NGO29、238真正Editor／0skip與同源5d2ebd2a...Windows／ARM64、原Scene／prefab ID保持。每20秒fire／reload／fire，45循環最多90發／45換彈，仍走原Move／RPC／彈藥；漏循環失敗不追補。長場19000活動tick／1200收集秒與原短1200／240分開，原0.5／1.5政策保持。14 exercise（新3）／27 active／5 artifact Python及3錯CLI模式拒絕成功；沒有後端產品／UI／rules／wire改動。

五端60秒原生063727-2069ec28，5項／597全回放／577 Running、每人6發／3換彈、3個20秒循環成功；來源活動tick跨度1202..1203。短場＋原管理命令063930-4ee0c139另7項成功；19玩家啟動器離線檢查成功。900秒Linked25後五房各5端，真正handle51871／064034-7c1ae2b7正在執行；此時尚未通過，不提前建立runtime snapshot或接受檔，最終結果另記。

原0.40 binary/log321＋6來源＝327先C/F archive核對；666新來源snapshot只含source，沒有複製正在寫入的DB。新玩家ZIP82651687／SHAf2c84949...、serverZIP82673487／SHAaf8a08b3...／APK60356910／SHA1187dfd2...，完整hash／簽章見文件。首server封裝缺stage-root在建立前拒絕，原觀察exec exit1／native exit未量測保留，補新目錄後成功，不覆蓋原檔。兩端建置全停後才原生測試；API0.31/UI0.31.2保持，保存SQLite不開、5080不動。完整11active，舊31／world371／startup／F吞吐／PickerHost及跨機真人／頭盔MR／硬體未改判。

## 2026-11-02：多人命令組合來源的完整雲端驗證

功能來源 **a58a52786ea4244940b3b2eb2c3dfd8e1ca6a4a1** 的[CI41356457654](https://github.com/peca12968/vr-command-center/actions/runs/41356457654)／job124997439220完整 **success**：Linux建置、772核心／459 HTTP／47 world、6 pipe／38實際API＋.NET硬體離線CLI、全部Python（含11 exercise／4新負向）／素材、89 Node／296 Chromium成功。2 Windows限定skip不當Editor／Windows原生／GUI／頭盔或實體硬體證據；本輪沒有重跑Unity或Quest建置，原231／6098雙平台保持。

- console49，artifact13103641973，ZIP **12,005,675 bytes／SHA256 b17a2b53c8671440a6e629a6d68cab19cc5c99149484a643053d60452e6a4f22**。
- control13，artifact13103766431，ZIP **3,919 bytes／SHA256 d1b8d7be81a4a4921b14a64a91721fbaab0a6932b77ea49a76d5b8e4fcc7597e**。
- hardware26，artifact13103193804，ZIP **22,361 bytes／SHA256 4d31e153f5513cc3b0ca127471bd0a1e75d83582ae4050ccb1de2777b82d522b**。
- decoded job log另存，SHA256 **e7506250d841ad5aabade21798b5d85f2e5cd6cc1f471b1a4de1aef6aaf67cd4**。三ZIP的GitHub digest／大小與逐檔hash核對，前輪88CI檔／三ZIP同hash。

1513＋49＝**1562 browser檔**，control13／hardware26及既有nativeUI7＋2另列，沒有新本機全browser／GUI。新C232／F與666來源snapshot、前C340／326history／666舊來源及原玩家／server ZIP／APK保持，保存SQLite不開、5080不動。後續僅文件使用skip ci，精確測試來源a58a527；30項／2909原生與附加2627 Running閉源讀回不由Linux CI取代。

原Linked／Independent生成器報告最大活動tick跨度分別361／550（18.05／27.5秒），全部明確Requested收尾；finish後停止生成輸入，但原姿態／結果流程持續。後面五房依序收尾增加了靜止回放，2909全回放或2627 Running幀不能當成全程動態輸入。 完整11項仍active，原31／world371／startup／F吞吐／PickerHost GUI、長任務多人與跨機／25真人／頭盔MR／廠商硬體仍待。

## 2026-11-02：25端持續移動與操作員命令組合

[短動態驗證](DESKTOP_EXERCISE.md)新增明確選用 `--operator-controls`。原16秒基本輸入窗口後，玩家繼續走既有生成器／原Move與RPC，先等待每人兩發已被統計接受，再對每個原場次送正常SetEnvironment／SetEnemies：雨夜／雷電／Patrol，接著Fog Day／Advance，autoAttack=false、敵軍數固定每房1位。每次使用自己的新UUID及當下expectedSequence；接受回條先保存，同session／非duplicate／原commandId及遞增序號核對，來源observed到達該序號、Running／非suspended、tick至少再20且全員walking，原存活敵軍ID／room／health保持、每位移動>1cm才成功。接受不當套用，不改原60活動秒／240秒收集上限或0.5／1.5政策；這是ManagementApi組合測試，沒有操作員UI／真人鍵盤／GPU或頭盔觀察。

先五端預跑 `061205-121a2aa8` **7項／202全回放**成功；最終 `061302-f5072feb` **30項／6場／2909完整回放**成功，Linked25後五房各5端。12階段／24個唯一正常命令、24個原before／applied checkpoint的packet及statistics精確重現於回放；50份原admission結果／6份CSV、雙seal／server原connection ACK一致、無timeout或send queue error。Linked Patrol／Storm的11幀及Advance／Fog的12幀為全部25位walking；五獨立房各自也有5位walking來源幀，不硬配跨房時鐘。

原程序terminal且cleanup空後，僅讀closed JSON的 `operator-timeline-readback.json` 對 **2627 Running幀**依該房實際接受的環境／AI序號逐項推導狀態，含兩個命令間可能不同步的序號窗口；weather／lightning／night／visibility／behavior／autoAttack、原敵軍ID／room／health無不符。這是post-terminal附加讀回，不是第31項新live檢查或網路容量／根因證明。所有普通完整回放及Room1明確Pause／Resume、其他四房tick前進門檻保持，未授權Paused不例外。

未選用新開關的 `061538-2e6870ad` **5項／179回放**成功，保留原無敵軍／兩發0中0殺／health100斷言；新模式同樣保持此精確統計。新4項負向證據測試覆蓋錯UUID／session／duplicate／倒序／bool序號、遺失命令及相同sequence卻不同packet／statistics；共 **11 exercise＋27 active＋5 artifact Python**成功。

本輪無新Editor／Unity或Quest建置，沿用Unity0.40／code50／NGO29、原231真正Editor、6098b485...同源Windows／ARM64及原Scene／prefab ID。玩家ZIP24aef...／serverZIP642e...／APKadb9...核對保持；新三組 **C232／F runtime-snapshot**同hash、666份新來源snapshot，前輪C340／326history／666舊來源snapshot也核對保持，保存SQLite不開、5080不動。原1513 browser與nativeUI7＋2保持，本輪未新跑本機全browser或GUI。完整11項仍active；舊31筆／world371／Windows startup／F吞吐／PickerHost、長任務多人操作、LAN／跨機25真人、Quest／VIVE／MR與廠商硬體仍待。

## 2026-11-02：多客戶端動態來源的完整雲端驗證

功能來源 **a4ff77c95553d04cfa90bfb33bd6cce55dcc0679** 的 [CI41354866315](https://github.com/peca12968/vr-command-center/actions/runs/41354866315)／job124992675470完整 **success**。Linux建置、772核心／459 HTTP／47 world、6 private pipe／38實際API＋.NET硬體離線CLI、全部Python（含新7項exercise）／素材、89 Node／296 Chromium成功。2個Windows限定skip不當Unity、Editor、Windows原生／啟動器GUI、頭盔或實體硬體證據。

- console49檔，artifact13102913618，ZIP **12,020,478 bytes／SHA256 4c090653090f17dca468b835df73398afafae73334822d7ffdbec307ca66b436**。
- control13檔，artifact13102684674，ZIP **3,918 bytes／SHA256 019f7e70600567a6f3fbab7994324b73479a950fbadea822d45ad02398a93515**。
- hardware26檔，artifact13103435263，ZIP **22,396 bytes／SHA256 fcb79042cf36c25d03b98dfd13307135383f9fdf66a0b79df2b6c0ce7e912134**。
- decoded job log另存，SHA256 **22deb5e4e9dc2066d79ed3d414862aa2882582da9823f0e582f7ff9f7e2183c8**；ZIP均與GitHub digest／大小相符，逐檔hash及前輪88檔／3ZIP核對成功。

原1464＋本次49＝**1513 browser檔**；control13／hardware26、既有nativeUI7與本輪serverUI2分開計數。這不是新增本機完整瀏覽器或新一輪原生遊戲。Unity0.40.0／code50／231真正Editor、6098b485...同源雙平台、18項／1951回放及兩個失敗fixture、default8／355、server包106／725／10原結果、玩家包19均保持原證據；原生數字不由Linux CI取代。

新C340／F與326份舊binary／source archive、666來源snapshot、舊75硬體及117／274／163／327 raw、9管理／5舊server／歷史玩家ZIP保持，保存SQLite不開。current0.40 APK與歷史0.39 APK分開保存。後續僅文件提交使用skip ci，測試精確來源a4ff77c；完整11項長期目標仍active，舊31筆／world371／startup／F吞吐／PickerHost GUI，以及跨機／25位真人、頭盔／MR／廠商硬體均未改判。

## 2026-11-02：原生多客戶端產生移動／射擊／換彈

新增[Windows batch Client短動態輸入](DESKTOP_EXERCISE.md)，Unity **0.40.0／code50／NGO29**，API0.31.0／UI0.31.2保持。明確新旗標／新目錄才啟用，只接受Windows Development batch Client且無XR，原桌面Move／Constrain與SubmitPose／SubmitWeapon RPC、簡報／Ready／Running及原伺服器門檻保持，沒有test RPC或直接寫server pose。40tick反向／0.4m/s約0.8m幅度、相對20／60／120tick的fire／reload／fire；只計真正呼叫原武器RPC的嘗試，接受另核對。60秒活動tick／240秒總窗口、finish／退出與owner／clock錯誤有界，不把report.complete當任務成功；普通啟動無元件，Tracked不搬動。

真正Editor **231／0skip**（原224＋7）成功，Windows／ARM64 Quest同源 **6098b4857b36d4b24a6b4ab275cbd64b17aa12353329cad9c96f36a9d339911b**、原Scene／prefab ID保持。PowerShell腳本因ExecutionPolicy未執行，原錯誤log保存，改直接呼叫同一Unity批次入口，沒有調整策略／安全性。兩平台建置全結束才跑網路測試，沒有建置負載重疊。

首`desktop-exercise/20261102-053940-74608ff9` memory helper名稱錯誤，在啟動玩家前failed；次`054005-b0589055`五端已移動，測試錯讀不存在的packet.observed而KeyError failed。兩場原C14／29、原log／原資料／cleanup空保持，不補成功旗標。修測試使用memory_status及實際observedSequence，另以原API名冊核對admission／room／seat，無產品pose規則修正。新7項Python證據驗證及5既有artifact檢查成功。

`054142-2d7a0827` **5項／139全回放**的五端smoke通過；`054350-5fe3e1a0` **18項／1951全回放**通過，Linked25原生client後五個Independent server各5client，16秒產生輸入，每位接受移動／reload、2發／0中／0殺／health100。50份原admission結果／6逐場CSV、雙seal與原server ACK／無timeout相符，無send queue full。Room1 Pause接受後等來源真正Paused、tick固定，其他四房tick前進，Resume fence保存；意外Paused不放過。完整回放所有Running body均核對connected／Simulated／健康／房間／位置、1500ms gap不放寬。Linked159 Running保存幀中154幀25位walking=true；各房5位移動的post-terminal讀回另存，不是第19個live檢查，沒有把不同來源時鐘硬配。

普通無旗標`unity-admission/20261102-054643-86ca91ed` **8項／355幀**撤銷／重連／精確seal成功。玩家包19 CLI檢查成功；server包`run-72e81d5697d64b43ace5cb2fb1d59ecb` **106項／725全回放（172/148/132/115/100/58）／10份原結果各CSV**、真browser正常UI End與精確來源／ACK、cleanup成功。parent-death仍是獨立未seal反例；此browser不是Windows launcher GUI，新GUI未驗，原PickerHost保持待解。

新玩家ZIP **82,651,129／SHA24aef191b5fc608430a5f131ffd34aabf2ec0b4938fefd3f2c8461c958cc50e2**，serverZIP **82,672,917／SHA642e5307cf3d62af7b136d9baaca06c2d9cd9c3bd1ed66c7d4e915803a7f8710**，各311 manifest／ZIP312，launcher來源a658／fb578不變且server實際compiler input保持。APK **60,358,086／SHAadb9a8bc6c94b0e9842c1498f5a74417071daf388f79622f742f060e3c098fa5**，aapt確認ARM64／min32／target35／0.40.0／50、v2 debug，非實機／效能／商店release。舊0.39的321 binary/log＋5source＝326先C封存再F同hash，舊APK0310...保留history，current路徑是新APK。

`desktop-exercise-delivery-validation.json`核對新C14＋29＋29＋174＋14＋80＝**340檔**／各F snapshot、666份凍結來源、兩平台receipt／包及原ID、舊C75與四報告117／274／163／327、舊9管理／5server ZIP及玩家ZIP保持，保存SQLite只rb/hash不開。前1464 browser／nativeUI7保持，新server browser2另列，舊77場3399 runtime未全重跑。新場是產生的Simulation輸入、0位實體操作者／1host／0rendered，不是25真人、LAN或完整容量；舊31／world371／Windows startup／F吞吐與完整GUI、頭盔MR／廠商硬體仍未修因／驗收。完整11active，正式5080不動。

## 2026-11-02：硬體離線模擬器CI與證據

[功能574df36](https://github.com/peca12968/vr-command-center/commit/574df36d3cd4246dec0ad67885e8a544fa4f47c1)的[CI41349387031](https://github.com/peca12968/vr-command-center/actions/runs/41349387031)／job124976066366完整 **success**：Linux772核心／459 HTTP／47 world、6 pipe、38實際API／.NET離線模擬CLI、全部Python／素材及89 Node／296 Chromium通過。2 Windows限定skip不是WinForms、Unity／Editor、native遊戲、實體硬體或頭盔驗收。console49 artifact13100741395／ZIP **12,022,752 bytes／SHA256 e24b2ce787ccae8aabb70c3bc32268a064ce9a89cc9c51313c37da983dd51d47**，control13 artifact13100701380／ZIP **3,919／SHA256 a2569dfd539a5c1fef56e3b703f7e83e1bc1dc9aa1eca2046fcff0311239077a**，hardware26 artifact13099889416／ZIP **22,380／SHA256 e8ce6368326ccb6080a5a9e4f7280e7a44bbeacad894929a079d8ad24f508172**，已下載核對GitHub digest／逐檔hash；hardware檢查與原API cleanup讀回成功，artifact不含DB、journal或角色金鑰。完整decoded log SHA256 **53685b090bb76aeb81af85d2c7270473cb3867b64fd50692c046af9eefc0f5fa**保存。`hardware-ci-validation.json`明列1415＋49＝**1464 browser證據**，control13／hardware26各自另列，nativeUI7保持；不是新本機全browser或Unity執行。本機C75／F與原C27／四舊報告、9管理／5server ZIP及原Unity0.39／e0d／224雙平台、玩家ZIP APK保持。後續只有文件提交skip ci，測試來源精確574df36，完整11active。

## 2026-11-02：硬體回饋離線模擬器

新增[HardwareFeedbackSimulation／開發測試台](HARDWARE_SIMULATOR.md) **0.1.0**，不是廠商wire或實機介面。新tool以整段schema6／7重建已Ended且戰鬥精確seal的單場，沿用原SessionManager／CombatLedger／admission與權限；只把ShotFired／PlayerDamaged投影成模擬訊號。原event／stream／report／ObservedSequence及room／admission不丟，晚到的報告不讀最終名冊。設備ID是本地模擬UUID，不是USB序號；無任何設備I/O、輸入事件注入、震動強度或實體停止保證，檔案符合重建規則不等於API來源簽章。

34新核心／**772完整核心**成功；128綁定、4096事件／步、虛擬0..600000ms、每設備32含in-flight、2秒虛擬期限，並不改遊戲0.5／1.5秒政策。重送／倒序拒絕、換綁與重連取消但不自動重播、錯設備／connection／delivery ACK不解除原flight；恰好期限先逾時。所有腳本最後取消殘留項，complete只表示腳本走完，SimulatedHardwareOnly=true／PhysicalDeliveryConfirmed=false。輸入8MiB、輸出64MiB、已有檔不覆蓋，受控錯誤exit1只型別。

五場真正隔離API＋.NET ArenaSession／TelemetryOutbox／原relay補送，初24／33／34／36與最終**38 CLI**各自成功；全部是Simulation，非Unity/native遊戲／設備。最終`hardware-simulator/run-883edf2541fc4063ab6c90e4e5454857`原12 events、2發2中1殺／受傷20／health80，3個訊號逐欄核對原event、report、stream、ObservedSequence、admission、room、kind與damage。原API事件／統計前後同、active0；每場原API私有pipe正常exit0／cleanup空才一次C→F snapshot。CLI真正使用的API／relay／simulator完整binary graph前後同hash。post-terminal逐欄讀回不是新的第39 live項。

最初錯權限輸入`hardware-rejection-before`已不寫報告，但CLI未捕捉原AccessDeniedException，Windows exit **3762504530**；輸入／stdout／無輸出反例保留。修正只將AccessDenied與KeyNotFound列為CLI受控拒絕，不改權限或歷史規則；同一位元原輸入在真正v2解壓包exit1／只型別／仍無輸出。原有效案例和初包保持，不能說先前已有受控拒絕。

初包`hardware-simulator-0.1.0-net10.zip` **122,332／SHAff7b1c6868ed84b8d4f7f9029207b2538047741277e68748c087c4c5ccf0511a**保持；主包 **hardware-simulator-0.1.0-v2-net10.zip** **122,352 bytes／SHA256 72e73214c03948ac312cac52c246338ae061e498fb7f8aa9f5d4e0bd62d7412b**，7 manifest／ZIP8。只有5個自己DLL／deps／runtimeconfig、合成example及README，需要.NET10 runtime，不含apphost／runtime／SDK／金鑰／DB。v2真正解壓執行sample，結果與原run逐位元一致，包保持同hash；manifest不是簽章，不假造實體ACK或stop。

`hardware-delivery-validation.json`核對新五場 **C75／F**、原C27及四舊報告117／274／163／327、9管理／5server ZIP、原玩家ZIP／APK／e0d60e4e...／224 Editor雙平台與原識別保持。最終build `hardware-c128f55c4c9442f5bebed300c9ba87c1`，197凍結輸入及同次輸出圖保存；Windows459 HTTP／47 world成功不改舊startup根因。API routes／UI／Unity來源未改，僅新Core離線類別／CLI／檢查；本機未新跑全browser或native遊戲，前1415 browser／nativeUI7保持。保存SQLite僅rb/hash不開，正式5080不動。完整11active，廠商協議／實機輸入輸出、MR、跨機25操作、原31／world371／startup／F吞吐與PickerHost GUI仍各自待驗。

## 2026-11-02：物件復原交付的CI與證據

[功能fddc59c](https://github.com/peca12968/vr-command-center/commit/fddc59c4f2e2571265fb19a0c81e3622c1b93eb9)的[CI41346124781](https://github.com/peca12968/vr-command-center/actions/runs/41346124781)／job124966206406完整 **success**：Linux738規則／459 HTTP／47 world、6 pipe、全部Python／素材及89 Node／296 Chromium通過。2 Windows限定skip不是Framework、WinForms、Unity、native遊戲或頭盔驗收。console49檔 artifact13099980133／ZIP **12,015,192 bytes／SHA256 d6012c7a79fccd1e2ed44ed13640f669f7708134ae6ca533eaae1328167dc13a**，control13檔 artifact13099004432／ZIP **3,920 bytes／SHA256 b1cde4b7e8ccd8ac06b2ed58c73213e5e300e5f91ca54764907c79d0dfd2db58**，已下載核對GitHub digest、逐檔hash及完整decoded log（SHA256 ffba6bdd60c1066877c19fbb92bd75f041dda4bebc2f22e55ea59f315b4aee8e）。`placement-ci-validation.json`明列1366＋49＝**1415 browser證據**，另13 metadata，nativeUI7保持；前CI60檔及ZIP另核對保持。C27／F及四舊runtime報告、9管理／5server ZIP、原Unity0.39／e0d／224／玩家ZIP APK不變。後續只有文件提交skip ci，測試來源精確fddc59c；完整11active。

## 2026-11-02：場景物件復原與重做

新增[物件編輯紀錄](PLACEMENT_HISTORY.md)，控制台 **0.31.2**／API **0.31.0**。本地物件新增、刪除、數值／素材與旋轉可完整復原／重做，保留順序及selection；一次拖曳／按住方向鍵為一步，放開／取消／失焦／切頁收束。只在配置圖攔截Ctrl／Meta快捷鍵，文字欄不攔截；載入任務／新增草稿／登出清紀錄，Master／busy／pending fence保持。儲存前收手勢，成功後同草稿還能undo，但只標記dirty，不回滾原不可變版本或管理寫入。50步／雙向UTF8序列化2MiB，完整步淘汰、返回值分離，版本／命令／憑證不進歷史。

新6 Node模型含500物件／參考隔離／分支與預算，完整 **89 Node／296 Chromium**成功。專項 **29項**實際拖曳／重複keydown／原物件鍵盤focus／快捷鍵／數值／刪除順序／儲存鎖定／新版保存／原版不可變／新草稿及登出房控；實際解壓包另29項成功。第一專項51184 exit1在保存後仍選已被head取代的原ID，30秒selectOption timeout、4原圖保持；後測真history.headId，不改期限。初隔離build漏複製Checks明確連結的AiTargetingCases.cs，CS2001／初snapshot保留，完成採新完整目錄，不當產品根因。

最終本機build `placement-90b30ba99f884d1cb18d967c6f535ee1`，API130／三tools各9／Checks90檔同次組，Windows **738規則／459 HTTP／47 world**通過；本機HTTP成功不解舊startup。管理服務整組自含publish484檔（.NET/ASP.NET10.0.14），Windows啟動器C#來源266d93c7...不變；新包 **control-server-api0.31.0-ui0.31.2-placement-win-x64.zip**，**52,472,096 bytes／SHA256 1eac2676113b47c58b5649ce444201e612603167a16d1e5bccb0599fc1dcf9a2**、504 manifest／ZIP505含manifest。94860 exit0／`control-package-checks/run-bf4e40038aea4fefb585694a915ae5d6` **105項**管理角色／五房25席／原實例重開／私有管線child停止及cleanup成功，25席不是遊戲端；7 control／4 server Python邊界與腳本語法成功。無新的WinForms GUI啟停操作；原server GUI仍failed。

`placement-delivery-validation.json`核對本輪管理runtime **C27／F snapshot**全raw hash，原四報告各C117／274／163／327及各F保持，原8管理ZIP＋新第9份、5serverZIP、玩家ZIP／APK、原e0d60e4e...／224 Editor雙平台及識別保持。新瀏覽器4failed＋3專項＋49完整＋3包專項＝**59檔**，原1307＋59＝**1366**；native UI7另列，原77場3399 runtime未全重跑。保存SQLite只rb/hash不開，自己writer已terminal且cleanup空才一次snapshot。沒有新native遊戲、Editor／Unity／APK或頭盔；完整11active，舊31／world371／Windows startup／F吞吐、完整server GUI／LAN／跨機／25操作／MR及廠商硬體各自待驗。

## 2026-11-02：伺服器清單交付的CI與證據

[功能a8855cc](https://github.com/peca12968/vr-command-center/commit/a8855cc96bdf8cb0ece5fcc4c2dc5e7e0743e2c0)的[CI41344259683](https://github.com/peca12968/vr-command-center/actions/runs/41344259683)／job124960591099完整 **success**：Linux738規則／459 HTTP／47 world、6 pipe、全部Python／素材及83 Node／269 Chromium通過；2 Windows限定skip不是Framework、WinForms、Unity、native或頭盔驗收。console47檔 artifact13098871115／ZIP **11,451,172 bytes／SHA256 bd4624e686c0f92778b9eee34dd3db57a128ac6d5b1c6f7a773955d0c22ee630**，control13檔 artifact13098607730／ZIP **3,918 bytes／SHA256 d8b15a858f0b43d5f07e934a8e2107bc0ab664d46660a75023526c8a2afd7d58**，均已下載核對GitHub digest、逐檔hash並保存完整decoded log（SHA256 4ad0493f6a621d9cc3d28a4e8a263daadaa9d096b9407c027d5ad24d16742829）。`server-catalog-ci-validation.json`明列1260＋47＝**1307 browser證據**，另13 metadata；既有native UI5與本輪native UI2另列。後續只有文件提交skip ci，測試來源精確a8855cc；本機38＋26與106／777範圍保持，GUI仍未完成。

## 2026-11-02：伺服器房間／任務清單與明確選取

新增[伺服器待開場次清單](SERVER_CATALOG.md)。Launcher **1.1.0**，獨立於原Unity **0.39.0／code49／NGO29**、API **0.31.0**及控制台 **0.31.1**；原e0d60e4e...／224真正Editor／雙平台、Scene／prefab ID與規則／wire保持，沒有新Editor、Unity或本機API build；CI另有Linux build與驗證。

原GUI只列UUID並需重選實例更新；現在直接輸入或選control-instance.json後載入／更新，清單顯示房間、模式、任務與id前綴，完整場次／任務版本ID另列，啟動仍用原UUID。初次不自選；路徑編輯先停用，載入失敗清原Current／Selected，不沿舊目標；更新只保留同path／instance ID／API／GameServer key且原id仍在的選取，不改選別房。Running／bound／MR不供啟動，原Start仍重新核對loaded API的GameServer／Preparing／未綁來源；清單不當預約／就緒。名稱顯示移除control／bidi並保留surrogate boundary，原name／id不改。新CLI --catalog只GET原身分／場次，bounded256Ki字元／5秒／最多5 active，拒絕錯id／mode／room重疊及資料錯型別；public JSON無key，complete只是read finished，不新增key、配票或管理寫入。

五份server ZIP全保留：新v4 **82,669,330 bytes／SHAf75b27e2d5fbcb106943808aa735651f93ebb6516e782716e1f56186529f6f4e**初候選，主包v5 **82,669,350 bytes／SHA3eef78fbe8319e366afa80cdfad31557bf42fb8bc3992402b6f252525e2857a2**、311 manifest／ZIP312，launcher input **fb57807d4744f06f6c2fe4f8737b1e7517543535a3d7eb8498a981f09340f073**；v4 input efec287c...。本輪package先凍結實際ServerLauncher.input.cs再編譯，原v3 source98c1f1...亦另保存；manifest不是簽章，無key／DB／ticket混入。原8份管理ZIP、玩家ZIP／APK及runtime未改。

初catalog／`server-catalog/run-f8663646f3d04ca9963540dca45ba805`有26 wrapper＋26真正Framework assertions成功。最終64877／`run-e7a553783114426daafc864ae27deff5` **exit0／38 CLI/API＋26 Framework**，包含真正五獨立／Linked、bound／MR metadata過濾、原id／version／read-only、role／marker改變、failure清除、原選取消失不換房與public JSON無生成key。proof直接編譯production catalog/state methods、不建立或操作WinForms；只在自己fresh fixture改還原marker/key且hash相同，以Master做一次測試End以證明選取消失，不能當產品catalog寫入或頭盔／校正MR。

新GUI70028／`server-gui/run-31f42864c4a0450a9d4daf9db9f70434` **exit1／未完成**：Window16189230／GUI10992，新增欄位與disabled Start可見；type_text未觀察落地，改用skill允許的ValuePattern後路徑確實改變、編輯提示與disabled Start生效。text-only click因geometry缺失未操作；補snapshot後兩次點擊（含activate／fresh state的一次重試）仍回報點上為PickerHost.exe而非Launch-Server，沒有load／selection／start或native來源成功。停止UI輸入、未操作PickerHost或任何權限／安全設定，只終止自己的GUI，API正常Stop／exit0，cleanup空列、C9／F保持；部分操作不當全GUI成功或根因修復。已向使用者非阻塞詢問是否有停留擷取／選檔視窗，其他PC工作繼續；沒有把未回覆當允許。

新版v5真正CLI31606／`server-package-checks/run-a6f7466c8f25462d86f73b41ad3900d4` **exit0／106項**：五獨立server＋五接收client，後Linked一server＋五接收client，真browser選原Running／一筆正常UI End／同source world GET提示與原native終界；**777完整API回放（185／158／144／124／110／56）**、10份原admission結果／CSV、雙seal／closed world journal durable尾界與原程序cleanup成功。terminal後另讀回10 CSV所有列／10原server network admission與ACK精確、無timeout，非新live／第107項。第七parent-exit仍故意未seal且無success final，不混六正常場；仍同機Simulation／接收者，沒有25位操作或GPU／LAN容量。

`server-catalog-delivery-validation.json`核對新C14＋14＋9failed＋80＝**117檔**與各F snapshot同hash、5份serverZIP／frozen compiler input、原8 controlZIP／玩家ZIP APK及e0d60e4e fingerprint，前C274／C163也同hash。1260 browser與原nativeUI5保持，新native UI2另列，未當新的全browser跑；4既有Python package邊界與新腳本語法成功。writer真正terminal才各一次snapshot，保存SQLite只rb/hash不開連線。完整11active，舊31／world371／Windows startup／F吞吐／完整GUI／乾淨新機／LAN／25操作／頭盔MR／廠商硬體各自待驗，不因本輪改判。

## 2026-11-02：主控台任務收尾與已封存End重試

[功能7a0da65](https://github.com/peca12968/vr-command-center/commit/7a0da6542c039b4de97b212aa67e3a651830a06b)的[CI41339991116](https://github.com/peca12968/vr-command-center/actions/runs/41339991116)／job124947761594／精確7a0da65完整**success**：Linux738規則／459 HTTP／47 world、6真正pipe程序、全部Python／素材與83 Node／269 Chromium通過。2 Windows限定skip不是Framework、Unity、native GUI或頭盔驗收。console47 artifact13097202219／ZIP **11,443,289 bytes／SHA4091035e0016961322021371bf8bae003459fd66238ee78625a768730753a6df**，control13 artifact13097370766／ZIP **3,919 bytes／SHA156cdc83d14a4658b4266fb50e07d2556afb08fbc63ef7efa1829ce4bcb17c97**與完整decoded log保存，ZIP digest與GitHub相符。`closure-ci-validation.json`明列1213＋47＝**1260 browser證據**，另13新CI metadata；本機C274／F、8管理ZIP／3 serverZIP／原玩家ZIP APK與前C163／C52native／C318control保持。文件後skip ci、測試來源精確7a0da65，failed／before不改判，完整11active。

新增[任務收尾](SESSION_CLOSURE.md)。API **0.31.0** REST／資料契約保持、控制台 **0.31.1**，分開顯示combat與world archive。只在選取的Ended來源場次頁可見時GET既有world，每兩秒／五秒逾時；同epoch／key／actor／session／sequence／stream與generation fence，世界header需同來源／rooms／clock、正數accepted與complete，統計精確同session序號／pending=false及combat.sealed才整體完成。隱藏／切頁／選取／登出／未知命令、刷新失敗或world讀取錯誤清除舊完成，401走原登出，404／403／5xx／異源不當綠。API的world seal已核對原Ended幀／combat尾界／統計，前端不讀live或保存journal／SQLite，不將archive當玩家送達／可關閉服務；原Begin、CSV閘門與0.5／1.5秒政策不動。

新增明確before反例：`console-closure-retry-before-20261102`／handle30262 **exit1**。真正API先接受End後GameServer封存0 combat，UI丟失回應、手動重試沿原UUID／expectedSequence，取得真正duplicate=true／sealed=true回條，舊畫面selected空／includeEnded=false／panelHidden=true，原30秒DOM逾時。compiled before API整組在`closure-b0bc5b...`，其WWW三source SHA另保存，沒有替換單DLL。修正只把「已確認End」保留條件改為response.session.state=Ended，已封存／無stream也保持選取，不再限定未seal；沒有自動寫入重試或改UUID。最終完整 **83 Node／269 Chromium**成功，包含原11項closure UI讀取／失敗／390px／登出fence及兩個真End retry檢查；world多狀態部分為明確UI route fixture，不當原生source。

新普通solution兩組各自保留；最終`closure-final-29fb7e09a7b2459aabed648f398c6e93`同次API136／三工具各9／Checks97，最終本機 **738規則／459 HTTP／47 world**成功。Windows HTTP這次成功不是舊startup根因修復。API/UI拆開版本以保持舊GameServer的0.31.0 gate，沒有新endpoint、world schema或Unity修改；Unity **0.39／code49／NGO29／e0d60e4e...／原224真正Editor與同源雙平台／Scene-prefab ID**保持。

兩個自含publication是`control-server-5d23dc...`與最終`control-server-4bb90a...`，各481輸出、原lock依賴群組保持，repository locks不改。兩份新管理ZIP皆 **52,466,368 bytes**，初closure SHA684f1f4d92ce206eff8319486245bcbc6b1ef6f1dfa76266fdf780d3892d61cc為保留候選，最終`control-server-api0.31.0-ui0.31.1-closure-final-win-x64.zip` **SHA7d87669d0f8478feb328697c3d9d58005aa8f0e3331726080374fa6ab5a254e5**、501 manifest（ZIP502）／481 runtime，含consoleVersion metadata。Framework啟動器source266d93...不變、API根版本0.31.0；不能僅用相同大小或版本認定同包。初control42125／`run-86f7aa...`與final93192／`run-709c59...`各 **105項**成功，沒有因本輪重做Windows啟動器GUI或改判原PickerHost。

首新native `server-package-checks/run-ad5b5fdd5ea34effb475ef463701b951`／21777 **exit1**：觀察器在原Running ready後等closure逾時，自己的browser22588正常exit0、cleanup乾淨，五房各已精確seal／回放，但未到Linked／公開10結果檢查。當時從別API通路End而未含Ended，可能被現有篩選移走；缺末刻DOM，不證唯一根因。改用真正UI End並補有限失敗state／五秒圖，60秒觀察期限保持。候選67639／`run-ce7572...` **106項／596完整回放**成功，scope與最終分開。

最終native15604／`run-c8d93c6d2da3455fa95f26db408d24a5` **exit0／106項**：包內API＋原server v3（SHA6cecfbee...）／原Unity，五獨立server＋五接收client，後Linked一server＋五接收client。真正頁面先選中Running，正常End按鈕只送一筆非duplicate 200 POST／原expectedSequence，來源完整回條、頁面自動含Ended、同source的world GET／已封存提示與原native精確尾界一致，沒有route fulfill／UI state注入；browser原process exit0，沒有送達聲稱。六場 **619全API回放（153／129／110／95／76／56）**、10份原admission結果／CSV、雙seal／closed world journal精確durable尾界與原child cleanup成功；第七parent-exit仍刻意未seal且無success final，不混正常六場。terminal後closed-readback另外只讀JSON／CSV／log，10 CSV每列／10原network admission與server ACK精確、無timeout，非新的live檢查或第107項。

本輪五family原C27＋60failed＋80candidate＋27＋80final＝**274檔**，全writer terminal後各一次F snapshot同hash，保存SQLite不開。`closure-delivery-validation.json`核對兩新pub／501主包、8管理ZIP／3 serverZIP、原玩家ZIP／APK／fingerprint及新API整組；`closure-prior-preservation.json`另核對前C52 native／C318 control及F370檔，前server package C163也保持。三browser資料夾47＋7before failed＋47final＝101，前1112＋101＝**1213 browser證據**，另兩成功／一failed native observer共5 PNG保持獨立範圍；原77／3399歷史native不混新family、不稱全重跑。7既有control／4既有server Python邊界成功。完整11active，原31／world371／Windows startup／F吞吐、完整server GUI／乾淨新機／LAN／25操作／頭盔MR／硬體仍待。

## 2026-11-02：Windows遊戲伺服器可攜啟動

[功能95411a2](https://github.com/peca12968/vr-command-center/commit/95411a264ac85894669b9127f3b40989982b30d0)的[CI41335830454](https://github.com/peca12968/vr-command-center/actions/runs/41335830454)／job124935327276／精確95411a2完整**success**：Linux738規則／459 HTTP／47 world、6真正pipe程序／4新Python封裝邊界與原工作流程／素材、78 Node／256 Chromium。2 Windows限定skip不是Framework／原生GUI／Editor／頭盔；本機103與failed GUI分開保持。console43 artifact13094744913／ZIP **10,005,039 bytes／SHAfd9e1fa1995ef18c65339b68308de501138f3a3cd8a91008d89810e3e2de75f4**，control13 artifact13095560953／ZIP **3,919 bytes／SHAacdf31e1d6331e34946ff3a4862814728446453441995d1d28ce6bd5e014b4c5**及完整decoded log保存，ZIP digest與GitHub相符。`server-ci-validation.json`明列1069＋43＝**1112 browser證據**，另13新CI管線metadata，未混入GUI／native；本輪沒有新本機browser場，後續文件skip ci、測試來源精確95411a2。

原handle27088 terminal後的`closed-readback.json`另外只讀既有JSON／CSV／log，核對六場10份CSV每列與sealed ledger一致，10個server admission network ID與10個原ACK集合精確相等、無server timeout。這是後補閉源讀回，不是第104項新live測試或又一場原生；原C78／F snapshot不動。`server-current-source.json`保存目前五份source byte且launcher SHA與v3實際編譯輸入相同，沒有冒充v1／v2來源原件備份。

新增[Windows遊戲伺服器包](WINDOWS_SERVER_PACKAGE.md)，Framework4.8繁中啟動器／CLI與原Unity0.39.0／code49／NGO29整組runtime封裝，操作員不需Python／Editor／SDK。API/UI0.31.0、rules0.8.0／world schema1／envelope7與原224真正Editor、e0d60e4ed6cefe5cd885e6aabe1621939da945ce00d56b3ed8820c0aed4db879同源Windows／ARM64 APK、原Scene／prefab ID保持，本輪沒有新Editor／Unity重建。

只用GameServer角色讀原Preparing VR且無combatStream的場次；新包外資料／私有log、同API／場次mutex，啟動前UDP衝突拒絕，Unity只收到GameServer key，沒有Master／玩家票券或代替管理Begin／End。原bootstrap先核對自己的combat UUID／origin／0 accepted／未seal，再StartServer寫真正network-start log；新啟動器沿這條原順序核對同場次API來源／world header才PUT immutable endpoint並驗回條，不開live獨佔journal。就緒不是玩家pose或Running證明。包內manifest逐檔SHA／大小及完整集合、拒絕連結／越界／額外檔，不是簽章。

Unity程序先suspended建立，加入私人kill-on-close Windows Job再Resume，只設終止旗標，不改CPU／優先序／記憶體／OS設定。正常End30秒內需雙seal，留36秒後以OS終止自己的Unity，原handle退出才complete；不是Unity graceful或玩家全收到／local ack最後落盤證明，玩家送達欄位null。失敗／中止保留journal、不自動End或接管舊Running，來源／管理請求失敗也不冒充正常完成；真頭盔、MR、網路及恢復機制另驗。

三份ZIP原件／receipt保持：v1 82,664,434／SHA26c44bed...、v2 82,664,466／SHAf77bf1a7...、主包v3 **82,664,818 bytes／SHA6cecfbeeffba1277000f93bc168c4ac387b825c34b73142628098dba28f67500**、311 manifest檔案（ZIP312含manifest），launcher來源SHA98c1f1db72049c301e8f1bee9a2835bbe388780027df75d84642131739b14642。v2是71項初輪；v3補完整包集合拒絕及GUI啟動等待中止，不重建Unity。Notices沿原玩家包素材／Transport授權。

真正handle35529 exit0／`server-package-checks/run-681a8591d76a45418b759e64315ab4f4`：71項、五獨立後Linked、原戰績ack／closed journal雙seal，未取完整API replay或精確原admission比對。最終handle27088 exit0／`run-d1463f9bd5be4d1aa5ab0ef98c402179`：**103項**；五獨立各一server／一接收client、後Linked一server／五接收client，10份原admission結果／CSV、Running的原Begin sequence／tick／observed／1.5秒來源界線、六場**553全API回放**（138／114／99／80／66／56）及雙seal／closed journal完整與ack精確尾界成功。每場只取有限live觀察，不是全程姿態健康或25位操作／跨機容量。Master／Room／Client／Host、混淆／多播IPv4、越界與32bit wrap埠、額外key、占用UDP、已End／bound Preparing等拒絕。兩組測試的第七個parent-exit場刻意在就緒後殺父程序，原Unity handle被Job收掉且無final成功報告；該場journal未seal，不能混入六個正常場。

新GUI handle6614／`server-gui/run-3c10b49ef207440aa060af85c0d6af41` **exit1／未完成**。CLI準備自己管理實例／API與Preparing場次，native Window31526058／GUI62088顯示欄位與disabled Start正確；選實例按鈕第一次及activate／新snapshot後一次重試均被非目標PickerHost.exe遮住（工具回報point over PickerHost而非Launch-Server），因此停止所有UI輸入，沒有選檔、啟動或遊戲來源成功。只終止自己的GUI，API正常Stop／exit0，cleanup空列，failed及原C9／F snapshot保存，不當PickerHost／Windows安全性根因或產品選檔驗收。後補helper關窗review在真GUI exit後最多等30秒，僅py_compile，沒有冒充新GUI場。管理服務包原GUI95151成功是另一產品流程。

4項Python package邊界與三新腳本語法檢查成功，假bytes測試不當native。`server-delivery-validation.json`用rb／SHA核對新C76＋C78＋GUI C9＝**163檔**與各F snapshot精確相同；原13場及後補pipe的C52 native／C318 control與F保持，六管理ZIP與主包、原0.39玩家ZIP／APK及source fingerprint同hash。原77場3399歷史native保持，不把這三個封裝family或未seal反例混入原總數，也沒有全重跑。原1069 browser與13 CI metadata保持，本輪尚未新增browser。保存SQLite不開，所有自己writer確認terminal才一次snapshot。完整11active，原31／world371／舊Windows startup／F吞吐與乾淨新機、LAN、25位操作／實機待驗不改判。

## 2026-11-02：Windows可攜管理服務與私有程序收尾

[功能1a959c6](https://github.com/peca12968/vr-command-center/commit/1a959c6b89e627791815537a57784c3bcb4819b1)的[CI41332911824](https://github.com/peca12968/vr-command-center/actions/runs/41332911824)／job124926578810／精確1a959c6完整**success**：Linux738規則／459 HTTP／47 world、6個真正私有管線程序案例、7項新Python封裝邊界與工作流程原檢查／素材、78 Node／256 Chromium全部通過。2 Windows限定skip不是Framework／GUI／Unity或頭盔證據；本機105與GUI／原生另外保存，沒有以CI代替。

CI下載console43檔artifact13093623576／ZIP **10,038,781 bytes／SHA `07e02d8202b099c6d6d21504aef3a89a26edb08cb32a3aee434346c9aa957df0`**，control-pipe13檔artifact13093473878／ZIP **3,918 bytes／SHA `34bc0eb51bdc4540ab33819ff56aa71f77e4fd4f58a47afa961c883f6e43d3b2`**及完整decoded job log，均與GitHub digest相符。control artifact只含6份遮蔽log／6份有限status／checks，closed-pipes stdout未觀察明確null，沒有runtime／key／DB。`control-ci-validation.json`核對前1026 browser／新43＝**1069份browser證據**與另13份CI管線metadata，原14場C52native／C318control與F snapshot、六候選ZIP／主包、478 publish、API整組、原Unity0.39／224及ZIP／APK保持。後續僅文件證據skip ci，測試來源精確1a959c6；Windows本輪459成功仍非舊startup根因修復，完整11項active。

API／控制台 **0.31.0** 新增[管理服務包](WINDOWS_CONTROL_PACKAGE.md)。Framework4.8編譯的繁中啟動器，可新增／選取自己的資料實例，明確選擇本機IPv4／埠、啟動／停止API及開啟控制台。API apphost自含.NET／ASP.NET Core **10.0.14 win-x64**，資料、七角色金鑰與票券簽章key獨立存放；Web／入場／統計／世界契約保持，Unity **0.39.0／code49／NGO29／e0d60e4e...**與原224 Editor／雙平台receipt保持，本輪沒有新Editor或Unity建置。

API只在明確ControlPipeToken配置時監看私有stdin，ApplicationStarted發本次nonce就緒事件。啟動器另核對原child存活、實際包內coreclr及Master身分，自己的stderr／stdout診斷有限且遮蔽全部key／nonce。錯token短行不停止，匹配STOP要求正常停止；EOF／越界／非ASCII／讀取或就緒輸出IO失敗也收尾。普通API沒有此token仍沿原生命週期；沒有公開HTTP停機／取key端點。正常Stop等原child真正退出／exit0，40秒後的強制收尾或未知不能綠，GUI保留未確認狀態。繼承的角色key／資料等設定不能蓋過自己的實例；exclusive lease拒絕同實例雙啟動。

publish採全新C來源snapshot，RID鎖定只在snapshot變動，原repository lock及原依賴群組／contentHash保持。第一次自含publish為`control-server-d9d920...`，後補就緒輸出IOException防護的最終為`control-server-09f992...`；兩組source／locks／478輸出均保留，沒有單換共用DLL。另兩個完整solution C build各自保留；最終regular API及三工具整組在`control-suite-final-0c4b4d...`，控制台／原生工具version gate同步0.31.0。

初候選Notices完整包名／版本／nuspec名稱造成實際resolved檔名290字元（logical237），Python一般路徑失敗、extended同一原件存在；這次檢查在建新實例前失敗，沒有API場次。改短Notices/pN並保留完整package／originalFileName對照，stage採短Pkg根目錄，不改系統long-path設定；六份ZIP／各receipt原件保持。原runtime授權／NuGet metadata及明確版本的上游參考授權已保留，參考SQLitePCLRaw2.1.12的NOTICE不冒充實際2.1.13來源證明，Git blob bytes另有7項邊界測試核對。

舊報告SaveNew在CreateNew後才序列化，第一個真正封裝場`control-package-checks/run-d2c1f2ed9e4143468cb7cbfff24b0815`／40749 **exit1**，讀取ready報告遇到未完成JSON；原runner於finally正常停止、first-final child19788 exit0／graceful及cleanup空列／閉源snapshot保存。修正為exclusive同目錄暫存、完整寫入／Flush後File.Move至新目的檔，不覆蓋既有檔。受控反射呼叫真正編譯方法、讓serializer getter等待時，舊版最終檔可見且0 bytes／原子斷言exit1，新版最終檔不可見／exit0，最後JSON相同；兩份來源／binary／getter proof保持，不把控制情境當原OS排程唯一原因或完整AppDomain證明。

原子候選`run-758d60...`／18136及reviewed候選`run-a6ac68...`／95428，各**105項**完整成功；最終release `run-8ba6cac8c70640e1b14d60bdf3c4bcb6`／61594 **exit0／105項**。包含真正compiled CLI拒絕／資料與report路徑隔離、七角色身分、五獨立房25個原admission、Room隔離與越權403、同實例雙啟動拒絕、原Preparing場次／序號／任務／keys重開相同、正常End後新Linked／active0、原child handle的正常停止及父程序被終止後EOF退出、輸出不含生成key。每項數包含有限診斷逐檔遮蔽檢查；25個名冊席位不是25個遊戲連線。

GUI首場`run-93dd11eb7d134dd5856d5350ab445c68`／77858 **exit1**，只開到舊樹狀資料夾對話框，未完成API啟停，取消／關窗後cleanup空列與snapshot保留。後改選control-instance.json的OpenFileDialog，可直接輸入完整路徑；新場`run-e8f5b5...`／80930及最終`run-8241a1ad5fa24de69ffdd7ac0f923af5`／95151皆**exit0**。實際選檔／Start／Stop／關窗、就緒／正常停止文字與GUI exit0觀察，自己的API48340／37612以原OS handle核對exit0、包內coreclr與Master，原三份私有檔案hash未改。GUI只重開CLI預先建立並暖啟動的實例，沒有UI生成key、剪貼簿或瀏覽器登入；沒有保存GPU probe圖／PCM或把review當程序退出證明。

最終主包`control-server-0.31.0-release-win-x64.zip` **52,456,642 bytes／SHA `b38391f1f72115a98a60ba1bc8f5cb1e7395abe633c1366c0fa9529dce794eb1`**，478 runtime、498 manifest檔案／ZIP499含manifest，角色／票券／DB不放進包。移除測試程序dotnet PATH並設不存在DOTNET_ROOT，實際child coreclr仍在本包，這不是乾淨新機或遠端LAN驗收。舊名稱final／atomic／reviewed／ui為保留候選，不可依檔名認定主包。最終方法反例`control-report-checks/run-6d6a4726f4394b4fadfd3398787ecac9`外層工具exit0，舊方法原斷言exit1／新exit0；先前兩組方法對照也保留。

真正普通API／私有管線最初兩個5案例、之後兩個6案例均保存。最終`control-pipe/run-67f9ec78c4904fd79a65ed08f941ebc0`／38152內6案例成功：普通stdin關閉仍活、非法token拒啟、錯STOP／128字短行不授權、正確STOP、EOF、129字越界與父端輸入輸出皆關閉收尾；這些子情境合計為6個程序案例，closed-pipes沒有觀察stdout，readyEvents明確null／DisabledByFixture，不填成0。GET與POST均無公開停機路由。原default案例以外部terminate結束、不是正常管線收尾成功。

本機最終 **738規則／459 HTTP／47 world、6管線、7新Python封裝邊界、78 Node／256 Chromium**成功。初regular候選與最終各一份43 browser檔，前940＋86＝**1026份browser證據**，不是測試數。原生候選`desktop-venue/20261102-011035-4b788abf`／70763與最終`20261102-012431-fb1c45ff`／21310皆**exit0／6項／7場**，採同版原Unity0.39、各自整組新API0.31；獨立／重用／舊票／後續Linked與精確seal成功，非25位操作或封裝GameServer驗收。

`control-delivery-validation.json`核對13個本輪已terminal場次：原生兩場C52、管理／管線／GUI各原件C275與各F snapshot逐byte相同，失敗仍failed；歷史native75場3347＋新2場52＝77場3399（不混入管理測試）。前940 browser、原0.39 binary／ZIP／APK／224、327 archive、原accepted API134＋三工具各9／Checks96均保持；新舊六ZIP與每份完整publish也核對。後補每pipe案例的接受／退出metadata與CI安全上傳，`run-c876b048f96a433a947e7e102f8c7e52`再6案例成功、原C43與F相同；control-pipe-metadata-validation.json記錄總14場、control318／native52，另13份有限log／status／checks，不把runtime keys／DB加入CI artifact。沒有開啟保存SQLite，自己writer全停才各一次snapshot。完整11項仍active，原31筆／world371姿態失效、Windows startup與F吞吐根因未由本輪修復；跨機／25位操作／頭盔／MR／廠商硬體與完整遊戲伺服器部署另驗。CI精確來源與結果於本節後續更新。

## 2026-11-02：電腦端蹲姿、掩體與焦點恢復

功能[c78be60](https://github.com/peca12968/vr-command-center/commit/c78be6003513ba0e17c55db2ed281e2bd26a1517)的首[CI41324739444](https://github.com/peca12968/vr-command-center/actions/runs/41324739444)／job124902203001最終failure：738規則／459 HTTP／47 world、工作流程Python含6 crouch／素材與78 Node已過，browser在world-browser:141的camera-save點擊等待30秒逾時。原16檔artifact13091095943＋完整decoded log／ZIP **3,831,691 bytes／SHA `7cceb1bce999b8e9b14480a8141feb79772e573eeb55723afa83d166272534ac`**保存且與GitHub digest相符；沒有當刻save按鈕狀態或對應失敗圖，原GET metadata只涵蓋較早reload，不能由此證明disabled、焦點、RAF、渲染負載或產品唯一原因。

後續fixture僅在該保存操作前明確bringToFront，保存最多4筆前／後／失敗control狀態與500字訊息、可見性／焦點／button rectangle／disabled，不收HTML、input值、key、header或payload；失敗另對正確remembered分頁5秒截圖並重拋、釋放save gate／route。原locator click30秒、API期限、60秒relay、所有原斷言及產品JS/API／遊戲政策不改，沒有force點擊或重試寫入。新本機69409原handle exit0：**78 Node／256 Chromium、43檔**，實際before-click為visible／focused／enabled，after-click進入pending、.046秒callback間隔含觀察成本非RTT；這是新場成功，非舊CI根因／修復證明。遊戲及API來源、224／雙平台／原生792與五房結果未重建或改判。前838＋失敗16＋本機43＝**897份browser證據**，不是測試數；新CI結果另記。

[fixture914051c](https://github.com/peca12968/vr-command-center/commit/914051ceaac54a9c9390e201c225fc828df8a27b)的[CI41325529518](https://github.com/peca12968/vr-command-center/actions/runs/41325529518)／job124904550210／精確914051c完整**success**：Linux738規則／459 HTTP／47 world、工作流程Python含6 crouch／素材、78 Node／256 Chromium。2 Windows限定skip不是Unity／原生或頭盔證據；真正224及本機C／W原生另外核對。新CI該相機操作before-click visible／focused／enabled、after-click pending，該時來源已Ended；本機新場同刻Running，各自保存，不當舊CI當刻狀態、唯一原因或修復證明。

43檔artifact13090259562＋完整decoded log／ZIP **10,003,359 bytes／SHA `e6c3cef5cf65c247ee370031d0d8ad4ea2d37a0f9ab8ce13035883e12a4219a4`**已下載且與GitHub digest相符。`desktop-crouch-ci-success-validation.json`核對原40 runtime／F snapshot、327 archive、兩次失敗Editor、API整組及新0.39 binary／ZIP／APK保持，前897 browser＋新43＝**940份browser證據**。首validation文字比對誤用Node舊版`# tests`格式而exit1、尚未產生成功JSON，修正為本輪實際`ℹ tests`／`ℹ pass`後採新driver成功；失敗driver保留，CI本身早已完整success，不改測試數或遊戲。後續只有文件證據提交skip ci，測試來源精確914051c、遊戲來源仍e0d60e4e...。

Unity **0.39.0／Android code49／NGO29**，API/UI0.30.2／rules0.8.0／world schema1保持。無頭盔owner新增左／右Ctrl按住與C切換蹲姿，眼高1.65→1.0m、手與槍口沿原相對旋轉；移動保留高度、原速度／房界／碰撞。HUD讀原server人物位置／有效性，失焦／應用暫停或恢復／停用立即清除stance並恢復本機站立，下一個原Pose再發布。Tracked、wire、header、素材profile、傷害及0.5／1.5政策不改。既有人物依高度縮放，未新增屈膝骨架動畫；完整機制見[DESKTOP_CROUCH](DESKTOP_CROUCH.md)。

新增16項、共**224真正Editor／0失敗／0 skip**，3項是官方Keyboard在真正PlayMode Dynamic消費事件。首場224／218／6：EditMode SendMessage被引擎拒絕及3鍵盤事件未路由；改直接呼叫callback邏輯後第二場224／221／3，保存實際鍵盤值0診斷。測試依本機已安裝InputSystem的Editor鍵盤routing暫時導向GameView、finally恢復設定後才224全過，正式InputSettings未更動。兩次真正exit1的XML／log／選定來源先封存，沒有抑制錯誤或改判；不是完整生命週期引擎派送驗證。另6項Python證據反例與5項原snapshot測試成功。

Windows／ARM64 Quest同源 fingerprint **`e0d60e4ed6cefe5cd885e6aabe1621939da945ce00d56b3ed8820c0aed4db879`**及原scene／prefab ID保持。雙平台建置結束後才執行真正Windows場。Windows包 **82,647,558 bytes／SHA `09f4ac14a9497329080d018dd634ebfdee13cabb0b7e0c7d2ed8b077173e47cc`**、311 runtime／原launcher，新C展開19項通過；第一次檢查指向誤寫的不存在子目錄、未啟動遊戲，修正pointer後採新driver，失敗driver保留。APK **60,334,582 bytes**、0.39.0／49／ARM64／min32 target35及v2簽章成功，尚無頭盔安裝。舊0.38 binary／log321＋6選定來源先封存327檔，不是完整source graph；舊ZIP及APK raw保持。

真正互動場`desktop-crouch/20261102-000305-4f367a90`原handle35883 **exit0／6項**：實際C蹲下、C站起、C與W移動，再在明確Pause後最小化／恢復自有視窗、不按C仍回站姿。792完整回放／739張已接受Begin的Running／Paused幀、11保存參考逐幀相符；本場Paused失效幀0，不把排除規則稱為觀察到失效。原.5／1.5門檻保持，收到時最大來源年齡0.201763秒含輪詢／發布、非RTT。

原席0 head=(-3,1.65,-3)、席1=(-1.5,1.65,-3)、Hold NPC feet=(-4.5,0,-1)，正常任務油桶feet=(-3.75,0,-2) yaw0，不注入姿態／武器。蹲姿source tick473→519維持100血，敵軍同期確實向站立同伴開火3次；站起恰好1發／20傷害，原管理命令關閉AutoAttack。W移動保留1.0m高度，同伴原位置／1.65m高度／彈藥不變。最後兩份原admission結果健康80／0、中彈1／5、耗彈均0；CSV、戰鬥6／world792／through17、雙seal與原兩連線唯一server ACK相符，active0／cleanup空列及writer全停後snapshot成功。官方Ctrl按住／放開僅Editor虛擬Keyboard證據，本輪原生實際輸入為C／W，沒有GPU probe圖檔／PCM／頭盔或跨機驗收。

一般五房`desktop-venue/20261102-000500-7b756ab9`原handle98440 **exit0／6項／7場**，五獨立房、單房End／重用、舊票／越權拒絕、後續Linked及精確seal／active0／cleanup成功。每房一玩家，非25位操作。未重建API或共用Simulation，沿用上一輪accepted C API134＋三工具各9／Checks96的整組0.30.2輸出，沒有單換DLL。

`desktop-crouch-validation.json`逐檔核對兩個新C runtime共40檔及F snapshot相符、新F evidence含snapshot共124檔；前838 browser、AI前4場68 runtime／snapshot、原accepted API整組、舊327 archive及兩次失敗測試5／6檔保持。歷史73場3307＋新2場40＝75場3347 runtime檔，不是全歷史重跑。新APK SHA **`0310fe1870668633e03f2413cb3b927e6eceb922f7cbe534efb7d45f14a2a263`**，raw未重封裝；保存SQLite僅rb雜湊、不開連線。

完整11項仍active；原31筆／world371參戰失效、Windows startup與F吞吐問題未由本輪修復，頭盔、MR、跨機及25位操作仍待實際驗收。完整CI精確來源及raw雜湊核對結果另記於本節後續。

## 2026-11-01：統計來源標籤不能當完整數字讀回

AI功能`17b75e9`的[CI41297698388](https://github.com/peca12968/vr-command-center/actions/runs/41297698388)／job124821936708最終failure：738規則／459 HTTP／47串流、工作流程Python含7 targeting／素材及78 Node已過，browser在check.cjs:205統計列精確斷言失敗。原只等「模擬資料」標籤後立即讀整列，沒有該刻row metadata；失敗後PNG的數字已正確，不能由較晚截圖推定斷言時也正確、或證明唯一CI原因。4檔artifact13080141669＋log／ZIP **1,053,078 bytes／SHA `9297eabd5a6fd7dfb3111cb6fb6ed96d0f01a634a3ce79b62fbd6c3071f78594`**精確保存，原failure不改判。

自己的C BrowserRuns保留原origin-only等待與精確數字斷言，只加入可控的真實較早GET：先接受ShotFired、擷取through13統計但暫不交付；再接受其餘3筆到session16，交付原GET。產品確實顯示「模擬資料」及Alpha 01的1／0／0／0／0%／100，原等待成立、原斷言失敗，16486原handle exit1；metadata與斷言前PNG保留。沒有偽造統計body或重送寫入，只持有同一次授權API實際回應。這證明等待條件不足，不把受控情境套成原CI的時間根因。

正式fixture保留同一受控前提，新增一項必須看見舊prefix的檢查；釋放後用原單一30秒DOM等待核對「來源＋完整統計列」同一讀取，再做原精確斷言，polling100。四筆原報告／ID／順序、產品JS/API／8秒API與遊戲0.5／1.5政策均不改，沒有寫入重試或提高期限；setup的擷取與舊prefix觀察也各有30秒界線，finally釋放兩gate／移除route。失敗另存無憑證的DOM統計列／phase／notice並重拋。

新本機37059原handle exit0：**78 Node／256 Chromium**，42檔`console-ai-target-stats-after-20261101`包含through13／accepted16反例metadata與完整checks。`ai-target-stats-fence-validation.json`核對舊CI4／受控反例7／新42、原68 runtime／F及遊戲binary／ZIP／APK hash未變；702前browser＋初41＋CI失敗4＋反例7＋新42＝**796份browser證據**，不是796項測試。本輪沒有新Unity／API建置或重跑原生，0f8287b0...／208及原三人／五房結果保持，完整11項active。

[fixture8dbb874](https://github.com/peca12968/vr-command-center/commit/8dbb8749a2cb5bbfeda5defb3b1e99a29ceec315)的[完整CI41298762465](https://github.com/peca12968/vr-command-center/actions/runs/41298762465)／job124825142728／精確8dbb874最終success：Linux738規則／459 HTTP／47 world、工作流程Python含7 targeting／素材、78 Node／256 Chromium全部成功。CI也保存through13／accepted16受控前提。2 Windows限定skip不是新Unity／native或頭盔證據，本機各場與雲端分開；原17b CI及受控舊fence均仍failed，不當原CI時間根因／產品修復證明。

42檔artifact13080935513與log／ZIP **10,040,719 bytes／SHA `20f05858ddf4861748e31d5c06414ed59541125acc0441a2c9fd71d4c182fc95`**已保存，下載與GitHub digest相符。`ai-target-ci-success-validation.json`重新核對前796 browser＋新42＝**838份browser證據**、本輪68原runtime／F snapshot、0.38 binary／ZIP／APK及舊327 archive未變。後續僅文件證據skip ci，測試來源精確8dbb874，遊戲來源仍0f8287b0...；ROADMAP目前M2／建置門檻更新208／0.38，不重寫歷史數量。完整11項active，跨機／頭盔／25位操作及原31／world371／startup／F吞吐仍另驗。

## 2026-11-01：AI 受阻後選擇可命中的玩家

從乾淨`5b4ff41`接續第6項，[AI_VISIBLE_TARGETS](AI_VISIBLE_TARGETS.md)修正只嘗試最近玩家的選敵：原同房／connected／存活／天氣日夜射程候選依距離與GUID排序，逐一原Cast，只有真正命中該玩家才接受。仍20tick／20傷害、原槍口、Hold／Patrol／Advance、Pause與0.5／1.5政策，Advance仍朝原最近合格者移動。AimTarget只供冷卻外觀追蹤，每發重新Cast，不改歷史射線、Tracked、wire、schema1／rules0.8.0或素材pin。最多每NPC5候選，完全受阻的Cast量可能增加，沒有據此宣稱25人效能完成。

Unity **0.38.0／code48／NGO29**、API/UI0.30.2；最終fingerprint **0f8287b002f46d0824bf4f3c27a450b672cc7554fdc156a4c238affdcd8f32b0**，原scene／prefab ID一致。Prepare79313、Tests37810、Desktop22837、Quest9574原handle均terminal exit0，**208真正Editor／0skip**；738規則／459 HTTP／47 world-stream、78 Node／255 Chromium與7新Python＋5 snapshot通過。初.NET fixture對nullable射線未明確檢查，CS8629失敗的C build／log保留；修正為pattern確認，採另一新C build，沒有放寬測試。首誤用Windows PowerShell5受執行政策拒絕、未啟動Editor；實際採既有PowerShell7 RemoteSigned，沒有改政策／授權或重裝工具。

真正ArenaSession產生器以六個合法VR地面物件得到NPC(-3,0,-1)與(-3,0,-.25)，玩家原席0／1／2 head在X=-3／-1.5／0、Y1.65、Z-3，原Connect＋有效Pose後才可攻擊。舊來源第1tick健康80／100／100、後NPC無射擊；50個Runtime檔僅換ArenaWorld、Program逐byte相同的副本exit0，健康80／100／80，後NPC首tick選第三位。9個行為案例在.NET與真正Editor共用同一pure fixture，另驗掩體／GUID平手／冷卻重選／Pause停火／射程房間隔離／Advance政策／外觀不改保存射線。

初未Connect、次未Pose候選不能當有效玩家；正確入場的兩人候選，其第二條射線仍被NPC身體邊緣擋住，舊／新不開火合理。這些C來源／log與原兩人native `20261101-145732-14715650` exit1均保留，不稱較遠玩家可見。修正為三人後，舊0.37.2 native `20261101-150050-725e00df`仍exit1、後NPC從未開火，兩場的原戰績／CSV／雙seal及cleanup成功。後續helper另加傷害配對、Pause序號與全回放靜止核對，不能稱native前後完全相同依賴graph；共用來源隔離對照另由相同Program／單Runtime檔提供。

最終新native `20261101-182258-207e5e24`真正exit0／**4項、32全回放／12張已接受Begin後Running／Paused幀**：兩個tick1 EnemyShot及緊接20點傷害、最近玩家仍存活80才後NPC選第三位；三份原admission結果健康80／100／80、中彈1／0／1、CSV／雙seal／三個唯一server ACK、helper SHA前後與cleanup成功。原3玩家全程靜止Simulated／connected、兩NPC Hold原位健康100，無玩家輸入／姿態注入／GPU／PCM；收到時最大來源年齡0.150225秒非RTT。五房 `20261101-182316-77cc9ff6`／8844 exit0，原6項／7場隔離／錯票／重用／後續Linked及精確seal，仍每房1位非25位操作。

新Windows包`windows-player-0.38.0.zip` **82,646,224 bytes／SHA `1f4a27d8ca7b310acfd24a4a018b44449fb73b1c2ac02107ea1af2251ed35d7c`**，311 runtime／原launcher a65846da...，新C展開19項核對／拒絕成功，非完整GUI／跨機。APK **60,330,662 bytes／SHA `7e175d4a4eb566758e454457d17a7adbfac5c615bae184525c2b6ad6ab3d517e`**，0.38.0／48／ARM64／min32 target35、v2簽章成功，無實機安裝。原82,782,417 APK與新檔各105 ZIP項，compressed60,306,850→60,309,211、非索引payload22,475,567→21,451；容器差異不當內容縮減／ELF／性能或唯一Gradle原因，raw不重封裝，receipt totalBytes不是APK大小。兩平台建置結束後才跑新原生，前後不當效能因果對照。

`ai-target-before-validation.json`核對舊327（321binary/log＋6選定來源）archive、50檔Runtime／相同Program、兩失敗native28 runtime／F snapshot、前702 browser／上一場native48／runtime14；`ai-target-delivery-validation.json`新2場40 runtime與F snapshot、新F122，加前失敗F66共188／runtime68，歷史69場3239加4場68為**73場3307 runtime檔**，不是全數重跑。新41 browser與前702保持；原0.30.2 C API134＋三工具各9／Checks96依hash不變，新整組也各自保存，不單換Simulation DLL。全部自有writer停才一次snapshot，保存SQLite不開，原正式5080／舊ZIP與APK均保留。CI結果另補，完整11項active，原31筆／world371／Windows startup／F吞吐與跨機／實機各自未修復。

## 2026-11-01：雙擊場地定位觀戰鏡頭

從乾淨`2e86a34`接續第9／10項，[OBSERVER_GROUND](OBSERVER_GROUND.md)新增即時觀戰與3D模擬回放的左鍵雙擊場地定位。API／UI **0.30.2**；目前渲染鏡頭射線與Y=0投影，只接受來源實際包含的12m房間，保持角度／距離、target高度0.8m，成功才退出follow。間隙／房外／未包含房間／無效射線不移動；草稿不被改寫，書籤仍明確保存與原身分／場次權限，回放不seek。沒有管理／玩家移動或碰撞規則變更。

本機locked restore／零警告build、729規則／**459 HTTP**／47 world-stream、**78 Node／255 Chromium**完整通過。80365原handle terminal exit0；新41份browser證據含ground截圖已檢視，6個新增Node反例與7個browser檢查涵蓋五房幾何、房外、草稿、角度距離、follow、無寫入、書籤重載與回放不seek。本次Windows HTTP完整成功是新場結果，不將以前startup失敗改成通過，也沒有修改OS／auth／期限或證明根因修復。

真正Windows `desktop-venue/20261101-143859-67587c42` helper36250／browser80356均exit0：**54 UI／native、165世界幀**，名冊替換／環境AI／Pause／End、精確雙seal／原玩家結果與CSV／回放ledger一致、active0及cleanup無殘留。最大來源年齡0.191771秒非RTT，SwiftShader觀戰不是新原生GPU。14個C runtime與F snapshot逐檔相符、新F48；歷史68場3225再加14為69場3239，不當25人／跨機／頭盔驗收。

`ground-camera-validation.json`核對前620 browser／上一輪74 runtime與F snapshot／Unity二進位及包hash、新41 browser／48 F及14 runtime。新C API134（新JS與.gz）＋三工具各9、Checks96保存hash；Unity0.37.2／47／NGO29／7d3e...及原199 Editor／雙平台／ID保持，沒有新Editor或APK重建。首次準備腳本cp950讀HTML失敗的初C build保持，完成後採明確UTF-8與新C build；不覆蓋舊API或正式5080。完整11項active，原31／world371／F吞吐及外部依賴未修復。

[功能5df27a8](https://github.com/peca12968/vr-command-center/commit/5df27a8c2ff40ea268a22aa565ad2ce69a3e6f33)的[完整CI41281968515](https://github.com/peca12968/vr-command-center/actions/runs/41281968515)／job124775534858／精確5df27a8最終success：Linux729／459 HTTP／47 world、工作流程Python／素材、78 Node／255 Chromium全過。2 Windows限定skip不當本機Windows／Unity或頭盔證據；本機459是前述獨立成功場，不混為同一次執行。41檔artifact13073935856＋log／**10,018,457 bytes ZIP／SHA `7386c55d2cdbae6b531e384550c9dd98586a000d0b159efd87c5ca7f379fd42d`**下載與GitHub digest相符；`ground-camera-ci-validation.json`核對前620＋本機41＝661 browser、48份native與14 runtime／snapshot、原Unity binaries／ZIP／APK保持；新增CI41後合計702 browser證據。後續僅文件skip ci，測試來源精確5df27a8。

ROADMAP已移除過期的「等待GitHub帳務」待辦並更新現有M2與建置檢查數量199／0.37.2，保留歷史失敗與完整待驗範圍，沒有把SDK或已恢復CI列為目前阻礙。

## 2026-11-01：鏡頭重載 CI 失敗與有界請求觀察

導航功能來源`40f8516da53feb9610dc75bb9fb19d85ddf23dbe`的[CI41279882687](https://github.com/peca12968/vr-command-center/actions/runs/41279882687)／job124769450079最終failure。729規則／459 HTTP／47 world-stream、工作流程Python／素材及72 Node已過；Chromium在新登入觀戰頁等待已保存鏡頭選項30秒逾時，不能稱248項通過。失敗畫面已載入世界，鏡頭提示回應不完整；原資料沒有該GET的狀態／完成時間，不能推定API、body decoding、主機或路由根因。

原15檔artifact13073096399、log及ZIP3,813,684 bytes／SHA `1d2e87c7548e5abaa7be8d7d06e817d17d1be62628e70b2a0e95e57ab0aa8007`完整保留。僅browser fixture加入該新頁重載期間最多128個同源API GET metadata，記path／狀態／回呼相對時間／有限錯誤碼，不記headers、query、body或憑證，不改產品、路由、操作順序、30秒斷言或10秒API期限；超界仍失敗，完成只是觀察未超界，不代表請求全部成功、body已解碼或RTT。finally卸除listener並保存metadata，原failure仍保留。

本機新場`console-navigation-anchors-diagnostic-20261101`完整248 Chromium通過，40檔含13條GET metadata；鏡頭GET 200並正常finished。這是新場成功，不是原逾時的根因或修復證明；使用本輪隔離C API與relay，不動正式5080。僅fixture變更，不重建Unity／APK或改稱另一來源。

[診斷f1dda0a](https://github.com/peca12968/vr-command-center/commit/f1dda0a4a956d2bab598ebccc883fbcd919aa2e9)已推送main；[完整CI41280898186](https://github.com/peca12968/vr-command-center/actions/runs/41280898186)／job124772433249／精確f1dda0a最終success：Linux729規則／459 HTTP／47 world-stream、工作流程Python含13 navigation／素材與72 Node／248 Chromium成功。2 Windows限定skip不是native／Editor或本機Windows完整HTTP通過；原startup失敗不改判。此場13條GET metadata中鏡頭GET 200並finished，仍非原失敗根因證明。

40檔artifact13072709116、log與ZIP **9,683,723 bytes／SHA `e75e9de589076b63e3024fd135a989f3c9a071e989e02a602b482dbe0805d9ba`**已保存，下載與GitHub digest一致。`navigation-anchor-ci-success-validation.json`核對原525 browser／前CI失敗15／本機新40、共580份既有browser證據，新增CI40後合計620；新4場74 runtime與F snapshot、APK／ZIP仍原hash。`navigation-anchor-browser-diagnostic-validation.json`保留本機成功與前失敗hash；沒有覆寫40f失敗。後續僅文件證據skip ci，完整CI來源精確f1dda0a；Unity來源仍7d3e／199／雙平台，完整11項active。

## 2026-11-01：實際非格點起終點接線與原生逐tick端點觀察

從乾淨`13f22c7`接續第6項，[AI_NAVIGATION_ANCHORS](AI_NAVIGATION_ANCHORS.md)修正0.75m任務候選座標接到0.5m路網的問題。Unity **0.37.2／code47／NGO29**，API/UI0.30.1、world格式／rules0.8.0及原scene／prefab ID保持。最終Windows／ARM64 Quest同源 **7d3e1a926f1b1c9176f03809af75de0c2af7be0e5f3e4ec24851664327aa4f92**；最終Tests62491／Desktop70410／Quest21212原handle皆exit0、**199真正Editor全過0skip**。先前Prepare42518／Tests62157的195項／Desktop94888／Quest31685為2c96...初候選，後加觀察器的Prepare78173亦exit0；初候選321檔及XML／receipt另存，不能把相同0.37.2／47當成相同來源。

凍結0.37.1原始ArenaSession產生器兩反例實際exit1：油桶(-4.6,0,-1)使合法出生(-3.75,0,-1)取整到被擋(-4,0,-1)，路線0點／320tick仍不動；油桶(5.1,0,5)使巡邏目標(3.75,0,5)被改為(4,0,5)，路線30點／320tick仍差.25m。相同Program與50個Runtime檔只換GridNavigation，兩例exit0、保留精確起終點、到達與逐tick通行／位移合格，JSON／C工程與binary保存。這是.NET規則證據，非原生或硬體。

實際兩端先Walkable，再各接所在格最多四個可見角點，起點→角點／角點→終點各依原ClearSegment核對；多起點／多終點BFS、625格四方向與2500 sbyte邊快取保持，回傳路線保留實際兩端。共享可見角點的近端點也須真實直線可走才直連；不是修改候選順序、搬動出生、傳送、放寬.3m半徑／.05m取樣／.1m活動tick或.15m巡邏切換。網格解析度與無可用局部角點的狹窄區域仍有限制，沒有完整3D／NavMesh／人群導航宣稱。原回放使用原幀，不重算歷史路線。

新6核心與6導航Editor案例驗產生器兩端點、往返／逐tick安全、Linked外側兩房、同格真實目標及不能切過旋轉角；另4 Editor驗逐tick觀察器的瞬間端點、完整最早tick／row上限、漏tick／倒退拒絕、Editor不安裝。**729核心（原723＋6）、199 Editor（原189＋10）**通過。Python navigation13＋artifacts5＋first-person7＝25通過，包括profile幾何、非格點目標、原生身分／tick／期限及finish IO失敗仍native cleanup；語法／diff、原player-body pin與293官方transport＋1 scoped patch通過。

| 真正原生場／原handle | 結果與範圍 |
|---|---|
| `desktop-navigation/20261101-132748-57972625`，46348 exit1 | 2c96初候選、未開逐tick觀察。20秒live189幀、16–204連續仍無<.2m端點；原failed與cleanup保存。closed209幀中world81／82為tick141／143、位置約(4.5,0,4.799997)、距.20000267m且forward相反；沒有142原始位置，不能插補到達或改判通過 |
| `20261101-134848-394c3763`，30771 exit0 | 最終blocked-start，4項／268完整回放／248已接受Begin來源幀／9 refs，fault0；實際409 row連續tick1–409，端點row142距約.100003m、首次Begin來源row後7.052074秒，worldSequence=null |
| `20261101-135057-d4dc1db0`，92372 exit0 | 最終non-grid-goal，4項／148完整回放／118來源幀／9 refs，fault0；143 row連續tick1–143，最早<.2m為row141距約.1500001m、6.991734秒，worldSequence=null |
| `desktop-venue/20261101-135539-ac75f5f8`，14004 exit0 | 一般五房6項／7場，隔離／錯票／單房環境AI與Pause／席位重用／後續Linked及精確seal、活動0、cleanup成功；沒有navigation-tick-probe目錄，非25位操作或全複本逐幀證據 |

無探針首場的closed rb／checksum／序號分析只證明已保存位置，沒有tick142資料；新場row142不能補舊場、不能用反向或clock校準猜到達／根因。兩個最終場都明確--tick-probe，僅自己的Windows Development server加--vr-navigation-probe：每個真實session.Tick後觀察當下NPC，不改20Hz規則或10Hz world錄製／傳輸；普通／Editor／Android／client不安裝。最多180秒／4096 NPC row，保持完整最早tick，自動上限／漏tick／倒退不可complete，收集中不寫狀態，明確finish停收集／clock後一次report。只輸出NPC欄位、原session／stream、observed及單調seconds，不輸出玩家姿態／憑證／GPU／PCM，不是零擾動。

工具維持<.2m／20秒，原生row須完整1..N、原NPC／room／health、位置／位移、正確session／stream及已接受Begin；不以缺失tick插值或硬配world序號。原生證據獨立存，refs另取真正world，兩場最早replay/live分別20/21與30/32。普通回放仍逐張核對Begin4已套用後所有Running／Paused的原玩家健康100／connected／Simulated、NPC／房間／攻擊關閉與位置／位移。診斷在後續Hold／Pause／Advance與End前已finish；原admission結果、CSV、精確雙seal、唯一server ACK與兩層cleanup成功才complete，5helper SHA前後一致但不是完整graph。兩個場與最終Quest建置重疊，五房在build結束後；不同條件不當因果／效能對照，原31筆／world371未修復。

最終`windows-player-0.37.2-final.zip` **82,645,932 bytes／SHA25dd1ee56234cd7da3da1f9671877b6c8967a41f03d71f903f3008558425d5c4**，311 runtime／原launcher a65846da...；新C展開da4070d46cef4107b80fbb63a6ac3576、28311 exit0／19真正核對拒絕，非完整GUI／跨機。普通0.37.2 ZIP為2c96初候選、5ca9a6f5...，其19項與原件保留。最終APK **82,782,417 bytes／SHAd804087c10e2c0b376d3eb2e3bd875a5ef3bf97760c0a6b30c5a0dadc47b5eaa**，0.37.2／47／ARM64／min32 target35、v2 debug簽章成功，無頭盔安裝。

APK raw比初候選60,310,826 bytes大；ZIP索引仍105項，compressed payload僅從60,289,375增至60,306,850 bytes，非payload區段由21,451增至22,475,567 bytes。libil2cpp raw增67,632 bytes，額外大段位於目前索引payload之間；這是容器範圍觀察，不當完整ELF／遊戲內容增量、執行效能或唯一打包原因證明，raw與簽章保持、不重新封裝，receipt totalBytes不是APK大小。

`navigation-anchor-prior-validation.json`核對前64 runtime3151與各F snapshot／前F3719；`navigation-anchor-runtime-validation.json`新4 C runtime74與F snapshot相符、新F190，合計68場3225 runtime檔，前525份browser／CI、原API三組159／mission accepted與拒絕候選／本輪C API及工具保持。`navigation-anchor-probe-validation.json`另核對兩份完整raw report、原生來源與null world序號、一般五房無probe、兩組321 binary/log＋各10選定來源、4個原Git source blob；另存原CombatAuthority blob，不稱完整依賴graph。全部自己的writer全停才一次snapshot，原C不移動，保存SQLite不開連線。

完整11項active，仍同機Simulation／headsets0。CI結果另補；原31／world371、Windows完整HTTP startup、F吞吐、多人持續操作、跨機／Wi-Fi／Quest／VIVE／MR與廠商硬體各自未完成，不因這兩個導航反例或新場成功改判。

## 2026-11-01：敵軍繞行旋轉掩體，保留端點觀察逾時

從乾淨`0368b33`接續第6項，修正[AI_NAVIGATION](AI_NAVIGATION.md)。Unity **0.37.1／code46／NGO29**，API/UI0.30.1、world格式／rules0.8.0保持。新雙平台fingerprint **69d247a9ecfa7b42ee1e9314e0319869995f1876379850928f5725901e642fc2**，原scene／prefab ID一致；Prepare84165、Tests14853、Desktop55866、Quest67152原handle皆terminal exit0，**189真正Editor全過、0skip**。正式5080不動；新.NET API／三工具／Checks均在自己的C BuildRuns，第一份fixture失敗候選與舊API copies保留，原Windows完整HTTP startup問題沒有在本輪改判。

舊GridNavigation只看格點可站立便相連，Move卻以原ClearSegment檢查實際路段，遇旋轉掩體角落會拒絕移動再選同一路。凍結舊來源反例：45°油桶(.25,0,.25)，(-2,0,1)→(2,0,1)產生9點／1條不可通行邊，320活動tick仍卡住。另一個真正任務產生器端點配置：油桶(.25,0,-1.75)、(-4.5,0,-1)→(4.5,0,5)，舊31點／1壞邊、320tick仍約(0,0,-1)。兩個.NET實際exit1、原JSON／C來源／binary保存，不當原生或頭盔。

只改GridNavigation的凍結來源副本產生11點／0壞邊並可往返；前後50個Runtime檔只有該檔不同、Program逐byte相同。新搜尋以既有ClearSegment核對格邊，正反向共用不可變幾何的有界快取：每房625格／2500個sbyte槽／最多1200無向邊。原四方向／順序、.3m半徑／.05m取樣／.1m活動tick上限與Move再次檢查保持，沒有改傷害、目標、Tracked或封包。歷史回放使用原幀，不重新求路；不是完整3D地形、任意非格點端點／動態目標可達性或人群導航完成。

本機**723核心檢查**（原717＋6）通過；Editor新增5案例含往返／逐tick通行速度、Hold／Pause、Linked兩外側房及封閉牆。首候選CoreChecks在第280項因fixture誤判封閉牆而崩潰退出：x=-4..4的五沙包仍留兩側通路，實際繞行合理；log／兩來源與C候選binary保留。修正fixture為x=-4.8..4.8／2.4m間距後新C建置與723成功，沒有修改遊戲半徑或刪除原失敗。新API採`navigation-final-build-path.txt`下bin，舊／失敗候選不覆蓋。

| 真正原生場／原handle | 結果與範圍 |
|---|---|
| `desktop-navigation/20261101-125121-d130384b`，41746 exit0 | 4項／133完整回放、9 refs，原getter及初次live檢查點起的玩家／NPC核對；不是最後較早的Begin回放閘門 |
| `20261101-125410-3d188963`，43827 exit1 | 提早回放閘門已加入，但原20秒getter沒讀到短暫端點，未進後續控制／完整回放／結果驗收。cleanup成功、原failed保留；closed world90／91、tick150／152確已到達，不當來源未到達 |
| `20261101-125724-93f88fed`，35386 exit0 | 最終4項／**128完整回放／113已接受Begin後Running或Paused幀／9 refs**，fault0；live端點串流69幀連續17–85、tick150，Hold／Pause／Resume／Advance、零戰鬥統計、原admission結果／CSV／精確雙seal／唯一server ACK與cleanup成功 |
| `desktop-venue/20261101-125821-51d9d6e5`，97903 exit0 | 原五房6項／7場、隔離／錯票／房1環境AI與Pause不擾其他房／席位重用／後續Linked及精確seal、活動0、cleanup無殘留。每房1位，非25位操作或逐client複本全程驗收 |

端點getter逾時在writer全停後以closed journal的rb／record checksum／序號metadata另查：保存219幀、world90最短2.861e-6m、91仍<.2m。closed分析不是完整規則重放，不開保存SQLite、不修復／ack，也不把已保存端點補成live成功或推定主機／網路根因。工具改成單一連續live串流、20秒／256幀、序號不能跳、每packet用原header擷取UTC＋elapsed檢查1.5秒來源年齡，**不延長20秒或放寬.2m**。原逾時仍exit1，沒有重寫其結果。

最終接受Begin4，回放最早納入world15、首live Running是17，兩者分開；不是從第一個live檢查點才開始忽略更早來源。每張已接受Begin的Running／Paused保存幀核對原玩家健康100／connected／Simulated、原NPC、房間／攻擊關閉、旋轉盒外位置及活動tick位移上限，中間失效恢復也失敗。保存之間缺少的tick不插補路徑；全20Hz通行另由共用規則／Editor檢查，不當每render或複本封包證據。新5helper SHA前後相同不是完整OS／runtime graph。端點最大收到時來源年齡0.117452秒，不是RTT／FPS或性能基線。前兩場與Quest建置重疊，最終場build已結束；負載不同，不當因果對照。

本機7 navigation＋5 artifacts＋7 first-person＝**19 Python**，含短暫端點先於返回仍被串流觀察、舊來源不可當新鮮、原人物失效／換NPC、NaN／bool、凍結tick移動及缺tick不插補；語法／diff／原player-body pin與293官方transport＋1 scoped patch核對成功。無新GPU／PCM、遊戲按鍵或姿態注入；原0.37.0六張手臂GPU證據保持原範圍。

新Windows包`windows-player-0.37.1.zip` **82,642,694 bytes／SHA cba3a25ba590c21f0b38b152042242b373ea656dce4c1ff434a742490f3b841f**，311 runtime檔／原launcher a65846da...；新C展開navigation-b0e09beb0a734d3f92cccfce3ddacec0、85847 exit0／19真正launcher核對拒絕，非完整封裝GUI／跨機。Quest APK **60,313,650 bytes／SHA723e57b59320b77a0b32523d092a75c6b5fe937325187be1f9fdc484505a980a**，com.vrcommand.quest／0.37.1／46／ARM64／min32 target35、v2 debug簽章成功；receipt建置總量不是APK大小，無實機安裝。建置前321舊binary／logs及10來源精確另存navigation-history-1fc294c6bd3f4748890eb85338834af5，原0.37.0及0.36.1 ZIP保持。

`navigation-prior-validation.json`核對前60 C runtime3083與F snapshot、前F證據3540、舊321＋10與兩個新C build候選／凍結反例來源。`navigation-runtime-validation.json`再核對**新4 C runtime68檔與F snapshot逐檔一致、新F179檔、486份前瀏覽器／CI證據**，總64場3151 runtime檔；原三API組159、accepted mission API及三個舊候選、新accepted navigation API／三工具／Checks都依原hash保持。全部自己的writer停才一次snapshot回F，原件不移動、保存SQLite不開連線。完整CI另補本節。

[功能9959c64](https://github.com/peca12968/vr-command-center/commit/9959c644bc91f93dcb24e87e43539b2fa3e6bf4b)已推送main；[CI41275385420](https://github.com/peca12968/vr-command-center/actions/runs/41275385420)／job124756415659／精確9959c64 **完整success**：Linux restore／build、723規則／459 HTTP／47 world-stream、工作流程Python（新增7 navigation）／素材與72 Node／248 Chromium通過。2 Windows限定skip不當原生、Editor或本機Windows完整HTTP啟動成功；先前startup失敗不改判。

39檔artifact13071202925與log／**9,675,831 bytes ZIP／SHA565bde8df61294a09f141c7dc60332792c92cda2c25762f5f1d39bd18ec141a5**已保存，實際下載與GitHub digest一致。`navigation-ci-validation.json`再核對前486份瀏覽器／CI證據、新runtime68與snapshot、APK／ZIP未變。後續僅文件證據skip ci，測試來源精確9959c64，不重跑冒充另一場。

完整11項active，仍同機Simulation／headsets0。這個可重現的旋轉格邊錯誤與原31筆／world371姿態失效、Windows startup、F吞吐各自不同，後者未修復；多人持續操作、複雜地形、跨機／Wi-Fi／Quest／VIVE／MR與廠商硬體仍待驗。

## 2026-11-01：電腦端第一人稱軍服手臂

從`e8b346a`接續完整11項中的軍事人物介面，新增[DESKTOP_FIRST_PERSON](DESKTOP_FIRST_PERSON.md)。Unity **0.37.0／code45／NGO29**、API/UI0.30.1／rules0.8.0保持；同源Windows與ARM64 Quest fingerprint **09eed85207b33d5304f6aae294a5aebe3237d48eca3f2b0cf9b01679530ed5c8**，原scene／prefab ID一致。Prepare9556、Tests46731、Desktop83079、Quest86239各原handle terminal exit0；**184真正Editor全部通過、0skip**，不是Python或雲端替代。新增5案例保護本機端點／隱藏、Tracked早退、死亡／失聯、切回遠端及保存換彈／Pause。沒有改API、wire、Shared數學或正式5080。

本機桌面owner現在顯示自己的軍服上臂／前臂及既有手套，隱藏自己的軀幹／腿／頭盔；其他玩家仍完整呈現原人物。重用五Mesh／404面與原player-body-v1 pin／lease／PlayerPresentation.Pose，不移動原槍口／pointer／Tracked關節、不新增Collider或改戰鬥規則；Tracked owner計算前隱藏返回。這是裝飾性兩節臂，不當完整追蹤人物、手指／腰腳或動畫完成。原0.5／1.5秒政策保持。

新check-desktop-first-person只開自己隔離API／server／可見client，實際Right／Down、Space、R由computer-use操作；每次action後刷新並經模型觀察，六張原生GPU檢視後另呼叫寫review.done。沒有姿態／輸入注入。**desktop-first-person/20261101-114930-25078562、57292 exit0，4項／6張GPU／1195完整連續回放／5原來源檢查點**；初次checkpoint起全部Running原solo健康100／connected／Simulated／非suspended，無瞬間參戰失效。paused兩張端點delta0、head／右手套握點對來源最大差5.382805623455056e-08m，左腕隨保存換彈tick移動。彈匣30／備彈89、1發0中0殺健康100，原admission最終結果、CSV、精確combat／world seal及唯一server ACK一致。probe明確finish先於End、兩層cleanup乾淨才complete；五helper hash不是完整依賴graph。

實際畫面可見左右袖，自己的頭盔／軀幹沒有擋住相機；槍仍會遮住部分手臂，沒有每角度完整可見或動畫品質宣稱。Quest建置與此功能場重疊、視窗尺寸隨焦點改變，不能作乾淨效能基線、像素benchmark或因果控制。NativePlayerBodyProbe保持明確Windows Development／visible untracked／600秒／8圖／900萬像素、無PCM／輸入；新增獨立firstPerson，遠端players[]及walking就緒語意不變。

舊人物工具第一次`desktop-venue/20261101-115513-5ef0869d`，72822 exit1：原300秒observer定位期限已到、target尚未啟動，沒有observer.done，cleanup乾淨；CUA視窗已關時停止輸入並重觀察，原失敗保留。第二次`20261101-120615-644b0391`，30210 exit0／4項／6圖，原工具與300秒不變；實際組合鍵定位再W／Space／R，遠端walking非零、paused端點差2.384185791015625e-07m。前景槍／袖及Pause文字遮住部分遠端身體，沒有全像素可見宣稱。原工具只有最終replay／seal統計，不冒充新增全程連續性或全員ACK。

Host場`desktop-debrief/20261101-121759-e60ee300`真正terminal exit0／4項：兩份原結果符合seal、移除admission不收結果、Host等peer ACK才shutdown。五房場`desktop-venue/20261101-121914-2748af54`已停止、stage passed／**6項／7場**、cleanup errors／remaining空：五房各1人隔離／錯票拒絕、房1環境與AI／Pause不干擾四房、重用席位及後續Linked、七個不同stream精確seal成功。**五房原shell回應在輸出裁切中遺失，不補造exit0**；依原stage／summary／cleanup及停止程序描述結果，不當25位同時操作。

本機7 first-person＋5 artifacts＋27 active＋12 debrief＝**51 Python通過**；包含私有owner／Tracked／遠端分類、錯phase／tick／rig、端點錯誤、NaN／bool、cleanup IO反例及中途失效恢復仍失敗。語法／diff、原player-body幾何pin及293官方transport檔／1 scoped patch核對成功。CI已加入新suite，完整雲端結果待另錄，不能把本機51當完整.NET／瀏覽器結果。

Quest實際APK **60,313,726 bytes／SHA067c41347a284e05fb5d8695277e0907052a984050c2220313dd23a21bce6e94**，包名com.vrcommand.quest、0.37.0／45、ARM64、min32／target35；receipt totalBytes1050650189是建置摘要、不是APK大小。首次apksigner.bat因JAVA_HOME缺失失敗log保留，之後明確Unity Java執行jar、v2驗證成功（Android Debug certificate），沒有改系統環境或宣稱商店／實機驗收。

新`windows-20261101-120352-b2b5c1c3.zip` **82,642,471 bytes／SHA08aa93385e4e2b2688714fee56ce6d9dfe6592574d8e7e844e15020e815ae030**，311 runtime／manifest、原launcher source a65846da...；新C展開`first-person-2de5107449ec4491b9401a514db4a699`，64171 exit0／19真正launcher核對與拒絕。不是完整封裝GUI／跨機或安全性提示操作驗收；manifest不是簽章。建置前321舊binary／logs及9來源精確另存first-person-history-eb3833ea49864c95930e651b70cada11，原兩ZIP保持。

`first-person-runtime-validation.json`在各場停止與cleanup核對後完成：**新5 C runtime102檔／F snapshot逐檔一致、新F證據221檔；前55 C runtime2981檔與各snapshot保持，合計60場3083檔**。原動態／observer／operator／尾界／獨立房歷史與三組API159、accepted mission API及拒絕候選、舊ZIP與archive321＋9、前CI39檔均核對原hash；保存SQLite只raw bytes、沒有開連線。新場五房shell exit未知另列，不把hash一致或stage成功補成原handle exit證據。

[功能81108e1](https://github.com/peca12968/vr-command-center/commit/81108e1c46a934dc4f90ba59d03a41dadffb3db9)已推送main；[CI41273127773](https://github.com/peca12968/vr-command-center/actions/runs/41273127773)／job124749808406／精確81108e1 **完整success**：Linux restore／build、717規則／459 HTTP／47 world-stream、工作流程Python（含新7 first-person）／素材與72 Node／248 Chromium成功。2 Windows限定skip不當原生或重跑Editor；雲端成功不改判前輪Windows完整HTTP啟動逾時。

保存39檔artifact13069804420、log與**9,710,227 bytes ZIP／SHA84d3f956d75fbd71e4ec680f03dc809b43266e9f3b924ad3d81a7a4fd787dec0**，實際下載與GitHub digest一致。`first-person-ci-validation.json`另核對新runtime102檔與snapshot未變；`first-person-browser-history-validation.json`依既有manifest核對447份前CI／本機瀏覽器檔，包含較早三個console快照及前輪讀取失敗／成功資料，範圍較前313份更廣、不是新增遊戲測試。後續只有文件證據使用skip ci，測試來源精確81108e1。

完整11項active；無頭盔、同機Simulation，原31筆／較新world371、Windows完整HTTP startup與F吞吐各自未修復。下一步仍包括多人持續操作、完整人物動畫／追蹤、跨機／Wi-Fi／Quest／VIVE／MR與廠商硬體，不重寫舊失敗。

## 2026-11-01：任務版本讀取不再被背景刷新失敗取消

上一輪屬實際進展，從乾淨`ada9eee`接續完整11項目標的第8項。[MISSION_READ_RECOVERY](MISSION_READ_RECOVERY.md)更新API／UI **0.30.1**，任務／世界格式、rules0.8.0、NGO29、Unity0.36.1／code44／e0594513...與原scene／prefab ID／179真正Editor及雙平台receipt保持。本輪沒有Unity／APK／launcher重建，正式5080不動；新.NET輸出在C的新BuildRuns，F來源及既有C copies／Windows／Quest原件不覆寫。

舊`run`等待共用refreshPromise，一旦列表刷新失敗便在action前退出。先用真正隔離API0.30.0／Chromium重現：handle46558 terminal exit1，受控catalog503後第一版已選、草稿仍第二版，未發出所選history GET，30秒DOM等待失敗。這是新受控證據，不是原c71 CI歷史載入逾時的根因證明。

只有載入最新版／選定版本／歷史分頁三個明確GET入口選用independentRead：等正在進行的刷新後，原epoch／actor且非HTTP狀態錯誤或5xx可以繼續重新讀history／version；成功仍警告背景列表未更新。401／403／其他4xx不恢復，登出／epoch變更取消尚未發出的讀取。版本本身503保留舊草稿，不取快取或別版。建立／修訂、場次命令、名冊、pending、原UUID／expectedSequence及認證權限保持。三個原生工具API gate同步0.30.1，沒有修改姿態、武器或錄影政策。

新專項handle兩次均exit0：先10項、擴充15項（含原shell2項／情境13項）；真API22個不可變版本、20＋2分頁，受控503／transport／403／401、選定history503、寫入零發出、登出不恢復及警告皆通過。focused檢查有自己的scope，不能當完整回歸。最多256筆方法／path metadata，截斷不得成功，不記headers／key／payload；新目錄拒絕覆蓋。

本機完整handle51663 terminal exit1：72 Node成功，後在原weather night複合斷言失敗，未到新讀取情境。保留weather-first-rain（tick20／sun0.08／非flash）及原畫面／log，該複合斷言沒有同時保存三個條件，不能證明唯一原因。fixture改為排除child啟動前已有session、只取新來源，並在單次JS觀察中同時確認選中錄影／rain128／nonflash／sun0.08／非原始音軌提示，保存night DTO及descriptor；原斷言與時間／天氣政策不放寬。最終handle98198 terminal exit0：**72 Node／248完整Chromium**成功（原235＋新13），39個畫面／資料檔。API／WorldRelay／Checks均指向同次C建置，不混root舊輸出；未將軟體WebGL當原生GPU。

`.NET restore --locked-mode`／build成功、0警告0錯誤，717規則與47 world streaming（handle24781 exit0）成功；5 artifacts＋27 active＋13 capacity＝45 Python、三個工具py_compile／兩個CJS syntax及diff-check成功。**本機完整HTTP沒有通過**：handle93770及49590在invalid credential子程序10秒退出等待逾時，未放寬期限。各自finally停止自己的Popen，後續同build程序清查沒有殘留。

為辨識啟動現象，自己的weak-key API在5秒觀察仍live、log已有Unhandled InvalidOperationException，原handle明確停止／terminal。曾做兩個未發布候選：捕捉後return＋exitCode仍live，explicitExit單次0.921秒exit1，但完整HTTP handle99746在第二個invalid credential仍10秒逾時，另有temp server.log清理Win32共享拒絕。這不足以證明整體修復，**已撤回兩種auth候選**，候選原C build／Program快照／probe及失敗log保留；不刪除殘件、不改ACL／Windows設定。最終Program的SHA與第一0.30.1候選精確相同，原憑證拒絕實作保持，不能稱Windows startup／本機459 HTTP成功或猜WER／防毒／檔案系統根因。

真正遊戲回歸handle37885 terminal exit0，`unity-admission/20261101-110701-fe372a4b` **8項／355幀**，驗票／撤銷／重連、接受來源與精確seal／cleanup成功；沒有輸入／姿態注入、沒有新trace。這是最終採用的第一API候選及原遊戲binary，同機Simulation／非互動／headsets0，不是實際Reconnect按鈕或25台證據。

`mission-read-runtime-validation.json`在全部自有handle terminal後只讀raw：新C runtime14檔／一次F snapshot一致、新F43檔；前54 C runtime2967／各F snapshot與前observer F264、UI1042／動態1138／operator383／F337／history321、原尾界及獨立房、API原三組各159、當前ZIP／APK／receipt及舊ZIP保持。總55 C runtime2981檔。三個.NET候選各API＋三工具159檔與Checks95檔均另存雜湊，只有第一候選採用；五個新瀏覽器目錄3／2／2／19／39共65檔，前失敗／成功不覆寫。Startup三份關閉raw log及HTTP temp殘留log已逐byte另存F並核對hash；暫存清理曾部分失敗，不宣稱保留完整HTTP temp，原殘件不刪／不解鎖。保存SQLite不開連線，native writer全停才snapshot。

採用建置的明確本機指標為`artifacts/mission-read-api-stage-path.txt`及`mission-read-api-stage-validation.json`（0.30.1／API132＋三工具各9＝159檔），指向第一候選的bin；名稱帶final／release的兩個候選**不採用**，原指標及原件仍保存，不能只憑名稱選部署來源。

[CI41268781091](https://github.com/peca12968/vr-command-center/actions/runs/41268781091)／job124737033873／精確`2c33d1d9adec23da4dfe457711836a4037f942c7` **完整success**：Linux restore／build、717規則／459 HTTP／47 world、工作流程Python／素材及72 Node／248 Chromium通過。2 Windows限定案例在Linux skip，不當原生或179 Editor證據。本機Windows完整HTTP仍失敗，不能用此Linux結果改判。保存39檔artifact13068238061與log，ZIP9677130 bytes、實際下載SHA256 `622a0b211f2c3c7f1243945b4f6fa7ba47ce980e7a3e4dd45328202c1ff567a8`與GitHub digest一致；`mission-read-ci-validation.json`核對前209＋本輪65＝274份瀏覽器證據、新native及三個候選build均保持。最後只有文件證據skip ci，測試來源精確2c33d1d。

完整11項active，原31筆／world371、Windows startup與原CI時序問題、F吞吐及跨機／Quest／VIVE／MR／廠商硬體仍各自待驗；本輪不把受控修正當所有歷史逾時修復。

## 2026-11-01：25端零按鍵視窗觀察與同場心跳對照

從乾淨`7bc82a1`接續，詳見[OBSERVER_TIMING](OBSERVER_TIMING.md)。API/UI0.30、Unity0.36.1／code44／NGO29、e0594513140ff7fb4bc084929691b91c15f7d908e8f59c114aa5ab27daaf11eb、原scene／prefab／rules0.8.0保持；本輪Python／文件，沒有Unity、APK、launcher或產品.NET重建，也沒有重跑原179 Editor。正式5080與原雙平台receipt保持。

新增`--observer-sequence`：自己的25個原生client＋server、0位操作／25接收、一個可見；不用W／Space／R或管理環境／AI命令，`--operator-ui`僅閒置控制台零表單。固定A3／S3／A3／S3共12次呼叫，原PID／player／session／同視窗及外部caller UTC＋單調時間，8秒baseline／120秒窗口／8秒quiet有界；metadata64KiB不保存image／可及性內容／憑證。先觀察再獨立ack、失敗abort，選窗在量測外。自己的normal-priority心跳沿用原240秒上限，server＋visible稀疏／server loop、replication原上限及0.5／1.5秒政策保持；timer加入tracked children，明確finish及所有writer全停才一次snapshot，例外也收native程序。

真正場`20261101-102507-8f94afad`／原handle8001 **terminal exit0**：8項／52快照／26 Requested完整報告、28237 Running列無失效，1153完整回放／2參考，25份原admission結果／CSV與精確雙seal及server25唯一ACK成功。world1153／combat0／ledger through31，25位健康100、零彈藥／命中／擊殺／損傷；閒置UI110.018秒零requests／attempts，native／UI／pose／timer cleanup皆乾淨，headsets0／hosts1／networkCapacityAccepted=false。

唯讀`observer-analysis-20261101-102507.json`對12次caller窗口都具有native／獨立timer coverage；原visible connection25／source1的PoseSend、PoseReceive／Accepted與MainThreadGap、timer>100ms記錄皆無重疊。timer88.7660042秒、最大wake10.7578ms、clock step0.0004636秒；caller最大0.0009828秒。Accessibility33.2628–78.5295ms／Screenshot96.5465–161.07ms是**含SDK queue、helper及結果返回的外部括號，非GPU／CPU／FPS／RTT**。Screenshot可能delta region、不當全frame像素量測；小樣本固定順序、零記錄大gap不證因果、不排除觀察擾動／小間隔，也不能配前場world371或舊31筆。

分析器校驗原visible／connection、closed cleanup及報告來源，UTC差>=0.05秒／不同主機／不足coverage返回null；同point裁切聯集、不同point與MainThreadGap／PlayerLoop不相加，CPU保留整個原Update sample括號、不比例切分或歸因。沒有world序號不能硬配。只讀關閉JSON，不開保存SQLite，輸出新檔且不得落原場／原runtime、不覆蓋raw；complete僅join資料完整、missionAcceptancePassed另列、rootCauseProven=false。

live之後補上stationary sample及全回放閘門：名冊、head／muzzle／forward／彈藥／reload／fireSequence不變，短暫移動恢復也失敗，connected／rig另由原參戰規則處理。**原8項沒有冒充新增live第9項**。`observer-closed-stationary-validation.json`第一版把REST float短格式與raw double展開直接比較，983幀誤報，例(-31,1.65,-3)與raw y=1.649999976158142；原失敗檔保留。`...-v2.json`以同一raw序號122作baseline、rb／checksum／連續序號讀完122–1104共983幀全相同，並另核對原journal1153精確seal，沒有改遊戲容差／原runtime或宣稱另一次live。

本機9 observer sequence＋6 analysis＋27 active＋7 heartbeat＋16 input analysis＝**65 Python通過**，含順序／錯場／錯window／clock step／host未知、缺coverage為null、交錯玩家／source不混流、同point union、完整CPU sample不縮放、暫時移動恢復仍失敗及timer報告IO失敗仍cleanup。py_compile／diff-check通過，CI新增兩個suite及新腳本compile。

首CI`41266207153`／job124729421211／精確c71a71d在mission-browser原第60行逾時，沒有完整通過；717規則／459 HTTP／47 world、Python／素材及72 Node成功，但歷史第一版已選取、草稿仍第四版、notice為更新失敗。保存4檔artifact13067331462（ZIP823374 bytes／SHA aab97eb4e5e61e2848138fcde58c7667a57a674687891faba7c3827dea2599d2）與log，前131份CI／本機證據保持；沒有當時request明細，不能證明路由／產品／主機根因。之後本機handle21473 terminal exit1：72 Node成功，原隔離API啟動期限內未就緒且log空，未開始browser checks；新目錄空白保存，原因未知，不當瀏覽器通過。

`8e335d6`僅補fixture失敗診斷：最多128筆GET path／status／完成／時間／failure，不存headers／憑證／body／response payload；啟動失敗保存原attempt／elapsed／exit／signal及既有有界log並遮罩臨時key，terminal包含signalCode。可明確選新的直屬artifacts/console-*目錄，拒絕既有以保留原console資料。本輪未改console產品JS／API、路由情境、斷言或8秒API／30秒DOM／啟動界線，這不是歷史任務載入問題的修復宣稱；兩個CJS syntax及diff-check通過。API8秒計時是瀏覽器GET／管理呼叫，不是原生15秒來源入場政策。

同`8e335d61e428dc37b6627918637bcc187142750d`本機handle46147 **terminal exit0、235 Chromium全部通過**，包含原歷史版本載入情境；37份原畫面／checks另存`console-observer-diagnostic-20261101`，先前空白啟動失敗目錄不動。前一handle21473的72 Node通過另計，不把未進browser的場稱完整成功。

[最終CI41266688006](https://github.com/peca12968/vr-command-center/actions/runs/41266688006)／job124730838741／精確8e335d6 **完整success**：Linux restore／build、717規則／459 HTTP／47 world-stream、工作流程Python（含9 observer／6 analysis）／素材、72 Node／235 Chromium均通過。2 Windows限定案例在Linux skip，不當原生Windows／179 Editor證據。保存37檔artifact13068160426、9464113 bytes ZIP，實際下載SHA256 `c0eb7fe41cf25e7fbe41ad386fed18c967ff734c67d175bd36c08bb8c39bb25c`與GitHub digest一致；另存log與`observer-ci-success-validation.json`，前CI／本機131＋本輪失敗4＋新本機37＝172檔保持。**這是增加診斷後的成功場，不是修復或證明原c71a71d歷史載入逾時／21473啟動失敗根因**；原生姿態反例也不因此變更。最後只有文件證據skip ci，測試來源精確8e335d6。

`observer-runtime-validation.json`：新C runtime176檔與一次F snapshot逐檔SHA一致、新F264檔；前53 C runtime2791檔／各F snapshot及前UI1042／operator383／動態1138／F337、原尾界失敗／獨立房／history321、API三組各159及當前ZIP／APK／receipt與舊ZIP保持。總54 C runtime2967檔；全部原handle terminal才稽核，保存SQLite只raw bytes不開連線。新分析與兩版stationary輸出在原場之外，原成功與失敗檔均不重寫。

完整11項active；下一步仍追查自然姿態空窗並接續多人持續操作。此輪沒有重現不等於修復舊31筆或前場371，沒有完成25人同時操作、跨機／Wi-Fi／Quest／VIVE／MR或廠商硬體驗收。

## 2026-11-01：控制台表單接入25端動態任務，保留新參戰反例

上一輪為實際進展，從乾淨`00d91a5`接續[動態PC](DESKTOP_ACTIVE.md)。**API/UI0.30、Unity0.36.1／code44／NGO29、e0594513140ff7fb4bc084929691b91c15f7d908e8f59c114aa5ab27daaf11eb、原scene／prefab／rules0.8.0保持**；本輪Python／Node驗收與文件，沒有新Unity／APK／launcher或產品.NET建置、沒有重跑原179 Editor；沿用原同源雙平台receipt，正式5080不動。

新增`--operator-ui`，將原三組環境／AI命令改成真正Chromium控制台表單的reload／fill／submit，使用自己隔離API／臨時Master，選定原五房Linked場，保存真正HTTP POST body、status與CommandReceipt；只有GET用於額外讀回，不以直接管理POST代替這六個動作。Python仍核對原request／session、先環境再AI、精確設定／expectedSequence／原UUID／非duplicate／接受尾界及來源Running／observed fence。409最多三個明確意圖、拒絕後才能refresh新提交；200即止、未知結果／5xx不重做。Begin／Pause／Resume／End仍由fixture處理，**不是本輪全生命週期的UI驗收或autoAttack傷害測試**。

助手僅本庫新desktop-active目錄、Simulation／headsets0、canonical127.0.0.1 HTTP非5080，server header必須原session的五房Simulation；不接受任意正式／遠端API或拿頭盔分類當在線。單調180秒／最多3組／每表單3意圖有界，finish輪詢先關browser並等helper terminal；report.complete只助手範圍。Python即使UI shutdown／報告IO例外仍須獨立native cleanup。原40秒UI確認、replication240秒／4096列與0.5秒姿態／1.5秒來源政策保持，沒有改Tracked、槍口、wire或戰鬥規則。

| 真正場／原handle | 結果與範圍 |
|---|---|
| `desktop-active/20261101-093809-9f82680e`，47587 exit1 | 六UI命令、182快照／26完整report、25份精確結果／CSV／雙seal與server ack成功；前13項成功，但最後全程連續性失敗。1271完整回放／11參考中，world371／tick566只有可見玩家參戰失效；26份report各觀察到同tick connected24／health2500／ready及coherent=true。26010 Running觀察列、26 bad列；原active-result.complete／continuityPassed=false、無summary接受檔。沒有當場姿態trace，原因未知 |
| `20261101-094604-d61ce911`，63574 exit1 | 新API health啟動30秒逾時，api.log空；尚未建立遊戲／UI／診斷程序。沒有調寬門檻／重用該場，cleanup空，原因未知 |
| `20261101-094719-ababcf4b`，93035 exit1 | 第一發done在同一orchestration呼叫中先於模型檢視新畫面寫入，不合確認順序；另存operator-observation-issue.json acceptancePassed=false。之後未送R，actual UI reload40秒逾時，沒有補ack／結果接受檔。兩份稀疏報告仍明確finish，UI／native cleanup乾淨；不可當完整操作成功 |
| `20261101-095005-60959386`，26798 exit0 | 正確分開觀察與ack，**14項／182快照／26 Requested完整report、21121 Running列無失效**，1132連續回放／11參考與25份精確結果／CSV／雙seal／server25唯一ack成功；UI與兩份稀疏診斷明確finish、cleanup無殘留。只代表本場 |

第一失效場的closed worldlog已逐record checksum／序號核對；367–370與372–375可見玩家connected=true／rig Simulated，只有371 connected=false／rig None，健康100保持、名冊25。370→371保存capture相隔112ms，371→372為293ms；這不是失效持續時間／RTT或pose收發間隔。當時保存狀態仍Clear／Hold、observed28／非suspended，尚未在該幀觀察到第一組UI接受31／32套用；**不能從此推定接受時間、Begin序號或UI／天氣／GPU／傳輸根因**。每client仍一個原native連線，參戰body狀態不當新的transport重連。恢復、最終戰績或最後乾淨場均不能抹除這一幀；原31筆失效也未修復。

原候選工具與依賴共10檔（含working.patch、無憑證）先精確封存於`active-ui-candidate-a5f5b675638b4ea984d3fcc1fb3311cd`並hash；之後補嚴格UI意圖順序／單調期限／時間metadata、助手cleanup例外仍必須native cleanup的反例，以及明確`--diagnose-visible-pose`。這份10檔不是完整OS／binary依賴graph。新診斷只有server＋visible client，server才PlayerLoop，不擴大舊收集器界線或當零擾動。

程序不合格場的兩份稀疏報告complete／clockJoinValid，client最大PoseSend gap0.5342256秒、server的pose streams最大gap0.5370066秒；關閉journal在初次capture後未找到可見玩家的保存Running connected／rig失效。`active-ui-pose-window-analysis.json`因此沒有可配對的fault窗口，missionAcceptancePassed仍false。**不把最大gap當另一個已保存失效、不能跨場套到原371、不能以本次時鐘檢查校準原無trace場次**。point沒有world序號，不硬配，clock／coverage不足須null。

最終場三組接受31／32、44／45、48／49，Running來源分別world374 observed32 tick466、world1013 observed45 tick1528、world1077 observed49 tick1562。Patrol與Advance只要求命令前基準至少20活動tick後的實際活敵移動；原五敵ID／room／health保持，四個活敵各約0.2m／1.7m，原room3死敵不復活。不是固定速度或精確套用延遲。每檢查點仍逐一比對25端＋server的環境／AI來源、身分、姿態、彈藥／健康與敵軍position／fireSequence；不將其當所有render frame或所有封包。

最終一位實際W／Space／R／Space、24接收端，2發2中1殺／100%，其餘24未受其輸入改動，所有玩家健康100。world1132／combat5／ledger through52的25份原admission結果精確一致；全部server ack對原nativeConnectionId，無timeout／queue error。replication最晚117.630233秒／最多857列，最大相鄰觀察Running tick gap0.1340429秒，非RTT／FPS。client probe End前停、server seal後停，UI助手3組／6次200／無page error、105.863859秒 Requested clean shutdown，才另行核對個別結果。

最終稀疏server／visible client各於118.354362／109.312755秒明確stop，clockJoinValid、最大檢查偏差0.0019386／0.00165秒，未截斷。client gaps0但threadWindows1；不能由稀疏列空集合宣稱全程無主執行緒空窗。報告在25份結果與精確seal後停止，diag complete不是任務接受。Windows雨夜／換彈／擊殺／暫停畫面已觀察；沒有新GPU／PCM量測或頭盔證據，CUA截圖payload未另解碼／保存。

**27 active＋13 capacity＋12 debrief，共52本機Python與72 Node通過**；新增6 Python／5 Node涵蓋外場／錯request、錯表單／尾界／UUID、未知結果、成功後多送／錯意圖序號、單獨server／visible的診斷opt-in及UI cleanup錯誤仍收原生程序。一般235瀏覽器套件本輪由後續CI驗證，不混用前輪本機結果；語法與diff成功，CI既有入口已包括新案例。

原生場後僅補UI cleanup例外／中斷仍在finally執行native cleanup，以及同session world header的顯式核對；27 active／5新Node反例重新成功，保存summary的原world header與UI config session讀回精確相同，沒有改遊戲或重跑整場假裝新的原生證據。[功能4102850](https://github.com/peca12968/vr-command-center/commit/4102850e9c35959cfcd36872f7e1d80f3753333f)的[CI41263637499](https://github.com/peca12968/vr-command-center/actions/runs/41263637499)／job124721781630**真正完整success**：Linux restore／build、717規則／459 HTTP／47 world-stream、工作流程Python／語法／素材及72 Node／235 Chromium通過。兩個Windows限定案例按平台skip，不能當雲端原生或重跑179 Editor的證據。這不改首場原生exit1／新371失效與原31筆狀態。

37檔artifact13066661666、9464550 bytes，ZIP SHA256 `d3748ab2048df8eda10d1b6ee5fc0f07be26e2545e5ab893fe58da7fe5e99690`，下載與log原handle5737 exit0，保存新`ci-41263637499-*`；`active-ui-ci-validation.json`核對成功37檔、前CI37／本機console42／兩失敗CI13＋2共94檔仍相同，log另存SHA。完整CI不是Windows／25人容量驗收；後續僅文件證據提交使用skip ci，測試來源精確為4102850。

`active-ui-closed-analysis.json`／`active-ui-runtime-validation.json`在四個原handle terminal後只讀關閉JSON／journal rb與checksum，保存SQLite不開連線、不ack／修復／截尾；metadata讀回不是完整raw規則重跑。新4 C runtime764檔／F snapshot相符，前49 runtime2027、前F337／四動態1138／前operator383／原尾界及獨立房證據、history321與各API159、當前ZIP／APK／receipt及舊0.36 ZIP保持；總53 C runtime2791檔，新場F1042檔另存hash。所有writer全停才一次snapshot、C原件不動，失敗也保存。

完整11項active。仍同機Simulation／一位操作24接收／headsets0／networkCapacityAccepted=false，不是25位同時操作、跨機／Wi-Fi或頭盔容量；診斷前後條件不同，不當因果對照。下一步以原失效樣本及獨立觀察／可見玩家診斷追查自然姿態空窗，並接續多人操作；原31筆／新371、F吞吐、MR／VIVE／跨機25台及廠商硬體各自待驗。

## 2026-11-01：25端動態任務中的環境與AI管理命令

上一輪為實際進展，從乾淨`cf3c8b4`接續；新增[動態PC選用流程](DESKTOP_ACTIVE.md)。**API/UI0.30、Unity0.36.1／code44／NGO29、e0594513140ff7fb4bc084929691b91c15f7d908e8f59c114aa5ab27daaf11eb與原scene／prefab ID、rules0.8.0保持**，只有Python驗收及文件修改，沒有新Unity／APK／launcher、179 Editor或本機.NET建置。既有雙平台receipt保持；正式5080不動。

舊動態工具只驗Clear／Day／Hold，本輪新增明確`--operator-controls`，在實際W後、Space／R／Space前切Storm／Night／lightning／Hold，擊殺後切Storm／Patrol及Fog／Day／Advance；全程autoAttack=false以保留原動作隔離與健康基線。管理命令走正常API，玩家鍵盤走computer-use，沒有REST／RPC／UDP注入姿態、命中、座標或統計；**這輪沒有重跑操作員瀏覽器UI或自動攻擊傷害**，相關舊證據仍分開。

原生場`desktop-active/20261101-085537-4eed0a0f`，**原handle33469真正exit0、13項成功、cleanup errors／remaining皆空**。一個server＋25個Windows native client，仍一位實際操作、24個無圖形接收端；source／binary在F，runtime明確C SSD、headsets0／hosts1／all25SimultaneouslyActive及networkCapacityAccepted=false。

| 管理命令組 | 保存接受序號 | 第一個符合條件的來源幀／observed／tick | 真正策略移動 |
|---|---|---|---|
| Storm／Night／lightning／Hold，射擊前 | 31、32 | world391／32／483 | 不要求移動，保留原射線目標 |
| Storm／Night／lightning／Patrol，擊殺後 | 44、45 | world1249／45／2043 | 原四個活敵各移動約1.300001m |
| Fog／Day／無閃電／Advance | 48、49 | world1305／49／2075 | 原四個活敵各移動約0.699999m |

兩份CommandReceipt先保存後輪詢，拒絕外場／duplicate／非遞增；來源必須非suspended、Running、tick前進、observed>=接受序號，且天氣／日夜／閃電／visibility／behavior／autoAttack相符。Patrol／Advance另外從命令前來源基準前進至少20 tick，原五敵ID／room／health完全保持，包括原room3死亡目標不復活；只算仍活敵的移動，不由死敵、重生或目前名冊猜測套用。`active-operator-controls.json`保存原回應及來源witness，逾時保留applied:null；這是輪詢首次符合條件的觀察，不是精確命令套用時間／RTT。

七個檢查點（initial／四動作／Patrol／Advance）共**182快照／26 Requested完整報告、28204觀察Running列**無失效。每個快照核對來源packet實際環境與25原連線／全名冊／姿態／彈藥／健康、敵軍位置與fireSequence。最晚145.318062秒finish、最多1134列，原240秒／4096列界線保持。相鄰觀察Running新tick最大間隔0.5542095秒，非RTT／FPS／精確PoseSend間隔；原0.5秒姿態與1.5秒世界政策未改，不能由此數值推根因或宣稱連續畫面。

原handle terminal且cleanup明確空列後，`active-operator-checkpoint-validation.json`另外只讀原JSON／快照，將七段直接對到命令指定環境與原接受fence：initial world120／move342為Clear Day；shot683／reload928／kill1194仍Storm Night Hold且observed35／37／42>=32；Patrol world1254 observed46>=45、Advance1310 observed50>=49。各段26個原client／server快照全部相符，其他身分／姿態／戰鬥閘門仍執行。最初Begin無保存接受回應，這份讀回的initial／move minimumAcceptedFence=null，不猜序號；complete只表示這次182快照讀回，不當新原生run、全量世界規則重算或連續渲染。

實際W短移動、雨夜第一發命中／R後30彈匣89備彈／第二發擊殺成功；主玩家2發2中1殺／100%，中彈與損耗0、健康100；其餘24位未受其輸入改動。25份原admission個別結果／CSV與combat及world精確雙seal一致，**world1359／combat5／ledger through52**，server25唯一ack集合精確對到原nativeConnectionId、沒有timeout／queue error。原probe先finish／server seal後finish、結果確認後才停程序的順序保持。

End後完整API回放**1359連續幀／12參考**精確一致，參考區間每張保存Running世界幀與所有觀察Running列均無參戰失效；這是保存及觀察到的樣本，非25位同時操作或任意負載證明。源環境與接收端為離散檢查點，不把管理接受當連續渲染證明。computer-use兩次get_window_state回報active request：第一次等待後重新取得雨夜畫面才射擊；後一次重試回報foreground未有PID、當時進入結果／收尾階段，沒有再輸入或推定原因，**沒有霧天人工GPU畫面證據**。未保存／解碼CUA截圖payload。

新增4 active＋2 capacity反例，含舊observed／Paused／suspended／未前進tick、正確fence但錯天氣／visibility／策略／autoAttack、死敵或靜止不能當移動、換敵／重生／換房／非有限移動、明確環境不放寬舊預設與未知枚舉／非bool拒絕。**21 active＋13 capacity＋12 debrief，共46本機Python通過**，語法及diff成功；既有CI入口涵蓋新案例。

功能[b014f1a](https://github.com/peca12968/vr-command-center/commit/b014f1a9378a65d4a176fd04d6105fdfeeee6f6b)的[CI41259359885](https://github.com/peca12968/vr-command-center/actions/runs/41259359885)／job124709212647真正執行.NET／717／459／47、Python／素材與67 Node，但最後瀏覽器在`world-browser.cjs:84`等待新登入分頁的camera-positions option 30秒逾時，exit1；這次在舊截圖步驟前失敗，不能稱前輪bringToFront已證明根因修復或整套通過。Chromium安裝步驟01:03:47–01:09:31Z仍正常完成，沒有因等待而重啟工作。原log與artifact13065165755（3517165 bytes、ZIP SHA256 `d40f412408a19ce8cf4693039fd6d7447adbbda3c5d67814fca4966761f7ef54`）下載新`ci-41259359885-console`保留。

瀏覽器fixture進一步在主觀戰及新登入分頁開始載入前明確bringToFront；行動房控分頁在原所有斷言／截圖完成後關閉其context，不讓已測完的viewer繼續占用renderer。沒有改正式UI／API、提高30秒等待或跳過原斷言；camera及clock仍用各自60秒來源。若新登入鏡頭載入再失敗，另外保存該分頁visibility／world及camera message／option count／world sequence與最多5秒失敗截圖，再重拋原錯誤；不記憑證／headers。這是fixture目標與生命週期修正，尚不當作已證明Chromium／CPU／網路根因。

該修正[e12a52a](https://github.com/peca12968/vr-command-center/commit/e12a52a4644ab3809a7ac4217344104e1a861865)本機原handle67605真正exit0，**67 Node／235 Chromium成功**、相機還原畫面已檢視。`operator-browser-evidence-validation.json`核對原console42檔先完整封存、現console42檔及b014失敗CI13檔／log另存hash，前原生runtime／證據不動。但[CI41260301809](https://github.com/peca12968/vr-command-center/actions/runs/41260301809)／job124712001366又真正exit1：.NET717／459／47、Python／素材與67 Node過，瀏覽器更早在`mission-browser.cjs:54`歷史版本草稿名稱等待30秒逾時，尚未到世界觀戰，不能稱相機修正已在這輪雲端驗過。原artifact13064888401為2 PNG、592388 bytes，ZIP SHA256 `e5debca0aff2da793649995aa8572e8cf509814d0de2ec6c4c8748bc062fd750`，與log保存在新`ci-41260301809-*`。

任務fixture原跨主頁／editor後未明確切回，DOM狀態又以`waitForFunction`預設動畫幀輪詢。[Playwright官方文件](https://playwright.dev/docs/api/class-page#page-wait-for-function)說明預設raf與明確毫秒輪詢的差異；新版本僅將該任務DOM等待統一為polling100，啟用editor及結束後主頁，原30秒逾時與所有版本／保存／衝突斷言保持。失敗時在關editor之前另存visibility／草稿名稱／版本選擇／history／notice及最多5秒截圖，仍重拋。這消除測試對動畫幀排程的不必要依賴，但舊CI沒有editor狀態，**尚未證明逾時時DOM已正確、背景RAF停住或產品無缺陷**；不能以推測宣稱根因／修復。修正的本機完整與雲端結果另記。

最終[a1556bf](https://github.com/peca12968/vr-command-center/commit/a1556bfc2b0575ead0810a4c71d7f1ef6841e25f)本機原handle98816真正exit0，**67 Node／235 Chromium再次完整成功**，不是只重跑任務小段。`mission-browser-evidence-validation.json`核對前42 console檔已完整封存（與前manifest逐檔相同）、目前42檔及e12失敗CI的2 PNG／log另存hash，原b014失敗CI13檔保持。以上Node互通檢查有自己的C# fixture，不是新產品API／三工具或Unity建置；既有同版產品DLL與receipt保持。

最終同[a1556bf來源CI41260889785](https://github.com/peca12968/vr-command-center/actions/runs/41260889785)／job124713745724**完整success**。Linux restore／build、717規則／459 HTTP／47 world-stream、工作流程Python／語法／素材及67 Node／235 Chromium成功；process timing與desktop artifacts各一個Windows限定案例按平台skip，不能當雲端真正Windows探針證據，本輪原生證據仍為本機33469。37檔artifact13064982961、9460116 bytes，ZIP SHA256 `19d0573e4bd5afbc6cd635b684c7ba4026915941293643e63fc3a549b30ee5be`；下載／log原handle79468 exit0，保存新`ci-41260889785-*`。`operator-ci-success-validation.json`核對成功37檔、前本機42＋兩失敗CI13／2共57檔完整，完整log另存SHA。這證明本輪修正來源的整套回歸成功，不證明舊逾時的唯一根因；兩次失敗與既有8d成功歷史都保持。後續僅文件證據提交使用skip ci，不把文件SHA當新測試來源。

`active-operator-runtime-validation.json`在原33469 terminal後核對新C runtime300檔／F snapshot完全一致，前48 runtime1727檔／前F337、前四動態F1138、原尾界反例與獨立房F證據、history321及各API159保持。總49 C runtime2027檔，新場F383檔另存hash；當前ZIP／APK／receipt metadata保持。所有writer全停才一次snapshot，C原件不動，保存SQLite只rb雜湊、不開連線／ack修復／截尾。完整11項active，原31筆／F發布吞吐、頭盔／MR／VIVE／跨機25台與廠商硬體仍各自待驗。

## 2026-11-01：同版動態PC與25份最終結果／server ack

上一輪為實際進展；從乾淨 `8938968` 接續[動態PC流程](DESKTOP_ACTIVE.md)。**API/UI0.30、Unity0.36.1／code44／NGO29與e0594513140ff7fb4bc084929691b91c15f7d908e8f59c114aa5ab27daaf11eb保持**。原生階段只有Python驗收／文件修改，沒有重建或重跑原179 Editor／雙平台／APK／launcher；後續雲端.NET及瀏覽器測試修正結果見下文。原scene／prefab／rules0.8.0／Tracked與0.5／1.5秒政策保持，正式5080不動。

以computer-use技能只操作自己本輪唯一可見的Windows遊戲視窗，逐階段實際W／Space／R／Space，畫面確認後才寫該階段done檔；沒有REST／RPC／UDP注入姿態或命中。所有場為25個原native client、1個server，**一位操作、24接收、同機Simulation**；all25SimultaneouslyActive／networkCapacityAccepted=false、headsets0，不能稱25位同時操作或頭盔／跨機／Wi-Fi驗收。GPU畫面只為Windows視窗觀察，沒有新原生GPU／PCM探針、FPS／聲音或XR追蹤證據。

| 真正PC場／原handle | 原結果與範圍 |
|---|---|
| `desktop-active/20261101-075730-56b9ca85`，43305 exit1 | 40秒actual UI move確認逾時；首次畫面不符後重新啟用並確認自己的遊戲視窗，W已送出，但確認時stage已failed，guard拒絕補寫move.done。沒有done、active-result／summary／全程continuity接受檔；26 initial snapshot與raw退出資料保持。cleanup空，不能稱引擎或姿態故障根因 |
| `20261101-075928-d971525e`，8014 exit0 | 修改前9項、130快照／26報告、26599 Running列及1223連續回放／6參考全過。raw有25份final，但工具當時未提供停止前的個別結果／server ack閘門，不補造新接受欄位 |
| `20261101-080727-7ba918cd`，56068 exit0 | 中間10項含25份精確個別結果與client phase，130快照／26報告、24252 Running列、1115全回放／6參考成功；server25 ack另離線相符，該版檔未記錄serverAcknowledgedConnections新閘門，原件保持 |
| `20261101-081224-46713819`，40247 exit0 | 最終來源10項，130快照／26完整報告、**33256觀察Running列**無失效，1420連續全回放／7參考及參考間所有保存Running幀無失效；25份精確結果與實際server ack通過，cleanup無殘留 |

最後三場各自明確finish、精確combat／world雙seal及25人CSV均成功，原生日誌無send queue full。最終26份probe皆reason=Requested、complete=true／truncated=false，各自收集起算最晚151.630929秒停止、最多1320列，沒有延長原240秒／4096列上限；client probe先停、server seal後停，之後才核對玩家結果。相鄰觀察Running新tick最大間隔0.383255秒，非RTT／FPS或每packet保證；不同報告樣本不當同一時刻。

最終實際短W移動0.05公尺，第一發敵軍100→50、彈匣30→29，R顯示RELOADING後30／89，再Space擊倒目標為29／89。權威與所有端列出的狀態欄位一致，其他24位位置／彈藥／統計未被這位玩家輸入改動。最終主玩家耗彈2、命中2、擊殺1、命中率100%、中彈／損耗0、健康100；25人CSV與個別結果逐一等於各自sealed ledger，不能把主玩家數值套給其他人。

原動態工具在seal後會直接stop_round，只核對操作、接收／回放與最終CSV；本輪先保持原9項baseline，再新增停止前等待結果。`validate_final_results`要求25個原native owner／admission／room、非空且精確相同的ack名單、25份無重複final、world stream／sequence／ledger through及實際API combat acceptedSequence。client每份只有一個原連線；server log另須25筆無重複VR_SERVER_DEBRIEF_ACK，ID集合精確等於原nativeConnectionId、沒有DEBRIEF_TIMEOUT。這區分final＋disconnect的client phase與真正server ack，沒有改遊戲30秒等待或斷線政策。

新`active-player-results.json`保存delivery／個別結果／實際serverAcknowledgedConnections，active-result增加individualResults／acknowledgedResults。最終25份皆worldSequence1420／combat5／through42，server確認也全部對到原25條連線；完成驗收後才停原程序。舊缺欄位是NotRecorded，原9項／中間版範圍不改寫，不能由空集合當全部送達。

新增9個反例含空／closed／未知delivery、缺失／重複結果、舊admission、前一幀世界尾界、錯combat tail／room／health及client已收但server ack缺失／重複／外連線／timeout。**17 active＋11 capacity＋12 debrief＋17 independent evidence，共57本機Python通過**，語法／diff成功；CI既有active入口自動包含新案例。這些原生檢查不當新跑179 Editor。

功能[b906236](https://github.com/peca12968/vr-command-center/commit/b906236e874e1112ce3e0c4349933b534f39c16a)的[CI 41256605682](https://github.com/peca12968/vr-command-center/actions/runs/41256605682)這次真正啟動，雲端.NET建置及717規則／459 HTTP／47 world-stream、Python與素材檢查成功，67 Node通過；最後瀏覽器在`world-browser.cjs:86`的第二分頁完整截圖30秒逾時而exit1，不能沿用前輪帳務阻擋的說法或稱整套瀏覽器成功。原job log一檔及artifact13063671486的13檔保存在`artifacts/ci-41256605682-*`，失敗畫面亦顯示原60秒camera來源已結束；這不證明Chromium底層根因。

測試現在先以[Playwright官方bringToFront](https://playwright.dev/docs/api/class-page#page-bring-to-front)明確啟用要截圖的分頁，關閉後啟用原頁。相機儲存／延遲回應流程結束時，停止並正常End自己原場，再為擷取時鐘與中斷測試建立另一個原有60秒上限relay；先核對新場Running且程序仍活著，避免慢CI拿已Ended的相機來源冒充即時資料。沒有提高截圖30秒或relay上限、跳過斷言、改正式UI／API／遊戲新鮮度政策。原第三個完整封存回放流程保持。

最終修正本機原handle30549真正exit0，**67 Node／235 Chromium**（新增一項獨立live來源前提）成功；Chromium151.0.7922.34／Playwright1.62.1，實際相機位置截圖已人工檢視。原console42檔先完整保存到`console-before-ci-focus-549e61a44ca645c785f23a43a576c519`並附hash，未覆寫原失敗或原生runtime證據。`browser-focus-evidence-validation.json`重新核對原42檔完整、現本機console42檔及原CI artifact13檔／job log另存SHA；後續修正CI另記，不把本機結果當雲端通過。

修正[8d2227a](https://github.com/peca12968/vr-command-center/commit/8d2227aa02b3eb384a9926ad498cf9ae7bb3b5ad)的[CI 41258070247](https://github.com/peca12968/vr-command-center/actions/runs/41258070247)／job124705387031**真正完成success**，本機watch原handle73920也exit0。Linux .NET restore／build、**717規則／459 HTTP／47 world-stream**、工作流程全部Python／語法／素材檢查及**67 Node／235真正Chromium**成功，沒有跳過原斷言。artifact13063049447（9453864 bytes、ZIP SHA256 `da8b3ebe38337f86227230e5572167018ebf3b49efa9de3a4d7e76625a8340b6`）下載到新`ci-41258070247-console`，37檔及job log另存SHA；成功相機位置畫面已人工檢視，即使camera來源自然結束，時鐘／中斷流程仍使用自己的新live來源。

`browser-focus-ci-success-validation.json`核對成功37檔、235通過metadata及前55份本機／失敗CI檔完整。兩次CI均保存，這是瀏覽器fixture修正與管理API回歸，不當Chromium底層根因證明、新Unity／XR／原生渲染或跨機容量驗收。後續僅文件證據提交使用`[skip ci]`，上述成功來源精確為8d2227a，沒有為文件重跑整套測試。

`active-e059-runtime-validation.json`核對本輪4 C runtime共836檔／F snapshot逐檔一致，前44 runtime891檔、前F337／原尾界反例F76／獨立房F112／0.36 history321與三組API各159保持；總48 C runtime1727檔，新四場F證據1138檔另存hash，失敗也保存。既有0.36／0.36.1 Windows包、APK與receipt metadata保持，來源／binary仍F、runtime明確C SSD。所有writer全停才一次snapshot保留原件，保存SQLite不開連線、沒有修復／ack補送或截尾。

這是同版實際輸入／接收／個別戰績的進展，不證明舊31筆或F發布吞吐已修復，也不把視窗觀察工具的影響當已排除。完整11項active；下一步推進操作員即時控制與動態玩家組合，原31筆、慢碟、實機／MR／VIVE／跨機25台及廠商硬體各自另驗。

## 2026-11-01：0.36.1五獨立房長任務與閉源證據讀回

功能 [4898c98](https://github.com/peca12968/vr-command-center/commit/4898c988e0cd1a5203d4b30ca7552c0bb5c8dd33) 已推送main、遠端SHA一致。[本功能CI run41254427165](https://github.com/peca12968/vr-command-center/actions/runs/41254427165)／check124694467148為failure、steps空；fresh annotation明確為付款失敗或支出上限，job未啟動，沒有雲端測試結果。未改帳務或手動重跑；下列為本機實際驗證。

上一輪為實際進展；從乾淨 `6fa0d7b` 接續五房獨立驗收。**API/UI0.30、Unity0.36.1／code44／NGO29及e0594513140ff7fb4bc084929691b91c15f7d908e8f59c114aa5ab27daaf11eb來源保持**；本輪只有Python／文件／CI，沒有改遊戲或重建／重跑179 Editor與雙平台，沿用原成功receipt與scene／prefab ID。沒有新.NET、一般瀏覽器、GPU或頭盔結果。

真正場 `desktop-long/20261101-073002-fab40f9a`，**原handle7849真正exit0，executionFinished／acceptancePassed／complete=true**。五個Windows server＋25個headless client，每房5位原admission、各自900秒活動倒數與唯一tick18000自動End。明確C SSD新runtime，來源與遊戲binary仍F；新API／159檔同版執行副本啟動前核對成功，原5080及正式資料不動。各房不同session／world stream／UDP port，Clear日／Fog日／Rain夜／Storm夜／Clear夜、各自barrel／sandbag與旋轉角度；Room控制台對其他房Begin與live watch均403，真正AI初始造成損耗後關閉自動攻擊，沒有玩家輸入／姿態／戰績注入或診斷probe。

Room1 Pause接受13、Resume14，凍結tick2410；在3.094秒觀察窗口內，Room2 2388→2449、Room3 2378→2439、Room4 2355→2418、Room5 2333→2395，皆持續Running。全回放35個Paused幀均在該接受fence且tick相同，原名冊／姿態／健康有效；不計Running人次，其他房的非預期暫停仍算失敗。

五房25份原playerId／admission／room／seat跨票券到期保持、各只一個原連線；每房5份final都對到自己精確world／combat封存，全部ack，CSV七統計／ledger through／stream tail一致。隨後五個4倍回放各自從第1幀到封存尾端，**42,341全幀／41,884 Running／209,420人次**全部核對，最終packet／統計一致：

| 房間 | 全回放幀／世界尾端 | Running幀 | 應核對人次 | 最大保存capture gap ms | 最大觀察時來源年齡秒 |
|---|---:|---:|---:|---:|---:|
| 1 | 8455 | 8352 | 41760 | 112 | 0.350129 |
| 2 | 8500 | 8422 | 42110 | 125 | 0.347735 |
| 3 | 8468 | 8386 | 41930 | 131 | 0.219043 |
| 4 | 8459 | 8367 | 41835 | 125 | 0.301952 |
| 5 | 8459 | 8357 | 41785 | 130 | 0.322635 |

每房live／replay均無body／Paused／環境失效、來源過期或send queue full；live分別跳6／3／3／2／9序號，由全回放補核，不稱丟包／RTT／render FPS。cleanup無錯誤／無殘留，原native script graph為 `40cb2d72a29d7e4bc2df222ca43e83871dbadd22b7dfc7ea6b70277012c0a2f5`，不是完整OS／binary依賴graph。主機其他負載未量測，不能當無負載或隨機因果對照；仍是同機靜止Simulation，headsets0／hosts1／networkCapacityAccepted=false，不是25位同時操作或跨機／Wi-Fi／頭盔驗收。

新增 `scripts/verify-independent-evidence.py`，操作見[五房文件](DESKTOP_INDEPENDENT_LONG.md)。要求原handle先terminal及cleanup明確空列；只讀固定JSON／CSV，逐房交叉核對獨立headers／seal／最後Ended packet、原native admission／room／seat、ack名單、CSV SHA及七統計／session／room／source／雙尾界。檢查Pause witness、Running人次及接受計數；拒絕未知null當乾淨、錯格式／原件內輸出／覆寫。live可coalesce，完整回放仍精確，不新增遊戲政策。輸出complete只表示讀回完成，acceptancePassed另保留失敗；hash非簽章，metadata讀回不是重跑原始規則、歷史OS程序或全量輸入／渲染證據。

新增17項反例涵蓋前一幀尾界、同ID換admission、獨立seal／ack／CSV篡改、統計相符但原body失敗仍false、Pause其他房不前進、replay缺幀、live既有政策及原檔byte保持。最後17＋原10 independent／11 multiplayer／8 comparison／14 journal，**60 Python通過**，語法及diff成功，CI已加入新入口。

舊原工具handle96709已不存在，原exit0與完整cleanup證據保持；新7849也確認terminal後，對舊 `20261031-193917-b2f30b7d` 及新場做兩份各自獨立讀回，`independent-evidence-e059-20261101.json`成功、兩場acceptance保留true。這不是Linked跨場比較器，不推定不同source／主機條件相同，也沒有改寫原0.36尾界失敗或原31筆姿態失效。

五份關閉VRWORLD1另作rb checksum／序號metadata核對，皆Ended tick18000、frame／ack精確相同、completion／seal各一、尾端積壓0；歷史最高本地durable回條積壓依房為4／3／3／3／3，**不是32幀記憶體queue、網路延遲或API拒收**。沒有保存精確Begin回應，applicationBoundaryKnown=false／firstApplied=null，不猜序號或套用延遲；詳見 `independent-e059-journals.json`，未開保存SQLite或outbox、未ack／修復／補送／截尾。

`independent-e059-runtime-validation.json`核對新1個C runtime22檔／F snapshot逐檔一致，前43 runtime869檔、前F337及原失敗場F76、0.36 history321檔保持；新場F證據112檔另存hash。總44 C runtime891檔，所有writer全停才一次snapshot保留原件。舊／0.35／本輪API各159，以及原0.36 ZIP／history與0.36.1 Windows包／APK／receipt metadata保持；本輪沒有新封裝或launcher驗證。

完整11項active。下一步推進同版動態玩家PC操作及連續性，慢碟發布吞吐、原31筆根因／修復、頭盔／MR／VIVE／跨機25台及廠商硬體仍各自待驗。

## 2026-11-01：背景世界錄製的戰績尾界競態

功能 [5443835](https://github.com/peca12968/vr-command-center/commit/544383540896a746a0ac3ac417d4c72681a85a8c) 已推送main、遠端SHA一致。[本功能CI run41252650265](https://github.com/peca12968/vr-command-center/actions/runs/41252650265)／check124689197862為failure、steps空；fresh annotation明確為付款失敗或支出上限，job未啟動、無雲端測試結果。未改帳務或手動重跑，下列均為本機實際驗證。

從 `e387223` 接續電腦端，新增 [結果尾界修正](DEBRIEF_BOUNDARY.md)。**Unity0.36.1／Android code44，API/UI0.30／NGO29保持**。Ended 的 pending context 綁定 writer 已接受的 terminal capture，最終送出另外核對同一 immutable durable State 的 Complete／Sealed／Last／Ack 及 session／stream／origin；不以 buffered 或舊 durable 前綴冒充最終世界。原30秒等待、撤銷／admission、ack／Host收尾、客戶端精確序號及遊戲政策保持。

原0.36的真正25端900秒場 `desktop-long/20261101-064213-cf891c07`，**handle46963真正exit1**，`Debrief world seal differs`。API／closed journal最終8442、Ended tick18000、雙seal成功；25份結果都有ack，但其中一份worldSequence8441，其餘24份8442。原journal8441為Running／observed36、8442為Ended／observed37，兩者tick18000；不能用相同到期tick或最終統計一致放過錯誤尾界。程式在逐玩家建立context時讀當時durable Last，背景End寫入可在迴圈中才完成，與反例一致。

該場live8366幀／8365 Running、209125人次、無bad／來源過期，最大來源年齡0.345400秒，但live跳2序號；在結果檢查就失敗，**沒有完整API回放、final CSV或multiplayer-checks完成檔**，不把抽樣乾淨當整場接受。cleanup空／無殘留，writer全停後一次snapshot保留原件。`debrief-boundary-counterexample`另外用rb核對原checksum／序號與25份結果，不重寫原場；原worldlog SHA `139c158a9fe796d2d37494efccaa3afb1a0f16fc9141103d8378b0d5db71a5c2`。

新增2項真正Editor測試，以自己的FileWorldJournal gate重現durable1／captured2，完整等待／落盤／ack／seal各階段與舊尾界／外場stream／失敗writer反例。**179 Editor全過，failed／skipped0**，包括原3項Editor PlayMode官方Touch虛擬action測試。最終來源 `e0594513140ff7fb4bc084929691b91c15f7d908e8f59c114aa5ab27daaf11eb`；真正Prepare保持原scene／prefab ID，無RebuildArena。

Windows receipt10月31日23:04:56Z、Quest23:14:49Z，同e059來源與原scene／prefab識別；APK60311450 bytes、SHA `263ae66309ef5f1f604286c38277aa74ec3f53418fabc32c6e88dcc75920c2e2`，aapt0.36.1／44、min32／target35、arm64及v2一signer有效。105 entries、indexed compressed60289996／uncompressed160904695、libil2cpp81993392；不把ZIP容器大小當程式碼／效能指標。

新 `windows-player-0.36.1.zip` 82642182 bytes、SHA `483a6f95b2944b622dffddd617559b742e480ee94072fd3b61fcf6b5dc8d3899`，311 runtime檔＋manifest，launcher source仍a65846da...。全新C解壓後19項真正核對／拒絕成功（`player-package-checks/20261101-072420-cde50e4f`），未重跑完整GUI／封裝雙PC瀏覽器或改launcher。封裝／驗包在長場Ended後的回放期執行，不作無負載對照。

| 新e059來源真正PC場 | 結果 |
|---|---|
| `desktop-debrief/20261101-070547-86e98e87`，一般 | handle55675 exit0，4項／兩份精確結果；移除玩家無結果、Ended票券拒絕，cleanup乾淨 |
| `desktop-debrief/20261101-070614-3ace3ad5`，Host | exit0，4項／兩份精確結果，Host等待peer ack後收尾，cleanup乾淨 |
| `desktop-debrief/20261101-070614-d47a6f09`，Preparing取消 | exit0，4項／兩份零事件結果、原拒絕流程，cleanup乾淨 |

新長場 `desktop-long/20261101-070628-e45c2643`，**handle80201真正exit0、executionFinished／acceptancePassed／complete均true**。25個原client＋1個server、900秒活動倒數／唯一tick18000內部End；8414完整回放、8331 Running／208275人次、無bad，25份原admission結果與CSV／combat及world精確雙seal全一致，全部worldSequence8414；cleanup空／無殘留、原生日誌無queue error。live8321幀／8320 Running、208000人次、跳4序號，已由全回放補查；最大保存擷取gap321ms、來源年齡0.173768秒，不當RTT／FPS。票券到期後tick5952仍25份原admission、每份只一個原連線，未重入場。三個短場及長場前段與真正Quest建置重疊（23:14:49Z完成），封裝在Ended後回放期，不稱無負載或隨機因果對照。

三場closed比較 `continuity-comparison/debrief-boundary-20261101` 成功，逐玩家原admission／CSV七統計／世界與combat尾界獨立核對；原0.32失效場仍2幀／31筆／18位、acceptance=false，0.33既有乾淨場與新e059並列。source及診斷欄位不同，causalRootProven／networkCapacityAccepted均false；complete只是比較完成。原0.36的8441反例沒有完成報告，另用明確失敗資料核對，不強塞進要求完整格式的比較器。

新場closed worldlog SHA `cedc9ad30a62e44955ed4677eb15751957eb28d566eaa3c6556865fad9199a89`，8414 frame／8414 ack／一completion與seal；尾端積壓0、歷史peak5，最早world5／ack0／byte82212。沒有保存Begin回應，applicationBoundaryKnown=false，不猜接受序號或套用延遲。這不是32幀writer queue的深度或網路延遲。

離線journal reader新增最高本地持久回條積壓及最早record邊界（byte offset），結束歸零／seal不抹除歷史高峰；反例原場peak4、尾端0，兩者可同時成立。這是已保存幀與本地durable receipt差額，不是32幀記憶體queue／網路延遲，ack沒有獨立UTC，不造持續時間。無Begin回應可省略接受序號，applicationBoundaryKnown=false／firstApplied=null，不猜Begin或補造舊raw欄位。新增3個反例後，14 journal＋10 publication＋10 stages＋8 comparison＋11 multiplayer，**53 Python成功**；CI已含原journal測試入口。

本輪沒有改後端／UI／共享Simulation／wire／rules／素材pin／Tracked，沒有重跑原717規則／459 HTTP／47串流或一般瀏覽器；API三工具仍取上一輪同版159檔C副本，原5080不動。來源／binary仍F，場次runtime明確C SSD；不是F USB吞吐修復、舊31筆修復或跨機／頭盔容量驗收。

`debrief-boundary-runtime-validation.json`核對新4個C runtime56檔／F snapshot相符；前39 runtime813檔（含原失敗場14檔）、前F337檔及該失敗場F證據76檔保持，總43 C runtime869檔。保存SQLite不開、沒有ack／repair／truncate。0.36 Windows／Quest／logs321檔先完整保存於 `debrief-boundary-history-path.txt` 所指目錄，最終逐byte hash仍相符；原0.36 ZIP及更舊／0.35／本輪API三工具各159檔也保持。audit只表示原始資料保持，不是遊戲驗收。

完整11項目標active；下一步推進同版五獨立房長任務及實際動態玩家PC驗收，慢碟發布吞吐、原31筆、實機／MR／跨機／25台及廠商硬體各自保留。

## 2026-11-01：有界背景世界writer與durable狀態快照

功能 [d18aad6](https://github.com/peca12968/vr-command-center/commit/d18aad6c3140628d33392ea3ad4949cda2f2480a) 已推送main、遠端SHA一致。[本功能CI run41249194813](https://github.com/peca12968/vr-command-center/actions/runs/41249194813)／check124678950692為failure、steps空；fresh annotation明確為付款失敗或支出上限，job未啟動，無雲端測試結果。未改帳務或手動重跑，下列為本機實際驗證。

從乾淨`23f3a06`依上輪量測實作[背景世界writer](ASYNC_WORLD_WRITER.md)。**Unity0.36.0／code43，API/UI0.30／NGO29保持**。主執行緒仍擷取Arena／實際頭手及原UTC／事件cursor，僅detach／提交immutable JSON；獨立writer依FIFO執行原Append／逐筆Flush(true)，Ended幀成功才寫completion。publisher另在背景運作，只讀真正durable Pending並等待原combat ack／world ack／雙seal。Outbox immutable State只在成功持久寫入後以Volatile公布，常態讀取不再等待journal gate；寫入／Pending仍使用原gate。

queue最多32幀（含in-flight）／8MiB UTF-8 JSON，單幀仍原record上限。滿載fail closed、停止新提交及暫停combat，已接受幀仍drain；IO失敗不補造frame／ack／completion。停止先拒新提交、等待writer及已取消／完成publisher後才關source lease，不同步阻塞主迴圈。captured／buffered不是durable；live NGO可能領先錄製，非正常process退出可能失去尚未落盤queue，補送仍不是引擎世界恢復。啟動header與combat journal仍可能同步IO，**不稱所有IO已移出主線或F USB吞吐量修復**。

不改world/header／wire／rules0.8.0／素材pin／Tracked／0.5與1.5秒政策。新診斷`WorldEnqueue`僅量主線提交，不和舊`WorldJournal`同步Append混稱；分析器明列Queued／Synchronous、混合模式拒絕。File Flush仍以managed ID分類，時間與重疊區間不加總。專用native checker的journal-trace模式有界讀自己的server.log尾64KiB以fail fast記錄故障計數，一般模式不新增該讀取；本輪F並未觸發queue滿載，不把單元反例當自然滿載實測。

**最終來源`7194dc98ab4466edfd23c9c31b959757b853155fbce657ee5dc0adfa6b96d8c6`**，真正Prepare、兩輪177 Editor全過（failed／skipped0）。新增8項含非主線寫入／durable尚未前進、caller mutation隔離、FIFO／同步原journal逐byte相同、幀數含in-flight／byte上限、IO失敗不假造邊界、Stop／exclusive lease及無效序號不消耗；既有gate測試改為驗證被阻塞receipt時state仍立即可讀。補WorldEnqueue名稱／fault通知後再次177與雙平台，非拿首輪代最終。

Windows receipt10月31日22:22:19Z、ARM64／IL2CPP Quest22:29:57Z同7194來源成功；scene `4314adcd8c63d86469d16497127d8cfb／1444571642`、prefab `6f3f36cb9d710e847b5ecc569665e1ce／5227825248646244841`保持，無RebuildArena。舊d30的0.35 Windows／Quest／logs完整保存於`queued-writer-history-path.txt`所指目錄。

| 真正PC場 | 結果 |
|---|---|
| `unity-admission/20261101-062423-831a1217`，C runtime／無probe | handle15166 exit0，原8項／400幀精確seal、cleanup空。當時另有Quest建置，不稱無負載基線 |
| `desktop-clock-faults/20261101-062942-8e7c8270`，C runtime／原loopback故障工具 | handle21534 exit0、8項。管理中斷於tick114停表，hold5.860秒後同policy恢復；發布中斷仍到精確tick1200凍結，未接受due時間hold6.672秒不授權End，恢復後唯一內部End／雙seal／client結果。743完整連續回放含94個due Running／64個suspended幀，末packet與戰績一致，cleanup／proxy均乾淨 |
| `unity-admission/20261101-063140-798211ab`，F資料＋真正封裝重疊 | parent25274 exit1，admission1／package0，Running15秒逾時、無summary／cleanup空。Begin接受7；45次live皆Preparing，world148→247、年齡19.834→23.996秒；來源world335／tick3已有效Running，擷取為回應後0.404647秒。關閉來源world478／Running tick321、ack254，**224未確認、未seal**，失敗保持 |
| `unity-admission/20261101-063345-d8304c05`，明確C SSD＋同封裝重疊 | parent67128 exit0，admission／package均0，8項／354幀精確seal、cleanup空。first有效live world49／tick5／observed7，單調回應後0.437秒、年齡0.073666秒；ack354、無積壓 |

兩個負載parent為`queued-world-overlap-8f2e4029af9141bb909b88e94b05bcca`及`...4c1f69bdc4b74c0c9de56811a0e4b9b9`，均確認package在native啟動及Begin檔出現時仍存活，無輸入／姿態注入。來源／Unity binary在F，API用本輪獨立159檔C副本；F／SSD只指場次SQLite／journal位置。

| Begin UTC窗口（不跨role加總） | F佇列版反例 | SSD佇列版 |
|---|---|---|
| 窗口／完整細分列 | 15.131338秒／2685列 | 0.430971秒／3271列 |
| 最大UTC／Stopwatch差 | 0.002119秒、可相關 | 0.001360秒、可相關 |
| Main world GateEnter／Main Frame Flush | **皆0秒** | **皆0秒** |
| Background Frame Flush聯集 | 8.864939秒，窗口142筆 | 0.002059秒 |
| Background Ack Flush聯集 | 3.467186秒 | 0.002042秒 |
| Main WorldEnqueue聯集／最大單次 | 0.016539秒／0.000635秒，140筆 | 0.000476秒／0.000118秒，5筆 |

兩份細分trace皆complete／未truncated／inFlight0、failedOperations0；來源Header啟動IO不在這個Begin窗口。0.35已量到main讀鎖／flush，本輪將這兩段世界路徑移到背景；主線仍有擷取／JSON成本，舊新窗口／取樣節奏／主機條件不同，**不作提升倍率、所有停頓／舊31筆或F整體修復證明**。F仍有明確發布積壓且沒有完整seal；不得用main世界IO為0把此場改成通過。UI仍以原UTC年齡顯示過期，WS／API／SQLite／combat未另量測或重構。

observer graph `79e8a90983c6ad01256b0af59b1f48f98b91bbaa662dc529f68738d11bd3262f`；三分析graph `0b0e1dbf6dd2b26a4fb595415be2ac0a8a816e68803ac2ca7b51adea2d94906a`，不是完整OS／binary依賴。F原worldlog SHA `3e8f5712e9a074ff6e1bfb3acf7147e0b78eb071639fdd87cd68ab89d0ff10e8`，原始長度／checksum／序號核對通過，不修復／補送／截尾／開SQLite。

本輪隔離`artifacts/queued-writer-dotnet` locked restore／Release成功、0 warning／error，**717規則／459 HTTP／47串流**成功。新增Queued模式／混合拒絕反例後，**48 Python**成功，語法／diff成功；UI未改，沒有新一般瀏覽器／GPU或頭盔證據。所有.NET DLL與三工具用同次建置整組，不單換Simulation DLL，原5080未動。

可攜包`artifacts/player-packages/windows-player-0.36.0.zip`，311 runtime檔＋manifest、82641883 bytes、SHA `a31af925c432576b2bf0e192085aadeffe2ddcdc5f27d24bd98f288562d2e0df`，launcher source仍a65846da...；新C解壓包19項真正核對／拒絕成功（`player-package-checks/20261101-063002-4e90e1d8`），未重跑完整GUI／封裝雙PC瀏覽器。APK60309566 bytes、SHA `a054dc6fe09b3167c3d937717fef9ff264d160402790411822021540f120b945`；aapt0.36／43、min32／target35／arm64，v2一signer有效。105 entries的compressed60288113／uncompressed160903604、libil2cpp81992416；相較0.35容器少約22MB不是程式碼縮減，indexed內容仍略增，未自行重打包／改簽章／清cache。

`queued-writer-runtime-validation.json`raw核對新3 C runtime72檔／F snapshot一致，前35 runtime727檔及snapshot、前自有F295檔保持；最終F42檔保存。更舊／0.35 API三工具各159檔保持，本輪新159檔來源／C副本一致；0.35 ZIP、封存APK與雙receipt精確hash保持。全停writer後才snapshot，原件保留，不讀正式key或保存SQLite，未動帳務／登入／防火牆。

下一步處理慢碟下發布吞吐／明確SSD部署與長任務壓力，保留原durability／封存、佇列上限及實際年齡；不先跳幀或放寬政策。完整11項active，Quest／VIVE實機、MR、跨機／25台與廠商硬體仍待；原31筆保持未證因／未修復。

## 2026-11-01：journal鎖／flush分段與0.35同源交付

功能 [2e77c8b](https://github.com/peca12968/vr-command-center/commit/2e77c8b1d8d31a3d625fb00d6827762d5af30f34) 已推送main、遠端SHA一致。[本功能CI run41246401262](https://github.com/peca12968/vr-command-center/actions/runs/41246401262)／check124670631224為failure、steps空；fresh annotation明確為付款失敗或支出上限，job未啟動、無雲端測試結果。未改帳務或手動重跑，下列結果均為本機實際驗證。

從乾淨`5332886`接續[細分journal計時](JOURNAL_STAGES.md)。**Unity0.35.0／Android code42，API/UI0.30／NGO29保持**。共享C#9／netstandard2.1 collector及明確Windows Development／專用Server探針分別量測所有outbox gate進入、File Write及真正FileStream.Flush(true)，只保存metadata／managed thread ID／成功旗標。原mutex、逐筆durable flush、exclusive lease、checksum／ack／seal與回放位元組保持；不改world／wire／rules0.8.0／素材pin／Tracked／0.5與1.5秒政策，不是效能修復。

collector上限32768完成列／64 in-flight，原生90秒、停止後最多5秒drain；完整／未truncated／inFlight0才可接受。一般／Editor／Android不安裝，finish.request僅每0.25秒查詢；cleanup先停兩個probe收集，再輸出／End／關閉。分析器用UTC終點減Stopwatch耗時定位、裁切聯集及Main wait與Background ack flush交集，避免raw UTC量化抹掉短呼叫；clock差>0.05秒或未覆蓋則null、不補造0。該診斷容差不是遊戲新政策。

**最終來源`d30cc34c697a612ef05733e4fb116281807151658460c0550df3c5e825a703e3`**，真正Prepare／169 Editor全過（failed／skipped0，新增6項含真實gate阻塞、失敗Write、並行Stop／drain及有／無trace原journal逐byte相同）。10月31日Windows receipt14:12:21Z／Quest14:20:08Z同源成功，原scene `4314adcd8c63d86469d16497127d8cfb／1444571642`、prefab `6f3f36cb9d710e847b5ecc569665e1ce／5227825248646244841`保留，無RebuildArena。中斷後舊handle92079已消失、Editor PID48628亦不存在；重新核對成功log exit0、新receipt／目前fingerprint及XML確認完成，未因觀察中斷重建。

| 最終d30來源的真正PC場 | 結果與來源 |
|---|---|
| `unity-admission/20261031-221302-b8a7421d`，C runtime、無probe | handle74773 exit0，原8項／363幀精確seal、cleanup空；沒有兩份trace。當時另有Quest建置，不當無負載基線 |
| `unity-admission/20261101-055610-ab7c9421`，F資料＋真正封裝重疊 | parent94479 exit1、admission1／package0，Running15秒逾時、無summary、cleanup空。Begin接受7；41次live皆observed6／Preparing tick0、world126→192、年齡9.472→16.056秒。關閉來源world205／tick5已有效Running，擷取為回應後0.667191秒；最後world328／Ended tick321、ack200，**128未確認、未seal** |
| `unity-admission/20261101-055717-fd2b98b6`，明確C SSD＋同封裝重疊 | parent66382 exit0、admission／package均0，原8項／355幀精確seal、cleanup空。接受7；首次有效live／journal皆world48／tick2／observed7，單調回應後0.563秒、年齡0.067086秒；ack355無積壓 |

兩parent為`journal-stage-overlap-29bb544bf3734279bdc08ed11c525c15`與`...7f1e790fc81a4992b4e113661da5f0fb`，均確認封裝程序在native啟動及Begin檔出現時仍活著，非僅排程意圖；無輸入／姿態注入。API用同次159檔C執行副本，來源與Unity binary在F；F／SSD指場次SQLite／journal位置，不能把API副本也說全在F。

| Begin UTC窗口內分段（重疊欄不可加總） | F最終反例 | C SSD最終場 |
|---|---|---|
| 窗口／完整分段列 | 15.077624秒／4328列，43.879866秒觀察 | 0.566151秒／9581列，37.865466秒觀察 |
| 最大UTC／Stopwatch差 | 0.002379秒，可相關 | 0.001252秒，可相關 |
| Main Frame DurableFlush聯集 | **8.814804秒**，窗口116筆 | 0.002560秒 |
| Main GateEnter聯集 | **3.134420秒**；CompleteState讀取占3.134406秒 | 0.000051秒 |
| Background Ack DurableFlush聯集 | 3.562025秒，窗口67筆 | 0.002721秒 |
| Main等待與Background ack flush交集 | **3.133609秒** | 0秒 |

兩份細分report皆complete／未truncated／inFlight0、failedOperations0。這次量到同一outbox gate的**狀態讀取**會等待背景ack持鎖flush；CompleteState讀取在原WorldCapture括號之前，不能漏算成沒有等待。Flush(true)耗時含OS／排程／儲存路徑，非純實體媒體時間；managed ID不是OS ID，File層Frame sequence0是unknown。WS／API／SQLite／combat journal未新增分段，不能由不同窗口比例推效能倍率、單一硬碟／原31筆或所有舊逾時已修復。

observer graph `c5f7aaaddf82ff0ce0ee6f01ef85a1397a562909062df9ad843cb50bdb75d9f9`、三分析腳本graph `017c740ccb43861dbf596b3b09d63176958a121637259aec0700bcf9abb9e50f`，不當完整OS／binary依賴。最終F原worldlog SHA `46ec2c21db389037c344ac8ba208cab883a83973a6b9c703e1a51fe56edf0a6c`／840268 bytes，原checksum／序號核對成功，不截尾／補送／開SQLite。

本輪隔離`--artifacts-path artifacts/journal-timing-dotnet` restore locked／Release成功，**717規則／459 HTTP／47串流**通過；共用.NET DLL及三工具整組使用，不只換單一Simulation DLL，不替換原5080。10項新分段反例（UTC量化／thread分類／unknown等）＋37既有，共**47 Python**成功，語法／diff成功。UI未改，沒有新瀏覽器／GPU或頭盔檢查。

最終玩家包`artifacts/player-packages/windows-player-0.35.0-final.zip`，311個runtime檔＋manifest，82638063 bytes、SHA `a18b27dab40927e10dac50a392eb196037bad23c943cc4f6b9ee235e0e260e81`，launcher source仍a65846da...；全新C解壓通過19項真正啟動器核對／拒絕（`player-package-checks/20261031-221714-ae922d8f`）。這是offline launcher＋上列原生回歸，**未重跑完整GUI按鈕／封裝雙PC瀏覽器流程**。最終APK82742165 bytes、SHA `f4dde150a8cce6cd6b21e11c86476e22502422644b588be1cc7bb2782b5c137c`；aapt核對0.35／42、min32／target35／arm64，apksigner v2一signer有效。105 entries的compressed60278055／uncompressed160864436、libil2cpp81959304；候選APK曾60297850 bytes，容器差異不當功能或程式碼增減。

保留探索／失敗：PS1被執行政策拒載後直接呼叫相同Editor入口，未改政策；.NET nullable CS8604／8602以原gate內明確null拒絕修正；首輪Prepare C#9 CS8773為測試PathFor漏括號。第一輪169實際Editor0／XML全過，但自有runner序列化XML Element時exit1，修正輸出後最終Prepare／Tests／雙平台依序成功，未把runner1稱0。`journal-candidate-path.txt`保存f93dbc9b... Windows／Quest／logs，`journal-timing-history-path.txt`保存更舊c233原0.34。候選正常363幀、F `220457-479bf14d`其實**Paused逾時**（Begin13.313秒才看見、年齡12.780秒，112未確認），候選SSD `220559-538c2cb0`8項354幀成功。初版每幀查結束檔增加干擾，改0.25秒後重新169／雙平台及最終兩場，候選不冒充最終。raw UTC相減探索分析另存，最終改Stopwatch投影並補反例，未修改原生資料。

`journal-stages-runtime-validation.json`raw核對最終新2 C runtime32檔／F snapshot完全一致、前33 runtime695檔及snapshot保持；前自有F253檔／舊API三工具159檔保持，新API三工具159檔亦核對來源／副本，最終F反例42檔保存。writer全停後才snapshot、原件保留，舊0.34 ZIP／歷史APK不覆寫，不讀正式key或保存SQLite；未動登入／帳務／網路安全性設定。

下一步評估已量到的main讀取等待／同步flush所需writer架構或明確SSD部署，不先關閉durability／跳幀／放寬政策。完整11項active；Quest／VIVE實機、MR、跨機／25台、廠商硬體及舊31筆因果驗收仍待。

## 2026-10-31：原生journal區段計時與再次負載重現

功能 [32e6ed7](https://github.com/peca12968/vr-command-center/commit/32e6ed7bb3ef5b7d51517c1315aca08ae5fd9a76) 已推送main、遠端SHA一致。[本次CI run41206671836](https://github.com/peca12968/vr-command-center/actions/runs/41206671836)／check124553038805為failure、steps空；fresh annotation為付款失敗或支出上限，job未啟動，沒有雲端測試結果。未改帳務或手動重跑，下列37項Python與原生結果為本機實際證據。

從乾淨`82ea45b`接續[發布區段計時](PUBLICATION_TIMING.md)，上一輪為實際進展。本輪以**原c233 Windows播放器既有探針**取得新證據，API/UI0.30、Unity0.34／code41／NGO29不變，沒有修改Unity／後端／共享程式、重建163 Editor／雙平台或改原0.5／1.5秒政策。一般玩家不附掛新診斷。

checker選用`--server-trace`只啟用自己的server既有240秒／32768列NativePoseTrace，結束／失敗時先request finish並取得完整report，再End／停止程序；缺report、overflow或cleanup失敗仍exit1。新分析器將原生UTC／Stopwatch與同場Begin窗口對應，先裁切再取同point區間聯集；WorldCapture內含WorldJournal，不相加。trace／witness不完整直接拒絕、時鐘差>0.05秒或未覆蓋窗口則相關數字unknown；該容差不是遊戲新政策。journal另確認sessionId，不能跨場借用接受序號。

| 同主機、真正玩家包編譯／壓縮重疊的新場 | F資料 `unity-admission/20261031-213407-7c213c4e` | 明確C SSD資料 `unity-admission/20261031-213539-3a0d26e6` |
|---|---|---|
| 真正parent終態／cleanup | handle81146 exit1，admission1／package0，無summary；cleanup空 | handle23513 exit0，admission／package均0，原8項／354幀精確seal；cleanup空 |
| Begin與live | 接受7；43次皆observed6／Preparing tick0；live106→180，年齡12.334→16.921秒 | 接受7；4 Preparing＋1 Running，first world47／tick2／observed7，單調回應後0.671秒、年齡0.069796秒 |
| UTC觀察窗口／完整原生trace | 15.242625秒；4752列、41.9633094秒完整／未truncated | 0.673960秒；3494列、37.5978764秒完整／未truncated |
| 最大UTC／單調差；全窗口覆蓋 | 0.011078秒、可相關 | 0.005593秒、可相關；UTC窗口與單調數字分開 |
| 窗口WorldJournal | 115個區段、聯集**9.379684秒**、最大0.182471秒，32個>=0.1秒 | 7個區段、聯集**0.004067秒**、最大0.000625秒，0個>=0.1秒 |
| 關閉來源journal | first有效world198／tick5／observed7，擷取為回應後0.879103秒；最後316／Ended tick312、ack187、**129未確認，未seal** | first有效world47同live，擷取為回應後0.604164秒；最後354／ack354、無積壓、已seal |

兩個parent為`admission-trace-overlap-ea7dad6322dd46b1819a9b08981e6279`與`...945b4146d0bd48f2862299cbba7619a6`，皆保存package在native啟動及Begin檔出現時仍存活的證據，非只排程意圖；沒有輸入／姿態注入或重發Begin。F失敗經cleanup送End後有completion intent，但未seal且無成功summary，不能稱完成。trace停止後仍有4個清理期間來源幀，因此312個journal spans不冒充全部316幀映射。

F窗口WorldCapture聯集9.383359秒、MainThreadGap聯集9.674268秒，與WorldJournal重疊，**不能加總**；MainThreadGap共有68個窗口異常，明細只留最早64、計數及聯集仍全量，這個明細旗標不表示原生trace溢位。這次已量到主執行緒長journal區段，但該區段包括mutex等待、序列化／驗證、append及Flush(true)，**不是單獨fsync或CPU時間**。背景ack鎖／flush、WebSocket及API／SQLite仍未分別量測，也沒有原生span-to-sequence標記。

最終分析`publication-timing-final.json`的兩檔fingerprint為`12c97ca83dd9ea5b0aca93a88d288774ccfb10856d0378c93ce0ebb6df749085`；兩次native observer凍結同`ac3a2d0acef7e7e3591dcd4e39592479cecf8aebf76250b373a4c4fe8dd30bf1`，原receipt皆c233。F最初探索分析採區間相加（9.380564秒），保留原檔，最終改用聯集避免UTC重疊重算；未改native結果。不同時間／窗口長度、trace條件與未控制IO／排程，不能用兩數比例當因果或容量提升倍率；舊場與31筆不合併成同一根因。

9項新相關性／裁切／重疊／unknown／溢位反例、11項journal（含新跨場拒絕）、8 witness、5真正Windows artifact lease及4 startup，共**37項Python成功**，語法／diff成功，CI加入新檢查。`publication-timing-runtime-validation.json`raw bytes核對新C16檔／F snapshot一致、前30 runtime647檔及其snapshot保持；前輪自有F167檔／API三工具159檔及正式0.34 ZIP／APK精確SHA保持。新F反例41檔保存，SQLite不開、5080／帳務／登入／安全性未動。

下一步把frame及背景ack的journal鎖等待與真正Flush耗時分開量測，再評估保持durable ack／完整回放的writer架構；不能為F延遲先關閉持久化、跳幀或放寬姿態政策。完整11項仍active；實機／MR／跨機與廠商硬體待驗。

## 2026-10-31：Preparing逾時重現、來源journal與SSD入場比較

功能 [d0b5f3c](https://github.com/peca12968/vr-command-center/commit/d0b5f3c929a113ef329aaa1ab411176cb1e44d2f) 已推送main、遠端SHA一致。[本次CI run41205865737](https://github.com/peca12968/vr-command-center/actions/runs/41205865737)／check124550701322為failure、steps空；fresh annotation明確為付款失敗或支出上限，job未啟動，沒有雲端測試結果。未改帳務或手動重跑，下列27項Python與原生結果為本機實際證據。

從乾淨`e0ea233`接續[開場觀察](STARTUP_WITNESS.md)，本輪在原撤銷／重新加入流程、真正玩家封裝編譯／壓縮同時執行的情境重現Running逾時，並分開核對live與關閉的來源journal。**API/UI0.30、Unity0.34／code41／NGO29及c233d804...來源保持**，未改遊戲／後端／wire／Tracked／規則或0.5／1.5秒政策；沒有新Editor或雙平台重建，原163與成功receipt仍屬前輪證據。

入場checker新增有界metadata witness，依Begin接受序號、Running／tick>0／非suspended判斷套用，保留來源UTC／年齡和原15秒觀察；新唯讀journal分析器逐筆驗證VRWORLD1長度／SHA／序號與receipt邊界，只輸出metadata、不開SQLite或寫回／修復。8項witness＋10項journal反例＋5項既有真實Windows artifact／writer lease及4項既有startup測試成功，共27項，語法／diff成功；CI加入相應檢查。checksum／序號不冒充完整世界規則驗證。

| 原生自有新場 | 實際終態 | Begin／來源與接收證據 |
|---|---|---|
| `unity-admission/20261031-211904-9cfe99f1`，F資料、無封裝重疊 | 真正handle28285 exit0、原8項／380幀精確seal、cleanup空 | 接受7；首次有效live world57／tick6／observed7，回應後0.984秒、年齡0.788秒；journal同最早有效幀、ack380、無積壓 |
| `unity-admission/20261031-212112-f59b1f99`，F資料、真正封裝重疊 | parent69722 exit1、admission exit1、package exit0；無summary，cleanup空 | 接受7／管理Running；37次live皆observed6／Preparing／tick0，年齡6.748→16.383秒。來源journal有232幀，world136已Running但tick0不算有效；world137／tick8／observed7非suspended才有效，擷取UTC為回應後0.801秒。最後來源world232／tick301，持久ack只126，**106幀未確認、未complete／未seal** |
| `unity-admission/20261031-212633-2f8c41bf`，明確C SSD資料、真正封裝重疊 | parent13610 exit0、admission／package均0；原8項／358幀精確seal、cleanup空 | 接受7；首次有效live與journal皆world49／tick2／observed7，回應後0.531秒、年齡0.083987秒；來源擷取為回應後0.451秒，ack358、無積壓 |

兩次重疊parent各保存獨立ZIP／log／result：`admission-package-overlap-901c47fe8eec4acfb7c8297134ec586a`與`...d8e054cbd7fb4dd68a7b3cbf12d305ab`，均核對package在native啟動及control-Begin檔出現時仍存活，不以排程意圖冒充實際重疊。F反例原始worldlog SHA `df77fc1ccb930cc92751cb9bb2b0ec57f6f1de9e9f87cd4117f64fab2406ae8d`／601712 bytes，全部359筆checksum／邊界核對通過（header1、frame232、ack126）。不是以提高15秒門檻、跳幀、刪掉Preparing或重發Begin取得通過。

這次已證明**該新反例的來源有套用Begin、API/live仍落後**，不能再把此場描述為來源一直停Preparing。發布積壓階段明確，但尚未量測每筆fsync／WS／DB／主機IO的耗時；不同輪次未控制所有排程／負載，**沒有證明單一F硬碟因果或所有舊逾時已修復**。原`204538-5c3e58ba`沒有Begin回應，不能把新場7套回舊場；原31筆姿態失效也不能與本場合併成同一根因。

checker新增明確`--runtime-root`，僅建立自己的新目錄；SQLite與journal移到所指定SSD，來源／binary仍F，不移既有資料。全部writer停止後以共用snapshot fence複製回F並保留C原件。最終observerFingerprint `f028c34d6811305904c44ea2777f189944cda290d404eab6d33822165ae87922`包括兩observer腳本及共用snapshot的venue檔，不當作完整OS／native依賴graph；前一組F baseline／反例的兩腳本graph為`7104ff9e...`。兩者原生receipt同c233；比較明列Python工具差異。

另保留本輪前兩場：`211254-eb2a9de6`／handle7977 exit0、8項365幀為加入witness前基線；`211658-6f8b48ab`／handle78548 exit0、8項377幀為探索輪，過程中曾修改空UTC處理，**不稱最終封閉工具來源結果**。最後F baseline與SSD場分別在工具凍結下完成。

`admission-backlog-runtime-validation.json`raw bytes核對新C runtime14檔／F snapshot一致、前29 runtime633檔及其snapshot未變；前API＋三工具159檔保持，四個本輪自有F run共167檔保存雜湊。初次audit誤把buildCopies陣列當hash字典，exit1、沒有寫成功報告；依實際manifest逐目錄核對後exit0。保存SQLite不開、未動5080／原正式ZIP及APK、未改帳務／登入／安全性設定。

下一步保留自然負載下來源／發布階段的有界因果量測，再檢查多人持續操作與跨機部署；不把一次SSD成功稱F USB效能修復、25台／實機／MR或硬體驗收。完整11項長期目標仍active。

## 2026-10-31：原生Begin接受／套用觀察與受控校準

功能 [395c156](https://github.com/peca12968/vr-command-center/commit/395c156bbae50a67a2b0741db405b3505d946547) 已推送main、遠端SHA一致。[本次CI run41204413573](https://github.com/peca12968/vr-command-center/actions/runs/41204413573)／check124546467295為failure、steps空；fresh annotation為近期付款失敗或支出上限，job未啟動，無雲端測試結果。未改帳務或手動重跑，下列原生與4項Python是本機實際結果。

從乾淨`1c59040`接續[開場觀察](STARTUP_WITNESS.md)。前輪為實際進展，這輪針對Preparing逾時補上可重跑的控制路徑證據；**API/UI0.30、Unity0.34／code41／NGO29與c233d804...來源保持**，未改Unity／後端、姿態、規則或0.5／1.5秒政策，也未新跑163 Editor／雙平台，不把前輪結果稱本輪重建。

新工具保存Begin接受回應／序號、開場前幀、所有live取樣、首次有效Running及完整回放最早幀；要求observedSequence>=接受序號、非suspended、Running且tick>0，來源UTC仍<1.5秒、開場觀察仍15秒。每場兩個真正獨立client，兩份原admission結果／七統計／world及ledger邊界、精確雙seal與全回放一致；沒有輸入或pose注入、沒有新原生診斷模式。4項Python反例／語法／diff檢查成功，CI加入unit／語法。

實際`desktop-clock-faults/20261031-210737-1e370d2d`由真正handle71811走到exit0：3場直接連線與1場受控管理失聯，每場一server＋兩client、新任務／session。Begin皆接受序號5；直接場在收到回應後0.266／0.297／0.718秒觀察到有效Running，live first world17／16／21、tick5／3／2；全回放最早為world16／16／21，兩種最早觀察分開保存。此數字包含本機輪詢、儲存／發布，不稱RTT或來源執行時間。

受控場使用原有loopback VenueHttpGate，明確拒絕管理GET一次、0.187秒後requested release；只在記憶體轉送HTTP憑證／payload，不讀UDP。操作員Begin已被原API接受、管理狀態Running，但來源仍Preparing／tick0且suspended=true，不能當已套用；恢復後同接受序號、world22／tick3有效，回應後0.719秒／release後0.672秒觀察。全回放保留7個suspended Preparing幀，gate無handler／route／容量錯誤或界線自動釋放，關閉後無活躍tunnel／worker。

四場完整回放21／21／26／28，共96幀，第1到各自seal尾端連續、末packet／統計一致；八份個別戰績均經原admission核對。所有actor及gate已關閉，cleanup無錯誤／殘留，startup-checks complete=true、causalRootProven=false、networkCapacityAccepted=false。toolFingerprint只是新腳本SHA，不冒充完整依賴graph；玩家receipt仍同c233來源。

`startup-runtime-validation.json`raw bytes核對新1 runtime／20檔C原件與F snapshot一致、前28 runtime／613檔原件及snapshot未變，保存SQLite不開連線；writer停止才snapshot、保留原件。來源及binary仍F，資料明確C SSD，不能稱F USB、跨機／25台或頭盔通過。未動5080、帳務、登入／授權或防火牆。

**仍未重現或修復舊Running15秒逾時。**舊場沒有保存Begin回應，不能推定observed6就是Begin；受控503會有明確suspended，但舊單幀false不能排除中間曾有其他狀態。新場沒有原撤銷／重加入與同時建置條件，不能以短場乾淨或已知校準當自然根因。下一步在原入場變動／F負載情境保留命令及來源時間窗口；原31筆姿態失效亦保持未解。完整11項active、實機／MR／跨機及硬體另驗。

## 2026-10-31：Quest右手B鍵重連與暫停解除

功能 [8eabda9](https://github.com/peca12968/vr-command-center/commit/8eabda9d987ba684e46e46446b6b19a3b5f0ae40) 已推送main、遠端SHA一致。[本次CI run41203749271](https://github.com/peca12968/vr-command-center/actions/runs/41203749271)／check124544547164為failure、steps空；fresh annotation為近期付款失敗或支出上限，job未啟動，沒有雲端測試結果。未改帳務或手動重跑；下列真正Editor／建置／原生結果為本機實際證據。

前輪玩家狀態為實際進展；從乾淨`8dcc61d`補上[Quest控制器重連](QUEST_RECONNECT.md)。原Android會略過桌面OnGUI，故其Reconnect按鈕無法在頭盔使用；新增獨立於avatar的右手secondaryButton（Quest B）及等待畫面提示，重用原`ReconnectClient`重讀原路徑票券與GameServer驗票。**Unity0.34.0／code41，NGO29、API/UI0.30保持**；不改wire、world schema、票券／admission政策、Tracked姿態、模型／槍口、命中或0.5／1.5秒規則。

Client且NGO停止listening／shutdown、兩秒間隔到期才可嘗試，焦點及右控制器isTracked＋位置／旋轉trackingState均有效；必須先放開B再按，不能從斷線／冷卻／失焦／追蹤缺失帶入一直按住的狀態。另以OnApplicationFocus、OnApplicationPause及OnDisable明確解除準備，避免Unity停止Update時漏掉失焦。Server／Host不提供此控制，左Y不當右B；不自行配票、呼叫主控API、清除未重試的戰績或改追蹤資料。輸入action在bootstrap銷毀時釋放，原桌面按鈕共用同一可重連判定。

真正Prepare成功並保留原Scene `4314adcd8c63d86469d16497127d8cfb／1444571642`、prefab `6f3f36cb9d710e847b5ecc569665e1ce／5227825248646244841`，沒有RebuildArena。**最終163項真正Editor檢查全過、failed／skipped均0**，含新增8項政策／暫停解除及3項官方Oculus Touch配置的真實InputAction綁定。三項在空場景EnterPlayMode後，僅以自己的虛擬裝置／state event，在真正Dynamic更新回呼核對原控制值與action結果；臨時InputSettings還原、裝置／layout移除，沒有正式程式的輸入／姿態注入。測試asmdef直接參考Unity.InputSystem及Unity.XR.OpenXR，不靠隱含傳遞。

保留五輪真正失敗XML／log：159／3、160／2、160／2、159／3、159／3。先是InputState.Change不支援Touch bitfield，再是無焦點Editor更新未將controller event送進玩家action；只改成StateEvent仍不足，EnterPlayMode後同步呼叫Update也仍讀到Editor狀態。最終改用真正Dynamic回呼、同時斷言原控制值及完整action結果才通過，沒有放寬斷言或接受界線。最初162項成功候選（source `bd4c6419...`，Windows12:33:35Z／Quest12:42:58Z、PC8項445幀）另完整保存；補生命週期解除後重新163項與雙平台，不能拿候選當最終來源。

最終Windows receipt `2026-10-31T12:45:18.9215215Z`、Quest ARM64 IL2CPP receipt `12:52:48.9499476Z`真正成功，來源重算及兩receipt同為 **`c233d8048101109508490a9ff7b04a8c772fe71b1401223f3f69323a4cf74f5d`**，原網路ID相同。aapt確認bundle0.34／code41、min32／target35、arm64-v8a；APK實際**82,676,953 bytes**、SHA `fb5d1b469aa48202fbc0e46110ec46d1c6208142e6b28507a5ae5a7caae1fd97`。apksigner verify成功、v2 true、1 signer；ZIP checksum成功，metadata包含新輸入類別。沒有頭盔安裝或按鍵／焦點／面板實測。

APK的libil2cpp81,867,888／metadata9,270,596 bytes；有效ZIP項目總解壓160,769,828 bytes，比0.33僅多5069，索引壓縮資料60,244,012 bytes。容器另有約22.4MB空間，libil2cpp索引移至後段；未將此差稱成新增22MB程式，沒有重封、重簽或清Library cache，體積整理另列待辦。BuildReport totalBytes不是APK大小。URP匯入過程的暫時資源list變動最終回復原保存設定，沒有提交外觀／資產pin變更；兩個新.meta、測試asmdef及實際bundle設定保存。

最終原生回歸首場`unity-admission/20261031-204538-5c3e58ba`在等待Running15秒逾時、工具exit1，原last packet119／elapsed17261／observed6、Preparing／tick0／suspended=false、無summary，全部raw／journal保留。它與Quest建置及封裝並行，**未證明其原因**，不能推成新輸入bug、磁碟或建置已證實根因。原checker早期失敗不更新latest指標，因此仍指舊成功場；已補starting、命令回應、失敗state／world／events與cleanup紀錄，保留原15秒界線及所有接受條件，不把stale指標當本場結果。

等建置停止後，以同c233來源及原接受條件重跑`unity-admission/20261031-205415-cb4efdfa`，**8項／372幀**、真正handle5548 exit0，撤銷／舊admission拒絕、同次入場重連位置／健康／彈藥保持、Ended拒絕、精確雙seal及回放統計一致。這是自己的F資料、無圖形Simulation及原程序啟停，非頭盔B鍵、桌面GUI按鈕、GPU或C SSD效能；無法由一次重跑通過宣稱前場逾時已修復。cleanup errors／remainingTrackedChildren空，所有自有actor terminal；測試主動停止的exit1屬清理，非自然失敗。

正式`windows-player-0.34.0.zip` **82,634,575 bytes**、SHA `0862df2c0bc3d3e7daa62f05a10bd91e10e2be7cd53d988428702ce04e98f9f4`，311檔＋manifest；實際解壓新C目錄、Python全檔及真正Launch-Player.exe --verify成功，沿用launcher SHA `a65846da6f3a77de38356dbd9e448e55a220288ef170a407bba52cb227e63d57`。未重跑舊17／19／13啟動器套件，也不宣稱本輪GUI／跨機。首個bd4候選ZIP、APK／receipts／logs及舊0.33 APK（原fc0054... SHA）均保存於自己的history，未覆寫成新來源證據。

`quest-reconnect-validation.json`以raw bytes核對前**28 runtime／613檔**C原件及F snapshot未變、C API／三工具159檔保持；不開保存SQLite。本輪兩次成功及一次失敗admission皆用自己的F runtime，沒有新C SQLite試跑或移動正式資料。首五測試反例XML／log SHA、原生逾時raw hashes、最終receipt／APK／ZIP均記錄；原5080、帳務、登入／授權及防火牆未動。沒有新後端／瀏覽器UI變更，未把原.NET／完整瀏覽器結果當本輪重跑。

完整11項目標active。仍需Quest實際B鍵／失焦／追蹤／暫停、原票券檔USB更新、面板可讀性及實體重連；文檔提供不force-stop的暫存push成功後更名流程，尚未實機驗。原Linked31筆失效與本輪早期Running逾時都未證明根因／修復，接續因果證據、多人PC／跨機；VIVE／MR／25台／廠商硬體分開驗收。

## 2026-10-31：Windows玩家的入場／拒絕／未確認與戰績狀態

功能 [ddfc617](https://github.com/peca12968/vr-command-center/commit/ddfc6179dbe78da46683248b0ae86cda807fbde7) 已推送main、遠端SHA一致。[本次CI run41200268833](https://github.com/peca12968/vr-command-center/actions/runs/41200268833)／check124534526644為failure、steps空；fresh annotation為近期付款失敗或支出上限，job未啟動，沒有雲端測試結果。未改帳務或手動重跑，本機真正Framework／原生結果如下。

前輪五房長測為實際進展；從乾淨`aa4b866`接續[玩家連線狀態](PLAYER_CONNECTION_STATUS.md)。現有external地址公告及四欄連線檔已可分開啟動玩家，這輪補上啟動器只顯示「程式啟動」卻無法辨別真正入場的操作缺口。**API/UI0.30、Unity0.33.0／code40／NGO29保持**，不改後端、Unity、Tracked、票券、規則或世界格式；沒有新Editor／雙平台重建，原152真正EditMode與成功receipt保持。目前重算及Windows／Quest receipt仍`c98f1e1d9b6857de6fc17ea3c9d585ba41881ac528314f5e7fc0073ee5958b1f`，原Scene／prefab ID不變。

原生.NET Framework啟動器新增同類別的有界日誌監看，顯示Waiting／Connected／Rejected／Disconnected／Unconfirmed／Final；Connected必須由自己這次遊戲的精確marker回報，不從程序啟動、ping或TCP推成入場。至少30秒未確認只請人核對IPv4／UDP埠／版本，不猜防火牆或其他網路根因。Final不被正常結束斷線覆蓋，新Connected才開始新狀態；記錄不可讀時明示僅是先前回報，控制台readiness仍是另一個權威快照。

GUI來源在每次啟動將Unity原生日誌指定到自己的LocalAppData PlayerRuns新目錄，不讀全域Player.log或其他程序；關閉啟動器仍不終止遊戲／End。每次最多64KiB、跨讀UTF8 decoder、完整換行才辨認、單列4096字元／過長整列忽略，狀態歷史64筆，日誌倒退或積壓>2MiB停止推定；不新增姿態／GPU／PCM或網路探測，不讀其他程序memory或OS畫面。普通GUI不寫狀態報告，原CLI未要求監看則保持原流程。

選用`--status-report`必須搭配waited launch與自己的新log，僅保存固定state／PID／exited／availability／有界transitions，不保存ticket、actor ID或raw結果。只在內容改變時寫入；大小寫路徑別名、包內輸出或覆寫輸入／舊檔在啟動前拒絕。complete僅表示狀態快照未超界，exited是獨立的退出欄位，均不代表任務、網路或設備成功。

真正Framework compiler編譯同一`PlayerConnectionMonitor`、**17項C#檢查**通過：等待30秒不假裝連線、拒絕／斷線／重連、Final保留、半列／UTF8半字元、prefix假marker／超長列、日誌倒退／2MiB及64筆界線、不洩漏內容。來源SHA `a65846da6f3a77de38356dbd9e448e55a220288ef170a407bba52cb227e63d57`；檢查來源SHA `d78e44aed9ad1e2178068cb21a8780b97099146ec71fceab44b4a0ebadb9aebf`。初次手動csc相對路徑參數未找到來源（CS1504），改實際絕對路徑重跑才成功；正式`check-player-connection-status.py`固定使用絕對來源並保存compile／run log。這是fixture parser檢查，不是Unity、原生入場或GUI證據。

新玩家包`windows-player-0.33.0-status-v1.zip` **82,633,458 bytes**、SHA `cff0c88aeaf89262f09f3efffb263a2980f7df68e13dae7d7a81f4ccdcf2e691`，311檔＋manifest；真正複製原runtime／編譯／ZIP成功，實際解壓新C目錄並核對全部檔案。原生啟動器**19項**核對／拒絕檢查成功（增加狀態輸出需wait、大小寫重疊、包內及舊檔保留）；Python包規則6成功／1因Windows symlink權限skip，語法、Node --check及diff檢查成功。ZIP／EXE／SDK／票券／資料不提交Git。

實際external場`desktop-venue/20261031-200737-de93284a`使用自己全新API／C SSD runtime、loopback／Simulation；Node的`--launcher-status`模式完成**13項原生／控制台整合**，真正handle58435 exit0。兩個獨立玩家使用控制台實際下載的票券、原解壓包啟動，其狀態皆Waiting→Connected→Final；原生與控制台readiness一致，Begin／Pause／End、380幀世界及七統計／原admission／精確雙seal一致，正常斷線不覆蓋Final。這是同機背景程序及Chromium SwiftShader，沒有GUI啟動器按鈕／截圖、GPU或跨機證據。

另兩個自有原生玩家分別使用錯誤票券、自己的不回應UDP端點（無GameServer，不讀payload）：真正狀態Waiting→Rejected及Waiting→Unconfirmed，均未出現Connected，原兩位參與者未受影響。Unconfirmed是本次30秒未收到確認，不當作已證明網路／防火牆故障。四個原生玩家／啟動器全清理、status報告exited=true且無ticket／actor ID／raw結果；部分由測試主動停止、native exit1屬清理，不拿它當自然退出或登入失敗。external helper自身仍allAcknowledged=null、headsets=null，兩份結果由獨立檢查器核對，不以空集合偽造全部收到。

原helper handle23787真正exit0，全部自有actor terminal，cleanup／native-cleanup無錯誤。`launcher-status-runtime-validation.json`raw bytes核對新**1 runtime／14檔**C原件與F snapshot一致、前**27 runtime／599檔**原件及snapshot未變、C API／三工具159檔保持；不開保存SQLite。writer停後一次snapshot、保留原件，source／binary仍F，資料明確C SSD，不是F USB效能。原5080、帳務、登入／授權／防火牆未動，既有GUI安全性提示由使用者自行處理。

這輪交付玩家端狀態來源與實際背景原生證據，**GUI完整操作、跨機／25台、頭盔與原Linked31筆根因／修復仍未驗證**。沒有新後端／瀏覽器UI行為變更，未重跑.NET／完整瀏覽器套件或Unity。完整11項目標保持active，後續取得安全性提示人工處理後驗GUI與實際跨機；仍可接續PC多人操作、原姿態自然窗口定位，Quest／VIVE／MR及廠商硬體分開驗收。

## 2026-10-31：五個獨立世界／25程序的15分鐘任務

功能 [171dabc](https://github.com/peca12968/vr-command-center/commit/171dabcf1c835924213e87ef7dc7d6fa3bd5a19b) 已推送main、遠端SHA一致。[本次CI run41199169762](https://github.com/peca12968/vr-command-center/actions/runs/41199169762)／check124531368540為failure且steps空；fresh annotation為近期付款失敗或支出上限，job未啟動，沒有雲端測試結果。沒有改帳務或手動重跑；下列本機原生與32項Python為實際結果。

前輪為實際進展；從乾淨`2e69066`接續[五房獨立長任務](DESKTOP_INDEPENDENT_LONG.md)，補上Linked長場之外，五份獨立世界同時運行、單房Pause及各自倒數／封存的證據。**API/UI0.30、Unity0.33.0／code40／NGO29保持**；只新增Python原生檢查器／10項反例與文件，未改後端、Unity、Tracked資料、0.5／1.5秒政策或幾何規則。沒有新跑Editor／雙平台，沿用原152真正EditMode與Windows／Quest成功receipt；目前來源重算及兩receipt皆為`c98f1e1d9b6857de6fc17ea3c9d585ba41881ac528314f5e7fc0073ee5958b1f`，原Scene／prefab ID保持。

真正場`desktop-long/20261031-193917-b2f30b7d`：5個Windows server＋25 headless client，每房5人、不同mission／session／world stream／UDP port、各自900秒活動任務；Clear日／Fog日／Rain夜／Storm夜／Clear夜與各房旋轉物件分開保存。原生程序分批入場、每次新增前檢查至少2 GiB可用記憶體，所有程序job workers=2，沒有啟用pose／replication probe或注入姿態／武器。名冊Quest3欄位只是分類，實際headsets0／hosts1、來源全為Simulation、networkCapacityAccepted=false。

各房Room控制台對其他房的Begin及live watch都被後端403拒絕；原5份header確認房間、來源、900秒、stream與物件範圍。每房真正AI造成一次20損耗後停止自動攻擊，個別健康各1位80／4位100；25個原playerId／admission／room／seat跨原票券到期保持，房1於tick5792、房2–5於5880–5882再次核對，未用過期票券重入。

房1自己的Pause接受序號13、Resume14，實際停在tick2404，主觀察3.265秒；同一期間房2由2384→2445、房3由2362→2424、房4由2343→2405、房5由2322→2388，皆持續Running。完整回放35個Paused幀都屬原接受序號區間且tick不變，逐玩家姿態／健康正常；不把它們算Running人次。其他房出現Pause仍算反例，沒有以本輪有暫停測試免除所有Pause。

五個live SSE獨立讀取，來源UTC及heartbeat保持原1.5秒界線；五房各自唯一tick18000自動End，**每房5份、共25份原admission戰績全部ack**，逐玩家七統計、world stream／sequence、ledger through及combat final一致。房1through16、房2–5 through14，各combat final1；五份CSV各5列與sealed ledger核對。之後五個4倍回放並行讀取各自第1幀到精確封存尾端，全部**42,293幀／41,847 Running／209,235應核對人次**，最終packet／統計一致，明細如下。

| 房間 | 全回放幀 | Running幀 | 應核對人次 | 最大capture gap ms | 最大來源年齡秒 |
|---|---:|---:|---:|---:|---:|
| 1 | 8417 | 8320 | 41600 | 118 | 0.155906 |
| 2 | 8457 | 8385 | 41925 | 132 | 0.155804 |
| 3 | 8469 | 8386 | 41930 | 117 | 0.155610 |
| 4 | 8471 | 8379 | 41895 | 133 | 0.156270 |
| 5 | 8479 | 8377 | 41885 | 132 | 0.153763 |

每房live／replay badFrames0、badPausedFrames0、badEnvironmentFrames0，>=1500ms capture gap0、來源過期0、send queue full0。`independent-checks.json`的executionFinished／acceptancePassed／complete=true，真正原工具handle96709最終exit0，未從stage或等待逾時重啟。五場是各自保留的世界、統計與歷史，沒有合併進新Linked。

新10 Python含Pause fence／原tick、最後一位玩家失效、其他房意外Pause、環境／suspended／敵軍跨房、保存gap與512界線及獨立header反例；既有11多人及11容量解析共**32項**實際通過，語法及git diff --check成功，CI加入新unit／語法。沒有後端／UI行為變更，本輪未重跑.NET／HTTP／瀏覽器，不把前輪結果當新跑。

`independent-long-runtime-validation.json`以raw bytes核對新**1 runtime／22檔**C原件與F snapshot一致，前**26 runtime／577檔**原件及snapshot完全未變，C API與三工具159檔保持；不開保存SQLite。所有actor及父handle皆terminal，cleanup errors／remainingTrackedChildren空，writer停後才一次snapshot並保留C原件；來源及binary仍F，資料明確C SSD，不是F USB效能。工具fingerprint `40cb2d72a29d7e4bc2df222ca43e83871dbadd22b7dfc7ea6b70277012c0a2f5`與結束後來源重算一致；原5080、帳務、登入／授權及防火牆未動，GUI安全性提示仍由使用者自行處理。

這證明本輪五個獨立、靜止、同機PC世界的長任務與封存，**不證明25位持續操作、25台、跨機／Wi-Fi、GPU／FPS或頭盔容量**。原Linked的31筆失效仍未通過，未證明根因／修復；不同模式未重現不能替代自然窗口定位。完整11項長期目標保持active，下一步多玩家持續操作與跨機部署、自然姿態失效的因果證據；Quest／VIVE／MR與廠商硬體另驗。

## 2026-10-31：同源25程序未啟用診斷對照與跨場核對

功能 [a12fd01](https://github.com/peca12968/vr-command-center/commit/a12fd0180560ad966991187440b10667f5311fa3) 已推送main、遠端SHA一致。[本次CI run41197458889](https://github.com/peca12968/vr-command-center/actions/runs/41197458889)／check124526402137為failure且steps空；fresh annotation為近期付款失敗或支出上限，job未啟動，沒有雲端測試結果。沒有改帳務或手動重跑；下列本機原生及27項Python為實際結果。

從乾淨`4497e9a`接續電腦端，補上[跨場證據比較](CONTINUITY_COMPARISON.md)與同源未啟用診斷的自然長場。**API/UI0.30、Unity0.33.0／code40／NGO29保持**；本輪只新增Python比較／測試及文件，未改Unity、後端、姿態／碰撞或0.5／1.5秒政策，也未重跑Editor／雙平台。沿用原152真正EditMode與成功receipt，不把它們稱本輪重建；目前來源重算及Windows／Quest receipt皆為`c98f1e1d9b6857de6fc17ea3c9d585ba41881ac528314f5e7fc0073ee5958b1f`，原Scene／prefab ID保持。

真正未帶`--pose-continuity`長場`desktop-long/20261031-191455-4bd7c8c7`：一個Windows server＋25 headless client、五房Linked各5、固定900秒，全部Simulation／同機靜止；報告明確poseContinuity=null且沒有manifest，模式為DisabledByTool。保留同一工具handle10367直到真正exit0，不從stage／無輸出或等待逾時重啟；全部actor結束、cleanup errors及remainingTrackedChildren均空後才作離線比較。

原25個playerId／admission／room跨票券到期保持，tick5960再次核對，AI損耗後個別健康5位80／20位100。唯一tick18000自動End，25份各自結果全部ack，七統計／through38／combat final5／world8475與CSV25列逐玩家一致、精確雙seal完成。CSV SHA `7d2a262ec8611d26e598b196bb50da616ba4150c5527c8d240dd8b1a65de4cde`。完整4倍回放**8475幀／8412 Running／210300應核對玩家人次**，badFrames0、保存最大capture gap123ms、>=1500ms為0、來源UTC最大0.153497秒／過期0、send queue full0；executionFinished／acceptancePassed／complete=true。是本場連續性通過，不是25位操作、實體網路或頭盔容量通過。

新`compare-desktop-continuity.py`只讀已結束場次的JSON／CSV，核對cleanup、獨立seal／diagnostic manifest、原入場／room、全部ack、七統計、world／ledger／combat邊界及CSV SHA；依全程live／replay、來源年齡、capture gap與queue反例重新核對接受結果。拒絕受控校準、未結束或不一致證據；輸出只寫全新artifacts，保存輸入檔SHA、不開保存SQLite或讀憑證。NotRecorded表示舊報告未保存模式，不能因欄位缺少當DisabledByTool。complete只表示比較完成，不表示每場成功。

實際三場比較與同源開／關比較都exit0：舊0.32／4f1173場8400 Running／210000人次、**2幀／31筆失效仍未通過**；0.33／c98f1稀疏場8391 Running／209775人次、0失效；本輪同c98f1未啟用場8412 Running／210300人次、0失效。三場已記錄差異為sourceFingerprint及diagnosticMode；同源兩場差異為diagnosticMode。這是先後進行的觀察，未量測主機條件並未因此受控，**causalRootProven=false、networkCapacityAccepted=false**。沒有依已證明原因作行為修正，不能說原31筆根因已解或已修復；下一步仍需捕捉自然失效窗口及送出／接收／loop／CPU括號重疊證據，再作針對性修正。

新8項Python反例、既有11項多人連續性及8項稀疏解析共**27項**實際通過，語法與git diff --check成功，CI加入新unit／語法。本輪沒有.NET／UI行為變更，未把原717規則／459 HTTP／47串流／234瀏覽器或Unity結果當新跑。

`continuity-comparison-runtime-validation.json`以raw bytes核對新**1 runtime／14檔**C原件與F snapshot一致，前**25 runtime／563檔**原件及snapshot完全未變；原C API與三工具159檔保持。所有writer停止才一次snapshot，保留C原件，來源及遊戲binary仍F、資料明確C SSD，非F USB效能。長工具指紋`a6d8d68f53bec2279f0625199a41e80a63b7807477a970790d6d61d1a3402499`仍與目前來源一致；原5080服務、帳務、登入／授權／防火牆未動，GUI安全性提示仍由使用者自行處理。

完整11項長期目標保持active。自然失效定位、多玩家持續操作、五獨立房長任務、跨機／25台、Quest／VIVE／MR及廠商硬體各自保留待驗收，不用同機靜止乾淨場取代完整交付。

## 2026-10-31：長任務稀疏收發／主執行緒診斷

功能 [6018e88](https://github.com/peca12968/vr-command-center/commit/6018e882c7262b03fdb6312b9465842484552363) 已推送main且遠端SHA一致。[本次CI run41195892102](https://github.com/peca12968/vr-command-center/actions/runs/41195892102)／check124521846878為failure、steps空，fresh annotation仍為近期付款失敗或支出上限，job未啟動；沒有雲端測試結果，未更改帳務或手動重跑。本機實際測試與未解限制如下。

前輪為實際進展；從乾淨`223613b`接續[POSE_CONTINUITY](POSE_CONTINUITY.md)，補上原240秒逐事件工具不能涵蓋第12分鐘失效的缺口。**Unity0.33.0／code40／NGO29，API/UI0.30保持**。新Windows Development opt-in獨立為1200秒／256聚合streams／各4096稀疏gap、body轉換及主執行緒窗口，超界保留最早證據並判不完整；舊pose32768列／240秒及replication240秒保持且與舊pose模式互斥。一般／Editor／Android不安裝，不修改世界、DB、命中規則0.8.0、Tracked資料或原0.5／1.5秒政策。

沿用原RPC前PoseSend、入口Receive／accepted／rejected／throttled與journal／capture／publish量測點，正常事件僅聚合，間隔／量測>200ms才留兩端，body只記轉換與接受姿態年齡；沒有位置、玩家姓名、key／ticket、UDP payload、GPU／PCM／OS畫面。只有server附加既有PlayerLoop邊界，client不裝loop。ManagementApply約0.5秒輪詢也會產生稀疏gap，不把總筆數稱姿態異常。

Install與本收集器Update只查自己的呼叫執行緒GetThreadTimes／QueryThreadCycleTime，用pseudo handle、不列舉／開啟其他thread、不讀memory／stack、不改優先級／OS。保存thread ID／creation FILETIME、kernel／user100ns及cycles、查詢前後UTC／單調括號；僅留>200ms Update-to-Update窗口，另計總samples。CPU值屬整個sample括號，不是engine node內CPU；cycles不轉秒，量化或零值不證明全程停住。數值／身份倒退拒絕，clock step達50ms不做跨程序join。

真正Editor Prepare、**152 EditMode**成功（新增8項聚合／上限／反例／snapshot／模式互斥、64位JSON及真正Windows呼叫thread API）；Windows receipt `2026-10-31T10:29:14.1866454Z`、Quest ARM64 IL2CPP receipt `10:39:20.8575012Z`同源成功，fingerprint `c98f1e1d9b6857de6fc17ea3c9d585ba41881ac528314f5e7fc0073ee5958b1f`與目前重算一致。原Scene `4314adcd8c63d86469d16497127d8cfb／1444571642`及prefab `6f3f36cb9d710e847b5ecc569665e1ce／5227825248646244841`保持，沒有RebuildArena。aapt確認0.33／40、min32／target35／arm64；實際APK60,264,566 bytes、SHA `fc0054d7b6a8bb3d87a82ea8c53ea705d8fd7430466f8cea8274e65571d5fd72`，libil2cpp81,864,328／metadata9,269,280 bytes且含新型別。BuildReport總輸出不當APK大小，仍無頭盔運行。

首次Quest確實失敗，log為Bee／PlayerScriptAssemblies存取UnauthorizedAccessException，exit1與原log保留；不因開頭token warning否定已成功Editor／Desktop授權或要求重新登入。沒有改Library cache／ACL／安全設定，後續真正重試exit0才採為成功；未證明初次檔案存取根因。官方293檔Transport單一修補與原字型pin核對成功，實際匯入的兩個新.meta及版本設定保存。

短校準第一場`desktop-long/20261031-183241-43db1261`完成受控1.2秒單一上行丟棄與恢復，但解析器把JsonUtility產生的未啟用loop初始化空物件誤判已宣告，父工具exit1。原raw／cleanup／封存保留，不補寫成passed。只接受精確空形狀、非空仍拒絕後，第二場`183431-27f2f323`真正重跑exit0：server主玩家PoseReceive gap **1.2776636秒**、body接受姿態年齡約0.5999984秒，sender無>200ms呼叫gap、peer仍有效、同admission恢復，原七統計／兩份結果／雙seal一致。轉送原UDP bytes、不讀payload，不注入姿態或武器；是已知受控原因的校準，不是自然31筆失效的根因證明。收集先停止／移除自己的marker再寫報告，輸出安排在End與全部ack後，與任務內觀察分開。

新版未帶診斷的一般原生入場`unity-admission/20261031-184149-3d3b0b53` **8項、377幀**成功，含撤銷／原程序重連／已接受健康與彈藥保持／Ended拒絕及回放統計。此工具使用自己的F資料，非下方C SSD配置或頭盔，真正handle exit0、沒有GUI／鍵鼠操作。新8 Python解析反例、原11多人連續性及語法通過，JSON clock／role／counter／aggregate fence不以資料缺少當成功；CI加入unit／語法，不稱雲端執行原生。

自然長場`desktop-long/20261031-184355-3b466dac`一server＋25 headless client、五房Linked各5，全部明確啟用新模式，僅server loop。固定900秒、原入場跨票券到期、AI每房一次20損耗後固定5位80／20位100、唯一tick18000、**25份個別ack及CSV／through38／combat final5／world8449精確雙seal一致**。完整4倍回放8449幀／8391 Running、209775應核對人次，badFrames0、保存最大gap114ms、source UTC最大0.220263秒／過期0、send queue full0；工具真正exit0、acceptancePassed及complete=true。是本場靜止Simulation的連續性通過，不是25位操作、物理網路、VIVE／Quest或容量完成。

26份報告皆完整／未截斷、時鐘可對齊；client最短901.9851532秒／至少81157次main-thread samples、server907.3074891秒／81632 samples。任務Running窗口內無body loss、PoseSend／Receive>200ms gap、主執行緒>200ms窗口或PlayerLoop>100ms空窗；server一筆loop空窗在啟動期，不當作任務內根因。server原1769筆稀疏gap主要為正常ManagementApply，沒有把它們當資料遺失。`pose-continuity-analysis.json` complete=true、missionAcceptancePassed=true、**causalRootProven=false**；沒有窗口不能說CPU／frame delta為0。新工具指紋 `a6d8d68f53bec2279f0625199a41e80a63b7807477a970790d6d61d1a3402499`在結束後與目前helpers／analyzer重算相同。

此場與原0.32未啟用的31筆反例條件不同，而且沒有針對已證明原因作行為修正；**沒有宣稱根因已解或修復**。原6931／6932幀13／18位及497ms窗口、完整raw與接受失敗保持不變。後續仍需自然失效窗口與未啟用對照、送出／接收／loop／CPU括號重疊分析，不能用乾淨一次或此校準取代原問題。

`continuity-runtime-validation.json`raw bytes核對新**3 runtime／106檔**C原件與F snapshot一致，前**22 runtime／457檔**未變，原C API／三工具159檔保持。保存SQLite完全不開連線；所有真正actor／fixture handles已terminal，cleanup errors／remainingTrackedChildren空。writer全停才一次snapshot、保留C原件，源碼與遊戲binary仍F，資料明確C SSD，非F USB效能。原5080 API、登入／授權／防火牆未動，GUI安全性提示仍待使用者自行處理，沒有自動操作。

另產生`windows-player-0.33.0.zip` **82,630,594 bytes**、SHA `d54bc0e97b5be90686a70e92e25169b507bafcd96af4dd874276cbfa6c38ca9c`，311檔＋manifest；正常啟動器來源`127a39d1d11a856070e6676ab566c4f4862e8e5ac168e2ed4d9a4a9b4660ab45`不變。已實際解壓C、Python與真正Launch-Player.exe --verify成功；本輪沒有重新完成GUI選檔或ZIP玩家入場流程，不把舊0.32 GUI未完成改成成功。APK／ZIP／SDK／憑證／DB／journal及artifacts不提交。

完整11項保持active。下一步使用此有界診斷取得自然失效與未啟用對照、再依因果證據修正；多玩家持續操作、五獨立房長任務、跨機／25台、Quest／VIVE／MR與廠商硬體分別驗收。

## 2026-10-31：25個PC原生程序的15分鐘Linked反例

功能／反例提交 [3ff94cf](https://github.com/peca12968/vr-command-center/commit/3ff94cfcefdee18b484fe53ba18eb8f66fa8ae9b) 已推送main、遠端SHA一致。[本次CI run41192014101](https://github.com/peca12968/vr-command-center/actions/runs/41192014101)／check124510546996為failure、steps空；fresh annotation仍為近期付款失敗或支出上限，job未啟動，沒有雲端測試結果。未改帳務／手動重跑；這與本機900秒檢查確實執行後因body失效exit1是兩件事。

前輪為實際進展；從乾淨`afc2b21`新增[DESKTOP_MULTIPLAYER_LONG](DESKTOP_MULTIPLAYER_LONG.md)及可重跑工具，將原單玩家900秒與25端短測之間的缺口接上。本輪**API/UI0.30、Unity0.32／code39／NGO29保持**，未修改Unity／規則、未重建或新跑144 Editor／雙平台；沿用原Windows receipt及source fingerprint `4f1173e9eac5aa82e0b37fa58ba73afa64c392b750218b790c85c08638c3b852`，原Scene／prefab ID保持。未以新Python檢查代替Unity或頭盔證據。

真正場`desktop-long/20261031-175042-1ad7c3c8`：一個Windows server、25個headless client、自己的新API／角色憑證及C SSD runtime，五房Linked各5席，按5個一批正常入場；不注入姿態、武器或統計，不附掛240秒replication probe或延長其界線。Source全為Simulation、headsets0／hosts1／networkCapacityAccepted=false；名冊Quest3分類不是設備。25個原生程序持續900秒活動任務，唯一自動End為tick18000。

真正AI在每房造成一次非零損耗，操作員關自動攻擊並於policy sequence36後固定個別健康：5位80、20位100。原票券全部於`09:55:48Z`到期後，`09:55:48.029474Z`／tick5954再次核對全部playerId／admission／room／seat保持，整段每client僅一次本地connected。這驗既有連線延續，不以過期票券重入，也不是25位持續移動／交火。

最終**25份各自current admission戰績全部ack、timedOut空**，七統計欄、world stream／sequence8463、combat finalStreamSequence5與ledger through38一致；CSV25列逐玩家核對，SHA `7318eeab778af2ca47ab22f99fbbdb809cc47f8942ccb9bc08952a270d584e8c`。combat／world雙seal完成，完整4倍速回放從1至8463，8400個Running幀、**210000應核對玩家人次**、最後完整packet與封存統計一致。這些完成項目不代表連續性接受。

**本輪連續性未通過：executionFinished=true、acceptancePassed=false、complete=false，真正工具handle exit1**。live8394幀（Running8393、跳1個live sequence）及完整replay都找到2個相同失效幀，reasonCounts inactiveBody31、18位不同玩家受影響。世界sequence6931／tick14701有13位，6932／tick14703有18位；6933／tick14706全部恢復。全量計數不因反例取樣上限200而丟失，正常Ended退場另排除；未用最後恢復、25份結果一致或少數正常檢查點宣稱全程成功。

封存後以同次授權API另讀6928–6935的原保存packet，另存`multiplayer-fault-window.json`，沒有開保存SQLite或注入／重寫資料。6929→6930的擷取elapsed gap **497ms**、tick14694→14695；之後6931為103ms／+6 tick、6932為100ms／+2、6933為106ms／+3並恢復。失效涵蓋五房及五席，policy36、Running、suspended=false與健康80／100保持。完整保存最大gap497ms、達1500ms的gap0；source UTC live最大年齡0.214368秒、badSamples0，原生日誌send queue full0。這證明僅查1.5秒來源新鮮度或擷取間隔會漏掉body失效；沒有收集此輪內部pose trace／主執行緒或packet時間，因此不能據此斷言GC、OS排程、傳輸、來源I/O或時鐘根因。原0.5秒姿態／1.5秒來源政策均未放寬，既有偶發問題沒有宣稱修復。

新工具指紋 `07a0032e658e476cfba8ae659f60d5d634c09c9830d3d8e10f9a7779c123097d`在cleanup後重算，與實際跑的helper／來源相同。**11新Python**通過，涵蓋最後玩家、錯房／健康／rig、缺少／重複／外來名冊、原admission／席位fence、意外Pause、live跳序與replay不得跳序、原1500ms界線及全量反例計數。新增原生反例形狀的497ms＋13／18失效＋恢復測試，第一位保持健康仍必須判fail，31筆不因恢復而消失；另原single3／capacity11共14項與新語法通過。CI僅加入unit及Python語法，沒有把Linux CI當900秒Windows流程。

`multiplayer-long-validation.json`raw-byte核對本輪**14檔**C原件與F snapshot SHA相同，前**21 runtime／443檔**未變、原C API及三工具159檔仍匹配舊SHA。保存SQLite不開連線；真正tool terminal後核對cleanup errors／remainingTrackedChildren空、沒有剩餘VrCommand程序。所有writer停後才一次snapshot、保留C原件與全部反例；raw audit complete=true是檔案審核完成，不會將acceptancePassed=false改為成功。資料明確C SSD，source及Unity binary仍F，不是F USB效能／跨機證據；5080舊API、登入／授權／安全設定未變，憑證／DB／journal／binary不提交。

完整11項保持active，GUI安全性提示仍待使用者自行處理。本輪已把25端較長任務的失效窗口縮到可重查的原始幀；下一步針對接近0.5秒的窗口收集送出／接收與主迴圈工作證據，再修復並重跑，不能拿降低人數或短測當25端解決。25位操作／5獨立房長任務、跨機、Quest／VIVE／MR與廠商硬體仍另驗。

## 2026-10-31：Windows可攜玩家包與繁中啟動器

功能 [2459725](https://github.com/peca12968/vr-command-center/commit/245972594d9898cde672aab63c25228c5c5b59d9) 已推送main且遠端SHA一致。[本次CI run41189792380](https://github.com/peca12968/vr-command-center/actions/runs/41189792380)／check124504023904為failure、steps空；fresh annotation仍為近期帳戶付款失敗或支出上限，job未啟動。沒有雲端測試結果，未改帳務或手動重跑；本機證據與GUI待驗限制如下。

前輪為實際進展；由乾淨`9c8cd02`接續新增[WINDOWS_PLAYER_PACKAGE](WINDOWS_PLAYER_PACKAGE.md)，補上外部PC不便手動輸入命令的部署缺口。玩家完整解壓後開啟Launch-Player.exe、選擇控制台下載的個別玩家檔並開始。封裝及獨立WinForms啟動器v1，**API/UI0.30、Unity0.32／code39／NGO29保持**，沒有修改Unity來源、重新Prepare或重跑144 Editor／同源雙平台；這些仍是前輪成功receipt，不當作本輪新測試。

封裝器要求真正Windows receipt、原輸出路徑與目前source fingerprint，使用.NET Framework系統compiler產生x64啟動器，/warnaserror編譯成功。玩家端不需Python、Editor或.NET10 SDK，仍需Windows x64／Framework4.8與適用驅動。只收原runtime允許目錄與檔案，DoNotShip debug不收；root其他config不包入，runtime內未知JSON／key／journal／DB／log則拒絕。原receipt與Transport／模板／字型通知保留，不讀正式憑證或歷史任務。

啟動器先限制四欄Client／canonical unicast IPv4／port1024–65535，再核對包內每檔長度與SHA；不顯示或寫出ticket內容，以不經shell的Process.Start及Windows參數引號啟動自己的Unity程式。格式檢查不驗票券簽章、效期或admission，仍由原GameServer驗證。診斷log／report只接受包外新路徑，一般雙擊不需要診斷參數；關閉啟動器不End或關閉已啟動遊戲。雜湊清單不是數位簽章、發行者信任或網路探測。

最終`artifacts/player-packages/windows-player-v3.zip` **82,625,103 bytes**、SHA256 `f477e8ebe196738330013a2cefdae27fc366f617d925395b627cd6703f8807d9`；311個runtime／啟動器／通知檔，另1個manifest，共312檔。launcher source SHA `127a39d1d11a856070e6676ab566c4f4862e8e5ac168e2ed4d9a4a9b4660ab45`，原遊戲source fingerprint仍`4f1173e9eac5aa82e0b37fa58ba73afa64c392b750218b790c85c08638c3b852`，Scene／prefab ID及原receipt保持。真正解壓至C自有`portable 玩家 & v3/VRCommand-Player`，ZIP checksum／全部312檔與解壓檔逐一SHA相同，執行後再核對一致。

**15項真正編譯啟動器檢查**於`player-package-checks/20261031-173359-b97c5a46`通過：完整包、拒Server／Host／管理key／缺或空ticket、URL／縮寫／wildcard／multicast／bool或超界port、過大輸入、缺runtime及越界manifest，不產生玩家PID、不回顯fixture secret。另7項Python中**6通過、1 Windows symlink權限不足明確skip**，不稱7項全過；涵蓋receipt、DoNotShip／root config、runtime私有資料拒絕、hash／缺檔、路徑與大小寫重複。Python語法及Node driver語法通過，CI加入跨平台unit與語法；沒有改後端或控制台來源，不重述前輪717／459／47／67／234為本輪重跑。

最終背景場`desktop-venue/20261031-173702-c7be6c84` **9項完整通過且檢查器exit0**：原真正API／控制台UI建任務與名冊、來源公布及實際loopback UDP，兩份實際UI下載檔含空白／繁中／&的路徑，分別透過解壓包的真Launch-Player.exe開兩個Unity client，正常原票券／admission入場；Begin／Pause／End與Simulation來源保持。78世界幀精確seal、through8／finalStream0，兩位各自己的current admission；七統計欄位逐一等於sealed ledger，耗彈／命中／擊殺／中彈／損耗0、健康100。未注入姿態、射擊或統計。

最終tool fingerprint `8e4ddbea48c9c3ff9d1787fbbbca42c4fc77b2a003b964387110870894c2b23f`與當前helper／venue／driver／packager／launcher來源重算相同。native-cleanup兩份nativeGone=true、errors空；測試主動關閉自己Unity，兩個launcher轉傳exit1是測試關閉結果，不是遊戲自然exit0。helper真正handle exit0、36秒結果保留與雙seal後完成，allAcknowledged／headsets仍null，不能用本測試知道的兩個PC改成全體送達或設備證明。Chromium為SwiftShader、兩端headless，沒有本輪GPU／PCM／原生戰鬥輸入或跨機證據。

未完成輪次全部保留：`172855-7fb29031`只過前三步，測試spawn誤用windowsHide將互動啟動器藏起；確認自有parent／child後停止自己的driver與launcher、End並保存空戰鬥世界，非通過。`173050-78ddc807`在v2真正繁中GUI顯示下載檔，以computer-use實際按開始並成功雙PC入場、416幀及九項工作流程核對，但cleanup把signalCode=SIGTERM／exitCode=null誤當仍活著，15秒後失敗。原先過早寫出的checks.json complete保留，**不能用它聲稱整場成功**；自己第二位native／driver經確認後停止、helper精確封存且exit0。新driver以exitCode或signalCode判terminal、逐一cleanup／關browser／End，先寫workflowComplete且cleanupPending的檔案，全部cleanup成功才寫最終checks.json；最終背景場已驗。

GUI檢視亦發現WinForms檔名Label將&當助記符，v3設定UseMnemonic=false並重新封裝。`173413-5efdc8c1`的最終v3互動重跑因Windows防火牆提示遮住啟動器，已請使用者自行決定關閉，未代按安全性提示。等待240秒後檢查器按原期限失敗，沒有啟動該玩家、沒有complete checks；自己的GUI以SIGTERM收尾、native-cleanup成功、helper也精確封存及exit0。GUI選檔dialog曾開啟，但computer-use對焦點／set_value回報不一致，未把未完成輸入稱成功；最後完整選檔互動及安全性提示後回歸仍待。v2的按鈕成功不替代最終v3完整GUI驗收。

`player-package-validation.json`用raw bytes核對本輪**4 runtime／56檔**C原件與F snapshot一致，前**17 runtime／387檔**未變，既有C API／三工具159檔與前輪SHA相同；保存SQLite完全不開連線。全部writer停後由helper一次snapshot、保留C原件，四個helper真正handle均exit0，cleanup errors／remainingTrackedChildren空；未改5080舊API、登入／授權／OS或防火牆設定。原件、未完成與成功紀錄都保留，DB／journal／ticket／binary／ZIP不提交Git。source／Unity binary原件仍F，本輪玩家使用C解壓副本、runtime亦C SSD，不稱F USB效能或另一台PC成功。

完整11項保持active，仍優先電腦端。接續多玩家持續操作、實際場館／跨機部署，以及使用者處理提示後的GUI選檔／重連流程；Quest／VIVE／MR、廠商硬體及25台分別驗收。

## 2026-10-31：來源連線公告、只開伺服器與下載檔玩家入場

功能提交 [b699ccd](https://github.com/peca12968/vr-command-center/commit/b699ccdb5009d9d5ad46f9b3d50320335b2e07e7) 已推送main並核對遠端相同。[本次CI run41188116962](https://github.com/peca12968/vr-command-center/actions/runs/41188116962)／check124499094625為failure、steps空；fresh annotation確認因近期帳戶付款失敗或支出上限，job未啟動，沒有雲端測試結果。未更改帳務或手動重跑，本機各項成功證據如下；完整目標仍active。

前輪屬實際進展；從乾淨`f2c278c`接續[EXTERNAL_CLIENTS](EXTERNAL_CLIENTS.md)。**API／UI0.30、Unity0.32.0／code39／NGO29**。修補操作員流程缺口：原本local工具會替所有名冊自動開PC client，外部玩家可能撞同一admission；新增external只開server、不領玩家票券／不占用入場。local維持預設，兩種模式分開記錄，不以外部未知設備填0或虛構ack。

來源在world header存在後，用同server的GameServer身分公告所選IPv4與該場配置port。新GET／PUT connection-endpoint v1逐次傳Actor，限owner寫、Master／可讀Room讀，GameServer／Internal不能當控制台讀取捷徑；綁session／stream／完整owner，接受後不可換址或port。原內容重試保留createdAt，房間重用不繼承；Ended公告僅metadata，不開場或授權配票。worlds.db新增connection_endpoints，world schema1／envelope7、原header／checksum、rules0.8.0與素材pin不改；不將公告當連通性或裝置證明。

控制台從相符stream採用空白的地址／port，保留人工修改、提供明確套用，切場／登出清草稿並fence晚回應。下載仍只有role／address／port／joinTicket，沒有Master／GameServer key。external必須明確提供advertise-address，預設listen0.0.0.0；local預設127.0.0.1。v1只canonical dotted IPv4 unicast／1024–65535，未支援DNS／IPv6／NAT／中繼。管理API仍loopback，沒有改OS／防火牆／安全設定。

發現Unity原程式不論config.address都硬寫監聽0.0.0.0；現新增server listenAddress並真正傳入UTP第三參數。缺失／空值保留原Any，提供值才驗canonical IPv4；新managed工具明確寫loopback。**144真正EditMode成功**，新增3項舊JSON預設、真UnityTransport分開advertise／listen及錯誤地址反例。Prepare重用原ID，沒有更動NGO wire、追蹤資料、碰撞、槍口、AI或命中規則。

真正Windows receipt `2026-10-31T08:42:39.7814594Z`、Quest ARM64 IL2CPP receipt `2026-10-31T08:51:27.5208986Z`成功，同一fingerprint `4f1173e9eac5aa82e0b37fa58ba73afa64c392b750218b790c85c08638c3b852`且與目前來源重算一致。原Scene `4314adcd8c63d86469d16497127d8cfb／1444571642`、prefab `6f3f36cb9d710e847b5ecc569665e1ce／5227825248646244841`保持。aapt確認0.32.0／39、min32／target35／arm64；實際APK60,187,786 bytes、libil2cpp81,608,584／metadata9,264,400 bytes，含新getter與欄位，見external-build-validation。BuildReport總輸出不當APK大小，仍無頭盔運行。

本機locked restore／隔離Release零警告錯誤，**717規則／459 HTTP／47世界串流、67 Node／234 Chromium**通過；新增19規則、6 HTTP狀態／4世界斷言、3 Node規則與5 UI反例。普通UI fixture只證顯示／保留草稿／跨場／登出；實際來源整合另述。6新external Python＋原17 desktop共23項、語法及293官方Transport單一修補核對成功，CI加入新Python及語法。

兩場真正server-only工具＋兩個另由測試程序啟動的Windows client，各**8項**完整成功：desktop-venue／`20261031-165613-bbc86e3f`（77幀，tool `b2da89ab808ff3faf802eea1bb2a082f25d7c136643dd9f024de986dffeafb8b`）與最終`170638-b2feb08f`（78幀，tool `47fc863ca2c70b15d5a380ba3b002e4fc13189d2d3ff6d98de173e41aafaa1c9`）。實際UI建任務／名冊，來源公告並自動填實際port；netstat只保存對應server PID／port，確認真正UDP綁127.0.0.1，最終PID58040／port58016。兩個名冊先保持未就緒、沒有工具自動client；再用真正UI下載的四欄短票券設定啟動兩個獨立PC程序，admission／seat驗證與正常姿態入場成功。

UI Begin／Pause／End接到真正世界，來源明確Simulation。兩位各收到自己的current admission結果，耗彈／命中／擊殺／中彈／損耗0、健康100；stream／through8／world77或78及全部統計等於精確seal並ack，另raw核對finalStreamSequence皆0。helper本身仍保留allAcknowledged=null／headsets=null，不把本檢查器知道的兩個PC外推所有外部裝置或空集合成功。server非阻塞保留至少36秒，原始30秒＋最多5秒HTTP期限不改；不是送達保證、四小時或崩潰恢復。

原local模式`165936-476c7855` **49項控制台／native回歸**通過，包含任務／配置、動態名冊、AI、觀戰／回放姿態及CSV，126幀精確seal。三場均無新的原生GPU／PCM／鍵盤觀察，Chromium為SwiftShader；只是同機分開程序／loopback，不是LAN、跨機、Quest／VIVE或25台驗收。已檢視來源公告、有效玩家與結束的控制台截圖，沒有把headset分類當實機。

保留前端反例：回應與場次都缺stream時，舊比較會把undefined等同；新增負例先失敗，補非空string fence後3 Node及最後完整67／234再次通過，並重跑最終8項原生下載流程。另將下載提示改稱玩家端、external啟動提示改正；早期C stage保留，不在執行中替換其靜態資產。三個stage只差提示／fence對應JS、gzip與static-web-assets metadata，所有DLL相同；並未放寬來源、入場或測試時限來通過。

`external-runtime-validation.json`核對**3個runtime／42檔**C原件與F snapshot逐檔SHA相同，前14個runtime／345檔亦未變；保存SQLite不開連線。全部writer停後一次snapshot、保留C原件，cleanup errors／tracked child空、測試玩家程序0。最終C API及三工具**159檔**與F輸出逐檔相同；source／遊戲binary仍F、DB／journal明確C SSD，不當F USB效能證據。原5080仍0.16，未動登入／授權／安全設定，憑證／DB／journal／binary不提交。

完整11項保持active。下一步多玩家持續操作、場館流程與實際跨機，再取得Quest／VIVE／MR／廠商硬體與25台驗收；本輪不以server-only模式或APK成功替代實機證據。

## 2026-10-31：名冊旁的玩家參戰快照

前輪有實際功能與驗證進展；從乾淨`01086d7`接續新增[PLAYER_READINESS](PLAYER_READINESS.md)。**API／UI0.29**，操作員可在名冊旁直接查看有效姿態數、等待來源／中斷／過期與本次入場同步，明確標示Simulation及合成／追蹤資料。這是已接受世界幀的觀察，不是裝置在線、型號、戴好頭盔或MR／安全校正證明；沒有加Begin條件、修改射擊授權、Tracked資料、rules0.8.0或DB格式。

新增GET readiness v1端點只限Master及可讀場次的RoomController，每次顯式Actor／範圍檢查，GameServer／Internal也拒絕。只回本次名冊的狀態／admission／room／seat及來源邊界，不含姿態座標、票券或管理key。WorldRecordings用最後已接受幀的observedSequence還原當時名冊，再對照本次管理快照；相同playerId的新admission不能繼承舊frame的connected。每份報告受其sessionSequence與抽樣時點限制，不授權戰鬥。

來源時間仍header擷取UTC＋packet.elapsed，而非收到時間；未知、超前1000ms以外、過期1500ms、suspended、階段未同步或Ended皆不綠色。前端約1Hz診斷、250ms本地老化更新，從請求開始計performance經過時間，包含下載等待；登入／選擇epoch、報告序號及admission fence阻擋晚回應。沒有走REST傳逐幀頭手，沒有修改原0.5／1.5秒政策。暫停仍能有有效姿態，與場次已暫停並列，不當作正在戰鬥。

**698規則檢查**成功，新增18項含真正SQLite／歷史投影、角色／範圍、header不等於frame、source時間雙邊界、舊admission、phase／suspended／End、legacy未知時間與唯讀性。本機locked restore及隔離Release零警告錯誤，**453 HTTP／43世界串流、64 Node／229 Chromium**通過。新增7個HTTP斷言、4個Node規則及6個UI反例；UI中mock的資料明確只驗顯示／時序，不當原生證據。已檢視過期、等待及實際原生資料的控制台截圖，仍為Chromium SwiftShader。

使用同版真正Windows server／兩個headless client、全新自有API／資料／憑證，`desktop-readiness/20261031-161305-e18fecc5` **8個原生＋8個實際API資料UI檢查**通過。tool fingerprint `a474ffcd9a887bdd37919b54907415b2e3c14913eb84277e1de94a49c5e805f2`。啟動前兩個名冊body均PoseUnavailable；兩個真正程序正常送姿態後2份有效。工具只關閉自己的peer程序，該玩家變PoseUnavailable、primary仍有效；同playerId移除／重入後，frame233仍新鮮但新admission為AwaitingAdmission／None／false，不能沿用舊身體。新票券啟動新程序後，frame244兩端皆Simulated且有效。

真正瀏覽器讀未mock的readiness並完成Begin／Pause／End，End後無綠色；兩份結果均為自己原current admission，耗彈／命中／擊殺／受傷0、健康100，combat與world精確seal、pending=false、through10／world287及全部統計等於ledger並ack。這是離散觀察與兩位同機Simulation，不是每render幀／RTT／25人容量，也沒有注入姿態、射擊RPC或統計；本輪沒有GPU／PCM／原生鍵盤／頭盔觀察。

失敗保留：第一個.NET新增fixture把合成雙手留在世界原點，正常世界驗證拒絕Invalid recorded player or tracked rig；只修fixture相對身體位置，未放寬驗證。原生首場`161031-39d9192f`前六步成功，但測試瀏覽器預設dismiss既有End確認，任務仍Paused，UI20秒／工具60秒逾時；已補只對該End接受確認及顯示Ended紀錄後，重新整場成功。首次啟動browser時ready pointer尚未建立，未重開仍活著的native程序，等同一handle出現native-ready後才接上。失敗原件／cleanup／精確seal保留，不改成passed。

`readiness-runtime-validation.json`核對本輪**2個runtime／28檔**C原件與F snapshot逐檔SHA相同，前12個runtime／317檔亦未變；保存SQLite不開連線。所有writer停後才一次snapshot，C原件保留，cleanup errors／tracked child空且測試玩家程序0。新的C API及三工具副本**157檔**與F隔離輸出一致；早期stage保留，最終只有index頁尾及其gzip／兩份static-web-assets metadata四檔不同，gzip分別還原為各自HTML、其餘檔及DLL相同。不是修改舊部署來冒充新證據；資料明確C SSD，遊戲source／binary仍F，原5080仍0.16，未動登入／授權／安全設定。

**遊戲保持Unity0.31.0／code38／NGO29**，本輪未修改Unity來源／wire或重建141 Editor／雙平台。重新計算來源仍 `213b9b04e02d506c73110ba6df23109fc5ce3f14bf8f233b9d803ef8dde4777c`，原Windows／Quest receipt與Scene／prefab ID保持；不能把前輪建置當本輪新的頭盔結果。API/UI一起部署0.29，原生工具gate同步；17個既有desktop Python、語法與293官方Transport單一修補核對亦通過。

完整11項目標保持active，後續持續多玩家操作、完整場館與跨機流程；25端最大長文／並行操作、實體Quest／VIVE、MR、廠商硬體與25台仍待驗收。

功能提交 `fbb9818e30318c50fb4a835a7b65df611150d1a1` 已推送main、遠端一致。[本功能CI run41184537724](https://github.com/peca12968/vr-command-center/actions/runs/41184537724)／check124488624265實際failure、steps空；fresh annotation明示付款失敗或支出上限，job未啟動，沒有雲端測試執行／通過。未更改帳務或手動重跑，本輪上述均為本機證據。

## 2026-10-31：繁中玩家任務簡報與原生輸入

從乾淨`5d4ac95`接續，新增[PLAYER_BRIEFING](PLAYER_BRIEFING.md)。原任務庫保存的名稱／內容，現在由GameServer送至玩家閱讀；不是另建一份任務。遊戲端**0.31.0／Android code38／NGO29**，API/UI保持0.28，envelope7／world schema1／驗票2／rules0.8.0及原素材profile不改。所有遊戲程序一起更新，Prepare原位保存Scene／PlayerAvatar ID，不重建歷史。

名稱100／內容10000 UTF-16單位、最多80個FixedString512塊，不切有效surrogate pair；header1保存完整長度／塊數／SHA，缺塊、內容異動或未知版本不能成為可讀簡報。20個code point一行、10行一頁，純文字標籤原樣保留。管理更新及晚連線不重設同一頁；本地頁碼／開關沒有新增world錄影欄位，不補造舊閱讀過程。

PC用B開啟／下一頁、Escape關閉、L授權，另有面板按鈕；Quest來源使用左X／Y／握柄，實體操作仍待。閱讀只抑制自己的射擊／換彈，關閉後須放開再按；姿態繼續、全場不暫停、仍可能受傷，End戰績接管。Tracked頭手與muzzle不改，XR只新增頭部前0.9m的Canvas。不是防作弊政策或無敵模式，沒有修改碰撞、AI或命中規則。

隨附官方未修改Noto Sans CJK TC Regular2.004，commit `f8d157532fbfaeda587e826d4cd5b21a49186f7c`、OTF16,435,884 bytes；SIL OFL1.1及NOTICE隨包並可在面板閱讀，不依賴OS字型。mission-fonts-v1三份固定SHA／真正OTF cmap檢查通過，OTF／TXT與meta納入來源指紋；改版需新profile，不可重寫舊pin。不是任意emoji／罕見字涵蓋或頭盔閱讀舒適度驗收。

**真正141 EditMode通過**，新增10項涵蓋完整長文／surrogate、部分與錯誤摘要、真正NGO序列化、純文字分頁、重複管理不重設頁、按住射擊須放開、Tracked頭部不搬動、真字型／授權載入與Unity JSON內容。最後不透明底板版再次141成功；Tests門檻與UI直接asmdef參考同步更新。Unity既有nullable／audio／ServerRpc warnings保留，沒有把managed SDK當本次Editor結果。

原生`check-desktop-briefing.py`本輪同一tool fingerprint `5628896249eda2a3f81c863388a7ba069b128d3d8aaf7f05ea37acbfe439d092`，一個server及兩個client，其中第二位在Running後晚連線。Preparing先收到真正10000字、79塊；三程序完整摘要均為 `64dfb429551b908a3000927c91c6f0416b5dd9e602317b387a3be9b700c45216`，頁數51，不截斷文字來通過。

`desktop-briefing/20261031-154143-b0890b35`先完整8項通過，但原生觀察發現底板半透明、後方HUD透出。改為不透明底板、重建Windows及再次141後，最終`20261031-154501-4648aef5`重新**8項**完整通過：真正B開啟繁中第一頁及literal `<b>`、Space被抑制、B第二頁、Escape後仍30／90、下一次Space變29／90；B／L可讀官方字型來源與授權。沒有注入姿態／射擊RPC／統計。UI helper一次active-request錯誤後先重新觀察，未誤標已按鍵。

最終穩定雙玩家閱讀區間，server changed-tick診斷**405列、失效0**，兩個身體connected／ready／coherent且tick持續。此為有界取樣，不是每render幀／網路RTT或完整25人容量。主玩家耗彈1、晚連線者0，兩者健康100、命中／擊殺／受傷0，各自原admission的final／stream／combat及world最終序號與ledger一致並ack；雙精確seal、world sequence758，保存任務原文不變。probe仍240秒／64captures，普通啟動不附掛。

首次`20261031-153913-dcd7167c`等待原生按鍵時逾時，失敗run保留，不當成功。兩個成功run及失敗run共**3個runtime／88檔**原件與F snapshot逐檔SHA一致；之前9個runtime／229檔亦未變，見`briefing-runtime-validation.json`。全停writer才一次snapshot且保留C原件，僅讀JSON／logs／raw bytes、沒有在保存SQLite開連線；cleanup errors空／tracked child空，測試玩家程序0。原5080仍0.16，未替換正式DLL／資料、未操作登入或安全設定。

本機.NET locked restore／Release零警告錯誤、**680規則／446 HTTP／43世界串流**通過，另17個既有desktop Python、字型pin／cmap、語法與293官方Transport單一修補核對成功。web UI沒有修改，本輪未重跑Node／Chromium，不把先前瀏覽器數量當新結果。

兩次從F隔離輸出的HTTP檢查先失敗：競爭writer程序及invalid-key程序各未在原10秒內退出，第一個診斷還被cp950的Unicode輸出遮住；UTF-8重試仍保留逾時。未放寬timeout／認證／安全設定。把本次API及三工具輸出的原樣副本放到全新C BuildRuns後，以相同檢查通過446／43；155檔與F來源逐檔SHA一致。這是測試部署路徑的結果，不證明F延遲或AV根因已查明；新原生試跑用該C API副本，遊戲binary及source仍F、DB／journal明確C SSD，不能稱F USB效能驗收。

真正Windows receipt `2026-10-31T07:44:51.3566843Z`、Quest ARM64 IL2CPP receipt `2026-10-31T07:54:06.8782171Z`成功，source fingerprint同為 `213b9b04e02d506c73110ba6df23109fc5ce3f14bf8f233b9d803ef8dde4777c`，也與目前來源Python重算一致。原Scene `4314adcd8c63d86469d16497127d8cfb／1444571642`、prefab `6f3f36cb9d710e847b5ecc569665e1ce／5227825248646244841`保持。aapt確認0.31.0／code38、min32／target35／arm64；實際APK60,189,546 bytes、libil2cpp81,607,904及metadata9,264,256 bytes，含新簡報型別，見`briefing-apk-validation.json`。receipt totalBytes是BuildReport總輸出，不當APK大小；沒有頭盔安裝／運行證據。

完整11項長期目標保持active。本輪為兩位同機PC Simulation，尚無Quest／VIVE、MR校正、廠商硬體、跨機與25台實機驗收；25端最大長文同時入場頻寬及Android字型記憶體也未量測。後續接續多玩家持續操作與場館流程，實機控制器／追蹤與閱讀舒適度分開驗收。

功能提交 `a579ef5ec82f85024de40e23d818e7d57ce23332` 已推送main並核對遠端一致。[本功能CI run41182512425](https://github.com/peca12968/vr-command-center/actions/runs/41182512425)／check124482634848實際failure、steps空；fresh annotation明示付款失敗或支出上限，job未啟動，不能稱雲端測試執行／通過。未更改帳務或手動重跑，本輪以上均為本機證據。提交前另核對三份字型／OFL／NOTICE的Git blob SHA與固定pin相符，明確保留TXT原行尾，避免Git文字正規化破壞來源證據；沒有改pin來配合正規化。

## 2026-10-31：15分鐘原生任務、完整連續性與封存失聯

前輪有實際進展；從乾淨`524667d`接續新增 [DESKTOP_LONG](DESKTOP_LONG.md)／`check-desktop-long.py` 及 [SEAL_RECOVERY](SEAL_RECOVERY.md)／`check-desktop-seal-faults.py`。本輪只改Python工具／測試／CI與文件；遊戲仍**API／UI0.28、Unity0.30.0／code37／NGO28**、原source fingerprint `d43085f4e6b755649b5da36b0885d6b690d7042f7ce4a871a947bc2e15ede53f`、原ID與同源Windows／Quest receipt。131 Editor／雙平台、680規則／446 HTTP／43串流／60 Node／223 Chromium為前輪成功結果，本輪未重建或重跑，不當新頭盔或UI證據。

**真正15分鐘通過**：`desktop-long/20261031-143453-51928ddf`，一個Windows server／一個headless client、stationary Simulation rig，沒有附掛240秒診斷或故障代理，也未延長其限制。先由真正AI造成20損耗／1次中彈，控制者停攻擊，健康80持續保存。工具fingerprint `7d684e6225dca664259dc78f058633de59497dc8d640acf1a5554ba5f53d1e79`，原player／admission／連線不重建；原票券到期後在tick5961仍收到同一身分的有效Running快照（UTC `2026-10-31T06:39:55.097841+00:00`），這是既有連線延續，不是讓過期票券重新入場。原生client只有一次CONNECTED。

固定900秒活動時間、唯一內部mission-clock End恰好tick18000；combat與world精確seal、pending=false、玩家自己的final JSON與原admission／stream／全部統計及兩個最終序號一致並ack。live觀察8453幀及869份status、來源年齡最大0.363945秒，badActive／badAge均0；live跳過1個序號，不忽略此事，而用完整封存回放逐幀補足。

完整replay自1走到8475，其中8460個Running幀：原玩家存在、connected、rig=Simulated；停攻政策生效後健康維持80，badRunning=0，沒有無意Pause。保存擷取間隔最大681ms、>=1500ms為0，tick不倒退／不超18000，末packet及所有statistics等於精確seal。回放另以4倍速實際讀完約3分45秒。`executionFinished`與`acceptancePassed`分開，任一反例不得complete，沒有篩掉失效幀或改規則來過。

這是**本次單玩家15分鐘的保存與收到快照範圍**；source UTC age是每份收到frame／status的觀察，不是每個時間點的網路延遲／RTT／FPS，也不是原生每render幀或完整0.5秒姿態接收統計。保存幀最大681ms與全Running body有效，仍不證明已修復歷史主迴圈停頓或25人情境。15分鐘不可外推4小時／長期穩定性。

15分鐘活動與雙seal完成後，才在完整replay讀取期間開另外兩個隔離短試跑，未在900秒活動量測中增加第二個原生負載。每場真正一server／一client，先AI造成20損耗／健康80，再Pause及操作員End；工具fingerprint `e0592a83cc72db0715dd50821d73b5db5c121813ea3155e6ade8a8e33a234bb1`，每場**8項**通過：

| desktop-seal-faults／20261031場次 | 模式 | 故障總秒／pending觀察秒 | 實際拒絕 | API狀態與CSV | 完整回放 |
|---|---|---|---|---|---|
| 145042-77e7c9b1 | combat-seal | 8.844／8.344 | 40次503 | combat未seal／pending=true／world未complete／CSV409 | 32幀 |
| 145100-e505c83d | statistics | 8.703／8.063 | 31次503 | 雙seal／pending=false／CSV可匯出，玩家仍pending | 32幀 |

兩種模式都至少8秒維持玩家pending，未接受final、未提早斷線；恢復後原請求重試、自己原admission的非零受傷結果／所有統計／stream及最終序號正確並ack，無DEBRIEF_TIMEOUT。CSV的session／player／room／origin／stream／through／finalStream及7項戰鬥數值、整段回放與ledger逐值一致。CSV既有政策是Ended＋combat seal，玩家final另須world seal及GameServer取得統計；依原契約分辨，沒有把已封存數字錯標pending或提前顯示final。

代理只新增`combat-seal` POST503及`statistics` GET503，原management／publication邊界保持；10項代理測試含舊8回歸及新2分流。8連線／HTTP1MiB／response2MiB／opaque WS64KiB、20秒fault／240秒life及non-daemon handler join均維持。兩場route／handler／capacity錯誤0、無自動上限、收尾tunnels0；不記payload／token／key，不注入姿態／武器／統計，不改OS／安全設定。舊試跑保持其原tool fingerprint，不覆寫歷史。

**49 Python**通過（原36 desktop＋新3 long連續性＋10 gate）；語法／293官方Transport單一修補亦通過，CI新增3項與兩個入口語法。本輪沒有新的.NET／Editor／APK／瀏覽器／GPU／PCM／鍵鼠／頭盔結果。native三場各自新資料／憑證，來源全Simulation，不把名冊Quest3標籤當接了頭盔。

`long-seal-validation.json`核對本輪**3個runtime／42檔**原件與snapshot SHA逐檔一致，之前6個runtime／187檔亦未變；僅JSON／logs／raw bytes，沒有在保存SQLite上開連線。資料明確C SSD、source／binary仍F，全停writer才一次回F且原件保留；三場cleanup無錯／tracked child空、原生玩家程序0，正式5080仍0.16。未操作Unity登入／授權／安全設定，沒有資料／憑證／binary提交。

完整11項長期目標保持active。這次通過一位同機PC的900秒與兩個可恢復約8秒故障，不是多玩家長期、25位持續操作、跨機、完整API／server崩潰、封存超過玩家期限或Quest／VIVE／MR／廠商硬體驗收。後續優先增加多玩家持續操作與更長／封存期限情境，實機項目分開保留。

額外raw JSON稽核也核對三位原生final的finalStreamSequence等於最後世界packet的throughCombatSequence、worldSequence等於精確acceptedSequence、throughSequence等於ledger；900秒End的actor確為mission-clock且證據tick18000。此與上述SHA核對一併記在long-seal-validation，未重開保存SQLite。

功能提交 `60bc110527d02caaeabb869125d942a94bcf9762` 已推送main、遠端一致。[本功能CI run41178736259](https://github.com/peca12968/vr-command-center/actions/runs/41178736259)／check124471590845實際failure、無步驟啟動；fresh annotation為付款失敗或支出上限，沒有雲端測試結果。未改帳務或手動重跑，本輪以上均為本機證據。

## 2026-10-31：管理與發布分通道失聯、原生計時恢復

前輪交付屬實際進展；從乾淨`0d39885`接續驗證 [CLOCK_RECOVERY](CLOCK_RECOVERY.md)。新增 `venue_http_gate.py` 及 `check-desktop-clock-faults.py`，本輪只改Python工具／測試／CI與文件。**遊戲仍API／UI0.28、Unity0.30.0／code37／NGO28**，原source fingerprint `d43085f4e6b755649b5da36b0885d6b690d7042f7ce4a871a947bc2e15ede53f`、Scene／prefab ID及同源Windows／Quest receipt保留。131真正EditMode、680規則／446 HTTP／43串流／60 Node／223 Chromium為前輪成功證據，**本輪未重建或重跑這些套件**，不當作新的頭盔或瀏覽器結果。

只把自己新建的Unity server指向本機代理；client NGO UDP不經代理，操作員觀察及命令直接到自己新建的API。先只拒絕同session管理GET，combat／world仍可發布；真正source保存suspended=true／Paused，原生server複本Ready=false／tick不變，而API管理狀態仍Running。這不是操作員Pause事件。恢復管理後原政策／同一場次接續，沒有重設倒數。

再於期限前約5秒關閉自己world tunnel並拒絕publish upgrade，保留管理與combat HTTP。真正server及client的既有NativeReplicationProbe觀察local tick恰好期限、Ready=false且phase仍Running；API接受序號固定在期限前、管理仍Running。本地到期待接受再維持6.5秒，證明沒有拿未發布時間直接End。恢復publication後原publisher重連同源補送，API才保存唯一mission-clock End；雙seal、pending=false、自己的原入場final JSON／所有統計及序號均一致，client ack後斷線。

同一tool fingerprint `9a842da5ebd55a0cff0d8ca839fda590e4422420206c06707d25e4308a0895d9`，兩個全新獨立runtime、每場一server／一headless client、Simulation頭手，各**8項**成功：

| desktop-clock-faults／20261031場次 | 秒數／凍結tick | 管理失聯總秒／停表觀察秒 | 發布失聯總秒／本地到期待接受秒 | API未接受邊界tick | 完整回放 |
|---|---|---|---|---|---|
| 142318-373dc579 | 60／1200 | 6.141／5.766，tick104固定 | 12.281／6.531 | 1100 | 726幀、60個suspended、85個到期Running |
| 142458-06088e37 | 180／3600 | 6.094／5.750，tick105固定 | 12.297／6.547 | 3502 | 1851幀、59個suspended、87個到期Running |

完整SSE從1走至最後，tick不倒退／不超過期限，末packet與所有statistics等於精確seal；包含暫停幀與到期仍Running等待End幀，不把到期本身冒充已封存。兩場各一次內部End、原stream／設定序號／原admission一致，正常結果的來源為Simulation；combat ledger原本零事件仍保持原null來源，不補造事件。時間含HTTP、取樣及輪詢，不是RTT、FPS或新的期限；未量測完整0.5／1.5秒連續性，不宣稱修復原主迴圈停頓。

每場各一個既有WS被關閉，分別12／12次管理GET回503、23／23次publication upgrade被拒，均2次成功WS連線（初次與恢復）。代理route／handler／capacity error全0、沒有自動block／lifetime上限、收尾active tunnel0。只有同一session所需路由，最多8連線、HTTP1MiB／response2MiB／opaque WS每塊64KiB；故障20秒／代理240秒固定上限。只在記憶體轉送原認證／body與不解析的WS bytes，不保存payload／票券／key，不注入姿態／射擊／RPC，不動OS／防火牆／安全設定。這不保證某個特定ACK曾被丟棄，亦非部署代理或認證邊界。

**44 Python**通過：8項新代理測試（實際loopback HTTP／opaque TCP tunnel、分通道、轉送body／認證、容量、body／scope拒絕、自動故障與lifetime上限、HTTP worker收尾等待）加36項既有desktop，不是原生試跑次數。語法及293官方Transport單一修補核對通過；CI新增8項與語法。最初6項測試中3個錯誤先指出HTTPConnection不支援context manager，改用contextlib.closing後通過，再補lifetime及HTTP worker案例為8；這是工具錯誤，未修改Unity／API或放寬規則來通過。

早期 `141303-3bc506ce`／`141505-ca55d190` 的計時與補送均通過，但代理只等待listener／watchdog，未明確等待HTTP處理執行緒，保留為舊scope，不當最終收尾證據。現改為non-daemon request handlers，server_close等待所有處理執行緒，新增真正in-flight HTTP等待反例；重新60／180秒兩場為上表最終結果，未改Unity／API。

所有probe均complete且未truncated／send queue error，finish在正常client斷線及固定240秒前；本輪沒有GPU／PCM／Windows輸入／頭盔觀察。probe僅讀真正本地複本，不讀仍有exclusive lease的world journal，也不把診斷來源變成Tracked。180秒是有界較長運行，**不是15分鐘、4小時或長期穩定性通過**；沒有改probe上限來湊證據。

資料明確C SSD、source／binary在F，全停writer後一次snapshot回F、原件保留。`clock-recovery-validation.json`核對本輪**4個runtime／159檔**原件與snapshot逐檔SHA一致，前輪兩個clock runtime／28檔亦逐檔未變；只讀JSON／log／raw bytes，未在保留SQLite上開連線。cleanup errors空且無tracked child；原5080仍0.16，Unity serve／原授權與安全設定未動，憑證／資料／binary不提交。

限制與下一步：這只證明一位同機PC在指定管理503／world連線中斷、60及180秒活動期限的恢復，不是整個API重啟、server crash、封存中斷、跨機、25位持續操作或Quest／VIVE／MR／硬體驗收。完整11項長期目標保持active。下一步獨立驗證更長任務及封存階段失聯，不用本工具240秒診斷替代長期驗收。

功能提交 `96f86d5a13f2793ba44f721b6859e0479ade0451` 已推送main、遠端一致。[本功能CI run41176835936](https://github.com/peca12968/vr-command-center/actions/runs/41176835936)／check124466037718實際failure，無步驟啟動；fresh annotation明示付款失敗或支出上限，沒有雲端測試結果。未更改帳務或手動重跑，本輪上述檢查為本機證據。

## 2026-10-31：選用任務活動倒數、到期 End 與兩房原生驗證

從乾淨 `336410b` 接續原始任務「時間」需求，新增 [MISSION_CLOCK](MISSION_CLOCK.md)。API／UI **0.28**、Unity **0.30.0／code37／NGO28**。操作員只在 Preparing 明確選用自動結束；新舊場次預設手動，不把既有 DurationSeconds 靜默改成期限。開始後政策及任務秒數不可變，規則仍0.8.0，原素材 pin／舊資料讀取／原始 binary header及checksum保留。

計時為原 ArenaWorld 20Hz 活動 tick，不是 UTC 或不中斷牆鐘；Preparing／Pause／管理中斷停表，主迴圈卡頓可使活動時間慢於現實。到期 ArenaSession 不再 tick、射擊／換彈或建立新遊戲 binding；Unity 強制保存邊界並持續發布。API 250ms服務只從已接受的同源世界幀確認版本、設定序號與期限，以固定內部 mission-clock 身分提交正常 End，再走原雙 journal／精確 seal／個人戰績 ack。未發布的本地時間不能授權 End，HTTP 沒有 Internal 捷徑；API失聯時只凍結等待，不能聲稱已結束／封存。手動 End 可先勝出，不追加第二筆。

新寫入事件 **envelope7，讀1–7**，SetMissionClock／source capability／自動End證據持久化。新 header missionClockVersion1與保存任務秒數由API獨立核對；world schema1、驗票2不變，不代表可降回舊reader。Prepare原位升28、原Scene及PlayerAvatar ID保持；API／UI／全部遊戲程序須協同更新。原5080仍0.16，不拿新來源接它或替換歷史。

**真正 Editor 131 EditMode**通過（6項新增：邊界／NGO序列化／HUD／Pause凍結／Unity null預設手動／header能力）。Windows receipt `2026-10-31T05:56:16.0212938Z`，Quest ARM64 IL2CPP receipt `2026-10-31T06:05:38.2561465Z`；同一來源 fingerprint `d43085f4e6b755649b5da36b0885d6b690d7042f7ce4a871a947bc2e15ede53f`。原Scene `4314adcd8c63d86469d16497127d8cfb／1444571642`、prefab `6f3f36cb9d710e847b5ecc569665e1ce／5227825248646244841`未變。aapt確認0.30.0／code37、min32／target35／arm64，實際APK46,416,866 bytes，包內libil2cpp81,313,216及metadata9,259,300 bytes，含MissionClockState；見clock-apk-validation.json。receipt totalBytes為BuildReport總輸出，不能當作APK實際大小。建置不是頭盔運行證據。

本機隔離 .NET locked restore／Release零警告錯誤、**680規則、446 HTTP、43世界串流**通過。**60 Node／223 Chromium**全回歸成功，另有 **13項**新時間控制／真正native錄製觀戰／最終結果核對，最後提示文字更新後再次13項成功。瀏覽器為SwiftShader，沒有當作原生GPU。17項既有desktop debrief／snapshot Python及語法、293官方Transport／單一修補核對通過；本輪未重跑25端容量。

真正Windows兩個獨立server／每房一個client，`desktop-clock/20261031-135731-313ea995` **8項完整通過**。60秒自動房Pause在tick103，35.157秒內每次採樣不變；恢復後恰好tick1200停表，只有一筆schema7／mission-clock End及同源證據。手動房在tick1906仍Running，未自動加政策，手動End在tick1927。兩場world complete／pending=false、兩位個別結果均ack。整段回放自動947幀／手動952幀，逐幀連續、auto無tick>1200，末統計等於精確ledger。

computer-use實際視窗觀察：Paused REMAIN00:55，真正Space後仍30／90、耗彈0；Running後Space變29／90，依序見00:47與00:16，最後看到自己的SEALED RESULTS、耗彈1／健康100／0%並斷線保留。沒有注入姿態／命中。額外觀戰工具只在C建立新的audit copy，從該副本啟動自己的API；13項核對新header活動時間為自動01:00／計畫01:00、手動01:36／計畫01:00，兩位final JSON的session／player／admission／room／stream／combat與world序號及全部統計一致。沒有在保留的原件／runtime-snapshot上開SQLite。

資料明確在C SSD，source／binary在F；所有writer停止後才回F一次副本。`clock-runtime-validation.json`核對本輪**2個runtime／28檔**原件與snapshot SHA逐檔相同、cleanup errors空且無tracked child；含原生工具初次失敗場次。正式5080／原Unity serve、授權、安全設定未動，沒有憑證／資料庫／binary提交。

保留檢查器失敗：首次瀏覽器用UI編輯前的隔離輸出資產，缺clock欄位，重新build資產；第二次把fieldset拿Playwright isDisabled判斷，改讀真正DOM disabled；第三次未等非同步refresh更新政策文字，加入對應渲染等待。最後完整回歸通過，這些不當作遊戲故障。原生 `135715-168b5367` 使用錯誤start_clients方法名，改成既有clients，失敗原件／seal／清理亦保留。未改規則、期限或放寬權限來通過。

限制：本輪兩位同機PC Simulation與明確暫停／到期案例；非25人同步操作、跨機／頭盔／MR／廠商硬體、長任務或API／server崩潰恢復驗收。原主迴圈停頓亦未證明修復。完整11項長期目標保持active。後續優先驗證計時期間管理／發布失聯與長任務，取得設備後另驗Quest追蹤、控制器、效能及VIVE相容。

功能提交 `3d90c9b8221b49825f11a984d14c8a3af85156e0` 已推送main並核對遠端一致。[本提交CI run41175253162](https://github.com/peca12968/vr-command-center/actions/runs/41175253162)／check124461355970實際failure、無任何步驟啟動；fresh annotation明示付款失敗或支出上限，不能稱雲端測試執行／通過。未更改帳務或手動重跑；以上為本機證據。

## 2026-10-31：End入場延遲、結果丟包與真正期限回歸

前輪交付及推送屬實際進展；本輪從乾淨`34ee9f7`接續驗證尚缺的結束競態。新增[DESKTOP_END_NETWORK](DESKTOP_END_NETWORK.md)／`check-desktop-end-race.py`及只供本輪自有client的`udp_gate.py`。最初推測剛approved的玩家可能因client尚未就緒而丟失結果，但第一個真正延遲實驗實際收到正確結果，**不以未重現的假設修改遊戲端／NGO協定**。

遊戲仍Unity0.29.0／code36／NGO27、API UI0.27，source fingerprint仍`a97b40a2836de7a8c5e8e64596b37feac3d545438a4538df4d403f5d73c4e9d3`，Windows／Quest receipt與原ID不變；125 EditMode及同源雙平台是前輪成功證據，**本輪未重建或重跑Unity／APK**，不是新的頭盔證據。rules0.8.0／資料格式／原資源與所有歷史保持。

兩個真正無圖形Windows client，一位直連、一位只經自己的loopback gate；server及API／世界發布不經gate。合法名冊先加入兩位再Begin，第一位先由真正AI造成中彈2／損耗40／健康60，第二位健康100，因此不能用另一人的結果混過。只延遲或丟棄原始UDP datagram，不注入RPC／姿態／武器／命中，不讀封包內容、不寫PCAP或payload。只綁127.0.0.1及自有server port，固定一個client endpoint，其他sender丟棄；不改MTU／0.5或1.5秒門檻／安全設定。

最終三場同一tool fingerprint `78ebb1f8ca3b7d580b0be3e6aba346a3501d240f19d2b3ec0d6daa94293a1bf8`，每場**6項**通過：入場及故障時機、正常peer自己的雙seal結果、延遲者結果或阻斷期間無final、Ended拒絕且ledger不變、combat stream尾界、整段回放連續且末packet／statistics完全相同。`complete=true`僅在gate停止及自有writer全停／snapshot成功後寫入，工具來源途中變動或自動queue／hold上限觸發都不能passed。

| desktop-end-race／20261031場次 | 模式 | 實際觀察 | 完整封存回放 |
|---|---|---|---|
| 131131-86bb1cda | join-delay | server已approved、client無CONNECTED log時End；暫存320包、188265 bytes，hold1.969秒，seal後釋放；兩人各自正確結果及ack | 37幀、末packet／statistics逐值相同 |
| 131140-00678de7 | result-drop | client先接受pending，再丟5033包下行；hold29.860秒，從End要求起30.578秒觀察connectionReleased，阻斷期間無final，解除後也無final | 37幀、同上；正常peer結果正確 |
| 131218-71180c22 | result-large-drop | pending後丟大於64 bytes的436包，33個較小datagram通過；hold30.218秒，End要求起30.688秒觀察DEBRIEF_TIMEOUT，阻斷及解除後無final | 37幀、同上；正常peer結果正確 |

64 bytes只按長度篩選，沒有把所有小包稱為keepalive。connectionReleased不指定未量測的傳輸根因，與明確的應用層DEBRIEF_TIMEOUT分開；觀察時間含HTTP及輪詢，不是修改後的遊戲期限、每包延遲、RTT或FPS。兩個loss場都先真正CONNECTED／接受pending，才啟用故障。延遲入場者End世界的connected=false／rig=None，未偽造參戰或Tracked，也不能從無CONNECTED log推定avatar尚未spawn；另一位為Simulated。新的Ended連線使用原票券仍被拒且收不到debrief；離線稽核確認拒絕時票券尚未過期，非拿過期冒充Ended拒絕。

所有三場world complete／pending=false／活動0、最終stream／序號與ledger一致；完整SSE回放從1走至37，封存不因client丟包變動。原生沒有新GPU／PCM／UI觀察，只有headless日誌與授權API／回放。**45 Python**為9項真實kernel UDP／有界／順序／單client／下行loss／長度篩選測試，加36項既有desktop規則，非45次原生試跑；語法與293官方Transport／單一修補核對亦過。CI新增這9項與語法步驟，沒有改或重跑後端／全瀏覽器／25端容量。

失敗與舊scope均保留：`125615-c80e9bcc`檢查器誤在Running加名冊被HTTP409拒，改為合法Preparing加入、Running才連線，未放寬政策；`125634-01b64006`原expect-missing假設失敗，結果其實正確，未宣稱遊戲bug；`130124-e1e5386a`過早數ack，把client先記final、server稍後才ack當失敗，改為獨立有界等待；`130402-fb6fc5e9`硬等應用期限，但實際先connection release，舊failed保留，現將兩個結果分型。`130355／130720／130756`先前成功只屬舊scope，未含整段replay／tool fingerprint，不當作最終三場。UDP工具初期drop位置及非原子計數假設由unit測試先擋下，修正後9項全過，未修改Unity Transport來源。

隔離資料明確C SSD、source／binary在F；全停writer才複製回F，未移動原件。`end-network-validation.json`覆核本輪**10個runtime／140檔**原件與副本SHA逐檔相同、cleanup乾淨，前輪20個runtime的保存manifest亦逐一未變。只讀JSON／log／原始bytes，未開SQLite。正式5080仍0.16歷史服務；Unity serve／登入／安全設定未動，沒有憑證／payload／binary提交。

功能提交`56b667b9872557fd9f2aa4a0f8de503834a17748`已推送main並核對遠端。最新[CI run41172328133](https://github.com/peca12968/vr-command-center/actions/runs/41172328133)／check124452732120實際failure、steps=null；annotation仍明示付款失敗或支出上限，job未開始，沒有雲端執行結果。未改帳務或重跑，以上測試為本機證據。

限制：這只驗兩個同機Windows client、選定的一次延遲與兩種loss，不是所有時序／重排、25位同時操作、跨機、頭盔／MR或完整故障／server crash驗收；封存連線中斷及長任務仍待。完整11項長期目標保持active，原主迴圈偶發停頓亦未證明修復。

## 2026-10-31：玩家End戰績、零事件修正與一般PC入口

新增[DESKTOP_DEBRIEF](DESKTOP_DEBRIEF.md)：Unity **0.29.0／code36／NGO27**，API／UI仍0.27，驗票2／rules0.8.0／歷史錄製與素材格式不變。End立即解除遊戲binding，只有原名冊player＋admission＋room＋seat相同的既有連線可等待自己的結果。combat及world journal都精確seal後，GameServer以原有認證statistics路由讀ledger，可靠target RPC只傳該玩家，含來源／session／admission／stream／最終序號；ack後斷線。Host須等peer結束才處理自己的ack／shutdown，不讓主持人先切掉其他結果。移除／換席仍立即撤銷，Ended不接受新入場，玩家不持有管理key。

PC先顯示等待封存，再顯示耗彈／命中／擊殺／中彈／損耗／健康／命中率及來源。結果留在bootstrap，avatar despawn／斷線不清除，真正Reconnect才清除；Ended停止姿態送報且結果接管HUD，不移動Tracked資料。無final只顯示未確認；等待30秒，正在進行的HTTP最多再5秒。沒有新增client永久結果檔，伺服器報表／回放仍保留。Android等候標籤接相同文字，無頭盔排版／操作驗收。

**找到並修正零事件漏測**：原練習場會先停client再seal，無法看結果；改為等送達後，`desktop-practice-checks/20261031-122249-c933da43`原27項仍通過，但五人／一人／兩人三場都只有pending，30秒後8人全部timeout，allAcknowledged=false（43／39／591世界幀）。精確報表封存不等於玩家收到結果，原passed只屬舊檢查範圍，結果及原件保留。真正EditMode新增API JSON `origin:null`反例，125項中1項失敗、訊息`JsonUtility null origin was []`，XML及log在`debrief-null-regression-*`。Unity把null string讀成空字串；現僅允許已封存、final combat sequence=0、全名冊零事件且健康100，來源取綁定stream，不補寫API的null combat origin。非零串流或任何玩家有事件的缺失來源仍拒絕。修正後 **125項真正EditMode全過**，新增共11項身分／序號／來源／不可覆寫／真實JSON驗證；Tests門檻125。

最終fingerprint `a97b40a2836de7a8c5e8e64596b37feac3d545438a4538df4d403f5d73c4e9d3`；Windows receipt `2026-10-31T04:29:48.3629507Z`，Quest receipt `2026-10-31T04:42:20.0862064Z`，同源ARM64／IL2CPP APK成功。aapt為0.29.0／code36、min32／target35／arm64-v8a，實際46,486,635 bytes；包內有81,279,680-byte libil2cpp、9,257,336-byte metadata及新debrief型別（不是實機執行證據）。原Scene `4314adcd8c63d86469d16497127d8cfb／1444571642`及prefab `6f3f36cb9d710e847b5ecc569665e1ce／5227825248646244841`保持，Prepare不重建ID，所有遊戲程序一起更新。

最終來源的原生證據（全為同機Windows、Simulation）：

| 20261031 artifact場次 | 範圍 | 世界幀／結果 |
|---|---|---|
| desktop-debrief/123041-bbe00436 | Begin前取消、4項 | 27幀；兩位零事件結果ack、Ended舊票券拒絕 |
| desktop-debrief/123047-12e8f352 | Host＋peer、4項 | 27幀；玩家一中彈1／損耗20／健康80，peer100；peer ack先於host shutdown |
| desktop-debrief/123052-2b34dd7e | dedicated server、4項 | 27幀；兩份不同結果與精確combat／world seal一致；移除者與Ended舊票券無結果 |
| desktop-demo/123058-1411a4e3 | 一般啟動器、真正GPU／Space及另列5項觀察 | 241幀；耗彈1／命中0／0%／健康100，peer全零；兩位ack、保留畫面、Reconnect清除及票券拒絕 |
| desktop-practice-checks/123148-24d21ff8 | 更新為30項、五人／一人／兩人 | 43／43／589幀；End、end.request、60秒到時均逐位收到並ack、精確seal／CSV／cleanup一致 |
| desktop-venue/123338-129116cb | 控制台49項UI／native，兩位在場及一位離場歷史 | 135幀；兩位結果ack，任務／配置／名冊／聲光設定／AI／觀戰／封存回放／CSV通過，Chromium SwiftShader另列 |
| desktop-venue/123517-5aebaf1b | 操作員工具兩連續場及4項真正GPU觀察 | 55／123幀；第一場結果仍在90秒保留期時新玩家開啟新Preparing視窗，第二場獨立結果；兩場各一位ack |

一般練習場及操作員入口新增`--results-seconds 0..300`（預設30），先等結果ack／斷線再處理保留畫面；操作員的保留期限不阻塞其他房間，新可見玩家優先取代舊結果。關閉結果或`dismiss-results.request`可提早結束保留。`*-player-results.json`將送達、只有斷線、關窗、逾時及空集合分開，空集合不當成功。送達結果以本場次cache固定，保留期限清掉程序後不能以空集合覆蓋已確認的receipt；新增單元反例與`desktop-venue/124502-969f19e5` results-seconds0／21幀及退出後receipt SHA一致。seal只要求自己API／authority存活，已正常關閉的玩家不阻止精確保存；一般等待仍檢查全部必需程序。

同源`unity-admission/20261031-123655-db6519b6` **8項／367幀**通過：重複入場、撤銷、同ID新epoch、舊移除與票券、舊client遲退出、真正transport釋放後同admission重連的已接受位置／健康／彈藥，以及Ended拒絕／封存；這次為無圖形回歸，不補稱0.65公尺實際鍵盤。**36 Python**（8 active＋11 capacity＋5 artifact＋12 debrief／入口生命週期）、語法及293官方Transport／單一修補核對通過。API／UI來源未改，未重跑全後端／201 Chromium／25端容量或PCM／FPS。已檢視本次operator-ui/final-report.png；軟體WebGL不是原生GPU證據，原生結果與新場視窗另以computer-use觀察。

隔離runtime全部明確C SSD，來源／binary仍F；全停writer後才一次複製回F，保留原件，未開SQLite作稽核。`debrief-final-validation.json`覆核**20個runtime、280檔**，原件／副本逐檔SHA一致，最終來源10個runtime（含上述三個練習場）皆乾淨；之前七場已保存manifest也保持不變。早期`120744-0024ac98`因工具誤用description而非必要briefing在HTTP400停止、未啟動遊戲，12檔保留。其餘早期UI修正前`120754／120804／120817`與零事件修正前`121037／121044／121053`各14檔保留；後三場fingerprint `002550...`與其8項／382幀重連不是最終來源。早期HUD曾有POSE REJECTED及斷線Preparing小框，已由最終畫面修正；不重寫舊passed或把舊receipt當新建置。Host早期summary的最後label過廣，debrief-result始終正確區分host shutdown與dedicated票券檢查，現由同一checks陣列產生摘要。原5080歷史服務與Unity serve／登入／安全設定未更動。

功能提交`c4917b6d70fc9e75e4f0361876a445e2d8d9dc32`已推送main、遠端一致。最新[CI run41170023324](https://github.com/peca12968/vr-command-center/actions/runs/41170023324)／check124445771935實際failure、steps=null；annotation明示付款失敗或支出上限，job未開始，不能當作雲端測試失敗或通過。未改帳務／重跑，以上為本機證據。

限制：本輪兩位結果接收及最多五位無圖形練習場，未驗25人同時操作、跨機、Quest／VIVE實機、MR或廠商硬體。真正零事件bug曾觸發30秒timeout，但這不是刻意丟包／斷網／封存中斷的完整故障驗收。近End入場競態及更長任務仍待；原主迴圈偶發停頓未證明修復，完整11項長期目標仍active。

## 2026-10-31：真正W／Space／R／Space與25端回放，補全程失效檢查

從乾淨`d39bd9e`接續PC動態操作。新增[DESKTOP_ACTIVE](DESKTOP_ACTIVE.md)／`check-desktop-active.py`，使用既有Unity0.28.3／code35／NGO26及API UI0.27，**一位實際操作、24個接收端**，一個真正GPU視窗及24個nographics程序。使用computer-use真實按鍵，無測試RPC／姿態／武器注入。合法油桶配置使實際候選網格把Room3靶位安排在(-3,0,-1)，不直接指定NPC位置、不改rules；W實際前進0.05公尺，Space命中50傷害、R補至30／89、第二發擊殺至29／89。主玩家耗彈2／命中2／擊殺1／100%、健康100；其他24人的頭位、彈藥／射擊及統計未被本玩家輸入改動。

第一個`desktop-capacity/20261031-111719-325e1088`舊版檢查器exit0、8功能項／130快照／518世界幀／6個回放參考／CSV一致，原始passed與248檔SSD-F副本保留。但逐列稽核發現**65筆Running失效列**，所有26份報告皆不符後加的全程條件：39列connected16／25、26列24／25，玩家數仍25／健康總和2500／Ready且coherent。server在tick242、244觀察16位，246為24位後恢復；最多本地新tick觀察空窗**0.9258025秒**，最大擷取UTC來源年齡0.569364秒（仍低於原1.5）。這是權威可參戰旗標短暫失效，不能單憑此斷言NGO連線已斷、是哪位玩家姿態／哪段CPU或GPU原因；不把後來的成功快照當作全程成功。稽核`active-first-continuity-audit.json`明示26份皆不通過，未改舊結果。

因此新增嚴格條件：各完整report從初始成功capture起的**所有觀察Running列**須25人／connected25／健康2500／Ready／coherent，同一Running區間相鄰新tick觀察<1.5秒；刻意Pause另列。SSE回放逐序號走完整封存錄製，初始至最後參考間每張保存Running幀亦驗全名冊／Simulated／可參戰，所有保存參考packet與statistics逐值相同；任一失效不能以後續恢復洗掉。這不是每packet、所有瞬間或網路RTT的證明，原0.5秒姿態及1.5秒來源門檻保持。失敗時active-result不改成complete，只有cleanup後成功才passed。

快照輸出從原同時26份改為預設`--capture-batch 1`，逐端要求／等待，同epoch共用參考tick下界、不稱同瞬間。可明確26重現fan-out，不刪失效列、不修改遊戲或放寬條件。新增自己`desktop-active` artifact family與pointer，不覆蓋靜態capacity入口。對照`--without-replication-probe`只檢查權威／回放、`localReplicaContinuityChecked=false`，空集合不算接收端證據。

| desktop-active／20261031場次 | 終態／範圍 | 保存幀／回放參考 | 最大來源年齡 | SSD-F檔數 |
|---|---|---|---|---|
| `112924-5da663bb` | exit1，無probe末發UI等待逾時，三步完成 | 869／未完成新回放核對 | 不作成功時序證據 | 14 |
| `113205-3d172a38` | exit1，無probe末發UI等待逾時，三步完成 | 913／未完成新回放核對 | 不作成功時序證據 | 14 |
| `113444-5c76154c` | exit0，無probe **9項權威／回放對照** | 1127／6 | 0.159532秒 | 14 |
| `113854-7e7d5f31` | exit0，分批probe **9項含全程／接收端檢查** | 966／5 | 0.167574秒 | 248 |

最後分批場26份report完整、**130／130快照**通過，共20658列，其中初始capture後**19916個Running觀察列全符合條件**、本地最大相鄰新tick間隔0.1445342秒，server最後觀察Ended。所有保存Running幀檢查通過，最終CSV25人逐項對ledger／精確尾端，SHA `5bad592a232c48ffe4eb3542116e655d5cba715ebb941c23f1037a6b99c2de07`；兩個完成場raw send queue full皆0。最低抽樣可用實體記憶體分別7,771,242,496／6,481,555,456 bytes，原2GiB保留未觸發。無probe場沒有各端快照／report，最後確認訊息當時沿用「world and local replicas」文字過廣，實際只判world與空本地集合，metadata明確false；已將後續訊息改為world only，未補造資料。

兩個中斷場都在確認畫面／恢復焦點時超過30／40秒的**操作員等待**，不是量到同長的網路延遲。曾收到不符遊戲的截圖，重選唯一自有window／activate後恢復正確畫面，沒有對非遊戲畫面輸入；第一場UI呼叫失敗後我誤寫kill.done，predicate沒有接受，未計擊殺或成功。後續改為呼叫成功、觀察正確畫面後，另一步才寫ack；無probe對照可用90秒等待，僅增加觀察／UI恢復時間，不改網路或姿態門檻。完成對照中的首次R呼叫結果未明，重新觀察29／90後一次重試並確認RELOADING，最後數值30／89及29／89符合；不把未知呼叫當成功。所有中斷場仍精確seal、cleanup無錯誤無殘留，failed及原件保留。

兩個成功／兩個中斷場的全部tracked writer停止才一次回F，原件／副本bytes SHA逐檔一致、稽核前後不變；first場248檔亦已核對。只讀JSON／CSV／bytes，未開原或snapshot SQLite、未重寫副本。摘要`artifacts/active-validation.json`、`active-first-continuity-audit.json`、`active-final-validation.json`。25程序source／binary仍F、新runtime明確C SSD，非F USB全資料或跨機。原5080唯讀仍0.16歷史，Unity serve／登入／安全性設定未碰。

**8 active規則／全程反例＋11容量＋5 artifact，共24項Python**與語法通過，CI新增active入口；不是24次原生試跑。只有Python／CI／文件變更，C#／資產／API UI與資料契約保持；目前來源fingerprint仍`e8ae6d846dc014e48984a035f2960c043d342a4fe192ff0feaae3891973ba3d0`，兩平台既有receipt及原scene／prefab ID一致。本輪沒有重建／重跑前輪114 EditMode或Quest／Windows，未重跑後端／全瀏覽器／49 UI native／27練習場／8重連，不混算。視窗觀察確實看見血條減半、RELOADING、30／89、敵軍移除與29／89；沒有新原生GPU讀回／PCM／FPS或聽感證據。

這組fan-out／無probe／分批比較不足以證明診斷I/O、GUI觀察、GPU、GC、排程或舊主迴圈停頓的根因，**不稱遊戲端全局修復**。它補足真實操作到25端資料／保存回放的證據並消除只看檢查點的漏洞；`all25SimultaneouslyActive=false`及`networkCapacityAccepted=false`。持續25人同時操作、更多場景／長任務、跨機／Wi-Fi、MR／Quest／VIVE／廠商硬體仍待，完整11項與長期目標保持開發中。

功能提交`2cdaa1fd8955166392f2708d14481822f1e701ee`已推送main、遠端一致，提交後來源fingerprint重算仍e8ae6d846dc014e48984a035f2960c043d342a4fe192ff0feaae3891973ba3d0。GitHub #1保持open，原11項及歷史封存連結保留，更新後獨立讀回本文逐字一致。[功能提交CI run41166328563](https://github.com/peca12968/vr-command-center/actions/runs/41166328563)／check124434582620實際failure、steps=null；annotation明示付款失敗或支出上限，工作未開始，沒有雲端測試結果。未改帳務或重跑，本機證據獨立保存。

## 2026-10-31：各玩家端複本證據與伺服器packet池

從乾淨`22c432c`接續前輪105行send queue full，完整目標保持開發中。新增[DESKTOP_REPLICATION](DESKTOP_REPLICATION.md)：明確`--replication-probe`只在Windows Development的自有程序觀察真正本地NGO狀態，普通／Editor／Android不安裝。240秒／4096 tick列／4096錯誤／64次capture有界，保留最早資料；穩定期不逐幀寫檔，明確要求才輸出唯一快照，finish取消threaded log訂閱後一次report。無測試RPC、輸入／姿態注入、PCM／GPU、讀他程序記憶體或OS設定變更。

每client／server五個檢查點（Running起點／60秒後、Pause、Resume、AI傷害後全Pause），核對實際收到的玩家／敵軍ID、房間、健康／彈藥／敵軍fireSequence、位置、avatar connection／owner、Simulated／accepted及Presentation／Actor tick。快照不早於自己的API參考tick；追趕失敗快照保留、不覆寫。起終點間每一筆本地新tick觀察亦須全名冊／健康100／coherent，含端點新tick間隔<1.5秒。這是端上觀察間隔，不是RTT、每packet送達、每張世界幀在所有client顯示或同一瞬間的跨端快照。client在End前明確finish，**不驗每client收到Ended**；server在精確seal後才finish。

0.28.2／code34僅作中間Windows診斷版，保留原driver128，沒有建置或交付該版Quest。以下基線與最終0.28.3完成資料集（desktop-capacity／20261031前綴）已全停writer、JSON／bytes SHA稽核，不開原或snapshot SQLite：

| 場次／版本 | 範圍／檢查 | 完整報告／成功capture | 本地tick列／穩定列 | 最大本地新tick間隔 | queue錯誤／SSD-F檔數 |
|---|---|---|---|---|---|
| `102502-3f9d73db`／0.28.2 | Linked25人60秒／9項 | 26／130 | 18252／17462 | 0.133572秒 | 0／264 |
| `103038-997cffd4`／0.28.2 | Linked及五獨立房各25人60秒／22項 | 56／280（286次嘗試） | 38532／36402 | 0.144540秒 | 112／534 |
| `105445-7f334dae`／0.28.3 | Linked及五獨立房各25人60秒／22項 | 56／280（286次嘗試） | 38087／36456 | 0.144500秒 | 0／534 |

第二場**重現Linked server112行錯誤，probe亦完整捕捉112筆**：15組在最後觀察到的Running tick62–1152，一組在Paused tick1255，每組7筆；本地秒數9.455454–70.160036，server最後已觀察Ended。phase／tick是log callback讀的最近Update快取，不宣稱發送內部的原子狀態。來源端／全部接收端仍達上述檢查，錯誤數不等於丟包數；這不表示可忽略錯誤。首次無錯誤與之後重現分開保留，不挑只過場。原始105行沒有時間戳，不能倒填成同一根因或階段。

官方UnityTransport的MaxPacketQueueSize是整個driver共用的每update send／receive packet容量，原128不是每peer。新增`VenueTransportProfile`，在StartServer／Host／Client前設定**server／host1024、client仍128**，不改MTU、reliable window、timeout、資料欄位、規則／權限或嵌入patch。此為有界伺服器突發保留候選配置，不能由數字本身稱修復。快照額外核對實際本地設定，並以Actors.WriteField只寫暫存記憶體量field bytes、不清dirty／變更集合。真正序列化測試30／125角色分別4232／17627 bytes，排除NGO／UTP包頭、其他狀態、重傳與入場；不當作實際頻寬或100敵軍負載已通過。

新遊戲端**0.28.3／Android code35**，API／UI0.27、NGO26不變；114項真正EditMode（原109＋2個診斷JSON回歸＋3個driver設定／真實序列化檢查）於02:38:39–02:38:45 UTC通過，Windows receipt02:37:53、Quest02:54:30成功。兩份來源fingerprint均`e8ae6d846dc014e48984a035f2960c043d342a4fe192ff0feaae3891973ba3d0`，原scene／prefab ID一致。真正SDK aapt確認APK0.28.3／code35、min32／target35／arm64-v8a；不是裝置啟動證據。IL2CPP過程較久，確認既有build handle及同身分自有compiler仍有CPU／輸出增加，未因觀察逾時重啟，也未改OS／安全政策。

最終兩模式22項及完整cleanup exit0後才stage=passed／complete=true；六世界4147保存幀，3374穩定期回放幀逐張全名冊／出生位／健康／來源核對，六份最終CSV／ledger／末幀一致。56份報告原始錯誤0、原生日誌亦0；六server均觀察到Ended才停止。端上快照實際server1024／client128、Actor field獨立房848／Linked4232 bytes；最小穩定區間60.222563秒、最小可用實體記憶體8,589,647,872 bytes，原2GiB保留未觸發。最大擷取UTC來源年齡0.179819秒，與本地tick間隔分開，不稱RTT／FPS改善。這證明此負載與本輪配置的錯誤由112到0，**不證明所有工作量／網路條件已修復或原偶發主迴圈停頓已解決**。資料摘要`artifacts/replication-validation.json`。

兩個開發失敗保留：`102252-fa8155d0`首次capture KeyError，因直接匯出無Serializable的WeatherState而JSON缺presentation；改明確DTO，實際Unity JSON回歸測試防再漏欄，沒有改遊戲WeatherState／wire。`102700-27f090b1`Linked檢查完成，但獨立房capture因完整暫存路徑過長FileNotFound而整體exit1；改短`replication/p001`目錄並保存程序對照，新增長名稱回歸測試，不改系統長路徑／安全政策。兩場cleanup均無錯誤無殘留，92／292檔SSD原件與失敗F副本SHA一致、稽核前後不變，失敗不改成通過。第一個成功pilot server探針在End前停止，後續完整場改持續到seal，不能替pilot補造End觀察。

同版未啟用probe的Linked25人／60秒對照`110021-8d1dc8e1` **8項**通過，658幀／561穩定回放幀、最大來源年齡0.155637秒，raw queue錯誤0；runtime無replication目錄或對照表，不補接收端證據，14檔SSD／F SHA一致、cleanup無錯誤無殘留／活動0。`unity-admission/20261031-110235-35459427` **8項真正原生入場／撤銷／同admission回連**亦exit0，392幀精確seal、回放／ledger一致、健康60及彈藥保持；沒有interactive按鍵／GPU、沒有移動後位置新證據。該既有小型fixture資料在F，只作正確性，不稱F USB的25人時序成功；37檔收尾後bytes稽核前後不變，全部自有Popen在finally終止／等待。兩場沒有queue錯誤。

**11項容量／接收端Python＋5項共用artifact檢查**及語法通過，包含非有限值／過期tick／owner／connection／敵軍fireSequence／長目錄對照與真正Windows獨占lease釋放等待；不是16次原生或頭盔試跑。補充稽核`artifacts/replication-final-extra-validation.json`。25程序場的來源／binary仍F、runtime明確C SSD，所有writer停止才一次回F並保留原件，只讀JSON／CSV／bytes、不開SQLite或重寫副本。原5080唯讀仍0.16歷史，Unity serve／登入／安全性提示未碰；無憑證提交。

規則0.8.0、envelope6／world schema1、原header／checksum、素材pins、Tracked資料／pointer／muzzle保持；沒有後端／UI／資產版本契約改動，不重跑歷史654核心／446 HTTP／43世界／217 Chromium、49 UI native／27練習場或人工GPU／DSP／主迴圈診斷，不混算前輪結果。沒有持續25玩家真實移動射擊、跨機／Wi-Fi、完整100敵軍／物件負載、長任務、FPS／聲學、Quest／VIVE／MR或廠商硬體證據，`networkCapacityAccepted`仍false。下一步以實際移動／射擊與更多場景驗證25端同步，再推跨機與設備；完整11項及長期目標保持開發中。

功能提交`54ef0c04c2541bfe555e24214dda5702d153db80`已推送main、遠端一致；提交後重算來源fingerprint仍e8ae6d846dc014e48984a035f2960c043d342a4fe192ff0feaae3891973ba3d0。GitHub #1保持open、原11項與歷史封存連結保留，更新後獨立讀回本文逐字一致。[功能提交CI run41163068604](https://github.com/peca12968/vr-command-center/actions/runs/41163068604)／check124424660203實際failure、steps=null；annotation明示付款失敗或支出上限，工作未開始，沒有雲端測試結果。未改帳務或重跑，本機及原生證據獨立記錄。

## 2026-10-31：25個原生PC程序、場次容量檢查與觀察檔修正

從乾淨`980d0c4`接續無頭盔的PC開發。新增[scripts/check-desktop-capacity.py](../scripts/check-desktop-capacity.py)，操作見[DESKTOP_CAPACITY](DESKTOP_CAPACITY.md)。只改Python／CI／文件，API／UI0.27、Unity0.28.1／code33／NGO26及原0.5秒姿態／1.5秒來源門檻保持。來源fingerprint仍`5eee75868e70237e91b4c6be989c0f4421da98e7e41c5c8adc31878bcb7617b6`，兩份既有receipt及原scene／prefab ID一致，沒有重跑109 EditMode或雙平台建置。

全新隔離API／短效玩家票券，先一個Linked server＋25個真正Windows UDP／NGO client，再精確封存、停止該批程序，另開五個獨立server／每房五個client（同時25人）。全部無圖形、job workers=2、Simulation靜止出生姿態；無時序／GPU／PCM探針、姿態／武器注入、視窗自動化或故意丟包。每房席0–4、不同player／admission／PID／同server connection ID與第六人拒絕均核對。兩模式各60秒穩定期；Pause凍結、Resume tick前進，獨立其他房繼續；之後短暫啟用真正AI攻擊，五房皆有中彈，關閉後End／精確seal／六份CSV及授權SSE回放一致。這不是60秒持續25人移動射擊／戰鬥負載。

成功完成的場次檢查run **`desktop-capacity/20261031-100055-1d0cee1d`**，原執行exit0、20項／六世界、complete=true且cleanup後才stage=passed：

| 世界 | 總幀／逐張核對穩定期回放幀 | 最大擷取UTC來源年齡 | 玩家／中彈／損耗 |
|---|---|---|---|
| Linked | 647／556 | 0.157579秒 | 25／5／100 |
| 獨立1 | 650／557 | 0.166231秒 | 5／1／20 |
| 獨立2 | 651／552 | 0.152643秒 | 5／1／20 |
| 獨立3 | 663／558 | 0.158965秒 | 5／1／20 |
| 獨立4 | 668／557 | 0.160492秒 | 5／2／40 |
| 獨立5 | 684／571 | 0.170800秒 | 5／1／20 |

共3963保存幀、3351張穩定期幀逐張確認全名冊／健康100／正確房間出生位／Simulated且connected、Running未suspend；最後幀與ledger相符。來源年齡不是RTT／client延遲。穩定期後的AI傷害分開統計，玩家射擊耗彈／命中／擊殺均0。主機總實體記憶體34,088,247,296 bytes，最小可用8.031555 GiB，2GiB保留檢查未觸發；不是產品效能保證。

**網路容量驗收仍未通過。**最後離線複查原生日誌發現Linked server有**105行send queue full**；其他原生日誌未有相同字串。原行無時間戳，未知發生階段／client接收影響，不能從world新鮮或回放／報表一致推論下行複本正常，也不能把錯誤行數當遺失封包數。20項僅是伺服器入場／靜止姿態／場次與封存證據，不是零網路錯誤或25人完整驗收。之後摘要明確validationScope、networkCapacityAccepted=false並掃描nativeLogFindings／WARN；只對已停原始日誌離線核對這項最後增補，未再啟動25人或重寫歷史capacity-result。下一步量測各client複本／時效與佇列錯誤階段，再判斷修正，不能盲目照log提高容量。

首輪`094657-3a41bb29`雖20功能檢查完成，卻在F snapshot複製exit1；SSD原件24檔完整，失敗F副本22檔，缺兩個空writer lease。稍後僅另複製兩lease到新probe目錄成功，提示短暫存取競爭，但原shutil詳細錯誤未記錄，**不能確定OS根因**。不覆蓋失敗副本、不補改其stage／cleanup。修正共用snapshot_runtime：全部追蹤writer退出後，最多5秒等待自己的mission／session lease可共享讀取，保持read handles才copytree一次；既有／巢狀目的地拒絕，持續錯誤非零、不改ACL／強制解鎖。cleanup保留有界detail，容量passed移到cleanup成功之後。

首輪練習場回歸`capacity-practice-regression.log`前兩case各9項，第三case因latest-frame.json原位截斷寫入而JSONDecodeError，exit1；finally自行End／收尾，不稱27項成功。共用Venue.save改同目錄唯一暫存完整寫入後replace，Windows分享／PermissionError最多2秒等待；read_json同類存取有界等待但不吞JSON格式錯誤，保存路徑不得逃出自有run。它不是journal的durable flush，也不把所有PermissionError直接歸因分享；持續權限錯誤仍失敗。CSV可指定安全檔名、六場各自保存，原練習場預設不變。

修正後**6項容量規則＋5項觀察檔Python檢查**與語法通過，含真正Windows獨占lease釋放等待及並行JSON讀寫，非11次原生試跑。練習場`desktop-practice-checks/20261031-100622-91f27744` **27項**全部通過；控制台`desktop-venue/20261031-101101-c8454660` launcher／checker皆exit0、**49項UI／native整合**，128幀／最大來源年齡0.152128秒。檢視final-report.png，主玩家損耗40／中彈2／健康60，離場Peer02與替換Peer03保留；瀏覽器SwiftShader／native無圖形，沒有新GPU／聽感證據。

容量24檔、三個練習場及控制台各14檔runtime皆全停writer才回F，cleanup無錯誤無殘留、活動0、world完整及精確戰鬥封存。SSD原件／F副本bytes SHA相同，稽核前後不變；只讀JSON／CSV／bytes，未開原SQLite、未重複複製或修改副本。摘要`artifacts/capacity-validation.json`及`capacity-regressions-validation.json`；容量日誌105行錯誤另明列上述限制。來源／binary仍F，runtime明確C SSD，不是F USB全資料成功。原5080唯讀GET仍0.16／原歷史，Unity serve未碰，憑證未輸出或提交。

未驗各client遠端複本、25個玩家持續真實移動／射擊、繪圖FPS／音訊、跨機／Wi-Fi、Quest／VIVE／MR或廠商硬體；原偶發姿態停頓根因亦未修復。沒有重跑歷史後端／完整瀏覽器／七場五房／8項重連；完整11項與長期目標保持開發中。

功能提交`21d746ef64df0aac41178bd282cdd86f22fd0f2f`已推送main並核對遠端一致。GitHub #1保持open，最新本文與原11項／歷史封存連結均保留。[功能提交CI run41159068469](https://github.com/peca12968/vr-command-center/actions/runs/41159068469)／check124412315156實際failure、steps=null；annotation明示付款失敗或支出上限，工作未開始，沒有雲端測試結果。未改帳務或重跑，本機及原生證據獨立保存。

## 2026-10-31：自有程序CPU時間／週期計數與主迴圈空窗

從乾淨`7083906`接續PC穩定性。新增`pose-process-timing.py`／`analyze-process-timing.py`及helper明確`--process-timing`，**僅讀取本輪三個自有Unity程序**。父程序先借用自己的Popen原handle取得建立FILETIME／執行檔，借用結束不關原handle；probe以QUERY_LIMITED_INFORMATION＋SYNCHRONIZE重新開啟唯讀handle，核對建立時間／完整exe，固定持有同一process object、不追隨重用PID。只查GetProcessTimes／QueryProcessCycleTime與零等待存活狀態，不列舉其他程序、不讀記憶體／堆疊、不開thread、不暫停或改優先級／權限／系統設定。

每50ms查三份累積kernel／user時間與CPU cycles；每次查詢有前後perf_counter／UTC括號，最多5000輪／15000列／240秒，保留最早資料、不環狀覆寫。首份ready在基線前一次寫入，收集期除每250ms檢查自己的finish.request，不輸出樣本。明確finish才完整，先關全部唯讀handle、再一次寫report；child handle由helper持有，正常及失敗finally均收尾，另存process-timing-cleanup。這是外部唯讀診斷，沒有新的Unity或後端程式碼／遊戲資料契約。

兩個真正直接loopback場，原Windows0.28.1／code33／NGO26、API／UI0.27、可見玩家＋無圖形peer＋server。都帶原有pose／loop trace、獨立10ms heartbeat與新CPU probe；無丟包控制／姿態或武器注入，computer-use真實Space三次，兩場HUD均29／28／27、權威耗彈3／命中0／擊殺0／健康100，各**4項真正原生流程**通過：

| desktop-venue／20261031前綴 | 世界幀／最大擷取UTC來源年齡 | CPU取樣 | 原Update／三方邊界共同空窗 | 運行期HUD過期後回ACTIVE |
|---|---|---|---|---|
| `091639-4a14adf0` | 793／0.647925秒 | 1556輪／4668列，原始版本未記cycles | 0.642856／0.6374241秒 | 約0.196110秒 |
| `092109-f446e5f7` | 687／0.577435秒 | 1336輪／4008列，cycleCounterVersion1 | 0.6070879／0.594546秒 | 約0.150704秒 |

兩場長空窗都再次位於after `TimeUpdate+WaitForLastPresentationAndUpdateTime`→before `TimeUpdate`，不是該Wait節點的before→after。loop三報告完整／detached並覆蓋全觀察期，CPU UTC／perf guard最大1.3915／2.1863ms；最長單次查詢1.095／1.905ms，最大同程序樣本分隔53.771／56.773ms。獨立heartbeat最大wake14.3472／18.9925ms，完整覆蓋原Update交集。啟動期HUD提示仍明示在觀察區間外，不當作運行期樣本。

第一場共同loop區間內，各程序都有**13個完整查詢括號**、實際首末跨度約0.606秒，kernel／user累積差皆0；相鄰名義等長前後窗口卻都增加（visible前0.21875／後0.15625 CPU秒，peer0.0625／0.03125，server0.078125／0.078125）。這只能記為noAccountedAdvanceObserved，**零值不證明整個程序被暫停**。因此在原場完全終止後，加入唯讀cycle counter再開第二場，沒有重啟仍存活的工作，也沒有補寫第一場raw cycles。

第二場共同loop區間ticks **639290065068466589–639290065074412049**（0.594546秒），每程序12個內部樣本，實測首末跨度約0.5586秒、且前後皆有樣本包住：

| 程序 | kernel＋user累積增加 | CPU cycles增加 | 11對相鄰內部查詢中cycles增加次數 | 前／後比較窗口CPU秒 |
|---|---|---|---|---|
| 可見玩家 | 0.03125秒 | 22,077,542 | 11／11 | 0.15625／0.140625 |
| 背景peer | 0.03125秒 | 20,440,676 | 11／11 | 0.0625／0.046875 |
| server | 0.015625秒 | 18,748,061 | 11／11 | 0.078125／0.046875 |

這次**三個process的計數在主迴圈共同空窗內仍持續增加**，不支持把整段直接解釋成三程序全程停止；但計數加總全部threads，仍不知道主執行緒本身／其他worker各做了什麼，不能據此說主線程正常、證明特定等待／音效／GPU／I/O／排程／transport根因或已修復。第一場粒度受限的零值不能推成與第二場成因相同或相反。取樣及外部視窗／輸出查詢的擾動仍未排除；下一步須辨識主執行緒與主迴圈外工作／等待，維持原0.5秒姿態及1.5秒來源門檻。

分析只用**查詢UTC括號完全落在區間內**的首末樣本差，不插值、不把外側CPU灌入；上界向外取整至100ns，少於兩點明示insufficientInteriorSamples／null。前後為名義等長比較窗口，實際首末樣本跨度不同，不把累積差直接當相同工作量。GetProcessTimes依[官方定義](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes)用100ns時間單位；[QueryProcessCycleTime](https://learn.microsoft.com/en-us/windows/win32/api/realtimeapiset/nf-realtimeapiset-queryprocesscycletime)是全程序threads的cycles，本工具不換算成秒或CPU百分比。檢查manifest身份逐字一致、角色／輪數／單調計數、handle關閉、完整性／clock guard；失敗或UTC差達50ms不做join，CLI非零。原始第一場缺cycle版本仍讀為0／unavailable，不造零cycles；舊0.28.1有／無loop的兩場資料重分析通過。

**43項Python檢查**通過：9個程序計時（8個合成／規則方法＋1個真正Windows唯讀producer與自己的Python CPU worker）、16個輸入、8個loop、7個heartbeat（其中1個真正timer程序）、3個舊分析；Python語法通過。這不是43次原生或頭盔試跑，Linux的Windows producer項明確skip而非冒充執行；本輪只在Windows本機實際跑。兩場先停外部probe與三份native trace，再獨立End／戰鬥與世界精確seal，world complete、回放／ledger一致、pending=false／活動0，三份cleanup均無錯誤無殘留，CPU report各關閉3個唯讀handle。每場**28檔**SSD runtime全停writer後回F、與保留原件SHA一致，稽核前後不變；只讀JSON／bytes，未開原SQLite或重寫snapshot。摘要`artifacts/pose-cpu-validation.json`。

本輪只改Python／CI與文件；Unity來源fingerprint仍 **`5eee75868e70237e91b4c6be989c0f4421da98e7e41c5c8adc31878bcb7617b6`**，既有Windows／Quest receipts及原scene／prefab ID一致。API／UI0.27、Unity0.28.1／code33／NGO26、rules0.8.0、envelope6／world schema1、header／checksum、profile pins與Tracked資料保持。沒有重跑前輪109 EditMode／雙平台、49 UI／native或歷史後端／完整瀏覽器／五房／重連，不混算為本輪通過數。原5080唯讀GET仍0.16／原歷史，Unity serve未碰。來源／binary仍F、新runtime明確C SSD，非F USB全資料、跨機、MR／Quest／VIVE實機、廠商硬體或25台證據；完整11項與長期目標保持開發中。

功能提交`079f3cec0ffaba5c45b1e05a14060b3763966d2a`已推送main並核對遠端一致；GitHub #1保持open，更新後獨立讀回3687字本文逐字一致，保留原11項與歷史封存連結。[功能提交CI run41155920513](https://github.com/peca12968/vr-command-center/actions/runs/41155920513)／check124402566095實際failure、steps=null，annotation明示付款失敗或支出上限、工作未開始，沒有雲端執行結果。未改帳務或重跑，本機／原生證據獨立記錄。

## 2026-10-31：主迴圈邊界定位、同版對照與0.28.1雙平台

從乾淨`19843f2`接續PC姿態過期。Unity **0.28.1／Android code33**，API／UI0.27及NGO26保持。新增明確選用的`--vr-pose-loop-trace`與helper `--player-loop`，只在原Windows Development pose trace一起安裝；一般啟動、Editor與Android不安裝。從目前PlayerLoop在當時既有節點前後插入自己的兄弟觀察點，不改原type／delegate／native function／loop condition與次序。512節點／32層前置界線、4096個>100ms稀疏空窗、240秒上限；保留最早資料，完整性／截斷獨立。每點讀單調時間、UTC、frame並更新有界計數，不做GPU、PCM、網路或收集期間檔案輸出。停止時只移除目前樹中屬於自己的marker，保留後來的NGO／其他變更；剩餘當幀callback由stopped旗標no-op，不還原舊樹快照。

真正Editor Prepare、**109 EditMode**（新增7）及**同源Windows／ARM64 IL2CPP Quest APK**成功。最終Tests XML 00:59:11–00:59:17 UTC、109／0失敗；Windows receipt 00:49:13、Quest 00:58:40 UTC，來源fingerprint皆 **`5eee75868e70237e91b4c6be989c0f4421da98e7e41c5c8adc31878bcb7617b6`**，目前來源再次計算相同，原scene／prefab GlobalObjectId保持。生成設定／新C# meta已保存，沒有重建Arena或舊profile／pin。首輪Desktop因我新增的`owner`區域變數與參數同名，在Windows Development分支CS0136／exit1；Editor條件未涵蓋該段，不能以109測試代替Windows編譯。失敗日誌`pose-loop-desktop-first-failure.log`保留，修為traceOwner後真正Desktop／Quest及最後Editor檢查皆成功。原有兩個audio名稱遮蔽警告仍在，不稱零警告。

同一新版本、直接loopback、可見玩家＋無圖形peer＋server、真正Space三次（兩場HUD均29／28／27），無故意丟包、姿態或武器注入。建置與最終Editor全停後才開始時序試跑；各有普通優先級獨立心跳、原有三份NativePoseTrace與visible HUD trace，沒有原生GPU讀回／PCM：

另以SDK真正aapt讀本次APK，確認versionName0.28.1／versionCode33、min API32／target35及arm64-v8a；輸出`artifacts/pose-loop-apk-badging.log`。這是APK內容核對，不是裝置啟動或追蹤驗證。

| 場次desktop-venue／20261031前綴 | 模式 | 幀／最大擷取UTC來源年齡 | 結果 |
|---|---|---|---|
| `085931-26eeed5d` | --heartbeat --player-loop | 649／0.763435秒 | 4項真正流程、再次重現HUD過期及三程序共同空窗 |
| `090053-3cd88fd6` | --heartbeat，未啟用loop記錄 | 850／0.288351秒 | 4項真正流程、觀察期無>100ms Update空窗／HUD過期 |
| `090233-64a95e32` | 一般控制台，未啟用任何pose／loop探針 | 164／0.158143秒 | **49項UI／native回歸**、動態名冊／天氣AI／觀戰回放／最終CSV一致 |

啟用場每程序實際**294個邊界（147節點）**；可見／peer／server callback分別1,605,352／1,706,390／1,721,790，時鐘guard最大1.8584ms，三份報告complete／detached且覆蓋完整觀察期。三程序的>0.5秒相鄰觀察空窗，都從 **`TimeUpdate+WaitForLastPresentationAndUpdateTime` 的after（path /0/0）到 `TimeUpdate` 的before（path /0）**，各0.8695835／0.7297024／0.7255199秒，記錄的frame起訖各自相同。這是**between observers**，不能把整段說成在該Wait節點內執行；可見玩家另有真正before→after的0.1291602秒Wait區段，與此共同長空窗分開。server啟動期ExecuteMainThreadJobs約0.136秒在觀察區間外，沒有混算。

原Update三方交集為 **0.727348秒**；新增三方邊界空窗共同交集是 **0.7167323秒**（ticks639290052032020974–639290052039188297）。兩者起點不同，不能混稱同一精確長度。HUD本次STALE約0.125008秒後ACTIVE，poseAccepted=true；發生於shot-1階段，該階段包含真實輸入後的視窗／輸出觀察與確認等待，不能當扣彈／武器處理耗時。外部Space呼叫時間另存根目錄，不當逐packet序號。獨立心跳6166次、64.0195秒、最大wake **16.4326ms**、UTC步進差1.2168ms，完整覆蓋共同區間，沒有>100ms列；不支持全部程序或整個OS一起暫停。

**定位更精確，底層原因及修復仍未證明。**節點名稱只標實際相鄰觀察點，不能假定引擎每次都依教科書框架順序執行，更不能把wall time當CPU／GPU／音效／排程或transport歸因。未啟用loop的同版單次對照乾淨，不能排除新記錄本身的成本／擾動或特定外部操作；舊版沒有新marker也曾有同類提示，但不能只由症狀相同斷言底層成因相同。接續針對這兩個觀察點間的引擎／訊息處理與各自有程序執行狀態取證，維持原0.5秒姿態與1.5秒來源門檻，不臆測「修正」引擎等待設定。

分析新增pair／系統名稱／計數、gap與最大值一致、時鐘與完整觀察覆蓋檢查；missing／partial／attached／截斷拒絕，UTC偏差達50ms不做loop phase／join，CLI非零。原生fixture完成metadata也是CLI必要條件。未啟用場首次分析exit1，實際發現JsonUtility把null class寫為完整的**空預設物件**，不是JSON null；保留原raw檔，以fixture明確playerLoop=false且物件逐欄等於空預設才忽略，不能藉disabled隱藏callbacks／失敗／非空資料。新增實例反例後兩場重新分析exit0，loop未啟用回null；舊無loop資料亦重新讀取通過。**33項Python檢查**通過：8個loop分析、15個輸入、7個心跳（含一個真正獨立timer程序）、3個舊分析；不是33次原生或頭盔試跑。

兩射擊場皆耗彈3／命中0／擊殺0／健康100，先明確finish三份trace再獨立End／戰鬥與世界精確seal。一般控制台回歸主玩家損耗40／中彈2／健康60，保留離場Peer02及替換Peer03，CSV全部指標／封存界線與ledger／回放一致；檢視`operator-ui/final-report.png`，瀏覽器觀戰為SwiftShader、native client無圖形，不稱新GPU／DSP探針或人工聽感。一般runtime沒有診斷report檔。三場world complete／pending=false／活動0／cleanup無錯誤無殘留；射擊場另heartbeat-cleanup無殘留。24／24／14檔SSD runtime在writer全停後回F，與保留原件SHA相同，稽核前後不變；僅讀JSON／bytes，未開原SQLite或重寫snapshot。摘要`artifacts/pose-loop-validation.json`。

不變：API／UI0.27、NGO26、rules0.8.0、envelope6／world schema1、原header／checksum、全部素材pin、追蹤資料與pointer／槍口。沒有重跑歷史654核心／446 HTTP／43世界／58 Node／217 Chromium、七場五房或8項入場重連，不混入本輪數量。原5080唯讀GET仍0.16／原歷史，unity CLI serve未碰。來源／binary仍F，明確C SSD全新runtime；非F USB全資料、跨機、MR／VIVE／Quest實機、廠商硬體或25台證據。完整11項及長期目標保持開發中。

功能提交`2c79a7308b5923dd370e31e81121b91953370b1c`已推送main、遠端一致；GitHub #1保持open，更新後獨立讀回3581字本文逐字一致，保留原11項及歷史封存連結。[功能提交CI run41153866259](https://github.com/peca12968/vr-command-center/actions/runs/41153866259)／check124396246125實際failure、steps=null；annotation明示付款失敗或支出上限，工作未開始，沒有雲端執行結果。未改帳務或重跑，以上本機／原生證據獨立記錄。

## 2026-10-31：獨立程序心跳與視窗／輸出輪詢對照

從乾淨`bbde0a1`接續PC偶發姿態過期調查。新增`scripts/pose-heartbeat.py`，由原生檢查器以明確`--heartbeat`啟動自己的獨立、一般優先級Python程序，每10ms sleep後量perf_counter、UTC與process CPU；沒有遊戲／網路／UI接入，也不調整優先級、計時器或系統設定。只在記憶體保留>100ms空窗及每秒clock anchor，4096列／256 anchors／240秒上限，明確finish才完整；報告序列化在觀察結束後。檢查器持有Popen handle，正常與失敗finally均收尾，另保存heartbeat-cleanup。沒有改C#、API／UI0.27或Unity0.28／code32／NGO26及原0.5／1.5秒門檻。

增加`--observation-only`的安靜基線→window-review→安靜收尾；過程不得按遊戲鍵，window-review.done只確認觀察。四個完成場皆直接loopback、兩個真正client＋server、原有三份NativePoseTrace及visible HUD trace，無LossGate、姿態／武器注入、原生GPU讀回或PCM：

| 本輪desktop-venue識別 | 實際操作 | 世界幀／最大擷取UTC來源年齡 | 心跳次數／最大wake間隔 | 結果 |
|---|---|---|---|---|
| `082241-c9a91e27` | 15秒基線，5次文字查詢＋5次截圖，無遊戲鍵，再安靜15秒 | 656／0.171283秒 | 6177／18.754ms | 觀察期無>100ms原生Update空窗、無HUD過期 |
| `082536-8cb741cb` | 10秒基線，真正Space三次，HUD29／28／27 | 772／0.612307秒 | 7389／13.348ms | 重現三Unity共同0.7017494秒空窗及HUD過期 |
| `083531-90e11646` | 無UI／遊戲鍵，接續時僅讀log，不能當完整輪詢對照 | 1184／0.166302秒 | 11669／14.518ms | 觀察期無>100ms原生空窗／HUD過期 |
| `083806-990e7dae` | 5秒基線，同一原執行連線連續6次空輸出poll，每次約5秒，無UI／遊戲鍵 | 552／0.162059秒 | 5166／13.205ms | 觀察期無>100ms原生空窗／HUD過期 |

完整目錄皆前綴`20261031-`。第一場保留外部10次查詢時間，先前初次activate及合併查詢另明示；最後一場保留6次實際unified-exec poll起訖時間。中間無UI場原exec handle在接續時不可取回，因此只以原PID、command line與log確認它仍在執行，再正常確認完成，沒有因缺少handle重啟；等原PID消失、sealed／summary及兩份cleanup完整後才另開匹配poll場。最後一場原handle持續保留並取得terminal exit0。這些乾淨對照不排除特定時機／組合操作、診斷或外部工具影響，也不能證明舊問題已修復。

射擊場可見玩家／peer／server最大Update觀察空窗為0.777354／0.702231／0.702255秒，共同區間ticks **639290031824251115–639290031831268609**（0.7017494秒）。同ID server收件最大空窗可見0.803226、peer0.714325秒；HUD於過期後約0.088214秒回ACTIVE，poseAccepted仍true。**獨立心跳完整覆蓋該共同區間，整場最大wake間隔僅13.348ms、沒有>100ms列**，UTC／perf步進差最大1.456ms，不能稱整個OS／全部程序同時暫停。仍不能從Update間隔歸因CPU、Unity引擎共用資源、選擇性排程、音效、GPU、I/O或transport；未量測的PlayerLoop區段與外部影響繼續取證，不臆測修復。啟動期HUD短暫STALE獨立標記withinPoseObservation=false，沒有當成本輪運行期重現。

分析器增加心跳完整性、單調counter／UTC guard、覆蓋區間與三方交集；不完整／缺失報告拒絕，UTC偏差達50ms時不做心跳join，不能以未覆蓋的時間宣稱獨立程序正常。前兩場raw report尚無exact起訖UTC欄位，使用首末clock anchors的保守覆蓋；不補寫或重造舊raw檔。後兩場及真正producer單元程序已有明確起訖欄位。階段自動支援window-review／quiet-after，舊無心跳075207場重新分析exit0且heartbeat=null，保持相容。

**7項心跳檢查**（6個合成分析方法及1個真正獨立timer程序）、**12項輸入分析反例**及原**3項分析回歸**通過；Python語法通過，CI加入心跳步驟。這22項不是22次原生／頭盔試跑。四個完成原生場各4項流程、三份trace明確finish後獨立End／世界與戰鬥精確seal，world complete／pending=false／活動0、回放／ledger一致；無輸入三場耗彈0、射擊場3，健康100。每場24檔SSD runtime在全部writer停止後回F，與保留原件SHA一致，稽核前後不變；只讀JSON／bytes，未開原SQLite或覆寫snapshot。摘要`artifacts/pose-heartbeat-validation.json`。確認本輪沒有剩餘native／heartbeat／helper程序，未碰unity CLI／正式5080。

首輪`081944-8218348a`未完成：外部視窗觀察在原60秒人工作業等待內未確認，helper timeout／exit1後關窗，第五次查詢因此找不到原視窗。失敗log與資料保留，核對原程序終止、無殘留視窗後才開新場；將**診斷人工作業確認上限**調為120秒，不是放寬0.5／1.5秒遊戲政策，240秒trace上限仍維持。此場不列入上述完成結果。

本輪僅Python診斷／分析、CI與文件，沒有重跑歷史後端／瀏覽器／102 EditMode／APK。Unity fingerprint仍`792a3aaac9a7903159718a898324def8f6ba4769f908f1f46f30a6c77744c725`，Windows／Quest既有receipts及原scene／prefab ID一致；原5080唯讀GET仍0.16／原歷史。來源與binary在F、全新runtime明確在C SSD，非F USB全資料、跨機、頭盔／MR／VIVE／廠商硬體或25台證據。完整11項與長期目標保持開發中。

功能提交`575216bc1820872bcf953d8f0567527cb2176771`已推送main並核對遠端一致；GitHub #1保持open，更新後獨立讀回3200字本文逐字一致，原11項與歷史封存連結保留。[功能提交CI run41151496751](https://github.com/peca12968/vr-command-center/actions/runs/41151496751)／check124388817676實際failure、steps=null，annotation明示付款失敗或支出上限、工作未開始，沒有雲端執行結果；未改帳務或重跑。本機檢查與原生證據如上，不把雲端未啟動當作通過。

## 2026-10-31：目前版本雙玩家姿態提示重現與三程序時序

從乾淨`e5fa9fa`接續PC穩定性。舊時序原生證據在Unity0.26.1、未含後續射擊音效及完整玩家人物；本輪新增[POSE_TIMING.md](POSE_TIMING.md)的`check-desktop-pose-input.py`／`analyze-pose-input.py`，用既有API／UI0.27及Unity0.28／code32／NGO26。自己的房間3、server、可見玩家及無圖形同伴直接loopback連線，沒有LossGate、故意丟包或payload改寫；三程序明確啟用原有NativePoseTrace，可見玩家另用原HUD trace。沒有改C#／正式輸入、防瞬移、傷害或0.5／1.5秒門檻，沒有原生GPU讀回／PCM／麥克風。

`desktop-venue/20261031-075207-5621fa8a` **4項真正原生流程**通過。先15.171秒無射擊基線，透過computer-use真實視窗Space三次，HUD依序29／28／27；第二發前亦實按W一步，沒有姿態／武器RPC注入。三份trace在觀察結束後明確finish，complete=true／truncated=false，再獨立End與戰鬥／世界精確seal；1121幀、最大擷取UTC來源年齡0.624341秒、健康100／耗彈3／命中0／擊殺0，回放／ledger一致，pending=false／活動0／cleanup零錯誤、無追蹤子程序。22檔SSD runtime在writer全停後回F，與保留原件SHA一致；分析只讀JSON／檔案bytes，不開原DB或重寫snapshot。摘要`artifacts/pose-input-validation.json`。

這次**取得真正POSE STREAM STALE樣本**，而非只重跑乾淨基線。HUD每渲染幀的五次狀態轉換保留，過期約0.133828秒後ACTIVE，poseAccepted=true／connected=false與原過期政策相符，沒有把它當姿態拒絕。可見client connection2，peer connection1；分析按ID篩server，不能用兩人交錯流量掩蓋其中一人的空窗：

| 觀察 | 可見玩家 | 背景同伴 | 伺服器 |
|---|---|---|---|
| 基線最大RPC呼叫／同ID入口 | 55.741／55.718ms | 55.801／57.281ms | 無發布過期或>100ms主執行緒空窗 |
| 全觀察最大RPC呼叫／同ID入口 | 0.812241／0.811725秒 | 0.744546／0.745023秒 | 兩個ID均曾發布過期 |
| 最大Update觀察空窗 | 0.810708秒 | 0.719134秒 | 0.646577秒 |
| 發布過期時接受姿態年齡 | 0.711310秒 | 0.700172秒 | 保持原0.5秒政策 |

三程序空窗共同交集為**0.6425932秒**，UTC2026-10-30 23:53:08.870723–23:53:09.513316（本機10/31上午）。第一發彈藥29已於23:53:04.242605被世界取樣觀察，第二發彈藥28在23:53:38.753050才被觀察，交集在兩發之間，並非扣彈當刻。這不是每packet／每發精確CPU時間；shot階段包含操作者觀察／確認等待。UTC對Stopwatch步進差最大1.5285ms，通過本機join guard；已量測的server記錄／發布區段在觀察期最長2.7402ms，尚未涵蓋停頓處，不能將全trace含啟動期18.8318ms與此區段混算。

**尚未證明底層根因或修復。**MainThreadGap只量兩次Update之間wall time，不是CPU耗時或整個OS暫停的證明。三程序同時缺口不能直接歸因於音效、GPU、磁碟、排程器、NGO／transport；也未排除診斷本身及外部computer-use視窗查詢／輸入的影響，不能推論一般人操作或頭盔同樣成因。這個新樣本改變下一步：對未量測的PlayerLoop及獨立時間心跳做對照，維持原警告與門檻，沒有把這輪診斷稱為修好。

新分析保留跨階段邊界的收／發間隔，按connection篩BodyConnection；connection變動拒絕分析，不把重連併成單流。三份trace完整性獨立驗證，HUD末尾沒有下一狀態明示rightCensored／未知duration，UTC步進達50ms時phases與三方join留null且CLI非零。**10項合成反例**通過，涵蓋peer掩蓋／邊界間隔／三方交集／缺少交集／時鐘步進／connection變更／trace截斷／誤錄GPU／HUD未知尾端；另原**3項時序分析回歸**通過。這13項是合成分析規則，不能當13次原生或頭盔試跑。CI新增新單元測試與Python語法步驟，py_compile本機通過。

本輪只新增Python診斷／分析及文件／CI，沒有重跑前輪後端／瀏覽器／102 EditMode／APK。Unity source fingerprint仍`792a3aaac9a7903159718a898324def8f6ba4769f908f1f46f30a6c77744c725`，既有Windows／Quest receipts及原scene／prefab識別一致；不改schema、資源pin、header或checksum。原5080確認仍API0.16／原歷史，未替換。全11項保持開發中；這是同機Simulation量測，不是Quest／VIVE、MR、廠商硬體、跨機或25台效能證據。

功能提交`54a724258e1407515bcf14365e0724b95526146c`已推送main並核對遠端；GitHub #1仍open，更新後獨立讀回3072字本文一致，原11項及歷史封存連結保留。[功能提交CI run41148997649](https://github.com/peca12968/vr-command-center/actions/runs/41148997649)／check124380747557實際failure、steps=null，annotation明示付款失敗或支出上限、工作未開始，沒有雲端執行結果；未改帳務或重跑。下一步繼續對未量測區段取證，沒有宣稱修復或完成整體目標。

## 2026-10-31：修復電腦練習場入口、五人同房與關窗封存

從乾淨`35bff7f`接續PC主線。實際執行舊`start-desktop-demo.py`搭本輪既有API0.27，程式在建立場次前因仍要求**0.21.0**而exit1，保留`artifacts/practice-old-launcher-failure.log`。原DESKTOP文件另仍寫0.16，兩者均已修正；沒有改回舊reader或替換5080歷史來配合。

練習場改共用已驗證Venue：API0.27版本gate、Windows receipt／當前Unity source fingerprint及嵌入Transport293檔檢查、短效admission票券、同一份CSV／世界／戰鬥精確seal與原擷取UTC1.5秒門檻。明確`--runtime-root`可將全新runtime放C SSD，來源／binary／設定仍F；每程序job workers預設2，沒有當作F USB或姿態偶發的修復。Venue新增受限artifact_family，預設desktop-venue及其latest pointer保持；練習獨立desktop-demo／latest-desktop-demo-path.txt，不覆蓋五房入口。來源／API／UI及NGO版本均不新增，本輪沒有任何Unity或後端產品變更。

每位client以admissionId命名，不再沿用同房號互相覆蓋；支援主玩家加0–4同伴，同房最多5個真正PC程序。正常關窗移除已停止handle，End後退場其餘自有client，只等API／server精確封存，不讓已關窗client誤觸live-child fence。控制台End、end.request、到時及Ctrl+C保留既有語意，duration為包含Pause的wall-clock上限。完成後從授權report.csv取得CSV，以標準csv／Decimal檢查玩家集合、身份／房間、全部指標、來源及stream尾界，再保存final-report.csv／SHA。舊summary頂層world／statistics／replayStatisticsMatch保留，新增stopReason／runtime／workers／finalReport；cleanup失敗仍exit非零，資料／原件保留。

新增可重現的`scripts/check-desktop-practice.py`。**27項真正無圖形流程**及**9項實際視窗流程**通過，來源皆Simulation；不是5台硬體、跨機或25台測試：

| 場次／結束方式 | 玩家／世界幀 | 最大來源年齡 | 結果 |
|---|---|---|---|
| `072944-8717ce7a`／控制台End | 5／48 | 0.145045秒 | 五席全部連線、Pause凍結tick／Resume、精確seal／CSV及14檔snapshot一致 |
| `072953-e2edc784`／end.request | 1／43 | 0.140979秒 | 同上單人收尾，stopReason=endRequested |
| `073000-1d385f64`／60秒到時 | 2／578 | 0.164424秒 | 同上雙人，stopReason=durationElapsed，不冒充遊戲內精確扣Pause倒數 |
| `073121-5b3def38`／正常關窗 | 2／582 | 0.303067秒 | 真正W／Space／R與Alt+F4；stopReason=windowClosed、精確seal／CSV及14檔snapshot一致 |

四場位於`artifacts/desktop-demo/20261031-<表內識別>`，活動0／pending=false／cleanup零錯誤且無剩餘追蹤程序，世界complete及回放／ledger一致。無圖形27項在`desktop-practice-checks/20261031-072944-7d9e81ba`，實際視窗9項在`20261031-073121-140758c9`。用computer-use技能的真實視窗按鍵；接受的玩家從(25,1.65,-3)移到(25,1.65,-2.95)，一次Space耗彈1／命中0／擊殺0／健康100，R完成後HUD及接受狀態30／89。普通遊戲影像／HUD已檢視，不是新的GPU探針或音效量測；射擊後一張擷取出現POSE STREAM STALE、下一張恢復，原0.5秒政策、歷史偶發根因均未改或證實修復。關窗後沒有強制停止正式服務或注入姿態／RPC。

另**3項preflight反例**通過：刻意錯誤fingerprint的自有假exe／receipt在新建run／API前以exit2拒絕、第六個玩家由參數拒絕、artifact family路徑穿越在建立資料前拒絕。新加入starting階段於API／native啟動前提供本輪目錄，checker的startup觀察界線涵蓋既有API／recording／admission等待；它不是放寬來源新鮮度，未就觀察逾時重新啟動程序。

**3項受控原生失敗檢查**亦通過：`20261031-073747-3ab76c77`在ready後，以launcher parent PID、exe絕對路徑、本輪config目錄及practice-client名稱確認兩個自有無圖形client，才停止其中一個。launcher實際exit1／stage failed，沒有完成summary；cleanup仍精確封存、停止全部自有程序且無錯誤，journal／snapshot保留，不能把這場當正常完成。詳見`artifacts/practice-expected-client-failure.json`。

共用Venue預設路徑的**49項既有UI／native回歸**重新通過，`desktop-venue/20261031-073345-0ae94b64`，166幀／0.172879秒，動態名冊、操作員天氣／AI／觀戰／回放及CSV一致、活動0／cleanup零錯誤；client無圖形、觀戰SwiftShader。全部正常練習與此回歸的SSD runtime在writer全停後各14檔複製回F，SHA與保留原件一致；稽核只讀檔案bytes／JSON／CSV，沒有開原DB或再覆寫snapshot。摘要`artifacts/practice-validation.json`。

僅Python啟動／檢查器、文件及CI語法步驟變更，`py_compile`通過；Linux CI此步不代表Windows程序曾執行。Unity fingerprint仍`792a3aaac9a7903159718a898324def8f6ba4769f908f1f46f30a6c77744c725`，Windows／Quest receipts及原識別保持，API／UI0.27、Unity0.28／code32／NGO26、rules0.8.0、header／checksum不變。沒有重跑前輪654核心／446 HTTP／43世界／58 Node／217 Chromium或102 EditMode／APK，沒有將歷史檢查計入本輪。原5080再次確認0.16／原歷史。本輪修復的是可操作入口與收尾；完整人物／動畫／聲學、複雜通路、長任務／跨機，以及頭盔／MR／VIVE／硬體／25台仍分別待驗，完整11項目標保持開發中。

功能提交`e397b443254ec5ccaad16150dcfc706a2463d94f`已推送main並核對遠端一致；GitHub #1仍open，更新後獨立讀回3152字本文一致，原11項及歷史封存連結保留。[功能提交CI run41146227105](https://github.com/peca12968/vr-command-center/actions/runs/41146227105)／check124371855173實際failure、steps=null，annotation明示付款失敗或支出上限，工作未開始，沒有雲端執行結果；未改帳務或重跑。

## 2026-10-31：最終任務 CSV、封存界線與原生報表整合

從乾淨 `95eae21` 接續PC主線，新增 [REPORTS.md](REPORTS.md) 的 `GET /api/sessions/{id}/report.csv` 與「下載最終報表 CSV」。API／UI **0.27.0**，reportVersion1；Unity仍0.28／code32／NGO26。這是最終戰鬥 ledger 匯出，包含離場玩家、原任務ID／名稱、來源、throughSequence、stream ID／接受尾界與原11項中的全部玩家統計，不依目前名冊重算。不宣稱世界錄影已完整、頭盔在線或25台通過。

FinalReport在同一session gate內授權、檢查Ended及combat精確seal後取metadata／statistics，拒絕進行中、Pause、僅End及尚未seal的尾端。來源／房間先檢查；HTTP明確傳入Actor，GameServer403／未驗證401。Linked房控沿既有全場讀取政策，外房獨立場拒絕。未綁stream的已結束歷史可匯出；合法空stream保留宣告來源及尾界0，無來源明示None。空場只有Session metadata列，不造玩家。沒有新的持久資料、事件或schema。

CSV為UTF-8 BOM、全欄引用、逗號／CRLF，數字invariant、accuracyPercent沿用原兩位小數；任務秒數標planned，不冒充扣Pause的實玩時間。公式開頭／控制文字只在CSV加單引號，原名字與JSON不變。重複下載、接受tail／seal重試與SQLite重啟位元組一致；不是簽章證書。HTTP attachment、no-store，檔名只含UUID；沒有憑證／地址或伺服器匯出檔案。前端以Bearer fetch下載、抑制重複並釋放ObjectURL；generation＋login epoch阻擋切離再回同場／登出再登入晚回應。讀header及blob後重查，錯誤MIME不下載，409可重試，當前401登出。一般輪詢不抹掉下載成功／錯誤文字。

locked restore、Release build **0警告／錯誤**、真正執行VrCommand.Checks **654項**（新增25）、**446 HTTP、43世界、58 Node／217 Chromium**全部通過。包含並行seal只能觀察拒絕或完整快照、返回陣列不可改ledger、離場／零發／空場、fr-FR小數、CSV公式／引號／換行、SQLite及HTTP真正重啟／key輪替後完全相同、實際瀏覽器下載bytes／檔名與read-only序號、切離再回及重登入晚回應、409／錯誤MIME／401與既有回放／素材回歸。API／UI來源與該次隔離輸出的三個JS／HTML逐位核對，檢視 `artifacts/console/final-report.png`；軟體WebGL不是原生GPU證據。

真正 Windows operator run **`desktop-venue/20261031-072120-4e03e4bb`**，**49項UI／native**（新增2）通過。使用現有同源0.28原生server／clients、Simulation rigs及自己的API0.27／C SSD runtime；不是注入姿態或新GPU／頭盔測試。163幀、最大來源年齡 **0.176034秒**，世界complete、回放／ledger一致、pending=false、活動0、cleanup零錯誤且無追蹤子程序。CSV含Operator01／已移除Peer02／替換Peer03共3列，throughSequence21／combat尾界2，Operator01中彈2／耗損40／健康60，三人耗彈／擊殺皆0；每項與該次ledger及封存回放一致。真正下載CSV SHA `f0de1ae7c3b095c02f722bb10e8c5eaebee2bb19ca801d434345bb85a727d0b5`，獨立Python標準csv parser再次核對。原生流程觀戰瀏覽器仍SwiftShader，client無圖形，沒有新增GPU／聽感證據。

writer全停後helper回F的runtime-snapshot共14檔與保留C SSD原件SHA一致，唯讀稽核前後皆保持；本輪沒有直接開原DB／snapshot SQLite，沒有二次覆寫snapshot。來源／binary仍F，非F USB全資料或跨機／25台驗收。`artifacts/report-v1-validation.json`保存本輪完整摘要。Unity source fingerprint仍 `792a3aaac9a7903159718a898324def8f6ba4769f908f1f46f30a6c77744c725`，既有Windows／Quest receipts及原scene／prefab識別相同；沒有改Unity來源／資產pin／shader、rules0.8.0、envelope6／world schema1／原binary header／checksum，未重建Editor／102 EditMode／APK，前輪結果保持歷史證據。只同步API／UI及兩個PC helper的明確版本gate，不需因報表重新生成場景。原5080確認仍0.16／原歷史，沒有替換。

首輪HTTP在既有無效憑證啟動檢查等待退出10秒逾時，finally另有臨時server.log sharing violation；失敗 `artifacts/report-v1-http.log`保留，未放寬timeout／修改憑證政策。確認本輪owned dotnet已無存活後，正常完整重跑446通過，根因未證實。瀏覽器先有214通過；補輪詢提示保持及精確MIME後，下載比對另曾失敗，記錄在report-v1-browser-selection-failed.log。檢視發現selectSession等待背景更新前尚未清掉舊場狀態，改為立即取消下載／清統計／隱藏面板，再以selection epoch只接受最後選擇；新增明確hold背景更新的兩個回歸。新測試的首輪unroute早於delayed fulfill，觸發Route already handled，失敗report-v1-browser-gate-failed.log保留，改等fulfill完成才unroute；未放寬產品政策或斷言。最終58／217全部通過，包含text/csv-fake拒絕。最終原生49重新執行；先前071253-1dc01ef2的49項／143幀／0.296376秒證據及14檔snapshot另保留，不混算成最終場。完整11項仍開發中，接續完整人物／動畫／聲學、複雜通路、長任務／跨機及實機／MR／硬體／25台，沒有因報表完成縮減目標。

功能提交 `46794a09d5e7d6439c704e537affc81fab5b4e1d` 已推送main並確認遠端一致；GitHub #1保持open，更新後獨立讀回2955字本文一致，保留原11項、完整目標及原63864字封存連結。[本次CI run41144100763](https://github.com/peca12968/vr-command-center/actions/runs/41144100763)／check124365009147實際failure、steps=null，annotation明示帳戶付款失敗或支出上限、工作未開始，沒有雲端測試執行結果；未改帳務／重跑。完整目標繼續進行。

## 2026-10-31：軍事玩家人物、保存步態與桌面換彈雙臂

從乾淨 `35ad78e` 接續無頭盔PC主線，新增 [PLAYER_BODY.md](PLAYER_BODY.md) 的 `player-body-v1`：原創頭盔／護目鏡、背心／彈袋、雙腿／靴及桌面雙臂，404面、五個Mesh／一材質，SHA `1035ca0dffafc31226616485c58ef530d8e7b809feef2b5e461229424bc9703b` 固定。原步槍／手套／閃光／NPC／掩體及獨立combat-audio-v1沿用，八個既有外觀與reader保留。

API／UI **0.26.0**、Unity **0.28.0／Android code32／NGO26**。header playerPresentationVersion新1／缺失0，每玩家hasPlayerPresentation及walking明確保存；新profile要求原敵軍／武器／雙方fire版本1。NGO既有walking欄位新增玩家語意並與presentationTick原子複製，需來源／API／UI／全部遊戲程序一起更新，不降reader。rules0.8.0、envelope6、mission／world schema1、票券2、environment1及原始binary header／checksum保持，沒有更動傷害、射速、命中、碰撞、0.5秒姿態／1.5秒世界新鮮度或admission。

只有原本接受成功、Running／存活／連線玩家的平面移動>1mm會標記移動tick，四tick內walking；轉頭／高度、拒絕及Preparing不觸發。保存tick%12產生±18度對向腿旋轉，Pause不推進步態時鐘，但原頭手追蹤仍可更新。根在頭部平面座標／地面Y0、軀幹垂直比例eyeHeight／1.65，身向取頭部yaw；這是裝飾性三點推算，不是腰腳追蹤、屈膝或腳掌IK。桌面腕點跟隨既有合成手套／保存換彈時鐘，兩節臂可延展、超出範圍隱藏；Tracked不把pointer當握點、不合成雙臂或改追蹤資料。只對新視覺的quaternion副本正規化，本玩家body隱藏且不求解live姿態，原接受旋轉容差／界線保持。

真正Prepare、**102項EditMode（0 failed／skipped）**、Desktop成功，原scene／prefab ID保持，未RebuildArena。測試覆蓋共用資源最後lease釋放、實際頭／腿／腕Mesh矩陣、NGO walking／Equals、owner隱藏、合法非單位四元數、JsonUtility新／舊契約，以及真正保存prefab的Visual子物件。Desktop receipt UTC2026-10-30T22:28:56.4385532Z，fingerprint `792a3aaac9a7903159718a898324def8f6ba4769f908f1f46f30a6c77744c725`。locked restore／Release build零警告錯誤、**629核心、403 HTTP、43世界、58 Node／201 Chromium**通過；涵蓋接受／拒絕／idle／Pause步態、新資料不能漏標記、舊外觀、C#／JS向量及實際Mesh跳轉還原。瀏覽器為SwiftShader，不當作原生GPU。

最終 `desktop-venue/20261031-063112-834f3646` **4項真正雙PC流程**通過。第一玩家實際S／Down／Right到z=-4.504、heading54／pitch15，第二玩家實際W、Space一次及R，六張自己的observer GPU PNG均已檢視。新頭盔／背心／腿／靴可見，舊綠色頭手標記已在Visual子層正確停用；只改執行時Renderer，不改prefab／joint Transform。Probe只在明確Windows Development／可見untracked owner及全新絕對目錄安裝，600秒／8張／900萬像素，沒有PCM／麥克風／OS畫面／RPC或姿態輸入；一般／Editor／Android不安裝。

| 原生取樣 | 實際結果 |
|---|---|
| Running移動 | tick4496、walking=true、stride=-15.58844°，真正步態PNG。該幀遠端頭部仍插值中，與保存的接受位置相差0.02246647m；不能把它稱為精確保存的繪製幀 |
| 兩張Pause | 同tick4499／walking=true／stride=-9°，步態與時鐘相同；端點逐軸最大差2.38419e-7m，在1微米界線內。回到Running的tick4522為idle／stride0 |
| 換彈Pause | tick4787、reloadUntil4790，即第27tick；左腕依原換彈回位動作改變，非峰值抽匣畫面。槍口／原動作／彈藥規則不改 |
| 任務封存 | 2536幀、耗彈1／命中0／擊殺0／雙玩家損耗0／健康100，回放與ledger一致、pending=false、活動0；最大來源年齡0.243825秒 |

六個取樣已在**額外完整SQLite副本**稽核。兩張Pause與換彈為相同保存tick，頭部／腕點與保存資料求解的最大世界端點差約3.15e-7m。Running／idle有兩張NGO取樣比最近10Hz保存packet晚1tick，按實際觀察tick及相對腕點比較；沒有假稱每張都精確對到保存幀。原件及F snapshot的24檔SHA於稽核前後保持，沒有直接開原DB／SHM。

新增47項控制台UI／native整合，`20261031-063618-c4df481b` 167幀／最大來源年齡0.308984秒；含真實來源的404面人物及封存後頭部／步態／腕點核對，client為無圖形、瀏覽器SwiftShader。普通無probe的 `20261031-063915-8b74dc78` 七場五房獨立／重用／封存後Linked通過，583幀／0.200379秒；`unity-admission/20261031-063937-7264fe3b` 八項無圖形入場／撤銷／transport釋放／同admission重連通過，373幀。成功組cleanup零錯誤、活動0，三組venue自己的SSD runtime在writer全停後回F，24／14／26檔與保留原件SHA一致；來源／binary仍F，非F USB全資料或跨機／25台驗收。

失敗及修正保留：首輪向量輸出Yaw／yaw大小寫衝突，改為inputYaw後Node通過。原生首輪150秒視角定位超時，次輪在單次W已回idle後要求非零Pause而等待超時；其後改直接擷取真正Running步態，保留原四tick呈現政策。原生圖另揭露head／hand Renderer在Visual子物件，修正層級停用並新增保存prefab回歸。`060538-b116deea` 是明確停止自有target的失敗組，cleanup另有seal錯誤、原資料保留，不列為通過；其他失敗組及成功組分開。`061347-f54c8112` 的暫停字典逐位相等斷言被2.38e-7m浮點差觸發，改明示1微米門檻及保存實測差值。`061931-a2d2b497` 診斷請求原位寫入造成Sharing violation，改同目錄原子replace、reader共享ReadWrite／Delete，helper優先讀終止report而非繼續等舊status；最終來源／102 Tests／Desktop及原生均重跑。HTTP首輪無效憑證程序10秒退出逾時，未放寬timeout，後續完整403／43通過；未證實根因。

Quest首輪在Bee後處理exit3／Editor exit1，UnityLinker成功且沒有具體編譯錯誤；已保存Editor／Bee／buildreport失敗檔，程序終止且F空間足夠後以同來源重試，沒有改Library／ACL／安全設定。重試Editor exit0，Quest receipt UTC2026-10-30T22:52:26.8221840Z，與Desktop相同fingerprint及原scene／prefab ID。APK46,309,126 bytes、SHA `a445f8e1e18d9114df5787dda60d3069ec5346ebb0ce6564f14155d2e2865583`，v2簽章、min32／target35、code32／bundle0.28.0及六個ELF64 AArch64庫含libil2cpp已核對；沒有手動重封裝／重簽或頭盔安裝。成功的三組venue及admission共39個原生／API log未見指定NullReference／MissingReference／ObjectDisposed／IndexOutOfRange／Shader error，完整本機證據在artifacts/player-body-validation.json。原5080仍API0.16／原歷史，未替換。完整11項目標保持開發中；第一人稱全身、真正腰腳／手指及完整動畫、複雜地形、原偶發姿態原因、跨機，以及Quest／VIVE／MR／廠商硬體／25台仍分別待驗。

功能提交 `241f2acb0dc4e4b8ca6313f1407c4576c9de1090` 已推送main並核對遠端。GitHub #1已更新，讀回open／3470字與送出本文完全一致；原11項範圍與63864字封存留言連結保留。[CI run41141572882](https://github.com/peca12968/vr-command-center/actions/runs/41141572882)／check124356841079實際failure、steps=null，annotation明示付款失敗或支出上限，工作未開始，不能稱雲端測試通過。另有ubuntu-latest遷移通知；未改帳務或重跑。

## 2026-10-31：接受射擊事件的玩家／敵軍空間音效

從乾淨 `f25b097` 接續使用者「無頭盔，先繼續電腦端」。新增獨立固定的 `combat-audio-v1`、原創合成步槍／手槍PCM與Unity／瀏覽器共用接受事件游標；規範、操作及pin見 [COMBAT_AUDIO.md](COMBAT_AUDIO.md)。API／UI **0.25.0**、Unity **0.27.0／code31／NGO25**。header combatAudioVersion缺失0／新來源1，必須有player／enemyFireVersion1；actor presentationRunning與原fire欄位原子複製。固定player-fire-v1與八個舊幾何profile、rules0.8.0、envelope6、mission／world schema1、票券2及environment1保持。協同更新來源／API／UI／全部遊戲程序，不能降reader或重寫歷史header／checksum。

聲音只來自已接受的新sequence，保留世界槍口；最多age3 tick／相鄰觀察差10 tick，首次加入、seek、長缺口、重新啟用先baseline，Pause／Ended停止。每listener32個同房空間聲源，1–25m線性衰減／doppler0；滿載重用最舊。沒有本地射擊預測、傷害／射速／碰撞／姿態規則改動，pointer／Tracked不搬動。瀏覽器明確點音效才啟用，換錄製／登出關閉，手動定位不補播；回放依事件重建短聲音，非原始音軌。沒有遮擋／混響／完整聲學設計或漏包每發可聞保證。

locked restore、Release build **0警告／錯誤**，**612核心、403 HTTP、43世界、53 Node／196 Chromium**通過；包含舊header0、未知版本拒絕、新版本fire witness條件、已接受stream不能移除音效政策、C#／JS游標對照、實際Web Audio非零、歷史序號／tick／槍口一致、Pause釋放聲源、舊錄製及按鈕狀態。真正Prepare、**93項EditMode（0 failed／skipped）**、Desktop成功；測例逐sample比對匯入PCM、32個無Collider聲源與明確釋放、NGO phase原子複製／Equals及重複Prepare資源GUID保持。未RebuildArena，原scene／prefab ID保持。Desktop receipt UTC2026-10-30T21:20:34.0971906Z，fingerprint `a62c4eb5139e5e64a2074f86bfe5954fd1067a544899cda3ee8a7238d7c0324e`；現在也包含WAV／meta與Resources資產引用。

首輪Prepare因測試組件直接引用與AudioImporter舊API失敗，改為正確Editor測試組件及defaultSampleSettings.preloadAudioData；93測試首輪92通過、1個EditMode清理反例失敗，新增明確IDisposable／despawn釋放後93全通過。瀏覽器首輪用environmentVersion0 fixture卻等待weather峰值，改為獨立combat峰值；後續196通過，另補換錄製音效狀態／epoch及reset後再全跑。兩次HTTP無效憑證程序10秒退出逾時，保留失敗log、未放寬timeout；其後以UTF-8正常完整403及43世界通過，沒有證實逾時原因。原生新helper首輪Python comprehension iterable內assignment expression語法錯誤，啟動前即失敗，改為明確predicate後才實際運行；不把該次當原生證據。

`desktop-venue/20261031-052256-580e3a99` **4項真正原生流程**通過。Sky實際Space一次、HUD30→29，之後操作員開AI至兩次原20點傷害，再停止AI／Pause／Resume，沒有姿態／RPC／武器注入。自己的AudioListener probe明確finish後才真正End／精確seal：

| 證據 | 實際結果 |
|---|---|
| 保存的聲源序號 | 玩家1／敵軍2、4；事件tick287／439／459，播放觀察tick288／440／459，保存槍口逐軸核對一致，沒有重複cue |
| PCM | 48000Hz stereo16-bit、1,287,168 frames／26.816秒、1257 callbacks、2,574,336 float samples；峰值0.158417、RMS0.00290234；WAV SHA `62e6035abbe5a8647d7b351d039a14032dc27749403449132a9458b675ddd648` |
| 靜音 | AI尚未啟用／玩家尚未開火基線、Pause穩定段與無新發的Resume尾段峰值均0，cue總數保持3 |
| 遊戲封存 | 314幀、耗彈1／命中0／擊殺0／中彈2／損耗40／健康60，回放與ledger一致、pending=false、活動0；最大來源年齡0.374625秒 |

這些是本遊戲混音DSP與實際播放呼叫，沒有麥克風／OS loopback、GPU擷取或人員聽感。Probe只在明確Windows Development／可見untracked owner、全新絕對目錄才安裝；180秒／1600萬float／12000視窗／1024 cue，超限或格式變更不算complete。普通遊戲有音效但無診斷，Editor／Android不裝探針。所有播放射線已在**額外完整SQLite副本**核對，未直接開保留原DB或snapshot；稽核後18檔原件／snapshot SHA不變。

普通無音訊診斷的 `20261031-052512-bdd7f05b` 七場五房獨立／單房重用／封存後Linked通過，581幀、最大來源年齡0.223837秒；不是25台。`20261031-052417-d15f5c04` 控制台自訂任務／動態名冊／觀戰及封存回放 **45項UI／native整合**通過，152幀、最大來源年齡0.137755秒；該組client為無圖形，瀏覽器SwiftShader。三組cleanup零錯誤、活動0，自己的SSD runtime在writer停止後由helper回F，18／14／26檔與保留原件逐檔SHA一致；來源及binary仍F，非F USB全資料配置。`unity-admission/20261031-052534-604e8f45` **8項無圖形**入場／撤銷／transport釋放／同admission重連通過，448幀、封存與回放一致、活動0。

Quest真正Editor exit0，receipt UTC2026-10-30T21:34:56.0225326Z，與Desktop相同fingerprint及原scene／prefab ID；APK46,285,274 bytes、SHA `c1df68caf967e819c1ae0b9f9ca1dcd958c55cab9185419de386a81f2d244351`，v2簽章、min32／target35、code31／bundle0.27.0與六個ELF64 AArch64庫含libil2cpp核對通過。這次APK為Unity原始建置，沒有手動重封裝／重簽，未安裝頭盔。三組venue及admission共38個原生／API log未見指定Exception／NullReference／MissingReference／ObjectDisposed／IndexOutOfRange／Shader error；完整本機證據為artifacts/combat-audio-validation.json。本機原5080仍原API0.16／原歷史，未被測試替換。完整11項長期目標持續開發；玩家全身、完整動畫／聲學、複雜場地、原偶發姿態原因、長任務／跨機，以及Quest／VIVE／MR／廠商硬體／25台仍分別待驗。

功能提交 `32725d1467b2e8990b793e9d90a33a416a31daef` 已推送main並核對遠端，GitHub #1已更新且讀回open／2925字與送出本文完全一致；原11項範圍與63864字歷史封存留言連結保留。[CI run41132393727](https://github.com/peca12968/vr-command-center/actions/runs/41132393727)／check124326302315實際failure、steps=null，annotation明示帳戶付款失敗或支出上限，工作未開始，不能稱雲端測試通過；未改帳務或重跑。另有ubuntu-latest遷移通知，不影響本輪本機結果。

## 2026-10-31：兩端姿態時序與受控丟包校準

前輪玩家射擊效果已提交，屬實際進度；本輪從乾淨 `bcdeed9` 接續無頭盔PC主線，追查偶發姿態過期。新增明確選用的NativePoseTrace，分開記錄owner的RPC呼叫、server RPC接收／格式／節流／接受或拒絕、發布時的參戰轉換，以及>100ms主線程空窗。WorldCapture／WorldJournal／CombatJournal／ManagementApply／WorldPublish與玩家GPU讀回／PNG編碼／寫檔各自量測，使用Stopwatch及UTC ticks保留同主機階段時間。規範及操作見 [POSE_TIMING.md](POSE_TIMING.md)。

Unity **0.26.1／Android code30**，API／UI **0.24.0**、NGO **24**及原player-fire-v1／所有pin、header版本、envelope／schema／rules保持。沒有新wire、沒有改0.5秒姿態新鮮度、防瞬移、Tracked座標、碰撞、射擊、admission或HUD警告，也沒有改1.5秒世界來源門檻。一般不帶旗標、Editor及Android不安裝；Windows Development明確--vr-pose-trace且全新絕對目錄才建立。普通呼叫只經未啟用guard，不另建資料／背景worker。

緩衝上限32768列／正常240秒，溢出明示truncated=true／complete=false並保留最早證據；主線程阻塞時須待Update恢復才能截止。只在記憶體收集，每0.25秒檢查finish.request，截止後才序列化／寫出最終report，該段輸出不在觀察內。沒有姿態位置／旋轉、姓名、憑證、UDP payload、GPU或PCM；可以配合另選用的GPU探針量測其區段。report.complete只代表診斷收集，真正End／精確seal另驗。

真正Prepare、**87項EditMode（0 failed／skipped）**、Desktop均成功；5項新測例覆蓋有界保留最早資料、不可變快照、無效時鐘／容量、JsonUtility精確64位UTC、一般未啟用行為，以及非法來源byte255仍可記錄而權威拒絕保持。原scene／prefab ID保持，未RebuildArena。Desktop receipt UTC2026-10-30T20:34:15.2740417Z，fingerprint `6615ee45cb079cc5c342c68f797669944671153412780358364727d3f811e239`。另**3項Python分析反例**通過，涵蓋跨邊界收件間隔、玩家主線程停頓混雜與UTC跳動；已加入CI。這輪沒有後端／管理UI／共用simulation變更，未重算前輪597核心／403 HTTP／43世界／49 Node／189 Chromium為本輪執行。

初版86 Tests、a65來源的雙平台與041743-af6d8459校準雖已成功，覆核發現記錄器僅接受source0–2，會在原驗證拒絕非法來源byte前先拋錯。改為保存完整原始byte0–255，仍由原AvatarPose.Valid拒絕非法姿態；補第87項反例後重跑Tests／Desktop與最終原生。初版receipt／資料保留，不配用最終來源。

新增check-desktop-pose-trace.py：自己的API／room3 server／可見Simulated玩家與loopback gate，先自然60秒（沒有GPU readback），再原樣丟棄單一玩家上行1.2秒，下行維持，最後真正Space一次與原生GPU探針。沒有RPC／姿態／武器注入、沒有防火牆變更。analyze-pose-trace.py只讀關閉後JSON及階段時間，不開SQLite／憑證，不會重建原資料SHM；若控制段玩家或server停頓、或時鐘跳動造成混雜，不能稱校準通過。

`desktop-venue/20261031-043445-1af91e65` **4項原生流程及分析校準通過**：

| 階段 | 實際觀察 |
|---|---|
| 自然60.151秒 | 1084個間隔，玩家RPC呼叫最大56.089ms、server接收66.677ms／接受66.677ms；沒有發布非參戰轉換、拒絕或>100ms主線程空窗。約18次／秒是這個場的實際取樣呼叫頻率，20Hz仍為設定目標，不冒充精確20Hz或頭盔實測 |
| 上行丟包1.2秒 | gate丟棄53 datagrams；玩家呼叫最大55.717ms且兩端沒有>100ms主線程空窗，server接收／接受空窗1.222318秒；最後接受姿態年齡0.588976秒時發布非參戰，恢復後同admission／原位置／健康／彈藥。沒有將發布觀察年齡當成政策閾值或RTT |
| 真正Space與GPU | 彈藥30→29、tick2091閃光／22mm後座、tick2128 Pause歸零，兩張原生PNG已檢視。GPU讀回最大38.168ms、PNG編碼13.939ms、寫檔1.086ms；該段玩家呼叫最大134.974ms、server接收183.526ms、一次主線程空窗134.971ms，沒有0.5秒收件空窗／發布失聯。不能把134.971ms全部歸因於GPU |

此場client／server分別2116／10842列，觀察118.471／122.482秒，complete=true、未截斷。相鄰UTC與單調時鐘步進差最大1.456／1.284ms，控制段未受大時鐘跳動混雜。GPU probe另以明確local stop完成，observedEnd=false、audioSamples／callbackCount0；遊戲另精確seal，耗彈1／命中0／擊殺0／耗損0／健康100，回放／ledger一致。1153幀、最大來源年齡0.188868秒，活動0、cleanup及gate-cleanup零錯誤。

普通未啟用旗標的 `20261031-043659-71fdf936` 七場五房／單房重用／封存後Linked通過，607幀、最大來源年齡0.229533秒，沒有產生trace目錄；非25台。兩場均自己的SSD runtime，writer停止後23／26檔由helper回存F，與保留SSD原件逐檔SHA一致，沒有另開SQLite改動副本。來源與binary仍F，不能稱F USB全資料通過。另 `unity-admission/20261031-043721-aa8aa0da` **8項無圖形**入場／撤銷／transport釋放／同admission重連通過，397幀、精確封存／回放一致／活動0。三組33個log未見指定NullReference／MissingReference／ObjectDisposed／IndexOutOfRange或Shader error。機器證據在artifacts/pose-timing-validation.json。

受控恢復另外在額外完整SQLite副本唯讀核對：保存packet616為非參戰、623已恢復，head／muzzle／forward／health／magazine／reserve完全一致；所有writer早已停止。檢查後再次核對保留SSD原件與F snapshot全部SHA未變，沒有直接開原DB／SHM。檢查器亦補上這些欄位的直接保存／比較；本場以封存副本核對作為證據。

這次診斷能辨別受控上行收件空窗與本機大停頓，但**沒有重現或證明歷史偶發原因，也沒有宣稱已修好失聯**。PoseSend只是RPC呼叫前，不是transport完成；無逐packet配對，不能單靠它分辨NGO排程與網路。BodyConnection只在10Hz發布觀察，不是每tick；乾淨樣本不能排除更短中間狀態。主線程最大值0只是沒有記到>100ms空窗。資料只證明此單次同主機／單房情境，不是跨機RTT、FPS或25台／頭盔效能。

最終Quest首次重建在建立Library/Bee/PlayerScriptAssemblies時Access denied，Editor明確exit1，未產生新receipt；失敗log保留。程序退出後該目錄已不存在，F空間足夠、無活躍Editor／編譯子程序；未改快取內容／ACL／安全設定，以相同來源重試。重試Editor exit0，Quest receipt UTC2026-10-30T20:47:25.4333944Z，fingerprint `6615ee45cb079cc5c342c68f797669944671153412780358364727d3f811e239` 及原scene／prefab ID與最終Desktop完全一致。APK68,404,947 bytes、SHA `4fe0ded3395f6dcb4136ff982cc29d9622c7bf610e151b5154e7a5591851bd14`；v2簽章、min32／target35、code30／bundle0.26.1及六個ELF64 AArch64庫含libil2cpp核對通過，沒有頭盔安裝。體積覆核發現ZIP中央目錄引用的壓縮資料46,239,658 bytes，另兩段未引用間隙共22,144,012 bytes，已保存包裝稽核；沒有重封裝或重簽，保留Unity原始成功產物，不把APK體積變化當作診斷／裝置效能證據。完整11項長期目標保持開發中；後續持續取證偶發原因，並接續射擊音效、玩家全身、完整動畫／場地操作與跨機。Quest／VIVE／MR、廠商硬體及25台仍待分別驗收。

功能提交 `2b4f1396a25350010ac38c87a63ee3137352f9f5` 已推送，遠端main核對相同。GitHub #1更新為本輪結果，讀回open／2946字與提交內容完全相同，原11項範圍、後續依賴及原63864字封存留言連結保留。[CI run41126416900](https://github.com/peca12968/vr-command-center/actions/runs/41126416900)／check124305993088實際failure、steps=null；讀回annotation明示付款失敗或支出上限，工作未開始，不能稱雲端通過。另有ubuntu-latest遷移通知；未改帳務或重跑。

## 2026-10-31：玩家接受射線、原生閃光與槍身後座

從乾淨 `141652d` 接續使用者「目前沒有頭盔，先繼續電腦端」。新增 `player-fire-v1`，組合固定264面玩家步槍、原合成手套、728面NPC與32面閃光；玩家脈衝倍率1.2，沒有外部素材。組合資料SHA `187c7df5346419edadafa1cc74a04db0763dda268650e066dbbcaf8304e60ff0` 固定，生成器先驗舊pin，原七profile／網格／色彩／reader完整保留。規範見 [PLAYER_FIRE.md](PLAYER_FIRE.md)。

API／UI **0.24.0**、Unity **0.26.0／code29／NGO24**。新header playerFireVersion1，缺失仍0，新profile同時要求enemy1／weapon1／enemyFire1；NGO既有原子fire欄位加入玩家語意，全部來源／API／UI／遊戲程序一起更新，不能降reader。envelope6、mission schema1、world schema1、票券2、environmentVersion1及rules0.8.0保持，binary原header／payload／checksum不重寫。

只在實際接受ShotFired後保存sequence、tick+1、原點及方向；去重／拒絕快速射擊不重啟效果或多扣彈藥。逐packet以上次狀態及本次事件核對最後一發，原合法muzzle範圍保持。閃光age0–2（0.15秒）跨正常10Hz發布，槍身後退依age0–3為14／22／12／4mm，age4復位。暫停／結束／seek只依保存tick，死亡／離線隱藏、換彈停止槍身後退但不抹去接受閃光。沒有聲音、Light、Collider或規則變更。

只把借用原Mesh的槍身Renderer及原彈匣放在後座子物件；原根Renderer執行時停用並排除通用顯示列表，真正根槍口／pointer／握點／Tracked資料不移動。Unity閃光脫離avatar父層，避免before-render追蹤更新挪動歷史射線。view銷毀自己的flash，最後model lease才釋放共享網格／材質，沒有重建prefab。

locked restore、Release build0警告／錯誤，**597核心、403 HTTP、43世界、49 Node／189 Chromium**通過。涵蓋tick0接受、去重、拒絕快速連射、同tick換彈、原邊界、事件射線不可改寫、SQLite非零玩家射擊重開、legacy缺欄位及原binary。C#／JS向量、實際WebGL非零後座／歷史閃光／直接seek及最終統計一致，瀏覽器為SwiftShader。真正Prepare、**82 EditMode（0 failed／skipped）**及最終Desktop成功；未RebuildArena，原scene／prefab ID保持。Desktop receipt UTC2026-10-30T19:52:40.1413652Z，fingerprint `9c9d9539bf209f2f66a4ac23483e8e67ab9cbcaf8ef2022de30da0208f0adef7`。完整本機證據在artifacts/player-fire-validation.json。

首次Prepare漏引VrCommand.Simulation造成CS0246，補直接using後通過，失敗log保留。早期暫用2tick脈衝，在發布取樣覆核後於未發布profile定為3tick並固定最終pin；重新生成、82 Tests、Desktop與完整核心／Node／瀏覽器皆用最終3tick來源。HTTP首輪在競爭writer程序10秒退出檢查逾時，接著cp950輸出失敗；第二輪在無效憑證程序10秒退出逾時且temp log清理遭鎖。兩份失敗log保留，未放寬timeout；第三輪以UTF-8完整403通過。未證實逾時的根因，不能歸結為已修復。

新NativePlayerFireProbe僅明確Windows Development／可見untracked client／全新絕對目錄，300秒／8圖／每圖900萬像素上限，無PCM／OS擷取／輸入。首場 `035311-ec9f5ddb` 白天實際Space扣彈並擷取閃光後，觀察到frame338／tick592短暫connected=false／rig=None，檢查器assert中止；frame340／tick597已恢復。cleanup正常、原場資料保留，不列全通過。檢查器改保留此類樣本，實際輸入階段只接受有效Simulated rig，不改遊戲或1.5秒新鮮度門檻，原暫時失聯根因仍待。

| 最終PC場（前綴20261031） | 幀／最大來源年齡 | 證據 |
|---|---|---|
| 035502-2fb88aa3 | 779／0.301179秒 | **4項真正按鍵／GPU流程**：Space白天與夜間各一次，兩張實際脈衝在tick740／909、後座均22mm；接受事件tick739／908，SQLite event packet398／487，射線float32精確相符。GPU時鐘與10Hz存幀不必同tick。Right一次後HUD方位003°、瞄準改變但保存射線不改；真正根仍pointer前0.15m。Pause在770／1120，效果已歸零，沒有峰值暫停GPU宣稱；峰值Pause由核心與Unity測試證明。四張GPU圖已檢視；complete=true／observedEnd=false／明確local diagnostic stop，audioSamples／callbackCount皆0。遊戲另精確seal，耗彈2／命中0／擊殺0／中彈0／健康100，回放一致 |
| 035635-194329c4 | 153／0.159144秒 | **45 UI／native，client無圖形**：任務保存／配置、動態名冊、天氣／AI／Patrol／Pause／End、鏡頭及封存回放，含真正NPC接受射線與WebGL效果核對。沒有本輪原生雨夜／雷聲人工檢視 |
| 035735-8b13eb6c | 七場580／0.192192秒 | 五個真正server／每房一個client隔離、單房End／重用、全部seal後Linked、舊票／升權拒絕及七個stream精確封存，新profile／playerFire1；非25台負載 |

三組均Simulation／Simulated、pendingTelemetry=false、活動0、cleanup零錯誤；writer停止後21／14／26檔回F並與保留SSD原件逐檔SHA相同。首次SQLite唯讀稽核重建了封存副本的worlds.db-shm（mode=ro仍可寫派生index）；已保留該派生SHM於額外artifact並從未變動的原件恢復，重新核對全部檔案一致。正式數值稽核改在另一份完整副本執行，前後再次確認原件及封存SHA不變。未重寫DB／WAL／journal／事件。程式及binary仍F、runtime明確SSD，source age非RTT／FPS，不能稱F USB全資料或25台通過。

另 `unity-admission/20261031-035827-e474b2ca` **8項無圖形**入場／撤銷／transport釋放／同admission重連通過，365幀、精確seal／回放一致與活動0。四組38個log未見指定NullReference／MissingReference／ObjectDisposed／IndexOutOfRange或Shader error。本輪未重跑真正按鍵擊殺／R換彈、互動走離出生點的重連、完整碰撞、GPU閃電或DSP／聽感；較窄SDK未另跑。原5080唯讀health ok，仍API0.16／原歷史，沒有替換DLL／資料／憑證。

Quest ARM64／IL2CPP亦exit0，receipt UTC2026-10-30T20:06:54.3684764Z，來源fingerprint與原scene／prefab ID和最終Desktop完全一致。APK46,228,012 bytes、SHA `6651622b5695d968f7222fa306a501b3cefb41330864050090abe8ab5cea1e71`，簽章v2、min32／target35、code29／bundle0.26及六個ELF64 AArch64庫含libil2cpp核對通過。沒有頭盔安裝。完整11項長期目標保持開發中；玩家／敵軍射擊音效、全身人物、完整動畫、原暫時失聯原因與跨機仍需推進，Quest／VIVE實機、MR、廠商硬體及25台須分別驗收。

功能提交 `96ab34918d8fa2619f7f674557d356cd70f0ccbf` 已推送，遠端main核對相同。GitHub #1原63864字本文已[完整封存於留言](https://github.com/peca12968/vr-command-center/issues/1#issuecomment-6532297157)，讀回確認原文完整後，本文改為目前11項目標／最新交付／後續及文件連結，保持open。原文SHA `d56064c431b1d8c83e5eef3f6cf3945f6270752b9582b83416a182f862c42fed`；新本文2413字讀回相同。[CI run41120847295](https://github.com/peca12968/vr-command-center/actions/runs/41120847295)／check124286744394目前queued、尚無步驟或雲端通過結果；不拿前輪帳務annotation推定本輪狀態，未改帳務或重跑。

## 2026-10-31：按接受射線還原敵軍閃光與槍身後座

從乾淨 `d8ee348` 接續無頭盔的PC主線。新增 `combat-effects-v1`，沿用固定728面持槍NPC／玩家換彈／掩體，再加原創32面封閉星形脈衝，每NPC最大760面。資料SHA `b8fe83d66781c2f65816d6873cc08ba01314418d42777a55e9eea2d1ee34a9bb` 固定，生成器先驗舊pin、Unity／瀏覽器共源；原六profile、原網格／色彩及reader保留，沒有外部素材。新unlit Shader保留instancing／stereo宏，不加Light或音效。規範見 [ENEMY_FIRE.md](ENEMY_FIRE.md)。

API／UI **0.23.0**、Unity **0.25.0／code28／NGO23**。新header enemyFireVersion1，缺失仍0；新profile還要求enemy1／weapon1。NGO enemy row原子新增fireSequence、fireTickPlusOne及原點／方向；來源／API／UI及全部遊戲端一起更新。envelope6、任務schema1、world schema1、票券2、environmentVersion1及rules0.8.0保持，不能降reader，binary原header／payload／checksum不重寫。

ArenaWorld只在原AI實際Emit EnemyShot後複製接受事件，逐packet驗證以上次狀態＋本次事件重建最後射擊；拒絕缺旗標、未來時鐘、憑空序號、改原點／方向或後續改寫。從未射擊明確true／sequence0／tick0／零向量。閃光使用保存世界射線，即使NPC已移動／轉向；age0–2顯示，槍身後退依tick為12／18／10／4／1mm、age5復位。僅停用原Gun Renderer並借同網格到子Renderer，真正槍口／手套／雙臂／Tracked資料、射速、原20點傷害與命中盒不動。Pause／Ended／seek保持保存tick，死亡隱藏效果但不刪歷史。沒有玩家步槍效果、聲音或實體後座，亦未完成完整人體／死亡／換彈動畫。

locked restore／Release build0警告錯誤、**575核心、403 HTTP、43世界、45 Node／184 Chromium**通過。新增事件證據、跨packet移動／改向、真實ArenaWorld暫停、死亡、SQLite非零射擊狀態重開、舊binary缺欄位與原位元組保留；C#／JS向量核對及實際WebGL閃光／位移／歷史射線／直接seek與統計一致。瀏覽器為SwiftShader。真正Prepare、**76 EditMode**及最終Desktop通過，原scene／prefab ID保持，未RebuildArena。最終Desktop receipt UTC2026-10-30T18:58:01.7951618Z，fingerprint `e2c4dba4f763a7109be018342b8e01154f0b247d921eddc383ed81da59470dbd`；Quest ARM64／IL2CPP亦exit0，receipt UTC2026-10-30T19:16:28.8845657Z，來源fingerprint及scene／prefab ID與最終Desktop完全一致；APK46,210,244 bytes、SHA `c7c4a34d13ef5126c2998cd597b863d4006bfbfad0bfe535ef139b48ae328013`，簽章v2、min32／target35、code28／bundle0.25及六個ELF64 AArch64庫含libil2cpp核對通過。沒有頭盔安裝。完整機器證據在artifacts/fire-validation.json。

首輪76 Tests有2項失敗：生成測例仍預期NGO22、Transform精確float相等；改預期23及1e-5m容差後重跑通過。首次世界smoke的固定fromMs200且假設必有非初始frame失敗，未保留當時數值，不能回推精確原因；改從來源實際保存的第6個packet時間求rightmost preceding sequence，要求精確序號且>1，另保存world-smoke-seek.json。最終requested409ms／expected6／actual6，43項通過；未放寬1.5秒來源或遊戲規則。Node測例的-0與0比較改驗證位移絕對值零，實際渲染／資料不改。失敗XML／log保留。

新NativeEnemyFireProbe只在明確Windows Development／可見untracked client／全新絕對目錄安裝，最多8圖／180秒、無PCM／輸入／OS擷取。EndOfFrame記錄實際套用而非較晚到的actor row，GPU影像與時鐘／Transform同行。首場 `025342-d1194176` 確有日夜GPU脈衝（tick1／22、12／18mm），但End撤銷入場會先despawn頭部，診斷未收到Ended而收尾失敗，不列全通過；cleanup正常、部分圖／資料保留。增加只停止診斷的本機finish.request，complete明確為收集完成，另有observedEnd／stopReason；伺服器seal獨立證明遊戲結束。重跑76及Desktop後才做最終原生。未使用的等待控制台場 `025526-971d0c03` 在未建立任何場次時正常停止，未算功能驗收。

| 最終PC場（前綴20261031） | 幀／最大來源年齡 | 證據 |
|---|---|---|
| 025840-cfe18ea8 | 582／0.158654秒 | **4項原生AI／GPU流程**：白天tick1及夜間tick21均有閃光／12mm槍身位移，圖片已檢視；對應world序號1／3及兩次傷害。Pause在tick11／32／43，效果已歸零，沒有宣稱此場在閃光中暫停。Patrol移動後仍保留原射線。兩張GPU擷取另外唯讀與封存SQLite逐event／float32射線精確核對。診斷complete=true／observedEnd=false／明確local stop，audioSamples及callbackCount皆0；真正場次另精確封存，耗彈0／中彈2／損耗40／健康60及回放一致 |
| 030033-6c7e1a82 | 155／0.163004秒 | **45 UI／native，client無圖形**：配置／任務保存、動態名冊、天氣／AI／Patrol／Pause／End、鏡頭及封存回放；新增實際WebGL射線／fire clock／flash與recoil核對，資料含真正接受射擊，非fixture注入。沒有人工GPU雨夜／雷聲檢視 |
| 030258-ac140d8d | 七場601／0.224976秒 | 五個真正server／每房一個client隔離、單房End／重用、全部seal後Linked、舊票／升權拒絕與七個精確stream封存，皆新profile／enemyFire1；非25台負載 |

三組均Simulation／Simulated、pendingTelemetry=false、活動0、cleanup零錯誤，writer停止後22／14／26檔回F並與保留SSD原件逐檔SHA相同。程式及binary仍F、這些runtime明確SSD，不是F USB全資料通過，source age非RTT／FPS。另 `unity-admission/20261031-030456-f7254c15` **8項無圖形**入場／撤銷／transport釋放／同admission重連通過，401幀、精確seal／回放一致與活動0。四組38個log未見指定NullReference／MissingReference／ObjectDisposed／IndexOutOfRange或Shader error。本輪未重跑真正按鍵擊殺／換彈、互動走離出生點重連、完整碰撞、GPU閃電或DSP／聽感；較窄SDK未另外重跑。原5080仍API0.16／health ok及原歷史，沒有替換正式DLL／憑證。完整11項長期目標保持開發中，實際Quest／VIVE、MR、廠商硬體、跨機與25台仍待。

功能提交 `7fb5ce2b376dd076255ae8a7de0358c7bfb3a36b` 已推送，遠端main核對相同。GitHub #1已同步本輪，讀回open／63864字，原62127字內容完整保留。 [CI run41114384316](https://github.com/peca12968/vr-command-center/actions/runs/41114384316)／check124264676068實際failure、steps=null；annotation明示付款失敗或支出上限，工作未啟動，不能稱雲端測試通過。未改帳務或重跑。

## 2026-10-31：敵軍雙手手槍與裝飾性雙臂

從乾淨 `3c3d71b` 接續無頭盔的PC主線。新增 `armed-combatants-v1`：原創緊湊型手槍、分離上下臂及合成手套，每NPC728面、八個共用Mesh／一材質；頭及腿取固定combatants-v1、手套為固定weapon-actions-v1的0.65倍副本，原五profile／pin完整保留。生成器先驗舊pin，新資料SHA `cc011e951163d4b846c4e2c217592251906844c0dfcee2f795618c8c1c388102`；check與記憶體改色反例拒絕通過。無外部素材／下載，規範見 [ARMED_ENEMIES.md](ARMED_ENEMIES.md)。

API／UI **0.22.0**、Unity **0.24.0／code27／NGO仍22**。新profile要求enemyPresentationVersion1及weaponPresentationVersion1，未加wire欄位；來源／API／UI與全部遊戲端一起更新。envelope6、任務schema1、world schema1、票券2、environmentVersion1與rules0.8.0保持，binary原header／payload／checksum與舊外觀不改，不能降舊reader。

共用C#9／JS依保存forward／tick求解雙臂，upper .22m／lower .25m，wrist附槍握點、elbow朝外下hint；不靠移動feet／追蹤資料補救。槍口仍feet+(0,1.4,0)、完整±90°pitch，頭仍±45°，命中half(.3,.9,.3)與AI射速／傷害不改。軀幹／頭位置是新裝飾性外觀，不改保存feet。Unity改用同一atomic actor row的原始位置，避免本地插值讓槍口偏離；10Hz階梯感未解。Paused／Ended及seek還原同姿勢，無Collider／NetworkObject。開火閃光需另保存射擊當下位置／方向及事件，本輪沒有補造；後座／NPC換彈／死亡、完整人體／手指／腳底IK、極端姿勢防穿插與音效仍待。

locked restore／Release build0警告／錯誤，**555核心、403 HTTP、43世界串流、41 Node／179 Chromium**通過。核心181個pitch核對方向／臂長、共線fallback／不可達拒絕、新profile版本政策及原20點傷害；SQLite保存重開新profile，保留舊reader測例。C#／JS向量、真正WebGL面數／子物件世界矩陣、直接seek、舊profile切換及精確結束統計通過，瀏覽器為SwiftShader。真正Prepare與**70 EditMode**通過，新增4項涵蓋外向網格、八Mesh重用／無碰撞、實際槍口／腕點及seek。Editor保存實際新增meta；曾暫時更新URP清單，最終Android匯入後與原檔無差異，未RebuildArena，原scene／prefab ID保持。

第一版Windows成功後覆核發現合法forward有微小長度容差，補上槍pitch前正規化及近單位向量測例，再重跑70 Tests／555核心／41 Node及179 Chromium，最終Desktop exit0。舊成功receipt另存artifacts/armed-desktop-before-normalization.json，最終receipt UTC2026-10-30T18:11:01.5598325Z，fingerprint `a712a41accad34ab19d2032cd1e204a2885e9158fd5decd4c6ea5fe74f27357f`；不能拿初版receipt配最終來源。較窄SDK在正規化修正前通過兩分支18 runtime／16 NUnit型別綁定，未當作最終Editor／APK證據。

| 最終PC場（前綴20261031） | 幀／最大來源年齡 | 證據 |
|---|---|---|
| 021117-c7d69f7a | 831／0.266805秒 | **44 UI／native**：保存配置／preflight、動態名冊、白天／雨夜／Pause的真正GPU畫面，近距離NPC雙手槍已檢視；AI傷害後GPU健康60／彈藥30/90、Patrol中Pause保留非零步態。封存回放的真正渲染槍口／完整方向／肘腕世界矩陣與保存frame核對一致，書籤／精確鏡頭及歷史玩家統計一致 |
| 021329-c5842479 | 七場605／0.165719秒 | 五個真正server／每房一個client隔離、單房End／重用、全部封存後Linked；舊票／升權拒絕，七個獨立stream精確封存且皆新profile／enemy1／weapon1 |

兩組均Simulation／Simulated、pendingTelemetry=false、活動0、cleanup零錯誤；14／26檔由helper在writer關閉後複製回F，再與保留SSD原件逐檔SHA一致。首次手動複製前的assert發現helper已產生snapshot，未覆寫；改核對既有副本。程式與binary仍F、上述runtime明確SSD，非F USB全資料或25台負載。source age為擷取新鮮度，非RTT／FPS。

另 `unity-admission/20261031-021401-e1fdfde9` **8項無圖形**入場／撤銷／transport釋放／同admission重連通過，381幀、精確封存／回放統計及活動0。三組共35個log未見NullReference／MissingReference／ObjectDisposed／IndexOutOfRange例外。本輪未重跑真正按鍵兩發擊殺、走離出生點的互動重連、完整碰撞、GPU閃電或DSP／聽感；既有結果保留為歷史，不混算新binary驗收。

Quest ARM64／IL2CPP亦exit0，receipt UTC2026-10-30T18:24:52.1314526Z；與最終Desktop來源fingerprint及scene／prefab ID完全一致。APK46,190,262 bytes、SHA `ad974f992046c7d70adcb19c7f9d0731e8e21ea79e869178fc96565d763caf5b`，簽章v2、min32／target35、code27／bundle0.24及六個ELF64 AArch64庫含libil2cpp核對通過。四張原生GPU截圖為Sky原始JPEG位元組，副檔名已對齊；完整機器證據在artifacts/armed-validation.json，未將舊APK或較窄SDK當本輪結果，沒有頭盔安裝。原5080已唯讀確認health ok、仍API0.16／原歷史，未替換DLL／正式憑證。完整11項長期目標持續開發中；後續接射擊事件及閃光／後座、玩家人物、完整動畫／音效、複雜地形／跨機與原停頓原因。Quest／VIVE實機、MR、廠商硬體及25台仍待分階段驗收。

功能提交 `5031250791b47da74363999659d41eb74c959064` 已推送，遠端main核對相同。GitHub #1已同步最新交付並完整保留原60538字內容，讀回open／62127字確認。 [CI run41106904487](https://github.com/peca12968/vr-command-center/actions/runs/41106904487)／check124239002725實際failure、steps=null；annotation明示近期付款失敗或支出上限，工作未啟動，非本輪雲端測試執行結果。未改帳務或重跑；本機結果獨立保存。

## 2026-10-31：保存換彈時鐘、分離彈匣及合成手套

從乾淨 `df2e649` 接續無頭盔的PC主線。新增 `weapon-actions-v1`，完整沿用既有人形敵軍／掩體，將固定264面步槍分為槍身240／彈匣24，加各120面的兩個原創手套；四Mesh／一材質跨avatar引用計數，無Collider或NetworkObject。生成器先驗證舊pin，再分離原三角形，新資料SHA `517c3616ec12dad34f25cc50f5309eae1033b62bcbbb636b4a3f378a5c12cab3` 固定；原四個profile及pin保留，沒有外部模型／貼圖。新舊原位264面的位置／法線／色彩已逐三角形核對，不能改舊回放。規範見 [WEAPON_ACTIONS.md](WEAPON_ACTIONS.md)。

API／UI **0.21.0**、Unity **0.23.0／code26／NGO22**。新header weaponPresentationVersion1及hasWeaponPresentation／reloadUntilTick直接保存原世界的30-tick完成點；共用驗證逐事件核對ReloadStarted／Completed，拒絕憑空、重疊或改時鐘。NGO玩家row原子含tick及until，來源／API／UI／遊戲端一起更新。預設及缺欄位舊header仍0，不補造動作，binary原header／payload／checksum保持；envelope6、任務schema1、world schema1、票券2、environmentVersion1與rules0.8.0不改，新資料不可降舊reader。

Unity／JS按保存tick做左手移向彈匣、抽出、短暫隱藏表示替換、插回與回握；Paused／Ended保留局部姿勢，seek不依本地wall clock。合成手套限Simulated且連線／存活，Tracked仍保留實際左手標記，不搬動關節資料配模型。槍口仍為原pointer前0.15m，動畫只動子物件；原射線、射速、換彈時間與彈藥規則不改。死亡／離線停止合成動作，原死亡可能留過期reloading旗標的規則保留；玩家身體／NPC武器、前臂／手指IK、物品庫、後座／死亡動畫、音效及真實換匣仍待，不能稱完整人物或追蹤握持。

locked restore／Release build通過、0警告／錯誤，**548核心、403 HTTP、43世界串流、37 Node／173 Chromium**通過。新增時鐘／事件證據、Pause／完成／原彈藥、無效及死亡狀態、原位幾何與資源生命週期、C#／JS全部30 tick與Tracked政策、真正WebGL子物件／非零位移／直接seek及統計。SQLite新profile保存／重開已覆蓋。原重複event交易反例因新換彈證據先被ArgumentException拒絕，補齊合法換彈狀態後仍確認原SQL唯一性拒絕，未放寬產品規則。

瀏覽器第一輪因API輸出目錄仍舊field-props.js而不識新profile，重新整包build；第二輪範例原無connected／rig，不能冒充合成手套，新增明確Synthetic測例rig並讓新版本匯入嚴格驗證；最後全套通過。舊無rig範例保持舊政策，沒有改其射線。失敗log／圖片保留。66項真正EditMode（0 failed／skipped）及Prepare／Desktop／Quest均exit0；新增5項覆蓋真正網格、共享無Collider、實際子Transform／根不動、Tracked資料不改、NGO及JsonUtility。另補強前輪舊NPC JSON測例為完整合法packet並驗證legacy讀取。未RebuildArena，原scene／prefab ID保持；Desktop receipt UTC2026-10-30T15:24:17.9621245Z，fingerprint `ab159159d9dbc182b4477d99125019db8052b6287485b362d8443bab0a1e8ef4`。離線SDK兩分支17 runtime／15 NUnit只證型別綁定。Quest receipt UTC2026-10-30T17:38:54.7872925Z，fingerprint與識別同Desktop；中斷前後來源再次核對一致。APK46,172,166 bytes，SHA `ae974c5fd51c5b34af2a346502a3dbba09cb102f313b1582fb3783b3b0602dde`，v2、min32／target35、code26／bundle0.23及六個ELF64 AArch64庫含libil2cpp核對通過；沒有頭盔安裝。

原生第一場 `20261030-232831-54ea8099` 在實際R／Pause後被中斷並斷線，不能算完整通過；`20261031-011139-67be926f` 早期第4 tick暫停、Space及30／89已觀察，但complete review標記逾時，亦不算全通過。兩場cleanup正常且原資料／快照保留。最終流程等到抽出階段才Pause，人工review等待改600秒，未放寬遊戲時間／來源新鮮度門檻。曾取到非遊戲視窗影像，未保存為遊戲證據；改用明確HUD影像探針，再以重新確認的遊戲視窗補完成畫面。探針有界285秒且audioSamples／callbackCount皆0，非聽感或頭盔證據；初期POSE REJECTED／STALE擷取亦保留，未宣稱原啟動旗標問題已解決。

| 最終PC場（前綴20261031） | 幀／最大來源年齡 | 證據 |
|---|---|---|
| 011829-38a0829c | 1938／0.160171秒 | **4項實際鍵盤／GPU流程**：Space1→29、R1，保存tick616／until632、elapsed14；GPU交換期手套／彈匣狀態已檢視，暫停再Space不耗彈，Resume後30／89、until0及回握畫面已確認。另**5項真正原生錄製觀戰**核對實際WebGL彈匣／手套位置、旋轉與隱藏狀態；保存完整數值及近距離鏡頭。封存耗彈1、命中／擊殺0、健康100且回放一致，無pose／combat注入 |
| 012755-8c66b16b | 115／0.156563秒 | **42 UI／native，客戶端無圖形**：保存配置／preflight、動態名冊、天氣／AI、Patrol／Pause／Resume／End、鏡頭、封存及最後姿勢；瀏覽器SwiftShader。此場沒有重做原生雨夜GPU／DSP |
| 012959-c53acede | 七場530／0.202684秒 | 五個真正server／每房一個client隔離、End／重用、封存後Linked、舊票／升權拒絕與七個精確stream封存；全為新profile／weapon version1，非25台 |

控制台前場 `012543-62053ba3` 單次讀狀態檔的暫停斷言未通過；其SQLite共722個Paused幀均tick62，沒有保存當下失敗讀回的原值，不能回推精確原因。改為等待同tick的有效讀回並保存前後樣本，若實際tick改變仍會失敗；最終42項通過。原生觀戰新工具首輪把option可見性當選單存在條件而timeout，改等attached後5項通過，不改產品。

最終三組均Simulation／Simulated、pendingTelemetry=false、活動0、cleanup零錯誤；writer關閉後25／14／26檔複製回F與SSD逐檔SHA一致且保留原件。另 `unity-admission/20261031-013124-c61855d2` 8項無圖形入場／撤銷／transport釋放／同admission重連通過，369幀、回放報表一致及活動0。沒有重跑走離出生點的互動重連、完整鍵盤碰撞、DSP／聽感、跨機或F USB全資料；source age為擷取新鮮度，非RTT或FPS。程式與binary仍F、runtime明確SSD。

最終原生39個log未見NullReference／MissingReference／ObjectDisposed／IndexOutOfRange例外。機器證據彙整於artifacts/actions-validation.json；原5080仍API0.16與原歷史且health ok，未替換正式資料／憑證。功能提交 `4ca6a59d059154c74a574541103dd3ab6e3d7052` 已推送並核對遠端main相同。[CI run41101273280](https://github.com/peca12968/vr-command-center/actions/runs/41101273280)／check124218763936目前queued、steps=null，尚無執行結果；不以歷史帳務失敗推定本輪結果，亦未改帳務或重跑。GitHub #1已同步目前ROADMAP、結果及限制，讀回確認open且保留前次完整內容。完整11項長期目標維持開發中；接續玩家人物／NPC武器、完整動畫／音效、複雜通路／地形、原停頓原因／啟動旗標、長任務與跨機；Quest／VIVE、MR、廠商硬體與25台仍待分階段實測。

## 2026-10-30：人形敵軍、權威朝向及可還原步態

從乾淨 `0170bb0` 接續使用者無頭盔的PC主線；前輪已交付玩家步槍，本輪新增原創404三角形人形敵軍（軀幹180、頭104、腿60重用兩次），含頭盔／護目鏡、背心／彈袋、紅色臂帶、護膝及靴子。生成器產出相同Unity Resources／瀏覽器頂點、法線、色彩與索引，固定資料SHA `39fa5e9baceec0eb71ce6a4664fc4460e7b0f212f2c58b75c7b4d75b3565fdf2`。生成check及記憶體改色反例拒絕通過；沒有外部模型／貼圖／下載，原掩體與步槍pin不改。NPC尚無武器模型、握持／換彈／死亡動畫或腳底IK，玩家身體與頭手仍為原型，不能稱完整人物美術。規範見 [ENEMY_PRESENTATION.md](ENEMY_PRESENTATION.md)。

新header assetSet=`combatants-v1`沿用固定掩體／玩家步槍，要求明確 `enemyPresentationVersion=1`；每個敵軍保存hasPresentation、單位forward及walking，未知／缺失版本拒絕。預設Create／Capture及缺欄位舊header仍0，完整保留三個舊profile與NPC外觀；binary原header／payload／checksum不改寫，codec只正規化舊缺失零向量。API／UI **0.20.0**、Unity **0.22.0／Android code25／NGO21**；envelope6、任務schema1、world schema1、票券2、environmentVersion1與rules0.8.0保持。新欄位及profile不能降舊reader，所有API／UI／遊戲程序一起更新。

ArenaWorld只在成功移動後標記walking及方向，有autoAttack目標時使用原射擊原點到目標的單位向量作朝向。沒有改目標選擇、導航、兩公尺Advance停止距離、攻擊間隔、原feet+(0,1.4,0)射擊原點或命中盒。NGO每個敵軍row原子複製facing／walking／presentationTick；Unity與觀戰共用保存tick規則，頭pitch視覺±45°、雙腿相反sin步態±18°。Paused／Ended保留最後模式與tick，直接seek相同；Unity位置仍插值，非逐pixel伺服器影像。模型無Collider／NetworkObject，原軸對齊敵軍half(.3,.9,.3)命中盒保留，擺腿輪廓不改命中；同點重疊／人群避讓仍待。

locked restore／Release build通過，0警告／錯誤；**534核心、403 HTTP、43世界串流、32 Node／167 Chromium**通過。涵蓋實際移動與原射線傷害、版本拒絕、SQLite重開與原binary逐byte保留、三Mesh資源池、固定法線、C#／JS時鐘向量及真正WebGL非零步態／seek／統計。審查發現JS原通用unit容差.011比renderer的.01寬，新NPC檢查已對齊.01並加1.0105反例，最後完整瀏覽器重跑通過；沒有改舊玩家容差。桌面／近距離回放截圖已檢視，瀏覽器為SwiftShader。首輪.NET建置抓到nullable約束，修正缺packet與forward guard；新核心測例先漏合成rig而被拒，補正測例，未放寬參戰姿態驗證。

真正Prepare、**61 EditMode（0 failed／skipped）**、Desktop／Quest均exit0，未RebuildArena，原scene／prefab識別保持。新增5項測試涵蓋真正匯入網格、共享資源／無Collider、實際Transform與seek、NGO序列化、JsonUtility舊資料；Tests門檻61。Desktop receipt UTC2026-10-29T20:04:05.5902819Z，fingerprint `7c4d759065020885b43d7dc5d4c04d42a91d822813b33c054434880f288ab2b3`。離線managed SDK兩分支各16 runtime／14 NUnit來源僅型別綁定，不冒充Editor／音訊／Shader／APK執行。Quest receipt UTC2026-10-30T14:53:43.7390900Z，fingerprint與識別同Desktop；兩次建置間有工作中斷，來源重新核對未變。APK46,147,574 bytes，SHA `11f8280ebcde4d30d1415bd6ac680c2650787be4a514fd63d816e633a3824200`，v2簽章、min32／target35、code25／bundle0.22及六個ELF64 AArch64庫含libil2cpp核對通過，沒有頭盔安裝。

人工檢視第一場 `040445-dde5b466` 因跨回合中斷逾時，不能稱UI全通過；helper到期後8250幀封存、清理正常。第二場 `223112-3335acc2` 實際看見敵軍前進／傷害及停止，最後walking=false使原測試要求移動的斷言失敗；因Advance已到原兩公尺門檻，改以真正控制台Patrol／Resume／Pause另驗非零步態，沒有為測試改AI停止距離或注入pose。失敗log／圖片／原資料與snapshot均保留，不能混作最終42項證據。

| 最終PC場（前綴20261030） | 幀／最大來源年齡 | 證據 |
|---|---|---|
| 223557-d36552a9 | 2757／0.175022秒 | **42 UI／native**：配置保存／preflight、動態名冊、天氣／AI Advance傷害、Patrol移動、Pause／Resume／End、鏡頭與封存回放；真正GPU白天全身、雨夜、Pause及巡邏中暫停均已檢視。最後保存tick3169、兩敵walking=true，實際觀戰物件yaw／head pitch／相反腿角與原生frame一致；自身健康60 |
| 224124-1ecc97e0 | 七場537／0.201650秒 | 五個真正server／每房一個client的隔離、單房End／重用、封存後Linked、舊票／升權拒絕與七個stream精確封存；每場combatants-v1／presentation1，非25台 |
| 224306-4ae70119 | 1587／0.171834秒 | 一般未掛探針的可見玩家，真正Left14／Down5瞄準及Space兩次，GPU看見新人形敵軍100→50→0、彈匣30→29→28，封存ammo2／hit2／kill1／100%、自身健康100，回放一致；無pose／combat注入 |

以上最終三組均Simulation／Simulated、pendingTelemetry=false、活動0、cleanup零錯誤；writer關閉後14／26／14檔複製回F與SSD逐檔SHA-256一致且保留原件。另 `unity-admission/20261030-224203-4dd71abf` **8項無圖形**入場／撤銷／transport釋放／同admission重連通過，370幀、封存回放一致、活動0；未重跑走離出生點的互動重連。本輪不重做DSP／聽感／完整鍵盤碰撞，舊證據保留；source age為擷取新鮮度，非RTT或FPS。程式與binary仍F、runtime明確SSD，不代表F USB全資料、跨機、25台或頭盔通過。

最終原生各自log共38檔未見NullReference／MissingReference／ObjectDisposed／IndexOutOfRange例外；機器證據彙整於artifacts/enemy-validation.json。原5080仍API0.16與原歷史且health ok，未替換正式資料／憑證。功能提交 `f4d9c749629101558ed419600d70c65cb82356b5` 已推送並核對遠端main相同。[CI run41076508175](https://github.com/peca12968/vr-command-center/actions/runs/41076508175)／check124134028244已結束，steps=null、annotation明確為近期付款失敗或支出限制、工作未啟動；另有ubuntu遷移通知，未改帳務或重跑。GitHub #1已同步ROADMAP、新結果與限制，讀回確認open且保留前次完整內容。完整11項長期目標維持開發中；下一步為NPC武器握持／玩家人物、換彈與死亡動畫、複雜通路／地形、原停頓原因／啟動旗標、長任務與跨機；Quest／VIVE實機、MR、廠商硬體及25台仍待設備與分階段驗收。

## 2026-10-30：玩家步槍、槍口對齊及實際命中

上一輪配置檢查已交付，從乾淨 `245ddb0` 接續使用者無頭盔的PC主線。新增自製264三角形步槍，槍托、機匣、握把、彈匣、護木、槍管及瞄具共用固定位置／法線／頂點色。生成器與Unity Resources／瀏覽器ES module同源，資料SHA `b054b9780b19104c6ff33a2384df15e9e4f6e2c73293297c4f70e2dd0d8eda25` 固定；生成check及記憶體改色反例拒絕通過。沒有外部模型／紋理／下載，沒有改field-props-v1 pin。人物／NPC、左手／頭部仍為原型，武器是靜態外觀，非完整人物、握持IK、換彈／後座動畫、槍械音效或廠商武器整合。

新header assetSet=`service-rifle-v1`明確由新Unity來源指定，完全沿用field-props-v1掩體、只換玩家步槍；field-props-v1及primitives-v1仍保留原武器，Create預設與缺欄位舊匯出維持legacy。API／UI **0.19.0**支援三種版本，未知／已接受header換版本拒絕；原binary header／checksum不改寫。envelope6／任務schema1／world schema1／environmentVersion1／票券2及rules0.8.0保持，不能降回不認識新profile的reader。NGO **20**隔離不同遊戲外觀與桌面預設，全部遊戲端一起更新。規範見 [SERVICE_RIFLE.md](SERVICE_RIFLE.md)。

Unity新模型為avatar根下的完整尺寸物件，跟隨pointer的旋轉及前方0.15m槍口；不繼承手部(.12,.12,.2)縮放。舊Weapon物件保留file ID但只在執行時停用；隱藏位於pointer的方盒Renderer，不假稱量測的握把／手掌。模型／server／HUD共用原0.15m常數，射擊仍由同一接受流程／射線確認，無新增Collider／NetworkObject或權威幾何。程序跨avatar共用Mesh／材質及引用計數；瀏覽器共用geometry、各角色獨立淡出材質，移除單一角色不釋放仍使用的共用網格。觀戰按已保存muzzle／forward，匹配的rightRotation保留roll，缺失／不匹配則按保存射線重建；本地畫面仍屬輸入預測／遠端插值，非逐幀伺服器影像。

候選場 `030454-deb7b4a2` 實際Space／R／Right20及傷害／Pause／淘汰基線雖通過（2393幀、最大來源年齡0.414904秒、30檔snapshot一致），GPU卻顯示自身武器在視野外。又從真正AcceptPose確認模型原點需要pointer前0.15m，原候選未對齊，不能稱視覺整合完成。已共用原常數並將**僅桌面合成**pointer預設由(.3,-.35,.4)改(.18,-.12,.75)，初始及更新一致；頭部、實體XR座標／來源與權威規則不改，保存的射擊原點沿實際接受姿態，舊錄製不重算。這是明確的桌面輸入預設變更，不能稱原姿態完全不變。新56項測試覆蓋原60°視野及多pitch／yaw、槍管前端可見與既有槍口範圍，真正GPU再驗如下。

locked restore／Release build通過，0警告／錯誤；**512核心、403 HTTP、43世界串流、27 Node／162 Chromium**通過。新profile實際經SQLite／canonical header／不可變重試與禁止降回field profile驗證；Node核對相同資料／pin、法線、槍口／方向／roll、資源池及壞資料。真正WebGL比較新舊玩家武器面數差異、seek統計及反覆切換，桌面／近距離回放截圖已檢視，瀏覽器為SwiftShader。首輪Prepare在測試的namespace解析出現CS0234，補global::；首輪55測試54通過／1項lossyScale精確相等失敗，改1e-5浮點容差而非放寬武器尺寸，再加視野測試後**56真正EditMode（0 failed／skipped）**全部通過。失敗wrapper保留，Editor標準路徑為最後成功log；managed SDK兩分支各15 runtime／13 NUnit來源僅型別綁定，不當作執行／Shader／APK證據。

真正Prepare、最終Desktop／Quest均exit0，未RebuildArena；scene／prefab識別保持，生成場景僅NGO19→20。bundle **0.21.0／Android code24**，兩端fingerprint同為 `32e2db5110d59fd3ce4a262b6a1d4bc59efacbef4732afafe5a391a6eb4b9523`。Desktop receipt UTC19:12:16.2548406Z、Quest19:27:52.6538646Z（10/29）；APK46,145,650 bytes，SHA `ebb3ad08021b74acf78bc9ab385b7175f6d74db11cec20f8c8f510739b7b49c4`，v2、min32／target35、六個ELF64 AArch64含libil2cpp已核對；沒有頭盔安裝。

| 最終PC場（前綴20261030） | 幀／最大來源年齡 | 證據 |
|---|---|---|
| 031303-baf6e9b4 | 2144／0.186412秒 | 真正Space1／R1／Right20，GPU看見自身與同伴步槍，彈藥29→30／89、方位60°，AI血量60／Pause／淘汰0與隱藏自身武器；封存耗彈1／中彈5／耗損100，無PCM |
| 031732-438e779c | 1800／0.195382秒 | **39 UI／native**：保存配置與preflight、動態名冊、天氣／AI／Pause／Resume／End、鏡頭及封存回放；新profile即時／末幀玩家步槍264面、掩體642面均保留，原生day／storm／pause實際檢視 |
| 032205-e46fb4ea | 七場509／0.220640秒 | 五個真正server／每房一個client隔離、單房End／重用、之後Linked、舊票／升權拒絕、七個stream封存；每場均service-rifle-v1，非25台負載 |
| 032841-f0e9103e | 2573／0.379273秒 | 新check-desktop-rifle.py，一般未掛診斷的可見玩家；真正Left14／Down5瞄準黃準星、Space兩次，敵軍100→50→0、彈匣30→29→28；封存ammo2／hit2／kill1／100%、自身血量100，回放一致；沒有注入pose／combat |

四場組均Simulation／Simulated、pendingTelemetry=false、活動0、cleanup零錯誤；writer關閉後30／14／26／14檔複製回F與SSD原件逐檔SHA-256一致且保留原件。另 `unity-admission/20261030-032225-ed6333fe` **8項無圖形**入場／撤銷／transport釋放／同admission重連通過，375幀、封存回放一致、活動0；未重跑走離出生點的互動重連。自有原生程序清空，相關log無NullReference／MissingReference／ObjectDisposed等異常。程式與binary仍F、runtime明確SSD；F USB全資料、跨機及25台未驗收。source age是擷取新鮮度，非玩家RTT或FPS。本輪雨夜／Pause看見新武器但沒有重做DSP量測；舊聲光／鍵盤碰撞證據保留，不混算新版。

機器證據彙整於artifacts/rifle-validation.json，包含原生接受的pointer到muzzle0.15m及資料／圖片／snapshot雜湊。原5080仍API0.16與原歷史且health ok，未替換正式資料／憑證。功能提交 `b33d76074d1362a74f573b2aae1c855e35a1d703` 已推送並核對遠端main相同。[CI run40942043585](https://github.com/peca12968/vr-command-center/actions/runs/40942043585)／check123687654479已結束，steps=null、annotation為近期付款失敗或支出限制、工作未啟動；另有ubuntu遷移通知。未改帳務或重跑；GitHub #1已同步新ROADMAP、結果與限制，保持open並保留前次完整內容。完整11項長期目標維持開發中；接續人物／敵軍美術、握持／換彈動畫、複雜通路／地形、原停頓原因／啟動旗標、長任務／跨機；Quest／VIVE、MR、廠商硬體及25台待設備與分階段驗收。

## 2026-10-30：新開 VR 場地配置檢查與草稿／歷史分離

依使用者「目前沒有頭盔，先繼續電腦端」，從乾淨 `acbdb9c` 接續。API／控制台 **0.18.0** 新增配置預覽及真正新開場的後端檢查，Unity **0.20.1／Android code23／NGO仍19**。共用 `ArenaLayout` 使用現有旋轉沙包／油桶包圍盒，檢查 Y 地面、角度／素材、整體 ±6m 邊界、四軸 SAT 重疊及真正五席出生位的 0.3m 通行空間。貼齊沙包允許；初始敵軍容量與實際規劃共用有序 0.75m 網格，單房需求為總數、Linked 為每房最多 ceil(總數／5)。未改 rules0.8.0 的碰撞／命中／導航，不能把容量當效能、通路可達性或運行中增援保證。

報告 version1／profile vr-room-v1／rulesVersion0.8.0／明確 mode，最多500物件、128問題但保留完整數量及全部無效索引。Master 的 POST `/api/mission-layout` 只預覽不保存；GET 精確任務版本 `/layout?mode=...` 沿用已認證共用範本讀取政策，每次明確 Actor。新 Create 的檢查在權限、已接受 request key 及房間衝突之後、任何提交之前，無效時400帶layout且不占房、不消耗未接受key。草稿仍可另存／修訂，舊場次投影、歷史世界及已接受原樣重試不重新套拒絕政策；測試涵蓋舊無效配置恢復、End後舊key只確認、修正後可重用先前未接受key。MR applies=false／canStart=null，不能稱校正通過。envelope6／任務schema1／world schema1／驗票2／NGO19不變；Core明確參考netstandard2.1 Simulation，Unity不引用後端。

控制台草稿自動檢查、紅色全部問題物件、真實出生空間及可點選問題；開場區讀精確保存版本／模式，未完成或未知版本不放行，未保存修正不會批准舊版。各請求序號、登入epoch、精確草稿／選擇及每次登入快取防止晚回應誤批准；後端另獨立檢查。API／UI須一起升0.18。操作與限制見 [LAYOUT.md](LAYOUT.md)，仍無MR、硬體、複雜通路／地形、25台或頭盔證據。

locked restore／Release build通過、0警告／錯誤，**510核心、403 HTTP、43世界串流、23 Node／158 Chromium**通過。新增旋轉角落／相切／AABB重疊但OBB分離、真正出生半徑、84格初始敵軍容量、128問題截斷、歷史與權限、草稿保存／修訂／新舊開場、模式切換與晚回應／登出／未知版本拒絕等檢查；沒有以dotnet test取代Checks。Core→Simulation新直接參考已更新全部相依lock，沒有套件升版。首次舊任務版本測試使用5.5m／45°沙包，角落出界，被正確擋住；改為4.5m並保留版本／重試目的。新增UI測試第二次嘗試從最新版選單直接選已移入歷史的原版而失敗，改以另一個現存無效head測換選晚回應，未放寬產品規則。桌面及390px截圖實際檢視，無頁面錯誤／CSP違反；失敗log／圖片保留在artifacts。

真正Prepare、**51 EditMode（0 failed／skipped）**、Desktop／Quest均exit0，未RebuildArena；新增5項涵蓋實際初始規劃84／85差異、出生／旋轉／截斷與舊重疊世界仍可讀。scene／prefab識別保持，兩端fingerprint同為 `2173ae32671877346fb6d0dfb33c3335928ba834c7a2ac12928d45a4ea6582a1`。Desktop receipt UTC18:35:10.0418215Z、Quest18:42:38.6848331Z（10/29）；APK46,142,410 bytes，SHA-256 `3e3c1a3be70f5770bc1a964d4cdd4266f12e3445175d90686dda821c2cf72e72`，v2簽章、min32／target35及六個ELF64 AArch64含libil2cpp已核對。managed SDK兩分支各14 runtime／12 NUnit來源僅型別綁定，與真正執行分開。field-props-v1／音訊生成check及293官方Transport檔唯一補丁核對通過；素材pin與wire規則未變。

新binary自己的SSD場 `desktop-venue/20261030-024255-e19b9185` **37項UI／native**通過，包含保存版本的UI／伺服器preflight、兩個真正client及替代peer、Begin／StormNight／Pause／Advance傷害／Resume／End、精確鏡頭與封存回放。已用computer-use檢視並保存白天、雨夜及Pause原生GPU原圖。736幀、最大來源年齡0.167620秒；回放／ledger一致、pendingTelemetry=false、活動0、cleanup零錯誤。停止writer後14檔複製回F與SSD逐檔SHA-256一致且保留原件；程式與binary仍在F，來源全部Simulation／Simulated。瀏覽器觀戰是SwiftShader，非真實GPU／頭盔效能。本輪未重跑聲光DSP或完整鍵盤碰撞，上一輪相同規則的證據仍保留，不能混算為新版重驗。

新binary另於 `desktop-venue/20261030-024533-f361585a` 通過五個真正server／每房一個client、權限與環境／AI隔離、單房End／重用、全部封存後Linked及舊票拒絕；七場58／93／99／104／107／58／64幀（共583），最大來源年齡0.149419秒，全部回放一致、pendingTelemetry=false／活動0／cleanup零錯誤。writer停止後26檔SSD與F snapshot逐檔SHA-256一致，原件保留；不是25台負載。`unity-admission/20261030-024637-eb92d672` 8項無圖形入場／撤銷／真正transport釋放／同admission重連回歸通過，364幀、封存回放一致、活動0；本輪沒有走離出生點的互動重連，舊證據保留。機器證據彙整於artifacts/layout-validation.json；自有原生程序已清空。功能提交 `921abb58b40e010c8130b4068810ad257729c27f` 已推送並核對遠端main相同。[CI run40934368225](https://github.com/peca12968/vr-command-center/actions/runs/40934368225)／check123660878977已結束，steps=null、annotation明確為近期付款失敗或支出限制，工作未啟動；另有ubuntu遷移通知，未改帳務或重跑。GitHub #1已同步目前ROADMAP、新結果與限制，讀回確認open且保留前次完整內容。原5080仍為原v0.16 DLL／資料且health ok，沒有為測試替換正式歷史。完整11項長期目標維持開發中；下一主線為人物／武器美術、複雜通路／地形、原停頓原因／啟動旗標、長任務與跨機，取得設備後再做Quest／VIVE、MR、廠商硬體及25台。

## 2026-10-30：原創沙包／油桶、保存素材版本及新舊觀戰

上一輪姿態分類與診斷屬實際進度。本輪從乾淨 `389eaa5` 接續無頭盔的PC主線，將玩家原方盒掩體換成自製低多邊形三層沙包／十二邊油桶，含縫線、桶箍、封蓋與警示色。固定生成器產出相同Unity Resources／瀏覽器ES module位置、法線、索引及頂點色；沙包256／油桶386三角形，重用兩個Mesh及單一材質，不新增Physics Collider。自製URP光照／霧shader引用既有URP shadow／depth pass，玩家、NPC、武器其餘幾何仍為原型；不是完整人物美術或頭盔驗收。

新增明確assetSet=`field-props-v1`，只由新Unity來源指定；Create預設、既有來源及缺欄位舊匯出保持primitives-v1。API／UI **0.17.0**支援兩個已知版本、未知拒絕、已接受header不可變；world schema1、rules0.8.0、environmentVersion1、envelope6／票券2不變。原binary header／checksum不改寫，DB結構未變不表示可降舊reader。NGO **19**隔離舊遊戲程序的不同外觀，全部遊戲端需一起更新；沒有RebuildArena。shader／Resources JSON已納入兩端來源fingerprint。v1資料SHA `7911140960f5e947f4cb7c474913608d7db5c1bec7c3558ffd9aac81eb6e3dc2`固定，生成器check與記憶體改色反例拒絕均通過；改模型須新ID且保留v1，不能覆寫pin改舊回放。

外觀不改碰撞／命中／導航：沙包2×.9×.7m，油桶.7×1.2×.7m，仍使用原旋轉方盒；桶邊角與袋體倒角／縫隙可能擋射線或行走，非逐pixel命中。觀戰明示包圍盒。配置圖原沙包僅畫1.6m、桶半徑.4m，現校正2m／.35m並畫虛線包圍盒；尚無擺放重疊／可玩區域檢查，沒有把示意圖稱MR校正。模型與操作／升級見[FIELD_PROPS.md](FIELD_PROPS.md)。

真正Prepare／**46 EditMode（0 failed／skipped）**／Desktop／Quest均exit0。新增4項EditMode涵蓋原碰撞尺寸、400面預算、有限頂點／外向法線、資源重用／無Collider及壞網格；直接資產匯入與native GPU另驗，SDK Android／Windows各14 runtime／11 NUnit檔只證型別綁定，不含URP shader執行。bundle **0.20.0／Android code22／NGO19**；原scene／prefab ID保持，兩平台fingerprint同為 `638b0543095bf79ee3e54a682171cfc6858cc0b4d3d06bad52ac65b617d4b7ef`。APK46,128,950 bytes、SHA-256 `55b3c366c33409289823c643549233795da06f7b0ce78f08bad3443c212866d5`，v2簽章、min32／target35及六個ELF64 AArch64庫含libil2cpp核對通過；未安裝頭盔。

locked restore／Release build通過、0警告／錯誤，**489核心、369 HTTP、43世界串流**通過。新增新舊profile、預設保留舊值、未知拒絕與重試不可換外觀。首次核心檢查發現API canonical header重建仍固定legacy，導致新profile被拒；保留field-checks-before-profile-fix.log，改為先驗證已知profile再以該profile重建canonical幾何後通過，房間／作者／身分檢查未放寬。

**23 Node／142 Chromium**通過，包含Unity／Web資料一致、資料範圍、舊串流仍12面方盒、配置尺寸及原權限／任務／鏡頭／聲光。首次瀏覽器在夜間sun=.08斷言失敗，原PNG／log保留；舊檢查只等待雨線，而閃電期間也有雨線，現明確等待下雨且非閃電狀態。首輪沒有保存原始sun值，未回推其精確tick／成因；後續weather-first-rain.json記錄tick20／sun.08／非flash。這是採樣條件修正，不改聲光規則或放寬亮度值。頁尾升v0.17後另有完整native UI流程與截圖覆蓋，沒有再重跑所有純瀏覽器項目。

| 原生場 | 範圍 | 幀／最高取樣來源年齡 | 結果 |
|---|---|---|---|
| 012703-9bbae7cd | 真正鍵盤掩體 | 5555／0.603690秒 | W17→沙包z=-2.6500003、S5→-2.9、D10→x=-2.5000005、W20→45°油桶z=-2.219239；各階段connected=true、健康100／30+90不變。先Down8觀看模型，移動仍只取yaw；輸入工具一次busy後重新觀測焦點及已接受z=-2.7000003，再完成原流程，未放寬斷言 |
| 013745-0900ae86 | 真正GPU／本玩家DSP | 274／0.157371秒 | 新模型／shader的flash亮度增32.6950，首次採樣flash141／thunder184（預期180，既定4tick容差內）；雨／雷／storm非零，穩定Pause52／Clear57窗口RMS0、PCM能量核對通過 |
| 013854-b0fa652b | 控制台＋真正PC | 1351／0.158653秒 | **35 UI／native**：保存／重載配置到GPU、新profile642面即時觀戰、精確鏡頭及封存末幀保留同版本、AI傷害與歷史名冊／回放一致；白天／雨夜／Pause／新素材回放均實際檢視 |
| 014757-f97348ee | 五房獨立／重用／Linked | 七場共533／0.204837秒 | 五個真正server／每房一個client的環境／AI／權限隔離、單房End／重用、之後五房Linked、舊票／升權拒絕及七個獨立stream精確封存均通過；所有header為field-props-v1，非25台負載 |

以上目錄前綴均20261030，來源維持Simulation／Simulated，全部pendingTelemetry=false、活動0、cleanup零錯誤。14／23／14／26檔於writer停止後複製回F，與SSD原件逐檔SHA-256一致並保留原件。原始GPU截圖未美化；瀏覽器為SwiftShader，不是頭盔／真實GPU效能。另 `unity-admission/20261030-015042-da81b3b3` **8項無圖形**入場／撤銷／真正transport release／同admission重連通過，370幀；這輪沒有重驗走離出生點後的視窗重連，舊互動證據保留。

機器證據在artifacts/field-validation.json，原生成物、.meta及成功匯入狀態保存；上游Three／Transport未修改。原5080仍為原v0.16 DLL／歷史，health ok；新程式使用自己的v0.17 API及新runtime，沒有移動或替換正式資料。人物／武器、擺放合法性、原停頓原因／啟動旗標、長任務／跨機、頭盔／MR／VIVE、廠商硬體及25台仍待，完整11項長期目標維持開發中。


功能提交 `df3a86552a3b2facb9c2d4f6dd89c615352cf055` 已推送並核對遠端main相同。[CI run40926478858](https://github.com/peca12968/vr-command-center/actions/runs/40926478858)／check123633239506已結束，steps=null、annotation為近期付款失敗或支出限制，工作未啟動；另有ubuntu遷移通知。未改帳務或重跑，新增生成器check尚未在雲端執行。GitHub #1已同步新版ROADMAP、證據及未解限制，保持開啟並保留前次內容。

## 2026-10-30：姿態逾時分類與可重現封包中斷

上一輪HUD屬實際進度。本輪從乾淨 `60713ba` 接續使用者「無頭盔、先繼續電腦端」。唯讀核對原場 `20261030-000040-9a2f550c` 的worlds.db：666→667幀相差688ms，tick仍1328；668幀connected=false，669幀100ms後恢復，頭部位置／健康100／彈藥29不變。先前警告把tracking、PoseAccepted及connected合併成POSE REJECTED，原PNG與0.25秒觀測不能分辨原因。這些新證據確認一次保存停頓與短暫非參戰狀態，不足以判定GPU、收件間隔、封包、CPU／IO或其他停頓根因；保留原資料，未宣稱修好延遲。

HUD現在分別顯示TRACKING INVALID、POSE REJECTED（PoseAccepted=false）及POSE STREAM STALE（前兩者有效但body.connected=false），桌面／XR文字共用。STALE維持紅色警告、非ACTIVE時不顯示準星／標籤；沒有延遲隱藏警告，也沒有改伺服器0.5秒姿態新鮮度、防瞬移、碰撞、admission或射擊規則。各複製旗標不是原子快照，不能把標題當封包根因或跨機時間證明。

NativeWeatherProbe新增互斥 `--vr-hud-trace`，只限明確選用、全新絕對目錄、Windows Development自己的未追蹤可見玩家。不配置PCM、不讀GPU／輸出PNG；0.25秒狀態之外，每個實際HUD Repaint保存狀態／原始旗標轉換，512筆有界、截斷明示且保留最初證據，結束才寫出轉換。快照含引擎時間／frame delta；原圖像模式另保存ReadPixels／PNG／寫檔耗時。一般啟動不附掛，沒有麥克風、OS loopback、遠端輸入注入或新網路欄位。

新增 `check-desktop-pose.py`：自己的API／room3 server／可見玩家，僅兩個127.0.0.1端點間原樣轉送UDP，暫時丟棄該玩家上行1.2／1.2／6秒，下行維持。不解析／保存payload、不改防火牆或正式服務。原生場 `20261030-005407-10c17163` 三次均驗證body.connected=false及HUD的poseAccepted／ready／tracking=true；已用computer-use實際看見紅色STALE、無準星，恢復後同admission／原位置／健康／彈藥維持，真正Space一次30→29，封存耗彈1／耗損0與回放一致。共丟棄386 datagrams、保存618幀、最大來源年齡0.160829秒；這是世界發布新鮮度，不能拿來充當被丟棄的玩家上行延遲。

逐繪製trace保存10次轉換，三次受控STALE到下一次ACTIVE為約0.8002／0.7009／5.5004秒。另捕捉入場初期POSE REJECTED約0.0369秒、其後STALE約0.0887秒才到AWAITING START，反映初始false及分開複製的到達順序；未隱藏這些警告、未把初始化當作實際拒絕封包證明。ACTIVE之後除了三次指定中斷沒有其他警告轉換；單次本機場不能證明零抖動。trace模式audioSamples=callbackCount=0、captures及captureTimings空、無PNG／WAV；三份Windows GPU截圖另存證據。

Prepare／**42項真正EditMode（0 failed／skipped）**／Desktop／Quest均exit0。新增3項測試涵蓋分類、短於週期採樣的轉換及容量／首筆保留；離線SDK Android／Windows各13 runtime／10 NUnit檔型別綁定通過，非執行證據。Transport的293官方檔／唯一修正驗證通過，未改上游補丁。沒有RebuildArena，原scene／prefab ID不變；bundle **0.19.1／Android code21／NGO仍18**，兩平台fingerprint同為 `b555847946006ec29716f4b302d9b331d15d914672774f308187c3d0bb7b4b93`。APK46,113,704 bytes、SHA-256 `36c8c52b9cfde24ae066ceb6649224d4018b0a879a4af2bca0b628e109dfff42`，v2簽章、min32／target35及六個ELF64 AArch64庫含libil2cpp核對通過；沒有頭盔運行。

同binary原生weather回歸 `20261030-005548-22ee28c2`：275幀／最大來源年齡0.160839秒；GPU閃電區域亮度增加27.6674，首次採樣flash141／thunder181（預期180，10Hz觀測容差內）。雨／雷／storm DSP非零，穩定Pause52／Clear59音訊窗口RMS均0，PCM量化核對通過；night／flash PNG已實際檢視。六次GPU讀回／編碼／寫檔耗時18.32–24.30ms，不能回推舊場停頓原因。兩場均pendingTelemetry=false、活動0、cleanup零錯誤；16／23檔於writer關閉後複製回F，與SSD原件SHA-256一致，原件保留。

完整機器證據在 `artifacts/pose-validation.json`、原資料核對在 `pose-historical-evidence.json`；操作／限制見 [TACTICAL_HUD.md](TACTICAL_HUD.md)。本輪無共享遊戲規則、後端或管理Web UI變更，不重算歷史485核心／369 HTTP／43世界／140 Chromium。5080 health仍ok，正式資料／DLL未換。啟動旗標提示、原停頓根因、長任務／跨機、3D軍事素材、頭盔／MR／VIVE、硬體與25台仍待；完整長期目標維持開發中。


功能提交 `b835d8c0327a3999ed6c2b756ded859c7b610558` 已推送並核對遠端main相同。[CI run 40917071587](https://github.com/peca12968/vr-command-center/actions/runs/40917071587)／check123600047504已結束，jobs.steps=null；annotation明確為近期付款失敗或支出限制、工作未啟動，另有ubuntu遷移通知。未重跑、改帳務或將其算測試失敗；本機證據與雲端未執行分開記錄。GitHub #1已同步新證據、未解限制及目前ROADMAP，重新讀取確認保持open、前次內容完整保留。

## 2026-10-30：軍事戰鬥HUD、場地方位與遮擋標記

上一輪原生聲光屬實際進度。本輪從乾淨 `65d5185` 接續無頭盔的電腦端與原始11項目標，新增 `TacticalHud`：軍綠狀態面板、血量條、大字彈匣／備彈、場地方位刻度、受遮擋限制的HOSTILE／ALLY短識別及血量條，桌面保留Simulation來源。準星沿用武器／掩體預測，射擊／換彈／傷害仍由server確認。XR既有world-space文字共用狀態優先序，修正淘汰被追蹤異常蓋過的情況；沒有把桌面方位或浮標直接套進HMD。

標記只讀同房、存活參戰者及已複製幾何，以與命中預測相同的盒檢查胸部視線，其他活角色亦可遮擋。候選10Hz、最多32個／8標記，每繪製幀用最新收到狀態重新檢查；不在掩體後保留舊標籤。這是保守顯示，部分露頭可能無標記，非逐pixel遮擋或防作弊／保密邊界。000°是場景正Z、不是地理北。原本角色／武器／物件幾何未改，primitives-v1、rules0.8.0、NGO18／API0.16及所有世界／事件契約保持。

首次真正Prepare抓到NetworkList不實作IEnumerable的CS1503，改為重用當幀自有快照後通過；最終 **39項真正EditMode（0 failed／skipped）**、Desktop／Quest均exit0，保存場景／玩家識別保持，無RebuildArena。生成設定依成功匯入結果保留；Quest建置後URP清單無最終差異。bundle **0.19.0／Android code20／NGO仍18**，兩平台fingerprint同為 `8fa5a0e8609b8f3521d14f98effa437075aecef2fcaed05963c8e585c48053df`。APK46,106,368 bytes，SHA-256 `2cd48b1c9371e4d8bbccb807ce133a0f0a718557982abbe8742bc7a6b44bbe9c`；簽章v2、min32／target35及六個AArch64庫含libil2cpp核對通過，無頭盔運行。

新增5個有意義EditMode檢查，涵蓋狀態優先序、方位、旋轉掩體／角色遮擋、同房／參戰／死亡／距離及移動後的新遮擋。離線SDK Android／Windows各13 runtime／10 test型別編譯通過。另核對 `65d5185` 的腳本，確實已定義DEVELOPMENT_BUILD；上一輪文件寫成未定義是記錄錯誤，已更正UNITY_SDK_CHECK及歷史段落。這補正編譯範圍，不把型別綁定當執行、GPU或DSP證據。

新增 `check-desktop-hud.py`，自己的API／room3 server、可見玩家及真正peer。HUD-only診斷與weather音訊模式互斥，285秒上限，不配置／保存PCM；GPU讀回與HUD繪製快照有界，正常啟動不附掛。原生場 `20261030-000040-9a2f550c` 以computer-use真正按鍵：Space1次→30降29，R→30／89並看見RELOADING，Right20次→060°及右方友軍；初始兩名敵軍只標記胸部未被油桶擋住的一名。AI造成血量60後Pause，之後淘汰血量0顯示ELIMINATED；全部已實際檢視截圖。2680幀、最大來源年齡0.767627秒；耗彈1／中彈5／耗損100、回放ledger一致、活動0、cleanup零錯誤。14份引擎截圖與五份Windows畫面保存，audioSamples=callbackCount=0且無audio.wav。

同場一份自動PNG亦實際看見短暫POSE_REJECTED；0.25秒保存觀測未捕捉該狀態，各輸入檢查點為ACTIVE且body.connected=true，後續射擊／換彈／轉向正常。保留原圖，未量測該次原因／確切持續時間；不宣稱全程無短暫拒絕或診斷模式效能。HUD忠實顯示拒絕狀態，未放寬權威姿態／時間檢查或以隱藏警告修飾結果，後續需在一般模式補充抖動定位。

新binary再跑weather模式 `20261030-000808-6ae72ca2`：274幀／最大年齡0.167383秒，GPU閃電區域亮度增加27.6674（新HUD遮住部分比較區域），flash140／thunder180，雨雷非零／穩定暫停及晴天RMS0，PCM量化能量一致。一般無probe、visible-room1場 `20261030-001934-4bc01194` **33項 UI／native**也通過，127幀／0.167325秒，控制台任務、動態名冊、環境／AI、鏡頭及封存回放一致。三場全數精確封存、pendingTelemetry=false、活動0、cleanup零錯誤；30／23／14檔在writer關閉後複製回F，與SSD原件SHA-256一致，保留原件，未移動5080資料。

完整驗證在 artifacts/tactical-validation.json，操作及界線見 [TACTICAL_HUD.md](TACTICAL_HUD.md)。本輪無後端／共享遊戲規則或管理Web UI變更，不重算歷史485核心／140 Chromium。3D軍事素材、完整長任務／一般模式抖動、頭盔／MR／VIVE、硬體、跨機及25台仍待，完整長期目標保持開發中。

功能提交 `0678c8f57aab2d20bc5c9bb25ac82bf8c4cef8af` 已推送並核對遠端main相同。CI run `40912886942`／check `123585281027` 已結束，steps=[]、日誌404 BlobNotFound；annotation仍為近期付款失敗或支出限制，另有ubuntu遷移通知，未改帳務或重跑。GitHub #1同步新HUD、原生證據與短暫姿態拒絕限制，保持開啟。原5080 health ok，自有Unity程序清空，正式DLL／資料未換。

## 2026-10-29：原生GPU閃電與本玩家DSP雨雷輸出

上一輪精確觀戰屬實際進度。本輪從乾淨 `893332e` 接續無頭盔的PC主線，針對需求5補強原生證據。新增 `NativeWeatherProbe` 與 `scripts/check-desktop-weather.py`：只有未追蹤、可見的Windows Development玩家，在明確CLI開關及全新絕對目錄下才附掛；一般啟動、Editor、Android或batch不附掛。只讀本玩家AudioListener DSP及GPU backbuffer，沒有麥克風、OS loopback、其他應用程式或遊戲輸入注入。兩個AudioSource仍由既有權威tick規則控制，僅增加LastApplied本地觀測欄位；不改戰鬥、網路或環境v1語意。

首次真正Prepare發現未宣告Image Conversion模組而出現CS1061；新增正式builtin imageconversion1.0.0後，UPM成功匯入並保存lock，Prepare／**34項EditMode**／Desktop／Quest均exit0。保存Arena／PlayerAvatar識別未變，無RebuildArena。bundle **0.18.1／Android code19／NGO仍18**，API0.16／驗票2／envelope6／world schema1／environmentVersion1保持。兩平台fingerprint相同：`ce2222224a687942a6492e9e861e72e4c5452134cf7cf6bb5537b09289faa7f5`。Quest ARM64／IL2CPP APK為46,085,944 bytes、SHA-256 `b0fd3ba170e953af7e2b388e52e51916b293e5cd0edefa2ee734c63c483094a0`，v2簽章、code19／0.18.1、min32／target35及六個AArch64原生庫含libil2cpp核對通過，沒有頭盔安裝或運行。

固定雨雷素材 `generate-weather-audio.py --check` 通過；離線managed SDK Android／Windows各12 runtime／9 test型別編譯通過，單一WeatherView Core／Audio窄檢查也通過。當時誤記「窄SDK圖沒有DEVELOPMENT_BUILD」；2026-10-30核對當時腳本已有該旗標，已更正文件。此圖仍只做型別綁定，真正Windows另有建置與運行；不把SDK當Editor／DSP或GPU證據。原生probe使用有界緩衝及音訊執行緒純記憶體採樣，End後才輸出PCM WAV並核對格式／樣本／量化能量，截圖於真實渲染幀結束後讀回。分析使用現有bundled Python／Pillow12.3.0，沒有全域安裝或更改系統音效設定。

第一場 `20261029-230508-0b5e7d5e` CLI通過：276幀、最大來源年齡0.614726秒，GPU閃電區域平均亮度比夜間增加34.5419（0–255）；48kHz雙聲道／24.085秒PCM，已檢視night.png及flash.png。第二場 `20261029-231752-cb648d31` 的靜音分類檢查失敗：10Hz主執行緒觀測把Resume後的兩個非零DSP回呼，誤歸到前一筆Paused快照；原始回呼時間12.532／12.551秒，第一筆已保存Running快照在12.554秒，穩定暫停區間均為零。保留失敗及278幀封存，修正分析器同時檢查狀態切換兩側、只分類穩定內部區間，不降低1e-6靜音或1.5秒來源門檻，也不更改遊戲播放邏輯。

最終 `20261029-232018-64b01ff3` 完整重驗通過：273幀、最大來源年齡0.154812秒；首次觀測閃電tick140、雷聲tick180，符合既有40tick延遲及10Hz觀測容差。2,263,040個交錯樣本／48kHz雙聲道、WAV RMS0.0164812；穩定雷聲／雨聲／暴風雨最大RMS0.0715666／0.0106800／0.0679965，暫停53批、尾音後晴天57批RMS皆0。閃電區域亮度增加34.5419，六份GPU截圖保存。關閉雷電不啟動新雷聲，但既有雷聲保留尾音；Pause停止聲音。這是原有規則，檢查不把自然尾音誤稱立即靜音。完整操作與範圍見 [NATIVE_WEATHER.md](NATIVE_WEATHER.md)。

一般未啟用probe、visible-room1的新binary場 `20261029-232121-aeab2eb8` **33項 UI／native**回歸通過，124幀、最大來源年齡0.133583秒。任務配置／動態名冊、天氣／AI／暫停、鏡頭保存及封存回放統計一致；所有自有場次皆精確封存、pendingTelemetry=false、活動0、cleanup零錯誤。三個聲光場各23檔及一般場14檔，在writer全停後複製回F，與實際解析的SSD原件逐檔SHA-256一致；原件保留。診斷PCM不進入worlds.db或一般回放，不等同任務原始音軌／影片交付。總驗證在 artifacts/weather-probe-validation.json，原5080 health ok，自有Unity程序清空，未更換正式服務DLL／資料。

本輪沒有後端／共享遊戲規則或管理Web UI變更，不重算歷史485核心／140 Chromium；新34 EditMode與33 native分開記錄。GPU擷取證明真正Windows閃光，DSP證明本遊戲混音有雨雷及穩定靜音，仍不證明人員聽感、實體喇叭／耳機、聲壓、Quest／VIVE、MR或25台。長期目標及完整11項保持開發中，接續軍事美術／長任務操作、跨機、頭盔／MR／硬體及25台分階段驗收。

功能提交 `dca912244e4e564c063b7850f93dd6612d9a5a7f` 已推送並核對遠端main相同。CI run `40902074120`／check `123546776707` 已結束，steps=[]、日誌404 BlobNotFound；annotation仍為近期付款失敗或支出限制，另有ubuntu遷移通知，未改帳務或重跑。GitHub #1同步原生聲光證據、失敗原因及限制，保持開啟。沒有以雲端未執行取代本機結果或宣布完整驗收。

## 2026-10-29：精確觀戰位置、角度與原生錄製回放

上一輪屬實際進度：掩體修正與 Windows／Quest v0.18 已交付。本輪從乾淨 `c46ea42` 接續完整長期目標與使用者「先繼續電腦端」。在既有自由觀戰旁新增看向 X／Y／Z、水平角／俯視角（度）、距離，以及讀取／套用按鈕及 Enter 操作；配合原拖曳、平移、縮放、角色跟隨及書籤，不占玩家席位。欄位是全館世界座標的觀看中心，不冒充相機位置或玩家姿態。

本地草稿只在明確套用時改動畫面，背景即時快照／書籤讀取不覆蓋編輯，錯誤或空白輸入不移動相機。登出／換場次清空並停用，讀取新錄製後啟用；同場回放／倍速重連不清草稿。套用切自由鏡頭，持久保存仍沿用身分／房間隔離、原樣重試與 tombstone 的既有書籤 API，沒有新增管理路由或移動玩家的能力。輸入範圍與既有書籤一致，參數以度數轉換後保存；操作見 [OBSERVER_CAMERA.md](OBSERVER_CAMERA.md)。

新增共用 camera-controls 瀏覽器檢查：數值對照實際 rendered camera、讀回角度、快照抵達仍保留草稿、空白／座標121／距離1／俯視0拒絕、真正左／右／Shift拖曳、wheel、方向鍵與±縮放，以及操作期間無管理寫入。新 native 檢查保存數值視角後核對 API 參數，切跟隨／舊書籤，再從封存回放讀回自訂位置。第一輪完整測試將換場清空斷言放在新 header 已填入預設值之後而失敗；保留 artifacts/camera-browser.log，修正為換場後、開始讀取新場之前檢查，不更改產品來迎合錯誤時點。

鎖定還原、隔離及一般 Release 皆成功，0警告／0錯誤。最終 **17 Node 資料＋140 Chromium** 通過，沒有頁面錯誤／CSP違反；已檢視 artifacts/console/world-camera-precise.png 與 world-replay-mobile.png，桌面數值／視角可見、390px沒有水平溢位。資料驗證與瀏覽器軟體 WebGL 證據分開，不重算歷史485核心／34 Unity EditMode。後端C#與Unity來源未改，API0.16／NGO18／世界及書籤格式保持；沿用 fingerprint `db5433bed1791b8e0b9be4587a657a005cb7471aa1f35a16d6fda0121c95eea1` 的 Windows／Quest，不為純管理UI重建二進位。

真正 Windows server／兩個 client 場 `20261029-224032-95b1d5c4`，以自己的隔離API／短票券與SSD runtime跑 **33項 UI／native**：看向(-28,1.25,0.4)、水平45°、俯視45°、距離12m保存後，已封存回放恢復完全相同的 rendered camera `-22.00,9.74,-5.60`。共126幀、最大來源年齡0.186783秒，保持1.5秒門檻；pendingTelemetry=false、回放統計一致、活動0、cleanup零錯誤。關閉writer後14檔複製回F並與SSD原件SHA-256一致，原件保留，沒有搬動5080資料。機器可讀證據在 artifacts/camera-validation.json。

更新一般 Release 的靜態資產後，以不帶 --api-dll 的預設啟動方式再跑 `20261029-224353-c5c71ac0`：同樣33項通過，116幀、最大來源年齡0.140497秒，精確視角／回放／統計保持一致、活動0、cleanup零錯誤，14檔SSD／F snapshot雜湊一致。原5080仍health ok，自有Unity程序清空。已檢視桌面與手機截圖，沒有替換原服務DLL／資料。

觀戰為 Chromium SwiftShader，這輪證明真實瀏覽器事件／操作與原生遊戲資料互通，不稱完整人工手感／真實GPU或頭盔驗收。原生閃電／雷聲、長任務鏡頭操作、正式軍事美術、跨機、Quest／VIVE、MR、硬體與25台仍待；完整11項保持開發中。

功能提交 `e15603b1d3a8cf25d48fb0dce6507512d4220574` 已推送並核對遠端main相同。CI run `40895099022`／check `123521924481` 已結束，steps=[]、日誌404 BlobNotFound；annotation仍為近期付款失敗或支出限制，另有ubuntu遷移通知，未改帳務或重跑。GitHub #1同步新功能、驗證與限制，保持開啟；原5080服務未換DLL或資料。

## 2026-10-29：電腦掩體移動 v0.18 與真正鍵盤驗證

從乾淨 `3106708` 接續使用者「沒有頭盔，先繼續電腦端」及完整長期目標。先在舊 v0.17 真正 Windows 玩家視窗重現問題：對沙包連續 W 17 次，伺服器保留最後合法 z=-2.65，但相機繼續向前、HUD 顯示 POSE REJECTED、connected=false。反例 `20261029-214952-e8fee276` 正常結束封存，只計為問題重現。

新增共用 `ArenaWalkSurface`，抽出原 GridNavigation 的 0.3m 半徑／旋轉矩形足跡及每最多 0.05m 線段取樣，供權威、AI 與桌面預測使用。桌面按同房間已複製幾何裁切移動、比較原位置出發的單軸候選，拒絕後回到最後接受的合成姿態；伺服器時間／位移／掩體檢查保持。不是解析掃掠或完整物理，Tracked XR 不被搬動。`CombatPropState` 新增 room 是 wire 變更，**NGO 18／bundle 0.18.0／Android code 18**，所有遊戲程序一起更新。API 0.16／驗票 2／envelope 6／world schema 1／rules 0.8.0 保持。Prepare 原位保存，沒有 RebuildArena，兩平台網路識別一致。

真正 Editor Prepare、**34 項 EditMode（0 failed／skipped）**、Windows 與 Quest 均 exit 0。Windows receipt 完成 UTC 14:07:11、Quest 14:15:35，來源 fingerprint 同為 `db5433bed1791b8e0b9be4587a657a005cb7471aa1f35a16d6fda0121c95eea1`。APK 45,993,624 bytes，SHA-256 `3f1303df47e52427f189f7305104f7dd9441e5b900239ed973db9cbb9aa24d41`；apksigner v2、code 18／0.18.0、min 32／target 35、六個 ELF64 AArch64 原生庫含 libil2cpp 核對通過。只是建置及靜態檢查，沒有安裝至頭盔。

鎖定還原及隔離／一般 Release 均成功、0 警告／0 錯誤；本輪實際 **485 核心、369 HTTP、43 世界串流** 通過。離線 managed 診斷 Android／Windows 各 11 runtime／9 test 型別編譯通過；Editor SDK 947 managed sources／13 assemblies 綁定及缺少 MetaQuest 直接參考的預期拒絕亦通過。診斷沒有執行 NUnit／UPM／ILPP／原生輸入，不能代替上方真正 Editor／binary 證據。嵌入 Transport 293 檔來源檢查保持通過。

新增可重現的 `scripts/check-desktop-collision.py`，自己的 API、room 3 server／可見 client、臨時票券與 SSD runtime；只接受外部操作完成檔，不注入姿態。`20261029-221556-be8bb604` 以 computer-use 真正鍵盤 W17／S5／D10／W20 四階段全部通過：沙包停在 (-3,1.65,-2.6500003)，退回 z=-2.9，側移 x=-2.5000005，再停在 45° 油桶前 z=-2.219239。每階段 connected=true、Simulated、健康100／彈匣30／備彈90；原生 HUD 沒有姿態拒絕，截圖 sandbag.png／barrel.png。共 **3889 幀**完整封存、最大量測來源年齡 **0.689724 秒**，回放／ledger 一致、活動0、cleanup零錯誤。

新 binary 另重驗：五房 `20261029-222305-af15ab00` 六組檢查、七場 **62／95／100／104／108／56／64 幀**，最大年齡 **0.22675 秒**；同 admission 撤銷／斷線恢復 `20261029-222346-d37c759b` **8 項／377 幀**，保留位置與健康／彈藥；控制台任務 `20261029-222449-7e99ae21` **15 項 UI／native／103 幀**、最大年齡 **0.164206 秒**，包含保存重載擺設、動態名冊、環境／AI／暫停、觀戰書籤與回放。全部精確封存、pendingTelemetry=false、統計一致及活動0。瀏覽器仍 SwiftShader，此輪沒有改 Web UI，不重算歷史 17 Node／122 Chromium。

三個 Venue runtime 在關閉 writer 後複製回 F，14／26／14 檔逐檔 SHA-256 與 SSD 原件一致，保留原件；不能宣稱 F USB 配置通過。機器可讀總驗證在 `artifacts/collision-validation.json`，各 build／check log 均保留。Unity 測試產生的 PerformanceTestRun JSON 明確忽略，不提交機器資訊或生成執行資料。操作與規則見 [DESKTOP_COLLISION.md](DESKTOP_COLLISION.md)。下一步是原生閃電／雷聲、自由鏡頭完整人工操作、軍事美術及跨機部署；Quest／VIVE、MR、廠商硬體、25 台及完整 11 項仍待驗，長期目標保持開發中。

功能提交 `c2ad954418f7dcc75cdb34392ad039a254e994d8` 已推送並核對遠端 main 相同。CI run `40891989275`／check `123510980195` 已結束，steps=[]、無可下載日誌（404 BlobNotFound）；annotation 明確為近期付款失敗或支出限制，另有 ubuntu-latest 遷移通知，未改帳務或重跑。原 5080 health ok，自有 Unity 程序已清空，沒有換正式 DLL／資料。GitHub #1 同步本輪與限制並保持開啟。

## 2026-10-29：控制台自訂任務接到真正 PC、圖形環境與原生觀戰

上一輪五房已交付，本輪從乾淨 `9c14d4d` 接續完整 11 項目標。新增 `scripts/start-desktop-control.py`，由操作員在自己的控制台建立／儲存／重載任務、建立 Preparing VR 場次與名冊；工具才啟動真正 Unity server，按 playerId＋admissionId 配發短效票券並啟動 client。開始、暫停、天氣與 AI 仍由控制台發令，不預先代替操作員建立固定任務。只接本工具自己新建 API，拒絕接管 Running／既有 combat source，玩家檔沒有 Master／GameServer key。

動態名冊可啟動新 client、關閉被移除入場的舊 client，並保留離場統計；最終按持久 PlayerJoined 事件分頁核對所有曾入場 ID，不用當前名冊取代歷史。共用 Venue 抽出 receipt／來源驗證及 server 啟動，舊五房工具沿用。operator-status 取自真正已接受世界幀的 phase／tick／環境／AI／連線玩家，持續維持 UTC 來源年齡 1.5 秒門檻。所有世界、頭手及戰鬥來源仍 Simulation。

`tests/browser/check-operator-native.cjs` 只接受本庫隔離目錄及 localhost 非 5080 的 Simulation ready；憑證直接讀自己的檔案進入頁面記憶體，不輸出值、不用正式預覽憑證。它實際透過 UI 配置沙包 (-3,0,0)／15°、油桶 (-1,0,1.5)／90°，儲存後清草稿、重新載入，再選已保存任務開房間 1。真正 native header 的世界座標為沙包 x=-31、油桶 z=1.5，與房間原點一致；兩名 client 以真實票券入場。測試亦在 Preparing 移除 Peer02，啟動 Peer03，最終統計保留三位歷史玩家。

首輪 `20261029-210117-f04e557f` 使用 computer-use 檢視真正 Direct3D 玩家視窗，看到配置、Clear／Day、由控制台改成 Storm／Night 後的暗場與雨線，以及 Pause HUD。原始截圖另複製到 artifacts/operator-ui/native-day.png／native-storm.png／native-paused.png。沒有錄到原生閃電瞬間或驗證雷聲聽感；不能把閃電設定啟用或瀏覽器音效圖當作原生聲光全驗收。此輪瀏覽器測試漏處理 End 確認框，最後 exact-seal 等待失敗，完整瀏覽器流程不算通過；修正對自己測試場確認框的處理後重驗。原場由工具正常 End，2730 幀完整封存、回放統計一致、活動數 0、cleanup 零錯誤，未動其他程序或預覽資料。

最終整合另確認真正世界 Running、Storm／Night／lightning、Paused tick 400 ms 不變、兩名 Advance／autoAttack 敵軍與確認傷害，並從 native recording 的控制台即時俯視、保存鏡頭、切跟隨後讀回位置、倍速與跳至末幀回放。**15 項 UI／native 檢查全過**，不是只檢查管理命令回應。隔離 API 場 `20261029-212125-ef9f8c83` 封存 **92 幀**、最大量測來源年齡 **0.15173 秒**。更新一般 Release 後，以不帶 --api-dll 的預設命令再重驗 `20261029-212436-81187953`：同樣 15 項通過、**94 幀**、最大年齡 **0.170777 秒**；Operator01 中彈 2／耗損 40／健康 60，Peer02 的歷史及 Peer03 均保留。兩場 pendingTelemetry=false、回放末幀／ledger 一致、活動 0。

測試觀戰瀏覽器明確為 Chromium SwiftShader，原生 GPU 畫面是上方獨立的 computer-use 證據；沒有稱瀏覽器已測真實 GPU、實際頭手或頭盔。控制台三處過時提示已更新為目前接入與仍待實機範圍。鎖定還原、隔離／一般 Release 建置都 0 警告／0 錯誤；完整既有瀏覽器回歸 **17 Node 資料＋122 Chromium** 通過，已檢視 artifacts/console/mission-planner.png 及 native-live-overhead 圖。

共用工具改動後，五房原生回歸 `20261029-211936-917f7f56` 也全過：七場 **62／100／104／108／114／56／63 幀**，最大來源年齡 **0.254718 秒**、回放統計一致、活動 0。仍使用明確 SSD runtime，關閉 writer 後複製回 F，與原件逐檔 SHA-256 一致；F USB 硬碟的限制不因本輪通過而解除。整體機器可讀驗證在 artifacts/operator-ui/validation.json，兩個啟動器的舊 receipt 反例均在建立場次前拒絕。

最後補強 UI 檢查器的版本競態：刷新允許已前進的較新序號，控制命令若確實收到 409，才由 UI 重新刷新並提出新操作，不重送已接受命令或移除版本／入場限制。全新預設命令場 `20261029-213239-26180ff6` 再通過 15 項、92 幀、最大來源年齡 0.212172 秒，雙管道精確封存、回放一致、活動 0、cleanup 零錯誤。可操作玩家原始日誌也確認 Direct3D 12 [level 12.2]，與觀戰的 SwiftShader 分開記錄。

Unity C#／NGO 17／bundle 0.17.0 及管理契約未變，沿用同源 fingerprint `d6baeb56101bc7adea85f4173d3e0a31788f1d5546ff6a2ab872a789ff242a20`，沒有為 Python／提示文字重建播放器，也不把歷史 29 EditMode／.NET 規則數字算成本輪新結果。操作見 [DESKTOP_CONTROL.md](DESKTOP_CONTROL.md)。下一步仍有原生完整聲光／碰撞／鏡頭人工操作、軍事美術、跨機部署／效能、Quest／VIVE、MR、硬體與 25 台；本機端到端操作不完成整體驗收。

功能提交 `86b7b32e7544133ba83d8ed454563ade4e325edb` 已推送並核對遠端 main 相同。CI run `40883545618`／check `123481119824` 已結束，steps／logs 為空；annotation 明確仍為近期付款失敗或支出限制，另有 ubuntu-latest 遷移通知。未改帳務或重跑；本機結果與雲端未執行分開。原 5080／PID 52992 仍 health ok，未換 DLL／資料；自有 native 程序均已停止。GitHub #1 同步本輪操作與限制，保持開發中。

## 2026-10-29：五房同時獨立、房間重用與之後的全館連線

上一輪已交付 PC 撤銷／重連，本輪從乾淨 `b36ac5d` 接續使用者「先繼續電腦端」，完整 11 項與 Quest／VIVE 目標保持開發中。新增 `scripts/start-desktop-venue.py`：自己的 API／七份臨時控制台與來源憑證、五個獨立任務、五個真正 Windows Unity server、每房一個真正 client，使用不同 UDP 埠及持久來源。可選一個房間顯示玩家視窗，其餘背景運行，控制台 URL／room/session/port／PID 存於 ready.json；玩家只有短效票券，所有頭手與戰鬥來源均為 Simulation。

新增 `--check` 原生流程，不注入戰鬥或姿態：五房不同天氣／日夜、敵軍 1–5、不同數量與角度的沙包／油桶，核對真正保存的世界、幾何及名冊。逐房控制台僅列自己的場次，跨房快照／統計／world／watch／Pause 全拒絕；有效 room-1 券送到 room-2 真正 server 亦拒絕。Room1 更新 Storm／Night／雷電及六名 Advance／autoAttack 敵軍，取得確認傷害後暫停，其他四房仍 Running、tick 前進且環境／AI／健康不變。

結束 room-1 後只釋放該房，其餘四房繼續；保留原統計與錄製並在房間 1 開新獨立場。四房仍占用時，全館 Linked 建立回 409。六個獨立歷史場次都精確封存後，Master 以一份任務新開五房 Linked、一個權威 server 加五個 client；舊獨立票券在仍未過期時拒絕，名冊使用新 admission。房間控制台不可 Begin／修改整個 Linked 環境，Master 控制通過。Linked 確認 AI 傷害、共同暫停 tick 凍結、End 與回放統計一致；七場保留不同 stream，最後活動數 0。這是新開共享世界，不合併舊世界或舊報表。

首次 F 槽全資料試跑落後 **13.996307 秒**，維持原 1.5 秒門檻而失敗；每程序兩個 job worker 的修正後試跑仍落後 **13.350486 秒**，移除物件的診斷也累積到約 23 秒，不能稱為成功。F 實際為 Seagate One Touch Hub／USB，C 為 Kingston NVMe；24 次 4 KiB flush+fsync 短測平均 F **17.166 ms**、C **1.754 ms**，支持同步持久寫入吞吐不足的判斷，並非完整磁碟／全負載保證。未關閉 flush、降低錄製頻率、丟棄幀、提高門檻、移除正式擺設或修改安全設定。

工具新增明確 `--runtime-root`。本輪使用 C 槽本機 AppData 下全新隔離目錄保存 SQLite／journal；程式碼、播放器、設定與證據目錄仍在 F 槽，沒有搬動原 5080 或既有資料。未指定時仍使用 F artifacts，不能宣稱 USB 配置已通過五房新鮮度。全部自有寫入程序停止後，才將 runtime 完整複製回 F 的 runtime-snapshot，保留 SSD 原件；逐檔 SHA-256 與來源一致。每程序兩個 job worker 是明確記錄的配置，並非延遲修復的單獨證據，官方參數見 DESKTOP_VENUE。

第一次兩 worker 探索因工具新增量測分支縮排錯誤而失敗，清理也被同一非預期例外中斷。已先查核該隔離 API 五場 End／世界全部封存，保存 manual-cleanup-seals，再僅停止該 fixture 的十個 native 與 API，未動正式預覽。現收尾各場獨立容錯、最外層 finally 一律停止自有程序；注入非預期 End／seal 例外的實際子程序守衛也通過。任何清理／快照錯誤均非零退出，不把該失敗試跑算成通過。

SSD 第一輪 `20261029-204334-40372c18` 七場封存幀數為 **63／95／99／104／109／56／65**，最大量測來源年齡 **0.195271 秒**。補上幾何精確位置、舊券尚未到期、新 admission、空來源統計及清理守衛後，最終 `20261029-204521-bf4bf7ff` 再完整通過：幀數 **53／85／89／98／104／60／64**，七場回放／報表一致，最大來源年齡 **0.275004 秒**，活動數 0。六個斷言群組涵蓋上述原生流程；不是 25 人或跨機效能數字。

一般可操作模式 `20261029-204600-12e42550` 也實測：computer-use 選取真正玩家視窗，看到 Running／Room1／100 血量／30/90 彈藥與場景；關閉標題列按鈕後，工具自動 End 五場，各封存 **797／801／810／814／815 幀**，合計 **4037 幀**、回放統計一致、活動數 0，CLI 退出 0。此輪只驗證可操作視窗啟動與關窗，不重複宣稱測過射擊或五房觀戰圖形。截圖為 artifacts/venue-ui/room1-running.png。

機器可讀驗證在 `artifacts/venue-ui/validation.json`：三次成功 runtime-snapshot 與 SSD 原件逐檔一致、cleanup 零錯誤／零剩餘程序；播放器 receipt 指紋仍為 `d6baeb56101bc7adea85f4173d3e0a31788f1d5546ff6a2ab872a789ff242a20`，舊 receipt 反例在建立場次前拒絕。此次未改 C#／後端／管理 Web UI，不重建同源播放器，也不混算歷史 29 EditMode／.NET／Chromium。文件同步修正 API 舊票券範例及過時驗證狀態。下一步為圖形聲光／擺設、操作員控制與觀戰操作驗收，後續仍須跨機、Quest／VIVE、MR、廠商硬體及 25 台。操作見 [DESKTOP_VENUE.md](DESKTOP_VENUE.md)。

功能提交 `1c86e627c1a8fe24e23137e55a520bcf1d7df708` 已推送並核對遠端 main 相同。CI run `40876982663`／check `123458210322` 在任何 step 開始前結束，steps／logs 為空；annotation 仍為近期付款失敗或支出限制，另有 ubuntu-latest 遷移通知。未改帳務或重跑。原預覽 5080／PID 52992 仍 health ok，本輪沒有換 DLL／資料；自有 native 視窗及程序均已停止。GitHub #1 同步本輪 SSD 條件及五房成果並保持開發中。

## 2026-10-29：電腦重連、入場撤銷與 Windows UDP 接收修正

從乾淨 `2601c7d` 接續使用者「沒有頭盔，先繼續電腦端」。本輪遊戲端升為 **v0.17.0／Android code 17／NGO protocol 17**；API 仍為 0.16.0、驗票 protocol 2、場次 envelope 6／世界 schema 1 不變。所有遊戲 server／client 須一起更新，不混用 NGO 16／17。完整 11 項及 VIVE／Quest 相容目標仍開發中。

新增桌面斷線後的 **Reconnect / reload player ticket**：重讀原玩家設定檔，只能以 Client 及短效票券重新連線。操作員移除舊 admission 後，即使相同 playerId／席位重新加入，舊票券及舊 If-Match-Admission 仍拒絕；更新玩家檔後可在原程序按鈕重連，不把 Master／GameServer key 放進玩家。連線日誌只記狀態及 transport client ID，不輸出票券或密鑰。

同次 admission 的桌面恢復快取只保存權威核心已接受的 Simulated 頭手姿態。新玩家物件先接收該初始姿態，再送自己的輸入，避免走遠後從出生點重送而違反既有防瞬移規則。健康／彈藥保留於原戰鬥世界；快取按 playerId＋admissionId 隔離，名冊移除／換 admission 清除，Tracked 來源不使用桌面快取。這是單一 server 程序內的恢復，不是持久世界或頭盔追蹤恢復。

真正 Windows 強制斷線揭露另一個問題：server 與 UDP 埠仍存在，新 client 卻進不了 approval。延長等待及背景更新都未修復；只轉送原封包的診斷代理觀察 client 送出而 server 無回應，這些試跑均保留為失敗，不算通過。真正使用的 Transport 2.7.4 在失敗 receive completion 分支未歸還 buffer；[Unity 工程師的確認](https://discussions.unity.com/t/unity-transport-6-6-0-udp-host-stops-receiving-after-abrupt-client-disconnect-on-windows/1736023) 支持該原因，但討論版本較新，本機結果仍須分別驗證。最初的舊版重連失敗同時受傳輸與姿態問題影響，不能把單次失敗全歸因於姿態。

官方 registry 當下最新仍為 2.7.4，因此以固定官方 archive 嵌入 `Packages/com.unity.transport`，只在該分支增加 `ReceiveQueue.ReleaseBuffer(bufferIndex)`。保留 293 份官方檔案／授權／metadata，另存來源與逐檔雜湊；不修改 Library 快取、防火牆或接收容量。`check-transport-patch.py` 離線核對完整清單，隔離反例證明來源／ledger／額外檔案改動都拒絕；CI 亦加入核對。UPM lock 為 embedded，建置指紋納入嵌入來源與 UPSTREAM.json，詳見 TRANSPORT_PATCH。

真正 Editor 新增三項 admission／姿態快取測試及一項 Windows 原生 NetworkDriver 小佇列強制斷線回歸，合計 **29 項 EditMode 全通過，零失敗／零跳過**。最初 coroutine 測試誤用 Temp allocator，已改為 Persistent 後重驗。第一次 Desktop 建置遇到 PlayerDataCache 目錄存取失敗，保留 `unity-reconnect-desktop-first-failure.log`；未刪快取／改權限，重新執行同一建置後成功。SDK 診斷補上真正已匯入的 UnityEngine.TestRunner DLL 與直接 Transport 參考，Android／Windows 均通過 11 runtime／8 test 來源型別編譯；它不執行測試，也不驗證嵌入 Transport 原生行為。

Windows／Quest 最終成功 receipt 的來源指紋同為 `d6baeb56101bc7adea85f4173d3e0a31788f1d5546ff6a2ab872a789ff242a20`；scene file ID `1444571642`、prefab file ID `5227825248646244841` 保持，未重建場景。Prepare 在保存的 Arena 上將 NGO 16 升至 17。Windows 完成 UTC 11:56:05，Quest 完成 UTC 12:13:46；APK **45,987,512 bytes**、SHA-256 `a1d790645afab03bb9bb389e2856bf4392e4ee5daf2fb9b853504be7188fbccf`，v2 簽章、com.vrcommand.quest、版本 0.17.0／17、minSdk 32／targetSdk 35、六份 ARM64 native library 及 IL2CPP ELF64 AArch64 核對通過。這是 Development 建置，沒有頭盔安裝／執行證據。

新 `check-unity-admission.py` 使用自己的 API／資料／憑證與真正 Windows UDP／NGO server 加 clients，八項入場／撤銷／重連／End 斷言全過。無圖形場 `20261029-195957-8a81f78a` 封存 **369 幀**；實際視窗場 `20261029-200137-a3569013` 封存 **1648 幀**。互動場在原 PID 23396 重新配票後點 Reconnect，再以 Space 射擊、W 前進 **0.65 公尺**；強制結束玩家程序、等真正 transport-left 回呼後重啟同 admission，權威位置仍為 **(25, 1.65, -2.35)**，健康 **60**、彈匣 **29**、備彈 **90** 均相同。統計耗彈 1／中彈 2／傷害 40；pendingTelemetry=false、末幀回放與報表一致、活動場次 0。全部是 Simulation／Simulated rig，沒有注入姿態或戰鬥 RPC。

第一個修正後試跑曾完成封存卻因工具 finally 使用不同 End commandId 得到 409，CLI 失敗，不能算完整通過。已統一 End ID，清理路徑容許失敗回覆並停止所有自有程序；僅清理該隔離 fixture 程序，再以上述兩個全新場重驗成功。正常 Independent／Linked 連線亦回歸通過，目錄分別 `20261029-200542-b9edbf40`／`20261029-200557-c2c87ae6`，各 **113 幀**，最大來源年齡 **0.572172／0.48822 秒**，維持原 1.5 秒門檻。這只是本機該次量測，不能當跨機 LAN 或 25 台 SLA。

完整機器可讀驗證在 `artifacts/reconnect-ui/validation.json`；原始日誌、失敗及截圖保留於忽略的 artifacts。ProjectBuilder 的較窄 Editor SDK 圖亦重新通過 947 來源／13 組件及移除 MetaQuestSupport 的編譯失敗反例，仍不含 URP 專用驗證分支。未變更後端／管理 Web UI，未混算歷史 .NET／Chromium 結果；末端原預覽 5080／PID 52992 仍回 health ok／API 0.16，本輪未換 DLL 或資料。操作見 [RECONNECT.md](RECONNECT.md)，一般練習場見 [DESKTOP.md](DESKTOP.md)。下一步為五場同時獨立與圖形聲光／操作員控制；跨機網路、server 崩潰恢復、Quest／VIVE、MR、硬體及 25 台仍待分別驗收。

功能提交 `94c49fc935ba233c72e72098c2bbb8f675626b22` 已推送，核對遠端 main 相同。GitHub CI run `40873523761`／check `123446386429` 已結束，steps／logs 為空；annotation 明確為近期付款失敗或支出限制，工作尚未啟動，另有 ubuntu-latest 遷移通知。未改帳務或重跑，沒有將雲端未執行稱為通過。GitHub 長期追蹤 #1 保持開發中；本機結果與完整實機目標分開。

## 2026-10-29：可操作電腦練習場、瞄準與真實視窗射擊統計

上一輪 990b946／1b4f3a7 已完成真正 Unity 建置與雙 client 無圖形驗證，屬於具體進展。本輪依使用者「目前沒有頭盔，先繼續電腦端」從乾淨 1b4f3a7 接續，不縮減完整 11 項需求。沒有登入、SDK 重裝或頭盔操作。

新增 scripts/start-desktop-demo.py，直接啟動自己的 API／SQLite／Master 與 GameServer 憑證、無圖形 Unity server、一個可操作視窗及預設一個無圖形同伴。Clear／Day、Hold 且不自動攻擊的練習任務含沙包／油桶；玩家只有短效票券，來源明確 Simulation。關閉玩家視窗、Ctrl+C 或時間結束後送 End，等待雙管道精確封存並比對回放／報表，再停止自有程序。產物與私密設定都留在忽略的 artifacts/desktop-demo，不讀取正式預覽憑證或改動 5080 資料。

桌面 HUD 改為可讀的畫面固定血量／彈藥／房間／phase 與操作提示，保留頭盔的原 world-space HUD。準星依收到的幾何與槍口預測投影，不把預覽當命中確認；伺服器仍處理姿態／射速／傷害。新增上下瞄準、方向鍵、Space 射擊；WASD 依水平視角前進、斜走不加速，按房間而非各出生席位根物件限制邊界，長幀不大幅跳位。掩體碰撞仍由核心拒絕，尚無完整本地移動預測。

實際視窗先證實滑鼠能扣彈，但自動鍵盤未改變畫面；補上短按 wasPressedThisFrame 後仍無效，不能只憑推測稱為修復。新增裝置診斷確認 keyboard／mouse 均存在，再接入視窗 key event 的後備路徑，才取得真正方向鍵／Space／R／W 操作證據。後備輸入在下一次 Update 與 InputSystem 狀態合併，避免同一原始按鍵重複套用；這是系統視窗事件相容，不是測試 RPC、直接寫命中或繞過伺服器。實體鍵盤的所有組合／手感仍待人工量測。

最終 Windows receipt 來源 fingerprint `05d97ef51db1b3f505fc6da89867325dcd8aff5af7f4a9382053fb74f64e5ef8`。在真正 Direct3D 玩家視窗以 computer-use 執行方向鍵轉向、Space 與左鍵射擊：兩次命中造成一個擊殺，再打一發空槍。API 報表為耗彈 **3**、命中 **2**、擊殺 **1**、命中率 **66.67%**，同伴耗彈 0。R 換彈由 27／90 到 **30／87**；W 前進後權威頭部位置由 (25, 1.65, -3) 到 (24.966543, 1.65, -2.9628427)，Up 後 forward.y 約 0.052336。Pause 後 Space 不扣彈，tick 保持 3505。

關閉真正玩家視窗後啟動器完成 **1967 幀**世界封存，pendingTelemetry=false、回放末幀統計與報表一致、活動場次 0。證據在 artifacts/desktop-demo/20261029-183207-5901bf78，實際畫面為 artifacts/desktop-ui/aim-hit.png 與 paused-reloaded.png。這是單機桌面 GPU 畫面與合成頭手操作，不是頭盔、軍事美術定稿、音效聽感、完整觀戰畫面或 25 人量測。

空事件試跑曾因統計 origin=null 被工具誤判來源混用；無戰鬥事件的空報表合法為 null。已改為只允許空計數的 null 或 Simulation，世界 header 仍須 Simulation，不允許 GameServer 混入。空場重驗保存 325 幀、完整封存／回放統計一致／活動 0，證據在 artifacts/desktop-demo/20261029-183610-a85e5ea9。新增四項真正 EditMode 測試驗證俯仰／無翻滾、水平相對移動／斜走速度、長幀及五席房界，總數 **25 項全通過**，Tests 門檻同步為 25。未改後端／管理 Web UI，沒有重跑或混算上一輪 .NET／Chromium 數字。

最終 Quest Development APK 亦成功，來源 fingerprint／scene／prefab 識別與上述 Windows 一致，沒有另建場景。APK 67,977,028 bytes、SHA-256 `f78b2ace8765109d39860d49754c501c4f12b3b7b6052222dbd348ff87a3d055`，v2 簽章、com.vrcommand.quest、minSdk 32／targetSdk 35、六份 ARM64 native library 與 IL2CPP ELF64 AArch64 核對通過。這不是頭盔執行證據。完整機器可讀驗證在 artifacts/desktop-ui/validation.json。

與 Android 建置並行的第一個連線回歸因快照來源年齡 6.263257 秒超過原 1.5 秒門檻而失敗，保留 artifacts/unity-pc-input-independent-smoke.log；沒有放寬門檻或宣稱該次封存成功。建置終止後，以新隔離場重驗 Independent：108 幀、tick 167、最大取樣年齡 0.405851 秒；Linked：112 幀、tick 171、0.39335 秒。兩者雙 client、AI 傷害、Pause、精確封存與回放統計均通過，證據目錄分別 20261029-184230-c46bf89a／20261029-184314-3cf58642。這證明本機該次條件；編譯並行或其他負載的延遲不達標仍需場館效能驗收，不能稱為所有負載的 SLA。

末端 health 檢查發現原 5080 無 listener、舊 PID 17748 已不存在；本輪自己的 API 都使用隨機埠且已停止，未宣稱原預覽一直健康。先將 root data 與 src/VrCommand.Api/data 的 21 檔備份並逐檔核對 SHA-256，再用原 build-v016 API DLL、原憑證與明確原 missions／sessions 路徑恢復，沒有重建空資料庫或升級後端。新自有 PID 52992／0.16.0／health ok，三個 SQLite 邏輯內容雜湊與重啟前完全相同，9 場歷史、10 任務版本／9 heads、4 world recording、活動 0。證據在 artifacts/pc-preview-restart-backup.json／pc-preview-restart-verified.json。

功能提交 b080a39 已推送並核對遠端 main 相同。CI run 40860603854／check 123402555735 在任何 step 開始前即結束，steps／logs 為空；annotation 仍明確為近期付款失敗或支出限制，另有 ubuntu-latest 遷移通知。未修改帳務或重跑受限工作，本機實際驗證與雲端未執行分開記錄。

交付前另外實測不帶 --api-dll 的預設命令，發現一般 Release 目錄仍是舊 API，雖能 health 卻無法發布目前世界。新增建立場次前的 API 0.16.0 檢查；舊 DLL 的反例立即拒絕（desktop-demo-stale-api-rejection.log），不以檔案存在當同版。鎖定還原與一般 Release 建置完成、0 警告／0 錯誤後，以預設 API 再成功啟動並收尾（artifacts/desktop-demo/20261029-185350-7c435723）；DESKTOP 已列出完整建置／啟動命令。原預覽仍使用自己的 build-v016 DLL 與原資料，沒有為更新一般輸出停止預覽。這次只更新啟動器及文件，不需重新建置相同 Unity 來源。

操作見 DESKTOP。原始完整目標仍開發中；接續 PC 重連／撤銷、五場同時隔離、圖形聲光與操作員控制驗收，取得設備後再做 Quest／VIVE、MR、硬體與 25 人。當前可繼續 PC 工作，沒有因缺頭盔或 CI 帳務限制宣告整個目標 blocked。

## 2026-10-29：真正 Unity 建置、穩定跨平台識別與電腦雙玩家驗證

使用者確認 Hub 有效授權後，真正 Editor 6000.3.27f1 已成功解析 UPM、編譯／ILPP、匯入音訊／Shader、Prepare、執行 **21 項 EditMode 全數通過**，並完成 Windows 播放器與 ARM64／IL2CPP Quest APK。這是目前狀態；下方舊 CLI session／Prepare 198 僅為歷史。使用者目前沒有頭盔，明確指定先繼續電腦端；完整 11 項與 VIVE／Quest 相容目標仍開發中。

真正匯入揭露並修正 Editor asmdef 缺少直接 MetaQuestSupport 引用、不存在的 textrendering module，以及 TestAssemblies 重複 TestRunner 引用。新增可離線的真正 Editor SDK 診斷工具及移除引用的 CS0234 反例；其較窄範圍見 UNITY_SDK_CHECK，不代替此輪真正 Editor 結果。保存實際 packages-lock.json、URP 升級結果、生成資產與全部 meta／OpenXR 設定。UPM 實際選用 Transport 2.7.4、Collections 2.7.1、Burst 1.8.31 等，與較早診斷圖分開記錄。

原 Prepare 每次重建場景會改變本地 file ID，不能將 Desktop／Quest 各生成一個世界。現在重用保存的 Arena／PlayerAvatar，驗證並持久保存非零 NGO hash；明確 RebuildArena 後須重建所有平台。新增三項實際資產整合測試，涵蓋重複 Prepare 識別、scene／prefab／音訊引用及 Android XR 設定。建置腳本最低 21 Tests，成功／失敗明確 exit 0／1；失敗反例已確認。增量建置的啟動 exe 可能維持舊時間，改以真正成功 BuildReport 後產生的新 receipt 驗證此次輸出。

最終 Desktop／Quest receipt 的來源 fingerprint 同為 `563c2b38ff5c0b079b0b5bfbf0e72db72348f5046494f02d8c27fa3a866c616b`，scene GlobalObjectId 尾端 `1444571642-0`、prefab 尾端 `5227825248646244841-0` 相同。Quest 最終完成 UTC 2026-10-29T03:46:02Z，APK 67,969,388 bytes，application-id com.vrcommand.quest、minSdk 32／targetSdk 35、簽章 v2 驗證成功；ARM64 與檔案雜湊詳見 artifacts/native-build-validation.json。Windows 完整播放器在 artifacts/desktop，不能只複製啟動 exe。兩者為 Development 建置，不是發行包或頭盔驗收。

新增 scripts/smoke-unity-player.py，建立自己的隔離 API／SQLite／短效玩家票券與憑證，啟動真正 Windows Unity server 加兩個真正 desktop client，使用 UDP／NGO。獨立房間 5 與五房 Linked（客戶端分別在房間 1／5）均驗證入場、兩份 Simulated rig、Running、敵軍確認傷害、Pause tick 凍結、End 戰鬥／世界精確封存及回放末幀統計一致；最終活動場次 0。全部使用 Simulation，沒有頭盔或正式服務資料寫入。

首次原生觀戰雖可封存，卻觀察約 12 秒排隊。WorldPublisher 網路 await 改為不捕捉 Unity 同步內容，成功送幀後移除額外固定 50 ms 等候，保留單份 outstanding、戰鬥依賴及 durable ack／seal。修正後獨立 smoke 保存 116 幀、暫停 tick 167、最大取樣來源年齡 0.46213 秒、AI 確認傷害合計 40；Linked 保存 115 幀、暫停 tick 172、最大取樣年齡 0.424355 秒、傷害 100。證據分別為 artifacts/unity-player-smoke/20261029-113725-8744e1bd 與 20261029-113913-7fc522c5。這是本機三個 Unity 程序的無圖形 smoke，不是所有網路條件的延遲分布、鍵鼠射擊、GPU、聲音聽感或 25 人證據。

共用發布器變更後，鎖定還原／隔離 Release 建置 0 警告／0 錯誤，重新通過 **472 核心、369 HTTP、43 世界串流**；Unity **21 項 EditMode** 實際執行通過。UI 未改，本輪沒有重跑先前 17 Node／122 Chromium，不將舊 1023 項混算為此次新結果。完整規範與限制見 NATIVE_VALIDATION。正式預覽 5080 未停止、未更換 DLL 或資料庫。ADB 最近為 0 裝置，使用者已明確無頭盔，不再要求立即連接。

下一步繼續電腦端的可操作畫面、鍵鼠射擊、重入／撤銷與斷線驗證；之後取得設備再做 Quest 控制器／追蹤、聲光／圖形、MR、VIVE／廠商硬體與 25 台效能。完整長期目標不以此輪建置成功結案。

功能提交 990b946 已推送並核對遠端 main 相同。CI run 40814450437／check 123252141894 已結束，steps／logs 為空；annotation 明確為近期付款失敗或支出限制，工作未啟動，另有 ubuntu-latest 遷移通知。本機與雲端結果分開記錄，未修改帳務或重跑受限工作。預覽 health 仍 ok。

## 2026-10-29：擴大 Quest managed SDK 綁定與 URP 版本對齊

上一輪 v0.16 已推送、部署並完成資料保留／模擬聲光驗證，屬於具體進展；本輪從乾淨 e6b6d86 接續，完整目標與 Quest 3 優先保持。最新真正 Prepare 仍是上一輪授權退出 198；本輪沒有新授權可用的證據，也沒有重複啟動相同失敗工作、重裝工具或操作登入／安全性提示。

新增 scripts/check-unity-sdk.py，將原本僅語法／單一天氣元件的檢查擴為 10 runtime／5 NUnit 檔案的實際 managed API 型別編譯。官方 NGO 2.7.0、Input 1.17.0、Transport 2.6.0、Burst 1.8.24、Collections 2.4.3、Math 1.3.2，綁定本機真正 Editor Core／Audio／UI／XR 等 DLL 與隨附 UI／NUnit。每個 Android／Windows 分支編譯 976 份 managed 來源（含上游），另引用共用 Simulation；沒有自製 stub，不修改上游來源。

本機實際 Unity.exe ProductVersion 為 6000.3.27f1_672d562a42a7，BuiltInPackages 的 URP／SRP Core 為 17.3.0，而 manifest 還指定 17.0.4，已對齊 17.3.0；Core 的 Collections 相依為 2.4.3。這是檔案／版本設定證據，不是 UPM 解析成功；原 17.1 範本資產及授權仍保留，匯入／升級待真正 Editor 驗證。API／bundle 0.16／NGO wire 16 不變，沒有替換預覽 DLL 或操作資料。

六份官方 registry archive 下載時核對固定 SHA-1，來源 receipt 另記各檔 SHA-256，快取改動／遺失／新增來源會拒絕。首五份從本輪已驗證的探索快取保留原文初始化正式快取，Collections 2.4.3 由正式工具下載驗證；原 2.2.1 探索資料保留在 artifacts。產物與報告在 artifacts/unity-sdk-check，僅編譯所需來源／支援 DLL／授權文件保留於正式快取，第三方內容不提交。報告開始即設 complete=false，成功記時間、檢查器與來源／DLL 雜湊、符號及退出碼，避免舊成功冒充新嘗試。

Android／Windows 與最終 --offline 重跑均通過，零錯誤；完整重建分別 18／19 警告（上游未使用欄位／隱藏成員、本工程 JsonUtility DTO 反射填入欄位的 CS0649），沒有宣稱零警告。18 項 NUnit 方法只完成型別編譯，沒有執行。另以自己的暫存 fixture 確認舊 URP pin 在編譯前拒絕；刻意修改自己的 Mathematics 快取來源後拒絕，finally 恢復原文及 receipt 核對成功，再實際離線編譯兩分支。證據為 artifacts/unity-sdk-guards.log、unity-sdk-offline.log 與 unity-sdk-check/report.json。

探索工具首次漏列舊 Unity 版本符號、誤納 Unity 忽略的 bee~ 來源，以及將隨附 ILSupport DLL 誤當空白 C# 專案，已依官方來源／README 改正工具選檔與引用，沒有修改上游程式來讓它通過。正式工具使用對齊 Core 的 Collections 2.4.3 及兩個明確條件分支，通過的是 managed 綁定；沒有模擬完整 Unity CompilationPipeline／UPM。ProjectBuilder／OpenXR／URP 渲染程式、NGO／Burst／Collections ILPP、原生執行、Shader／音訊匯入、EditMode／Desktop／IL2CPP／APK／頭盔均仍待驗收，診斷 DLL 不可部署。

文件已同步至 UNITY_SDK_CHECK、QUEST3、README、ROADMAP、REQUIREMENTS 與 AGENTS。管理服務 5080 當下 PID 17748、API 0.16.0／health 正常；沒有停止、換資料庫或新建場次。本輪未變更業務／UI，因此沒有重跑 v0.16 的 1023 項管理／模擬／瀏覽器檢查，該結果仍只是上一輪證據。下一主線仍為有效 Editor 授權、真正 Prepare／18 Tests／Desktop／Quest 及雙 Quest 實測；本輪可重複的完整 runtime 型別證據不能替代它們。CI 按推送實際結果另記，長期目標保持開發中。

fc44414 已推送，遠端 main 核對相同。CI run 40792806909／check 123181895880 已終止且 steps／logs 為空，annotation 再次明確為近期付款失敗或支出限制，工作未啟動；另有 ubuntu-latest 遷移 notice。沒有雲端通過證據，未修改帳務或重跑受限工作；本機 SDK 檢查結果與範圍如上。

## 2026-10-29：v0.16 天氣聲光、共用時間規則與舊錄製相容

從乾淨 a3e2dee 接續完整長期目標，Quest 3 仍優先。本輪再次實際執行 Prepare，退出 198，日誌為「No valid Unity Editor license found」，沒有待執行中的建置；未操作登入／安全性提示、重裝已整理的 SDK 或重問已同意的條款。CLI 登入狀態不能單獨否定 Hub 授權，這裡以實際 Editor 結果為準。整個 Unity／NGO／ILPP／Shader／AudioImporter／18 項 EditMode／桌面程式／APK／頭盔均沒有成功證據。

需求 5 新增共用 EnvironmentPresentation（C# 9／.NET Standard 2.1）：依權威 tick 決定雨、霧、日夜、閃電與延遲雷聲，不用本機時間推進戰鬥。每房 64／128 雨線，最多 640 根、1280 頂點單網格；聲音兩個可重用音源，都是顯示效果，不改命中／碰撞／尋路。首次觀察、倒退、長缺口及設定變更不補播錯過的雷聲，暫停／過期停止聲光活動。Unity 已接原子 WeatherState 與網格／AudioSource，生成器 NGO protocol／Android code 16、bundle 0.16.0，所有遊戲端需同版重建。

新增 check-weather-unity-api.ps1，以本機真正 Unity 6000.3.27f1 的 CoreModule／AudioModule DLL 編譯單一 UnityWeatherView 與共用核心，0 警告／0 錯誤；不是 stub，但不涵蓋 SceneAuthority／NGO 或整個 Unity 工程。26 份 C# 9 語法檢查通過。新增三項未執行 EditMode，總數 18；沒有以部分 SDK 編譯替代實際 Editor 結果。

世界 header 新增選用 environmentVersion，新來源預設 1、舊缺欄位保持 0，拒絕未知版本與改既有版本。舊資料庫 header 原文與 binary JSON／checksum 不改寫，WorldOutbox 用 codec 正規化後比對。新 NDJSON 也附擷取 UTC，舊來源仍保持原本未知／有時間狀態。worlds.db schema 1、session envelope 6 不變，但嚴格舊 reader 不接受新欄位，需 API／UI／來源協同升級且不可直接降版。schema 2 本機模擬回放沒有完整環境欄位，仍用既有顯示。

瀏覽器觀戰／持久回放以同一時間規則重建雨、霧、日夜與閃電；按音效開關後才建立／恢復 Web Audio。兩份原創合成 PCM 由固定整數 DSP 生成，各 4 秒 mono／22050 Hz／16-bit，provenance 記 SHA-256，API 直接打包 Unity 同一份來源。重現不是原始音軌或影片，沒有聽感／聲壓或 MR 驗收；legacy 保留原光霧且音效關閉。規範、操作與可重現旗標 --environment-demo true 見 ENVIRONMENT。

鎖定還原與 Release 建置通過，0 警告／0 錯誤；**472 核心、369 HTTP、43 世界串流、17 Node、122 Chromium，共 1023 項通過**。涵蓋 144 組 C#／JS 樣式、60 組雨座標、85 組雷聲步驟向量、舊 header／journal 恢復、版本拒絕、實際 Web Audio 非零輸出／延遲 cue、回放閃電、跳轉不補播、暫停與 legacy 顯示。世界測試首輪 43 項通過後，新增 fixture 的 Python sqlite connection 尚未關閉導致 Windows 清理失敗；已顯式 close，重跑整個世界測試退出 0。語法檢查首次誤用 Windows PowerShell 不支援 utf8NoBOM，改以環境的 PowerShell 7 執行後通過；腳本原本無需修改。已檢視 world-environment-rain-night.png，仍是基本幾何、合成頭手及軟體 WebGL，沒有頭盔證據。

預覽確認活動 0／自有 PID 25348 後停止，root data 及實際 src/VrCommand.Api/data 完整備份至 artifacts/backups/pre-v016-20261029-075351，共 21 檔雜湊一致，pointer 為 artifacts/pre-v016-backup-path.txt。隔離 v0.16 DLL 明確指定資料目錄啟動，新 exec 29871。原 8 場歷史、9 任務版本／8 heads、3 world metadata 與主控鏡頭位置保留；metadata 僅在回應增加 legacy environmentVersion 0，另以備份 DB 比對確認原始 header 完全沒改寫。

真實舊 v0.13 binary 來源 clocked-20261029-052526.worldlog 由 v0.16 工具恢復，64 幀 ack／complete 保持、整檔雜湊不變，API metadata 亦不變。另在自己的空房 5 新建 Simulation 夜間雷雨 d23778f9-1834-4afe-a50e-52a2760690b4，共 244 幀、environmentVersion 1、含 UTC 及 tick 140／180，完整封存後活動 0。所有原資料與鏡頭逐欄保留，兩份實際預覽 WAV 與 canonical bytes 一致；來源及摘要在 artifacts/v016-live-demo.json 與 artifacts/world-source-demo/weather-20261029-075426.worldlog。這不是 Quest 遊戲運行。

後續先完成有效 Editor 授權與真正 Prepare／18 Tests／Desktop／Quest、雙 Quest 互見／頭手／撤銷／排空及聲光同步；再推進正式美術、MR、廠商硬體、VIVE 相容及 25 台效能。完整 11 項保持開發中，CI 按本輪推送實際結果另記，不改帳務或重跑已知受限工作。

功能提交 6df4d3a 已推送並確認遠端 main 相同。CI run 40790759521／check 123175098637 已結束，沒有 steps 或 logs；annotation 明確為近期付款失敗或支出限制，工作未啟動。ubuntu-latest 遷移通知不是測試失敗。本機 1023 項結果保持有效，雲端尚未通過；未修改帳務或重跑受限工作。

## 2026-10-29：v0.15 不可變任務修訂、歷史與新舊版開場

上一輪 v0.14.1 已推送及部署鏡頭位置，屬於具體進展。本輪從乾淨的 9639a32 接續，CLI 仍 loggedIn=false、active=false／licenses 空，未找到新的常見授權檔；沒有重跑同一個 Prepare 或重啟舊回呼。最近 Editor 結果仍為 198，Hub 登入／有效授權待本機確認。沒有新的 Unity／15 項 EditMode／桌面程式／APK／頭盔結果，也沒有操作登入、安全提示或重裝 SDK。Quest 3 主線優先及原始完整 11 項範圍保持。

需求 8 新增 Persistence.SqliteMissionLibrary：DataDirectory/missions.db，WAL／FULL／獨占 writer lease，完整 schema 1 Mission、series／number／previous、服務端作者及 request 同交易。根版本為 series 自身，修訂只從當前 head 新增不可變 ID，並行舊 base 只有一個可成功。新任務的 key 選用以相容舊工具，修訂 key 必須提供；UI 兩者固定提供。相同請求綁作者／kind／parent／全部定義，之後 head 前進仍回原接受版本。任務本體、場次 envelope 6、世界 schema 1 及 NGO protocol 14 不變，既有場次不跟著任務庫更新。

首次啟動把原 GUID.json 在同一交易匯入各自第 1 版，保留原檔 bytes；壞資料／不一致鏈失敗即回滾，後續只讀 catalog。目前 Core 的舊 JSON helper 讀寫已版本化目錄會拒絕，不混跑不同版 API。ReadMission 明確驗證已認證身分，共用範本對配置角色可讀，AuthorMission 限 Master／受信任 in-process Internal；所有 HTTP 路由傳入 Actor，不用隱含 Internal。history 只取有界 metadata（預設 20／最多 100），選取才讀完整定義，主控台輪詢 /mission-library 的各系列 head，舊 /missions 保留全部快照契約。

UI 新增保存下一版、歷史分頁／讀回及「選用草稿原版開場」。背景更新保留草稿、已知 head 不倒退、開場版本不偷偷跳到最新版；已知舊草稿不得修訂，409 保留內容供載入新版本或另存新任務。網路、逾時及 5xx 保留完整原請求；保存已接受但後續資料讀回失敗仍保留重試，不再重複建立新任務。登出清理草稿／版本／配置並阻擋晚回應。手機保存列移除多餘的固定高度空白，已檢視 mission-versions-desktop.png 與 mission-versions-mobile.png。

鎖定還原、Release 0 警告／0 錯誤；**451 核心、369 HTTP、39 世界串流、12 回放資料、108 Chromium，共 979 項通過**。驗證含匯入原檔不變、失敗回滾與修復重試、writer lease、非法身分、線性並行、保存 key 衝突／跨作者拒絕、游標分頁、重啟後請求／head／舊場次保持、新舊版實際 API 開場、主控回應遺失後 head 前進、保存後讀回 503、舊 catalog 晚到不倒退與登出競態。本輪未改 Unity／共享 Runtime，這些是管理／Simulation／軟體 WebGL 證據，不代表 Unity 場景還原或頭盔測試。

升級前空陣列檢查因直接 @(Invoke-RestMethod) 的包裝誤判，檢查退出後仍錯誤啟動新版，被既有 events writer lease 拒絕；原服務與資料未動，也未建立 missions.db。已改為先賦值再檢查並分步驗證成功後才啟動相依操作。真正確認活動 0／自有程序後停止，root data 及 src/VrCommand.Api/data 完整備份至 artifacts/backups/pre-v015-20261028-231232，17 檔雜湊一致，pointer 為 artifacts/pre-v015-backup-path.txt。新 exec 49439 為 0.15.0，原 8 任務／8 場歷史／3 份 world metadata／主控鏡頭位置逐欄一致，任務皆匯入第 1 版。前置快照的鏡頭陣列亦有額外包裝，僅比對時解包，原 artifact 留存，證據為 artifacts/v015-migration-check.json。

於自己既有 clocked Simulation 任務 f71fb223-dcc0-4a4a-8166-35b06ec47379 建立第 2 版 913a28f2-9826-4c8e-a8e0-34fc76c1bdd2「Quest 3・夜霧巡邏（開發示範）」，保存 1800 秒、Fog／Night、2 名 Patrol 敵軍；同 key 再送回同一版本。原 v1 及歷史場次 e382ddcc-733b-440a-ab6a-395f5aa37a35 完全不變，活動仍 0。主控可直接在任務編輯器查閱新舊版；沒有把此任務保存宣稱為遊戲運行。摘要在忽略的 artifacts/v015-live-mission.json。

完整契約與備份／不可直接降版見 MISSION_VERSIONS，已更新相關需求、路線、API 與儲存文件。接續仍先取得有效 Unity 授權及實際 Prepare／Tests／Desktop／Quest、雙 Quest 頭手／重連／撤銷／排空，再做正式軍事素材、硬體、MR、VIVE 及 25 台效能。CI 依推送結果另記，不改帳務或重跑已知受限工作；長期目標保持開發中。

3430a67 已推送；功能 CI run 40786700224／check 123161576652 已終止且 steps 空，失敗 annotation 為付款／支出限制，工作未啟動。另有 ubuntu-latest 遷移 notice，不是本輪測試失敗。本機 979 項結果有效，未宣稱雲端通過，未更改帳務或重跑受限工作。

## 2026-10-29：v0.14.1 觀戰鏡頭位置持久保存與重試

上一輪已安裝、驗證並啟動 Hub，屬於實際工具鏈進展。本輪從乾淨的 28cdac3 接續；CLI 仍無登入／授權，但不單獨據此否定 Hub。Hub 及 Licensing Client 已在執行，實際 Prepare 再驗仍因「No valid Unity Editor license」退出 198，已結束。沒有新登入／安全性操作、重裝 SDK 或重問已同意條款；Unity／15 項 EditMode／桌面程式／APK／頭盔仍未通過，Quest 3 主線保持優先。

需求 10 的觀戰新增命名保存、切換、移除與重新讀取鏡頭位置，保存世界目標、theta／phi／radius；跟隨時只保存當下固定位置。位置存在同一 worlds.db 的新增 camera_bookmarks 表，按完整 OperatorIdentity 及場次隔離，只有 Master／RoomController 可用，每次重查可讀房間及錄製。每身分／場次最多 24 個有效位置，名稱／座標／角度／距離有界，不寫瀏覽器儲存或影響玩家名額、世界幀、統計、錄製 updatedAtUtc。

PUT 以客戶端新 GUID 保存不可變內容，相同內容重試回原建立時間，不同內容 409；DELETE 留 tombstone，可原樣確認。已接受後被其他視窗移除的舊 PUT 回 Deleted，不重新建立位置。UI 保存／移除遇網路中斷、10 秒逾時或 5xx 保留原 ID／名稱／視角，凍結新寫入及換場，提供重試；登出清理，epoch 阻擋晚回應進入另一身分。修正全部房間取景把 'all' 轉為 NaN；窄視窗全館所需較大距離可保存，縮放／保存範圍一致為 2–240 m。共享 Runtime、envelope 6、world schema 1 及 NGO protocol 14 不變，API／UI 版本為 0.14.1。

鎖定還原與 Release 建置 0 警告／0 錯誤；**420 核心、322 原 HTTP、39 世界串流、12 回放資料、90 Chromium，共 883 項通過**。覆蓋 SQLite 重啟、完整身分隔離／房間及角色拒絕、配額、非法視角、保存／移除遺失回應、舊保存晚到不復活、任意平移旋轉還原、新登入讀回、登出後舊保存回應不污染另一控制台。已檢視 world-camera-positions.png 及 world-replay-mobile.png，桌面／手機鏡頭介面可操作。本輪未改 Unity 來源；這些結果是 Simulation／軟體 WebGL，不能代替 Unity、真實 GPU 或頭盔驗收。

確認預覽活動場次 0 及自有程序後停止，完整備份 root data 與實際 src/VrCommand.Api/data（含 WAL／keys）；16 份 API data 檔逐檔雜湊相符。路徑為 artifacts/backups/pre-v0141-20261028-223839，pointer 為 artifacts/pre-v0141-backup-path.txt。隔離 DLL 以明確 DataDirectory／SessionDataDirectory 啟動，新 exec 16894 服務 0.14.1；原 8 份歷史場次與 3 份 world metadata 逐欄完全一致，活動仍 0。於自己既有 clocked Simulation e382ddcc-733b-440a-ab6a-395f5aa37a35 保存「房間5・開發示範全景」鏡頭，ID 45f90259-b86c-4053-a146-3cbf3b9fcbd6，主控可直接選取回放及切換。來源／升級摘要在忽略的 artifacts/v0141-*。

接續仍先完成本機 Hub 有效授權及真正 Prepare／Tests／Desktop／Quest、雙 Quest 頭手／重連／撤銷／排空；再推進正式軍事素材、任務版本、硬體協議、MR、VIVE 及 25 台效能。完整 11 項驗收範圍維持，長期目標開發中。本輪 CI 以推送實際結果另記，不改帳務或重跑受限工作。

a8cc007 已推送；功能 CI run 40782250833／check 123146580012 已終止、steps 空。失敗 annotation 明確為近期付款失敗或支出限制，工作沒有啟動；另有 ubuntu-latest 映像遷移通知，不能把它當成本次測試失敗原因。本機 883 項結果有效，未宣稱雲端通過、未修改帳務或重跑受限工作。

## 2026-10-29：Unity Hub 安裝與授權診斷

從乾淨的 19aacf9 接續，先核對 M2 建置阻礙，未擴增遊戲來源或宣稱新功能版本。CLI 仍未登入，license list 空，license status 為 active=false／signedIn=false；先前 Prepare 的 198 結果不變，本輪沒有重跑相同失敗建置。Appx、解除安裝登錄及常見安裝目錄原先未找到 Hub，只有 CLI；也未找到常見位置的本機授權檔。這些診斷不能取代實際 Editor 授權／建置結果。

已從 Windows 套件來源取得 Unity 官方 CDN 的 Hub 3.22.5 x64 MSIX（260081856 bytes），SHA-256 與來源提供值相符，Authenticode Valid／Unity Technologies SF。以 Add-AppxPackage 安裝，註冊版本 3.22.5.65535／Status 0，主程序 49404 及 Unity Hub 3.22.5 視窗均已實際確認。Windows 管理的套件位於 C 槽；工程、6000.3.27f1 Editor、Android 工具與安裝包仍在 F 槽。未重裝 Editor／SDK，原生工具的既有成功結果維持。

Computer Use 觀察到 Windows 安全性對 adb.exe 網路存取提示遮住 Hub；未操作提示、變更防火牆或代填帳戶。已請使用者自行處理提示、在 Hub 登入並到 Settings → Licenses 確認有效授權；若需新增，由使用者選擇適用方案及確認條款。不要求提供密碼／token／序號，也沒有選擇 Personal 資格或購買授權。

QUEST3、ROADMAP 與 AGENTS 已記錄新狀態，避免後續誤稱 Hub 尚未安裝或重啟過期登入回呼。官方 CLI beta.14 支援帳戶啟用；Hub 授權也可能獨立於 CLI 工作階段，後續以實際 Prepare／Tests／Desktop／Quest 為準。授權確認仍待使用者操作；沒有新的 Unity 編譯、EditMode、桌面程式、APK 或頭盔證據。既有 v0.14 的 843 項本機檢查未在本輪重跑；本輪只改文件，未變更後端／遊戲／預覽資料。長期目標保持開發中，完整 11 項驗收範圍不變。

## 2026-10-29：v0.14 每次入場識別、票券 v2 與撤銷接入

上一輪 v0.13 已推送、部署並完成具體驗證。本輪以乾淨的 27242b2 接續原目標，CLI 仍 loggedIn false／license list 空；新的 Prepare 實際退出 198，命令已結束，沒有等待中的 Unity 工作。SDK 條款無須重問，沒有重裝或代填登入。長期目標保持開發中。

新增 Player.admissionId，以原始 PlayerJoined.EventId 為本次入場識別；新 schema 6 payload 明確保存，舊 1–5 從原 EventId 穩定推導，不改寫歷史。相同玩家／房間／席位重新加入仍取得新識別；相同加入 requestId 只確認歷史。PlayerLeft 保存實際 admission 與原始 expectedAdmissionId；同 requestId 改 fence 回 409。DB schema 仍 1，但新 envelope 不能降回舊 reader。

票券改 v2，HMAC 簽 session／player／admission／room／seat／expiry／nonce，仍五分鐘且頭盔只拿四欄連線檔。舊 v1 即使原簽章／期限有效也拒絕。配票及新的 HTTP 玩家移除必須 If-Match-Admission，缺／壞 header 400、入場變更 409；已接受的舊移除只確認，不影響後來入場者，未接受的舊 fence 不可移除新成員。舊版已接受且無 fence 的 requestId 仍可確認。

GameServer 驗票需 protocolVersion:2，驗簽後原子比對當前 admission／room／seat／state，回 throughSequence 及 expiry。ArenaSession.Connect 必帶 admission，Preparing 輪詢即使跳過離場／同 ID 重入也能撤銷舊 binding，舊姿態／武器不影響新身體。Running 不得換 epoch／重生。Preparing 重新入場變更名稱的世界統計 metadata 亦對齊最終 ledger，避免封存名稱不一致。

Unity 來源碼加入驗後取得至少 throughSequence 的快照、expiry／epoch 比對、即時清除內部過時 binding、遠端斷線／Host 關閉，以及合併串行管理 fetch，避免多個 approval 回應造成快照倒退。approval buffer 20 秒；既有連線撤銷仍依管理觀察，正常目標 0.5 秒，管理過期 1.5 秒暫停，未承諾實機零延遲。生成器 bundle／Android／NGO protocol 14。新增三項待執行 EditMode，總數 15；JSON 舊管理範例補 admission，不以忽略 epoch 作相容解法。

鎖定還原／Release 0 警告／0 錯誤，**399 核心、322 HTTP、32 世界串流、12 回放資料、78 Chromium，共 843 項通過**。23 份 C# 9 語法通過；同源 Runtime 仍真正建置 .NET Standard 2.1，沒有 Unity SDK 編譯。驗證含 SQLite 後撤銷保持、同 ID／同席位重入、簽章正確的舊 v1 拒絕、過時／空 fence、原始重試內容、舊 schema 派生與無 fence 歷史確認、跨輪詢撤銷、世界 metadata／封存一致；瀏覽器讓移除先接受但丟回應，再由其他操作員重入，原 fence 重試保持新玩家。15 項 EditMode 未執行，沒有 APK 或頭盔證據。

本機 5080 先確認自有程序且活動場次 0，停止後完整備份至 artifacts/backups/pre-v014-*，再升級 API／控制台；新 exec 59527 服務 0.14.0。原七場在 player 新增可推導 admissionId 後逐欄一致，三份 world metadata 完全不變。另以自己的空房 5 新建純 API 驗證場次 deb56282-e99c-49a7-abf4-dcd6c1134272：同 ID／席位取得不同 admission、舊票券拒絕、舊 leave retry 無害、新券有效，驗後 End 釋放房間；目前活動 0。沒有把此 API 驗證稱為遊戲或實機，摘要在忽略的 artifacts/v014-live-admission.json。

規範與升級見 ADMISSION.md。下一步仍先取得工具可讀授權，實際 Prepare／15 Tests／Desktop／Quest，驗雙 Quest 的重連／撤銷／追蹤與排空，再推進 5／25 台、硬體、MR、VIVE、任務版本與書籤等未完成項目。完整 11 項及雙平台範圍保留；CI 依本輪推送另記，不改帳務或盲目重跑受限工作。

5e77123 已推送；雲端 run 40778846449／check 123135061355 steps 為空，annotation 指出付款／支出限制，工作未啟動。只有本機 843 項通過，沒有本輪雲端成功證據；未修改帳務或盲目重跑。

## 2026-10-29：v0.13 共用世界來源、Unity 頭手接入與擷取時間

上一輪 v0.12 已推送並部署，屬於實際進展。本輪依目前乾淨的 418decb 接續，CLI auth 仍 loggedIn false／license list 空。完成來源接入後實際 Prepare 再次退出 198，log 為 No valid Unity Editor license；該 exec 32393 已結束，沒有仍在等待的安裝或建置，也沒有 Unity／APK／頭盔通過證據。長期目標持續開發。

新增共用 WorldOutbox／WorldPublisher／WorldWebSocket，真正建置 C# 9／.NET Standard 2.1，Unity 與 Native 工具只替換 JSON codec。來源 binary journal 以 VRWORLD1／length／SHA-256、獨占 lease 及 Flush(true) 保存 header／幀／ack／completion／seal，逐筆重開且只保留最後／待送幀。失敗 ack 不推進 cursor；丟回應／封存重試維持同一內容，壞尾端不自動截斷。發布等待 combat durable ack，世界封存另等 combat sealed；來源補送仍不是世界運算恢復。

Unity 來源新增接受後的世界頭／左右手及旋轉、None／Simulated／Tracked 宣告、追蹤中斷停送、10 Hz 世界錄製、管理前後邊界、suspended Pause、Ended completion 與非同步排空／取消生命週期。頭與雙控制器需同時 isTracked，trackingState 含 Position／Rotation。右手 aim、左手 device pose，尚無手指骨架。Tracked 是客戶端宣告經位置／格式驗證後保留，不能當作裝置認證。AvatarPose 新 source byte 由生成器 NGO ProtocolVersion 13 區隔；bundle 0.13／Android code 13。

Native WorldRelay 新 --world-journal 走相同 Runtime 發布器與校驗來源；--combat-journal 可對應 Unity 原始 journal，恢復前核對 session／stream／origin。原 --recording NDJSON 保留。新增實際來源重開、獨占、掉 ack、掉 seal、磁碟 receipt／completion 失敗、世界對統計依賴、並行發送拒絕與 damaged-tail 測試。Unity 新增五個待執行 EditMode 測試，總數 12；腳本不能再以舊七個結果宣稱通過。

另修正補送新鮮度：header 保存不可重設的 UTC 擷取基準，elapsed 保留來源單調時間，API capturedAtUtc 對照擷取時間，updatedAtUtc 仍為接收時間。觀戰以正在顯示幀的擷取時間判斷，持續收到舊幀仍標過期，無時間標未知、超前時鐘標未同步。v0.12 舊 header 補空值可讀／去重；SQLite schema 1／session envelope 5 未變，但舊嚴格 reader 不接受新欄位，不能把 v0.13 來源配舊 API 或直接降版。

鎖定還原及 Release 建置 0 警告／0 錯誤，**363 核心、302 原 HTTP、32 真實世界串流、12 回放資料、76 Chromium 通過，共 785 項**。22 份 C# 9 語法通過；12 項 Unity EditMode 僅有來源，沒有結果。真實 WebSocket／SQLite／SSE／瀏覽器皆使用共用 Native 發布器驗證，仍不等同 Unity SDK／ILPP／IL2CPP、頭盔或 25 台效能。已檢視 world-old-capture.png，確認有新資料抵達但擷取時間老舊仍顯示過期。

現有 5080 自有預覽先確認活動場次 0，停止後備份完整 API data 至 artifacts/backups/pre-v013-*，再升級前後端，新 exec session 17719 版本 0.13.0。原六份歷史完全一致、兩份 world metadata 僅新增預設 captureStartedAtUtc 空值／capturedAtUtc null。實際重送舊 v0.12 NDJSON 64 幀後 metadata 不變，驗證舊 header 缺欄位的相容性。另新增自己的房 5 clocked Simulation：e382ddcc-733b-440a-ab6a-395f5aa37a35，64 幀 complete、UTC 擷取時間保存、彈藥 2／擊殺 1／血量 80；另一程序恢復 ack 64 後不變，舊六場均保持一致，活動場次仍 0。前面另一次未升級預覽的 shared-source 示範也保留，所有示範均無頭盔。

本輪 ADB 實際讀取 ready 0／unauthorized 0，只表示當下沒有可用 ADB 裝置，未宣稱有頭盔實測。來源／驗證摘要在忽略的 artifacts/world-source-demo 與 artifacts/v013-live-demo.json。接入與補送見 WORLD_SOURCE.md。下一步仍需工具可讀的 Unity 授權及真正 Prepare／12 Tests／Desktop／Quest，驗兩位 Quest 的頭手／追蹤中斷、HTTP／WS 分別斷線、Pause／End、完整排空，再做效能、MR、硬體與 VIVE。未把來源接線當成 Unity 運行完成，完整 11 項需求保持原範圍。CI 依本輪推送另記；未改帳務或重跑已知受限工作。

7c4ddb9 已推送；CI run 40773104321／check 123115220952 的 steps 空白，annotation 指出付款／支出限制，工作沒有啟動。本機 785 項結果有效，但不宣稱雲端成功；未修改帳務或盲目重跑相同工作。

## 2026-10-29：v0.12 持久世界、即時觀戰與伺服器回放

上一輪 v0.11 已推送並部署，屬於實際進展。本輪接續同一 F 槽儲存庫，Unity CLI 仍未讀到登入／授權；沒有啟動新登入或盲目重裝，沒有新的 Unity 編譯／APK／頭盔結果。長期目標保持開發中。

新增 engine-independent WorldRecording field DTO：schema 1、rules 0.8.0、primitives-v1／uncalibrated-vr，保存頭／槍口／方向、頭旋轉／左右手位置旋轉與來源、健康／彈藥／換彈／參戰、敵軍、完整世界事件及環境／AI 政策。此 schema 與既有本機 schema 2 模擬檔不同。未知版本、非有限資料、壞旋轉、幀／世界事件／戰鬥邊界不連續、越界／缺少名冊／政策衝突均拒絕。

新增 GameServer owner 專用 WebSocket world/publish，與既有 combat-stream 同 ID／origin／身分。先 header 再 frame／seal；UTF-8 文字最多 1 MiB。每份四種統計事件逐筆對照 durable combat witness，核對 ID／順序／來源／玩家／shot／enemy／damage／觀察時序，血量及剩餘彈藥也對上此事件前綴。未知來源不會變成真人／物理證據。沒有以世界渲染重新推算權威射擊。

世界另存 SessionDataDirectory/worlds.db（SQLite schema 1、WAL／FULL），管理 events.db／envelope 5 不變。每幀、統計、唯一事件 ID 及 cursor 同交易，拒絕／寫入失敗沒有部分幀。以 sequence／elapsed 索引讀取，不在啟動時載入整場幀。最後 Ended、精確 finalSequence、combat sealed、相同戰鬥邊界及最終統計都對上，才 complete=true；API End 不製造世界末幀。

主控台新增「觀戰與任務回放」，用有 Bearer 標頭的 fetch SSE 讀取 latest／replay，不加入玩家席位。支援房間與角色、自由／俯視／跟隨、暫停、時間索引跳轉、0.25–4 倍速及逐幀統計；頭手來源明示 None／Simulated／Tracked。來源超過 1.5 秒沒有新快照即標過期，心跳不能掩蓋停送；登出／切頁／換場取消串流。刪除離場角色的渲染資源，並修正即時時間軸長度及手機標題排列。

新增 VrCommand.WorldRelay：只建立自己的 Simulation 任務，以真正共用核心產生射擊／擊殺／AI 傷害／暫停／天氣／Ended。原始 NDJSON Flush(true) 後才逐幀送出並核對 ack，旁邊保留既有 combat journal；另一程序可逐行重送，同序內容只確認。來源損壞不自動截斷，缺少完成記錄不補造 seal；目前網路錯誤保留檔案後退出，尚無自動世界重連／恢復運算。

鎖定還原與 Release 建置 0 警告／0 錯誤，**333 核心、302 原 HTTP、24 真實世界串流、12 回放資料、72 Chromium 檢查通過，共 743 項**。17 份 Unity／共享 C# 語法通過，embedded Runtime 亦真正以 .NET Standard 2.1 建置，但沒有綁定 Unity SDK／ILPP。已檢視 world-live.png、world-stale.png 與 world-replay-mobile.png；含真實發布／SSE、來源強制中止後過期、房間範圍、回放統計、SQLite 重啟、整份來源跨程序重送、衝突重試及交易回滾。本機軟體 WebGL 不能代替頭盔／GPU 效能驗收。

本機預覽先確認自有舊程序及活動場次為 0，停止後備份完整 API data 至 artifacts/backups/pre-v012-*，再升級前後端。新 exec session 82831 服務版本 0.12.0，原四份歷史場次逐欄完全一致。新增自己的房 5 Simulation：b15507b1-d4cf-45a7-a830-7c2b4192ac6d，64 幀封存，彈藥 2／擊殺 1／健康 80；用新程序補送後世界 metadata 及五份歷史場次均不變，活動場次仍 0。來源／驗證摘要在忽略的 artifacts/world-demo*，預覽可直接選取此場回放。

Unity 目前只有共享錄製 DTO，**尚未接上世界發布器或真正頭手採樣**；既有統計 outbox 來源碼也仍未編譯運行。接續先完成工具可讀的 Unity 授權及真實 Prepare／Tests／Desktop／Quest，再接世界發送、頭手、雙玩家及斷線驗收。書籤、保留／壓縮、長任務／25 台吞吐量、正式資產、硬體、MR、VIVE 與實機仍待做。GitHub CI 依本輪推送結果另記，沒有修改帳務或重跑已知受限工作。

87e7a6c 已推送。其雲端 CI run 40766549749／check 123092115458 的 steps 為空，annotation 明確指出近期付款失敗或支出限制，因此工作未啟動。不能宣稱本輪雲端測試通過；本機 743 項結果仍有效。未修改帳務、未盲目重跑相同受限工作。

## 2026-10-29：v0.11 持久戰鬥補送、結束封存與主控台完整性

上一輪 v0.10 已推送來源碼與測試修正，屬於實際進展。本輪以該工作樹接續：CLI 仍未登入、license list 空，完成程式後實際 Unity Prepare 再次退出 198；命令已結束，不是仍在等待的建置。整體長期目標開發中，沒有 Unity 編譯、APK 或頭盔結果。

新增 GameServer 專用 combat-stream／reports／batch／seal 端點，Preparing 綁定唯一 streamId、origin 與來源身分。streamSequence 連續，observedSequence 指向事件產生時最後觀察的 Running 管理快照，以稀疏管理索引驗證當時狀態及名冊。Pause／End 後仍接受原觀察尾端，未來／暫停／已離場觀察不能偽造新射擊；既有報告可原樣去重，來源及內容不可換手。綁定後舊 combat 端點不可繞過。

End 釋放房間但 pendingTelemetry 維持 true；精確 finalSequence 已收到且來源送出 seal 後才標為完整。主控台 End 時自動保留待確認歷史，顯示補送／封存提示；新房間場次不受舊尾端影響。新 envelope schema 5 保留舊 1–4，SQLite user_version 仍 1；不得直接降版。批次最多 128 筆、逐筆持久化，失敗可已提交前綴，原樣重試去重續送，不宣稱跨批次原子性。

共用 Runtime 新增 TelemetryOutbox：獨占 journal、版本與身分、SHA-256 frame 完整性、批次 Flush、累計 acknowledgment、completion 及 seal。穩定 eventId 轉 reportId，只選四種統計事件，AI 射線／reload 不冒充玩家彈藥。檔案損壞／截斷不自動丟棄尾端；磁碟失敗不推進記憶體 cursor／ack。補送恢復不是世界恢復，尚無自動修復、壓縮或保留政策。

Unity 來源碼已在伺服器建立 journal／綁來源後開放戰鬥，武器及 tick 在保存後才發佈快照，網路／5xx 保留重試，永久拒絕／磁碟錯誤暫停戰鬥；在管理 End 前先保存原觀察尾端，再完成／補送／封存。預設明確 Simulation，server.json 指到 F 槽 data/telemetry，頭盔四欄設定不含密鑰。尚未編譯／運行發送器，不宣稱實機報表已一致。

新增 VrCommand.TelemetryRelay，可在原程序停止後以同一 journal 補送；只有 completion 存在才嘗試封存，否則保留未確認完整。其 demo 模式在空閒房建立自己的 Simulation 世界，以真正兩次射擊／命中／擊殺及一次 AI 傷害生成六份報告，先 End 並退出；另一程序才讀檔補送。HTTP fixture 另先接受一筆但不保存回應、重啟 API，再跑補送，驗證同一前綴不重複計數。

鎖定還原及 Release 建置 0 警告／0 錯誤，**295 項核心（新增 41 項）、302 項 HTTP、12 項回放資料、59 項 Chromium 通過**；16 份 C# 9 語法通過，embedded Runtime 真正建置 .NET Standard 2.1，Unity SDK／ILPP 未綁定。已檢視 telemetry-pending.png，畫面及測試區分 Ended／待補送／已封存。測試含競爭來源、失序、觀察資格、來源混用、批次部分提交／重試、兩邊獨立重啟、磁碟失敗、壞尾端及確認邊界。

本機原 5080 服務先驗證為本任務程序且活動場次 0，停止後備份完整 API data 至忽略的 artifacts/backups/pre-v011-*，再升級前後端；新 exec session 24293 正在服務，版本 0.11.0，原三份歷史快照在新增 null combatStream 相容欄位後完全一致。舊服務已停止。另於自有房 5 執行 demo 及恢復，場次 bafd9eb0-9309-4e10-b422-0a27a2e9cd78 六筆確認、sealed true、pending false、彈藥 2／擊殺 1／血量 80；只操作新建示範場次。journal 與摘要在忽略的 artifacts/telemetry-demo。

接續優先真正編譯／實測 Unity 管道與 Quest 雙玩家，並開發完整世界持久化、頭手錄製及即時觀戰；25 台吞吐量、硬體、MR、VIVE 型號與實機仍待驗收。沒有把這次統計補送當作完整遊戲完成。GitHub CI 先前曾部分運行但最新受帳務限制，待本次推送再依實際狀態記錄，沒有改帳務或盲目重跑受限工作。

## 2026-10-29：v0.10 Quest 任務與戰鬥接入來源碼

上一輪 v0.9 已推送並更新本機服務，屬於具體進展。本輪再次查核 Unity CLI，仍未登入且無 license；完成接入程式後實際 Prepare 仍退出 198，日誌為 No valid Unity Editor license found。該命令已結束，沒有執行中的安裝／建置等待，也沒有 APK 或 Unity 編譯通過證據。長期目標保持開發中。

embedded package 升至 0.10.0，新增無引擎 ArenaSession 與 field DTO，以真實管理 SessionView JSON 建立世界、名冊、任務掩體、固定席位與全場敵軍。重複刷新保持物件身分；敵軍增減不復活既有死者。VR 場地、資產、地面高度、出生點及範圍會驗證，拒絕不支援的 MR／幾何。遊戲伺服器須從 Preparing 啟動，不以新世界假冒 Running／Ended 的恢復。

以經驗票的連線 ID 綁定玩家，姿態不能指定玩家／傷害。新增核心 Connected 參戰狀態及粗略平面位移檢查；未連線、姿態超過 0.5 秒、斷線或名冊移除者不射擊、不擋彈、不被 AI 選取，保留血量／彈藥。新連線有獨立輸入 ID 域，晚到輸入／舊斷線不影響新連線。Preparing 移除已綁定玩家會安全重建未開局世界；管理 Begin 後全員離開而被輪詢跳過時，也不補造玩家或卡死轉移。

Unity Runtime asmdef 已引用核心，新增 CombatAuthority、伺服器固定步進與管理新鮮度暫停、伺服器 NetworkList、同源掩體及敵軍渲染、右手 OpenXR aim／扳機／A 鍵、桌面左鍵／R、owner 武器 RPC、健康／彈藥／換彈 HUD 與有效參戰顯示。生成器移除未與核心一致的展示掩體，改由任務資料提供，增加武器盒與 CombatAuthority。來源碼要求 Floor tracking origin，尚不可用時暫用 1.65m offset；並非 MR 校正方案。

依本機官方 NGO 2.7.0 原始碼確認 HostServerInitialize 不等待非同步 approval，改為啟動前驗 Host 票券，再同步回答；過期 pending client 不保留綁定。輪詢名冊後斷開被撤銷／結束的遠端連線；Host 玩家被撤銷則關閉 Host。這些都是尚待 Unity 運行的路徑，不能把原始碼檢視當作網路測試。

本機鎖定還原與 Release 建置 0 警告／0 錯誤，**254 項核心（新增 41 項）、282 項 HTTP、12 項回放資料、56 項 Chromium 通過**。15 份 C# 9 語法通過；embedded Runtime 真正型別建置為 .NET Standard 2.1，Unity SDK／ILPP 未綁定。新增三個待執行 EditMode 測試，合計七個；腳本要求至少七個通過，不能用舊四個結果宣稱新接入驗證。新檔案有穩定 meta GUID。

管理 API／瀏覽器仍為 v0.9，本輪未停用或更新原 5080 服務。Unity WorldEvent 目前只在記憶體，未送入 API CombatReport，頭盔 HUD 尚不會自動更新主控台統計。持久 outbox、Pause／End 事件排空、正式世界錄製及即時觀戰列為接續工作，詳見 GAMEPLAY。既有 SimulationDemo 維持明確 Simulation，舊回放規則／格式保留。

下一步仍先讓 Unity 授權可讀並真正 Prepare／Tests／Desktop／Quest，再實測雙玩家、武器／掩體／AI、管理中斷及撤銷；並行可做正式 outbox 與任務結束契約。沒有重新要求已同意的 SDK 條款，沒有代填登入、購買授權或改 GitHub 帳務。

de972be 的雲端 CI（40755707968）已實際啟動，故先前「帳務未讓工作啟動」已不適用本次；Linux 建置、254 項核心、282 項 HTTP 及 12 項回放資料通過。瀏覽器失敗在把隨機 UUID 排序報表的第一列誤認為 Alpha；新增 Temporary 玩家後列序不保證。改以明確玩家列核對，保留六項數值要求，再驗本機及雲端結果。

修正提交 76ab77d 以固定低 UUID 的離場玩家穩定重現此列序，本機 56 項 Chromium 通過。其雲端 run 40756358256／check 123056213471 再次因付款／支出限制未啟動（steps 空，annotation 明確指出帳務原因）。故只可聲明前次 Linux 部分檢查及修正後本機通過，不能宣稱完整雲端成功，也不能認定帳務依賴已永久解除。未修改帳務或盲目重跑相同受限工作。

## 2026-10-29：v0.9 場次與名冊的持久重試

上一輪 v0.8 已推送，屬於有實際程式與驗證結果的進展。本輪再次查核 Unity CLI，仍無登入 session、license list 為空；沒有啟動新登入或重裝 SDK，繼續可獨立開發的連線可靠性工作。整體長期目標保持開發中。

建立場次、加入玩家與移除玩家支援選用 `Idempotency-Key` UUID，與原事件在同一筆 SQLite append 交易中接受。跨三種操作與全館場次共用 key 索引，綁定身分、種類、目標及內容，持久化後重啟重建，失敗 append 不保留 key。每次重試仍檢查房間權限；改內容／身分／操作回傳 409，無效／全零／多值標頭回傳 400。不帶 key 的舊 API 行為保留。

重試回傳原操作已接受的確認與目前快照，不重播舊狀態：已離開玩家不因舊加入重試復活，重新入場者不因舊離開重試被移除；封存場次的建立重試不會占用新場次房間。新事件 envelope 為 schema 4，增加 requestId 與 PlayerLeft.roomId，保留 schema 1–3 讀取；資料庫 user_version 仍 1。不得在寫入新事件後直接降版。

瀏覽器三種操作都保存原 key、路徑、玩家 ID 與 body；遇到連線中斷／5xx 時鎖定後續寫入、切換與輪詢，在工作區頂端保留重試入口，無選中場次也可確認建立結果。成功後重新載入目前狀態。控制命令原去重保留，API 回應 body 讀完後也再次核對登入 epoch；登出後舊回應不能改寫新狀態。待確認操作只在頁面記憶體，關頁不持久保存。

本機鎖定還原及 Release 建置 0 警告／0 錯誤；**213 項核心、282 項 HTTP、12 項回放資料及 56 項 Chromium 檢查通過**。新增並行建立／加入／離開、內容及身分衝突、跨操作 key、容量已滿仍可確認原加入、晚到重試、封存／新場次隔離、SQLite 重啟、append 失敗恢復及 schema 相容／重複 key 拒絕。瀏覽器實際讓伺服器先完成操作再丟棄回應，驗證原 key／body 重送與單筆事件。HTTP 檢查失敗日誌亦改為容錯解碼及遮蔽測試憑證，避免 Windows 編碼錯誤蓋過原失敗。

原本 5080 服務已確認為本任務建立的程序且活動場次為 0。停止後將完整 API data 備份至忽略的 `artifacts/backups/pre-v09-*`，再建置並以原 `scripts/start-local.ps1` 升級主控台與後端；新 exec session 81620 正在服務，`GET /` 為 0.9.0、`/console/` 為 200，升級前後三份歷史場次快照完全一致。舊程序已停止，不要再當作活程序。前後端需一同升級，沒有將可重試前端留給忽略 key 的舊 API。

本輪只完成管理連線可靠性，不代表裝置重連、票券即時撤銷、Unity／APK／頭盔或正式世界串流驗收。接續優先取得工具可讀的 Unity 授權並接入已驗證共用核心；可獨立進行每次入場票券撤銷版本、遊戲伺服器與世界儲存工作。GitHub CI 帳務限制尚無解除證據。

## 2026-10-29：v0.8 3D 模擬回放與 Android 工具修復

新增「3D 模擬回放」頁，可載入實際幾何模擬紀錄或本機檔案，支援播放／暫停、逐格、時間跳轉、0.25–4 倍速、自由旋轉／平移／縮放、俯視及跟隨／點選角色。以快照還原角色、武器與實際掩體盒，顯示已記錄的射線，統計按快照 throughSequence 重建並與結束報表核對，不重新運行 AI。Three.js 0.186.1 由官方套件取得、SHA-512 核對，原始碼及 MIT／provenance 保留，不使用 CDN。

紀錄升至 schema 2／rules 0.8.0，增加 world props、射擊當下槍口／方向／距離／碰撞目標、快照的 AI／能見度／夜間設定。示範新增 10 秒巡邏，實際輸出 216 份快照、8 筆世界事件、10.4 秒邏輯時間；來源強制 Simulation。範例已保存為公開合成資產，沒有控制台憑證或真人資料。舊 schema 1 檔案保留但回放拒絕猜測缺少的資料。正式持久世界、頭盔六軸／雙手、即時觀戰與長任務串流仍待整合。

本機 Release 建置 0 警告／0 錯誤；**181 項核心、234 項 HTTP、12 項回放資料及 50 項 Chromium 檢查通過**。新增射線／快照設定驗證、資料因果與統計一致性、真實軟體 WebGL、鏡頭及時間控制、390px 版面、錯誤檔拒絕、文字渲染與登出後延遲回應不恢復舊檔。已檢視 `artifacts/console/replay-combat.png`、`replay-mobile.png`；這不是實機 GPU／頭盔效能證據。操作及限制見 `REPLAY.md`。

已將新版靜態資產更新到原本 5080 預覽輸出，`/console/` 與回放模組實際 200；沒有為此停止原 API 或改資料庫。管理 API 契約維持 v0.6，主控台／共用核心為 v0.8。

使用者已明確回覆「同意條款並安裝」，已執行 Android 模組安裝。原程序（exec session 34308／CLI PID 40596）已終止，不要再當作活程序重啟：Android、OpenJDK、SDK parent、platform 34 登錄成功，八個子模組回報失敗；單獨重試 Platform Tools 也回報失敗。檔案實際已解壓，部分留在巢狀目錄。

依官方 6000.3.27f1 module metadata 建立 `repair-android-layout.ps1`，先 WhatIf 核對來源／最終絕對目標，再整理限定 AndroidPlayer 內的 NDK、CMake、Build Tools、command-line tools；沒有覆寫／刪除既有目標。再次 WhatIf 無待移動。ADB 37.0.1、Temurin 17.0.18+8、NDK r27c／27.2.12479018（clang 18.0.3）、CMake 3.22.1、aapt2 均可執行；SDK Manager 辨識 Build Tools 36 及 platform 34／35／36。經使用者同意的 android-sdk-license 已用官方 SDK Manager 登錄。

`check-android-toolchain.ps1` 已實際以 CMake／Ninja／NDK 編譯及連結 C++17、Android log／STL、API 32 arm64-v8a 共享庫，驗證 ELF64 AArch64；輸出 `artifacts/android-toolchain-check/build/libvr_command_probe.so`。這是主要原生工具可用的證據，CLI 失敗登錄仍保留，不能宣稱 Unity APK 或 Quest 執行通過。

使用者另回覆「已登入並啟用」，但工具端 `auth status` 仍 loggedIn false、`license list` 空陣列；實際 Prepare 再次退出 198。已啟動一次 Unity 瀏覽器登入（exec session 1845），Chrome 標題停在 Unity ID Account Login，CLI 最終 AUTH_LOGIN_FAILED／登入逾時；該 session 已終止。後續需由使用者本機重新執行登入並等成功，再核對適用授權；不得把使用者回覆本身當作編輯器授權成功證據。沒有購買授權或代填登入。新詢問已提出，繼續其他可獨立開發工作。

整體目標仍開發中。下一步先取得工具端可讀的 Unity 授權並真正 Prepare／Tests／Desktop／Quest，接入共用核心與任務；同時仍需建立正式世界儲存、即時觀戰、硬體與頭盔實機流程。GitHub 雲端 CI 的既有帳務限制未有解除證據。

## 2026-10-29：v0.7 同源射擊、掩體、武器與 AI 模擬

新增 Unity embedded package `com.vrcommand.simulation`，Runtime 四份 C# 是唯一來源；`src/VrCommand.Simulation` 直接編譯為 .NET Standard 2.1／C# 9，不引用 .NET 10 後端或 UnityEngine。已實作固定 20 Hz 時間、準備／執行／暫停／結束、可旋轉掩體與身體盒射線、最近碰撞、隊友阻擋、射擊去重、射速、有限彈匣／備彈、換彈及傷害／死亡。

AI 核心已有 Hold／Patrol／Advance、自動攻擊開關、0.5m 四鄰 BFS 繞障與不可達處理、每步移動上限、視線及攻擊冷卻、霧／暴風雨／夜間範圍。這是簡化平面遊戲規則，沒有群體避讓、進階戰術、垂直地形、硬體或真實戰術模型。每個世界保留穩定事件 ID／序號，以及含武器姿態與 throughSequence 的隔離快照，尚非完整回放或持久世界。

新增 `tools/VrCommand.SimulationDemo`，只建立空閒房的自有場次，以真實射線計算低槍口被油桶擋住、AI 命中、操作設定關閉自動攻擊、側移後兩次命中擊殺；將核心事件依序送進 API 並固定標記 Simulation。預期為彈藥 3、命中 2、擊殺 1、耗損 20、中彈 1、命中率 66.67%、血量 80。API 的幾何場景／槍械輸入仍由外部受信任遊戲伺服器負責，此工具不是頭盔遊戲或持續運作的遊戲伺服器。

新增 51 項有意義的模擬檢查；本機 **179 項核心、234 項 HTTP 斷言、36 項 Chromium 檢查通過**。HTTP 測試用隔離服務實際執行新工具、驗證世界檔與 SQLite 統計及釋放房間。12 份 Unity／套件 C# 語法通過；其中共用 Runtime 另外通過真正的 .NET Standard API 型別綁定，仍不能取代 Unity 編譯／IL2CPP。

一般建置曾因現有主控台程序鎖住 API 的依賴 DLL 而失敗；改用 `artifacts/build-v07` 隔離輸出後，鎖定還原與完整 Release 建置 0 警告、0 錯誤。測試腳本新增 `VR_COMMAND_API_DLL`／`VR_COMMAND_SIMULATION_DEMO_DLL` 路徑選項，保持既有 5080 服務執行，不重啟或停止使用中的主控台。

在本機服務另實際執行房 5 幾何模擬並完成場次，保留 Simulation 歷史供主控台查閱；只操作示範自己建立的場次。除錯檔於忽略的 `artifacts/simulation-demo/latest.json`。完整規則、隔離建置、示範及限制見 `SIMULATION.md`。

下一步仍是 Unity 工程授權／Android 模組完成後匯入編譯，再將此核心接入任務、玩家輸入、擺設／敵軍渲染、NGO 世界快照與可靠統計傳送。現有 Unity 場景未呼叫此核心，管理介面也尚不會自動驅動它；沒有 APK、實機射擊／AI、實機混用或 25 人效能證據。整體長期目標維持開發中。

## 2026-10-29：v0.6 瀏覽器主控台、任務與平面配置

在 Unity 授權／Android 模組等待期間推進可獨立驗證的管理操作。新增 `/console/`，與 API 同程序提供繁體中文軍事風格主控／房間介面。可查看五房名額、從任務建立獨立／五房 Linked 場次、操作開始／暫停／繼續／結束、設定環境與敵軍、管理自房玩家及下載短效玩家連線檔。統計含六項需求指標、剩餘血量、明確來源與歷史查閱；操作紀錄不是 3D 回放。

任務編輯器支援名稱、內容、時間、環境／敵軍及沙包／油桶上視圖配置，可拖曳、方向鍵移動、輸入座標與旋轉、移除，再儲存為新的不可變任務；重新載入保留配置。尚無碰撞檢查、場館校正、任務版本鏈、覆寫或 Unity 載入這份配置。

控制台憑證僅保留在頁面記憶體，登出或重新載入需重新登入；所有資料仍由既有 API 授權，房間控制台不能修改 Linked 整場設定或其他房玩家。下載檔只含玩家票券與遊戲連線資料。使用獨立 JS／CSS 檔案、CSP、文字渲染，不載入第三方 CDN。靜態 web root 固定在輸出目錄，實際 DLL 從儲存庫根目錄啟動亦可服務，不依賴 Development 的來源映射。

管理命令失去回應時保留原 commandId／body／expectedSequence，鎖定後續寫入並提供重試；暫停與 End 的實際已接受／回應遺失情境均驗證只追加一次。待確認時停止刷新，避免已結束場次從活動列表消失而藏住重試入口。表單保存載入序號，舊設定不能覆寫他人命令，背景更新不會悄悄改掉正在輸入的草稿。建立／加入／離開去重與跨頁面重試恢復仍未完成。

本機 Release 建置 0 警告、0 錯誤；**128 項核心、229 項 HTTP 與 36 項真實 Chromium 檢查通過**。瀏覽器使用獨立 API、SQLite 與隨機憑證；驗證拖曳／重載、單房與 Linked 開局、環境／敵軍命令、權限、票券、過期表單、失去回應後重試、模擬統計、未信任文字、登出與手機寬度。已檢視截圖，位於忽略的 `artifacts/console/`。測試原先將 fieldset 當作 Playwright disabled 目標，已改驗實際輸入與按鈕；拖曳測試先捲動到可見圖面後操作。

瀏覽器相依固定 Playwright 1.62.1／pnpm 11.25.0，鎖定檔已產生。F 槽 exFAT 導致 pnpm 預設符號連結安裝失敗；確認 pnpm 11 改從 `pnpm-workspace.yaml` 讀取 `nodeLinker`，新增 hoisted 設定後，已鎖定安裝到隔離的 `artifacts/browser-hoisted` 並以該處套件執行 36 項檢查通過。未更改系統執行原則。CI 已加入鎖定安裝及瀏覽器檢查，雲端執行仍須解除既有 GitHub 帳戶付款／支出限制。操作說明見 `CONSOLE.md`。

當次已用 `start-local.ps1` 啟動本機 API，`/health` 及 `/console/` 實際回傳 200，確認 Production 也能載入介面；不是已部署的 Windows 常駐服務，後續先檢查實際程序，避免重複啟動。

完整長期目標仍未完成。Unity 仍無成功編譯／APK／頭盔證據；實際戰鬥、AI、硬體、MR、自由觀戰、世界快照與 3D 回放尚待開發。

## 2026-10-29：v0.5 Quest 3 工程來源碼與玩家票券

依「先用 META QUEST 3」建立 `clients/unity/`，固定 Unity 6000.3.27f1、OpenXR 1.19.0、XR Management 4.6.1、NGO 2.7.0、Input System 1.17.0、URP 17.0.4。採官方 URP Blank 17.1.0 的專案／渲染設定並保留授權，不含模板快取或雲端專案連結。來源碼包含簡化五區軍事場景生成、頭手姿態、桌面伺服器／玩家模式、玩家審核、狀態與霧／日夜／閃光同步。這些仍待 Unity 實際編譯與運行。

後端新增 HMAC-SHA256 五分鐘玩家入場票券。主控／自房控制台可配發，僅 GameServer 可驗證；驗證包含場次、名冊、到期與已結束狀態。簽章鑰保存在忽略的本機資料目錄，可重啟沿用；不寫進事件。每房固定 `seat` 0–4，離開時其他玩家不移位；舊事件沒有席位時依原加入順序重建。頭盔設定僅含地址、埠及自己的票券，不含控制台／GameServer 憑證。完整撤銷／重連與已連線玩家踢出仍待整合。

新增 `prepare-vr-session.py` 產生自己的單房 Preparing 場次與連線檔、`build-unity.ps1` 建置／EditMode 入口、`deploy-quest.ps1` 型號與設定欄位檢查及部署入口。詳細操作與限制見 `QUEST3.md`。HTTP 測試實際驗證設定助手與票券，但沒有執行 Unity 玩家或 ADB。

本機鎖定還原與 Release 建置通過，0 警告、0 錯誤；**128 項核心檢查及 229 項 HTTP 斷言通過**。包含票券竄改／到期／跨場次／錯誤角色／離開與結束拒絕、API 重啟後票券可驗、舊名冊恢復席位及玩家檔案不含伺服器憑證。8 份 Unity C# 通過 C# 9 純語法解析；PowerShell 腳本通過語法解析。語法檢查未綁定 Unity SDK，不能代替 Unity 編譯。

工具鏈：Unity CLI 1.0.0-beta.14 已安裝；Editor 已完整安裝至 `F:\Tools\UnityEditors\6000.3.27f1`，原安裝程序已成功結束，Package Manager 已就緒。實際 `build-unity.ps1 -Target Prepare` **退出 198：未登入／未啟用有效 Unity 授權**，日誌在 `artifacts/unity-logs/prepare.log`。已請使用者本機執行 `unity auth login` 並啟用適用授權；沒有自行建立帳戶、判定 Personal 資格或購買授權。

Android 模組尚未安裝。Unity 安裝器要求 `--accept-eula` 才能繼續 SDK／NDK 等模組安裝，已請使用者確認條款；尚未代為接受。**沒有成功的 Unity 編譯、生成場景／prefab、EditMode 結果、桌面程式、APK、雙玩家互見或頭盔實測**。下一個 Unity 步驟須先解決授權，再依 QUEST3.md 實際 Prepare／Tests／Desktop／Quest，修正編譯與執行問題。GitHub CI 的帳戶付款／支出限制仍無解除證據。

## 2026-10-29：v0.4 SQLite、戰鬥統計與 Quest 3 優先

使用者回覆「先用 META QUEST 3」。已同步路線、需求及開發指引：先實作 Quest 3 垂直切片，暫按 Android 獨立執行規劃，VIVE 後續接入；未將原始雙平台與 11 項需求縮減為後端原型。

新增 `VrCommand.Persistence`，使用 Microsoft.Data.Sqlite 10.0.14 與版本鎖定檔。預設事件改為 SQLite 交易逐筆追加，管理與戰鬥共用連續序號，記憶體採追加清單、命令／報告索引及增量統計；不再為每次射擊重寫全部歷史。舊 schema 1／2 JSON 先驗證後一次匯入，交易全有全無，原檔保留。單一寫入程序鎖、資料列／envelope 身分驗證與啟動恢復檢查均保留。

新增 schema 3 的 `CombatRecorded`、GameServer 認證接入、明確的 Simulation／GameServer 來源、射擊與命中關聯、唯一敵軍擊殺，以及傷害／血量投影。統計提供彈藥、命中數／命中率、擊殺、中彈、實際耗損及剩餘血量，保留已離開玩家並可重啟重建。主控與房間控制台不能提交戰鬥報告；模擬與 GameServer 來源不能同場混用。

新增 `scripts/demo_combat.py`：只在空閒房間建立自己的模擬場次，使用 Quest3 玩家分類，產生彈藥 3、命中率 66.67%、擊殺 1、中彈 1、耗損 20、血量 80，結束後保留歷史。HTTP 測試實際執行此腳本，並確認沒有占用既有場次或殘留房間名額。

本機鎖定還原與 Release 建置通過（0 警告、0 錯誤）。**119 項核心檢查、207 項 HTTP 斷言通過**，並將測試資料庫放在 `F:\Projects\vr-command-center\artifacts\temp` 重驗 SQLite、交易、鎖定及程序重啟。檢查涵蓋 schema 2 JSON 升級、錯誤匯入重試、唯一約束回滾、重複報告／射擊／擊殺拒絕、因果順序、傷害截斷、離開與暫停、事件不含憑證、兩次 API 重啟與統計一致。

五房 25 個 Quest3 分類的模擬玩家，合計 175 筆戰鬥報告，連同名冊／生命週期共 203 筆事件；總彈藥 75、命中 50、擊殺 25、耗損 500，各玩家血量 80。這是資料與儲存驗證，沒有 25 台頭盔、實際射擊／碰撞／AI 或 FPS／延遲證據。接收端信任 GameServer 來源的已分類事件，尚未獨立判斷真實場景命中。

契約、限制與升級流程見 `COMBAT_PROTOCOL.md`、`STORAGE.md`；CI 已加入 `--locked-mode`，但帳戶付款／支出限制造成雲端工作無法開始的問題尚無通過證據。完整長期目標仍在開發中。

## 2026-10-29：v0.3 控制台認證、五房權限與事件身分

所有 `/api` 端點現在要求 Bearer 控制台憑證，`/health` 保持公開。主控可管理全館；Room1–Room5 的列表／快照限制在自房及包含自房的共享場次，只能控制自己的獨立任務，以及管理本房玩家名額。全連線的整場命令只允許主控。GameServer 身分可讀取場次，不能管理任務、名額或場次；預留作為後續戰鬥事件來源。

新事件 envelope schema 2 保存伺服器驗證的控制台 ID／角色／房間，不保存憑證值。復原時重新檢查事件身分的權限；去重 ID 不能由另一控制台接管。舊 schema 1 保持可讀與 `actor: null`，不補造身分。核心的 Internal 身分僅供受信任的程序內部呼叫；HTTP 不會配發。

新增 `scripts/start-local.ps1`，首次產生七份不同的隨機本機憑證到 Git 忽略的 `data/operator-keys.local.json`，不在畫面印出鑰匙。也可使用環境變數或 `--OperatorKeyFile`；缺少主控、過短、重複或未知憑證設定會拒絕啟動。換鑰在重啟後生效。控制台認證尚不等同人員個別登入、TLS 部署或頭盔設備註冊。

本機驗證：Release 建置 0 警告、0 錯誤；**70 項核心檢查及 163 項 HTTP 斷言通過**，涵蓋五房列表／操作範圍、跨房讀寫拒絕、全連線權限、body 偽造角色無效、錯誤設定拒絕啟動、憑證檔載入、重啟換鑰與舊鑰失效、事件不含憑證，以及既有場次恢復與併發去重。啟動助手已通過 PowerShell 語法解析；HTTP 測試驗證其使用的憑證檔啟動方式，未對實際開發憑證檔進行操作。

文件已同步至 `AUTHORIZATION.md`、README、API 與事件契約。戰鬥統計尚未實作；下一步先選定可持續接收戰鬥事件的儲存方式，避免將高頻事件塞入目前逐次重寫完整檔案的低頻管理事件儲存，再實作統計與模擬器。M1 與完整長期目標均未完成。

## 2026-10-29：v0.2 場次生命週期與持久化管理事件

已實作 `Preparing → Running ↔ Paused → Ended` 管理狀態，建立場次與真正開始分開。新增環境與敵軍設定命令、命令去重 ID、可選預期序號及活動／歷史場次列表。結束後保留名冊與事件，並釋放房間與玩家名額。

事件包含版本、事件 ID、場次 ID、連續序號、後端 UTC 時間及資料；以相同轉移規則在重啟時重建狀態。採單一寫入程序鎖與暫存檔替換；寫入成功才更新記憶體。第二個 API 程序無法同時取得同一事件目錄。未知 schema、損壞資料與序號缺口會使啟動失敗，不重設歷史。

驗證於 Windows 本機完成：Release 建置 0 警告、0 錯誤；**50 項核心檢查及 116 項 HTTP 斷言通過**。包含 20 次併發核心命令重送、12 次併發 HTTP 重送、兩次實際 API 程序重啟、活動與結束場次恢復、第二個 API 寫入程序被拒絕、版本衝突、磁碟錯誤不推進狀態與損壞檔案拒絕恢復。測試資料與子程序在結束後清理。

契約與操作範例見 `SESSION_PROTOCOL.md`、`API.md` 及 README。v0.1 的 `GET` 已結束場次由 404 改為可讀取歷史；`StartedAtUtc` 改為在 `Begin` 前可為 null。建立／加入／離開操作尚未提供客戶端去重 ID；優先使用 `/commands` 進行可重試的控制。

這些是管理事件，尚無操作者身分、戰鬥事件、傷害、3D 世界快照或頭盔同步；環境／敵軍命令僅更新設定，尚未接到渲染或 AI。M1 仍在進行中。GitHub 雲端 CI 的帳戶付款／支出限制尚未解除，本次結果僅宣稱本機驗證。

## 2026-10-28：建立長期目標及 M0

長期目標已在本對話建立，維持開發中；本地開發根目錄為 `F:\Projects\vr-command-center`。本檔保存接續工作的事實與依賴，整體需求見 `REQUIREMENTS.md`。

GitHub 長期開發追蹤：[Issue #1](https://github.com/peca12968/vr-command-center/issues/1)。階段完成後更新此追蹤與本地文件。

已建立管理核心、REST API、任務 JSON 範例、核心規則檢查與 GitHub Actions 工作流程。後端使用本機已有的 .NET SDK 10.0.400；尚未安裝或建立 Unity 工程。

Release 建置成功：0 警告、0 錯誤。15 項核心檢查全部通過，包含五房獨立、全館 25 人名額、併發加入限制、快照隔離、任務持久化與場次釋放。66 項 HTTP 斷言全部通過，包含實際服務啟動、JSON 往返、錯誤碼與完整名額操作。

上述測試在 Windows 本機執行。私人 GitHub 儲存庫已建立，首次提交 `f4b836a` 已推送至 `main`，遠端私有狀態與分支已確認。實際指令見根目錄 README；CI 設定使用相同建置、核心檢查及 HTTP 整合腳本。

GitHub Actions [首次執行](https://github.com/peca12968/vr-command-center/actions/runs/40720827902) 在任何 step 啟動前失敗。check-run `122930936531` 的 annotation 明確回報：最近帳戶付款失敗，或需要提高 spending limit。第二次提交的執行也於啟動前失敗。**雲端 CI 尚未驗證，不能標示通過**；未變更帳務或啟用付費執行器。本機測試仍可執行，M1 開發不受影響。

## 未完成與外部資料

- Unity 工程尚未編譯或運行；共用核心已有 .NET 驗證，管理／配置 UI 與 3D 模擬回放可操作。Unity／頭盔遊戲、硬體通訊、正式持久錄影與即時觀戰仍待整合。
- 尚未收到廠商 SDK／協議；需依 `HARDWARE.md` 取得資料。
- VIVE XR 確切型號、Android 一體機／PCVR、場館尺寸與網路架構待確認。
- 沒有頭盔或硬體實測證據；25 個玩家記錄通過不代表 25 人實際連線達標。

## 接續位置

下一主線是解決 Unity 授權與 Android 模組條款後實際匯入／編譯，接入共用戰鬥核心、任務擺設、輸入與世界同步，完成 Quest 3 雙玩家切片。管理建立／加入／離開去重、裝置準備與重連、可靠世界儲存、自由觀戰及 3D 回放仍需補齊。等待使用者操作期間可繼續不依賴 Unity 的世界資料與回放工具；雲端 CI 須等 GitHub 帳戶付款／支出限制解除。每次開始先查實際 Git／程序與最新證據，不把無頭盔模擬當成已驗證的遊戲。
