#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
키우ME 파인튜닝 실행 스크립트
OpenAI API를 사용하여 gpt-4o-mini 모델을 파인튜닝합니다.

KIWUME: OpenAI 파인튜닝 자동화 스크립트
"""

import os
import sys
import time
import json
from pathlib import Path
from openai import OpenAI

# KIWUME: Windows 콘솔 한글 출력 설정
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


def load_config():
    """
    config.json 파일에서 설정을 로드
    """
    # 프로젝트 루트의 config.json 파일 로드
    project_root = Path(__file__).parent.parent
    config_path = project_root / "config.json"
    
    if not config_path.exists():
        raise ValueError(f"[ERROR] config.json 파일을 찾을 수 없습니다: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    api_key = config.get("openai_api_key")
    if not api_key:
        raise ValueError("[ERROR] openai_api_key를 config.json에서 찾을 수 없습니다.")
    
    return config


def upload_training_file(client: OpenAI, file_path: str):
    """
    학습용 JSONL 파일을 OpenAI에 업로드
    
    Args:
        client: OpenAI 클라이언트
        file_path: 업로드할 JSONL 파일 경로
        
    Returns:
        업로드된 파일 ID
    """
    print(f"[UPLOAD] 학습 파일 업로드 중: {file_path}")
    
    with open(file_path, "rb") as f:
        response = client.files.create(
            file=f,
            purpose="fine-tune"
        )
    
    file_id = response.id
    print(f"[OK] 파일 업로드 완료! File ID: {file_id}")
    
    return file_id


def create_finetune_job(client: OpenAI, file_id: str, model: str = "gpt-4o-mini-2024-07-18", suffix: str = "kiwume-v1"):
    """
    파인튜닝 작업 생성
    
    Args:
        client: OpenAI 클라이언트
        file_id: 업로드된 학습 파일 ID
        model: 베이스 모델 (기본값: gpt-4o-mini)
        suffix: 모델 이름 suffix
        
    Returns:
        파인튜닝 작업 ID
    """
    print(f"[CREATE] 파인튜닝 작업 생성 중...")
    print(f"   베이스 모델: {model}")
    print(f"   학습 파일 ID: {file_id}")
    print(f"   모델 Suffix: {suffix}")
    
    response = client.fine_tuning.jobs.create(
        training_file=file_id,
        model=model,
        suffix=suffix  # KIWUME: 모델 이름에 suffix 추가
    )
    
    job_id = response.id
    print(f"[OK] 파인튜닝 작업 생성 완료! Job ID: {job_id}")
    
    return job_id


def monitor_finetune_job(client: OpenAI, job_id: str):
    """
    파인튜닝 작업 상태를 모니터링
    
    Args:
        client: OpenAI 클라이언트
        job_id: 파인튜닝 작업 ID
        
    Returns:
        완료된 파인튜닝 모델 ID
    """
    print(f"\n[MONITOR] 파인튜닝 진행 상황 모니터링 중...")
    print("   (Ctrl+C로 중단 가능, 작업은 계속 진행됩니다)")
    print("-" * 80)
    
    try:
        while True:
            # 작업 상태 확인
            job = client.fine_tuning.jobs.retrieve(job_id)
            status = job.status
            
            # 상태 출력
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] 상태: {status}")
            
            # 완료 상태 확인
            if status == "succeeded":
                model_id = job.fine_tuned_model
                print("-" * 80)
                print(f"[SUCCESS] 파인튜닝 완료!")
                print(f"   모델 ID: {model_id}")
                return model_id
            
            elif status == "failed":
                print("-" * 80)
                print(f"[ERROR] 파인튜닝 실패!")
                print(f"   에러: {job.error}")
                return None
            
            elif status == "cancelled":
                print("-" * 80)
                print(f"[CANCELLED] 파인튜닝 작업이 취소되었습니다.")
                return None
            
            # 10초마다 체크
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n[INFO] 모니터링 중단됨. 작업은 백그라운드에서 계속 진행됩니다.")
        print(f"   작업 확인: https://platform.openai.com/finetune/{job_id}")
        return None


def save_model_info(model_id: str, job_id: str):
    """
    완료된 모델 정보를 파일로 저장
    
    Args:
        model_id: 파인튜닝된 모델 ID
        job_id: 파인튜닝 작업 ID
    """
    project_root = Path(__file__).parent.parent
    output_file = project_root / "data" / "kiwume_model_info.json"
    
    model_info = {
        "model_id": model_id,
        "job_id": job_id,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "base_model": "gpt-4o-mini-2024-07-18",
        "purpose": "키우ME 감정 분석 챗봇"
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(model_info, f, ensure_ascii=False, indent=2)
    
    print(f"\n[SAVED] 모델 정보 저장됨: {output_file}")


def main():
    """메인 실행 함수"""
    
    print("=" * 80)
    print("키우ME 파인튜닝 스크립트")
    print("=" * 80)
    
    # KIWUME: 프로젝트 경로 설정
    project_root = Path(__file__).parent.parent
    training_file = project_root / "data" / "kiwume_train.jsonl"
    
    # 1. 설정 로드
    try:
        config = load_config()
        api_key = config["openai_api_key"]
        base_model = config.get("base_model", "gpt-4o-mini-2024-07-18")
        model_suffix = config.get("model_suffix", "kiwume-v1")
        print(f"[OK] 설정 로드 완료")
        print(f"   API 키: {api_key[:20]}...{api_key[-10:]}")
        print(f"   베이스 모델: {base_model}")
    except Exception as e:
        print(f"[ERROR] {e}")
        return
    
    # 2. OpenAI 클라이언트 초기화
    client = OpenAI(api_key=api_key)
    print("[OK] OpenAI 클라이언트 초기화 완료")
    
    # 3. 학습 파일 존재 확인
    if not training_file.exists():
        print(f"[ERROR] 학습 파일을 찾을 수 없습니다: {training_file}")
        return
    
    # 4. 파일 업로드
    try:
        file_id = upload_training_file(client, str(training_file))
    except Exception as e:
        print(f"[ERROR] 파일 업로드 실패: {e}")
        return
    
    # 5. 파인튜닝 작업 생성
    try:
        job_id = create_finetune_job(client, file_id, base_model, model_suffix)
    except Exception as e:
        print(f"[ERROR] 파인튜닝 작업 생성 실패: {e}")
        return
    
    # 6. 작업 모니터링
    model_id = monitor_finetune_job(client, job_id)
    
    # 7. 완료 시 모델 정보 저장
    if model_id:
        save_model_info(model_id, job_id)
        print("\n" + "=" * 80)
        print("[COMPLETE] 모든 작업이 완료되었습니다!")
        print(f"[INFO] 모델 ID를 .env 파일에 추가하세요:")
        print(f"       KIWUME_MODEL_ID={model_id}")
        print("=" * 80)


if __name__ == "__main__":
    main()

