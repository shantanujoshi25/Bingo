import redis.asyncio as aioredis
import json
import asyncio
import random
from datetime import datetime
from typing import List, Dict, Any, Optional

from redis_client import redis
from lobby import get_lobby_info, update_player_numbers, update_player_grid # Assuming these will be exposed/used

# Constants
NUMBER_CALLING_INTERVAL_SECONDS = 3
TOTAL_BINGO_NUMBERS = 50 # Numbers 1-50

# --- Game Logic Functions ---

def validate_numbers_selection(numbers: List[int]) -> bool:
    """Validates player's selected numbers."""
    if len(numbers) != 9:
        return False
    if len(set(numbers)) != 9: # Check for uniqueness
        return False
    if not all(1 <= num <= TOTAL_BINGO_NUMBERS for num in numbers):
        return False
    return True

def validate_grid_arrangement(selected_numbers: List[int], grid: List[List[int]]) -> bool:
    """Validates player's grid arrangement."""
    if len(grid) != 3 or any(len(row) != 3 for row in grid):
        return False
    
    flattened_grid = [num for row in grid for num in row]
    if len(flattened_grid) != 9:
        return False
    if len(set(flattened_grid)) != 9: # Check for uniqueness within grid
        return False
    
    # Check if all grid numbers match previously selected numbers
    if set(flattened_grid) != set(selected_numbers):
        return False
        
    return True

