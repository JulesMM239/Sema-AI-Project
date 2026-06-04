from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.db.database import get_db
from app.db.models import User
from app.db.schemas import LoginRequest, SignupRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=payload.email, full_name=payload.full_name, password_hash=hash_password(payload.password))
    # First registered user becomes admin for MVP convenience
    if db.query(User).count() == 0:
        user.is_admin = True
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.email, extra={"is_admin": user.is_admin})
    return TokenResponse(access_token=token, is_admin=user.is_admin)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(user.email, extra={"is_admin": user.is_admin})
    return TokenResponse(access_token=token, is_admin=user.is_admin)
