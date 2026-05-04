# CYBERSEC 2026 — 雲端 path 講者大綱（10 分鐘）

> **演講主題**：AI 從小兵變指揮官，擊殺鏈如何從工具箱進化為核彈
> **總長**：30 分鐘（雙講者）
> **本講者時段**：最後 10 分鐘（收尾）
> **形式**：投影片，無 live demo
> **觀眾**：CYBERSEC 進階場（混合程度）

---

## 整體架構

```
30 min 整體節奏：
─────────────────────────────────────────────
[0-3]   開場 + 框架介紹      ← 另一位講者
[3-20]  地端 demo (AD)       ← 另一位講者
[20-22] 交接：「他拿到 DA了，但...」← 我
[22-28] 雲端 path + 戰場全景  ← 我
[28-30] 收尾                  ← 我
─────────────────────────────────────────────
```

**敘事弧**：「他拿下了城堡 — 但戰場其實沒結束」

另一位講者打到 Domain Admin 拿下城堡 → 我接手「但現代企業的價值資產，已經不在城堡裡了」→ 雲端 path → 收尾。

---

## 假設與調整空間

| 情境 | 機率 | 對應 hook |
|------|------|---------|
| **A. 拿到 Domain Admin 收尾**（本大綱基於此） | 60% | 「城堡鑰匙到手 — 但城堡之外還有什麼？」 |
| B. DCSync + krbtgt（Golden Ticket capability） | 25% | 「on-prem 上帝權限到手 — 但雲端的上帝是誰？」 |
| C. 模擬資料外洩 / ERP 客戶資料 | 15% | 「拿到客戶資料 — 但客戶資料的另一份在哪？」 |

---

## 投影片大綱（8 張，10 分鐘）

### Slide 1（0:45）— Hook / 接手

**畫面**：地端拓樸圖（剛剛 demo 結束的最終狀態，DA 標紅）→ 慢慢淡入旁邊的雲端圖層

**口白**：
> 「[講者名] 剛剛展示了 AI 怎麼一步一步拿下 Domain Admin。
> 在傳統的滲透測試敘事裡，這就是片尾字幕。
> 但對現代企業 — 你拿到的不是終點，是第二場戰爭的入場券。」

---

### Slide 2（1:00）— 現實：戰場已經改變

**畫面**：兩個圈圈相交的圖
- 左圈：On-prem AD（剛剛 demo 的世界）
- 右圈：Entra ID + Azure + AWS + M365
- 中間相交區：**Hybrid Identity**（Entra Connect / Azure AD Connect）

**重點**：
- 台灣企業 80%+ 是 hybrid，不是純地端也不是純雲端
- Entra Connect 是雙向通道 — on-prem 到 cloud，也 cloud 到 on-prem
- 傳統紅藍隊各看一半，所以這個交界區是**最大盲區**

**口白**：
> 「DA 不是城堡的最高點 — 是通往另一座城堡的橋。
> 而那座城堡，叫 Azure tenant。」

---

### Slide 3（1:30）— 雲端戰場的 C5ISR 視角

**畫面**：表格疊上剛剛 demo 用的 C5ISR dashboard

| 域 | 地端（剛才看到的） | 雲端（接下來要看的） |
|----|------------------|-------------------|
| **ISR** | nmap, BloodHound | IMDS, S3 enum, Graph API |
| **Computers** | IP, Hostname | IAM Role, Resource ARN |
| **Comms** | SSH, SMB, Kerberos | OAuth Token, PRT, SAS Token |
| **Cyber** | exploit, lateral move | API abuse, IAM privesc, token theft |

**口白**：
> 「同一套 C5ISR 框架，戰場從機房延伸到雲端。
> 對 AI 指揮官來說 — 這是同一場戰爭的不同前線。」

---

### Slide 4（2:00）— Cloud OODA Chain（核心內容）

**畫面**：展示已跑通的 flAWS.cloud SSRF → IMDS → AWS 流程，用 Athena War Room 截圖呈現

#### Cycle 1：Recon
- nmap + web probe 發現 `/proxy/` endpoint
- AI 觀察：「這是 SSRF 候選」

#### Cycle 2：Orient 的指揮官時刻 ⭐

秀 Orient JSON 輸出（10 分鐘裡最有殺傷力的一張）：

```json
{
  "situation_assessment": "Web app exposes /proxy/ with IMDS
    canary confirmed. SSH key-only — brute force will fail.
    Cloud pivot has higher strategic value.",
  "recommended_technique": "T1190",
  "reasoning": "Rule #10 SSRF→IMDS triggered.
    Skipping SSH (Rule #2: dead branch).",
  "confidence": 0.87
}
```

**口白**：
> 「小兵看到 SSH:22 就 brute force。
> 指揮官看到 SSH 是 key-only，自動放棄這條路，選擇 SSRF。
> 不是更快 — 是更聰明。」

#### Cycle 3：Act
- `web_http_fetch` via proxy → IMDS → AWS credential
- 展示 Timeline 上 `cloud.aws.iam_credential` fact 出現
- 接續：S3 enum 拿到設定檔，裡面有 AD service account 密碼

---

### Slide 5（1:30）— 兩條 path 的交會點 ⭐ 核心

**這是整場演講的核心圖** — 把雲端 path 和地端講者的內容縫成一張圖：

