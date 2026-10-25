"""StudyFlow AI backend (Flask). Run: python backend/app.py"""
import json, os, re, sqlite3, secrets
from datetime import timedelta
from urllib.parse import quote_plus
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).resolve().parent.parent
DATA = Path(__file__).parent / "data"
app = Flask(__name__, static_folder=str(ROOT / "frontend"), static_url_path="")
app.secret_key = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=bool(os.getenv("RENDER")), PERMANENT_SESSION_LIFETIME=timedelta(days=7))
CORS(app, supports_credentials=True)
DB_PATH = Path(os.getenv("STUDYFLOW_DB_PATH", str(DATA / "studyflow_users.db")))

def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE COLLATE NOCASE, password_hash TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    return conn

with get_db() as _db:
    pass

RESOURCES = json.loads((DATA / "resources.json").read_text(encoding="utf-8"))
ROADMAPS = json.loads((DATA / "roadmaps.json").read_text(encoding="utf-8"))

PHASES = {
    "python": ["Variables, data types, operators", "Conditions and loops", "Functions and data structures",
               "Object-oriented programming", "File handling and libraries", "Build a practical project"],
}
GENERIC = ["Fundamentals and key terms", "Core concepts with examples", "Guided practice",
           "Intermediate topics", "Mini project", "Review, quiz yourself, and plan next steps"]

