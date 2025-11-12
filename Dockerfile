# 베이스 이미지: Python 3.11 이상
FROM python:3.11-slim

# 컨테이너 내부 작업 디렉토리 설정
WORKDIR /app

# 필요한 파일 복사
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 나머지 코드 복사
COPY . .

# FastAPI 서버 실행 (포트 5002로 설정)
EXPOSE 5002
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5002"]
