# Fair Bingo - Technical Implementation Guide

**Version:** 2.0 (FastAPI + React + Redis)  
**Date:** February 7, 2026  
**Platform:** Alien Mini App  
**Target:** Implementation Guide

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Tech Stack](#tech-stack)
3. [System Architecture](#system-architecture)
4. [Core Game Mechanics](#core-game-mechanics)
5. [Data Models](#data-models)
6. [Backend API Specification](#backend-api-specification)
7. [Frontend Implementation](#frontend-implementation)
8. [Alien Integration](#alien-integration)
9. [Redis Schema](#redis-schema)
10. [Game Flow State Machine](#game-flow-state-machine)
11. [Implementation Checklist](#implementation-checklist)

---

## 1. Executive Summary

Fair Bingo is a multiplayer Bingo game built as an Alien Mini App that leverages verified human identity to prevent Sybil attacks. Players compete in real-time with a winner-takes-all pot funded by Alien coin buy-ins.

### Key Features
- **Sybil-Resistant:** One Alien ID = One ticket per lobby
- **Real-Time Multiplayer:** 2-10 players per game
- **Instant Payments:** Alien coins for buy-ins and payouts
- **3×3 Grid:** Players select and arrange 9 numbers (1-50)
- **Live Number Calling:** Numbers drawn every 3 seconds
- **Win Verification:** Server-side claim validation

### Success Metrics
- Zero duplicate Alien IDs per lobby
- < 2 second state sync latency
- 100% payment verification via webhooks
- < 3 minute average game duration

---

## 2. Tech Stack

### Frontend
```
Framework:     React 18.3+
Build Tool:    Vite 5.0+
SDK:          @alien_org/react (Mini App SDK)
State:        React hooks + polling
Styling:      Tailwind CSS
```

### Backend
```
Framework:     FastAPI 0.104+
Language:      Python 3.11+
ASGI Server:   Uvicorn
Async:        asyncio + httpx
Validation:   Pydantic v2
Auth:         Alien JWT verification
```

### Database
```
Primary:      Redis 7.0+ (in-memory)
Data Types:   Hashes, Sets, Sorted Sets, Strings
Persistence:  None (ephemeral game state only)
TTL:         Auto-expire finished games
```

### Infrastructure
```
Tunnel:       ngrok (dev/hackathon)
Production:   Railway / Render / Fly.io
Monitoring:   Structured logging (JSON)
```

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ALIEN MINI APP HOST                      │
│  • JWT injection (window.__ALIEN_AUTH_TOKEN__)             │
│  • Payment interface (window.AlienPayment)                  │
│  • WebView container                                        │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ HTTPS (ngrok tunnel)
                 │
┌────────────────▼────────────────────────────────────────────┐
│                    REACT FRONTEND                           │
│  • @alien_org/react hooks (useAlien, usePayment)          │
│  • Client-side polling (1.5s interval)                     │
│  • Game UI rendering                                        │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ REST API (JSON)
                 │
┌────────────────▼────────────────────────────────────────────┐
│                   FASTAPI BACKEND                           │
│  • JWT validation                                           │
│  • Game logic & state management                            │
│  • Payment webhook handler                                  │
│  • Number calling background task                           │
└────────────────┬────────────────────────────────────────────┘
                 │
         ┌───────┴───────┐
         │               │
    ┌────▼────┐    ┌────▼─────┐
    │  REDIS  │    │  ALIEN   │
    │IN-MEMORY│    │ PAYMENT  │
    │  STORE  │    │   API    │
    └─────────┘    └──────────┘
```

---

## 4. Core Game Mechanics

### 4.1 Number Selection & Arrangement

**Numbers:** 1-50 (no duplicates within a grid)  
**Grid:** 3×3 = 9 numbers per player  
**Selection Time:** Unlimited (during lobby formation)  
**Arrangement Time:** 90 seconds after selection  
**Timeout Behavior:** Auto-arrange randomly OR move to new lobby

### 4.2 Lobby System

**Capacity:** 2 (min) to 10 (max) players  
**Formation Timer:** 2 minutes OR until full  
**Buy-In Tiers:** 3,500 / 7,000 / 17,500 Alien coins  
**Matchmaking:** Players grouped by buy-in amount  
**State Persistence:** Redis with 10-minute TTL

### 4.3 Game Play

**Number Calling Interval:** 3 seconds per number  
**Display:** Only current + previous number (no history)  
**Polling Rate:** 1.5 seconds (frontend)  
**Manual Marking:** Player clicks to mark called numbers  
**No Auto-Mark:** Strategic memory challenge

### 4.4 Win Conditions

**Valid Patterns:**
- 3 Rows: Horizontal lines
- 3 Columns: Vertical lines  
- 2 Diagonals: Top-left to bottom-right, Top-right to bottom-left

**Claim Process:**
1. Player clicks "CLAIM BINGO" button
2. Backend verifies ALL 8 possible patterns
3. First valid claim wins pot
4. Invalid claims result in kick

**No Winner Scenario:**
- All 50 numbers called without valid claim → House keeps pot
- All players kicked for false claims → House keeps pot

### 4.5 Payment Flow

**Entry Fee:**
- User selects buy-in amount
- Frontend creates invoice via backend
- Payment requested through Alien SDK
- Webhook confirms transaction
- Player added to lobby

**Winner Payout:**
- **Phase 1 (MVP):** Manual payout after demo
- **Phase 2:** Automated if Alien API supports programmatic sends

---

## 5. Data Models

### 5.1 Pydantic Models (Backend)

```python
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime

class NumberSelection(BaseModel):
    numbers: List[int] = Field(..., min_items=9, max_items=9)
    
    @validator('numbers')
    def validate_numbers(cls, v):
        if len(set(v)) != 9:
            raise ValueError("Numbers must be unique")
        if not all(1 <= n <= 50 for n in v):
            raise ValueError("Numbers must be between 1 and 50")
        return v

class GridArrangement(BaseModel):
    grid: List[List[int]]  # 3x3 nested list
    
    @validator('grid')
    def validate_grid(cls, v):
        if len(v) != 3 or any(len(row) != 3 for row in v):
            raise ValueError("Grid must be 3x3")
        flat = [n for row in v for n in row]
        if len(set(flat)) != 9:
            raise ValueError("Grid must contain 9 unique numbers")
        return v

class Player(BaseModel):
    alien_id: str
    numbers: List[int]
    grid: List[List[int]]
    active: bool = True
    joined_at: datetime

class GameState(BaseModel):
    lobby_id: str
    status: Literal['forming', 'arranging', 'active', 'finished']
    buy_in_amount: int
    pot: int
    players: dict[str, Player]
    numbers_called: List[int] = []
    latest_number: Optional[int] = None
    previous_number: Optional[int] = None
    winner: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

class InvoiceRequest(BaseModel):
    alien_id: str
    buy_in_amount: int
    lobby_id: str

class InvoiceResponse(BaseModel):
    invoice_id: str
    amount: str
    recipient: str

class ClaimRequest(BaseModel):
    alien_id: str

class ClaimResponse(BaseModel):
    valid: bool
    winner: bool = False
    kicked: bool = False
    pot: Optional[int] = None
    message: str
    pattern: Optional[str] = None
```

### 5.2 TypeScript Types (Frontend)

```typescript
// types.ts
export interface Player {
  alien_id: string;
  numbers: number[];
  grid: number[][];
  active: boolean;
  joined_at: string;
}

export interface GameStatus {
  lobby_id: string;
  status: 'forming' | 'arranging' | 'active' | 'finished';
  buy_in_amount: number;
  pot: number;
  player_count: number;
  players: Record<string, Player>;
  latest_number: number | null;
  previous_number: number | null;
  winner: string | null;
  time_elapsed: number;
}

export interface ClaimResult {
  valid: boolean;
  winner: boolean;
  kicked: boolean;
  pot?: number;
  message: string;
  pattern?: string;
}
```

---

## 6. Backend API Specification

### Base URL
```
Development:  http://localhost:8000
Production:   https://{your-ngrok-url}.ngrok.io
```

### Authentication
All endpoints (except `/health` and `/webhook`) require Alien JWT:
```
Authorization: Bearer <alien_jwt_token>
```

### Endpoints

#### 6.1 Health Check

```http
GET /health
```

**Response 200:**
```json
{
  "status": "healthy",
  "redis_connected": true,
  "timestamp": "2026-02-08T10:00:00Z"
}
```

---

#### 6.2 Create Invoice

```http
POST /api/invoices
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "alien_id": "user_abc123",
  "buy_in_amount": 3500,
  "lobby_id": "lobby_xyz789"
}
```

**Response 200:**
```json
{
  "invoice_id": "inv_abc123",
  "amount": "3500",
  "recipient": "YOUR_ALIEN_PROVIDER_ADDRESS"
}
```

**Implementation:**
1. Validate JWT → extract alien_id
2. Generate unique invoice_id (UUID)
3. Store in Redis: `invoice:{invoice_id}` → {alien_id, lobby_id, amount, status}
4. Return invoice for frontend payment

---

#### 6.3 Join Lobby

```http
POST /api/game/join
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "alien_id": "user_abc123",
  "buy_in_amount": 3500
}
```

**Response 200:**
```json
{
  "lobby_id": "lobby_xyz789",
  "status": "forming",
  "player_count": 3,
  "pot": 10500
}
```

**Implementation:**
1. Validate JWT
2. Check for available lobby with matching buy_in_amount
3. If found and not full → add player
4. If not found → create new lobby
5. Check if player already in this lobby → reject
6. Return lobby info

---

#### 6.4 Submit Numbers

```http
POST /api/game/{lobby_id}/numbers/select
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "alien_id": "user_abc123",
  "numbers": [5, 12, 23, 7, 34, 45, 2, 19, 38]
}
```

**Response 200:**
```json
{
  "success": true,
  "message": "Numbers selected. Now arrange your grid."
}
```

**Validation:**
- Exactly 9 numbers
- All unique
- All in range 1-50

---

#### 6.5 Submit Grid Arrangement

```http
POST /api/game/{lobby_id}/numbers/arrange
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "alien_id": "user_abc123",
  "grid": [
    [12, 23, 45],
    [7, 34, 50],
    [2, 19, 38]
  ]
}
```

**Response 200:**
```json
{
  "success": true,
  "verified": true,
  "message": "Grid arrangement verified"
}
```

**Validation:**
- 3x3 structure
- All 9 positions filled
- All numbers unique
- Matches previously selected numbers

---

#### 6.6 Get Game Status

```http
GET /api/game/{lobby_id}/status
Authorization: Bearer <jwt>
```

**Response 200:**
```json
{
  "lobby_id": "lobby_xyz789",
  "status": "active",
  "buy_in_amount": 3500,
  "pot": 35000,
  "player_count": 10,
  "players": {
    "user_abc123": {
      "alien_id": "user_abc123",
      "numbers": [5, 12, 23, 7, 34, 45, 2, 19, 38],
      "grid": [[12,23,45], [7,34,50], [2,19,38]],
      "active": true,
      "joined_at": "2026-02-08T10:00:00Z"
    }
  },
  "latest_number": 23,
  "previous_number": 7,
  "winner": null,
  "time_elapsed": 45
}
```

**Note:** `numbers_called` array is NOT included (server-side only)

---

#### 6.7 Claim Bingo

```http
POST /api/game/{lobby_id}/claim
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "alien_id": "user_abc123"
}
```

**Response 200 (Valid):**
```json
{
  "valid": true,
  "winner": true,
  "pot": 35000,
  "message": "🎉 YOU WON! +35,000 Alien coins",
  "pattern": "row_1"
}
```

**Response 400 (Invalid):**
```json
{
  "valid": false,
  "kicked": true,
  "message": "Invalid claim. You've been removed from the game.",
  "missing_numbers": [23, 45]
}
```

**Verification Logic:**
1. Check if game is active
2. Check if player is active
3. Get player's grid
4. Test all 8 patterns (3 rows + 3 cols + 2 diagonals)
5. For each pattern: verify all 3 numbers in `numbers_called`
6. If any pattern valid → Winner
7. If no pattern valid → Kick player

---

#### 6.8 Payment Webhook

```http
POST /api/webhooks/payment
Content-Type: application/json
X-Webhook-Signature: <ed25519_signature_hex>

{
  "invoice": "inv_abc123",
  "status": "finalized",
  "txHash": "...",
  "amount": "3500",
  "token": "ALIEN",
  "network": "alien",
  "test": false
}
```

**Response 200:**
```json
{
  "success": true
}
```

**Implementation:**
1. Read raw body as bytes
2. Get X-Webhook-Signature header
3. Verify Ed25519 signature with WEBHOOK_PUBLIC_KEY
4. If invalid → 401 Unauthorized
5. Parse JSON payload
6. Find payment intent by invoice ID
7. If status == "finalized":
   - Increment lobby pot
   - Mark player as paid
   - Check if lobby should transition to next state
8. Return success

---

## 7. Frontend Implementation

### 7.1 Project Structure

```
frontend/
├── src/
│   ├── App.tsx                  # Root with AlienProvider
│   ├── main.tsx                 # Entry point
│   ├── config.ts                # API URL, constants
│   ├── hooks/
│   │   ├── useGameState.ts      # Polling hook
│   │   ├── usePayment.ts        # Payment flow
│   │   └── useAuth.ts           # Alien auth wrapper
│   ├── components/
│   │   ├── Lobby.tsx            # Waiting room
│   │   ├── NumberSelector.tsx   # Pick 9 numbers
│   │   ├── GridArranger.tsx     # Drag-drop 3x3 grid
│   │   ├── BingoCard.tsx        # Game card display
│   │   ├── NumberDisplay.tsx    # Current/previous numbers
│   │   ├── ClaimButton.tsx      # Bingo claim
│   │   ├── WinnerScreen.tsx     # Victory UI
│   │   ├── KickedScreen.tsx     # Invalid claim UI
│   │   └── LoadingSpinner.tsx   # Loading states
│   ├── services/
│   │   └── api.ts               # API client
│   └── types.ts                 # TypeScript definitions
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── index.html
```

### 7.2 Key Hooks

#### useAlien Hook (from @alien_org/react)

```typescript
import { useAlien } from '@alien_org/react';

function MyComponent() {
  const { authToken, isReady } = useAlien();
  
  // authToken: JWT for backend API calls
  // isReady: true when Mini App fully loaded
}
```

#### usePayment Hook (from @alien_org/react)

```typescript
import { usePayment } from '@alien_org/react';

function PaymentComponent() {
  const { pay, isPaid, isLoading, txHash, errorCode } = usePayment({
    onPaid: (txHash) => console.log('Payment successful!', txHash),
    onCancelled: () => console.log('User cancelled'),
    onFailed: (errorCode) => console.error('Payment failed:', errorCode)
  });

  async function handleBuyIn() {
    // Step 1: Create invoice on backend
    const { invoice_id } = await fetch('/api/invoices', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        alien_id: myAlienId,
        buy_in_amount: 3500,
        lobby_id: currentLobbyId
      })
    }).then(r => r.json());

    // Step 2: Request payment
    await pay({
      recipient: 'YOUR_ALIEN_PROVIDER_ADDRESS',
      amount: '3500',  // String!
      token: 'ALIEN',
      network: 'alien',
      invoice: invoice_id,
      item: {
        title: 'Bingo Entry Fee',
        iconUrl: 'https://your-app.com/icon.png',
        quantity: 1
      },
      test: 'paid'  // For testing only
    });
  }
}
```

#### useGameState Hook (Custom)

```typescript
// hooks/useGameState.ts
import { useState, useEffect } from 'react';
import { GameStatus } from '../types';

export function useGameState(lobbyId: string | null, authToken: string) {
  const [gameState, setGameState] = useState<GameStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!lobbyId || !authToken) return;

    const interval = setInterval(async () => {
      try {
        const response = await fetch(`/api/game/${lobbyId}/status`, {
          headers: { Authorization: `Bearer ${authToken}` }
        });
        
        if (response.ok) {
          const data = await response.json();
          setGameState(data);
        } else {
          setError('Failed to fetch game state');
        }
      } catch (err) {
        setError(err.message);
      }
    }, 1500); // Poll every 1.5 seconds

    return () => clearInterval(interval);
  }, [lobbyId, authToken]);

  return { gameState, error };
}
```

### 7.3 Component Examples

#### App.tsx

```typescript
import { AlienProvider } from '@alien_org/react';
import GameFlow from './components/GameFlow';

