# 玩家與敵軍射擊音效

API／UI **0.25.0**、Unity **0.27.0／Android code31／NGO25**。新的世界 header `combatAudioVersion=1` 選用 `combat-audio-v1`；缺欄位保持0，舊資料不補造射擊聲。音效版本獨立於固定的 `player-fire-v1` 幾何，八個既有外觀 profile 及原始 binary header／checksum 均保留。新 header 必須同時具有 playerFireVersion1／enemyFireVersion1，沿用已接受事件及逐 packet 的 fire witness 核對。來源、API、UI及全部遊戲程序一起更新，不能降舊 reader。

本輪只新增呈現。rules0.8.0、envelope6、mission schema1、world schema1、驗票2及environmentVersion1保持。NGO actor 增加與 presentationTick／fire 狀態一起複製的 `presentationRunning`，故 protocol 升至25；Prepare 原位升版，重用保存的 scene／prefab ID。沒有改射速、傷害、命中、彈藥、姿態規則、Tracked 資料或碰撞。

聲音只由新接受的玩家 ShotFired／NPC EnemyShot 觸發，播放位置固定在該發保存的世界槍口，不跟隨之後轉向。沒有本地扳機預測。共用 CombatAudioCursor／JS 對照只在連續 Running 觀察、新 sequence、射擊 age≤3 tick及相鄰觀察差≤10 tick時播放最後一發；首次觀察、加入中途、倒退、長缺口、重新啟用與手動 seek 先建立基線，不補播遺漏的全部子彈。Pause／Ended、來源失效及隱藏頁面停止聲源；恢復後需要新基線與後續新發。

Unity 每個本玩家 AudioListener 有32個獨立空間聲源，同房、25公尺內，線性衰減1–25公尺、doppler0；候選按距離／ID排序，滿載重用最舊聲源。來源離線／死亡前已接受的發射仍可呈現。聲源不加Collider／NetworkObject，隨owner despawn明確Dispose；共享AudioClip由固定Resources引用。瀏覽器使用同一PCM、equalpower Panner、相同距離與32聲源上限，依觀察鏡頭及房間選擇定位；必須點「音效」才建立／啟用Web Audio輸出，換錄製或登出會關閉。沒有遮擋濾波、混響、傳播延時或完整聽覺設計。兩種引擎混音不保證逐sample相同。

`scripts/generate-combat-audio.py` 以自製整數雜訊、濾波、三角波及包絡合成，沒有第三方取樣；mono16-bit／22050Hz、Unity匯入PCM／DecompressOnLoad／預載，EditMode逐sample比對原WAV。固定資源如下，變更需新聲音版本，不可重寫v1 pin：

| 檔案 | 長度 | SHA256 |
|---|---|---|
| rifle-shot-v1.wav | 5292 samples／0.24秒 | d3b366164342346cb99e22e88c18482b927f382782d0368b3f7285e57608a6ae |
| pistol-shot-v1.wav | 3969 samples／0.18秒 | 33723ad9023704124ccdc1d8de1c29fa4341e39fb78627df999eeb28dad453f9 |
| combat-audio-v1.json | 聲源與衰減規範 | 92d1a05a3d6598e61f88e38b9386efd882ac5776f58e27b4f122c98fef043a2f |

建置來源fingerprint新增Audio WAV／其meta及Resources asset／其meta，涵蓋實際PCM匯入設定與library引用。Editor及Python檢查器使用相同檔案圖；兩平台要核對最終receipt，不以SDK診斷代替。

```powershell
python scripts/generate-combat-audio.py --check
python scripts/check-desktop-combat-audio.py --runtime-root C:/Users/USER/AppData/Local/VrCommand/SimulationRuns
```

後者使用自己的API／Room3 server／可見Simulation玩家，stage要求真正Space一次；看見HUD29後才寫該次fire.done，不能注入RPC或姿態。自動控制AI後核對原20點傷害、Pause／Resume靜音、封存及回放統計。來源及binary在F，runtime明確用SSD，writer全停後helper才回存F；既有預覽資料不動。

`--vr-combat-audio-probe <全新絕對目錄>` 僅Windows Development／可見untracked本玩家AudioListener啟用，與weather／HUD／射擊GPU探針互斥。普通遊戲有音效但不安裝診斷；Editor／Android不安裝。最多180秒、16,000,000 float PCM、12000音訊視窗及1024播放紀錄，超限明示truncated／complete=false；格式改變同樣失敗。48kHz stereo時sample容量約166.7秒，可能早於180秒時間上限。finish.request先完成本機診斷，再由server真正End／精確seal；owner先銷毀不算完整收集。

探針只記本遊戲AudioListener的混音與聲源播放序號，沒有麥克風、OS loopback、GPU或輸入注入。WAV／DSP非零及靜音是程式音訊證據，**沒有人工聽感、實體喇叭／耳機、聲壓、Quest／VIVE或25台驗收**。任務回放是依事件重建短音效，不是保存原始音軌；不代表漏包時每發必然可聞。實際數值、失敗與最新雙平台結果見 [PROGRESS.md](PROGRESS.md)。
