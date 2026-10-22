FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY platformcare platformcare
COPY runbooks runbooks
COPY dashboard.py .
CMD ["uvicorn", "platformcare.api:app", "--host", "0.0.0.0", "--port", "8000"]
