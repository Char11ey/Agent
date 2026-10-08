from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """读取环境变量；.env 里的值会被 os.environ 覆盖。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls()
