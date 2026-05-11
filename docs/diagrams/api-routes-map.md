# Athena 2.0 — API 路由速查

> Base URL: `http://localhost:58000/api`

---

## 路由總覽

```mermaid
mindmap
  root((API /api))
    health
      GET /health
    operations
      GET /operations
        列出所有 op 及迭代次數
      POST /operations
        啟動新 OODA 操作
        mode=normal 預設
        mode=operator_override
      POST /operations/:op_id/abort
      POST /operations/:op_id/iterate
        對既有 op 再跑一輪
      POST /operations/:op_id/approve
        人類核准高風險操作
        approved_by: String
    facts
      GET /operations/:op_id/facts
      GET /operations/:op_id/facts/count
    ooda_phases
      POST /operations/:op_id/observe
      GET /operations/:op_id/observe/summary
      POST /operations/:op_id/orient
      POST /operations/:op_id/decide
      POST /operations/:op_id/act
    scheduler
      POST /operations/:op_id/scheduler/start
      DELETE /operations/:op_id/scheduler/stop
      GET /scheduler/active
    intelligence
      POST /operations/:op_id/scope/check
      GET /operations/:op_id/opsec
      POST /operations/:op_id/opsec/consume
      GET /operations/:op_id/c5isr
      GET /operations/:op_id/brief
      GET /operations/:op_id/report
      GET /operations/:op_id/report/markdown
      POST /operations/:op_id/recon
    vuln
      GET /vuln/cve/:cve_id
      GET /vuln/search?keyword=&limit=
    kb
      GET /kb/search?q=&limit=
      GET /kb/:id
      GET /kb/category/:category
```

---

## POST /operations 完整參數

```mermaid
graph LR
    subgraph Request Body
        N[name: String\n操作名稱 可選]
        IP[target_ip: String\n目標 IP 可選]
        HN[target_hostname: String\n目標 hostname 可選]
        MODE[mode: OperationMode\nnormal 預設\noperator_override]
        OT[operator_techniques: Vec String\nmode=override 時必填]
        OR[override_reason: String\n記錄覆蓋原因]
    end

    subgraph Response
        OID[op_id: UUID]
        NM[name: String]
        IID[iter_id: UUID]
        FC[facts_collected: usize\n本輪新增]
        TF[total_facts: usize\n累計]
        TIP[target_ip: String]
        MD[mode: String\nnormal / operator_override]
    end
```

---

## 典型操作流程

```mermaid
flowchart TD
    A[POST /operations\ntarget_ip + mode] --> B{OODA 執行}
    B --> C{Decide 結果}
    C -->|approved=true\nrisk ≤ 0.80| D[ACT 執行技術]
    C -->|approved=false\nrisk > 0.80| E[等待人類審批]
    E --> F[POST /operations/:op_id/approve\napproved_by: team_lead]
    F --> G[OODA 再跑一輪\nDecide 讀 human_approved fact\n直接批准]
    G --> D
    D --> H[GET /operations/:op_id/facts\n查看收集的 facts]
    H --> I{需要再跑一輪？}
    I -->|是| J[POST /operations/:op_id/iterate]
    J --> H
    I -->|否| K[GET /operations/:op_id/brief\n生成作戰簡報]
    K --> L[GET /operations/:op_id/report\n生成滲透測試報告]
    L --> M[GET /operations/:op_id/c5isr\nC5ISR 六域評估]

    B --> N{需要自動循環？}
    N -->|是| O[POST /operations/:op_id/scheduler/start\ninterval_secs: 60]
    O --> P[DELETE /operations/:op_id/scheduler/stop]
```

---

## 認證

```
ATHENA_API_TOKEN 環境變數未設定 → 所有請求免認證
ATHENA_API_TOKEN=<token> 已設定 → 需帶 Authorization: Bearer <token>
/api/health 永遠免認證
```