function App() {
  return (
    <AlienProvider autoReady={true}>
      <div className="min-h-screen bg-gray-900 text-white">
        <GameFlow />
      </div>
    </AlienProvider>
  );
}

export default App;
```

#### NumberSelector.tsx

```typescript
import { useState } from 'react';

interface Props {
  onConfirm: (numbers: number[]) => void;
}

export default function NumberSelector({ onConfirm }: Props) {
  const [selected, setSelected] = useState<number[]>([]);

  const toggleNumber = (num: number) => {
    if (selected.includes(num)) {
      setSelected(selected.filter(n => n !== num));
    } else if (selected.length < 9) {
      setSelected([...selected, num]);
    }
  };

  return (
    <div className="p-4">
      <h2 className="text-2xl font-bold mb-4">
        Select 9 Numbers ({selected.length}/9)
      </h2>
      
      <div className="grid grid-cols-10 gap-2 mb-6">
        {Array.from({ length: 50 }, (_, i) => i + 1).map(num => (
          <button
            key={num}
            onClick={() => toggleNumber(num)}
            className={`
              h-12 rounded-lg font-bold text-lg
              ${selected.includes(num) 
                ? 'bg-green-500 text-white' 
                : 'bg-gray-700 text-gray-300'}
              hover:scale-105 transition-transform
            `}
          >
            {num}
          </button>
        ))}
      </div>

      <button
        onClick={() => onConfirm(selected)}
        disabled={selected.length !== 9}
        className="w-full py-3 bg-blue-600 rounded-lg font-bold disabled:opacity-50"
      >
        Confirm Selection
      </button>
    </div>
  );
}
```

---

## 8. Alien Integration

### 8.1 Mini App Configuration

**Dev Portal Settings:**
- **Name:** Fair Bingo
- **Provider URL:** https://{your-ngrok}.ngrok.io
- **Allowed Origins:** https://{your-ngrok}.ngrok.io
- **Icon:** 512×512 PNG logo
- **Description:** "Multiplayer Bingo with verified human players"

### 8.2 Authentication Flow

```typescript
// Frontend: Auto-injected JWT
import { useAlien } from '@alien_org/react';

