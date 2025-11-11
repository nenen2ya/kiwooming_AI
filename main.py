# main.py
from fastapi import FastAPI
from pydantic import BaseModel
from scripts.chat_with_kiwooming import get_ai_response

app = FastAPI(title="Kiwooming AI Server")

# ✅ JSON body용 데이터 모델
class ChatRequest(BaseModel):
    text: str
    context: str | None = None

@app.get("/")
def root():
    return {"message": "🚀 Kiuming AI Server Running!"}

@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    """
    프론트/백엔드에서 {text, context} JSON으로 전달하는 요청을 처리
    """
    reply = get_ai_response(req.text, req.context)
    return {"reply": reply}
