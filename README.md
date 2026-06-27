# ResearchTrack — FastAPI Academic Paper Explorer

**ResearchTrack** is a FastAPI-backed academic paper search and thesis proposal evaluator.

This repository provides a web service for searching academic papers across **IEEE, ACM, arXiv, and Semantic Scholar**, storing results in SQLite, and generating a Claude-powered evaluation of research ideas across seven expert dimensions.

---

## What it does

### Research Search
- Search by Research Area, Research Domain, Research Topic Name, Research Topic Details
- Parallel paper discovery from IEEE, ACM, arXiv, and Semantic Scholar
- Deduplicates results by DOI and ranks them by relevance
- Stores search history and fetched papers in a local SQLite database

### AI Evaluation
- Claude AI evaluation of research topics across seven dimensions:
  - **Feasible**
  - **Novel**
  - **Relevant**
  - **Ethical**
  - **Scope**
  - **Professor View**
  - **Career Alignment**
- Evaluation results are cached in SQLite to avoid repeated AI calls

### Search History and User Flow
- User registration and login via email/password
- Browse past searches and evaluation status
- Delete outdated searches
- View per-search paper lists and paper metadata

---

## Current Architecture

```
researchtrack-streamlit/
├── main.py                   FastAPI app entrypoint
├── app/
│   ├── __init__.py
│   ├── core/
│   │   └── security.py       Authentication and JWT helpers
│   ├── routes/
│   │   ├── views.py          Search, dimensions, bot, and page rendering
│   │   ├── api.py            Health check and API route stubs
│   │   └── auth_views.py     Login/signup/logout routes
│   ├── static/               CSS and web assets
│   └── templates/            Jinja2 templates for HTML pages
├── core/
│   ├── database.py           SQLite storage layer and persistence helpers
│   ├── fetchers.py           Academic paper fetchers (OpenAlex, CrossRef, arXiv)
│   └── evaluate.py           Claude AI evaluation prompt and API integration
├── researchtrack.db          Auto-created SQLite datastore
├── .env                      Local environment variables (gitignored)
├── .env.example              Template for needed env vars
├── requirements.txt         Python dependencies
├── README.md                Project overview and architecture
└── EXECUTION.md             Local run and deployment instructions
```

> Note: The active app in this repository is a FastAPI web service. A `backup/` folder contains an older Streamlit port and is not the current runtime.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI |
| Runtime server | Uvicorn |
| Templates | Jinja2 |
| Database | SQLite (`sqlite3`) |
| Email / OTP | SMTP via Python `smtplib` |
| AI evaluation | Anthropic Claude |
| HTTP / APIs | `requests` |
| Auth | `passlib`, `PyJWT` |

---

## External APIs

| API | Purpose | Key required? |
|---|---|---|
| OpenAlex | Academic paper discovery | No |
| CrossRef | Paper metadata / DOI lookup | No |
| arXiv | Preprint search | No |
| Anthropic | AI evaluation service | Yes |

---

## Deployment Notes

- Local development uses `uvicorn main:app --reload`
- Production-ready deployment can target **Zoho Catalyst AppSail**
- `main.py` is the correct service entrypoint for both local and cloud deployment

---

## Useful Files

- `main.py` — FastAPI application runner
- `core/database.py` — SQLite DB schema and persistence
- `core/fetchers.py` — paper fetchers for OpenAlex, CrossRef, arXiv
- `core/evaluate.py` — Anthropic Claude evaluation logic
- `app/routes/views.py` — search and page rendering routes
- `app/routes/auth_views.py` — authentication routes
- `app/routes/api.py` — API and health endpoints
- `.env.example` — template for environment variables
- `requirements.txt` — Python dependency list
- `EXECUTION.md` — full local and Zoho Catalyst deployment guide
