# main.py
from fastapi import FastAPI
from pydantic import BaseModel
from scripts.chat_with_kiwooming import get_ai_response
import requests
import os
import orjson 

app = FastAPI(title="Kiwooming AI Server")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")
PARSER_URL = os.getenv("PARSER_URL", "http://localhost:4001")
COMPARE_URL = os.getenv("COMPARE_URL", "http://localhost:6002/compare")

compare_cache: dict[str, dict] = {}
backend_cache: dict[str, dict] = {}
parser_cache: dict[str, dict] = {}

def get_backend_ui(screen: str):
    screen = screen.lower()
    if screen in backend_cache:
        return backend_cache[screen]

    print(f"🔁 [CACHE MISS] backend_ui: {screen}")
    url = f"{BACKEND_URL}/ui/{screen}"
    res = requests.get(url, timeout=30)
    data = res.json()
    backend_cache[screen] = data
    return data


def get_parser(screen: str):
    screen = screen.lower()
    if screen in parser_cache:
        return parser_cache[screen]

    print(f"🔁 [CACHE MISS] parser: {screen}")
    url = f"{PARSER_URL}/parse/{screen}"
    res = requests.get(url, timeout=30)
    data = res.json()
    parser_cache[screen] = data
    return data


def get_compare(screen: str):
    screen = screen.lower()
    if screen in compare_cache:
        return compare_cache[screen]

    print(f"🔁 [CACHE MISS] compare: {screen}")


    payload = {
        "parser_url": f"{PARSER_URL}/parse/{screen}",
        "backend_url": f"{BACKEND_URL}/ui/{screen}",
    }


    res = requests.post(COMPARE_URL, json=payload, timeout=30)
    data = res.json()
    compare_cache[screen] = data
    return data


from dotenv import load_dotenv
load_dotenv()  # .env 파일 읽기

@app.get("/")
def root():
    return {"message": "🚀 Kiuming AI Server Running!"}

@app.on_event("startup")
def preload_cache():
    preload_screens = ["home", "stockhome", "newsdetail", "order", "quote", "chart"]
    print("🔥 Preloading caches...")

    for sc in preload_screens:
        try:
            get_backend_ui(sc)
            get_parser(sc)
            get_compare(sc)
            print(f"   ✔ {sc} loaded")
        except Exception as e:
            print(f"   ⚠️ preload failed ({sc}): {e}")

    print("🔥 Preload complete!")

class ChatRequest(BaseModel):
    text: str
    context: str | None = None
    section: str | None = None
    scrollY: float | None = 0

import time    

