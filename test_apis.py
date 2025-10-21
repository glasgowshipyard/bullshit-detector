#!/usr/bin/env python3
"""Test API discovery and model availability"""

import os
import sys
import requests

# Parse secret keys file
def load_keys():
    keys = {}
    with open('secret-keys.dmb', 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            parts = line.split()
            if len(parts) >= 2:
                keys[parts[0]] = parts[1]
    return keys

keys = load_keys()
print("Loaded keys:", list(keys.keys()))
print()

# Test each provider
providers = {
    "openai": {
        "endpoint": "https://api.openai.com/v1/models",
        "auth": {"Authorization": f"Bearer {keys.get('OPENAI_API_KEY')}"}
    },
    "anthropic": {
        "endpoint": "https://api.anthropic.com/v1/models",
        "auth": {
            "x-api-key": keys.get('CLAUDE_API_KEY'),
            "anthropic-version": "2023-06-01"
        }
    },
    "mistral": {
        "endpoint": "https://api.mistral.ai/v1/models",
        "auth": {"Authorization": f"Bearer {keys.get('MISTRAL_API_KEY')}"}
    },
    "deepseek": {
        "endpoint": "https://api.deepseek.com/v1/models",
        "auth": {"Authorization": f"Bearer {keys.get('DEEPSEEK_API_KEY')}"}
    }
}

for provider, config in providers.items():
    print(f"Testing {provider}...")
    try:
        response = requests.get(config["endpoint"], headers=config["auth"], timeout=5)
        print(f"  Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                print(f"  First model full response:")
                import json as j
                print(f"  {j.dumps(data['data'][0], indent=2)}")
        else:
            print(f"  Error: {response.text[:200]}")
    except Exception as e:
        print(f"  Exception: {e}")
    print()
