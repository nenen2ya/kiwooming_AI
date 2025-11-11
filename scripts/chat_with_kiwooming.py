#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
키우밍 대화 챗봇
파인튜닝된 키우밍 모델과 실시간으로 대화합니다.

KIWUME: 키우밍 인터랙티브 챗봇
"""

import json
import sys
from pathlib import Path
from openai import OpenAI

# KIWUME: Windows 콘솔 한글 출력 설정
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


def load_config():
    """config.json 파일에서 설정을 로드"""
    project_root = Path(__file__).parent.parent
    config_path = project_root / "config.json"
    
    if not config_path.exists():
        raise ValueError(f"[ERROR] config.json 파일을 찾을 수 없습니다: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    return config


def chat_with_kiwooming(client: OpenAI, model_id: str, system_prompt: str):
    """
    키우밍과 대화하기
    
    Args:
        client: OpenAI 클라이언트
        model_id: 파인튜닝된 모델 ID
        system_prompt: 키우밍 페르소나 프롬프트
    """
    # 대화 히스토리 초기화
    conversation_history = [
        {"role": "system", "content": system_prompt}
    ]
    
    print("\n" + "=" * 80)
    print("🌱 키우밍과 대화를 시작합니다!")
    print("=" * 80)
    print("\n[안내]")
    print("  • 궁금한 투자 질문을 자유롭게 해보세요")
    print("  • 'quit', 'exit', '종료'를 입력하면 대화가 종료됩니다")
    print("  • 'clear', '초기화'를 입력하면 대화 기록이 초기화됩니다")
    print("-" * 80)
    
    # 키우밍 인사말
    greeting = "안녕하세요! 저는 키우밍이에요 🌱 함께 투자 실력을 키워볼까요? 궁금한 게 있으시면 편하게 물어보세요!"
    print(f"\n🌱 키우밍: {greeting}\n")
    
    # 대화 루프
    message_count = 0
    
    while True:
        try:
            # 사용자 입력
            user_input = input("💬 나: ").strip()
            
            # 종료 명령어 체크
            if user_input.lower() in ['quit', 'exit', '종료', 'q']:
                print("\n🌱 키우밍: 오늘도 좋은 투자 되세요! 다음에 또 만나요 👋")
                print("=" * 80)
                break
            
            # 초기화 명령어 체크
            if user_input.lower() in ['clear', '초기화', 'reset']:
                conversation_history = [
                    {"role": "system", "content": system_prompt}
                ]
                message_count = 0
                print("\n[INFO] 대화 기록이 초기화되었습니다.\n")
                continue
            
            # 빈 입력 체크
            if not user_input:
                continue
            
            # 사용자 메시지 추가
            conversation_history.append({
                "role": "user",
                "content": user_input
            })
            
            # API 호출
            print("\n🌱 키우밍: ", end="", flush=True)
            
            response = client.chat.completions.create(
                model=model_id,
                messages=conversation_history,
                temperature=0.7,
                max_tokens=300
            )
            
            # 키우밍 답변 추출
            assistant_reply = response.choices[0].message.content
            
            # 답변 출력
            print(f"{assistant_reply}\n")
            
            # 대화 히스토리에 추가
            conversation_history.append({
                "role": "assistant",
                "content": assistant_reply
            })
            
            message_count += 1
            
            # 대화가 너무 길어지면 경고
            if message_count > 10:
                print("[TIP] 대화가 길어지면 토큰 비용이 증가해요. 'clear'로 초기화할 수 있어요.\n")
        
        except KeyboardInterrupt:
            print("\n\n🌱 키우밍: 대화를 종료할게요. 좋은 하루 보내세요! 👋")
            print("=" * 80)
            break
        
        except Exception as e:
            print(f"\n[ERROR] 오류가 발생했습니다: {e}")
            print("다시 시도해보세요.\n")

def get_ai_response(user_input: str, context: str | None = None) -> str:
    """
    FastAPI용 — 서버에서 호출 가능한 버전
    """
    try:
        config = load_config()
        client = OpenAI(api_key=config["openai_api_key"])
        model_id = config.get("kiwume_model_id")
        system_prompt = config.get("kiwooming_system_prompt", "당신은 키움증권 투자 도우미 키우밍입니다.")

        conversation_history = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]

        response = client.chat.completions.create(
            model=model_id,
            messages=conversation_history,
            temperature=0.7,
            max_tokens=400
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"⚠️ 오류 발생: {str(e)}"


def main():
    """메인 실행 함수"""
    
    print("=" * 80)
    print("🌱 키우밍 대화 챗봇 시작")
    print("=" * 80)
    
    # 1. 설정 로드
    try:
        config = load_config()
        api_key = config["openai_api_key"]
        model_id = config.get("kiwume_model_id")
        kiwooming_prompt = config.get("kiwooming_system_prompt")
        
        if not model_id:
            print("[ERROR] config.json에 kiwume_model_id가 없습니다.")
            return
        
        if not kiwooming_prompt:
            print("[ERROR] config.json에 kiwooming_system_prompt가 없습니다.")
            return
        
        print("\n[OK] 설정 로드 완료")
        print(f"     모델: {model_id}")
    except Exception as e:
        print(f"[ERROR] {e}")
        return
    
    # 2. OpenAI 클라이언트 초기화
    try:
        client = OpenAI(api_key=api_key)
        print("[OK] OpenAI 클라이언트 초기화 완료")
    except Exception as e:
        print(f"[ERROR] OpenAI 클라이언트 초기화 실패: {e}")
        return
    
    # 3. 대화 시작
    chat_with_kiwooming(client, model_id, kiwooming_prompt)


if __name__ == "__main__":
    main()

