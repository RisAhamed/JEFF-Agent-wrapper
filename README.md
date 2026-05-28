# Jeff AI Agent FastAPI Wrapper

This `day-1` app wraps the TypeScript Jeff agent workflow with FastAPI for the WordPress integration.

## What Is Done

- `POST /chat` validates mode, restores per-session chat history, checks guardrails, routes to Jeff or Informer, and returns a `text/plain` streaming response.
- The Node agent runs as a persistent sidecar instead of a subprocess per request.
- TypeScript is compiled at build time into `dist/`, so Render no longer depends on runtime `tsx`.
- Streaming uses `@openai/agents` streaming events from the sidecar and forwards real token deltas through FastAPI.
- `pitch_deck` has been replaced with `campaign_builder` in validation, UI tabs, welcome text, and mode context.
- `POST /export/xlsx` and `POST /export/pdf` generate files server-side from structured payloads.
- A rolling 24-hour in-memory token cap is enforced per `user_id` or `session_id`, defaulting to `150000`.
- CORS is restricted to JustStartUP domains plus local development origins.
- Jeff and Informer models are configurable with `JEFF_AGENT_MODEL` and `INFORMER_AGENT_MODEL`; defaults are set to `gpt-3.5-turbo` so the current unverified org can return working chat output.

## Pending

- Replace in-memory session and token stores with Redis before production scale-out or multi-instance Render deployment.
- Deploy the updated Render blueprint and paste the final public URL into the submission.
- Raj still owns the Campaign Builder platform/system prompt. The UI currently sends `mode: "campaign_builder"` plus a lightweight mode context saying the user wants campaign brief, launch messaging, channel plan, and content-outline help.

## Known Broken

- Token quota is process-local until Redis is added. A Render restart clears counters and session memory.
- Response headers show quota remaining before the current streamed run. The run usage is recorded for the next request after streaming completes.
- Hosted tools are disabled in the default local agent runtime because the current organization rejects the previous hosted-tool/model combinations. Re-enable tools after model/tool access is verified.

## Environment Variables

Copy `.env.example` to `.env` locally:

```env
OPENAI_API_KEY=
JEFF_WORKFLOW_ID=
JEFF_AGENT_MODEL=gpt-3.5-turbo
INFORMER_AGENT_MODEL=gpt-3.5-turbo
CORS_ORIGINS=https://juststrtup.com,http://juststrtup.com,https://www.juststrtup.com
PRO_TOKEN_LIMIT=150000
NODE_SIDECAR_URL=http://127.0.0.1:3000
SIDECAR_PORT=3000
START_NODE_SIDECAR=true
NODE_VERSION=22.16.0
```

Do not commit real API keys.

## Local Setup

```bash
npm install
npm run build
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```

FastAPI starts the compiled Node sidecar automatically. Open `http://127.0.0.1:8000` for the full-screen Jeff UI.

## API Contract

```http
POST /chat
Content-Type: application/json
```

```json
{
  "message": "string",
  "mode": "investor | business_model | customer | campaign_builder | financial",
  "session_id": "string",
  "user_id": "optional string"
}
```

Response: `text/plain` chunked stream.

Quota headers:

- `X-Tokens-Limit`
- `X-Tokens-Remaining`
- `X-Tokens-Reset`
- `Retry-After` on `429`

Export endpoints:

- `POST /export/xlsx`
- `POST /export/pdf`

Both accept:

```json
{
  "payload": { "title": "Campaign Brief", "rows": [] },
  "filename": "campaign-brief",
  "title": "Campaign Brief"
}
```

## Render Deployment

The included `render.yaml` runs:

```bash
pip install -r requirements.txt
npm ci --include=dev
npm run build
```

Start command:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Set these Render environment variables:

- `OPENAI_API_KEY`
- `JEFF_WORKFLOW_ID` if available
- `JEFF_AGENT_MODEL`
- `INFORMER_AGENT_MODEL`
- `CORS_ORIGINS`
- `PRO_TOKEN_LIMIT`
- `NODE_VERSION=22.16.0`

## Tested

- `npm run build`
- `python -m py_compile main.py test_endpoints.py`
- Local smoke test with the workspace venv:
  - `GET /health`
  - invalid `POST /chat` returns `422`
  - `POST /export/xlsx` returns an Excel file
  - `POST /export/pdf` returns a PDF file
- Browser UI smoke test with `npx agent-browser`:
  - opened `http://127.0.0.1:8000`
  - selected `Campaign Builder`
  - sent a message
  - received a visible Jeff response plus Excel/PDF buttons

I did not redeploy Render from this machine, and I did not claim the live `/chat` URL is fixed until the updated blueprint is deployed.
