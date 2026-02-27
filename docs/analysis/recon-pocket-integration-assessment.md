# recon-pocket 整合評估

> 文件日期：2026-02-27
> 狀態：評估完成
> 來源倉庫：https://github.com/astroicers/recon-pocket

---

## 摘要

recon-pocket 是一個以 Docker Compose 為基礎的單機偵察工具平台，包含 14+ 滲透測試工具容器。本文件評估其與 Athena 整合的可行性、需修復的問題，以及建議的整合策略。

**結論：不重構，提煉整合。** 工具容器本身品質可接受 (8/10)，但編排層品質極低 (2/10)，重構成本接近重寫。建議僅提煉工具容器至 Athena，編排層捨棄。

---

## 一、現狀評估

### 整體品質評分

| 面向 | 評分 | 說明 |
|------|------|------|
| Dockerfile 標準化 | 8/10 | 一致的模式、最小化基礎映像，但無版本釘選 |
| 錯誤處理 | 2/10 | 僅 exit code，輸出抑制，靜默失敗 |
| 資料合約清晰度 | 3/10 | 無 schema，格式不一致，隱式假設 |
| 基建耦合度 | 5/10 | 中度 — 檔案路徑和環境變數，無 K8s 原生功能 |
| 可復用性 | 5/10 | 工具容器可復用，編排層緊耦合 |
| 文件完整度 | 3/10 | README 展示流程但無 API 文件 |
| 測試覆蓋 | 1/10 | 無測試，僅手動/視覺驗證 |
| 運營就緒度 | 3/10 | 無監控、日誌、重試邏輯、健康檢查 |
| **整體** | **4/10** | **可運作的原型，非生產就緒** |

### 兩套互不相容的編排系統

專案同時存在兩套編排機制，且互不相容：

| 模式 | 狀態 | 問題 |
|------|------|------|
| Docker Compose (主要) | 可運作 | 序列執行、手動提示、靜默失敗 |
| Argo Workflows (次要) | **壞的** | 引用不存在的映像，inline 腳本與 shell 腳本矛盾 |

---

## 二、致命 Bug 清單

### Bug 1：Loop Variable Shadowing — 6 個工具靜默丟失 90%+ 資料

**嚴重度：致命**
**影響工具：** dnsrecon, gau, waybackurls, dig, nmap_quick_tcp, nmap_full_tcp

**問題程式碼模式：**

```bash
# 以 gau.sh 為例（其他 5 個工具相同模式）
cat /subdomain_live.txt | while read -r subdomain_live; do
    gau $subdomain_live --verbose --o /tmp/gau_$subdomain_live.txt
done

# 迴圈結束後，${subdomain_live} = 最後一筆讀取的值
mv /tmp/gau_${subdomain_live}.txt /gau/gau_${subdomain_live}.txt
# 只有最後一個子域名的結果被移出！其餘全部留在 /tmp 中靜默丟失
```

**影響**：假設輸入 100 個子域名，只有第 100 個的結果被保留，前 99 個靜默消失。

**修復方式：**

```bash
cat /subdomain_live.txt | sed '/^$/d' | while read -r subdomain_live; do
    gau "$subdomain_live" --verbose -o "/tmp/gau_${subdomain_live}.txt"
    mv "/tmp/gau_${subdomain_live}.txt" "/gau/gau_${subdomain_live}.txt"
done
```

### Bug 2：Argo Workflow 引用不存在的映像

**嚴重度：嚴重 (整個 K8s 路徑無法執行)**

```yaml
# argo/main.yaml 引用：
- image: astroicers/whois:latest      # ← 不存在於任何 registry
- image: astroicers/subfinder:latest   # ← 不存在於任何 registry
```

且 Argo inline 指令與 tools/ 中的 shell 腳本矛盾：

```yaml
# Argo 中：
args: ["subfinder -silent -d {{inputs.parameters.domain}} > /tmp/subfinder.txt"]

# tools/subfinder/subfinder.sh 中：
/bin/subfinder -silent -d ${1} -o /tmp/subfinder.txt
# 不同的輸出重導方式，會產生不同結果
```

### Bug 3：錯誤輸出完全抑制

**嚴重度：嚴重**

