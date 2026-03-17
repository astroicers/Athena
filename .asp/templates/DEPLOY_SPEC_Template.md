# 部署規格書 (Deployment Specification)

> **使用說明**：複製此模板至專案 `docs/DEPLOY_SPEC.md`。本文件定義所有環境的部署規格、CI/CD 流程及維運標準，應在首次部署前完成並通過技術負責人審閱。

---

| 欄位 | 內容 |
|------|------|
| **專案名稱** | <!-- TODO: 填入專案名稱 --> |
| **版本** | v0.1.0 |
| **最後更新** | <!-- TODO: YYYY-MM-DD --> |
| **狀態** | Draft / Review / Accepted |
| **作者** | <!-- TODO: 填入作者 --> |
| **審閱者** | <!-- TODO: 技術負責人 / SRE --> |

---

## 1. 環境定義

### 1.1 環境清單

| 環境 | 用途 | URL | 部署觸發 | 資料重置 |
|------|------|-----|----------|----------|
| `local` | 本地開發 | `http://localhost:3000` | 手動 | 隨時 |
| `dev` | 功能整合測試 | `https://dev.{domain}` | Push to `develop` | 每日凌晨 |
| `staging` | UAT、效能測試、上線前驗收 | `https://staging.{domain}` | PR merged to `main` | 按需 |
| `prod` | 正式生產環境 | `https://{domain}` | 手動觸發（審批後） | 禁止 |

### 1.2 環境差異對照

| 項目 | Local | Dev | Staging | Prod |
|------|-------|-----|---------|------|
| 資料庫 | Docker PostgreSQL | RDS t3.small | RDS t3.medium | RDS r6g.large (Multi-AZ) |
| 快取 | Docker Redis | ElastiCache t3.micro | ElastiCache t3.small | ElastiCache r6g.large (Cluster) |
| API 實例數 | 1 | 1 | 2 | 最小 3，自動擴展至 10 |
| CDN | 無 | 無 | CloudFront | CloudFront |
| Log Level | DEBUG | DEBUG | INFO | WARN |
| Feature Flags | 全開 | 全開 | 依測試需求 | 受控發布 |
| 外部通知（Email/SMS） | 停用（Mock） | Sandbox 模式 | 限制收件者 | 正式發送 |

### 1.3 環境變數清單

> **安全規則**：所有敏感值（Secret, Key, Password）禁止硬編碼，必須透過 Secret Manager 注入。

#### 應用程式設定

| 變數名 | 類型 | 必填 | 範例值（非生產） | 說明 |
|--------|------|------|-----------------|------|
| `NODE_ENV` | string | 是 | `production` | 執行環境 |
| `PORT` | number | 是 | `3000` | API 監聽 Port |
| `API_BASE_URL` | string | 是 | `https://api.example.com` | API 基礎 URL |
| `ALLOWED_ORIGINS` | string | 是 | `https://example.com` | CORS 允許來源（逗號分隔） |
| `LOG_LEVEL` | string | 是 | `info` | 日誌等級：debug/info/warn/error |

#### 資料庫

| 變數名 | 類型 | 必填 | 說明 |
|--------|------|------|------|
| `DATABASE_URL` | string | 是 | PostgreSQL 連線字串（含帳密，從 Secrets Manager 注入） |
| `DATABASE_POOL_MIN` | number | 否 | 最小連線數，預設 2 |
| `DATABASE_POOL_MAX` | number | 否 | 最大連線數，預設 20 |
| `DATABASE_SSL` | boolean | 是 | 生產環境必須為 `true` |

#### 認證

| 變數名 | 類型 | 必填 | 說明 |
|--------|------|------|------|
| `JWT_PRIVATE_KEY` | string | 是 | RS256 私鑰（PEM 格式，從 Secrets Manager 注入） |
| `JWT_PUBLIC_KEY` | string | 是 | RS256 公鑰 |
| `JWT_ACCESS_EXPIRES_IN` | string | 是 | Access Token 有效期，預設 `15m` |
| `JWT_REFRESH_EXPIRES_IN` | string | 是 | Refresh Token 有效期，預設 `7d` |

#### 快取

