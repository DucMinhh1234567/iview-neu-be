import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()


def get_env(key: str, default: Optional[str] = None) -> str:
    value = os.getenv(key, default)
    if value is None:
        raise ValueError(f"Required environment variable {key} is not set")
    return value


def get_env_int(key: str, default: int) -> int:
    value = os.getenv(key)
    return int(value) if value else default


def get_env_float(key: str, default: float) -> float:
    value = os.getenv(key)
    return float(value) if value else default


def get_env_bool(key: str, default: bool) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.lower() in ('true', '1', 'yes', 'on')


# Supabase
SUPABASE_URL = get_env("SUPABASE_URL")
SUPABASE_KEY = get_env("SUPABASE_KEY")
SUPABASE_ANON_KEY = get_env("SUPABASE_ANON_KEY", "")

# File Storage
USE_SUPABASE_STORAGE = get_env_bool("USE_SUPABASE_STORAGE", False)
UPLOAD_FOLDER = get_env("UPLOAD_FOLDER", "./uploads")
MAX_UPLOAD_SIZE_MB = get_env_int("MAX_UPLOAD_SIZE_MB", 50)
MAX_UPLOAD_SIZE = MAX_UPLOAD_SIZE_MB * 1024 * 1024  # Convert to bytes

# Supabase Storage buckets
SUPABASE_STORAGE_BUCKETS = {
    "materials": "materials",  # Public bucket
    "cv": "private",           # Private bucket (for CV uploads)
    "jd": "private"            # Private bucket (for JD uploads)
}

# Gemini
GEMINI_API_KEY = get_env("GEMINI_API_KEY", "")
GEMINI_MODEL = get_env("GEMINI_MODEL", "gemini-2.5-flash")
EMBEDDING_MODEL = get_env("EMBEDDING_MODEL", "models/text-embedding-004")

# Vector Search
MAX_CHUNKS_PER_QUESTION = get_env_int("MAX_CHUNKS_PER_QUESTION", 3)
BATCH_SIZE = get_env_int("BATCH_SIZE", 8)

# Application
DEBUG = get_env_bool("DEBUG", False)
SECRET_KEY = get_env("SECRET_KEY", "change-me-in-production")
# Default CORS origins
default_cors = "http://localhost:3000,http://localhost:3001,http://localhost:8000,http://localhost:8080"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", default_cors).split(",")
CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS if origin.strip()]


def validate_config() -> None:
    required_vars = [
        ("SUPABASE_URL", SUPABASE_URL),
        ("SUPABASE_KEY", SUPABASE_KEY),
        ("GEMINI_API_KEY", GEMINI_API_KEY),
    ]
    
    missing = []
    for name, value in required_vars:
        if not value:
            missing.append(name)
    
    if missing:
        raise ValueError(
            f"Missing required configuration variables: {', '.join(missing)}"
        )


# Validate on import
try:
    validate_config()
except ValueError as e:
    print(f"Configuration warning: {e}")

