"""
Configuration management for gabo platform
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import yaml


@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    host: str = "localhost"
    port: int = 5432
    database: str = "gabo"
    username: str = "gabo_user"
    password: str = ""
    vector_table: str = "embeddings"
    metadata_table: str = "metadata"


@dataclass
class EmbeddingConfig:
    """Embedding model configuration"""
    provider: str = "openai"  # openai, cohere, voyage
    model: str = "text-embedding-ada-002"  # Default to OpenAI, can be overridden
    api_key: str = ""
    batch_size: int = 100
    max_retries: int = 3


@dataclass
class LLMConfig:
    """Large Language Model configuration"""
    provider: str = "openai"  # openai, anthropic, local
    model: str = "gpt-4"
    api_key: str = ""
    temperature: float = 0.1
    max_tokens: int = 2000


@dataclass
class StorageConfig:
    """Storage and file handling configuration"""
    data_dir: str = "./data"
    temp_dir: str = "./temp"
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    supported_formats: list = None
    
    def __post_init__(self):
        if self.supported_formats is None:
            self.supported_formats = ['.pdf', '.txt', '.eml', '.msg', '.docx']


@dataclass
class TaskConfig:
    """Async task configuration"""
    broker_url: str = "redis://localhost:6379/0"
    result_backend: str = "redis://localhost:6379/0"
    task_serializer: str = "json"
    result_serializer: str = "json"
    accept_content: list = None
    
    def __post_init__(self):
        if self.accept_content is None:
            self.accept_content = ["json"]


@dataclass
class APIConfig:
    """API configuration"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: list = None
    
    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["http://localhost:3000"]


@dataclass
class Config:
    """Main configuration class"""
    database: DatabaseConfig
    embedding: EmbeddingConfig
    llm: LLMConfig
    storage: StorageConfig
    task: TaskConfig
    api: APIConfig
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Create configuration from environment variables"""
        return cls(
            database=DatabaseConfig(
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", "5432")),
                database=os.getenv("DB_NAME", "gabo"),
                username=os.getenv("DB_USER", "gabo_user"),
                password=os.getenv("DB_PASSWORD", ""),
                vector_table=os.getenv("DB_VECTOR_TABLE", "embeddings"),
                metadata_table=os.getenv("DB_METADATA_TABLE", "metadata")
            ),
            embedding=EmbeddingConfig(
                provider=os.getenv("EMBEDDING_PROVIDER", "openai"),
                model=os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002"),
                api_key=os.getenv("EMBEDDING_API_KEY", ""),
                batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", "100")),
                max_retries=int(os.getenv("EMBEDDING_MAX_RETRIES", "3"))
            ),
            llm=LLMConfig(
                provider=os.getenv("LLM_PROVIDER", "openai"),
                model=os.getenv("LLM_MODEL", "gpt-4"),
                api_key=os.getenv("LLM_API_KEY", ""),
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
                max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2000"))
            ),
            storage=StorageConfig(
                data_dir=os.getenv("STORAGE_DATA_DIR", "./data"),
                temp_dir=os.getenv("STORAGE_TEMP_DIR", "./temp"),
                max_file_size=int(os.getenv("STORAGE_MAX_FILE_SIZE", str(100 * 1024 * 1024)))
            ),
            task=TaskConfig(
                broker_url=os.getenv("TASK_BROKER_URL", "redis://localhost:6379/0"),
                result_backend=os.getenv("TASK_RESULT_BACKEND", "redis://localhost:6379/0")
            ),
            api=APIConfig(
                host=os.getenv("API_HOST", "0.0.0.0"),
                port=int(os.getenv("API_PORT", "8000")),
                debug=os.getenv("API_DEBUG", "false").lower() == "true"
            )
        )
    
    @classmethod
    def from_file(cls, config_path: str) -> 'Config':
        """Create configuration from YAML file"""
        config_path = Path(config_path)
        if not config_path.exists():
            # Fall back to environment variables
            return cls.from_env()
        
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        return cls(
            database=DatabaseConfig(**config_data.get("database", {})),
            embedding=EmbeddingConfig(**config_data.get("embedding", {})),
            llm=LLMConfig(**config_data.get("llm", {})),
            storage=StorageConfig(**config_data.get("storage", {})),
            task=TaskConfig(**config_data.get("task", {})),
            api=APIConfig(**config_data.get("api", {}))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "database": self.database.__dict__,
            "embedding": self.embedding.__dict__,
            "llm": self.llm.__dict__,
            "storage": self.storage.__dict__,
            "task": self.task.__dict__,
            "api": self.api.__dict__
        }
    
    def validate(self) -> bool:
        """Validate configuration"""
        # Check required API keys
        if not self.embedding.api_key:
            raise ValueError("Embedding API key is required")
        
        if not self.llm.api_key:
            raise ValueError("LLM API key is required")
        
        # Check database connection
        if not self.database.password:
            raise ValueError("Database password is required")
        
        # Create directories if they don't exist
        Path(self.storage.data_dir).mkdir(parents=True, exist_ok=True)
        Path(self.storage.temp_dir).mkdir(parents=True, exist_ok=True)
        
        return True


# Default configuration
DEFAULT_CONFIG = Config.from_env() 