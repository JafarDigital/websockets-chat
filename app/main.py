from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, Form, Request, Depends
from fastapi.templating import Jinja2Templates
from app.auth import get_current_user, get_db
from app.auth import router as auth_router
from app.chat import chat_manager
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from starlette.websockets import WebSocketState
import json
import os
from fastapi.staticfiles import StaticFiles

app = FastAPI()
router = APIRouter()
app.include_router(auth_router)

templates = Jinja2Templates(directory="app/templates")  # ✅ Ensure correct path
app.mount("/static", StaticFiles(directory="app/static"), name="static")  # ✅ Serve static files
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "supersecretkey"))

@app.get("/")
async def home(request: Request, user: dict = Depends(get_current_user)):
    chat_history = chat_manager.get_chat_history()  # ✅ Get past messages
    return templates.TemplateResponse("index.html", {"request": request, "user": user, "chat_history": chat_history})

@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})    

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
    
    new_user = User(username=username, email=email, password=hashed_password, display_name=display_name)
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/login", status_code=303)

@app.get("/settings")
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await websocket.accept()
    user = await get_current_user(websocket)
    if not user:
        await websocket.close()
        return

    display_name = user.get("display_name", username)
    sender_username = username  # Use username explicitly

    await chat_manager.connect(websocket, display_name)

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            if "message" in message_data:
                await chat_manager.broadcast(sender_username, display_name, message_data["message"])
    except WebSocketDisconnect:
        chat_manager.disconnect(websocket, display_name)
