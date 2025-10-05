FROM python:3.11-slim

WORKDIR /app

# تجنب تثبيت مكتبات نظامية على المضيف؛ نفّذ ما يلزم هنا
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY services /app/services

ENV PYTHONPATH /app

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "services.critic.main:app", "--host", "0.0.0.0", "--port", "8000"]