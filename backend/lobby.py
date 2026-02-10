import uuid
import json
import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Optional

from redis_client import redis

import os

MAX_PLAYERS = 10
MIN_PLAYERS = 2
FORMING_TIMEOUT = 120  # 2 minutes
NUMBER_CALL_INTERVAL = 3  # 3 seconds
LOBBY_TTL = 600  # 10 minutes
MAX_NUMBER = 20
BUY_IN_AMOUNT = 3500  # Fixed buy-in per player

ACTIVE_LOBBIES_KEY = "active_lobbies"

CELESTIAL_NAMES = [
    "Andromeda", "Orion", "Nebula", "Pulsar", "Quasar", "Vega", "Sirius",
    "Polaris", "Centauri", "Nova", "Eclipse", "Cosmos", "Zenith", "Astral",
    "Lyra", "Cygnus", "Draco", "Perseus", "Cassiopeia", "Arcturus",
    "Rigel", "Betelgeuse", "Aldebaran", "Antares", "Capella", "Deneb",
    "Procyon", "Spica", "Regulus", "Altair",
]


# --- Multi-Lobby Management ---

async def _pick_lobby_name() -> str:
    """Pick a celestial name not currently used by any active lobby."""
    active_ids = await redis.smembers(ACTIVE_LOBBIES_KEY)
    used_names = set()
    for lid in active_ids:
        name = await redis.hget(f"lobby:{lid}", "name")
        if name:
            used_names.add(name)
    for name in CELESTIAL_NAMES:
        if name not in used_names:
            return name
    return f"Cosmos-{random.randint(100, 999)}"


async def create_lobby() -> dict:
    """Create a new forming lobby with a celestial name."""
    lobby_id = f"lobby_{uuid.uuid4().hex[:8]}"
    name = await _pick_lobby_name()

    await redis.hset(f"lobby:{lobby_id}", mapping={
        "lobby_id": lobby_id,
        "name": name,
        "status": "forming",
        "buy_in_amount": str(BUY_IN_AMOUNT),
        "pot": "0",
        "winner": "",
        "created_at": datetime.utcnow().isoformat(),
        "forming_deadline": "",
        "started_at": "",
        "finished_at": "",
    })
    await redis.expire(f"lobby:{lobby_id}", LOBBY_TTL)
    await redis.sadd(ACTIVE_LOBBIES_KEY, lobby_id)
    return {"lobby_id": lobby_id, "name": name, "status": "forming", "player_count": 0, "pot": 0}


async def ensure_empty_lobby_exists() -> None:
    """Ensure exactly one empty forming lobby exists. Remove extras."""
    active_ids = await redis.smembers(ACTIVE_LOBBIES_KEY)
    empty_lobbies = []

    for lid in active_ids:
        lobby = await redis.hgetall(f"lobby:{lid}")
        if not lobby or lobby.get("status") == "finished":
            await redis.srem(ACTIVE_LOBBIES_KEY, lid)
            continue
        if lobby.get("status") == "forming":
            player_keys = await redis.keys(f"lobby:{lid}:player:*")
            if len(player_keys) == 0:
                empty_lobbies.append(lid)

    if len(empty_lobbies) == 0:
        await create_lobby()
    elif len(empty_lobbies) > 1:
        # Keep the first, remove the rest
        for lid in empty_lobbies[1:]:
            await redis.delete(f"lobby:{lid}")
            await redis.srem(ACTIVE_LOBBIES_KEY, lid)


async def list_lobbies() -> list:
    """Return all active lobbies (forming/active) with summary info."""
    active_ids = await redis.smembers(ACTIVE_LOBBIES_KEY)
    lobbies = []
    for lid in active_ids:
        lobby = await redis.hgetall(f"lobby:{lid}")
        if not lobby:
            await redis.srem(ACTIVE_LOBBIES_KEY, lid)
            continue
        if lobby["status"] == "finished":
            await redis.srem(ACTIVE_LOBBIES_KEY, lid)
            continue
        player_keys = await redis.keys(f"lobby:{lid}:player:*")
        lobbies.append({
            "lobby_id": lobby["lobby_id"],
            "name": lobby.get("name", "Unknown"),
            "status": lobby["status"],
            "player_count": len(player_keys),
            "max_players": MAX_PLAYERS,
            "pot": int(lobby.get("pot", 0)),
            "buy_in_amount": int(lobby.get("buy_in_amount", BUY_IN_AMOUNT)),
        })
    return lobbies


async def initialize_lobbies() -> None:
    """Called on app startup to ensure at least one empty lobby exists."""
    await ensure_empty_lobby_exists()


