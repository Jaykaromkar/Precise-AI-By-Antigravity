import asyncio
import httpx
import json

async def test_chat():
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post('http://127.0.0.1:8000/api/chat/stream', 
                                     json={"session_id": 1, "query": "Hello AI"},
                                     timeout=30)
            print("Status:", resp.status_code)
            async for line in resp.aiter_lines():
                print(line)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(test_chat())
