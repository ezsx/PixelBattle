from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


# This config is used to define environment variables for their further use in the project.

class Settings(BaseSettings):
    SECRET_KEY: str = "dfdfdfwrwqrqwrq434ads"  # secrets.token_urlsafe(32)
    SECURITY_PASSWORD_SALT: str = "dljkfsaqwueriovbak234"
    EMAIL_CONFIRMATION_TOKEN_EXPIRATION: int = 3600

    FIELD_SIZE: tuple[int, int] = (64, 64)

    FRONTEND_URL: str = "http://localhost:8000"

    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # * 24 * 8
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    DEBUG_MODE: bool = Field(False, validation_alias='DEBUG_MODE')
    SERVICE_NAME: str = Field('test_task', validation_alias='SERVICE_NAME')

    DB_TYPE: str = "postgresql"
    DB_CONNECTOR: str = ""  # if use sql alchemy we add smth like: +asyncpg
    DB_HOST: Optional[str] = Field("localhost", validation_alias='POSTGRES_HOST')
    DB_PORT: Optional[int] = Field("5432", validation_alias='POSTGRES_PORT')
    DB_USER: Optional[str] = Field("myuser", validation_alias='POSTGRES_USER')
    DB_PASSWORD: Optional[str] = Field("mypassword", validation_alias='POSTGRES_PASSWORD')
    DB_DB: Optional[str] = Field("postgres", validation_alias='POSTGRES_DB')

    DB_POOL_SIZE_MAX: int = Field(50, validation_alias='POOL_SIZE_MAX')
    DB_POOL_TIMEOUT: int = Field(300, validation_alias='POOL_TIMEOUT')
    BACKEND_DOMAIN: str = Field('localhost', validation_alias='BACKEND_DOMAIN')
    BACKEND_DOMAIN_PORT: int = Field(8000, validation_alias='BACKEND_DOMAIN_PORT')

    @property
    def DB_URL(self) -> str:
        return f"{self.DB_TYPE}{self.DB_CONNECTOR}://" \
               f"{self.DB_USER}:{self.DB_PASSWORD}@" \
               f"{self.DB_HOST}:{self.DB_PORT}/" \
               f"{self.DB_DB}"

    @property
    def DB_URL_without_password(self) -> str:
        return f"{self.DB_TYPE}{self.DB_CONNECTOR}://" \
               f"{self.DB_USER}:XXX@" \
               f"{self.DB_HOST}:{self.DB_PORT}/" \
               f"{self.DB_DB}"


config = Settings()

print(config.DB_URL_without_password)
# print(config.SECRET_KEY)
