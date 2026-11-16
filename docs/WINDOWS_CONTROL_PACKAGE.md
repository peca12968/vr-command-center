# Windows 可攜管理服務

2026-11-16 管理台 0.31.214 的 Windows ZIP 為 53,394,941 位元組，SHA-256 `2226ccd0dc560183c07d445c5b23ae90f515759415aa526c85008a5d30d82477`。解壓後逐檔核對 568 筆。建立單房、五房合併及五房獨立場次時，管理台核對回條中的完整保存任務。 [管理包](../artifacts/mission-launch-content-031214/VRCommand-ControlServer-0.31.214.zip) · [開場操作](MISSION_VERSIONS.md#五房各自獨立)

2026-11-16 管理台 0.31.213 的 Windows ZIP 為 53,394,282 位元組，SHA-256 `61d7cb125af8b0e00e13ba12823af7192cf976c2a62fcb060ec7dd41cf3bcee9`。解壓後逐檔核對 568 筆。即時觀戰在管理服務中斷後有 20 秒自動重連窗口。 [管理包](../artifacts/observer-management-restart-031213/VRCommand-ControlServer-0.31.213.zip) · [觀戰操作](WORLD_RECORDING.md)

2026-11-16 管理台 0.31.212 的 Windows ZIP 為 53,393,741 bytes，SHA-256 `f6eab938633620da662ac77c5e7dd0eec70083ec01e669db1415ce09732d0780`。主控可直接查看五房 UDP 預檢的待補席位與原因。 [管理包](../artifacts/venue-udp-console-20261116-1654/VRCommand-ControlServer-0.31.212.zip) · [操作說明](EXTERNAL_CLIENTS.md#補測未完成的全館-udp-預檢)

2026-11-16 管理台 0.31.211 的 Windows ZIP 為 53,388,918 bytes，SHA-256 `2fb8140421c5529b9b9068c0717a97cd9f48f001cc5af8784a7b3823f25f49fe`。解壓核對 568 檔。從事件搜尋結果或前後跳轉開啟畫格時，會核對所選事件的原始識別。 [管理包](../artifacts/windows-control-event-ids-031211.zip) · [操作說明](WORLD_RECORDING.md)

2026-11-16 管理台 0.31.210 的 Windows ZIP 為 53,388,035 bytes，SHA-256 `83bf8afb67f7a4aa7a30f21e1709340735eaa8cb0f31a695ac420a405ee437df`。解壓核對 568 檔。從戰績開啟個人回放時，會核對封存尾端的玩家與戰績。 [管理包](../artifacts/windows-control-player-replay-score-031210.zip) · [操作說明](REPORTS.md#從戰績開啟個人回放)

2026-11-16 管理台 0.31.209 的 Windows ZIP 為 53,387,386 bytes，SHA-256 `6088b5027020f0807dcb9183f22fe50e81d01cc1e64441c3a1a8281371d027eb`。解壓核對 568 檔。主控從受阻快照可直接返回全館開場檢查，依目前席位狀態繼續操作。 [管理包](../artifacts/windows-control-return-opening-031209.zip) · [操作說明](PLAYER_READINESS.md#五房追蹤驗收開場)

2026-11-16 `VRCommand-ControlServer-0.31.205.zip` 為 53,377,195 bytes，SHA-256 `380804a5ececfe59e80f8fb901b097deb832875b0a1213ed4d08db6433ee76b2`。解壓核對 568 筆清單。主控可從全館結束批次查看離場玩家的封存戰績，並開啟原房間的個人回放。 [管理包](../artifacts/VRCommand-ControlServer-0.31.205.zip) · [收尾操作](SESSION_CLOSURE.md)

2026-11-16 `VRCommand-ControlServer-0.31.204.zip` 為 53,371,734 bytes，SHA-256 `6745c43a596b0cad237e016c0753e1004317563f1119b3fb61e2addf58b13714`。解壓核對 568 筆清單。全館批次驗收 ZIP 可保留各場的原離場紀錄與封存戰績。 [管理包](../artifacts/VRCommand-ControlServer-0.31.204.zip) · [操作說明](EXTERNAL_CLIENTS.md#核對五房批次中的離場戰績)

2026-11-16 `VRCommand-ControlServer-0.31.203.zip` 為 53,371,377 bytes，SHA-256 `67b002aaf537ae9ef17f64bddc2024a8879ea73d620cf9767cecca51d32223dd`。解壓核對 568 筆清單。單場驗收 ZIP 可保留原離場紀錄與封存戰績。 [管理包](../artifacts/VRCommand-ControlServer-0.31.203.zip) · [操作說明](EXTERNAL_CLIENTS.md#核對任務中被移出的玩家)

2026-11-16 `VRCommand-ControlServer-0.31.202.zip` 為 53,368,058 bytes，SHA-256 `b0f42cd8ef77683168d49236de98bc61619f9ebb40c22027af1551a7af4e37b3`。解壓核對 568 筆清單。單場驗收 ZIP 可附原 VR 追蹤開場資料，供原生錄製核對。 [管理包](../artifacts/VRCommand-ControlServer-0.31.202.zip) · [操作說明](EXTERNAL_CLIENTS.md#用單場-zip-核對追蹤開場)

2026-11-16 `VRCommand-ControlServer-0.31.201.zip` 為 53,367,469 bytes，SHA-256 `1363f4ee7cffb4fcc805b8082fc636b1092d1a021a1ee8f76c125e8834b4a819`。解壓核對 568 筆清單。單場 VR 追蹤開場通過時會保存原畫格，封存後可從任務收尾直接回看。 [管理包](../artifacts/VRCommand-ControlServer-0.31.201.zip) · [操作說明](SESSION_CLOSURE.md#回看單場-vr-追蹤開場)

2026-11-16 `VRCommand-ControlServer-0.31.200.zip` 為 53,362,701 bytes，SHA-256 `86c963b87287ee1c10a1e03c088f7c5f9667516b16cad5466a24c426fe6e0615`。解壓核對 568 筆清單。個別 `GameServer` VR 場次可在開始時重新核對原名冊與有效追蹤。 [管理包](../artifacts/VRCommand-ControlServer-0.31.200.zip) · [操作說明](PLAYER_READINESS.md#單場-vr-追蹤開場)

2026-11-16 `VRCommand-ControlServer-0.31.199.zip` 為 53,360,013 bytes，SHA-256 `a959c7d8e1ba67c88143ef62578a5457ca92e31e06f8cfab8d3ec8d0ba1b14a9`。解壓核對 568 筆清單。單席 Quest 3 部署可驗證原入場、票券、公告端點、近期遊戲畫格及 MR 原鎖定校正檔。 [管理包](../artifacts/VRCommand-ControlServer-0.31.199.zip) · [操作說明](QUEST3.md#部署前核對單席連線檔)

2026-11-16 `VRCommand-ControlServer-0.31.198.zip` 為 53,358,273 bytes，SHA-256 `f7edd81e096da16a3b4e6b1b86045f549d92018c8b8de53ddfb8a7ccac8826dc`。解壓核對 568 筆清單。全館敵軍策略的已覆寫與已結束房間可查找原執行畫格與該房當時人數。 [管理包](../artifacts/VRCommand-ControlServer-0.31.198.zip) · [操作說明](LAYOUT.md#核對最近一批敵軍策略)

2026-11-16 `VRCommand-ControlServer-0.31.197.zip` 為 53,356,132 bytes，SHA-256 `20ffd5463db919c9dec51c4ce24393348d9dc3417e32513602709c162ec529d1`。解壓核對 568 筆清單。全館環境批次的已覆寫與已結束房間可查找原命令的執行畫格。 [管理包](../artifacts/VRCommand-ControlServer-0.31.197.zip) · [操作說明](ENVIRONMENT.md#核對最近一批環境指令)

2026-11-16 `VRCommand-ControlServer-0.31.196.zip` 為 53,352,935 bytes，SHA-256 `1be5639c6440cce924da04f9cfa96c555449a3349961d2d369a32eb0d29f8b57`。解壓核對 568 筆清單。全館開場清單可查看各房原錄製來源，快照過期後會撤下來源標示。 [管理包](../artifacts/VRCommand-ControlServer-0.31.196.zip) · [操作說明](PLAYER_READINESS.md#五房追蹤驗收開場)

2026-11-13 `VRCommand-ControlServer-0.31.195.zip` 為 53,352,827 bytes，SHA-256 `e96d4ddae0080938dabbe5c20f5c2214f8b036fb92542fb3f9db7c6acb67faf6`。解壓核對 568 筆清單。主控可直接下載原批次已完成房間的戰績 CSV。 [管理包](../artifacts/VRCommand-ControlServer-0.31.195.zip) · [分房戰績](REPORTS.md#在全館收尾比較分房戰績)

2026-11-13 `VRCommand-ControlServer-0.31.194.zip` 為 53,348,658 bytes，SHA-256 `d3e5a88d8a14d03f7b7260714de9a68e5fd3bb2dca31359e14c9fa4dcb2365d5`。解壓核對 568 筆清單。全館收尾可先查看已就緒的分房戰績。 [管理包](../artifacts/VRCommand-ControlServer-0.31.194.zip) · [分房戰績](REPORTS.md#在全館收尾比較分房戰績)

2026-11-13 `VRCommand-ControlServer-0.31.193.zip` 為 53,347,166 bytes，SHA-256 `a5ca7ef5cd1481aa26802dd9317ac0e42860c28e10a7be676fab814a2d4344c9`。解壓核對 568 筆清單。分房觀戰可重連原錄製並保留鏡頭。 [管理包](../artifacts/VRCommand-ControlServer-0.31.193.zip) · [驗證摘要](../artifacts/live-room-reconnect-193-validation.json)

2026-11-13 `VRCommand-ControlServer-0.31.192.zip` 為 53,346,681 bytes，SHA-256 `8203b293848cd401b12131962a636b9e6cb497ecb263bbd3e0c4fd0517568da4`。解壓核對 568 筆清單。主控切換即時觀戰房間前會先核對目標快照。 [管理包](../artifacts/VRCommand-ControlServer-0.31.192.zip) · [觀戰操作](WORLD_RECORDING.md)

2026-11-13 `VRCommand-ControlServer-0.31.191.zip` 為 53,345,999 bytes，SHA-256 `74384bd4f6b5059f0d736e2760ebb42c700849aee30f119e1a94ac8bfbad7e40`。解壓核對 568 筆清單。主控可下載同時包含離線播放器與原片段 JSON 的回放 ZIP。 [管理包](../artifacts/VRCommand-ControlServer-0.31.191.zip) · [回放交付](WORLD_RECORDING.md#讓玩家開啟回放)

2026-11-13 `VRCommand-ControlServer-0.31.190.zip` 為 53,344,452 bytes，SHA-256 `8561bb8e1c8df45f7e898df9167e99a866b767e848f3cd9ffc21809df3956aca`。解壓核對 568 筆清單。控制台可下載單檔離線播放器。 [管理包](../artifacts/VRCommand-ControlServer-0.31.190.zip) · [回放交付](WORLD_RECORDING.md#讓玩家開啟回放)

2026-11-13 `VRCommand-ControlServer-0.31.189.zip` 為 53,157,781 bytes，SHA-256 `aff0f1b38ddb6c423adaf2ba4ba640a35fbd55447d4a1e481df4898bb1ae747b`。解壓核對 567 筆清單。玩家回放頁可依場館提供的原畫格序號定位。 [管理包](../artifacts/VRCommand-ControlServer-0.31.189.zip) · [回放操作](WORLD_RECORDING.md)

2026-11-13 `VRCommand-ControlServer-0.31.188.zip` 為 53,157,142 bytes，SHA-256 `a75f61c029a9056e2b1964eee7fd5b9f4c3c4d3badf9e9928bfe65fe7d60dc36`。解壓核對 567 筆清單。暫停回放時可輸入序號直接跳到保存畫格。 [管理包](../artifacts/VRCommand-ControlServer-0.31.188.zip) · [回放操作](WORLD_RECORDING.md#暫停逐格檢視)

2026-11-13 `VRCommand-ControlServer-0.31.187.zip` 為 53,156,172 bytes，SHA-256 `9bd97111bb9f74ceb7bff17d81953e916ab52b6fc8ec4b0c7f1938ec92f3c4a5`。解壓核對 567 筆清單。全館收尾戰績 ZIP 可同時下載各房明細與全館合計。 [管理包](../artifacts/VRCommand-ControlServer-0.31.187.zip) · [戰績匯出](REPORTS.md#下載全館結束批次)

2026-11-13 `VRCommand-ControlServer-0.31.186.zip` 為 53,156,497 bytes，SHA-256 `d26b43c610f526812a2b5c62cddd44b179db5e063afe04b90cdf418ddae56cdb`。解壓核對 567 筆清單。任務編輯器可在本機下載尚未儲存的草稿範本。 [管理包](../artifacts/VRCommand-ControlServer-0.31.186.zip) · [操作說明](MISSION_VERSIONS.md#在管理實例間交接任務範本)

2026-11-13 `VRCommand-ControlServer-0.31.185.zip` 為 53,155,138 bytes，SHA-256 `8d32dc994de2d4d2216b11d8c8c06808975d0503f773b996e679aecac4ecbccf`。解壓核對 567 筆清單。玩家頁可在瀏覽器循環播放場館交付的回放檔。 [管理包](../artifacts/VRCommand-ControlServer-0.31.185.zip) · [回放操作](WORLD_RECORDING.md)

2026-11-13 `VRCommand-ControlServer-0.31.184.zip` 為 53,154,739 bytes，SHA-256 `df119a1d89a2b436d88785579ad96452536f297771d9c34a5098dcc52a3d2beb`。解壓核對 567 筆清單。主控可逐台查看工作站回條未通過的原因。 [管理包](../artifacts/VRCommand-ControlServer-0.31.184.zip) · [工作站操作](#核對主控與五房控的直連來源)

2026-11-13 `VRCommand-ControlServer-0.31.183.zip` 為 53,151,722 bytes，SHA-256 `0a246e910d2276215ef1887052d1aecfcba29c6fd49cdffd03956dd34cbbd4d3`。解壓核對 567 筆清單。主控核對 Windows 結束報告後，可開啟原全館結束批次的戰績與回條。 [管理包](../artifacts/VRCommand-ControlServer-0.31.183.zip) · [操作說明](WINDOWS_SERVER_PACKAGE.md#核對未確認的啟動報告)

2026-11-13 `VRCommand-ControlServer-0.31.182.zip` 為 53,149,900 bytes，SHA-256 `4bd23d126015466b4c4f8a8d296536e4e35ae96b159248df51e4ab1c5522b05d`。解壓核對 567 筆清單。由 Windows 結束報告開啟的獨立房間回放可對齊同批房間。 [管理包](../artifacts/VRCommand-ControlServer-0.31.182.zip) · [回放操作](WORLD_RECORDING.md#對齊同批獨立房間的回放)

2026-11-13 `VRCommand-ControlServer-0.31.181.zip` 為 53,148,887 bytes，SHA-256 `75dbf9738dac50f4edbfd64b9250e60c434fe43a33632eceb8c2882edaa7bb06`。解壓核對 567 筆清單。核對 Windows 結束報告後，可逐房開啟原封存回放。 [管理包](../artifacts/VRCommand-ControlServer-0.31.181.zip) · [操作說明](WINDOWS_SERVER_PACKAGE.md#核對未確認的啟動報告)

2026-11-13 `VRCommand-ControlServer-0.31.180.zip` 為 53,148,494 bytes，SHA-256 `b2282b16e71a279281db5fbd64adeb33b11d5e1f567dfb59c4f2273d12463450`。解壓核對 567 筆清單。主控可匯入第四版 Windows 全館正常結束報告，核對五房原戰鬥與回放的封存序號。 [管理包](../artifacts/VRCommand-ControlServer-0.31.180.zip) · [核對操作](WINDOWS_SERVER_PACKAGE.md#核對未確認的啟動報告)

2026-11-13 `VRCommand-ControlServer-0.31.161-opening-replay-win-x64.zip` 為 53,120,954 bytes，SHA-256 `4c5f6ee0ac5dfdcd4630988f95f1cdcb90a53d999f552026cea8f7de25f94647`。主控可在同一錄製比較原開場畫格與首個有效執行畫格。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.161-opening-replay-win-x64.zip) · [回放操作](SESSION_CLOSURE.md#比較準備與執行畫格)

2026-11-13 `VRCommand-ControlServer-0.31.160-mission-maps-win-x64.zip` 為 53,117,222 bytes，SHA-256 `a56e61f10d4a4d2b4a5e521ea7529ff7dec1ed24bce78c50b969940802bcf442`。五房任務配置檔可對照目前準備與檔案版本的平面圖。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.160-mission-maps-win-x64.zip) · [任務配置](MISSION_VERSIONS.md#在開場前保存五房任務配置)

2026-11-13 `VRCommand-ControlServer-0.31.159-clip-loop-win-x64.zip` 為 53,114,782 bytes，SHA-256 `1bd809dc89bbebf9c9790f68ba1f86bae73ebb6505f5f17235266e3df732e472`。主控台可循環播放已標記的任務片段。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.159-clip-loop-win-x64.zip) · [回放操作](WORLD_RECORDING.md#重看指定片段)

2026-11-13 `VRCommand-ControlServer-0.31.158-venue-receipts-win-x64.zip` 為 53,113,932 bytes，SHA-256 `8aa9aef7c3defca4d38acd9c055625b7c374ace2f6cbab3e8f6f7ccb976e7d43`。全館收尾可下載含全員確認回條的場館驗收 ZIP。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.158-venue-receipts-win-x64.zip) · [收尾操作](SESSION_CLOSURE.md#下載驗收-zip-與全員回條)

2026-11-13 `VRCommand-ControlServer-0.31.157-mission-enemies-final-win-x64.zip` 為 53,111,901 bytes，SHA-256 `585fa62ffcc4a46e2893dd1fbad3a167b53adeb24933ca37a14982e5956ef93b`。五房任務準備可逐房核對初始敵軍設定。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.157-mission-enemies-final-win-x64.zip) · [任務設定](MISSION_VERSIONS.md#逐房指定任務版本)

2026-11-13 `VRCommand-ControlServer-0.31.156-venue-score-summary-win-x64.zip` 為 53,111,552 bytes，SHA-256 `9c8a5a8abcf62033deb947a920371a83beb71c2c60a092c31d28199794b36637`。全館收尾可下載各房及全批戰績合計。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.156-venue-score-summary-win-x64.zip) · [分房戰績](REPORTS.md#在全館收尾比較分房戰績)

2026-11-13 `VRCommand-ControlServer-0.31.155-live-policy-review-win-x64.zip` 為 53,108,899 bytes，SHA-256 `b5d486ad995368641b4c8140f2ee89f7e62d52cb3bbe583ece565a4dfc83d6c9`。即時觀戰可定位最近的保存設定，並返回同場最新快照。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.155-live-policy-review-win-x64.zip) · [操作方式](WORLD_RECORDING.md#從即時觀戰定位最近設定)

2026-11-13 `VRCommand-ControlServer-0.31.154-replay-policy-neighbor-win-x64.zip` 為 53,107,857 bytes，SHA-256 `d0742333206c63707d3b086c4ff31bf04b96b3001fd33a11866e81c32e536614`。回放可從目前畫格向前或向後跳到符合種類的最近原設定。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.154-replay-policy-neighbor-win-x64.zip) · [操作方式](WORLD_RECORDING.md#查閱錄製中的設定切換)

2026-11-13 `VRCommand-ControlServer-0.31.153-replay-policy-filter-win-x64.zip` 為 53,102,059 bytes，SHA-256 `067d0d7d45bcbdaa65b4bb9c15d3fab6f8136933345f8a164f044d36f340b673`。回放可依設定種類查閱原畫格，跳轉時核對原設定與名單。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.153-replay-policy-filter-win-x64.zip) · [操作方式](WORLD_RECORDING.md#查閱錄製中的設定切換)

2026-11-13 `VRCommand-ControlServer-0.31.152-mission-climate-win-x64.zip` 為 53,100,746 bytes，SHA-256 `b7a5157512f3205ee33b1d02e9888776471e1f3654aa8c855ca89b2c46adf52a`。逐房準備與配置檔預覽顯示原保存版本的初始環境，並在五房建立回覆核對初始環境。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.152-mission-climate-win-x64.zip) · [操作方式](MISSION_VERSIONS.md#逐房指定任務版本)

2026-11-13 `VRCommand-ControlServer-0.31.151-mission-file-review-win-x64.zip` 為 53,100,303 bytes，SHA-256 `18097064f506e62a6c1f2e42b3c2d06a40e8e71fc571e43ad3796bddcd531b2a`。主控可在載入五房任務配置前逐房比對版本及場地結果。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.151-mission-file-review-win-x64.zip) · [操作說明](MISSION_VERSIONS.md#在開場前保存五房任務配置)

2026-11-13 `VRCommand-ControlServer-0.31.150-layout-proposal-win-x64.zip` 為 53,097,624 bytes，SHA-256 `31fbb72fab836d1d36df2a6eebed8ae2a07aac8be3f770f1821510cf8aa585f4`。任務編輯器會在套用批次移動、旋轉及成列複製前檢查候選配置。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.150-layout-proposal-win-x64.zip) · [操作方式](LAYOUT.md#套用前檢查物件預覽)

2026-11-13 `VRCommand-ControlServer-0.31.149-venue-seats-win-x64.zip` 為 53,095,201 bytes，SHA-256 `d614b1c30e250b692b41efb488ac06c67cc51e8bbbe02b7245129ba929aeec64`。主控可在所選結束批次查全館未確認席位、下載個人 CSV 並開啟原回放。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.149-venue-seats-win-x64.zip) · [操作方式](SESSION_CLOSURE.md#查看全館未確認席位)

2026-11-13 `VRCommand-ControlServer-0.31.148-windows-source-gate-win-x64.zip` 為 53,092,123 bytes，SHA-256 `6ff6abe82f062ad9d099feea0138ca9cf956c30c251b67797399235ae3581b04`。支援在 Windows 五房連線檔交付前核對原遊戲來源。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.148-windows-source-gate-win-x64.zip) · [分發方式](EXTERNAL_CLIENTS.md#依電腦分發-windows-vr-連線檔)

2026-11-13 `VRCommand-ControlServer-0.31.147-recording-pages-win-x64.zip` 為 53,091,893 bytes，SHA-256 `98a1a672aed29e91be0c7b569cfc0473426eb5efda2f407b55e679178a554df6`。觀戰清單先顯示最近 30 筆錄製及使用中的來源，可向前載入並從收尾直接回放原場次。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.147-recording-pages-win-x64.zip) · [操作說明](WORLD_RECORDING.md#載入較早錄製)

2026-11-13 `VRCommand-ControlServer-0.31.146-archive-list-win-x64.zip` 為 53,085,046 bytes，SHA-256 `e4e27df2b4c25a134a362c4daa3e57a9d64c3b159cac9e0ecd3699f9b4290d69`。錄製清單改為分批查詢。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.146-archive-list-win-x64.zip) · [錄製說明](WORLD_RECORDING.md#儲存與驗證邊界)

2026-11-13 `VRCommand-ControlServer-0.31.145-clip-csv-win-x64.zip` 為 53,083,946 bytes，SHA-256 `3418934d503bca0a1c5935794e1e38a72a67b88a79d98362708ad2c423d428e8`。下載前會核對片段戰績 CSV 與畫面內容。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.145-clip-csv-win-x64.zip) · [操作說明](REPORTS.md#下載指定片段的戰績)

2026-11-11 `VRCommand-ControlServer-0.31.144-projected-events-win-x64.zip` 為 53,081,518 bytes，SHA-256 `a975d44a03fc4d9c58a3bf3e12ab839795fe36ab36cc9af3fa368d2e419fa8b5`。本房回放的事件搜尋和跳轉採用與本房畫格相同的篩選。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.144-projected-events-win-x64.zip) · [操作說明](WORLD_RECORDING.md#依房間與種類搜尋戰鬥事件)

2026-11-11 `VRCommand-ControlServer-0.31.143-closure-replay-win-x64.zip` 為 53,079,206 bytes，SHA-256 `ea716f1db724a506ca9ded16e887bae36a653e2614124d035c23f9da49dfe5d9`。支援從單一場次收尾直接播放原錄製或已保存片段。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.143-closure-replay-win-x64.zip) · [操作說明](WORLD_RECORDING.md#從單一場次的任務收尾回放)

2026-11-11 `VRCommand-ControlServer-0.31.142-session-reprepare-win-x64.zip` 為 53,078,580 bytes，SHA-256 `7d5b4ba76c5aee2b6271a7d4eafb52d02c376a57393c5800541086d289bdedb2`。支援從單一已結束場次選用原任務版本。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.142-session-reprepare-win-x64.zip) · [操作說明](MISSION_VERSIONS.md#從單一已結束場次選用原任務)

2026-11-11 `VRCommand-ControlServer-0.31.141-venue-missions-win-x64.zip` 為 53,077,832 bytes，SHA-256 `218fe8ba9b3d9a5422d61ceb4a1fad4f5baafdcff424122b6ac1fda95974f67a`。支援開場前下載及載入五房任務配置檔。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.141-venue-missions-win-x64.zip) · [操作說明](MISSION_VERSIONS.md#在開場前保存五房任務配置)

2026-11-11 `VRCommand-ControlServer-0.31.140-linked-archive-win-x64.zip` 為 53,074,040 bytes，SHA-256 `80a07ea1b2da80955cf0ea96c6693c677871773fb87e20569ca67e6fccc5cb80`。主控可從全館收尾套用完整合併場的原任務版本。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.140-linked-archive-win-x64.zip) · [操作說明](MISSION_VERSIONS.md#從全館收尾套用五房原版本)

2026-11-11 `VRCommand-ControlServer-0.31.139-layout-rejection-win-x64.zip` 為 53,072,943 bytes，SHA-256 `84595b1957f375a15f0b6cdc23c6ba14c0a3d9f2774403baa0df1f9a09a3bc20`。建立五房場次若收到場地拒絕，所有使用同一版本的房間會顯示回覆指出的問題物件及出生位。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.139-layout-rejection-win-x64.zip) · [操作說明](MISSION_VERSIONS.md#逐房指定任務版本)

2026-11-11 `VRCommand-ControlServer-0.31.138-port-drafts-win-x64.zip` 為 53,072,726 bytes，SHA-256 `dbbbf83fbf1732b16c2c3ed1bcb1c8f2ee690c1941da92ac4fbc52aec213e739`。重讀五房啟動計畫時可保留本頁輸入的 UDP 埠，並核對最新場次。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.138-port-drafts-win-x64.zip) · [操作說明](WINDOWS_SERVER_PACKAGE.md#從主控台下載場館計畫)

2026-11-11 `VRCommand-ControlServer-0.31.137-seat-replay-win-x64.zip` 為 53,072,161 bytes，SHA-256 `ab50f8cb077ae7c3adb30cbe1fa01f65d4768d89bcece2fdee0af663e1ace0e5`。主控可從原批次的席位明細開啟個人回放。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.137-seat-replay-win-x64.zip) · [操作說明](SESSION_CLOSURE.md#從全館收尾查看席位)

2026-11-11 `VRCommand-ControlServer-0.31.136-seat-scores-win-x64.zip` 為 53,071,201 bytes，SHA-256 `bdf5940f7cfd9da977e6259e1751edefdacf1568ad0e1ee568fe9c55018dff56`。主控可在全館收尾查看每席七項原封存戰績。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.136-seat-scores-win-x64.zip) · [操作說明](SESSION_CLOSURE.md#從全館收尾查看席位)

2026-11-11 `VRCommand-ControlServer-0.31.135-live-event-win-x64.zip` 為 53,069,127 bytes，SHA-256 `a762f4b0408489b714a707bfc783bb6b99bbedd6e243caa24771ba9614aa12a8`。即時觀戰可按事件種類定位同房最近保存格，再返回原錄製。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.135-live-event-win-x64.zip) · [操作說明](WORLD_RECORDING.md#從即時觀戰定位最近事件)

2026-11-11 `VRCommand-ControlServer-0.31.134-room-layouts-final-win-x64.zip` 為 53,068,259 bytes，SHA-256 `790fdf39e9ecdd4067d61575fdb21228b2eee8d11cb91182fede7ca20c6a8561`。主控可在逐房指定任務時同時核對五張保存平面圖。解壓核對 564 筆清單，包含 544 個管理服務發行檔案。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.134-room-layouts-final-win-x64.zip) · [操作說明](MISSION_VERSIONS.md#逐房指定任務版本)

2026-11-11 `VRCommand-ControlServer-0.31.133-seat-report-win-x64.zip` 為 53,065,219 bytes，SHA-256 `4ff07d1f768fd321d0c30e9779a413418db0a33f681c8409910ca1ee8d72c668`。可從全館收尾的原席位直接下載個人封存 CSV。解壓核對 564 筆清單。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.133-seat-report-win-x64.zip) · [操作說明](SESSION_CLOSURE.md#從全館收尾查看席位)

2026-11-11 `VRCommand-ControlServer-0.31.132-debrief-seats-win-x64.zip` 為 53,062,930 bytes，SHA-256 `b2fccb88421a0d7373e497626065f0897f86d509bd0b19e7c9dcfe773b406f8e`。全館收尾可按房間查看原結束名冊的席位回條。解壓核對 564 筆清單。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.132-debrief-seats-win-x64.zip) · [操作說明](SESSION_CLOSURE.md#從全館收尾查看席位)

2026-11-11 `VRCommand-ControlServer-0.31.131-placement-rotation-win-x64.zip` 為 53,052,518 bytes，SHA-256 `8b8ac2cfa248f3508963c875d9950200517a834c1faab1c1e1a7625da335646b`。管理台可預覽並批次旋轉及平移所選場地物件。解壓核對 561 筆清單。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.131-placement-rotation-win-x64.zip) · [操作說明](LAYOUT.md#批次旋轉場地物件)

2026-11-11 `VRCommand-ControlServer-0.31.130-placement-move-win-x64.zip` 為 53,050,953 bytes，SHA-256 `d2e921b126b41efa9f4ff2a251998e86ededeeeda4119f16e378d3930bf365f2`。主控可預覽及一次移動所選場地物件。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.130-placement-move-win-x64.zip) · [操作說明](LAYOUT.md#批次移動場地物件)

2026-11-11 `VRCommand-ControlServer-0.31.129-live-rooms-win-x64.zip` 為 53,044,445 bytes，SHA-256 `aaede94ebb4d2eb63c38289a7a9c012172cc3a47aaf1525f6d0bad5dd264a9b5`。主控可從觀戰頁直接切換目前房間。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.129-live-rooms-win-x64.zip) · [操作說明](WORLD_RECORDING.md#從觀戰頁切換目前房間)

2026-11-11 `VRCommand-ControlServer-0.31.128-mission-restore-win-x64.zip` 為 53,042,122 bytes，SHA-256 `aa6c5764b6dcbb83ca22ac3d0244a19ebbcb2c58529a5451479e1436aa90d2d6`。解壓核對 558 筆清單與 538 個發行檔案。主控可在任務版本比較中將舊版內容保存為下一版，保留目前草稿。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.128-mission-restore-win-x64.zip) · [操作說明](MISSION_VERSIONS.md#將歷史版本保存為下一版)

2026-11-11 `VRCommand-ControlServer-0.31.127-venue-setting-download-win-x64.zip` 為 53,040,936 bytes，SHA-256 `f159c318057ce2ebf6bda12329a9c503813883b847563f06a889e557d3ac8c4a`。解壓核對 558 筆清單與 538 個發行檔案。主控可下載畫面使用的環境或敵軍批次 JSON。 [管理包](../artifacts/control-server-packages/VRCommand-ControlServer-0.31.127-venue-setting-download-win-x64.zip) · [發行核對](../artifacts/venue-release-0.50.6-console-127.json)

2026-11-11 `VRCommand-ControlServer-0.31.126-clip-statistics-csv-win-x64.zip` 為 53,040,237 bytes，SHA-256 `2e3008df77c222480c49c3c8fe51357eaedf551261f9fec55e5d494193249672`。解壓核對 558 筆清單與 538 個發行檔案。回放可下載目前已核對範圍的片段戰績。 [片段戰績操作](REPORTS.md#下載指定片段的戰績) · [發行核對](../artifacts/venue-release-0.50.4-clip-statistics-csv.json)

2026-11-11 `VRCommand-ControlServer-0.31.125-mission-time-replay-win-x64.zip` 為 53,037,410 bytes，SHA-256 `dd8bc871de4b254e54d029aa0d52af0ecf7d84b77effa918bfb128e643a337ca`。解壓核對 558 筆清單與 538 個發行檔案。獨立房的同批封存回放可按原任務活動時間對齊。 [回放操作](WORLD_RECORDING.md#對齊同批獨立房間的回放) · [發行核對](../artifacts/venue-release-0.50.4-mission-time-replay.json)

2026-11-11 `VRCommand-ControlServer-0.31.124-vr-seat-check-win-x64.zip` 為 53,033,714 bytes，SHA-256 `e5649cabf85f20c13bfa123ad2e6fd8c2c80459e17b6283e429a401241130925`。解壓核對 558 筆清單與 538 個發行檔案。VR 場次可逐席核對原票券、現行入場與公告端點。 [VR 席位操作](EXTERNAL_CLIENTS.md#在管理台核對-vr-單席連線檔) · [發行核對](../artifacts/venue-release-0.50.4-vr-seat-file.json)

2026-11-11 `VRCommand-ControlServer-0.31.123-workstation-console-win-x64.zip` 為 53,029,288 bytes，SHA-256 `ee7a1dece7dcf53b17a9e7a16ef1de650370b2b02d40310b593bb91165700060`。解壓核對 558 筆清單與 538 個發行檔案。場館 HTTPS 控制台可收集及核對主控與五房控的連線回條。 [工作站操作](#核對主控與五房控的直連來源) · [發行核對](../artifacts/venue-release-0.50.4-workstation-console.json)

2026-11-11 `VRCommand-ControlServer-0.31.122-layout-clearance-win-x64.zip` 為 53,018,740 bytes，SHA-256 `47446747476ff463478aeba1a48df1ffe65b59dffb1ef3eca2216ebae7cdfa52`。解壓核對 555 筆清單與 535 個發行檔案。草稿與保存版本的旋轉方向對齊遊戲，並可顯示玩家通行邊界。 [平面圖操作](LAYOUT.md#開場前查看保存版本平面圖) · [發行核對](../artifacts/venue-release-0.50.4-layout-clearance.json)

2026-11-11 `VRCommand-ControlServer-0.31.121-observer-integrity-win-x64.zip` 為 53,017,017 bytes，SHA-256 `2cd6e31c1e73f676ed1fc3cc7a088f74327f6c698dc090d492b1be2e823994a5`。解壓核對 555 筆清單及 535 個發行檔案。觀戰核對錄製狀態及序號，並顯示此格的姿態與最後保存格標記。 [觀戰操作](WORLD_RECORDING.md#操作) · [發行核對](../artifacts/venue-release-0.50.4-observer-integrity.json)

2026-11-11 `VRCommand-ControlServer-0.31.120-setting-drafts-win-x64.zip` 為 53,016,141 bytes，SHA-256 `a813efb255223f947c741cf86fdde1c7f515c1674d4049a7706f3f0c6a4e8ed1`。解壓核對 555 筆清單及 535 個發行檔案。即時環境與敵軍可分開編輯，管理服務依設定版本檢查是否可套用。 [操作方式](ENVIRONMENT.md) · [發行核對](../artifacts/venue-release-0.50.4-setting-drafts.json)

2026-11-11 `VRCommand-ControlServer-0.31.119-room-enemy-edit-win-x64.zip` 為 53,014,011 bytes，SHA-256 `5c31c8fd898b3a05f771c9df8fbbbd4efaa4a699316d93407f71a87579d2c55c`。解壓核對 555 筆清單及 535 個發行檔案。五房合併場的分房敵軍策略依各房版本套用，版本已變更時保留草稿。 [逐房操作](LAYOUT.md#合併場分房敵軍策略) · [發行核對](../artifacts/venue-release-0.50.4-room-enemy-edit.json)

2026-11-11 `VRCommand-ControlServer-0.31.118-mission-text-win-x64.zip` 為 53,011,585 bytes，SHA-256 `fdd0324239620985b0036c48c6e280d4600f4c48c9215ff41496474161759703`。解壓核對 555 筆清單及 535 個發行檔案。管理台保留未編輯的任務名稱和簡報原文，並在載入及保存後讀回時核對版本。 [任務版本操作](MISSION_VERSIONS.md) · [發行核對](../artifacts/venue-release-0.50.4-mission-text.json)

2026-11-11 `VRCommand-ControlServer-0.31.117-room-observation-win-x64.zip` 為 53,010,627 bytes，SHA-256 `974c2557af4c09c2c88f9baaab3504a62706f8172479cd357a9af217dd0c81ca`。解壓核對 555 筆清單及 535 個發行檔案。合併場可從房卡啟用本房觀戰串流。 [房卡操作](WORLD_RECORDING.md#從房卡或全館收尾開啟)

2026-11-11 `VRCommand-ControlServer-0.31.116-replay-loss-win-x64.zip` 為 53,007,796 bytes，SHA-256 `d169c1b8cf8d7f5b5c9376c43b4aebbb40b1716c87860346934d9e3bb8ec3c3c`。解壓核對 555 筆清單及 535 個發行檔案。回放片段、逐格與最終戰績依實際生命值耗損核對。 [片段戰績](WORLD_RECORDING.md#重看指定片段) · [發行核對](../artifacts/venue-release-0.50.4-replay-loss.json)

2026-11-11 `VRCommand-ControlServer-0.31.115-venue-launch-review-win-x64.zip` 為 53,007,477 bytes，SHA-256 `24b159207ef17782e6aa308d320017a9a9d4908498b10059af6a101534993866`。解壓核對 555 筆清單與 535 個發行檔案。主控可從原啟動報告唯讀核對來源及端點。 [操作方式](WINDOWS_SERVER_PACKAGE.md#核對未確認的啟動報告) · [發行核對](../artifacts/venue-release-0.50.4-launch-review.json)

2026-11-11 `VRCommand-ControlServer-0.31.114-venue-source-batch-win-x64.zip` 為 52,989,867 bytes，SHA-256 `f529ae0a5ce5dcd8e404fce7a0c36b7b54ba7c256483e422227c154f10ce855c`。解壓核對 552 筆清單與 532 個發行檔案。管理服務在同一筆交易核對並登記整批遊戲來源。 [操作方式](WINDOWS_SERVER_PACKAGE.md#依場館計畫批次啟動)

2026-11-11 `VRCommand-ControlServer-0.31.113-guarded-source-win-x64.zip` 為 52,985,085 bytes，SHA-256 `c713cb92051b7b9ff145e904e795dca8d6fd153d79294df0fc1b9d9dc376a513`。解壓核對 552 筆清單與 532 個發行檔案。搭配 1.14 啟動器，核對場次序號與寫入遊戲來源在同一次操作完成。 [操作方式](WINDOWS_SERVER_PACKAGE.md#依場館計畫批次啟動) · [發行核對](../artifacts/venue-release-0.50.3-guarded-source.json)

2026-11-11 `VRCommand-ControlServer-0.31.112-venue-plan-win-x64.zip` 下載的第二版場館計畫包含場次序號與任務版本，搭配 Windows 啟動器 1.13。ZIP 為 52,984,487 bytes，SHA-256 `ae2bc7c2efb5c9eab6f7b0be69665abb83c2672ae96571677a259dcd7727b8b4`，解壓核對 552 筆清單與 532 個發行檔案。 [操作方式](WINDOWS_SERVER_PACKAGE.md#從主控台下載場館計畫) · [發行核對](../artifacts/venue-release-0.50.2-plan-revisions.json)

2026-11-11 `VRCommand-ControlServer-0.31.111-receipt-export-win-x64.zip` 可下載全館原批次的戰績回條 JSON，供離線驗收與玩家及伺服器日誌逐席核對。ZIP 為 52,984,201 bytes，SHA-256 `acee48db25c7a4752c35b74deb0cafe4d4878526eb9935dc845d3547969cde9f`，解壓核對 552 筆清單與 532 個發行檔案。 [操作方式](SESSION_CLOSURE.md#下載本批戰績回條) · [發行核對](../artifacts/venue-release-0.50.2-receipt-export.json)

2026-11-11 `VRCommand-ControlServer-0.31.110-startup-validation-win-x64.zip` 在操作員憑證設定不合規，或工作階段、任務庫無法取得寫入鎖時，以失敗碼 1 及明確診斷結束新程序。ZIP 為 52,980,876 bytes，SHA-256 `7a961c987685e2d0f081957a84e71397a9be08c6b8e585241db4b12f79d8582f`，解壓核對 552 筆清單及 532 個發行檔案。 [發行核對](../artifacts/venue-release-0.50.2-startup-validation.json)

2026-11-11 `VRCommand-ControlServer-0.31.110-venue-debrief-win-x64.zip` 可在全館收尾逐房核對戰績回條。ZIP 為 52,979,956 bytes，SHA-256 `2ba2320c161cbbc9b8c3d02d401110fe82ea41efd3782f263fb3b618b686da2b`，解壓核對 552 筆清單與 532 個發行檔案。搭配 Windows 與 Quest 遊戲 0.50.2。 [操作方式](SESSION_CLOSURE.md#全館批次結束) · [發行核對](../artifacts/venue-release-0.50.2-venue-debrief.json)

2026-11-10 `VRCommand-ControlServer-0.31.109-debrief-win-x64.zip` 可在個別場次查看玩家戰績回條。ZIP 為 52,976,827 bytes，SHA-256 `8dbc8121a660e1123afd41ab4dcd24b10536af19f589402f8f5cccd5890eb27a`，解壓核對 552 筆清單與 532 個發行檔案。 [玩家戰績回條](SESSION_CLOSURE.md#玩家戰績回條)

2026-11-10 `VRCommand-ControlServer-0.31.108-workstations-win-x64.zip` 可為六個操作員角色簽發管理連線回條。ZIP 為 52,970,098 bytes，SHA-256 `f1899e4749f7fd29350c2c743c62cbd0752131bd15e02d886a6f75fbbb0d3679`，解壓核對 552 筆清單與 532 個發行檔案。 [工作站核對](#核對主控與五房控的直連來源)

2026-11-10 `VRCommand-ControlServer-0.31.108-venue-https-win-x64.zip` 可同時提供場館 HTTPS 與本機遊戲管理 HTTP。ZIP 為 52,958,499 bytes，SHA-256 `75404520bae27eff4a8da79538e3f44055620cf1b8ee5f5e7025c5de967a3ca5`。解壓核對 552 筆清單及 532 個發行檔案。 [場館設定](#啟用場館-https)

2026-11-10 `VRCommand-ControlServer-0.31.108-win-x64.zip` 支援從發射、命中及擊殺追查同發射擊。ZIP 為 52,955,370 bytes，SHA-256 `777724118f443456c61f90507a20283ba7204a8a60d05ecb27ff7cc3d46bf356`。解壓核對 552 筆清單及 532 個發行檔案。 [射擊檢討](WORLD_RECORDING.md#追查同發射擊)

2026-11-10 `VRCommand-ControlServer-0.31.107-win-x64.zip` 支援依原錄製起訖讀取片段戰績。ZIP 為 52,944,041 bytes，SHA-256 `cf7a9fe38754e08335790992ea70c1dd145daf827c4030a50f4f071350c58036`。解壓核對 549 筆清單及 529 個發行檔案。 [片段回放](WORLD_RECORDING.md#重看指定片段)

2026-11-10 `VRCommand-ControlServer-0.31.106-win-x64.zip` 在五房追蹤總覽顯示共同取樣及各房原畫格，並可直接開啟中斷回放。ZIP 為 52,933,388 bytes，SHA-256 `4337bd3734be390c0a007beb9efa514b503d225d4e7ea007af206eb4adb48463`。解壓核對 546 筆清單及 526 個發行檔案。 [追蹤總覽](PLAYER_READINESS.md#執行中五房追蹤總覽)

2026-11-10 `VRCommand-ControlServer-0.31.105-win-x64.zip` 支援 Quest 五房追蹤工具一次取得原場次的共同取樣。ZIP 為 52,930,231 bytes，SHA-256 `8d420e1c7b9ec6a9b4df0d2e450543c93ae4ac78085116a9115e5805d1e204b3`。解壓核對 546 筆清單及 526 個發行檔案。 [追蹤驗收](QUEST3.md#核對頭盔追蹤席位)

2026-11-10 `VRCommand-ControlServer-0.31.104-win-x64.zip` 支援 Quest 逐席寫入前驗證原端點、名冊與遊戲來源。ZIP 為 52,926,956 bytes，SHA-256 `c47651bbb4e6634a0969dc3e12ff48d84d45e8cb18215e893093fce09ea3c783`。解壓核對 546 筆清單及 526 個發行檔案。 [部署操作](QUEST3.md#用裝置清單部署-25-席)

2026-11-10 `VRCommand-ControlServer-0.31.103-win-x64.zip` 會在 Quest 3 MR 五房部署頁顯示各房原端點，並在瀏覽器交付 ZIP 前重新核對來源。ZIP 為 52,925,549 bytes，SHA-256 `27ec4e6f1a50a12fdb31cde4313d8cd7b2e173a68f7795633b43926fba1bf72b`。解壓核對 546 筆清單及 526 個發行檔案。 [部署操作](QUEST3.md#從主控台下載五房部署包)

2026-11-10 `VRCommand-ControlServer-0.31.102-win-x64.zip` 可在原來源短暫停止更新時停用已開啟的五房配票預覽，並在同一來源恢復後重新開放下載。ZIP 為 52,924,195 bytes，SHA-256 `bea1676d7621421c96ccfb3821e36b609fbeaeab614c2c7c71089bafafa1c214`。解壓核對 546 筆清單及 526 個發行檔案。 [配票操作](EXTERNAL_CLIENTS.md#按房間下載連線檔)

2026-11-10 `VRCommand-ControlServer-0.31.101-win-x64.zip` 會在原遊戲來源沒有近期有效畫格時暫停新批次端點的配票。ZIP 為 52,922,457 bytes，SHA-256 `5d0c83b19b7bfd39c9a1057ae4874227d79f6cbb95010a76c60ac73014c80793`。解壓核對 546 筆清單及 526 個發行檔案。 [配票操作](EXTERNAL_CLIENTS.md#按房間下載連線檔)

2026-11-10 `VRCommand-ControlServer-0.31.100-win-x64.zip` 支援整批公告場館端點。ZIP 為 52,920,674 bytes，SHA-256 `2a36a4ddf18c9d10efddae31311ce5287e0f10b18d298b0686ffee625190b46e`。解壓核對 546 筆清單及 526 個發行檔案。 [五房啟動](WINDOWS_SERVER_PACKAGE.md#依場館計畫批次啟動)

2026-11-10 `VRCommand-ControlServer-0.31.99-win-x64.zip` 可確認分房恢復沿用全場敵軍策略，並核對全館預覽後是否有更新的分房命令。ZIP 為 52,916,425 bytes，SHA-256 `86a02a8f2c7b6cf04560703315adfed0c1392379519b30c7794e41b4c58ce2ef`。解壓核對 546 筆清單及 526 個發行檔案。 [分房操作](LAYOUT.md#合併場分房敵軍策略)

2026-11-10 `VRCommand-ControlServer-0.31.98-win-x64.zip` 加入合併場的分房敵軍策略。ZIP 為 52,913,898 bytes，SHA-256 `e991ce29abceb85fdb94488f2958be31461cf4ad8d52f54f921433f26abfa4cd`。解壓核對 546 筆清單及 526 個發行檔案，通過 107 項管理包檢查。 [分房操作](LAYOUT.md#合併場分房敵軍策略)

2026-11-10 `VRCommand-ControlServer-0.31.97-win-x64.zip` 可下載五房 Windows 伺服器啟動計畫。ZIP 為 52,907,145 bytes，SHA-256 `2635ab1537219de08a97f99566fcc027874f5e3f694ea35a046bdf53562921b7`。解壓核對 546 筆清單及 526 個發行檔案，通過 107 項管理包檢查。 [下載計畫操作](WINDOWS_SERVER_PACKAGE.md#從主控台下載場館計畫)

2026-11-10 `VRCommand-ControlServer-0.31.96-win-x64.zip` 可逐房查閱回放中的敵軍增援與撤除。ZIP 為 52,894,327 bytes，SHA-256 `d362eabf85a2fd8775654f846a5b756a21f8a15b69c638f2e36e44c883a1d2f7`。解壓核對 543 筆清單及 523 個執行檔，通過 107 項管理包檢查。建置憑證記錄封裝開始時的基底 `e6bd807`，另逐檔核對 174 個建置輸入與功能提交的內容相同。 [回放操作](WORLD_RECORDING.md#查閱錄製中的設定切換)

2026-11-10 `VRCommand-ControlServer-0.31.95-win-x64.zip` 可在暫停的戰鬥事件上標記前後保存畫格。ZIP 為 52,890,437 bytes，SHA-256 `2cc8506a3a418b431b89a0c42258b5bf2d193eec479a83d51d12abaa590333e1`。解壓核對 543 筆清單及 523 個執行檔，通過 107 項管理包檢查。 [回放操作](WORLD_RECORDING.md#重看指定片段)

2026-11-10 `VRCommand-ControlServer-0.31.94-win-x64.zip` 提供主控的五房硬體名冊快照。ZIP 為 52,886,246 bytes，SHA-256 `079c47487ada9c4c51862abe5b4854c416469d4e954be2d568b3e65d23921d63`。解壓核對 543 筆清單與 523 個執行檔。 [五房綁定操作](HARDWARE.md#一次建立五房設備綁定)

2026-11-10 `VRCommand-ControlServer-0.31.93-win-x64.zip` 提供同批獨立房間的回放對齊。ZIP 為 52,884,271 bytes，SHA-256 `17123aae22f880a0a647c41ec094e1d21ce381f8318e3f0aa0a134f892bda9ef`。解壓核對 543 筆清單與 523 個執行檔。 [回放操作](WORLD_RECORDING.md#對齊同批獨立房間的回放)

2026-11-10 `VRCommand-ControlServer-0.31.92-win-x64.zip` 提供全館開場逐席狀態。ZIP 為 52,878,039 bytes，SHA-256 `b5c2432541bffb257f4fa52b579dfb956308672566856f705caad6499d6f8db7`。解壓核對 543 筆清單與 523 個執行檔。 [開場操作](MISSION_CLOCK.md#全館開始)

2026-11-10 `VRCommand-ControlServer-0.31.91-win-x64.zip` 可從全館結束批次套用五房原任務版本。ZIP 為 52,875,286 bytes，SHA-256 `3aaf852593eb65c4939b7e7b140045ee2cd76a81a963a24b64d45f32608801d8`。解壓核對 543 筆清單與 523 個執行檔。 [操作說明](MISSION_VERSIONS.md#從全館收尾套用五房原版本)

2026-11-10 `VRCommand-ControlServer-0.31.90-win-x64.zip` 提供觀戰統計的玩家列跟隨。ZIP 為 52,872,341 bytes，SHA-256 `a0f1782e26014a67a48b784fb5c8c72c4c418ed2ba9dcdb34a47503c1d457a9e`。解壓核對 543 筆清單與 523 個執行檔。 [觀戰操作](WORLD_RECORDING.md#操作)

2026-11-10 `VRCommand-ControlServer-0.31.89-win-x64.zip` 新增個人封存戰績 CSV。ZIP 為 52,871,130 bytes，SHA-256 `ad3d3a73389c300f51740f3e3f33a58c835c98d4f01adc60f6e18ccea0259f9d`。解壓核對 543 筆清單與 523 個執行檔。 [個人戰績](REPORTS.md#從戰績開啟個人回放)

2026-11-10 `VRCommand-ControlServer-0.31.88-win-x64.zip` 新增封存戰績的「跳到最近中彈」。ZIP 為 52,869,754 bytes，SHA-256 `44b0f03bd3dc4117c7117666409990442d221b4dfe6b638173bea323f729fbea`，解壓核對 543 筆清單與 523 個執行檔。 [戰後檢討](REPORTS.md#從戰績開啟個人回放)

2026-11-10 `VRCommand-ControlServer-0.31.87-win-x64.zip` 提供從姿態中斷快照返回即時觀戰。ZIP 為 52,868,764 bytes，SHA-256 `afa049dddb70971d7fcf880e35913e20a5eb18fa4e270aeda15b6238058dce22`，解壓核對 543 筆清單與 523 個執行檔。 [房卡操作](PLAYER_READINESS.md#從房卡查看姿態中斷快照)

2026-11-10 `VRCommand-ControlServer-0.31.86-win-x64.zip` 提供 VR／MR 房卡姿態中斷快照。ZIP 為 52,868,690 bytes，SHA-256 `970a23fd1fb2c73e53f0d3d79b312cd09e7c0477c82d3c039ffc967e0a2abec9`，解壓核對 543 筆清單與 523 個執行檔。 [房卡操作](PLAYER_READINESS.md#從房卡查看姿態中斷快照)

2026-11-10 `windows-control-console-0.31.83-vr-resume-win-x64.zip` 提供 VR 房卡席位恢復檢查與繼續。ZIP 為 52,852,966 bytes，SHA-256 `d203ce5545ff84d2c553898e9494a327a03f2991b343d7c24e85bf3476ca1c4d`，解壓核對 540 筆清單及 520 個執行檔案。 [恢復操作](PLAYER_READINESS.md#從-vr-房卡確認恢復並繼續)

2026-11-10 `windows-control-console-0.31.82-vr-pause-win-x64.zip` 提供 VR 房卡暫停與遊戲端套用確認。ZIP 為 52,850,515 bytes，SHA-256 `9f2f4bf1390a25307cd0cc2966639409db81f45113fabb28c6e7370c7d4404ed`，解壓核對 540 筆清單及 520 個執行檔案。 [房卡操作](PLAYER_READINESS.md#從-vr-房卡暫停檢查席位)

2026-11-10 `windows-control-console-0.31.81-venue-scores-win-x64.zip` 在全館收尾提供分房最終戰績與本批合計。ZIP 為 52,847,763 bytes，SHA-256 `1dd1051f1462d54af63bccd5caa1574224e636f43cf1bdd96ef1da64e429a555`，解壓核對 540 筆清單及 520 個執行檔案。 [戰績操作](REPORTS.md#在全館收尾比較分房戰績)

2026-11-10 `windows-control-console-0.31.80-participation-replay-win-x64.zip` 可從全館收尾回看有效姿態開場。ZIP 為 52,842,586 bytes，SHA-256 `ed34a4a3e8cf1170e21e335f72a074058c3b5389d78fa32b833119c550132ce7`，解壓核對 540 筆清單及 520 個執行檔案。 [開場回看](SESSION_CLOSURE.md#回看有效姿態開場)

2026-11-10 `windows-control-console-0.31.79-participation-closure-win-x64.zip` 提供場館驗收 ZIP 的有效姿態開場畫格指標。ZIP 為 52,841,556 bytes，SHA-256 `36f9afd313e021339f17ac06327e90a3111d2c95d84447e4e9d27927de966114`，解壓核對 540 筆清單及 520 個執行檔案。 [封存核對](EXTERNAL_CLIENTS.md#核對五房有效姿態開場)

2026-11-10 `windows-control-console-0.31.78-full-participation-win-x64.zip` 提供可選的五房 25 席有效姿態開場。ZIP 為 52,840,795 bytes，SHA-256 `d4cdbbdb51b399596f846853c543f57a9756bb1a5dbe514b678bc005fa513292`，解壓核對 540 筆清單與 520 個執行檔案。 [開場操作](PLAYER_READINESS.md#五房各-5-席有效姿態開場)

2026-11-10 `windows-control-console-0.31.77-live-watch-win-x64.zip` 提供即時觀戰中斷後的同來源重連。ZIP 為 52,839,148 bytes，SHA-256 `43f7dd9454adf46b3bf0aec1441451417aa7568199c50929bcf84c5d445f08f7`，解壓核對 540 筆清單與 520 個執行檔案。 [觀戰操作](WORLD_RECORDING.md#即時觀戰斷線後重新連接)

2026-11-10 `windows-control-console-0.31.76-fine-opening-win-x64.zip` 提供場地通路的細格補查。ZIP 為 52,837,112 bytes，SHA-256 `9296a87ff50338c8a35862dda7d45f36326751ff614def8cacf99a844a0490e5`，解壓核對 540 筆清單與 520 個執行檔案。 [場地操作](LAYOUT.md#出生位通路預覽)

2026-11-10 `windows-control-console-0.31.75-player-room-replay-win-x64.zip` 提供合併錄製的分房玩家回放。ZIP 為 52,835,923 bytes，SHA-256 `ce937ef5e582d9bf73b63ecac789719e8ab5ef387fb7cfe26947675fe5f7b1ea`，解壓核對 540 筆清單與 520 個執行檔案。 [回放操作](WORLD_RECORDING.md#讓玩家開啟回放)

2026-11-10 `windows-control-console-0.31.74-ticket-download-win-x64.zip` 提供下載前再次核對配票名冊。ZIP 為 52,829,273 bytes，SHA-256 `5d42f2497a03df275644c5a06f71c4c60abe1048089c34da81750d315351fe80`，解壓核對 540 筆清單與 520 個執行檔案。 [配票操作](EXTERNAL_CLIENTS.md#下載前再次核對名冊)

2026-11-10 `windows-control-console-0.31.73-statistics-snapshot-win-x64.zip` 提供同序號的場次、玩家戰績與最近事件。ZIP 為 52,827,832 bytes，SHA-256 `d5e948cacbdda15a9093cd6806ea287a20313e98efaed5c7ea133dde5daac5d6`，解壓核對 540 筆清單與 520 個執行檔案。 [戰績操作](REPORTS.md#場次與戰績同步)

2026-11-10 `windows-control-console-0.31.72-live-tracking-win-x64.zip` 提供執行中五房追蹤總覽。ZIP 為 52,827,383 bytes，SHA-256 `51d69438ecb3b8565d92a0cae98926ddb52d048fdef9a24b00e0af0b40afc737`，解壓核對 540 筆清單與 520 個執行檔案。 [操作方式](PLAYER_READINESS.md#執行中五房追蹤總覽)

2026-11-10 `windows-control-console-0.31.71-environment-batch-win-x64.zip` 提供最近一批全館環境指令的逐房核對及快照入口。ZIP 為 52,823,437 bytes，SHA-256 `daad337381f86a80dd65889a5405d2ec846d40d0fed9c45f9bb3c07d162fcb43`。解壓核對 540 筆清單，含 520 個執行檔案，通過 106 項管理包檢查。 [環境核對](ENVIRONMENT.md#核對最近一批環境指令)

2026-11-10 `windows-control-console-0.31.70-placement-row-win-x64.zip` 加入成列複製及小數座標與角度儲存。ZIP 為 52,820,861 bytes，SHA-256 `612da6dea5dad1381f59c473ceddb5d8fb4a9c4dbf8c95e09f54de0f5d413cc2`。解壓核對 540 個清單檔案，含 520 個執行檔案，通過 106 項管理包檢查。 [成列操作](LAYOUT.md#複製物件成列)

2026-11-10 `windows-control-console-0.31.69-enemy-batch-win-x64.zip` 加入最近一批全館敵軍策略的逐房核對。ZIP 為 52,818,502 bytes，SHA-256 `c11e0ae8199fc2778032b0b970b33f3f732133c0b3e7f982b1f5617c7b4e1ce9`。解壓核對 540 個清單檔案，含 520 個執行檔案，通過 106 項管理包檢查。 [敵軍策略核對](LAYOUT.md#核對最近一批敵軍策略)

2026-11-10 `windows-control-console-0.31.68-instant-replay-win-x64.zip` 加入即時觀戰回看。ZIP 為 52,813,246 bytes，SHA-256 `a8b5c15480155eebf2ef38315bcc4de1a1451d9f9e92197be1ac16af73428943`。解壓核對 540 個清單檔案，含 520 個執行環境檔案，通過 106 項管理包檢查。 [觀戰操作](WORLD_RECORDING.md#從即時觀戰回看最近-10-秒)

2026-11-09 `windows-control-0.31.48-win-x64.zip` 在房卡顯示原遊戲伺服器公布的 UDP 端點。ZIP 為 52,735,775 bytes，SHA-256 `7bcbbb8e03cbe4735133567a1164bdea548872f37cae528ab3777b8cd9b1ff6f`。解壓核對 528 個清單檔案，含 508 個執行環境檔案，通過 106 項管理包檢查。 [房卡操作](EXTERNAL_CLIENTS.md#五房房卡的連線端點)

2026-11-09 `windows-control-0.31.47-win-x64.zip` 加入混合 VR／MR 五房獨立部署。ZIP 為 52,734,795 bytes，SHA-256 `e44221aeaade39748aa9f53097dacb3c882e0c7e83bdf4a116744f9d83331f90`。解壓核對 528 個清單檔案，含 508 個執行環境檔案，通過 106 項管理包及 98 項原生伺服器混合部署檢查。 [混合配票](QUEST3.md#混合-vr-與-mr-五房部署包)

2026-11-09 `windows-control-0.31.46-final-win-x64.zip` 加入五房逐房指定任務版本。ZIP 為 52,720,812 bytes，SHA-256 `8e02b23ad367fcfd8b5aa0c33b5c1beb0733094e330a690cd248ebbf6c2e7a8d`。解壓核對 528 個清單檔案，含 508 個執行環境檔案，通過 106 項管理包及 527 項 Chromium 檢查。早期同版候選保留，交付版的任務選單改為較寬的欄位。 [逐房操作](MISSION_VERSIONS.md#逐房指定任務版本)

2026-11-09 `windows-control-0.31.45-win-x64.zip` 加入保存版本的開場平面圖。ZIP 為 52,707,989 bytes，SHA-256 `0bb155a0c0a972db1a696a4fce02c41c1111be3e0439623336d4c87193ff2849`。解壓核對 525 個清單檔案，含 505 個執行環境檔案，通過 106 項管理包及 521 項 Chromium 檢查。 [開場平面圖](LAYOUT.md#開場前查看保存版本平面圖)

2026-11-09 `windows-control-0.31.44-win-x64.zip` 加入個人事件回放。ZIP 為 52,705,739 bytes，SHA-256 `973a31e68d7e3ac6849d22b03068f0ad52b8505fa598d8c2129dc10dcd6532c9`。解壓核對 525 個清單檔案，含 505 個執行環境檔案，通過 106 項管理包及 514 項 Chromium 檢查。 [戰後檢討](REPORTS.md#從戰績開啟個人回放)

2026-11-09 `windows-control-0.31.43-win-x64.zip` 加入任務回放戰鬥事件搜尋。ZIP 為 52,702,213 bytes，SHA-256 `f10eefebbfdd050d6bba691007c6abae79ba3b0ba03c37b7c39e4c0d53af2827`。解壓核對 525 個清單檔案，含 505 個執行環境檔案，通過 106 項管理包及 509 項 Chromium 檢查。 [回放操作](WORLD_RECORDING.md#依房間與種類搜尋戰鬥事件)

2026-11-09 `windows-control-0.31.42-win-x64.zip` 加入 VR 五房原始連線檔的線上驗票與端點核對，供 Quest 部署工具使用。ZIP 為 52,691,458 bytes，SHA-256 `c0221ebcae33a688d630f1b495fe984f3013144983ba01f3fa0a5a4fd42cfdb4`。解壓核對 522 個清單檔案，含 502 個執行環境檔案，通過 106 項管理包及 20 項 Chromium 專項。 [部署操作](QUEST3.md#直接使用-vr-五房連線-zip)

2026-11-09 `windows-control-0.31.41-win-x64.zip` 加入 VR 五房配票。ZIP 為 52,685,935 bytes，SHA-256 `e0271a060aaf2574779edcf64fea82673fb3ef9c92d4c9eb51b352b135549198`。解壓核對 522 個清單檔案，含 502 個執行環境檔案，通過 106 項管理包及 16 項 Chromium 專項。 [操作方式](EXTERNAL_CLIENTS.md#vr-五房配票)

2026-11-09 `windows-control-0.31.40-win-x64.zip` 加入全館收尾的批次場館驗收 ZIP。ZIP 為 52,669,871 bytes，SHA-256 `0dd5f090842866875de22dc0e2c9b2700976ae7d3e0534789305b6e38c0b9c7e`。解壓核對 519 個清單檔案，含 499 個執行環境檔案，通過 106 項管理包及 54 項 Chromium 專項。 [操作方式](SESSION_CLOSURE.md#下載本批場館驗收)

2026-11-09 `windows-control-0.31.39-win-x64.zip` 加入全館收尾歷史分頁與批次選取。ZIP 為 52,666,279 bytes，SHA-256 `e04a246feec0cfd1eb9447605cfedd42b771f4547498ddd66edaf7a37cbeda57`。解壓核對 519 個清單檔案，含 499 個執行環境檔案，通過 106 項管理包及 49 項 Chromium 專項。 [操作方式](SESSION_CLOSURE.md#歷史批次)

2026-11-09 `windows-control-0.31.38-win-x64.zip` 加入房卡即時俯視與全館收尾直接回放。ZIP 為 52,657,530 bytes，SHA-256 `fdc8f6dea454a2a96529ea93c9b517532af75110a03dd22d608f13ba6cd62161`。解壓核對 516 個清單檔案，含 496 個執行環境檔案，通過 106 項管理包及 43 項 Chromium 專項。 [操作方式](WORLD_RECORDING.md#從房卡或全館收尾開啟)

2026-11-09 `windows-control-0.31.37-win-x64.zip` 加入全館結束批次的戰績 ZIP。ZIP 為 52,654,339 bytes，SHA-256 `7a7c856b24e2c155a39095b76c2e623215becde878db63d4ff95d6cc41baa1ac`。解壓核對 516 個清單檔案，含 496 個執行環境檔案，通過 106 項管理包及 38 項 Chromium 專項。 [報表操作](REPORTS.md#下載全館結束批次)

2026-11-09 `windows-control-0.31.36-win-x64.zip` 加入全館敵軍策略與逐房快照確認。ZIP 為 52,648,048 bytes，SHA-256 `bec21e893db1de7d458bc8b8f11d9ef1680c6ce96517d5f00c20ef963dae8f7a`。解壓核對 516 個清單檔案，含 496 個執行環境檔案，通過 106 項管理包及 33 項 Chromium 專項。 [全館敵軍策略](LAYOUT.md#全館敵軍策略)

2026-11-09 `windows-control-0.31.35-win-x64.zip` 加入全館即時環境與逐房快照確認。ZIP 為 52,643,959 bytes，SHA-256 `15c3c2016e77373bad9b5d228103fa552099c34029139f253e5c61e16634d9dc`。解壓核對 516 個清單檔案，含 496 個執行環境檔案，通過 106 項管理包及 29 項 Chromium 專項。 [全館環境](ENVIRONMENT.md#全館即時環境)

2026-11-09 `windows-control-0.31.34-win-x64.zip` 加入全館批次結束與原場次的封存總覽。ZIP 為 52,638,294 bytes，SHA-256 `d2e0a13b0f7d9b35708f1c75b9cc5e1527422b55d2d5215080685a6d070c68d8`。解壓核對 516 個清單檔案，含 496 個執行環境檔案，通過 106 項管理包及 25 項 Chromium 專項。 [全館收尾](SESSION_CLOSURE.md#全館批次結束)

2026-11-09 `windows-control-0.31.33-win-x64.zip` 加入全館批次開始，並由各房執行中快照確認套用。ZIP 為 52,631,401 bytes，SHA-256 `3169d74682ec46e6a2d4cc249a36821e9960c4ac22d85d9b61b2bc9bf5ef43b3`。解壓核對 516 個清單檔案，含 496 個執行環境檔案，通過 106 項管理包及 18 項 Chromium 專項。 [全館開始](MISSION_CLOCK.md#全館開始)

2026-11-09 `windows-control-0.31.32-win-x64.zip` 在房卡顯示全館暫停與繼續的遊戲端確認，並要求各目標場次確認暫停後才能批次繼續。ZIP 為 52,628,544 bytes，SHA-256 `29f5379275ebb5f15c1aae4f51a0e02641ab92f52b6b2559a10f8f3751aa261e`。解壓核對 516 個清單檔案，含 496 個執行環境檔案，通過 106 項管理包及 14 項 Chromium 專項檢查。 [全館操作](MISSION_CLOCK.md#全館暫停與繼續)

2026-11-09 `windows-control-0.31.31-win-x64.zip` 新增全館暫停與繼續。ZIP 為 52,623,859 bytes，SHA-256 `50ff83ac6bb8b2e9c872b25c7dfc6fa0892c171463f2d0c67c0f489b5fa8a162`。解壓核對 516 個清單檔案，含 496 個執行環境檔案，通過 106 項管理包檢查。 [全館操作](MISSION_CLOCK.md#全館暫停與繼續)

2026-11-09 `windows-control-0.31.30-win-x64.zip` 在五房總覽顯示最近接受的任務活動時間或自動結束倒數。ZIP 為 52,612,892 bytes，SHA-256 `a9ecdb2857166a31ee5f5e5568782d9ef77f2570a9f32d580338ea6cff8ddc43`。解壓核對 516 個清單檔案，含 496 個執行環境檔案，通過 106 項管理包檢查。 [房卡操作](MISSION_CLOCK.md#五房房卡)

2026-11-09 `windows-control-0.31.29-win-x64.zip` 加入 Quest 3 MR 五房部署包。ZIP 為 52,609,639 bytes，SHA-256 `49c5062eef233fa37dee0bf248fd0e4dc14727d43e3543337c9e911888a891f7`。解壓核對 516 個清單檔案，含 496 個執行環境檔案，通過 106 項管理包檢查。 [操作方式](QUEST3.md#從主控台下載五房部署包)

2026-11-09 `windows-control-0.31.28-win-x64.zip` 加入「五房各自獨立」準備模式。ZIP 為 52,593,371 bytes，SHA-256 `bf81456b4f6ce7de901a6163290f89aed551017b2d50847e02d32451bca6d307`。解壓核對 513 個清單檔案，含 493 個執行環境檔案，通過 106 項管理包檢查。 [操作方式](MISSION_VERSIONS.md#五房各自獨立)

2026-11-09 `windows-control-0.31.27-win-x64.zip` 加入按房間讀取即時戰鬥回饋。ZIP 為 52,586,583 bytes，SHA-256 `ab72ea260e8cfe404d51490f70285eb1b56e758cf722a70aad600622dade760f`。解壓核對 513 個清單檔案，通過 106 項管理包檢查。 [介面操作](HARDWARE.md#即時戰鬥回饋介面)

2026-11-09 `windows-control-0.31.26-win-x64.zip` 加入五房 MR 部署線上核對。ZIP 為 52,581,968 bytes，SHA-256 `a57a620c8dec978e991ced2a77ec49d0fa1573f19a5364e1fac4ae03b0c88f68`。解壓核對 513 個清單檔案，含 493 個執行環境檔案，通過 106 項管理包檢查。 [五房部署核對](QUEST3.md#向管理服務核對五房名冊)

2026-11-09 `windows-control-0.31.25-win-x64.zip` 加入 Quest 3 MR 席位部署核對，搭配遊戲 0.48.0。ZIP 為 52,577,088 bytes，SHA-256 `5a288322c250fed7d5c0436d4b93ce8ecae6bcc959ef5ce3b41b9039ca3f28a3`。解壓核對 513 個清單檔案，包含 493 個執行環境檔案，通過 106 項管理包檢查。 [席位核對](QUEST3.md#在管理台核對席位部署檔)

2026-11-09 `windows-control-0.31.24-win-x64.zip` 加入 MR 配票時的校正檔雜湊，搭配遊戲 0.48.0 和專案的 PowerShell 部署工具。ZIP 為 52,563,263 bytes，SHA-256 `cb37b880f03a070567685f4d03a6bea4c9e4f6a6c64f7c2cb2ff16d5b51fe066`，解壓核對 510 個清單檔案並通過 106 項檢查。 [部署操作](QUEST3.md#quest-3-場地對位部署)

2026-11-09 `windows-control-0.31.23-final-win-x64.zip` 加入主控台 MR 校正檔鎖定，搭配 Windows 遊戲 0.48.0。ZIP 為 52,562,191 bytes，SHA-256 `5f5d78549e699a1fd629a3509e2a1df451d213689698b93cf0705463b0bd2737`，解壓核對 510 個清單檔案及 106 項管理包檢查。 [主控操作](QUEST3.md#啟動-mr-伺服器前鎖定校正檔)

2026-11-09 `windows-control-0.31.22-mr-pins-win-x64.zip` 搭配遊戲 0.48.0，支援主控鎖定場次的 MR 校正檔。ZIP 為 52,551,678 bytes，SHA-256 `bf8f22a6101232e4decdd3f6a7cb77711012645d793587e51bf8823f6c0e8480`，解壓後核對 507 個清單檔案，106 項可攜管理包檢查通過。 [主控操作](QUEST3.md#啟動-mr-伺服器前鎖定校正檔)

2026-11-09 主包 `artifacts/control-packages/windows-control-0.31.22-win-x64.zip`，52,548,970 bytes，SHA-256 `aca1704db2c25852152f4bf0d0a0451adb2c688912b2a50efb6ee034971c3cf0`。檔案清單 507 筆，API 執行內容 487 份。解壓後通過 106 項管理包檢查及 22 項 MR 開場、執行中追蹤與繼續的瀏覽器檢查。 [執行中追蹤](PLAYER_READINESS.md#執行中追蹤)

0.31.21 的 `artifacts/control-packages/windows-control-0.31.21-final-win-x64.zip` 已保留，52,547,151 bytes，SHA-256 `c7b74ae46619102a01d5031e27e314cef1ab6ed7ba38de09737fd8c36e9a658f`。解壓後通過 106 項管理包檢查及 19 項 MR 開場與繼續瀏覽器檢查。 [MR 繼續檢查](PLAYER_READINESS.md#暫停後繼續)

0.31.20 的 `artifacts/control-packages/windows-control-0.31.20-win-x64.zip` 已保留，52,545,587 bytes，SHA-256 `19cb55b3cb9da52eac2041c8ddb6f3dac2be0a67508de389f853a15bb3f7836f`。解壓後通過 106 項管理包檢查及 12 項 MR 開場瀏覽器專項檢查。 [MR 開場檢查](PLAYER_READINESS.md#mr-開場條件)

0.31.19 的 `artifacts/control-packages/windows-control-0.31.19-final-win-x64.zip` 已保留，52,542,323 bytes，SHA-256 `28c590b5e3a4480e45fdaa501385dd18cdaf31af49175a5a520f2c2a3abbaa95`。解壓後通過 106 項管理包檢查。任務編輯器可預覽移除選取掩體後新開通的路徑。 [通路試算](LAYOUT.md#出生位通路預覽)

0.31.18 的 `artifacts/control-packages/windows-control-0.31.18-win-x64.zip` 已保留，52,539,720 bytes，SHA-256 `1d8f6f912f8e01d5ca888705437876ebe5873d051572c263c564daa418f04108`。主控可一次下載全場及五份分房戰績 CSV。 [五房戰績下載](REPORTS.md#一次下載五房戰績)

0.31.17 的 `artifacts/control-packages/windows-control-0.31.17-win-x64.zip` 已保留，52,538,304 bytes，SHA-256 `ee35a0e627b4993f5b4f50240ccd96e3b6502c49ca5bf970cdc51a5ff84cfeb4`。多房觀戰及回放可快速選房，同時聚焦鏡頭與篩選快照統計。 [觀戰操作](WORLD_RECORDING.md)

0.31.16 的 `artifacts/control-packages/windows-control-0.31.16-win-x64.zip` 已保留，52,535,773 bytes，SHA-256 `0f9226271f3750b2f0793fbe4c651c653d735370ce66a0e7a8993e3393dc1bc2`。開場區可預覽選定版本的任務條件與目標房間。 [任務版本操作](MISSION_VERSIONS.md)

0.31.15 的 `artifacts/control-packages/windows-control-0.31.15-win-x64.zip` 已保留，52,533,210 bytes，SHA-256 `5f71a0bb6cc5a12ae8cbedaf037eb6bd2008a8e0144cb2e3b1d96ebc46d4518f`。未封存回放可從剛看完的下一格接續補送的片段。 [接續已保存片段](WORLD_RECORDING.md#回放未封存的已保存片段)

0.31.14 新增全館主控的場館驗收 ZIP，可在封存場次的「任務收尾」下載名冊、統計與公告端點。該版 ZIP 已保留，52,531,647 bytes，SHA-256 `fb2df7651f01d1cbd1990083bf89d4730beef34918601f3b30a514d5af5addea`。 [場館驗收操作](EXTERNAL_CLIENTS.md#核對封存戰績與-udp-來源)

2026-11-08 交付 `artifacts/control-packages/control-server-api0.31.0-ui0.31.11-win-x64.zip`，52,521,554 bytes，SHA256 `ad64df163524f0ac04e6f641a3146cf5759e26bd8b231871320acb507beb832e`。檔案清單有 507 筆，管理服務執行內容共 487 份。控制台支援 MR 場地三點水平校正試算與 JSON 下載，重新解壓的管理包通過 106 項 Windows 檢查。 [場地水平校正試算](LAYOUT.md#mr-場地水平校正試算)

2026-11-06 交付 `artifacts/control-packages/control-server-api0.31.0-ui0.31.10-win-x64.zip`，52,508,822 bytes，SHA256 `cd1f7437460ab899c3295587fa32296fb72486d8ee5b0bd9902aabaf47be8f53`。檔案清單有 504 筆，管理服務執行檔與相依檔共 484 份。控制台可在錄製尚未封存時回放已保存片段。重新解壓的管理包通過 105 項 Windows 檢查。 [回放已保存片段](WORLD_RECORDING.md#回放未封存的已保存片段)

2026-11-06 交付 `artifacts/control-packages/control-server-api0.31.0-ui0.31.9-win-x64.zip`，52,506,196 bytes，SHA256 `d65ed155e3a4691f0193db07cdb2771c14727d43ccca5fd7b638749840144f2e`。檔案清單有 504 筆，管理服務執行檔與相依檔共 484 份。控制台可逐格檢視任務回放，並從指定序號續播。重新解壓的管理包通過 105 項 Windows 檢查。 [逐格檢視](WORLD_RECORDING.md#暫停逐格檢視)

2026-11-06 交付 `artifacts/control-packages/control-server-api0.31.0-ui0.31.8-win-x64.zip`，52,502,728 bytes，SHA256 `51d4cf3fd476d0b6f300b44d13b7ae3a64fc2b6b8a882a9b1a93343ca3f10005`。檔案清單有 504 筆，管理服務執行檔與相依檔共 484 份。五房連線場次可分房匯出最終戰績，解壓包通過 105 項 Windows 檢查。 [分房匯出](REPORTS.md#五房分房匯出)

2026-11-06 交付 `control-server-api0.31.0-ui0.31.7-win-x64.zip`，52,500,466 bytes，SHA256 `5bc8bdd6cbdcc9713337caab6d62556c97cc0848aad41e992fa04792c76f6d0e`。任務配置新增五個出生位到中線的取樣通路，解壓包通過 105 項 Windows 檢查。 [出生位通路預覽](LAYOUT.md#出生位通路預覽)

2026-11-06 交付 `control-server-api0.31.0-ui0.31.6-win-x64.zip`，52,494,879 bytes，SHA256 `aa37499ea550d7cce90f0bfd23d42162b4360bb3a5677e6e62bde5761b37b92e`。五房總覽新增有效姿態與兩種來源的人數，解壓包通過 105 項 Windows 檢查。 [五房總覽](PLAYER_READINESS.md#五房總覽)

2026-11-06 交付 `control-server-api0.31.0-ui0.31.5-win-x64.zip`，52,490,290 bytes，SHA256 `1984acf7b29aaace53054f306036625a7a38a041116e9e1be4491dd3b1b8e243`。控制台會保留命令的原場次，原場次離開清單後需重新選取。解壓包通過 105 項 Windows 檢查。 [場次切換與操作](SESSION_CLOSURE.md#場次切換與操作)

2026-11-06 交付包 `control-server-api0.31.0-ui0.31.4-win-x64.zip`，52,489,449 bytes，SHA256 `158e4d10e5bde2e347f3661cbbfeefbe57231668e5ee5f7b7b1aba3a6198d18b`。控制台新增整房配票 ZIP。解壓包通過 105 項 Windows 檢查，實際 ZIP 也通過同機雙玩家入場與封存。 [開發進度](PROGRESS.md)

2026-11-06 交付包 `control-server-api0.31.0-ui0.31.3-win-x64.zip`，52,484,295 bytes，SHA256 `0bc73d3452638f83363ac663eee8f767c114449bd7b58e6789712b8512c682dc`。控制台 0.31.3 在配票前核對 IPv4 與埠號。解壓包通過 105 項 Windows 檢查，另有 89 項 Node 與 301 項瀏覽器回歸通過。 [開發進度](PROGRESS.md)

API **0.31.0**／控制台 **0.31.19**，管理服務可以獨立解壓執行。`Start-Control.exe`提供繁中介面，API隨包附帶.NET／ASP.NET Core **10.0.14 win-x64**，使用者電腦需要Windows x64及.NET Framework 4.8，管理服務不依賴Python或.NET SDK。遊戲伺服器可使用[獨立伺服器包](WINDOWS_SERVER_PACKAGE.md)，玩家另外啟動，參見[外部玩家流程](EXTERNAL_CLIENTS.md)與[Windows玩家包](WINDOWS_PLAYER_PACKAGE.md)。

0.31.2 交付包為`artifacts/control-packages/control-server-api0.31.0-ui0.31.2-placement-win-x64.zip`，**52,472,096 bytes／SHA256 `1eac2676113b47c58b5649ce444201e612603167a16d1e5bccb0599fc1dcf9a2`**、504 manifest／484 runtime。新增[場景物件復原／重做](PLACEMENT_HISTORY.md)，新Windows CLI105與實際解壓包29項瀏覽器操作成功；完整89 Node／296 Chromium。沿用原管理啟動器C#來源，沒有新WinForms GUI啟停或native遊戲／Unity建置驗收。

前版0.31.1主包`artifacts/control-packages/control-server-api0.31.0-ui0.31.1-closure-final-win-x64.zip`保持，**52,466,368 bytes／SHA256 `7d87669d0f8478feb328697c3d9d58005aa8f0e3331726080374fa6ab5a254e5`**、501 manifest／481 runtime檔案。新增[任務收尾與End重試](SESSION_CLOSURE.md)，新CLI105／真正browser UI End＋原生106通過；Windows啟動器C#來源保持，沒有新GUI啟停操作驗收。相同大小、SHA684f1f4d...的closure初候選保留，其舊End篩選反例未通過。以下初版0.31.0證據亦保留。

原初版主包為`artifacts/control-packages/control-server-0.31.0-release-win-x64.zip`，**52,456,642 bytes／SHA256 `b38391f1f72115a98a60ba1bc8f5cb1e7395abe633c1366c0fa9529dce794eb1`**、498份manifest檔案。檔名中的final、atomic、reviewed或ui是保留候選，驗收須對照本頁、manifest及[PROGRESS](PROGRESS.md)，不能只看版本或檔名。

## 使用

1. 完整解壓至本機簡短路徑，開啟`Start-Control.exe`。首次選擇 IPv4 與埠號，按「新增資料實例」。預設 `127.0.0.1:5081` 供本機使用。場館的其他控制電腦可使用 HTTPS 入口。 [場館設定](#啟用場館-https)
2. 按「啟動管理服務」，等候「服務已就緒」，再按「開啟控制台」。選擇Master或Room1–Room5，複製該角色金鑰到控制台登入；GameServer角色供遊戲伺服器使用。
3. 重開時按「選取資料實例」，選擇原資料夾的`control-instance.json`，再啟動。選取實例會帶回原地址／埠號；修改旁邊的設定只用於新增實例，不會默默改寫已選取實例。
4. 任務結束後等候正常戰績與封存完成，再停止管理服務。視窗關閉也會等待自己的API停止；API停止與任務End／世界seal是不同流程。

資料實例預設放在使用者LocalAppData的`VrCommand/ControlServers/<新識別>`。每個實例保有七個互異角色金鑰、玩家票券簽章金鑰、任務庫與場次／世界資料。完整保留該資料夾供重開及備份；只有全體writer停止後才備份全部檔案與WAL。管理服務包本身以程式、網站、執行環境與授權文件組成，實例資料由啟動器另外建立。

初版驗收在有 SDK 的電腦上移除啟動環境的 dotnet PATH，並設定不存在的 DOTNET_ROOT。實際 API 的程序 handle 與載入的 coreclr 路徑證實使用包內執行環境。初版當時的測試範圍為同機 HTTP。Windows 新機、跨機及頭盔各有現場驗收，啟動器不設定防火牆或系統網路。

## 啟用場館 HTTPS

在已停止的 `127.0.0.1` 管理實例資料夾內，放入 `control-https.json` 與 `control-https.pfx`。JSON 填管理電腦已配置的場館 IPv4。HTTPS 埠可用 443 或 1024 至 65535，須與管理實例原 HTTP 埠不同。

```json
{
  "schemaVersion": 1,
  "bindAddress": "192.168.50.10",
  "port": 8443
}
```

PFX 由場館管理員提供，包含一張當前有效的站台憑證、該憑證的私鑰，以及必要的中繼憑證。房控用的 DNS 名稱或 IPv4 要在憑證的名稱範圍內。管理員負責設定 DNS、房控信任及防火牆通行範圍。PFX 留在原本的私人資料實例，和操作員金鑰及資料庫一併保管。

在解壓後的管理包目錄執行下列 PowerShell，輸入 PFX 密碼後啟動圖形介面。選取原實例，再按「啟動管理服務」。

```powershell
$secure = Read-Host '管理 HTTPS PFX 密碼' -AsSecureString
try {
    $env:VR_COMMAND_CONTROL_PFX_PASSWORD = [System.Net.NetworkCredential]::new('', $secure).Password
    Start-Process -FilePath '.\Start-Control.exe'
} finally {
    Remove-Item Env:VR_COMMAND_CONTROL_PFX_PASSWORD -ErrorAction SilentlyContinue
    $secure.Dispose()
}
```

畫面顯示本機管理位址和房控 HTTPS 監聽位址。CLI `--run` 使用同一設定，並在就緒報告提供 `httpsBinding`。`uri` 仍是本機 HTTP，供本機遊戲伺服器與「開啟控制台」使用。房控應使用憑證上的 DNS 名稱或 IPv4 加 `/console/`。若 PFX、密碼或 HTTPS 埠有誤，本次啟動會失敗。更換憑證及監聽設定須先正常停止服務。 [Kestrel 端點與憑證](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/servers/kestrel/endpoints?view=aspnetcore-10.0)

## 從房控電腦核對管理服務

場館設定好管理網站的 HTTPS 入口後，在主控和五台房控電腦分別執行預檢。管理員另行提供正式 DNS 名稱（或憑證涵蓋的 IPv4）、埠號，以及站台葉憑證 DER 的 SHA-256。若管理員給的是 DER `.cer` 檔，可用 `Get-FileHash -Algorithm SHA256 -LiteralPath '.\management-leaf.cer'` 取得指紋。

```powershell
$fingerprint = Read-Host '管理員提供的站台憑證 SHA-256'
python .\scripts\check-venue-operator.py https://control.venue.example --role room3 --certificate-sha256 $fingerprint
```

主控選 `master`，房控依工作站選 `room1` 至 `room5`。提示出現後，只輸入該工作站被分配的操作員金鑰。若場館使用自己的 CA，可加上 `--ca-file .\venue-ca.pem` 讓這次檢查使用該 CA。預檢在每次送出請求前確認 TLS 信任鏈、站台名稱和葉憑證指紋，遇到轉址會停止。更換站台憑證後，使用管理員重新提供的指紋。

退出碼 `0` 和 `complete: true` 表示從本台工作站讀到控制台頁面、匿名存取遭拒，且主控看見五房或房控只看見自己的房間，每房容量為五席。失敗時可看 `failedCheck` 和 `error`。JSON 只保留來源、預期角色與驗證結果。此預檢使用既有 HTTPS 入口，涵蓋管理網站的唯讀連線和房間範圍。玩家 UDP、控制操作及現場跨機容量另有驗收。 [玩家連線驗收](EXTERNAL_CLIENTS.md#核對-25-席各自的直連來源)

### 核對主控與五房控的直連來源

控制台 0.31.123 可直接收集工作站回條。六台各自開啟管理員提供的場館 HTTPS 網址並登入，再到「房間與場次」展開「主控與五房控連線核對」。

1. 主控按「產生新代號」，將代號交給五台房控。
2. 主控及房控各自在本站輸入相同代號，按「下載本站回條」。畫面會顯示管理服務實際觀察到的來源位址。
3. 主控選取下方格式的 `workstations.json`，再一次選取六份原始回條。瀏覽器下載的回條與命令列預檢報告皆可使用，檔案順序不限。
4. 在回條有效的 15 分鐘內按「核對六台工作站」。管理服務核對原來源、角色、簽章、時間與監聽位址後，畫面列出主控和五房的確認結果。

控制台 0.31.184 會列出未通過的工作站與原因。可先選取已收到的回條，畫面會標示缺少或重複的角色，收齊後才提交管理服務。遇到來源位址不符，請讓對應房控從原場館 HTTPS 網址重新下載回條，並確認清單上的位址。回條過期時使用同一輪代號更新過期的回條。

瀏覽器使用作業環境的憑證信任設定。需要逐次比對管理員提供的葉憑證指紋時，使用下方命令列預檢。代號與回條選取只留在當前頁面，離開「房間與場次」或登出後須重新選取。切換代號或檔案會清除上次結果。管理連線核對可在建立場次前完成。

#### 命令列操作

使用新版管理包的直接 HTTPS 監聽位址。主控先用 `(New-Guid).Guid` 產生本輪代號，交給五房控。六台使用相同的 HTTPS 原點、憑證指紋及代號，各自以分配到的角色執行。下列為房 1 的例子，其他工作站更換 `--role` 與輸出檔名。使用私有 CA 時另加 `--ca-file .\venue-ca.pem`。

```powershell
$challenge = Read-Host '本輪工作站代號'
$fingerprint = Read-Host '管理站台憑證 SHA-256'
python .\scripts\check-venue-operator.py https://control.venue.example --role room1 --certificate-sha256 $fingerprint --venue-challenge $challenge | Set-Content .\room1.json -Encoding utf8
```

主控依原本的實體工作站配置建立 `workstations.json`。房間位址依房 1 到房 5 的順序排列。六個來源須為相異的私有 IPv4，主控可與管理服務同機，五個房控來源各須與管理服務位址不同。

```json
{
  "masterAddress": "192.168.50.10",
  "roomAddresses": ["192.168.50.21", "192.168.50.22", "192.168.50.23", "192.168.50.24", "192.168.50.25"]
}
```

在同一台主控工作站收集六份原始 JSON，並於 15 分鐘內送回同一個管理程序核對。

```powershell
python .\scripts\check-venue-operator.py https://control.venue.example --role master --certificate-sha256 $fingerprint --venue-challenge $challenge --verify-workstations .\workstations.json .\master.json .\room1.json .\room2.json .\room3.json .\room4.json .\room5.json
```

`complete: true` 表示六個角色各有一份同輪回條，簽章、時限與管理服務實際觀察到的來源都符合配置。管理服務重新啟動後，請使用新代號重做。回條含站台與工作站位址，留在場館私人資料夾。這項核對涵蓋直接管理連線的角色及位址，實體電腦標籤、玩家 UDP、場次操作及頭盔仍由現場驗收。 [玩家跨機驗收](EXTERNAL_CLIENTS.md#第二台電腦的驗收步驟)

`--verify-workstations` 可混用瀏覽器下載的原回條及命令列 JSON。可先傳入清單及已收到的一至六份檔案，命令列會在本機列出缺少或重複的角色，收齊後才連線。管理包 0.31.184 回傳的逐台拒絕原因也會列在 `issues`。`workstation` 的 0 代表主控，1 至 5 代表房號。失敗輸出不包含回條簽章或位址，退出碼為 1。

## 啟動與停止的證據

啟動器先核對manifest與來源檔案，再取得所選實例的exclusive lease。只啟動自己包內的API apphost，顯式指定資料／金鑰路徑並清除繼承的角色金鑰等覆寫。API在原始資料恢復與服務啟動成功後，透過私有stdout輸出本次隨機token的就緒事件；啟動器另核對原child仍存活、實際coreclr來自本包及原Master身分。單純程序啟動、埠號已開或別的服務回應不算就緒。

`ControlPipeToken`只有明確配置時才啟用，沒有新增HTTP停機或領取金鑰端點。短行的`STOP <本次token>`要求正常StopApplication；錯token不停止，EOF、過長／非ASCII輸入或讀取錯誤結束此私有控制管線。就緒輸出IO失敗也要求停止。啟動器的stdin writer關閉後，自己的API會退出；沒有配置的普通API仍沿原生命週期，不因stdin關閉自動退出。IPC不修改命令、入場、命中、姿態或世界資料格式。

正常停止等待原child handle退出，保留真正exit code；超過40秒的最後收尾才嘗試終止自己的child，再等5秒。強制或未知停止不能回報complete成功。圖形介面定期確認自己的child狀態，意外中斷時不持續顯示就緒；尚未確認停止則保留實例lease與視窗。

報告／金鑰寫入先完成同資料夾的exclusive暫存檔、Flush，再以新檔名Move發布，既有目的檔不覆蓋。舊候選使用CreateNew後才序列化，實際測試曾在發布期間讀到未完成JSON；原failed、binary及來源保持。受控反射呼叫實際編譯SaveNew、阻擋一個serializer getter時，舊版最終檔已可見且0 bytes，修正後最終檔不可見，放行後兩版內容相同。這是方法層級的原子發布反例，不當原Windows排程唯一原因證明。

## 建置與驗證

```powershell
pnpm --dir tests/browser install --frozen-lockfile
python scripts/publish-control-server.py --build-root "$env:LOCALAPPDATA/VrCommand/BuildRuns"
python scripts/package-control-server.py --publication <上述全新輸出目錄> --stage-root "$env:LOCALAPPDATA/VrCommand/Pkg" --output <新的ZIP>
python scripts/check-control-package.py <完整解壓後的VRCommand-ControlServer> --runtime-root "$env:LOCALAPPDATA/VrCommand/ControlChecks"
python scripts/check-control-https.py <完整解壓後的VRCommand-ControlServer> --runtime-root "$env:LOCALAPPDATA/VrCommand/HttpsChecks" --listen-address <本機場館IPv4>
python scripts/check-control-report.py <完整解壓後的VRCommand-ControlServer>
python scripts/check-control-gui.py <完整解壓後的VRCommand-ControlServer> --runtime-root "$env:LOCALAPPDATA/VrCommand/ControlChecks"
```

HTTPS 驗證可另帶 `--server-package <完整解壓後的VRCommand-GameServer>`，用一個 Windows 模擬玩家核對房控配票、即時畫格、回放與原戰績回條。使用啟動器 1.11 及 Windows 0.50.1 時，可加上 `--game-management-https` 一併核對原生伺服器的 HTTPS 管理請求與 WSS 世界上傳。憑證由測試在獨立實例產生，信任只限本次測試。

新版包可另加 `--operator-network`，用本機私有 IPv4 核對六角色原回條與單一來源拒絕。現場的六工作站使用前述主控驗收流程。

publish從明確的來源清單建立全新C槽snapshot，在該snapshot增加RID鎖定群組；原repository的NuGet lock不改，原依賴群組／contentHash必須一致。API及其依賴整組publish，self-contained runtimeconfig與必要native DLL明確核對；編譯、輸入與每份輸出雜湊保存於receipt。package拒絕資料庫、journal、票券／角色金鑰設定、額外publication檔案、連結與越界路徑。manifest是完整性清單，並非數位簽章。

105項Windows封裝檢查包含CLI拒絕、七角色與房控權限、五獨立API名冊共25席、原Preparing場次／admission及任務重開、私有檔案保持、後續Linked／active0、原API正常停止、父程序被終止後的EOF停止及有限診斷不含角色金鑰。25席只是管理名冊，沒有冒充25個遊戲端。GUI工具只準備自己的新實例及觀察程序；實際選檔／啟停／關窗透過native UI操作，review不能取代child退出及HTTP身分證據。先用CLI建立及暖啟動，GUI只重開同一實例，不操作新增金鑰、剪貼簿或瀏覽器登入。

額外6項真正API私有管線案例與7項Python封裝邊界檢查納入[精確1a959c6的成功CI](https://github.com/peca12968/vr-command-center/actions/runs/41332911824)；738規則／459 HTTP／47 world、Python／素材、78 Node／256 Chromium全部通過。Windows Framework／GUI及受控編譯方法反例只在本機執行，不由Linux CI代替。舊樹狀資料夾選擇的GUI場次未完成而failed，後改為可輸入路徑的設定檔選取；原件與cleanup保持。最終場次、CI43＋13檔證據、其他候選及未驗限制見[PROGRESS](PROGRESS.md)。

Notices保留實際NuGet／runtime包的原始metadata與授權；另附[SQLitePCLRaw上游參考授權](https://github.com/ericsink/SQLitePCL.raw/blob/v2.1.12/LICENSE.TXT)、[參考NOTICE](https://github.com/ericsink/SQLitePCL.raw/blob/v2.1.12/NOTICE.TXT)及[Microsoft.Data.Sqlite上游授權](https://github.com/dotnet/efcore/blob/v10.0.14/LICENSE.txt)，原blob byte雜湊已核對。SQLitePCLRaw實際2.1.13的原NuGet metadata保留；參考NOTICE來自明確標示的2.1.12，可能提到本包沒有的元件，不當成實際2.1.13來源版本證明。
