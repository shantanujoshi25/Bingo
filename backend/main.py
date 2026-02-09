from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
import json
from dotenv import load_dotenv
from datetime import datetime

from redis_client import redis, check_redis_connection
from auth import verify_alien_token
from lobby import (
    get_or_create_global_lobby,
    add_player_to_lobby,
    submit_grid as lobby_submit_grid,
    get_game_status as lobby_get_game_status,
    verify_claim,
)

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

# --- Pydantic Models ---
class JoinLobbyRequest(BaseModel):
    alien_id: str

class SubmitGridRequest(BaseModel):
    alien_id: str
    grid: List[List[int]]

class ClaimRequest(BaseModel):
    alien_id: str
    highlighted_numbers: List[int]

# --- API Endpoints ---

@app.get("/health")
async def health_check():
    redis_connected = await check_redis_connection()
    return {
        "status": "healthy",
        "redis_connected": redis_connected,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/game/join")
async def join_lobby(request: JoinLobbyRequest, alien_id: str = Depends(verify_alien_token)):
    try:
        lobby_info = await get_or_create_global_lobby()

        if lobby_info["in_progress"]:
            return {
                "lobby_id": lobby_info["lobby_id"],
                "status": "in_progress",
                "player_count": 0,
                "pot": 0,
            }

        result = await add_player_to_lobby(lobby_info["lobby_id"], request.alien_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/game/{lobby_id}/submit-grid")
async def submit_grid(lobby_id: str, request: SubmitGridRequest, alien_id: str = Depends(verify_alien_token)):
    try:
        result = await lobby_submit_grid(lobby_id, request.alien_id, request.grid)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/game/{lobby_id}/status")
async def get_game_status(lobby_id: str, alien_id: str = Depends(verify_alien_token)):
    try:
        return await lobby_get_game_status(lobby_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/game/{lobby_id}/claim")
async def claim_bingo(lobby_id: str, request: ClaimRequest, alien_id: str = Depends(verify_alien_token)):
    try:
        result = await verify_claim(lobby_id, request.alien_id, request.highlighted_numbers)
        if not result["valid"]:
            raise HTTPException(status_code=400, detail=result)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/webhooks/payment")
async def payment_webhook(request: Request):
    body = await request.body()
    payload = json.loads(body)

    invoice_id = payload.get("invoice")
    if not invoice_id:
        raise HTTPException(status_code=400, detail="Missing invoice ID")

    invoice_data = await redis.hgetall(f"invoice:{invoice_id}")
    if not invoice_data:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if payload.get("status") == "finalized":
        lobby_id = invoice_data["lobby_id"]
        amount = int(invoice_data["amount"])
        await redis.hset(f"invoice:{invoice_id}", "status", "finalized")
        await redis.hincrby(f"lobby:{lobby_id}", "pot", amount)

    return {"success": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
