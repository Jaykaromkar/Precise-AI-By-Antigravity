from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from core.database import get_db
from models.domain import ChatSession, DocumentMetadata, DocumentReport
from services.document_parser import parse_and_split_document
from services.rag_pipeline import vector_store
from services.report_generator import generate_document_report, stream_manager
from sse_starlette.sse import EventSourceResponse
from fastapi import BackgroundTasks, Request
import json
import asyncio

router = APIRouter()

@router.post("/upload")
async def upload_document(session_id: int, background_tasks: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(get_db)):
    db_session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not db_session:
        db_session = ChatSession(id=session_id)
        db.add(db_session)
        db.commit()
        db.refresh(db_session)

    try:
        import os
        file_content = await file.read()
        
        # Save file securely for preview
        session_upload_dir = os.path.join("uploads", str(session_id))
        os.makedirs(session_upload_dir, exist_ok=True)
        file_path = os.path.join(session_upload_dir, file.filename)
        with open(file_path, "wb") as f:
            f.write(file_content)

        chunks = parse_and_split_document(file_content, file.filename)
        
        if chunks:
            for chunk in chunks:
                chunk.metadata['session_id'] = session_id
            vector_store.add_documents(chunks)

        doc_meta = DocumentMetadata(
            session_id=db_session.id,
            filename=file.filename,
            file_type=file.filename.split('.')[-1]
        )
        db.add(doc_meta)
        db.commit()
        db.refresh(doc_meta)

        full_text = "\n\n".join([chunk.page_content for chunk in chunks])
        if db_session.user and db_session.user.email:
            background_tasks.add_task(generate_document_report, doc_meta.id, full_text, file.filename, db_session.user.email, db_session.user.username)
        else:
            background_tasks.add_task(generate_document_report, doc_meta.id, full_text, file.filename)

        return {"message": "Document uploaded successfully", "chunks": len(chunks), "document_id": doc_meta.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list/{session_id}")
def list_documents(session_id: int, db: Session = Depends(get_db)):
    docs = db.query(DocumentMetadata).filter(DocumentMetadata.session_id == session_id).all()
    # Check if a report exists for each doc
    results = []
    for d in docs:
        rep = db.query(DocumentReport).filter(DocumentReport.document_id == d.id).first()
        status = rep.status if rep else "READY" # Using READY for legacy docs without a report schema
        results.append({"id": d.id, "filename": d.filename, "uploaded_at": d.uploaded_at, "report_status": status})
    return results

@router.get("/report/{document_id}")
def get_report(document_id: int, db: Session = Depends(get_db)):
    rep = db.query(DocumentReport).filter(DocumentReport.document_id == document_id).first()
    if not rep or not rep.report_json:
        raise HTTPException(status_code=404, detail="Report not generated yet")
    return {"status": rep.status, "report_json": json.loads(rep.report_json)}

@router.get("/report/stream/{document_id}")
async def stream_report(request: Request, document_id: int):
    q = stream_manager.get_queue(document_id)
    
    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                # Wait for next event
                event = await asyncio.wait_for(q.get(), timeout=30.0)
                yield {
                    "event": event["event"],
                    "data": event["data"]
                }
                if event["event"] in ["complete", "error"]:
                    break
        except asyncio.TimeoutError:
            yield {"event": "error", "data": json.dumps({"detail": "Timeout waiting for report stream."})}
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"detail": str(e)})}
            
    return EventSourceResponse(event_generator())
