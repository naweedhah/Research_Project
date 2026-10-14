from fastapi import APIRouter, HTTPException

from app.schemas.ai_schemas import AIChatRequest, AIChatResponse
from app.services.ai_service import answer_ai_question


router = APIRouter(
    prefix="/ai",
    tags=["AI Health Assistant"],
)


@router.post("/chat", response_model=AIChatResponse)
def chat_with_ai(request: AIChatRequest):
    try:
        return answer_ai_question(
            message=request.message,
            district=request.district,
            year=request.year,
            month=request.month,
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"AI assistant could not process the request: {exc}",
        )