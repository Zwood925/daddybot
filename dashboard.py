import os
import sqlite3
import json
import aiohttp
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

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

# ─── Main dashboard ──────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def main_dashboard(request: Request):
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

    # Inventory items (could be shared or per user - now shared)
    try:
        cursor.execute("SELECT * FROM inventory ORDER BY item_name ASC")
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
async def add_book(title: str = Form(...), author: str = Form(""), rating: str = Form(""), user: str = Form("")):
    conn = get_db()
    cursor = conn.cursor()
    user_map = {
        "Daddy": "zwood925",
        "KittyKat": "swood_38102",
    }
    db_user = user_map.get(user, user)
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO read_books (user_name, book_title, author, rating) VALUES (?, ?, ?, ?)",
            (db_user, title.strip(), author.strip(), int(rating) if rating.isdigit() else None)
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
async def add_item(name: str = Form(...), box_id: str = Form("UNLABELED")):
    conn = get_db()
    cursor = conn.cursor()
    # Ensure box exists (simplified — create a basic box if missing)
    try:
        cursor.execute("SELECT 1 FROM boxes WHERE box_id = ?", (box_id,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO boxes (box_id, theme, status) VALUES (?, ?, ?)", (box_id, "General", "Active"))
        cursor.execute("INSERT INTO items (item_name, box_id) VALUES (?, ?)", (name, box_id))
        conn.commit()
    finally:
        conn.close()
    return JSONResponse({"status": "ok", "item": name, "box_id": box_id})

# ─── AI book recommendation ──────────────────────────────────────────────────
@app.post("/api/recommend_book", response_class=HTMLResponse)
async def recommend_book():
    conn = get_db()
    cursor = conn.cursor()
    history = []
    try:
        cursor.execute("SELECT title, author FROM read_books LIMIT 5")
        history = [f"{r['title']} by {r['author']}" for r in cursor.fetchall()]
    except Exception:
        pass
    conn.close()

    history_str = ", ".join(history) if history else "Sci-Fi and Tech classics"
    prompt = f"Based on these books: {history_str}. Recommend 1 fantastic book. Give title, author, and 2 punchy sentences why. No markdown headers or bullet points."

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
        <div class="font-bold text-indigo-400 mb-1">🤖 Ollama Recommendation:</div>
        {rec_text}
    </div>
    '''

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
    uvicorn.run("dashboard:app", host="0.0.0.0", port=8000, reload=True)
