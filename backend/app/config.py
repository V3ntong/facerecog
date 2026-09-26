import os
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    DB_SERVER: str = "localhost"
    DB_NAME: str = "FaceRecognitionDB"
    DB_DRIVER: str = "{ODBC Driver 18 for SQL Server}"
    DB_TRUST_SERVER_CERTIFICATE: str = "yes"
    DB_AUTH: str = "trusted"
    DB_USER: str = ""
    DB_PASSWORD: str = ""

    RECOGNITION_THRESHOLD: float = 0.45
    FACE_MIN_SIZE: int = 40

    AI_PROVIDER: str = "gemini"
    AI_MODEL: str = "gemini-3.5-flash-lite"
    AI_FALLBACK_MODEL: str = "gemini-flash-latest"
    AI_MAX_RETRIES: int = 1
    AI_TIMEOUT_SECONDS: float = 25.0
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    VIDEO_DESCRIBE_FRAMES: int = 4
    VIDEO_FRAME_MAX_DIM: int = 512

    DATASET_DIR: str = r"C:\FaceDataset"

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    MAX_UPLOAD_SIZE_MB: int = 100
    RATE_LIMIT_PER_MINUTE: int = 60

    model_config = {
        # .env lives at the repo root, not in the backend dir where uvicorn runs.
        "env_file": str(Path(__file__).resolve().parents[2] / ".env"),
        "env_file_encoding": "utf-8",
    }

    @property
    def connection_string(self) -> str:
        base = (
            f"DRIVER={self.DB_DRIVER};"
            f"SERVER={self.DB_SERVER};"
            f"DATABASE={self.DB_NAME};"
            f"TrustServerCertificate={self.DB_TRUST_SERVER_CERTIFICATE};"
        )
        if self.DB_AUTH.lower() == "trusted":
            return base + "Trusted_Connection=yes;"
        return base + f"UID={self.DB_USER};PWD={self.DB_PASSWORD};"

    @property
    def sqlalchemy_url(self) -> str:
        if self.DB_AUTH.lower() == "trusted":
            return (
                f"mssql+pyodbc://{self.DB_SERVER}/{self.DB_NAME}"
                f"?driver=ODBC+Driver+18+for+SQL+Server"
                f"&TrustServerCertificate=yes"
                f"&trusted_connection=yes"
            )
        return (
            f"mssql+pyodbc://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_SERVER}/{self.DB_NAME}"
            f"?driver=ODBC+Driver+18+for+SQL+Server"
            f"&TrustServerCertificate=yes"
        )


settings = Settings()
