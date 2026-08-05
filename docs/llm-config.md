# LLM 配置指南

Athena 的 **Orient（研判）**階段由一個可換的 LLM 後端驅動。你可以在三種後端之間選擇——雲端 hosted、地端 / 自架（OpenAI 相容，例如 Ollama）、或確定性 mock——全部透過**環境變數**選擇。

## 三種後端

| 後端 | 由什麼選中 | 用途 |
|------|-----------|------|
| **mock** | `MOCK_LLM=true` | 確定性、離線；測試與 demo |
| **openai-compatible**（本地 / 自架） | 設 `OLLAMA_BASE_URL` | OpenAI 相容端點（如 Ollama）；可 air-gap |
| **anthropic**（hosted） | **預設**（前兩者都沒設時） | 雲端託管 API |

### 選擇順序（first-match-wins）

啟動時依序判斷，**第一個命中的勝出**：

1. `MOCK_LLM=true` → **mock**（優先於一切）
2. 否則若有設 `OLLAMA_BASE_URL` → **openai-compatible（本地）**
3. 否則 → **anthropic（預設 fallback）**

> 因此若同時設了 `OLLAMA_BASE_URL` 與 `ANTHROPIC_API_KEY`，**本地（Ollama）勝出**。

---

## 各後端環境變數

### mock

```bash
export MOCK_LLM=true      # 必須剛好是字串 "true"（"1" / "TRUE" 不算）
```

回傳固定的研判結果，適合測試與離線 demo。

> 🔒 生產保護：當 `ATHENA_ENV=production` 時，`MOCK_LLM=true` 會被拒絕、開機中止——避免正式環境誤用假後端。

### openai-compatible（本地 / 自架，例如 Ollama）

```bash
export OLLAMA_BASE_URL=http://<your-host>:11434
```

指向任何 OpenAI 相容的 `/v1/chat/completions` 端點。這條路徑讓 Athena 可完全**地端 / air-gap** 運行、決策腦不依賴外部雲。

### anthropic（hosted，預設）

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

前兩者都沒設時走此後端。`ANTHROPIC_API_KEY` **不是選擇器**——它只在「已落到 anthropic 這條預設路徑」時**提供金鑰**。若未提供金鑰，會嘗試既有的本機憑證來源；都沒有則以空金鑰啟動並印出警告。

---

## 設定使用的模型

模型名稱**可覆寫**（本文件刻意不寫死特定 model 字串——請以你要用的模型為準）。兩種方式，優先序由高到低：

1. **環境變數 `ANTHROPIC_MODEL`** — 最高優先，套用於**所有**後端（名稱雖含 `ANTHROPIC` 但對 Ollama 路徑也生效）。
   ```bash
   export ANTHROPIC_MODEL="<your-model-name>"
   ```
2. **設定檔 / 設定環境變數** — `athena.toml` 的 `[llm] default_model`，或等效的
   `ATHENA_LLM__DEFAULT_MODEL`：
   ```toml
   # athena.toml
   [llm]
   default_model = "<your-model-name>"
   ```

未覆寫時使用內建預設模型。

---

## 該選哪個後端？

- **hosted（anthropic）**：想要最強推理、可連外、不想自架 → 設 `ANTHROPIC_API_KEY`。
- **本地 / 自架（Ollama）**：資料主權 / air-gap / 成本考量、可接受自架模型 → 設 `OLLAMA_BASE_URL`。
- **mock**：跑測試、CI、離線 demo，不想真的呼叫模型 → `MOCK_LLM=true`。

---

## 注意事項

- **後端選擇只看上面的環境變數**。`athena.toml` 的 `[llm]` 區塊除了 `default_model` 外，其餘欄位不影響後端選擇——請用環境變數（`MOCK_LLM` / `OLLAMA_BASE_URL` / `ANTHROPIC_API_KEY`）來切換後端，而非設定檔。
- 每次請求的 `max_tokens` 由呼叫端決定（預設值內建）；**沒有** `temperature` 設定項。
- hosted / 本地端點的連線與整體逾時為內建值（非環境變數可調）。
