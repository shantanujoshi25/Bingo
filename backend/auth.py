from fastapi import Depends, HTTPException, Header
from jose import jwt, jwk
from jose.exceptions import JOSEError
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

ALIEN_SSO_URL = "https://sso.alien-api.com/oauth/jwks"
AUDIENCE = os.getenv("ALIEN_PROVIDER_ADDRESS")
ISSUER = "https://sso.alien-api.com"
DEV_MODE = os.getenv("DEV_MODE", "true").lower() == "true"

async def get_jwks():
    async with httpx.AsyncClient() as client:
        response = await client.get(ALIEN_SSO_URL)
        response.raise_for_status()
        return response.json()

async def verify_alien_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth header")

    token = authorization.split(" ")[1]

    # Dev mode: accept any token, extract alien_id from body later
    if DEV_MODE:
        return token  # Return the token itself as the identity

    try:
        jwks = await get_jwks()
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
        if rsa_key:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=["RS256"],
                audience=AUDIENCE,
                issuer=ISSUER
            )
            return payload.get("sub")  # alien_id

        raise HTTPException(status_code=401, detail="Unable to find appropriate key")

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTClaimsError:
        raise HTTPException(status_code=401, detail="Incorrect claims, please check audience and issuer")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Unable to parse authentication token: {e}")
