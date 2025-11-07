#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
키우ME 파인튜닝 데이터셋 생성 스크립트
CSV 파일을 OpenAI 파인튜닝용 JSONL 형식으로 변환합니다.

KIWUME: CSV → JSONL 변환 스크립트
"""

import csv
import json
import os
import sys
from pathlib import Path

# KIWUME: Windows 콘솔 한글 출력 설정
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


def csv_to_jsonl(input_csv: str, output_jsonl: str):
    """
    CSV 파일을 OpenAI 파인튜닝용 JSONL 형식으로 변환
    
    Args:
        input_csv: 입력 CSV 파일 경로 (user, reply 컬럼 포함)
        output_jsonl: 출력 JSONL 파일 경로
    """
    
    # KIWUME: 시스템 프롬프트 정의 (금융 지식 중심)
    system_prompt = (
        "너는 키움증권 사용자에게 투자 관련 금융 지식과 실용적인 조언을 제공하는 전문 강아지이다. "
        "사용자의 질문이나 상황을 분석하여, 구체적인 투자 전략, 리스크 관리 방법, "
        "키움증권 시스템 사용법 등을 명확하고 이해하기 쉽게 설명한다."
    )
    
    # 변환된 데이터를 저장할 리스트
    jsonl_data = []
    
    # CSV 파일 읽기 (UTF-8 인코딩)
    with open(input_csv, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for row in reader:
            user_message = row['user']
            reply_text = row['reply']
            
            # KIWUME: OpenAI messages 형식으로 변환
            # assistant의 content는 답변 텍스트만 포함 (emotion 제거)
            message_obj = {
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_message
                    },
                    {
                        "role": "assistant",
                        "content": reply_text
                    }
                ]
            }
            
            jsonl_data.append(message_obj)
    
    # JSONL 파일로 저장 (한 줄에 하나의 JSON 객체)
    with open(output_jsonl, 'w', encoding='utf-8') as jsonlfile:
        for item in jsonl_data:
            # ensure_ascii=False로 한글 유지
            json_line = json.dumps(item, ensure_ascii=False)
            jsonlfile.write(json_line + '\n')
    
    print(f"[OK] 변환 완료!")
    print(f"   입력: {input_csv}")
    print(f"   출력: {output_jsonl}")
    print(f"   총 {len(jsonl_data)}개의 샘플이 변환되었습니다.")


def main():
    """메인 실행 함수"""
    
    # KIWUME: 프로젝트 루트 기준 경로 설정
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    input_csv = project_root / "data" / "kiwume_raw.csv"
    output_jsonl = project_root / "data" / "kiwume_train.jsonl"
    
    # 입력 파일 존재 확인
    if not input_csv.exists():
        print(f"[ERROR] 입력 파일을 찾을 수 없습니다 - {input_csv}")
        return
    
    # 출력 디렉토리 생성 (없으면)
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    
    # 변환 실행
    csv_to_jsonl(str(input_csv), str(output_jsonl))
    
    # KIWUME: 변환 결과 샘플 출력
    print("\n[SAMPLE] 생성된 JSONL 샘플 (처음 2줄):")
    print("-" * 80)
    with open(output_jsonl, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i < 2:  # 처음 2줄만 출력
                print(json.dumps(json.loads(line), ensure_ascii=False, indent=2))
                print("-" * 80)
            else:
                break


if __name__ == "__main__":
    main()

