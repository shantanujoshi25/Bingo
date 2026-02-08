import redis.asyncio as aioredis
import os
from dotenv import load_dotenv

load_dotenv()

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
redis = aioredis.from_url(redis_url, decode_responses=True)

async def check_redis_connection():
    try:
        await redis.ping()
        return True
    except Exception:
        return False