function MyComponent() {
  const { authToken, isReady } = useAlien();
  
  useEffect(() => {
    if (isReady && authToken) {
      // Token available for API calls
      localStorage.setItem('alien_token', authToken);
    }
  }, [isReady, authToken]);
}
```

```python
# Backend: Verify JWT
from fastapi import Depends, HTTPException, Header
import jwt
import httpx

async def verify_alien_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth header")
    
    token = authorization.split(" ")[1]
    
    # Fetch JWKS from Alien SSO
    async with httpx.AsyncClient() as client:
        response = await client.get("https://sso.alien-api.com/oauth/jwks")
        jwks = response.json()
    
    # Verify JWT signature
    try:
        payload = jwt.decode(
            token,
            key=jwks,
            algorithms=["RS256"],
            audience="YOUR_PROVIDER_ADDRESS",
            issuer="https://sso.alien-api.com"
        )
        return payload["sub"]  # alien_id
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### 8.3 Payment Integration

**Frontend Payment Flow:**

```typescript
import { usePayment } from '@alien_org/react';

function BuyInButton() {
  const { pay } = usePayment({
    onPaid: async (txHash) => {
      console.log('Payment confirmed!', txHash);
      // Poll for webhook confirmation
      await waitForPaymentConfirmation(invoiceId);
    },
    onCancelled: () => alert('Payment cancelled'),
    onFailed: (errorCode) => alert(`Payment failed: ${errorCode}`)
  });

  async function handleBuyIn() {
    // Create invoice
    const invoice = await createInvoice(alienId, buyInAmount, lobbyId);
    
    // Request payment
    await pay({
      recipient: PROVIDER_ADDRESS,
      amount: String(buyInAmount),
      token: 'ALIEN',
      network: 'alien',
      invoice: invoice.invoice_id,
      item: {
        title: 'Bingo Entry Fee',
        iconUrl: 'https://app-url/icon.png',
        quantity: 1
      }
    });
  }
}
```

