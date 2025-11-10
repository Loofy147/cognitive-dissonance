FROM python:3.9-slim

WORKDIR /app

COPY services/ui/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY services/ui/app.py .

EXPOSE 7860

CMD ["python", "app.py"]
