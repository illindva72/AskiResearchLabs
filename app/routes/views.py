from fastapi import APIRouter, Request, Form, UploadFile, File, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from typing import List, Optional
import logging
from core import database as db
from core import fetchers
from app.core.security import get_current_user_from_cookie

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Initialize database to make sure it exists
db.init_db()

@router.get("/")
async def read_root(request: Request):
    user = get_current_user_from_cookie(request)
    return templates.TemplateResponse(request, "pages/home.html", {"request": request, "user": user})

@router.get("/search")
async def search_page(request: Request):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    return templates.TemplateResponse(request, "pages/search.html", {"request": request, "papers": None, "user": user})

@router.post("/search")
async def execute_search(
    request: Request,
    area: str = Form("Predictive Analytics"),
    topic_name: str = Form(...),
    domain: str = Form(""),
    sources: List[str] = Form(...),
    topic_details: str = Form(""),
    limit: int = Form(20),
    uploaded_doc: Optional[UploadFile] = File(None)
):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    if not topic_name.strip():
        # Ideally add error handling context here
        return templates.TemplateResponse(request, "pages/search.html", {"request": request, "error": "Research Topic Name is required.", "papers": None})

    if not sources:
        return templates.TemplateResponse(request, "pages/search.html", {"request": request, "error": "Select at least one source.", "papers": None})

    _, _, label = fetchers.build_compound_query(area, domain, topic_name, topic_details)

    doc_text = ""
    if uploaded_doc and uploaded_doc.filename:
        filename = uploaded_doc.filename.lower()
        content = await uploaded_doc.read()
        if filename.endswith(".docx"):
            try:
                import io
                import docx
                doc_obj = docx.Document(io.BytesIO(content))
                doc_text = "\n".join([p.text for p in doc_obj.paragraphs])
            except ImportError:
                print("Missing python-docx")
        elif filename.endswith(".txt") or filename.endswith(".md"):
            doc_text = content.decode("utf-8", errors="ignore")

    # Use authenticated user
    user_id = user["id"]

    search_rec = db.create_search(
        user_id=user_id,
        topic=label or topic_name,
        sources=sources,
        area=area,
        domain=domain,
        topic_name=topic_name,
        topic_details=topic_details,
    )

    papers = fetchers.fetch_papers(
        search_id=search_rec["id"],
        area=area,
        domain=domain,
        topic_name=topic_name,
        topic_details=topic_details,
        sources=sources,
        limit=limit,
        document_text=doc_text,
    )

    saved = []
    seen_dois = set()
    for p in papers:
        doi = p.get("doi") or ""
        if doi and doi in seen_dois:
            continue
        if doi:
            seen_dois.add(doi)
        saved.append(db.create_paper(
            search_id=search_rec["id"],
            title=p["title"],
            authors=p.get("authors", []),
            abstract=p.get("abstract", ""),
            year=p.get("year"),
            journal=p.get("journal"),
            doi=p.get("doi"),
            url=p.get("url"),
            citations=p.get("citations", 0),
            relevance_score=p.get("relevance_score", 0),
            tags=p.get("tags", []),
            source=p.get("source", ""),
        ))

    return templates.TemplateResponse(request, "pages/search.html", {
        "request": request,
        "search": search_rec,
        "papers": saved,
        "user": user
    })

@router.get("/history")
async def history_page(request: Request):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    searches = db.get_all_searches(user_id=None if user.get("role") == "admin" else user["id"])
    
    # Calculate storage size
    size_bytes = db.get_user_storage_size(user["id"])
    size_mb = size_bytes / (1024 * 1024)
    limit_mb = 150.0
    
    return templates.TemplateResponse(request, "pages/history.html", {
        "request": request, 
        "user": user, 
        "searches": searches,
        "size_mb": size_mb,
        "limit_mb": limit_mb,
        "over_limit": size_mb >= limit_mb
    })

@router.post("/upgrade")
async def upgrade_plan_route(request: Request):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
        
    size_bytes = db.get_user_storage_size(user["id"])
    size_mb = size_bytes / (1024 * 1024)
    
    from core.auth import send_upgrade_email
    send_upgrade_email(user["email"], user["name"], size_mb)
    
    return templates.TemplateResponse(request, "pages/history.html", {
        "request": request,
        "user": user,
        "searches": db.get_all_searches(user_id=None if user.get("role") == "admin" else user["id"]),
        "size_mb": size_mb,
        "limit_mb": 150.0,
        "over_limit": size_mb >= 150.0,
        "success": "Upgrade request sent to admin."
    })