**Backend Webhook Handler:**

```python
from fastapi import Request, HTTPException
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

@app.post("/api/webhooks/payment")
async def payment_webhook(request: Request):
    # Read raw body
    body = await request.body()
    signature_hex = request.headers.get("x-webhook-signature")
    
    if not signature_hex:
        raise HTTPException(status_code=401, detail="No signature")
    
    # Verify Ed25519 signature
    public_key = ed25519.Ed25519PublicKey.from_public_bytes(
        bytes.fromhex(WEBHOOK_PUBLIC_KEY)
    )
    
    try:
        public_key.verify(
            bytes.fromhex(signature_hex),
            body
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse payload
    payload = json.loads(body)
    
    if payload["status"] == "finalized":
        # Update game state in Redis
        invoice_id = payload["invoice"]
        invoice_data = await redis.hgetall(f"invoice:{invoice_id}")
        
        lobby_id = invoice_data["lobby_id"]
        alien_id = invoice_data["alien_id"]
        amount = int(payload["amount"])
        
        # Increment pot
        await redis.hincrby(f"lobby:{lobby_id}", "pot", amount)
        
        # Mark player as paid
        await redis.hset(f"lobby:{lobby_id}:players", alien_id, "paid")
    
    return {"success": True}
```

---

## 9. Redis Schema

