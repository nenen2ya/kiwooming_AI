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


    # compare_url 로 HTTP 요청하지 말고 함수로 직접 실행
    data = compare_ui(CompareRequest(**payload))
    compare_cache[screen] = data
    return data


from datetime import datetime

def get_live_chart_data():
    try:
        # 오늘 날짜 YYYYMMDD
        today = datetime.now().strftime("%Y%m%d")

        # 고정 종목코드
        code = "039490"

        # 백엔드 차트 API URL
        url = f"{BACKEND_URL}/chart/{code}?base_dt={today}"

        print(f"📡 Fetching live chart: {url}")
        res = requests.get(url, timeout=8)
        res.raise_for_status()

        return res.json()

    except Exception as e:
        print(f"❌ live_chart fetch error: {e}")
        return None

def compute_chart_indicators(chart_json):
    try:
        candles = chart_json.get("stk_dt_pole_chart_qry", [])

        # 🔥 문자열 → 숫자 변환
        closes = [int(c["cur_prc"]) for c in candles]
        highs  = [int(c["high_pric"]) for c in candles]
        lows   = [int(c["low_pric"]) for c in candles]
        volumes = [int(c["trde_qty"]) for c in candles]

        def ma(arr, n):
            if len(arr) < n:
                return None
            return sum(arr[-n:]) / n

        return {
            "MA5": ma(closes, 5),
            "MA10": ma(closes, 10),
            "MA20": ma(closes, 20),
            "MA60": ma(closes, 60),
            "MA120": ma(closes, 120),

            "recent_closes": closes[-5:],
            "recent_highs": highs[-5:],
            "recent_lows": lows[-5:],
            "recent_volumes": volumes[-5:],
        }

    except Exception as e:
        print(f"❌ indicator compute error: {e}")
        return {}



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
        raw_context = req.context or "home"
        screen = raw_context.strip("/").lower().split("/")[-1]

        print(f"📍 context raw: {raw_context}, cleaned_screen: {screen}")
        backend_json   = get_backend_ui(screen)
        parser_json    = get_parser(screen)
        compare_result = get_compare(screen)

        chart_indicators = None
        if screen == "chart":
            print("📈 Chart screen detected → MA 계산 시작")
            live_chart = get_live_chart_data()
            if live_chart:
                chart_indicators = compute_chart_indicators(live_chart)
                print("📊 MA 계산 완료")
            else:
                print("⚠️ live_chart is None (백엔드 응답 없음)")

        chart_block = ""
        if chart_indicators:
            chart_block = "[chart_indicators]\n" + orjson.dumps(chart_indicators).decode()


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

        2. **현재 스크롤 위치(scrollY)와 섹션(section)을 "Home" 화면과 "StockHome"화면에서 반드시 고려하라.**
           - 사용자가 상단(`section=bigdata`)이나 중간(`section=ranking`)에 있을 때,
             실제 기능이 화면 하단(`region=bottom`)에 있다면  
             "이 페이지에서 가능하지만 지금 화면에서는 바로 보이지 않아요. 스크롤을 조금 내려보세요 🐾"처럼 안내해야 한다.
           - 반대로 이미 하단(`section=ai_report`)에 있고 관련 기능이 상단에 있다면  
             "위쪽으로 스크롤해 보시면 있습니다" 라고 안내한다.
           - 다만 스크롤이 없는 화면에서는 이 규칙을 적용하지 않는다. 

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

        7. 사용자가 뉴스 화면(newsdetail)에서 어떤 형태로든 기사 내용에 대한 질문을 하면 (예: "이게 뭐야?", "무슨 말이야?", "요약해줘", "좀 설명해줘", "핵심만 알려줘", "이 기사 뭐임?", "뭔 소리야?") 화면 설명이 아니라 **기사 요약**을 제공해야 한다.

            요약 형식은 아래를 반드시 따른다:

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
        
        8. **사용자가 차트 화면에서 기능이 아닌 현재 시세나 관련된 분석을 요청하면 다음 같은 규칙을 따른다**
            차트 분석은 오직 서버가 전달한 chart_indicators(이동평균선, 최근 종가, 거래량 등) 데이터를 기반으로 한다.
            분석의 초점은 이동평균선 정배열/역배열, 단기/중기 추세, 최근 5개 봉의 양봉·음봉 비율, 거래량 증가/감소 같은 “흐름 해설”에 한정한다. (매매 추천이나 미래 가격 예측은 절대 금지)
            차트 분석 시 “현재가가 MA5 위에 있다” 같은 문구 대신 “단기 이동평균선 위에 현재가가 위치해 있어 단기 상승 추세임을 나타냅니다” 같은 해설형 문구를 사용한다.
            데이터가 없으면 임의로 생성하지 말고 “현재 데이터가 부족해 정확한 판단이 어려워요”라고 솔직하게 말한다.
            차트 데이터가 존재하는 경우 절대 "데이터가 부족하다"고 말하지 말고, 주어진 지표 범위 내에서 최대한 단순화하여 상승/하락 흐름을 판단한다.
            좋다 나쁘다 같은 주관적 판단을 피하고, 오직 객관적 데이터 해석에 집중한다.
            chart_indicators는 다음 정보를 포함한다:
            - ma5, ma20, ma60 (단기·중기·장기 이동평균)
            - 최근 봉의 고가/저가/종가/거래량
            - 단기 추세: ma5 > ma20이면 '단기 상승 흐름'
            - 중기 추세: ma20 > ma60이면 '중기 상승 흐름'
            - 장기 추세: ma60이 우상향하면 장기 우상향
            - 최근 종가가 MA 위에 있으면 → 강한 상승 흐름
            - 종가가 MA 아래면 → 약세 흐름
            - 최근 3~5개 봉이 양봉 위주면 → 단기 모멘텀 ↑
            - 거래량 증가 + 양봉 → 매수세 유입
            - 거래량 감소 + 음봉 → 매도세 약함
            예시 답변
            - “MA5가 MA20을 상향 돌파해서 단기적으로 상승 모멘텀이 있어요 🐾”
            - “거래량이 최근 평균보다 줄어서 관망세예요.”
            - “최근 저가가 조금씩 높아지는 ‘저점 상승’ 패턴이 보이네요.”
                        
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

        {chart_block}

        [사용자 질문]
        {req.text}
        """
        print("🧵 Prompt length:", len(user_input_full))

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
