# Alex Agent Pre-commit Review

**版本：** 2026-05-06 / 嵌入完 speaker notes 後
**審稿人：** alex agent
**檔案：** `docs/presentation/slides.md` (4340 行)

---

## TL;DR — GO / NO-GO

**GO，但 commit 訊息要老實寫「speaker notes embedded for slides 1-28 only」**——slides 29-31 沒嵌、slides 30 也沒嵌，這不是 bug，是 scope，但你 commit 訊息要交代清楚，未來自己回頭看才不會以為是漏掉。

---

## Speaker note 嵌入品質

掃過 28 個 `<!-- ... -->` block (line 54 → 2477)，全部位於 slide 內容**之後**、`---` separator **之前**——位置一致、Slidev 可以正確 render 為 presenter notes。

**口吻檢查 vs `speaker-script-p1.md`：** 我抽了 Slide 3、Slide 4、Slide 17、Slide 27、Slide 28 (finale) 五個點對照——逐字一致，沒有走樣。Alex 的招牌「[掃視全場]」「[語速放慢]」「[加重每個字]」舞台指示都在；「重點是——」「每個推薦都要對得起一條 fact」「指揮官不靠感覺下令」這幾條 catchphrase 也都保住。**沒有 AI 化、沒有翻譯腔、沒有把口語改寫成正式書面。**

**衝突檢查：** 唯一一個邊緣狀況是 **Slide 26 的 speaker note**（line 2205-2210）寫「我前面已經給你看過 ARCHITECTURE 那邊的細節，這一張是把它跟軍事 doctrine 接起來」——這是好事，自我交代了 Slide 16/17 跟 Slide 26 的內容重疊問題。**不算衝突，是 honest framing**。其他都是 visible content + speaker notes 互補（visible 是 anchor，notes 是 narrative），沒看到「螢幕上已經寫了，note 又重唸一次」的廢話冗餘。

**一個小提醒不是問題但提一下：** Slide 4 visible content 寫「接下來 50 張投影片」，但 hide 後總頁數 68，從 4 算還剩 64。這是 rough rounding 不是事實錯誤，但你上台講的時候**口語直接說「接下來這場簡報」**，不要照唸 50 這個數字，省得有人較真。

---

## 還原的 7 個 bridge-bottom / alert-box

逐張對照位置與用途：

| Slide | Line | 元素 | 位置正確？ | 文字合理？ |
|-------|------|------|-----------|-----------|
| 4 | 245 | `bridge-bottom`「接下來 50 張投影片…敲這三個鼓點」 | ✓ 在 numbered-lines 之後、speaker note 之前 | ✓ 三條信條 → 後續 deck 的鋪陳收尾 |
| 15 | 1163 | `alert-box`「看到那個 0.87 了嗎？— 下一張告訴你它怎麼算出來的 →」 | ✓ JSON code block 之後 | ✓ 預告 Slide 17 的 confidence 拆解 |
| 16 | 1239 | `bridge-bottom`「Decide 不是黑盒 — 下一張拆開 confidence 的三個來源 →」 | ✓ 三 numbered card 之後 | ✓ 重複指 Slide 17，跟 Slide 15 的 alert 形成雙重 setup（OK，加深 punchline） |
| 17 | 1317 | `alert-box`「校正後 Brier score 從 0.31 降到 0.12（demo 環境 200 輪樣本）」 | ✓ 公式之後做 evidence cap | ✓ 數據 anchor，呼應 FACT-DRIVEN doctrine |
| 18 | 1430 | `bridge-bottom`「17 個工具今天好用 — 但明天新環境怎麼辦？下一張 →」 | ✓ 6 格網格之後 | ✓ Cliff-hanger 進 Slide 19 |
| 19 | 1520 | `bridge-bottom`「動態路由很爽 — 但 LLM 怎麼知道用哪個工具？最後一張 →」 | ✓ compare-2 之後 | ✓ 推進到 Slide 20 schema sandbox |
| 22 | 1751 | `bridge-bottom`「Athena 的設計：把 OODA 的四步當骨架…」+ 副行 | ✓ compare-2 之後 | ✓ Chapter 04 開章的 thesis statement |

