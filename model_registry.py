"""
Model Provider Registry

Defines how to interact with each AI provider.
Model IDs are auto-discovered and updated by the scheduler.
"""

import os

# Load the latest discovered models (updated by scheduler)
def load_model_config():
    """Load model IDs discovered by the scheduler from /tmp"""
    import json
    config_file = "/tmp/model_config.json"

    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
            # Extract just the model IDs for backward compatibility
            return {
                "last_updated": config.get("last_updated"),
                "source": config.get("source"),
                "openai": config.get("openai", {}).get("id") if isinstance(config.get("openai"), dict) else config.get("openai"),
                "anthropic": config.get("anthropic", {}).get("id") if isinstance(config.get("anthropic"), dict) else config.get("anthropic"),
                "mistral": config.get("mistral", {}).get("id") if isinstance(config.get("mistral"), dict) else config.get("mistral"),
                "deepseek": config.get("deepseek", {}).get("id") if isinstance(config.get("deepseek"), dict) else config.get("deepseek")
            }
    else:
        # Last known good fallback (will be updated by scheduler on first run)
        return {
            "last_updated": "2025-10-20T00:00:00Z",
            "source": "last_known_good_fallback",
            "openai": "gpt-4o",
            "anthropic": "claude-3-opus-20240229",
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
                "anthropic-version": "2023-06-01"
            },
            "payload_fn": lambda model_id, prompt: {
                "model": model_id,
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}]
            },
            "response_path": ["content", 0, "text"],
            "model_id": model_config.get("anthropic", "claude-3-5-sonnet-20241022"),
            "models_endpoint": "https://api.anthropic.com/v1/models",
            "models_auth": lambda: {"x-api-key": CLAUDE_API_KEY, "anthropic-version": "2023-06-01"}
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


def load_full_model_config():
    """Load full model config with IDs and doc URLs for metadata endpoint from /tmp"""
    import json
    config_file = "/tmp/model_config.json"

    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    else:
        # Last known good fallback with doc URLs
        return {
            "last_updated": "2025-10-20T00:00:00Z",
            "source": "last_known_good_fallback",
            "openai": {
                "id": "gpt-4o",
                "docs_url": "https://platform.openai.com/docs/models"
            },
            "anthropic": {
                "id": "claude-3-opus-20240229",
                "docs_url": "https://docs.anthropic.com/about-claude/models/overview"
            },
            "mistral": {
                "id": "mistral-large-latest",
                "docs_url": "https://docs.mistral.ai/getting-started/models/"
            },
            "deepseek": {
                "id": "deepseek-chat",
                "docs_url": "https://api-docs.deepseek.com/models"
            }
        }
