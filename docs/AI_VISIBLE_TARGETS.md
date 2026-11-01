# AI 選擇可命中的玩家

Unity **0.38.0／Android code48／NGO29**，API/UI0.30.2。自動攻擊依原距離與GUID順序逐一使用原Cast檢查候選玩家；最近者被掩體／其他敵軍擋住時，仍可攻擊後續真正可命中的玩家。不穿過阻擋、不把命中別人的射線當成此目標命中，也不靠瞄準ID授權傷害。

候選仍限同房、connected、存活與原天氣／日夜射程；原槍口feet+(0,1.4,0)、20活動tick冷卻、20點傷害、Hold／Patrol／Advance與AutoAttack、Pause及姿態0.5／世界1.5秒政策保持。Advance仍朝原最近合格玩家移動，不把可射擊目標拿來改寫尋路。每房最多5候選，只在可嘗試射擊時做射線；沒有命中不消耗射擊冷卻。完全受阻時最多增加為原本5倍候選Cast，本輪不是最壞場景或25人效能驗收。

敵軍內部AimTarget僅讓冷卻期間的外觀持續朝最近一次選中的有效玩家，玩家斷線／移除／失效則不再使用；實際每發仍重新選敵及Cast。更新朝向不改已保存的EnemyFireState歷史射線，不移動Tracked資料。沒有新wire／header／任務欄位或素材profile，world schema1／rules0.8.0與原NGO29保持，歷史回放使用原保存事件／幀，不重新求敵或補造攻擊。

## 真正任務產生器反例

房3六個正常VR地面物件，經原開場preflight接受：直立沙包(-4.6,-.6) yaw90、油桶(-3.8,-.6)、三沙包X=-1.5／.8／3.1且Z=-.625、油桶(4.9,-.625)。實際產生兩NPC feet=(-3,0,-1)與(-3,0,-.25)，原席0／1／2的玩家head=(-3,1.65,-3)、(-1.5,1.65,-3)、(0,1.65,-3)。不用自訂出生位置、玩家輸入、姿態或命中注入。

前NPC擋住後NPC到前兩位玩家的射線，第三位可命中。三位都經原admission Connect及有效Pose才可攻擊：舊0.37.2第1 tick只有前NPC射擊，玩家健康80／100／100；只替換ArenaWorld的凍結副本為80／100／80，後NPC在tick1選第三位。50個Runtime檔中僅ArenaWorld.cs不同、Program逐byte相同，C工程與JSON／真正exit1及exit0都保存；這是共用規則來源對照，不當完整主機因果graph。

初候選未Connect、第二候選未Pose，兩者都沒有可參戰玩家，不能證明選敵問題。後續兩玩家候選的第二條射線仍被NPC身體邊緣擋住，舊／新都不該射擊；原failed及凍結來源保留，不能把它當成「可見較遠玩家」的正例。真正三玩家反例才符合上述前提。

舊Windows三人場`desktop-ai-targeting/20261101-150050-725e00df`真正exit1：後NPC從未開火，原結果／CSV／雙seal與cleanup正常。原兩人錯分類場`20261101-145732-14715650`也保留failed，各自C原件與F snapshot逐檔相符。後續checker另加傷害配對、Pause序號及完整靜止參戰核對，不能稱兩次native使用完全相同helper graph。

## 驗證與執行

9個共用行為案例分別在.NET與真正Unity Editor執行：原產生器、矮身玩家掩體、受阻不耗冷卻、GUID平手、冷卻重選、停火／Pause、射程與房間隔離、Advance不改目標與新瞄準不重寫舊射線。本機**738規則／208真正Editor（0 skip）／459 HTTP／47世界串流／78 Node／255 Chromium**成功；7新Python證據反例與5原snapshot檢查成功。首.NET候選因測試讀取nullable射線未明確檢查而編譯失敗，原C build／log保持，明確pattern確認後採新C build，沒有放寬檢查。

```powershell
python scripts/check-desktop-ai-targeting.py --api-dll <本輪API.dll> --runtime-root <新的SSD runtime根目錄>
```