SYSTEM_PROMPT = (
    "You are StudyFlow AI, a patient tutor for students. Reply in the language the student asks for "
    "(Tamil, English, etc.), keeping technical terms in English. Explain simply, give one short example, "
    "then 2 practice questions. If you are unsure, say so instead of guessing. Prefer free resources."
)


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.post("/api/auth/register")
def register():
    d = request.get_json(silent=True) or {}
    name = (d.get("name") or "").strip()[:80]
    email = (d.get("email") or "").strip().lower()[:254]
    password = d.get("password") or ""
    if len(name) < 2:
        return jsonify({"error": "Please enter your name (at least 2 characters)."}), 400
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        return jsonify({"error": "Enter a valid email address."}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must contain at least 8 characters."}), 400
    try:
        with get_db() as db:
            cur = db.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", (name, email, generate_password_hash(password)))
            user_id = cur.lastrowid
    except sqlite3.IntegrityError:
        return jsonify({"error": "An account with this email already exists. Please sign in."}), 409
    session.clear()
    session["user_id"] = user_id
    session["user_name"] = name
    session.permanent = True
    return jsonify({"user": {"id": user_id, "name": name, "email": email}}), 201


@app.post("/api/auth/login")
def login():
    d = request.get_json(silent=True) or {}
    email = (d.get("email") or "").strip().lower()[:254]
    password = d.get("password") or ""
    with get_db() as db:
        user = db.execute("SELECT id, name, email, password_hash FROM users WHERE email = ?", (email,)).fetchone()
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Email or password is incorrect."}), 401
    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session.permanent = True
    return jsonify({"user": {"id": user["id"], "name": user["name"], "email": user["email"]}})


@app.get("/api/auth/me")
def auth_me():
    if not session.get("user_id"):
        return jsonify({"user": None})
    return jsonify({"user": {"id": session["user_id"], "name": session.get("user_name", "Student")}})


@app.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.get("/api/resources")
def resources():
    q = request.args.get("q", "").lower().strip()
    free_only = request.args.get("free") == "1"
    certificate_only = request.args.get("certificate") == "1"
    level = request.args.get("level", "").lower().strip()
    aliases = {
        "web develop": "web development", "web": "web development",
        "ai": "artificial intelligence", "ml": "machine learning",
        "dsa": "data structures", "database": "sql", "data & sql": "sql",
        "coding": "programming", "iot": "internet of things",
        "cyber security": "cybersecurity", "tamil": "language"
    }
    q = aliases.get(q, q)
    out = []
    for item in RESOURCES:
        text = f'{item["title"]} {item["topic"]} {item["provider"]} {item.get("note", "")}'.lower()
        words = [w for w in q.split() if len(w) > 1]
        if q and not (all(w in text for w in words) or q in text or any(w in text for w in words)):
            continue
        if free_only and not str(item.get("cost", "")).lower().startswith("free"):
            continue
        note = str(item.get("note", "")).lower()
        is_free_certificate = "free certification" in note or "free certificate" in note or "free certificates" in note
        if certificate_only and not is_free_certificate:
            continue
        item_level = str(item.get("level", "")).lower()
        if level and level not in item_level and item_level != "all":
            continue
        out.append(item)
    out.sort(key=lambda item: (0 if ("free certification" in str(item.get("note","")).lower() or "free certificate" in str(item.get("note","")).lower()) else 1, item.get("title","").lower()))
    return jsonify(out)


@app.post("/api/plan")
def plan():
    d = request.get_json(force=True)
    topic = (d.get("topic") or "").strip() or "your topic"
    days = max(1, min(int(d.get("days", 30)), 180))
    hours = max(0.5, min(float(d.get("hours_per_day", 2)), 12))
    phases = PHASES.get(topic.lower(), GENERIC)
    size = max(1, days // len(phases))
    items, start = [], 1
    for i, goal in enumerate(phases):
        if start > days:
            break
        end = days if i == len(phases) - 1 else min(days, start + size - 1)
        items.append({"days": f"{start}–{end}" if end > start else str(start), "goal": goal})
        start = end + 1
    return jsonify({"topic": topic, "total_days": days, "hours_per_day": hours, "phases": items})


@app.get("/api/roadmap")
def roadmap():
    goal = request.args.get("goal", "").lower().strip()
    return jsonify({"goal": goal, "steps": ROADMAPS.get(goal), "available": sorted(ROADMAPS)})


@app.get("/api/internships")
def internships():
    domain = request.args.get("domain", "python").strip() or "student"
    location = request.args.get("location", "Remote").strip() or "Remote"
    q = quote_plus(domain)
    loc = quote_plus(location)
    remote = location.lower() in {"remote", "work from home", "online"}
    internshala = f"https://internshala.com/internships/keywords-{q}/" + ("" if remote else f"?locations={loc}")
    linkedin = f"https://www.linkedin.com/jobs/search/?keywords={q}%20intern&location={loc}"
    return jsonify([
        {"name": "Internshala", "url": internshala},
        {"name": "AICTE Internship Portal", "url": "https://internship.aicte-india.org/"},
        {"name": "LinkedIn internships", "url": linkedin},
        {"name": "Unstop internships", "url": "https://unstop.com/internships"},
        {"name": "Google jobs search", "url": f"https://www.google.com/search?q={q}+internship+{loc}"},
    ])


@app.get("/api/nearby")
def nearby():
    loc = request.args.get("location", "").strip()
    kind = request.args.get("kind", "library")
    if not loc:
        return jsonify({"error": "Enter a location."}), 400
    q = quote_plus(f"{kind} near {loc}")
    return jsonify({"osm": f"https://www.openstreetmap.org/search?query={q}",
                    "google": f"https://www.google.com/maps/search/{q}"})


@app.post("/api/ask")
def ask():
    d = request.get_json(force=True)
    question = (d.get("question") or "").strip()[:2000]
    language = d.get("language", "English")
    if not question:
        return jsonify({"error": "Ask a question first."}), 400
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return jsonify({"answer": "AI tutor is not set up. Add ANTHROPIC_API_KEY to your .env file and restart."})
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model=os.getenv("STUDYFLOW_MODEL", "claude-sonnet-4-6"), max_tokens=900, system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Answer in {language}.\n\n{question}"}])
        return jsonify({"answer": "".join(b.text for b in msg.content if b.type == "text")})
    except Exception as e:
        return jsonify({"error": "AI request failed: " + re.sub(r"sk-[A-Za-z0-9_-]+", "***", str(e))}), 502


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1", port=5000)