| 變數名 | 類型 | 必填 | 說明 |
|--------|------|------|------|
| `REDIS_URL` | string | 是 | Redis 連線 URL |
| `REDIS_TLS` | boolean | 是 | 生產環境必須為 `true` |

#### 第三方服務

| 變數名 | 類型 | 必填 | 說明 |
|--------|------|------|------|
| `SENDGRID_API_KEY` | string | 是 | Email 服務 API Key |
| `SENDGRID_FROM_EMAIL` | string | 是 | 寄件者地址 |
| `GOOGLE_OAUTH_CLIENT_ID` | string | 否 | Google OAuth Client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | string | 否 | Google OAuth Secret（從 Secrets Manager 注入） |
| <!-- TODO --> | <!-- TODO --> | <!-- TODO --> | <!-- TODO: 補充專案特定變數 --> |

---

## 2. Container 規格

### 2.1 Base Image

```dockerfile
# 後端 API（Node.js 範例）
FROM node:20-alpine AS base

# 安全考量：
# - 使用 Alpine 減小攻擊面
# - 固定 major.minor 版本，避免意外升級
# - 定期更新 base image（CI 每週掃描）
```

```dockerfile
# 前端（Next.js 範例）
FROM node:20-alpine AS base
```

### 2.2 Multi-Stage Build（後端 API）

```dockerfile
# ===================== Stage 1: Dependencies =====================
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile --production=false

# ===================== Stage 2: Build =====================
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN yarn build

# ===================== Stage 3: Production =====================
FROM node:20-alpine AS runner
WORKDIR /app

# 安全：非 root 使用者執行
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodeuser -u 1001

# 僅複製生產所需檔案
COPY --from=builder --chown=nodeuser:nodejs /app/dist ./dist
COPY --from=builder --chown=nodeuser:nodejs /app/node_modules ./node_modules
COPY package.json ./

USER nodeuser

EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget -qO- http://localhost:3000/health || exit 1

CMD ["node", "dist/main.js"]
```

### 2.3 Health Check 端點

**`GET /health`（存活探針 Liveness Probe）：**

```json
// 僅確認進程存活
HTTP 200
{ "status": "ok", "timestamp": "2024-01-15T10:30:00Z" }
```

**`GET /health/ready`（就緒探針 Readiness Probe）：**

```json
// 確認所有依賴就緒
HTTP 200
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "migrations": "current"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}

// 未就緒時（503）：
{
  "status": "not_ready",
  "checks": {
    "database": "error: connection refused",
    "redis": "ok",
    "migrations": "pending"
  }
}
```

### 2.4 Resource Limits

| 環境 | 元件 | CPU Request | CPU Limit | Memory Request | Memory Limit |
|------|------|-------------|-----------|----------------|--------------|
| Dev | API | 100m | 500m | 128Mi | 512Mi |
| Staging | API | 250m | 1000m | 256Mi | 1Gi |
| Prod | API | 500m | 2000m | 512Mi | 2Gi |
| Prod | Worker | 250m | 1000m | 256Mi | 1Gi |
| Prod | Migration Job | 100m | 500m | 128Mi | 512Mi |

**HPA（Horizontal Pod Autoscaler）設定（Prod）：**

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
spec:
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70     # CPU > 70% 時觸發擴展
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## 3. CI/CD Pipeline

### 3.1 Pipeline 架構

```
PR 建立
│
├── [自動觸發] CI Pipeline
│   ├── Stage 1: Code Quality
│   │   ├── Lint（ESLint, Prettier）
│   │   ├── Type Check（TypeScript）
│   │   └── Security Scan（npm audit, Trivy）
│   │
│   ├── Stage 2: Testing
│   │   ├── Unit Tests（Jest）
│   │   ├── Integration Tests
│   │   └── Coverage Report（門檻：80%）
│   │
│   └── Stage 3: Build Verification
│       ├── Docker Build
│       └── Docker Image Scan（Trivy）
│
PR 合併至 main
│
├── [自動觸發] CD Pipeline - Staging
│   ├── Build & Push Image（with SHA tag）
│   ├── Run DB Migrations（Staging）
│   ├── Deploy to Staging（Rolling Update）
│   ├── Smoke Tests
│   └── E2E Tests（Playwright）
│
手動審批（Production Release）
│
└── [手動觸發] CD Pipeline - Production
    ├── 確認 Staging 健康狀態
    ├── 建立 Release Tag（v{semver}）
    ├── Build & Push Image（with semver tag）
    ├── Run DB Migrations（Prod，含備份）
    ├── Blue-Green Deploy
    ├── Smoke Tests（Production）
    └── 通知 Slack 部署成功/失敗
```

