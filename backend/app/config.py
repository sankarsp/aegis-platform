"""Runtime settings, read from environment variables (prefix AEGIS_)."""

from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AEGIS_", env_file=".env", extra="ignore")

    # Either a full URL, or the parts below (ECS injects the Aurora password from Secrets Manager).
    database_url: str = "sqlite:///./aegis.db"
    db_host: str | None = None
    db_port: int = 5432
    db_name: str = "aegis"
    db_user: str | None = None
    db_password: str | None = None
    # Secrets Manager ARN of the RDS-managed secret. Read at connect time, so password rotation needs no restart.
    db_secret_arn: str | None = None

    # "bedrock" uses Amazon Bedrock Titan Text Embeddings v2; "hash" is an offline embedder for dev and tests.
    embedding_provider: str = "hash"
    embedding_dim: int = 1024
    aws_region: str = "us-east-1"
    bedrock_embedding_model_id: str = "amazon.titan-embed-text-v2:0"
    # Optional: a Bedrock chat model or inference profile ID to draft answers for /api/ask.
    bedrock_chat_model_id: str | None = None

    cors_origins: list[str] = ["http://localhost:5173"]
    seed_demo_data: bool = True

    # Sign-in. With no user pool configured the API runs in dev mode and trusts X-User / dev_user.
    cognito_user_pool_id: str | None = None
    cognito_client_id: str | None = None
    dev_user: str = "Priya Nair"
    dev_user_email: str = "priya.nair@northwindpay.example"
    # Demo data assigns the seeded review inbox to this person. Set it to your own email in AWS.
    demo_reviewer_email: str = "priya.nair@northwindpay.example"

    @model_validator(mode="after")
    def _compose_database_url(self) -> "Settings":
        if self.db_host and self.db_secret_arn:
            # Credentials are filled in per connection by db.py from the secret.
            self.database_url = f"postgresql+psycopg://@{self.db_host}:{self.db_port}/{self.db_name}?sslmode=require"
        elif self.db_host and self.db_user and self.db_password:
            self.database_url = (
                f"postgresql+psycopg://{quote_plus(self.db_user)}:{quote_plus(self.db_password)}"
                f"@{self.db_host}:{self.db_port}/{self.db_name}?sslmode=require"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
