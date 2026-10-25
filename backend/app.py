"""StudyFlow AI backend (Flask). Run: python backend/app.py"""
import json, os, re, sqlite3, secrets, hashlib, smtplib
from datetime import timedelta, datetime, timezone
from email.message import EmailMessage
from urllib.parse import quote_plus
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, jsonify, request, send_from_directory, session
from werkzeug.utils import secure_filename
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).resolve().parent.parent
DATA = Path(__file__).parent / "data"
app = Flask(__name__, static_folder=str(ROOT / "frontend"), static_url_path="")
app.secret_key = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=bool(os.getenv("RENDER")), PERMANENT_SESSION_LIFETIME=timedelta(days=7), MAX_CONTENT_LENGTH=5 * 1024 * 1024)
CORS(app, supports_credentials=True)
DB_PATH = Path(os.getenv("STUDYFLOW_DB_PATH", str(DATA / "studyflow_users.db")))

def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE COLLATE NOCASE, password_hash TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    conn.execute("CREATE TABLE IF NOT EXISTS password_reset_tokens (token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL, expires_at INTEGER NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)")
    conn.execute("CREATE TABLE IF NOT EXISTS user_profiles (user_id INTEGER PRIMARY KEY, profile_json TEXT NOT NULL DEFAULT '{}', updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)")
    conn.execute("CREATE TABLE IF NOT EXISTS user_documents (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, doc_type TEXT NOT NULL, title TEXT NOT NULL, stored_name TEXT NOT NULL, original_name TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)")
    return conn

with get_db() as _db:
    pass

RESOURCES = json.loads((DATA / "resources.json").read_text(encoding="utf-8"))
ROADMAPS = json.loads((DATA / "roadmaps.json").read_text(encoding="utf-8"))

PHASES = {
    "python": ["Set up Python; variables, types and input/output", "Conditions, loops and problem-solving", "Functions, lists, tuples and dictionaries", "Strings, files, exceptions and modules", "OOP, classes and simple libraries", "Build a small project and revise with a quiz"],
    "web development": ["HTML structure and semantic elements", "CSS layout, responsive design and accessibility", "JavaScript variables, functions and DOM events", "Forms, validation and browser storage", "Git and GitHub; publish a static website", "Build and deploy a portfolio project"],
    "sql": ["Tables, rows, columns and SELECT", "WHERE, ORDER BY, LIMIT and filtering", "JOINs and relationships", "GROUP BY, aggregate functions and HAVING", "INSERT, UPDATE, DELETE and safe query habits", "Build a mini database project and practise queries"],
    "machine learning": ["Python, NumPy/Pandas and basic statistics", "Prepare data and understand train/test splits", "Regression and classification basics", "Model evaluation and avoiding data leakage", "Use scikit-learn for a small experiment", "Document a mini project and explain its results"],
    "data structures": ["Arrays, strings and time complexity basics", "Linked lists, stacks and queues", "Searching and sorting", "Hash tables, sets and maps", "Trees, graphs and traversal", "Solve practice problems and review complexity"],
    "cybersecurity": ["Networking, operating systems and security ethics", "Passwords, MFA and account security", "Web security basics and common vulnerabilities", "Linux commands and log reading", "Practise in legal beginner labs only", "Create a defensive security checklist and report"],
    "cloud": ["Cloud concepts and shared responsibility", "Compute, storage and networking basics", "Identity, access and cost controls", "Deploy a simple web application", "Monitoring, backups and reliability", "Document and review a small cloud project"],
    "data analyst": ["Spreadsheet basics and data cleaning", "SQL queries and joins", "Python with Pandas", "Charts and dashboard fundamentals", "Statistics and explaining findings", "Create a portfolio analysis project"],
    "ai engineer": ["Python and essential maths", "Data structures, statistics and data handling", "Machine learning fundamentals", "Neural networks and model evaluation", "Build a small AI application responsibly", "Portfolio, documentation and internship preparation"],
    "iot developer": ["C/Python basics and electronics safety", "Microcontrollers and sensor readings", "Collect and clean sensor data", "Send data to a simple dashboard", "Add alerts and basic analytics", "Build and document an IoT prototype"]
}
GENERIC = ["Learn the essential terms and setup the tools", "Understand the main concepts with worked examples", "Practise small exercises and check your answers", "Apply the concepts to a realistic problem", "Build a mini project and write down what you learned", "Review, take a quiz and plan the next skill"]

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


