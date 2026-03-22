from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import asyncio
from core.database import get_db
from models.domain import User
from services.email_service import send_welcome_email, send_login_alert, send_password_recovery

router = APIRouter()

class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class ForgotPassword(BaseModel):
    email: str

@router.post("/register")
async def register(user: UserRegister, db: Session = Depends(get_db)):
    db_user = db.query(User).filter((User.username == user.username) | (User.email == user.email)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    new_user = User(username=user.username, email=user.email, password=user.password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Send welcome email asynchronously via event loop isolation
    asyncio.create_task(send_welcome_email(new_user.email, new_user.username, new_user.password))
    
    return {"message": "User created successfully", "user_id": new_user.id, "username": new_user.username}

@router.post("/login")
async def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter((User.username == user.username) & (User.password == user.password)).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Send login alert asynchronously via event loop isolation
    if db_user.email:
        asyncio.create_task(send_login_alert(db_user.email, db_user.username))
    
    return {"message": "Login successful", "user_id": db_user.id, "username": db_user.username}

@router.post("/forgot-password")
async def forgot_password(req: ForgotPassword, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == req.email).first()
    if not db_user:
        return {"message": "If an account exists, a recovery email was sent."}
    
    asyncio.create_task(send_password_recovery(db_user.email, db_user.username, db_user.password))
    return {"message": "Recovery email sent successfully."}

@router.get("/me/{user_id}")
async def get_user_details(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": db_user.id,
        "username": db_user.username,
        "email": db_user.email
    }
