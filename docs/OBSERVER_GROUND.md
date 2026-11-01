# 雙擊場地定位觀戰鏡頭

2026-11-01：API／UI **0.30.2**。在「觀戰與任務回放」或「3D 模擬回放」的場景內，以滑鼠左鍵雙擊場地，鏡頭便看向所點地面上方0.8公尺，保留原角度與距離，並切至自由調整。原單擊角色選取、拖曳／平移、滾輪、方向鍵與精確數值介面繼續使用。此功能不會移動玩家、跳轉回放或送出管理命令。

投影採目前實際渲染鏡頭的透視射線與世界地面Y=0交點，只接受該錄製所列房間的12×12公尺範圍；房間中心X=(roomId−3)×14。房間之間的空隙、未包含的房間、外側、平行／向上／地板下方或非有限射線均不定位。不用物件／角色碰撞面替代地面，也不是MR實體地板、觸控雙擊或原生Unity鏡頭。

跟隨時成功定位才解除跟隨；房外雙擊不解除。未套用的數值草稿不被手勢覆蓋，按「讀取目前鏡頭」可取得新位置；需要日後切換時仍須明確命名保存。保存走原登入身分／場次隔離的書籤API，讀回及封存後回放沿用原位置，沒有自動寫入、修改錄製或新增授權。

本機6項幾何反例涵蓋透視交點、五房／邊界、間隙／缺房、反向／平行、NaN／overflow與非法ID；全部Node78、完整Chromium255通過。瀏覽器以真正pointer雙擊及可見表單核對新target、角度／距離、草稿保留、退出跟隨、房外不移動、無管理寫入、書籤／新登入重載與舊式回放不seek。新41份截圖／JSON在`artifacts/console-ground-camera-20261101`，ground截圖已檢視，軟體WebGL不當原生GPU或頭盔證據。

真正Windows場`desktop-venue/20261101-143859-67587c42`：操作員helper36250／browser80356皆terminal exit0，**54 UI／native檢查、165世界幀**、完整回放與ledger相符，原名冊替換／環境AI／Pause／End、個別結果／CSV／雙seal與active0成功；最大收到時來源年齡0.191771秒，不是RTT。新增五個定位檢查使用真正房1世界與可見控制，沒有場景global／玩家輸入／姿態注入。普通原生server／client沒有新診斷，3個入場身分含被替換者，並非25位操作或跨機。自己的writer全部停止才snapshot，新C14檔與F逐檔相符、48份F證據保留，原件不移動、保存SQLite不開。

本輪729規則／459 HTTP／47 world-stream、locked restore／零警告build成功；本機HTTP這次完整成功，不證明先前Windows拒絕startup逾時的根因／修復。只將API版本與三個既有PC工具gate協同升0.30.2，不改驗票／REST授權／world格式／rules0.8.0。原生來源仍Unity0.37.2／code47／NGO29與7d3e1a92...、原ID、既有199 Editor／雙平台／ZIP／APK；沒有新Editor測試或遊戲重建。

`ground-camera-validation.json`核對前620 browser／前輪74 runtime與F snapshot／Unity binaries及包hash、新41 browser／48 F證據／14 runtime，保存新C API134（新增JS與SDK產生的.gz）與三工具各9／Checks96的hash；不是完整OS或依賴graph。首次準備腳本因Windows預設cp950讀HTML失敗，該份C build保留；完整腳本明確UTF-8並使用新C build，測試採後者。

[精確5df27a8的CI41281968515](https://github.com/peca12968/vr-command-center/actions/runs/41281968515)完整success：729／459／47、工作流程Python／素材、78 Node／255 Chromium；41檔artifact13073935856與log／10,018,457 bytes ZIP／SHA7386c55d...下載核對。前661 browser＋新CI41＝702份保持，native48與runtime14／snapshot、原Unity binaries／ZIP／APK再次核對。2 Windows限定skip非Unity／頭盔證據，完整記錄見[PROGRESS](PROGRESS.md)，後續文件skip ci不改測試來源。

完整11項active，原31筆／world371姿態失效、F吞吐、多人持續操作、跨機、頭盔／MR與硬體仍待。
