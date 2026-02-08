from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
from dotenv import load_dotenv
from datetime import datetime
import asyncio # New import
import json # New import

from redis_client import redis, check_redis_connection
from auth import verify_alien_token
from lobby import find_or_create_lobby, update_player_numbers, update_player_grid, start_lobby_monitor, check_state_transition # New import
from game_logic import validate_numbers_selection, validate_grid_arrangement, get_game_status_data, claim_bingo_logic, call_numbers_task # New import

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
    try:
        if request.alien_id != alien_id:
            raise HTTPException(status_code=403, detail="Unauthorized Alien ID")
        
        lobby_info = await find_or_create_lobby(request.alien_id, request.buy_in_amount)
        return lobby_info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.post("/api/game/{lobby_id}/numbers/select")
async def submit_numbers(lobby_id: str, request: NumberSelectionRequest, alien_id: str = Depends(verify_alien_token)):
    try:
        if request.alien_id != alien_id:
            raise HTTPException(status_code=403, detail="Unauthorized Alien ID")
        
        if not validate_numbers_selection(request.numbers):
            raise HTTPException(status_code=400, detail="Invalid number selection. Must be 9 unique numbers between 1-50.")
        
        # Check lobby status - should be 'forming'
        lobby_info = await redis.hgetall(f"lobby:{lobby_id}")
        if not lobby_info:
            raise HTTPException(status_code=404, detail="Lobby not found.")
        
        if lobby_info.get(b'status').decode('utf-8') != 'forming':
            raise HTTPException(status_code=400, detail="Numbers can only be selected during lobby formation.")

        await update_player_numbers(lobby_id, request.alien_id, request.numbers)
        return {"success": True, "message": "Numbers selected. Now arrange your grid."}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.post("/api/game/{lobby_id}/numbers/arrange")
async def submit_grid(lobby_id: str, request: GridArrangementRequest, alien_id: str = Depends(verify_alien_token)):
    try:
        if request.alien_id != alien_id:
            raise HTTPException(status_code=403, detail="Unauthorized Alien ID")
        
        # Retrieve player's selected numbers to validate grid against them
        player_data = await redis.hgetall(f"lobby:{lobby_id}:player:{request.alien_id}")
        if not player_data or not player_data.get(b'numbers'):
            raise HTTPException(status_code=400, detail="Please select your numbers first.")
        
        selected_numbers = json.loads(player_data[b'numbers'].decode('utf-8'))
        
        if not validate_grid_arrangement(selected_numbers, request.grid):
            raise HTTPException(status_code=400, detail="Invalid grid arrangement. Must be 3x3 with your selected numbers.")

        # Check lobby status - should be 'arranging' or 'forming' if not yet transitioned
        lobby_info = await redis.hgetall(f"lobby:{lobby_id}")
        if not lobby_info:
            raise HTTPException(status_code=404, detail="Lobby not found.")
        
        status = lobby_info.get(b'status').decode('utf-8')
        if status not in ['forming', 'arranging']: # Allow arranging even if still in forming and arrangement phase hasn't officially started
            raise HTTPException(status_code=400, detail="Grid arrangement can only be submitted during forming or arrangement phase.")

        await update_player_grid(lobby_id, request.alien_id, request.grid)
        
        # After a player submits their grid, check for state transition
        # This will trigger if all players have arranged their grids
        asyncio.create_task(check_state_transition(lobby_id))

        return {"success": True, "verified": True, "message": "Grid arrangement verified"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.get("/api/game/{lobby_id}/status")
async def get_game_status(lobby_id: str, alien_id: str = Depends(verify_alien_token)):
    try:
        # No direct alien_id check needed as get_game_status_data will return None if not found
        # and the token itself is already verified
        game_status = await get_game_status_data(lobby_id)
        
        if not game_status:
            raise HTTPException(status_code=404, detail="Lobby or game not found.")
        
        # Ensure the player requesting the status is part of the game
        if alien_id not in game_status.get('players', {}):
             raise HTTPException(status_code=403, detail="Not a participant of this game.")

        return game_status
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.post("/api/game/{lobby_id}/claim")
async def claim_bingo(lobby_id: str, request: ClaimRequest, alien_id: str = Depends(verify_alien_token)):
    try:
        if request.alien_id != alien_id:
            raise HTTPException(status_code=403, detail="Unauthorized Alien ID")
        
        result = await claim_bingo_logic(lobby_id, request.alien_id)
        
        if not result.get("valid"):
            if result.get("kicked"):
                raise HTTPException(status_code=400, detail=result.get("message"))
            else:
                # Other invalid reasons like game not active, lobby not found etc.
                raise HTTPException(status_code=400, detail=result.get("message"))
        
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.on_event("startup")
async def startup_event():
    await start_lobby_monitor() # This will create a background task
    print("Application startup: Lobby monitor started.")

@app.post("/api/webhooks/payment")
async def payment_webhook(request: dict):
    # Placeholder - No auth on this endpoint, but will have signature verification in a later phase
    return {"message": "Payment webhook endpoint"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
