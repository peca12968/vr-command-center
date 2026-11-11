# VR/MR 軍事戰鬥系統長期開發

狀態：**開發中／保持 open**。開發根目錄 `F:\Projects\vr-command-center`，先用 Meta Quest 3；使用者目前沒有頭盔，先繼續電腦端。VIVE 的確切型號與接入留待後續。管理原型、Simulation 或 APK 成功均不代表完整交付。

11-10　控制台 0.31.62 可匯出及匯入任務範本。詳見 docs/PROGRESS.md。
11-10　25席追蹤、回看、硬體、敵軍環境、通路、Quest部署。

11-10　OpenXR 中途失去追蹤後沿用原票券與連線復原，實際控制台複驗 78 項通過。詳見 docs/PROGRESS.md。

最新進度（2026-11-10）　Windows OpenXR 模擬追蹤入場 70 項通過，兩份戰績、66 格回放及封存相符。頭盔實機待驗。[開發進度](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-10-windows-openxr-追蹤入場複驗)

最新進度（2026-11-10）　0.49.0 加入 Windows OpenXR 選用啟動。272 項 Editor、23 項玩家包、457 項同機連線核對通過。Quest 開發 APK 已建置，頭盔待驗。[開發進度](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-10-windows-openxr-玩家啟動)

最新進度（2026-11-09）　五房頭盔追蹤新增全 25 席核對，Windows 原生 457 項及 VR／MR 準備場 117 項通過。WinForms 遇 Windows 防火牆提示，實機待驗。[開發進度](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-09-五房頭盔追蹤核對)

## 原始驗收範圍

1. 主控台與五個房間控制，五房可獨立或全部連線同玩。
2. 軍事戰鬥遊戲介面。
3. 依其他公司的連結技術資料整合硬體。
4. 五房總計25名玩家。
5. VR/MR場地的天氣、日夜、雷電控制。
6. 敵軍AI自動攻擊及控制人員設定攻擊方式。
7. 沙包、油桶等環境物件擺設介面。
8. 控制者事先編輯任務名稱、內容與時間，儲存並選取還原條件。
9. 任務執行過程回放。
10. 即時觀戰、上帝視角及位置／角度選取。
11. 彈藥、擊殺、自身損耗、中彈與命中率統計。

