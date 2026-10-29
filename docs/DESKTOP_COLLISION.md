# 電腦端掩體移動 v0.18

2026-10-30 v0.20／NGO19新[軍事掩體](FIELD_PROPS.md)已用真正鍵盤重驗四階段，5555幀／來源年齡最高0.60369秒，原位置、健康／彈藥及封存回放一致。模型只改善外觀，桶體角落及沙包縫隙仍採同一包圍盒；下列舊數值與操作流程保留，最新完整證據見PROGRESS。

WASD 現在會在沙包／油桶及房間邊界前停止，能退回及側移。原生 Windows 視窗已用真正鍵盤驗證，來源維持 **Simulation**；沒有頭盔／MR／25 人驗收。一般練習見 [DESKTOP.md](DESKTOP.md)，控制台自訂擺設見 [DESKTOP_CONTROL.md](DESKTOP_CONTROL.md)。

## 共用規則

`ArenaWalkSurface` 是權威姿態檢查、AI 導航及桌面預測的共用平面通行規則，從原 `GridNavigation` 抽出。玩家半徑 0.3m，房間 12m × 12m；沙包與油桶使用同一份旋轉矩形擴張足跡。線段仍按原規則每最多 0.05m 取樣，並非解析物理掃掠。預測以 12 次二分裁切移動，另比較單軸候選；所有候選都從原位置檢查，避免側移繞角後送出伺服器會拒絕的直線。

Unity 只用伺服器複製的同房幾何快取，未準備好時不移動。實際姿態仍須通過伺服器的場地、掩體、距離及時間檢查；若桌面合成姿態被拒絕，退回最後接受的位置。Tracked XR 不套用這項相機位移修正。標準 `primitives-v1` 尺寸以外的幾何仍須另行設計，不支援台階、跳躍、攀爬、動態推物或物理場地校正。

## 版本與建置

`CombatPropState` 增加房間欄位，**NGO protocol 18／bundle 0.18.0／Android code 18**。所有 Unity server／client 須一起更新，不能混跑 17。API 0.16、驗票 protocol 2、envelope 6、world schema 1、rules 0.8.0 保持。Prepare 原位升級保存場景，重用 Arena／PlayerAvatar file ID；本輪沒有 RebuildArena。

Windows 與 Quest 成功 receipt 的來源 fingerprint 相同：`db5433bed1791b8e0b9be4587a657a005cb7471aa1f35a16d6fda0121c95eea1`。34 項真正 Unity EditMode 通過；.NET 485 核心、369 HTTP、43 世界串流通過。較窄 managed SDK 診斷另通過 11 runtime／9 test 的 Android／Windows 型別編譯，不能取代上述真正 Editor 或原生運行結果。

## 可重現的原生操作檢查

先依 QUEST3 建置 Desktop／API；不要與 IL2CPP 編譯同時量測新鮮度。下例明確用 SSD 保存新測試資料，程式碼、binary 與證據仍在 F。工具僅管理自己的 API、房間 3、server／可見 client 與臨時憑證，結束並關閉 writer 後將 runtime snapshot 複製回 F，保留原件。

```powershell
python scripts/check-desktop-collision.py --runtime-root C:/Users/USER/AppData/Local/VrCommand/SimulationRuns
# 需要時另加 --api-dll <同次隔離建置的 API DLL>
```

在真正玩家視窗完成工具印出的每階段操作，然後在該證據目錄新增對應的空白檔。標記只確認操作完成，實際結果由已接受的 native 世界幀判定，不注入姿態。

| 階段／完成檔 | 輸入 | 原生驗證位置 |
|---|---|---|
| sandbag.done | W 短按 17 次 | z 約 -2.6500003，停在沙包前 |
| retreat.done | S 短按 5 次 | z 約 -2.9000001，能退出掩體邊界 |
| sidestep.done | D 短按 10 次 | x 約 -2.5000005，繞過沙包端點 |
| barrel.done | W 短按 20 次 | z 約 -2.219239，停在 45° 油桶足跡前 |

2026-10-29 實際場 `20261029-221556-be8bb604` 四階段均保持 connected=true、Simulated 頭手、健康 100、彈匣 30／備彈 90；沙包與油桶截圖、逐階段 JSON、完整世界／統計封存及 cleanup 在 `artifacts/desktop-venue/<場次>/`。舊 v0.17 反例 `20261029-214952-e8fee276` 同樣推牆會顯示 POSE REJECTED、connected=false；它只證明原問題曾重現，不能算成功結果。最新回歸、二進位與剩餘限制見 [PROGRESS.md](PROGRESS.md)。
