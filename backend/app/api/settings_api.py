from pathlib import Path
import importlib.util
from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.core.security import get_current_user
from app.models.models import User
from app.schemas.schemas import SystemStatusOut

router = APIRouter(prefix="/api/settings", tags=["Settings"])


def _check_tesseract() -> bool:
    settings = get_settings()
    try:
        import pytesseract
        if settings.TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


@router.get("/status", response_model=SystemStatusOut)
def get_system_status(current_user: User = Depends(get_current_user)):
    settings = get_settings()
    return SystemStatusOut(
        llm_configured=bool(settings.LLM_API_KEY and settings.LLM_API_KEY.strip()),
        llm_provider=settings.LLM_PROVIDER,
        llm_model=settings.LLM_MODEL,
        ocr_available=_check_tesseract(),
        faiss_available=importlib.util.find_spec("faiss") is not None,
        max_upload_size_mb=settings.MAX_UPLOAD_SIZE_MB,
    )
