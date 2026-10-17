from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from app.schemas.auth_schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
)

from app.services.auth_service import (
    register_user,
    authenticate_user,
    create_access_token,
    decode_access_token,
)

from app.services.email_service import (
    send_warning_report,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

security = HTTPBearer()


@router.post(
    "/register",
    response_model=UserResponse,
)
def register(request: RegisterRequest):
    user = register_user(
        name=request.name,
        email=request.email,
        password=request.password,
    )

    if user is None:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists.",
        )

    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
    }


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(request: LoginRequest):
    user = authenticate_user(
        email=request.email,
        password=request.password,
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    token = create_access_token(user)

    warning_email_status = None

    try:
        warning_email_status = send_warning_report(
            user_id=user["id"],
            recipient_email=user["email"],
        )

    except Exception as exc:
        # Login must still succeed even if email sending fails.
        warning_email_status = {
            "status": "email_failed",
            "message": str(exc),
        }

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
        },
        "warning_email": warning_email_status,
    }


@router.get(
    "/me",
    response_model=UserResponse,
)
def current_user(
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

    return {
        "id": payload["sub"],
        "name": payload["name"],
        "email": payload["email"],
    }