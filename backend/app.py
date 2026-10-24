"""StudyFlow AI backend (Flask). Run: python backend/app.py"""
import json, os, re
from urllib.parse import quote_plus
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).resolve().parent.parent
DATA = Path(__file__).parent / "data"
app = Flask(__name__, static_folder=str(ROOT / "frontend"), static_url_path="")
CORS(app)

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


@app.get("/api/resources")
def resources():
    q = request.args.get("q", "").lower().strip()
    free_only = request.args.get("free") == "1"
    out = []
    for r in RESOURCES:
        text = f'{r["title"]} {r["topic"]} {r["provider"]}'.lower()
        if q and not any(w in text for w in q.split()):
            continue
        if free_only and not r["cost"].startswith("free"):
            continue
        out.append(r)
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
    q = quote_plus(request.args.get("domain", "python").strip())
    return jsonify([
        {"name": "Internshala", "url": f"https://internshala.com/internships/keywords-{q}/"},
        {"name": "AICTE Internship Portal", "url": "https://internship.aicte-india.org/"},
        {"name": "LinkedIn Jobs", "url": f"https://www.linkedin.com/jobs/search/?keywords={q}%20intern"},
        {"name": "Unstop", "url": "https://unstop.com/internships"},
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
    app.run(debug=True, port=5000)
