# CYBERSEC 2026 — Cloud Slot Deck

10 分鐘收尾講者投影片（雲端 path），8 張 slides。
基於 [iac-landmines](../../../cybersec-talk-iac-landmines) 的視覺風格。

---

## 結構

```
docs/presentation/
├── CYBERSEC-2026-cloud-slot.md     ← 大綱（規劃文件）
├── slides.md                        ← 投影片內容（單一來源）
├── README.md                        ← 本檔案
│
├── deck-dark/                       ← 深色版（GitHub dark）
│   ├── slides.md → ../slides.md    (symlink)
│   ├── style.css                    (從 iac-landmines/deck 抄)
│   ├── global-bottom.vue
│   └── package.json
│
└── deck-light/                      ← 淺色版（暖色奶油）
    ├── slides.md → ../slides.md    (symlink)
    ├── style.css                    (從 iac-landmines/deck-a 抄)
    ├── global-bottom.vue
    └── package.json
```

**單一來源**：只編輯 `docs/presentation/slides.md`，兩個 deck 透過 symlink 自動同步。

---

## 第一次 setup

```bash
# 深色版
cd docs/presentation/deck-dark
npm install   # 或 pnpm install

# 淺色版
cd ../deck-light
npm install
```

---

## 跑兩個版本同時 preview

```bash
# Terminal 1 — 深色版（http://localhost:3030）
cd docs/presentation/deck-dark
npm run dev

# Terminal 2 — 淺色版（http://localhost:3031）
cd docs/presentation/deck-light
npm run dev
```

---

## 編輯 slides

只編輯 **`docs/presentation/slides.md`**。兩個 deck 會 hot-reload 同步顯示。

如果只想調某個版本的視覺差異 → 改該 deck 資料夾下的 `style.css`。

---

## Build / Export

```bash
# 在某個 deck 資料夾下
npm run build      # 產生靜態網頁
npm run export     # 產生 PDF
```

---

## 常用元件 class（從 iac-landmines 繼承）

| Class | 用途 |
|-------|------|
| `slide-eyebrow` | 章節標籤（橘色 uppercase mono） |
| `slide-h1` / `slide-sub` | 標題 / 副標 |
| `kill-chain` + `kc-node` | 攻擊鏈節點，分 `attacker` / `recon` / `exploit` / `benign` |
| `compare-2` | 左右對照卡（綠/紅 border） |
| `numbered-lines` + `numbered-line` | 收尾編號清單 |
| `matrix` | 結構化表格 |
| `funnel` / `spectrum` | 視覺化分層 |
| `cmd-list` / `cmd-row` | 指令清單，`critical` 標紅 |
| `stat-big` / `stat-label` | 大數字 callout |
| `alert-box` / `danger-box` / `bridge-bottom` | 強調框 |
| `deco-squares tl/br` | 角落裝飾方塊 |
| `cover-footer` | 封面底部講者資訊 |

---

## TODO

- [ ] Slide 1：與另一位講者確認結尾，調整 hook 句子（A/B/C 三版備案見大綱）
- [ ] Slide 4：插入實際 War Room 截圖（雲端 OODA log）
- [ ] Slide 5：Blast Radius 視覺化升級（目前是 kill-chain 線性，可考慮輻射狀 SVG）
- [ ] 跑 `npm install` × 2 啟動兩個 deck
- [ ] 演練 ≥ 3 次計時，確認 10 分鐘內結束