# --- Player Joining ---

async def add_player_to_lobby(lobby_id: str, alien_id: str) -> dict:
    """Add a player to a lobby. Returns lobby info."""
    lobby = await redis.hgetall(f"lobby:{lobby_id}")
    if not lobby:
        raise ValueError("Lobby not found")

    if lobby["status"] != "forming":
        raise ValueError("Lobby is no longer accepting players")

    # Check if player is already in this lobby — return current state
    exists = await redis.exists(f"lobby:{lobby_id}:player:{alien_id}")
    if exists:
        player_keys = await redis.keys(f"lobby:{lobby_id}:player:*")
        return {
            "lobby_id": lobby_id,
            "status": lobby["status"],
            "player_count": len(player_keys),
            "pot": int(lobby["pot"]),
        }

    # Check capacity
    player_keys = await redis.keys(f"lobby:{lobby_id}:player:*")
    if len(player_keys) >= MAX_PLAYERS:
        raise ValueError("Lobby is full")

    # Add player
    await redis.hset(f"lobby:{lobby_id}:player:{alien_id}", mapping={
        "alien_id": alien_id,
        "numbers": "[]",
        "grid": "[]",
        "ready": "false",
        "active": "true",
        "joined_at": datetime.utcnow().isoformat(),
    })
    await redis.expire(f"lobby:{lobby_id}:player:{alien_id}", LOBBY_TTL)

    player_count = len(player_keys) + 1
    pot = int(lobby["pot"])

    # Auto-credit buy-in
    await redis.hincrby(f"lobby:{lobby_id}", "pot", BUY_IN_AMOUNT)
    pot += BUY_IN_AMOUNT

    # Start forming timer on first player join
    if not lobby.get("forming_deadline"):
        deadline = (datetime.utcnow() + timedelta(seconds=FORMING_TIMEOUT)).isoformat()
        await redis.hset(f"lobby:{lobby_id}", "forming_deadline", deadline)
        asyncio.create_task(forming_timer(lobby_id))

    # Ensure a new empty lobby is available after this join
    await ensure_empty_lobby_exists()

    return {
        "lobby_id": lobby_id,
        "status": lobby["status"],
        "player_count": player_count,
        "pot": pot,
    }


async def remove_player_from_lobby(lobby_id: str, alien_id: str) -> dict:
    """Remove a player from a forming lobby and refund buy-in."""
    lobby = await redis.hgetall(f"lobby:{lobby_id}")
    if not lobby:
        raise ValueError("Lobby not found")

    if lobby["status"] != "forming":
        raise ValueError("Cannot leave a game in progress")

    exists = await redis.exists(f"lobby:{lobby_id}:player:{alien_id}")
    if not exists:
        raise ValueError("Player not in this lobby")

    # Remove player
    await redis.delete(f"lobby:{lobby_id}:player:{alien_id}")

    # Refund buy-in
    await redis.hincrby(f"lobby:{lobby_id}", "pot", -BUY_IN_AMOUNT)

    # If lobby is now empty, clean up extra empties
    player_keys = await redis.keys(f"lobby:{lobby_id}:player:*")
    if len(player_keys) == 0:
        # Reset forming deadline since no players left
        await redis.hset(f"lobby:{lobby_id}", "forming_deadline", "")

    await ensure_empty_lobby_exists()

    return {"success": True}


# --- Submit Grid (combined select + arrange) ---

async def submit_grid(lobby_id: str, alien_id: str, grid: List[List[int]]) -> dict:
    """Store player's grid (numbers + arrangement in one step). Marks player ready."""
    lobby = await redis.hgetall(f"lobby:{lobby_id}")
    if not lobby:
        raise ValueError("Lobby not found")

    if lobby["status"] != "forming":
        raise ValueError("Cannot submit grid in current game state")

    player = await redis.hgetall(f"lobby:{lobby_id}:player:{alien_id}")
    if not player:
        raise ValueError("Player not in this lobby")

    # Validate grid structure
    if len(grid) != 3 or any(len(row) != 3 for row in grid):
        raise ValueError("Grid must be 3x3")

    flat = [n for row in grid for n in row]
    if len(set(flat)) != 9:
        raise ValueError("Grid must contain 9 unique numbers")

    if not all(1 <= n <= MAX_NUMBER for n in flat):
        raise ValueError(f"Numbers must be between 1 and {MAX_NUMBER}")

    # Store numbers and grid, mark ready
    await redis.hset(f"lobby:{lobby_id}:player:{alien_id}", mapping={
        "numbers": json.dumps(flat),
        "grid": json.dumps(grid),
        "ready": "true",
    })

    # Check if all players are ready → start game immediately
    player_keys = await redis.keys(f"lobby:{lobby_id}:player:*")
    if len(player_keys) >= MIN_PLAYERS:
        all_ready = await check_all_players_ready(lobby_id)
        if all_ready:
            await start_game(lobby_id)

    ready_count = await _count_ready_players(lobby_id)

    return {
        "success": True,
        "ready_count": ready_count,
        "message": "Grid submitted. Waiting for other players.",
    }


