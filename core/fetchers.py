"""
fetchers.py — Academic paper fetchers for AskiResearchLabs (Python/Streamlit port)

Sources supported:
  - IEEE     → OpenAlex (publisher filter P4310319808) + CrossRef (member:263)
  - ACM      → OpenAlex (publisher filter P4310319798) + CrossRef (member:320)
  - arXiv    → arXiv API quoted-phrase search
  - Semantic Scholar → OpenAlex broad search (no publisher filter)

All functions return a list of normalised paper dicts ready for DB insertion.
"""

import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
import requests
import datetime

HEADERS = {"User-Agent": "AskiResearchLabs/1.0 (mailto:research@tracker.app)"}
TIMEOUT = 12

OPENALEX_IEEE_ID = "P4310319808"
OPENALEX_ACM_ID  = "P4310319798"


# ─── Low-level API callers ────────────────────────────────────────────────────

def _fetch_openalex_publisher(query: str, publisher_id: str, limit: int) -> list:
    try:
        min_year = datetime.datetime.now().year - 2
        filter_val = f"primary_location.source.publisher_lineage:{publisher_id},publication_year:>{min_year-1},primary_location.source.type:journal"
        fields = ("title,publication_year,primary_location,cited_by_count,"
                  "doi,open_access,authorships,abstract_inverted_index")
        url = (
            f"https://api.openalex.org/works"
            f"?search={requests.utils.quote(query)}"
            f"&per-page={limit}"
            f"&filter={requests.utils.quote(filter_val)}"
            f"&select={fields}"
            f"&sort=relevance_score:desc"
        )
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if not r.ok:
            return []
        return r.json().get("results", [])
    except Exception:
        return []


def _fetch_openalex_broad(query: str, limit: int) -> list:
    try:
        min_year = datetime.datetime.now().year - 2
        filter_val = f"publication_year:>{min_year-1},primary_location.source.type:journal"
        fields = ("title,publication_year,primary_location,cited_by_count,"
                  "doi,open_access,authorships,abstract_inverted_index")
        url = (
            f"https://api.openalex.org/works"
            f"?search={requests.utils.quote(query)}"
            f"&per-page={limit}"
            f"&filter={requests.utils.quote(filter_val)}"
            f"&select={fields}"
            f"&sort=relevance_score:desc"
        )
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if not r.ok:
            return []
        return r.json().get("results", [])
    except Exception:
        return []


def _fetch_crossref_member(query: str, member_id: str, limit: int) -> list:
    try:
        min_year = datetime.datetime.now().year - 2
        fields = "title,author,abstract,published,container-title,DOI,is-referenced-by-count"
        filter_val = f"member:{member_id},type:journal-article,from-pub-date:{min_year}-01-01"
        url = (
            f"https://api.crossref.org/works"
            f"?query={requests.utils.quote(query)}"
            f"&rows={limit}"
            f"&filter={filter_val}"
            f"&select={fields}"
            f"&sort=relevance"
        )
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if not r.ok:
            return []
        items = r.json().get("message", {}).get("items", [])
        return [i for i in items if i.get("title")]
    except Exception:
        return []


