FROM python:3.12-slim

# WeasyPrint 시스템 의존성 + 한글 폰트(Noto CJK)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render는 $PORT 환경변수로 포트를 지정함
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
