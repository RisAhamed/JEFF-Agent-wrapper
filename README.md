# JEFF Agent Wrapper

This repository contains the FastAPI wrapper around the persistent Node.js OpenAI agent sidecar.

- **Live Deployment Link**: [https://jeff-agent-wrapper.onrender.com/](https://jeff-agent-wrapper.onrender.com/)

---

## 1. What Was Wrong

1. **Sidecar Process Crash in Production**: 
   - Render only launched the Python FastAPI server (`uvicorn main:app`). The TypeScript/Node.js sidecar was never started.
   - The fallback path in `main.py` tried to spawn the sidecar using `tsx` (which is in `devDependencies`), triggering an `exit code 127` (command not found) crash.
2. **Generic 405 Method Not Allowed**:
   - Hitting `/chat` or export routes using `GET` (such as opening the URL directly in a browser address bar) returned a generic `{"detail":"Method Not Allowed"}`.
   - Additionally, requests with trailing slashes (e.g. `/chat/`) triggered HTTP-to-HTTPS redirects, causing some HTTP clients to convert the request method to `GET` and fail with a 405 error.

---

## 2. What We Did & How We Fixed It

1. **Dual-Process Launcher (`start.sh`)**:
   - Created `start.sh` to run the compiled Node sidecar in the background (`node dist/server.js &`) and then execute the FastAPI server in the foreground.
   - Changed the start command in `render.yaml` to `bash start.sh`.
   - Bound the Node.js Express sidecar to `127.0.0.1` so it remains internal-only.
2. **Trailing-Slash Routing Support**:
   - Registered stacked decorators on all endpoints (e.g., both `@app.post("/chat")` and `@app.post("/chat/")`) to process both URLs natively without redirection.
3. **Friendly GET Error Handlers**:
   - Added specific `GET` route handlers for the POST-only endpoints (`/chat`, `/export/xlsx`, `/export/pdf`) that raise a helpful exception indicating that a `POST` request with JSON payload is required.
4. **Session TTL (2-Hour Expiry)**:
   - Added `session_timestamps` to track user accesses in `main.py`. Any sessions inactive for more than 2 hours are automatically cleaned up in `get_session_history()`.

---

## 3. Current Live Deployment Features

- **Real Token Streaming**: Token-by-token streaming is enabled on the `/chat` route.
- **Modes Supported**: `investor`, `business_model`, `customer`, `campaign_builder` (renamed from pitch_deck), and `financial`.
- **Pro Quota System**: A rolling 24-hour limit of 150,000 tokens is tracked and returned in the HTTP response headers:
  - `X-Session-Id`
  - `X-Tokens-Limit`
  - `X-Tokens-Remaining`
  - `X-Tokens-Reset`
- **File Exports**: `/export/xlsx` (Excel using openpyxl) and `/export/pdf` (PDF using reportlab) are fully active.

---

## 4. How to Test

### Live Interface
Visit the root URL in a web browser to use the interactive playground:
👉 [https://jeff-agent-wrapper.onrender.com/](https://jeff-agent-wrapper.onrender.com/)

### Smoke Tests & curl Output

#### 1. Check Service Health
```bash
curl -X GET https://jeff-agent-wrapper.onrender.com/health
```
**Response:**
```json
{
  "status": "ok",
  "service": "Jeff AI Agent",
  "sidecar": "ok"
}
```

#### 2. Test Chat Endpoint (Returns Streamed Response)
```bash
curl -X POST https://jeff-agent-wrapper.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello Jeff", "mode": "campaign_builder"}'
```
**Response Headers:**
```http
HTTP/1.1 200 OK
Content-Type: text/plain; charset=utf-8
X-Session-Id: default_session
X-Tokens-Limit: 150000
X-Tokens-Remaining: 150000
X-Tokens-Reset: 1779951600
```
*(Response body streams the tokens real-time)*

#### 3. Test Direct GET Browser Message
```bash
curl -X GET https://jeff-agent-wrapper.onrender.com/chat
```
**Response:**
```json
{
  "detail": "Method Not Allowed. The /chat endpoint requires a POST request with a JSON payload (e.g., {'message': '...', 'mode': '...', 'session_id': '...'})."
}
```