```bash
# recon-pocket.sh：
docker-compose -f ./docker-compose.find_subdomain.yml up \
  --build --quiet-pull 2>&1 > /dev/null  # ← 吞掉所有 stdout 和 stderr

if [[ ${?} != 0 ]]; then
    printf "${RED}finding of subdomain failed...${NO_COLOR}\n"
fi
# 只知道失敗了，但完全不知道為什麼
```

### Bug 4：無輸入驗證

**嚴重度：中等**

```bash
# recon-pocket.sh：
export TARGET=${1}
# 若執行 ./recon-pocket.sh （不帶參數）
# TARGET="" — 空字串跑完整 pipeline，每個工具對空 domain 執行
```

---

## 三、耦合分析

### 3.1 Docker Compose 耦合 (高)

```yaml
# 每個 docker-compose 檔案期望：
volumes:
  - ../${TREASURE}/[toolname]:/[toolname]  # ← 路徑依賴
command: [ "[toolname].sh", "${TARGET}" ]  # ← 環境變數依賴
```

耦合點：
- `${TREASURE}`, `${TARGET}` 環境變數必須存在
- 工具假設 `/[toolname]` 可寫目錄
- 部分工具引用相對路徑 `./subdomain.txt`（在容器外執行會壞）

### 3.2 狀態依賴 (致命)

Pipeline 依賴有序的檔案產出：

```
1. ${TREASURE}/subdomain.txt         ← 所有 finder 合併結果
2. ${TREASURE}/subdomain_live.txt    ← ping 檢查後的存活子域名
3. 後續工具假設這些檔案在特定路徑
```

任何步驟失敗，後續步驟靜默產出垃圾資料。

### 3.3 目錄結構脆弱性

```bash
# 手動建立 14+ 目錄 + 手動複製檔案：
mkdir ${PWD}/${TREASURE}/{whois,subfinder,assetfinder,...}
cp ./${TREASURE}/subdomain_live.txt ./tools/gau/
cp ./${TREASURE}/subdomain_live.txt ./tools/waybackurls/
# 5+ 個失敗點
```

---

## 四、可復用性評估

### 可復用的部分 (~85% 的工具容器)

| 組件 | 可復用度 | 說明 |
|------|----------|------|
| Go 工具 Dockerfile | 100% | subfinder, assetfinder, gau, waybackurls, amass — 直接複製 |
| Python 工具 Dockerfile | 80% | dnsrecon, altdns, sublist3r — 需更新 requirements.txt |
| 系統工具 Dockerfile | 100% | whois, dig, crt_sh, nmap — 直接複製 |
| Shell 腳本基本結構 | 70% | 修復 bug 後可作為模板 |

### 不可復用的部分

| 組件 | 可復用度 | 說明 |
|------|----------|------|
| Argo workflow | 0% | 映像不存在，inline 腳本不可攜 |
| recon-pocket.sh | 0% | 緊耦合 14 工具特定集合 |
| docker-compose 檔案 | 20% | 路徑/環境變數硬編碼 |
| 資料合併腳本 | 10% | 只適用子域名發現，無法泛化 |

---

## 五、整合建議

### 策略：提煉工具容器，捨棄編排層

```
保留什麼                   捨棄什麼
──────                     ──────
14 個工具 Dockerfile       recon-pocket.sh (主腳本)
工具 shell 腳本 (修 bug)   8 個 docker-compose.yml
                           argo/main.yaml (壞的)
                           目錄結構耦合邏輯
                           資料合併腳本
```

### 在 Athena 側建立 ContainerEngineClient

```
Athena 新增
──────────
backend/app/clients/container_client.py   ← BaseEngineClient 實作
backend/app/tools/registry.yaml           ← 工具定義 registry
docker/tools/                             ← 搬入的 Dockerfile

OODA 流程整合
────────────
OrientEngine 推薦技術
  → EngineRouter 判斷引擎
    → 若為自定義工具 → ContainerEngineClient
      → 啟動容器 → 解析輸出 → FactCollector
```

### 工具容器改造規格

統一 I/O 介面，從檔案系統模式改為 JSON stdin/stdout：

