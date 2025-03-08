from fastapi import APIRouter, Request, Form, Depends, HTTPException, File, UploadFile
from starlette.responses import RedirectResponse
from starlette.config import Config  # ✅ Add this line
from app.models import SessionLocal, User, database
from passlib.context import CryptContext
from PIL import Image
import os
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth

config = Config(".env")  # Ако искаш да пазиш ключовете в .env файл

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth = OAuth(config)
oauth.register(
    "google",
    client_id=config("GOOGLE_CLIENT_ID", default="your_google_client_id"),
    client_secret=config("GOOGLE_CLIENT_SECRET", default="your_google_client_secret"),
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    access_token_url="https://oauth2.googleapis.com/token",
    client_kwargs={"scope": "openid email profile"},
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ Local User Registration
@router.post("/register")
async def register(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(...),
    db: Session = Depends(get_db),
):
    hashed_password = pwd_context.hash(password)
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # ✅ Check if username or email already exists
    existing_user = db.query(User).filter((User.username == username) | (User.email == email)).first()
    if existing_user:
        if existing_user.username == username:
            raise HTTPException(status_code=400, detail="Username already taken")
        if existing_user.email == email:
            raise HTTPException(status_code=400, detail="Email already registered")

    # ✅ Create new user
    new_user = User(username=username, email=email, password=hashed_password, display_name=display_name)
    db.add(new_user)
    db.commit()
    
	# ✅ Automatically log in the user after registration
    Request.session["user"] = {
        "username": new_user.username,
        "display_name": new_user.display_name,
        "profile_picture": new_user.profile_picture
    }
    
    return RedirectResponse(url="/", status_code=303)

# ✅ Local Login
@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username).first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid username or password")

    if not pwd_context.verify(password, user.password):  # ✅ Fix Password Verification
        raise HTTPException(status_code=400, detail="Invalid username or password")

    request.session["user"] = {
        "username": user.username,
        "display_name": user.display_name,
        "profile_picture": user.profile_picture
    }

    return RedirectResponse(url="/", status_code=303)

async def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        return None  # No user logged in
    return user

@router.get("/auth/google/login")
async def login_google(request: Request):
    return await oauth.google.authorize_redirect(request, "http://127.0.0.1:8000/auth/google/callback")

@router.get("/auth/google/callback")
async def auth_google_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user = await oauth.google.parse_id_token(request, token)
    
    request.session["user"] = {
        "username": user["email"].split("@")[0],  # Use part of the email as username
        "display_name": user.get("name", "Unknown"),
        "profile_picture": user.get("picture", "https://via.placeholder.com/150")
    }
    return RedirectResponse(url="/")

@router.post("/upload-avatar")
async def upload_avatar(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    file_path = f"app/static/avatars/{user['username']}.png"
    
    # ✅ Resize image
    image = Image.open(file.file)
    image.thumbnail((150, 150))  # Resize
    image.save(file_path, "PNG")

    # ✅ Update profile picture in DB
    db_user = db.query(User).filter(User.username == user["username"]).first()
    db_user.profile_picture = f"/static/avatars/{user['username']}.png"
    db.commit()
    
    return {"message": "Avatar uploaded successfully"}

@router.post("/update-profile")
async def update_profile(
    request: Request, display_name: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)
):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    db_user = db.query(User).filter(User.username == user["username"]).first()
    db_user.display_name = display_name
    db_user.password = pwd_context.hash(password)
    db.commit()

    request.session["user"]["display_name"] = display_name
    return RedirectResponse(url="/", status_code=303)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")
