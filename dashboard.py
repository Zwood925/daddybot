import os
import sqlite3
import json
import aiohttp
from fastapi import FastAPI, Request, Form, HTTPException, Header
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from dotenv import load_dotenv
load_dotenv()

URL_KEY = os.getenv("URL_KEY") 
app = FastAPI(title="DaddyBot Command Center")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "daddybot_memory.db")
STATIC_DIR = os.path.join(BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def row_to_dict(row):
    if row is None:
        return {}
    return {k: row[k] for k in row.keys()}

def init_db():
    """Ensure read_books has a read_at timestamp column."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE read_books ADD COLUMN read_at TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists
    finally:
        conn.close()

# ─── Main dashboard ──────────────────────────────────────────────────────────
# ─── Auth Middleware ─────────────────────────────────────────────────────────
@app.middleware("http")
async def check_secret_key(request: Request, call_next):
    # Always allow static files (PWA icons/styles)
    if request.url.path.startswith("/static"):
        return await call_next(request)

    # Check key from URL parameter OR saved browser cookie
    provided_key = request.query_params.get("key") or request.cookies.get("daddy_auth")

    # Lock down if URL_KEY isn't set in .env OR provided key is wrong
    if not URL_KEY or provided_key != URL_KEY:
        return HTMLResponse(
            "<h1 style='color:red;text-align:center;margin-top:20%'>403 Forbidden</h1>"
            "<p style='color:gray;text-align:center'>Invalid or missing key parameter.</p>",
            status_code=403
        )

    response = await call_next(request)

    # If accessed via ?key=..., save a cookie so app buttons and future visits work automatically
    if request.query_params.get("key") == URL_KEY:
        response.set_cookie(key="daddy_auth", value=URL_KEY, max_age=31536000)  # 1 year

    return response

@app.get("/", response_class=HTMLResponse)
async def main_dashboard(request: Request):
    init_db()
    conn = get_db()
    cursor = conn.cursor()

    daddy_books, wife_books, inventory, movies = [], [], [], []
    stats = []

    # Books per user
    try:
        cursor.execute("SELECT * FROM read_books WHERE user_name = 'zwood925' ORDER BY id DESC")
        daddy_books = [row_to_dict(r) for r in cursor.fetchall()]
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("SELECT * FROM read_books WHERE user_name = 'swood_38102' ORDER BY id DESC")
        wife_books = [row_to_dict(r) for r in cursor.fetchall()]
    except sqlite3.OperationalError:
        pass

    # Inventory items (join items with their boxes)
    try:
        cursor.execute("""
            SELECT i.id, i.item_name, i.box_id, b.color_code, b.container_type, b.theme, b.location, b.status
            FROM items i
            LEFT JOIN boxes b ON b.box_id = i.box_id
            ORDER BY i.item_name ASC
        """)
        inventory = [row_to_dict(r) for r in cursor.fetchall()]
    except sqlite3.OperationalError:
        pass

    # Movies (could be per user - now shared)
    try:
        cursor.execute("SELECT * FROM movies ORDER BY id DESC")
        movies = [row_to_dict(r) for r in cursor.fetchall()]
    except sqlite3.OperationalError:
        pass

    # Stats (user-level book counts) — friendly names
    user_map = {
        "zwood925": "Daddy",
        "swood_38102": "KittyKat",
    }
    try:
        cursor.execute("SELECT user_name, COUNT(*) AS count FROM read_books GROUP BY user_name ORDER BY count DESC")
        for r in cursor.fetchall():
            raw = r["user_name"] or "Unknown"
            display = user_map.get(raw, raw)
            stats.append({"user": display, "count": r["count"]})
    except sqlite3.OperationalError:
        pass

    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "daddy_books": daddy_books,
            "wife_books": wife_books,
            "inventory": inventory,
            "movies": movies,
            "stats": stats,
        }
    )

# ─── Manifest & PWA assets ───────────────────────────────────────────────────
@app.get("/manifest.json", response_class=FileResponse)
async def manifest():
    return FileResponse(os.path.join(STATIC_DIR, "manifest.json"))

@app.get("/static/sw.js", response_class=FileResponse)
async def service_worker():
    return FileResponse(os.path.join(STATIC_DIR, "sw.js"))

@app.get("/static/icons/{name}")
async def icons(name: str):
    return FileResponse(os.path.join(STATIC_DIR, "icons", name))

# ─── Inventory update (HTMX) ─────────────────────────────────────────────────
@app.post("/api/inventory/update", response_class=HTMLResponse)
async def update_inventory(item_id: int = Form(...), action: str = Form(...)):
    conn = get_db()
    cursor = conn.cursor()
    delta = 1 if action == "add" else -1
    try:
        cursor.execute("UPDATE inventory SET quantity = MAX(0, quantity + ?) WHERE id = ?", (delta, item_id))
        conn.commit()
        cursor.execute("SELECT * FROM inventory WHERE id = ?", (item_id,))
        item = row_to_dict(cursor.fetchone())
    finally:
        conn.close()

    min_qty = item.get('min_quantity', 1) or 1
    badge_style = "text-red-400 bg-red-950/50 border-red-800" if item['quantity'] <= min_qty else "text-emerald-400 bg-emerald-950/50 border-emerald-800"
    return f"""
    <div id="item-{item['id']}" class="flex items-center justify-between p-3 bg-zinc-800/60 rounded-lg border border-zinc-700/50">
        <div>
            <span class="font-medium text-zinc-100">{item['item_name']}</span>
            <span class="ml-2 text-xs px-2 py-0.5 rounded border {badge_style}">Qty: {item['quantity']}</span>
        </div>
        <div class="flex gap-1">
            <button onclick="updateQty({item['id']},'sub')" class="w-8 h-8 bg-zinc-700 hover:bg-zinc-600 text-zinc-200 rounded font-bold transition">-</button>
            <button onclick="updateQty({item['id']},'add')" class="w-8 h-8 bg-zinc-700 hover:bg-zinc-600 text-zinc-200 rounded font-bold transition">+</button>
        </div>
    </div>
    """

# ─── Add book ────────────────────────────────────────────────────────────────
@app.post("/api/book/add")
async def add_book(title: str = Form(...), author: str = Form(""), rating: str = Form(""), review: str = Form(""), user: str = Form("")):
    conn = get_db()
    cursor = conn.cursor()
    user_map = {
        "Daddy": "zwood925",
        "KittyKat": "swood_38102",
    }
    db_user = user_map.get(user, user)
    try:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        cursor.execute(
            "INSERT OR IGNORE INTO read_books (user_name, book_title, author, rating, read_at, what_i_liked) VALUES (?, ?, ?, ?, ?, ?)",
            (db_user, title.strip(), author.strip(), int(rating) if rating.isdigit() else None, now, review.strip() or None)
        )
        conn.commit()
        result = "ok"
    except Exception as e:
        result = str(e)
    finally:
        conn.close()
    return JSONResponse({"status": result, "title": title})

# ─── Add inventory item ─────────────────────────────────────────────────────
@app.post("/api/inventory/add")
async def add_item(
    name: str = Form(...),
    box_id: str = Form("UNLABELED"),
    color_code: str = Form(""),
    container_type: str = Form(""),
    theme: str = Form(""),
    location: str = Form(""),
    status: str = Form("Active"),
):
    box_id = box_id.strip().upper() or "UNLABELED"
    conn = get_db()
    cursor = conn.cursor()
    try:
        # Ensure the box exists; create it with whatever details were provided
        cursor.execute("SELECT 1 FROM boxes WHERE box_id = ?", (box_id,))
        if not cursor.fetchone():
            cursor.execute(
                """INSERT INTO boxes (box_id, color_code, container_type, theme, location, status)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (box_id, color_code or None, container_type or None, theme or None, location or None, status or "Active"),
            )
        else:
            # Update any fields that were provided
            updates = []
            params = []
            if color_code:
                updates.append("color_code = ?"); params.append(color_code)
            if container_type:
                updates.append("container_type = ?"); params.append(container_type)
            if theme:
                updates.append("theme = ?"); params.append(theme)
            if location:
                updates.append("location = ?"); params.append(location)
            if status:
                updates.append("status = ?"); params.append(status)
            if updates:
                params.append(box_id)
                cursor.execute(f"UPDATE boxes SET {', '.join(updates)} WHERE box_id = ?", params)

        cursor.execute("INSERT INTO items (item_name, box_id) VALUES (?, ?)", (name.strip(), box_id))
        conn.commit()
        return JSONResponse({"status": "ok", "item": name, "box_id": box_id})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
    finally:
        conn.close()

