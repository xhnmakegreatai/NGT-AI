"""FastAPI 应用配置"""

from typing import List

try:
    from pydantic_settings import BaseSettings
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "缺少依赖 pydantic-settings，请先运行 `pip install pydantic-settings`。"
    ) from exc


class Settings(BaseSettings):
    """后端通用配置"""

    app_name: str = "NGT-AI Decision System"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = ["*"]
    use_real_apis: bool = False

    database_url: str = "sqlite:///./ngtai.db"
    database_echo: bool = False

    redis_url: str | None = None

    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expires_minutes: int = 60 * 24

    class Config:
        env_file = ".env"


settings = Settings()

# 未显式配置 JWT 密钥时,生成临时密钥(仅本地开发用,重启失效);生产请用环境变量 JWT_SECRET_KEY。
if not settings.jwt_secret_key:
    import logging
    import secrets

    settings.jwt_secret_key = secrets.token_urlsafe(32)
    logging.getLogger(__name__).warning(
        "未设置 JWT_SECRET_KEY,已生成临时密钥(仅供本地开发,重启后失效)。生产环境请通过环境变量配置。"
    )
