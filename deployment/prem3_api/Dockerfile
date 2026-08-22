FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    PREM3_API_RUNTIME=cloud

WORKDIR /app

COPY deployment/prem3_api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY app /app/app

# FastAPI/Uvicorn only. Do not start ADK, Meridian, or the frontend.
# Cloud Run injects PORT. Bind all interfaces. Never enable reload.
CMD ["sh", "-c", "exec uvicorn app.service.app:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers"]