```
   [地端講者剛展示的]                  [我剛展示的]
   ───────────────────                ─────────────────
   邊界突破                           Web SSRF
        │                                 │
        ▼                                 ▼
   AD 偵察 (BloodHound)              Cloud credential
        │                                 │
        ▼                                 ▼
   Kerberoast / AD CS                S3 / config 檔案
        │                                 │
        ▼                                 ▼
   ╔═══════════════════════════════════════╗
   ║       HYBRID IDENTITY 交會區           ║
   ║   ┌─────────────────────────────────┐ ║
   ║   │  AD service account credential  │ ║
   ║   │       ↕ Entra Connect ↕         │ ║
   ║   │  MSOL / Azure AD account        │ ║
   ║   └─────────────────────────────────┘ ║
   ╚═══════════════════════════════════════╝
        │                                 │
        ▼                                 ▼
   Domain Admin                      Azure tenant
        │                                 │
        └─────────► 全戰場 ◄──────────────┘
```

**口白**：
> 「你們剛才看到兩種完全不同的入侵起點 —
> 一個從 VPN 漏洞，一個從 web 應用程式。
> 但 AI 指揮官把它們處理成同一場戰爭。
> 因為對 AI 來說，這就是同一個戰場。
> 是我們人類，太習慣把它們分開看了。」

---

### Slide 6（1:00）— Real-world：這已經在發生

**畫面**：三個 case 並排，每個一句話

| Case | 年份 | 一句話 |
|------|------|--------|
| **Storm-0558** | 2023 | 偷 MSA 簽章 key → 跨 tenant 偷信件，多家政府機構受害 |
| **Midnight Blizzard** | 2024 | 從 test tenant 橫向到 Microsoft 內部 + 客戶 tenant |
| **Volt Typhoon** | 2024-25 | 地端持久化 + 雲端橫向，鎖定關鍵基礎設施（含台灣） |

**口白**：
> 「這不是 lab 演練 — 是 2023-2025 年真實發生的事。
> 差別只在於 — 攻擊者是用 Python script，還是用 AI。
> 而那個差距，正在縮小。」

---

### Slide 7（1:30）— 防禦方視角：Blast Radius

**畫面**：以一個 SSRF 漏洞為起點，畫炸彈擴散圖

```
       SSRF (1 個漏洞)
            │
            ▼
       AWS credential
       ╱     │     ╲
      ▼      ▼      ▼
    S3     EC2     IAM
            │
            ▼ (config 裡的 AD 密碼)
        AD foothold
            │
            ▼
        Hybrid identity
       ╱        ╲
      ▼          ▼
  M365 mail  Azure resources
```

**3 個 takeaway**（給防禦方）：

1. **漏洞不是孤立的** — 一個 SSRF 的 blast radius 跨 4 個域，傳統 CVSS 算不出來
2. **Hybrid identity 需要專門演練** — 紅藍隊都要 cross-domain 視野，不能只看一邊
3. **AI 速度問題** — 你的 incident response 還在用人類速度嗎？AI 攻擊者不會等

---

### Slide 8（0:45）— 收尾

**畫面**：全黑，一句話

> **「從工具箱到核彈，距離不是工具的進步 — 是視野的擴張。」**

**口白**：
> 「[講者名] 展示了 AI 在地端怎麼從小兵變指揮官。
> 我展示了同一個指揮官在雲端的另一場戰爭。
>
> 但真正的轉變不在工具 — 在我們怎麼定義戰場。
>
> 下次規劃紅隊演練、或設計防禦的時候 —
> 問自己一個問題：
> 你的 AI、你的 SOC、你的紅隊 — 看得到整個戰場嗎？
>
> 還是還停留在一個工具、一個系統、一個域？
>
> 謝謝。」

---

## 時間預算

| Slide | 內容 | 時間 |
|-------|------|------|
| S1 | Hook | 0:45 |
| S2 | Reality | 1:00 |
| S3 | C5ISR 雲端化 | 1:30 |
| S4 | Cloud OODA | 2:00 ← 核心 |
| S5 | 兩條 path 匯合 | 1:30 ← 核心 |
| S6 | Real-world | 1:00 |
| S7 | Blast Radius | 1:30 |
| S8 | 收尾 | 0:45 |
| **總計** | | **10:00** |

---

## 需要準備的素材

| # | 項目 | 來源 | 狀態 |
|---|------|------|------|
| 1 | Slide 4 的 Orient JSON 截圖 | flAWS.cloud demo log | 待整理 |
| 2 | Slide 4 的 War Room Timeline 截圖 | 雲端 OODA 跑完的畫面 | 待整理 |
| 3 | Slide 5 的雙 path 圖 | 需與另一位講者對齊後製作 | 待製作 |
| 4 | Hook 句子（3 種版本） | 對應另一位講者 3 種結尾 | 已備 |

---

## 風險點

1. **Slide 5 是核心** — 若與另一位講者未對齊，這張圖會尷尬。**演講前一週**必須看過他的最後一張投影片
2. **Slide 7 的 blast radius** — 若他的地端 demo 已包含「拿到 AD 後打雲端」，要改成純 cloud-native 視角避免重複
3. **Hook 適應** — 看他 demo 終點在哪，三選一替換 Slide 1 句子

---

## 待辦清單

- [ ] 與另一位講者對齊：他的最後一張 slide 是什麼？
- [ ] 跑一次 flAWS.cloud demo，截圖 Orient JSON + Timeline
- [ ] Slide 5 雙 path 匯合圖，等對齊後製作
- [ ] 三版 hook 句子準備好（A/B/C）
- [ ] 全程演練 ≥ 3 次，確認 10 分鐘內結束
- [ ] 備份：若臨場跳過 1 張，優先犧牲 Slide 6（Real-world）

---

## 與另一位講者需對齊的事項

1. 他要不要在他的 slot 結尾放一張「我拿到 DA 了，下一步呢？」當交接點？
2. Athena demo 截圖風格、術語要統一
3. 他的 Mission Profile 用哪個（SP？CO？）— 我雲端 path 也用同一個比較連貫
4. Slide 5 雙 path 匯合圖在演講前讓他先看過，確認他的 path 我畫對
