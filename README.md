# JEFF Agent Wrapper

The **JEFF Agent Wrapper** is a FastAPI gateway proxy interfacing with a persistent Node.js OpenAI agent sidecar. It manages cross-origin access (CORS), handles sliding-session memory, enforces rolling token caps, and parses structured data to generate downloadable PDF and Excel reports.

- **Production API Playground**: [https://jeff-agent-wrapper.onrender.com/](https://jeff-agent-wrapper.onrender.com/)

---

## What Changed

### 1. Production tsx / MODULE_NOT_FOUND Fix
Moved away from subprocess + tsx entirely. TypeScript is now compiled to JS at build time (tsc). The `start.sh` launcher starts the compiled `dist/server.js` as a persistent Express sidecar on `127.0.0.1:3000` (internal only), then brings up `uvicorn` in the foreground. If `dist/server.js` doesn't exist at startup, the process raises a hard error immediately rather than silently failing mid-request.

### 2. Real Streaming Engine
The `asyncio.sleep(0.05)` word-split simulation is gone. The Node sidecar now uses `runner.run()` with `stream: true` (yielding `StreamedRunResult`) and emits newline-delimited JSON (`{ type: "token", text: "..." }`) as tokens arrive. FastAPI reads these line-by-line and forwards them to the client in real time via `StreamingResponse`. The user sees tokens as they are generated — not a pop-in after 10–30s.

### 3. Session Memory Restoration
`session_id` is no longer ignored. In-memory session history is keyed by `session_id`, passed to the sidecar on every request, and updated after each run. Sessions expire after 2 hours of inactivity. Flagged in the code that this needs Redis for multi-instance production.

### 4. Subprocess-per-request Elimination
There is no more `subprocess.Popen` on each `/chat` call. The Express sidecar stays alive for the lifetime of the Render dyno. FastAPI communicates with it over HTTP on localhost. Cold-start overhead is gone after the first dyno wake.

### 5. Pitch Deck → Campaign Builder Renaming
Renamed across the frontend tab label, mode validation list, and welcome message references. The value sent in the request body is now `campaign_builder`. The system prompt on the OpenAI platform remains managed by the client — the UI is sending the correct mode value ready for the updated agent instructions.

### 6. Excel and PDF Export Endpoints
- `POST /export/xlsx` — uses `openpyxl`, returns a formatted `.xlsx` file
- `POST /export/pdf` — uses `reportlab`, returns a styled `.pdf` file
The LLM generates structured JSON. These endpoints format it server-side. No binary generation from the model.

### 7. 24-hour Token Limits
Rolling 150,000 token cap per session. Tracked in-memory (flagged for Redis). On cap hit, returns HTTP 429 with `Retry-After` header. Every response includes `X-Tokens-Remaining` and `X-Tokens-Reset` headers. The frontend reads these and displays the remaining quota.

### 8. Frontend Modernization
`jeff-ui.html` now reads the streaming `ReadableStream` correctly, handles `422`/`429`/`500` with inline error messages (not browser alerts), shows the Campaign Builder tab, and displays a token quota indicator from response headers.

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
