import requests
import json
import logging
import os
from datetime import datetime
import time
from model_registry import get_provider_config

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Load API keys from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

def discover_latest_models():
    """
    Query each provider's models endpoint to discover the latest available model.
    Returns a dict mapping provider names to model IDs.
    """
    models = {}
    providers = ["openai", "anthropic", "mistral", "deepseek"]

    for provider in providers:
        try:
            config = get_provider_config(provider)
            endpoint = config["models_endpoint"]
            headers = config["models_auth"]()

            logging.info(f"Querying {provider} models endpoint: {endpoint}")
            response = requests.get(endpoint, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # Extract latest model based on provider response format
                if provider == "openai":
                    # OpenAI returns list of models, most recent first
                    if "data" in data and len(data["data"]) > 0:
                        model_id = data["data"][0]["id"]
                        models[provider] = model_id
                        logging.info(f"OpenAI latest model: {model_id}")
                    else:
                        logging.warning(f"No models returned from OpenAI")

                elif provider == "anthropic":
                    # Anthropic returns models in 'data' array, most recent first
                    if "data" in data and len(data["data"]) > 0:
                        model_id = data["data"][0]["id"]
                        models[provider] = model_id
                        logging.info(f"Anthropic latest model: {model_id}")
                    else:
                        logging.warning(f"No models returned from Anthropic")

                elif provider == "mistral":
                    # Mistral returns models in 'data' array
                    if "data" in data and len(data["data"]) > 0:
                        model_id = data["data"][0]["id"]
                        models[provider] = model_id
                        logging.info(f"Mistral latest model: {model_id}")
                    else:
                        logging.warning(f"No models returned from Mistral")

                elif provider == "deepseek":
                    # DeepSeek returns models in 'data' array
                    if "data" in data and len(data["data"]) > 0:
                        model_id = data["data"][0]["id"]
                        models[provider] = model_id
                        logging.info(f"DeepSeek latest model: {model_id}")
                    else:
                        logging.warning(f"No models returned from DeepSeek")

            else:
                logging.error(f"Error querying {provider}: HTTP {response.status_code}")

        except Exception as e:
            logging.error(f"Error discovering models for {provider}: {e}")

    return models


def save_model_config(models):
    """Save discovered models to /tmp for sharing between dynos"""
    try:
        # Map discovered model IDs to their official documentation URLs
        docs_urls = {
            "openai": "https://platform.openai.com/docs/models",
            "anthropic": "https://docs.anthropic.com/about-claude/models/overview",
            "mistral": "https://docs.mistral.ai/getting-started/models/",
            "deepseek": "https://api-docs.deepseek.com/models"
        }

        config_data = {
            "last_updated": datetime.now().isoformat() + "Z",
            "source": "scheduler_auto_discovery",
        }

        # Add model ID and docs URL for each provider
        for provider, model_id in models.items():
            config_data[provider] = {
                "id": model_id,
                "docs_url": docs_urls.get(provider, "")
            }

        with open("/tmp/model_config.json", "w") as f:
            json.dump(config_data, f, indent=2)
        logging.info(f"Model config updated with discovered models and doc URLs: {models}")
    except Exception as e:
        logging.error(f"Error saving model config: {e}")


def get_model_metadata():
    """Discover and update available models from each provider"""
    logging.info("Starting model discovery...")

    # Discover latest models from each provider
    discovered_models = discover_latest_models()

    if discovered_models:
        logging.info(f"Discovered models: {discovered_models}")
        save_model_config(discovered_models)
        return discovered_models
    else:
        logging.warning("No models discovered, keeping existing config")
        return {}

# New function to get credit status from DeepSeek API
def get_credit_status():
    """Get credit balance from DeepSeek API and calculate status"""
    try:
        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
        response = requests.get("https://api.deepseek.com/user/balance", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            # Extract total balance
            total_balance = float(data["balance_infos"][0]["total_balance"])
            # Assuming initial or max balance is 100 units
            initial_balance = 10.00  # $10 = 100% battery
            
            # Calculate percentage remaining
            percentage = (total_balance / initial_balance) * 100
            
            # Determine status based on percentage
            if percentage > 60:
                status = "green"
                icon = "fa-battery-full"
            elif percentage > 10:
                status = "yellow"
                icon = "fa-battery-half"
            else:
                status = "red"
                icon = "fa-battery-quarter"
                
            credit_info = {
                "status": status,
                "icon": icon,
                "percentage": round(percentage),
                "balance": total_balance,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Save to a JSON file for the frontend to access
            with open('/tmp/credit_status.json', 'w') as f:
                json.dump(credit_info, f, indent=2)
                
            logging.info(f"Credit status updated: {status} ({percentage}%)")
            return credit_info
            
        else:
            logging.error(f"Error getting DeepSeek balance: {response.status_code}")
            return {"status": "unknown", "icon": "fa-battery", "percentage": 0}
            
    except Exception as e:
        logging.error(f"Error checking credit balance: {e}")
        return {"status": "unknown", "icon": "fa-battery", "percentage": 0}

# Updated run_scheduler function to also check credit status
def run_scheduler():
    """Run this script once every 24 hours to update model metadata and credit status"""
    while True:
        try:
            logging.info("Fetching model metadata...")
            discovered_models = get_model_metadata()
            if discovered_models:
                logging.info(f"Successfully discovered {len(discovered_models)} models: {discovered_models}")
            else:
                logging.warning("No new models discovered, using existing config")

            # Get credit status
            logging.info("Checking API credit status...")
            credit_status = get_credit_status()
            logging.info(f"Credit status: {credit_status['status']} ({credit_status['percentage']}%)")

            # Sleep for 24 hours
            logging.info("Next update in 24 hours")
            time.sleep(24 * 60 * 60)  # 24 hours in seconds
        except Exception as e:
            logging.error(f"Error in scheduler: {e}")
            # If there's an error, wait 1 hour and try again
            logging.info("Retrying in 1 hour")
            time.sleep(60 * 60)  # 1 hour in seconds

if __name__ == "__main__":
    # Create static directory if it doesn't exist
    os.makedirs("static", exist_ok=True)
    
    # Run the scheduler
    run_scheduler()