工具只操作自己的隔離API與Windows server／三個headless client，保持Simulation與0頭盔。Begin需原接受序號、Running、tick>0及非suspended，Pause另保存原命令及來源fence；先正常End／精確雙seal、三份原admission結果／唯一server ACK／CSV，再停止自己的程序、完整SSE回放核對，cleanup成功才complete。原始逐事件序號不能跳／重複；首後NPC射擊必須tick1、第三位、正確槍口／方向與緊接20點傷害，且之前最近玩家僅被前NPC傷20、仍存活。不能用最近者死亡後換敵冒充可見目標選擇。每張已接受Begin的Running／Paused保存幀核對原靜止玩家／Simulated及兩個原Hold NPC，缺失tick不插值。

新artifact family為desktop-ai-targeting及自己的latest pointer。五helper SHA只核對所列來源前後一致，不當完整runtime／OS graph；writer全停才一次snapshot，不打開保存SQLite。

最終新Windows三人場`20261101-182258-207e5e24`真正exit0／4項、32完整回放／12張已接受Begin的Running／Paused保存幀；tick1只有前NPC→席0、後NPC→席2的兩個EnemyShot及各20點傷害，三份原結果為健康80／100／80、各中彈1／0／1。三份admission結果／CSV／雙seal／三個唯一ACK及cleanup成功，收到時最大來源年齡0.150225秒不是RTT。一般五房`20261101-182316-77cc9ff6`真正exit0／6項／7場，獨立／重用／錯票／後續Linked及精確seal成功；每房1位，非25位操作。

208真正Editor及同源Windows／ARM64 Quest fingerprint `0f8287b002f46d0824bf4f3c27a450b672cc7554fdc156a4c238affdcd8f32b0`、原scene／prefab ID相同。舊321 binary／log與6選定來源先封存，不是完整來源graph。Windows包`windows-player-0.38.0.zip` **82,646,224 bytes／SHA `1f4a27d8ca7b310acfd24a4a018b44449fb73b1c2ac02107ea1af2251ed35d7c`**、311 runtime檔／原launcher，新C展開19項核對成功，非完整GUI／跨機。APK **60,330,662 bytes／SHA `7e175d4a4eb566758e454457d17a7adbfac5c615bae184525c2b6ad6ab3d517e`**、0.38.0／48／ARM64／min32 target35、v2簽章成功，未安裝頭盔；兩平台建置結束才執行新原生場。

APK原82,782,417降至60,330,662 bytes，ZIP索引105項compressed僅60,306,850→60,309,211；非索引payload區段22,475,567→21,451。這是容器記帳，不當遊戲內容縮減、ELF／執行效能或唯一Gradle原因證明，兩份raw保持、不重封裝，receipt totalBytes不是APK大小。

功能17b75e9的首CI41297698388在較早的統計列斷言失敗，4檔／log／ZIP保持；尚未完成該次完整browser。受控through13較早GET在四報告已接受到16後仍能顯示「模擬資料」，證明原標籤等待不足，但不是原CI時間根因證明。fixture改為等待來源與完整列、仍同一30秒與原精確值；產品、遊戲來源及binary不改，新本機78 Node／256 browser成功。原controlled舊等待exit1與新完整結果分開保留，完整CI來源與證據以[PROGRESS](PROGRESS.md)為準。

[精確8dbb874的CI41298762465](https://github.com/peca12968/vr-command-center/actions/runs/41298762465)完整success：738規則／459 HTTP／47 world、工作流程Python／素材、78 Node／256 Chromium。42檔artifact13080935513與log／10,040,719 bytes ZIP／SHA20f05858...已下載核對，前796 browser＋新42＝838，原68 runtime／snapshot／0.38包與327 archive保持。2 Windows限定skip不是Unity／native或頭盔證據，首CI與受控舊fence仍failed，後續文件skip ci不改測試來源。

沒有新GPU／PCM、實機／跨機或25位操作證據，原31筆／world371姿態失效與F吞吐等問題未由本輪修復，完整11項仍active。
