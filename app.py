from flask import Flask, request, jsonify, render_template, redirect
import logging
import os
import requests
import json
import re
import stripe
from datetime import datetime

from flask_sslify import SSLify
from preprocess import preprocess_query
from model_registry import get_provider_config, get_value_at_path, load_full_model_config
from apscheduler.schedulers.background import BackgroundScheduler

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')

# Force SSL
sslify = SSLify(app, permanent=True)

# Load Stripe API key (others are loaded by model_registry)
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
stripe.api_key = STRIPE_SECRET_KEY

# Model discovery functions (moved from metadata_scheduler.py)
def discover_latest_models():
    """
    Query each provider's models endpoint to discover the latest available model.
    Sorts by creation timestamp to find the actual latest.
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

                # Extract latest model by sorting by creation timestamp
                if "data" in data and len(data["data"]) > 0:
                    model_list = data["data"]

                    # Sort by creation timestamp to find latest
                    def get_timestamp(model):
                        if "created_at" in model:
                            # ISO format string (Anthropic)
                            try:
                                dt = datetime.fromisoformat(model["created_at"].replace("Z", "+00:00"))
                                return dt.timestamp()
                            except:
                                return 0
                        elif "created" in model:
                            # Unix timestamp (OpenAI, Mistral)
                            return model["created"]
                        return 0

                    sorted_models = sorted(model_list, key=get_timestamp, reverse=True)
                    model_id = sorted_models[0]["id"]
                    models[provider] = model_id
                    logging.info(f"{provider.capitalize()} latest model: {model_id}")
                else:
                    logging.warning(f"No models returned from {provider}")

            else:
                logging.error(f"Error querying {provider}: HTTP {response.status_code}")

        except Exception as e:
            logging.error(f"Error discovering models for {provider}: {e}")

    return models


def save_model_config(models):
    """Save discovered models to /tmp with doc URLs"""
    try:
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


def run_model_discovery():
    """Run model discovery job"""
    logging.info("Starting scheduled model discovery...")
    discovered_models = discover_latest_models()
    if discovered_models:
        logging.info(f"Discovered models: {discovered_models}")
        save_model_config(discovered_models)
    else:
        logging.warning("No models discovered")


# Initialize background scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(run_model_discovery, 'interval', hours=24)
scheduler.start()

# Run discovery immediately on startup
run_model_discovery()

# Function to strip markdown formatting
def strip_markdown(text):
    """Remove common markdown formatting from text"""
    if not text:
        return text
        
    # Remove bold/italic formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    # Remove headers
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    # Remove code blocks
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    # Remove inline code
    text = re.sub(r'`(.*?)`', r'\1', text)
    return text

# Detect recusals and policy limitations
def detect_recusal(content):
    """
    Detect if a model is recusing itself from judgment due to paradox, 
    philosophical objection, or unanswerable nature of the question
    """
    recusal_patterns = [
        r"\brecuse\b",
        r"\bparadox\b", 
        r"\bself-referential\b",
        r"\bcannot be definitively labeled\b",
        r"\binherently unanswerable\b",
        r"\bphilosophical\b.*\bobjection\b",
        r"\bcategory error\b",
        r"\bunanswerable by design\b"
    ]
    
    content_lower = content.lower()
    return any(re.search(pattern, content_lower) for pattern in recusal_patterns)

def detect_policy_limitation(content):
    """
    Detect if a model is declining to answer due to policy constraints
    rather than factual uncertainty
    """
    policy_patterns = [
        r"\bpolicy_limited\b",
        r"\bi (don't|do not) feel comfortable\b",
        r"\bi apologize.*cannot\b",
        r"\bnot appropriate to discuss\b",
        r"\brecommend consulting\b",
        r"\bwould suggest referring to\b",
        r"\bplease consult official sources\b",
        r"\bit's important to rely on\b",
        r"\bi'm not comfortable speculating\b"
    ]
    
    content_lower = content.lower()
    return any(re.search(pattern, content_lower) for pattern in policy_patterns)

# Function to query different AI models
def query_model(provider_name, prompt):
    """
    Query an AI model provider using the model registry.

    Args:
        provider_name (str): Provider identifier ("openai", "anthropic", "mistral", "deepseek")
        prompt (str): The preprocessed query to send

    Returns:
        dict: Standardized response with keys:
            - success: Boolean indicating if the request succeeded
            - content: The model's response text
            - model: Name of the model that provided the response
            - error: Error message (if success is False)
    """
    try:
        # Get provider configuration from registry
        config = get_provider_config(provider_name)

        if not config:
            return {
                "success": False,
                "content": None,
                "model": provider_name,
                "error": f"Unknown provider: {provider_name}"
            }

        endpoint = config["endpoint"]
        headers = config["headers_fn"]()
        model_id = config["model_id"]
        payload = config["payload_fn"](model_id, prompt)
        response_path = config["response_path"]

        logging.debug(f"Querying {provider_name} with model {model_id}")

        # Make the API call with timeout
        response = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        logging.debug(f"{provider_name} API status code: {response.status_code}")

        if response.status_code != 200:
            error_msg = response.text[:200] if response.text else f"HTTP {response.status_code}"
            logging.error(f"Error from {provider_name}: {error_msg}")
            return {
                "success": False,
                "content": None,
                "model": provider_name,
                "error": f"API returned {response.status_code}"
            }

        try:
            response_json = response.json()
        except ValueError as e:
            logging.error(f"{provider_name} returned non-JSON response: {response.text[:200]}")
            return {
                "success": False,
                "content": None,
                "model": provider_name,
                "error": f"Non-JSON response: {str(e)}"
            }

        logging.debug(f"{provider_name} response JSON: {response_json}")

        # Extract content using the provider's response path
        try:
            content = get_value_at_path(response_json, response_path)
            content = strip_markdown(content)  # Normalize formatting

            return {
                "success": True,
                "content": content,
                "model": provider_name,
                "error": None
            }
        except (KeyError, IndexError, TypeError) as e:
            logging.error(f"Could not extract content from {provider_name} response: {e}")
            logging.error(f"Full response JSON: {response_json}")
            logging.error(f"Expected response_path: {response_path}")
            return {
                "success": False,
                "content": None,
                "model": provider_name,
                "error": f"Malformed response: {str(e)}"
            }

    except requests.Timeout:
        logging.error(f"Timeout querying {provider_name}")
        return {
            "success": False,
            "content": None,
            "model": provider_name,
            "error": "Request timeout"
        }
    except Exception as e:
        logging.error(f"Error querying {provider_name}: {e}")
        return {
            "success": False,
            "content": None,
            "model": provider_name,
            "error": str(e)
        }

# Function to analyze model responses and calculate confidence
def analyze_responses(responses):
    """
    Analyze responses from multiple models to determine verdict and confidence,
    accounting for policy-based hesitations and uncertainty
    
    Args:
        responses (dict): Dictionary of model responses
        
    Returns:
        dict: Analysis results with verdict and confidence
    """
    # Extract TRUE/FALSE/UNCERTAIN judgments from each model
    judgments = {}
    policy_limited_responses = []
    uncertain_responses = []
    
    # Policy hesitation patterns that indicate reluctance but not factual uncertainty
    policy_patterns = [
        "I apologize", "I do not feel comfortable", "I would suggest referring to",
        "I cannot speculate", "not appropriate to discuss", "recommend consulting",
        "would advise looking at", "suggest referring to factual information",
        "it's important to rely on", "please consult official sources"
    ]
    
    # Uncertainty patterns that indicate factual uncertainty rather than policy limits
    uncertainty_patterns = [
        "cannot be definitively answered", "complex issue", "not enough evidence",
        "remains disputed", "difficult to determine", "would require more information",
        "cannot be answered with a simple", "insufficient evidence", "uncertain",
        "depends on", "ambiguous", "unclear", "debated", "controversial"
    ]
    
    for model, response in responses.items():
        if not (response["success"] and response["content"]):
            continue
            
        # Check for explicit opt-outs first
        if detect_recusal(response["content"]):
            judgments[model] = "RECUSE"
            continue
            
        if detect_policy_limitation(response["content"]):
            judgments[model] = "POLICY_LIMITED"
            policy_limited_responses.append(model)
            continue
        
        content = response["content"].upper()
        text = response["content"].lower()
        
        # Check for uncertainty indicators
        uncertain = any(pattern in text for pattern in uncertainty_patterns)
        
        # Extract explicit judgments
        if "FALSE" in content and not ("NOT FALSE" in content or "ISN'T FALSE" in content):
            if uncertain:
                judgments[model] = "UNCERTAIN"
                uncertain_responses.append(model)
            else:
                judgments[model] = "FALSE"
        elif "TRUE" in content and not ("NOT TRUE" in content or "ISN'T TRUE" in content):
            if uncertain:
                judgments[model] = "UNCERTAIN"
                uncertain_responses.append(model)
            else:
                judgments[model] = "TRUE"
        elif "UNCERTAIN" in content or uncertain:
            judgments[model] = "UNCERTAIN"
            uncertain_responses.append(model)
        else:
            judgments[model] = "UNCERTAIN"
            uncertain_responses.append(model)
    
    # Count different judgments - exclude RECUSE and POLICY_LIMITED
    substantive_judgments = {k: v for k, v in judgments.items() if v not in ["RECUSE", "POLICY_LIMITED"]}
    judgment_counts = {"TRUE": 0, "FALSE": 0, "UNCERTAIN": 0}
    for judgment in substantive_judgments.values():
        judgment_counts[judgment] += 1

    logging.info(f"Judgments dict: {judgments}")
    logging.info(f"Substantive judgments: {substantive_judgments}")
    logging.info(f"Judgment counts: {judgment_counts}")

    # Determine the majority verdict
    total_models = len(substantive_judgments)
    if judgment_counts["UNCERTAIN"] >= (total_models / 3) or judgment_counts["UNCERTAIN"] >= 2:
        majority_verdict = "UNCERTAIN"
    else:
        # Otherwise use the most common verdict
        majority_verdict = max(
            ("TRUE", judgment_counts["TRUE"]), 
            ("FALSE", judgment_counts["FALSE"]),
            ("UNCERTAIN", judgment_counts["UNCERTAIN"]),
            key=lambda x: x[1]
        )[0]
    
    # If there's a tie between TRUE and FALSE, use UNCERTAIN
    if judgment_counts["TRUE"] == judgment_counts["FALSE"] and judgment_counts["TRUE"] > 0:
        majority_verdict = "UNCERTAIN"
    
    # Calculate confidence percentage
    if total_models == 0:
        confidence = 0
    else:
        # Calculate effective agreement (non-policy-limited models + agreeing policy-limited models)
        agreement_count = judgment_counts[majority_verdict]
        
        # If verdict is UNCERTAIN, confidence is based on uncertainty agreement
        if majority_verdict == "UNCERTAIN":
            # Cap confidence for UNCERTAIN verdicts
            confidence = min(70, (agreement_count / total_models) * 100)
        else:
            # For TRUE/FALSE verdicts
            policy_aligned = sum(1 for model in policy_limited_responses 
                               if model in judgments and judgments[model] == majority_verdict)
            
            # Calculate effective non-policy models
            non_policy_total = total_models - len(policy_limited_responses)
            
            if non_policy_total > 0:
                # Give more weight to direct, non-policy-limited responses
                base_confidence = ((agreement_count - policy_aligned) / non_policy_total) * 100
                
                # Add bonus for policy-limited responses that still align with majority
                policy_bonus = (policy_aligned / total_models) * 20  # 20% max bonus
                
                confidence = min(100, base_confidence + policy_bonus)
            else:
                # If all responses are policy-limited, just use agreement percentage
                confidence = (agreement_count / total_models) * 90  # Cap at 90% if all are policy-limited
            
            # Reduce confidence if there are uncertain responses
            if judgment_counts["UNCERTAIN"] > 0:
                uncertainty_penalty = (judgment_counts["UNCERTAIN"] / total_models) * 30
                confidence = max(40, confidence - uncertainty_penalty)
    
    # Determine confidence level text
    if confidence >= 90:
        confidence_level = "VERY HIGH"
    elif confidence >= 70:
        confidence_level = "HIGH"
    elif confidence >= 50:
        confidence_level = "MEDIUM"
    elif confidence >= 30:
        confidence_level = "LOW"
    else:
        confidence_level = "VERY LOW"

    logging.info(f"FINAL CONFIDENCE: verdict={majority_verdict}, confidence={round(confidence)}%, level={confidence_level}, agreement_count={agreement_count}, total_models={total_models}, uncertain_count={judgment_counts['UNCERTAIN']}")

    return {
        "verdict": majority_verdict,
        "confidence_percentage": round(confidence),
        "confidence_level": confidence_level,
        "model_judgments": judgments,
        "policy_limited_responses": policy_limited_responses,
        "uncertain_responses": uncertain_responses
    }

@app.route('/ask', methods=['POST'])
def ask():
    try:
        # Try different methods to get the JSON data
        if request.is_json:
            data = request.get_json()
        else:
            # Force parsing as JSON even if Content-Type is incorrect
            data = request.get_json(force=True)
        
        logging.debug(f"Received request data: {data}")
        
        if not data or "query" not in data:
            return jsonify({"error": "No query provided"}), 400
        
        raw_query = data["query"].strip()

        # Preprocess the query before sending to LLMs
        structured_query = preprocess_query(raw_query)

        # Get responses from all providers
        responses = {}
        responses["openai"] = query_model("openai", structured_query)
        responses["anthropic"] = query_model("anthropic", structured_query)
        responses["mistral"] = query_model("mistral", structured_query)
        responses["deepseek"] = query_model("deepseek", structured_query)
        
        # Analyze responses to determine verdict and confidence
        analysis = analyze_responses(responses)

        return jsonify({
            "query": raw_query,
            "structured_query": structured_query,
            "responses": responses,
            "analysis": analysis
        })
    except Exception as e:
        logging.error(f"Error in /ask route: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/model-metadata', methods=['GET'])
def get_model_metadata():
    """Return model metadata with doc URLs for the frontend"""
    try:
        # Load model config (either from scheduler or fallback)
        config = load_full_model_config()

        # Format for frontend with provider names
        provider_names = {
            "openai": "OpenAI",
            "anthropic": "Anthropic",
            "mistral": "Mistral AI",
            "deepseek": "DeepSeek"
        }

        formatted_metadata = {
            "last_updated": config.get("last_updated"),
            "source": config.get("source"),
            "models": {}
        }

        for provider, provider_name in provider_names.items():
            if provider in config:
                model_info = config[provider]
                if isinstance(model_info, dict):
                    formatted_metadata["models"][provider] = {
                        "id": model_info.get("id"),
                        "provider": provider_name,
                        "docs_url": model_info.get("docs_url")
                    }

        return jsonify(formatted_metadata)
    except Exception as e:
        logging.error(f"Error fetching model metadata: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/credit-status')
def credit_status():
    try:
        # Check if credit status file exists
        credit_file = "/tmp/credit_status.json"
        if os.path.exists(credit_file):
            with open(credit_file, 'r') as f:
                credit_data = json.load(f)
                return jsonify(credit_data)
        else:
            # Return a default status if file doesn't exist
            return jsonify({
                "status": "unknown",
                "icon": "fa-battery",
                "percentage": 100,
                "balance": "N/A",
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
    except Exception as e:
        logging.error(f"Error fetching credit status: {e}")
        return jsonify({"error": str(e)}), 500

from metadata_scheduler import get_model_metadata, get_credit_status

@app.route('/admin/run-scheduler', methods=['POST'])
def trigger_scheduler():
    try:
        # Run the metadata collection
        get_model_metadata()
        # Run the credit status check  
        get_credit_status()
        return jsonify({"status": "success", "message": "Scheduler completed"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        data = request.get_json()
        amount = data.get('amount', 500)  # Default to $5.00 if not specified
        
        # Create a checkout session with dynamic pricing
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Bullshit Detector Donation',
                        'description': 'Support truth detection in the age of AI',
                    },
                    'unit_amount': amount,  # This is in cents ($1 = 100 cents)
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url='https://bullshitdetector.ai/success',
            cancel_url='https://bullshitdetector.ai/',
        )
        
        return jsonify({'id': session.id})
        
    except Exception as e:
        logging.error(f"Stripe error: {e}")
        return jsonify({'error': str(e)}), 500
@app.route('/success')
def success():
    return '''
    <html>
        <head>
            <title>Thank You!</title>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; text-align: center; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
                .container { max-width: 600px; padding: 40px; background: rgba(30, 41, 59, 0.8); backdrop-filter: blur(10px); border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.1); }
                h1 { color: #3b82f6; margin-bottom: 20px; }
                .link { display: inline-block; margin-top: 20px; padding: 10px 20px; background: #3b82f6; color: white; text-decoration: none; border-radius: 6px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Thank You!</h1>
                <p>Your donation helps keep the Bullshit Detector running.</p>
                <p>Credits will be restored within 24 hours.</p>
                <a href="/" class="link">Return to Bullshit Detector</a>
            </div>
        </body>
    </html>
    '''

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)