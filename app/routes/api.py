from fastapi import APIRouter

router = APIRouter(prefix="/api")

@router.get("/health")
async def health_check():
    return {"status": "ok", "message": "ResearchTrack backend is running"}

# Future endpoints for bot streaming, auth verification, etc., will go here.