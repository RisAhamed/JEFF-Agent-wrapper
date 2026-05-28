import os
import json
import asyncio
import time
import subprocess
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
import httpx
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
import io
from openpyxl import Workbook
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

load_dotenv()

app = FastAPI(
    title="Jeff AI Agent API",
    description="FastAPI endpoint wrapping the persistent TypeScript agent sidecar.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://juststrtup.com", "http://localhost", "http://127.0.0.1", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Start Node sidecar in the background
node_process = None

@app.on_event("startup")
async def startup_event():
    global node_process
    npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
    node_process = subprocess.Popen(
        [npx_cmd, "tsx", "server.ts"],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    # Wait for the node server to start
    await asyncio.sleep(3)

@app.on_event("shutdown")
def shutdown_event():
    global node_process
    if node_process:
        node_process.terminate()

class ChatRequest(BaseModel):
    message: str
    mode: str
    session_id: str = "default_session"

class ExportRequest(BaseModel):
    content: str
    filename: str = "export"

VALID_MODES = ["investor", "business_model", "customer", "campaign_builder", "financial"]

session_store: dict[str, InMemoryChatMessageHistory] = {}
token_usage_store: dict[str, dict] = {} # user/session -> {"tokens": int, "reset_at": float}
TOKEN_LIMIT = 150000
TOKEN_WINDOW = 24 * 3600

def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in session_store:
        session_store[session_id] = InMemoryChatMessageHistory()
    return session_store[session_id]

def check_token_limit(session_id: str):
    now = time.time()
    # NOTE: In production, this should be stored in Redis
    usage = token_usage_store.get(session_id, {"tokens": 0, "reset_at": now + TOKEN_WINDOW})
    if now > usage["reset_at"]:
        usage = {"tokens": 0, "reset_at": now + TOKEN_WINDOW}
        token_usage_store[session_id] = usage
    return usage

def update_token_limit(session_id: str, prompt_tokens: int, completion_tokens: int):
    usage = check_token_limit(session_id)
    usage["tokens"] += (prompt_tokens + completion_tokens)
    token_usage_store[session_id] = usage

@app.post("/chat")
async def chat(request: ChatRequest, response: Response):
    if request.mode not in VALID_MODES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid mode '{request.mode}'. Must be one of: {', '.join(VALID_MODES)}"
        )
    
    session_id = request.session_id
    usage = check_token_limit(session_id)
    
    if usage["tokens"] >= TOKEN_LIMIT:
        response.headers["Retry-After"] = str(int(usage["reset_at"] - time.time()))
        raise HTTPException(status_code=429, detail="Token limit exceeded for the last 24 hours.")

    chat_history = get_session_history(session_id)
    
    # Format messages for the Node sidecar
    messages = []
    for msg in chat_history.messages:
        if isinstance(msg, HumanMessage):
            messages.append({"role": "user", "content": [{"type": "input_text", "text": msg.content}]})
        elif isinstance(msg, AIMessage):
            messages.append({"role": "assistant", "content": [{"type": "text", "text": msg.content}]})

    messages.append({"role": "user", "content": [{"type": "input_text", "text": request.message}]})

    payload = {
        "messages": messages,
        "mode": request.mode
    }

    async def stream_response():
        full_response = ""
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream("POST", "http://127.0.0.1:3000/chat", json=payload) as r:
                    if r.status_code != 200:
                        error_text = await r.aread()
                        yield f"Error from sidecar: {r.status_code} {error_text.decode()}"
                        return
                    async for chunk in r.aiter_text():
                        if "__USAGE__:" in chunk:
                            parts = chunk.split("__USAGE__:")
                            text_part = parts[0]
                            usage_part = parts[1]
                            
                            if text_part:
                                full_response += text_part
                                yield text_part
                            
                            try:
                                usage_data = json.loads(usage_part.strip())
                                update_token_limit(
                                    session_id, 
                                    usage_data.get("prompt_tokens", 0), 
                                    usage_data.get("completion_tokens", 0)
                                )
                            except Exception as e:
                                pass
                        else:
                            full_response += chunk
                            yield chunk
            
            # Save to LangChain memory
            chat_history.add_message(HumanMessage(content=request.message))
            chat_history.add_message(AIMessage(content=full_response))
        except Exception as e:
            yield f"Stream failed: {e}"

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "X-Tokens-Remaining": str(max(0, TOKEN_LIMIT - usage["tokens"])),
        "X-Tokens-Reset": str(int(usage["reset_at"]))
    }
    return StreamingResponse(stream_response(), media_type="text/plain", headers=headers)

@app.post("/export/xlsx")
async def export_xlsx(request: ExportRequest):
    wb = Workbook()
    ws = wb.active
    ws.title = "Export"
    
    lines = request.content.split("\n")
    for i, line in enumerate(lines, start=1):
        ws.cell(row=i, column=1, value=line)
        
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={request.filename}.xlsx"}
    )

@app.post("/export/pdf")
async def export_pdf(request: ExportRequest):
    output = io.BytesIO()
    c = canvas.Canvas(output, pagesize=letter)
    
    y = 750
    for line in request.content.split("\n"):
        if y < 50:
            c.showPage()
            y = 750
        c.drawString(30, y, line[:100]) # Trim to fit page width roughly
        y -= 15
        
    c.save()
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={request.filename}.pdf"}
    )

@app.post("/clear")
async def clear_session(request: Request):
    data = await request.json()
    session_id = data.get("session_id")
    if session_id in session_store:
        del session_store[session_id]
    return {"status": "cleared", "session_id": session_id}

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Jeff AI Agent"}

@app.get("/")
async def serve_frontend():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ui_path = os.path.join(base_dir, "jeff-ui.html")
    if os.path.exists(ui_path):
        return FileResponse(ui_path)
    return {"message": "Jeff AI Agent API is running."}