### 9.1 Data Structures

#### Lobby State (Hash)

```
Key:    lobby:{lobby_id}
Type:   Hash
TTL:    600 seconds (10 minutes after creation)

Fields:
  lobby_id          : string
  status            : 'forming' | 'arranging' | 'active' | 'finished'
  buy_in_amount     : int
  pot               : int
  winner            : string | null
  created_at        : timestamp
  started_at        : timestamp | null
  finished_at       : timestamp | null
```

#### Player Data (Hash per player)

```
Key:    lobby:{lobby_id}:player:{alien_id}
Type:   Hash
TTL:    Inherit from lobby

Fields:
  alien_id          : string
  numbers           : JSON array [1,5,12,...]
  grid              : JSON nested array [[...],[...],[...]]
  active            : boolean
  joined_at         : timestamp
```

#### Numbers Called (List)

```
Key:    lobby:{lobby_id}:numbers_called
Type:   List
TTL:    Inherit from lobby

Values: [12, 23, 7, 34, ...]  (pushed as game progresses)
```

#### Active Lobbies Index (Sorted Set)

```
Key:    active_lobbies:{buy_in_amount}
Type:   Sorted Set
Score:  timestamp (for sorting by creation time)
Member: lobby_id

Purpose: Find available lobbies quickly when player joins
```

