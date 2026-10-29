# 軍事掩體素材 field-props-v1

Unity v0.20／NGO19與API／觀戰端v0.17加入自製低多邊形掩體：三層交錯沙包、十二邊油桶、桶箍、封蓋與警示色。玩家、敵軍及武器仍使用原先幾何；這是場景素材進度，不代表整套正式軍事美術或頭盔驗收。

`scripts/generate-field-props.py`以固定數值產生原創網格，沒有外部模型、紋理、字型、下載或隨機輸入。Unity Resources的JSON與瀏覽器本地ES module包含相同位置、法線、三角索引及頂點顏色，provenance保存資料SHA-256與面數。所有相依均在庫內／既有Unity套件，不新增CDN。

```powershell
python scripts/generate-field-props.py --check
# 缺少生成檔時可執行不帶 --check 的版本，重建相同的 v1 檔案
```

| 模型 | 尺寸（公尺） | 三角形 |
|---|---|---|
| 沙包牆 | 2 × 0.9 × 0.7 | 256 |
| 油桶 | 0.7 × 1.2 × 0.7 | 386 |

原點為腳底、Y向上、世界軸及yaw與原錄製一致。Unity每個CombatAuthority重用兩個Mesh及一個材質，瀏覽器每次場景載入同樣重用網格／材質；舊場景清除時每個共用資源只釋放一次。Unity採自製URP頂點色光照／霧shader，引用既有URP的ShadowCaster及DepthOnly；瀏覽器採Three.js頂點色標準材質。光照模型不同，不宣稱像素相同。GPU instancing選項不等於已量測批次或效能；2500物件／25台仍待實測。

v1幾何及配色發布後固定，生成器以資料SHA-256 pin拒絕同ID下的改動。新模型或配色必須另立assetSet，保留v1資料與reader，更新全部接入及驗證；不能更新pin來靜默改寫既有錄製外觀。光照、GPU與引擎仍可能造成像素差異，這不是影像逐幀錄影。

## 外觀與權威幾何

尺寸沿用rules0.8.0的WorldProp：沙包half=(1,.45,.35)，油桶half=(.35,.6,.35)。頂點最大僅有縫線／蓋面0.00001m的深度避讓。Mesh不新增Unity物理Collider，射擊、碰撞、導航、準星與HUD遮擋仍使用既有旋轉包圍盒。

桶體是圓形輪廓，但權威掩體是方盒；因此桶邊四角及袋體倒角／縫線空隙仍可能擋住射線或行走。這是明確的粗略幾何規則，非逐像素命中或圓柱碰撞。觀戰介面顯示「命中／碰撞採包圍盒」；不能因新外觀而推算不同傷害或把裝飾Mesh當物理來源。之後若改真實碰撞形狀，必須另升rules、事件／世界契約與所有接入，不能只換shader或偷偷改舊回放。

## 錄製與部署版本

WorldRecordingHeader的schema仍1，assetSet有兩個明確允許值：

- `primitives-v1`：舊方盒／邊線外觀，既有生產者的Create預設及舊匯出缺少欄位時維持此版本。
- `field-props-v1`：新Unity來源明確指定的新沙包／油桶。新版API驗證其已知版本後，以同版本核對canonical任務幾何；來源重試不可變更已接受的header。

未知版本拒絕，不能退回方盒假裝相容。舊binary journal的原始header／checksum不改寫，worlds.db結構未改；這不表示寫入新素材版本後能降回舊reader／UI。先備份正式兩處資料及SQLite WAL，再部署新版API／UI與全部NGO19遊戲端；不要將新UI、來源或票券工具接到舊API。原5080預覽目前沿用原v0.16 DLL／資料，本輪新場使用自己的v0.17 API及全新SSD runtime，沒有替換正式歷史。

Unity的Prepare重用既有Arena／PlayerAvatar file ID，僅升NGO protocol19，避免舊遊戲端用不同素材解讀同場；不執行RebuildArena。bundle0.20.0／Android code22，票券protocol2、envelope6、world schema1、environmentVersion1及rules0.8.0保持。來源fingerprint除原C#／asmdef／packages，新增Resources JSON及shader，不能以舊receipt驗收新素材。

## 驗證操作

實際執行結果以[PROGRESS](PROGRESS.md)為準。Unity EditMode涵蓋Mesh有限值／外向法線、原碰撞尺寸、400面預算、資源重用及無Collider；Node核對Unity／瀏覽器資料相同與舊／未知profile。核心檢查另驗證新舊header、不可變重試及未知版本拒絕。

先依QUEST3完成Prepare、Tests、Desktop及Quest；後端依開發指引還原／建置／規則／HTTP／world檢查。`tests/browser/check.cjs`驗證舊串流保留方盒；`check-operator-native.cjs`以自己的控制台、真正PC世界驗證新assetSet與642個prop三角形，並在封存、鏡頭讀回與末幀跳轉後核對。瀏覽器是軟體WebGL，不能替代真正GPU或頭盔。

`check-desktop-collision.py`的真正鍵盤推牆／後退／側移／45°油桶回歸，用來核對新外觀沒有改變權威行走規則。`check-desktop-weather.py`則回歸新shader在日夜、霧、閃電、雨雷及暫停下的表現。所有native量測應在Unity／IL2CPP建置結束後執行；使用明確SSD runtime，writer結束後複製回F保留原件。一般啟動不開診斷錄音或GPU讀回。
