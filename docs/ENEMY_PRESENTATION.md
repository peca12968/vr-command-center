# 人形敵軍與保存姿態

`combatants-v1` 在既有沙包／油桶與玩家步槍上增加原創低多邊形敵軍：頭盔、護目鏡、背心／彈袋、臂帶、手套、褲子、護膝及靴子。每名404三角形，三個Mesh（軀幹180、頭104、腿60重用兩次）。`scripts/generate-combatants.py` 產出相同Unity Resources JSON與瀏覽器module；無外部模型、貼圖或下載。SHA-256固定為 `39fa5e9baceec0eb71ce6a4664fc4460e7b0f212f2c58b75c7b4d75b3565fdf2`，`--check` 核對資料及provenance；改模型必須新增profile，不能覆寫pin或改舊回放。

API／UI **0.20.0**、Unity **0.22.0／Android code25／NGO21**。管理envelope6、任務schema1、world schema1、票券2、environmentVersion1與rules0.8.0保持。NGO的敵軍actor row新增facing、walking與presentationTick，一列保存同次姿態，不以另一個時鐘推測步態。Prepare只原位升protocol並重用Arena／PlayerAvatar ID；全體遊戲server／client與API／UI一起更新。新profile／欄位寫入後不能降舊reader，DB schema不變不是降版許可。

## 資料與重建

- 新來源明確指定header `enemyPresentationVersion=1`，每個敵軍保存 `hasPresentation=true`、單位向量 `forward`、布林 `walking`。combatants-v1缺版本或未知版本拒絕。Create／Capture的預設仍為0，不把既有來源自動升成人形。
- 缺欄位舊header維持0；primitives-v1、field-props-v1、service-rifle-v1保留原NPC／武器外觀。版本0不補造朝向或動畫；舊schema2模擬匯出的額外世界欄位不觸發新外觀。解析舊packet時只正規化缺少的零向量，binary原header、payload及checksum不改寫。
- `ArenaWorld` 只在真正成功移動後設walking／方向；Hold或被阻擋的當次tick為standing。autoAttack且有有效目標時，朝向使用原NPC射擊原點到目標的向量；不改目標選擇、路徑、攻擊間隔或命中射線。
- `EnemyPresentation.Pose` 與JS同規則：yaw依forward，頭部pitch視覺夾在±45°，完整forward仍保存；左右腿使用 `sin((tick%12)*π/6)*18°` 與相反值。tick範圍0至1728000。Preparing／死亡不得walking，Paused／Ended可保留最後walking模式與tick，直接seek與暫停都還原同一姿勢。

Unity的Mesh／材質由場景池共享，瀏覽器共享geometry、各NPC獨立淡出材質；移除一個NPC不能釋放其他NPC使用的網格。玩家端隱藏死亡NPC，觀戰／回放沿用淡出顯示死亡位置的政策；幾何與保存姿態一致，不宣稱每個視窗逐pixel相同。Unity位置仍有插值，腿部沒有本地時間動畫。

## 命中與目前限制

模型不加Collider或NetworkObject。命中仍為原軸對齊方盒，中心feet+(0,.9,0)、half=(.3,.9,.3)；原NPC射擊原點仍feet+(0,1.4,0)。轉向、靴子擺動、頭盔或四肢輪廓不改命中盒。這不是逐pixel命中、完整骨架、腳底IK、避碰人群、武器握持或死亡動畫。

NPC目前沒有武器模型／換彈動畫，既有AI射擊仍顯示保存射線；不能為了接玩家步槍而移動權威NPC槍口或假稱已完成握持。玩家身體與頭手仍為原型，頭盔與Tracked XR沒有實測。多人NPC可能沿既有規則走到同一停止點，尚未加入人群避讓；完整策略、複雜地形與25台效能仍待。

## 驗證方式

核心檢查包含初始／成功移動／原射擊方向與傷害、暫停姿勢、版本拒絕、SQLite保存重開與原binary位元組保留。真正EditMode新增5項，涵蓋匯入網格／外向法線、三Mesh重用／無Collider、實際Transform、原子NGO序列化及JsonUtility舊資料。瀏覽器以編譯後C#向量核對JS，真正SwiftShader WebGL比新舊面數、非零步態與seek還原、資源切換及統計。

PC流程使用 `start-desktop-control.py` 與 `check-operator-native.cjs --manual-inspection`：保存配置、動態名冊、Begin、StormNight、AI Advance／傷害，另以真正控制台Patrol／Resume／Pause取得非零步態。不能假定Advance會持續行走，它會在原兩公尺門檻停止。四個人工GPU檢視階段分別為native-day、native-storm、native-paused、native-opponents；`.done` 只在實際檢視後建立。最後比較保存frame與真正觀戰物件的yaw／pitch／腿角，而非只檢查同名資料標記。

最新建置／原生場、測試數量、失敗紀錄及限制以 [PROGRESS](PROGRESS.md) 為準；合成姿態、新鮮度與軟體WebGL不能當頭盔／RTT／GPU效能驗收。