async def get_game_status_data(lobby_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves comprehensive game status for a lobby."""
    lobby_info = await get_lobby_info(lobby_id)
    if not lobby_info:
        return None
    
    # Get numbers called
    numbers_called_raw = await redis.lrange(f"lobby:{lobby_id}:numbers_called", 0, -1)
    numbers_called = [int(num.decode('utf-8')) for num in numbers_called_raw]

    latest_number = numbers_called[-1] if numbers_called else None
    previous_number = numbers_called[-2] if len(numbers_called) >= 2 else None
    
    lobby_info['latest_number'] = latest_number
    lobby_info['previous_number'] = previous_number
    # Note: numbers_called array is NOT included as per spec
    
    return lobby_info


def check_win_conditions(player_grid: List[List[int]], called_numbers: List[int]) -> Optional[str]:
    """
    Checks if a player's grid has a winning pattern based on called numbers.
    Returns the pattern type (e.g., "row_0", "col_1", "diag_lr") or None.
    """
    
    # Flatten player_grid for easier lookup of marked numbers
    marked_grid = [[(cell in called_numbers) for cell in row] for row in player_grid]

    # Check Rows
    for i, row in enumerate(marked_grid):
        if all(row):
            return f"row_{i}"

    # Check Columns
    for j in range(3):
        if all(marked_grid[i][j] for i in range(3)):
            return f"col_{j}"

    # Check Diagonals
    # Top-left to Bottom-right
    if all(marked_grid[i][i] for i in range(3)):
        return "diag_lr"

    # Top-right to Bottom-left
    if all(marked_grid[i][2-i] for i in range(3)):
        return "diag_rl"

    return None

async def claim_bingo_logic(lobby_id: str, alien_id: str) -> Dict[str, Any]:
    """
    Handles the claim Bingo process.
    Verifies claim, awards pot, or kicks player for invalid claim.
    """
    lobby_info = await get_lobby_info(lobby_id)
    if not lobby_info:
        return {"valid": False, "kicked": False, "message": "Lobby not found."}

    if lobby_info.get("status") != "active":
        return {"valid": False, "kicked": False, "message": "Game is not active."}

    player_data = lobby_info['players'].get(alien_id)
    if not player_data or not player_data.get('active'):
        return {"valid": False, "kicked": False, "message": "Player not active in this game."}

    player_grid = player_data.get('grid')
    if not player_grid:
        return {"valid": False, "kicked": True, "message": "No grid submitted. Kicking player."}

    numbers_called_raw = await redis.lrange(f"lobby:{lobby_id}:numbers_called", 0, -1)
    called_numbers = [int(num.decode('utf-8')) for num in numbers_called_raw]

    winning_pattern = check_win_conditions(player_grid, called_numbers)
    
    if winning_pattern:
        # Check if there's already a winner for this lobby
        current_winner = await redis.hget(f"lobby:{lobby_id}", "winner")
        if current_winner:
            return {
                "valid": False,
                "kicked": False,
                "message": f"A winner ({current_winner.decode('utf-8')}) has already claimed for this lobby.",
                "pattern": winning_pattern # Indicate the pattern they would have won on
            }

        # Valid claim - declare winner
        await redis.hset(f"lobby:{lobby_id}", "winner", alien_id)
        await redis.hset(f"lobby:{lobby_id}", "status", "finished")
        
        pot_amount = lobby_info['pot']
        # TODO: Implement actual coin transfer in a later phase (Phase 4 Payment Integration)
        
        return {
            "valid": True,
            "winner": True,
            "pot": pot_amount,
            "message": f"🎉 YOU WON! +{pot_amount} Alien coins",
            "pattern": winning_pattern
        }
    else:
        # Invalid claim - kick player
        await redis.hset(f"lobby:{lobby_id}:player:{alien_id}", "active", "false")
        
        # Get missing numbers for feedback
        missing_numbers = []
        for row in player_grid:
            for num in row:
                if num not in called_numbers:
                    missing_numbers.append(num)

        # Check if all players are kicked (no winner scenario)
        active_players = 0
        for pid, pdata in lobby_info['players'].items():
            if pid != alien_id and pdata.get('active'): # Check other players
                active_players += 1
        
        if active_players == 0:
            await redis.hset(f"lobby:{lobby_id}", "status", "finished")
            # TODO: House keeps pot (no payout)
            
        return {
            "valid": False,
            "kicked": True,
            "message": "Invalid claim. You've been removed from the game.",
            "missing_numbers": sorted(list(set(missing_numbers)))
        }

# --- Background Number Calling Task ---

async def call_numbers_task(lobby_id: str):
    """
    Background task to call numbers for an active lobby.
    """
    print(f"Starting number calling for lobby {lobby_id}...")
    
    # Generate all possible numbers once
    all_numbers = list(range(1, TOTAL_BINGO_NUMBERS + 1))
    random.shuffle(all_numbers)
    
    await redis.delete(f"lobby:{lobby_id}:numbers_called") # Clear previous called numbers
    
    for number in all_numbers:
        lobby_info = await get_lobby_info(lobby_id)
        if not lobby_info or lobby_info.get("status") != "active":
            print(f"Number calling for lobby {lobby_id} stopped (lobby not active).")
            break
        
        # Check if a winner has already been declared
        if lobby_info.get("winner"):
            print(f"Number calling for lobby {lobby_id} stopped (winner declared).")
            await redis.hset(f"lobby:{lobby_id}", "status", "finished")
            break

        await redis.rpush(f"lobby:{lobby_id}:numbers_called", number)
        await redis.hset(f"lobby:{lobby_id}", "latest_number", str(number))
        
        # Get previous number (second to last)
        numbers_called_list = await redis.lrange(f"lobby:{lobby_id}:numbers_called", 0, -1)
        if len(numbers_called_list) >= 2:
            previous_number = numbers_called_list[-2].decode('utf-8')
            await redis.hset(f"lobby:{lobby_id}", "previous_number", previous_number)
        else:
            await redis.hdel(f"lobby:{lobby_id}", "previous_number") # No previous number

        print(f"Lobby {lobby_id}: Called number {number}")
        
        await asyncio.sleep(NUMBER_CALLING_INTERVAL_SECONDS)
    
    # If all numbers called and no winner
    final_lobby_info = await get_lobby_info(lobby_id)
    if final_lobby_info and not final_lobby_info.get("winner"):
        print(f"All numbers called for lobby {lobby_id}. No winner. House keeps pot.")
        await redis.hset(f"lobby:{lobby_id}", "status", "finished")

