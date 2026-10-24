# StudyFlow AI — AI-Powered Personalized Student Learning Platform

StudyFlow AI helps students discover learning resources, build study plans, explore internship portals, find nearby learning spaces, follow career roadmaps, and ask a multilingual AI tutor.

This repository now contains two versions:
- **Root front-end prototype** (index.html, styles.css, app.js) — the existing static dashboard.
- **Flask app from the uploaded ZIP** (frontend/, backend/) — a separate front end plus API backend.

## Features in the Flask version
- Search a curated catalogue of learning resources and filter for free resources.
- Generate a topic-based study plan and track completed phases in browser local storage.
- Ask the AI tutor in a selected language (requires an Anthropic API key).
- Open internship portal searches.
- Search map links for libraries and learning centres by entered location.
- Browse career roadmaps for AI engineering, data analysis, web development and IoT.

## Run the Flask version locally

Use Python 3.10+ and run these commands from the repository root.

```bash
python -m venv .venv
```

**Windows PowerShell**
```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python backend/app.py
```

**macOS / Linux**
```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python backend/app.py
```

Open http://localhost:5000. The AI tutor returns a setup hint until you add a valid ANTHROPIC_API_KEY to .env. Never commit your real .env or API key.

## API endpoints
| Method and endpoint | Purpose |
|---|---|
| GET /api/resources?q=python&free=1 | Search learning resources |
| POST /api/plan | Generate a study plan; JSON: { "topic": "Python", "days": 30, "hours_per_day": 2 } |
| POST /api/ask | Ask the AI tutor; JSON: { "question": "...", "language": "Tamil" } |
| GET /api/internships?domain=python | Return internship portal links |
| GET /api/nearby?location=Madurai&kind=library | Return map search links |
| GET /api/roadmap?goal=ai%20engineer | Return a career roadmap |

## Project structure

```
StudyMap-AI/
├── index.html, styles.css, app.js   # Existing static prototype
├── frontend/index.html              # Flask version interface
├── backend/app.py                  # Flask API and static-file server
├── backend/data/resources.json      # Curated learning resources
├── backend/data/roadmaps.json       # Career roadmaps
├── docs/PROJECT_OVERVIEW.md
├── requirements.txt
├── .env.example
└── LICENSE
```

## Current limitations
This is a student project prototype, not a production-ready AI platform. The course catalogue is static; internship results are portal links, not verified live listings. Nearby search opens external map searches and does not use automatic geolocation. The AI tutor requires an API key and internet access. The Flask server currently runs in debug mode for local development only; do not deploy it publicly as-is. Authentication, database/cloud sync, a RAG pipeline, comprehensive tests and production deployment are not implemented yet.

## License
MIT. See LICENSE.
