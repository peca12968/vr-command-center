# Windows 遊戲伺服器包

2026-11-16 啟動器 1.27 搭配 Windows 遊戲 0.50.12。ZIP 為 84,988,858 位元組，SHA-256 `22a6bafe884702fa4251b589c4dd2309836a6a1514106de17227021ad3f0db96`。與既有 Windows 玩家包和 Quest 0.50.12 APK 完成共同發行檢查。 [伺服器 ZIP](../artifacts/venue-udp-deadlines-20261116-1643/VRCommand-GameServer-0.50.12-launcher-1.27.0-win-x64.zip) · [共同發行報告](../artifacts/venue-udp-deadlines-20261116-1643/venue-release.json)

## 依場館發行報告核對伺服器包

啟動器可在離線核對、五房預覽或五房批次啟動時加上 `--release-report`。使用由主控提供且含 `windows.serverManifestSha256` 的原發行報告，報告及輸出放在程式包之外。工具比對清單原始位元組的 SHA-256，逐檔核對遊戲伺服器包。伺服器包不符時在查詢管理服務與建立遊戲程序前退出。

```powershell
& .\Launch-Server.exe --verify package --release-report C:\Delivery\venue-release.json --report C:\Delivery\server-verified.json
& .\Launch-Server.exe --venue-check C:\Delivery\venue-plan.json --release-report C:\Delivery\venue-release.json --report C:\Delivery\venue-preview.json
```

