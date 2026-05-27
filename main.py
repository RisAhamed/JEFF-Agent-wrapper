import os
import json
import subprocess
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

load_dotenv()

app = FastAPI(
    title="Jeff AI Agent API ",
    description="FastAPI endpoint wrapping the TypeScript agent.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    mode: str
    session_id: str | None = None

async def stream_words(text: str):
    for word in text.split(" "):
        yield word + " "
        await asyncio.sleep(0.05)

@app.post("/chat")
async def chat(request: ChatRequest):
    # Call the node script wrapped in tsx
    def run_node():
        process = subprocess.run(
            "npx tsx wrapper.ts",
            cwd=os.path.dirname(os.path.abspath(__file__)),
            input=json.dumps({"input_as_text": request.message}),
            capture_output=True,
            text=True,
            shell=True
        )
        return process

    loop = asyncio.get_running_loop()
    process = await loop.run_in_executor(None, run_node)

    if process.returncode != 0:
        try:
            err_data = json.loads(process.stderr)
            raise HTTPException(status_code=500, detail=err_data.get("error", process.stderr))
        except:
            raise HTTPException(status_code=500, detail=f"Process failed: {process.stderr or process.stdout}")

    try:
        # Search for JSON object in stdout (ignoring potential other console logs)
        stdout = process.stdout.strip()
        lines = stdout.splitlines()
        result_json = None
        for line in reversed(lines):
            try:
                result_json = json.loads(line)
                if "output_text" in result_json:
                    break
            except:
                continue
        
        if not result_json:
            result_json = json.loads(stdout)
            
        output_text = result_json.get("output_text", "")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse agent output. Output was: {process.stdout}")

    return StreamingResponse(
        stream_words(output_text), 
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Jeff AI Agent (TS Wrapper)"}

@app.get("/")
async def serve_frontend():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ui_path = os.path.join(base_dir, "jeff-ui.html")
    if os.path.exists(ui_path):
        return FileResponse(ui_path)
    return {"message": "Jeff AI Agent API is running."}
