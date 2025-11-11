# main.py
from fastapi import FastAPI
from scripts.chat_with_kiwooming import get_ai_response  # ← 이게 네 실제 AI 함수라고 가정

app = FastAPI()

@app.get("/")
def root():
    return {"message": "🚀 Kiuming AI Server Running!"}

@app.post("/chat")
def chat_endpoint(text: str, context: str = None):
    reply = get_ai_response(text, context)
    return {"reply": reply}