async def check_all_players_ready(lobby_id: str) -> bool:
    """Check if all active players have submitted their grid."""
    player_keys = await redis.keys(f"lobby:{lobby_id}:player:*")
    for key in player_keys:
        player = await redis.hgetall(key)
        if player.get("active") == "true" and player.get("ready") != "true":
            return False
    return True


async def _count_ready_players(lobby_id: str) -> int:
    """Count players who have submitted their grid."""
    player_keys = await redis.keys(f"lobby:{lobby_id}:player:*")
    count = 0
    for key in player_keys:
        player = await redis.hgetall(key)
        if player.get("ready") == "true" and player.get("active") == "true":
            count += 1
    return count


# --- Timers & State Transitions ---

def _generate_random_grid() -> List[List[int]]:
    """Generate a random 3x3 grid with 9 unique numbers from 1-MAX_NUMBER."""
    nums = random.sample(range(1, MAX_NUMBER + 1), 9)
    return [nums[0:3], nums[3:6], nums[6:9]]


async def forming_timer(lobby_id: str):
    """2-minute countdown. When it expires, auto-submit random grids for unready players and start."""
    await asyncio.sleep(FORMING_TIMEOUT)

    lobby = await redis.hgetall(f"lobby:{lobby_id}")
    if not lobby or lobby["status"] != "forming":
        return

    # Auto-submit random grids for unready players
    player_keys = await redis.keys(f"lobby:{lobby_id}:player:*")
    for key in player_keys:
        player = await redis.hgetall(key)
        if player.get("active") == "true" and player.get("ready") != "true":
            grid = _generate_random_grid()
            flat = [n for row in grid for n in row]
            await redis.hset(key, mapping={
                "numbers": json.dumps(flat),
                "grid": json.dumps(grid),
                "ready": "true",
            })

    # All players now have grids — start if enough players
    active_keys = []
    for key in player_keys:
        player = await redis.hgetall(key)
        if player.get("active") == "true":
            active_keys.append(key)

    if len(active_keys) >= MIN_PLAYERS:
        await start_game(lobby_id)
    else:
        await finish_game(lobby_id, winner=None)


async def start_game(lobby_id: str):
    """Transition to active state and start calling numbers."""
    lock_acquired = await redis.set(f"lobby:{lobby_id}:starting", "1", nx=True, ex=30)
    if not lock_acquired:
        return

    current_status = await redis.hget(f"lobby:{lobby_id}", "status")
    if current_status != "forming":
        return

    await redis.hset(f"lobby:{lobby_id}", mapping={
        "status": "active",
        "started_at": datetime.utcnow().isoformat(),
    })

    await redis.expire(f"lobby:{lobby_id}", LOBBY_TTL)

    asyncio.create_task(call_numbers_task(lobby_id))


# --- Number Calling ---

async def call_numbers_task(lobby_id: str):
    """Background task that calls numbers every 3 seconds."""
    numbers_pool = list(range(1, MAX_NUMBER + 1))
    random.shuffle(numbers_pool)

    for number in numbers_pool:
        lobby = await redis.hgetall(f"lobby:{lobby_id}")
        if not lobby or lobby["status"] != "active":
            return

        current_latest = lobby.get("latest_number", "")

        await redis.rpush(f"lobby:{lobby_id}:numbers_called", str(number))

        update = {"latest_number": str(number)}
        if current_latest:
            update["previous_number"] = current_latest
        await redis.hset(f"lobby:{lobby_id}", mapping=update)

        await asyncio.sleep(NUMBER_CALL_INTERVAL)

    await finish_game(lobby_id, winner=None)


# --- Win Verification ---

def check_win_patterns(grid: List[List[int]], numbers_called: set) -> Optional[str]:
    """Check all 8 possible winning patterns."""
    for i in range(3):
        if all(grid[i][j] in numbers_called for j in range(3)):
            return f"row_{i}"

    for j in range(3):
        if all(grid[i][j] in numbers_called for i in range(3)):
            return f"col_{j}"

    if all(grid[i][i] in numbers_called for i in range(3)):
        return "diagonal_main"

    if all(grid[i][2 - i] in numbers_called for i in range(3)):
        return "diagonal_anti"

    return None


