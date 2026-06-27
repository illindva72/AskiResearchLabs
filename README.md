# ResearchTrack — FastAPI Academic Paper Explorer & Model Evaluator

**ResearchTrack** is a FastAPI-backed academic research tracking platform designed for data scientists and researchers.

This repository provides a web service for searching academic papers across **IEEE, ACM, arXiv, and Semantic Scholar**, storing results in a local SQLite database, and utilizing **Claude 3.5 Sonnet** to generate comprehensive AI evaluations, execution plans, and opportunity scores for your research topics.

---

## What it does

### 🔍 Research Search
- Search by Research Area, Research Domain, Research Topic Name, and Topic Details.
- Parallel paper discovery from IEEE, ACM, arXiv, and Semantic Scholar.
- Deduplicates results by DOI and ranks them by relevance.
- Stores search history and fetched papers in a local SQLite database.

### 📊 Model Opportunity Score
- Interactive Plotly-based dashboard evaluating whether an AI/ML topic is worth pursuing.
- Evaluates 10 critical dimensions (Problem Value, Data Availability, Technical Feasibility, ROI Potential, etc.) on a 1-10 scale using Claude.
- **Scoring Profiles:** Instantly toggle between Default, Startup, Research, and Enterprise profiles to dynamically adjust the dimension weights and recalculate the final score out of 100 without hitting the API again.
- Radar charts for raw dimension comparisons and Bar charts for weighted contributions.

### 🛠️ Model Execution Factors
- Generates realistic execution plans for research topics.
- **Architecture Flowcharts:** ASCII-based structural workflow diagrams.
- **Dataset Needs:** Recommended datasets, sources, sizes, and formats.
- **Model Variables:** Clear input and output variables for the ML model.
- **Literature Match:** Cross-references with existing academic papers.

### 🧠 AI Evaluation (Summary of Dimensions)
- Claude AI evaluation of research topics across seven foundational dimensions:
  - **Feasible, Novel, Relevant, Ethical, Scope, Professor View, Career Alignment**
- Evaluation results are cached in SQLite to prevent redundant AI API calls.

### 👤 User Flow
- User registration and login via email/password.
- Browse past searches, execution factors, and opportunity scores.
- Clean up and delete outdated searches.

---

## Current Architecture

```
AskiResearchLab/
├── main.py                   FastAPI app entrypoint
├── app/
│   ├── __init__.py
│   ├── core/
│   │   └── security.py       Authentication and JWT helpers
│   ├── routes/
│   │   ├── views.py          Search, dimensions, execution, opportunity, and page rendering
│   │   ├── api.py            Health check and API route stubs
│   │   └── auth_views.py     Login/signup/logout routes
│   ├── static/               CSS and web assets
│   └── templates/            Jinja2 templates for HTML pages (Plotly integrated)
├── core/
│   ├── database.py           SQLite storage layer (Users, Searches, Opportunity Scores, etc.)
│   ├── fetchers.py           Academic paper fetchers (OpenAlex, CrossRef, arXiv)
│   └── evaluate.py           Claude API integration, prompts, and mathematical weighting
├── researchtrack.db          Auto-created SQLite datastore
├── .env                      Local environment variables (gitignored)
├── .env.example              Template for needed env vars
├── requirements.txt         Python dependencies
├── README.md                Project overview and architecture
└── EXECUTION.md             Local run and deployment instructions
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI |
| Runtime server | Uvicorn |
| Templates | Jinja2 |
| Frontend Charts | Plotly.js |
| Database | SQLite (`sqlite3`) |
| Email / OTP | SMTP via Python `smtplib` |
| AI evaluation | Anthropic Claude 3.5 Sonnet (using `anthropic-beta` headers) |
| HTTP / APIs | `requests` |
| Auth | `passlib`, `PyJWT` |

---

## External APIs

| API | Purpose | Key required? |
|---|---|---|
| OpenAlex | Academic paper discovery | No |
| CrossRef | Paper metadata / DOI lookup | No |
| arXiv | Preprint search | No |
| Anthropic | AI evaluation & scoring | Yes |

---

## Deployment Notes

- Local development uses `uvicorn main:app --reload`
- Production-ready deployment can target **Zoho Catalyst AppSail**
- `main.py` is the correct service entrypoint for both local and cloud deployment

See [EXECUTION.md](EXECUTION.md) for step-by-step local setup and deployment instructions.