@router.get("/dimensions")
async def dimensions_list_page(request: Request):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    searches = db.get_all_searches(user_id=None if user.get("role") == "admin" else user["id"])
    return templates.TemplateResponse(request, "pages/dimensions.html", {"request": request, "user": user, "searches": searches})

@router.get("/dimensions/{search_id}")
async def search_detail_page(request: Request, search_id: int):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    search = db.get_search(search_id)
    if not search or (user.get("role") != "admin" and search.get("user_id") != user["id"]):
        return templates.TemplateResponse(request, "pages/dimensions.html", {"request": request, "user": user, "error": "Search not found or access denied."})
        
    papers = db.get_papers_for_search(search_id)
    eval_data = db.get_evaluation_for_search(search_id)
    
    return templates.TemplateResponse(request, "pages/search_detail.html", {
        "request": request,
        "user": user,
        "search": search,
        "papers": papers,
        "eval": eval_data
    })

@router.post("/history/{search_id}/delete")
async def delete_search_route(request: Request, search_id: int):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
        
    search = db.get_search(search_id)
    if search and (user.get("role") == "admin" or search.get("user_id") == user["id"]):
        db.delete_search(search_id)
        
    return RedirectResponse(url="/history", status_code=302)

@router.post("/dimensions/{search_id}/evaluate")
async def evaluate_search_route(
    request: Request, 
    search_id: int, 
    feedback: str = Form(None)
):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
        
    search = db.get_search(search_id)
    if not search or (user.get("role") != "admin" and search.get("user_id") != user["id"]):
        return RedirectResponse(url="/dimensions", status_code=302)
        
    papers = db.get_papers_for_search(search_id)
    eval_data = db.get_evaluation_for_search(search_id)
    
    if feedback:
        db.create_evaluation_feedback(search_id, user["id"], feedback)
    
    from core.evaluate import evaluate_research
    try:
        result = evaluate_research(
            area=search.get("area", ""),
            domain=search.get("domain", ""),
            topic_name=search.get("topic_name") or search.get("topic", ""),
            topic_details=search.get("topic_details", ""),
            papers=[
                {
                    "title":     p["title"],
                    "source":    p.get("source", ""),
                    "year":      p.get("year"),
                    "citations": p.get("citations", 0),
                }
                for p in papers
            ],
            previous_feedback=feedback,
            previous_eval=eval_data
        )
        db.create_evaluation(
            search_id=search_id,
            feasible=result.get("feasible", {}),
            novel=result.get("novel", {}),
            relevant=result.get("relevant", {}),
            ethical=result.get("ethical", {}),
            scope=result.get("scope", {}),
            professor_view=result.get("professorView", {}),
            career_alignment=result.get("careerAlignment", {}),
        )
    except Exception as e:
        logger.exception(f"Error generating AI evaluation for search {search_id}: {e}")
        eval_data = db.get_evaluation_for_search(search_id)
        return templates.TemplateResponse(request, "pages/search_detail.html", {
            "request": request,
            "user": user,
            "search": search,
            "papers": papers,
            "eval": eval_data,
            "error": str(e)
        })
        
    return RedirectResponse(url=f"/dimensions/{search_id}", status_code=302)

@router.get("/bot")
async def bot_page(request: Request):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    return templates.TemplateResponse(request, "pages/bot_agent.html", {"request": request, "user": user})

@router.get("/execution")
async def execution_list_page(request: Request):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    searches = db.get_all_searches(user_id=None if user.get("role") == "admin" else user["id"])
    return templates.TemplateResponse(request, "pages/execution.html", {"request": request, "user": user, "searches": searches})

@router.get("/execution/{search_id}")
async def execution_detail_page(request: Request, search_id: int):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    search = db.get_search(search_id)
    if not search or (user.get("role") != "admin" and search.get("user_id") != user["id"]):
        return templates.TemplateResponse(request, "pages/execution.html", {"request": request, "user": user, "error": "Search not found or access denied."})
        
    factors = db.get_prerequisites_for_search(search_id)
    
    return templates.TemplateResponse(request, "pages/execution_detail.html", {
        "request": request,
        "user": user,
        "search": search,
        "factors": factors
    })