def _fetch_arxiv(query: str, limit: int) -> list:
    try:
        words = query.strip().split()[:8]
        phrase = "+".join(words)
        arxiv_query = f'ti:"{phrase}"+OR+abs:"{phrase}"'
        url = (
            f"https://export.arxiv.org/api/query"
            f"?search_query={arxiv_query}"
            f"&start=0&max_results={limit * 3}"
            f"&sortBy=relevance&sortOrder=descending"
        )
        r = requests.get(url, headers={"User-Agent": "AskiResearchLabs/1.0"}, timeout=TIMEOUT)
        if not r.ok:
            return []

        entries = []
        # Namespace-aware parsing
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(r.text)
        for entry in root.findall("atom:entry", ns):
            title_el   = entry.find("atom:title", ns)
            summary_el = entry.find("atom:summary", ns)
            id_el      = entry.find("atom:id", ns)
            pub_el     = entry.find("atom:published", ns)

            title    = re.sub(r"\s+", " ", title_el.text.strip()) if title_el is not None else ""
            abstract = re.sub(r"\s+", " ", summary_el.text.strip()) if summary_el is not None else ""
            link     = id_el.text.strip() if id_el is not None else ""
            year_str = (pub_el.text or "")[:4] if pub_el is not None else ""
            year     = int(year_str) if year_str.isdigit() else None

            authors = [
                name.text.strip()
                for author in entry.findall("atom:author", ns)
                for name in [author.find("atom:name", ns)]
                if name is not None
            ]
            min_year = datetime.datetime.now().year - 2
            if title and year and year >= min_year:
                entries.append({
                    "title": title,
                    "abstract": abstract,
                    "id": link,
                    "year": year,
                    "authors": authors,
                })
        return entries[:limit]
    except Exception:
        return []


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _reconstruct_abstract(inverted: Optional[dict]) -> str:
    if not inverted:
        return ""
    pairs = [(pos, word) for word, positions in inverted.items() for pos in positions]
    pairs.sort(key=lambda x: x[0])
    return " ".join(w for _, w in pairs)


def _extract_authors(authorships: list) -> list[str]:
    if not isinstance(authorships, list):
        return []
    return [
        a.get("author", {}).get("display_name", "")
        for a in authorships[:8]
        if a.get("author", {}).get("display_name")
    ]


def _detect_source(src: Optional[dict]) -> str:
    if not src:
        return "Semantic Scholar"
    name    = (src.get("display_name") or "").lower()
    pub     = (src.get("publisher") or "").lower()
    lineage = [s.lower() for s in (src.get("publisher_lineage_names") or [])]
    host    = (src.get("host_organization_name") or "").lower()

    if "ieee" in name or "ieee" in pub or any("ieee" in s for s in lineage) or "ieee" in host:
        return "IEEE"
    if "acm" in name or "acm" in pub or any("acm" in s for s in lineage) or "association for computing" in host:
        return "ACM"
    if "springer" in name or "springer" in pub:
        return "Springer"
    if "elsevier" in name or "elsevier" in pub:
        return "Elsevier"
    return "Semantic Scholar"


def compute_relevance(title: str, abstract: str, context: str) -> int:
    query_words = [w for w in context.lower().split() if len(w) > 3]
    text = (title + " " + abstract).lower()
    score = 35
    for w in query_words:
        if w in title.lower():
            score += 12
        elif w in text:
            score += 5
    return min(score, 99)


_TAG_MAP = [
    ("machine learning",           "Machine Learning"),
    ("deep learning",              "Deep Learning"),
    ("neural network",             "Neural Networks"),
    ("transformer",                "Transformers"),
    ("natural language processing","NLP"),
    (" nlp ",                      "NLP"),
    ("large language model",       "LLMs"),
    (" llm",                       "LLMs"),
    ("computer vision",            "Computer Vision"),
    ("reinforcement learning",     "Reinforcement Learning"),
    ("federated",                  "Federated Learning"),
    ("mlops",                      "MLOps"),
    ("generative",                 "Generative AI"),
    ("diffusion model",            "Diffusion Models"),
    ("graph neural",               "GNNs"),
    ("object detection",           "Object Detection"),
    ("segmentation",               "Segmentation"),
    ("optimization",               "Optimization"),
    ("benchmark",                  "Benchmark"),
    ("survey",                     "Survey"),
    ("systematic review",          "Survey"),
    ("financial",                  "Finance"),
    ("investment",                 "Finance"),
    ("healthcare",                 "Healthcare"),
    ("medical",                    "Healthcare"),
    ("robotics",                   "Robotics"),
    ("autonomous",                 "Autonomous Systems"),
    ("security",                   "Security"),
    ("privacy",                    "Privacy"),
    ("edge computing",             "Edge Computing"),
    ("time series",                "Time Series"),
    ("anomaly detection",          "Anomaly Detection"),
    ("sentiment",                  "Sentiment Analysis"),
    ("recommendation",             "Recommender Systems"),
    ("devops",                     "DevOps"),
    ("pipeline",                   "Pipelines"),
    ("risk",                       "Risk Management"),
    ("classification",             "Classification"),
]


