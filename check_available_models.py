#!/usr/bin/env python3
"""
Script to check actually available models from OpenAI and Anthropic APIs
"""
import requests
import json
import os
from datetime import datetime

# Load API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

def check_openai_models():
    """Get available OpenAI models"""
    print("🔍 Checking OpenAI models...")
    try:
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
        response = requests.get("https://api.openai.com/v1/models", headers=headers)
        
        if response.status_code == 200:
            models = response.json()
            # Filter for chat/completion models
            chat_models = [m for m in models['data'] if 'gpt' in m['id'].lower()]
            print(f"✅ Found {len(chat_models)} GPT models:")
            for model in sorted(chat_models, key=lambda x: x['id']):
                print(f"   - {model['id']}")
            return [m['id'] for m in chat_models]
        else:
            print(f"❌ OpenAI API error: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ OpenAI error: {e}")
        return []

def check_claude_models():
    """Get available Claude models"""
    print("\n🔍 Checking Anthropic models...")
    try:
        headers = {
            "x-api-key": CLAUDE_API_KEY,
            "anthropic-version": "2023-06-01"
        }
        response = requests.get("https://api.anthropic.com/v1/models", headers=headers)
        
        if response.status_code == 200:
            models = response.json()
            print(f"✅ Found {len(models['data'])} Claude models:")
            for model in models['data']:
                print(f"   - {model['id']} ({model.get('display_name', 'N/A')})")
            return [m['id'] for m in models['data']]
        else:
            print(f"❌ Claude API error: {response.status_code}")
            print(f"Response: {response.text}")
            return []
    except Exception as e:
        print(f"❌ Claude error: {e}")
        return []

def test_model(model_id, provider="openai"):
    """Test if a specific model works"""
    test_prompt = "Respond with just 'OK' if you can understand this."
    
    try:
        if provider == "openai":
            headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
            payload = {"model": model_id, "messages": [{"role": "user", "content": test_prompt}], "max_tokens": 10}
            response = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
        
        elif provider == "claude":
            headers = {
                "x-api-key": CLAUDE_API_KEY,
                "Content-Type": "application/json", 
                "anthropic-version": "2023-06-01"
            }
            payload = {"model": model_id, "max_tokens": 10, "messages": [{"role": "user", "content": test_prompt}]}
            response = requests.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers)
        
        return response.status_code == 200
    except:
        return False

def main():
    print("🚀 Checking available models for Bullshit Detector\n")
    
    # Check available models
    openai_models = check_openai_models()
    claude_models = check_claude_models()
    
    # Test specific models we want to use
    print("\n🧪 Testing specific models...")
    
    test_models = {
        "openai": ["gpt-4o", "gpt-4", "gpt-4-turbo", "gpt-4.1", "gpt-3.5-turbo"],
        "claude": ["claude-3-5-sonnet-20241022", "claude-3-5-sonnet-latest", "claude-sonnet-4-20250514", "claude-3-7-sonnet-latest"]
    }
    
    results = {}
    
    for provider, models in test_models.items():
        results[provider] = {}
        for model in models:
            if model in (openai_models if provider == "openai" else claude_models):
                working = test_model(model, provider)
                status = "✅ WORKS" if working else "❌ FAILS"
                print(f"   {provider.upper()}: {model} - {status}")
                results[provider][model] = working
            else:
                print(f"   {provider.upper()}: {model} - 🚫 NOT AVAILABLE")
                results[provider][model] = False
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"/tmp/model_test_results_{timestamp}.json", "w") as f:
        json.dump({
            "timestamp": timestamp,
            "available_openai_models": openai_models,
            "available_claude_models": claude_models,
            "test_results": results
        }, f, indent=2)
    
    print(f"\n📊 Results saved to /tmp/model_test_results_{timestamp}.json")
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    working_openai = [m for m, works in results["openai"].items() if works]
    working_claude = [m for m, works in results["claude"].items() if works]
    
    if working_openai:
        print(f"   Use OpenAI model: {working_openai[0]}")
    if working_claude:
        print(f"   Use Claude model: {working_claude[0]}")

if __name__ == "__main__":
    main()