#### Payment Intents (Hash)

```
Key:    invoice:{invoice_id}
Type:   Hash
TTL:    600 seconds

Fields:
  invoice_id        : string
  alien_id          : string
  lobby_id          : string
  amount            : int
  status            : 'pending' | 'finalized' | 'failed'
  created_at        : timestamp
```

### 9.2 Redis Operations Examples

```python
import redis.asyncio as aioredis
import json

redis = aioredis.from_url("redis://localhost:6379", decode_responses=True)

# Create lobby
async def create_lobby(buy_in_amount: int) -> str:
    lobby_id = f"lobby_{uuid.uuid4().hex[:8]}"
    
    await redis.hset(f"lobby:{lobby_id}", mapping={
        "lobby_id": lobby_id,
        "status": "forming",
        "buy_in_amount": buy_in_amount,
        "pot": 0,
        "created_at": datetime.utcnow().isoformat()
    })
    
    await redis.expire(f"lobby:{lobby_id}", 600)
    await redis.zadd(f"active_lobbies:{buy_in_amount}", {lobby_id: time.time()})
    
    return lobby_id

# Add player to lobby
async def add_player(lobby_id: str, alien_id: str, numbers: List[int], grid: List[List[int]]):
    await redis.hset(f"lobby:{lobby_id}:player:{alien_id}", mapping={
        "alien_id": alien_id,
        "numbers": json.dumps(numbers),
        "grid": json.dumps(grid),
        "active": "true",
        "joined_at": datetime.utcnow().isoformat()
    })

# Get lobby state
async def get_lobby(lobby_id: str) -> dict:
    lobby_data = await redis.hgetall(f"lobby:{lobby_id}")
    
    # Get all players
    player_keys = await redis.keys(f"lobby:{lobby_id}:player:*")
    players = {}
    for key in player_keys:
        player_data = await redis.hgetall(key)
        alien_id = player_data["alien_id"]
        players[alien_id] = {
            "alien_id": alien_id,
            "numbers": json.loads(player_data["numbers"]),
            "grid": json.loads(player_data["grid"]),
            "active": player_data["active"] == "true"
        }
    
    lobby_data["players"] = players
    return lobby_data

# Call number
async def call_number(lobby_id: str, number: int):
    await redis.rpush(f"lobby:{lobby_id}:numbers_called", number)
    await redis.hset(f"lobby:{lobby_id}", "latest_number", number)
    
    # Get previous number
    numbers_called = await redis.lrange(f"lobby:{lobby_id}:numbers_called", -2, -2)
    if numbers_called:
        await redis.hset(f"lobby:{lobby_id}", "previous_number", numbers_called[0])
```

