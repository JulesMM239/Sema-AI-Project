from pydantic_settings import BaseSettings
from pathlib import Path



class Settings(BaseSettings):
    """
    Global application settings.
    Loaded from environment variables and .env file.
    """

    # --- Security ---
    jwt_secret: str = "CHANGE_ME_SUPER_SECRET"

    # --- ASR (faster-whisper) ---
    asr_model: str = "small"
    asr_device: str = "cpu"          # cpu | cuda
    asr_compute_type: str = "int8"   # int8 | float16

    # --- LLM (llama.cpp / GGUF) ---
    # MUST point to an existing .gguf file
    llm_gguf: str = ""               # mapped from LLM_GGUF
    llm_ctx: int = 4096
    llm_threads: int = 4
    llm_gpu_layers: int = 0

    # --- TTS (Piper) ---
    piper_onnx: str = ""             # mapped from PIPER_ONNX
    piper_json: str = ""             # mapped from PIPER_JSON
    piper_bin: str = "./piper/piper" # optional, default path

    # --- Database ---
    app_db_url: str = "sqlite:///./app.db"

    # --- API / Network ---
    public_base_url: str = "http://localhost:8000"

    # --- Training / Workers ---
    redis_url: str = ""
    trained_root: str = "./models/trained"
    train_output_dir: str = "./models/trained"

    # --- Translation behaviour ---
    translate_use_llm: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
