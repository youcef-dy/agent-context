FROM python:3.11-slim-bookworm@sha256:2333bd330d12de02514770b3585cad313644316047cdee24a7acfdece6de6efb

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements-server.txt ./
RUN pip install --no-cache-dir --only-binary=:all: --require-hashes \
    -r requirements-server.txt
COPY context_runtime ./context_runtime

RUN useradd --system --uid 10001 --no-create-home context
USER 10001

EXPOSE 8765
CMD ["python", "-m", "context_runtime.serve"]
