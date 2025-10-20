"""
Model Provider Registry

Defines how to interact with each AI provider.
Model IDs are auto-discovered and updated by the scheduler.
"""

import os

# Load the latest discovered models (updated by scheduler)
def load_model_config():
    """Load model IDs discovered by the scheduler"""
    import json
    config_file = "model_config.json"

    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    else:
        # Fallback defaults if scheduler hasn't run yet
        return {
            "openai": "gpt-4o",
            "anthropic": "claude-3-5-sonnet-20241022",
            "mistral": "mistral-large-latest",
            "deepseek": "deepseek-chat"
        }


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")


def get_provider_config(provider_name):
    """
    Get the API configuration for a specific provider.

    Returns a dict with:
    - endpoint: API endpoint URL
    - headers_fn: Function to generate headers
    - payload_fn: Function to generate request payload
    - response_path: Path to extract content from response
    - model_key: Key for current model ID in model config
    """

    model_config = load_model_config()

    providers = {
        "openai": {
            "endpoint": "https://api.openai.com/v1/chat/completions",
            "headers_fn": lambda: {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            "payload_fn": lambda model_id, prompt: {
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 1000
            },
            "response_path": ["choices", 0, "message", "content"],
            "model_id": model_config.get("openai", "gpt-4o"),
            "models_endpoint": "https://api.openai.com/v1/models",
            "models_auth": lambda: {"Authorization": f"Bearer {OPENAI_API_KEY}"}
        },
        "anthropic": {
            "endpoint": "https://api.anthropic.com/v1/messages",
            "headers_fn": lambda: {
                "x-api-key": CLAUDE_API_KEY,
                "Content-Type": "application/json",
                "anthropic-version": "2024-10-01"  # Updated to support latest models
            },
            "payload_fn": lambda model_id, prompt: {
                "model": model_id,
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}]
            },
            "response_path": ["content", 0, "text"],
            "model_id": model_config.get("anthropic", "claude-3-5-sonnet-20241022"),
            "models_endpoint": "https://api.anthropic.com/v1/models",
            "models_auth": lambda: {"x-api-key": CLAUDE_API_KEY, "anthropic-version": "2024-10-01"}
        },
        "mistral": {
            "endpoint": "https://api.mistral.ai/v1/chat/completions",
            "headers_fn": lambda: {
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
                "Content-Type": "application/json"
            },
            "payload_fn": lambda model_id, prompt: {
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 1000
            },
            "response_path": ["choices", 0, "message", "content"],
            "model_id": model_config.get("mistral", "mistral-large-latest"),
            "models_endpoint": "https://api.mistral.ai/v1/models",
            "models_auth": lambda: {"Authorization": f"Bearer {MISTRAL_API_KEY}"}
        },
        "deepseek": {
            "endpoint": "https://api.deepseek.com/v1/chat/completions",
            "headers_fn": lambda: {
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            "payload_fn": lambda model_id, prompt: {
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 1000
            },
            "response_path": ["choices", 0, "message", "content"],
            "model_id": model_config.get("deepseek", "deepseek-chat"),
            "models_endpoint": "https://api.deepseek.com/v1/models",
            "models_auth": lambda: {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
        }
    }

    return providers.get(provider_name)


def get_value_at_path(obj, path):
    """
    Extract a value from a nested dict/list using a path.
    Example: path = ["choices", 0, "message", "content"]
    """
    current = obj
    for key in path:
        if isinstance(current, list):
            current = current[int(key)]
        else:
            current = current[key]
    return current
