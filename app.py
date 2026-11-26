import html
import os
import socket
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import redis

app = FastAPI(title="IEEE SIESGST Hackathon Board")

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
CONTAINER_ID = socket.gethostname()

redis_client = None
if REDIS_HOST:
    try:
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        client.ping()
        redis_client = client
    except redis.RedisError:
        redis_client = None

memory_hits = 0
memory_notes: list[str] = []


class NoteIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=200)


def get_state(increment: bool = False) -> tuple[int, list[str], bool]:
    global memory_hits
    if redis_client:
        hits = int(redis_client.incr("page_hits")) if increment else int(redis_client.get("page_hits") or 0)
        notes = redis_client.lrange("hackathon_notes", 0, -1)
        return hits, notes, True
    if increment:
        memory_hits += 1
    return memory_hits, memory_notes, False


@app.get("/health")
def health():
    hits, notes, is_persistent = get_state(increment=False)
    return {
        "status": "ok",
        "container_id": CONTAINER_ID,
        "storage": "redis" if is_persistent else "in-memory",
        "hits": hits,
        "ideas_count": len(notes),
    }


@app.post("/api/notes")
def add_note(payload: NoteIn):
    cleaned = payload.text.strip()
    if cleaned:
        if redis_client:
            redis_client.rpush("hackathon_notes", cleaned)
        else:
            memory_notes.append(cleaned)
    return {"saved": True, "container_id": CONTAINER_ID}


@app.get("/", response_class=HTMLResponse)
def home():
    hits, notes, is_persistent = get_state(increment=True)
    badge_bg = "rgba(16, 185, 129, 0.18)" if is_persistent else "rgba(245, 158, 11, 0.18)"
    badge_border = "#10B981" if is_persistent else "#F59E0B"
    badge_color = "#34D399" if is_persistent else "#FBBF24"
    badge_text = (
        "● Storage: Redis (Persistent Volume)"
        if is_persistent
        else "● Storage: In-Memory (Ephemeral)"
    )

    items_html = "".join(
        f"<li class='idea'>{html.escape(note)}</li>"
        for note in reversed(notes)
    ) or "<li class='empty'>No hackathon ideas yet — drop your first one above.</li>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>IEEE SIESGST • Docker 2026 Live Demo</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; min-height: 100vh; padding: 48px 20px;
      font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;
      color: #F8FAFC;
      background:
        radial-gradient(circle at 18% 15%, rgba(36, 150, 237, 0.28), transparent 42%),
        radial-gradient(circle at 82% 85%, rgba(16, 185, 129, 0.22), transparent 45%),
        #050914;
    }}
    .glass {{
      max-width: 740px; margin: 0 auto; padding: 34px;
      background: rgba(17, 24, 39, 0.72);
      backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
      border: 1px solid rgba(148, 163, 184, 0.22);
      border-top: 2px solid #2496ED;
      border-radius: 20px;
      box-shadow: 0 24px 60px rgba(0, 0, 0, 0.55);
    }}
    .top {{
      display: flex; justify-content: space-between; align-items: center;
      gap: 12px; flex-wrap: wrap; margin-bottom: 20px;
    }}
    .badge {{
      padding: 6px 14px; border-radius: 999px; font-size: 13px; font-weight: 700;
      background: {badge_bg}; border: 1px solid {badge_border}; color: {badge_color};
    }}
    .cid {{
      font-family: ui-monospace, 'Cascadia Code', Consolas, monospace;
      font-size: 13px; color: #38BDF8;
      background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(56, 189, 248, 0.35);
      padding: 6px 12px; border-radius: 10px;
    }}
    h1 {{ margin: 0; font-size: 30px; letter-spacing: -0.02em; }}
    .sub {{ color: #94A3B8; margin: 6px 0 22px; font-size: 15px; }}
    .stats {{
      display: flex; align-items: baseline; justify-content: space-between;
      background: rgba(15, 23, 42, 0.75); border: 1px solid rgba(148, 163, 184, 0.16);
      border-radius: 14px; padding: 16px 22px; margin-bottom: 22px;
    }}
    .metric {{ font-size: 42px; font-weight: 800; color: #38BDF8; line-height: 1; }}
    .links a {{
      color: #94A3B8; text-decoration: none; font-family: monospace; font-size: 13px;
      margin-left: 14px; padding: 5px 10px; border-radius: 8px;
      border: 1px solid rgba(148, 163, 184, 0.2);
    }}
    .links a:hover {{ color: #F8FAFC; border-color: #2496ED; }}
    form {{ display: flex; gap: 10px; margin-bottom: 22px; }}
    input {{
      flex: 1; padding: 13px 16px; border-radius: 12px;
      border: 1px solid rgba(148, 163, 184, 0.28);
      background: rgba(15, 23, 42, 0.85); color: #F8FAFC; font-size: 15px;
      outline: none;
    }}
    input:focus {{ border-color: #2496ED; }}
    button {{
      padding: 13px 22px; border-radius: 12px; border: none;
      background: linear-gradient(135deg, #2496ED, #00629B);
      color: #FFFFFF; font-weight: 700; font-size: 15px; cursor: pointer;
    }}
    ul {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; }}
    .idea {{
      padding: 13px 16px; background: rgba(30, 41, 59, 0.65);
      border: 1px solid rgba(148, 163, 184, 0.14);
      border-left: 4px solid #2496ED; border-radius: 10px; font-size: 15px;
    }}
    .empty {{ color: #64748B; text-align: center; padding: 18px; font-size: 14px; }}
  </style>
</head>
<body>
  <div class="glass">
    <div class="top">
      <div class="badge">{badge_text}</div>
      <div class="cid">Container ID: {CONTAINER_ID}</div>
    </div>
    <h1>IEEE SIESGST Hackathon Board</h1>
    <p class="sub">Docker in 2026 • Multi-Container FastAPI + Redis Persistent Demo</p>
    <div class="stats">
      <div>
        <div style="font-size:12px;color:#94A3B8;font-family:monospace;">PAGE HITS</div>
        <div class="metric">{hits}</div>
      </div>
      <div class="links">
        <a href="/health" target="_blank">/health</a>
        <a href="/docs" target="_blank">/docs (Swagger)</a>
      </div>
    </div>
    <form id="ideaForm">
      <input id="ideaInput" type="text" placeholder="Drop a hackathon idea..." required />
      <button type="submit">Add Idea</button>
    </form>
    <ul>{items_html}</ul>
  </div>
  <script>
    document.getElementById('ideaForm').addEventListener('submit', async (e) => {{
      e.preventDefault();
      const input = document.getElementById('ideaInput');
      const text = input.value.trim();
      if (!text) return;
      await fetch('/api/notes', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ text }})
      }});
      window.location.reload();
    }});
  </script>
</body>
</html>"""