在 `--venue-run` 加入相同參數，即可於啟動時重新核對。啟動器 1.26 的離線核對、五房預覽、就緒及收尾檔會同時列出 `serverManifestSha256` 和整份原發行報告的 `venueReleaseReportSha256`。用 `start-verified-venue.py` 開啟五房時，帶入預覽原本使用的 `--release-report`。若換成另一份報告或修改過原檔內容，工具會在開啟遊戲前拒絕。換用新伺服器包時，請用它重新預覽並產生 UDP 預檢報告。 [產生原發行報告](EXTERNAL_CLIENTS.md#發送前離線核對交付套件) · [戰後核對伺服器發行](EXTERNAL_CLIENTS.md#核對五房伺服器發行版本)

2026-11-16 啟動器 1.26／Windows 遊戲 0.50.11 的 ZIP 為 84,984,799 位元組，SHA-256 `c12fc5c5b5e66825be2bef971cd8ddfdc5d5603f327123d34b3f82de84812a4b`。解壓核對 331 筆清單。 [伺服器包](../artifacts/windows-server-release-report-1260-05011.zip) · [共同發行報告](../artifacts/venue-release-server-report-1260-05011.json)

2026-11-16 `VRCommand-GameServer-0.50.11-1.24-win-x64.zip` 為 84,985,912 bytes，SHA-256 `3b6f84c96b05daba8b2f72202b7db13bcb0b3217feba4459adf1b5a395f00bbe`。解壓核對 331 筆清單，已和 Quest 0.50.11 核對來源及網路識別。 [伺服器包](../artifacts/server-packages/VRCommand-GameServer-0.50.11-1.24-win-x64.zip) · [發行報告](../artifacts/venue-release-quest-reconnect-0511.json)

2026-11-16 `VRCommand-GameServer-0.50.10-1.24-win-x64.zip` 為 84,984,809 bytes，SHA-256 `02c29654473635860b2698b674008d58b5f19418b5a33024b1322e59dfe5c089`。解壓核對 331 筆清單，已和 Quest 0.50.10 核對來源及網路識別。 [伺服器包](../artifacts/server-packages/VRCommand-GameServer-0.50.10-1.24-win-x64.zip) · [發行報告](../artifacts/venue-release-quest-link-0510.json)

2026-11-16 `VRCommand-GameServer-0.50.9-1.24-win-x64.zip` 為 84,984,800 bytes，SHA-256 `10a905084d642c8ebee152a1572cb16ca8ad4a8d30819942a9a3c4d620f74152`。解壓核對 331 筆清單，已和 Quest 0.50.9 核對來源及網路識別。 [伺服器包](../artifacts/server-packages/VRCommand-GameServer-0.50.9-1.24-win-x64.zip) · [發行報告](../artifacts/venue-release-quest-openxr-0509.json)

2026-11-16 `VRCommand-GameServer-0.50.8-1.24-win-x64.zip` 為 84,984,763 bytes，SHA-256 `9949eeb0c2f1c07ad983783e126c1bb8e93f854d2add56f8c67b5d17f5877f62`。解壓核對 331 筆清單，支援 VR 場次的 `GameServer` 追蹤來源。 [伺服器包](../artifacts/server-packages/VRCommand-GameServer-0.50.8-1.24-win-x64.zip) · [發行核對](../artifacts/venue-release-tracked-vr-0508.json)

2026-11-13 `VRCommand-GameServer-0.50.7-1.23-win-x64.zip` 為 84,984,410 bytes，SHA-256 `1b5a6789d6ba8d5ea6f63495866359fc75bc33bf854b3703f391e9a936f6b2ae`。解壓核對 331 筆清單。五房批次視窗可複製本輪就緒與結果報告的完整路徑。 [伺服器包](../artifacts/server-packages/VRCommand-GameServer-0.50.7-1.23-win-x64.zip)

2026-11-13 `VRCommand-GameServer-0.50.7-1.22-win-x64.zip` 為 84,983,846 bytes，SHA-256 `7043c427022e40f4f4048e6801992504671e75d9a779b260964d0aeb9d19a293`。解壓核對 331 筆清單。五房批次啟動視窗可逐房查看已登記的席號。 [伺服器包](../artifacts/server-packages/VRCommand-GameServer-0.50.7-1.22-win-x64.zip)

2026-11-11 `VRCommand-GameServer-0.50.7-1.20-win-x64.zip` 為 84,981,993 bytes，SHA-256 `ce417b05968a31d3ecf13cb07acc8f8c132ea481e8a746de8ddf52e04154ab03`。解壓核對 331 筆清單。執行中的合併場實測指定網卡上的遊戲 UDP 及本機上的 Unity 編輯器連線。 [伺服器包](../artifacts/server-packages/VRCommand-GameServer-0.50.7-1.20-win-x64.zip) · [監聽紀錄](../artifacts/windows-local-profiler-0507/linked-server-sockets.json)

2026-11-11 `VRCommand-GameServer-0.50.6-1.20-win-x64.zip` 為 84,981,819 bytes，SHA-256 `b6ce6d22ba811a9f6743d33f2720a14c90ddc909ad1dc8ca64b4fe3b442d7c73`，解壓核對 331 筆清單。 [伺服器包](../artifacts/server-packages/VRCommand-GameServer-0.50.6-1.20-win-x64.zip) · [發行核對](../artifacts/venue-release-0.50.6-xr-startup.json)

2026-11-11 `VRCommand-GameServer-0.50.5-1.20-win-x64.zip` 為 84,815,253 bytes，SHA-256 `872b8bd494d13497897b001020b093b8902e3e029763cff3c2532946caf29683`。解壓核對 330 筆清單。五房批次支援 Alt+V、Enter 與 Alt+S。 [批次鍵盤操作](#從-windows-視窗核對並啟動)

2026-11-11 `VRCommand-GameServer-0.50.5-1.19-win-x64.zip` 為 84,815,122 bytes，SHA-256 `8f92eca496b21c6b4977e689e9487d95727134b7ff1608df48d921694fe487d2`。解壓核對 330 筆清單。支援 Alt+R 選房、Alt+P 設定 UDP 埠及 Alt+S 啟動。 [操作方式](SERVER_CATALOG.md)

2026-11-11 `VRCommand-GameServer-0.50.5-1.18-weapon-gate-win-x64.zip` 為 84,815,059 bytes，SHA-256 `80a9c1f88f430b7d201ba4f5e63962ecc81c4a201937b60ff71d6a2fce0eca16`，解壓核對 330 筆清單。搭配同版 0.50.5 玩家與 Quest 開發 APK。 [桌面武器輸入](DESKTOP_WEAPON_INPUT.md)

2026-11-11 `VRCommand-GameServer-0.50.4-1.18-keyboard-win-x64.zip` 為 84,814,935 bytes，SHA-256 `0ce48c52dc23f83eb5960b529c0765c6f807dcd7595233fe4c207006514cf434`。解壓核對 330 筆清單。啟動器提供管理路徑欄 Enter 載入，搭配 Windows 遊戲 0.50.4。 [鍵盤操作](SERVER_CATALOG.md)

2026-11-11 `VRCommand-GameServer-0.50.4-1.17-catalog-win-x64.zip` 為 84,814,710 bytes，SHA-256 `ea9e997f21a93c51609d0255babb2ad65ee97198953ee65ab216f846c1453d5b`。解壓核對 330 筆清單。啟動器在背景讀取單房視窗的待開清單，遊戲沿用 0.50.4。 [待開清單操作](SERVER_CATALOG.md)

2026-11-11 `VRCommand-GameServer-0.50.4-1.16-venue-receipt-retry-win-x64.zip` 為 84,812,731 bytes，SHA-256 `a033b9936e45cb4fdfc72d1d0af99c83ddbea12a602051c39822e2bd8fd5fc5f`。解壓核對 330 筆清單。遊戲沿用 0.50.4，啟動器可重送原全館來源登記及端點公告。 [操作與報告](#依場館計畫批次啟動)

2026-11-11 `VRCommand-GameServer-0.50.4-1.15-venue-source-batch-win-x64.zip` 為 84,811,892 bytes，SHA-256 `aa4e19c1548e61136a58d7e396a38fa4fc41b98b6031cd32d39215b0a1ad0c19`。解壓核對 330 筆清單。第四版計畫等待全部遊戲程序準備後，再登記整批來源。 [操作方式](#依場館計畫批次啟動)

2026-11-11 `VRCommand-GameServer-0.50.3-1.14-guarded-source-win-x64.zip` 為 84,808,914 bytes，SHA-256 `889e69380e7f32becf3c18fc0d9cbdeec1427943252932c5ad5d55a9b0e503e6`。解壓核對 330 筆清單。支援在登記遊戲來源時核對原場次序號。 [操作方式](#依場館計畫批次啟動)

2026-11-11 `VRCommand-GameServer-0.50.2-1.13-venue-plan-win-x64.zip` 為 84,807,939 bytes，SHA-256 `9886b6d73eeb0f90a162938245897f08e9b466a051e9a8e2641b039e7f653c76`。解壓核對 330 筆清單。第二版場館計畫須比對原場次序號與任務版本，沿用遊戲 0.50.2。 [操作方式](#依場館計畫批次啟動)

2026-11-10 `VRCommand-GameServer-0.50.2-1.12-debrief-win-x64.zip` 為 84,807,998 bytes，SHA-256 `59e25280556639f219faecbdbd3b174bddaa99fad29e778e9feea971ff65f1cb`。解壓核對 330 筆清單。遊戲 0.50.2 可將玩家戰績回條送至 0.31.109 管理包。 [任務收尾](SESSION_CLOSURE.md#玩家戰績回條)

2026-11-10 `VRCommand-GameServer-0.50.1-1.12-https-venue-final-win-x64.zip` 為 84,807,075 bytes，SHA-256 `a8290ac78089d0281177962b01409c4c733c1bb3a371ab4820894de3aca5aa0b`。解壓核對 330 筆清單，沿用原 0.50.1 遊戲。啟動器可用一份私人 HTTPS 設定查詢場次及啟動五房批次。 [設定方式](#建立遊戲主機的-https-連線設定)

2026-11-10 `VRCommand-GameServer-0.50.1-1.11-https-win-x64.zip` 為 84,806,680 bytes，SHA-256 `80b733db21c1351e0701c8630f67b44ae2c45099d06f3a32c5c7983a19cfd984`。解壓核對 330 筆清單。個別場次 CLI 支援指定管理站台的 HTTPS、WSS 及憑證指紋。 [遊戲主機設定](#遊戲主機連到遠端管理-https)

2026-11-10 `windows-server-0.50.0-launcher1.10-win-x64.zip` 為 84,800,547 bytes，SHA-256 `e12a6049410a3d01a3423bf9ff1ddffa7125db627f0c3c1beaabfab196258b1b`。解壓核對 330 筆清單。全館啟動使用管理包 0.31.100 的整批端點公告。 [五房啟動](#依場館計畫批次啟動)

2026-11-10 `windows-server-0.50.0-launcher1.9-win-x64.zip` 為 84,799,236 bytes，SHA-256 `59c159d66daa7fbd97a256b8713eb6aee48132191d9574579ef5ac2da0ada43b`。解壓核對 330 筆清單，328 個檔案與 1.8 逐檔一致。遊戲來源、Windows 玩家及 Quest 開發 APK 沿用 0.50.0。 [五房視窗操作](#從-windows-視窗核對並啟動)

2026-11-10 `windows-server-0.50.0-launcher1.8-win-x64.zip` 為 84,794,219 bytes，SHA-256 `d551a2d461e02619ddb8e434af0925c23d5eb4167bd83a3460587b5b52ef0fc7`。解壓核對 330 筆清單。遊戲來源支援合併場分房敵軍策略，與同版 Windows 玩家及 Quest APK 使用相同場景網路識別。 [分房操作](LAYOUT.md#合併場分房敵軍策略)

2026-11-10 `windows-server-0.49.1-launcher1.8-final-win-x64.zip` 為 84,792,691 bytes，SHA-256 `dcd31cbb24a6092b87dba8e78bf2c8adffa667bbce4b6624d06356bf85a5f7dd`。解壓核對 330 筆清單。與 0.49.1 的 1.7 伺服器包相比，328 個清單檔案的雜湊一致。 [批次操作](#依場館計畫批次啟動)

2026-11-10 `windows-server-0.49.0-launcher1.7-win-x64.zip` 為 84,787,603 bytes，SHA-256 `f5ecb57361f981e6f66497bb987598a3f57a83f623ddb14d9e5ad05647002d39`。解壓核對 330 個清單檔案。此版本與 Windows 玩家包使用同源遊戲建置。

2026-11-09 `windows-server-0.48.1-launcher1.7-win-x64.zip` 為 83,470,147 bytes，SHA-256 `c3d15a8fc23fec76b5a127c8ffc977719eb538074b0e2bfd693974c6be368bd0`。解壓核對 328 個清單檔案。搭配同源 0.48.1 Windows 玩家及 Quest APK。 [版本相容性](EXTERNAL_CLIENTS.md#遊戲版本相容性)

2026-11-09 `windows-server-0.48.0-launcher1.7-win-x64.zip` 為 83,469,619 bytes，SHA-256 `dce833f49f6a94e630666a6d36d152e80ae5fa693d8a7ad5ffd6f744798a03ef`。解壓核對 328 個清單檔案，321 個 Unity 0.48.0 執行檔案與 1.6 逐檔一致。Windows 啟動器新增場館驗收的來源紀錄開關。 [操作方式](#跨機來源診斷)

2026-11-09 `windows-server-0.48.0-launcher1.6-win-x64.zip` 為 83,468,953 bytes，SHA-256 `aeb7b59c58a43f86918ec6135227658596d58afab5a397cfeaf2badda777fb92`。解壓後核對 328 個清單檔案，321 個 `Runtime/` 檔案逐檔符合 1.5 的 Unity 0.48.0 執行內容。新版會在啟動前核對 MR 場次的房間校正鎖定。 [操作方式](SERVER_CATALOG.md#mr-校正鎖定與啟動資格)

2026-11-09 `windows-server-0.48.0-launcher1.5-win-x64.zip` 為 83,468,072 bytes，SHA-256 `fa6baef98f2d52a5fff9e0d0a3a09cff9dbc2aab3c2111b18b86b88fd8335e82`。解壓後核對 328 個清單檔案。MR 場次須在啟動前鎖定全部房間的校正檔。 [主控操作](QUEST3.md#啟動-mr-伺服器前鎖定校正檔)

2026-11-09 `windows-server-0.47.1-launcher1.5-win-x64.zip` 為 83,466,797 bytes，SHA-256 `f885bc1b2fc7c3131dd59498f965d408749e60b00c8b9dbcc98209927907a9a7`。解壓後核對 328 個清單檔案。 [版本相容性](EXTERNAL_CLIENTS.md#遊戲版本相容性)

Unity 0.47.0 伺服器可搭配控制台 0.31.14。啟動器 1.5 可選擇待開的 VR 或 MR 場次，並在就緒後容許短暫管理服務中斷。場中增援由配套管理服務核對場地容量與錄製版本。 [場中敵軍增援](LAYOUT.md#場中敵軍增援)

## 選檔啟動及結算驗收

單場視窗也可以直接貼上 `control-instance.json` 的完整路徑並按 **Enter**。等清單載入，按 **Alt+R** 聚焦場次、按 **Alt+↓** 展開，再用方向鍵選擇並按 **Enter**。核對完整場次 ID 與任務版本後，用 **Tab** 移到公告 IPv4、綁定 IPv4、UDP 埠及來源紀錄選項。按 **Alt+S** 啟動。等畫面顯示「任務已封存並停止」後，可按 **Alt+F4** 關閉。 [0.50.7 單場複驗](PROGRESS.md#2026-11-11-windows-伺服器-0507-單房視窗複驗)

2026-11-10 以伺服器包 0.49.0 和管理包 0.31.64 實測。管理服務運行時，在啟動器按「選擇檔案」，開啟該實例的 `control-instance.json`。場次清單載入後，選定房間並核對場次與任務版本。設定公告與綁定位址、UDP 埠，需要保存來源時勾選「記錄本次玩家連線來源（場館驗收）」，再按「啟動伺服器」。收尾時等畫面顯示「任務已封存並停止」後關閉。

本輪單房的一名 Windows 模擬玩家在同機入場。開始與結束由測試程式經管理 API 送出，UDP 來源、原戰績、伺服器確認回條與 79 格回放均通過核對。原遊戲程序停止後從視窗正常關閉，診斷選項清除。 [實測紀錄](PROGRESS.md#2026-11-10-windows-遊戲伺服器選檔至結算驗收)

## 依場館計畫批次啟動

`--venue-run` 使用同一份計畫在一台遊戲主機啟動五個獨立遊戲伺服器，或啟動涵蓋五房的一個合併伺服器。先在管理服務準備場次，再從控制台下載或手動建立計畫。計畫與工作目錄放在解壓包及管理實例之外。啟動器 1.12 的計畫可引用本機管理實例或遊戲主機上獨立保存的 HTTPS 連線設定，兩種檔案名稱皆為 `control-instance.json`。 [分機設定](#建立遊戲主機的-https-連線設定)

### 從主控台下載場館計畫

使用控制台 0.31.114 搭配 Windows 啟動器 1.15 與遊戲伺服器 0.50.4 或以上版本。以主控登入，在「房間與場次」展開「Windows 遊戲伺服器啟動計畫」，按「讀取五房場次」。控制台列出各房原場次和任務，指出空房、已附掛來源或等待鎖定校正的 MR 房間。五房都可以啟動後，填入伺服器電腦上的 `control-instance.json` 完整路徑、公告 IPv4 及 UDP 埠。綁定 IPv4 留空會沿用公告位址，也可明確填入 `0.0.0.0`。

獨立場每房填一個不同 UDP 埠，合併場只填一個。點選「下載啟動計畫 JSON」後，控制台會再次核對原場次，並把場次序號與任務版本寫入第四版計畫。設定、名冊或校正鎖定若有變更，請重讀場次後再下載。完整路徑只在瀏覽器組入檔案，檔案也不含憑證或入場票券。下載後在伺服器電腦開啟。

控制台 0.31.138 若發現場次變更，會指出受影響的房間並要求重讀。留在「房間與場次」時，重讀會保留此頁已輸入的 UDP 埠。獨立模式分房保留，合併模式保留單一埠。刻意清空的欄位要重新填寫才能下載。離開「房間與場次」或登出會清除這次的輸入。下載時仍會核對最新場次、版本及 UDP 設定。

控制台可選取版本 1 的席位 IPv4 表，再按「下載 UDP 預檢清單 JSON」。五房需有相同席數，每房 1 至 5 席。預檢清單使用具體綁定位址，並與席位表同為私有區網或本機測試 IPv4。從 0.31.175 起，表內的房號與席號須和準備中場次的已登記席位完全一致。表內位址只在瀏覽器讀取，下載前會重新核對場次與席位。下載後沿用 Windows 啟動計畫與啟動器預覽，交給雙端 UDP 預檢。 [席位表與預檢流程](EXTERNAL_CLIENTS.md#從原啟動預覽產生網路清單)

啟動器 1.21 在版本 2 至 4 的成功預覽中附上 `registeredSeats`，只列房號與從 1 起算的席號。由原預檢報告執行 `start-verified-venue.py` 時會先重新取得此預覽。場次、名冊、端點或實例不符時，啟動會在建立遊戲程序前停止。

三包整合驗證可同時使用 `--check-venue-plan-ui`、`--check-venue-preview`、`--check-venue-udp-readiness`、`--peer-diagnostics` 和 `--venue-field-evidence`。Chromium 下載啟動計畫與預檢清單，後續預檢、Windows 啟動及戰後逐席核對都讀取同一份清單。命令另需 `--prepare-independent-set --check-venue-begin --check-venue-end --check-venue-launcher`。 [三包整合驗證](#三個可攜包整合驗證)

`GET /api/venue/server-plan` 限主控，回應五房的場次、序號、任務識別及啟動條件。Windows 啟動器核對計畫並取得全館本機啟動鎖後，等待各遊戲程序準備自己的日誌來源 ID。第四版計畫透過 `PUT /api/venue/combat-streams` 在同一筆資料庫交易核對序號及登記全部來源。遊戲取得原批次與來源的回條後才開啟 UDP。任一房的原場次已變更時，整批登記會遭拒絕，可重新下載同一批場次。全館端點等所有 UDP 綁定確認後才一起公告。

可在三包整合驗證加入 `--prepare-independent-set --check-venue-begin --check-venue-end --check-venue-launcher --check-venue-plan-ui`，使用 Chromium 下載原計畫再交給啟動器。

### 從 Windows 視窗核對並啟動

啟動器 1.20 可按 **Alt+V** 開啟「五房批次啟動」。貼上控制台下載的 JSON 完整路徑，按 **Enter** 核對計畫。確認清單上的房號、任務、場次 ID 與 UDP 埠後，按 **Alt+S** 啟動全館。視窗也提供「選擇計畫」與「核對計畫」按鈕。將滑鼠停在清單列可看見場次序號、任務版本與本機綁定位址。

啟動器 1.22 的「已登記席號」從 1 起算，保留名冊中空出的席位，例如 `1、4`。合併場顯示五列房間，各列共用同一場次 ID 與 UDP 埠。已核對的空房顯示「尚未登記」，第一版計畫顯示「計畫未提供」。請在按 **Alt+S** 前對照主控台名冊。啟動時會再核對原場次和名冊。

修改路徑會清除前次核對結果。啟動器會在開場前重讀計畫及管理實例。若檔案在核對後被更換，啟動會拒絕舊預覽、清除清單並停用啟動。請從控制台重新下載並核對當次計畫。

視窗顯示「全館就緒」後，回控制台配票、開始和結束任務。結束後等視窗顯示全館結果。中止會停止這次視窗建立的遊戲程序，並把這批標為未完成。工作及結果分別寫入本機的 `%LOCALAPPDATA%\VrCommand\GameServers` 與 `GameServerReports`。

啟動器 1.23 可按「複製就緒路徑」或「複製結果路徑」。若主控台瀏覽器在同一台電腦，可將完整路徑貼到報告選檔視窗。若主控台在另一台電腦，先將原報告交給主控，再從該電腦選檔。按鈕會在原報告寫出後啟用，批次結束後仍可複製這輪的兩份報告。修改計畫路徑或重新核對計畫會清除前一輪的按鈕。批次未完成時，已寫出的結果仍可供查閱，封存狀態以報告內的結果為準。 [主控核對](#核對未確認的啟動報告)

也可用 `Launch-Server.exe --venue-window <計畫完整路徑>` 開啟五房視窗並填入路徑。命令列的 `--venue-check <計畫完整路徑> --report <新結果檔>` 會核對相同的房間、任務、校正及 UDP 條件。核對結果沒有憑證，啟動時仍會取得原場次的本機鎖。

開場前可將這份成功預覽和 Windows／Quest UDP 雙端報告一併核對。若某房的模式、埠或公告／綁定位址與網路清單不符，場館報告會標出該房，供主控修正。 [五房 UDP 核對](EXTERNAL_CLIENTS.md#開場前核對五房-udp-報告)

### 以 UDP 預檢報告啟動五房

可先用 `start-verified-venue.py --verify-only --launch-plan .\venue-plan.json --network-plan .\venue-network.json --readiness .\venue-readiness.json` 重驗全館預檢引用的原檔。完整且有效時回傳 `udp-evidence-verified`。未完成的報告也可帶入。工具會重驗其中保留的原檔，回傳 `udp-evidence-incomplete`、待補房號與席號，以及未配對、無法讀取或仍待處理的收件問題數，退出碼為 1。這一步只核對檔案和預檢有效期限，實際啟動須提供完整報告並向管理服務確認最新名冊與場次。

待補席位的 `reason` 可指出原檔無法讀取（`unreadable-original`）、超過 30 分鐘（`expired`）、量測時間未早於核對時間（`clock-ahead`）、雙端屬不同交換（`exchange-mismatch`）、端點不符（`binding-mismatch`）或報告無效（`invalid-report`）。若可從一端的完成報告確認原計畫中的來源，`missingRole` 會指出需補的 `listener`（監聽端）或 `probe`（探測端）。若雙端都無法確認，請依待補席位與無法讀取的配對數量查找原檔。

新產生的全館預檢報告保存每組監聽端和探測端的 SHA-256。若原路徑下的雙端報告仍有效但內容已換過，重驗會在受影響的席位標示 `changed-original`，啟動也會停止。若已重新探測，請用新雙端報告重新產生全館預檢。既有未保存雜湊的預檢報告仍可按原流程重驗。

原計畫與預覽仍相符，且只有 UDP 證據需補件時，在同一條 `--verify-only` 指令加上 `--retry-output .\venue-retry.json`。若重驗未完成，工具會保存一份可供 `--retry-report` 使用的報告，保留這輪仍有效的雙端原檔。重驗全部通過時不會建立補件檔。 [補測指令](EXTERNAL_CLIENTS.md#補測未完成的全館-udp-預檢)

需要在開場前重驗預檢時，從專案目錄執行以下指令。使用本次的網路清單、原啟動計畫，以及核對計畫和預覽後產生的完整 `venue-readiness.json`。保留報告所引用的原始雙端檔案及預覽路徑。工作目錄和兩份結果檔使用新路徑。

```powershell
python .\scripts\start-verified-venue.py `
  --launcher C:\VRCommand\GameServer\Launch-Server.exe `
  --launch-plan C:\VRCommand\venue-plan.json --network-plan C:\VRCommand\venue-network.json `
  --readiness C:\VRCommand\venue-readiness.json --seconds 3600 `
  --work C:\VRCommand\venue-work --ready-report C:\VRCommand\venue-ready.json `
  --report C:\VRCommand\venue-result.json --peer-diagnostics
```

指令先重驗原計畫、網路清單及雙端 UDP 報告。在 Windows 啟動器完成最新預覽後，會再次核對這些檔案的雜湊和既有 30 分鐘期限。缺件、逾時或原檔異動會在遊戲程序建立前回報。看到 `udp-preflight-verified` 後，仍須等啟動器寫出 `venue-ready`，再到控制台配票和開始。`--peer-diagnostics` 可選，用於需要保存玩家 UDP 來源的驗收。 [補測方式](EXTERNAL_CLIENTS.md#補測未完成的全館-udp-預檢)

使用啟動器 1.27 時，工具會自動傳入逐房 UDP 期限。若遊戲啟動期間超出期限，啟動器會停止本批作業，保留本次結果，控制台也不會收到這次的全館端點公告。期限以 Windows 觀察到各房實際 UDP 綁定的時間為準。舊版啟動器搭配此指令時，仍會在啟動前重驗，並在收尾核對實際綁定。

正常封存並停止後，指令會按就緒檔核對各端點的實際 UDP 綁定時間。每個端點須在其最早一組監聽報告完成後的 30 分鐘內綁定。若遊戲啟動期間超出期限，指令會在收尾回報該房未通過。要讓戰後驗收核對這次啟動，可加 `--start-receipt C:\VRCommand\venue-start.json`。核對通過才會輸出回條，保存最後重驗時間，以及預檢、就緒檔與結束檔的 SHA-256。請保留三份原檔及雙端報告。 [封存核對](EXTERNAL_CLIENTS.md#核對-windows-五房啟動回條)

### 重跑五房視窗驗收

在 Windows 使用解壓後的伺服器包及管理包，指定新的本機測試目錄。`--topology Independent` 驗證五個伺服器，`--topology Linked` 驗證一個涵蓋五房的伺服器。`--players-per-room 5` 會啟動 25 個同機 Windows 模擬端。

```powershell
python scripts/check-server-venue-gui.py <伺服器包目錄> --control-package <管理包目錄> --runtime-root "$env:LOCALAPPDATA/VrCommand/VenueGuiChecks" --topology Linked --players-per-room 5
```

1. 測試程式會建立隔離管理實例及第四版啟動計畫，再開啟批次視窗。按 Enter 核對清單，確認所有房間、場次與 UDP 埠，勾選來源紀錄，按 Alt+S。將 `{"topology":"Linked"}` 或 `{"topology":"Independent"}` 存為本輪輸出目錄的 `preview.review.json`。
2. 測試程式配票並透過管理 API 開始、結束場次。畫面顯示「全館任務已封存並停止」後關閉視窗，確認視窗消失，再將 `{"closed":true}` 存為同一目錄的 `closed.review.json`。
3. 查看 `checks.json`、戰績 CSV 與 `cleanup.json`。驗收核對原伺服器公告的端點、每席結果回條，以及戰鬥和世界日誌的封存邊界。`runtime-snapshot` 包含本輪隔離實例資料，保留在本機。

### 手動建立及執行場館計畫

```json
{
  "version": 4,
  "controlInstance": "C:\\VRCommand\\control\\control-instance.json",
  "topology": "Independent",
  "address": "192.168.1.100",
  "listenAddress": "192.168.1.100",
  "servers": [
    {"roomIds": [1], "sessionId": "11111111-1111-4111-8111-111111111111", "sessionSequence": 1, "missionId": "aaaa0000-0000-4000-8000-000000000001", "port": 7771},
    {"roomIds": [2], "sessionId": "22222222-2222-4222-8222-222222222222", "sessionSequence": 1, "missionId": "aaaa0000-0000-4000-8000-000000000001", "port": 7772},
    {"roomIds": [3], "sessionId": "33333333-3333-4333-8333-333333333333", "sessionSequence": 1, "missionId": "aaaa0000-0000-4000-8000-000000000001", "port": 7773},
    {"roomIds": [4], "sessionId": "44444444-4444-4444-8444-444444444444", "sessionSequence": 1, "missionId": "aaaa0000-0000-4000-8000-000000000001", "port": 7774},
    {"roomIds": [5], "sessionId": "55555555-5555-4555-8555-555555555555", "sessionSequence": 1, "missionId": "aaaa0000-0000-4000-8000-000000000001", "port": 7775}
  ]
}
```

換成實際位址、UDP 埠及同一次預覽回傳的場次 ID、序號與任務版本 ID。合併模式使用 `Linked`，`servers` 只有一筆，該筆的 `roomIds` 為 `[1,2,3,4,5]`。同機排演可以將兩個位址都設為 `127.0.0.1`。MR 場次仍須先由主控完成原房間校正鎖定。既有第二、三版計畫沿用逐場登記時的序號核對。既有第一版手動計畫沿用原房間、場次與 UDP 核對。

```powershell
& .\Launch-Server.exe --venue-run 'C:\VRCommand\venue-plan.json' `
  --work 'C:\VRCommand\run-01' --seconds 3600 `
  --ready-report 'C:\VRCommand\venue-ready-01.json' --report 'C:\VRCommand\venue-result-01.json'
```

啟動前會核對全館原場次、房號、校正鎖定及本機 UDP 埠，並取得全部原場次的本機啟動鎖。等 `venue-ready` 報告出現，確認各房原場次、來源、公告及 Windows 觀察到的 UDP 綁定，再由控制台配票和開始。獨立場的房控可以各自操作，主控也能沿用原全館開始及結束。

啟動器 1.10 的批次功能需搭配控制台 0.31.100 或以上的管理包。它等所有原遊戲程序與 UDP 綁定確認後，才送出全館端點。管理服務以同一筆資料庫交易寫入全部端點。若任一筆寫入失敗，整批端點都不會出現在控制台。已附掛的場次與錄製仍可供主控辨識及收尾。

終止報告的 `endpointPublication` 會記錄 `not-attempted`、`unconfirmed` 或 `confirmed`。若回條未確認，請先在管理服務核對原場次與端點再處理，因為管理服務可能已提交而啟動器未收到回應。配票仍以全館就緒檔為準。

第四版報告另記錄 `venueLaunchId`、`sourceAttachment` 與失敗原因。若收到 `rejected`，可重新讀取原場次並下載計畫。若是 `unconfirmed`，先由主控核對原場次是否已登記。整批來源登記後才發生的遊戲程序或 UDP 問題，仍沿用管理端辨識原來源與收尾的流程。

啟動器 1.16 遇到暫時性的來源登記或端點公告回應錯誤時，會在原程序仍可用的條件下重送一次原請求。管理服務使用相同批次與來源回傳已保存的結果。啟動器核對回條及 Windows UDP 綁定後才產生就緒檔。終止報告的 `sourceAttachmentRetried` 及 `endpointPublicationRetried` 可核對是否重送。若重送後仍是 `unconfirmed`，由主控核對管理端是否已登記來源或端點。

### 核對未確認的啟動報告

以主控登入管理包 0.31.176，在「房間與場次」展開「核對全館伺服器就緒」。選取 Windows 啟動器產生的 `venue-ready` JSON，再按「核對原場次」。管理服務會逐組核對原場次、來源識別、公告 IPv4、UDP 埠及近期快照。五房合併場會顯示同一組來源及端點。結果是按下核對時的取樣。玩家的入場、姿態及開場條件仍由原名冊及場次控制檢查。

同一面板也接受尚未產生就緒檔且來源登記或端點公告為 `unconfirmed` 的第四版結果 JSON。

管理台 0.31.177 核對到相符的管理實例、原遊戲來源及公告端點時，會在結果下方提供各房「查看名冊」。五房合併場可直接選擇其中一房，開啟同一原場次並套用房間篩選。點選時會再讀取原場次，若原場次已結束或來源不符，請重新核對就緒檔。

管理台 0.31.178 在準備中的原場次旁顯示各房席號及最新姿態狀態，包含未編列、等候入場同步、姿態未就緒、合成姿態及追蹤姿態。畫面沿用房間開場狀態的資料與有效期限。快照過期或原場次與端點變更時，席位狀態會撤下。全館開始與追蹤政策仍在「全館場次控制」確認。

管理台 0.31.180 將面板改為「核對全館啟動與封存」。第四版計畫正常結束後，選取原 `venue-sealed-stopped` JSON。管理服務會逐組核對原啟動批次、場次、遊戲來源，以及戰鬥和世界回放各自的最後封存序號。結果會指出相符、尚未完成雙封存或來源與序號不符的房間。玩家戰績回條仍可在全館結算查看。 [戰績回條](REPORTS.md)

管理台 0.31.181 在管理實例相符且原場次雙封存通過後，提供「回放房間」按鈕。五房合併會在同一份原錄製中選取指定房間，獨立房間會開啟各自的原錄製。觀戰頁在播放前重新核對場次、來源、房間與世界封存尾端。房間之後開了新任務，這個按鈕仍指向原場次。

管理台 0.31.182 若確認五個獨立場次來自同一筆全館結束命令，從結束報告開啟回放後也可暫停並對齊同批房間。選擇原擷取時間，或在任務開始後選擇任務活動時間，再按「對齊房間」。合併場可直接切換同一錄製中的房間。 [對齊回放](WORLD_RECORDING.md)

管理台 0.31.183 核對到原全館結束批次後，顯示「查看原批次戰績與回條」。按下會重新讀取該批次，核對場次、房間與錄製尾端，然後在「全館收尾」選取原批次。獨立與合併模式都可使用，逐房個別結束的場次仍可由原回放入口開啟。

瀏覽器在本機讀取報告。送給管理服務的資料只有管理實例、原批次與場次識別、房間、來源識別，以及依報告所需的 UDP 綁定或封存序號。管理包會拒絕其他實例的報告。若管理服務從原始碼啟動而未設定 `ControlInstanceId`，畫面會標明只按原場次識別比對。

畫面逐場顯示取樣時的階段、原來源及端點狀態。若綁定為 `0.0.0.0`，報告可用來核對埠號，實際公告位址仍取自管理端。近期快照只反映管理服務收到的紀錄。核對只讀取資料，操作員仍由原流程處理場次及票券。

若全館就緒前有程序啟動失敗，本次啟動器會停止自己已建立的遊戲程序。已附掛的場次和錄製留在管理端，由主控依原流程結束。全館就緒後，各場分別等雙封存與 36 秒保留期，正常收尾後由原啟動器停止各自的子程序。若其中一場失敗，其他已就緒場次仍各自收尾。最終報告的 `servers[].result` 保留逐場退出與封存結果，全部場次均成功時才回報 `venue-sealed-stopped`。可加 `--peer-diagnostics on` 為這次所有子程序啟用原來源診斷。

## 遊戲主機連到遠端管理 HTTPS

遊戲主機與管理主機分開時，啟動器 1.11 起可用個別場次 CLI。啟動器 1.12 也可用圖形介面與五房批次。個別場次設定將管理員提供的 HTTPS 原點及葉憑證 SHA-256 指紋填入私人檔案。原點使用小寫 DNS 名稱或正規 IPv4，結尾不加斜線。使用 443 時可省略埠號。指紋為 DER 葉憑證雜湊的小寫 64 位十六進位字串。

```json
{
  "role": "Server",
  "managementApiUrl": "https://control.venue.example:8443",
  "managementCertificateSha256": "填入管理員另外提供的葉憑證SHA-256",
  "gameServerKey": "填入GameServer金鑰",
  "sessionId": "填入Preparing場次UUID",
  "address": "192.168.50.20",
  "listenAddress": "192.168.50.20",
  "port": 7777
}
```

透過既有 `Launch-Server.exe --run` 啟動。遊戲主機只需要 `GameServer` 金鑰。HTTPS 管理請求與 WSS 世界串流核對同一張當前有效的葉憑證，遊戲管理 HTTP 請求遇到轉址會停止。這個部署使用設定中的明確憑證信任，管理員應另外交付指紋。更新站台憑證前先完成場次封存，再更新遊戲主機的設定。房控瀏覽器仍使用一般 HTTPS 信任鏈。 [管理服務設定](WINDOWS_CONTROL_PACKAGE.md#啟用場館-https) · [Unity 憑證驗證](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Networking.CertificateHandler.ValidateCertificate.html)

### 建立遊戲主機的 HTTPS 連線設定

在遊戲主機的私人資料夾建立 `control-instance.json`。管理員從原管理實例提供 `instanceId`、HTTPS 原點、葉憑證指紋及單一 `GameServer` 金鑰。待開清單及啟動器會用 HTTPS 核對該站台和角色。這份設定只需交付遊戲主機。

```json
{
  "schemaVersion": 1,
  "kind": "VrCommand-RemoteGameServer",
  "instanceId": "填入原管理實例的UUID",
  "managementApiUrl": "https://control.venue.example:8443",
  "managementCertificateSha256": "填入葉憑證SHA-256的小寫十六進位字串",
  "gameServerKey": "填入GameServer金鑰"
}
```

個別房間可直接在啟動器載入此檔、選擇場次，再填遊戲 UDP 位址與埠。五房批次則在控制台的啟動計畫填這份檔案在遊戲主機上的完整路徑，下載後用「五房批次啟動」、`--venue-check` 或 `--venue-run` 開啟。計畫和公開結果只使用路徑與場次資訊。更換 HTTPS 原點、金鑰或指紋後，重新載入場次或重新核對計畫再啟動。 [批次操作](#依場館計畫批次啟動)

## 管理服務短暫中斷

2026-11-09 主包 `artifacts/server-packages/windows-server-0.47.0-launcher1.5-win-x64.zip`，83,466,340 bytes，SHA-256 `89cdef1e26468a25cd4a145a817f8b5fe11fddbf2ecd834cfdf3f4394b13a891`。解壓後逐檔核對 328 筆。遊戲執行內容使用 0.47.0 的原建置，配套管理包為控制台 0.31.14。 [實測結果](PROGRESS.md#2026-11-09-遊戲伺服器保留原場次等待管理恢復)

就緒後，遊戲伺服器啟動器遇到暫時性 HTTP 讀取錯誤時，會保留自己已啟動的遊戲程序。請以相同 IPv4 與埠號重新啟動原管理實例。啟動器給予 15 秒恢復窗口，自首筆失敗的讀取開始計算，回應到達後重新核對原場次、戰鬥來源與單調增加的序號。既有的每次 HTTP 讀取期限也適用於進行中的讀取。

恢復只適用於可判定的暫時性連線錯誤或 HTTP 502、503、504。認證或權限錯誤、找不到原場次、資料不符與期限到達時，啟動器會停止自己的遊戲程序並留下未完成報告。遊戲引擎依管理可用狀態處理暫停與續行。End 後的雙封存檢查、原玩家戰績與 36 秒保留仍由各自的既有流程處理。

結果報告的 `managementRecovery` 提供 `outages`、`recoveries` 及 `longestMilliseconds`，可核對啟動器觀察到的讀取中斷。玩家戰績送達應另對原伺服器和玩家日誌。 [封存戰績核對](EXTERNAL_CLIENTS.md#核對封存戰績與-udp-來源)

同機可用以下命令排演五房獨立場次。改成 `--topology linked` 可排演一個遊戲伺服器同時負責五房。桌面玩家預設每房一位，`--players-per-room 5` 可同時連上 25 個桌面客戶端。測試在新資料夾建立管理實例，只中斷自己啟動的管理 API。每輪核對原連線、全館結束命令、雙封存、戰績確認、完整回放及程序清理。啟動前會先讀取各接收入站連線的程式在本機的防火牆設定。 [無人值守的 Windows 測試](#無人值守的-windows-測試)

選加 `--observer-console C:\packages\VrCommand-ControlServer\Runtime\wwwroot\console` 可在背景以 Chromium 開啟指定發布版的第 4 房觀戰，查驗管理 API 重啟後仍是同一錄製、房間與鏡頭。瀏覽器直接向受測實例請求 API，指定目錄供應頁面與其他靜態檔。

```powershell
python .\scripts\check-packaged-management-restart.py `
  --control-package 'C:\packages\VrCommand-ControlServer' `
  --server-package 'C:\packages\VrCommand-GameServer' `
  --runtime-root (Join-Path $env:LOCALAPPDATA 'vr-restart-checks') `
  --expect recover --topology independent --players-per-room 5
```

## 遊戲程序退出後補送錄製

Windows 錄製補送工具 0.1.0 使用原遊戲伺服器工作資料夾中的 `server-config.json`，以及設定指向的 `telemetry` 下同一場次的 `.journal` 與 `.worldlog`。遊戲程序退出後，先在原管理實例結束該場次並釋放房間，再解壓補送工具。原設定檔含該伺服器的 GameServer 金鑰，請與日誌一併私下保管。

```powershell
.\Recover-Recording.exe --recover-server 'C:\private\server-work\server-config.json' `
  --work 'C:\private\recovered-room1'
```

工作資料夾必須是新路徑，上層須已存在。工具在兩份原檔保持唯讀獨占的期間建立工作副本，核對原場次、原錄製來源及原管理端接受序號後補送。獨立五房可分別處理受影響的場次，合併場只需處理其原伺服器一次。

退出碼 0 會在工作資料夾留下 `recovery.json`，列出兩份日誌補送前後的接受序號與各自封存狀態。若原日誌未完成結尾，主控台可播放已保存片段，場次仍顯示未完整封存。只在有原完成紀錄且服務確認精確尾端時封存。補送之後可另行開新場次。 [回放保存片段](WORLD_RECORDING.md#回放未封存的已保存片段)

退出碼 1 會在終端顯示原因，並保留可用的工作副本。若戰鬥已補送、世界暫時失聯，待服務恢復後用同一原設定及原日誌、另開工作資料夾重試。伺服器會核對已接受的原資料，再接續未接受部分。損壞或仍由原程序鎖住的日誌需先排除問題，工具不截斷原檔。

## 本機 UDP 綁定確認

2026-11-06 主包為 `artifacts/server-packages/windows-server-0.41.2-launcher1.3-win-x64.zip`，82,676,182 bytes，SHA256 `0f5448df34c5857286d8e29d4feb497fd72961685359033e65b926747fb3555c`。清單有 311 筆，內含 304 份與啟動器 1.2 相同的遊戲執行檔及相依檔。

啟動器 1.3 在公告場次連線設定之前，向 Windows 核對本次遊戲子程序的 PID、本機 IPv4 與 UDP 埠。明確綁定時必須完全相符，設定 `0.0.0.0` 時則核對萬用位址。等待綁定仍受原 90 秒就緒期限限制。

CLI 的就緒及結果檔新增 `udpBinding`，含 `processId`、`address`、`port` 及 `observedAtUtc`。原就緒檔的 `address` 仍表示玩家要連到的公告地址。WinForms 運行狀態會顯示啟動時已核對的本機 UDP 位址。Windows 的紀錄用於確認啟動時的綁定，跨機可達性另以第二台電腦入場驗證。 [Microsoft Windows UDP 端點表](https://learn.microsoft.com/en-us/windows/win32/api/udpmib/ns-udpmib-mib_udprow_owner_pid)

遊戲啟動前可先用 PowerShell 在規劃的同一個位址與埠測試 UDP 往返。探測程序退出後再交由遊戲伺服器綁定。 [兩端探測操作](EXTERNAL_CLIENTS.md#開場前核對兩端-udp)

私有乙太網路位址與預設 loopback 的解壓包分別通過 374 及 124 項整合檢查。兩次都另有一場核對 `0.0.0.0`，並保留不同的玩家公告位址。 [驗證紀錄](PROGRESS.md#2026-11-06-遊戲伺服器公告前的-udp-綁定核對)

## 跨機來源診斷

啟動器 1.7 可在 WinForms 選定場次並填好 UDP 位址與埠後，勾選「記錄本次玩家連線來源（場館驗收）」，再啟動伺服器。選項預設關閉，運行期間鎖定，收尾後會取消勾選。CLI 仍使用 `--peer-diagnostics on`。就緒及結果檔的 `peerDiagnosticsEnabled` 會顯示原遊戲子程序啟動時的選擇。結果檔的 `workDirectory` 可定位本次的 `server.log`。 [戰績與來源核對](EXTERNAL_CLIENTS.md#核對封存戰績與-udp-來源)

2026-11-06 新版 `windows-server-0.41.2-win-x64.zip` 為 82,674,494 bytes，SHA256 `a8e4a529adbe744cdc11450dae209795adbfe52be0581e0ed652169220a86646`，包含 311 筆檔案清單及清單本身。

伺服器啟動器 1.2 搭配遊戲 0.41.2，可在一般 CLI 啟動參數後加入 `--peer-diagnostics on`。實際的 Windows 遊戲伺服器在核准的玩家連上後，由 Unity Transport 讀取來源位址與埠，記錄於自己的 `server.log`。可用同一連線編號核對玩家入場及伺服器的戰績確認回條。來源埠是玩家的 UDP 埠，通常會與伺服器的公告埠不同。

每次啟動最多記錄 256 筆，超出時記錄一筆 `VR_SERVER_PEER_LIMIT`。若當下無法讀取來源，該筆記為 `unavailable`。預設 CLI、WinForms、頭盔與玩家程式均不開啟診斷。這些記錄含來源位址，請保留在私人資料夾。地址表示伺服器這一端實際觀察的網路來源，經 NAT 時可能是轉譯後位址。 [第二台電腦的驗收步驟](EXTERNAL_CLIENTS.md#第二台電腦的驗收步驟)

在三包整合測試命令加上 `--peer-diagnostics`，可在 Linked 核對來源與原玩家回條，同時驗證獨立房間的預設流程沒有來源記錄。

## 三個可攜包整合驗證

環境驗收可加 `--check-venue-environment --check-venue-environment-ui`。獨立與合併場均送出暴風雨夜間及晴朗白天兩批設定，核對各場來源確認。瀏覽器另外核對最新一批的五房狀態、原指令序號及第 4 房俯視快照。 [環境核對](ENVIRONMENT.md#核對最近一批環境指令)

2026-11-06 使用既有管理包 0.31.4、遊戲伺服器包 0.41.1 v2 與玩家包 0.41.1 v2 完成同機測試。五個獨立房間先各以一個伺服器運行，之後改用一個伺服器執行 Linked。每種模式各有 25 個背景玩家同時入場，每房五席。遊戲 UDP 綁定同一台電腦的乙太網路 IPv4，管理服務保留在 loopback。10 份整房 ZIP 直接取自管理包，由 `Launch-Player.exe` 使用對應席位檔。 [整房配票操作](EXTERNAL_CLIENTS.md#按房間下載連線檔)

319 項通過，六個正常場次共 812 幀完整回放、50 份玩家戰績及 6 份 CSV。測試核對戰績的原 admission、戰鬥與世界封存，以及伺服器對每條原連線的確認回條。這是同機 Simulation 的 CLI 流程，跨機、WinForms 多人操作、頭盔與 25 位真人待驗。

在測試機將下列三個資料夾與 IPv4 換成實際解壓路徑及本機私有位址。省略最後兩個選項會執行原 loopback 驗證，每種模式共五個玩家。

```powershell
python scripts/check-server-package.py <VRCommand-GameServer> `
  --control-package <VRCommand-ControlServer> `
  --runtime-root "$env:LOCALAPPDATA/VrCommand/RuntimeEvidence" `
  --player-package <VRCommand-Player> --game-address 192.168.1.100
```

搭配控制台 0.31.18，可加上 `--check-room-reports`。測試會對照同一個五房連線場次的封存全場 CSV、五份分房 CSV 和戰績 ZIP，並確認房控指定別房時收到 403。再加 `--check-room-combat` 可讓兩種模式的每位原玩家都實際收到敵軍傷害，核對敵軍射線、同房傷害事件、逐格統計與最終戰績。 [分房匯出](REPORTS.md#五房分房匯出)

搭配管理包 0.31.46，可加上 `--prepare-independent-set --check-independent-room-missions`。測試用一筆 API 請求為五個獨立房指定不同的 VR 任務。逐房核對已進入 Running 的原遊戲快照及標頭，包括任務時間、天氣、日夜、雷電、敵軍策略與數量，以及掩體座標與角度。接著按原流程核對回放、雙封存及原玩家戰績。 [逐房操作](MISSION_VERSIONS.md#逐房指定任務版本)

搭配管理包 0.31.134，可再加 `--check-independent-room-layouts-ui`。Chromium 會從控制台確認五張平面圖及各房保存版本，送出原五房建立請求。測試沿用該次回條及場次 ID，核對 Windows 遊戲實際載入的配置。

搭配管理包 0.31.161 或更新版，可在三包命令加上 `--prepare-independent-set --check-venue-begin --check-venue-participation-gate --check-venue-end --check-venue-replay-ui --check-venue-opening-replay`。五房獨立與合併各啟動 25 個同機 Windows 玩家程序。原遊戲程序停止後，工具從各場封存世界日誌找出第一個已套用原開場指令的有效執行畫格，再以 Chromium 核對兩個回放按鈕、原場次、房間與鏡頭。 [回放操作](SESSION_CLOSURE.md#比較準備與執行畫格)

要以同機 Windows 套件排演 5 人或 10 人場測，在三包命令加入 `--peer-diagnostics --field-evidence --venue-field-evidence --check-venue-end --field-players-per-room 1` 或將最後的數字改成 `2`。工具從房間連線 ZIP 啟動指定席數，對兩種模式核對同次原封存與戰績。加上 `--check-venue-begin` 會檢查未滿 25 席時全員參與閘門拒絕開始，接著以一般全館開始執行該階段。 [現場清單](EXTERNAL_CLIENTS.md#分階段驗收-5-人與-10-人)

Quest 小批次驗證可在三包命令加上 `--check-vr-venue-tickets --check-quest-vr-partial-map`。獨立與合併的名冊各登記 15 個 Quest 3 席位與 10 個 VIVE XR 席位。工具從原控制台 ZIP 測試錯列 VIVE 的拒絕，再把五份指定設定送至模擬 ADB。MR 可省略 `--player-package`，保留本機 `--game-address`，改用 `--mr-venue-bundle-only --check-mapped-quest`，核對完整清單與五席清單各自使用的原鎖定校正檔。 [小批次操作](QUEST3.md#部署指定的-quest-席位)

在批次 VR 驗證加入 `--check-quest-deployment-retry`，可讓模擬 ADB 在第一席送出啟動後中斷，再用原報告和原清單補跑其餘席位。`--mixed-venue-bundle-only` 也會核對這個流程及 MR 校正檔。 [重試操作](QUEST3.md#從原部署報告重試未完成席位)

批次 VR 驗證可另加 `--check-quest-tracking-wait`。用原控制台部署 ZIP 等候追蹤就緒，驗證較新的原生保存格仍將 25 個同機桌面玩家標為合成姿態，且逾時不改變任何場次序號。 [現場操作](QUEST3.md#等候指定席位同時追蹤就緒)

五房 VR 追蹤驗證可在上述小批次命令再加 `--check-venue-openxr --openxr-mock-pose-dll '<測試 DLL 路徑>' --check-room-readiness --check-venue-begin --check-venue-end --check-room-reports --check-venue-reports`。兩種模式各以一個 Windows OpenXR 模擬玩家和 24 個桌面玩家同時入場。工具沿用控制台下載的原 ZIP，核對第 5 房第 2 席的就緒、中斷及恢復，並保存其餘 24 席的狀態與原場次回放。VIVE XR 是該席在名冊上的裝置分類，驗證使用 Unity Mock Runtime。 [測試 DLL 建置](WINDOWS_PLAYER_PACKAGE.md#本機追蹤整合驗證)

使用管理包 0.31.72 可再加 `--check-venue-live-tracking`，在上述實際來源的四個取樣點比對主控 API 的 `venueTracking`，並核對房控權限。 [執行中五房追蹤](PLAYER_READINESS.md#執行中五房追蹤總覽)

使用管理包 0.31.87 並加上 `--check-venue-pose-review`，可從實際遊戲來源以第 5 房房控開啟第 2 席的原姿態中斷畫格，再核對回到同房同鏡頭的即時畫面。工具會將兩格與場次封存後的原錄製比對。 [房卡操作](PLAYER_READINESS.md#從房卡查看姿態中斷快照)

加上 `--check-venue-openxr-reconnect` 可在兩種拓撲各中斷第 5 房第 2 席的本機 UDP 轉送。此測試需支援 Vive Menu 及扳機的測試 DLL，請省略 `--check-windows-venue-staging` 與 `--check-room-combat`。使用原 ZIP 的測試副本設定轉送端點，切回原伺服器時由房控重發同一入場的票券。測試核對原 OpenXR 程序、重連前的單發耗彈、恢復的有效追蹤、封存回放中的其餘 24 席，以及重連後的戰績確認。 [五房重連操作](QUEST_RECONNECT.md#五房-udp-中斷複驗)

同時傳入 `--peer-diagnostics --field-evidence --venue-field-evidence --check-venue-end`，可用上述原程序及伺服器日誌複驗場館 ZIP 的重連歷程。這場排演的 OpenXR 初始啟動埠屬於本機轉送，姿態由原生回放核對，離線檢查使用舊連線釋放、來源與最終戰績。 [離線重連驗收](EXTERNAL_CLIENTS.md#核對原程序的重連歷程)

搭配控制台 0.31.10，可加上 `--check-interrupted-replay`。測試在另一個獨立場次錄到敵軍實際傷害後終止該次啟動器，核對原遊戲程序退出，再檢查保存片段的尾端、戰績及未封存狀態。 [中斷場次回放](WORLD_RECORDING.md#回放未封存的已保存片段)

2026-11-02 本輪同源Unity0.41.1／code52／NGO29／242真正Editor、4ebd雙平台：新server主包 `windows-server-0.41.1-v2-win-x64.zip`，**82,673,732 bytes／SHA256 `ca285a42e0c22bdde17f62eb6dd8a65523c9d3a5cae19a33cad41636899fb368`**、311 manifest／ZIP312。啟動器1.1來源fb57807d...不變但重新編譯binary不同，runtime逐byte同v1；v1與所有舊包保持。包說明改引用Runtime/build-receipt.json，不再寫死Unity0.39。

實際F解壓包106項／623全回放、五房後Linked／10原結果與CSV／雙seal／原server ACK／無active成功，parent-death是另留的未封存反例；closure UI新增Running與Archived兩PNG、精確原session/stream/final world，nativeUI9＋2＝11，非雲端CI檔。

**實際WinForms流程已成功**（run-3d179468...／真正handle64853 exit0）：直接輸入既有實例路徑、載入兩房清單、明確選房1完整UUID／任務版本、設定127.0.0.1及本次UDP、按啟動，fixture API Begin後原來源Running/tick>0/observed fence，再API End、雙seal保留36秒、原child停止、畫面「任務已封存並停止」後按關閉。原實例marker／三key檔hash不變；GUI exit0／closed journal精確ACK尾界／cleanup空、C14→F raw同hash。名冊只有fixture roster一位，**未啟動玩家client**；不宣稱玩家送達／操作／LAN／頭盔。此次沒有測系統「選擇檔案」視窗、GUI建立key或透過GUI按Begin/End；Begin/End仍是fixture正常API。

使用者自行關PickerHost後重驗，舊PickerHost失敗保持。首新GUI run-e615...已選對並啟動，但fixture空名冊Begin被原API409拒絕、helper finally清理後C9→F同hash，仍failed；只修fixture先加一位明確roster，不改產品／API／啟動器或Begin原規則，py_compile與新真GUI成功。期間自動化bounds變更後重新選取/擷取再操作，沒有繞過任何安全提示。上述GUI不代表舊Windows startup／31／world371／F吞吐修復，完整11active。

以下為歷史交付與當時驗證狀態；目前版本與新GUI結果以上段為準。

前主包`windows-server-0.40.0-win-x64.zip`，**82,672,917 bytes／SHA256 `642e5307cf3d62af7b136d9baaca06c2d9cd9c3bd1ed66c7d4e915803a7f8710`**，原啟動器1.1／source fb57807d...及新Unity0.40 runtime／6098b485...，311 manifest／ZIP312。106項實際包驗證／725回放／原結果CSV及cleanup成功，原生自動化25端與普通入場另見[DESKTOP_EXERCISE](DESKTOP_EXERCISE.md)。不是新的Windows launcher GUI、LAN／25真人或頭盔驗收。

前版[啟動器1.1／房間任務清單](SERVER_CATALOG.md)的`windows-server-0.39.0-v5-win-x64.zip`保持，82,669,350 bytes／SHA3eef78fbe8319e366afa80cdfad31557bf42fb8bc3992402b6f252525e2857a2。CLI38／Framework model26／原生106成功，完整GUI開場仍被PickerHost擋住；以下v3與舊failed證據保留，不能只看同一Unity版本選包。

可搭配API0.31.0／控制台0.31.1的[任務收尾](SESSION_CLOSURE.md)顯示雙封存與保留已確認End；原server v3 runtime／SHA保持，不需要因這個唯讀UI更新Unity或頭盔。

`Launch-Server.exe`將既有Unity Windows播放器以獨立Server模式啟動。操作員只需Windows x64與.NET Framework4.8，不需要Python、Unity Editor或.NET SDK。管理網站用[管理服務包](WINDOWS_CONTROL_PACKAGE.md)，玩家使用[玩家包](WINDOWS_PLAYER_PACKAGE.md)，三者分開運行。

原PC原型v3主包為`artifacts/server-packages/windows-server-0.39.0-v3-win-x64.zip`，**82,664,818 bytes**、SHA256 **`6cecfbeeffba1277000f93bc168c4ac387b825c34b73142628098dba28f67500`**，311個manifest檔案／ZIP312含manifest。v1、v2候選原件保留。沿用Unity **0.39.0／code49／NGO29／e0d60e4ed6cefe5cd885e6aabe1621939da945ce00d56b3ed8820c0aed4db879**，API/UI仍0.31.0，沒有修改Unity來源、重建Editor／APK或更新原場景／prefab ID。

## VR 場次使用實機追蹤

場館使用頭盔進行 VR 驗收時，在單場或「五房批次啟動」視窗勾選「VR 房間只接受追蹤姿態」。啟動器 1.24 會用 `GameServer` 來源登記該場次。遊戲伺服器 0.50.8 起，只有 `Tracked` 姿態能取得參戰狀態；玩家可用主控台的席位狀態確認追蹤。單房和五房開啟此模式時，請搭配原發行報告部署同版頭盔程式。 [Quest 單房流程](QUEST3.md#單房實機追蹤驗收)

單場 `--run` 或五房 `--venue-run` 可加 `--tracked-vr on`。透過 `start-verified-venue.py` 啟動五房時加 `--tracked-vr`。有需保留的 UDP 與戰績連線證據時，可同時啟用來源診斷。一般桌面排演可沿用預設的 `Simulation`。MR 場次採用 `GameServer`，並依原房間校正與追蹤規則開場。

### 重跑五房追蹤來源驗證

用解壓後的 Windows 0.50.8 伺服器包及支援第四版計畫的管理包，在同一台電腦驗證 `GameServer` 來源及開場條件。測試只開本機迴環位址上的伺服器，會先驗證獨立五房，再驗證五房合併。每輪用空名冊驗證全館追蹤開場被拒，然後結束場次、核對逐場封存及完整回放。

```powershell
python scripts/check-server-package.py '<解壓後的 VRCommand-GameServer>' `
  --control-package '<解壓後的 VRCommand-ControlServer>' `
  --runtime-root "$env:LOCALAPPDATA/VrCommand/TrackedVenueChecks" --tracked-vr-venue-only
```

### 無人值守的 Windows 測試

Windows 依執行檔的完整路徑套用程式規則。即使只有同機測試，新解壓路徑的 `vrcommand.exe` 也可能觸發入站連線提示。自動測試用 `127.0.0.1`，並先核對實際 EXE 路徑在目前網路設定檔的既有規則。新路徑尚未確認時，可先跑建置、套件驗證及使用測試替身的檢查。 [Microsoft Windows 防火牆規則](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/rules)

桌面場館、Unity 啟動與入場測試，以及會啟動原生遊戲的套件和 GUI 驗證，會在開啟遊戲或啟動器前，自動核對執行檔路徑與所有啟用中的防火牆設定檔。`start-verified-venue.py` 在啟動五房前會檢查解壓包內的 `Launch-Server.exe` 與 `Runtime/VrCommand.exe`。離線 `--verify-only` 可直接執行。Unity Editor 建置、Quest 的 ADB 部署及擷取、Quest 單席與五房 UDP 探測也有啟動前檢查。使用 PowerShell 接收入站 UDP 的場館探測會檢查該 PowerShell 執行檔。

Unity 冒煙和入場測試會同時核對玩家程式與管理 API 的啟動程式。若 `dotnet.exe` 的路徑未通過查核，可以給 `smoke-unity-player.py` 和 `check-unity-admission.py` 加上 `--api-exe`，指定已通過查核的管理包 `Runtime/VrCommand.Api.exe`。HTTP、回放及管理服務程序測試可使用 `VR_COMMAND_API_EXE` 指向同一執行檔。測試用獨立資料與 `127.0.0.1`。

同機 UDP 轉送及管理 API 故障測試也會在啟動前檢查實際執行的 `python.exe`。`start-local.ps1` 先完成 Release 建置，再查核 Windows 管理程式。桌面場館、練習模式與操作員工具可用 `--api-exe` 指向已通過查核的管理包 `Runtime/VrCommand.Api.exe`。

直接執行 `tests/browser/check.cjs` 或 `tests/browser/check-clock-native.cjs` 時，也會先查核負責測試連接埠的 Node 及實際啟動管理服務的 `dotnet.exe`。若要在新解壓路徑下測試管理服務，可以使用 [Windows 本機 IPC 測試流程](PLAYER_READINESS.md#windows-原生回歸)。本機 IPC 方式會檢查管理服務的 TCP 監聽與 UDP 端點均為零，迴環轉送使用已通過查核的 Python。

`tests/browser/check-external-native.cjs` 在開啟瀏覽器及送出操作前，會核對這一輪實際使用的 `VrCommand.exe`。執行 `--launcher-status` 時也會核對負責 UDP 的 Node。管理服務 HTTPS 測試會核對負責連接埠的 Python，並查核測試選用的伺服器啟動器。管理服務重新啟動測試同樣會核對伺服器啟動器。

直接執行 `check-lan-udp.ps1` 的 `Listen` 或 `Probe` 時，腳本在繫結埠前會檢查目前的 PowerShell 程序。配對報告及產生測試金鑰仍可離線執行。原生姿態測試、伺服器場次目錄測試和硬體模擬整合測試也會查核各自的迴環接收程式。硬體模擬的兩支整合測試皆可用 `--api-exe` 指向已通過查核的管理包。

直接執行 `hardware-mock-peer.py` 也會在開始接收迴環 TCP 連線前核對 Python。自動執行 Windows 原生連線測試時，優先沿用已通過查核的固定執行檔路徑。解壓到新資料夾後，Windows 會以新路徑個別判定。

若啟用通知的設定檔缺少涵蓋實際 EXE 的入站 TCP 與 UDP 規則，或查核無法完成，工具會在終端機回報並停止啟動。這項檢查只讀取防火牆設定。可用同一支指令檢查其他執行檔的實際路徑。

```powershell
pwsh -NoProfile -NonInteractive -File .\scripts\check-windows-firewall-notifications.ps1 -Executable .\artifacts\desktop\VrCommand.exe
```

要在這台電腦關閉防火牆入站允許視窗，可從系統管理員 PowerShell 一次關閉三種網路設定檔的入站通知，再從有效設定核對 `NotifyOnListen`。若只需處理私人網路，將第一行的 `Domain,Private,Public` 改為 `Private`。 [Microsoft Windows 防火牆命令列設定](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/configure-with-command-line)

```powershell
Set-NetFirewallProfile -Profile Domain,Private,Public -NotifyOnListen False
Get-NetFirewallProfile -PolicyStore ActiveStore |
    Select-Object Name, Enabled, NotifyOnListen, DefaultInboundAction
```

## 操作流程與目前限制

1. 完整解壓管理、伺服器及玩家包。先開管理服務，在網頁控制台建立Preparing VR場次。
2. 開`Launch-Server.exe`，選管理服務原資料夾內的`control-instance.json`，選尚未綁定來源的場次，明確填寫公告IPv4、本機綁定IPv4及UDP埠。預設127.0.0.1只供同機；固定綁定地址須已配置於本機且與公告地址相同，或明確選0.0.0.0綁定。
3. 五個Independent場次各開一個啟動器，使用不同UDP埠；五房Linked場次只需一個。新增場次後重選管理實例可更新列表。
4. 伺服器就緒後，由控制台下載每位玩家的短效連線檔，交給玩家包，再在控制台Begin。此啟動器不領取玩家票券、不建立／改變名冊或代替操作員下Begin／End。
5. 在控制台End後，等待戰鬥與世界雙封存，保留36秒供原玩家接收戰績，再停止自己的Unity程序。這是封存後的OS程序終止，**不是Unity正常退出證明，也不能單憑36秒推定所有玩家已收到戰績**。原始journal與玩家／server回條另驗。

**本輪103項Windows CLI／原生整合通過；新GUI完整選檔／啟動流程未完成驗證。** native視窗可見且欄位／標籤正確，但兩次點擊均被非目標`PickerHost.exe`攔住；activate並重新觀察後的一次重試仍回報`point ... is over PickerHost.exe, not target window Launch-Server.exe`，因此停止UI輸入。自己GUI與API已終止，failed、原snapshot及有限觀察保留。這不是產品選檔成功、Windows安全性或PickerHost根因證明。管理服務包原先已成功的GUI95151不替代本輪伺服器GUI。

啟動器接受尚未綁定戰鬥來源的 Preparing VR 或 MR 場次。就緒前的管理讀取失敗、來源改變、就緒 90 秒逾時，或觀察到 End 後 30 秒仍未雙封存時，啟動器停止自己的子程序並保留不完整結果。GUI「中止」會停止本次子程序。資料預設在 `%LOCALAPPDATA%/VrCommand/GameServers`，結果在 `GameServerReports`。伺服器私鑰保留在包外資料夾。所有寫入程序停止後再備份。 [MR 開場方式](QUEST3.md#主控建立-mr-場次)

## 啟動、來源與停止界線

啟動器核對manifest逐檔大小／SHA與完整檔案集合、拒絕連結／越界／額外檔案；清單不是數位簽章。只接受GameServer角色，Unity設定只帶這個key，不帶Master。GUI讀既有管理實例的JSON，不新增或複製角色金鑰。遠端管理可由CLI的私人七欄JSON明確指定；尚無LAN、TLS或乾淨新機驗證。

每輪使用新的包外資料夾與日誌，核對 Preparing、VR／MR 模式及來源未綁定，再取得以 API 地址及場次命名的本機 mutex。UDP 探查會拒絕啟動前衝突，正式就緒另由原 Unity 程序的綁定與錄製來源確認。

Unity 先核對自己的戰鬥串流識別、來源、接受序號與封存狀態，再啟動伺服器並記下 `VR_NETWORK_STARTED ... started=True ... port=...`。啟動器讀取本次啟動日誌，並透過 API 核對同場次的戰鬥串流和世界錄製來源。VR 實機追蹤與 MR 使用 `GameServer`，一般 VR 排演使用 `Simulation`。核對後以原 GameServer 角色公告連線端點，並比對回條的場次、串流、IPv4 與埠。

Windows子程序以suspended建立，先加入私人kill-on-close Job，再Resume，原生OS handle保留至實際退出。只設定KILL_ON_JOB_CLOSE，沒有改優先序、CPU／記憶體限制或系統設定。已加入Job的父程序被終止後，原Unity handle實際退出；這不是斷電恢復、未落盤queue保障，或建立程序到指派Job之間所有崩潰時點的證明。API雙seal＋36秒留存＋原child終止後，報告才complete；玩家送達欄位明確null。參考[Microsoft Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)與[AssignProcessToJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject)。

## CLI與建置

既有 HTTP 私人設定包含 `role`、`managementApiUrl`、`gameServerKey`、`sessionId`、`address`、`listenAddress` 及 `port`。`role` 須為 `Server`，HTTP 格式為 `http://IPv4:port`。HTTPS 增加 `managementCertificateSha256`。拒絕多餘欄位、Master 或 Room 角色、混淆 IPv4、越界埠及重複的輸出路徑。報告在同目錄完成寫入後以新檔名發布。

```powershell
Launch-Server.exe --run <私人JSON> --work <全新包外資料夾> --seconds 3600 --ready-report <新就緒檔> --report <新結果檔>
Launch-Server.exe --verify package --report <新結果檔>
```

seconds限制60..86400，從就緒後計算；90秒啟動等待分開。結果與就緒路徑必須互異、位於包外及work外。就緒不宣告任務已Running；報告complete也不是玩法或跨機容量驗收。

```powershell
python scripts/package-windows-server.py --stage-root "$env:LOCALAPPDATA/VrCommand/Pkg" --output <新ZIP>
python scripts/check-server-package.py <VRCommand-GameServer> --control-package <VRCommand-ControlServer> --runtime-root "$env:LOCALAPPDATA/VrCommand/RuntimeEvidence"
python -m unittest discover -s tests -p test_server_package.py
```

package沿用原實際Windows build receipt及素材／Transport授權，保留自己launcher來源SHA；原runtime allowlist拒絕私人設定與journal混入。4項Python邊界測試只驗假bytes的完整性／路徑，不能當Unity或GUI執行證據。`check-server-gui.py`只建自己的CLI測試資料／觀察原child，UI輸入另由computer-use完成；本輪它是failed，後補關窗review有界等待只經語法檢查，沒有冒充新GUI通過。

最終103項包含五個獨立server＋五個接收client，之後一個Linked server＋五個接收client；觀察原Begin的Running／tick／observed／原1.5秒來源界線，六場553完整API回放、10份原admission精確結果／CSV、雙seal與closed journal durable尾界及cleanup全部成功。parent-exit第七場刻意殺父程序，自己的Unity被Job收掉、沒有成功final報告，該journal保持未封存，不混入六個正常完成場。每組只在自己的所有writer終止後一次F snapshot，不開保存SQLite。詳見[PROGRESS](PROGRESS.md)。

這些都是同機Simulation，非25位同時操作、跨機、GPU效能、頭盔／MR或硬體廠商整合。完整11項長期目標仍active；原31筆、world371、舊Windows startup及F吞吐問題不因新包成功而改判。

[精確95411a2的CI41335830454](https://github.com/peca12968/vr-command-center/actions/runs/41335830454)完整success：Linux738／459／47、6私有管線、4新Python邊界及素材、78 Node／256 Chromium。console43與control13檔下載digest核對，1112 browser證據與另13 metadata分開。2 Windows skip不當Framework／Unity／GUI證據；本機103與failed GUI維持各自範圍。後補closed-readback僅讀原件，10 CSV及10原network admission／server ACK精確相符，非新live測試。
