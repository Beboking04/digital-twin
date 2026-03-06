import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import hindsight_client

app = FastAPI(title="Digital Twin Dashboard")

templates = Jinja2Templates(directory="/app/templates")
os.makedirs("/app/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="/app/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
async def health():
    hindsight_ok = await hindsight_client.health_check()
    return {
        "status": "ok",
        "hindsight": "online" if hindsight_ok else "offline",
    }


@app.get("/api/memories")
async def get_memories(q: str = ""):
    if q:
        results = await hindsight_client.recall(q)
    else:
        results = await hindsight_client.get_memories()
    return {"memories": results}


@app.get("/api/mental-models")
async def get_mental_models():
    results = await hindsight_client.get_mental_models()
    return {"models": results}


@app.get("/api/stats")
async def get_stats():
    return await hindsight_client.get_stats()


@app.post("/api/reflect")
async def trigger_reflect():
    result = await hindsight_client.reflect()
    return {"result": result}


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    query = body.get("message", "")
    if not query:
        return {"error": "No message provided"}

    from bot import get_twin_response
    response = await get_twin_response(query)
    return {"response": response}