@app.post("/api/auth/forgot-password")
def forgot_password():
    d = request.get_json(silent=True) or {}
    email = (d.get("email") or "").strip().lower()[:254]
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        return jsonify({"error": "Enter the email address associated with your account."}), 400
    with get_db() as db:
        user = db.execute("SELECT id, email FROM users WHERE email = ?", (email,)).fetchone()
        if user:
            token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
            expires = int(datetime.now(timezone.utc).timestamp()) + 1800
            db.execute("DELETE FROM password_reset_tokens WHERE user_id = ?", (user["id"],))
            db.execute("INSERT INTO password_reset_tokens (token_hash, user_id, expires_at) VALUES (?, ?, ?)", (token_hash, user["id"], expires))
    if user:
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        sender = os.getenv("SMTP_FROM") or smtp_user
        if not all([smtp_host, smtp_user, smtp_password, sender]):
            app.logger.error("Password reset requested but SMTP environment variables are not configured.")
            return jsonify({"error": "Password reset email is not configured yet. Please contact the StudyFlow administrator."}), 503
        reset_url = request.host_url.rstrip("/") + "/?reset_token=" + quote_plus(token)
        msg = EmailMessage()
        msg["Subject"] = "Reset your StudyFlow AI password"
        msg["From"] = sender
        msg["To"] = user["email"]
        msg.set_content("We received a request to reset your StudyFlow AI password. This link expires in 30 minutes and can be used once:\n\n" + reset_url + "\n\nIf you did not request this, ignore this email.")
        try:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
        except Exception:
            app.logger.exception("Failed to send password reset email")
            return jsonify({"error": "Could not send the reset email right now. Please try again later."}), 502
    return jsonify({"message": "If an account exists for that email, a password reset link has been sent."})


@app.post("/api/auth/reset-password")
def reset_password():
    d = request.get_json(silent=True) or {}
    token = (d.get("token") or "").strip()
    password = d.get("password") or ""
    if len(password) < 8:
        return jsonify({"error": "New password must contain at least 8 characters."}), 400
    if not token:
        return jsonify({"error": "This reset link is invalid. Request a new one."}), 400
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = int(datetime.now(timezone.utc).timestamp())
    with get_db() as db:
        row = db.execute("SELECT user_id FROM password_reset_tokens WHERE token_hash = ? AND expires_at > ?", (token_hash, now)).fetchone()
        if not row:
            return jsonify({"error": "This reset link is expired or already used. Request a new one."}), 400
        db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(password), row["user_id"]))
        db.execute("DELETE FROM password_reset_tokens WHERE token_hash = ?", (token_hash,))
    session.clear()
    return jsonify({"message": "Password reset successfully. Please log in with your new password."})


@app.get("/api/auth/config")
def auth_config():
    return jsonify({"google_client_id": os.getenv("GOOGLE_CLIENT_ID", "").strip()})


