# 伺服器待開場次清單

啟動器 1.17 會在背景讀取管理服務。讀取時可以移動或關閉視窗，選房與啟動暫時停用。成功後只會保留同一實例中仍可用的原場次選取。讀取失敗會清空舊場次，重新載入後再選房。 [實測紀錄](PROGRESS.md#2026-11-11-windows-啟動器背景載入待開場次)

啟動器 1.12 可讀取遊戲主機上的私人 HTTPS `control-instance.json`。換了站台原點、金鑰或憑證指紋時，原場次選取會失效。個別啟動前也會重讀設定檔。 [建立 HTTPS 連線設定](WINDOWS_SERVER_PACKAGE.md#建立遊戲主機的-https-連線設定)

## MR 校正鎖定與啟動資格

Windows 伺服器啟動器 1.6 在待開清單標示「待鎖定校正」。選取該場可查看缺少鎖定的房號，啟動按鈕會停用。由主控鎖定校正檔後按「載入／更新」，同一實例會保留仍在清單中的原場次選取。單房獨立核對該房，五房合併核對全部五房。

`--catalog` 的每個場次會回傳 `canStart` 與 `missingAlignmentRoomIds`。此處表示場次符合清單的開場設定，IP、UDP 埠、管理服務可用性及頭盔就緒需分別核對。CLI 與 WinForms 啟動前都會重新讀取實際場次，缺少鎖定時在建立工作目錄和 Unity 程序前停止。 [本機驗證](PROGRESS.md#2026-11-09-mr-伺服器啟動前核對)

## 既有版本與場次清單流程

Windows伺服器啟動器 **1.1.0** 可直接輸入管理實例的`control-instance.json`完整路徑，按「載入／更新」，也保留選檔方式。清單顯示房間、單房／五房模式、任務名稱與場次識別前綴；選取後另列完整場次與任務版本ID。真正啟動使用原UUID，沒有從顯示文字反解或替換任務版本。

本輪主包為`artifacts/server-packages/windows-server-0.39.0-v5-win-x64.zip`，**82,669,350 bytes／SHA256 `3eef78fbe8319e366afa80cdfad31557bf42fb8bc3992402b6f252525e2857a2`**，311 manifest檔案／ZIP312含manifest。v4初候選為82,669,330／SHAf75b27e2...，原件與實際compiler input保存。Launcher版本獨立於Unity **0.39.0／code49／NGO29**與API **0.31.0**；控制台0.31.1、原224真正Editor、e0d60e4e...同源Windows／Quest、原Scene／prefab ID不變，沒有新Unity重建。

## 選取與更新

1. 先啟動管理服務，輸入或選取該實例檔案，按載入／更新。
2. 明確選擇要啟動的房間與任務，核對完整ID，設定本機公告／綁定IPv4及UDP埠，再啟動。初次載入不自動選第一個場次。
3. 重新整理只保留同一路徑、instance ID、API及GameServer key中，仍在新清單裡的原選取。原場次被綁定或結束而消失時，不改選別的房間。
4. 編輯路徑後停用啟動／選單，必須重新載入；載入失敗清除原目標與選取。變更實例身分或憑證後也需重新選擇。此輪伺服器停止後，下一次啟動前需更新清單。

啟動器 1.4 的清單接受尚未綁定來源的 Preparing VR 或 MR，並顯示任務的體驗模式。最多五筆場次。Independent 須一房，Linked 須完整五房。啟動前仍會核對 API 身分、Preparing 階段及來源狀態。 [MR 開場](QUEST3.md#主控建立-mr-場次)

目標以本次載入的 API 與憑證為準。外部修改實例檔案後請更新。API 根路由、身分及清單各有 5 秒請求期限，清單最多 256 Ki 個字元。讀取使用既有 GameServer 角色。

## CLI與驗證

```powershell
Launch-Server.exe --catalog <control-instance.json完整路徑> --report <新的包外及實例外JSON>
```

catalog只GET身分與場次，報告含任務／房間／原識別、不含key，complete只表示讀取完成。既有報告不覆蓋。空清單或被過濾的來源都不當遊戲完成。測試命令：

```powershell
python scripts/check-server-catalog.py <VRCommand-GameServer> --control-package <VRCommand-ControlServer> --runtime-root "$env:LOCALAPPDATA/VrCommand/RuntimeEvidence"
python scripts/check-server-package.py <VRCommand-GameServer> --control-package <VRCommand-ControlServer> --runtime-root "$env:LOCALAPPDATA/VrCommand/RuntimeEvidence" --observe-closure-ui
```

最終catalog **38項實際CLI／API檢查**與另 **26項真正Framework production parser／selection-state檢查**通過。包括真正五獨立／Linked、已綁定／MR過濾、無寫入、同名不同ID、同實例更新、變更身分／錯角色憑證／讀取失敗的清除及原選取消失不換房。Framework proof只在自己的未保存fixture修改／還原marker與key並以Master做一次測試End；這不是產品catalog寫入，也沒有操作WinForms UI。原碼／proof在獨立程序編譯，production不隨包帶測試Master key。

另新版實際server **106項**、五獨立後Linked、**777完整回放**、10份原admission結果／CSV與雙seal／closed world journal精確尾界／server ACK及cleanup成功；此處是CLI啟動，browser只是原Running／正常UI End／原world尾界觀察，不能代替Windows啟動器GUI驗收。所有runtime writer真正terminal後才各一次snapshot，保存SQLite不開。

本輪Windows GUI仍**未完成／failed**：實際欄位及路徑ValuePattern設定、編輯後disabled Start可確認；文字輸入未見落地、text-only click缺geometry，補snapshot後兩次點擊（含fresh activate重試）仍被PickerHost.exe擋住，沒有載入／選取／啟動或遊戲來源成功。停止桌面輸入，未操作PickerHost、權限或安全設定；只收自己的GUI／API，原failed與C/F保持。這是外部視窗阻擋，不是證明特定Windows或產品根因；新增直接路徑也沒有解掉這個阻擋。

[功能a8855cc](https://github.com/peca12968/vr-command-center/commit/a8855cc96bdf8cb0ece5fcc4c2dc5e7e0743e2c0)的[CI41344259683](https://github.com/peca12968/vr-command-center/actions/runs/41344259683)／job124960591099完整 **success**：Linux738規則／459 HTTP／47 world、6 pipe、全部Python／素材及83 Node／269 Chromium通過；2 Windows限定skip不是Framework、WinForms、Unity、native或頭盔驗收。console47檔 artifact13098871115／ZIP **11,451,172 bytes／SHA256 bd4624e686c0f92778b9eee34dd3db57a128ac6d5b1c6f7a773955d0c22ee630**，control13檔 artifact13098607730／ZIP **3,918 bytes／SHA256 d8b15a858f0b43d5f07e934a8e2107bc0ab664d46660a75023526c8a2afd7d58**，均已下載核對GitHub digest、逐檔hash並保存完整decoded log（SHA256 4ad0493f6a621d9cc3d28a4e8a263daadaa9d096b9407c027d5ad24d16742829）。`server-catalog-ci-validation.json`明列1260＋47＝**1307 browser證據**，另13 metadata；既有native UI5與本輪native UI2另列。後續只有文件提交skip ci，測試來源精確a8855cc；本機38＋26與106／777範圍保持，GUI仍未完成。

詳細輪次與雜湊見[PROGRESS](PROGRESS.md)，原操作契約見[WINDOWS_SERVER_PACKAGE](WINDOWS_SERVER_PACKAGE.md)。完整11項仍active；不是乾淨新機、LAN、25位操作、Quest／VIVE實機、MR校正或廠商硬體驗收，原31／world371／Windows startup／F吞吐問題保持待解。
