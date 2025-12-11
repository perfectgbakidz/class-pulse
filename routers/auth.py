from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas import UserCreate, Token, UserOut
from utils.hashing import hash_password, verify_password
from utils.jwt_utils import create_access_token

router = APIRouter()

@router.post('/signup', response_model=UserOut)
def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail='Email already registered')
    hashed = hash_password(user_in.password)
    user = User(full_name=user_in.full_name, email=user_in.email, password_hash=hashed, role=user_in.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

from fastapi.security import OAuth2PasswordRequestForm

@router.post('/login', response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2PasswordRequestForm has fields: username, password
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user:
        raise HTTPException(status_code=401, detail='Incorrect credentials')
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail='Incorrect credentials')
    token = create_access_token({"user_id": user.id, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}