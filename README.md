# Jeff AI Agent — FastAPI Backend (Persistent Node.js Sidecar)

This directory contains a FastAPI wrapper that serves the official JustStartUP Jeff Agent workflow.

## What's Done
- **Persistent Node.js Sidecar:** Switched from spawning a subprocess per request to a persistent Node.js Express server (`server.ts`) that runs alongside the FastAPI app, drastically reducing latency.
- **Real Streaming:** Replaced the simulated chunking logic with true token streaming using the `@openai/agents` SDK's `runner.runStreamed()`, which pipes real tokens via HTTP chunked transfer to FastAPI.
- **Session Memory:** Re-implemented LangChain's `InMemoryChatMessageHistory` keyed by `session_id`, restoring multi-turn conversational capabilities.
- **Mode Update:** Renamed "Pitch Deck" to "Campaign Builder" across the frontend tab, mode validation logic, and agent contextual prompts.
- **File Export Features:** Added `/export/xlsx` and `/export/pdf` endpoints generating downloadable structured files using `openpyxl` and `reportlab`.
- **Token Tracking (24-hr Limits):** Added a system to intercept the final usage block from the agent stream, track rolling 24-hour token totals (defaulting to 150k limit), and returning `429 Too Many Requests` alongside `X-Tokens-Remaining` and `X-Tokens-Reset` headers.
- **Production Build Fix:** Added TS-execution dependencies properly into `dependencies` instead of `devDependencies`, and configured FastAPI to spawn `npx.cmd tsx server.ts` so Render correctly installs and executes the TS sidecar.

## What's Pending
- Replace in-memory token tracking and session storage with Redis for robust production clustering.
- Integrate the frontend UI to display `X-Tokens-Remaining` quota and add "Export to Excel/PDF" buttons natively in the chat interface.

## What's Known-Broken
- N/A at the moment. All targeted endpoints have been locally simulated and proxy properly.

## Testing Performed
- **Live Local Setup:** Booted the environment via `uvicorn main:app --port 8000`. Verified that `server.ts` spun up silently on port `3000`.
- **Mode Validation:** Sent POST requests to `/chat` with invalid modes (e.g. `invalid_mode`) and verified it returned HTTP 422. Sent valid requests with `campaign_builder`.
- **Streaming:** Sent multi-turn cURL requests and watched tokens stream natively. Verified tokens accumulate and memory holds context of past questions.
- **Token Limits:** Triggered multiple requests, monitored the headers (`X-Tokens-Remaining`), and confirmed that the threshold resets as designed.
- **Exports:** Triggered `/export/xlsx` and `/export/pdf` using mock string content and verified the binary files download cleanly and aren't corrupted.

## Setup Instructions

### 1. Prerequisites
- **Node.js** (v18+) & **npm**
- **Python** (3.11+)

### 2. Environment Variables
Create a `.env` file in this directory and populate it with your OpenAI API key:

```env
OPENAI_API_KEY=sk-proj-YOUR_API_KEY_HERE
```

### 3. Install Dependencies
**Install Node Dependencies:**
```bash
npm install
```

**Install Python Dependencies:**
```bash
pip install -r requirements.txt
```

## Running the Application

To run the application locally on port 8000 (which will automatically start the sidecar):

```bash
uvicorn main:app --port 8000
```

Then visit `http://localhost:8000` to interact with the Jeff UI frontend.
