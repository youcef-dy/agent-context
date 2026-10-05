FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml README.md ./
COPY context_runtime ./context_runtime
RUN pip install --no-cache-dir ".[postgres,server]"

EXPOSE 8765
CMD ["python", "-m", "context_runtime.serve"]
