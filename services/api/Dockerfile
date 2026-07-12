FROM python:3.11-slim

ENV PIP_REQUIRE_HASHES=0 \
    PIP_DEFAULT_TIMEOUT=600 \
    PIP_RETRIES=20 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN rm -f /etc/pip.conf /root/.config/pip/pip.conf /root/.pip/pip.conf || true

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir --prefer-binary --timeout 600 --retries 20 -r /app/requirements.txt

COPY . /app

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["python", "run.py"]