# ─── Inventory: browse, locate, find ─────────────────────────────────────────
import difflib

@app.get("/api/inventory/browse")
async def inventory_browse():
    """Return nested tree: location -> color -> [boxes]"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT b.box_id, b.color_code, b.container_type, b.theme, b.location, b.status,
                   COUNT(i.id) AS item_count
            FROM boxes b
            LEFT JOIN items i ON i.box_id = b.box_id
            GROUP BY b.box_id
            ORDER BY COALESCE(b.location, 'Unassigned') ASC,
                     COALESCE(b.color_code, 'Untagged') ASC,
                     b.box_id ASC
        """)
        rows = [row_to_dict(r) for r in cursor.fetchall()]
    except sqlite3.OperationalError:
        rows = []
    finally:
        conn.close()

    # Nest: location -> color -> [boxes]
    tree = {}
    for r in rows:
        loc = r.get("location") or "Unassigned"
        col = r.get("color_code") or "Untagged"
        tree.setdefault(loc, {}).setdefault(col, []).append({
            "box_id": r["box_id"],
            "container_type": r.get("container_type") or "Unknown",
            "theme": r.get("theme") or "—",
            "status": r.get("status") or "Active",
            "item_count": r.get("item_count", 0),
        })
    return JSONResponse(tree)


