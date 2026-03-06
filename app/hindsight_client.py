import httpx
import os
import logging

logger = logging.getLogger(__name__)

HINDSIGHT_URL = os.getenv("HINDSIGHT_URL", "http://hindsight:8888")
BANK_ID = "digital-twin"
BASE = f"/v1/default/banks/{BANK_ID}"


def _client():
    return httpx.AsyncClient(base_url=HINDSIGHT_URL, timeout=60.0)


async def ensure_bank():
    async with _client() as client:
        resp = await client.get(f"{BASE}")
        if resp.status_code == 200:
            logger.info("Bank '%s' exists", BANK_ID)
            return

        resp = await client.put(BASE, json={
            "retain_extraction_mode": "verbose",
        })
        if resp.status_code in (200, 201):
            logger.info("Bank '%s' created", BANK_ID)
        else:
            logger.error("Failed to create bank: %s %s", resp.status_code, resp.text)


async def retain(text: str, metadata: dict | None = None):
    async with _client() as client:
        item = {"content": text}
        if metadata:
            tags = [f"{k}:{v}" for k, v in metadata.items()]
            item["tags"] = tags

        resp = await client.post(f"{BASE}/memories", json={
            "items": [item],
        })
        resp.raise_for_status()
        return resp.json()


async def recall(query: str, limit: int = 10):
    async with _client() as client:
        resp = await client.post(f"{BASE}/memories/recall", json={
            "query": query,
            "max_tokens": 4096,
        })
        resp.raise_for_status()
        return resp.json()


async def reflect(query: str = "Was sind meine wichtigsten Denkmuster, Werte und Entscheidungsweisen?"):
    async with _client() as client:
        resp = await client.post(f"{BASE}/reflect", json={
            "query": query,
        })
        resp.raise_for_status()
        return resp.json()


async def get_memories(limit: int = 50):
    async with _client() as client:
        resp = await client.get(f"{BASE}/memories/list")
        if resp.status_code == 200:
            return resp.json()
        return []


async def get_mental_models():
    async with _client() as client:
        resp = await client.get(f"{BASE}/mental-models")
        if resp.status_code == 200:
            return resp.json()
        return []


async def get_stats():
    async with _client() as client:
        resp = await client.get(f"{BASE}/stats")
        if resp.status_code == 200:
            return resp.json()
        return {}


async def health_check():
    try:
        async with _client() as client:
            resp = await client.get("/health")
            return resp.status_code == 200
    except Exception:
        return False
