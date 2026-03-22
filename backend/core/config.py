import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    AI_PROVIDER: str = "openrouter"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPEN_ROUTER_API: str = ""
    GROK_API_KEY: str = ""
    GROK_MODEL: str = "llama-3.3-70b-versatile"
    GROK_BASE_URL: str = "https://api.groq.com/openai/v1"
    DATABASE_URL: str = "sqlite:///./rag_database_v3.db"
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    CONTACT_TO_EMAIL: str = ""
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
