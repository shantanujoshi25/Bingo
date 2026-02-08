import redis.asyncio as aioredis
import json
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from redis_client import redis

# Constants
LOBBY_CAPACITY_MIN = 2
LOBBY_CAPACITY_MAX = 10
LOBBY_FORMATION_TIMER_SECONDS = 120 # 2 minutes
GRID_ARRANGEMENT_TIMER_SECONDS = 90

# --- Lobby Management Functions ---

async def get_lobby_info(lobby_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves all information for a given lobby ID from Redis."""
    lobby_data = await redis.hgetall(f"lobby:{lobby_id}")
    if not lobby_data:
        return None
    
    # Decode byte strings to UTF-8
    decoded_lobby_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in lobby_data.items()}
    
    # Parse specific fields
    decoded_lobby_data['pot'] = int(decoded_lobby_data['pot'])
    decoded_lobby_data['buy_in_amount'] = int(decoded_lobby_data['buy_in_amount'])
    decoded_lobby_data['player_count'] = int(decoded_lobby_data['player_count'])
    
    # Get players in lobby
    player_keys = await redis.keys(f"lobby:{lobby_id}:player:*")
    players = {}
    for key in player_keys:
        player_id = key.decode('utf-8').split(':')[-1]
        player_data = await redis.hgetall(key)
        decoded_player_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in player_data.items()}
        
        # Deserialize JSON fields
        if 'numbers' in decoded_player_data:
            decoded_player_data['numbers'] = json.loads(decoded_player_data['numbers'])
        if 'grid' in decoded_player_data:
            decoded_player_data['grid'] = json.loads(decoded_player_data['grid'])
        decoded_player_data['active'] = decoded_player_data['active'].lower() == 'true'

        players[player_id] = decoded_player_data
    
    decoded_lobby_data['players'] = players
    
    return decoded_lobby_data

async def find_or_create_lobby(alien_id: str, buy_in_amount: int) -> Dict[str, Any]:
    """
    Finds an existing 'forming' lobby with matching buy-in or creates a new one.
    """
    # 1. Look for existing 'forming' lobbies with matching buy_in_amount
    all_lobby_keys = await redis.keys("lobby:*")
    
    for key in all_lobby_keys:
        lobby_id = key.decode('utf-8').split(':')[-1]
        lobby_data = await redis.hgetall(key)
        
        if not lobby_data: # Lobby might have expired or been removed
            continue

        decoded_lobby_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in lobby_data.items()}
        
        if (decoded_lobby_data.get('status') == 'forming' and
            int(decoded_lobby_data.get('buy_in_amount', 0)) == buy_in_amount and
            int(decoded_lobby_data.get('player_count', 0)) < LOBBY_CAPACITY_MAX):
            
            # Check if player is already in this lobby
            if await redis.exists(f"lobby:{lobby_id}:player:{alien_id}"):
                raise ValueError("Player already in this lobby") # Or return current lobby info
            
            # Found a suitable lobby, add player and return
            return await add_player_to_lobby(lobby_id, alien_id, buy_in_amount)

    # 2. No suitable lobby found, create a new one
    lobby_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    
    lobby_data = {
        "lobby_id": lobby_id,
        "status": "forming",
        "buy_in_amount": str(buy_in_amount),
        "pot": str(buy_in_amount), # Initial pot is the buy-in of the first player
        "player_count": "0",
        "created_at": created_at,
        "started_at": "" # Will be set when game moves to 'active'
    }
    
    await redis.hset(f"lobby:{lobby_id}", mapping=lobby_data)
    await redis.expire(f"lobby:{lobby_id}", timedelta(minutes=10)) # Set TTL for lobby

    # Add the first player to the newly created lobby
    return await add_player_to_lobby(lobby_id, alien_id, buy_in_amount)

async def add_player_to_lobby(lobby_id: str, alien_id: str, buy_in_amount: int) -> Dict[str, Any]:
    """Adds a player to an existing lobby."""
    # Check if player is already in this lobby (double check)
    if await redis.exists(f"lobby:{lobby_id}:player:{alien_id}"):
        # Return current lobby info if player already in
        return await get_lobby_info(lobby_id)
    
    # Add player data to lobby (initially without numbers/grid)
    player_data = {
        "alien_id": alien_id,
        "active": "true",
        "joined_at": datetime.utcnow().isoformat()
    }
    await redis.hset(f"lobby:{lobby_id}:player:{alien_id}", mapping=player_data)
    
    # Increment player count and pot, set TTL for player
    await redis.hincrby(f"lobby:{lobby_id}", "player_count", 1)
    await redis.hincrby(f"lobby:{lobby_id}", "pot", buy_in_amount)
    
    # Fetch and return updated lobby info
    updated_lobby = await get_lobby_info(lobby_id)
    
    # Check for state transition if lobby is full or timer started (this will be handled by a background task)
    asyncio.create_task(check_state_transition(lobby_id))
    
    return updated_lobby

async def update_player_numbers(lobby_id: str, alien_id: str, numbers: List[int]):
    """Updates a player's selected numbers in Redis."""
    await redis.hset(f"lobby:{lobby_id}:player:{alien_id}", "numbers", json.dumps(numbers))

async def update_player_grid(lobby_id: str, alien_id: str, grid: List[List[int]]):
    """Updates a player's grid arrangement in Redis."""
    await redis.hset(f"lobby:{lobby_id}:player:{alien_id}", "grid", json.dumps(grid))

async def check_all_players_arranged(lobby_id: str) -> bool:
    """Checks if all players in a lobby have submitted their grid arrangements."""
    lobby_info = await get_lobby_info(lobby_id)
    if not lobby_info:
        return False

    player_count = lobby_info['player_count']
    arranged_count = 0
    
    for player_id, player_data in lobby_info['players'].items():
        if player_data.get('grid'):
            arranged_count += 1
            
    return arranged_count == player_count


# --- State Transition Logic ---
async def check_state_transition(lobby_id: str):
    """
    Handles state transitions for a lobby based on player count and timers.
    This function should ideally be called by a background task or regularly polled.
    """
    lobby_data = await redis.hgetall(f"lobby:{lobby_id}")
    if not lobby_data:
        print(f"Lobby {lobby_id} not found for state transition check.")
        return

    decoded_lobby = {k.decode('utf-8'): v.decode('utf-8') for k, v in lobby_data.items()}
    current_status = decoded_lobby.get('status')
    
    if current_status == "forming":
        player_count = int(decoded_lobby.get("player_count", 0))
        created_at_str = decoded_lobby.get("created_at")
        
        if created_at_str:
            created_at = datetime.fromisoformat(created_at_str)
            time_elapsed = (datetime.utcnow() - created_at).total_seconds()
        else:
            time_elapsed = 0 # Should not happen if created_at is always set

        # Transition from 'forming' to 'arranging'
        if player_count >= LOBBY_CAPACITY_MIN and (time_elapsed >= LOBBY_FORMATION_TIMER_SECONDS or player_count >= LOBBY_CAPACITY_MAX):
            await redis.hset(f"lobby:{lobby_id}", "status", "arranging")
            print(f"Lobby {lobby_id} transitioned from 'forming' to 'arranging'.")
            asyncio.create_task(arrangement_timer(lobby_id)) # Start arrangement timer
    
    elif current_status == "arranging":
        # This transition will be handled by arrangement_timer or when all players arranged
        pass # The arrangement_timer will handle the transition to 'active'


async def arrangement_timer(lobby_id: str):
    """
    Timer for the grid arrangement phase.
    After the timer, if all players haven't arranged, lobby moves to active.
    If all players arrange before timer, it can also move to active.
    """
    print(f"Arrangement timer started for lobby {lobby_id}. {GRID_ARRANGEMENT_TIMER_SECONDS} seconds.")
    
    start_time = datetime.utcnow()
    while (datetime.utcnow() - start_time).total_seconds() < GRID_ARRANGEMENT_TIMER_SECONDS:
        # Check if all players have arranged their grid
        if await check_all_players_arranged(lobby_id):
            print(f"All players in lobby {lobby_id} arranged their grids. Moving to active.")
            await redis.hset(f"lobby:{lobby_id}", "status", "active")
            await redis.hset(f"lobby:{lobby_id}", "started_at", datetime.utcnow().isoformat())
            # asyncio.create_task(call_numbers_task(lobby_id)) # This will be started by game_logic
            return
        await asyncio.sleep(1) # Check every second
    
    # Timer expired
    lobby_info = await get_lobby_info(lobby_id)
    if lobby_info and lobby_info['status'] == 'arranging':
        print(f"Arrangement timer expired for lobby {lobby_id}. Moving to active.")
        await redis.hset(f"lobby:{lobby_id}", "status", "active")
        await redis.hset(f"lobby:{lobby_id}", "started_at", datetime.utcnow().isoformat())
        # asyncio.create_task(call_numbers_task(lobby_id)) # This will be started by game_logic

# Background task to periodically check for lobby state transitions
async def lobby_state_monitor():
    """
    A background task that periodically checks all lobbies for state transitions.
    This ensures lobbies move through states even if no new players join.
    """
    while True:
        print("Running lobby state monitor...")
        all_lobby_keys = await redis.keys("lobby:*")
        for key in all_lobby_keys:
            lobby_id = key.decode('utf-8').split(':')[-1]
            # Only check lobbies that are 'forming' or 'arranging'
            status = await redis.hget(f"lobby:{lobby_id}", "status")
            if status and status.decode('utf-8') in ["forming", "arranging"]:
                await check_state_transition(lobby_id)
        await asyncio.sleep(5) # Check every 5 seconds

# Start the monitor when the application starts
async def start_lobby_monitor():
    await redis.wait_until_ready() # Ensure redis is connected before starting monitor
    asyncio.create_task(lobby_state_monitor())
