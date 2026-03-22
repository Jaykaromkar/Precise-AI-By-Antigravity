import os
import json
import httpx
from chromadb import PersistentClient
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from core.config import settings

client = PersistentClient(path=settings.CHROMA_PERSIST_DIR)
collection_name = "financial_docs"
# Load local sentence transformers embeddings
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vector_store = Chroma(
    client=client,
    collection_name=collection_name,
    embedding_function=embeddings
)

async def stream_rag_response(query: str, chat_history: list, session_id: int):
    # Search ChromaDB
    try:
        retriever = vector_store.as_retriever(search_kwargs={"k": 4, "filter": {"session_id": session_id}})
        docs = retriever.invoke(query)
    except Exception as e:
        print(f"ChromaDB retrieval error: {e}")
        docs = []

    from services.pii_masker import PIIVault
    vault = PIIVault()
    masked_context = ""
    audit_chunks = []
    
    for doc in docs:
        original = doc.page_content
        masked = vault.mask(original)
        source = doc.metadata.get('filename', 'Unknown')
        
        masked_context += f"\n--- Source: {source} ---\n{masked}"
        audit_chunks.append({"source": source, "original": original, "masked": masked})
        
    audit_data = {"chunks": audit_chunks, "mapping": vault.mapping}
    yield {"type": "audit", "data": audit_data}

    system_prompt = (
        "You are an Expert Financial Analysis Assistant. You use the provided context to answer questions.\n"
        "If you don't know the answer, say so. ALWAYS be helpful, accurate, and format with Markdown.\n"
        "If the user asks for data visualization or charts or current context contains numerical historical tabular data that should be charted, "
        "output a JSON code block with Chart.js compatible data at the *very end* of your response.\n"
        "Format chart block strictly like this:\n```json\n{\"type\": \"bar\", \"data\": {\"labels\": [\"A\"], \"datasets\": [{\"label\": \"value\", \"data\": [1]}]}}\n```\n"
        f"Context provided:\n{masked_context}"
    )

    messages = [{"role": "system", "content": system_prompt}]
    for msg in chat_history[-5:]: # Keep last 5 messages for context
        masked_historic = vault.mask(msg.content)
        messages.append({"role": msg.role, "content": masked_historic})
        
    masked_query = vault.mask(query)
    messages.append({"role": "user", "content": masked_query})
    
    # Send an explicit audit intercept for the prompt itself, so UI restitution catches it
    audit_data = {"chunks": audit_chunks, "mapping": vault.mapping, "prompt_intercepts": len(vault.mapping)}
    yield {"type": "audit", "data": audit_data}

    headers = {
        "Authorization": f"Bearer {settings.GROK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": settings.GROK_MODEL,
        "messages": messages,
        "stream": True
    }

    async with httpx.AsyncClient() as http_client:
        async with http_client.stream("POST", f"{settings.GROK_BASE_URL}/chat/completions", headers=headers, json=payload, timeout=60.0) as response:
            if response.status_code != 200:
                error_msg = await response.aread()
                yield {"type": "error", "data": f"Error from Grok/Groq: {error_msg.decode()}"}
                return
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        if "choices" in data and len(data["choices"]) > 0:
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield {"type": "chunk", "delta": content}
                    except json.JSONDecodeError:
                        continue
