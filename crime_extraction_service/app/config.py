"""
Configuration management using Pydantic Settings
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017/"
    mongodb_database: str = "crime2"
    mongodb_collection: str = "articles2"
    
    # Azure Cosmos DB
    cosmos_endpoint: str
    cosmos_key: str
    cosmos_database: str = "crime_db"
    cosmos_container: str = "structured_crimes"
    
    # Cerebras API
    cerebras_api_key: str
    cerebras_api_url: str = "https://api.cerebras.ai/v1/chat/completions"
    
    # Ollama (fallback)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    
    # Service
    service_name: str = "crime_extraction_service"
    log_level: str = "INFO"
    batch_size: int = 10
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
