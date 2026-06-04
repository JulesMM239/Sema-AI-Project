FROM python:3.11-slim

ARG WITH_LORA=0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# system deps (psycopg binary is used, so minimal deps)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Optional: LoRA fine-tuning deps (heavy)
COPY requirements-lora.txt /app/requirements-lora.txt
RUN if [ "$WITH_LORA" = "1" ]; then pip install --no-cache-dir -r /app/requirements-lora.txt; fi

COPY . /app

EXPOSE 8010
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010"]
