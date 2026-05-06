import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
from pathlib import Path
from main import AgentSession

app = FastAPI(title="Sentry Agentic API")

# Create downloads dir and mount as static files
_DOWNLOADS_DIR = Path("/Users/sarvpriyaadarsh/ollama-agent/downloads")
_DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/downloads", StaticFiles(directory=str(_DOWNLOADS_DIR)), name="downloads")

# Global session store
sessions: Dict[str, AgentSession] = {}

# Enable CORS for local Swift app connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    model: str = "gemma4:latest"

@app.post("/chat")
async def trigger_chat(request: ChatRequest):
    """
    Processes a chat turn using a stateful agent session.
    """
    if not request.message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    # Retrieve or create session
    if request.session_id not in sessions:
        sessions[request.session_id] = AgentSession(model=request.model)
    
    session = sessions[request.session_id]
    
    # Update model if requested (lazy update)
    if session.model != request.model:
        sessions[request.session_id] = AgentSession(model=request.model)
        session = sessions[request.session_id]

    try:
        # Run the turn (for the API, we currently auto-deny risky tools unless we add a callback mechanism)
        response = await session.run_turn(request.message)
        return {
            "status": "success",
            "response": response,
            "session_id": request.session_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
