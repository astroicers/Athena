# Alex Agent — 5 張不確定 slide 動畫判斷

**版本：** 2026-05-06

## Slide 5 — Mission Briefing · Agenda
**Verdict:** NO
**Reason:** 這張是過場張，講稿明確標記「語速加快，這張不要拖」、「我不一個一個唸」。功能是讓觀眾看到全景章節地圖，audience 自己掃一眼六列就完事，加 v-click 把六列拆開反而違背「不要拖」的指示。30 秒 slot 多六次 click 會把節奏完全打死。Audience 提前讀沒有壞處——他們知道接下來會講什麼，反而幫助錨定。
**If YES, where to add v-click:** 不適用。

## Slide 7 — 每一階段在做什麼
**Verdict:** YES
**Reason:** 講稿是典型 staged reveal 的節奏 — 「第一段……」「第二段……」「第三段……」，每段之間 [停頓]，最後有一個 climactic 收尾「傳統紅隊一週、AI 20 分鐘」。如果三個 numbered line 一次出現，audience 會跳到底下 read ahead，講「第一段」時他們已經看完第三段。staged reveal 配 [停頓] 的講稿，動畫服務節奏的價值最高。
**If YES, where to add v-click:** 三個 `numbered-line`（01 / 02 / 03）逐條 v-click，最後 `bridge-bottom`「傳統紅隊一週的工作量 ─ AI 在 20 分鐘內全程自走」獨立一個 click 作為 punchline。共 4 步。

## Slide 8 — 軍事作戰遇到過同樣的問題
**Verdict:** YES
**Reason:** 左右對比 layout，講稿是「[指紅框]……[指綠框]……」的雙段結構，紅框講的是「問題」、綠框講的是「解法」。如果兩塊一次出現，「為什麼一個資安場子要講軍事」這個 hook 就洩了——觀眾還沒被勾起興趣，已經看到答案是 C5ISR。staged reveal 把 narrative arc 守住：先 problem，後 answer，最後 bridge_bottom 收。
**If YES, where to add v-click:** 紅框（二戰前 / 各兵種各自為政）先出 → 綠框（戰後解法 / C2 → C5ISR）後出 → `bridge-bottom`「軍事先解決了這個問題，我們直接借用」最後出。共 3 步。中間的 ↔ 跟著綠框一起進來。

## Slide 15 — Orient 的輸出
**Verdict:** NO
**Reason:** 全螢幕 JSON，內容是一個整體結構，講稿說「我給你看一行就好」然後用 [指 confidence: 0.87]、[指 options] 口頭聚焦。JSON code block 在 Slidev 拆 v-click 很彆扭——拆字串行不自然，整塊閃進閃出又破壞「結構化判斷」的視覺感。Audience 看 code block 本來就是邊聽邊掃，講者用「指」帶他們看哪一行更自然。如果真的擔心 read ahead，可以靠 highlight 而不是 v-click。
**If YES, where to add v-click:** 不建議。如果一定要加，可以給 `slide-sub` 那行（「LLM 讀完 facts，吐回的就是這份結構化判斷」）一個獨立 click 在 JSON 之後出，當作 callback。但 marginal value，不加也行。

## Slide 20 — Schema 是介面，也是 sandbox
**Verdict:** YES
**Reason:** 三個 numbered card 結構跟 Slide 7 同型，但這張第三條是整章 architecture 的 climax — 「Prompt injection via MCP description」是講稿明確 [語速放慢]、[停頓]、[掃視] 的位置，是要給觀眾呼吸空間的安全警告。如果三條一次出現，第三條的衝擊力會被前兩條稀釋；觀眾眼睛已經掃到「allowlist、純 ASCII」，講者再強調就晚了。staged reveal 讓第三條獨立呼吸是必要的。
**If YES, where to add v-click:** 三條 `numbered-line` 逐條 v-click，第三條（prompt injection）前留一個明顯停頓位（用獨立 click step）。最後 `bridge-bottom`「架構講完了 — 接下來把它跑成五個動作循環」可以跟第三條一起出，或獨立一步。建議共 4 步：01 → 02 → 03 → bridge。

## TL;DR
**YES：** Slide 7、Slide 8、Slide 20（三張都有明確 staged narrative + 講稿 [停頓] 標記）
**NO：** Slide 5（過場張，講稿要求加速）、Slide 15（JSON 整塊呈現，口頭指引比 v-click 自然）
