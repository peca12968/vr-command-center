# 玩家任務簡報

遊戲端0.31.0／Android code38／NGO29，API／控制台保持0.28。控制者在原任務庫保存的名稱與內容，現在由GameServer送到玩家遊戲內閱讀，包含晚加入者。不是另外編輯一份玩家文字；場次仍使用開場時選定的不可變任務版本。

PC按 **B** 開啟／下一頁，最後一頁再按會關閉；**Escape**關閉，**L**切換字型授權頁。開啟時也可點面板的下一頁／關閉／授權按鈕。關閉入口是文字提示，避免滑鼠點入口同時射擊。Quest來源綁定左手 **X** 開啟／下一頁、**Y**關閉、左握柄切換授權；已編譯Android，不代表控制器／頭盔已實測。

閱讀只抑制本機射擊及換彈輸入，不暫停全場、不取得無敵狀態，也不更動權威戰鬥規則。開關／翻頁後，已按住的扳機或按鍵必須放開再按才能射擊。頭手仍走原NGO姿態管道；Tracked頭手及槍口偏移都不修改。XR面板是頭部前方0.9m的子Canvas，沒有Collider；舒適度、遮擋與實體安全界線仍需頭盔驗收。End戰績優先，關閉簡報。

## 完整文字及版本邊界

名稱最多100、內容最多10000個UTF-16 code units，與既有任務契約一致。使用UTF-8正規化處理不成對的surrogate，128個UTF-16單位分塊且不切開有效surrogate pair，最多80塊。NGO的FixedString512保存每塊，header版本1包含名稱、完整長度、塊數及SHA256。摘要使用BinaryWriter寫入版本、長度前綴的名稱與內容；部分、錯序、異動或未知版本不能成為可讀簡報。這是完整性檢查，不是認證或防作弊邊界。

全部內容保留並分頁，每行最多20個Unicode code points、每頁10行；CRLF／CR統一換行、Tab轉一空白、NUL顯示替代字元。內容是純文字，`<b>`等原文照樣顯示，不執行富文字或超連結。不保證字型涵蓋任意emoji／罕見字，明確換行與單字可跨頁。PC面板隨視窗縮放並有不透明底板；XR使用同一分頁及隨附字型。頁碼／開關／閱讀按鍵是本地狀態，沒有新增世界錄影欄位，也沒有補造舊回放的閱讀過程。

SceneAuthority新增BriefingHeader及NetworkList，**全部GameServer／PC／Quest須同版NGO29**；Prepare原位升級並保存原Arena／PlayerAvatar ID。API／UI0.28、envelope7、world schema1、驗票2、rules0.8.0與舊素材profile保持，不因此允許降回不支援既有新資料的API reader。

## 隨附繁中字型

使用未修改的Noto Sans CJK TC Regular 2.004，來源是[官方noto-cjk](https://github.com/notofonts/noto-cjk/tree/f8d157532fbfaeda587e826d4cd5b21a49186f7c)，SIL OFL1.1、原授權及來源告示隨Resources一起出貨，也能從面板閱讀。沒有依賴或安裝作業系統字型。

`Resources/VrCommand/Fonts/font-source-v1.json`保存來源commit與字型／OFL／NOTICE三份SHA pin。`python scripts/check-mission-font.py`核對固定pin與真正OTF cmap中的繁中／Latin glyph；Unity測試另實際載入字型。發布後mission-fonts-v1固定，改字型需新profile並保留舊來源，不可重寫pin冒充原版。來源fingerprint同時納入OTF／TXT及其Unity meta，Windows／Quest須一致。

## 原生檢查

```powershell
python scripts/check-desktop-briefing.py --runtime-root "$env:LOCALAPPDATA/VrCommand/SimulationRuns" --api-dll <本次隔離API.dll>
```

此入口只用全新自有API／資料／憑證，F來源與播放器、明確C SSD runtime。一個server、可見主玩家及Running後晚連線玩家；任務有10000字繁中與純文字標籤。每個awaiting階段必須實際操作並觀察原生視窗後，才寫該run的`.done`確認；不得自動注入姿態、射擊RPC或統計來代替輸入。stage檔只是工具提示，不代替程序仍在運行的證據。

檢查全部文字摘要到達三程序、管理更新／晚加入不重設閱讀頁、Space被抑制但tick及身體連續、翻頁／Escape／下一次Space恰好一發、授權頁，以及雙玩家各自結算／精確seal與保存任務不變。NativeReplicationProbe新增簡報有效性／字數／塊數／摘要、頁數與本機被抑制按下次數，不寫全文或憑證；240秒／64capture上限保持，普通啟動不附掛診斷。

最新實際run、receipt、141項EditMode、同源雙平台及失敗紀錄以[PROGRESS](PROGRESS.md)為準。這是兩位同機PC Simulation，不是Quest／VIVE／MR、跨機、25台、人工聲學或長期穩定性驗收。25端最大長文同時入場的頻寬、Android字型記憶體與閱讀舒適度尚未量測。
