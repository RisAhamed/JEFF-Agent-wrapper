# JEFF Agent Wrapper

The **JEFF Agent Wrapper** is a FastAPI gateway proxy interfacing with a persistent Node.js OpenAI agent sidecar. It manages cross-origin access (CORS), handles sliding-session memory, enforces rolling token caps, and parses structured data to generate downloadable PDF and Excel reports.

- **Production API Playground**: [https://jeff-agent-wrapper.onrender.com/](https://jeff-agent-wrapper.onrender.com/)

---

## What Changed

1. **Robust Double-Route Matching (Trailing Slashes)**:
   - Configured stacked route decorators for all main endpoints (supporting both `/chat` and `/chat/`, `/export/xlsx` and `/export/xlsx/`, etc.). This stops HTTP clients from encountering `GET`-redirect degradation and returning 405 errors.
2. **Self-Documenting GET Fallbacks**:
   - Implemented custom `GET` exception handlers for POST-only endpoints. If someone tries to open the endpoints directly in a web browser, they receive clear JSON instructions on the required body structure rather than a generic 405 error.
3. **Automated Dual-Process Launcher**:
   - Integrated a startup wrapper (`start.sh`) that spins up the TypeScript-compiled sidecar on `127.0.0.1:3000` (internal only) and binds the FastAPI app to the public port.
4. **Session Sliding Memory Expiry (TTL)**:
   - Configured an automatic 2-hour inactivity cleanup window for message histories.
5. **Pro Token Quota System**:
   - Set a rolling 24-hour limit of 150,000 tokens for Pro users, returning limit and remaining token stats in response headers.

---

## Core Features (Fully Functional)

- **Real-Time Streaming**: Delivers token-by-token text streams over TCP via Line-Delimited JSON (NDJSON) chunks.
- **Dynamic Exports**: Converts structured data JSON arrays or raw text into format-aligned reports (.xlsx and .pdf).
- **Guardrail Protection**: Moderates user queries against PII leak, NSFW, and prompt injection tripwires, automatically rerouting flagged prompts to a restricted Informer agent.

---

## How to Test

### 1. Interactive Interface
You can load the playground and converse with the agent directly in your web browser:
👉 [https://jeff-agent-wrapper.onrender.com/](https://jeff-agent-wrapper.onrender.com/)

---

### 2. "Gold" Test Prompts & API Commands

Here are the specific test inputs used to verify streaming, reasoning, and document generation:

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

#### B. Streaming Chat Request ("Gold Prompt" for Campaign Builder Mode)
**Prompt Input:** `"I want to launch a SaaS startup, give me a quick campaign hook."`
```bash
curl -X POST https://jeff-agent-wrapper.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I want to launch a SaaS startup, give me a quick campaign hook.", "mode": "campaign_builder"}'
```
*Expected Behavior:*
- Response headers return `X-Tokens-Remaining` (e.g. `149810`) and `X-Session-Id`.
- Response body streams campaign content word-by-word.

#### C. Spreadsheet Export Verification (POST /export/xlsx)
**Payload Data:** Passing structured revenue and expense metrics.
```bash
curl -X POST https://jeff-agent-wrapper.onrender.com/export/xlsx \
  -H "Content-Type: application/json" \
  -d '{"payload": {"summary": "Q1 Financial Projection", "rows": [{"month": "Jan", "revenue": 10000, "burn": 4000}, {"month": "Feb", "revenue": 12000, "burn": 4500}, {"month": "Mar", "revenue": 15000, "burn": 5000}]}, "filename": "financial-projection"}' \
  --output financial-projection.xlsx
```
*Expected Result:* Successfully downloads `financial-projection.xlsx` containing formatted columns with the specified financial figures.

#### D. PDF Report Export Verification (POST /export/pdf)
**Payload Data:** Passing structured textual analysis or project briefs.
```bash
curl -X POST https://jeff-agent-wrapper.onrender.com/export/pdf \
  -H "Content-Type: application/json" \
  -d '{"payload": {"title": "Campaign Launch Plan", "sections": [{"header": "Audience", "text": "Tech founders and solo builders."}, {"header": "Budget", "text": "Targeting $2,000 monthly burn."}]}, "filename": "launch-plan"}' \
  --output launch-plan.pdf
```
*Expected Result:* Successfully generates and downloads a clean, styled `launch-plan.pdf` document.

#### E. GET Route Fallback Check
Verify that requesting `/chat` without `POST` returns the descriptive developer instructions:
```bash
curl -X GET https://jeff-agent-wrapper.onrender.com/chat
```
*Expected Response:*
```json
{
  "detail": "Method Not Allowed. The /chat endpoint requires a POST request with a JSON payload (e.g., {'message': '...', 'mode': '...', 'session_id': '...'})."
}
```