### 3.2 自動化測試門檻

| 測試類型 | 工具 | 通過門檻 | 失敗行為 |
|----------|------|----------|----------|
| Lint | ESLint + Prettier | 0 Error | Block PR |
| Type Check | TypeScript | 0 Error | Block PR |
| Unit Tests | Jest | 全通過 | Block PR |
| Coverage | Jest --coverage | 核心模組 > 90%，整體 > 80% | Block PR |
| Integration Tests | Jest + Supertest | 全通過 | Block PR |
| Security Scan | npm audit | 0 Critical, 0 High | Block PR |
| Container Scan | Trivy | 0 Critical | Block PR |
| E2E Tests | Playwright | 全通過 | Block Deploy |
| Performance | k6 | P95 < 200ms, Error Rate < 1% | 通知，不阻擋 |

### 3.3 Deployment Strategy

**Staging：Rolling Update**

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1         # 最多額外啟動 1 個 Pod
    maxUnavailable: 0   # 確保全程無中斷
```

**Production：Blue-Green Deploy**

1. 部署新版本至「Green」環境（不對外流量）
2. 執行 Smoke Tests 確認 Green 健康
3. Load Balancer 切換流量：Blue → Green（< 1 分鐘）
4. 觀察 5 分鐘，確認錯誤率無異常
5. 保留 Blue 環境 30 分鐘作為快速回滾備援
6. 確認後刪除 Blue 環境

**Feature Flags（受控發布）：**

- 使用 <!-- TODO: LaunchDarkly / Unleash / 自建 --> 管理 Feature Flags
- 新功能初次上線使用 Feature Flag 控制，允許按使用者比例逐步開放
- Flag 清單須定期審查，已全量發布的 Flag 在兩個迭代後移除

---

## 4. 監控與告警

### 4.1 Metrics 定義

#### 系統層 Metrics

| Metric | 類型 | 標籤 | 說明 |
|--------|------|------|------|
| `http_requests_total` | Counter | method, path, status_code | HTTP 請求總數 |
| `http_request_duration_seconds` | Histogram | method, path, status_code | HTTP 回應時間分佈 |
| `http_request_size_bytes` | Histogram | method, path | 請求大小 |
| `process_cpu_usage` | Gauge | — | CPU 使用率 |
| `process_memory_usage_bytes` | Gauge | — | 記憶體使用量 |
| `db_pool_active_connections` | Gauge | — | 資料庫連線池使用數 |
| `db_query_duration_seconds` | Histogram | operation, table | 資料庫查詢時間 |
| `cache_hits_total` | Counter | cache_name | 快取命中數 |
| `cache_misses_total` | Counter | cache_name | 快取未命中數 |

#### 業務層 Metrics

| Metric | 類型 | 說明 |
|--------|------|------|
| `user_logins_total` | Counter | 登入次數（按成功/失敗） |
| `user_registrations_total` | Counter | 新使用者註冊數 |
| <!-- TODO --> | <!-- TODO --> | <!-- TODO: 業務核心指標 --> |

### 4.2 告警規則

| 告警名稱 | 條件 | 持續時間 | 嚴重程度 | 通知對象 |
|----------|------|----------|----------|----------|
| `HighErrorRate` | HTTP 5xx 錯誤率 > 1% | 5 分鐘 | Critical | PagerDuty + Slack #oncall |
| `HighLatency` | P95 回應時間 > 500ms | 10 分鐘 | Warning | Slack #alerts |
| `PodCrashLooping` | Pod 重啟 > 3 次 | 5 分鐘 | Critical | PagerDuty + Slack #oncall |
| `HighCPU` | CPU 使用率 > 85% | 15 分鐘 | Warning | Slack #alerts |
| `HighMemory` | 記憶體使用率 > 90% | 10 分鐘 | Critical | PagerDuty + Slack #oncall |
| `DatabaseConnectionPool` | 連線池使用率 > 80% | 5 分鐘 | Warning | Slack #alerts |
| `SlowQuery` | 查詢時間 > 1s | 即時 | Warning | Slack #dev |
| `CertificateExpiry` | SSL 憑證 < 30 天到期 | 每日 | Warning | Slack #infra |
| `DiskUsage` | 磁碟使用率 > 80% | 30 分鐘 | Warning | Slack #infra |

### 4.3 SLA 定義

| 服務 | SLA 目標 | 量測方式 | 報告頻率 |
|------|----------|----------|----------|
| API 可用性 | 99.9%（月計，允許 ~43 分鐘停機） | Synthetic Monitoring（每分鐘） | 月報 |
| API P95 回應時間 | < 200ms | Percentile from metrics | 週報 |
| 資料庫備份成功率 | 100% | 備份任務狀態監控 | 日報 |
| 部署成功率 | > 95% | CI/CD 成功率統計 | 月報 |

### 4.4 監控儀表板

**必備儀表板（Grafana / Datadog）：**

1. **系統總覽 Dashboard**
   - 請求率（RPS）、錯誤率、P50/P95/P99 回應時間
   - 實例健康狀態、Pod 數量
   - CPU、記憶體、磁碟使用率

2. **資料庫 Dashboard**
   - 連線池使用率、查詢 QPS
   - 慢查詢 Top 10
   - Replication Lag（若有 Read Replica）

3. **業務指標 Dashboard**
   - <!-- TODO: 業務核心 KPI 圖表 -->
   - 使用者活躍數、功能使用率

4. **SLA Dashboard**
   - 月度可用性
   - 錯誤預算消耗

---

## 5. 災難復原（Disaster Recovery）

### 5.1 Backup 策略

| 資料來源 | 備份方式 | 頻率 | 保留期限 | 儲存位置 |
|----------|----------|------|----------|----------|
| PostgreSQL | 自動快照（RDS Automated Backup） | 每日 | 30 天 | 同區域 S3 |
| PostgreSQL | Cross-Region 快照複製 | 每日 | 7 天 | 備援區域 S3 |
| PostgreSQL | WAL Archiving（時間點恢復） | 連續 | 7 天 | S3 |
| Redis | 不備份（快取可重建） | — | — | — |
| S3 物件（使用者上傳） | S3 Cross-Region Replication | 即時同步 | 永久 | 備援區域 S3 |
| 應用程式設定/Secret | Secrets Manager 版本控制 | 每次變更 | 永久 | AWS Secrets Manager |

**備份驗證：**
- 每月執行一次備份還原演練（在隔離環境），驗證備份完整性
- 演練結果記錄於 `docs/dr-drills/` 目錄

### 5.2 RTO / RPO 目標

| 情境 | RTO（Recovery Time Objective） | RPO（Recovery Point Objective） |
|------|-------------------------------|--------------------------------|
| 單一 Pod 故障 | < 2 分鐘（自動重啟） | 0（無資料遺失） |
| 可用區故障 | < 5 分鐘（Multi-AZ 自動 Failover） | < 1 分鐘 |
| 資料庫主節點故障 | < 3 分鐘（RDS Multi-AZ Failover） | < 1 分鐘 |
| 區域性故障（整個 Region） | < 4 小時（手動切換至備援區域） | < 24 小時 |
| 資料誤刪（邏輯性損壞） | < 2 小時（PITR 還原） | 時間點還原，最多遺失 5 分鐘 |

### 5.3 Rollback 程序

#### 應用程式版本回滾

```bash
# 1. 確認當前部署版本
kubectl get deployment api -o jsonpath='{.spec.template.spec.containers[0].image}'

