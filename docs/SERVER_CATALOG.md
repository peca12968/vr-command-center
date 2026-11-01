# 伺服器待開場次清單

Windows伺服器啟動器 **1.1.0** 可直接輸入管理實例的`control-instance.json`完整路徑，按「載入／更新」，也保留選檔方式。清單顯示房間、單房／五房模式、任務名稱與場次識別前綴；選取後另列完整場次與任務版本ID。真正啟動使用原UUID，沒有從顯示文字反解或替換任務版本。

本輪主包為`artifacts/server-packages/windows-server-0.39.0-v5-win-x64.zip`，**82,669,350 bytes／SHA256 `3eef78fbe8319e366afa80cdfad31557bf42fb8bc3992402b6f252525e2857a2`**，311 manifest檔案／ZIP312含manifest。v4初候選為82,669,330／SHAf75b27e2...，原件與實際compiler input保存。Launcher版本獨立於Unity **0.39.0／code49／NGO29**與API **0.31.0**；控制台0.31.1、原224真正Editor、e0d60e4e...同源Windows／Quest、原Scene／prefab ID不變，沒有新Unity重建。

## 選取與更新

1. 先啟動管理服務，輸入或選取該實例檔案，按載入／更新。
2. 明確選擇要啟動的房間與任務，核對完整ID，設定本機公告／綁定IPv4及UDP埠，再啟動。初次載入不自動選第一個場次。
3. 重新整理只保留同一路徑、instance ID、API及GameServer key中，仍在新清單裡的原選取。原場次被綁定或結束而消失時，不改選別的房間。
4. 編輯路徑後停用啟動／選單，必須重新載入；載入失敗清除原目標與選取。變更實例身分或憑證後也需重新選擇。此輪伺服器停止後，下一次啟動前需更新清單。

清單只接受沒有來源的Preparing VR；Running、已綁來源及MR不供此工具啟動。最多5筆active場次，識別須canonical非空GUID，Independent須一房、Linked須完整五房；拒絕重複ID／重疊房間／越界或錯型別。名稱顯示移除控制與bidi格式字元、適度截短，不截斷surrogate pair；原名稱／ID保持。清單不是預約、就緒或頭盔在線證明，啟動前仍走原API身分與Preparing／無來源檢查，不重啟舊world。

目標以本次載入的API與憑證為準；外部修改實例檔案後請更新。載入仍為有界同步讀取，API root／身分／清單各5秒，清單最多256Ki個字元，未聲稱完整LAN故障恢復。只使用既有GameServer角色，不使用Master啟動Unity、不新增key／配票或下Begin／End。原session mutex、私有log來源核對、endpoint、雙seal／36秒保留／原child收尾保持。

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
