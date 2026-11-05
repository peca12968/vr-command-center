# Windows 可攜管理服務

2026-11-06 交付 `control-server-api0.31.0-ui0.31.7-win-x64.zip`，52,500,466 bytes，SHA256 `5bc8bdd6cbdcc9713337caab6d62556c97cc0848aad41e992fa04792c76f6d0e`。任務配置新增五個出生位到中線的取樣通路，解壓包通過 105 項 Windows 檢查。 [出生位通路預覽](LAYOUT.md#出生位通路預覽)

2026-11-06 交付 `control-server-api0.31.0-ui0.31.6-win-x64.zip`，52,494,879 bytes，SHA256 `aa37499ea550d7cce90f0bfd23d42162b4360bb3a5677e6e62bde5761b37b92e`。五房總覽新增有效姿態與兩種來源的人數，解壓包通過 105 項 Windows 檢查。 [五房總覽](PLAYER_READINESS.md#五房總覽)

2026-11-06 交付 `control-server-api0.31.0-ui0.31.5-win-x64.zip`，52,490,290 bytes，SHA256 `1984acf7b29aaace53054f306036625a7a38a041116e9e1be4491dd3b1b8e243`。控制台會保留命令的原場次，原場次離開清單後需重新選取。解壓包通過 105 項 Windows 檢查。 [場次切換與操作](SESSION_CLOSURE.md#場次切換與操作)

2026-11-06 交付包 `control-server-api0.31.0-ui0.31.4-win-x64.zip`，52,489,449 bytes，SHA256 `158e4d10e5bde2e347f3661cbbfeefbe57231668e5ee5f7b7b1aba3a6198d18b`。控制台新增整房配票 ZIP。解壓包通過 105 項 Windows 檢查，實際 ZIP 也通過同機雙玩家入場與封存。 [開發進度](PROGRESS.md)

2026-11-06 交付包 `control-server-api0.31.0-ui0.31.3-win-x64.zip`，52,484,295 bytes，SHA256 `0bc73d3452638f83363ac663eee8f767c114449bd7b58e6789712b8512c682dc`。控制台 0.31.3 在配票前核對 IPv4 與埠號。解壓包通過 105 項 Windows 檢查，另有 89 項 Node 與 301 項瀏覽器回歸通過。 [開發進度](PROGRESS.md)

API **0.31.0**／控制台 **0.31.2**，管理服務可以獨立解壓執行。`Start-Control.exe`提供繁中介面，API隨包附帶.NET／ASP.NET Core **10.0.14 win-x64**，使用者電腦需要Windows x64及.NET Framework 4.8，管理服務不依賴Python或.NET SDK。遊戲伺服器可使用[獨立伺服器包](WINDOWS_SERVER_PACKAGE.md)，玩家另外啟動，參見[外部玩家流程](EXTERNAL_CLIENTS.md)與[Windows玩家包](WINDOWS_PLAYER_PACKAGE.md)。

目前主包為`artifacts/control-packages/control-server-api0.31.0-ui0.31.2-placement-win-x64.zip`，**52,472,096 bytes／SHA256 `1eac2676113b47c58b5649ce444201e612603167a16d1e5bccb0599fc1dcf9a2`**、504 manifest／484 runtime。新增[場景物件復原／重做](PLACEMENT_HISTORY.md)，新Windows CLI105與實際解壓包29項瀏覽器操作成功；完整89 Node／296 Chromium。沿用原管理啟動器C#來源，沒有新WinForms GUI啟停或native遊戲／Unity建置驗收。

前版0.31.1主包`artifacts/control-packages/control-server-api0.31.0-ui0.31.1-closure-final-win-x64.zip`保持，**52,466,368 bytes／SHA256 `7d87669d0f8478feb328697c3d9d58005aa8f0e3331726080374fa6ab5a254e5`**、501 manifest／481 runtime檔案。新增[任務收尾與End重試](SESSION_CLOSURE.md)，新CLI105／真正browser UI End＋原生106通過；Windows啟動器C#來源保持，沒有新GUI啟停操作驗收。相同大小、SHA684f1f4d...的closure初候選保留，其舊End篩選反例未通過。以下初版0.31.0證據亦保留。

原初版主包為`artifacts/control-packages/control-server-0.31.0-release-win-x64.zip`，**52,456,642 bytes／SHA256 `b38391f1f72115a98a60ba1bc8f5cb1e7395abe633c1366c0fa9529dce794eb1`**、498份manifest檔案。檔名中的final、atomic、reviewed或ui是保留候選，驗收須對照本頁、manifest及[PROGRESS](PROGRESS.md)，不能只看版本或檔名。

## 使用

1. 完整解壓至本機簡短路徑，開啟`Start-Control.exe`。首次選擇IPv4與埠號，按「新增資料實例」。預設127.0.0.1:5081只供本機；可明確選取本機已配置的IPv4供其他控制PC連線。
2. 按「啟動管理服務」，等候「服務已就緒」，再按「開啟控制台」。選擇Master或Room1–Room5，複製該角色金鑰到控制台登入；GameServer角色供遊戲伺服器使用。
3. 重開時按「選取資料實例」，選擇原資料夾的`control-instance.json`，再啟動。選取實例會帶回原地址／埠號；修改旁邊的設定只用於新增實例，不會默默改寫已選取實例。
4. 任務結束後等候正常戰績與封存完成，再停止管理服務。視窗關閉也會等待自己的API停止；API停止與任務End／世界seal是不同流程。

資料實例預設放在使用者LocalAppData的`VrCommand/ControlServers/<新識別>`。每個實例保有七個互異角色金鑰、玩家票券簽章金鑰、任務庫與場次／世界資料。完整保留該資料夾供重開及備份；只有全體writer停止後才備份全部檔案與WAL。管理服務包本身以程式、網站、執行環境與授權文件組成，實例資料由啟動器另外建立。

本輪在有SDK的這台PC，移除啟動環境的dotnet PATH、設定不存在的DOTNET_ROOT，再從實際API的OS程序handle與載入的coreclr路徑確認使用包內執行環境。這不是乾淨新機、跨機LAN、TLS、頭盔或25位操作驗收；網路可達性與場館部署仍須另驗。啟動器不設定防火牆或系統網路。原Unity0.39.0／code49／NGO29與e0d60e4e...雙平台保持，未因本輪重新執行Editor或建置頭盔。

## 啟動與停止的證據

啟動器先核對manifest與來源檔案，再取得所選實例的exclusive lease。只啟動自己包內的API apphost，顯式指定資料／金鑰路徑並清除繼承的角色金鑰等覆寫。API在原始資料恢復與服務啟動成功後，透過私有stdout輸出本次隨機token的就緒事件；啟動器另核對原child仍存活、實際coreclr來自本包及原Master身分。單純程序啟動、埠號已開或別的服務回應不算就緒。

`ControlPipeToken`只有明確配置時才啟用，沒有新增HTTP停機或領取金鑰端點。短行的`STOP <本次token>`要求正常StopApplication；錯token不停止，EOF、過長／非ASCII輸入或讀取錯誤結束此私有控制管線。就緒輸出IO失敗也要求停止。啟動器的stdin writer關閉後，自己的API會退出；沒有配置的普通API仍沿原生命週期，不因stdin關閉自動退出。IPC不修改命令、入場、命中、姿態或世界資料格式。

正常停止等待原child handle退出，保留真正exit code；超過40秒的最後收尾才嘗試終止自己的child，再等5秒。強制或未知停止不能回報complete成功。圖形介面定期確認自己的child狀態，意外中斷時不持續顯示就緒；尚未確認停止則保留實例lease與視窗。

報告／金鑰寫入先完成同資料夾的exclusive暫存檔、Flush，再以新檔名Move發布，既有目的檔不覆蓋。舊候選使用CreateNew後才序列化，實際測試曾在發布期間讀到未完成JSON；原failed、binary及來源保持。受控反射呼叫實際編譯SaveNew、阻擋一個serializer getter時，舊版最終檔已可見且0 bytes，修正後最終檔不可見，放行後兩版內容相同。這是方法層級的原子發布反例，不當原Windows排程唯一原因證明。

## 建置與驗證

```powershell
python scripts/publish-control-server.py --build-root "$env:LOCALAPPDATA/VrCommand/BuildRuns"
python scripts/package-control-server.py --publication <上述全新輸出目錄> --stage-root "$env:LOCALAPPDATA/VrCommand/Pkg" --output <新的ZIP>
python scripts/check-control-package.py <完整解壓後的VRCommand-ControlServer> --runtime-root "$env:LOCALAPPDATA/VrCommand/ControlChecks"
python scripts/check-control-report.py <完整解壓後的VRCommand-ControlServer>
python scripts/check-control-gui.py <完整解壓後的VRCommand-ControlServer> --runtime-root "$env:LOCALAPPDATA/VrCommand/ControlChecks"
```

publish從明確的來源清單建立全新C槽snapshot，在該snapshot增加RID鎖定群組；原repository的NuGet lock不改，原依賴群組／contentHash必須一致。API及其依賴整組publish，self-contained runtimeconfig與必要native DLL明確核對；編譯、輸入與每份輸出雜湊保存於receipt。package拒絕資料庫、journal、票券／角色金鑰設定、額外publication檔案、連結與越界路徑。manifest是完整性清單，並非數位簽章。

105項Windows封裝檢查包含CLI拒絕、七角色與房控權限、五獨立API名冊共25席、原Preparing場次／admission及任務重開、私有檔案保持、後續Linked／active0、原API正常停止、父程序被終止後的EOF停止及有限診斷不含角色金鑰。25席只是管理名冊，沒有冒充25個遊戲端。GUI工具只準備自己的新實例及觀察程序；實際選檔／啟停／關窗透過native UI操作，review不能取代child退出及HTTP身分證據。先用CLI建立及暖啟動，GUI只重開同一實例，不操作新增金鑰、剪貼簿或瀏覽器登入。

額外6項真正API私有管線案例與7項Python封裝邊界檢查納入[精確1a959c6的成功CI](https://github.com/peca12968/vr-command-center/actions/runs/41332911824)；738規則／459 HTTP／47 world、Python／素材、78 Node／256 Chromium全部通過。Windows Framework／GUI及受控編譯方法反例只在本機執行，不由Linux CI代替。舊樹狀資料夾選擇的GUI場次未完成而failed，後改為可輸入路徑的設定檔選取；原件與cleanup保持。最終場次、CI43＋13檔證據、其他候選及未驗限制見[PROGRESS](PROGRESS.md)。

Notices保留實際NuGet／runtime包的原始metadata與授權；另附[SQLitePCLRaw上游參考授權](https://github.com/ericsink/SQLitePCL.raw/blob/v2.1.12/LICENSE.TXT)、[參考NOTICE](https://github.com/ericsink/SQLitePCL.raw/blob/v2.1.12/NOTICE.TXT)及[Microsoft.Data.Sqlite上游授權](https://github.com/dotnet/efcore/blob/v10.0.14/LICENSE.txt)，原blob byte雜湊已核對。SQLitePCLRaw實際2.1.13的原NuGet metadata保留；參考NOTICE來自明確標示的2.1.12，可能提到本包沒有的元件，不當成實際2.1.13來源版本證明。
