# test_compare.py
import requests
import json

# 🔹 로컬 환경 엔드포인트
PARSER_URL = "http://localhost:4001/parse/Home"
BACKEND_URL = "http://localhost:8001/ui/Home"
AI_COMPARE_URL = "http://localhost:6002/compare"

def test_compare():
    payload = {
        "parser_url": PARSER_URL,
        "backend_url": BACKEND_URL
    }

    try:
        res = requests.post("http://localhost:6002/compare", json=payload, timeout=20)
        res.raise_for_status()
        data = res.json()
        print("✅ 비교 결과:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except requests.exceptions.RequestException as e:
        print("⚠️ 요청 실패:", e)
    except json.JSONDecodeError:
        print("⚠️ JSON 파싱 실패:", res.text)

if __name__ == "__main__":
    test_compare()