# 2. 列出可回滾的版本
kubectl rollout history deployment/api

# 3. 立即回滾至上一版本（< 2 分鐘）
kubectl rollout undo deployment/api

# 4. 或回滾至指定版本
kubectl rollout undo deployment/api --to-revision=3

# 5. 確認回滾成功
kubectl rollout status deployment/api
```

#### 資料庫 Migration 回滾

```bash
# 1. 確認當前 Migration 版本
make db-migration-status

# 2. 回滾至指定版本（需預先撰寫 down migration）
make db-migration-rollback VERSION=V003

# 3. 驗證資料完整性
make db-health-check
```

**Migration 回滾原則：**
- 每個 `UP` migration 必須對應撰寫 `DOWN` migration
- 回滾前必須評估資料影響（欄位刪除、資料轉換不可逆）
- 重大 Migration 上線前需備份資料庫

#### 完整災難恢復流程（區域故障）

1. **宣告事故（< 5 分鐘）**
   - 通知 On-call 工程師、技術負責人
   - 建立事故 Channel（Slack）
   - 更新狀態頁面（<!-- TODO: status.{domain}.com -->）

2. **評估影響範圍（< 15 分鐘）**
   - 確認受影響服務與使用者範圍
   - 評估資料遺失風險

3. **啟動備援區域（< 1 小時）**
   - 更新 DNS 指向備援區域（TTL 預先設為 60 秒）
   - 確認備援資料庫可用
   - 部署最後一個穩定版本至備援環境

4. **驗證與通知（< 30 分鐘）**
   - 執行 Smoke Tests
   - 通知使用者服務已恢復

5. **事後分析（48 小時內）**
   - 執行 Postmortem：`make postmortem-new TITLE="..."`
   - 更新 DR 計畫

### 5.4 On-Call 輪值

| 欄位 | 說明 |
|------|------|
| 輪值工具 | <!-- TODO: PagerDuty / OpsGenie --> |
| 輪值週期 | 每週輪換 |
| 回應時間（Critical） | 15 分鐘內回應 |
| 回應時間（Warning） | 工作時間內處理 |
| Escalation Policy | Primary → Secondary → 技術負責人（每 15 分鐘升級） |
| On-Call 手冊 | `docs/oncall-runbook.md` |

---

## 附錄

### A. 部署前檢查清單

**每次 Production 部署前確認：**

- [ ] Staging 環境 Smoke Tests 全部通過
- [ ] E2E Tests 全部通過
- [ ] 效能測試無回歸
- [ ] Security Scan 無新增 Critical/High 問題
- [ ] DB Migration 已在 Staging 驗證
- [ ] 備份已執行且驗證成功
- [ ] Feature Flags 設定正確
- [ ] 相關文件已更新（CHANGELOG, API 文件）
- [ ] 技術負責人已審批
- [ ] On-Call 工程師已就位
- [ ] 部署時間已通知相關利害關係人

### B. Secret 輪換計畫

| Secret | 輪換頻率 | 負責人 | 最後輪換日期 |
|--------|----------|--------|--------------|
| JWT Private Key | 每年 | <!-- TODO --> | <!-- TODO --> |
| Database Password | 每季 | <!-- TODO --> | <!-- TODO --> |
| API Keys（第三方） | 每年或按需 | <!-- TODO --> | <!-- TODO --> |

### C. 容量規劃

| 指標 | 當前值 | 6 個月預測 | 12 個月預測 | 擴容觸發點 |
|------|--------|------------|------------|------------|
| DAU（日活躍使用者） | <!-- TODO --> | <!-- TODO --> | <!-- TODO --> | 達觸發點時啟動評估 |
| 資料庫大小 | <!-- TODO --> | <!-- TODO --> | <!-- TODO --> | 使用率 > 70% |
| API RPS（峰值） | <!-- TODO --> | <!-- TODO --> | <!-- TODO --> | P95 > 150ms |

### D. 變更歷史

| 版本 | 日期 | 變更摘要 | 作者 |
|------|------|----------|------|
| v0.1.0 | <!-- TODO: YYYY-MM-DD --> | 初版建立 | <!-- TODO --> |

### E. 相關文件

- [`SRS.md`](./SRS.md) — 軟體需求規格書
- [`SDS.md`](./SDS.md) — 軟體設計規格書（第 1.3 節部署架構）
- [`docs/adr/`](./docs/adr/) — 架構決策記錄
- [`docs/oncall-runbook.md`](./docs/oncall-runbook.md) — On-Call 操作手冊
- 監控儀表板：<!-- TODO: 連結 -->
- 狀態頁面：<!-- TODO: status.{domain}.com -->
