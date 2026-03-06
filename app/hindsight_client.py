import httpx
import os
import logging

logger = logging.getLogger(__name__)

HINDSIGHT_URL = os.getenv("HINDSIGHT_URL", "http://hindsight:8888")
BANK_NAME = "digital-twin"


async def _client():
    return httpx.AsyncClient(base_url=HINDSIGHT_URL, timeout=30.0)


async def ensure_bank():
    async with await _client() as client:
        try:
            resp = await client.get(f"/banks/{BANK_NAME}")
            if resp.status_code == 200:
                return
        except Exception:
            pass

        resp = await client.post("/banks", json={
            "name": BANK_NAME,
            "description": "Digital Twin memory bank"
        })
        if resp.status_code in (200, 201, 409):
            logger.info("Bank '%s' ready", BANK_NAME)
        else:
            logger.error("Failed to create bank: %s %s", resp.status_code, resp.text)


async def retain(text: str, metadata: dict | None = None):
    async with await _client() as client:
        payload = {
            "bank": BANK_NAME,
            "content": text,
        }
        if metadata:
            payload["metadata"] = metadata

        resp = await client.post("/retain", json=payload)
        resp.raise_for_status()
        return resp.json()


async def recall(query: str, limit: int = 10):
    async with await _client() as client:
        resp = await client.post("/recall", json={
            "bank": BANK_NAME,
            "query": query,
            "limit": limit,
        })
        resp.raise_for_status()
        return resp.json()


async def reflect():
    async with await _client() as client:
        resp = await client.post("/reflect", json={
            "bank": BANK_NAME,
        })
        resp.raise_for_status()
        return resp.json()


async def get_memories(limit: int = 50):
    async with await _client() as client:
        resp = await client.post("/recall", json={
            "bank": BANK_NAME,
            "query": "alles was ich gesagt und erlebt habe",
            "limit": limit,
        })
        if resp.status_code == 200:
            return resp.json()
        return []


async def get_mental_models():
    async with await _client() as client:
        resp = await client.post("/recall", json={
            "bank": BANK_NAME,
            "query": "wie ticke ich, meine Denkweise, Entscheidungsmuster, Werte",
            "limit": 20,
        })
        if resp.status_code == 200:
            return resp.json()
        return []


async def health_check():
    try:
        async with await _client() as client:
            resp = await client.get("/health")
            return resp.status_code == 200
    except Exception:
        return False