詳細階段與每項驗收：[ROADMAP](https://github.com/peca12968/vr-command-center/blob/main/docs/ROADMAP.md)、[REQUIREMENTS](https://github.com/peca12968/vr-command-center/blob/main/docs/REQUIREMENTS.md)；逐輪證據與限制：[PROGRESS](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md)。

## 2026-11-09 UDP 預檢與封存端點核對

場館驗收可選用原 UDP 監聽與探測報告，比對遊戲伺服器原綁定、埠、已收到戰績確認的玩家來源，以及綁定觀察前 30 分鐘的監聽完成時間。獨立五房逐場核對，合併場核對共用端點。 [操作方式](https://github.com/peca12968/vr-command-center/blob/main/docs/EXTERNAL_CLIENTS.md#將-udp-預檢納入封存驗收)

[458 Windows integration checks and evidence](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md)

## 2026-11-09 保存戰鬥事件雙向跳轉

控制台 0.31.51 加入「上一筆事件」與「下一筆事件」。暫停回放時可沿用房間、事件類型及原玩家篩選，從目前格向前或向後找最近的相符保存格。每次查詢最多 2,048 格，控制台在固定保存尾端內接續搜尋。 [操作方式](https://github.com/peca12968/vr-command-center/blob/main/docs/WORLD_RECORDING.md#依房間與種類搜尋戰鬥事件)

[0.31.51 verification and Windows package evidence](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md)

## 2026-11-09 分房觀戰角色與跟隨

控制台 0.31.50 依所選房間篩選角色清單與場景點選。玩家名稱取自該格已接受統計。跟隨目標消失時保留最後視角，等候操作員重新選取。 [觀戰操作](https://github.com/peca12968/vr-command-center/blob/main/docs/WORLD_RECORDING.md#操作)

- 本機 981 項核心、102 項 Node、533 項 Chromium 及 106 項解壓管理包檢查通過。瀏覽器以已接受的合併快照驗證分房名稱、玩家移除後鏡頭位置不變，以及恢復全館角色清單。
- Windows 原生整合 `run-bc8c26d275b245198451a4450418bbed` 退出碼 0，365 項通過。獨立與合併各 25 個同機桌面玩家。合併場從第 4 房房卡開始觀戰，切換第 2 房與全館，在單一原串流核對各房角色、25 個玩家名稱、跟隨解除及場次序號不變。50 份原戰績與伺服器確認、982 幀回放及六場封存核對完成，活動場次與剩餘程序為零。
- 首輪 `run-bc401d9a057145ec85fdf3ff6dd3abe9` 因驗證器拒絕任何 POST 退出碼 1，原始記錄保留。複驗限定允許唯讀 `POST /api/mission-layout`，其餘非 GET 請求仍會拒絕，並另外比對場次序號及 25 席。複驗實際只觀察到該版面預覽 POST。
- Windows 管理包 `artifacts/control-packages/windows-control-server-0.31.50-win-x64.zip` 為 52,738,906 bytes，SHA-256 `46a690a8e851dd900431f8e42d137ef97ed1af4108e57054e9c1a41b2a4d4659`。528 個解壓內容檔及 166 個發行來源檔均已核對。功能 `ca15429314ad1d0c8e8765b91d279248d39e2103`、驗證器 `e28996e9ce50e5705b3d5cd266f82ec743f5e16f`。兩次 GitHub Actions 均因帳務或支出上限未啟動。實機頭盔、MR 場地、跨機 25 人及廠商設備仍待驗收。 [功能 CI](https://github.com/peca12968/vr-command-center/actions/runs/42591623486) · [驗證器 CI](https://github.com/peca12968/vr-command-center/actions/runs/42591894638)

## 2026-11-09 VR 房卡席位提示

控制台 0.31.49 在準備中及執行中的 VR 房卡列出等待入場同步、姿態待確認及淘汰席位。依房間、入場及已觀察的管理階段核對，來源失效時撤下舊提示。 [房卡操作](https://github.com/peca12968/vr-command-center/blob/main/docs/PLAYER_READINESS.md#vr-房卡的席位提示)

- 本機通過 981 項核心、747 項 HTTP、65 項世界串流、102 項 Node、530 項 Chromium 及 106 項解壓管理包檢查。早期核心測試直接改生命值時被原世界驗證拒絕，後續使用已接受的傷害回報。另依原準備階段換席規則驗證待同步提示。
- 原生整合 `run-ce6eaf81968d43c08a3583ae99a1b662` 退出碼 0，376 項通過。兩種模式各啟動 25 個同機桌面玩家，第 4 房第 3 席原程序終止後，其餘 24 席持續有效。等原 UDP 連線釋放，以原票券從新程序重連，五房恢復 5／5。實際獨立模式控制台核對提示、恢復及結束。50 份戰績、原伺服器確認、2,814 幀回放與六場封存相符，活動場次及剩餘程序均為零。
- Windows 管理包 `artifacts/control-packages/windows-control-server-0.31.49-win-x64.zip` 為 52,737,796 bytes，SHA-256 `5c38a77341a93627f4724c4afd951a902cda2424f04a634880c445dfdf397019`。解壓後核對 528 個內容檔及 166 個發行來源檔。原生測試使用遊戲 0.48.1。
- 功能來源 `bbbd5307cd8920403de1e4574150b0ec2682e272`。GitHub Actions job `129069879906` 因帳務或支出上限未啟動。Quest 3、VIVE、MR 場地、跨機 25 人及廠商設備仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42590259813)

## 2026-11-09 Quest 原入場票券更新

新增 `deploy-quest.ps1 -RefreshPlayerTicket`，供同一入場用新票券按 B 重連。比對原場次、玩家、席位、端點及鎖定 MR 校正，只更新 `joinTicket`。在頭盔端核對原檔與暫存檔雜湊後替換。 [票券更新](https://github.com/peca12968/vr-command-center/blob/main/docs/QUEST_RECONNECT.md#保留遊戲程序並更新票券)

- Windows 的 Quest 部署套件 40 項通過。以模擬 ADB 和實際 POSIX 檔案命令核對逾期原票券、MR 與 VR 透視設定、同票券重試、錯席位、端點、校正及較早效期。原設定或暫存檔在替換前變動時會拒絕並清理自己的暫存檔。
- Windows 原生場 `20261109-165122-925d0c74` 退出碼 0，8 項入場與重連檢查、354 幀回放。待舊連線釋放後，新桌面玩家程序以同一入場恢復原位置及健康 60、彈匣 30、備彈 90。原回放與封存統計相符，活動場次和剩餘程序皆為零。另用該場實際簽發的原票券通過模擬 ADB 更新並拒絕撤銷的舊入場，原始設定檔雜湊相符。證據見同目錄 `quest-ticket-refresh-readback.json`。
- 功能來源 `743edaede5ac269b1173cdee3e67769b294a08e9`。GitHub Actions job `129066324133` 因帳務或支出上限未啟動。Quest 3 USB 更新與原程序 B 鍵重連、VIVE、MR 實地、跨機 25 人及廠商設備仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42589186598)

## 2026-11-09 Quest 五房整批日誌擷取

用原五房 VR、MR 或混合部署 ZIP 和版本 1 裝置清單並行擷取。預設完整 25 席，可選用 `--allow-partial-map` 擷取指定的 Quest 席位。逐席保存原 logcat、PID 和校驗值，失敗席位保留可用的 `.partial`，其他席位繼續擷取。 [整批操作](https://github.com/peca12968/vr-command-center/blob/main/docs/QUEST3.md#一次擷取五房-quest-日誌)

- Windows Python 3.12.10／PowerShell 7.6.9 通過 Quest 部署 37 項和場館驗收 30 項。25 個模擬 ADB 連線全部讀到原啟動記錄後才釋放終止戰績。另核對已過期原票券、混合五房的指定席位、錯誤入場只影響該席，以及拒絕重用原輸出路徑。
- 使用 Windows 原生場 `run-07f1951bf8e74fbeaf6e90c6832f153c` 保存的兩份 VR 部署 ZIP 與 50 份原玩家日誌。模擬 ADB 以生成的 logcat 格式讀入原 Windows 戰績標記，獨立和合併各 25 席，原入場、程序標記、戰績及輸出雜湊相符。兩份 ZIP 及 50 份原日誌校驗值維持一致。複驗摘要在 `artifacts/quest-venue-capture/windows-archive-07f1951/readback.json`。
- 功能來源 `4ffc02c8dc493b3a23256d550d18d9637fac4add`。GitHub Actions job `129063923230` 因帳務或支出上限未啟動。Quest 3／VIVE 真正裝置擷取、MR 實地、跨機 25 人與廠商設備仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42588469791)

## 2026-11-09 單房硬體模擬停止

Windows 硬體模擬器 0.2.2 加入 `--stop-file`。每個房間閘道可用自己的本機標記檔停止，等待確認的批次保留 `cancelled`，報告終止原因為 `operator-stop`。 [停止操作](https://github.com/peca12968/vr-command-center/blob/main/docs/HARDWARE.md#停止單房模擬閘道)

- 即時模擬 20 項通過，最終 ZIP 解壓後再通過 20 項。涵蓋既有標記、輸出同路徑、握手中、閒置及待確認批次。待確認測試核對原連線及批次 ID，該閘道確認數為零，另一房在原連線上繼續確認。離線 CLI 38 項、封裝工具 10 項及 .NET 核心 974 項通過。解壓後離線範例與原報告逐位元相同。
- Windows 原生整合 `run-8342b5268d1e413886ef02c537789e21` 退出碼 0，420 項通過。五房獨立及合併各 25 個同機桌面玩家，分別核對 108 與 105 筆模擬確認，合計 1,692 幀回放及 50 份原戰績與伺服器確認。活動場次為零，原管理、遊戲、玩家及硬體模擬程序均已清理。
- 最終包 `artifacts/hardware-packages/hardware-simulator-0.2.2-final-net10.zip` 為 182,028 bytes，SHA-256 `15e64996efb8420e89407faa707708755b84d3a75e8b5e04f041e97b1f0e13af`。八個解壓內容檔與原生整合所用初包一致，最終 manifest 指向完成附掛驗證後的測試證據。0.2.1 的 ZIP 校驗值與歷史紀錄相符。
- 功能來源 `de44f15752f5dc84e00683874bef92a8d06ead7b`。GitHub Actions job `129060167914` 因帳務或支出上限未啟動。廠商協議、實體設備輸入、輸出與停止、Quest 3、VIVE、MR 實體場地與跨機 25 人仍待驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42587330947)

## 2026-11-09 MR 校正封存驗收

主控可選用 `--room-alignment` 或在整批 `roomAlignments` 提供部署 ZIP 的原校正檔。核對當次任務模式、`quest-room-mr-v1` 回放來源、各房鎖定 SHA-256 與原 Quest 戰績。選用後，整批每個 MR 房間都需原檔，每場都需原回放。 [校正封存](https://github.com/peca12968/vr-command-center/blob/main/docs/EXTERNAL_CLIENTS.md#核對-mr-校正封存)

- 場館驗收 30 項、回放分析 14 項、封裝工具 10 項及既有 .NET 核心 974 項通過。合成對戰資料覆蓋混合五房及全 MR 合併模式，也檢查重寫原檔、錯房、缺檔、錯回放來源與缺 Quest 日誌。原 Windows VR 三包的兩份 v1 摘要唯讀重驗完全一致。
- 混合 Windows 原生場 `run-e8b0163c89b1445591b37537fbcf2704` 退出碼 0，119 項通過。五間各自封存，共 496 格回放。兩間 MR 的原校正檔與封存鎖定相符，交叉送檔均被拒絕。全 MR 原生場 `run-6a9d6bb06ad64e37a3167e24f31303b1` 退出碼 0，128 項通過。合併一場及五個獨立場核對十次房間鎖定及 272 格回放。八個 MR 原生場都只到準備階段，均依預期無法通過正式對戰驗收。兩次活動場次與剩餘程序均為零。
- 功能來源 `43fc4036a48f0dcbcdd116ab3b2c14d702f8d00f`。GitHub Actions job `129056833825` 因帳務或支出上限未啟動。Quest 3、VIVE、MR 實體量測與透視、跨機 25 人及廠商設備仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42586297102)

## 2026-11-09 場館原生回放檔驗收

單場驗收可選用 `--world-journal`，五房清單可為每場提供 `worldJournal`。沿用閉源讀取器檢查每筆記錄的 SHA-256、連續影格、場次與校正設定、活動中影格、最後戰鬥序號及原世界收據。整批同時核對最後影格已觀察到該批結束指令。 [封存操作](https://github.com/peca12968/vr-command-center/blob/main/docs/EXTERNAL_CLIENTS.md#核對封存戰績與-udp-來源)

- 場館驗收 27 項、回放檔分析 14 項及封裝工具 10 項通過。覆蓋原來源不符、校驗碼損壞、缺最後收據、戰鬥尾界不符、只停留在準備階段、晚於最後狀態的時間及批次缺檔。原先只驗收戰績的指令仍可使用。
- 唯讀複查 `field-journal-readback-cfcf9103` 的六個原 900 秒 Windows 封存檔，51,342 格回放逐場與原 API 回放相同。首次複查將舊 `Running` 統計直接比對活動影格而失敗。原回放證明每場有一格 tick 0，改依原回放逐格核對活動定義後得到 51,073 格。原準備後結束的 MR 檔案亦按預期被活動場次條件拒絕。
- Windows 三包 `run-e93bcab4ff474112ae3ccf906cff02e3` 退出碼 0，462 項通過。獨立與合併各 25 個同機桌面玩家，六份原生回放檔共 1,659 格及 953 格活動影格。50 份戰績與伺服器確認、212 筆 AI 傷害、雙封存及整批驗收相符。活動場次與剩餘測試程序均為零。
- 功能來源 `3373a8036b33a3dacd4cba9cc7b2deeeedd7da09`。GitHub Actions job `129053981203` 因帳務或支出上限未啟動。頭盔、MR 場地、跨機 25 人及廠商設備仍待實地驗收。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42585426018)

## 2026-11-09 Quest 場館日誌持續擷取

`capture-quest-field-log.py` 由原玩家連線檔取得 UDP 埠及入場識別。遊戲啟動後開始串流指定 PID 的原 `threadtime` 日誌，保留重連，直到原入場戰績與最後斷線。寫出完整檔案前再核對 PID，並回傳 PID 及 SHA-256。擷取上限 16 MiB，失敗時保留已擷取的 `.partial`。 [現場操作](https://github.com/peca12968/vr-command-center/blob/main/docs/QUEST3.md#收集-quest-場館驗收日誌)

- 場館驗收測試 25 項通過，含 9 項新擷取測試。覆蓋原檔逐位元、重連後最後戰績、同埠舊入場、錯誤啟動來源、PID 更換、ADB 串流中斷、逾時、大小上限與既有檔保護。實際本機 ADB 在沒有裝置時拒絕，未建立日誌。
- `artifacts/quest-live-capture-919acb59` 用原 Windows 三包封存的 50 份玩家連線檔與 Unity 事件，分別以 25 個模擬 ADB CLI 擷取獨立及合併模式。原事件文字、入場及最終結果逐份相符，日誌檔與報告 SHA-256 一致。模擬只提供 Android 日誌外層和 ADB 串流，測試程序均退出。Quest 3 真機擷取、VIVE、MR 場地、跨機 25 人及廠商設備仍待實地驗證。
- Windows 三包 `run-7561c3bf2d4e4c8a9830f160a722d932` 退出碼 0，417 項通過。獨立和合併各 25 個同機桌面玩家。使用各原伺服器及玩家日誌，核對 50 個入場、UDP 來源、戰績及伺服器確認，並比對 6 份 CSV、910 格回放和雙封存。兩個整批驗收 ZIP 都拒絕將同機結果申報為跨機，後一批也未改動原獨立批 ZIP。活動場次和剩餘程序均為零。
- 功能來源 `2234d5091f9d25b24ced2e120fa04e3d843376cf`。GitHub Actions job `129049370742` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42584023496)

## 2026-11-09 Windows 0.48.1 雙模式長場複驗

現行 Windows 0.48.1 與管理包 0.31.48 依原門檻執行兩種 900 秒原生長場。先驗合併 25 席，再驗獨立五房各 5 席。遊戲來源指紋 `00fdc5bb2f905a08b36c85749367de91c106cd829d338cf2c3981f497c84633e`。這次沿用既有建置與測試工具。 [長場操作](https://github.com/peca12968/vr-command-center/blob/main/docs/DESKTOP_ENDURANCE.md#windows-0481-長場複驗)

- `20261109-151952-6c10c16e` 退出碼 0，18 項通過。每席完成 90 發射擊與 45 次換彈，所有生成器均明確收尾。原輸入活動跨度 17,947 至 18,001 tick，最長本機收集 902.532 秒。
- 合併場核對 8,510 格回放，其中 8,470 格為執行中。獨立五房分別核對 8,569／8,558／8,559／8,549／8,597 格。六場共 51,342 格完整回放、51,079 格執行中回放、50 份戰績與確認、6 份 CSV 和雙封存，沒有原生送出佇列錯誤。活動場次與剩餘程序均為零。關閉寫入後逐檔核對 SSD 與 F 槽的 174 檔副本，SHA-256 全數相同。
- 範圍為單台 Windows 的自動化桌面輸入。實機 Quest 3、VIVE、MR 場地、跨機 25 人及廠商設備仍待驗收。

## 2026-11-09 開場前 UDP 報告配對

UDP 探測工具可讀取兩端原始報告，核對互為對端的 IPv4、同一 UDP 埠、完整樣本與同次交換摘要。配對成功回報 `pair-verified`。核對時只需兩份已關閉的原始報告。 [兩端操作](https://github.com/peca12968/vr-command-center/blob/main/docs/EXTERNAL_CLIENTS.md#開場前核對兩端-udp)

- Windows PowerShell 5.1 與 PowerShell 7 各 6 項通過，涵蓋兩個不同 loopback 位址、BOM 報告、錯誤簽章與重送、同一埠的不同探測、逾時與埠重新綁定。首次正向測試發現測試仍持有監聽輸出檔，改在關閉後核對。另修正 5.1 將小數往返時間解析成 `Decimal` 的相容性。伺服器封裝工具另 10 項通過。
- `artifacts/lan-pair-native-a12fc24f` 以本機私有 IPv4 執行同一封裝驗證函式，五個獨立埠及一個合併埠各完成三筆往返。六份交換摘要各自不同，兩端原始報告逐組相符，六個原埠均可重新綁定。本次六埠只量測 PowerShell UDP，實際跨機與 Unity 入場另驗。
- Windows 三包 `run-93b4735ae8364d53ac4be25544f7e5f2` 退出碼 0，371 項通過。五個獨立房與合併場的六組原始探測報告均配對成功。各 Unity 子程序實際接手原埠後才公告端點。兩種模式各 25 個同機桌面玩家同時入場，六場核對 1,039 格回放、50 份戰績、50 次伺服器確認、6 份 CSV 和雙封存。活動場次及剩餘測試程序均為零。
- 功能來源 `55739448b159f4e9e53a1f8c2cec59e9ebeed58b`。GitHub Actions job `129034386539` 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42579426094)

## 2026-11-09 Quest 部署後逐席追蹤核對

Quest 部署工具的 `-VerifyTrackedSeats` 可從主控電腦用原五房 VR、MR 或混合 ZIP 核對追蹤。先由管理服務驗證原連線檔，再讀同一場次的一份就緒快照，逐席比對玩家、入場、場次版本與 `Tracked` 姿態。可用裝置清單選取部分席位，核對不呼叫 ADB。 [部署後核對](https://github.com/peca12968/vr-command-center/blob/main/docs/QUEST3.md#核對頭盔追蹤席位)

- 35 項 PowerShell 部署工具測試通過。模擬回覆覆蓋就緒、舊入場、過期來源、尚未套用的序號、重複席位、無回覆與 MR 來源設定。合併場只讀一份快照，獨立場按原場次讀取。輸出只含房號、席位及狀態等驗收資訊。
- 首次 Windows 三包 `run-4d43de0de05446409b558b652c2b6255` 缺少專案鎖定的 Chromium，退出碼 1 並正常清理。F 槽安裝測試瀏覽器時遇到安裝鎖逾時，改用 SSD 快取並核對版本 `151.0.7922.34`。
- Windows 三包重跑 `run-90e578c3d90c4dd99a33fd8ee6068ac2` 退出碼 0，363 項通過。獨立五房與合併場各有 25 個同機 Windows 模擬玩家同時連線，兩種模式全部回報 `Fresh` 與 `not-tracked`，均未判成頭盔就緒。六場核對 50 份原戰績、50 次伺服器確認、6 份 CSV、雙封存及 1,482 格回放。活動場次及剩餘測試程序均為零。
- 混合場前兩輪 `run-296bd4ae871d4f3988cbda3b8fe41135` 和 `run-b1c18413d49b466e896336cb1bff8cfd` 在席位斷言退出碼 1。第二輪保留報告，確認工具正確略過房 1 席 2，測試將 API 從 0 起算的席位直接拿去比對操作員從 1 起算的報告。只修正測試對照並先留存報告。最終 `run-1ddfab6155f8492babe9204d2881dded` 退出碼 0，113 項通過。3 間 VR、2 間 MR 的快照新鮮，24 個 Quest 席位均等待追蹤，略過 1 個 VIVE 名額。五場共 448 格封存回放，活動場次與測試程序均已清理。
- 功能來源 `05306a0c9af5544447b0daaa072131b5a70987f9`，混合測試修正 `a839bb141886b4132a8dac6414cf4f7673d1bbfa`。兩次 GitHub Actions job `129029946316` 和 `129031121213` 因帳務或支出上限未啟動，零步驟。這次使用既有 Windows 遊戲 0.48.1 與管理包 0.31.48。實機追蹤、MR 場地、VIVE、跨機 25 人及廠商設備仍待驗證。 [功能 CI](https://github.com/peca12968/vr-command-center/actions/runs/42577992336) · [測試修正 CI](https://github.com/peca12968/vr-command-center/actions/runs/42578376188)

## 2026-11-09 XR 焦點恢復與按鍵重新啟用

遊戲 0.48.1 失去應用程式或 OpenXR 輸入焦點時停止發布本機追蹤姿態。恢復焦點後，射擊、換彈、B 重連與 MR 左扳機取點都需先放開再按下。失焦會清除尚未完成的 MR 量測。單純失焦保留已完成校正，應用程式暫停或追蹤原點改變則清除。 [操作方式](https://github.com/peca12968/vr-command-center/blob/main/docs/QUEST3.md#追蹤恢復後的武器輸入)

- 最終 Unity Editor 269 項全數通過，含虛擬 Touch 的持續按住、放開後再按與焦點模擬。另有 974 項核心及 10 項封裝工具檢查通過。Windows 與 Android 由來源指紋 `00fdc5bb2f905a08b36c85749367de91c106cd829d338cf2c3981f497c84633e` 建置，場景與玩家預製物網路識別相符。Quest APK 0.48.1／62 經 ARM64、OpenXR 程式庫與 APK v2 開發簽章核對。舊版建置與日誌共 338 檔逐檔核對後封存。
- Windows 玩家包與伺服器包均解壓核對 328 檔，玩家啟動器 19 項檢查通過。 [玩家包](https://github.com/peca12968/vr-command-center/blob/main/docs/WINDOWS_PLAYER_PACKAGE.md) · [伺服器包](https://github.com/peca12968/vr-command-center/blob/main/docs/WINDOWS_SERVER_PACKAGE.md)
- Windows 首輪 `20261109-144811-b561388b` 的合併 25 席通過，啟動獨立場時觸發既有 2 GiB 可用記憶體保護並退出碼 1。Quest 建置結束後依原門檻重跑 `20261109-145527-aaaeced1`，退出碼 0，19 項通過。合併一場與獨立五場各有 25 個同機模擬玩家同時入場，每席兩發、兩中、一殺，完成換彈、50 份原玩家結果與確認、6 份 CSV、雙封存及 1,932 格完整回放。測試活動場次與剩餘程序均為零。
- 解壓伺服器包 `run-7b630066d4f9489c9f078b615f35f9b9` 退出碼 0，152 項通過。五個獨立 VR 場及合併 VR 場核對 10 份原玩家結果與 CSV。獨立 MR 測試確認缺校正鎖定資料時拒絕啟動，正確鎖定後拒絕桌面玩家，缺已追蹤名冊時維持 Preparing，並封存操作員套用的夜間雷雨。七場共 552 格完整回放。另有刻意終止啟動器的反例保持未封存。測試活動場次及剩餘程序均為零。
- 使用者關閉原畫面擷取視窗後，WinForms 重試 `run-0533d07f3b4746378f13094bd7fd4108` 看見 `vrcommand.exe` 的 Windows 防火牆提示遮住啟動器。依 computer-use 技能規則停止桌面輸入。360 秒後退出碼 1，未載入管理實例或從圖形介面啟動遊戲伺服器。測試 GUI 與 API 已退出，清理無錯誤。
- 功能來源 `a2908ef5c84c262e4572046c927c8494937d625b`。GitHub Actions job `129024129873` 因帳務或支出上限未啟動，零步驟。Quest 3 真機焦點、MR 場地、VIVE、跨機 25 人及廠商硬體仍待實地驗證。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42576126265)

## 2026-11-09 五房房卡的連線端點

Windows 管理包 0.31.48 在五房房卡顯示該場遊戲伺服器公布的 IPv4 與 UDP 埠，標明合併場共用與 loopback 僅同機。主控看全館，房控僅讀本房。房卡核對房間、場次、來源及當前名冊，房間更換或回覆不符時移除舊端點。 [操作方式](https://github.com/peca12968/vr-command-center/blob/main/docs/EXTERNAL_CLIENTS.md#五房房卡的連線端點)

- 974 項核心、747 項 HTTP、65 項世界串流、106 項管理包、17 項封裝工具、101 項 Node 與 530 項 Chromium 檢查通過。瀏覽器核對合併場 loopback 標示、獨立端點及換場後的舊回覆，歷史場次端點保留且從房卡移除。
- Windows 原生混合場 `run-11fcf8dcff534c16927a1befcbe45de3` 退出碼 0，112 項通過。3 間 VR、2 間 MR 使用自己的 UDP 綁定，五個房控都只收到本房端點。真實解壓版 Chromium 在 390 像素寬顯示五個端點，並完成原混合 ZIP 及模擬 ADB 回歸。五個準備場共封存 498 格。
- Windows 三包 `run-07f1951bf8e74fbeaf6e90c6832f153c` 退出碼 0，352 項通過。獨立五房與合併模式的房卡分別對上五個不同綁定及同一共用綁定。兩種拓撲各 25 個同機模擬玩家同時入場，六場共核對 1,236 格回放、50 份原玩家戰績、50 次伺服器確認及 6 份 CSV。兩次原生測試均確認活動場次和剩餘程序為零。頭盔、跨機與廠商硬體仍待實機。
- 功能來源 `b0e8e402986f5dbcf61e5d30b6784fa04b08dc2d`。GitHub Actions job `129017459584` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42573983804)

## 2026-11-09 伺服器啟動器的連線來源紀錄

Windows 遊戲伺服器啟動器 1.7 加入圖形介面的來源紀錄開關，預設關閉，每場明確選用，運行中鎖定，收尾後重設。沿用 Unity 0.48.0 的伺服器來源紀錄。結果檔的 `peerDiagnosticsEnabled` 及 `workDirectory` 可核對該次啟動設定與原 `server.log`。 [操作方式](https://github.com/peca12968/vr-command-center/blob/main/docs/WINDOWS_SERVER_PACKAGE.md#跨機來源診斷)

- F 槽新 ZIP 解壓核對 328 個清單檔案，321 個 Unity 執行檔案與 1.6 逐檔一致。伺服器工具 10 項、場館戰績驗收 16 項及 Windows 場次清單 51 項通過，另有 46 項實際編譯的 Framework 狀態檢查。
- 三包命令列 `run-034584ef3e744e77b2dae223e074879e` 退出碼 0，388 項通過。獨立與合併各 25 個同機 Windows 模擬玩家同時入場。獨立五房的關閉設定保留至結果，原日誌無來源記錄。合併場開啟後 25 個來源端點分別與原玩家連線及伺服器戰績確認相符。六場 50 份原戰績、6 份 CSV 與 965 格完整回放核對通過。另有 MR 準備場確認校正鎖定、桌面拒絕及 22 格封存回放。活動場次與剩餘測試程序皆為零。
- WinForms `run-17ee38baf50641e1a3f6f54c69c01539` 已看見未勾選的來源選項。Windows 防火牆提示遮住視窗，依 computer-use 技能規則停止桌面輸入。360 秒後該輪退出碼 1，未載入場次或啟動遊戲子程序，測試 GUI 與 API 已退出，清理無錯誤。圖形介面勾選至實際記錄的流程、實體跨機、頭盔及廠商設備仍待驗證。
- 功能來源 `c843224615133bc454842bebf579819dd69f58ac`。GitHub Actions job `129013879678` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42572831703)

## 2026-11-09 Quest 場館戰績驗收日誌

場館驗收工具可把 Quest 3 的原始 logcat 與 Windows 玩家日誌一起核對。單場用 `--quest-player`，全館清單為 Quest 席位加上 `logcatPid`。核對同一程序的啟動、最終連線及戰績，再對照原 Quest 3 入場名額、伺服器觀察到的 UDP 來源、戰績確認及雙封存。 [擷取與核對](https://github.com/peca12968/vr-command-center/blob/main/docs/QUEST3.md#收集-quest-場館驗收日誌)

- 16 項場館驗收、10 項伺服器工具及 5 項 LAN 預檢測試通過。測試日誌涵蓋全連線 25 席 Quest 格式、獨立五房各一席 Quest 和四席 Windows，以及重連後使用最後一條有戰績確認的連線。其他 PID、錯誤埠、錯誤入場、來源地址及封存序號不符皆拒絕。
- 唯讀重驗 Windows 原生封存 `run-564cff2a85b14aa2b1a68a82d4ec6234`。獨立與合併各 25 席，兩份摘要均與原結果相同。50 份原 Windows 玩家標記另用合成 logcat 外框測試，保留原連線及戰績，錯 PID 全數拒絕。本機驗證摘要存於 `artifacts/quest-field-logcat-20261109/readback.json`。Quest 真機擷取、實際場館網路容量、VIVE 及廠商硬體仍待驗證。
- 功能來源 `87ea9b911dbfef7278e3bb0539a2371038a5878b`。GitHub Actions job `129011660453` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42572132563)

## 2026-11-09 混合 VR／MR 五房部署

Windows 管理包 0.31.47 可為含 VR 與 MR 的五個獨立房間一次下載部署 ZIP。主控依原場次、UDP 端點、來源及名冊配票，只有 MR 房需上傳原始校正檔。部署腳本整包核對 25 席，再依房間模式部署單席或清單。 [操作方式](https://github.com/peca12968/vr-command-center/blob/main/docs/QUEST3.md#混合-vr-與-mr-五房部署包)

- Windows 管理及伺服器包 `run-e5f2380d140e4bc58dfa0efba3f411aa` 退出碼 0，98 項通過。實際 3 個 VR、2 個 MR 原生 Windows 伺服器各公布 UDP 端點。控制台下載的 ZIP 通過 25 席原簽章、席位頭盔類型、兩份原始校正檔及端點核對，拒絕修改校正檔、過期來源和變更端點。
- 指定每房一席共五席，在模擬 ADB 依序核對各序號，三席 VR 使用原設定，兩席 MR 另寫入逐位元相同的校正檔並啟用透視設定。原場次資料在配票、預檢和模擬部署期間一致。五場結束後完成雙封存，逐場核對共 457 格完整回放，活動場次及剩餘程序皆為零。此輪驗證在準備階段執行，實體 Quest 3、VIVE、跨機及廠商硬體仍待驗。
- 核心 974 項、HTTP 747 項、世界串流 64 項、解壓管理包 106 項、部署腳本 34 項、伺服器工具 10 項、Node 100 項及解壓版 Chromium 527 項通過。
- 功能來源 `381c2c766c50c1ec15874778b16ec1444b99618f`。GitHub Actions job `129009132416` 因帳務或支出上限未啟動，零步驟。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42571327228)

## 2026-11-09 Quest 指定席位小批次部署

部署腳本新增 `-AllowPartialMap`，可從原五房 VR 或 MR ZIP 選擇 1 至 25 個 Quest 席位。正式部署仍核對原 25 份連線檔、名冊與端點，裝置檢查和寫入只針對清單上的序號。預設全席清單維持 25 席。管理包 0.31.46 與遊戲 0.48.0 沿用原建置。 [小批次操作](https://github.com/peca12968/vr-command-center/blob/main/docs/QUEST3.md#部署指定的-quest-席位)

- 33 項部署腳本與 10 項伺服器工具測試通過。涵蓋單席、空清單、重複席位或序號、未選票券失效、混合 VR 名冊、原設定與 MR 原校正檔保留，以及完整 25 席回歸。
- VR Windows 三包 `run-6b5f6a212fe842e6a2e756e38cebc7c3` 退出碼 0，346 項通過。獨立與合併各以 15 席 Quest 3、10 席 VIVE XR 的原名冊下載控制台 ZIP。兩種模式皆拒絕把 VIVE 席位加進 Quest 部署清單，並只對五個指定模擬 ADB 序號寫入原設定及請求啟動。另以每種模式 25 個同機 Windows 模擬玩家入場，六場核對 1,330 格完整回放、50 份戰績、50 次伺服器確認、6 份 CSV 及雙封存。活動場次和剩餘測試程序皆為零。
- MR Windows 管理及伺服器包 `run-94a7daef7e4d4b0b9fea8cd21e9a58f2` 退出碼 0，109 項通過。獨立與合併的原 ZIP 都通過完整 25 席及指定五席兩種模擬 ADB 測試。各模式核對原公告端點、原鎖定校正檔及設定，指定序號的校正檔逐位元一致。六個準備場共封存 536 格回放，活動場次與剩餘測試程序皆為零。
- 功能來源 `36927b7f94ff6b7e359702e5add5f91ddd2a603b`。GitHub Actions job `129004181757` 因帳務或支出上限未啟動，零步驟。Quest 3、VIVE、跨機及廠商硬體仍待實機驗證。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42569762925)

## 2026-11-09 五房逐房指定任務版本

控制台 0.31.46 可在「五房各自獨立」為每房指定保存版本，並逐房查看時間、初始環境、敵軍與平面圖。五房共用一次交易，重送取回原場次及版本分配。原共用版本入口仍可使用。 [逐房操作](https://github.com/peca12968/vr-command-center/blob/main/docs/MISSION_VERSIONS.md#逐房指定任務版本)

- 974 項核心、747 項 HTTP、64 項世界串流、106 項解壓管理包、18 項解壓版 Chromium 專項及 527 項完整瀏覽器檢查通過。核對不完整計畫與錯房配置的拒絕、實際 SQLite 第三筆寫入失敗整批回滾，以及重啟後原分配。瀏覽器核對 390 像素視窗、配置未通過阻擋建立，以及回覆遺失與新版本保存後的原樣重送。
- Windows 三包 `run-8f852fce23014193956fe888381c8dd8` 退出碼 0，346 項通過。五個獨立房各用不同的保存 VR 任務，遊戲錄製逐房核對 210 至 330 秒的計畫時間、天氣／日夜／雷電、2 至 6 個敵軍及各自的油桶座標與角度。獨立和合併各有 25 個同機模擬玩家同時入場。六場共核對 1,005 格完整回放、50 份戰績、50 次伺服器確認、6 份 CSV 和雙封存。活動場次為零，所有原測試程序均已退出。
- 功能來源 `d35e5536666b0b1ea63fe282302aa1a61706d33c`。GitHub Actions job `129001576670` 因帳務或支出上限未啟動，零步驟。Quest 3、VIVE、跨機及廠商硬體仍待實機驗證。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42568933364)

## 2026-11-09 保存版本的開場平面圖

控制台 0.31.45 在準備場次前可展開保存版本平面圖，核對掩體位置、旋轉、碰撞包圍盒、出生位及到中線的取樣通路。圖層沿用所選版本與模式的場地檢查，編輯草稿保持獨立。 [開場平面圖](https://github.com/peca12968/vr-command-center/blob/main/docs/LAYOUT.md#開場前查看保存版本平面圖)

- 968 項核心、725 項 HTTP、64 項世界串流、106 項解壓管理包及 521 項解壓版 Chromium 檢查通過。瀏覽器核對舊版及修正版、圖層與草稿隔離、錯誤版本清圖、遲到回應隔離、封閉防線及 390 像素視窗。
- Windows 同機 `20261109-132908-75fd3f6a` 的 Chromium 與原生工具都以退出碼 0 結束。從解壓管理包選歷史第 1 版，沙包未儲存的位移留在草稿。平面圖的兩個物件、五個出生位和五條路徑與原版檢查一致。透過實際控制台建立及開始五房合併場次，每房一個模擬玩家。遊戲來源的 10 個物件與原保存座標和角度一致。雨夜、雷電和各房初始敵軍 2／2／1／1／1 已核對，封存 91 格、五份玩家戰績已確認送達，活動場次與剩餘程序皆為零。
- Windows 管理及伺服器包 `run-74f7e304784b44f4b74612f786a29169` 退出碼 0，136 項通過。五房獨立及合併各每房一個同機模擬玩家，核對六場原保存沙包位置和中線缺口、536 格完整封存回放與 10 份原玩家戰績。測試後活動場次歸零，原管理、伺服器與玩家程序均退出。
- 功能來源 `7b5cc66117efd6e6289d8adfa25553b8e223f01e`。GitHub Actions job `128997959491` 因帳務或支出上限未啟動，零步驟。Quest 3、VIVE、跨機及廠商硬體仍待實機驗證。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42567771797)

## 2026-11-09 從戰績開啟個人回放

控制台 0.31.44 在雙封存後可從「任務統計」選擇玩家。開啟時核對原場次及戰鬥與世界封存序號，停在最後一格並搜尋該玩家的事件。選單含已離場的玩家，依玩家 ID 歸屬事件。 [戰後檢討](https://github.com/peca12968/vr-command-center/blob/main/docs/REPORTS.md#從戰績開啟個人回放)

- 968 項核心、725 項 HTTP、64 項世界串流、22 項短場工具測試、106 項解壓管理包與 514 項解壓版 Chromium 檢查通過。瀏覽器核對未封存及封存序號不符時拒絕開啟、正常封存的原序號跳轉、個人事件筆數與清除篩選。
- Windows 同機原生 `20261109-131846-924cdd5e` 退出碼 0，25 項通過。五房合併與五房獨立各有 25 個同時連線的模擬玩家。六場共 2,044 格封存回放，核對 50 組個人搜尋的 160 頁、100 筆射擊及各玩家的最終彈藥統計。每位玩家兩發兩中、一擊殺。原 50 份戰績、50 次伺服器確認和雙封存均通過。活動場次為零，原測試程序均退出。
- 功能來源 `8d30515bb7a359e3adb1b160c07a2813b144b018`。GitHub Actions job `128994921718` 因帳務或支出上限未啟動，零步驟。Quest 3、VIVE、跨機及廠商硬體仍待實機驗證。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42566796111)

## 2026-11-09 任務回放戰鬥事件搜尋

控制台 0.31.43 在回放暫停後可依房間和事件種類搜尋，從結果直接跳到原始保存格。未封存片段沿用原本固定的保存尾端，既有錄製可直接搜尋。 [回放操作](https://github.com/peca12968/vr-command-center/blob/main/docs/WORLD_RECORDING.md#依房間與種類搜尋戰鬥事件)

- 968 項核心、725 項 HTTP、62 項世界串流、22 項短場驗證工具測試、106 項解壓管理包、100 項 Node 與 509 項解壓版 Chromium 檢查通過。瀏覽器用保存的玩家受傷事件驗證搜尋、原序號跳格和篩選切換，並核對未封存片段的搜尋請求。
- Windows 同機原生 `20261109-130941-2954c691` 退出碼 0，24 項通過。五房合併和五房獨立各有 25 個同時連線的模擬玩家。以 1,981 格完整保存回放核對 10 組房間搜尋、32 頁與 100 筆射擊，其中 7 頁無相符格但仍有後續游標。六場各有雙封存，核對 50 份戰績及伺服器確認與 6 份 CSV。活動場次歸零，原測試程序全數退出。
- 功能來源 `f540d6873818cbf0889f0adad7e004bdcf3c77d3`。GitHub Actions job `128992200308` 因帳務或支出上限未啟動，零步驟。Quest 3、VIVE、跨機及廠商硬體仍待實機驗證。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42565893105)

## 2026-11-09 Quest 直接部署 VR 五房 ZIP

Quest 工具可直接讀取原始 VR 五房配票 ZIP，支援全館預檢、指定單席及依裝置清單部署。管理包 0.31.42 在寫入前核對票券、原端點及現行 Quest 3 席位。 [部署操作](https://github.com/peca12968/vr-command-center/blob/main/docs/QUEST3.md#%E7%9B%B4%E6%8E%A5%E4%BD%BF%E7%94%A8-vr-%E4%BA%94%E6%88%BF%E9%80%A3%E7%B7%9A-zip)

- 本機通過 31 項部署、506 項完整 Chromium、422 項 VR 原生及 103 項 MR 原生回歸。兩種模式各向 25 台模擬 ADB 裝置配發正確設定，VR 同一批原檔另供同機 Windows 玩家入場並核對 50 份戰績。
- 程式及文件已推送 `main`。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE、跨機與廠商硬體待實機驗證。 [驗證紀錄](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md) [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42564824993)

## 2026-11-09 VR 五房配票

Windows 管理包 0.31.41 讓主控在五房總覽核對名冊、席位及來源端點，再一次下載 VR 的 25 份短效連線檔。獨立與合併皆會在簽發前核對五房的場次、來源及現行入場資料。 [操作方式](https://github.com/peca12968/vr-command-center/blob/main/docs/EXTERNAL_CLIENTS.md#vr-%E4%BA%94%E6%88%BF%E9%85%8D%E7%A5%A8)

- 本機通過 502 項完整 Chromium、106 項解壓管理包與 438 項 Windows 原生檢查。獨立與合併各以管理台下載的原始連線檔啟動 25 個同時連線的模擬玩家。核對 50 份戰績、伺服器確認與雙封存。
- 程式及文件已推送 `main`。GitHub Actions 因帳務或支出上限未啟動。跨機、Quest 3、VIVE 及廠商硬體待實機驗證。 [驗證紀錄](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md) [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42563818673)

## 2026-11-09 Windows 玩家席位與票券效期

Windows 玩家啟動器 1.2 顯示連線檔標示的房間、席位與依本機時鐘計算的效期。改路徑後會清除舊提示，實際入場由遊戲伺服器驗票。 [玩家操作](https://github.com/peca12968/vr-command-center/blob/main/docs/PLAYER_CONFIG_REVIEW.md#%E9%80%A3%E7%B7%9A%E6%AA%94%E5%B8%AD%E4%BD%8D%E8%88%87%E6%95%88%E6%9C%9F)

- 本機通過 36 項 Framework 連線檔檢查、17 項入場狀態檢查、19 項解壓包檢查與 10 項 WinForms、管理台及原生遊戲流程檢查。實際視窗換入主控下載的有效檔後，兩位同機玩家入場，核對各自戰績與 136 幀雙封存回放。
- 程式與文件已推送 `main`。GitHub Actions 因帳務或支出上限未啟動。跨機、Quest 3、VIVE 及廠商硬體待實機驗證。 [驗證紀錄](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md) [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42562998575)

## 2026-11-09 遊戲開場前 UDP 探測

新增 Windows PowerShell 探測工具，兩端可先在規劃的遊戲位址和埠交換經驗證的 UDP 封包。監聽退出後，由 Unity 接手同一埠。 [操作方式](https://github.com/peca12968/vr-command-center/blob/main/docs/EXTERNAL_CLIENTS.md#%E9%96%8B%E5%A0%B4%E5%89%8D%E6%A0%B8%E5%B0%8D%E5%85%A9%E7%AB%AF-udp)

- Windows PowerShell 5.1 與 PowerShell 7 各通過 5 項程序測試。456 項同機 Windows 原生檢查通過，五房獨立及合併六個遊戲端點共 18 筆有效探測，原 Unity 子程序接手相同端點。兩種模式各有 25 個同時連線的模擬玩家，原戰績及雙封存已核對。
- 程式與文件已推送 `main`。GitHub Actions 因帳務或支出上限未啟動。第二台電腦、實際網路容量、Quest 3、VIVE 及廠商硬體待驗。 [驗證紀錄](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md) [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42562094069)

## 2026-11-09 整批場館驗收 ZIP

管理包 0.31.40 讓主控從全館收尾一次下載指定批次的明細及各原場次的驗收 ZIP。各原場次曾開場、完成雙封存並具備公告端點與相符名冊後可下載。 [驗收操作](https://github.com/peca12968/vr-command-center/blob/main/docs/SESSION_CLOSURE.md#%E4%B8%8B%E8%BC%89%E6%9C%AC%E6%89%B9%E5%A0%B4%E9%A4%A8%E9%A9%97%E6%94%B6)

- 本機通過 489 項完整 Chromium、106 項管理包及 446 項 Windows 原生檢查。兩種模式各 25 個同時連線的模擬玩家，六份內層 ZIP 與單場原檔逐位元組一致。合併場結束後，主控從歷史清單再下載獨立批次，與原檔逐位元組一致。
- 程式與文件已推送 `main`。GitHub Actions 因帳務或支出上限未啟動。跨機、Quest 3、VIVE 及廠商硬體待實機驗證。 [驗證紀錄](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md) [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42561034836)

## 2026-11-09 五房 25 席場館驗收核對

新增五房離線核對。獨立與合併各讀取原結束批次、管理 ZIP、伺服器終止報告及玩家日誌，逐房核對五個席位、UDP 來源和各自的戰績確認。 [驗收操作](https://github.com/peca12968/vr-command-center/blob/main/docs/EXTERNAL_CLIENTS.md#%E4%B8%80%E6%AC%A1%E6%A0%B8%E5%B0%8D%E4%BA%94%E6%88%BF-25-%E5%B8%AD)

- 本機通過 12 項場館核對、10 項伺服器包、10 項 Chromium 專項與 439 項原生檢查。兩種模式各 25 個同時連線的模擬玩家，合計核對 50 份戰績、50 筆伺服器確認與 1,549 幀回放。兩份同機資料均拒絕以直連跨機模式驗收。
- 程式與證據說明已推送 `main`。GitHub Actions 因帳務或支出上限未啟動。第二台電腦的實際連線、25 台容量、Quest 3、VIVE 及廠商硬體待驗。 [驗證紀錄](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md) [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42560162635)

## 2026-11-09 全館收尾歷史

Windows 管理包 0.31.39 加入全館收尾歷史分頁。主控可保留指定批次，開啟各原場次回放並下載當時的戰績 ZIP。 [操作方式](https://github.com/peca12968/vr-command-center/blob/main/docs/SESSION_CLOSURE.md#%E6%AD%B7%E5%8F%B2%E6%89%B9%E6%AC%A1)

- 本機通過 968 項核心、725 項 HTTP、58 項世界串流、100 項 Node、484 項 Chromium、106 項管理包及 434 項同機原生檢查。
- 五房獨立與合併兩種模式各有 25 個同時連線的模擬玩家。六場共核對 1,949 幀回放、50 份原玩家戰績及 11 份 CSV。合併批次結束後，管理台重新開啟獨立批次第 3 房原回放，下載的 ZIP 與原檔逐位元組一致。
- 程式已推送到 `main`。GitHub Actions 因帳務或支出上限未啟動。Quest 3、VIVE、跨機與廠商硬體待驗。 [驗證紀錄](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md) [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42559077055)

## 2026-11-09 房卡觀戰與全館原場次回放

Windows 管理包 0.31.38 可從房卡直接開啟本房即時俯視，或從全館收尾直接開啟原場次回放。未封存的片段以收尾表確認的尾端為播放界線。原錄製無法取得時會保留未選取狀態。

478 項 Chromium、106 項管理包及 433 項同機原生檢查通過。兩種模式各 25 名同機模擬玩家。實際管理台開啟五個獨立錄製與一個合併錄製，核對原來源、播放位置、房間視角和封存尾端。六場核對 1,829 幀回放、50 份戰績及雙封存。Quest 3、VIVE、跨機及廠商硬體待實機驗證。

來源 `68c05ac`。 [操作方式](https://github.com/peca12968/vr-command-center/blob/main/docs/WORLD_RECORDING.md#從房卡或全館收尾開啟) · [本機驗證](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-09-房卡觀戰與全館原場次回放)。GitHub Actions 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42558050459)

## 2026-11-09 全館結束批次戰績 ZIP

Windows 管理包 0.31.37 在全館收尾提供原結束批次的戰績 ZIP。所有原場次的戰鬥報表可匯出後，下載包含各房 CSV 與原場次清單。房間重用與後續批次不影響原批次網址。

473 項 Chromium、106 項管理包及 429 項同機原生檢查通過。獨立與合併各 25 名同機模擬玩家，獨立 ZIP 含五份分房 CSV，合併 ZIP 含全場與五份分房 CSV。每份 CSV 與逐一下載逐位元組一致，核對 50 份原玩家戰績、1,898 幀回放與雙封存。Quest 3、VIVE、跨機及廠商硬體待實機驗證。

來源 `88adc67`。 [報表操作](https://github.com/peca12968/vr-command-center/blob/main/docs/REPORTS.md#下載全館結束批次) · [本機驗證](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-09-全館結束批次戰績-zip)。GitHub Actions 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42557039331)

## 2026-11-09 全館敵軍策略

Windows 管理包 0.31.36 可由主控一次調整執行中場次的守備、巡邏、推進及自動攻擊，保留各場原有的敵軍目標數。房卡依各場有效遊戲快照確認策略。

468 項 Chromium、106 項管理包及 414 項同機原生檢查通過。五房獨立與合併各 25 個同時連線的模擬玩家，每人都受到同房敵軍傷害。兩種模式各有 105 筆傷害，均在自動攻擊開啟期間。12 個策略確認快照對上封存回放，六場核對 1,908 幀、50 份戰績、11 份 CSV 及雙封存。Quest 3、VIVE、跨機及廠商硬體待實機驗證。

來源 `f91ff0d`。 [操作方式](https://github.com/peca12968/vr-command-center/blob/main/docs/LAYOUT.md#全館敵軍策略) · [本機驗證](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-09-全館敵軍策略)。GitHub Actions 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42555945107)

## 2026-11-09 全館即時環境

Windows 管理包 0.31.35 可由主控一次設定執行中場次的天氣、日夜與閃電。送出前核對各場階段與環境序號，接受後以各場有效快照確認。VR／MR 模式與保存任務版本保留。

464 項 Chromium、106 項管理包及 388 項同機原生檢查通過。五房獨立與合併各有 25 個同時連線的模擬玩家，兩種模式均完成暴風雨夜開啟閃電及晴朗白天關閉閃電。12 個確認封包逐欄對上原封存回放，六場共核對 1,276 幀回放、50 份戰績、11 份 CSV 與清理。Quest 3、VIVE、跨機與廠商硬體待實機驗證。

來源 `0336bf9`。 [操作方式](https://github.com/peca12968/vr-command-center/blob/main/docs/ENVIRONMENT.md#全館即時環境) · [本機驗證](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-09-全館即時環境)。GitHub Actions 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42554756144)

## 2026-11-09 全館批次結束與封存總覽

Windows 管理包 0.31.34 可由主控一次結束所有未結束的場次。收尾總覽顯示最近一批原場次的戰鬥統計與世界回放封存，房間重用後仍可開啟原紀錄。

460 項 Chromium、106 項管理包及 380 項同機原生檢查通過。五房獨立與合併各有 25 個同時連線的模擬玩家。收尾總覽對上原場次及雙封存，六場共核對 1,080 幀回放、50 份戰績、11 份 CSV 與清理。Quest 3、VIVE、跨機與廠商硬體仍待實機驗證。

來源 `3672d39`。 [操作方式](https://github.com/peca12968/vr-command-center/blob/main/docs/SESSION_CLOSURE.md#全館批次結束) · [本機驗證](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-09-全館批次結束與封存總覽)。GitHub Actions 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42553671302)

## 2026-11-09 全館批次開始

Windows 管理包 0.31.33 支援主控一次開始所有準備場次。每場須有名冊與當前序號的有效準備快照，VR 要求有效姿態，MR 要求 Quest 3 追蹤就緒。等待期間顯示房號，接受管理命令後由各房執行中快照確認。

453 項 Chromium、106 項管理包及 372 項同機原生檢查通過。兩種模式各有 25 個同時連線的模擬玩家。獨立模式保存五筆開始命令，合併模式只保存一筆並由五房共用。六場核對 1,100 幀回放、50 份戰績、11 份 CSV、雙封存與清理。Quest 3、VIVE、跨機與廠商硬體仍待實機驗證。

來源 `34abbfa`。 [全館操作](https://github.com/peca12968/vr-command-center/blob/main/docs/MISSION_CLOCK.md#全館開始) · [本機驗證](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-09-全館批次開始)。GitHub Actions 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42552680211)

## 2026-11-09 全館命令的遊戲端確認

Windows 管理包 0.31.32 的五房房卡顯示全館暫停與繼續的遊戲端確認。全館繼續要等 VR 或 MR 各目標回傳有效的暫停快照，MR 另須滿足當前追蹤條件。

449 項 Chromium、106 項管理包和 366 項同機原生檢查通過。合併與獨立各有 25 個同時連線的模擬玩家，合併五房共用同一筆遊戲端確認，獨立第 2 房維持個別暫停。六場共 1,194 幀回放、50 份戰績、11 份 CSV、雙封存與清理。Quest 3、VIVE、跨機和廠商硬體待實機驗證。

來源 `25ee024`。 [全館操作](https://github.com/peca12968/vr-command-center/blob/main/docs/MISSION_CLOCK.md#全館暫停與繼續) · [本機驗證](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-09-全館命令的遊戲端確認)。GitHub Actions 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42551574563)

## 2026-11-09 全館暫停與繼續

Windows 管理包 0.31.31 讓主控一次暫停當時執行中場次，並只繼續仍處於全館暫停階段的場次。以同一 SQLite 交易保存，預覽改變或 MR 追蹤尚未就緒時整批拒絕，重送取回原回條。

445 項 Chromium、106 項管理包及 366 項原生檢查通過。合併與獨立各 25 個同機模擬玩家，獨立房保留個別暫停，合併場各用一次暫停與繼續。六場共 1,140 幀回放、50 份戰績、11 份 CSV、雙封存及清理。實體頭盔、跨機與廠商硬體待驗。

來源 `82afb95`。 [全館操作](https://github.com/peca12968/vr-command-center/blob/main/docs/MISSION_CLOCK.md#全館暫停與繼續) · [本機驗證](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-09-全館暫停與繼續)。GitHub Actions 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42550465179)

## 2026-11-09 五房房卡任務計時

Windows 管理包 0.31.30 的五房總覽從最近接受的有效快照顯示活動時間或自動結束倒數。舊階段或過期快照會清除時間，房控只讀取本房。

438 項 Chromium、106 項管理包與 360 項原生檢查通過。合併及獨立模式各 25 個同機模擬玩家。獨立房暫停時，另一房繼續計時。合併場五房共用同一值。六場共 1,037 幀回放、50 份戰績、11 份 CSV、雙封存和清理。頭盔、跨機及廠商硬體仍待驗。

來源 `cdc9a1d`。 [房卡操作](https://github.com/peca12968/vr-command-center/blob/main/docs/MISSION_CLOCK.md#五房房卡) · [本機驗證](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-09-五房房卡任務計時)。GitHub Actions 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42549072359)

## 2026-11-09 Quest 3 裝置清單與 25 席批次部署

以五房 ZIP 及 25 席裝置清單預檢 ADB 授權、Quest 3 型號和已啟用的應用程式版本。明確指定批次套用時，先向管理服務核對票券、名冊、校正原檔與公布端點，再按房號與席位套用設定並請求啟動。中途失敗回報已處理、失敗與未嘗試席位。

28 項 PowerShell、10 項伺服器包、9 項 Chromium 專項及 103 項原生檢查通過。合併和獨立模式各用原生伺服器及實際簽發的 25 份設定核對模擬 ADB，六個 MR 準備場雙封存、476 幀回放，活動場次為零。Quest 3 實機、VIVE、跨機與廠商設備仍待驗。

來源 `57cacd6`。 [部署操作](https://github.com/peca12968/vr-command-center/blob/main/docs/QUEST3.md#用裝置清單部署-25-席) · [本機驗證](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-09-quest-3-裝置清單與-25-席批次部署)。GitHub Actions 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42548148669)

## 2026-11-09 直接從五房 ZIP 部署 Quest 席位

部署工具可直接讀取管理包 0.31.29 的原始 ZIP。可預檢 25 席，或指定房號、席位與 Quest 裝置序號部署。線上模式同時驗證票券、名冊、原始校正檔及各場公布的端點。

通過 25 項 PowerShell、9 項解壓包 Chromium 及 97 項原生檢查。用實際簽發的合併／獨立 ZIP 各核對 25 席，均取回第 4 房第 2 席。模擬 ADB 確認只寫入指定席位與房間原檔。六個 MR 準備場完成雙封存、286 幀回放，活動場次為零。實體裝置安裝、跨機、VIVE 與廠商硬體待驗。

來源 `ebe5d84`。 [部署操作](https://github.com/peca12968/vr-command-center/blob/main/docs/QUEST3.md#直接用-zip-預檢或部署單席) · [本機驗證](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-09-直接從五房-zip-部署-quest-席位)。GitHub Actions 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42547379596)

## 2026-11-09 Quest 3 MR 五房部署包

Windows 管理包 0.31.29 支援一次下載五房 Quest 3 MR 部署包，含五房連線 ZIP、鎖定校正原檔及 `venue.json`。主控可從一個合併場或五個獨立場配發 25 席，按伺服器已公布的端點及當前名冊生成。

通過 432 項完整 Chromium、106 項管理包及 95 項原生檢查。一個合併場及五個獨立場的 Windows 遊戲程序公布原 UDP 端點，兩種模式各 25 席通過 PowerShell 線上預檢。六場完成雙封存及 287 幀回放，活動場次為零。實體 Quest 3、VIVE、跨機及廠商設備仍待驗。

來源 `1f4ff7f`。 [部署操作](https://github.com/peca12968/vr-command-center/blob/main/docs/QUEST3.md#從主控台下載五房部署包) · [本機驗證](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-09-quest-3-mr-五房部署包)。GitHub Actions 因帳務或支出上限未啟動。 [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42546517393)

## 2026-11-09 五房獨立場次一次準備

Windows 管理包 0.31.28 新增主控專用「五房各自獨立」。使用同一已保存的 VR 或 MR 任務版本，一次建立五個 Preparing 場次。任一房忙碌或 SQLite 寫入失敗時整批不成立，遺失回覆可用原請求取回原五場。

本機通過 892 項核心、725 項 HTTP、58 項世界串流、426 項完整 Chromium、12 項解壓包 Chromium 專項及 106 項管理包檢查。三個解壓包同機通過 378 項原生檢查，獨立及合併各 25 個 Unity 玩家程序，合計 1,683 幀回放、50 份戰績、11 份 CSV 與雙封存。活動場次為零。Quest 3、VIVE、場館跨機與廠商設備待驗。

來源 `08c37f9`，操作與本機驗證見[專案進度](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-09-五房獨立場次一次準備)。[GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42545258202) 因帳務或支出上限未執行任何步驟。

## 2026-11-09 即時模擬閘道取消待確認批次

模擬器 0.2.1 在等候 ACK 時仍檢查場次。扣住 ACK 的實測顯示，暫停或結束時原連線在設備收到批次後 140 至 156 毫秒關閉，舊 0.2.0 同一排演為 891 至 906 毫秒。

解壓包的原生 Windows 驗證，五房獨立及合併各 25 位 Unity 模擬玩家。213 筆模擬確認逐筆對回原受傷事件和入場。共 407 項原生檢查、1,694 幀回放、50 份原玩家戰績。測試程序均已清理。廠商設備、頭盔及跨機場館仍待驗。

功能 90df932，文件 ed8b6d9。GitHub Actions 因帳務或支出上限未啟動。 [操作方式](https://github.com/peca12968/vr-command-center/blob/main/docs/HARDWARE.md#即時模擬閘道) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42543802908)

## 2026-11-09 即時硬體模擬閘道

模擬器 0.2.0 可依房間、玩家、當次入場及席位將即時回饋送到本機模擬程序。批次確認後再次核對場次階段與事件。錯誤回覆、逾時、斷線、暫停及結束時的批次各有本機驗證。

解壓包與真實自含管理服務以合成戰鬥事件驗證五房獨立、五房合併各 25 筆模擬確認。兩輪共 50 筆，每房五筆，活動場次為零。879 項核心、38 項離線、14 項即時檢查通過。廠商設備協定、實際輸入輸出、停止與場館跨機仍待驗收。

功能 80e4985，文件 74128e4。GitHub Actions 因帳務或支出上限未啟動。 [閘道操作](https://github.com/peca12968/vr-command-center/blob/main/docs/HARDWARE.md#即時模擬閘道) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42542988118)

## 2026-11-09 房間即時戰鬥回饋

Windows 管理包 0.31.27 提供房間限定的即時射擊與受傷事件。依場次階段、現行入場及接受時間篩選，暫停、結束或重連均有明確游標行為。

同一台 Windows 的原生 Unity Simulation 驗證，五房獨立及合併各 25 個玩家程序。212 筆即時傷害訊號逐筆對回正式接受的戰鬥事件，兩輪共 387 項原生檢查、1,609 幀回放及 50 份玩家原戰績。廠商協議、設備輸入輸出及停止方式仍待實機。

功能 7fa86c3，文件 32ad95f。GitHub Actions 因帳務或支出上限未啟動。 [介面](https://github.com/peca12968/vr-command-center/blob/main/docs/HARDWARE.md#即時戰鬥回饋介面) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42541682674)

## 2026-11-09 五房 MR 部署線上核對

管理包 0.31.26 與 PowerShell 部署工具可由主控一次核對 25 張票券的簽章、現行入場名額及鎖定的校正原檔。解壓包的合併與獨立兩種模式均通過 25 席，各自拒絕偽造票券與重配前票券，受影響房間重下載 ZIP 後恢復通過。六場均結束，活動場次為零。Quest 3 實機、VIVE、場館跨機與廠商硬體仍待驗收。

功能 4bbc2e7，文件 378493a。697 項 HTTP、21 項 PowerShell 與 106 項管理包檢查等本機驗證通過。GitHub Actions 因帳務或支出上限未啟動。 [測試紀錄](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-09-五房-mr-部署線上核對) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42540847623)

## 2026-11-09 MR 伺服器啟動前核對

Windows 啟動器 1.6 顯示尚未鎖定的 MR 房號，CLI 與 WinForms 都在建立 Unity 程序前重新核對鎖定。單房及五房合併的未鎖定場次經實際 CLI 驗證，均在建立子程序與工作目錄前被拒絕。

本機 51 項 CLI／API、46 項 Framework 與 137 項伺服器包檢查通過。另以五房合併 25 席名冊啟動原生 MR 伺服器，核對 UDP、雙封存及原程序退出。WinForms 初始畫面被 Windows 防火牆提示覆蓋，GUI 互動、實體追蹤及場館跨機仍待驗。

功能 a9390c2，文件 703c69a。GitHub Actions 因帳務或支出上限未啟動。 [測試紀錄](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-09-mr-伺服器啟動前核對) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42540162892)

## 2026-11-09 Quest 3 MR 席位部署核對

控制台 0.31.25 可逐席核對連線檔及房間原始校正檔。管理服務驗簽及比對當前名額與鎖定雜湊，結果標明房間及席位。房控限本房，主控可核對全場。

解壓後的管理服務共核對 173 筆 HTTP。五房合併與五房獨立各 25 席相符，30 筆錯席、改檔與跨房請求遭拒。活動場次為零，原管理程序正常停止。417 項 Chromium 回歸、16 項解壓包專項及 106 項管理包檢查通過。Quest 3 實機、VIVE、場館跨機及廠商硬體仍待驗。

功能 ecf4f0d，文件 a4a7279。GitHub Actions 因帳務或支出上限未啟動。 [測試紀錄](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-09-quest-3-mr-席位部署核對) · [GitHub Actions](https://github.com/peca12968/vr-command-center/actions/runs/42539048680)

## 2026-11-09 MR 連線檔與部署預檢交接

- 控制台 0.31.24 的 MR 單席與整房連線檔包含該房鎖定的校正檔 SHA-256。房控可在主控鎖定後配票，PowerShell 依連線檔自動選用 MR，並在呼叫 ADB 前拒絕雜湊不符的檔案。
- 實際管理包簽發並驗簽 50 張票券。全連線和獨立模式各 25 席通過預檢，各拒絕一份變動過的同房檔案。單席模擬 ADB 驗證錯檔零呼叫，正確原檔依原始位元組寫入。實體頭盔、VIVE 與場館連線待驗。
- 404 項 Chromium、19 項 PowerShell、106 項 Windows 管理包檢查通過。GitHub Actions 因帳務或支出上限未啟動。 [部署操作](https://github.com/peca12968/vr-command-center/blob/main/docs/QUEST3.md#quest-3-場地對位部署) · [驗證紀錄](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-09-mr-連線檔與部署預檢交接)

## 2026-11-09 主控台鎖定 MR 校正檔

- 控制台 0.31.23 的 MR 場次面板可逐房選檔，核對量測及原檔 SHA-256。全數核對才可一次鎖定。回應遺失時沿用原命令，歷史場次可查看原雜湊。
- 最終 97 項 Node、401 項 Chromium、19 項專項及 106 項可攜管理包檢查通過。用最終管理包在瀏覽器鎖定五房，再由原 0.48.0 Windows 伺服器啟動同一 25 席名冊，完成雙封存與 10 幀回放。這輪涵蓋同機管理與伺服器流程，實體裝置及跨機待驗。
- GitHub Actions 因帳務或支出上限未啟動。 [操作方式](https://github.com/peca12968/vr-command-center/blob/main/docs/QUEST3.md#啟動-mr-伺服器前鎖定校正檔) · [驗證紀錄](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-09-主控台鎖定-mr-校正檔)

## 2026-11-09 MR 校正檔入場鎖定

- 遊戲 0.48.0／NGO 31。主控在 Preparing 透過管理 API 鎖定各房校正檔 SHA-256，伺服器啟動與入場核對鎖定值。五房鎖定資料已驗證實際管理服務重開和精確命令重送。
- Windows 真正伺服器拒絕同一房的另一份有效校正檔、錯房、舊格式及一般 VR 入場，接受正確雜湊。測試客戶端為替換入場資料的 Windows 副本，原伺服器及發行包保持完整。265 項 Unity 及 137 項 Windows 伺服器包檢查通過。
- 另跑 Windows 同機五房全連線 25 端及五房獨立各 5 端，50 份戰績獲確認，完整回放 1,856 幀。Windows 與 Quest APK 同源建置，Quest 3 實機、VIVE、透視、跨機及廠商硬體待驗。
- GitHub Actions 因帳務或支出上限未啟動。 [主控操作](https://github.com/peca12968/vr-command-center/blob/main/docs/QUEST3.md#啟動-mr-伺服器前鎖定校正檔) · [驗證紀錄](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-09-mr-校正檔入場鎖定)

## 2026-11-09 Quest 五房部署預檢

- 用五份整房 ZIP 與各房校正檔一次核對 25 席。檢查場次、房號、席位、重複入場識別、效期與 UDP 端點，報告不含票券。
- 16 項部署測試通過。實際可攜管理服務簽發並逐張驗證 50 張票券，全連線與獨立模式各 25 席通過，各拒絕一份錯場清單。頭盔安裝、追蹤、場地校正及 UDP 待驗。
- GitHub Actions 因帳務或支出上限未啟動。 [操作方式](https://github.com/peca12968/vr-command-center/blob/main/docs/QUEST3.md#五房-25-席部署預檢) · [開發紀錄](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-09-quest-五房部署預檢)

## 2026-11-09 XR 追蹤恢復與武器重新啟用

- 遊戲 0.47.1 在 VR／MR 追蹤、校正或參戰條件失效時撤下武器輸入。恢復後須先放開右手扳機與換彈鍵，再主動按下。263 項 Unity 測試通過，其中包含虛擬 Touch 追蹤及按鍵測試。
- 同源 Windows 與 Quest ARM64 APK 完成建置，APK 版本碼 60 且 v2 開發簽章通過。兩個 Windows 包解壓後各核對 328 個檔案，玩家啟動器另通過 19 項。
- Windows 同機五房全連線 25 端、五房獨立各 5 端。25 項檢查通過，六場共 100 發、100 中、50 擊殺，50 份原戰績獲伺服器確認，6 份 CSV 與雙封存、1,848 幀完整回放通過。
- GitHub Actions 因帳務或支出上限未啟動。Quest 3 實機、VIVE、MR 透視、跨機 25 位真人及廠商硬體仍待驗。 [開發紀錄](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-09-xr-追蹤恢復與武器重新啟用)

## 2026-11-09 MR 執行中追蹤提示

- 第 1／4／5 項。控制台 0.31.22 於 MR 執行中在房卡及場次面板顯示缺少追蹤的存活席位。五房 25 席的合成快照經實際 API／WebSocket 發布，僅房間 4 第 2 席缺少追蹤，淘汰第 5 席保留紀錄。過期清除舊警示，新的追蹤快照恢復計數，並已驗證人工暫停、繼續及雙封存。
- 最終 852 項核心、621 項 HTTP、58 項世界串流、97 項 Node、385 項 Chromium 通過。解壓管理包通過 106 項及 22 項 MR 專項。實機追蹤、透視與跨機仍待。[執行中追蹤](https://github.com/peca12968/vr-command-center/blob/main/docs/PLAYER_READINESS.md#執行中追蹤)
- 功能提交 `6498b72` 已推送。GitHub Actions 因帳務或支出上限未啟動。[工作紀錄](https://github.com/peca12968/vr-command-center/actions/runs/42531048443)

## 2026-11-09 MR 暫停後恢復追蹤

- 第 1／4／5 項。控制台 0.31.21 要求最新的 MR 暫停快照確認存活席位的追蹤，再接受繼續。五房 25 席以合成追蹤和實際 API／WebSocket 驗證拒絕舊快照及缺少姿態。房間 4 第 2 席恢復後繼續，已淘汰第 5 席保留戰績，原 25 席及開始時間不變，重送保留回條並完成雙封存。
- 最終 847 項核心、621 項 HTTP、58 項世界串流、95 項 Node、382 項 Chromium 通過。解壓管理包通過 106 項及 19 項 MR 專項。首輪完整回歸發現原開場提示被覆蓋，已修正重驗。實機對位、透視與跨機仍待。[繼續操作](https://github.com/peca12968/vr-command-center/blob/main/docs/PLAYER_READINESS.md#暫停後繼續)
- 追蹤閘門 `8ae7a33` 與最終提示修正 `fb1060d` 已推送。GitHub Actions 因帳務或支出上限未啟動。[最終工作](https://github.com/peca12968/vr-command-center/actions/runs/42530141149)

## 2026-11-09 MR 開場檢查與等候席位

- 第 1／4／5 項。控制台 0.31.20 在開始任務旁顯示各房追蹤就緒人數和等候席位。五房 25 席合成追蹤經實際 WebSocket 發布。瀏覽器指出房間 4 的第 2、5 席等候，並在快照過期或管理序號未同步時撤下提示。補齊後由主控在 UI 開場，最後雙封存。
- 832 項核心、621 項 HTTP、58 項世界串流、94 項 Node、375 項 Chromium 通過。解壓管理包另通過 106 項和 12 項 MR 專項。實機追蹤、透視及跨機容量仍待。[開場操作](https://github.com/peca12968/vr-command-center/blob/main/docs/PLAYER_READINESS.md#mr-開場條件)
- 功能提交 `c0c6f9b` 已推送。GitHub Actions 因帳務或支出上限未啟動。[工作紀錄](https://github.com/peca12968/vr-command-center/actions/runs/42528950179)

## 2026-11-09 Quest 3 部署檔離線預檢

- 第 4／5 項。部署可先用 PowerShell 7 的 `-CheckOnly` 核對房號、席位、效期及校正檔 SHA-256。實際管理 API 簽發五房 25 份玩家票券全部對上同房校正檔，五組錯房配對被拒絕。
- 本機 9 項 PowerShell 與 621 項 HTTP 檢查通過。模擬 ADB 核對原檔變動仍使用預檢內容，以及啟用失敗時保留舊設定及清除暫存。Quest 0.47.0 APK 的 ARM64 與 v2 開發簽章已複驗。實機安裝、追蹤及透視仍待驗收。[部署操作](https://github.com/peca12968/vr-command-center/blob/main/docs/QUEST3.md#quest-3-場地對位部署)
- 功能提交 `020d47d` 已推送。GitHub Actions 因帳務或支出上限未啟動。[工作紀錄](https://github.com/peca12968/vr-command-center/actions/runs/42527893009)

## 2026-11-09 五房 UDP 丟包驗證

- 第 1／4／9／11 項。兩種五房模式各 25 位同機 Windows 模擬玩家，入場後各連線雙向約 5% 週期性 UDP 丟包。24 項原生檢查通過，核對 100 發、4,111 幀完整回放、六份 CSV、雙封存及全部 50 份原個人戰績確認。
- 1,500 次應用層探測有 183 次逾時，與戰績送達分開計數。跨機、實際無線環境、25 位真人及頭盔仍待驗收。[進度及本機驗證](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-09-五房-udp-丟包驗證)
- 功能提交 `4943faf` 已推送。GitHub Actions 因帳務或支出上限未啟動。[工作紀錄](https://github.com/peca12968/vr-command-center/actions/runs/42526857101)

## 2026-11-09 掩體移除通路試算

- 第 7／8 項。Windows 控制台 0.31.19 可試算移除一件掩體後新開通的出生位路徑，並以黃色虛線疊加。首輪測試找出選物件會誤標草稿變更，已修正。最終瀏覽器核對五席通路、無效試算及切換物件後延遲回應。[通路操作](https://github.com/peca12968/vr-command-center/blob/main/docs/LAYOUT.md#出生位通路預覽)
- 本機通過 825 項核心、621 項 HTTP、366 項 Chromium 及 106 項管理包檢查。原生 Windows 驗證另通過 136 項，核對六場已保存掩體座標及缺口、544 幀回放、10 份模擬玩家戰績。實地行走、跨機及頭盔仍待驗收。[驗證紀錄](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-09-掩體移除通路試算)
- 功能提交 `d871b52` 已推送。GitHub Actions 因帳務或支出上限未啟動。[工作紀錄](https://github.com/peca12968/vr-command-center/actions/runs/42526265393)

## 2026-11-09 五房原生玩家射擊與戰績

新增 `--marksmanship`，用既有 Windows 0.47.0 開發版執行檔、自動桌面輸入及正常油桶配置驗證。五房獨立與連線各 25 位同機模擬玩家，每位兩發兩中、一擊殺。共 100 發、100 中、50 擊殺、1,976 幀完整回放與 50 份獲確認的個人戰績。Linked ZIP 六份 CSV 對上原個別匯出。這次使用不自動攻擊的守備敵軍。 [驗證紀錄](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-09-五房原生玩家射擊與戰績)

25 項原生射擊檢查、5 項原短場回歸與 22 項 Python 通過。GitHub Actions 因帳務或支出上限未啟動。 [驗證程式](https://github.com/peca12968/vr-command-center/commit/a595be0eca3475c940316c569f6aa78025e04678) · [Actions](https://github.com/peca12968/vr-command-center/actions/runs/42525329858)

## 2026-11-09 五房原生交火與戰績對照

使用既有 Windows 0.47.0 遊戲、玩家包及 0.31.18 管理包，在五房獨立和五房連線各 25 個同機模擬玩家中啟停敵軍攻擊。每位原玩家都受傷。共逐格核對 215 筆同房傷害、1,620 幀回放及 50 份玩家戰績。Linked ZIP 的六份 CSV 與原檔一致。這次驗證範圍是敵軍造成的耗損與中彈，模擬玩家未發射武器。 [驗證紀錄](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-09-五房原生交火與戰績對照)

377 項 Windows 原生三包及 10 項 Python 檢查通過。GitHub Actions 因帳務或支出上限未啟動。 [驗證程式](https://github.com/peca12968/vr-command-center/commit/25092b5fa57c9e6d8cbba84648a893d1b1839266) · [Actions](https://github.com/peca12968/vr-command-center/actions/runs/42524680190)

## 2026-11-09 五房戰績 ZIP

控制台 0.31.18 可由主控一次下載全場及五份分房 CSV。Windows 三個可攜包以每房 5 位同機模擬玩家驗證，Linked ZIP 的六份檔案逐位元對上原有 CSV 與同場 25 份戰績。六個原生場次共 50 份戰績獲確認，878 幀回放，該輪為零交火。 [操作說明](https://github.com/peca12968/vr-command-center/blob/main/docs/REPORTS.md#一次下載五房戰績)

347 項 Windows 三包、106 項管理包、825 項核心、621 項 HTTP 及 362 項 Chromium 檢查通過。GitHub Actions 因帳務或支出上限未啟動。 [功能提交](https://github.com/peca12968/vr-command-center/commit/63da0283b229a1f2cbe8267e8eacfc51bbc4b741) · [Actions](https://github.com/peca12968/vr-command-center/actions/runs/42523999292)

## 2026-11-09 五房觀戰快速切換

控制台 0.31.17 在即時觀戰與回放提供全場及各房的快速切換，保持俯視角度並顯示同一快照的連線玩家、存活敵軍及房內玩家統計。原生 Windows 0.47.0 五房場次以一房一位同機模擬玩家驗證，房間 1 的即時耗損與房間 5 的第 77 格回放均對上原快照。五份玩家戰績取得伺服器確認。 [操作說明](https://github.com/peca12968/vr-command-center/blob/main/docs/WORLD_RECORDING.md)

359 項 Chromium、92 項 Node、58 項世界串流及 106 項 Windows 管理包檢查通過。GitHub Actions 因帳務或支出上限未啟動。 [功能提交](https://github.com/peca12968/vr-command-center/commit/f17408d3365cac7e1c2fcf865113833565ec0aad) · [Actions](https://github.com/peca12968/vr-command-center/actions/runs/42523418102)

## 2026-11-09 五房開場條件預覽

控制台 0.31.16 顯示保存版本、房間、簡報、時間、初始環境、敵軍及每房物件。實際 Windows 0.47.0 五房連線驗證使用選定的歷史版，五個同機模擬玩家各入一房，確認暴風雨夜間、閃電、7 名巡邏敵軍及 10 件掩體。雙封存至第 31 格，五份玩家戰績獲伺服器確認。 [操作說明](https://github.com/peca12968/vr-command-center/blob/main/docs/MISSION_VERSIONS.md)

357 項 Chromium、603 項 HTTP 及 106 項 Windows 管理包檢查通過。GitHub Actions 因帳務或支出上限未啟動。 [功能提交](https://github.com/peca12968/vr-command-center/commit/db6c9cfe08b357dda8fd8f9934acc37e69b1979e) · [Actions](https://github.com/peca12968/vr-command-center/actions/runs/42522638107)

## 2026-11-09 接續補送後的新保存片段

控制台 0.31.15 可在未封存回放的尾端接續補送的影格。Windows 原生程序退出後，房控以 Chromium 看完第 16 格。補送後只請求第 17 至 46 格，最終影格與原始統計一致，並保留未封存狀態。新版 Windows 管理包通過 106 項檢查，另有 354 項 Chromium 檢查通過。這次原生驗證使用一位同機模擬玩家。 [操作說明](https://github.com/peca12968/vr-command-center/blob/main/docs/WORLD_RECORDING.md#回放未封存的已保存片段)

GitHub Actions 因帳務或支出上限未啟動。 [功能提交](https://github.com/peca12968/vr-command-center/commit/ffff9e6a303e3961820844276ce36ed66f3658e9) · [Actions](https://github.com/peca12968/vr-command-center/actions/runs/42521882313)

## 2026-11-09 遊戲程序中斷後補送原始回放

Windows 0.47.0 原生遊戲子程序終止後，修正後的 WorldRelay 可依原時鐘版本補送世界及戰鬥紀錄。測試保留兩份原始 journal，API 從 18 幀補到 46 幀，戰鬥事件由 1 筆補到 4 筆。房間管理員回放至原尾端，世界與戰鬥保持未封存，CSV 與場館 ZIP 維持待確認。另以 TelemetryRelay 重送戰鬥副本核對去重。這次使用一個同機模擬玩家。 [開發進度](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md#2026-11-09-遊戲程序中斷後補送原始回放)

Windows 建置及 825 項核心、603 項 HTTP、58 項世界串流通過。GitHub Actions 因帳務或支出上限未啟動。 [功能提交](https://github.com/peca12968/vr-command-center/commit/560da7b86f69579b09ed71fbaedf211926e3ecbb) · [Actions](https://github.com/peca12968/vr-command-center/actions/runs/42521177480)

## 2026-11-09 遊戲伺服器等待原管理服務恢復

- Windows 伺服器啟動器 1.5 在就緒後可等待暫時性管理讀取故障，恢復窗口 15 秒。原 API 回來後核對同一場次、來源與序號。權限、資料錯誤及逾期仍會以未完成收尾。
- 實際終止管理 API 後，舊版停止原遊戲。新版同實例重開測試通過 16 項，記錄一次 9,292 ms 中斷與一次恢復。原玩家連線延續，119 幀回放中 78 幀在中斷時暫停且固定於第 31 tick，原戰績、CSV、驗收 ZIP 及雙封存一致。持續失聯通過 11 項，保留未完成紀錄。
- 新封裝通過 147 項一般 Windows 原生回歸、38 項清單 CLI／API 與 42 項 Framework 檢查。GitHub Actions 因帳務或支出上限未啟動。跨機、25 位真人、頭盔及廠商硬體仍待驗。

[管理恢復與部署](https://github.com/peca12968/vr-command-center/blob/2ef1181e2a184cf28841c4e0070bc33c3a482089/docs/WINDOWS_SERVER_PACKAGE.md#管理服務短暫中斷) · [驗證結果](https://github.com/peca12968/vr-command-center/blob/2ef1181e2a184cf28841c4e0070bc33c3a482089/docs/PROGRESS.md#2026-11-09-遊戲伺服器保留原場次等待管理恢復)

## 2026-11-09 主控下載場館驗收資料

- 控制台 0.31.14 的「任務收尾」提供全館主控下載場館驗收 ZIP。通過開始與結束、雙封存、端點及名冊統計核對後，提供同場次的名冊、統計與公告端點三份 JSON。
- Windows 新管理包通過 106 項封裝檢查。Windows 0.47.0 三包通過 360 項同機原生檢查，共 913 幀回放、50 份戰績確認及 6 份 CSV。全連線的 ZIP 已實際解壓，與 25 份玩家戰績、UDP 來源及伺服器確認對上。
- 本機 825 項核心、603 項 HTTP、58 項串流、92 項 Node 與 352 項 Chromium 通過。GitHub Actions 因帳務或支出上限未啟動。實際跨機、頭盔與廠商硬體仍待驗。

[驗收操作](https://github.com/peca12968/vr-command-center/blob/f0c0883bccfc9090e72472a59d4840f36bfc57db/docs/EXTERNAL_CLIENTS.md#核對封存戰績與-udp-來源) · [驗證結果](https://github.com/peca12968/vr-command-center/blob/f0c0883bccfc9090e72472a59d4840f36bfc57db/docs/PROGRESS.md#2026-11-09-主控下載場館驗收資料)

## 2026-11-09 場館連線與戰績核對

- 新增場館離線驗收工具，將原玩家入場、伺服器觀察到的 UDP 來源、確認回條與世界及戰鬥封存逐位核對。摘要省略原始位址、票券與玩家身分。
- Windows 0.47.0 三包使用本機乙太網路位址，五房獨立和全連線各 25 個模擬玩家。通過 356 項原生檢查、895 幀回放、50 份戰績確認及 6 份 CSV。全連線 25 份原始資料可離線驗證，改標雙機時受控拒絕。實體雙機與場館容量仍待驗。
- 8 項工具測試及 4 項伺服器封裝測試在本機通過。Actions 因帳務或支出上限未啟動。

[驗收操作](https://github.com/peca12968/vr-command-center/blob/10bc614c00edf2b7099e5e344c8e399cf85ce04c/docs/EXTERNAL_CLIENTS.md#核對封存戰績與-udp-來源) · [驗證結果](https://github.com/peca12968/vr-command-center/blob/10bc614c00edf2b7099e5e344c8e399cf85ce04c/docs/PROGRESS.md#2026-11-09-場館連線與戰績核對)

## 2026-11-09 遊戲 0.47.0 角色同步壓縮

- 同機每種模式各 25 個 Windows 原生模擬玩家程序。全連線下行 UDP 負載由 17.523 降至 13.186 Mbit/s，減少 24.75%。五房獨立由 3.759 降至 2.909 Mbit/s，減少 22.60%。六場完成 4299 幀回放與 50 份戰績確認。
- 全連線 25 個玩家端與伺服器在五個檢查點共完成 130 次角色複本核對。Windows 伺服器包通過 147 項原生整合，Unity 260 項 EditMode 通過，Windows 與 Quest 3 APK 皆已建置並核對來源。
- 遊戲協定升至 NGO 30，伺服器與玩家端須一併更新。原生測試確認舊版會在入場核准前被拒絕。Windows 新版 WinForms 複驗受到防火牆提示遮擋，CLI 已通過。GitHub Actions 因帳務或支出上限未啟動。跨機、25 位真人、頭盔及廠商硬體仍待驗。

[開發及驗證紀錄](https://github.com/peca12968/vr-command-center/blob/a478537d4908c57c3cdee1825830aabf874e02d0/docs/PROGRESS.md#2026-11-09-壓縮即時角色同步) · [功能來源](https://github.com/peca12968/vr-command-center/commit/ccb18b6c1ab4934c9b0529fa29992beab713be6d)

## 2026-11-09 同機 UDP 流量量測

- 原 0.46.0 Windows 程序可用 `--udp-traffic` 在同機負載測試記錄每玩家、每房及全場的雙向 UDP 負載。量測使用共同 Running 視窗，獨立模式等暫停房間恢復後開始。
- 全連線與五房獨立各 25 端，分別量測 39.31／34.36 秒。全連線全場平均上／下行 0.646／17.523 Mbit/s，獨立 0.623／3.759 Mbit/s。20 項原生檢查、3,937 幀回放、50 份原戰績和 6 份 CSV 通過。五端另驗證可與往返探測一起使用，既有 UDP 延遲回歸通過。
- GitHub Actions 因帳務條件未啟動。跨機、網卡層頻寬、渲染幀率、25 位真人、頭盔與廠商硬體仍待驗。 [操作](https://github.com/peca12968/vr-command-center/blob/d54112a9209f493be991f075bd1b045a7c351fba/docs/EXTERNAL_CLIENTS.md#同機-udp-流量量測) · [驗證](https://github.com/peca12968/vr-command-center/blob/d54112a9209f493be991f075bd1b045a7c351fba/docs/PROGRESS.md#2026-11-09-同機-udp-流量量測)

## 2026-11-09 Windows 玩家連線量測

- Windows 0.46.0 開發版提供選用的遊戲連線量測。每位玩家最多 30 筆，報表分列應用層往返、逾時與 Unity 更新頻率。伺服器僅回覆已入場的連線。
- 實際同機無圖形 Windows 驗證兩種模式各 25 端，1,500 筆均有回覆，全連線與獨立 p95 各 22.24／22.18 毫秒。20 項整合檢查、4,501 幀回放、50 份原戰績與 6 份 CSV 通過。舊伺服器對照保存 30 次逾時、772 幀完整回放及原戰績確認。
- 259 項 Unity Editor、17 項 Python、最終玩家啟動器 19 項和伺服器包 135 項通過。Windows 及 Quest 3 ARM64 APK 已同源建置。GitHub Actions 因帳務條件未啟動。頻寬、渲染幀率、跨機 25 位真人、頭盔及廠商硬體仍待驗。 [操作](https://github.com/peca12968/vr-command-center/blob/113e029bf7cda7a593bcaca7f3c96e549b1ff4ed/docs/EXTERNAL_CLIENTS.md#windows-玩家連線量測) · [驗證](https://github.com/peca12968/vr-command-center/blob/113e029bf7cda7a593bcaca7f3c96e549b1ff4ed/docs/PROGRESS.md#2026-11-09-windows-玩家連線量測)

## 2026-11-09 場中敵軍增援

- 控制台 0.31.13 與伺服器 0.45.0 依已保存場地核對敵軍上限。暫時占用的出生點等待空位，其他房間及管理指令繼續運行。觀戰與回放顯示實際敵軍與存活數。
- 本機通過 825 項核心、603 項 HTTP、58 項世界串流、344 項 Chromium 與 258 項 Unity Editor 檢查。實際 Windows 伺服器包通過 147 項及 670 幀回放。增援場拒絕 85 名目標，成功補到 84 名、減回 1 名並暫停，保留原敵軍識別、雙封存及玩家戰績確認。
- Windows 及 Quest 3 ARM64 APK 0.45.0 已同源建置並保存於 F 槽。GitHub Actions 因帳務條件未啟動。Quest 3 實機、VIVE、跨機 25 位真人及廠商硬體仍待驗。 [操作說明](https://github.com/peca12968/vr-command-center/blob/8b86700ba41f3708bf50be84ce98dc1d5718b249/docs/LAYOUT.md#場中敵軍增援) · [本機驗證](https://github.com/peca12968/vr-command-center/blob/8b86700ba41f3708bf50be84ce98dc1d5718b249/docs/PROGRESS.md#2026-11-09-場中敵軍增援)

## 2026-11-09 主控建立 MR 場次

- 控制台 0.31.12 支援從 MR 任務建立單房或五房連線場次。Quest 3 名冊完成對位後，場控以最新 GameServer 追蹤快照確認開場。場中可調整天氣、時段與雷電。
- 本機通過 818 項核心、594 項 HTTP、58 項世界串流、342 項 Chromium 與 257 項 Unity Editor 檢查。實際最終 Windows 伺服器包通過 135 項，共 511 幀 VR 與 22 幀 MR 準備回放。MR 已驗證拒絕桌面票券、缺追蹤維持 Preparing、套用環境設定與雙封存。
- 同源 0.44.0 Windows 與 Quest 3 ARM64 APK 已建置，並核對 APK 透視功能宣告及 v2 Debug 簽章。WinForms 重驗在 Windows 防火牆提示出現後停在載入前。GitHub Actions 受帳務條件阻擋，工作未執行。
- Quest 3 實體追蹤與透視、跨裝置定位、VIVE 相容、跨機 25 位真人及廠商硬體仍待驗。 [操作說明](https://github.com/peca12968/vr-command-center/blob/97fd727567b77204e3a6e69dd7ae639e522d1d27/docs/QUEST3.md#主控建立-mr-場次) · [本機驗證](https://github.com/peca12968/vr-command-center/blob/97fd727567b77204e3a6e69dd7ae639e522d1d27/docs/PROGRESS.md#2026-11-09-主控建立-mr-場次)

## 2026-11-09 Quest 3 透視呈現

Unity 0.43.0 可在既有 VR 場次以 Quest 3 選用透視，搭配當次 A、B、C 場地校正。Meta 合成層呈現實景，虛擬敵軍、擺設與天氣沿用場次。 [部署方式](https://github.com/peca12968/vr-command-center/blob/798499142e937ac9e092a0bb229077df8294dcfa/docs/QUEST3.md#quest-3-透視呈現)

257 項 Unity Editor、800 項核心、581 項 HTTP、58 項串流及 18 項 Windows 原生檢查通過。兩個 Windows 包解壓後各核對 328 筆，玩家啟動器 19 項與伺服器包 124 項檢查通過。Quest ARM64 Development APK 已確認 Meta 透視功能、原生函式庫及 v2 Debug 簽章。 [驗證紀錄](https://github.com/peca12968/vr-command-center/blob/798499142e937ac9e092a0bb229077df8294dcfa/docs/PROGRESS.md#2026-11-09-quest-3-透視呈現)

Quest 3 實景與遮擋、場控建立 MR 場次、VIVE、跨機 25 位真人及廠商硬體仍待驗。GitHub Actions 因帳務條件未啟動。 [功能工作](https://github.com/peca12968/vr-command-center/actions/runs/42502509011/job/128798109302) · [打包工作](https://github.com/peca12968/vr-command-center/actions/runs/42502843815/job/128799110749)

## 2026-11-09 Unity 場地對位

Unity 0.42.0 讀取入場房間的校正檔，依當次 A、B、C 量測將頭部、雙手與瞄準方向轉成全館座標。追蹤原點更新後需重新量測。 [操作說明](https://github.com/peca12968/vr-command-center/blob/2afb61fbf115a814bca81af113c3c84b8699dbab/docs/LAYOUT.md#quest-3-場地對位)

本機通過 254 項 Unity Editor、800 項核心、581 項 HTTP、58 項世界串流及 18 項 Windows 原生檢查。兩種 Windows 拓撲合計六場、2,022 幀完整回放、10 份原玩家戰績及 10 筆伺服器確認。Windows 玩家與伺服器包、同源 ARM64 Quest Development APK 均已產出。 [驗證紀錄](https://github.com/peca12968/vr-command-center/blob/2afb61fbf115a814bca81af113c3c84b8699dbab/docs/PROGRESS.md#2026-11-09-unity-場地對位)

Quest 3 實機取樣、MR 透視、VIVE、跨機 25 位真人及廠商硬體仍待驗。GitHub Actions 因帳務條件未啟動。 [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42499467687/job/128788839838)

## 2026-11-08 MR 場地水平校正試算

Windows 控制台 0.31.11 在任務編輯頁接受同三個地面標記的遊戲與追蹤座標。A、B 決定平移和旋轉，C 獨立核對。三點平面誤差均在 5 公分內時可匯出房間專用 JSON。 [操作與座標契約](https://github.com/peca12968/vr-command-center/blob/dd5c4ec/docs/LAYOUT.md#mr-場地水平校正試算)

11 月 9 日完成重跑，800 項核心、92 項 Node、340 項 Chromium 及 106 項 Windows 管理包檢查通過。實際瀏覽器下載第五房 JSON 並與 API 回應逐欄比對，核對鏡像誤差與主控權限。 [驗證紀錄](https://github.com/peca12968/vr-command-center/blob/dd5c4ec/docs/PROGRESS.md#2026-11-08-mr-場地水平校正試算)

GitHub Actions 因帳務條件未啟動。頭盔取樣、實際套用、透視、跨機、廠商硬體及 25 位真人仍待驗。 [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42110672529/job/127537068586)

## 2026-11-06 遊戲伺服器公告前的 UDP 綁定核對

Windows 啟動器 1.3 會在公告之前向 Windows 核對原遊戲程序的 PID、本機 IPv4 和 UDP 埠。CLI 的就緒與結果檔保留啟動時的實際觀察，並分開記錄玩家公告位址。交付包沿用同一份 0.41.2 遊戲執行檔。 [部署說明](https://github.com/peca12968/vr-command-center/blob/5f4ec45/docs/WINDOWS_SERVER_PACKAGE.md#本機-udp-綁定確認)

38 項 CLI、33 項 Framework、私有乙太網路 374 項及 loopback 124 項整合檢查通過。Windows 獨立查詢核對五個單房端點、一個 Linked 端點及萬用綁定。私有乙太網路測試在兩種拓撲各有 25 個同機模擬玩家，共 910 幀正常回放與 50 份戰績。loopback 有 506 幀和 10 份戰績。 [驗證紀錄](https://github.com/peca12968/vr-command-center/blob/5f4ec45/docs/PROGRESS.md#2026-11-06-遊戲伺服器公告前的-udp-綁定核對)

GitHub Actions 因帳務條件未啟動。新版 WinForms 狀態、跨機、頭盔、廠商硬體及 25 位真人仍待驗。 [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42108137984/job/127528314944)

## 2026-11-06 中斷場次的已保存回放

控制台 0.31.10 顯示已接受的戰鬥筆數和錄製格數。來源中斷後可播放已保存片段，逐格、時間跳轉與續播都沿用開啟時的尾端。最終戰績依原封存條件提供。 [操作說明](https://github.com/peca12968/vr-command-center/blob/979c17a/docs/WORLD_RECORDING.md#回放未封存的已保存片段)

本機通過 792 項核心、58 項世界串流、92 項 Node、331 項 Chromium、111 項 Windows 整合及 105 項管理包檢查。中斷場次中，終止啟動器後確認原遊戲程序退出，回放完整讀出 22 格已保存資料，保留原傷害 20 和血量 80。已接受 1 筆戰鬥，兩種最終 CSV 均回 409，玩家也沒有收到最終結果。另有六場正常封存、531 幀回放與 10 份戰績。 [驗證紀錄](https://github.com/peca12968/vr-command-center/blob/979c17a/docs/PROGRESS.md#2026-11-06-中斷場次的已保存回放)

GitHub Actions 因帳務條件未啟動。跨機、頭盔、廠商硬體及 25 位真人仍待驗。 [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42106207634/job/127521593270)

## 2026-11-06 任務回放逐格檢視

控制台 0.31.9 可暫停後逐格檢視保存的射擊、命中、擊殺、受傷及換彈。單格事件、玩家和統計來自同一份快照，繼續回放時使用選定的原序號。 [操作說明](https://github.com/peca12968/vr-command-center/blob/a7438b9/docs/WORLD_RECORDING.md#暫停逐格檢視)

本機通過 792 項核心、53 項世界串流、91 項 Node、327 項 Chromium 和 105 項解壓管理包檢查。Windows 五房連線使用五個同機自動操作程式，6 項檢查、178 幀完整回放、5 份原玩家戰績及確認回條。單格回傳第 30 格五筆射擊，續播第 30、31 格均對上原封存回放。 [驗證紀錄](https://github.com/peca12968/vr-command-center/blob/a7438b9/docs/PROGRESS.md#2026-11-06-任務回放逐格檢視)

GitHub Actions 因帳務條件未啟動。Windows 鍵盤穿越、跨機、頭盔、廠商硬體及 25 位真人仍待驗。 [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42103740969/job/127513006266)

## 2026-11-06 五房戰績分房匯出

控制台 0.31.8 讓主控下載五房連線場次的全場或單房 CSV。房控畫面固定為所屬房間，分房端點拒絕跨房請求。分房保留離場玩家及原場次與封存序號。 [報表操作](https://github.com/peca12968/vr-command-center/blob/012ec33/docs/REPORTS.md#五房分房匯出)

本機通過 792 項核心、91 項 Node、322 項 Chromium、105 項解壓管理包及 348 項 Windows 三包檢查。五房獨立與五房連線各有 25 個同機模擬玩家，六場共 851 幀完整回放及 50 份戰績。五份分房報表各五列，逐列對上同場 25 筆封存戰績。 [驗證紀錄](https://github.com/peca12968/vr-command-center/blob/012ec33/docs/PROGRESS.md#2026-11-06-五房戰績分房匯出)

完整 Windows HTTP 回歸在啟動與程序檢查中止。GitHub Actions 因帳務條件未啟動。實際跨機、頭盔、廠商硬體及 25 位真人仍待驗。 [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42100962160/job/127503314612)

## 2026-11-06 通路預覽的移動判定與鍵盤驗收準備

共用遊戲權威端在同一席位拒絕落入或跨越完整沙包牆的姿態，移除正前方沙包後，接受預覽到中線的七個取樣點。785 項 .NET 核心檢查通過。新 Windows 鍵盤工具可比對兩個已儲存版本，首輪缺修訂請求鍵已修正。第二輪原生遊戲啟動後，Windows 防火牆提示遮住遊戲，第一個鍵盤階段逾時，兩次紀錄均保存。跨機、頭盔、廠商硬體與 25 位真人待驗。來源 `14f6d46` 的 GitHub Actions 因帳務條件未啟動。 [開發進度](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md) · [CI](https://github.com/peca12968/vr-command-center/actions/runs/42099308275/job/127497581684)

## 2026-11-06 任務配置出生位通路預覽

控制台 0.31.7 可預覽五席到中線的取樣路徑。整排沙包的基本配置可開場，預覽會標出未找到路徑的出生位。移除一個沙包後，五席均有路線經過缺口。783 項核心、571 項 HTTP、47 項世界串流、91 項 Node、318 項 Chromium、105 項解壓包檢查通過。 [配置預覽](https://github.com/peca12968/vr-command-center/blob/main/docs/LAYOUT.md#出生位通路預覽)

Windows 三包通過 355 項。兩種模式各有 25 個同機模擬玩家，六場 30 條預覽路徑與 50 個封存沙包座標核對通過，另有 889 幀回放、50 份戰績和 6 份 CSV。通路逐段由共用 C# 判定驗證，本輪原生玩家維持在出生區。跨機、實體頭盔、廠商硬體與 25 位真人仍待驗。來源 `f6131a5` 的 GitHub Actions 因帳務條件未啟動。 [開發進度](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md) · [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42097466387/job/127491166056)

## 2026-11-06 五房有效姿態總覽

控制台 0.31.6 的房卡分列名冊、有效姿態、合成和追蹤。房控只收到自己的摘要。778 項核心、567 項 HTTP、47 項世界串流、91 項 Node、314 項 Chromium、105 項管理包檢查通過。 [五房總覽](https://github.com/peca12968/vr-command-center/blob/main/docs/PLAYER_READINESS.md#五房總覽)

Windows 三包通過 343 項。五房獨立及連線模式各有 25 個同機模擬玩家，兩種模式的摘要均為每房 5 筆有效合成姿態。瀏覽器實際顯示五個獨立房間。六場共 831 幀回放、50 份戰績、6 份 CSV。追蹤欄位以瀏覽器測試回應驗證，實際跨機、頭盔、廠商硬體與 25 位真人待驗。來源 `c9cc3bb` 的 GitHub Actions 因帳務條件未啟動。 [開發進度](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md) · [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42095436816/job/127484096337)

## 2026-11-06 五房控制台場次隔離

控制台 0.31.5 修正兩房操作競態。舊版在刷新期間外部結束 A，原本按在 A 的暫停實際送往 B。新版同一測試送出零筆命令，B 維持 Running，需明確選取場次後才能操作。通過 89 項 Node、309 項 Chromium、105 項解壓管理包檢查及實際解壓包的 20 項聚焦測試。 [操作方式](https://github.com/peca12968/vr-command-center/blob/main/docs/SESSION_CLOSURE.md#場次切換與操作)

新版三包同機驗證通過 338 項，兩種模式各 25 個模擬玩家，共 50 份戰績、6 份 CSV、932 幀回放。控制台實際結束第一房並保留原場次，畫面封存序號 199 對上伺服器報告。跨機、頭盔、廠商硬體與 25 位真人待驗。來源 `2caf8a2` 的 GitHub Actions 因帳務條件未啟動。 [開發進度](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md) · [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42092953218/job/127475496332)

## 2026-11-06 Windows 遊戲伺服器來源診斷

遊戲 0.41.2 與 Windows 伺服器啟動器 1.2 新增可選的 UDP 來源診斷。實際解壓三包的同機測試通過 335 項，Linked 25 筆來源均對上原入場及伺服器戰績確認回條。五個獨立房間預設無來源紀錄。兩模式共 778 幀回放、50 份戰績和 6 份 CSV。 [跨機部署與核對方式](https://github.com/peca12968/vr-command-center/blob/main/docs/WINDOWS_SERVER_PACKAGE.md#跨機來源診斷)

同源 Windows 與 Quest ARM64 APK 已建置，242 項 Unity EditMode 測試通過。APK 版本 53，v2 開發簽章，實體頭盔尚未安裝。實際跨機、廠商硬體及 25 位真人待驗。來源 `7f0d98d` 的 GitHub Actions 因帳務條件未啟動。 [開發進度](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md) · [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42091327531/job/127469817419)

## 2026-11-06 Windows 三個可攜包整合

使用現有管理包 0.31.4、遊戲伺服器與玩家包 0.41.1，在同一台 Windows 電腦用乙太網路 IPv4 測試。五房獨立與五房連線模式各有 25 個模擬玩家同時入場，玩家啟動器直接使用 10 份整房 ZIP 內的席位檔。319 項通過，六場共 812 幀回放，50 份戰績與 6 份 CSV 對上雙封存及原連線的伺服器確認回條。原 loopback 流程另重跑 103 項通過。 [部署與重現方式](https://github.com/peca12968/vr-command-center/blob/main/docs/WINDOWS_SERVER_PACKAGE.md#三個可攜包整合驗證)

本次使用背景 CLI 與靜止模擬玩家。跨機、頭盔、廠商硬體及 25 位真人仍待驗。來源 `df70e9d` 的 GitHub Actions 因帳務條件未啟動。 [GitHub 工作](https://github.com/peca12968/vr-command-center/actions/runs/42086684963/job/127453575830)

## 2026-11-06 控制台 0.31.4 整房配票

操作員選擇授權房間後可下載最多五份席位 JSON 的 ZIP，房控可處理自己的房間。服務在產生 ZIP 前核對完整名冊與本次入場。HTTP 驗證五房共 25 份票券，304 項瀏覽器與 105 項解壓管理包檢查通過。兩位 Windows 玩家用實際下載的 ZIP 入場，戰績對應世界封存序號 180。這是同機 IPv4 Simulation，跨機、頭盔及 25 位真人待驗。CI 42084911404 因帳務條件未啟動。 [開發進度](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md) · [CI 工作](https://github.com/peca12968/vr-command-center/actions/runs/42084911404/job/127447285124)

## 2026-11-06 控制台 0.31.3 配票前驗證

控制台共用玩家連線目的地的 IPv4 與埠號規則。四種無效輸入各送出零筆配票請求，修正後送出一筆並下載本次入場的連線檔。89 Node、301 Chromium、105 項解壓管理包檢查與同機雙玩家 9 項通過，兩份個別戰績對應世界封存序號 227。首輪伺服器尚未公告位址即逾時，原結果保留。CI 42083067052 因帳務條件未啟動。跨機、頭盔及真人容量待驗。 [進度與包資訊](https://github.com/peca12968/vr-command-center/blob/main/docs/PROGRESS.md) · [CI 工作](https://github.com/peca12968/vr-command-center/actions/runs/42083067052/job/127440889457)

## 2026-11-06 本機網卡與雙機驗收準備

外部玩家工具可明確選擇本機私有 IPv4，並核對 UDP 綁定、控制台公告與下載的玩家連線檔。乙太網路 IPv4 同機雙玩家通過 13 項，預設 loopback 通過 9 項。兩場各有兩份戰績與雙封存，世界封存序號分別為 637 和 198。部署文件已補第二台電腦的操作及驗收步驟。 [外部玩家連線](https://github.com/peca12968/vr-command-center/blob/main/docs/EXTERNAL_CLIENTS.md)

來源 `3f243c3` 的 CI 工作因帳務條件未啟動。跨機連線、頭盔及 25 位真人仍待驗收。 [CI 工作](https://github.com/peca12968/vr-command-center/actions/runs/42081624524/job/127435870115)

## 2026-11-06 Windows 玩家啟動器驗收

玩家啟動器 1.1 支援貼上完整路徑並載入連線檔。實際 WinForms 測試確認檔案變更後拒絕啟動，重新載入後正常加入場次。GUI／CLI 雙玩家通過 9 項，世界封存序號 828，兩份個別戰績吻合封存資料。另有背景雙玩家 13 項、解壓玩家包 19 項及來源 `e963e48` 的 CI 通過紀錄。原 11 月 2 日的 GUI 逾時結果保留。測試範圍是同機 Simulation，跨機、頭盔及 25 位真人驗收待完成。 [玩家連線檔流程](https://github.com/peca12968/vr-command-center/blob/main/docs/PLAYER_CONFIG_REVIEW.md) · [CI](https://github.com/peca12968/vr-command-center/actions/runs/41368791791)

## 2026-11-02 電腦端900秒兩模式長場及實際伺服器視窗流程

[功能4bdf294](https://github.com/peca12968/vr-command-center/commit/4bdf294db3587443228b3afbb82fe7530c9deb4f)、[DESKTOP_ENDURANCE](https://github.com/peca12968/vr-command-center/blob/main/docs/DESKTOP_ENDURANCE.md)、[WINDOWS_SERVER_PACKAGE](https://github.com/peca12968/vr-command-center/blob/main/docs/WINDOWS_SERVER_PACKAGE.md)。Unity **0.41.1／code52／NGO29／242真正Editor0skip**，同源Windows／ARM64 fingerprint **4ebdcd12b9cbf1d00f342cb25dbec21d84f60c048284d8333cb8fa01c42a495c**，原Scene／prefab ID保持；API0.31／UI0.31.2／rules0.8.0保持。

新900秒兩模式原handle33928／073638-487017bd **terminal exit0、18項／51601完整回放／51351 Running**。先Linked25端，再五房各5端；50位各90發／45reload／45週期，50原admission結果／6CSV／combat與world雙seal及原server ACK、無timeout或queue error。活動跨度17943..18003tick、最長收集902.3086214秒，active0／cleanup空後C174→F逐檔同hash。60秒兩模式18／3760、普通無生成旗標入場／撤銷／重連8／354、玩家包19也通過。

長場只讀自己的本機Z於起點..+.8m換向、回±.2原Move／Constrain／RPC，不clamp／teleport／寫server pose／搬Tracked；原短40tick與0.5／1.5、走道、武器彈藥／durability不變。原0.41生成器走道場仍 **exit1**：Room5 world3400..3402共8筆Z不符，原C174/F與36896取證保持，未補CSV或改判；這不是舊31筆失聯，亦未宣稱其修復。原328及更早327 binary/log/source archive與manifest逐hash保持。

新server **v2 ZIP82673732／SHAca285a42e0c22bdde17f62eb6dd8a65523c9d3a5cae19a33cad41636899fb368**，311manifest／ZIP312、原launcher1.1來源fb57807d...重新編譯binary不同，runtime同v1；包說明引用實際receipt，v1與失敗stage保持。真正F解壓包 **106項／623全回放／10原結果及CSV／雙seal及ACK**、五獨立後Linked／active0／cleanup空成功；另留parent-death未封存反例。C80/F同hash，closure UI兩PNG與原world尾相符，nativeUI累計11另於CI計。

使用者關閉PickerHost後，新WinForms原handle64853／run-3d179468... **exit0／passed**：直接輸入既有實例、載入兩房清單、明確選房1完整ID／任務版本、填127.0.0.1與本次UDP、啟動。fixture正常API Begin後原來源Running/tick>0/observed fence，再API End、雙seal保留36秒、原child停止，畫面顯示已封存並停止後關閉。GUI exit0／精確journal ACK尾／原marker與三key檔hash不變／cleanup空，C14/F一致。只建一位roster、沒有玩家client；未測系統檔案picker、GUI建key或GUI Begin/End、玩家送達／LAN／頭盔。首新GUI空名冊Begin409的exit1／C9保持，僅fixture補roster、原API規則不改。舊PickerHost失敗亦保留。

玩家ZIP **82651927／SHAdcc46c80c68d0a2861957c7d534b1abacd15964fb22f310ecdd1e60dddf7d2df**；APK **60361942／SHA766d80180c0facf67136412d4f9a4b9e35ae0d6dc5f5cac9b128261282188e48**，ARM64／min32／target35／v2 debug，未裝頭盔。

[最終CI41367545805](https://github.com/peca12968/vr-command-center/actions/runs/41367545805)／job125030805195，精確65b072d完整 **success**：772核心／459 HTTP／47 world／6pipe／38硬體CLI、全部Python／素材、89Node／296Chromium；2Windows限定skip不當原生／Editor／GUI／頭盔。console51／control13／hardware26原ZIP的GitHub digest、大小及逐檔hash與完整log均保存；browser總1819，nativeUI11另列。前c55與659成功及原7ed／4bdf／1d三failed CI保持，原15／30秒／產品規則不變，不證舊逾時根因。新GUI roster修正僅fixture；本機242Editor／4ebd／900秒與真GUI另驗。文件提交ddaa535使用skip ci，不冒充精確測試來源。

完整原始11項 **仍active**。上述為同機AutomatedSimulation及有限GUI流程；舊31／world371／Windows startup／F吞吐、LAN／跨機25真人、Quest／VIVE／MR及廠商SDK／實體硬體仍待。保存SQLite不開、5080不動，不以CI／生成器代替實機。

## 後續與外部依賴

繼續PC完整第一人稱／追蹤人物、手指／腰腳及動畫、聲學、複雜通路／地形、長任務與跨機部署；歷史偶發姿態原因仍未證明或修復。取得Quest後驗控制器、追蹤中斷、雙玩家、聲光／效能與封存；再進行VIVE／MR／廠商硬體與5／10／25人驗收。SDK／NDK與Unity授權已處理且真正建置成功，不當目前阻礙。廠商協議、設備及實機驗收仍未提供／完成。

## 歷史進度

原本文63864字已[完整封存於此留言](https://github.com/peca12968/vr-command-center/issues/1#issuecomment-6532297157)，讀回確認原文逐字保留（SHA256 `d56064c431b1d8c83e5eef3f6cf3945f6270752b9582b83416a182f862c42fed`）。本文維持目前目標及最新交付，完整逐輪歷史繼續保存於PROGRESS與封存留言，避免超出GitHub字數上限。
