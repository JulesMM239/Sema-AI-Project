FROM python:3.11-slim
# Désactive toute config pip "require-hashes"
ENV PIP_REQUIRE_HASHES=0

# Nettoie configs pip (si elles existent)
RUN rm -f /etc/pip.conf /root/.config/pip/pip.conf /root/.pip/pip.conf || true

# (optionnel) upgrade pip
RUN python -m pip install --upgrade pip setuptools wheel

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

ENV PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=15

RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir --timeout 300 --retries 15 -r /app/requirements.txt

COPY . /app

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["python", "run.py"]
