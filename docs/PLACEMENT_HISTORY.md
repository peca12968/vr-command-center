# 場景物件復原與重做

控制台 **0.31.2** 的任務編輯器新增「復原物件／重做物件」。操作員可以還原沙包或油桶的新增、刪除、移動、旋轉及素材／座標修改；還原保留原陣列順序、完整數值與選取物件。文字、任務名稱、環境、AI設定及管理命令不進入物件紀錄。

一次滑鼠拖曳直到放開、取消或失焦為一步；方向鍵的連續keydown直到keyup或失焦為一步。聚焦配置圖時可用 Ctrl／⌘+Z 復原，Ctrl／⌘+Y 或 Ctrl／⌘+Shift+Z 重做；文字輸入欄位保留瀏覽器自己的文字復原，不攔截全頁快捷鍵。數值欄位完成一次有效change為一步，未變值或無效空欄不清掉重做。復原後新增另一個編輯會清掉原重做分支。

控制台 0.31.70 的成列複製在套用時只增加一步。復原會移除整批複本並重新選取原物件，重做會重新加入整批並選取最後一份。半透明預覽留在當前畫面，套用前不進入草稿或物件紀錄。 [成列操作](LAYOUT.md#複製物件成列)

紀錄僅在本頁記憶體，最多50個完整編輯，雙向序列化快照合計最多2MiB UTF-8；大型配置可能保留較少步。滿載從最舊的完整步驟淘汰，不裁掉物件。一個步驟若超出總預算則清除紀錄；目前最多500物件的正常任務也有完整還原檢查。回傳快照與保留資料分離，不保留呼叫者可變參考；目前物件若與預期分支不符，停止套用並清除紀錄。

新增草稿、成功載入最新／歷史任務、登出或頁面重載都清掉紀錄，不能復原到另一份任務。儲存或其他有待確認操作期間，按鈕與配置圖快捷鍵都受既有Master／busy／pending條件限制。儲存前關閉未完成的手勢，沿用原任務版本與request key流程；儲存成功不清除同一草稿的物件紀錄。此後復原只標示本地草稿未儲存，須明確另存或保存下一版，不回滾已保存版本，也不修改既有場次。

配置檢查仍使用原先的草稿內容fence，復原及重做後重新計算，不能以修改草稿放行另一個已保存版本。API仍 **0.31.0**，Unity仍 **0.39.0／code49／NGO29**；本輪不改API、規則、wire、Tracked姿態或Unity來源。原224真正Editor、e0d60e4e...同源雙平台及原Scene／prefab識別保留，沒有新Editor／Unity／APK重建。

本機專項 `console-placement-focused-2` 已通過 **29項**真實Chromium操作與API讀回，另有 **6項**Node模型檢查，包含500物件及記憶體／分支邊界。第一次專項在保存新版後仍選原舊ID而30秒逾時，原4張圖與失敗紀錄保持；改為選擇API真正回傳的headId，不延長期限。最初隔離建置漏複製Checks專案明確連結的AiTargetingCases.cs，CS2001與初snapshot保存；完整snapshot另建新目錄，不當產品編譯根因或修復。

完整本機回歸 **89 Node／296 Chromium**、Windows738／459／47、真正解壓包專項29及Windows管理CLI105通過。主包`control-server-api0.31.0-ui0.31.2-placement-win-x64.zip`為52,472,096 bytes，SHA256 `1eac2676113b47c58b5649ce444201e612603167a16d1e5bccb0599fc1dcf9a2`，含自有.NET／ASP.NET Core10.0.14，504 manifest／484 runtime。沿用原Windows管理啟動器來源，沒有新WinForms GUI操作驗收或新native遊戲場次。

[功能fddc59c](https://github.com/peca12968/vr-command-center/commit/fddc59c4f2e2571265fb19a0c81e3622c1b93eb9)的[CI41346124781](https://github.com/peca12968/vr-command-center/actions/runs/41346124781)／job124966206406完整 **success**：Linux738規則／459 HTTP／47 world、6 pipe、全部Python／素材及89 Node／296 Chromium通過。2 Windows限定skip不是Framework、WinForms、Unity、native遊戲或頭盔驗收。console49檔 artifact13099980133／ZIP **12,015,192 bytes／SHA256 d6012c7a79fccd1e2ed44ed13640f669f7708134ae6ca533eaae1328167dc13a**，control13檔 artifact13099004432／ZIP **3,920 bytes／SHA256 b1cde4b7e8ccd8ac06b2ed58c73213e5e300e5f91ca54764907c79d0dfd2db58**，已下載核對GitHub digest、逐檔hash及完整decoded log（SHA256 ffba6bdd60c1066877c19fbb92bd75f041dda4bebc2f22e55ea59f315b4aee8e）。`placement-ci-validation.json`明列1366＋49＝**1415 browser證據**，另13 metadata，nativeUI7保持；前CI60檔及ZIP另核對保持。C27／F及四舊runtime報告、9管理／5server ZIP、原Unity0.39／e0d／224／玩家ZIP APK不變。後續只有文件提交skip ci，測試來源精確fddc59c；完整11active。

交付與原件雜湊見[PROGRESS](PROGRESS.md)，既有部署見[WINDOWS_CONTROL_PACKAGE](WINDOWS_CONTROL_PACKAGE.md)。此功能是原第7／8項的任務編輯能力進展，完整11項仍active；沒有以瀏覽器編輯證據取代頭盔、MR校正、硬體、跨機或25人驗收。Windows遊戲伺服器GUI先前的PickerHost阻擋及原31／world371／Windows startup／F吞吐仍各自待解。
