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
        pii_mapping = {}
        try:
            async for item in stream_rag_response(query, history, session_id):
                if await request.is_disconnected():
                    break
                if isinstance(item, dict):
                    if item.get("type") == "audit":
                        if "mapping" in item['data']:
                            pii_mapping = item['data']['mapping']
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
                import re
                
                parts = re.split(r'(```json.*?```)', full_response, flags=re.DOTALL)
                for i, part in enumerate(parts):
                    if part.startswith('```json'):
                        for tag, real_val in pii_mapping.items():
                            core_tag = tag.replace('[', '').replace(']', '')
                            numeric_val = "".join([c for c in str(real_val) if c.isdigit() or c == '.'])
                            if not numeric_val: numeric_val = "0"
                            part = part.replace(tag, numeric_val)
                            part = re.sub(rf'\b{re.escape(core_tag)}\b', numeric_val, part)
                        part = re.sub(r'\[(?:MONEY|CARDINAL|PERCENT|DATE|NAME|EMAIL|PHONE)_\d+\]', '0', part)
                        parts[i] = part
                    else:
                        for tag, real_val in pii_mapping.items():
                            span_html = f'<span class="bg-blue-500/20 text-blue-300 border border-blue-500/30 px-1 rounded text-[0.9em]" title="Securely restored from database">{real_val}</span>'
                            part = part.replace(tag, span_html)
                            
                            core_tag = tag.replace('[', '').replace(']', '')
                            numeric_val = "".join([c for c in str(real_val) if c.isdigit() or c == '.'])
                            if not numeric_val: numeric_val = "0"
                            part = re.sub(rf'\b{re.escape(core_tag)}\b', numeric_val, part)
                        part = re.sub(r'\[(?:MONEY|CARDINAL|PERCENT|DATE|NAME|EMAIL|PHONE)_\d+\]\s*=\s*', '', part)
                        part = re.sub(r'\s*\[(?:MONEY|CARDINAL|PERCENT|DATE|NAME|EMAIL|PHONE)_\d+\]', '', part)
                        parts[i] = part
                
                full_response = "".join(parts)

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
