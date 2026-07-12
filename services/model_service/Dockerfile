FROM python:3.11-slim

ARG WITH_LORA=0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=600 \
    PIP_RETRIES=20 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# system deps for llama-cpp-python and Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    cmake \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel \
  && pip install --no-cache-dir --prefer-binary --timeout 600 --retries 20 -r /app/requirements.txt

# Optional: LoRA fine-tuning deps (heavy)
COPY requirements-lora.txt /app/requirements-lora.txt
RUN if [ "$WITH_LORA" = "1" ]; then pip install --no-cache-dir --prefer-binary --timeout 600 --retries 20 -r /app/requirements-lora.txt; fi

COPY . /app

EXPOSE 8010
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010"]
