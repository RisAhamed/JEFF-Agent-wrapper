# JEFF Agent Wrapper

The **JEFF Agent Wrapper** is a FastAPI gateway proxy designed to orchestrate and interface with a persistent Node.js agent execution sidecar. It manages cross-origin access (CORS), handles sliding-session memory, enforces rolling token caps, and parses structured data to generate downloadable PDF and Excel reports.

- **Production API Playground**: [https://jeff-agent-wrapper.onrender.com/](https://jeff-agent-wrapper.onrender.com/)

---

## System Overview & Features

### 1. Persistent Sidecar Integration
The application uses a dual-process runner (`start.sh`) that spins up the TypeScript-compiled sidecar on `127.0.0.1:3000` (internal only) and binds the FastAPI app to the public port.
- Communicates internally over HTTP on localhost, eliminating subprocess startup overhead on chat requests.
- Raises a hard error immediately during startup if `dist/server.js` compilation is missing.

### 2. Token-Streaming Engine
- Delivers real-time token-by-token text streams over TCP via Line-Delimited JSON (NDJSON) chunks.
- Reads sidecar events via `StreamingResponse` and streams directly to the frontend.

### 3. Session Sliding Memory (2-Hour TTL)
- Chat histories are keyed by `session_id` and preserved across requests.
- Sessions automatically expire and are cleaned up after **2 hours** of inactivity to optimize RAM usage.
- *Note:* In-memory storage is used for development; Redis is required for multi-instance production.

### 4. Mode Routing & Guardrail Pipeline
- Supports five modes: `investor`, `business_model`, `customer`, `campaign_builder`, and `financial`.
- Automatically scrubs and checks input prompts against active guardrails. Flagged inputs are automatically rerouted to a restrictive Informer agent.

### 5. Excel and PDF Export Endpoints
- Converts structured payload JSON or text arrays into downloadable reports server-side.
- **Excel (`POST /export/xlsx`)**: Uses `openpyxl` to compile data rows.
- **PDF (`POST /export/pdf`)**: Uses `reportlab` to construct styled flowable layouts.

### 6. 24-Hour Token Limit (150,000 Token Cap)
- Pro users are capped at a rolling **150,000 tokens per 24 hours**.
- Returns a standard `429 Too Many Requests` status with a `Retry-After` header when the cap is exceeded.
- Reports consumption and remaining limit balances in the HTTP headers (`X-Tokens-Remaining`, `X-Tokens-Reset`, `X-Session-Id`).

---

## How to Test

### 1. Live Playground
Interact with the frontend UI directly in your web browser:
👉 [https://jeff-agent-wrapper.onrender.com/](https://jeff-agent-wrapper.onrender.com/)

### 2. API Verification Commands

#### A. Health Check
```bash
curl -X GET https://jeff-agent-wrapper.onrender.com/health
```
*Expected Response:*
```json
{
  "status": "ok",
  "service": "Jeff AI Agent",
  "sidecar": "ok"
}
```

#### B. Streaming Chat Request (POST /chat)
**Test Input:** `"I want to launch a SaaS startup, give me a quick campaign hook."`
```bash
curl -X POST https://jeff-agent-wrapper.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I want to launch a SaaS startup, give me a quick campaign hook.", "mode": "campaign_builder"}'
```
*Expected Behavior:*
- Returns quota statistics headers (e.g. `X-Tokens-Remaining`, `X-Session-Id`).
- Streams real-time markdown text chunk-by-chunk.

#### C. Spreadsheet Export (POST /export/xlsx)
```bash
curl -X POST https://jeff-agent-wrapper.onrender.com/export/xlsx \
  -H "Content-Type: application/json" \
  -d '{"payload": {"summary": "Q1 Financial Projection", "rows": [{"month": "Jan", "revenue": 10000, "burn": 4000}, {"month": "Feb", "revenue": 12000, "burn": 4500}]}, "filename": "financial-projection"}' \
  --output financial-projection.xlsx
```
*Expected Result:* Downloads a valid Excel spreadsheet containing the formatted columns.

#### D. PDF Report Export (POST /export/pdf)
```bash
curl -X POST https://jeff-agent-wrapper.onrender.com/export/pdf \
  -H "Content-Type: application/json" \
  -d '{"payload": {"title": "Campaign Launch Plan", "sections": [{"header": "Audience", "text": "Tech builders."}]}, "filename": "launch-plan"}' \
  --output launch-plan.pdf
```
*Expected Result:* Generates and downloads a clean, styled PDF report.

#### E. GET Route Fallback
Verify the POST-only routes return descriptive developer feedback instead of generic 405 errors:
```bash
curl -X GET https://jeff-agent-wrapper.onrender.com/chat
```
*Expected Response:*
```json
{
  "detail": "Method Not Allowed. The /chat endpoint requires a POST request with a JSON payload (e.g., {'message': '...', 'mode': '...', 'session_id': '...'})."
}
```