def extract_tags(title: str, abstract: str) -> list[str]:
    combined = (title + " " + abstract).lower()
    tags: list[str] = []
    for key, tag in _TAG_MAP:
        if key in combined and tag not in tags:
            tags.append(tag)
        if len(tags) >= 5:
            break
    return tags


# ─── Query builder ────────────────────────────────────────────────────────────

STOP_WORDS = {
    "this","that","with","from","have","will","been","they","their","which",
    "about","also","some","such","into","more","than","when","using","based",
    "approach","method","proposed","paper","study","research","work","result",
    "show","used","data","model","system","these","those","each","both","where",
    "what","were","would",
}


def build_compound_query(area: str, domain: str, topic_name: str,
                          topic_details: str) -> tuple[str, str, str]:
    """Returns (primary_query, secondary_query, label)."""
    primary = " ".join(filter(None, [topic_name, domain]))

    all_text = " ".join(filter(None, [area, domain, topic_name, topic_details]))
    words = re.sub(r"[^a-z0-9\s]", " ", all_text.lower()).split()
    words = [w for w in words if len(w) >= 4 and w not in STOP_WORDS]
    seen: set[str] = set()
    unique = [w for w in words if not (w in seen or seen.add(w))]  # type: ignore
    secondary = " ".join([topic_name] + unique[:6])

    label = " › ".join(filter(None, [area, domain, topic_name]))
    return primary, secondary, label


# ─── Main public function ─────────────────────────────────────────────────────

