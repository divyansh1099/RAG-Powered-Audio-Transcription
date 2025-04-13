from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from app.auth.utils import hash_password, verify_password, create_access_token
from app.db.mongodb import users_collection


router = APIRouter()

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

@router.post("/register")
async def register(user: UserCreate):
    existing = await users_collection.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered.")
    hashed_pw = hash_password(user.password)
    await users_collection.insert_one({
        "email": user.email,
        "password": hashed_pw
    })
    return {"msg": "User registered successfully."}

@router.post("/login")
async def login(user: UserLogin):
    record = await users_collection.find_one({"email": user.email})
    if not record or not verify_password(user.password, record["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    
    # ✅ Store email in the token's `sub` field
    token = create_access_token({
        "sub": user.email
    })

    return {"access_token": token, "token_type": "bearer"}
