from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
from dotenv import load_dotenv
from datetime import datetime

from redis_client import redis, check_redis_connection
from auth import verify_alien_token

load_dotenv()

app = FastAPI()

# CORS Middleware
origins = [
    os.getenv("ALLOWED_ORIGINS", "http://localhost:5173"),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models (from Phase 1 doc) ---
class InvoiceRequest(BaseModel):
    alien_id: str
    buy_in_amount: int
    lobby_id: str

class JoinLobbyRequest(BaseModel):
    alien_id: str
    buy_in_amount: int

class NumberSelectionRequest(BaseModel):
    alien_id: str
    numbers: List[int]

class GridArrangementRequest(BaseModel):
    alien_id: str
    grid: List[List[int]]

class ClaimRequest(BaseModel):
    alien_id: str

# --- API Endpoints ---

@app.get("/health")
async def health_check():
    redis_connected = await check_redis_connection()
    return {
        "status": "healthy",
        "redis_connected": redis_connected,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/invoices")
async def create_invoice(request: InvoiceRequest, alien_id: str = Depends(verify_alien_token)):
    # Placeholder
    return {"message": "Invoice creation endpoint"}

@app.post("/api/game/join")
async def join_lobby(request: JoinLobbyRequest, alien_id: str = Depends(verify_alien_token)):
    # Placeholder
    return {"message": "Join lobby endpoint"}

@app.post("/api/game/{lobby_id}/numbers/select")
async def submit_numbers(lobby_id: str, request: NumberSelectionRequest, alien_id: str = Depends(verify_alien_token)):
    # Placeholder
    return {"message": f"Submit numbers for lobby {lobby_id}"}

@app.post("/api/game/{lobby_id}/numbers/arrange")
async def submit_grid(lobby_id: str, request: GridArrangementRequest, alien_id: str = Depends(verify_alien_token)):
    # Placeholder
    return {"message": f"Submit grid for lobby {lobby_id}"}

@app.get("/api/game/{lobby_id}/status")
async def get_game_status(lobby_id: str, alien_id: str = Depends(verify_alien_token)):
    # Placeholder
    return {"message": f"Get status for lobby {lobby_id}"}

@app.post("/api/game/{lobby_id}/claim")
async def claim_bingo(lobby_id: str, request: ClaimRequest, alien_id: str = Depends(verify_alien_token)):
    # Placeholder
    return {"message": f"Claim bingo for lobby {lobby_id}"}

@app.post("/api/webhooks/payment")
async def payment_webhook(request: dict):
    # Placeholder - No auth on this endpoint, but will have signature verification in a later phase
    return {"message": "Payment webhook endpoint"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