@app.post("/api/auth/google")
def google_login():
    d = request.get_json(silent=True) or {}
    credential = (d.get("credential") or "").strip()
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        return jsonify({"error": "Google sign-in is not configured yet. The administrator must add GOOGLE_CLIENT_ID in Render."}), 503
    if not credential:
        return jsonify({"error": "Google did not return a sign-in credential. Please try again."}), 400
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        claims = id_token.verify_oauth2_token(credential, google_requests.Request(), client_id)
        email = (claims.get("email") or "").strip().lower()
        if not claims.get("email_verified") or not email:
            return jsonify({"error": "Google must verify your email address before you can continue."}), 401
        name = (claims.get("name") or email.split("@")[0] or "Student").strip()[:80]
        with get_db() as db:
            user = db.execute("SELECT id, name, email FROM users WHERE email = ?", (email,)).fetchone()
            if user:
                user_id, display_name = user["id"], user["name"]
            else:
                cur = db.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", (name, email, generate_password_hash(secrets.token_urlsafe(48))))
                user_id, display_name = cur.lastrowid, name
        session.clear()
        session["user_id"] = user_id
        session["user_name"] = display_name
        session.permanent = True
        return jsonify({"user": {"id": user_id, "name": display_name, "email": email}})
    except ValueError:
        return jsonify({"error": "Google sign-in token is invalid or expired. Please try again."}), 401
    except Exception:
        app.logger.exception("Google sign-in failed")
        return jsonify({"error": "Google sign-in failed. Please try again later."}), 502


@app.get("/reset-password")
def reset_password_page():
    return send_from_directory(app.static_folder, "index.html")


PROFILE_FIELDS = {"phone":25,"location":100,"language":30,"bio":1000,"college":150,"degree":120,"major":120,"year":40,"grade":30,"graduation":30,"skills":1500,"linkedin":300,"github":300,"portfolio":300}
UPLOAD_DIR = ROOT / "uploads" / "student-documents"
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"}

@app.route("/api/profile", methods=["GET", "PUT"])
def student_profile():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Please log in to manage your student profile."}), 401
    with get_db() as db:
        user = db.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            session.clear()
            return jsonify({"error": "Account not found. Please log in again."}), 401
        row = db.execute("SELECT profile_json FROM user_profiles WHERE user_id = ?", (user_id,)).fetchone()
        profile = json.loads(row["profile_json"]) if row else {}
        if request.method == "PUT":
            incoming = request.get_json(silent=True) or {}
            for field, max_len in PROFILE_FIELDS.items():
                if field in incoming:
                    value = incoming[field]
                    if not isinstance(value, str):
                        return jsonify({"error": "Profile fields must be text."}), 400
                    value = value.strip()
                    if len(value) > max_len:
                        return jsonify({"error": field.capitalize() + " is too long."}), 400
                    if field in {"linkedin", "github", "portfolio"} and value and not re.match(r"^https://", value, re.I):
                        return jsonify({"error": field.capitalize() + " link must begin with https://"}), 400
                    profile[field] = value
            if "name" in incoming:
                name = (incoming.get("name") or "").strip()
                if not 2 <= len(name) <= 80:
                    return jsonify({"error": "Full name must contain 2–80 characters."}), 400
                db.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))
                session["user_name"] = name
                user = db.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,)).fetchone()
            db.execute("INSERT INTO user_profiles (user_id, profile_json, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) ON CONFLICT(user_id) DO UPDATE SET profile_json = excluded.profile_json, updated_at = CURRENT_TIMESTAMP", (user_id, json.dumps(profile, ensure_ascii=False)))
    return jsonify({"user": {"id": user["id"], "name": user["name"], "email": user["email"]}, "profile": profile})


