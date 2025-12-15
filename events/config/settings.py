from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_url: str = "postgresql+asyncpg://user:pass@localhost/command_tower"
    redis_url: str = "redis://localhost:6379/0"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    worker_callback_url: str = "http://worker-svc:8000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()