@app.get("/api/inventory/box/{box_id}")
async def inventory_box(box_id: str):
    """Full dossier for a single box + all its items."""
    box_id = box_id.strip().upper()
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT box_id, color_code, container_type, theme, location, status
            FROM boxes WHERE box_id = ?
        """, (box_id,))
        box = cursor.fetchone()
        if not box:
            return JSONResponse({"error": f"Box {box_id} not found"}, status_code=404)
        box_d = row_to_dict(box)

        cursor.execute("SELECT id, item_name FROM items WHERE box_id = ? ORDER BY item_name ASC", (box_id,))
        items = [row_to_dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

    box_d["items"] = items
    return JSONResponse(box_d)


@app.get("/api/inventory/find")
async def inventory_find(q: str = ""):
    """Fuzzy search: difflib ranks all items against query, returns top matches with full context."""
    q = (q or "").strip().lower()
    if not q:
        return JSONResponse({"query": "", "matches": []})

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT i.item_name, b.box_id, b.color_code, b.container_type,
                   b.theme, b.location, b.status
            FROM items i
            JOIN boxes b ON b.box_id = i.box_id
        """)
        rows = [row_to_dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

    # Score each row against the query using difflib on item name
    scored = []
    for r in rows:
        name = (r.get("item_name") or "").lower()
        # Direct substring match wins big
        ratio = difflib.SequenceMatcher(None, q, name).ratio()
        # Bonus for word-overlap (handles "cast iron skillet" vs "cast-iron frying pan")
        q_words = set(q.replace("-", " ").split())
        n_words = set(name.replace("-", " ").split())
        overlap = len(q_words & n_words) / max(len(q_words), 1)
        score = max(ratio, overlap * 0.85)
        if q in name:
            score = max(score, 0.95)  # substring = near-perfect
        scored.append((score, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [r for s, r in scored[:20] if s > 0.25]  # filter weak matches
    return JSONResponse({"query": q, "matches": top})


# ─── Create box (matches Discord cog's guided flow) ──────────────────────────
@app.post("/api/inventory/box")
async def create_box(
    box_id: str = Form(...),
    color_code: str = Form(""),
    container_type: str = Form(""),
    theme: str = Form(""),
    location: str = Form(""),
    status: str = Form("Active"),
):
    box_id = box_id.strip().upper()
    if not box_id:
        return JSONResponse({"status": "error", "message": "box_id required"}, status_code=400)
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT INTO boxes (box_id, color_code, container_type, theme, location, status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (box_id, color_code or None, container_type or None, theme or None, location or None, status or "Active"),
        )
        conn.commit()
        return JSONResponse({"status": "ok", "box_id": box_id})
    except sqlite3.IntegrityError:
        return JSONResponse({"status": "exists", "box_id": box_id})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
    finally:
        conn.close()


# ─── Delete box / container ─────────────────────────────────────────────────────
@app.post("/api/inventory/box/delete")
async def delete_inventory_box(box_id: str = Form(...)):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM boxes WHERE box_id = ?", (box_id,))
        conn.commit()
    finally:
        conn.close()
    return JSONResponse({"status": "ok"})

# ─── AI book recommendation ──────────────────────────────────────────────────
@app.post("/api/recommend_book", response_class=HTMLResponse)
async def recommend_book(seed_title: str = Form("")):
    conn = get_db()
    cursor = conn.cursor()
    history = []
    try:
        cursor.execute("SELECT book_title, author FROM read_books ORDER BY id DESC LIMIT 10")
        history = [f"{r['book_title']} by {r['author']}" for r in cursor.fetchall()]
    except Exception:
        pass
    conn.close()

    history_str = ", ".join(history) if history else "Sci-Fi and Tech classics"
    
    if seed_title.strip():
        prompt = f"""Based on the user's library: {history_str}.

The user just read or is interested in: "{seed_title}".

Recommend 5 books they'd love. For each: title, author, and 1-2 punchy sentences why it fits. No markdown headers, no bullet points, just clean numbered list."""
    else:
        prompt = f"""Based on these books: {history_str}. Recommend 5 fantastic books they'd love. For each: title, author, and 1-2 punchy sentences why. No markdown headers or bullet points, just a clean numbered list."""

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("http://localhost:11434/api/generate", json={
                "model": "llama3.1:8b",
                "prompt": prompt,
                "stream": False
            }) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    rec_text = data.get("response", "Could not fetch recommendation.").strip()
                else:
                    rec_text = f"Ollama API error ({resp.status})"
    except Exception as e:
        rec_text = f"Failed to connect to Ollama: {e}"

    return f'''
    <div class="p-4 bg-indigo-950/40 border border-indigo-800/60 rounded-lg text-indigo-200 text-sm leading-relaxed">
        <div class="font-bold text-indigo-400 mb-1">🤖 Ollama Recommendations:</div>
        {rec_text}
    </div>
    '''

# ─── Inventory: remove item ────────────────────────────────────────────────────
@app.post("/api/inventory/item/delete")
async def delete_inventory_item(id: int = Form(...)):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM items WHERE id = ?", (id,))
        conn.commit()
        deleted = cursor.rowcount > 0
    finally:
        conn.close()
    return JSONResponse({"status": "ok" if deleted else "not_found", "deleted_rows": cursor.rowcount})

# ─── Movie family-filter evaluation ──────────────────────────────────────────
@app.post("/api/movie/evaluate", response_class=HTMLResponse)
async def movie_evaluate(request: Request):
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    title = body.get("title", "")
    if not title:
        return "No movie title provided."

    system_prompt = """
    You are a highly protective AI media filter for the Wood family.

    1. Potty humor and slapstick violence are OK.
    2. Glorifying Demonic, occult, or dark magic themes are not cool.
    3. We operate from a Christian worldview but are not crazy stuck up.
    4. We don't like blatant agendas being pushed through kid's movies.

    Movies OK: Guardians of the Galaxy, Despicable Me, Luca, Goat.
    Movies rejected: Minions and Monsters, later seasons of Stranger Things.

    Give a brief summary, list potential triggers, and give a final PASS/FAIL.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("http://localhost:11434/api/generate", json={
                "model": "llama3.1:8b",
                "prompt": f"{system_prompt}\n\nMovie to evaluate: {title}",
                "stream": False
            }) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("response", "No response.").strip()
                else:
                    return f"Ollama error ({resp.status})"
    except Exception as e:
        return f"Failed: {e}"

# ─── Weather ─────────────────────────────────────────────────────────────────
@app.get("/api/weather")
async def weather(city: str = ""):
    import os
    api_key = os.getenv("WEATHER_API_KEY", "")
    if not city or not api_key:
        return JSONResponse({"output": "Weather API key or city not configured."})
    url = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q={city}&days=3"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    actual_city = data['location']['name']
                    lines = [f"**3-day forecast for {actual_city}**"]
                    for day in data['forecast']['forecastday']:
                        d = day['date']
                        hi = day['day']['maxtemp_f']
                        lo = day['day']['mintemp_f']
                        cond = day['day']['condition']['text']
                        rain = day['day']['daily_chance_of_rain']
                        lines.append(f"📅 {d}: {cond} | High: {hi}°F | Low: {lo}°F | {rain}% chance")
                    return JSONResponse({"output": "\n".join(lines)})
                else:
                    return JSONResponse({"output": f"City '{city}' not found or API error."})
    except Exception as e:
        return JSONResponse({"output": f"Weather fetch failed: {e}"})

# ─── Stats ───────────────────────────────────────────────────────────────────
@app.get("/api/stats")
async def stats_api():
    conn = get_db()
    cursor = conn.cursor()
    results = []
    try:
        cursor.execute("SELECT user_name AS user, COUNT(*) AS count FROM read_books GROUP BY user_name ORDER BY count DESC")
        results = [row_to_dict(r) for r in cursor.fetchall()]
    except sqlite3.OperationalError:
        pass
    conn.close()
    return JSONResponse(results)

if __name__ == "__main__":
    uvicorn.run("dashboard:app", host="0.0.0.0", port=8001, reload=True)
