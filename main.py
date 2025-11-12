# main.py
from fastapi import FastAPI
from pydantic import BaseModel
from scripts.chat_with_kiwooming import get_ai_response
import requests

app = FastAPI(title="Kiwooming AI Server")

compare_cache: dict[str, dict] = {}  # {"screen_name": compare_result_json}

from dotenv import load_dotenv
load_dotenv()  # .env 파일 읽기


# ✅ JSON body용 데이터 모델
class ChatRequest(BaseModel):
    text: str
    context: str | None = None

@app.get("/")
def root():
    return {"message": "🚀 Kiuming AI Server Running!"}

@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    try:
        screen = req.context or "Home"

        # 1️⃣ UI 데이터 로드
        backend_res = requests.get(f"http://localhost:8001/ui/{screen}")
        backend_json = backend_res.json()

        parser_res = requests.get(f"http://localhost:4001/parse/{screen}")
        parser_json = parser_res.json()

        # 2️⃣ AI가 직접 비교하도록 프롬프트 구성
        user_input_full = f"""
            [시스템 규칙]
            너는 '키우밍'이라는 챗봇이야.  
            아래 두 JSON 데이터(`parser_json`과 `backend_json`)를 비교하여,  
            사용자가 현재 어떤 화면에 있고 어떤 기능들이 존재하는지 파악해.  
            이 데이터를 기반으로만 대답해야 하며,  
            기능 외에 일반적인 금융지식이나 주식 정보를 물어볼 때만 너의 내장 지식을 사용해.

            [parser_json]
            {parser_json}

            [backend_json]
            {backend_json}

            [사용자 질문]
            {req.text}

            비교 규칙:
            1. backend_json의 elements.description을 기준으로 설명을 우선 신뢰한다.
            2. parser_json의 tag와 backend_json의 element_label이 유사하면 연결된다고 간주한다.
            3. 두 데이터에 공통으로 등장하지 않는 기능은 "이 화면에는 없습니다."라고 답한다.
            """

        reply = get_ai_response(user_input_full)
        return {"reply": reply}

    except Exception as e:
        return {"reply": f"오류 발생: {str(e)}"}



class CompareRequest(BaseModel):
    parser_url: str  
    backend_url: str

@app.post("/compare")
def compare_ui(req: CompareRequest):
    try:
        parser_res = requests.get(req.parser_url)
        parser_json = parser_res.json()

        backend_res = requests.get(req.backend_url)
        backend_json = backend_res.json()

        results = []
        parser_elements = parser_json.get("elements", [])
        backend_components = backend_json.get("components", [])

        for el in parser_elements:
            matched_desc = None
            for comp in backend_components:
                for be in comp.get("elements", []):
                    if be["element_label"].lower() in el.get("tag", "").lower():
                        matched_desc = be["description"]
                        break
                if matched_desc:
                    break
            results.append({
                "tag": el.get("tag"),
                "attrs": el.get("attrs"),
                "description": matched_desc or "설명 없음"
            })

        return {"screen": parser_json.get("screen"), "elements": results}
    except Exception as e:
        return {"error": str(e)}

# ✅ compare 결과를 요약해주는 함수
def summarize_ui(compare_result: dict) -> str:
    elements = compare_result.get("elements", [])
    screen = compare_result.get("screen", "Unknown")

    # 요소별 설명 추출
    desc_list = [f"- {el.get('tag', '?')}: {el.get('description', '설명 없음')}" for el in elements]
    summary = "\n".join(desc_list)

    # 최종 요약 문자열
    return f"[현재 화면: {screen}]\n화면 구성 요소 요약:\n{summary}"
