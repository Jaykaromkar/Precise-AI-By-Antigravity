import urllib.request

req = urllib.request.Request("http://localhost:8000/api/chat/message/stream?session_id=1&query=test")
try:
    with urllib.request.urlopen(req) as response:
        for line in response:
            print(line.decode('utf-8'), end="")
except Exception as e:
    print(f"Error: {e}")
