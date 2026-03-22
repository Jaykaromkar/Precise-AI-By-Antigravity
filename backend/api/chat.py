from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from core.database import get_db
from models.domain import ChatSession, ChatMessage
from services.rag_pipeline import stream_rag_response
from core.config import settings
import json

router = APIRouter()

@router.get("/provider")
async def get_provider():
    provider = settings.AI_PROVIDER.title() if settings.AI_PROVIDER else "OpenRouter"
    if "api.groq.com" in settings.GROK_BASE_URL:
        provider = "Groq"
    elif "api.openai.com" in settings.GROK_BASE_URL:
        provider = "OpenAI"
    return {"provider": provider, "model": settings.GROK_MODEL}

class ChatRequest(BaseModel):
    session_id: int
    query: str

class CreateSessionRequest(BaseModel):
    user_id: int

@router.get("/message/stream")
async def chat_stream_get(request: Request, session_id: int, query: str, db: Session = Depends(get_db)):
    db_session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not db_session:
        return {"error": "Session missing"}
    
    user_msg = ChatMessage(session_id=session_id, role="user", content=query)
    db.add(user_msg)
    db.commit()

    history = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()

    async def event_generator():
        full_response = ""
        try:
            async for item in stream_rag_response(query, history, session_id):
                if await request.is_disconnected():
                    break
                if isinstance(item, dict):
                    if item.get("type") == "audit":
                        yield {
                            "event": "audit",
                            "data": json.dumps(item['data'])
                        }
                    elif item.get("type") == "chunk":
                        chunk = item["delta"]
                        full_response += chunk
                        yield {
                            "event": "message",
                            "data": json.dumps({'delta': chunk})
                        }
                    elif item.get("type") == "error":
                        yield {
                            "event": "error",
                            "data": json.dumps({"detail": item['data']})
                        }
                else:
                    yield {
                        "event": "error",
                        "data": json.dumps({"detail": str(item)})
                    }
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"detail": str(e)})
            }
        finally:
            if full_response:
                from core.database import SessionLocal
                with SessionLocal() as final_db:
                    assistant_msg = ChatMessage(session_id=session_id, role="assistant", content=full_response)
                    final_db.add(assistant_msg)
                    final_db.commit()
            
            yield {
                "event": "message",
                "data": "[DONE]"
            }

    return EventSourceResponse(event_generator())

@router.get("/history/{session_id}")
def get_history(session_id: int, db: Session = Depends(get_db)):
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()
    return [{"role": m.role, "content": m.content, "created_at": m.created_at} for m in messages]

@router.get("/sessions/{user_id}")
def get_sessions(user_id: int, db: Session = Depends(get_db)):
    sessions = db.query(ChatSession).filter(ChatSession.user_id == user_id).order_by(ChatSession.created_at.desc()).all()
    return [{"id": s.id, "title": s.title, "created_at": s.created_at} for s in sessions]

@router.post("/sessions")
def create_session(req: CreateSessionRequest, db: Session = Depends(get_db)):
    new_session = ChatSession(title="New Analysis Session", user_id=req.user_id)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return {"id": new_session.id, "title": new_session.title}

class UpdateSessionRequest(BaseModel):
    title: str

@router.put("/sessions/{session_id}")
def update_session(session_id: int, req: UpdateSessionRequest, db: Session = Depends(get_db)):
    db_session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if db_session:
        db_session.title = req.title
        db.commit()
    return {"status": "ok"}

@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db)):
    from models.domain import DocumentMetadata
    db_session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if db_session:
        # Manual Cascade Delete
        db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
        db.query(DocumentMetadata).filter(DocumentMetadata.session_id == session_id).delete()
        db.delete(db_session)
        db.commit()
    return {"status": "ok"}