---

## 10. Game Flow State Machine

```
┌──────────┐
│ forming  │  ← Players joining, selecting numbers
└────┬─────┘
     │ Trigger: Min 2 players + (timer expired OR 10 players)
     ↓
┌──────────┐
│arranging │  ← Players arranging 3x3 grids (90s timer)
└────┬─────┘
     │ Trigger: All players arranged OR timer expired
     ↓
┌──────────┐
│  active  │  ← Numbers being called every 3 seconds
└────┬─────┘
     │ Trigger: Valid claim OR all 50 numbers called
     ↓
┌──────────┐
│ finished │  ← Winner determined, payouts processed
└──────────┘
```

### State Transition Logic

```python
async def check_state_transition(lobby_id: str):
    lobby = await redis.hgetall(f"lobby:{lobby_id}")
    status = lobby["status"]
    
    if status == "forming":
        player_count = await redis.hlen(f"lobby:{lobby_id}:players")
        created_at = datetime.fromisoformat(lobby["created_at"])
        time_elapsed = (datetime.utcnow() - created_at).seconds
        
        if player_count >= 2 and (time_elapsed >= 120 or player_count >= 10):
            await redis.hset(f"lobby:{lobby_id}", "status", "arranging")
            # Start 90-second arrangement timer
            asyncio.create_task(arrangement_timer(lobby_id))
    
    elif status == "arranging":
        # Check if all players have arranged
        all_arranged = await check_all_players_arranged(lobby_id)
        if all_arranged:
            await redis.hset(f"lobby:{lobby_id}", "status", "active")
            await redis.hset(f"lobby:{lobby_id}", "started_at", datetime.utcnow().isoformat())
            # Start number calling
            asyncio.create_task(call_numbers_task(lobby_id))
    
    elif status == "active":
        # State transitions handled by claim verification
        pass
```

---

## 11. Implementation Checklist

### Phase 1: Backend Foundation (2 hours)

- [ ] FastAPI project setup
  - [ ] `main.py` with app initialization
  - [ ] `.env` file with config
  - [ ] `requirements.txt` dependencies
  
- [ ] Redis connection
  - [ ] `redis_client.py` with async client
  - [ ] Connection health check
  - [ ] Test basic operations
  
- [ ] JWT authentication
  - [ ] `auth.py` middleware
  - [ ] JWKS fetching from Alien SSO
  - [ ] Token verification dependency
  
- [ ] API routes structure
  - [ ] `/health` endpoint
  - [ ] `/api/invoices` endpoint
  - [ ] `/api/game/*` endpoints skeleton
  - [ ] `/api/webhooks/payment` endpoint

