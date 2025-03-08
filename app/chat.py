from typing import List
from fastapi import WebSocket
from sqlalchemy.orm import Session
from app.models import SessionLocal, Message
from starlette.websockets import WebSocketState
import asyncio
import json

class ChatManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.online_users = set()

    async def connect(self, websocket: WebSocket, display_name: str):
        print(f"🔹 Connecting {display_name} to chat.")
        if websocket.client_state == WebSocketState.CONNECTING:
            await websocket.accept()  # Accept the WebSocket connection
        self.active_connections.append(websocket)
        self.online_users.add(display_name)
        await self.broadcast_online_users()

    def disconnect(self, websocket: WebSocket, display_name: str):
        print(f"❌ {display_name} disconnected from chat.")
        self.active_connections.remove(websocket)
        self.online_users.discard(display_name)
        asyncio.create_task(self.broadcast_online_users())

    async def broadcast(self, sender_username: str, display_name: str, message: str):
        self.save_message(sender_username, message)

        message_data = {
            "type": "message",
            "username": sender_username,  # for avatar
            "display_name": display_name,  # for display purposes
            "message": message
        }

        tasks = [asyncio.create_task(connection.send_text(json.dumps(message_data))) for connection in self.active_connections]
        await asyncio.gather(*tasks)


    async def broadcast_online_users(self):
        data = json.dumps({"type": "online_users", "users": list(self.online_users)})
        tasks = [asyncio.create_task(connection.send_text(data)) for connection in self.active_connections]
        await asyncio.gather(*tasks)

    def save_message(self, sender, text):
        db = SessionLocal()
        new_message = Message(sender=sender, text=text)
        db.add(new_message)
        db.commit()
        db.close()

    def get_chat_history(self):
        db = SessionLocal()
        messages = db.query(Message).order_by(Message.timestamp).all()
        db.close()
        return [{"sender": msg.sender, "text": msg.text, "timestamp": msg.timestamp} for msg in messages]

chat_manager = ChatManager()