def fetch_papers(search_id: int, area: str, domain: str, topic_name: str,
                 topic_details: str, sources: list[str],
                 limit: int = 20, document_text: str = "") -> list[dict]:
    """
    Fetch papers from all selected sources in parallel.
    Returns a deduplicated list of normalised paper dicts.
    """
    primary, secondary, _ = build_compound_query(area, domain, topic_name, topic_details)
    full_context = " ".join(filter(None, [area, domain, topic_name, topic_details, document_text]))

    tasks: list = []  # list of (callable, *args)

    if "IEEE" in sources:
        ieee_lim = max(1, int(limit * 0.5))
        tasks.append(("openalex_pub", primary, OPENALEX_IEEE_ID, ieee_lim, "IEEE"))
        tasks.append(("crossref",     primary, "263",             ieee_lim, "IEEE"))

    if "ACM" in sources:
        acm_lim = max(1, int(limit * 0.4))
        tasks.append(("openalex_pub", primary, OPENALEX_ACM_ID, acm_lim, "ACM"))
        tasks.append(("crossref",     primary, "320",            acm_lim, "ACM"))

    if "Semantic Scholar" in sources:
        tasks.append(("openalex_broad", primary, max(1, int(limit * 0.5)), None, None))

    if "arXiv" in sources:
        tasks.append(("arxiv", secondary, max(1, int(limit * 0.4)), None, None))

    paper_list: list[dict] = []
    seen_dois: set[str] = set()

    def add_paper(p: dict) -> None:
        doi = p.get("doi") or ""
        if doi and doi in seen_dois:
            return
        if doi:
            seen_dois.add(doi)
        paper_list.append(p)

    def run_task(task):
        kind = task[0]
        if kind == "openalex_pub":
            _, query, pub_id, lim, forced_source = task
            results = _fetch_openalex_publisher(query, pub_id, lim)
            out = []
            for r in results:
                if not r.get("title"):
                    continue
                abstract = _reconstruct_abstract(r.get("abstract_inverted_index"))
                authors  = _extract_authors(r.get("authorships", []))
                doi      = (r.get("doi") or "").replace("https://doi.org/", "")
                src      = (r.get("primary_location") or {}).get("source")
                venue    = (src or {}).get("display_name", "") if src else ""
                out.append({
                    "search_id":       search_id,
                    "title":           r["title"],
                    "authors":         authors,
                    "abstract":        abstract or "Abstract not available.",
                    "year":            r.get("publication_year"),
                    "journal":         venue or None,
                    "doi":             doi or None,
                    "url":             r.get("doi") or (r.get("open_access") or {}).get("oa_url"),
                    "citations":       r.get("cited_by_count") or 0,
                    "relevance_score": compute_relevance(r["title"], abstract, full_context),
                    "tags":            extract_tags(r["title"], abstract),
                    "source":          forced_source,
                })
            return out

        elif kind == "crossref":
            _, query, member_id, lim, forced_source = task
            results = _fetch_crossref_member(query, member_id, lim)
            out = []
            for r in results:
                title = (r["title"][0] if isinstance(r["title"], list) else r["title"]) or ""
                if not title:
                    continue
                doi     = r.get("DOI") or ""
                authors = [
                    " ".join(filter(None, [a.get("given"), a.get("family")]))
                    for a in (r.get("author") or [])
                ]
                pub     = r.get("published", {})
                parts   = pub.get("date-parts", [[None]])[0] if pub else [None]
                year    = parts[0] if parts else None
                journal = ((r.get("container-title") or []) + [""])[0]
                abstract = r.get("abstract") or ""
                out.append({
                    "search_id":       search_id,
                    "title":           title,
                    "authors":         authors,
                    "abstract":        abstract or "Abstract not available.",
                    "year":            year,
                    "journal":         journal or None,
                    "doi":             doi or None,
                    "url":             f"https://doi.org/{doi}" if doi else None,
                    "citations":       r.get("is-referenced-by-count") or 0,
                    "relevance_score": compute_relevance(title, abstract, full_context),
                    "tags":            extract_tags(title, abstract),
                    "source":          forced_source,
                })
            return out

        elif kind == "openalex_broad":
            _, query, lim, _, _ = task
            results = _fetch_openalex_broad(query, lim)
            out = []
            for r in results:
                if not r.get("title"):
                    continue
                abstract = _reconstruct_abstract(r.get("abstract_inverted_index"))
                authors  = _extract_authors(r.get("authorships", []))
                doi      = (r.get("doi") or "").replace("https://doi.org/", "")
                src_obj  = (r.get("primary_location") or {}).get("source")
                venue    = (src_obj or {}).get("display_name", "") if src_obj else ""
                detected = _detect_source(src_obj)
                # Skip if already fetched by dedicated IEEE/ACM tasks
                if detected == "IEEE" and "IEEE" in sources:
                    continue
                if detected == "ACM" and "ACM" in sources:
                    continue
                out.append({
                    "search_id":       search_id,
                    "title":           r["title"],
                    "authors":         authors,
                    "abstract":        abstract or "Abstract not available.",
                    "year":            r.get("publication_year"),
                    "journal":         venue or None,
                    "doi":             doi or None,
                    "url":             r.get("doi") or (r.get("open_access") or {}).get("oa_url"),
                    "citations":       r.get("cited_by_count") or 0,
                    "relevance_score": compute_relevance(r["title"], abstract, full_context),
                    "tags":            extract_tags(r["title"], abstract),
                    "source":          detected,
                })
            return out

        elif kind == "arxiv":
            _, query, lim, _, _ = task
            results = _fetch_arxiv(query, lim)
            out = []
            for r in results:
                if not r.get("title"):
                    continue
                out.append({
                    "search_id":       search_id,
                    "title":           r["title"],
                    "authors":         r.get("authors", []),
                    "abstract":        r.get("abstract") or "Abstract not available.",
                    "year":            r.get("year"),
                    "journal":         "arXiv preprint",
                    "doi":             None,
                    "url":             r.get("id"),
                    "citations":       0,
                    "relevance_score": compute_relevance(r["title"], r.get("abstract",""), full_context),
                    "tags":            extract_tags(r["title"], r.get("abstract","")),
                    "source":          "arXiv",
                })
            return out

        return []

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(run_task, t): t for t in tasks}
        for future in as_completed(futures):
            for paper in (future.result() or []):
                add_paper(paper)

    # Rank and filter conceptually
    paper_list = rank_and_filter_papers_conceptually(paper_list, area, domain, topic_name, topic_details, document_text, limit)
    
    return paper_list

