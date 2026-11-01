# 長場原生自動化輸入

Unity **0.41.0／Android code51／NGO29** 新增獨立旗標 `--vr-desktop-endurance <新的本機絕對目錄>`。只接受Windows Development batch Client、無XR；與原 `--vr-desktop-exercise` 互斥。普通啟動沒有生成器；原短模式的1200活動tick／240秒上限保持。這是AutomatedSimulation，沒有真人鍵盤、頭盔、LAN或容量驗收。

```powershell
python scripts/check-desktop-exercise.py --api-dll <同次API0.31完整建置DLL> --runtime-root <SSD runtime根目錄> --mode both --players-per-room 5 --seconds 900 --endurance
```

先Linked25端，再五個Independent房間各5端。每種模式實際執行900單調秒，完整回放仍使用原4倍速度，會另花時間；60秒選項僅供預測試。短模式仍只接受12..40秒，長場只接受60或900秒，不能與operator-controls合用。兩種原生輸入旗標不能同時出現。

## 排程與界線

每位原owner從自己的首個有效tick開始，透過原DesktopPreviewControls.Move／Constrain與SubmitPose／SubmitWeapon RPC，以0.4m/s每40tick前後反向。每400tick（20秒）在相對20／60／120tick提供fire／reload／fire，仍等原武器分支真正提交才記次數；原簡報、Ready、Running、冷卻、ownership／姿態／伺服器驗票及彈藥都保持。45週期最多90發／45次換彈，使用原30發彈匣＋90備彈，不生成彈藥。

如果上個週期沒有完成，或跳過整個週期，就以ScheduleIncomplete失敗並停止生成輸入；不補送漏掉的射擊。不倒退時鐘、不重設owner，不放寬0.5秒姿態／1.5秒來源或佇列／封存政策。活動tick滿19000（950秒）停止，收集最多1200單調秒；900秒後不再產生新武器意圖，只保留短暫移動收尾窗口。這些是新長場儀表的上限，不是已驗收950／1200秒遊戲。

report仍為version1／AutomatedSimulation，新增profile=Endurance／maximumActiveTicks=19000／maximumCollectionSeconds=1200；正常短模式profile=Short。明確finish後停止所有生成輸入，但原姿態／戰績流程保留；complete只表示儀表明確收尾。Tracked裝置／焦點等原路徑不搬動，追蹤裝置與owner改變仍失敗。

## 驗證範圍

真正Editor **238／0skip**（原231＋7）通過：排程完整45週期／90發／45換彈、相同tick不重送、漏週期不追補、inactive與倒退時鐘、各自界線。Python **14 exercise（新3）／27 active／5 artifact**通過，另實際CLI拒絕三種錯誤模式組合，皆在配置任何場次前退出。

原生五端60秒預測試 `20261102-063727-2069ec28` **5項／597完整回放／577 Running幀**成功；每人6發／3換彈，實際活動tick跨度1202..1203，每個20秒週期都有接受的移動、換彈與精確累計彈數。原短模式＋管理命令五端 `063930-4ee0c139` **7項**成功。900秒原生 `064034-7c1ae2b7` 目前正在依序執行Linked與Independent；未完成前不得當作通過。

完整回放逐幀核對原名冊／connected／Simulated／健康／房間／站姿有界移動與來源capture gap；每位以自己的首個tick分20秒區間，每個區間需要移動>0.1m、walking來源幀、reload來源幀與精確累計兩發。缺一週期或之後恢復不能抹去失效。原0.1m範圍是本測試移動證據，不更動遊戲幾何或命中規則。長場至少需要要求時間減5秒的實際活動tick跨度，以辨識未真正跑滿的報告；明確列出最後實測值，不把900秒caller窗口當精確900秒來源時間。

每個原admission結果／CSV／雙seal／combat與world尾界／原server connection ACK另驗。長場模式在所有房間先各自收尾並停止原生程序，再逐房回放，避免其他房因等待前一房225秒回放而額外錄製大量靜止時間。失敗仍End／保存反例／cleanup，只有所有原writer停後才C→F snapshot，保存SQLite不開、正式5080不動。

## 建置與交付

Windows／Quest同源fingerprint **5d2ebd2a4bedd832c903144e508b44f8660c65e357c4dca6a0abde2cb7230a0c**，原Scene／prefab ID保持。兩端建置都結束才執行上述原生測試。原0.40 binary／log321及6來源共327檔先C／F archive，原APK與ZIP保留；當前APK是新0.41，不能混稱原檔未變。

- 玩家ZIP **82,651,687 bytes／SHA256 f2c84949ba9007b0dbe88c3460bb4f9cb84898de96d7c97938aca887a672ce93**，311 manifest／ZIP312，原啟動器source a65846da...保持；19離線檢查成功。
- Server ZIP **82,673,487 bytes／SHA256 af8a08b3f9f92392f8577d52e01de835abc06f762df1801e86d8dd7a800bddc8**，311 manifest／ZIP312、啟動器1.1.0／source fb57807d...保持。首封裝指令缺stage-root而在建立前被拒絕，紀錄保存，補新目錄後成功。
- APK **60,356,910 bytes／SHA256 1187dfd2f0e18c9f092b03d5de94bb6bfd5f17fe8bea00adfa0af2a8a9d5edce**，aapt確認ARM64／min32／target35／0.41.0／code51，v2 debug簽章成功；未裝頭盔。

API0.31／console0.31.2／rules0.8.0保持，沒有更新後端產品或錄影／Tracked wire。完整11項仍active，舊31筆／world371／startup／F吞吐／PickerHost GUI、跨機／25位真人、頭盔／MR及廠商硬體仍待；新短場或後續乾淨長場都不能當作原根因修復。最新執行與CI結果見[PROGRESS](PROGRESS.md)。