### Phase 2: Game Logic (2 hours)

- [ ] Lobby management
  - [ ] `lobby.py` with create/join logic
  - [ ] Player addition/removal
  - [ ] State transitions
  
- [ ] Number calling system
  - [ ] Background task with `asyncio`
  - [ ] 3-second interval
  - [ ] Store in Redis list
  
- [ ] Win verification
  - [ ] Pattern checking (8 patterns)
  - [ ] Claim validation
  - [ ] Player kicking logic

### Phase 3: Frontend Core (2 hours)

- [ ] React setup
  - [ ] Vite project initialization
  - [ ] Tailwind CSS configuration
  - [ ] @alien_org/react installation
  
- [ ] Components
  - [ ] App.tsx with AlienProvider
  - [ ] NumberSelector component
  - [ ] GridArranger component
  - [ ] BingoCard component
  - [ ] NumberDisplay component
  
- [ ] Hooks
  - [ ] useGameState polling hook
  - [ ] useAuth wrapper
  - [ ] usePayment integration

### Phase 4: Payment Integration (1.5 hours)

- [ ] Invoice creation
  - [ ] Backend endpoint implementation
  - [ ] Redis storage
  
- [ ] Payment flow
  - [ ] Frontend payment button
  - [ ] usePayment hook setup
  - [ ] Success/failure handling
  
- [ ] Webhook handler
  - [ ] Ed25519 signature verification
  - [ ] Payment confirmation logic
  - [ ] Lobby state updates

### Phase 5: Testing & Polish (1.5 hours)

- [ ] End-to-end game flow test
  - [ ] Join lobby
  - [ ] Select numbers
  - [ ] Arrange grid
  - [ ] Play game
  - [ ] Claim win
  
- [ ] Multi-device testing
  - [ ] 2-3 phones/browsers
  - [ ] Simultaneous gameplay
  
- [ ] UI polish
  - [ ] Loading states
  - [ ] Error messages
  - [ ] Animations
  
- [ ] Error handling
  - [ ] Network failures
  - [ ] Invalid claims
  - [ ] Payment failures

### Phase 6: Deployment (30 minutes)

- [ ] ngrok setup
  - [ ] Start tunnel
  - [ ] Update frontend API URL
  
- [ ] Alien Dev Portal
  - [ ] Update allowed origins
  - [ ] Set webhook URL
  - [ ] Test via deeplink
  
- [ ] Final testing
  - [ ] Full game with real payments
  - [ ] Verify webhook confirmations

---

## Appendix A: Environment Variables

```bash
# Backend (.env)
REDIS_URL=redis://localhost:6379
ALIEN_PROVIDER_ADDRESS=your_provider_address_from_dev_portal
WEBHOOK_PUBLIC_KEY=ed25519_public_key_hex_from_dev_portal
ALLOWED_ORIGINS=https://your-ngrok-url.ngrok.io
```

```bash
# Frontend (.env)
VITE_API_URL=https://your-ngrok-url.ngrok.io
VITE_PROVIDER_ADDRESS=your_provider_address_from_dev_portal
```

---

## Appendix B: Key Commands

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev

# Redis
redis-server

# ngrok
ngrok http 5173
```

---

## Appendix C: Testing Scenarios

### Scenario 1: Happy Path
1. User joins lobby
2. Selects 9 numbers
3. Arranges grid
4. Game starts
5. Numbers called
6. User claims valid Bingo
7. Wins pot

### Scenario 2: Invalid Claim
1. User joins game
2. Claims Bingo too early
3. Backend verifies: invalid
4. User kicked from game
5. Game continues for others

### Scenario 3: No Winner
1. All 50 numbers called
2. No valid claims
3. House keeps pot
4. Game ends

### Scenario 4: Payment Failure
1. User starts buy-in
2. Payment webhook returns "failed"
3. Player not added to lobby
4. User prompted to retry

---

**END OF DOCUMENT**

This comprehensive guide provides all specifications needed to implement Fair Bingo with FastAPI + React + Redis stack.