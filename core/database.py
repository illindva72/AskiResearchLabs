"""
database.py — SQLite storage layer for AskiResearchLabs (Python/Streamlit port)

Tables:
  searches    — one row per user research query
  papers      — fetched academic papers tied to a search
  evaluations — AI dimension evaluation results (cached per search)
"""

import sqlite3
import json
import time
import os
from typing import Optional

db_name = os.getenv("DB_NAME", "askiresearchlabs.db")
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), db_name)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create all tables if they don't exist yet."""
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS searches (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL,
            topic         TEXT    NOT NULL,
            sources       TEXT    NOT NULL,   -- JSON array
            area          TEXT,
            domain        TEXT,
            topic_name    TEXT,
            topic_details TEXT,
            created_at    INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS papers (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            search_id       INTEGER NOT NULL REFERENCES searches(id),
            title           TEXT    NOT NULL,
            authors         TEXT    NOT NULL, -- JSON array
            abstract        TEXT,
            year            INTEGER,
            journal         TEXT,
            doi             TEXT,
            url             TEXT,
            citations       INTEGER DEFAULT 0,
            relevance_score INTEGER DEFAULT 0,
            tags            TEXT    NOT NULL DEFAULT '[]', -- JSON array
            source          TEXT,
            created_at      INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS evaluations (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            search_id        INTEGER NOT NULL UNIQUE REFERENCES searches(id),
            feasible         TEXT NOT NULL, -- JSON
            novel            TEXT NOT NULL,
            relevant         TEXT NOT NULL,
            ethical          TEXT NOT NULL,
            scope            TEXT NOT NULL,
            professor_view   TEXT NOT NULL,
            career_alignment TEXT NOT NULL,
            created_at       INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS prerequisites (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            search_id        INTEGER NOT NULL UNIQUE REFERENCES searches(id),
            flowchart        TEXT NOT NULL,
            dataset          TEXT NOT NULL,
            input_vars       TEXT NOT NULL,
            output_vars      TEXT NOT NULL,
            created_at       INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS opportunity_scores (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            search_id        INTEGER NOT NULL UNIQUE REFERENCES searches(id),
            total_score      REAL NOT NULL,
            rating           TEXT NOT NULL,
            profile          TEXT NOT NULL,
            dimensions       TEXT NOT NULL, -- JSON
            created_at       INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS api_metrics (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER REFERENCES users(id),
            search_id        INTEGER REFERENCES searches(id),
            page             TEXT NOT NULL,
            time_taken       REAL NOT NULL,
            is_reevaluation  BOOLEAN NOT NULL DEFAULT 0,
            model_api        TEXT NOT NULL,
            created_at       INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            university TEXT,
            area_interest TEXT,
            domain_interest TEXT,
            specialization TEXT,
            role TEXT DEFAULT 'user',
            hashed_password TEXT,
            otp TEXT,
            otp_expiry INTEGER,
            phone TEXT,
            place TEXT,
            city TEXT,
            country TEXT,
            created_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            message TEXT NOT NULL,
            created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS evaluation_feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            search_id INTEGER NOT NULL REFERENCES searches(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            feedback TEXT NOT NULL,
            created_at INTEGER NOT NULL
        );
        -- add user_id to searches if not exists handled previously

        -- Schema Migration for new scalable Auth
    """)
    try:
        cur.executescript("ALTER TABLE users ADD COLUMN hashed_password TEXT;")
    except sqlite3.OperationalError:
        pass # Column already exists
    try:
        cur.executescript("ALTER TABLE users ADD COLUMN area_interest TEXT;")
    except sqlite3.OperationalError:
        pass
    try:
        cur.executescript("ALTER TABLE users ADD COLUMN domain_interest TEXT;")
    except sqlite3.OperationalError:
        pass
    try:
        cur.executescript("ALTER TABLE searches ADD COLUMN user_id INTEGER NOT NULL DEFAULT 0;")
    except sqlite3.OperationalError:
        pass
    try:
        cur.executescript("ALTER TABLE prerequisites ADD COLUMN matching_papers TEXT NOT NULL DEFAULT '[]';")
    except sqlite3.OperationalError:
        pass
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE searches ADD COLUMN is_favorite BOOLEAN NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE searches ADD COLUMN favorite_reason TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


# ─── API Metrics ──────────────────────────────────────────────────────────────

def log_api_metric(user_id: int, search_id: int, page: str, time_taken: float, is_reevaluation: bool, model_api: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO api_metrics (user_id, search_id, page, time_taken, is_reevaluation, model_api, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, search_id, page, time_taken, is_reevaluation, model_api, int(time.time())))
    conn.commit()
    conn.close()

def get_user_api_call_count(user_id: int) -> int:
    conn = get_conn()
    cur = conn.execute("SELECT COUNT(*) FROM api_metrics WHERE user_id = ?", (user_id,))
    count = cur.fetchone()[0]
    conn.close()
    return count

# ─── Searches ─────────────────────────────────────────────────────────────────

def create_search(user_id: int, topic: str, sources: list, area: str, domain: str,
                  topic_name: str, topic_details: str) -> dict:
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO searches (user_id, topic, sources, area, domain, topic_name, topic_details, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, topic, json.dumps(sources), area or None, domain or None,
         topic_name or None, topic_details or None, int(time.time() * 1000))
    )
    conn.commit()
    row = conn.execute("SELECT * FROM searches WHERE id=?", (cur.lastrowid,)).fetchone()
    conn.close()
    return _row_to_search(row)


def get_all_searches(user_id: Optional[int] = None) -> list[dict]:
    conn = get_conn()
    if user_id is None:
        rows = conn.execute("SELECT * FROM searches ORDER BY created_at DESC").fetchall()
    else:
        rows = conn.execute("SELECT * FROM searches WHERE user_id=? ORDER BY created_at DESC", (user_id,)).fetchall()
    conn.close()
    return [_row_to_search(r) for r in rows]


def get_search(search_id: int) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM searches WHERE id=?", (search_id,)).fetchone()
    conn.close()
    return _row_to_search(row) if row else None


def delete_search(search_id: int) -> None:
    conn = get_conn()
    conn.execute("DELETE FROM papers WHERE search_id=?", (search_id,))
    conn.execute("DELETE FROM evaluations WHERE search_id=?", (search_id,))
    conn.execute("DELETE FROM prerequisites WHERE search_id=?", (search_id,))
    conn.execute("DELETE FROM searches WHERE id=?", (search_id,))
    conn.commit()
    conn.close()


def _row_to_search(row) -> dict:
    d = dict(row)
    d["sources"] = json.loads(d.get("sources", "[]"))
    return d


def toggle_favorite_search(search_id: int, user_id: int, is_favorite: bool, reason: str = "") -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE searches SET is_favorite = ?, favorite_reason = ? WHERE id = ? AND user_id = ?",
        (int(is_favorite), reason, search_id, user_id)
    )
    conn.commit()
    conn.close()

# ─── Papers ───────────────────────────────────────────────────────────────────

def create_paper(search_id: int, title: str, authors: list, abstract: str,
                 year: Optional[int], journal: Optional[str], doi: Optional[str],
                 url: Optional[str], citations: int, relevance_score: int,
                 tags: list, source: str) -> dict:
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO papers
           (search_id, title, authors, abstract, year, journal, doi, url,
            citations, relevance_score, tags, source, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (search_id, title, json.dumps(authors), abstract, year, journal,
         doi, url, citations, relevance_score, json.dumps(tags), source,
         int(time.time() * 1000))
    )
    conn.commit()
    row = conn.execute("SELECT * FROM papers WHERE id=?", (cur.lastrowid,)).fetchone()
    conn.close()
    return _row_to_paper(row)


def get_papers_for_search(search_id: int) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM papers WHERE search_id=? ORDER BY relevance_score DESC",
        (search_id,)
    ).fetchall()
    conn.close()
    return [_row_to_paper(r) for r in rows]


def _row_to_paper(row) -> dict:
    d = dict(row)
    if isinstance(d.get("authors"), str):
        d["authors"] = json.loads(d["authors"])
    if isinstance(d.get("tags"), str):
        d["tags"] = json.loads(d["tags"])
    return d

# ─── Users & Auth ─────────────────────────────────────────────────────────────

def get_user_by_email(email: str) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_id(user_id: int) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def update_user_info(user_id: int, phone: str, place: str, city: str, country: str):
    conn = get_conn()
    conn.execute(
        """UPDATE users 
           SET phone = ?, place = ?, city = ?, country = ?
           WHERE id = ?""",
        (phone, place, city, country, user_id)
    )
    conn.commit()
    conn.close()

def get_all_users() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def create_user(email: str, name: str, university: str, area_interest: str = None, domain_interest: str = None, specialization: str = None, role: str = 'user', hashed_password: str = None) -> dict:
    conn = get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO users (email, name, university, area_interest, domain_interest, specialization, role, hashed_password, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (email, name, university, area_interest, domain_interest, specialization, role, hashed_password, int(time.time() * 1000))
        )
        conn.commit()
        user_id = cur.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return get_user_by_email(email) # type: ignore
    
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row)

def update_user_password(email: str, hashed_password: str):
    conn = get_conn()
    conn.execute("UPDATE users SET hashed_password=? WHERE email=?", (hashed_password, email))
    conn.commit()
    conn.close()

def update_user_otp(email: str, otp: str, expiry: int):
    conn = get_conn()
    conn.execute("UPDATE users SET otp=?, otp_expiry=? WHERE email=?", (otp, expiry, email))
    conn.commit()
    conn.close()

def get_user_storage_size(user_id: int) -> int:
    conn = get_conn()
    cur = conn.cursor()
    # Approx size of searches
    cur.execute("SELECT sum(length(topic) + length(sources) + length(topic_name) + length(topic_details)) FROM searches WHERE user_id=?", (user_id,))
    size_searches = cur.fetchone()[0] or 0
    # Approx size of papers
    cur.execute("""
        SELECT sum(length(title) + length(authors) + length(abstract) + length(tags)) 
        FROM papers 
        WHERE search_id IN (SELECT id FROM searches WHERE user_id=?)
    """, (user_id,))
    size_papers = cur.fetchone()[0] or 0
    # Approx size of evaluations
    cur.execute("""
        SELECT sum(length(feasible) + length(novel) + length(relevant) + length(ethical) + length(scope) + length(professor_view) + length(career_alignment)) 
        FROM evaluations 
        WHERE search_id IN (SELECT id FROM searches WHERE user_id=?)
    """, (user_id,))
    size_evals = cur.fetchone()[0] or 0
    conn.close()
    return size_searches + size_papers + size_evals

# ─── Feedbacks ────────────────────────────────────────────────────────────────

def create_feedback(user_id: int, message: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO feedbacks (user_id, message, created_at) VALUES (?, ?, ?)",
        (user_id, message, int(time.time() * 1000))
    )
    conn.commit()
    conn.close()

def get_all_feedbacks() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("""
        SELECT f.*, u.email, u.name 
        FROM feedbacks f 
        JOIN users u ON f.user_id = u.id 
        ORDER BY f.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def create_evaluation_feedback(search_id: int, user_id: int, feedback: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO evaluation_feedbacks (search_id, user_id, feedback, created_at) VALUES (?, ?, ?, ?)",
        (search_id, user_id, feedback, int(time.time() * 1000))
    )
    conn.commit()
    conn.close()

# ─── Evaluations ──────────────────────────────────────────────────────────────

def create_evaluation(search_id: int, feasible: dict, novel: dict,
                      relevant: dict, ethical: dict, scope: dict,
                      professor_view: dict, career_alignment: dict) -> dict:
    conn = get_conn()
    # Delete any existing evaluation for this search (upsert pattern)
    conn.execute("DELETE FROM evaluations WHERE search_id=?", (search_id,))
    conn.execute(
        """INSERT INTO evaluations
           (search_id, feasible, novel, relevant, ethical, scope,
            professor_view, career_alignment, created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (search_id, json.dumps(feasible), json.dumps(novel), json.dumps(relevant),
         json.dumps(ethical), json.dumps(scope), json.dumps(professor_view),
         json.dumps(career_alignment), int(time.time() * 1000))
    )
    conn.commit()
    conn.close()
    return get_evaluation_for_search(search_id)


def get_evaluation_for_search(search_id: int) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM evaluations WHERE search_id=?", (search_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    for key in ("feasible", "novel", "relevant", "ethical", "scope",
                "professor_view", "career_alignment"):
        if isinstance(d.get(key), str):
            d[key] = json.loads(d[key])
    return d

# ─── Prerequisites ────────────────────────────────────────────────────────────

def create_prerequisites(search_id: int, flowchart: str, dataset: str, input_vars: str, output_vars: str, matching_papers: list) -> dict:
    conn = get_conn()
    conn.execute("DELETE FROM prerequisites WHERE search_id=?", (search_id,))
    conn.execute(
        """INSERT INTO prerequisites
           (search_id, flowchart, dataset, input_vars, output_vars, matching_papers, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (search_id, flowchart, dataset, input_vars, output_vars, json.dumps(matching_papers), int(time.time() * 1000))
    )
    conn.commit()
    conn.close()
    return get_prerequisites_for_search(search_id)

def get_prerequisites_for_search(search_id: int) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM prerequisites WHERE search_id=?", (search_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    if isinstance(d.get("matching_papers"), str):
        try:
            d["matching_papers"] = json.loads(d["matching_papers"])
        except json.JSONDecodeError:
            d["matching_papers"] = []
    return d

# ─── Opportunity Scores ────────────────────────────────────────────────────────────

def create_opportunity_score(search_id: int, total_score: float, rating: str, profile: str, dimensions: dict) -> None:
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO opportunity_scores (search_id, total_score, rating, profile, dimensions, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(search_id) DO UPDATE SET
            total_score = excluded.total_score,
            rating = excluded.rating,
            profile = excluded.profile,
            dimensions = excluded.dimensions,
            created_at = excluded.created_at
        """,
        (search_id, total_score, rating, profile, json.dumps(dimensions), int(time.time() * 1000))
    )
    conn.commit()
    conn.close()

def get_opportunity_score_for_search(search_id: int) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM opportunity_scores WHERE search_id = ?", (search_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    if isinstance(d.get("dimensions"), str):
        d["dimensions"] = json.loads(d["dimensions"])
    return d