@app.route("/api/documents", methods=["GET", "POST"])
def student_documents():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Please log in to manage your resume and certificates."}), 401
    if request.method == "GET":
        with get_db() as db:
            rows = db.execute("SELECT id, doc_type, title, original_name, created_at FROM user_documents WHERE user_id = ? ORDER BY created_at DESC, id DESC", (user_id,)).fetchall()
        return jsonify([{"id": r["id"], "type": r["doc_type"], "title": r["title"], "filename": r["original_name"], "created_at": r["created_at"]} for r in rows])
    uploaded = request.files.get("file")
    doc_type = (request.form.get("doc_type") or "other").strip().lower()
    title = (request.form.get("title") or "").strip()[:120]
    if doc_type not in {"resume", "certificate", "other"}:
        return jsonify({"error": "Choose a valid document type."}), 400
    if not uploaded or not uploaded.filename:
        return jsonify({"error": "Choose a file before uploading."}), 400
    original = secure_filename(uploaded.filename)
    ext = Path(original).suffix.lower()
    if not original or ext not in ALLOWED_DOCUMENT_EXTENSIONS:
        return jsonify({"error": "Allowed formats: PDF, DOC, DOCX, JPG and PNG."}), 400
    title = title or Path(original).stem[:120] or "Student document"
    stored = secrets.token_hex(16) + ext
    user_dir = UPLOAD_DIR / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    uploaded.save(user_dir / stored)
    with get_db() as db:
        cur = db.execute("INSERT INTO user_documents (user_id, doc_type, title, stored_name, original_name) VALUES (?, ?, ?, ?, ?)", (user_id, doc_type, title, stored, original))
        doc_id = cur.lastrowid
    return jsonify({"id": doc_id, "type": doc_type, "title": title, "filename": original}), 201


@app.get("/api/documents/<int:document_id>/download")
def download_student_document(document_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Please log in to download your documents."}), 401
    with get_db() as db:
        row = db.execute("SELECT stored_name, original_name FROM user_documents WHERE id = ? AND user_id = ?", (document_id, user_id)).fetchone()
    if not row:
        return jsonify({"error": "Document not found."}), 404
    return send_from_directory(UPLOAD_DIR / str(user_id), row["stored_name"], as_attachment=True, download_name=row["original_name"])


@app.delete("/api/documents/<int:document_id>")
def delete_student_document(document_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Please log in to manage your documents."}), 401
    with get_db() as db:
        row = db.execute("SELECT stored_name FROM user_documents WHERE id = ? AND user_id = ?", (document_id, user_id)).fetchone()
        if not row:
            return jsonify({"error": "Document not found."}), 404
        db.execute("DELETE FROM user_documents WHERE id = ? AND user_id = ?", (document_id, user_id))
    try:
        (UPLOAD_DIR / str(user_id) / row["stored_name"]).unlink(missing_ok=True)
    except OSError:
        app.logger.exception("Could not remove uploaded student document")
    return jsonify({"ok": True})


@app.get("/api/auth/me")
def auth_me():
    if not session.get("user_id"):
        return jsonify({"user": None})
    with get_db() as db:
        user = db.execute("SELECT id, name, email FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    if not user:
        session.clear()
        return jsonify({"user": None})
    return jsonify({"user": {"id": user["id"], "name": user["name"], "email": user["email"]}})


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
    phases = PHASES.get(topic.lower(), PHASES.get(next((k for k in PHASES if k in topic.lower()), ""), GENERIC))
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
    key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not key:
        return jsonify({"error": "AI Tutor is not configured yet. Add GEMINI_API_KEY in your Render web service Environment settings, then redeploy."}), 503
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
            contents=f"Answer in {language}.\\n\\n{question}",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=900,
            ),
        )
        answer = (response.text or "").strip()
        if not answer:
            return jsonify({"error": "Gemini returned an empty response. Please try asking in a different way."}), 502
        return jsonify({"answer": answer})
    except Exception as e:
        message = str(e).lower()
        if "api key" in message or "api_key" in message or "401" in message or "403" in message or "unauthorized" in message:
            return jsonify({"error": "Gemini could not authenticate this key. Check that GEMINI_API_KEY in Render contains a valid Gemini API key, then redeploy."}), 502
        if "429" in message or "quota" in message or "resource_exhausted" in message:
            return jsonify({"error": "Gemini free-tier quota or rate limit reached. Wait and try again later, or check your model and quota in Google AI Studio."}), 502
        return jsonify({"error": "Gemini AI Tutor request failed. Check the Render logs and confirm the selected Gemini model is available for your API key."}), 502


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1", port=5000)
