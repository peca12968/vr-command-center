# 主控台任務收尾

控制台 **0.31.1** 在場次控制按鈕下新增「任務收尾」，分別顯示戰鬥統計與世界回放的封存狀態。沿用API **0.31.0** 的場次、統計及world唯讀端點，沒有新增API契約或要求更新遊戲端。Unity **0.39.0／code49／NGO29**、原224真正Editor及同源Windows／ARM64 APK保持。

## 操作與狀態

Preparing時提示先啟動本場遊戲伺服器、加入玩家、交付各自的連線檔，再開始任務。Running／Paused時只提示結束後確認資料，不把目前的姿態、來源或程序狀態當成封存完成。

End後，戰鬥統計需要同場次、精確目前管理序號、明確pendingTelemetry=false及原combatStream.sealed=true。世界回放需要服務回傳complete=true、正數acceptedSequence，以及同session／stream／origin／房間與任務時鐘能力；舊clock0仍可讀。這裡信任既有world seal契約：API已核對最後Ended幀、原combat尾界與最終統計。前端沒有重新驗證全回放，也不讀local journal或SQLite。

| 畫面 | 意義 |
| --- | --- |
| 戰鬥已封存、世界等待封存 | CSV可依原規則匯出，世界回放仍待確認 |
| 雙封存 | 本場資料已由服務確認封存；不確認玩家戰績送達或伺服器可關閉 |
| 尚無世界錄製紀錄 | GET world為404，不能把沒有資料視為成功 |
| 暫時無法確認／來源尚未對上 | 傳輸、權限、格式或來源不符，清除舊完成提示並等待更新 |
| 沒有遊戲來源 | 只有管理場次與統計，沒有可確認的遊戲錄製 |

本頁不控制玩家戰績傳送或遊戲程序。雙封存後仍須等待原伺服器完成戰績傳送與收尾；[Windows伺服器包](WINDOWS_SERVER_PACKAGE.md)保留36秒並自行收掉原程序，這也不能單憑時間當作所有玩家收到。原CSV匯出、Begin／End權限、名冊與票券規則不變，沒有新增Begin gate或依世界封存擋CSV。

## 讀取與隔離

只在房間與場次頁可見、目前登入且選中Ended／有來源場次時，每兩秒最多一次GET world，單次五秒逾時。依epoch／key／actor／場次／序號／stream與generation隔離回應；選取、登出、切頁、隱藏頁面或未確認命令會清除舊狀態，背景更新失敗也使封存未確認。新的成功場次刷新才可解除該失敗狀態。401走原登出流程；403／5xx／斷線不沿用舊綠色。沒有增加寫入、重試End或變更0.5／1.5秒參戰政策。

已確認的End會保留目前場次並勾選「包含已結束紀錄」。原先只對尚未combat seal的回條如此處理，若End回應遺失、手動重試時已seal，畫面會把Ended場次篩掉。現在只要同一End回條確認Ended便保留，包含已封存的duplicate；命令UUID／expectedSequence與原手動重試流程保持。

受控舊候選回歸先真實接受一次End、由原GameServer角色封存0筆combat，再丟失回應；重試沿原UUID／expectedSequence取得真正duplicate／sealed回條，舊畫面selected空值、includeEnded=false、panelHidden=true，原30秒等待exit1。修正後完整瀏覽器檢查可保留同一場次。這是明確的篩選邏輯反例，不是原生觀察器逾時或舊Windows startup根因證明；before API整組、WWW來源及失敗圖／狀態保留。

## 驗證範圍

5個Node反例涵蓋雙seal、統計序號、異源／房間／時鐘／schema、0幀／錯型別／讀取失敗及legacy clock。瀏覽器檢查使用真正隔離API，world完成功能的多種狀態部分為明確route fixture；另有真正lost-End／sealed-duplicate流程，沒有放寬原API／DOM期限或重送新UUID。

真正原生觀察器從主控台登入自己的測試憑證、選中原Running場次，再以正式End按鈕送一筆非duplicate的200 POST，核對回條與精確原native world尾界；沒有替換world回應、注入UI state或用API接受冒充畫面確認。瀏覽器程序有真實close／exit與有限失敗診斷，私有fixture憑證只存測試runtime，不隨包／CI交付。角色與管理啟動器的Windows GUI、遊戲伺服器GUI是不同驗證範圍，不能互相替代。

第一個原生觀察場只有Running ready後等待closure而逾時；當時從另一API通路End且未勾含Ended，與篩選行為不一致，但沒有保存末刻DOM，不能證明唯一根因。後改為真正UI End並新增最多800字收尾狀態／500字notice及五秒失敗圖，原60秒觀察期限保持。初failed與所有已封存資料／cleanup保持，不改判成成功。

可執行包、精確輪次／來源／雜湊與CI見[PROGRESS](PROGRESS.md)。這是同機PC／Simulation與控制台資料收尾，不是25位操作、LAN、GPU效能、頭盔／MR／硬體驗收；完整11項目標仍active。