def rank_and_filter_papers_conceptually(papers: list[dict], area: str, domain: str, topic_name: str, topic_details: str, document_text: str, limit: int) -> list[dict]:
    import anthropic, json, os, re
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or not papers:
        papers.sort(key=lambda p: p.get("relevance_score", 0), reverse=True)
        return papers[:limit]
        
    client_kwargs = {"api_key": api_key}
    if os.getenv("ANTHROPIC_BASE_URL"):
        client_kwargs["base_url"] = os.getenv("ANTHROPIC_BASE_URL")
    client = anthropic.Anthropic(**client_kwargs)
    
    payload = []
    # Send top 40 initial keyword-matched papers
    papers.sort(key=lambda p: p.get("relevance_score", 0), reverse=True)
    for i, p in enumerate(papers[:40]):
        payload.append({
            "id": i,
            "title": p.get("title"),
            "abstract": p.get("abstract")[:800] # Truncate abstract to save tokens
        })
        
    doc_context = f"\n=== USER RESEARCH DOCUMENT ===\n{document_text[:2000]}\n==============================\n" if document_text else ""
    
    prompt = f"""
You are an expert AI Research Assistant. Your task is to rank and filter a list of academic papers based on their conceptual relevance to a specific research topic.
You should find more relevant topics in terms of concept rather than simple wording.

RESEARCH TOPIC:
Area: {area}
Domain: {domain}
Topic Name: {topic_name}
Topic Details: {topic_details}
{doc_context}

Here are the retrieved papers:
{json.dumps(payload, indent=2)}

Evaluate each paper conceptually. Does it directly address the input ideas?
DO NOT include papers that are irrelevant to the input ideas.
Return a JSON array of the most relevant papers, ranked from most relevant (1) to least relevant.
Return up to {limit} papers.

Return ONLY a valid JSON array of objects in this exact format:
[
  {{ "id": integer, "rank": integer, "reason": "Short explanation of conceptual match." }}
]
"""
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2500,
            system="Respond ONLY with a valid JSON array. Be extremely strict about removing irrelevant papers.",
            messages=[{"role": "user", "content": prompt}]
        )
        raw = (msg.content[0].text or "").strip()
        cleaned = re.sub(r"^```json\s*", "", raw, flags=re.IGNORECASE)
        cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"```\s*$", "", cleaned).strip()
        
        analysis_arr = json.loads(cleaned)
        
        ranked_papers = []
        for item in analysis_arr:
            idx = item.get("id")
            if idx is not None and 0 <= idx < len(papers):
                paper = papers[idx]
                paper["rank"] = item.get("rank")
                paper["abstract"] = f"**💡 Conceptual Match Rank #{item.get('rank')}:** {item.get('reason')}\n\n{paper.get('abstract', '')}"
                # Override relevance score with conceptual rank logic to maintain order in UI
                paper["relevance_score"] = 100 - int(item.get("rank", 0)) 
                ranked_papers.append(paper)
                
        ranked_papers.sort(key=lambda p: p.get("rank", 999))
        return ranked_papers
    except Exception as e:
        print(f"Conceptual ranking failed: {e}")
        papers.sort(key=lambda p: p.get("relevance_score", 0), reverse=True)
        return papers[:limit]
