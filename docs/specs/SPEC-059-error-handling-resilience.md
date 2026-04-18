# SPEC-059: Error Handling Resilience

> Cross-cutting error handling hardening across backend and frontend.

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-059 |
| **Related ADR** | N/A (no architectural change) |
| **Estimated Complexity** | Medium |
| **HITL Level** | minimal |

---

## Goal

Harden error handling across the entire Athena codebase to eliminate crash risks,
silent failures, and resource leaks. Ensure all error paths log diagnostics,
release resources, and surface actionable feedback to users.

---

## Scope

### Backend (6 files)

| File | Change |
|------|--------|
| `backend/app/main.py` | Global exception handler with structured logging |
| `backend/app/routers/operations.py` | Replace bare `except` with specific catches + logging |
| `backend/app/routers/terminal.py` | Add timeout and cleanup for terminal sessions |
| `backend/app/services/engine_router.py` | Guard engine dispatch with fallback + logging |
| `backend/app/services/initial_access_engine.py` | Wrap SSH/credential flows with proper cleanup |
| `backend/app/services/ooda_controller.py` | Add resilient LLM fallback for Orient phase |

### Frontend (8 files)

| File | Change |
|------|--------|
| `frontend/src/components/ErrorBoundary.tsx` | New generic ErrorBoundary with i18n labels prop |
| `frontend/src/app/client-shell.tsx` | Wrap app shell in ErrorBoundary with translated labels |
| `frontend/src/contexts/OperationContext.tsx` | Guard context initialization errors |
| `frontend/src/contexts/ToastContext.tsx` | Prevent toast queue overflow |
| `frontend/src/hooks/useGlobalAlerts.ts` | Add error handling for WebSocket alert parsing |
| `frontend/src/hooks/useTerminal.ts` | Add connection error recovery |
| `frontend/src/hooks/useVulns.ts` | Guard against malformed API responses |
| `frontend/messages/{en,zh-TW}.json` | Add `Common.errorBoundary*` i18n keys |

---

## Changes Summary

### 1. Backend Error Handling

- All `except Exception` blocks now include `logger.exception()` or `logger.error()`
- No silent `pass` in catch blocks
- f-string SQL patterns validated against column whitelist
- Engine router has fallback when engine lookup fails

### 2. Frontend Error Boundary (New Component)

- Generic `ErrorBoundary` class component wrapping React's `componentDidCatch`
- Accepts optional `labels` prop for i18n (class components cannot use hooks)
- Accepts optional `fallback` prop for custom error UI
- Retry button resets error state and re-renders children
- Falls back to hardcoded English when no labels provided

### 3. Frontend Hook Resilience

- All `.catch()` handlers log errors (no empty catches)
- Context providers guard against initialization failures
- WebSocket message parsing wrapped in try-catch

---

## Verification

| Check | Command |
|-------|---------|
| TypeScript compilation | `cd frontend && npx tsc --noEmit` |
| Frontend tests | `cd frontend && npx vitest run` |
| Backend tests | `cd backend && python3 -m pytest tests/ -q` |
| i18n schema consistency | `cd frontend && npx vitest run src/test/i18n-schema.test.ts` |
| Grep: no silent catches (BE) | `grep -rn "except Exception" backend/app/ \| grep -v "logger\|log\.\|logging"` |
| Grep: no silent catches (FE) | `grep -rn "catch(() =>" frontend/src/ \| grep -v "console\.\|warn\|error"` |

---

## Done When

- [ ] All 14 error handling fixes applied (6 BE + 8 FE files)
- [ ] ErrorBoundary i18n via labels prop (no hardcoded English in production path)
- [ ] ErrorBoundary unit tests pass (4 cases)
- [ ] i18n keys added to both en.json and zh-TW.json
- [ ] Full-project grep scan confirms no remaining silent catches
- [ ] `npx tsc --noEmit` passes
- [ ] `npx vitest run` passes
