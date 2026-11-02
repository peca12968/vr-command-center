# 玩家連線檔載入與核對

Windows 玩家啟動器1.1新增「玩家連線檔完整路徑」及「載入／更新」，也保留原選檔按鈕。可貼上控制人員個別交付的JSON完整路徑，載入後只顯示檔名與IPv4／埠，不顯示票券。仍只接受原Client四欄結構，入場、效期、簽章與admission由原遊戲伺服器驗證；不新增網路探測。

編輯路徑立刻解除舊選取並停用「開始遊戲」；載入失敗不沿用先前檔案。載入時在拒絕其他writer的本機讀取lease內，以同一檔案解析與SHA256保存核對狀態。啟動前再次檢查內容，改址、換票、空白等任何byte變更或檔案遺失都解除選取，須重新載入並核對。包核對之後、真正Process.Start之前也重查hash；這是本機preflight，不能宣稱從UI到Unity讀檔的原子交付。

遊戲啟動後停用路徑／選檔／載入，原連線狀態與最終戰績保留不變。關閉啟動器不停止玩家或End任務；遊戲已啟動後，控制人員可依原Reconnect流程在原路徑更新票券。CLI原選項及無GUI啟動流程保持，不套用新的GUI核對狀態。

沿用Unity0.41.1／code52／NGO29、242真正Editor與4ebd雙平台的既有runtime；本輪不重建Unity或APK。新包名稱windows-player-0.41.1-v2.zip，與舊包只差啟動器、開始使用說明及manifest，完整hash與實際範圍見PROGRESS。包version1格式保持，另加launcherVersion1.1.0。

實際Framework ConfigReview24項覆蓋換地址、同地址換票、遺失、無效角色、相對路徑、被writer占用與解除舊選取；原monitor17項成功，皆不是GUI或入場證據。首次runner預期25而實際24，原compile/run檔保留後更正精確計數，未增加或跳過斷言。Linux CI明確skip此Windows Framework執行，不能稱雲端也跑過它。

```powershell
python -m unittest tests.test_player_config_review tests.test_player_package
python scripts/check-player-connection-status.py
node tests/browser/check-external-native.cjs <本次隔離ready.json> <F解壓目錄/VRCommand-Player> --package-interactive --package-path-input
```

最後一項需要實際操作啟動器：工具不預填第一位路徑，待操作人員載入／核對／按開始；第二位仍用原CLI。正式UI下載兩份個別短效票券，核對原native入場、Begin／Pause／End、結果與雙seal並清理。這是同機Simulation，頭盔／LAN／25真人仍待。新版包19項、實際GUI與兩玩家結果尚待本輪完成，未提前接受，完整11項目標保持active。
