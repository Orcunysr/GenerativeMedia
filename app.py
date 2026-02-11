"""
Backend API: Chat endpoint for the GenerativeMedia graph.
Session state kept in memory; optional image upload.
"""
import os
import sys
import uuid
from pathlib import Path

# Patch / path (same as main.py)
try:
    import langchain_core.pydantic_v1
except ImportError:
    try:
        from pydantic import v1 as pydantic_v1
        sys.modules["langchain_core.pydantic_v1"] = pydantic_v1
    except ImportError:
        pass
sys.path.insert(0, os.getcwd())

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from graph.chains.product_description import get_product_description_llm
from graph.graph import graph
from graph.state import State

# Session store: session_id -> state (dict)
sessions: dict[str, dict] = {}

# Uploads dir (created on first upload)
UPLOADS_DIR = Path(__file__).resolve().parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

STATE_COLLECTED_KEYS = (
    "url", "url_content", "tavily_search_results", "items_story",
    "items_image_address", "user_image_address", "user_prompt",
    "poster_promt", "video_promt", "items_quality",
)


def parse_turn(line: str, state: State, image_path: str | None = None) -> State:
    """Parse user message (and optional image path) into state updates."""
    line = (line or "").strip()
    updates: dict = {}
    if image_path:
        updates["user_image_address"] = image_path
        updates["question"] = line or "Poster ve reklam videosu oluştur."
    if not line and not image_path:
        return {**state, **updates}
    lower = line.lower()
    if lower.startswith("foto:") or lower.startswith("resim:"):
        path = line.split(":", 1)[1].strip().strip('"\'')
        if os.path.isfile(path):
            updates["user_image_address"] = path
            updates["question"] = "Poster ve reklam videosu oluştur."
        return {**state, **updates} if updates else state
    if lower.startswith("url:") or lower.startswith("ürün:"):
        url = line.split(":", 1)[1].strip().strip('"\'')
        if url.startswith("http://") or url.startswith("https://"):
            updates["url"] = url
            updates["question"] = state.get("question") or "Ürün bilgisi topla."
        return {**state, **updates} if updates else state
    if lower.startswith("ürün hikaye:") or lower.startswith("items_story:"):
        story = line.split(":", 1)[1].strip().strip('"\'')
        updates["items_story"] = story
        return {**state, **updates} if updates else state
    if line.startswith("http://") or line.startswith("https://"):
        updates["url"] = line
        # Soruyu URL olarak bırak: gather_finish "sadece URL" görünce tema sorusu sorar; "poster/video" yazarsak direkt 5 seçenek üretir.
        updates["question"] = line
        return {**state, **updates}
    if not image_path and os.path.isfile(line):
        updates["user_image_address"] = line
        updates["question"] = "Poster ve reklam videosu oluştur."
        return {**state, **updates}
    updates["question"] = line
    return {**state, **updates}


def state_summary(state: dict) -> dict:
    """JSON-safe state summary for the client."""
    out = {}
    for key in STATE_COLLECTED_KEYS:
        v = state.get(key)
        if v is None or v == "":
            continue
        if key == "tavily_search_results" and isinstance(v, list):
            out[key] = f"{len(v)} sonuç"
        elif key == "items_image_address":
            out[key] = v
        elif isinstance(v, str) and len(v) > 100:
            out[key] = v[:100] + "..."
        else:
            out[key] = v
    return out


app = FastAPI(title="GenerativeMedia Chat API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/chat")
async def chat(
    message: str = Form(""),
    session_id: str | None = Form(None),
    image: UploadFile | None = File(None),
):
    """Send a message (and optional image). Returns assistant reply and optional poster/video URLs."""
    sid = session_id or str(uuid.uuid4())
    state = sessions.get(sid)
    if state is None:
        state = {}
    # Normalize: remove non-JSON-safe keys from loaded state so graph doesn't break
    state = {k: v for k, v in state.items() if k != "messages" or (isinstance(v, list) and len(v) < 1000)}

    image_path = None
    if image and image.filename:
        ext = Path(image.filename).suffix or ".jpg"
        path = UPLOADS_DIR / f"{sid}_{uuid.uuid4().hex}{ext}"
        content = await image.read()
        path.write_bytes(content)
        image_path = str(path.resolve())

    state = parse_turn(message, state, image_path)
    if not state.get("question") and not state.get("user_image_address"):
        raise HTTPException(status_code=400, detail="Mesaj veya görsel gerekli.")

    try:
        result = graph.invoke(state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    history = list(state.get("conversation_history") or [])
    history.append(f"User: {message or '(görsel yüklendi)'}")
    history.append(f"Assistant: {result.get('generated') or ''}")
    new_state = {**result, "conversation_history": history}
    # Don't store huge messages list long-term
    if "messages" in new_state and len(new_state.get("messages", [])) > 20:
        new_state["messages"] = new_state["messages"][-20:]
    sessions[sid] = new_state

    # Tema ekranında fotoğraf altında: LLM'in yazdığı kısa ürün açıklaması (ham sayfa metni değil)
    product_description = ""
    if new_state.get("items_story") or new_state.get("url_content"):
        if not new_state.get("poster_image_address"):
            product_description = get_product_description_llm(new_state)
        if not product_description:
            raw = (new_state.get("items_story") or new_state.get("url_content") or "").strip()
            product_description = raw[:400] + ("…" if len(raw) > 400 else "") if raw else ""

    return {
        "session_id": sid,
        "generated": new_state.get("generated") or "",
        "poster_image_address": new_state.get("poster_image_address"),
        "video_image_address": new_state.get("video_image_address"),
        "video_scenario": new_state.get("video_scenario"),
        "prompt_options": new_state.get("prompt_options"),  # 5 farklı prompt; kullanıcı 1-5 seçer
        "state_summary": state_summary(new_state),
        "product_description": product_description,  # Foto altında: LLM ürün açıklaması
    }


# Static files (frontend)
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    """Serve chat UI."""
    p = STATIC_DIR / "index.html"
    if not p.exists():
        raise HTTPException(status_code=404, detail="static/index.html not found")
    return FileResponse(p)
