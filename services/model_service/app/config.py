from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    database_url: str = "postgresql+psycopg://sema:sema@db:5432/sema_model"
    redis_url: str = "redis://redis:6379/0"
    data_dir: str = "/data"
    service_port: int = 8010

    # Online GGUF model hosted on Hugging Face.
    # Example:
    #   HF_MODEL_REPO=Qwen/Qwen2.5-0.5B-Instruct-GGUF
    #   HF_MODEL_FILE=Qwen2.5-0.5B-Instruct-Q4_K_M.gguf
    hf_model_id: str = "qwen2.5-0.5b-instruct-q4_k_m"
    hf_model_repo: str = ""
    hf_model_file: str = ""
    hf_token: str = ""
    hf_cache_dir: str = "/models/model_service_data/hf_cache"

    llm_ctx: int = 4096
    llm_threads: int = 4
    llm_gpu_layers: int = 0
    llm_temperature: float = 0.2
    llm_max_tokens: int = 256

settings = Settings()
