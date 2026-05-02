from fastapi import APIRouter, Body, HTTPException, Request, status

from app.db.report_store import get_report_store
from app.utils.auth import create_access_token, hash_password, verify_password
from app.utils.request_guard import require_authenticated_user

router = APIRouter()


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
async def register(
    email: str = Body(...),
    password: str = Body(...),
):
    store = get_report_store()
    existing = store.get_user_by_email(email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists.")

    user = store.create_user(email=email, password_hash=hash_password(password))
    token = create_access_token(user_id=user["id"], email=user["email"])
    return {
        "user": {"id": user["id"], "email": user["email"], "created_at": user["created_at"]},
        "access_token": token,
        "token_type": "bearer",
    }


@router.post("/auth/login", status_code=status.HTTP_200_OK)
async def login(
    email: str = Body(...),
    password: str = Body(...),
):
    store = get_report_store()
    user = store.get_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    token = create_access_token(user_id=user["id"], email=user["email"])
    return {
        "user": {"id": user["id"], "email": user["email"], "created_at": user["created_at"]},
        "access_token": token,
        "token_type": "bearer",
    }


@router.get("/auth/me", status_code=status.HTTP_200_OK)
async def me(request: Request):
    user = require_authenticated_user(request)
    return {"id": user["id"], "email": user["email"], "created_at": user["created_at"]}