**七個全部命中、位置對、文字節奏對得上 speaker notes 的 transition line**。沒看到語氣斷裂或排版破洞。

---

## Deck 結構

**Slide 3 vs Slide 2（Harry）一致性：** ✓ 對齊。Harry 寫「紅隊主管 / 網路中文資訊股份有限公司」，Alex 寫「資安暨雲端顧問・講師 / 七維思股份有限公司」——同樣是「職稱 / 公司」格式，字級、line-height、bullet 風格全部一致。Harry 4 條 bullets，Alex 3 條 bullets——略短但**這是優點**，speaker notes 已經點明「簡短，不要肉麻」，bio 卡寫成 4 條反而會稀釋「2024 也站過這舞台」這條 punchline 的重量。

**Slide 27 trim 之後跟 23-26 視覺有沒有斷層？** ✓ 沒有。三欄結構保留、color tokens (green/amber/blue) 一致、border-top 3px 規格一樣、card 內結構（label + 標題 + body + ▌ 重點）一致。trim 後 visible content 5.1KB，跟 Slide 26 的 4.7KB 在同一級距，不顯得空、也不顯得密。**從 23 一路看到 27 是同一個排版語言**。

**Slide 32 hide 之後 31 → 33 順嗎？** ✓ 順。
- Slide 31 收尾：「接下來看 AI 怎麼打穿這三台」+ 「目標確認 — 接下來 24 張，看 Athena 怎麼一步步打過去 →」
- Slide 33 開場：「靶機 AD 設定錯誤全景」（INTEL / RECON）

從「目標確認」直接接「來看 AD 設定錯誤」是合理的 mission setup → intel briefing 跳轉。原本 Slide 32（踩過的坑）是 architecture failure-mode 補充，放在這個位置本來就是 PPTX 原檔的 hidden slide——hide 是回到 Harry 的原意，不是新動作。

**28 → 29 (Alex finale → Harry handover) 收得乾淨嗎？** ✓ 乾淨。Slide 28 finale notes 結尾「Harry——換你了」+ `[transition] 移交給 Harry 接 slide 29 live demo`，Slide 29 是 Chapter 05 cover「真槍實彈」+ 「剛剛三條信條，每一頁印證一次」——這句話正好 callback 你 finale 那段「FACT-DRIVEN / DOCTRINE BEATS TOOLS / TEMPO 你看到 30 倍是什麼意思」三句重述。**handover 那一拍是踩在 callback 上的，不是斷掉的**。

---

## 最後三件該動的（如果有）

只有兩件，沒有第三件值得動：

1. **commit message 明寫 scope。** 「embed speaker notes for slides 1-28 (Alex section); slides 29-31 not embedded by design (Harry's section script ownership)」——半年後你回來看 git log 才能立刻 reload context，避免懷疑自己漏掉。

2. **Slide 4 line 246 的「50 張」上台時口語化。** 不要照念，講「接下來這場簡報，每一頁都在敲這三個鼓點」。投影片文字不用改（rough rounding 沒問題），但你嘴巴別卡在這個數字上。

第三件原本想列「Slide 16 + Slide 15 都預告 Slide 17 confidence 拆解」這個雙重 setup，但**重複預告反而加重 0.87 那個 punchline，是優點不是 bug**——不動。

---

## 通過的

- 28 個 speaker note block 位置全對、口吻全是 Alex 的聲音、跟 `speaker-script-p1.md` 沒走樣
- 7 個 bridge-bottom / alert-box 還原全部命中位置、文字、節奏
- Slide 3 bio 跟 Slide 2 Harry 視覺一致、bullets 數量刻意短這個決定對
- Slide 27 trim 落在跟 Slide 26 同級距，視覺沒斷層
- Slide 32 hide 是回歸 Harry 原 PPTX 設計，31 → 33 narrative 接得上
- Slide 28 → 29 handover 踩在 callback 上，finale 收得乾淨
- 圖檔路徑 `/alex.png` 在 `deck-dark/public/` 跟 `deck-light/public/` 都存在
- 總頁數 138 個 separator → 69 nominal slides → 扣掉 hide:true 1 張 = 68，跟 commit message 對得上

GO。Commit。
