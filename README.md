# Jeff AI Agent — FastAPI Backend (TypeScript Wrapper)

This directory contains a FastAPI wrapper that serves the official JustStartUP Jeff Agent workflow. Because the core agent is authored using the `@openai/agents` SDK in TypeScript, this Python application acts as a bridge.

## Architecture

1. **Frontend**: The dark-themed chat interface (`jeff-ui.html`).
2. **FastAPI Application (`main.py`)**: Accepts HTTP POST requests at `/chat` and streams tokens back to the client.
3. **TypeScript CLI Bridge (`wrapper.ts`)**: A minimal script that pipes standard input into the `runWorkflow` function and prints JSON to standard output.
4. **Agent Engine (`agent.ts`)**: Contains the core Jeff agent and Informer agent setups leveraging `@openai/agents` and `@openai/guardrails`. The model has been upgraded to `o3-mini` for advanced reasoning capabilities.

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
You need to install dependencies for both Python (FastAPI) and Node.js (Agent Engine).

**Install Node Dependencies:**
```bash
npm install
```

**Install Python Dependencies:**
```bash
pip install -r requirements.txt
```

## Running the Application

To run the application locally on port 8000:

```bash
uvicorn main:app --port 8000 --reload
```

Then visit `http://localhost:8000` to interact with the Jeff UI frontend.

## Deployment to Render

This project is configured to deploy effortlessly to [Render.com](https://render.com) using the included `render.yaml` blueprint. The blueprint automatically runs both `npm install` and `pip install`, and spins up the FastAPI server natively binding to the required port.

1. Connect your GitHub repo to Render using the "Blueprint" flow.
2. In the Render Dashboard under **Environment**, add the `OPENAI_API_KEY` secret.
3. Render will deploy the application automatically.
