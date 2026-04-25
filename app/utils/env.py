import os

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