async def verify_claim(lobby_id: str, alien_id: str, highlighted_numbers: List[int]) -> dict:
    """Verify a bingo claim using the player's highlighted numbers."""
    lobby = await redis.hgetall(f"lobby:{lobby_id}")
    if not lobby:
        raise ValueError("Lobby not found")

    if lobby["status"] != "active":
        raise ValueError("Game is not active")

    player = await redis.hgetall(f"lobby:{lobby_id}:player:{alien_id}")
    if not player:
        raise ValueError("Player not in this lobby")

    if player.get("active") != "true":
        raise ValueError("Player is no longer active in this game")

    grid = json.loads(player["grid"])
    called_raw = await redis.lrange(f"lobby:{lobby_id}:numbers_called", 0, -1)
    numbers_called = set(int(n) for n in called_raw)

    highlighted_set = set(highlighted_numbers)

    # Check 1: Do highlighted numbers form a winning pattern on the grid?
    pattern = check_win_patterns(grid, highlighted_set)

    # Check 2: Are ALL highlighted numbers actually called?
    all_called = highlighted_set.issubset(numbers_called)

    if pattern and all_called:
        pot = int(lobby["pot"])
        await finish_game(lobby_id, winner=alien_id)
        return {
            "valid": True,
            "winner": True,
            "pot": pot,
            "message": f"YOU WON! +{pot:,} Alien coins",
            "pattern": pattern,
        }
    else:
        await redis.hset(f"lobby:{lobby_id}:player:{alien_id}", "active", "false")

        all_kicked = await check_all_players_kicked(lobby_id)
        if all_kicked:
            await finish_game(lobby_id, winner=None)

        return {
            "valid": False,
            "kicked": True,
            "message": "Invalid claim. You've been removed from the game.",
        }


async def check_all_players_kicked(lobby_id: str) -> bool:
    """Check if all players have been kicked."""
    player_keys = await redis.keys(f"lobby:{lobby_id}:player:*")
    for key in player_keys:
        player = await redis.hgetall(key)
        if player.get("active") == "true":
            return False
    return True


async def finish_game(lobby_id: str, winner: Optional[str]):
    """Finish the game, set winner, clean up."""
    await redis.hset(f"lobby:{lobby_id}", mapping={
        "status": "finished",
        "winner": winner or "",
        "finished_at": datetime.utcnow().isoformat(),
    })
    # Remove from active set and ensure an empty lobby exists
    await redis.srem(ACTIVE_LOBBIES_KEY, lobby_id)
    await ensure_empty_lobby_exists()


# --- Game Status ---

async def get_game_status(lobby_id: str) -> dict:
    """Get full game status for polling."""
    lobby = await redis.hgetall(f"lobby:{lobby_id}")
    if not lobby:
        raise ValueError("Lobby not found")

    player_keys = await redis.keys(f"lobby:{lobby_id}:player:*")
    players = {}
    ready_count = 0
    for key in player_keys:
        player_data = await redis.hgetall(key)
        aid = player_data["alien_id"]
        is_ready = player_data.get("ready") == "true"
        if is_ready and player_data.get("active") == "true":
            ready_count += 1
        players[aid] = {
            "alien_id": aid,
            "numbers": json.loads(player_data.get("numbers", "[]")),
            "grid": json.loads(player_data.get("grid", "[]")),
            "ready": is_ready,
            "active": player_data.get("active") == "true",
            "joined_at": player_data.get("joined_at", ""),
        }

    called_raw = await redis.lrange(f"lobby:{lobby_id}:numbers_called", 0, -1)
    called_numbers = [int(n) for n in called_raw]

    time_elapsed = 0
    if lobby.get("started_at"):
        started = datetime.fromisoformat(lobby["started_at"])
        time_elapsed = int((datetime.utcnow() - started).total_seconds())

    return {
        "lobby_id": lobby["lobby_id"],
        "status": lobby["status"],
        "buy_in_amount": int(lobby["buy_in_amount"]),
        "pot": int(lobby["pot"]),
        "player_count": len(player_keys),
        "ready_count": ready_count,
        "players": players,
        "forming_deadline": lobby.get("forming_deadline") or None,
        "latest_number": int(lobby["latest_number"]) if lobby.get("latest_number") else None,
        "previous_number": int(lobby["previous_number"]) if lobby.get("previous_number") else None,
        "called_numbers": called_numbers,
        "winner": lobby.get("winner") or None,
        "time_elapsed": time_elapsed,
    }
