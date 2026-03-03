# Bingo with Aliens

Multiplayer bingo game built for the [Alien](https://aliengo.xyz) mini app platform. Built during the [Alien Genesis Hackathon](https://luma.com/alien-genesis-hack?tk=dC4IfU) (Feb 2026, SF) — placed Top 5.

Players join lobbies, pick 9 numbers on a 3x3 grid, and mark them off as numbers are called. First valid bingo wins the pot.

## Why Alien

Alien is building a super app with ID-verified users and integrated payments (Alien Coin). Every user on the platform is a real, verified person — which matters for a game where real money is on the line. No bots, no duplicate accounts, no fraud.

The Alien Bridge SDK handles authentication, so the app doesn't need its own login or identity system. Players are identified by their `alien_id`, and the platform's built-in payment rails mean the game can handle buy-ins and pot payouts natively once programmatic transfers ship.

## Stack

- **Frontend:** React + TypeScript + Tailwind CSS (Vite)
- **Backend:** FastAPI (Python)
- **State:** Redis
- **Auth:** Alien Bridge SDK
- **Hosting:** Railway

## Prerequisites

- Python 3.10+
- Node.js 18+
- Redis running on `localhost:6379` (or set `REDIS_URL` env var)

## Running locally

**1. Start Redis**

```bash
redis-server
```

**2. Backend**

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**3. Frontend**

```bash
cd frontend
npm install
npm run dev
```

App runs at `http://localhost:5173`. Frontend proxies `/api` requests to the backend via Vite config.

**Environment variables**

- `REDIS_URL` — Redis connection string (defaults to `redis://localhost:6379`)
- `VITE_PROVIDER_ADDRESS` — Alien provider address from the dev portal

## Deployment

Hosted on Railway with auto-deploy on push. The Dockerfile builds the frontend, copies the static files into the backend, and FastAPI serves everything. Redis is provisioned as a Railway service.

## How it works

1. Browse open lobbies and join one (3,500 coin buy-in)
2. Pick 9 numbers (1-20) and arrange them on your 3x3 grid
3. Numbers are called every 3 seconds once the game starts
4. Mark your grid as numbers come up
5. Claim bingo when you have a winning line (row, column, or diagonal)
6. Valid claim wins the entire pot — bad claim kicks you out