@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    start = time.time()
    print("⏱️ /chat 요청 시작")
    try:
        screen = (req.context or "home").lower()

        backend_json   = get_backend_ui(screen)
        parser_json    = get_parser(screen)
        compare_result = get_compare(screen)

        user_input_full = f"""
        [시스템 규칙]
        너는 '키우밍'이라는 챗봇이야.  
        아래 두 JSON 데이터(`parser_json`과 `backend_json`)를 비교하여,
        사용자가 현재 어떤 화면에 있고 어떤 기능들이 존재하는지 파악해.  
        이 데이터를 기반으로만 대답해야 하며,  
        기능 외에 일반적인 금융지식이나 주식 정보를 물어볼 때만 너의 내장 지식을 사용해.

        [대화 규칙]
        1. **절대 실제 행동을 수행하지 마라.**
           사용자가 화면 이동, 스크롤, 버튼 클릭 등을 요청하더라도
           직접 수행하지 말고, 말로만 안내하라.
           예: "스크롤을 조금 내려보세요." / "왼쪽 상단 버튼을 눌러보세요." / "아래쪽에 뉴스 카드가 있습니다." 등

        2. **현재 스크롤 위치(scrollY)와 섹션(section)을 반드시 고려하라.**
           - 사용자가 상단(`section=bigdata`)이나 중간(`section=ranking`)에 있을 때,
             실제 기능이 화면 하단(`region=bottom`)에 있다면  
             "이 페이지에서 가능하지만 지금 화면에서는 바로 보이지 않아요. 스크롤을 조금 내려보세요 🐾"처럼 안내해야 한다.
           - 반대로 이미 하단(`section=ai_report`)에 있고 관련 기능이 상단에 있다면  
             "위쪽으로 스크롤해 보시면 있습니다" 라고 안내한다.

        3. **backend_json의 'region' 필드를 이용해 위치를 파악하라.**
           - region이 'top'이면 "화면 상단"
           - region이 'middle'이면 "화면 중간"
           - region이 'bottom'이면 "화면 하단"
           으로 간주한다.

        4. **backend_json의 description을 우선 신뢰하라.**
           parser_json의 tag가 backend_json의 element_label과 유사할 경우 연결된 기능으로 본다.

        5. 두 JSON에 공통으로 존재하지 않는 기능은
           "이 화면에는 그런 기능이 없습니다." 라고 답한다.

        6. **너는 사용자의 반려동물 역할이다.**
           귀엽고 친근한 말투로 대답하라. 가끔 🐾 같은 이모지도 섞어줘라.
           사용자가 스트레스를 받거나 화가 난 것 같으면 부드럽게 위로하거나 응원하라.
           무조건 존댓말로만 답변하라.

        7. **사용자가 뉴스 화면에서 뉴스 화면에서 질문하면 관련 정보를 제공하거나 아래 형식으로 간결하게 요약하라.**
            핵심 내용
            - 기사에서 가장 중요한 사실 2~4개를 bullet으로 정리한다.
            - 사건/주체/결과가 명확히 드러나야 한다.

            배경(선택)
            - 필요한 경우에만 한 줄로 배경 또는 맥락을 제공하라.
            의미·영향
            - 기사에서 직접 언급된 영향·의미·시사점을 1~2문장으로 요약하라.
            - 추측해서 확장하지 말고 기사 안에서 확인되는 내용만 기재하라.
            현재 상황
            - 기사에서 언급된 현재 단계(승인, 심사, 발표 등)를 간단히 정리하라.

            다음과 같은 규칙을 따라라.
            기사에서 확인되지 않은 내용은 절대 생성하지 않는다.
            수치는 그대로 보존(금액·비율·날짜·기관명 등)하라.
            5줄 이내로 간결하게, 대신 핵심은 절대 빠뜨리지 않는다.
            질문 의도에 맞게 “투자/경제/정책 기사”는 사실 중심, “사회/사건 기사”는 사건 구조 중심으로 요약하라.

        [현재 맥락]
        - 현재 화면: {req.context}
        - 현재 섹션: {req.section}
        - 현재 스크롤 위치: {req.scrollY}

        [backend_json]
        {orjson.dumps(backend_json).decode()}

        [parser_json]
        {orjson.dumps(parser_json).decode()}

        [compare_result]
        {orjson.dumps(compare_result).decode()}

        [사용자 질문]
        {req.text}
        """

        reply = get_ai_response(user_input_full)
        end = time.time()
        print(f"⏱️ /chat 처리 시간: {end - start:.2f}초")
        return {"reply": reply}

    except Exception as e:
        print(f"❌ [chat_endpoint ERROR] {e}")
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

# # ✅ compare 결과를 요약해주는 함수
# def summarize_ui(compare_result: dict) -> str:
#     elements = compare_result.get("elements", [])
#     screen = compare_result.get("screen", "Unknown")

#     # 요소별 설명 추출
#     desc_list = [f"- {el.get('tag', '?')}: {el.get('description', '설명 없음')}" for el in elements]
#     summary = "\n".join(desc_list)

#     # 최종 요약 문자열
#     return f"[현재 화면: {screen}]\n화면 구성 요소 요약:\n{summary}"
