import requests

res = requests.post(
    "http://localhost:6002/chat",
    json={"text": "안녕", "context": "Home"}
)
print(res.json())
