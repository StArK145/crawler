FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y wget gnupg libasound2 libgbm1 libgtk-3-0 libnss3 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt uvicorn
RUN pip install playwright
RUN playwright install chromium --with-deps
COPY . .
CMD sh -c "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-10000}"
