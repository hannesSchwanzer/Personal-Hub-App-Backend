import os
from typing import Tuple

def get_user_token_copilot() -> str:
    """
    Retrieve the Copilot GitHub token from the environment variable.
    Raises a RuntimeError if not found.
    """
    token = os.environ.get("COPILOT_GITHUB_TOKEN")
    if not token:
        raise RuntimeError("COPILOT_GITHUB_TOKEN not set in environment.")
    return token

def get_user_token_openrouter() -> str:
    """
    Retrieve the OpenRouter API key from the environment variable.
    Raises a RuntimeError if not found.
    """
    token = os.environ.get("OPENROUTER_API_KEY")
    if not token:
        raise RuntimeError("OPENROUTER_API_KEY not set in environment.")
    return token

def get_oauth_fatsecret() -> Tuple[str, str]:
    client_id = os.environ.get("FATSECRET_CLIENT_ID")
    client_secret = os.environ.get("FATSECRET_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("FATSECRET_CLIENT_ID and FATSECRET_CLIENT_SECRET must be set in environment.")
    return client_id, client_secret

def get_database_url_async() -> str:
    """
    Build and return the PostgreSQL connection URL from environment variables.
    Uses POSTGRES_* variables only. Raises RuntimeError if required variables are missing.
    """
    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")
    host = os.environ.get("POSTGRES_HOST")
    port = os.environ.get("POSTGRES_PORT")
    dbname = os.environ.get("POSTGRES_DB")

    if not user or not password or not dbname or not host or not port:
        raise RuntimeError("PostgreSQL connection details (POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_HOST, POSTGRES_PORT) must be set in environment.")

    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{dbname}"


def get_database_url_sync() -> str:
    """
    Build and return the PostgreSQL connection URL from environment variables.
    Uses POSTGRES_* variables only. Raises RuntimeError if required variables are missing.
    """
    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")
    host = os.environ.get("POSTGRES_HOST")
    port = os.environ.get("POSTGRES_PORT")
    dbname = os.environ.get("POSTGRES_DB")

    if not user or not password or not dbname or not host or not port:
        raise RuntimeError("PostgreSQL connection details (POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_HOST, POSTGRES_PORT) must be set in environment.")

    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
