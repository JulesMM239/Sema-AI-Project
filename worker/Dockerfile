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
    git build-essential cmake libglib2.0-0 libsm6 libxext6 libxrender-dev \     
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir redis rq
RUN pip install --no-cache-dir llama-cpp-python==0.3.7
ENV PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=15

RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir --timeout 300 --retries 15 -r requirements.txt
COPY . ./
CMD ["python", "worker.py"]