@router.post("/execution/{search_id}/generate")
async def generate_execution_factors(request: Request, search_id: int):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
        
    search = db.get_search(search_id)
    if not search or (user.get("role") != "admin" and search.get("user_id") != user["id"]):
        return RedirectResponse(url="/execution", status_code=302)
        
    papers = db.get_papers_for_search(search_id)
    
    from core.evaluate import generate_prerequisites
    try:
        result = generate_prerequisites(
            area=search.get("area", ""),
            domain=search.get("domain", ""),
            topic_name=search.get("topic_name") or search.get("topic", ""),
            topic_details=search.get("topic_details", ""),
            papers=[
                {
                    "title":     p["title"],
                    "source":    p.get("source", ""),
                    "year":      p.get("year"),
                    "abstract":  p.get("abstract", "")
                }
                for p in papers
            ]
        )
        db.create_prerequisites(
            search_id=search_id,
            flowchart=result.get("flowchart", ""),
            dataset=result.get("dataset", ""),
            input_vars=result.get("input_vars", ""),
            output_vars=result.get("output_vars", ""),
            matching_papers=result.get("matching_papers", [])
        )
    except Exception as e:
        logger.exception(f"Error generating execution factors for search {search_id}: {e}")
        factors = db.get_prerequisites_for_search(search_id)
        return templates.TemplateResponse(request, "pages/execution_detail.html", {
            "request": request,
            "user": user,
            "search": search,
            "factors": factors,
            "error": str(e)
        })
        
    return RedirectResponse(url=f"/execution/{search_id}", status_code=302)

# ─── Opportunity Score ─────────────────────────────────────────────────────────

@router.get("/opportunity")
async def opportunity_list_page(request: Request):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    searches = db.get_all_searches(user_id=None if user.get("role") == "admin" else user["id"])
    return templates.TemplateResponse(request, "pages/opportunity.html", {"request": request, "user": user, "searches": searches})

@router.get("/opportunity/{search_id}")
async def opportunity_detail_page(request: Request, search_id: int):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    search = db.get_search(search_id)
    if not search or (user.get("role") != "admin" and search.get("user_id") != user["id"]):
        return templates.TemplateResponse(request, "pages/opportunity.html", {"request": request, "user": user, "error": "Search not found or access denied."})
    
    score_data = db.get_opportunity_score_for_search(search_id)
    
    return templates.TemplateResponse(request, "pages/opportunity_detail.html", {
        "request": request,
        "user": user,
        "search": search,
        "score_data": score_data
    })

@router.post("/opportunity/{search_id}/evaluate")
async def generate_opportunity_score(request: Request, search_id: int):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
        
    search = db.get_search(search_id)
    if not search or (user.get("role") != "admin" and search.get("user_id") != user["id"]):
        return RedirectResponse(url="/opportunity", status_code=302)
        
    form = await request.form()
    profile = form.get("profile", "Default")
    
    existing_score = db.get_opportunity_score_for_search(search_id)
    existing_dimensions = existing_score["dimensions"] if existing_score else None
        
    from core.evaluate import evaluate_opportunity
    try:
        result = evaluate_opportunity(
            area=search.get("area", ""),
            domain=search.get("domain", ""),
            topic_name=search.get("topic_name") or search.get("topic", ""),
            topic_details=search.get("topic_details", ""),
            profile_name=profile,
            existing_dimensions=existing_dimensions
        )
        db.create_opportunity_score(
            search_id=search_id,
            total_score=result["total_score"],
            rating=result["rating"],
            profile=result["profile"],
            dimensions=result["dimensions"]
        )
    except Exception as e:
        logger.exception(f"Error generating opportunity score for search {search_id}: {e}")
        score_data = db.get_opportunity_score_for_search(search_id)
        return templates.TemplateResponse(request, "pages/opportunity_detail.html", {
            "request": request,
            "user": user,
            "search": search,
            "score_data": score_data,
            "error": str(e)
        })
        
    return RedirectResponse(url=f"/opportunity/{search_id}", status_code=302)

# ─── Account & Subscription ──────────────────────────────────────────────────

@router.get("/account")
async def account_info_page(request: Request):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Re-fetch user to get the latest optional fields
    full_user = db.get_user_by_id(user["id"])
    return templates.TemplateResponse(request, "pages/account.html", {"request": request, "user": full_user})

@router.post("/account")
async def update_account_info(request: Request):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    form = await request.form()
    phone = form.get("phone", "")
    place = form.get("place", "")
    city = form.get("city", "")
    country = form.get("country", "")
    
    db.update_user_info(user["id"], phone, place, city, country)
    return RedirectResponse(url="/account?success=1", status_code=302)

@router.get("/subscription")
async def subscription_page(request: Request):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
        
    return templates.TemplateResponse(request, "pages/subscription.html", {"request": request, "user": user})

@router.post("/contact-admin")
async def contact_admin(request: Request):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    form = await request.form()
    title = form.get("title", "")
    subject = form.get("subject", "")
    query_details = form.get("query_details", "")
    
    from core.auth import send_contact_email
    send_contact_email(user["sub"], user["name"], title, subject, query_details)
    
    return RedirectResponse(url="/subscription?success=1", status_code=302)