"""
config.py — Application settings.

Uses pydantic-settings to load configuration from environment variables
with sensible defaults for development.

In production, set DATABASE_URL to point to MySQL:
    DATABASE_URL=mysql+aiomysql://root:matchingengine@localhost:3306/matching_engine
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application configuration.

    All settings can be overridden via environment variables:
        DATABASE_URL=mysql+aiomysql://...
        DEFAULT_SYMBOLS=AAPL,GOOGL,MSFT
        ENABLE_WEBSOCKET=true
    """
    # Database
    database_url: str = "sqlite+aiosqlite:///./matching_engine.db"

    # Symbols — comma-separated list
    default_symbols: str = "AAPL,GOOGL,MSFT,AMZN,TSLA"

    # Order book
    max_book_depth: int = 50

    # WebSocket
    enable_websocket: bool = True

    # API
    api_title: str = "Order Matching Engine"
    api_version: str = "1.0.0"

    @property
    def symbol_list(self) -> list[str]:
        """Parse comma-separated symbols into a list."""
        return [s.strip() for s in self.default_symbols.split(",") if s.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# Singleton settings instance
settings = Settings()
