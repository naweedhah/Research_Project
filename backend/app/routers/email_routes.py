from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from app.services.auth_service import (
    decode_access_token,
)

from app.services.email_service import (
    send_warning_report,
)


router = APIRouter(
    prefix="/email",
    tags=["Email"],
)

security = HTTPBearer()


@router.post("/send-warning-report")
def send_warning_email(
    credentials: HTTPAuthorizationCredentials = Depends(
        security
    ),
):
    payload = decode_access_token(
        credentials.credentials
    )

    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token.",
        )

    try:
        return send_warning_report(
            user_id=payload["sub"],
            recipient_email=payload["email"],
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Email sending failed: {exc}",
        )