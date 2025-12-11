from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas import UserCreate, Token, UserOut, LoginSchema
from utils.hashing import hash_password, verify_password
from utils.jwt_utils import create_access_token

router = APIRouter()


# ---------------- SIGNUP ---------------- #

@router.post('/signup', response_model=UserOut)
def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail='Email already registered')

    hashed = hash_password(user_in.password)

    user = User(
        full_name=user_in.full_name,
        email=user_in.email,
        password_hash=hashed,
        role=user_in.role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ---------------- LOGIN (UPDATED FOR JSON) ---------------- #

@router.post('/login', response_model=Token)
def login(payload: LoginSchema, db: Session = Depends(get_db)):
    # accept JSON: { "email": "...", "password": "..." }

    user = db.query(User).filter(User.email == payload.email).first()

    if not user:
        raise HTTPException(status_code=401, detail='Incorrect credentials')

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail='Incorrect credentials')

    # generate JWT
    token = create_access_token({
        "user_id": user.id,
        "role": user.role
    })

    return {"access_token": token, "token_type": "bearer"}
