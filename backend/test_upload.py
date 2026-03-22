import httpx
import asyncio

async def test_upload():
    try:
        files = {'file': ('test.txt', b'Hello !!, this is a financial text document.', 'text/plain')}
        async with httpx.AsyncClient() as client:
            resp = await client.post('http://127.0.0.1:8000/api/documents/upload?session_id=1', files=files, timeout=30)
            with open('err.txt', 'w') as f:
                f.write(f"Status: {resp.status_code}\nResponse: {resp.text}")
    except Exception as e:
        with open('err.txt', 'w') as f:
            f.write(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_upload())
