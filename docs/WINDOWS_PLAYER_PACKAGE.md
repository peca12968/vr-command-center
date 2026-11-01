# Windows 可攜玩家包

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
