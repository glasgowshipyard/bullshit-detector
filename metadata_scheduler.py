import requests
import json
import logging
import os
from datetime import datetime
import time

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Load API keys from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

def get_model_metadata():
    """Collect metadata about AI models including training cutoff dates and token usage"""
    metadata = {
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        "models": {}
    }
    
    # OpenAI (GPT-4o)
    try:
        # Get model info
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
        response = requests.get("https://api.openai.com/v1/models/gpt-4o", headers=headers)
        if response.status_code == 200:
            data = response.json()
            # In reality, you'd extract this from the response if available
            metadata["models"]["gpt-4o"] = {
                "name": "GPT-4o",
                "provider": "OpenAI",
                "training_cutoff": "April 2023",
                "status": "active"
            }
            
        # Get token usage - typically from the billing API
        # This is a simplified example - actual implementation depends on OpenAI's billing API
        usage_response = requests.get("https://api.openai.com/v1/usage", headers=headers)
        if usage_response.status_code == 200:
            usage_data = usage_response.json()
            # Extract token usage
            metadata["models"]["gpt-4o"]["token_usage"] = {
                "tokens_used": "Usage data not available from API",
                "tokens_remaining": "N/A"
            }
    except Exception as e:
        logging.error(f"Error getting OpenAI metadata: {e}")
        metadata["models"]["gpt-4o"] = {
            "name": "GPT-4o", 
            "provider": "OpenAI",
            "training_cutoff": "April 2023", 
            "status": "error",
            "error": str(e)
        }
    
    # Anthropic (Claude)
    try:
        headers = {
            "x-api-key": CLAUDE_API_KEY,
            "anthropic-version": "2023-06-01"
        }
        # Anthropic doesn't have a public model info API, so we're using hardcoded info
        metadata["models"]["claude-3"] = {
            "name": "Claude 3 Opus",
            "provider": "Anthropic",
            "training_cutoff": "August 2023",
            "status": "active",
            "token_usage": {
                "tokens_used": "Usage data not available from API",
                "tokens_remaining": "N/A"
            }
        }
    except Exception as e:
        logging.error(f"Error getting Claude metadata: {e}")
        metadata["models"]["claude-3"] = {
            "name": "Claude 3 Opus", 
            "provider": "Anthropic",
            "training_cutoff": "August 2023", 
            "status": "error",
            "error": str(e)
        }
    
    # Mistral AI
    try:
        headers = {"Authorization": f"Bearer {MISTRAL_API_KEY}"}
        # Mistral doesn't have a public model info API, so we're using hardcoded info
        metadata["models"]["mistral"] = {
            "name": "Mistral Large",
            "provider": "Mistral AI",
            "training_cutoff": "December 2023",
            "status": "active",
            "token_usage": {
                "tokens_used": "Usage data not available from API",
                "tokens_remaining": "N/A"
            }
        }
    except Exception as e:
        logging.error(f"Error getting Mistral metadata: {e}")
        metadata["models"]["mistral"] = {
            "name": "Mistral Large", 
            "provider": "Mistral AI",
            "training_cutoff": "December 2023", 
            "status": "error",
            "error": str(e)
        }
    
    # DeepSeek
    try:
        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
        # DeepSeek doesn't have a public model info API, so we're using hardcoded info
        metadata["models"]["deepseek"] = {
            "name": "DeepSeek Chat",
            "provider": "DeepSeek AI",
            "training_cutoff": "January 2023",
            "status": "active",
            "token_usage": {
                "tokens_used": "Usage data not available from API",
                "tokens_remaining": "N/A"
            }
        }
    except Exception as e:
        logging.error(f"Error getting DeepSeek metadata: {e}")
        metadata["models"]["deepseek"] = {
            "name": "DeepSeek Chat", 
            "provider": "DeepSeek AI",
            "training_cutoff": "January 2023", 
            "status": "error",
            "error": str(e)
        }
    
    # Save to a JSON file
    try:
        with open('/tmp/model_metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        logging.info(f"Metadata saved to static/model_metadata.json")
    except Exception as e:
        logging.error(f"Error saving metadata: {e}")
    
    return metadata

# New function to get credit status from DeepSeek API
def get_credit_status():
    """Get credit balance from DeepSeek API and calculate status"""
    try:
        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
        response = requests.get("https://api.deepseek.com/user/balance", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            # Extract total balance
            total_balance = data.get("total_balance", 0)
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
            metadata = get_model_metadata()
            logging.info(f"Successfully collected metadata for {len(metadata['models'])} models")
            
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