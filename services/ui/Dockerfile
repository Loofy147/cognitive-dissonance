FROM python:3.9-slim

WORKDIR /app

# Copy the common package to allow importing config
COPY services/common /app/services/common
COPY services/__init__.py /app/services/__init__.py

COPY services/ui/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/ui/app.py .

EXPOSE 7860

CMD ["python", "app.py"]