```bash
# 改造前 (recon-pocket 現狀)
subfinder -silent -d ${1} -o /tmp/subfinder.txt
mv /tmp/subfinder.txt /subfinder/subfinder.txt

# 改造後 (Athena 整合)
#!/bin/sh
DOMAIN="${TOOL_INPUT_DOMAIN}"
RESULT=$(subfinder -silent -d "${DOMAIN}" 2>/dev/null)
echo "${RESULT}" | jq -Rsc '{
  tool: "subfinder",
  type: "subdomain-enumeration",
  target: env.TOOL_INPUT_DOMAIN,
  results: split("\n") | map(select(length > 0))
}'
# 標準 JSON 輸出 → ContainerEngineClient 解析 → FactCollector
```

**統一輸出格式：**

```json
{
  "tool": "subfinder",
  "type": "subdomain-enumeration",
  "target": "example.com",
  "results": ["sub1.example.com", "sub2.example.com", "..."],
  "error": null
}
```

**統一輸入介面：**

| 方式 | 環境變數 | 說明 |
|------|----------|------|
| 主要目標 | `TOOL_INPUT_DOMAIN` | 目標域名 |
| 批次輸入 | `TOOL_INPUT_FILE` | 掛載的輸入檔案路徑 |
| 額外參數 | `TOOL_INPUT_PARAMS` | JSON 格式額外參數 |

---

## 六、工作量估算

| 項目 | 估計量 | 說明 |
|------|--------|------|
| `ContainerEngineClient` | ~200 行 Python | 新程式碼，實作 `BaseEngineClient` 介面 |
| 工具 registry YAML | ~140 行 | 14 工具 × ~10 行定義 |
| 修復 14 個工具腳本 | 各 15-30 分鐘 | loop bug + JSON 輸出 + 錯誤處理 |
| EngineRouter 整合 | ~30 行修改 | 新增 container engine 路由邏輯 |
| Dockerfile 搬遷 | 直接複製 | 無需修改 |
| **不需要動的** | — | OODA Controller, OrientEngine, DecisionEngine, 前端 |

---

## 七、工具清單與分類

### 偵察工具 (Athena 整合優先)

| 工具 | 類型 | Dockerfile 品質 | 優先度 |
|------|------|-----------------|--------|
| subfinder | 子域名發現 | 高 (Go multi-stage) | P0 |
| assetfinder | 資產發現 | 高 (Go multi-stage) | P0 |
| nmap | 網路掃描 | 高 (apk install) | P0 |
| amass | 進階子域名映射 | 高 (Go multi-stage) | P1 |
| nuclei | 漏洞掃描 | 高 (Go multi-stage) | P1 |
| dnsrecon | DNS 列舉 | 中 (Python) | P1 |

### 網頁分析工具

| 工具 | 類型 | Dockerfile 品質 | 優先度 |
|------|------|-----------------|--------|
| gau | 歷史 URL 擷取 | 高 (Go multi-stage) | P2 |
| waybackurls | Wayback Machine | 高 (Go multi-stage) | P2 |
| gobuster | 目錄列舉 | 高 (Go multi-stage) | P2 |

### 漏洞利用工具

| 工具 | 類型 | Dockerfile 品質 | 優先度 |
|------|------|-----------------|--------|
| sqlmap | SQL Injection | 中 (Python) | P3 |
| xsstrike | XSS | 中 (Python) | P3 |

### 輔助工具

| 工具 | 類型 | Dockerfile 品質 | 優先度 |
|------|------|-----------------|--------|
| whois | 域名資訊 | 高 (apk install) | P2 |
| dig | DNS 查詢 | 高 (apk install) | P2 |
| crt_sh | 憑證透明度 | 高 (apk + curl) | P2 |
| altdns | 子域名變異 | 中 (Python) | P3 |
| git-hound | GitHub Secret | 低 (外部二進位下載) | P3 |

---

## 八、專案處置建議

| 動作 | 說明 |
|------|------|
| **Archive recon-pocket** | GitHub 設為 archived，README 加註「工具容器已整合至 Athena」 |
| **提煉工具容器** | 複製 Dockerfile + 修復後的 shell 腳本至 Athena `docker/tools/` |
| **不遷移** | 編排腳本、docker-compose、argo workflow、合併邏輯 |

recon-pocket 作為獨立專案的歷史使命已完成。它的價值被提煉為工具容器庫，融入 Athena 的 `ContainerEngineClient` 執行引擎架構中。
